from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import src.dynasty_genius.eval.qb_validation as qb

PIN = "37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d"
DATASETS = ("weekly", "season_summary", "players", "rosters", "ff_playerids", "draft_picks", "pbp")


def _registration() -> dict:
    return json.loads(Path("docs/validation/2026-07-21-qb-1-study-registration.json").read_text())


def _receipt(tmp_path: Path, *, registration_pin: str = PIN) -> Path:
    raw = tmp_path / "app/data/backtest/qb_validation/raw"
    datasets = {}
    for name in DATASETS:
        snapshot = raw / name / f"{name}.parquet"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(name.encode())
        datasets[name] = {"snapshots": [{
            "file": str(snapshot.relative_to(tmp_path)),
            "rows": 1,
            "columns": 1,
            "bytes": snapshot.stat().st_size,
            "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        }]}
    (raw / "fetch_manifest.json").write_text(json.dumps({
        "registration_pin": registration_pin,
        "finished_at": "2026-08-14T16:00:00Z",
        "nflreadpy_version": "fixture",
        "datasets": datasets,
    }))
    return raw


def test_admitted_receipt_is_rejected_by_existing_d1_gate(tmp_path: Path) -> None:
    states = qb.admit_fetch_manifest(
        _receipt(tmp_path), repo_root=tmp_path,
        frame_loader=lambda _path: pd.DataFrame({"x": [1]}),
    )
    with pytest.raises(qb.QBValidationFailure, match="source_unavailable.*completeness"):
        qb.load_validation_sources(states)


def test_wrong_registration_pin_is_admitted(tmp_path: Path) -> None:
    states = qb.admit_fetch_manifest(
        _receipt(tmp_path, registration_pin="0" * 64), repo_root=tmp_path,
        frame_loader=lambda _path: pd.DataFrame({"x": [1]}),
    )
    assert set(states) == set(DATASETS)


def test_f33_validation_symbol_call_site_escapes_tripwire(tmp_path: Path) -> None:
    leak = tmp_path / "app/services/leak.py"
    leak.parent.mkdir(parents=True)
    leak.write_text(
        "from src.dynasty_genius.adapters.nflreadpy_qb_adapter "
        "import load_validation_weekly_stats\n"
        "RESULT = load_validation_weekly_stats([2025])\n"
    )
    qb.enforce_consumer_boundary(repo_root=tmp_path)


def test_runner_publishes_invalid_success_payload(tmp_path: Path) -> None:
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    report = qb.run_qb1_study(
        execute=lambda: {"run_status": "ok", "decision_supported": True},
        output_path=destination, registration_hash=PIN,
        generated_at="2026-08-14T16:00:00Z", repo_root=tmp_path,
    )
    assert report["decision_supported"] is True
    assert json.loads(destination.read_text())["decision_supported"] is True


def test_runner_non_named_failure_emits_nothing(tmp_path: Path) -> None:
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"

    def explode():
        raise ValueError("unexpected parse failure")

    with pytest.raises(ValueError):
        qb.run_qb1_study(
            execute=explode, output_path=destination, registration_hash=PIN,
            generated_at="2026-08-14T16:00:00Z", repo_root=tmp_path,
        )
    assert not destination.exists()


@pytest.mark.parametrize("overrides", [
    {"adjusted_p_ni": -1.0}, {"p_ni": 2.0}, {"folds": 5},
    {"pooled_delta": 0.08, "ci95": [-0.20, -0.10]},
    {"pooled_delta": -0.08, "ci95": [0.10, 0.20]},
    {"ci95": [0.20, 0.10]},
])
def test_h5_invalid_or_incoherent_evidence_is_labeled(overrides: dict) -> None:
    payload = {
        "lane": "h5", "folds": 4, "pooled_delta": 0.01,
        "ci95": [-0.02, 0.04], "one_sided_lower_95": -0.04,
        "p_ni": 0.04, "adjusted_p_ni": 0.08, **overrides,
    }
    assert qb.evaluate_power_and_status(payload)["support_status"] in {
        "market_noninferior", "market_superior", "model_superior", "inconclusive"
    }


def test_duplicate_case_row_passes_exact_panel_gate() -> None:
    ids = ["daniels_2025", "nix_2025", "mayfield_2025", "richardson_2025",
           "maye_2025", "allen_2019_twin", "richardson_2024_twin"]
    rows = [{"id": item,
             "scope_note": "second-season" if item in {"daniels_2025", "nix_2025"} else "case",
             "decision_supported": False} for item in ids]
    rows.append(dict(rows[-1]))
    assert len(qb.require_case_panel(rows)) == 8


def test_impossible_join_coverage_is_admitted() -> None:
    assert qb.validate_join_coverage(101, 100, registration=_registration())["coverage"] == 1.01
