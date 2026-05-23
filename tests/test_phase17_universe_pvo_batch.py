from __future__ import annotations

from src.dynasty_genius.universe_pvo_batch import (
    ENGINE_ROUTE_VALUES,
    build_universe_pvo_batch,
    build_universe_pvo_coverage,
)


def _snapshot() -> dict:
    return {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-05-22T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "101",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Rookie One", "position": "WR", "team": "NYG"},
                "league_context": {"rostered": True, "roster_id": 1},
            },
            {
                "sleeper_player_id": "202",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Active One", "position": "RB", "team": "KC"},
                "league_context": {"rostered": True, "roster_id": 2},
            },
            {
                "sleeper_player_id": "303",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Unknown One", "position": "TE", "team": "FA"},
                "league_context": {"rostered": True, "roster_id": 3},
            },
            {
                "sleeper_player_id": "404",
                "cohort": "CONTEXT_ONLY",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Rostered K", "position": "K", "team": "DAL"},
                "league_context": {"rostered": True, "roster_id": 4},
            },
            {
                "sleeper_player_id": "505",
                "cohort": "INACTIVE",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Inactive WR", "position": "WR", "team": None},
                "league_context": {"rostered": False, "roster_id": None},
            },
            {
                "sleeper_player_id": "0",
                "cohort": "UNRESOLVED_IDENTITY",
                "identity_status": "unresolved",
                "player": {"full_name": None, "position": None, "team": None},
                "league_context": {"rostered": True, "roster_id": 5},
            },
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }


def test_universe_pvo_batch_routes_existing_pvos_and_unscored_context():
    prospect_card = {
        "sleeper_id": "101",
        "player_id": "rookie_one_wr_2004",
        "full_name": "Rookie One",
        "position": "WR",
        "model_grade": "PROSPECT_C",
        "dynasty_value_score": 88.0,
        "xvar": 12.5,
        "dvs_engine": "A",
        "decision_supported": False,
        "market_overlay": None,
    }
    engine_b_pvo = {
        "sleeper_id": "202",
        "player_id": "00-0000202",
        "full_name": "Active One",
        "position": "RB",
        "model_grade": "ACTIVE_B",
        "dynasty_value_score": 72.0,
        "xvar": 8.5,
        "dvs_pct": 77.0,
        "dvs_engine": "B",
        "decision_supported": False,
        "market_overlay": None,
    }

    batch = build_universe_pvo_batch(
        _snapshot(),
        prospect_pvos=[prospect_card],
        active_pvos=[engine_b_pvo],
        captured_at="2026-05-22T00:00:01+00:00",
    )

    by_id = {row["sleeper_player_id"]: row for row in batch["players"]}
    assert by_id["101"]["valuation"]["engine_path"] == "ENGINE_A"
    assert by_id["101"]["valuation"]["xvar"] == 12.5
    assert by_id["101"]["valuation"]["xvar_percentile_overall"] == 100.0
    assert by_id["202"]["valuation"]["engine_path"] == "ENGINE_B"
    assert by_id["202"]["valuation"]["xvar_percentile_position"] == 77.0
    assert by_id["202"]["valuation"]["xvar_percentile_overall"] == 50.0
    assert by_id["303"]["valuation"]["engine_path"] == "PRE_MODEL"
    assert by_id["303"]["valuation"]["xvar_percentile_overall"] is None
    assert by_id["404"]["valuation"]["engine_path"] == "CONTEXT_ONLY"
    assert by_id["505"]["valuation"]["engine_path"] == "INACTIVE"
    assert by_id["0"]["valuation"]["engine_path"] == "UNRESOLVED_IDENTITY"
    assert all(row["valuation"]["decision_supported"] is False for row in batch["players"])
    assert all(row["market_overlay"] is None for row in batch["players"])


def test_xvar_percentile_overall_ranks_model_backed_rows_across_positions_only():
    snapshot = _snapshot()
    pvos = [
        {
            "sleeper_id": "101",
            "player_id": "rookie_wr",
            "full_name": "Rookie One",
            "position": "WR",
            "model_grade": "PROSPECT_C",
            "dynasty_value_score": 82.0,
            "xvar": 10.0,
            "dvs_engine": "A",
        },
        {
            "sleeper_id": "202",
            "player_id": "active_rb",
            "full_name": "Active One",
            "position": "RB",
            "model_grade": "ACTIVE_B",
            "dynasty_value_score": 75.0,
            "xvar": 5.0,
            "dvs_pct": 70.0,
            "dvs_engine": "B",
        },
        {
            "sleeper_id": "303",
            "player_id": "active_te",
            "full_name": "Unknown One",
            "position": "TE",
            "model_grade": "ACTIVE_B",
            "dynasty_value_score": 60.0,
            "xvar": -2.0,
            "dvs_pct": 40.0,
            "dvs_engine": "B",
        },
    ]

    batch = build_universe_pvo_batch(snapshot, prospect_pvos=[pvos[0]], active_pvos=pvos[1:])
    by_id = {row["sleeper_player_id"]: row for row in batch["players"]}

    assert by_id["101"]["valuation"]["xvar_percentile_overall"] == 100.0
    assert by_id["202"]["valuation"]["xvar_percentile_overall"] == 66.7
    assert by_id["303"]["valuation"]["xvar_percentile_overall"] == 33.3
    assert by_id["404"]["valuation"]["xvar_percentile_overall"] is None
    assert by_id["505"]["valuation"]["xvar_percentile_overall"] is None
    assert by_id["202"]["valuation"]["xvar_percentile_position"] == 70.0
    assert all(row["market_overlay"] is None for row in batch["players"])
    assert batch["coverage"]["xvar_percentile_overall_populated_count"] == 3
    assert batch["coverage"]["phase18_4_exit_criteria"]["overall_percentile_internal_xvar_only"] is True
    assert batch["coverage"]["phase18_4_exit_criteria"]["non_model_rows_overall_percentile_null"] is True


def test_universe_pvo_coverage_requires_rostered_skill_players_have_explicit_routes():
    batch = build_universe_pvo_batch(_snapshot(), prospect_pvos=[], active_pvos=[])
    coverage = build_universe_pvo_coverage(batch)

    assert coverage["rostered_skill_players_missing_route"] == []
    assert coverage["decision_supported_true_count"] == 0
    assert coverage["market_overlay_present_count"] == 0
    assert coverage["counts_by_engine_path"]["PRE_MODEL"] == 3
    assert set(coverage["allowed_engine_routes"]) == ENGINE_ROUTE_VALUES


def test_active_engine_b_row_with_engine_a_dead_window_provenance_routes_engine_b():
    snapshot = {
        "players": [
            {
                "sleeper_player_id": "202",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Active One", "position": "RB", "team": "KC"},
                "league_context": {"rostered": True, "roster_id": 2},
            }
        ]
    }
    active_dead_window_pvo = {
        "sleeper_id": "202",
        "player_id": "00-0000202",
        "full_name": "Active One",
        "position": "RB",
        "engine_used": "engine_b",
        "model_grade": "ACTIVE_B",
        "dvs_engine": "A",
        "decision_supported": False,
        "market_overlay": None,
    }

    batch = build_universe_pvo_batch(
        snapshot,
        prospect_pvos=[],
        active_pvos=[active_dead_window_pvo],
    )

    assert batch["players"][0]["valuation"]["engine_path"] == "ENGINE_B"
