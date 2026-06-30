"""League Pulse Increment 1 T2 contract tests for mappers + assembler."""

from __future__ import annotations

from importlib import import_module

import pytest


def _assembler():
    return import_module("app.api.routes.league_pulse_assembler")


def _posture_artifact(*, schema_version: str = "team_posture.v1") -> dict:
    return {
        "schema_version": schema_version,
        "captured_at": "2026-05-24T17:19:56Z",
        "source_artifacts": {"team_posture": "fixture"},
        "league_id": "league-1",
        "decision_supported": False,
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "David"},
                "posture": {
                    "label": "CONTENDER",
                    "score": 0.75,
                    "components": {"lineup": 0.8},
                    "caveats": ["phase18_heuristic_posture"],
                    "decision_supported": True,
                },
            },
            {
                "roster_id": 2,
                "owner": {"team_name": "Counterparty"},
                "posture": {
                    "label": "REBUILDING",
                    "score": -0.55,
                    "components": {"lineup": -0.5},
                    "caveats": [],
                    "decision_supported": False,
                },
            },
        ],
    }


def _value_team(roster_id: int, team_name: str) -> dict:
    return {
        "roster_id": roster_id,
        "owner": {"team_name": team_name},
        "team_value_views": {
            "starter_weighted_xvar": 42.0,
            "lineup_xvar": 38.0,
            "depth_credit_xvar": 4.0,
            "total_xvar_capped": 46.0,
            "top_n_xvar": 44.0,
            "market_overlay_total": 9999.0,
        },
        "age_profile": {"weighted_age": 25.3},
        "positional_summary": {"WR": {"z_score": 1.1, "surplus_label": "surplus"}},
        "future_picks": {"owned_count": 4, "outgoing_count": 1, "pick_value_status": "unvalued"},
        "players": [{"full_name": "Must Not Leak", "market_value": 123}],
    }


def _value_artifact(*, schema_version: str = "team_value_matrix.v1") -> dict:
    return {
        "schema_version": schema_version,
        "captured_at": "2026-05-24T17:19:56Z",
        "league_id": "league-1",
        "teams": [_value_team(1, "David"), _value_team(2, "Counterparty")],
    }


def _roster_card(**overrides: object) -> dict:
    card = {
        "card_id": "opp-roster",
        "card_type": "ROSTER_SURPLUS_DEFICIT_MATCH",
        "evidence_status": "evidence_gated",
        "sort_key": "positional_z_differential_desc",
        "sort_value": 2.2,
        "rationale": {
            "primary": "POSITIONAL_SURPLUS_ON_COUNTERPARTY",
            "secondary": ["PERSPECTIVE_POSITIONAL_DEFICIT"],
            "evidence": {
                "position": "WR",
                "perspective_position_z": -1.0,
                "counterparty_position_z": 1.2,
                "positional_z_differential": 2.2,
                "perspective_surplus_label": "deficit",
                "counterparty_surplus_label": "surplus",
            },
        },
        "score_components": {
            "fit_score": 0.5,
            "divergence_score": 0.0,
            "feasibility_score": 0.5,
        },
        "caveats": ["future_pick_values_deferred"],
        "decision_supported": True,
    }
    card.update(overrides)
    return card


def _waiver_card(**overrides: object) -> dict:
    card = {
        "card_id": "opp-waiver",
        "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
        "evidence_status": "evidence_complete",
        "sort_key": "absolute_model_market_delta_desc",
        "sort_value": 0.4,
        "rationale": {
            "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
            "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
            "evidence": {
                "signal": "MODEL_HIGH_MARKET_LOW",
                "evidence_status": "evidence_complete",
                "model_minus_market_delta": 0.4,
                "asset_xvar": 1.2,
            },
        },
        "score_components": {
            "fit_score": 0.4,
            "divergence_score": 0.7,
            "feasibility_score": 0.9,
        },
        "roster_capacity_candidates": {
            "decision_supported": True,
            "pool_status": "constrained_single_candidate",
            "selection_rule": "descriptive_candidate_pool_no_tool_selection",
            "narrowing_rule": "only_one_capacity_candidate_available",
            "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
            "items": [
                {
                    "sleeper_player_id": "drop-1",
                    "full_name": "Drop Candidate",
                    "position": "WR",
                    "value_status": "valued",
                    "xvar_pct": 12.0,
                    "dvs": 30.0,
                    "capacity_conflict_status": "hard_roster_rules_conflict",
                    "rule_conflict_label": "IR compliance violation",
                    "caveats": [],
                    "decision_supported": True,
                    "market_value": 123,
                }
            ],
            "caveats": [],
        },
        "caveats": ["waiver_status_from_sleeper_snapshot"],
        "decision_supported": False,
    }
    card.update(overrides)
    return card


