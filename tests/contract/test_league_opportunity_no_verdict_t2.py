"""Phase 1 T2 RED: replace recommended_drop with descriptive capacity pool."""

from __future__ import annotations

from typing import Any

from app.api.routes import league_pulse_assembler, league_pulse_models
from src.dynasty_genius.roster_cut_engine import RosterCutCandidate, RosterCutResult


def _candidate(
    pid: str,
    *,
    name: str,
    position: str = "WR",
    xvar_pct: float | None = 20.0,
    dvs: float | None = 40.0,
    cut_priority: int = 1,
    ir_status: str = "NOT_ON_IR",
    rationale: list[str] | None = None,
) -> RosterCutCandidate:
    return RosterCutCandidate(
        sleeper_player_id=pid,
        full_name=name,
        position=position,
        age=25.0,
        years_exp=2,
        ir_compliance_status=ir_status,
        taxi_eligibility="INELIGIBLE_VET",
        scoring_tier="A" if xvar_pct is not None else "C",
        xvar_pct=xvar_pct,
        dvs=dvs,
        cut_priority=cut_priority,
        age_cliff_warning=False,
        cut_rationale=rationale or ["waiver_status_from_sleeper_snapshot"],
        exempt=False,
        exempt_reason=None,
    )


def _cut_result(candidates: list[RosterCutCandidate]) -> RosterCutResult:
    return RosterCutResult(
        roster_id=1,
        total_players=27,
        active_slots=25,
        total_capacity=26,
        cuts_required=max(0, len(candidates)),
        reserve_unrestricted=True,
        cut_candidates=candidates,
        exempt_players=[],
    )


def _team(roster_id: int) -> dict[str, Any]:
    return {
        "schema_version": "team_value_matrix.v1",
        "roster_id": roster_id,
        "owner": {"team_name": f"Team {roster_id}"},
        "positional_summary": {
            pos: {"z_score": 0.0, "surplus_label": "neutral", "n_rostered": 2}
            for pos in ("QB", "RB", "WR", "TE")
        },
        "team_value_views": {
            "starter_weighted_xvar": 100.0,
            "lineup_xvar": 100.0,
            "depth_credit_xvar": 0.0,
            "total_xvar_capped": 100.0,
            "top_n_xvar": 100.0,
        },
        "age_profile": {},
        "posture": {"label": "UNCLASSIFIED", "score": None},
        "future_picks": {"owned": [], "outgoing": []},
        "players": [],
        "decision_supported": False,
    }


def _team_posture() -> dict[str, Any]:
    return {
        "schema_version": "team_posture.v1",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "Team 1"},
                "posture": {
                    "label": "BALANCED",
                    "score": 0.0,
                    "components": {},
                    "caveats": [],
                },
            }
        ],
    }


def _team_value() -> dict[str, Any]:
    return {
        "schema_version": "team_value_matrix.v1",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [_team(1)],
    }


def _market_divergence() -> dict[str, Any]:
    return {
        "schema_version": "market_divergence.v1",
        "league_id": "league",
        "players": [
            {
                "sleeper_player_id": "waiver-1",
                "dg_player_id": "dg_waiver_1",
                "player": {"full_name": "Waiver Player", "position": "WR"},
                "league_context": {
                    "rostered": False,
                    "roster_id": None,
                    "on_taxi": False,
                    "on_ir": False,
                },
                "valuation": {"engine_path": "ENGINE_B", "xvar": 10.0},
                "divergence": {
                    "signal": "MODEL_HIGH_MARKET_LOW",
                    "signal_status": "gates_passed",
                    "model_minus_market_delta": 0.25,
                    "model_percentile": 0.75,
                    "market_percentile": 0.50,
                    "decision_supported": False,
                },
            }
        ],
    }


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def _waiver_card(opportunity: dict[str, Any]) -> dict[str, Any]:
    cards = [
        card
        for card in opportunity["cards"]
        if (card.get("asset") or {}).get("sleeper_player_id") == "waiver-1"
    ]
    assert len(cards) == 1
    return cards[0]


def test_t2_bumps_producer_to_v2_and_assembler_accepts_v1_and_v2() -> None:
    """T2 flips the producer contract, while League Pulse tolerates stale v1."""
    from src.dynasty_genius import league_opportunity_map as producer

    assert producer.SCHEMA_VERSION == "league_opportunity.v2"
    assert "league_opportunity.v1" in league_pulse_assembler.ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS
    assert "league_opportunity.v2" in league_pulse_assembler.ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS


