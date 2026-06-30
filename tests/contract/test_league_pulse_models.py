"""League Pulse Increment 1 T1 contract tests for typed DTOs and tokens."""

from __future__ import annotations

from importlib import import_module

import pytest
from pydantic import ValidationError


def _models():
    return import_module("app.api.routes.league_pulse_models")


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0


def test_response_dtos_lock_decision_supported_false_recursively() -> None:
    """Every League Pulse DTO coerces decision_supported=True to False."""
    m = _models()

    response = m.LeaguePulseResponse(
        status="active",
        perspective_roster_id=1,
        source_artifacts=m.LeaguePulseSources(
            team_posture={
                "schema_version": "team_posture.v1",
                "captured_at": "2026-05-24T17:19:56Z",
            },
            team_value_matrix={
                "schema_version": "team_value_matrix.v1",
                "captured_at": "2026-05-24T17:19:56Z",
            },
            league_opportunity={
                "schema_version": "league_opportunity.v1",
                "captured_at": "2026-05-24T17:19:59Z",
            },
            decision_supported=True,
        ),
        captured_at="2026-05-24T17:19:59Z",
        caveats=[],
        team_postures=[
            m.LeaguePulseTeamPosture(
                roster_id=1,
                team_name="David",
                posture_label="CONTENDER",
                score=0.7,
                components={"lineup": 0.8},
                caveats=[],
                decision_supported=True,
            )
        ],
        team_values=[
            m.LeaguePulseTeamValue(
                roster_id=1,
                team_name="David",
                value_views=m.LeaguePulseValueViews(
                    starter_weighted_xvar=42.0,
                    lineup_xvar=38.0,
                    depth_credit_xvar=4.0,
                    total_xvar_capped=46.0,
                    top_n_xvar=44.0,
                    decision_supported=True,
                ),
                age_profile={"weighted_age": 25.2},
                positional_summary={},
                future_picks={
                    "owned_count": 4,
                    "outgoing_count": 1,
                    "pick_value_status": "unvalued",
                },
                decision_supported=True,
            )
        ],
        partner_rankings=[
            m.LeaguePulsePartnerRanking(
                counterparty_roster_id=2,
                counterparty_team_name="Counterparty",
                partner_score=0.61,
                matched_positions=["WR"],
                score_components={"divergence_density_score": 0.3},
                evidence={"divergence_row_count": 2},
                decision_supported=True,
            )
        ],
        model_native_cards=[
            m.LeaguePulseCard(
                card_id="opp-0001",
                card_type="ROSTER_SURPLUS_DEFICIT_MATCH",
                evidence_status="evidence_gated",
                sort_key="positional_z_differential_desc",
                sort_value=2.2,
                rationale_primary="positional_surplus_match",
                rationale_secondary=["perspective_positional_deficit"],
                evidence={"position": "WR"},
                score_components={"fit_score": 0.4, "feasibility_score": 0.5},
                caveats=[],
                decision_supported=True,
            )
        ],
        market_overlay_cards=[
            m.LeaguePulseMarketCard(
                card_id="opp-0002",
                card_type="UNROSTERED_MODEL_MARKET_DIVERGENCE",
                evidence_status="evidence_complete",
                sort_key="absolute_model_market_delta_desc",
                sort_value=0.4,
                rationale_primary="opportunity_signal",
                rationale_secondary=["market_divergence_context"],
                evidence={"model_minus_market_delta": 0.4, "asset_xvar": 1.2},
                score_components={
                    "fit_score": 0.4,
                    "divergence_score": 0.7,
                    "feasibility_score": 0.9,
                },
                caveats=["market_overlay_unvalidated_divergence"],
                roster_capacity_candidates=m.LeaguePulseCapacityCandidatePool(
                    pool_status="constrained_single_candidate",
                    selection_rule="descriptive_candidate_pool_no_tool_selection",
                    narrowing_rule="only_one_capacity_candidate_available",
                    sort_key="xvar_pct_ascending_then_full_name_then_sleeper_player_id",
                    items=[
                        m.LeaguePulseCapacityCandidate(
                            sleeper_player_id="drop-1",
                            full_name="Drop Candidate",
                            position="WR",
                            value_status="valued",
                            xvar_pct=12.0,
                            dvs=30.0,
                            capacity_conflict_status="roster_capacity_pressure",
                            rule_conflict_label=None,
                            caveats=[],
                            decision_supported=True,
                        )
                    ],
                    caveats=[],
                    decision_supported=True,
                ),
                decision_supported=True,
            )
        ],
        card_section_counts=[
            m.LeaguePulseCardSectionCount(
                sort_key="absolute_model_market_delta_desc",
                total_count=5,
                shown_count=2,
                section_cap=2,
                decision_supported=True,
            )
        ],
        dropped=m.LeaguePulseDropCounts(
            team_postures=0,
            team_values=0,
            partner_rankings=0,
            model_native_cards=0,
            market_overlay_cards=0,
            roster_capacity_candidate_pools=0,
            decision_supported=True,
        ),
        decision_supported=True,
    )

    assert response.decision_supported is False
    assert _decision_supported_true_count(response) == 0


