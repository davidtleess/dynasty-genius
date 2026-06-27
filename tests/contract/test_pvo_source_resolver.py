from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PVO_CONSUMER_FILES = {
    "app/api/routes/players.py",
    "app/api/routes/trade.py",
    "app/api/routes/trade_market.py",
    "app/services/roster_auditor.py",
    "scripts/build_roster_cut_report.py",
    "scripts/build_team_value_matrix.py",
    "scripts/build_universe_market_divergence.py",
    "scripts/run_model_forward_capture.py",
}

PVO_DIRECT_REFERENCE_ALLOWLIST = {
    "src/dynasty_genius/pvo_source.py": (
        "resolver owns the seed/runtime contract and runtime artifact names"
    ),
    "scripts/run_pvo_refresh.py": (
        "publisher/orchestrator reads the committed seed as drift baseline and writes runtime"
    ),
    "scripts/validate_surface3_regen_integrity.py": (
        "intentional seed-pinned pre/post regeneration integrity audit"
    ),
    "scripts/run_league_intelligence_refresh.py": (
        "legacy David-gated seed-writing orchestrator; consumer migration is out of scope"
    ),
    "scripts/promote_pvo_seed.py": (
        "David-gated tool that copies the verified runtime to the committed seed paths"
    ),
}

_PVO_SEED_NAME = "universe_pvo_latest.json"
_COVERAGE_SEED_NAME = "universe_pvo_coverage_latest.json"
_PVO_RUNTIME_NAME = "universe_pvo_runtime.json"
_COVERAGE_RUNTIME_NAME = "universe_pvo_coverage_runtime.json"
_READY_MARKER_NAME = "universe_pvo_runtime.ready.json"


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


def _repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


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
    pvo = _write_pvo(runtime_dir / _PVO_RUNTIME_NAME, "runtime-player")
    coverage = _write_coverage(runtime_dir / _COVERAGE_RUNTIME_NAME, 2)
    return runtime_dir, pvo, coverage


def _write_api_pvo(path: Path, sleeper_id: str, *, score: float = 42.0) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "universe_pvo_batch.v1",
            "captured_at": "2026-06-27T13:00:00+00:00",
            "players": [
                {
                    "sleeper_player_id": sleeper_id,
                    "dg_player_id": f"dg-{sleeper_id}",
                    "identity_ids": {"sleeper_id": sleeper_id},
                    "player": {
                        "full_name": f"Player {sleeper_id}",
                        "position": "RB",
                        "team": "NYJ",
                        "age": 22.0,
                    },
                    "league_context": {
                        "rostered": True,
                        "roster_id": 1,
                        "in_current_draft": True,
                    },
                    "lineage": {
                        "governance_version": "1.0.0",
                        "sleeper_snapshot_hash": "snapshot-hash",
                    },
                    "valuation": {
                        "engine_path": "ENGINE_A",
                        "valuation_status": "MODEL_SUPPORTED",
                        "dynasty_value_score": score,
                        "xvar": score / 10,
                        "model_grade": "PROSPECT_C",
                        "feature_completeness": 0.5,
                        "decision_supported": False,
                    },
                }
            ],
        },
    )


def _write_runtime_api_pair(
    runtime_dir: Path,
    sleeper_id: str,
    *,
    score: float = 99.0,
) -> tuple[Path, Path]:
    pvo = _write_api_pvo(runtime_dir / _PVO_RUNTIME_NAME, sleeper_id, score=score)
    coverage = _write_coverage(runtime_dir / _COVERAGE_RUNTIME_NAME, 1)
    _write_ready_marker(runtime_dir, pvo_path=pvo, coverage_path=coverage)
    return pvo, coverage


