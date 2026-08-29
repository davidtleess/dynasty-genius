"""DG-086 wiring contract: the ONE computer of dvs_pct feeds the assembled ACTIVE_B population.

The defect: universe_pvo_batch.py fills valuation.xvar_percentile_position from
pvo.get("dvs_pct"), but scripts/compute_dvs_pct_batch.compute_dvs_pct_batch — the one
authority for the within-position percentile, the only place that stamps dvs_pct_as_of —
had ZERO callers, so the field was null for every scored row ever published (measured
2026-08-28: 0 of 468). David's ruling 2026-08-29: wire the existing calculator; no twin
implementation.

Determinism guard (second test): dvs_pct_as_of is a wall-clock stamp. The forward-capture
vintage (semantic_output_hash) excludes only TOP-LEVEL volatile row keys
(model_forward_capture_driver._semantic_projection), so the stamp must stay on the
in-memory PVO objects and NEVER enter a published row — otherwise every same-day rerun
would present a fresh vintage and the store's immutability guard would refuse all day.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.dynasty_genius.models.player_value_object import PlayerValueObject
from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch

producer = importlib.import_module("scripts.build_universe_pvo_batch")

# gsis -> (position, dynasty_value_score, model_grade). Two positions so the test can
# tell a within-position percentile from an overall one: w1's 80.0 ranks below q1's 90.0
# overall but is the TOP wide receiver, so within-position it must read 100.0.
_POPULATION = {
    "q1": ("QB", 90.0, "ACTIVE_B"),
    "q2": ("QB", 70.0, "ACTIVE_B"),
    "q3": ("QB", 50.0, "ACTIVE_B"),
    "w1": ("WR", 80.0, "ACTIVE_B"),
    "w2": ("WR", 40.0, "ACTIVE_B"),
    "qn": ("QB", None, "ACTIVE_B"),  # scored-population outsider: null DVS
    "pm": ("WR", 60.0, "PRE_MODEL"),  # not ACTIVE_B: never in the reference population
}


def _pvo(gsis: str, pos: str, dvs: float | None, grade: str) -> PlayerValueObject:
    return PlayerValueObject(
        player_id=gsis,
        full_name=f"Player {gsis}",
        position=pos,
        model_grade=grade,
        dynasty_value_score=dvs,
        signal_completeness=1.0,
    )


def test_active_pvo_assembly_routes_population_through_dvs_pct_computer(monkeypatch):
    """_active_pvos_from_engine_b must pass the WHOLE assembled population through
    compute_dvs_pct_batch before model_dump — the percentile is a population statistic,
    so per-row wiring cannot compute it and a missing call leaves every dvs_pct None."""
    pvos_by_gsis = {g: _pvo(g, *spec) for g, spec in _POPULATION.items()}
    ff = {
        g: {
            "name": f"Player {g}",
            "position": spec[0],
            "birthdate": None,
            "sleeper_id": f"s-{g}",
            "pfr_id": None,
        }
        for g, spec in _POPULATION.items()
    }
    monkeypatch.setattr(producer, "_load_ff_playerids", lambda: (ff, None))
    monkeypatch.setattr(producer, "_crosswalk_identifier", lambda entry, key: entry.get(key))
    stub_source = SimpleNamespace(
        path=Path("stub.csv"),
        metadata=lambda: {
            "feature_csv_path": "stub.csv",
            "feature_source_kind": "stub",
            "feature_csv_sha256": "0" * 64,
        },
    )
    monkeypatch.setattr(producer, "resolve_feature_source", lambda **_kw: stub_source)
    monkeypatch.setattr(producer, "_load_engine_b_feature_rows", lambda _path: {})
    monkeypatch.setattr(
        producer,
        "score_inference_partition",
        lambda **_kw: [
            {"player_id": g, "position": spec[0], "team": "KC"}
            for g, spec in _POPULATION.items()
        ],
    )
    monkeypatch.setattr(producer, "assemble_pvo", lambda identity, **_kw: pvos_by_gsis[identity.dg_id])

    dumps = producer._active_pvos_from_engine_b()

    by_id = {d["player_id"]: d for d in dumps}
    assert set(by_id) == set(_POPULATION)
    # Within-QB spread over the three scored QBs.
    assert by_id["q1"]["dvs_pct"] == pytest.approx(100.0)
    assert by_id["q2"]["dvs_pct"] == pytest.approx(50.0)
    assert by_id["q3"]["dvs_pct"] == pytest.approx(0.0)
    # Within-POSITION, not overall: the top WR is 100.0 despite trailing q1 overall.
    assert by_id["w1"]["dvs_pct"] == pytest.approx(100.0)
    assert by_id["w2"]["dvs_pct"] == pytest.approx(0.0)
    # Outside the reference population: honestly None, never fabricated.
    assert by_id["qn"]["dvs_pct"] is None
    assert by_id["pm"]["dvs_pct"] is None
    # The calculator, not a twin, ran: its as-of stamp rides the scored dumps only.
    for gsis in ("q1", "q2", "q3", "w1", "w2"):
        assert by_id[gsis]["dvs_pct_as_of"] is not None
    assert by_id["qn"]["dvs_pct_as_of"] is None
    assert by_id["pm"]["dvs_pct_as_of"] is None


def _keys_recursive(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys_recursive(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _keys_recursive(item)


def test_dvs_pct_as_of_never_reaches_the_published_artifact():
    """Pin the determinism boundary: the artifact carries the percentile VALUE
    (deterministic per population) but never the wall-clock as-of stamp."""
    active = {
        "sleeper_id": "202",
        "player_id": "00-0000202",
        "full_name": "Active One",
        "position": "RB",
        "model_grade": "ACTIVE_B",
        "dynasty_value_score": 72.0,
        "xvar": 8.5,
        "dvs_pct": 77.0,
        "dvs_pct_as_of": "2026-08-29T13:45:00+00:00",
        "dvs_engine": "B",
        "decision_supported": False,
        "market_overlay": None,
    }
    snapshot = {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-08-29T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "202",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Active One", "position": "RB", "team": "KC"},
                "league_context": {"rostered": True, "roster_id": 2},
            }
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }

    batch = build_universe_pvo_batch(
        snapshot, active_pvos=[active], captured_at="2026-08-29T00:00:01+00:00"
    )

    row = next(r for r in batch["players"] if r["sleeper_player_id"] == "202")
    assert row["valuation"]["xvar_percentile_position"] == 77.0
    assert "dvs_pct_as_of" not in set(_keys_recursive(batch))


def _active(sleeper_id: str, dvs: float | None, dvs_pct: float | None) -> dict:
    return {
        "sleeper_id": sleeper_id,
        "player_id": f"gsis-{sleeper_id}",
        "full_name": f"Active {sleeper_id}",
        "position": "RB",
        "model_grade": "ACTIVE_B",
        "dynasty_value_score": dvs,
        "xvar": 8.5 if dvs is not None else None,
        "dvs_pct": dvs_pct,
        "dvs_engine": "B",
        "decision_supported": False,
        "market_overlay": None,
    }


def _snapshot_rows(ids: list[str]) -> dict:
    return {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-08-29T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": sid,
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": f"Active {sid}", "position": "RB", "team": "KC"},
                "league_context": {"rostered": True, "roster_id": int(sid)},
            }
            for sid in ids
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }


def test_coverage_counts_the_position_percentile_population():
    """DG-086 observability: the 2026-06-24→08-28 all-NULL defect went unnoticed
    because nothing counted this field. The coverage artifact now reports the
    populated count against the spec-5.14 reference population (ACTIVE_B with
    non-null DVS) and an exit criterion that goes false the day either a
    reference row misses its percentile or a non-reference row gains one."""
    actives = [
        _active("1", 72.0, 100.0),
        _active("2", 60.0, 0.0),  # 0.0 is a real percentile — must count as populated
        _active("3", None, None),  # ACTIVE_B but unscored: outside the reference population
    ]

    batch = build_universe_pvo_batch(
        _snapshot_rows(["1", "2", "3"]),
        active_pvos=actives,
        captured_at="2026-08-29T00:00:01+00:00",
    )

    coverage = batch["coverage"]
    assert coverage["xvar_percentile_position_populated_count"] == 2
    assert coverage["xvar_percentile_position_reference_count"] == 2
    assert (
        coverage["dg086_exit_criteria"]["position_percentile_covers_reference_population"]
        is True
    )


def test_coverage_exit_criterion_fails_when_a_reference_row_misses_its_percentile():
    actives = [
        _active("1", 72.0, 100.0),
        _active("2", 60.0, None),  # scored ACTIVE_B with NO percentile — the regression state
    ]

    batch = build_universe_pvo_batch(
        _snapshot_rows(["1", "2"]),
        active_pvos=actives,
        captured_at="2026-08-29T00:00:01+00:00",
    )

    coverage = batch["coverage"]
    assert coverage["xvar_percentile_position_populated_count"] == 1
    assert coverage["xvar_percentile_position_reference_count"] == 2
    assert (
        coverage["dg086_exit_criteria"]["position_percentile_covers_reference_population"]
        is False
    )
