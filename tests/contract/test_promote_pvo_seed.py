"""F-seed-split T5a RED: David-gated runtime -> committed PVO seed promotion."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _write_pair(root: Path, *, player: str, prefix: str = "seed") -> tuple[Path, Path]:
    pvo = _write_json(
        root / f"{prefix}_pvo.json",
        {
            "schema_version": "universe_pvo_batch.v1",
            "players": [{"sleeper_player_id": player}],
        },
    )
    coverage = _write_json(
        root / f"{prefix}_coverage.json",
        {
            "schema_version": "universe_pvo_coverage.v1",
            "total_players": 1,
            "counts_by_engine_path": {"ENGINE_B": 1},
        },
    )
    return pvo, coverage


def _write_runtime_pair(
    runtime_dir: Path,
    *,
    player: str = "runtime-player",
    status: str = "ok",
    seed_staleness: dict | None = None,
) -> tuple[Path, Path]:
    pvo = _write_json(
        runtime_dir / "universe_pvo_runtime.json",
        {
            "schema_version": "universe_pvo_batch.v1",
            "players": [{"sleeper_player_id": player}],
        },
    )
    coverage = _write_json(
        runtime_dir / "universe_pvo_coverage_runtime.json",
        {
            "schema_version": "universe_pvo_coverage.v1",
            "total_players": 1,
            "counts_by_engine_path": {"ENGINE_B": 1},
        },
    )
    _write_json(
        runtime_dir / "universe_pvo_runtime.ready.json",
        {
            "status": status,
            "pvo_sha256": _sha(pvo),
            "coverage_sha256": _sha(coverage),
            "source_as_of": "2026-06-27T13:30:00+00:00",
            "seed_staleness": seed_staleness
            if seed_staleness is not None
            else {
                "decision_supported": False,
                "promote_recommended": True,
                "count_players_drifted_gt_5pct": 22,
                "count_model_supported_players_drifted_gt_5pct": 22,
                "coverage_count_deltas": {"ENGINE_B": 0},
                "mean_abs_value_delta": 6.0,
                "p95_abs_value_delta": 6.0,
                "seed_as_of": "2026-06-24T12:00:00+00:00",
                "seed_age_days": 3.0,
            },
            "decision_supported": False,
        },
    )
    return pvo, coverage


def _load_promoter():
    return importlib.import_module("scripts.promote_pvo_seed")


def test_promote_pvo_seed_refuses_when_no_runtime_is_published(tmp_path: Path) -> None:
    promoter = _load_promoter()
    seed_pvo, seed_coverage = _write_pair(tmp_path / "seed", player="seed-player")
    before = (seed_pvo.read_bytes(), seed_coverage.read_bytes())

    report = promoter.promote_pvo_seed(
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=tmp_path / "valuation_runtime",
        confirm=True,
    )

    assert report["status"] == "refused"
    assert report["reason"] == "no_runtime_published"
    assert report["decision_supported"] is False
    assert seed_pvo.read_bytes() == before[0]
    assert seed_coverage.read_bytes() == before[1]


def test_promote_pvo_seed_refuses_unverified_runtime_without_writing(
    tmp_path: Path,
) -> None:
    promoter = _load_promoter()
    seed_pvo, seed_coverage = _write_pair(tmp_path / "seed", player="seed-player")
    runtime_pvo, _runtime_coverage = _write_runtime_pair(
        tmp_path / "valuation_runtime", player="runtime-player", status="blocked"
    )
    before = (seed_pvo.read_bytes(), seed_coverage.read_bytes())

    report = promoter.promote_pvo_seed(
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=runtime_pvo.parent,
        confirm=True,
    )

    assert report["status"] == "refused"
    assert report["reason"] == "runtime_not_ready"
    assert "aborted_reason" in report
    assert report["decision_supported"] is False
    assert seed_pvo.read_bytes() == before[0]
    assert seed_coverage.read_bytes() == before[1]


def test_promote_pvo_seed_dry_run_shows_drift_and_never_writes(
    tmp_path: Path,
) -> None:
    promoter = _load_promoter()
    seed_pvo, seed_coverage = _write_pair(tmp_path / "seed", player="seed-player")
    runtime_pvo, runtime_coverage = _write_runtime_pair(
        tmp_path / "valuation_runtime", player="runtime-player"
    )
    before = (seed_pvo.read_bytes(), seed_coverage.read_bytes())

    report = promoter.promote_pvo_seed(
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=runtime_pvo.parent,
        confirm=False,
    )

    assert report["status"] == "dry_run"
    assert report["would_promote"] is True
    assert report["decision_supported"] is False
    assert report["runtime"]["pvo_sha256"] == _sha(runtime_pvo)
    assert report["runtime"]["coverage_sha256"] == _sha(runtime_coverage)
    assert report["seed_staleness"]["decision_supported"] is False
    assert report["seed_staleness"]["promote_recommended"] is True
    assert seed_pvo.read_bytes() == before[0]
    assert seed_coverage.read_bytes() == before[1]


def test_promote_pvo_seed_confirm_copies_runtime_pair_and_never_invokes_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    promoter = _load_promoter()
    seed_pvo, seed_coverage = _write_pair(tmp_path / "seed", player="seed-player")
    runtime_pvo, runtime_coverage = _write_runtime_pair(
        tmp_path / "valuation_runtime", player="runtime-player"
    )

    def forbid_git(*_args, **_kwargs):
        raise AssertionError("promote_pvo_seed must never invoke git")

    monkeypatch.setattr(promoter.subprocess, "run", forbid_git, raising=False)

    report = promoter.promote_pvo_seed(
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=runtime_pvo.parent,
        confirm=True,
    )

    assert report["status"] == "promoted"
    assert report["decision_supported"] is False
    assert report["git_commit_performed"] is False
    assert report["manual_commit_required"] is True
    assert seed_pvo.read_bytes() == runtime_pvo.read_bytes()
    assert seed_coverage.read_bytes() == runtime_coverage.read_bytes()
    # Runtime remains in place for the next scheduled refresh to overwrite.
    assert runtime_pvo.exists()
    assert runtime_coverage.exists()


def test_promote_pvo_seed_restores_prior_seed_pair_on_mid_write_failure(
    tmp_path: Path,
) -> None:
    promoter = _load_promoter()
    seed_pvo, seed_coverage = _write_pair(tmp_path / "seed", player="seed-player")
    runtime_pvo, _runtime_coverage = _write_runtime_pair(
        tmp_path / "valuation_runtime", player="runtime-player"
    )
    prior = {seed_pvo: seed_pvo.read_bytes(), seed_coverage: seed_coverage.read_bytes()}
    calls: list[Path] = []

    def fail_on_second_replace(src: Path | str, dst: Path | str) -> None:
        dst_path = Path(dst)
        calls.append(dst_path)
        if dst_path == seed_coverage:
            raise OSError("simulated coverage promote failure")
        Path(dst).write_bytes(Path(src).read_bytes())
        Path(src).unlink()

    report = promoter.promote_pvo_seed(
        seed_pvo_path=seed_pvo,
        seed_coverage_path=seed_coverage,
        runtime_dir=runtime_pvo.parent,
        confirm=True,
        replace_fn=fail_on_second_replace,
    )

    assert report["status"] == "aborted"
    assert report["aborted_stage"] == "promote"
    assert report["restored_from_backup"] is True
    assert report["decision_supported"] is False
    assert seed_pvo.read_bytes() == prior[seed_pvo]
    assert seed_coverage.read_bytes() == prior[seed_coverage]
    assert seed_pvo in calls
    assert seed_coverage in calls


def test_promote_pvo_seed_cli_confirm_flag_is_the_only_write_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    promoter = _load_promoter()
    calls: list[bool] = []

    def fake_promote_pvo_seed(**kwargs):
        calls.append(kwargs["confirm"])
        return {"status": "dry_run" if not kwargs["confirm"] else "promoted"}

    monkeypatch.setattr(promoter, "promote_pvo_seed", fake_promote_pvo_seed)
    argv = [
        "--seed-pvo-path",
        str(tmp_path / "seed_pvo.json"),
        "--seed-coverage-path",
        str(tmp_path / "seed_coverage.json"),
        "--runtime-dir",
        str(tmp_path / "runtime"),
    ]

    assert promoter.main(argv) == 0
    assert calls == [False]
    assert '"status": "dry_run"' in capsys.readouterr().out

    assert promoter.main([*argv, "--confirm"]) == 0
    assert calls == [False, True]
    assert '"status": "promoted"' in capsys.readouterr().out