def _pvo_fixture_root(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    seed_dir = root / "app" / "data" / "valuation"
    runtime_dir = root / "app" / "data" / "valuation_runtime"
    seed_pvo = _write_api_pvo(seed_dir / _PVO_SEED_NAME, "seed-player", score=11.0)
    seed_coverage = _write_coverage(seed_dir / _COVERAGE_SEED_NAME, 1)
    return root, seed_pvo, seed_coverage, runtime_dir


def _configure_route_pvo_paths(monkeypatch: pytest.MonkeyPatch, module, root: Path) -> None:
    seed_dir = root / "app" / "data" / "valuation"
    monkeypatch.setattr(module, "_ROOT", root, raising=False)
    monkeypatch.setattr(module, "ROOT", root, raising=False)
    monkeypatch.setattr(module, "PVO_SEED_PATH", seed_dir / _PVO_SEED_NAME, raising=False)
    monkeypatch.setattr(
        module,
        "PVO_SEED_COVERAGE_PATH",
        seed_dir / _COVERAGE_SEED_NAME,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "PVO_RUNTIME_DIR",
        root / "app" / "data" / "valuation_runtime",
        raising=False,
    )
    # Current code still uses these direct constants; GREEN should stop relying on them.
    monkeypatch.setattr(
        module, "UNIVERSE_PVO_PATH", seed_dir / _PVO_SEED_NAME, raising=False
    )
    monkeypatch.setattr(
        module,
        "UNIVERSE_PVO_LATEST_PATH",
        seed_dir / _PVO_SEED_NAME,
        raising=False,
    )


def _write_sleeper_snapshot(root: Path) -> Path:
    return _write_json(
        root / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json",
        {"rosters": [], "players": {}, "david_roster_id": 1},
    )


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


def test_pvo_producers_do_not_self_resolve_runtime_outputs() -> None:
    """T4 guard: PVO producers write artifacts; they must never resolve their own output."""
    for relative_path in (
        "scripts/build_universe_pvo_batch.py",
        "src/dynasty_genius/universe_pvo_batch.py",
    ):
        text = _repo_text(relative_path)
        assert "resolve_pvo_source" not in text
        assert "PvoSourceNotReadyError" not in text


def test_pvo_direct_reference_allowlist_has_explicit_rationales() -> None:
    """T4 map: every non-consumer direct seed/runtime reference needs a named rationale."""
    required_allowlist = {
        "src/dynasty_genius/pvo_source.py",
        "scripts/run_pvo_refresh.py",
        "scripts/validate_surface3_regen_integrity.py",
        "scripts/run_league_intelligence_refresh.py",
        "scripts/promote_pvo_seed.py",
    }
    assert set(PVO_DIRECT_REFERENCE_ALLOWLIST) == required_allowlist
    for rationale in PVO_DIRECT_REFERENCE_ALLOWLIST.values():
        assert len(rationale.split()) >= 6


def test_t4_consumers_route_pvo_reads_through_resolver_not_committed_seed_paths() -> None:
    """T4 RED: consumers must resolve the PVO pair instead of reading the seed directly."""
    forbidden_markers = (
        "app/data/valuation/universe_pvo_latest.json",
        "app/data/valuation/universe_pvo_coverage_latest.json",
        "UNIVERSE_PVO_PATH",
        "UNIVERSE_PVO_LATEST_PATH",
        "PVO_PATH",
    )
    offenders: dict[str, list[str]] = {}
    for relative_path in sorted(PVO_CONSUMER_FILES):
        text = _repo_text(relative_path)
        missing_resolver = "resolve_pvo_source" not in text
        direct_markers = [marker for marker in forbidden_markers if marker in text]
        if missing_resolver or direct_markers:
            offenders[relative_path] = [
                *(["missing resolve_pvo_source"] if missing_resolver else []),
                *direct_markers,
            ]

    assert offenders == {}


def test_players_route_loads_verified_runtime_and_fails_closed_on_bad_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    players_route = importlib.import_module("app.api.routes.players")
    root, _seed_pvo, _seed_coverage, runtime_dir = _pvo_fixture_root(tmp_path)
    _write_runtime_api_pair(runtime_dir, "runtime-player", score=99.0)
    _configure_route_pvo_paths(monkeypatch, players_route, root)
    players_route._load_player_detail_artifacts.cache_clear()

    runtime_payload = players_route._load_player_detail_artifacts()

    assert runtime_payload["players"][0]["sleeper_player_id"] == "runtime-player"

    (runtime_dir / _READY_MARKER_NAME).write_text(
        json.dumps({"status": "blocked"}, sort_keys=True)
    )
    players_route._load_player_detail_artifacts.cache_clear()
    with pytest.raises(Exception) as exc_info:
        players_route._load_player_detail_artifacts()
    assert getattr(exc_info.value, "status_code", None) == 503


@pytest.mark.parametrize(
    "module_name",
    ["app.api.routes.trade", "app.api.routes.trade_market"],
)
def test_trade_routes_load_verified_runtime_and_fail_closed_on_bad_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    route_module = importlib.import_module(module_name)
    root, _seed_pvo, _seed_coverage, runtime_dir = _pvo_fixture_root(tmp_path)
    _write_sleeper_snapshot(root)
    _write_runtime_api_pair(runtime_dir, "runtime-player", score=99.0)
    _configure_route_pvo_paths(monkeypatch, route_module, root)

    universe_pvo, _snapshot = route_module._load_reconcile_artifacts()

    assert universe_pvo["players"][0]["sleeper_player_id"] == "runtime-player"

    (runtime_dir / _READY_MARKER_NAME).write_text(
        json.dumps({"status": "blocked"}, sort_keys=True)
    )
    with pytest.raises(Exception) as exc_info:
        route_module._load_reconcile_artifacts()
    assert getattr(exc_info.value, "status_code", None) == 503


def test_roster_auditor_loads_verified_runtime_and_falls_back_to_seed_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roster_auditor = importlib.import_module("app.services.roster_auditor")
    root, _seed_pvo, _seed_coverage, runtime_dir = _pvo_fixture_root(tmp_path)
    _write_runtime_api_pair(runtime_dir, "runtime-player", score=99.0)
    _configure_route_pvo_paths(monkeypatch, roster_auditor, root)

    # T4d: the loader now returns (rows, resolved-provenance) — unpack the rows map.
    runtime_rows, _runtime_provenance = roster_auditor._load_rostered_engine_a_universe_pvos()

    assert set(runtime_rows) == {"runtime-player"}

    for path in runtime_dir.iterdir():
        path.unlink()
    seed_rows, _seed_provenance = roster_auditor._load_rostered_engine_a_universe_pvos()

    assert set(seed_rows) == {"seed-player"}


def test_what_changed_model_pvo_staleness_discloses_source_but_silences_quiet_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T4d: always disclose PVO provenance; do not nag on quiet seed drift."""
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    models = importlib.import_module("app.api.routes.league_what_changed_models")

    class Resolved:
        def metadata(self) -> dict:
            return {
                "decision_supported": False,
                "pvo_source_kind": "runtime",
                "pvo_sha256": "runtime-pvo-sha",
                "coverage_sha256": "runtime-coverage-sha",
                "source_as_of": "2026-06-27T13:30:00+00:00",
                "pvo_path": "app/data/valuation_runtime/universe_pvo_runtime.json",
                "coverage_path": (
                    "app/data/valuation_runtime/universe_pvo_coverage_runtime.json"
                ),
                "seed_staleness": {
                    "decision_supported": False,
                    "promote_recommended": False,
                    "count_players_drifted_gt_5pct": 1,
                    "count_model_supported_players_drifted_gt_5pct": 0,
                    "mean_abs_value_delta": 0.02,
                    "p95_abs_value_delta": 0.05,
                    "coverage_count_deltas": {"ENGINE_B": 0, "PRE_MODEL": 0},
                    "seed_as_of": "2026-06-24T12:00:00+00:00",
                    "seed_age_days": 3.0,
                },
            }

    monkeypatch.setattr(
        report, "resolve_pvo_source", lambda **_kwargs: Resolved(), raising=False
    )

    staleness = report._model_pvo_staleness()

    assert staleness == {
        "decision_supported": False,
        "pvo_source_kind": "runtime",
        "pvo_sha256": "runtime-pvo-sha",
        "coverage_sha256": "runtime-coverage-sha",
        "source_as_of": "2026-06-27T13:30:00+00:00",
        "pvo_path": "app/data/valuation_runtime/universe_pvo_runtime.json",
        "coverage_path": "app/data/valuation_runtime/universe_pvo_coverage_runtime.json",
        "seed_staleness": None,
    }
    model = models.WhatChangedModelSection.model_validate(
        {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "pvo_staleness": staleness,
        }
    )
    assert model.pvo_staleness is not None
    assert model.pvo_staleness.decision_supported is False
    assert model.pvo_staleness.seed_staleness is None


def test_what_changed_model_pvo_staleness_surfaces_promote_recommended_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T4d: the passive staleness line appears only on the §3.6 promotion tripwire."""
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    models = importlib.import_module("app.api.routes.league_what_changed_models")
    seed_staleness = {
        "decision_supported": False,
        "promote_recommended": True,
        "count_players_drifted_gt_5pct": 22,
        "count_model_supported_players_drifted_gt_5pct": 22,
        "mean_abs_value_delta": 6.0,
        "p95_abs_value_delta": 6.0,
        "coverage_count_deltas": {"ENGINE_B": 0, "PRE_MODEL": 0},
        "seed_as_of": "2026-06-24T12:00:00+00:00",
        "seed_age_days": 3.0,
    }

    class Resolved:
        def metadata(self) -> dict:
            return {
                "decision_supported": False,
                "pvo_source_kind": "runtime",
                "pvo_sha256": "runtime-pvo-sha",
                "coverage_sha256": "runtime-coverage-sha",
                "source_as_of": "2026-06-27T13:30:00+00:00",
                "pvo_path": "app/data/valuation_runtime/universe_pvo_runtime.json",
                "coverage_path": (
                    "app/data/valuation_runtime/universe_pvo_coverage_runtime.json"
                ),
                "seed_staleness": seed_staleness,
            }

    monkeypatch.setattr(
        report, "resolve_pvo_source", lambda **_kwargs: Resolved(), raising=False
    )

    staleness = report._model_pvo_staleness()

    assert staleness["seed_staleness"] == seed_staleness
    model = models.WhatChangedModelSection.model_validate(
        {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "pvo_staleness": staleness,
        }
    )
    assert model.pvo_staleness is not None
    assert model.pvo_staleness.seed_staleness is not None
    assert model.pvo_staleness.seed_staleness.promote_recommended is True
    assert model.pvo_staleness.seed_staleness.mean_abs_value_delta == 6.0
    assert model.pvo_staleness.seed_staleness.p95_abs_value_delta == 6.0


def test_what_changed_model_pvo_staleness_accepts_real_marker_shape_in_public_dto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5c-D1: real ready-marker seed_staleness must validate when promoted."""
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    models = importlib.import_module("app.api.routes.league_what_changed_models")
    raw_real_seed_staleness = {
        "decision_supported": False,
        "promote_recommended": True,
        "recommendation_reasons": [
            "count_model_supported_players_drifted_gt_5pct>20"
        ],
        "baseline_status": "compared",
        "count_players_drifted_gt_5pct": 22,
        "count_model_supported_players_drifted_gt_5pct": 22,
        "mean_abs_value_delta": 6.0,
        "p95_abs_value_delta": 6.0,
        "coverage_count_deltas": {"ENGINE_B": 0, "PRE_MODEL": 0},
        "seed_as_of": "2026-06-24T12:00:00+00:00",
        "seed_age_days": 3.0,
    }

    class Resolved:
        def metadata(self) -> dict:
            return {
                "decision_supported": False,
                "pvo_source_kind": "runtime",
                "pvo_sha256": "runtime-pvo-sha",
                "coverage_sha256": "runtime-coverage-sha",
                "source_as_of": "2026-06-27T13:30:00+00:00",
                "pvo_path": "app/data/valuation_runtime/universe_pvo_runtime.json",
                "coverage_path": (
                    "app/data/valuation_runtime/universe_pvo_coverage_runtime.json"
                ),
                "seed_staleness": raw_real_seed_staleness,
            }

    monkeypatch.setattr(
        report, "resolve_pvo_source", lambda **_kwargs: Resolved(), raising=False
    )

    staleness = report._model_pvo_staleness()

    assert staleness["seed_staleness"] == raw_real_seed_staleness
    model = models.WhatChangedModelSection.model_validate(
        {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "pvo_staleness": staleness,
        }
    )
    assert model.pvo_staleness is not None
    assert model.pvo_staleness.seed_staleness is not None
    assert model.pvo_staleness.seed_staleness.promote_recommended is True
    assert model.pvo_staleness.seed_staleness.baseline_status == "compared"
    assert model.pvo_staleness.seed_staleness.recommendation_reasons == [
        "count_model_supported_players_drifted_gt_5pct>20"
    ]


def test_what_changed_model_pvo_staleness_discloses_not_ready_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unverified runtime is a fault disclosure, not a quiet no-op."""
    report = importlib.import_module("src.dynasty_genius.what_changed.report")
    pvo_source = importlib.import_module("src.dynasty_genius.pvo_source")
    models = importlib.import_module("app.api.routes.league_what_changed_models")

    def not_ready(**_kwargs):
        raise pvo_source.PvoSourceNotReadyError("runtime marker hash mismatch")

    monkeypatch.setattr(report, "resolve_pvo_source", not_ready, raising=False)

    staleness = report._model_pvo_staleness()

    assert staleness == {
        "decision_supported": False,
        "pvo_source_status": "not_ready",
        "pvo_source_kind": None,
        "aborted_reason": "runtime marker hash mismatch",
    }
    model = models.WhatChangedModelSection.model_validate(
        {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "pvo_staleness": staleness,
        }
    )
    assert model.pvo_staleness is not None
    assert model.pvo_staleness.decision_supported is False


def test_what_changed_model_pvo_staleness_dto_rejects_fabricated_or_market_fields() -> None:
    """DTO is a closed, model-only provenance/staleness shape."""
    models = importlib.import_module("app.api.routes.league_what_changed_models")

    assert hasattr(models, "WhatChangedModelPvoStaleness")
    assert hasattr(models, "WhatChangedModelPvoSeedStaleness")

    with pytest.raises(Exception):
        models.WhatChangedModelPvoStaleness.model_validate(
            {
                "decision_supported": False,
                "pvo_source_kind": "invented",
                "pvo_sha256": "abc123",
            }
        )
    with pytest.raises(Exception):
        models.WhatChangedModelPvoStaleness.model_validate(
            {
                "decision_supported": False,
                "pvo_source_status": "maybe_ready",
                "pvo_source_kind": None,
                "aborted_reason": "marker mismatch",
            }
        )
    with pytest.raises(Exception):
        models.WhatChangedModelPvoSeedStaleness.model_validate(
            {
                "decision_supported": False,
                "promote_recommended": True,
                "count_players_drifted_gt_5pct": 22,
                "count_model_supported_players_drifted_gt_5pct": 22,
                "mean_abs_value_delta": 6.0,
                "p95_abs_value_delta": 6.0,
                "coverage_count_deltas": {"ENGINE_B": 0},
                "seed_as_of": "2026-06-24T12:00:00+00:00",
                "seed_age_days": 3.0,
                "market_overlay": {"must": "not validate"},
            }
        )


def test_what_changed_pvo_staleness_openapi_and_zod_snapshots_are_regenerated() -> None:
    """T4d changes the public What-Changed DTO, so generated schema artifacts must move."""
    openapi_snapshot = REPO_ROOT / "frontend" / "openapi.json"
    zod_client = REPO_ROOT / "frontend" / "src" / "lib" / "api" / "zod.gen.ts"

    openapi_text = openapi_snapshot.read_text(encoding="utf-8")
    zod_text = zod_client.read_text(encoding="utf-8")

    assert "WhatChangedModelPvoStaleness" in openapi_text
    assert "WhatChangedModelPvoSeedStaleness" in openapi_text
    assert "pvo_staleness" in openapi_text
    assert "zWhatChangedModelPvoStaleness" in zod_text
    assert "zWhatChangedModelPvoSeedStaleness" in zod_text
    assert "pvo_staleness" in zod_text
    assert "baseline_status" in openapi_text
    assert "recommendation_reasons" in openapi_text
    assert "baseline_status" in zod_text
    assert "recommendation_reasons" in zod_text