def test_producer_emits_descriptive_pool_not_tool_selected_drop() -> None:
    from src.dynasty_genius import league_opportunity_map as producer

    opportunity = producer.build_league_opportunity_map(
        {"schema_version": "team_value_matrix.v1", "league_id": "league", "teams": [_team(1)]},
        _market_divergence(),
        perspective_roster_id=1,
        roster_cut_result=_cut_result(
            [
                _candidate("z-low", name="Zulu Low", xvar_pct=10.0),
                _candidate("a-low", name="Alpha Low", xvar_pct=10.0),
                _candidate(
                    "ir-hard",
                    name="IR Hard Conflict",
                    position="TE",
                    xvar_pct=3.0,
                    cut_priority=0,
                    ir_status="ILLEGAL_RESERVE",
                    rationale=["reserve_slot_ineligible_must_comply"],
                ),
                _candidate("unvalued", name="Unvalued Player", xvar_pct=None, dvs=None),
            ]
        ),
        captured_at="2026-06-30T10:00:00+00:00",
    )

    card = _waiver_card(opportunity)

    assert card["schema_version"] == "opportunity.v2"
    assert "recommended_drop" not in card
    pool = card["roster_capacity_candidates"]
    assert pool["decision_supported"] is False
    assert pool["pool_status"] == "available"
    assert pool["sort_key"] == "xvar_pct_ascending_then_full_name_then_sleeper_player_id"
    assert pool["selection_rule"] == "descriptive_candidate_pool_no_tool_selection"
    assert pool["narrowing_rule"] == "all_capacity_candidates"
    assert [row["sleeper_player_id"] for row in pool["items"]] == [
        "ir-hard",
        "a-low",
        "z-low",
        "unvalued",
    ]
    assert pool["items"][0]["capacity_conflict_status"] == "hard_roster_rules_conflict"
    assert pool["items"][0]["rule_conflict_label"] == "IR compliance violation"
    assert pool["items"][0]["value_status"] == "valued"
    assert pool["items"][-1]["value_status"] == "unvalued"
    assert pool["items"][-1]["xvar_pct"] is None
    assert "valuation_unavailable" in pool["items"][-1]["caveats"]
    assert _decision_supported_true_count(card) == 0


def test_empty_and_single_row_pools_expose_constraints_without_nomination() -> None:
    from src.dynasty_genius import league_opportunity_map as producer

    empty_opportunity = producer.build_league_opportunity_map(
        {"schema_version": "team_value_matrix.v1", "league_id": "league", "teams": [_team(1)]},
        _market_divergence(),
        perspective_roster_id=1,
        roster_cut_result=_cut_result([]),
        captured_at="2026-06-30T10:00:00+00:00",
    )
    empty_pool = _waiver_card(empty_opportunity)["roster_capacity_candidates"]
    assert empty_pool["pool_status"] == "empty"
    assert empty_pool["items"] == []
    assert empty_pool["narrowing_rule"] == "no_safe_capacity_candidates"
    assert "capacity_blocks_move_unless_protected_player_cut" in empty_pool["caveats"]

    single_opportunity = producer.build_league_opportunity_map(
        {"schema_version": "team_value_matrix.v1", "league_id": "league", "teams": [_team(1)]},
        _market_divergence(),
        perspective_roster_id=1,
        roster_cut_result=_cut_result([_candidate("only", name="Only Candidate")]),
        captured_at="2026-06-30T10:00:00+00:00",
    )
    single_pool = _waiver_card(single_opportunity)["roster_capacity_candidates"]
    assert single_pool["pool_status"] == "constrained_single_candidate"
    assert single_pool["selection_rule"] == "descriptive_candidate_pool_no_tool_selection"
    assert single_pool["narrowing_rule"] == "only_one_capacity_candidate_available"
    assert single_pool["items"][0]["sleeper_player_id"] == "only"


