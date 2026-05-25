"""Phase 21 W2 — Waiver-Drop Integration TDD tests (7 tests).

Written RED-first before league_opportunity_map.py is updated.
"""
from __future__ import annotations

from src.dynasty_genius.league_opportunity_map import build_league_opportunity_map
from src.dynasty_genius.roster_cut_engine import RosterCutCandidate, RosterCutResult

# ─── Fixture helpers ──────────────────────────────────────────────────────────


def _team(roster_id: int, *, players: list[dict] | None = None) -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "roster_id": roster_id,
        "owner": {"display_name": f"owner{roster_id}", "team_name": f"Team {roster_id}"},
        "positional_summary": {
            pos: {"z_score": 0.0, "surplus_label": "neutral", "n_rostered": 2}
            for pos in ("QB", "RB", "WR", "TE")
        },
        "team_value_views": {"starter_weighted_xvar": 100.0, "lineup_xvar": 100.0},
        "posture": {"label": "UNCLASSIFIED", "score": None},
        "future_picks": {"owned": [], "outgoing": []},
        "players": players or [],
        "decision_supported": False,
    }


def _player(
    sleeper_id: str,
    *,
    name: str = "Test Player",
    position: str = "WR",
    roster_id: int | None = None,
    signal: str = "MODEL_HIGH_MARKET_LOW",
    delta: float = 0.25,
) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player": {"full_name": name, "position": position},
        "league_context": {
            "rostered": roster_id is not None,
            "roster_id": roster_id,
            "on_taxi": False,
            "on_ir": False,
        },
        "valuation": {"engine_path": "ENGINE_B", "xvar": 10.0},
        "market_overlay": {"market_value": 1000.0},
        "divergence": {
            "signal": signal,
            "signal_status": "gates_passed",
            "model_minus_market_delta": delta,
            "model_percentile": 0.75,
            "market_percentile": 0.50,
            "decision_supported": False,
        },
    }


def _fixtures(
    *,
    waiver_players: list[dict] | None = None,
    rostered_players: list[dict] | None = None,
) -> tuple[dict, dict]:
    """Minimal team_matrix + market_divergence."""
    team_matrix = {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-05-24T12:00:00+00:00",
        "teams": [_team(1), _team(2)],
    }
    all_players = list(waiver_players or []) + list(rostered_players or [])
    market_divergence = {
        "schema_version": "market_divergence.v1",
        "league_id": "league",
        "players": all_players,
    }
    return team_matrix, market_divergence


def _make_cut_candidate(
    pid: str,
    *,
    position: str = "WR",
    cut_priority: int = 1,
    ir_compliance_status: str = "NOT_ON_IR",
) -> RosterCutCandidate:
    return RosterCutCandidate(
        sleeper_player_id=pid,
        full_name=f"Player {pid}",
        position=position,
        age=25.0,
        years_exp=2,
        ir_compliance_status=ir_compliance_status,
        taxi_eligibility="INELIGIBLE_VET",
        scoring_tier="A",
        xvar_pct=30.0,
        dvs=40.0,
        cut_priority=cut_priority,
        age_cliff_warning=False,
        cut_rationale=[],
        exempt=False,
        exempt_reason=None,
    )


def _make_cut_result(
    cut_candidates: list[RosterCutCandidate],
    *,
    cuts_required: int = 1,
) -> RosterCutResult:
    return RosterCutResult(
        roster_id=1,
        total_players=22,
        active_slots=20,
        total_capacity=26,
        cuts_required=cuts_required,
        reserve_unrestricted=True,
        cut_candidates=cut_candidates,
        exempt_players=[],
    )


# ─── W2 Tests ─────────────────────────────────────────────────────────────────


def test_no_recommended_drop_when_roster_cut_result_is_none():
    """Without roster_cut_result, WAIVER_CANDIDATE cards have no recommended_drop field."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    result = build_league_opportunity_map(tm, md)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    assert len(waiver_cards) >= 1
    for card in waiver_cards:
        assert "recommended_drop" not in card


def test_waiver_cards_get_recommended_drop_when_cut_result_provided():
    """With a cut result, every WAIVER_CANDIDATE card has a recommended_drop dict."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    cut_result = _make_cut_result([_make_cut_candidate("c1", position="RB")])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    assert len(waiver_cards) >= 1
    for card in waiver_cards:
        assert "recommended_drop" in card
        assert card["recommended_drop"] is not None
        assert "sleeper_player_id" in card["recommended_drop"]