def _taxi_card() -> dict:
    return {
        "card_id": "opp-taxi",
        "card_type": "TAXI_LONG_TERM_VALUE_PRESENT",
        "evidence_status": "evidence_gated",
        "sort_key": "taxi_long_term_value_desc",
        "sort_value": 8.0,
        "rationale": {
            "primary": "TAXI_LONG_TERM_VALUE_PRESENT",
            "secondary": ["ACTIVATION_COST_REPRESENTED", "URGENT_TARGET_FOR_CONTENDER"],
            "evidence": {
                "raw_xvar": 8.0,
                "lineup_role": "taxi",
                "signal": "MODEL_HIGH_MARKET_LOW",
                "model_minus_market_delta": 0.35,
            },
        },
        "score_components": {
            "fit_score": 0.32,
            "divergence_score": 0.35,
            "feasibility_score": 0.4,
        },
        "caveats": ["taxi_activation_cost_requires_manual_review"],
        "decision_supported": False,
    }


def _opportunity_artifact(*, schema_version: str = "league_opportunity.v2") -> dict:
    return {
        "schema_version": schema_version,
        "captured_at": "2026-05-24T17:19:59Z",
        "source_artifacts": {"league_opportunity": "fixture"},
        "league_id": "league-1",
        "perspective_roster_id": 1,
        "decision_supported": False,
        "partner_rankings": [
            {
                "counterparty_roster_id": 2,
                "counterparty_team_name": "Counterparty",
                "partner_score": 0.61,
                "matched_positions": ["WR"],
                "score_components": {"divergence_density_score": 0.3},
                "evidence": {"divergence_row_count": 2, "counterparty_posture": "REBUILDING"},
                "decision_supported": True,
            }
        ],
        "cards": [_roster_card(), _waiver_card(), _taxi_card()],
    }


def test_team_value_mapper_suppresses_market_overlay_total_and_raw_players() -> None:
    m = _assembler()
    raw = _value_team(1, "David")

    mapped = m.map_team_value(raw)
    dumped = mapped.model_dump()

    assert mapped.roster_id == 1
    assert "market_overlay_total" not in dumped["value_views"]
    assert "players" not in dumped
    assert "Must Not Leak" not in str(dumped)


def test_card_mapper_routes_and_sanitizes_model_native_and_overlay_cards() -> None:
    m = _assembler()

    model_lane, model_card = m.map_card(_roster_card())
    overlay_lane, overlay_card = m.map_card(_waiver_card())
    taxi_lane, taxi_card = m.map_card(_taxi_card())

    assert model_lane == "model_native_cards"
    assert model_card.card_type == "ROSTER_SURPLUS_DEFICIT_MATCH"
    assert "divergence_score" not in model_card.score_components
    assert model_card.rationale_primary == "opportunity_signal"
    assert model_card.decision_supported is False

    assert overlay_lane == "market_overlay_cards"
    assert overlay_card.card_type == "UNROSTERED_MODEL_MARKET_DIVERGENCE"
    assert overlay_card.rationale_primary == "market_divergence_context"
    assert "market_overlay_unvalidated_divergence" in overlay_card.caveats
    assert overlay_card.roster_capacity_candidates is not None
    pool = overlay_card.roster_capacity_candidates
    assert pool.pool_status == "constrained_single_candidate"
    assert pool.selection_rule == "descriptive_candidate_pool_no_tool_selection"
    assert pool.decision_supported is False
    assert pool.items[0].sleeper_player_id == "drop-1"
    assert pool.items[0].decision_supported is False
    # Allowlist-select drops the non-schema market_value key (no leak).
    assert "market_value" not in pool.items[0].model_dump()

    assert taxi_lane == "market_overlay_cards"
    assert taxi_card.card_type == "TAXI_LONG_TERM_VALUE_PRESENT"
    assert taxi_card.rationale_primary == "taxi_long_term_value_present"
    assert taxi_card.rationale_secondary == [
        "activation_cost_represented",
        "opportunity_signal",
    ]
    assert "taxi_activation_cost_requires_manual_review" in taxi_card.caveats


def test_mapper_caveats_are_safe_token_filtered() -> None:
    """Posture/card caveat arrays route through validate_tokens (no raw banned tokens)."""
    m = _assembler()

    posture = m.map_team_posture(
        {
            "roster_id": 1,
            "owner": {"team_name": "David"},
            "posture": {
                "label": "CONTENDER",
                "score": 0.5,
                "components": {},
                "caveats": ["phase18_heuristic_posture", "BUY_NOW", "totally_unknown"],
            },
        }
    )
    assert posture.caveats == [
        "phase18_heuristic_posture",
        "evidence_suppressed_banned_term",
    ]

    lane, card = m.map_card(
        _roster_card(
            caveats=["future_pick_values_deferred", "SELL_NOW", "totally_unknown"]
        )
    )
    assert lane == "model_native_cards"
    assert "SELL_NOW" not in card.caveats
    assert "totally_unknown" not in card.caveats
    assert card.caveats == [
        "future_pick_values_deferred",
        "evidence_suppressed_banned_term",
    ]


