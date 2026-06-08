from typing import Any

from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch

SURFACE3_PRESERVED_KEYS = {
    "counter_argument",
    "risk_flags",
    "top_drivers",
    "caveats",
    "draft_class",
    "nfl_draft_pick",
    "nfl_draft_round",
    "projection_1y",
    "projection_2y",
    "projection_3y",
}

EXPECTED_EXISTING_ROW = {
    "schema_version": "universe_pvo_batch.v1",
    "pipeline_run_id": None,
    "captured_at": "2026-06-06T00:00:01+00:00",
    "sleeper_player_id": "13269",
    "dg_player_id": "rookie_qb_13269",
    "identity_status": "resolved",
    "identity_ids": {
        "sleeper_id": "13269",
        "gsis_id": "00-rookie-qb",
        "pfr_id": None,
        "pff_id": None,
        "espn_id": None,
    },
    "player": {
        "full_name": "Rookie Quarterback",
        "position": "QB",
        "team": "KC",
        "age": 22.0,
        "years_exp": 0,
        "sleeper_status": "Active",
        "dg_status": "ENGINE_A",
    },
    "league_context": {"rostered": True, "roster_id": 1},
    "dvs_engine": "A",
    "final_college_age": 21.4,
    "te_ryptpa_final": None,
    "te_yards_per_reception_career": None,
    "valuation": {
        "engine_path": "ENGINE_A",
        "valuation_status": "MODEL_SUPPORTED",
        "dynasty_value_score": 84.25,
        "xvar": 11.75,
        "xvar_percentile_overall": 100.0,
        "xvar_percentile_position": 91.0,
        "model_version": "engine_a_v3",
        "model_grade": "PROSPECT_A",
        "feature_completeness": 0.93,
        "decision_supported": False,
    },
    "market_overlay": None,
    "divergence": None,
    "lineage": {
        "sleeper_snapshot_hash": "sha256:surface3-test",
        "governance_version": "1.0.0",
    },
}


def _snapshot() -> dict[str, Any]:
    return {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-surface3",
        "captured_at": "2026-06-06T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "13269",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {
                    "full_name": "Fallback Name",
                    "position": "QB",
                    "team": "FA",
                    "age": 22.5,
                    "years_exp": 0,
                    "sleeper_status": "Active",
                },
                "league_context": {"rostered": True, "roster_id": 1},
            }
        ],
        "lineage": {"sleeper_players_hash": "sha256:surface3-test"},
    }


def _prospect_pvo() -> dict[str, Any]:
    return {
        "sleeper_id": "13269",
        "player_id": "rookie_qb_13269",
        "full_name": "Rookie Quarterback",
        "position": "QB",
        "nfl_team": "KC",
        "age": 22.0,
        "gsis_id": "00-rookie-qb",
        "model_grade": "PROSPECT_A",
        "model_version": "engine_a_v3",
        "signal_completeness": 0.93,
        "dynasty_value_score": 84.25,
        "xvar": 11.75,
        "dvs_pct": 91.0,
        "dvs_engine": "A",
        "decision_supported": False,
        "market_overlay": None,
        "final_college_age": 21.4,
        "counter_argument": "Premium valuation assumes a fragile QB path.",
        "risk_flags": ["limited_nfl_sample"],
        "top_drivers": ["Round 1 draft capital", "Early declare"],
        "caveats": ["Projection remains experimental."],
        "draft_class": 2026,
        "nfl_draft_pick": 14,
        "nfl_draft_round": 1,
        "projection_1y": 7.5,
        "projection_2y": 12.0,
        "projection_3y": 15.25,
    }


def test_surface3_preserves_only_the_ten_dto_backed_fields_additively():
    source_pvo = _prospect_pvo()

    batch = build_universe_pvo_batch(
        _snapshot(),
        prospect_pvos=[source_pvo],
        captured_at="2026-06-06T00:00:01+00:00",
    )

    row = batch["players"][0]
    existing_projection = {
        key: value for key, value in row.items() if key not in SURFACE3_PRESERVED_KEYS
    }

    assert existing_projection == EXPECTED_EXISTING_ROW
    assert set(row) == set(EXPECTED_EXISTING_ROW) | SURFACE3_PRESERVED_KEYS
    for key in SURFACE3_PRESERVED_KEYS:
        assert row[key] == source_pvo[key]
