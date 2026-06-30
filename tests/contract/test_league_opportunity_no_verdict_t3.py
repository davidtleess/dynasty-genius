"""Phase 1 T3 RED: remove opportunity_score and expose transparent sorting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.api.routes import league_pulse_assembler, league_pulse_models


def _team(
    roster_id: int,
    *,
    rb_z: float = 0.0,
    wr_z: float = 0.0,
    players: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    z_values = {"QB": 0.0, "RB": rb_z, "WR": wr_z, "TE": 0.0}
    return {
        "schema_version": "team_value_matrix.v1",
        "roster_id": roster_id,
        "owner": {"team_name": f"Team {roster_id}"},
        "positional_summary": {
            position: {
                "z_score": z,
                "surplus_label": (
                    "surplus" if z >= 0.75 else "deficit" if z <= -0.75 else "neutral"
                ),
                "n_rostered": 2,
            }
            for position, z in z_values.items()
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
        "players": players or [],
        "decision_supported": False,
    }


def _market_row(
    sleeper_id: str,
    *,
    full_name: str,
    position: str,
    roster_id: int | None,
    delta: float,
    xvar: float,
    signal_status: str = "gates_passed",
    signal: str = "MODEL_HIGH_MARKET_LOW",
) -> dict[str, Any]:
    return {
        "sleeper_player_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player": {"full_name": full_name, "position": position},
        "league_context": {
            "rostered": roster_id is not None,
            "roster_id": roster_id,
            "on_taxi": False,
            "on_ir": False,
        },
        "valuation": {
            "engine_path": "ENGINE_B",
            "xvar": xvar,
            "decision_supported": False,
        },
        "divergence": {
            "signal": signal,
            "signal_status": signal_status,
            "model_minus_market_delta": delta,
            "model_percentile": 0.75,
            "market_percentile": 0.50,
            "decision_supported": False,
        },
    }


def _opportunity_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    team_matrix = {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [
            _team(1, rb_z=-1.0, wr_z=-1.5),
            _team(
                2,
                rb_z=1.5,
                wr_z=0.9,
                players=[
                    {
                        "sleeper_player_id": "rb-target",
                        "full_name": "Rostered RB",
                        "position": "RB",
                        "raw_xvar": 18.0,
                    }
                ],
            ),
            _team(3, wr_z=1.8),
        ],
    }
    market_divergence = {
        "schema_version": "market_divergence.v1",
        "league_id": "league",
        "players": [
            _market_row(
                "waiver-high-delta-low-value",
                full_name="High Delta Low Value",
                position="WR",
                roster_id=None,
                delta=0.95,
                xvar=0.2,
            ),
            _market_row(
                "waiver-low-delta-high-value",
                full_name="Low Delta High Value",
                position="WR",
                roster_id=None,
                delta=0.30,
                xvar=24.0,
            ),
            _market_row(
                "rostered-gated",
                full_name="Rostered Gated",
                position="RB",
                roster_id=2,
                delta=0.50,
                xvar=15.0,
                signal_status="gates_blocked",
            ),
            _market_row(
                "rostered-unavailable",
                full_name="Rostered Unavailable",
                position="RB",
                roster_id=2,
                delta=0.40,
                xvar=13.0,
                signal_status="unavailable",
            ),
        ],
    }
    return team_matrix, market_divergence


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_producer_drops_composite_score_and_exposes_transparent_sort_fields() -> None:
    from src.dynasty_genius import league_opportunity_map as producer

    team_matrix, market_divergence = _opportunity_inputs()
    result = producer.build_league_opportunity_map(
        team_matrix,
        market_divergence,
        perspective_roster_id=1,
        captured_at="2026-06-30T10:00:00+00:00",
        max_cards=20,
    )

    assert result["schema_version"] == "league_opportunity.v2"
    assert all("opportunity_score" not in card for card in result["cards"])
    assert all("signal_status" not in card for card in result["cards"])
    assert {card["evidence_status"] for card in result["cards"]} >= {
        "evidence_complete",
        "evidence_gated",
        "inputs_unavailable",
    }
    assert _decision_supported_true_count(result) == 0

    high_delta = next(
        c
        for c in result["cards"]
        if (c.get("asset") or {}).get("sleeper_player_id") == "waiver-high-delta-low-value"
    )
    low_delta = next(
        c
        for c in result["cards"]
        if (c.get("asset") or {}).get("sleeper_player_id") == "waiver-low-delta-high-value"
    )
    assert high_delta["card_type"] == "UNROSTERED_MODEL_MARKET_DIVERGENCE"
    assert high_delta["sort_key"] == "absolute_model_market_delta_desc"
    assert high_delta["sort_value"] == 0.95
    assert high_delta["rationale"]["evidence"]["model_minus_market_delta"] == 0.95
    assert high_delta["rationale"]["evidence"]["asset_xvar"] == 0.2
    assert low_delta["rationale"]["evidence"]["model_minus_market_delta"] == 0.30
    assert low_delta["rationale"]["evidence"]["asset_xvar"] == 24.0

    market_cards = [
        c
        for c in result["cards"]
        if c["sort_key"] == "absolute_model_market_delta_desc"
    ]
    assert [c["sort_value"] for c in market_cards] == sorted(
        [c["sort_value"] for c in market_cards],
        reverse=True,
    )


def test_roster_fit_cards_sort_by_positional_differential_not_composite_blend() -> None:
    from src.dynasty_genius import league_opportunity_map as producer

    team_matrix, market_divergence = _opportunity_inputs()
    result = producer.build_league_opportunity_map(
        team_matrix,
        market_divergence,
        perspective_roster_id=1,
        captured_at="2026-06-30T10:00:00+00:00",
        max_cards=20,
    )

    fit_cards = [
        c for c in result["cards"] if c["card_type"] == "ROSTER_SURPLUS_DEFICIT_MATCH"
    ]
    assert fit_cards
    assert {c["sort_key"] for c in fit_cards} == {"positional_z_differential_desc"}
    assert [c["sort_value"] for c in fit_cards] == sorted(
        [c["sort_value"] for c in fit_cards],
        reverse=True,
    )
    for card in fit_cards:
        evidence = card["rationale"]["evidence"]
        expected = abs(evidence["perspective_position_z"]) + evidence["counterparty_position_z"]
        assert card["sort_value"] == round(expected, 3)
        assert evidence["positional_z_differential"] == card["sort_value"]


def test_dto_and_assembler_accept_new_contract_and_reject_old_score_field() -> None:
    assert "opportunity_score" not in league_pulse_models.LeaguePulseCard.model_fields
    assert "opportunity_score" not in league_pulse_models.LeaguePulseMarketCard.model_fields
    assert "evidence_status" in league_pulse_models.LeaguePulseCard.model_fields
    assert "sort_key" in league_pulse_models.LeaguePulseMarketCard.model_fields
    assert "sort_value" in league_pulse_models.LeaguePulseMarketCard.model_fields

    raw = {
        "card_id": "opp-0001",
        "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
        "sort_key": "absolute_model_market_delta_desc",
        "sort_value": 0.95,
        "evidence_status": "evidence_complete",
        "opportunity_score": 0.99,
        "rationale": {
            "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
            "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
            "evidence": {
                "signal": "MODEL_HIGH_MARKET_LOW",
                "evidence_status": "evidence_complete",
                "model_minus_market_delta": 0.95,
                "asset_xvar": 0.2,
            },
        },
        "score_components": {
            "fit_score": 0.4,
            "divergence_score": 0.95,
            "feasibility_score": 0.9,
        },
        "caveats": ["waiver_status_from_sleeper_snapshot"],
    }

    lane, card = league_pulse_assembler.map_card(raw)

    assert lane == "market_overlay_cards"
    assert card.card_type == "UNROSTERED_MODEL_MARKET_DIVERGENCE"
    assert card.sort_key == "absolute_model_market_delta_desc"
    assert card.sort_value == 0.95
    assert card.evidence_status == "evidence_complete"
    assert "opportunity_score" not in card.model_dump()


# RETIRED AT T4c: test_assembler_maps_stale_v1_card_types_and_scores_to_v2_dto_shape
# exercised map_card's normalization of legacy v1 card types/scores via the
# league_pulse_v1_compat shim, which T4c deleted (map_card is now v2-only). The
# replacement guard — stale v1 fails closed — lives in
# tests/contract/test_league_opportunity_no_verdict_t4c.py
# (test_t4c_assembler_is_v2_only_and_stale_v1_fails_closed).


def test_t3_shrinks_cordon_for_backend_openapi_score_and_candidate_enum_debt() -> None:
    import scripts.scan_league_opportunity_no_verdict as scanner

    t3_paths = {
        "src/dynasty_genius/league_opportunity_map.py",
        "app/api/routes/league_pulse_models.py",
        "app/api/routes/league_pulse_assembler.py",
        "frontend/openapi.json",
    }
    removed_tokens = {
        "opportunity_score",
        "WAIVER_CANDIDATE",
        "TAXI_ACTIVATION_CANDIDATE",
    }
    stale_entries = [
        entry
        for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
        if entry.path in t3_paths and entry.token in removed_tokens
    ]
    assert stale_entries == []

    findings = scanner.scan_paths(
        [Path(path) for path in t3_paths],
        allowlist=scanner.KNOWN_DEBT_ALLOWLIST,
    )
    assert findings == []