def test_dto_and_assembler_use_pool_shape_with_recursive_decision_supported_false() -> None:
    assert not hasattr(league_pulse_models, "LeaguePulseRecommendedDrop")
    assert "recommended_drops" not in league_pulse_models.LeaguePulseDropCounts.model_fields
    assert "roster_capacity_candidate_pools" in league_pulse_models.LeaguePulseDropCounts.model_fields

    opportunity_v2 = {
        "schema_version": "league_opportunity.v2",
        "captured_at": "2026-06-30T10:01:00+00:00",
        "perspective_roster_id": 1,
        "partner_rankings": [],
        "cards": [
            {
                "schema_version": "opportunity.v2",
                "card_id": "opp-0001",
                "card_type": "WAIVER_CANDIDATE",
                "opportunity_score": 0.5,
                "rationale": {
                    "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
                    "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
                    "evidence": {
                        "signal": "MODEL_HIGH_MARKET_LOW",
                        "signal_status": "gates_passed",
                        "model_minus_market_delta": 0.25,
                        "xvar": 10.0,
                    },
                },
                "score_components": {
                    "fit_score": 0.4,
                    "divergence_score": 0.25,
                    "feasibility_score": 0.9,
                },
                "caveats": ["waiver_status_from_sleeper_snapshot"],
                "roster_capacity_candidates": {
                    "decision_supported": False,
                    "pool_status": "constrained_single_candidate",
                    "selection_rule": "descriptive_candidate_pool_no_tool_selection",
                    "narrowing_rule": "only_one_capacity_candidate_available",
                    "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
                    "items": [
                        {
                            "sleeper_player_id": "cut-1",
                            "full_name": "Cut Candidate",
                            "position": "WR",
                            "value_status": "valued",
                            "xvar_pct": 20.0,
                            "dvs": 40.0,
                            "capacity_conflict_status": "roster_capacity_pressure",
                            "rule_conflict_label": None,
                            "caveats": [],
                            "decision_supported": False,
                        }
                    ],
                    "caveats": [],
                },
            }
        ],
    }

    response = league_pulse_assembler.assemble_league_pulse(
        _team_posture(),
        _team_value(),
        opportunity_v2,
    )

    card = response.market_overlay_cards[0]
    assert hasattr(card, "roster_capacity_candidates")
    assert not hasattr(card, "recommended_drop")
    assert card.roster_capacity_candidates.items[0].sleeper_player_id == "cut-1"
    assert _decision_supported_true_count(response) == 0


def test_assembler_maps_stale_v1_recommended_drop_into_pool_shape() -> None:
    """Stale on-disk v1 artifacts keep League Pulse live during the T2/T3 migration."""
    opportunity_v1 = {
        "schema_version": "league_opportunity.v1",
        "captured_at": "2026-06-23T13:17:35+00:00",
        "perspective_roster_id": 1,
        "partner_rankings": [],
        "cards": [
            {
                "card_id": "opp-0001",
                "card_type": "WAIVER_CANDIDATE",
                "opportunity_score": 0.5,
                "rationale": {
                    "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
                    "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
                    "evidence": {
                        "signal": "MODEL_HIGH_MARKET_LOW",
                        "signal_status": "gates_passed",
                        "model_minus_market_delta": 0.25,
                        "xvar": 10.0,
                    },
                },
                "score_components": {
                    "fit_score": 0.4,
                    "divergence_score": 0.25,
                    "feasibility_score": 0.9,
                },
                "caveats": ["waiver_status_from_sleeper_snapshot"],
                "recommended_drop": {
                    "sleeper_player_id": "legacy-cut",
                    "full_name": "Legacy Cut",
                    "position": "WR",
                    "cut_priority": 1,
                    "ir_compliance_status": "NOT_ON_IR",
                    "cut_rationale": [],
                    "decision_supported": False,
                },
            }
        ],
    }

    response = league_pulse_assembler.assemble_league_pulse(
        _team_posture(),
        _team_value(),
        opportunity_v1,
    )

    pool = response.market_overlay_cards[0].roster_capacity_candidates
    assert pool.pool_status == "legacy_single_candidate"
    assert pool.selection_rule == "legacy_v1_field_migrated_no_tool_selection"
    assert pool.narrowing_rule == "stale_v1_artifact_compatibility"
    assert pool.items[0].sleeper_player_id == "legacy-cut"


def test_t2_shrinks_league_pulse_allowlist_for_recommended_tokens_in_touched_files() -> None:
    import scripts.scan_league_opportunity_no_verdict as scanner

    touched_paths = {
        "src/dynasty_genius/league_opportunity_map.py",
        "app/api/routes/league_pulse_models.py",
        "app/api/routes/league_pulse_assembler.py",
    }
    remaining = [
        entry
        for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
        if entry.path in touched_paths and "recommend" in entry.token.lower()
    ]
    assert remaining == []

    findings = scanner.scan_paths(
        [__import__("pathlib").Path(path) for path in touched_paths],
        allowlist=[
            entry
            for entry in scanner.KNOWN_DEBT_ALLOWLIST
            if not (entry.path in touched_paths and "recommend" in entry.token.lower())
        ],
    )
    assert [
        (finding.path, finding.token)
        for finding in findings
        if "recommend" in finding.token.lower()
    ] == []
