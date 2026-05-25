"""Phase 8.1 contract tests: GET /roster/audit returns PVO-shaped objects.

Verifies:
1. run_audit_pvo() returns a dict with "players" containing PVO-shaped objects.
2. No banned field appears on any player object.
3. TE players carry engine_b_experimental_v1_fallback caveat and EXPERIMENTAL grade.
4. market_overlay is None on every player object.
5. decision_supported is False on every player object.
6. counter_argument is present on players with a non-null dynasty_value_score.
7. Response envelope carries "status" = "active" and "engine" = "pvo_assembler_v1".
8. Non-skill positions are excluded from the players array.
9. Players are sorted by years_to_cliff ascending.
10. Empty roster returns an empty players array.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

from app.services.roster_auditor import run_audit_pvo

# ── Constants ─────────────────────────────────────────────────────────────────

BANNED_FIELDS = {"action", "verdict", "dynasty_tier", "confidence", "my_total", "their_total"}

# ── Fixtures ──────────────────────────────────────────────────────────────────

_RB_PLAYER = {
    "player_id": "sleeper_rb_001",
    "full_name": "Test RB",
    "position": "RB",
    "team": "KC",
    "age": 25,
    "gsis_id": "gsis_rb_001",
}

_WR_PLAYER = {
    "player_id": "sleeper_wr_001",
    "full_name": "Test WR",
    "position": "WR",
    "team": "DET",
    "age": 24,
    "gsis_id": "gsis_wr_001",
}

_TE_PLAYER = {
    "player_id": "sleeper_te_001",
    "full_name": "Test TE",
    "position": "TE",
    "team": "KC",
    "age": 27,
    "gsis_id": "gsis_te_001",
}

_QB_PLAYER = {
    "player_id": "sleeper_qb_001",
    "full_name": "Test QB",
    "position": "QB",
    "team": "BUF",
    "age": 28,
    "gsis_id": "gsis_qb_001",
}

_NON_SKILL_PLAYER = {
    "player_id": "sleeper_k_001",
    "full_name": "Test Kicker",
    "position": "K",
    "team": "NE",
    "age": 30,
    "gsis_id": "gsis_k_001",
}

_ROOKIE_PLAYER = {
    "player_id": "13414",
    "full_name": "Kaelon Black",
    "position": "RB",
    "team": "SF",
    "age": 24,
    "gsis_id": None,
}

_RB_ENGINE_B_SCORE = {
    "player_id": "gsis_rb_001",
    "predicted_avg_ppg_t1_t2": 15.5,
    "engine": "engine_b_v2_rb",
    "feature_season": 2024,
    "position": "RB",
    "decision_supported": False,
    "experimental": False,
    "caveats": ["engine_b_not_decision_grade"],
}

_TE_ENGINE_B_SCORE = {
    "player_id": "gsis_te_001",
    "predicted_avg_ppg_t1_t2": 9.0,
    "engine": "engine_b_v1",
    "feature_season": 2024,
    "position": "TE",
    "decision_supported": False,
    "experimental": True,
    "caveats": [
        "engine_b_not_decision_grade",
        "engine_b_does_not_beat_baseline_for_this_position",
    ],
}


def _default_roster():
    return [_RB_PLAYER, _WR_PLAYER, _TE_PLAYER, _QB_PLAYER, _NON_SKILL_PLAYER]


def _default_scores():
    return [_RB_ENGINE_B_SCORE, _TE_ENGINE_B_SCORE]


def _run(roster=None, scores=None):
    roster = roster if roster is not None else _default_roster()
    scores = scores if scores is not None else _default_scores()
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=roster,
        ),
        patch(
            "app.services.roster_auditor.score_inference_partition",
            return_value=scores,
        ),
        patch(
            "app.services.roster_auditor.load_qb_identity_bridge",
            return_value={"players": {}},
        ),
    ):
        return asyncio.run(run_audit_pvo())


def _universe_row_for_rookie() -> dict:
    return {
        "sleeper_player_id": "13414",
        "dg_player_id": "kaelon_black_rb",
        "identity_status": "resolved",
        "identity_ids": {"sleeper_id": "13414"},
        "player": {
            "full_name": "Kaelon Black",
            "position": "RB",
            "team": "SFO",
            "age": 24.0,
            "dg_status": "ENGINE_A",
        },
        "league_context": {
            "rostered": True,
            "roster_id": 1,
            "in_current_draft": True,
            "on_taxi": False,
        },
        "valuation": {
            "engine_path": "ENGINE_A",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 61.55,
            "xvar": 13.4,
            "model_grade": "PROSPECT_C",
            "feature_completeness": 0.2857,
            "decision_supported": False,
        },
    }


def _run_with_universe(tmp_path, universe_rows, roster=None, scores=None):
    path = tmp_path / "universe_pvo_latest.json"
    path.write_text(json.dumps({"players": universe_rows}))
    roster = roster if roster is not None else [_ROOKIE_PLAYER, _RB_PLAYER]
    scores = scores if scores is not None else [_RB_ENGINE_B_SCORE]
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=roster,
        ),
        patch(
            "app.services.roster_auditor.score_inference_partition",
            return_value=scores,
        ),
        patch(
            "app.services.roster_auditor.load_qb_identity_bridge",
            return_value={"players": {}},
        ),
        patch(
            "app.services.roster_auditor.UNIVERSE_PVO_LATEST_PATH",
            path,
            create=True,
        ),
        patch(
            "src.dynasty_genius.services.market_overlay_service.enrich_pvo_list_with_market_overlay",
            return_value=None,
        ),
    ):
        return asyncio.run(run_audit_pvo())


# ── Test 1: PVO-shaped players array ─────────────────────────────────────────

def test_response_has_pvo_shaped_players():
    result = _run()
    assert "players" in result
    assert isinstance(result["players"], list)
    assert len(result["players"]) > 0
    required = {"player_id", "position", "model_grade", "caveats", "decision_supported", "signal_completeness"}
    for player in result["players"]:
        for field in required:
            assert field in player, f"PVO field {field!r} missing from {player.get('player_id')}"


# ── Test 2: Envelope shape ────────────────────────────────────────────────────

def test_response_envelope():
    result = _run()
    assert result["status"] == "active"
    assert result["engine"] == "pvo_assembler_v1"
    assert result["decision_supported"] is False
    assert "reason" in result
    assert "caveats" in result


# ── Test 3: No banned fields on any player ───────────────────────────────────

def test_no_banned_fields_on_players():
    result = _run()
    for player in result["players"]:
        found = BANNED_FIELDS & set(player.keys())
        assert not found, f"Banned fields on {player.get('player_id')}: {found}"


# ── Test 4: TE carries experimental caveat and grade ─────────────────────────

def test_te_carries_experimental_caveat_and_grade():
    result = _run()
    te_players = [p for p in result["players"] if p.get("position") == "TE"]
    assert te_players, "No TE players in result"
    for te in te_players:
        assert "engine_b_experimental_v1_fallback" in te["caveats"], (
            f"TE {te.get('player_id')} missing engine_b_experimental_v1_fallback"
        )
        assert te["model_grade"] == "EXPERIMENTAL", (
            f"TE {te.get('player_id')} model_grade={te['model_grade']!r}"
        )


# ── Test 5: market_overlay is None on all players ────────────────────────────

def test_market_overlay_is_none():
    result = _run()
    for player in result["players"]:
        assert player.get("market_overlay") is None, (
            f"market_overlay={player['market_overlay']!r} for {player.get('player_id')}"
        )


# ── Test 6: decision_supported is False on all players ───────────────────────

def test_decision_supported_is_false():
    result = _run()
    for player in result["players"]:
        assert player["decision_supported"] is False, (
            f"decision_supported not False for {player.get('player_id')}"
        )


# ── Test 7: counter_argument present when dynasty_value_score is non-null ────

def test_counter_argument_present_when_scored():
    result = _run()
    for player in result["players"]:
        if player.get("dynasty_value_score") is not None:
            assert player.get("counter_argument") is not None, (
                f"counter_argument missing on scored player {player.get('player_id')}"
            )


# ── Test 8: Non-skill positions excluded ─────────────────────────────────────

def test_non_skill_positions_excluded():
    result = _run()
    positions = {p["position"] for p in result["players"]}
    assert "K" not in positions
    assert "DEF" not in positions
    assert "P" not in positions


# ── Test 9: Players sorted by years_to_cliff ascending ───────────────────────

def test_players_sorted_by_years_to_cliff():
    result = _run()
    cliffs = [
        p["roster_audit"]["years_to_cliff"]
        for p in result["players"]
        if p.get("roster_audit") and p["roster_audit"].get("years_to_cliff") is not None
    ]
    assert cliffs == sorted(cliffs), f"Not sorted by years_to_cliff: {cliffs}"


# ── Test 10: Empty roster returns empty players array ────────────────────────

def test_empty_roster_returns_empty_players():
    result = _run(roster=[], scores=[])
    assert result["players"] == []
    assert result["status"] == "active"


def test_current_draft_rookie_uses_engine_a_universe_pvo(tmp_path):
    result = _run_with_universe(tmp_path, [_universe_row_for_rookie()])
    rookie = next(p for p in result["players"] if p["sleeper_id"] == "13414")
    assert rookie["player_id"] == "kaelon_black_rb"
    assert rookie["model_grade"] == "PROSPECT_C"
    assert rookie["engine_used"] == "engine_a"
    assert rookie["dynasty_value_score"] == 61.55
    assert rookie["xvar"] == 13.4
    assert rookie["decision_supported"] is False


def test_engine_a_rookie_reconciliation_preserves_veteran_engine_b_path(tmp_path):
    result = _run_with_universe(tmp_path, [_universe_row_for_rookie()])
    veteran = next(p for p in result["players"] if p["sleeper_id"] == "sleeper_rb_001")
    assert veteran["model_grade"] == "ACTIVE_B"
    assert veteran["engine_used"] == "engine_b"
    assert veteran["dynasty_value_score"] is not None


def test_engine_a_rookie_carries_counter_argument_when_dvs_above_80(tmp_path):
    high_dvs_row = {
        **_universe_row_for_rookie(),
        "sleeper_player_id": "99999",
        "dg_player_id": "mendoza_wr",
        "identity_ids": {"sleeper_id": "99999"},
        "player": {"full_name": "Fernando Mendoza", "position": "WR", "team": "MIA", "age": 22.0},
        "valuation": {
            "engine_path": "ENGINE_A",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 85.14,
            "xvar": 10.31,
            "model_grade": "PROSPECT_B",
            "feature_completeness": 0.28,
            "decision_supported": False,
        },
    }
    high_dvs_player = {
        "player_id": "99999",
        "full_name": "Fernando Mendoza",
        "position": "WR",
        "team": "MIA",
        "age": 22,
        "gsis_id": None,
    }
    result = _run_with_universe(
        tmp_path,
        [_universe_row_for_rookie(), high_dvs_row],
        roster=[_ROOKIE_PLAYER, high_dvs_player, _RB_PLAYER],
        scores=[_RB_ENGINE_B_SCORE],
    )
    mendoza = next(p for p in result["players"] if p["sleeper_id"] == "99999")
    assert mendoza["dynasty_value_score"] == 85.14
    assert mendoza["counter_argument"] is not None, "Product Constitution Rule 4: counter_argument required for DVS > 80"


def test_roster_audit_degrades_when_universe_artifact_absent(tmp_path):
    missing_path = tmp_path / "missing.json"
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=[_ROOKIE_PLAYER],
        ),
        patch("app.services.roster_auditor.score_inference_partition", return_value=[]),
        patch("app.services.roster_auditor.load_qb_identity_bridge", return_value={"players": {}}),
        patch("app.services.roster_auditor.UNIVERSE_PVO_LATEST_PATH", missing_path, create=True),
        patch(
            "src.dynasty_genius.services.market_overlay_service.enrich_pvo_list_with_market_overlay",
            return_value=None,
        ),
    ):
        result = asyncio.run(run_audit_pvo())
    rookie = result["players"][0]
    assert rookie["sleeper_id"] == "13414"
    assert rookie["model_grade"] == "PRE_MODEL"
