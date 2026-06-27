from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _write_pvo(path: Path, player_id: str) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "universe_pvo_batch.v1",
            "captured_at": "2026-06-27T13:00:00+00:00",
            "players": [
                {
                    "sleeper_player_id": player_id,
                    "valuation": {
                        "engine_path": "ENGINE_B",
                        "dynasty_value_score": 42.0,
                        "decision_supported": False,
                    },
                }
            ],
        },
    )


def _write_coverage(path: Path, engine_b_count: int) -> Path:
    return _write_json(
        path,
        {
            "total_players": 1,
            "counts_by_engine_path": {"ENGINE_B": engine_b_count},
            "decision_supported_true_count": 0,
        },
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_ready_marker(
    runtime_dir: Path,
    *,
    pvo_path: Path,
    coverage_path: Path,
    status: str = "ok",
    pvo_sha256: str | None = None,
    coverage_sha256: str | None = None,
    seed_staleness: dict | None = None,
) -> dict:
    payload = {
        "status": status,
        "pvo_sha256": pvo_sha256 or _sha(pvo_path),
        "coverage_sha256": coverage_sha256 or _sha(coverage_path),
        "source_as_of": "2026-06-27T13:00:00+00:00",
        "seed_staleness": seed_staleness
        or {
            "promote_recommended": False,
            "count_players_drifted_gt_5pct": 0,
            "count_model_supported_players_drifted_gt_5pct": 0,
        },
        "decision_supported": False,
    }
    (runtime_dir / "universe_pvo_runtime.ready.json").write_text(
        json.dumps(payload, sort_keys=True)
    )
    return payload


def _seed_paths(tmp_path: Path) -> tuple[Path, Path]:
    seed_dir = tmp_path / "seed"
    pvo = _write_pvo(seed_dir / "universe_pvo_latest.json", "seed-player")
    coverage = _write_coverage(seed_dir / "universe_pvo_coverage_latest.json", 1)
    return pvo, coverage


def _runtime_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "valuation_runtime"
    pvo = _write_pvo(runtime_dir / "universe_pvo_runtime.json", "runtime-player")
    coverage = _write_coverage(runtime_dir / "universe_pvo_coverage_runtime.json", 2)
    return runtime_dir, pvo, coverage


def test_resolve_pvo_source_falls_back_to_seed_only_when_runtime_absent(
    tmp_path: Path,
) -> None:
    pvo_source = importlib.import_module("src.dynasty_genius.pvo_source")
    seed_pvo, seed_coverage = _seed_paths(tmp_path)

    resolved = pvo_source.resolve_pvo_source(
        seed_paths={"pvo": seed_pvo, "coverage": seed_coverage},
        runtime_dir=tmp_path / "valuation_runtime",
    )

    assert resolved.source_kind == "seed"
    assert resolved.pvo_path == seed_pvo
    assert resolved.coverage_path == seed_coverage
    assert resolved.pvo_sha256 == _sha(seed_pvo)
    assert resolved.coverage_sha256 == _sha(seed_coverage)
    assert resolved.source_as_of is None
    assert resolved.ready is True
    assert resolved.seed_staleness is None
    assert resolved.metadata() == {
        "pvo_source_kind": "seed",
        "pvo_sha256": _sha(seed_pvo),
        "pvo_path": str(seed_pvo),
        "coverage_sha256": _sha(seed_coverage),
        "coverage_path": str(seed_coverage),
        "source_as_of": None,
        "seed_staleness": None,
        "decision_supported": False,
    }


def test_resolve_pvo_source_prefers_verified_runtime_pair_and_stamps_metadata(
    tmp_path: Path,
) -> None:
    pvo_source = importlib.import_module("src.dynasty_genius.pvo_source")
    seed_pvo, seed_coverage = _seed_paths(tmp_path)
    runtime_dir, runtime_pvo, runtime_coverage = _runtime_pair(tmp_path)
    seed_staleness = {
        "promote_recommended": True,
        "count_players_drifted_gt_5pct": 21,
        "count_model_supported_players_drifted_gt_5pct": 21,
    }
    ready = _write_ready_marker(
        runtime_dir,
        pvo_path=runtime_pvo,
        coverage_path=runtime_coverage,
        seed_staleness=seed_staleness,
    )

    resolved = pvo_source.resolve_pvo_source(
        seed_paths={"pvo": seed_pvo, "coverage": seed_coverage},
        runtime_dir=runtime_dir,
    )

    assert resolved.source_kind == "runtime"
    assert resolved.pvo_path == runtime_pvo
    assert resolved.coverage_path == runtime_coverage
    assert resolved.pvo_sha256 == _sha(runtime_pvo)
    assert resolved.coverage_sha256 == _sha(runtime_coverage)
    assert resolved.source_as_of == ready["source_as_of"]
    assert resolved.ready is True
    assert resolved.seed_staleness == seed_staleness

    metadata = resolved.metadata()
    assert metadata["pvo_source_kind"] == "runtime"
    assert metadata["pvo_sha256"] == _sha(runtime_pvo)
    assert metadata["coverage_sha256"] == _sha(runtime_coverage)
    assert metadata["source_as_of"] == ready["source_as_of"]
    assert metadata["seed_staleness"] == seed_staleness
    assert metadata["decision_supported"] is False


@pytest.mark.parametrize(
    "case",
    [
        "missing_marker",
        "blocked_marker",
        "pvo_hash_mismatch",
        "coverage_hash_mismatch",
        "missing_pvo",
        "missing_coverage",
    ],
)
def test_resolve_pvo_source_fails_closed_when_runtime_present_but_unverified(
    tmp_path: Path,
    case: str,
) -> None:
    pvo_source = importlib.import_module("src.dynasty_genius.pvo_source")
    seed_pvo, seed_coverage = _seed_paths(tmp_path)
    runtime_dir, runtime_pvo, runtime_coverage = _runtime_pair(tmp_path)

    if case == "missing_pvo":
        runtime_pvo.unlink()
    elif case == "missing_coverage":
        runtime_coverage.unlink()

    if case != "missing_marker":
        _write_ready_marker(
            runtime_dir,
            pvo_path=runtime_pvo if runtime_pvo.exists() else seed_pvo,
            coverage_path=runtime_coverage if runtime_coverage.exists() else seed_coverage,
            status="blocked" if case == "blocked_marker" else "ok",
            pvo_sha256="not-the-pvo-hash" if case == "pvo_hash_mismatch" else None,
            coverage_sha256=(
                "not-the-coverage-hash" if case == "coverage_hash_mismatch" else None
            ),
        )

    with pytest.raises(pvo_source.PvoSourceNotReadyError):
        pvo_source.resolve_pvo_source(
            seed_paths={"pvo": seed_pvo, "coverage": seed_coverage},
            runtime_dir=runtime_dir,
        )


def test_resolve_pvo_source_passes_through_seed_staleness_without_diffing_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The resolver may read the ready marker, but it must not parse/diff PVO JSON."""
    pvo_source = importlib.import_module("src.dynasty_genius.pvo_source")
    seed_pvo, seed_coverage = _seed_paths(tmp_path)
    runtime_dir, runtime_pvo, runtime_coverage = _runtime_pair(tmp_path)
    seed_staleness = {
        "promote_recommended": True,
        "count_players_drifted_gt_5pct": 22,
        "count_model_supported_players_drifted_gt_5pct": 22,
        "mean_abs_value_delta": 0.4,
        "p95_abs_value_delta": 1.1,
    }
    _write_ready_marker(
        runtime_dir,
        pvo_path=runtime_pvo,
        coverage_path=runtime_coverage,
        seed_staleness=seed_staleness,
    )

    original_loads = json.loads

    def guarded_loads(payload, *args, **kwargs):
        text = payload.decode() if isinstance(payload, bytes) else str(payload)
        assert "seed_staleness" in text, "resolver parsed artifact JSON instead of marker"
        return original_loads(payload, *args, **kwargs)

    monkeypatch.setattr(pvo_source.json, "loads", guarded_loads)

    resolved = pvo_source.resolve_pvo_source(
        seed_paths={"pvo": seed_pvo, "coverage": seed_coverage},
        runtime_dir=runtime_dir,
    )

    assert resolved.seed_staleness == seed_staleness
    assert resolved.metadata()["seed_staleness"] == seed_staleness