def test_value_views_forbid_market_overlay_total_and_extra_fields() -> None:
    """Value views must omit market_overlay_total by construction."""
    m = _models()

    valid = m.LeaguePulseValueViews(
        starter_weighted_xvar=1.0,
        lineup_xvar=2.0,
        depth_credit_xvar=3.0,
        total_xvar_capped=4.0,
        top_n_xvar=5.0,
    )

    dumped = valid.model_dump()
    assert "market_overlay_total" not in dumped

    with pytest.raises(ValidationError):
        m.LeaguePulseValueViews(
            starter_weighted_xvar=1.0,
            lineup_xvar=2.0,
            depth_credit_xvar=3.0,
            total_xvar_capped=4.0,
            top_n_xvar=5.0,
            market_overlay_total=999.0,
        )


def test_partner_ranking_is_always_market_influenced() -> None:
    """Partner rankings must force the market-influenced label."""
    m = _models()

    ranking = m.LeaguePulsePartnerRanking(
        counterparty_roster_id=2,
        counterparty_team_name="Counterparty",
        partner_score=0.4,
        matched_positions=["QB"],
        score_components={"divergence_density_score": 0.2},
        evidence={"counterparty_posture": "REBUILDING"},
        market_influenced=False,
    )

    assert ranking.market_influenced is True
    assert "partner_score_market_influenced" in ranking.caveats
    assert ranking.decision_supported is False


def test_model_native_card_rejects_market_overlay_fields() -> None:
    """Model-native cards expose only model-native score/evidence fields."""
    m = _models()

    clean = m.LeaguePulseCard(
        card_id="opp-0001",
        card_type="ROSTER_SURPLUS_DEFICIT_MATCH",
        evidence_status="evidence_gated",
        sort_key="positional_z_differential_desc",
        sort_value=2.2,
        rationale_primary="positional_surplus_match",
        rationale_secondary=["perspective_positional_deficit"],
        evidence={"position": "WR"},
        score_components={"fit_score": 0.4, "feasibility_score": 0.5},
        caveats=[],
    )
    assert "divergence_score" not in clean.score_components

    with pytest.raises(ValidationError):
        m.LeaguePulseCard(
            card_id="opp-0001",
            card_type="ROSTER_SURPLUS_DEFICIT_MATCH",
            evidence_status="evidence_gated",
            sort_key="positional_z_differential_desc",
            sort_value=2.2,
            rationale_primary="positional_surplus_match",
            rationale_secondary=[],
            evidence={"position": "WR", "market_percentile": 0.1},
            score_components={
                "fit_score": 0.4,
                "feasibility_score": 0.5,
                "divergence_score": 0.1,
            },
            caveats=[],
        )