def test_model_native_card_with_market_leak_or_nonzero_divergence_drops() -> None:
    m = _assembler()
    market_leak = _roster_card()
    market_leak["rationale"]["evidence"]["market_percentile"] = 0.2
    nonzero_divergence = _roster_card(
        score_components={"fit_score": 0.5, "divergence_score": 0.1, "feasibility_score": 0.5}
    )

    assert m.map_card(market_leak) is None
    assert m.map_card(nonzero_divergence) is None
    assert m.map_card({"card_id": "bad", "card_type": "UNKNOWN"}) is None


def test_assembler_valid_nominal_degrades_for_stale_artifact_state_only() -> None:
    m = _assembler()

    response = m.assemble_league_pulse(
        _posture_artifact(),
        _value_artifact(),
        _opportunity_artifact(),
    )
    dumped = response.model_dump()

    assert response.status == "degraded"
    assert response.perspective_roster_id == 1
    assert response.source_artifacts.team_posture["schema_version"] == "team_posture.v1"
    assert response.captured_at == "2026-05-24T17:19:59Z"
    assert "league_pulse_artifact_state_2026-05-24" in response.caveats
    assert len(response.team_postures) == 2
    assert len(response.team_values) == 2
    assert len(response.partner_rankings) == 1
    assert len(response.model_native_cards) == 1
    assert len(response.market_overlay_cards) == 2
    assert response.dropped.model_native_cards == 0
    assert "market_overlay_total" not in str(dumped)
    assert "Must Not Leak" not in str(dumped)
    assert _decision_supported_true_count(dumped) == 0


def test_assembler_isolated_bad_records_drop_and_degrade() -> None:
    m = _assembler()
    opportunity = _opportunity_artifact()
    bad_roster = _roster_card()
    bad_roster["score_components"]["divergence_score"] = 0.4
    opportunity["cards"] = [_roster_card(), bad_roster, {"card_type": "UNKNOWN"}]
    opportunity["partner_rankings"].append(
        {
            "counterparty_roster_id": 999,
            "counterparty_team_name": "Unknown",
            "partner_score": 0.1,
            "matched_positions": [],
            "score_components": {},
            "evidence": {},
        }
    )

    response = m.assemble_league_pulse(
        _posture_artifact(),
        _value_artifact(),
        opportunity,
    )

    assert response.status == "degraded"
    assert len(response.model_native_cards) == 1
    assert response.dropped.model_native_cards == 2
    assert response.dropped.partner_rankings == 1


@pytest.mark.parametrize(
    ("posture_version", "value_version", "opportunity_version"),
    [
        ("wrong", "team_value_matrix.v1", "league_opportunity.v2"),
        ("team_posture.v1", "wrong", "league_opportunity.v2"),
        ("team_posture.v1", "team_value_matrix.v1", "wrong"),
    ],
)
def test_assembler_schema_version_mismatch_is_systemic_503(
    posture_version: str,
    value_version: str,
    opportunity_version: str,
) -> None:
    m = _assembler()

    with pytest.raises(m.LeaguePulseDependencyError):
        m.assemble_league_pulse(
            _posture_artifact(schema_version=posture_version),
            _value_artifact(schema_version=value_version),
            _opportunity_artifact(schema_version=opportunity_version),
        )


def test_assembler_total_required_section_failure_is_systemic_503() -> None:
    m = _assembler()
    value = _value_artifact()
    value["teams"] = [{"roster_id": 1, "owner": {"team_name": "Bad"}}]

    with pytest.raises(m.LeaguePulseDependencyError):
        m.assemble_league_pulse(_posture_artifact(), value, _opportunity_artifact())


def test_assembler_total_join_failure_is_systemic_503() -> None:
    m = _assembler()
    posture = _posture_artifact()
    value = _value_artifact()
    opportunity = _opportunity_artifact()
    for team in posture["teams"]:
        team["roster_id"] += 100
    for team in value["teams"]:
        team["roster_id"] += 200
    for ranking in opportunity["partner_rankings"]:
        ranking["counterparty_roster_id"] += 300

    with pytest.raises(m.LeaguePulseDependencyError):
        m.assemble_league_pulse(posture, value, opportunity)


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(item) for item in value)
    return 0
