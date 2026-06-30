"""Phase 1 T4a RED: backend section caps + What-Changed cleanup."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes import league_pulse_assembler, league_pulse_models
from app.main import app


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


def _market_row(sleeper_id: str, *, delta: float, xvar: float = 4.0) -> dict[str, Any]:
    return {
        "sleeper_player_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player": {"full_name": f"Market {sleeper_id}", "position": "WR"},
        "league_context": {
            "rostered": False,
            "roster_id": None,
            "on_taxi": False,
            "on_ir": False,
        },
        "valuation": {
            "engine_path": "ENGINE_B",
            "xvar": xvar,
            "decision_supported": False,
        },
        "divergence": {
            "signal": "MODEL_HIGH_MARKET_LOW",
            "signal_status": "gates_passed",
            "model_minus_market_delta": delta,
            "model_percentile": 0.75,
            "market_percentile": 0.50,
            "decision_supported": False,
        },
    }


def _minimal_artifacts(cards: list[dict[str, Any]], section_counts: list[dict[str, Any]]) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    posture = {
        "schema_version": "team_posture.v1",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "Team 1"},
                "posture": {"label": "BALANCED", "score": 0.0, "components": {}},
            }
        ],
    }
    value = {
        "schema_version": "team_value_matrix.v1",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [_team(1)],
    }
    opportunity = {
        "schema_version": "league_opportunity.v2",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "perspective_roster_id": 1,
        "partner_rankings": [],
        "cards": cards,
        "card_section_counts": section_counts,
        "decision_supported": False,
    }
    return posture, value, opportunity


def _decision_supported_true_count(value: object) -> int:
    if hasattr(value, "model_dump"):
        return _decision_supported_true_count(value.model_dump())
    if isinstance(value, dict):
        here = 1 if value.get("decision_supported") is True else 0
        return here + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_producer_caps_each_section_independently_and_emits_section_counts() -> None:
    from src.dynasty_genius import league_opportunity_map as producer

    team_matrix = {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-06-30T10:00:00+00:00",
        "teams": [
            _team(1, rb_z=-1.2),
            _team(
                2,
                rb_z=1.5,
                players=[
                    {
                        "sleeper_player_id": "rb-target",
                        "full_name": "Rostered RB",
                        "position": "RB",
                        "raw_xvar": 18.0,
                    }
                ],
            ),
        ],
    }
    market_divergence = {
        "schema_version": "market_divergence.v1",
        "league_id": "league",
        "players": [
            _market_row("waiver-1", delta=0.91),
            _market_row("waiver-2", delta=0.82),
            _market_row("waiver-3", delta=0.73),
            _market_row("waiver-4", delta=0.64),
            _market_row("waiver-5", delta=0.55),
        ],
    }

    result = producer.build_league_opportunity_map(
        team_matrix,
        market_divergence,
        perspective_roster_id=1,
        captured_at="2026-06-30T10:00:00+00:00",
        max_cards=2,
    )

    market_cards = [
        c for c in result["cards"] if c["sort_key"] == "absolute_model_market_delta_desc"
    ]
    fit_cards = [
        c for c in result["cards"] if c["sort_key"] == "positional_z_differential_desc"
    ]
    assert len(market_cards) == 2
    assert len(fit_cards) == 1
    assert [c["sort_value"] for c in market_cards] == [0.91, 0.82]
    assert fit_cards[0]["sort_value"] == 2.7

    assert result["card_section_counts"] == [
        {
            "sort_key": "absolute_model_market_delta_desc",
            "total_count": 5,
            "shown_count": 2,
            "section_cap": 2,
            "decision_supported": False,
        },
        {
            "sort_key": "positional_z_differential_desc",
            "total_count": 1,
            "shown_count": 1,
            "section_cap": 2,
            "decision_supported": False,
        },
    ]
    assert _decision_supported_true_count(result) == 0


def test_league_pulse_dto_assembler_and_openapi_expose_section_count_metadata() -> None:
    assert "card_section_counts" in league_pulse_models.LeaguePulseResponse.model_fields
    assert hasattr(league_pulse_models, "LeaguePulseCardSectionCount")

    raw_card = {
        "card_id": "opp-0001",
        "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
        "sort_key": "absolute_model_market_delta_desc",
        "sort_value": 0.91,
        "evidence_status": "evidence_complete",
        "rationale": {
            "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
            "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
            "evidence": {
                "signal": "MODEL_HIGH_MARKET_LOW",
                "evidence_status": "evidence_complete",
                "model_minus_market_delta": 0.91,
                "asset_xvar": 4.0,
            },
        },
        "score_components": {
            "fit_score": 0.4,
            "divergence_score": 0.91,
            "feasibility_score": 0.9,
        },
        "caveats": ["waiver_status_from_sleeper_snapshot"],
    }
    section_counts = [
        {
            "sort_key": "absolute_model_market_delta_desc",
            "total_count": 5,
            "shown_count": 2,
            "section_cap": 2,
            "decision_supported": False,
        }
    ]
    response = league_pulse_assembler.assemble_league_pulse(
        *_minimal_artifacts([raw_card], section_counts)
    )

    assert [row.model_dump() for row in response.card_section_counts] == section_counts
    assert _decision_supported_true_count(response) == 0

    schema = TestClient(app).get("/openapi.json").json()
    response_schema = schema["components"]["schemas"]["LeaguePulseResponse"]
    assert "card_section_counts" in response_schema["properties"]
    assert "card_section_counts" in response_schema["required"]
    assert "LeaguePulseCardSectionCount" in schema["components"]["schemas"]


def test_what_changed_replaces_dead_recommended_drop_name_with_capacity_context() -> None:
    from app.api.routes.league_what_changed_models import WhatChangedCard
    from src.dynasty_genius.what_changed.report import _build_league_opportunity_section

    assert "recommended_drop_name" not in WhatChangedCard.model_fields
    assert "roster_capacity_context" in WhatChangedCard.model_fields

    section = _build_league_opportunity_section(
        {
            "partner_rankings": [],
            "cards": [
                {
                    "card_id": "waiver-1",
                    "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                    "asset": {"full_name": "Noah Fant"},
                    "roster_capacity_candidates": {
                        "pool_status": "available",
                        "items": [
                            {
                                "full_name": "Do Not Surface Me",
                                "capacity_conflict_status": "roster_capacity_pressure",
                            },
                            {
                                "full_name": "Also Hidden",
                                "capacity_conflict_status": "hard_roster_rules_conflict",
                            },
                        ],
                    },
                }
            ],
        }
    )

    assert section["top_cards"] == [
        {
            "card_id": "waiver-1",
            "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
            "asset_name": "Noah Fant",
            "roster_capacity_context": {
                "pool_status": "available",
                "candidate_count": 2,
                "hard_conflict_count": 1,
            },
        }
    ]
    assert "Do Not Surface Me" not in str(section)
    assert _decision_supported_true_count(section) == 0

    schema = TestClient(app).get("/openapi.json").json()
    card_schema = schema["components"]["schemas"]["WhatChangedCard"]
    assert "recommended_drop_name" not in card_schema["properties"]
    assert "roster_capacity_context" in card_schema["properties"]


def test_t4a_shrinks_backend_recommended_drop_name_cordon_entries_only() -> None:
    import scripts.scan_league_opportunity_no_verdict as scanner

    backend_entries = {
        ("src/dynasty_genius/what_changed/report.py", "recommended_drop_name"),
        ("app/api/routes/league_what_changed_models.py", "recommended_drop_name"),
        ("frontend/openapi.json", "recommended_drop_name"),
    }
    current_lp_entries = {
        (entry.path, entry.token) for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
    }
    assert not (backend_entries & current_lp_entries)

    # FE codegen/render are explicitly T4b/T4c and remain tracked debt for now.
    assert {
        ("frontend/src/lib/api/types.gen.ts", "recommended_drop_name"),
        ("frontend/src/lib/api/zod.gen.ts", "recommended_drop_name"),
    } <= current_lp_entries

    findings = scanner.scan_paths(
        [
            Path("src/dynasty_genius/what_changed/report.py"),
            Path("app/api/routes/league_what_changed_models.py"),
            Path("frontend/openapi.json"),
        ],
        allowlist=scanner.KNOWN_DEBT_ALLOWLIST,
    )
    assert findings == []