def test_market_card_accepts_taxi_and_requires_overlay_caveat() -> None:
    """TAXI cards are overlay cards and must not be valid model-native cards."""
    m = _models()

    overlay = m.LeaguePulseMarketCard(
        card_id="opp-taxi",
        card_type="TAXI_LONG_TERM_VALUE_PRESENT",
        evidence_status="evidence_gated",
        sort_key="taxi_long_term_value_desc",
        sort_value=8.0,
        rationale_primary="taxi_long_term_value_present",
        rationale_secondary=["activation_cost_represented"],
        evidence={
            "raw_xvar": 8.0,
            "lineup_role": "taxi",
            "model_minus_market_delta": 0.4,
        },
        score_components={
            "fit_score": 0.32,
            "divergence_score": 0.4,
            "feasibility_score": 0.4,
        },
        caveats=["market_overlay_unvalidated_divergence"],
    )
    assert overlay.card_type == "TAXI_LONG_TERM_VALUE_PRESENT"

    # DTO backstop: an overlay card built WITHOUT the caveat still carries it
    # (forced like PartnerRanking.market_influenced) — the DTO is the
    # impenetrable label, not the mapper.
    overlay_no_caveat = m.LeaguePulseMarketCard(
        card_id="opp-waiver",
        card_type="UNROSTERED_MODEL_MARKET_DIVERGENCE",
        evidence_status="evidence_complete",
        sort_key="absolute_model_market_delta_desc",
        sort_value=0.3,
        rationale_primary="opportunity_signal",
        rationale_secondary=[],
        evidence={"model_minus_market_delta": 0.3, "asset_xvar": 1.0},
        score_components={"fit_score": 0.4, "divergence_score": 0.3, "feasibility_score": 0.9},
    )
    assert "market_overlay_unvalidated_divergence" in overlay_no_caveat.caveats

    with pytest.raises(ValidationError):
        m.LeaguePulseCard(
            card_id="opp-taxi",
            card_type="TAXI_LONG_TERM_VALUE_PRESENT",
            evidence_status="evidence_gated",
            sort_key="taxi_long_term_value_desc",
            sort_value=8.0,
            rationale_primary="taxi_long_term_value_present",
            rationale_secondary=["activation_cost_represented"],
            evidence={"model_minus_market_delta": 0.4},
            score_components={"fit_score": 0.32, "divergence_score": 0.4},
            caveats=[],
        )


def test_capacity_candidate_item_forbids_unknown_fields_and_forces_decision_supported() -> None:
    """The descriptive capacity-candidate item has its own typed fail-closed boundary."""
    m = _models()

    item = m.LeaguePulseCapacityCandidate(
        sleeper_player_id="drop-1",
        full_name="Drop Candidate",
        position="WR",
        value_status="valued",
        xvar_pct=12.0,
        dvs=30.0,
        capacity_conflict_status="hard_roster_rules_conflict",
        rule_conflict_label="IR compliance violation",
        caveats=["valuation_unavailable"],
        decision_supported=True,
    )

    assert item.decision_supported is False

    with pytest.raises(ValidationError):
        m.LeaguePulseCapacityCandidate(
            sleeper_player_id="drop-1",
            full_name="Drop Candidate",
            position="WR",
            value_status="valued",
            capacity_conflict_status="roster_capacity_pressure",
            market_value=100,
        )


def test_safe_tokens_cover_known_league_pulse_caveats_and_taxi_token() -> None:
    """SAFE_TOKENS must include current producer caveats, including TAXI."""
    m = _models()

    producer_tokens = {
        "phase17_non_decision_grade",
        "future_pick_values_deferred",
        "posture_unclassified",
        "phase18_heuristic_posture",
        "market_overlay_unvalidated_divergence",
        "waiver_status_from_sleeper_snapshot",
        "partner_score_market_influenced",
        "taxi_activation_cost_requires_manual_review",
        "evidence_suppressed_banned_term",
    }

    assert producer_tokens <= m.SAFE_TOKENS
    clean, caveats = m.validate_tokens(
        ["market_overlay_unvalidated_divergence", "target_this_manager"]
    )
    assert clean == ["market_overlay_unvalidated_divergence"]
    assert caveats == ["evidence_suppressed_banned_term"]


def test_rationale_token_labels_are_exhaustive_with_safe_fallback() -> None:
    """Raw rationale tokens must never pass through to the client."""
    m = _models()

    assert (
        m.neutral_label_for_token("UNROSTERED_MODEL_MARKET_ASYMMETRY")
        == "market_divergence_context"
    )
    assert (
        m.neutral_label_for_token("TAXI_LONG_TERM_VALUE_PRESENT")
        == "taxi_long_term_value_present"
    )
    assert (
        m.neutral_label_for_token("ACTIVATION_COST_REPRESENTED")
        == "activation_cost_represented"
    )
    assert m.neutral_label_for_token("URGENT_TARGET_FOR_CONTENDER") == "opportunity_signal"
    assert "TARGET" not in m.neutral_label_for_token("URGENT_TARGET_FOR_CONTENDER")

