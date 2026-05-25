from __future__ import annotations

import copy

import pytest


def _row(
    sleeper_id: str,
    position: str,
    xvar: float | None,
    *,
    engine_path: str = "ENGINE_B",
    valuation_status: str = "MODEL_SUPPORTED",
    identity_status: str = "resolved",
) -> dict:
    return {
        "schema_version": "universe_pvo_batch.v1",
        "sleeper_player_id": sleeper_id,
        "identity_status": identity_status,
        "player": {
            "full_name": f"Player {sleeper_id}",
            "position": position,
            "dg_status": engine_path,
        },
        "valuation": {
            "engine_path": engine_path,
            "valuation_status": valuation_status,
            "dynasty_value_score": xvar,
            "xvar": xvar,
            "xvar_percentile_overall": None,
            "xvar_percentile_position": None,
            "decision_supported": False,
        },
        "market_overlay": None,
        "divergence": None,
    }


def _fc(sleeper_id: str, position: str, value: float, *, volatility: float = 0.0) -> dict:
    return {
        "player": {
            "sleeperId": sleeper_id,
            "name": f"Market {sleeper_id}",
            "position": position,
        },
        "value": value,
        "overallRank": 1,
        "positionRank": 1,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": volatility,
    }


def _batch(rows: list[dict]) -> dict:
    return {
        "schema_version": "universe_pvo_batch.v1",
        "league_id": "league",
        "captured_at": "2026-05-22T12:00:00+00:00",
        "players": rows,
        "defaults": {"divergence_noise_band": 0.10},
    }


def test_market_divergence_compares_percentiles_not_raw_values():
    from src.dynasty_genius.universe_market_divergence import (
        build_universe_market_divergence,
    )

    batch = _batch([
        _row("a", "WR", 90.0),
        _row("b", "WR", 80.0),
        _row("c", "WR", 70.0),
    ])
    fc_response = [
        _fc("a", "WR", 1000.0),
        _fc("b", "WR", 9000.0),
        _fc("c", "WR", 500.0),
    ]

    result = build_universe_market_divergence(
        batch,
        fc_response,
        min_cohort_size=3,
        volatility_threshold=999.0,
    )

    row = next(player for player in result["players"] if player["sleeper_player_id"] == "a")
    assert row["market_overlay"]["market_value"] == 1000.0
    assert row["valuation"]["xvar"] == 90.0
    assert "market_value" not in row["valuation"]
    assert row["divergence"]["model_percentile"] == pytest.approx(5 / 6, abs=0.001)
    assert row["divergence"]["market_percentile"] == pytest.approx(0.5, abs=0.001)
    assert row["divergence"]["signal"] == "MODEL_HIGH_MARKET_LOW"
    assert row["divergence"]["signal_status"] == "gates_passed"
    assert row["divergence"]["decision_supported"] is False


def test_market_divergence_suppresses_stale_volatile_and_small_cohort_rows():
    from src.dynasty_genius.universe_market_divergence import (
        build_universe_market_divergence,
    )

    stale = build_universe_market_divergence(
        _batch([_row("a", "RB", 10.0), _row("b", "RB", 8.0)]),
        [_fc("a", "RB", 100.0), _fc("b", "RB", 200.0)],
        fetch_caveats=["stale_market_data"],
        min_cohort_size=2,
    )
    assert stale["players"][0]["divergence"]["signal"] == "SUPPRESSED_STALE_MARKET"
    assert "stale_market_data" in stale["players"][0]["divergence"]["failed_gates"]

    volatile = build_universe_market_divergence(
        _batch([_row("a", "TE", 10.0), _row("b", "TE", 8.0)]),
        [_fc("a", "TE", 100.0, volatility=151.0), _fc("b", "TE", 200.0)],
        min_cohort_size=2,
        volatility_threshold=150.0,
    )
    assert volatile["players"][0]["divergence"]["signal"] == "SUPPRESSED_VOLATILE_MARKET"
    assert "volatile_market" in volatile["players"][0]["divergence"]["failed_gates"]

    small = build_universe_market_divergence(
        _batch([_row("a", "QB", 10.0), _row("b", "QB", 8.0)]),
        [_fc("a", "QB", 100.0), _fc("b", "QB", 200.0)],
        min_cohort_size=3,
    )
    assert small["players"][0]["divergence"]["signal"] == "SUPPRESSED_SMALL_COHORT"
    assert "small_cohort" in small["players"][0]["divergence"]["failed_gates"]


def test_market_divergence_marks_unavailable_without_imperative_language():
    from src.dynasty_genius.universe_market_divergence import (
        build_universe_market_divergence,
    )

    result = build_universe_market_divergence(
        _batch([
            _row("pre", "RB", None, engine_path="PRE_MODEL", valuation_status="PRE_MODEL"),
            _row("bad", "WR", None, engine_path="UNRESOLVED_IDENTITY", valuation_status="UNRESOLVED_IDENTITY", identity_status="unresolved"),
            {
                **_row("name", "TE", None, engine_path="PRE_MODEL", valuation_status="PRE_MODEL"),
                "player": {"full_name": "Russell Example", "position": "TE", "dg_status": "PRE_MODEL"},
            },
        ]),
        [_fc("pre", "RB", 100.0), _fc("bad", "WR", 100.0), _fc("name", "TE", 100.0)],
        min_cohort_size=1,
    )

    assert result["coverage"]["banned_language_present"] == []
    assert result["coverage"]["phase17_4_exit_criteria"]["no_imperative_language"] is True
    assert result["players"][0]["divergence"]["signal"] == "UNAVAILABLE"
    assert result["players"][1]["divergence"]["signal"] == "UNRESOLVED_IDENTITY"
    assert result["coverage"]["decision_supported_true_count"] == 0


def test_market_divergence_does_not_mutate_input_batch():
    from src.dynasty_genius.universe_market_divergence import (
        build_universe_market_divergence,
    )

    batch = _batch([_row("a", "WR", 10.0), _row("b", "WR", 8.0)])
    original = copy.deepcopy(batch)
    build_universe_market_divergence(
        batch,
        [_fc("a", "WR", 100.0), _fc("b", "WR", 200.0)],
        min_cohort_size=2,
    )
    assert batch == original


def test_market_divergence_module_not_imported_by_engine_training_paths():
    from pathlib import Path

    forbidden = "universe_market_divergence"
    scanned_paths = [
        Path("src/dynasty_genius/scoring/engine_a.py"),
        Path("src/dynasty_genius/eval/backtest_harness.py"),
        Path("scripts/build_universe_pvo_batch.py"),
        Path("scripts/assemble_engine_b_dataset.py"),
    ]
    offenders = [path.as_posix() for path in scanned_paths if forbidden in path.read_text()]
    assert offenders == []