def test_recommended_drop_matches_same_position():
    """WR waiver target + WR cut candidate → recommended_drop is the WR."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    wr_cut = _make_cut_candidate("wr_cut", position="WR", cut_priority=1)
    rb_cut = _make_cut_candidate("rb_cut", position="RB", cut_priority=2)
    # Both are cut candidates; WR should be paired with the WR waiver target
    cut_result = _make_cut_result([wr_cut, rb_cut])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    w1_card = next(c for c in waiver_cards if c["asset"]["sleeper_player_id"] == "w1")
    assert w1_card["recommended_drop"]["sleeper_player_id"] == "wr_cut"
    assert w1_card["recommended_drop"]["position"] == "WR"


def test_recommended_drop_falls_back_to_priority1_when_no_position_match():
    """QB waiver target, no QB cut candidates → recommended_drop is priority-1 cut."""
    waiver = [_player("w1", position="QB")]
    tm, md = _fixtures(waiver_players=waiver)
    rb_cut = _make_cut_candidate("rb_cut", position="RB", cut_priority=1)
    wr_cut = _make_cut_candidate("wr_cut", position="WR", cut_priority=2)
    cut_result = _make_cut_result([rb_cut, wr_cut])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    w1_card = next(c for c in waiver_cards if c["asset"]["sleeper_player_id"] == "w1")
    # No QB cut candidate → fallback to priority-1 (rb_cut)
    assert w1_card["recommended_drop"]["sleeper_player_id"] == "rb_cut"


def test_forced_compliance_overrides_position_pairing():
    """Forced-compliance candidate (cut_priority=0) is recommended regardless of position."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    forced = _make_cut_candidate("forced_rb", position="RB", cut_priority=0,
                                 ir_compliance_status="ILLEGAL_RESERVE")
    wr_cut = _make_cut_candidate("wr_cut", position="WR", cut_priority=1)
    # Even though wr_cut matches position, forced should override
    cut_result = _make_cut_result([forced, wr_cut])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    w1_card = next(c for c in waiver_cards if c["asset"]["sleeper_player_id"] == "w1")
    assert w1_card["recommended_drop"]["sleeper_player_id"] == "forced_rb"
    assert w1_card["recommended_drop"]["cut_priority"] == 0


def test_non_waiver_cards_do_not_get_recommended_drop():
    """DIVERGENCE_MODEL_HIGH cards must not have a recommended_drop field."""
    rostered = [_player("r1", position="WR", roster_id=2)]
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver, rostered_players=rostered)
    cut_result = _make_cut_result([_make_cut_candidate("c1")])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    non_waiver = [c for c in result["cards"] if c["card_type"] != "WAIVER_CANDIDATE"]
    for card in non_waiver:
        assert "recommended_drop" not in card


def test_decision_supported_false_preserved_with_recommended_drop():
    """Cards enriched with recommended_drop still have decision_supported=False."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    cut_result = _make_cut_result([_make_cut_candidate("c1")])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    assert len(waiver_cards) >= 1
    for card in waiver_cards:
        assert card["decision_supported"] is False


# ─── Codex patch: Finding 2 — nested decision_supported in recommended_drop ──


def test_recommended_drop_contains_decision_supported_false():
    """Every non-null recommended_drop must carry its own decision_supported: False."""
    waiver = [_player("w1", position="WR")]
    tm, md = _fixtures(waiver_players=waiver)
    cut_result = _make_cut_result([_make_cut_candidate("c1")])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)
    waiver_cards = [c for c in result["cards"] if c["card_type"] == "WAIVER_CANDIDATE"]
    assert len(waiver_cards) >= 1
    for card in waiver_cards:
        drop = card.get("recommended_drop")
        if drop is not None:
            assert "decision_supported" in drop, "recommended_drop missing decision_supported key"
            assert drop["decision_supported"] is False


def test_opportunity_map_recursive_no_decision_supported_true():
    """Recursive walk of the full opportunity map output finds no decision_supported=True."""
    waiver = [_player("w1", position="WR")]
    rostered = [_player("r1", position="RB", roster_id=2)]
    tm, md = _fixtures(waiver_players=waiver, rostered_players=rostered)
    cut_result = _make_cut_result([_make_cut_candidate("c1")])
    result = build_league_opportunity_map(tm, md, roster_cut_result=cut_result)

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            assert obj.get("decision_supported") is not True, (
                f"decision_supported=True found in: {obj}"
            )
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(result)
