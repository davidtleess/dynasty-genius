"""War Room #2 T2 RED: report emitter + structural current-context assembler.

T2 composes the T1 pure diff with allowlisted structural context. It is still
backend-only: no API and no frontend surface.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.api.routes.league_what_changed_models import WhatChangedResponse
from src.dynasty_genius.capture.fc_forward_capture_store import FCForwardCaptureStore
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
)
from src.dynasty_genius.what_changed.report import (
    assemble_structural_context,
    emit_daily_what_changed_report,
)

FC_SOURCE = "fc_native"
SETTINGS_HASH = "sf_ppr_12"
MODEL_SOURCE = MODEL_PVO_SOURCE
GENERATED_AT = datetime(2026, 6, 24, 13, 17, 30, tzinfo=timezone.utc)


def _fc_entry(
    *,
    snapshot_date: str,
    player_key: str,
    sleeper_id: str,
    player_name: str,
    position: str,
    value: int,
    overall_rank: int,
    position_rank: int,
) -> dict:
    return {
        "snapshot_date": snapshot_date,
        "source": FC_SOURCE,
        "settings_hash": SETTINGS_HASH,
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "player_name": player_name,
        "position": position,
        "value": value,
        "overall_rank": overall_rank,
        "position_rank": position_rank,
        "trend_30day": 0,
        "retrieved_at": f"{snapshot_date}T13:00:00+00:00",
        "payload_hash": f"{player_key}:{snapshot_date}:{value}",
        # Phase-0b: the store requires every entry to declare what its volatility
        # field means. These fixtures carry no volatility, which is `source_omitted`.
        "market_volatility": None,
        "market_volatility_status": "source_omitted",
    }


def _model_entry(*, capture_date: str, player_key: str, sleeper_id: str) -> dict:
    return {
        "capture_date": capture_date,
        "source": MODEL_SOURCE,
        "semantic_output_hash": "semantic-v1",
        "provenance_hash": "provenance-v1",
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player_name": "Bijan Robinson",
        "position": "RB",
        "engine_path": "ENGINE_B",
        "dynasty_value_score": 98.5,
        "dvs_pct": 99.2,
        "xvar": 21.4,
        "model_grade": "MODEL",
        "model_version": "engine_b_v2",
        "artifact_vintage": f"{capture_date}T14:00:00+00:00",
        "row_index": 0,
        "semantic_row_hash": f"row:{player_key}:98.5",
        "payload_hash": f"row:{player_key}:98.5",
    }


def _seed_fc_store(db_path: Path) -> None:
    store = FCForwardCaptureStore(db_path)
    store.append_entries(
        [
            _fc_entry(
                snapshot_date="2026-06-23",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                value=10000,
                overall_rank=5,
                position_rank=2,
            ),
            _fc_entry(
                snapshot_date="2026-06-23",
                player_key="sleeper:6786",
                sleeper_id="6786",
                player_name="CeeDee Lamb",
                position="WR",
                value=9000,
                overall_rank=4,
                position_rank=1,
            ),
        ]
    )
    store.append_entries(
        [
            _fc_entry(
                snapshot_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                value=10250,
                overall_rank=3,
                position_rank=1,
            ),
            _fc_entry(
                snapshot_date="2026-06-24",
                player_key="sleeper:6786",
                sleeper_id="6786",
                player_name="CeeDee Lamb",
                position="WR",
                value=8600,
                overall_rank=8,
                position_rank=3,
            ),
        ]
    )


def _seed_one_day_model_store(db_path: Path) -> None:
    ModelForwardCaptureStore(db_path).append_entries(
        [
            _model_entry(
                capture_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
            )
        ]
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def _fixture_paths(tmp_path: Path) -> dict[str, Path]:
    captured_at = "2026-06-23T13:17:30+00:00"
    valuation = tmp_path / "valuation"
    snapshots = tmp_path / "league_snapshots"

    sleeper_snapshot = _write_json(
        snapshots / "sleeper_universe_snapshot_latest.json",
        {
            "captured_at": captured_at,
            "david_roster_id": 1,
            "rosters": [
                {
                    "roster_id": 1,
                    "players": ["9509", "6786"],
                    "player_map": {"9509": {"full_name": "raw leak"}},
                },
                {"roster_id": 2, "players": ["9999"]},
            ],
            "players": {"9509": {"full_name": "raw player universe leak"}},
        },
    )
    team_posture = _write_json(
        valuation / "team_posture_latest.json",
        {
            "captured_at": captured_at,
            "decision_supported": False,
            "teams": [
                {
                    "roster_id": 1,
                    "owner": {
                        "display_name": "Dleess",
                        "team_name": "Woodbury Riders",
                        "user_id": "827345221493850112",
                    },
                    "posture": {
                        "label": "REBUILDING",
                        "score": -0.975,
                        "components": {"starter_weighted_xvar_z": -2.258},
                        "decision_supported": False,
                    },
                    "decision_supported": False,
                },
                {
                    "roster_id": 2,
                    "owner": {"team_name": "League Mate"},
                    "posture": {"label": "BALANCED", "score": 0.0},
                    "decision_supported": False,
                },
            ],
        },
    )
    team_value_matrix = _write_json(
        valuation / "team_value_matrix_latest.json",
        {
            "captured_at": captured_at,
            "teams": [
                {
                    "roster_id": 1,
                    "owner": {
                        "display_name": "Dleess",
                        "team_name": "Woodbury Riders",
                        "user_id": "827345221493850112",
                    },
                    "posture": {"label": "UNCLASSIFIED", "score": None},
                    "decision_supported": False,
                    "team_value_views": {
                        "depth_credit_xvar": 11.5,
                        "lineup_xvar": 88.25,
                        "starter_weighted_xvar": 72.0,
                        "top_n_xvar": 101.75,
                        "total_xvar_capped": 129.5,
                        "market_overlay_total": 9999.0,
                    },
                    "players": [{"full_name": "raw player leak"}],
                    "lineup": {"starters": ["raw lineup leak"]},
                }
            ],
        },
    )
    league_opportunity = _write_json(
        valuation / "league_opportunity_latest.json",
        {
            "captured_at": captured_at,
            "decision_supported": False,
            "partner_rankings": [
                {
                    "counterparty_roster_id": 2,
                    "counterparty_team_name": "League Mate",
                    "partner_score": 78.5,
                    "matched_positions": ["RB"],
                    "score_components": {"raw": "leak"},
                    "evidence": [{"raw": "leak"}],
                    "decision_supported": False,
                }
            ],
            "cards": [
                {
                    "card_id": "waiver-1",
                    "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                    "asset": {
                        "sleeper_player_id": "5857",
                        "full_name": "Noah Fant",
                        "position": "TE",
                    },
                    "roster_capacity_candidates": {
                        "pool_status": "available",
                        "items": [
                            {
                                "full_name": "AJ Barner",
                                "capacity_conflict_status": "roster_capacity_pressure",
                            }
                        ],
                    },
                    "rationale": ["raw rationale leak"],
                    "score_components": {"raw": "leak"},
                    "decision_supported": False,
                }
            ],
        },
    )
    roster_cut_report = _write_json(
        valuation / "roster_cut_report_latest.json",
        {
            "captured_at": captured_at,
            "roster_cut_report": {
                "roster_id": 1,
                "total_players": 30,
                "total_capacity": 28,
                "cuts_required": 2,
                "decision_supported": False,
                "cut_candidates": [
                    {
                        "sleeper_player_id": "6786",
                        "full_name": "CeeDee Lamb",
                        "position": "WR",
                        "cut_priority": 1,
                        "dvs": 91.2,
                        "xvar_pct": 97.0,
                        "cut_rationale": ["raw rationale leak"],
                        "decision_supported": False,
                    }
                ],
            },
        },
    )
    return {
        "sleeper_snapshot_path": sleeper_snapshot,
        "team_posture_path": team_posture,
        "team_value_matrix_path": team_value_matrix,
        "league_opportunity_path": league_opportunity,
        "roster_cut_report_path": roster_cut_report,
    }


def _real_shape_fixture_paths(tmp_path: Path) -> dict[str, Path]:
    """Structural fixture shaped like the live Phase-17/18 latest artifacts.

    The synthetic T2 fixtures used scalar owner/posture names and legacy xVAR keys.
    The real artifacts carry nested owner/posture objects, different xVAR view keys,
    and nested card player names under ``full_name``. This fixture intentionally
    mirrors those shapes so the report emitter is validated against the API DTO.
    """

    captured_at = "2026-06-23T13:17:30+00:00"
    valuation = tmp_path / "valuation"
    snapshots = tmp_path / "league_snapshots"

    sleeper_snapshot = _write_json(
        snapshots / "sleeper_universe_snapshot_latest.json",
        {
            "captured_at": captured_at,
            "david_roster_id": 1,
            "rosters": [
                {
                    "roster_id": 1,
                    "players": ["9509", "6786"],
                    "player_map": {"9509": {"full_name": "raw leak"}},
                },
                {"roster_id": 2, "players": ["9999"]},
            ],
            "players": {"9509": {"full_name": "raw player universe leak"}},
        },
    )
    team_posture = _write_json(
        valuation / "team_posture_latest.json",
        {
            "captured_at": captured_at,
            "decision_supported": False,
            "teams": [
                {
                    "roster_id": 1,
                    "owner": {
                        "display_name": "Dleess",
                        "team_name": "Woodbury Riders",
                        "user_id": "827345221493850112",
                    },
                    "posture": {
                        "label": "REBUILDING",
                        "score": -0.975,
                        "components": {"starter_weighted_xvar_z": -2.258},
                        "decision_supported": False,
                    },
                }
            ],
        },
    )
    team_value_matrix = _write_json(
        valuation / "team_value_matrix_latest.json",
        {
            "captured_at": captured_at,
            "teams": [
                {
                    "roster_id": 1,
                    "owner": {
                        "display_name": "Dleess",
                        "team_name": "Woodbury Riders",
                        "user_id": "827345221493850112",
                    },
                    "posture": {"label": "UNCLASSIFIED", "score": None},
                    "team_value_views": {
                        "depth_credit_xvar": 11.5,
                        "lineup_xvar": 88.25,
                        "starter_weighted_xvar": 72.0,
                        "top_n_xvar": 101.75,
                        "total_xvar_capped": 129.5,
                        "market_overlay_total": 9999.0,
                    },
                    "players": [{"full_name": "raw player leak"}],
                    "lineup": {"starters": ["raw lineup leak"]},
                }
            ],
        },
    )
    league_opportunity = _write_json(
        valuation / "league_opportunity_latest.json",
        {
            "captured_at": captured_at,
            "decision_supported": False,
            "partner_rankings": [
                {
                    "counterparty_roster_id": 2,
                    "counterparty_team_name": "League Mate",
                    "partner_score": 78.5,
                    "matched_positions": ["RB"],
                    "score_components": {"raw": "leak"},
                    "evidence": [{"raw": "leak"}],
                    "decision_supported": False,
                }
            ],
            "cards": [
                {
                    "card_id": "waiver-1",
                    "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                    "asset": {
                        "sleeper_player_id": "5857",
                        "full_name": "Noah Fant",
                        "position": "TE",
                    },
                    "roster_capacity_candidates": {
                        "pool_status": "available",
                        "items": [
                            {
                                "full_name": "AJ Barner",
                                "capacity_conflict_status": "roster_capacity_pressure",
                            }
                        ],
                    },
                    "rationale": ["raw rationale leak"],
                    "score_components": {"raw": "leak"},
                    "decision_supported": False,
                }
            ],
        },
    )
    roster_cut_report = _write_json(
        valuation / "roster_cut_report_latest.json",
        {
            "captured_at": captured_at,
            "roster_cut_report": {
                "roster_id": 1,
                "total_players": 30,
                "total_capacity": 28,
                "cuts_required": 2,
                "decision_supported": False,
                "cut_candidates": [
                    {
                        "sleeper_player_id": "6786",
                        "full_name": "CeeDee Lamb",
                        "position": "WR",
                        "cut_priority": 1,
                        "dvs": 91.2,
                        "xvar_pct": 97.0,
                        "cut_rationale": ["raw rationale leak"],
                        "decision_supported": False,
                    }
                ],
            },
        },
    )
    return {
        "sleeper_snapshot_path": sleeper_snapshot,
        "team_posture_path": team_posture,
        "team_value_matrix_path": team_value_matrix,
        "league_opportunity_path": league_opportunity,
        "roster_cut_report_path": roster_cut_report,
    }


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _assert_report_section_decision_supported_false(report: dict[str, Any]) -> None:
    """Every report section root must explicitly carry the non-decision marker."""
    assert report["decision_supported"] is False
    assert report["daily_diff"]["decision_supported"] is False
    assert report["daily_diff"]["market"]["decision_supported"] is False
    assert report["daily_diff"]["model"]["decision_supported"] is False
    assert report["structural_context"]["decision_supported"] is False
    for section in report["structural_context"]["sections"].values():
        assert section["decision_supported"] is False


def _assert_absent_keys_recursive(value: Any, forbidden: set[str]) -> None:
    if isinstance(value, dict):
        assert not (set(value) & forbidden)
        for nested in value.values():
            _assert_absent_keys_recursive(nested, forbidden)
    elif isinstance(value, list):
        for nested in value:
            _assert_absent_keys_recursive(nested, forbidden)


def _assert_all_structural_sections_are_current_not_delta(context: dict[str, Any]) -> None:
    assert context["current_not_delta"] is True
    for name, section in context["sections"].items():
        assert section["current_not_delta"] is True, name
        assert "comparison_window" not in section
        assert "deltas" not in section


def test_report_emitter_composes_diff_and_allowlisted_structural_context(
    tmp_path,
) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    report_path = tmp_path / "what_changed" / "what_changed_latest_report.json"
    paths = _fixture_paths(tmp_path)
    _seed_fc_store(fc_db)
    _seed_one_day_model_store(model_db)

    report_path.parent.mkdir(parents=True)
    report_path.write_text("{\"stale\": true}\n")

    report = emit_daily_what_changed_report(
        fc_db_path=fc_db,
        model_db_path=model_db,
        report_path=report_path,
        now_fn=lambda: GENERATED_AT,
        top_n=25,
        **paths,
    )

    assert json.loads(report_path.read_text()) == report
    assert "stale" not in report
    assert report["schema_version"] == "war_room_2_what_changed_v1"
    assert report["generated_at"] == "2026-06-24T13:17:30+00:00"
    assert report["decision_supported"] is False
    _assert_report_section_decision_supported_false(report)
    assert report["overall_status"] == "degraded"
    assert report["daily_diff"]["market"]["status"] == "ok"
    assert report["daily_diff"]["model"]["status"] == "insufficient_history"

    context = report["structural_context"]
    assert context["status"] == "ok"
    assert context["current_not_delta"] is True
    _assert_all_structural_sections_are_current_not_delta(context)

    posture = context["sections"]["team_posture"]
    assert posture == {
        "status": "ok",
        "decision_supported": False,
        "current_not_delta": True,
        "source_path": str(paths["team_posture_path"]),
        "captured_at": "2026-06-23T13:17:30+00:00",
        "staleness_caveat": {
            "basis": "captured_at_vs_report_generated_at",
            "report_generated_at": "2026-06-24T13:17:30+00:00",
            "age_hours": 24.0,
            "is_stale": True,
        },
        "david_roster_id": 1,
        "david_team_name": "Woodbury Riders",
        "david_posture": "REBUILDING",
        "team_count": 2,
    }

    team_value = context["sections"]["team_value"]
    assert team_value["david_value_summary"] == {
        "roster_id": 1,
        "team_name": "Woodbury Riders",
        "posture_label": "UNCLASSIFIED",
        "depth_credit_xvar": 11.5,
        "lineup_xvar": 88.25,
        "starter_weighted_xvar": 72.0,
        "top_n_xvar": 101.75,
        "total_xvar_capped": 129.5,
    }
    assert "market_overlay_total" not in team_value["david_value_summary"]

    opportunity = context["sections"]["league_opportunity"]
    assert opportunity["top_partner_rankings"] == [
        {
            "counterparty_roster_id": 2,
            "counterparty_team_name": "League Mate",
            "partner_score": 78.5,
            "matched_positions": ["RB"],
        }
    ]
    assert opportunity["top_cards"] == [
        {
            "card_id": "waiver-1",
            "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
            "asset_name": "Noah Fant",
            "roster_capacity_context": {
                "pool_status": "available",
                "candidate_count": 1,
                "hard_conflict_count": 0,
            },
        }
    ]

    drop_pressure = context["sections"]["drop_pressure"]
    assert drop_pressure["summary"] == {
        "roster_id": 1,
        "total_players": 30,
        "total_capacity": 28,
        "cuts_required": 2,
    }
    assert drop_pressure["top_candidates"] == [
        {
            "sleeper_player_id": "6786",
            "player_name": "CeeDee Lamb",
            "position": "WR",
            "cut_priority": 1,
            "dvs": 91.2,
            "xvar_pct": 97.0,
        }
    ]

    sleeper = context["sections"]["sleeper_snapshot"]
    assert sleeper["david_roster_id"] == 1
    assert sleeper["david_roster_player_count"] == 2
    assert sleeper["league_roster_count"] == 2

    _assert_decision_supported_false_recursive(report)
    _assert_absent_keys_recursive(
        context,
        {
            "players",
            "player_map",
            "lineup",
            "rosters",
            "cards",
            "partner_rankings",
            "evidence",
            "rationale",
            "score_components",
            "cut_rationale",
        },
    )


def test_structural_context_maps_real_phase_artifact_shapes_without_raw_objects(
    tmp_path,
) -> None:
    paths = _real_shape_fixture_paths(tmp_path)

    context = assemble_structural_context(
        team_posture_path=paths["team_posture_path"],
        team_value_matrix_path=paths["team_value_matrix_path"],
        league_opportunity_path=paths["league_opportunity_path"],
        roster_cut_report_path=paths["roster_cut_report_path"],
        sleeper_snapshot_path=paths["sleeper_snapshot_path"],
        generated_at=GENERATED_AT,
    )

    assert context["status"] == "ok"
    posture = context["sections"]["team_posture"]
    assert posture["david_team_name"] == "Woodbury Riders"
    assert posture["david_posture"] == "REBUILDING"

    team_value = context["sections"]["team_value"]
    assert team_value["david_value_summary"] == {
        "roster_id": 1,
        "team_name": "Woodbury Riders",
        "posture_label": "UNCLASSIFIED",
        "depth_credit_xvar": 11.5,
        "lineup_xvar": 88.25,
        "starter_weighted_xvar": 72.0,
        "top_n_xvar": 101.75,
        "total_xvar_capped": 129.5,
    }
    assert "market_overlay_total" not in team_value["david_value_summary"]

    opportunity = context["sections"]["league_opportunity"]
    assert opportunity["top_cards"] == [
        {
            "card_id": "waiver-1",
            "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
            "asset_name": "Noah Fant",
            "roster_capacity_context": {
                "pool_status": "available",
                "candidate_count": 1,
                "hard_conflict_count": 0,
            },
        }
    ]

    _assert_absent_keys_recursive(
        context,
        {
            "owner",
            "posture",
            "players",
            "player_map",
            "lineup",
            "rosters",
            "cards",
            "partner_rankings",
            "evidence",
            "rationale",
            "score_components",
            "cut_rationale",
            "components",
            "market_overlay_total",
        },
    )


def test_emitted_real_shape_report_validates_through_api_response_dto(
    tmp_path,
) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    report_path = tmp_path / "what_changed" / "what_changed_latest_report.json"
    paths = _real_shape_fixture_paths(tmp_path)
    _seed_fc_store(fc_db)
    _seed_one_day_model_store(model_db)

    report = emit_daily_what_changed_report(
        fc_db_path=fc_db,
        model_db_path=model_db,
        report_path=report_path,
        now_fn=lambda: GENERATED_AT,
        top_n=25,
        **paths,
    )

    validated = WhatChangedResponse.model_validate(report)
    assert validated.structural_context.sections.team_posture.david_team_name == (
        "Woodbury Riders"
    )
    assert validated.structural_context.sections.team_value.david_value_summary
    assert json.loads(report_path.read_text()) == report


def test_missing_structural_artifact_degrades_only_that_section(tmp_path) -> None:
    paths = _fixture_paths(tmp_path)
    missing_roster_cut = tmp_path / "valuation" / "missing_roster_cut.json"

    context = assemble_structural_context(
        team_posture_path=paths["team_posture_path"],
        team_value_matrix_path=paths["team_value_matrix_path"],
        league_opportunity_path=paths["league_opportunity_path"],
        roster_cut_report_path=missing_roster_cut,
        sleeper_snapshot_path=paths["sleeper_snapshot_path"],
        generated_at=GENERATED_AT,
    )

    assert context["status"] == "degraded"
    assert context["decision_supported"] is False
    assert context["sections"]["team_posture"]["status"] == "ok"
    assert context["sections"]["team_value"]["status"] == "ok"
    assert context["sections"]["league_opportunity"]["status"] == "ok"
    assert context["sections"]["sleeper_snapshot"]["status"] == "ok"
    assert context["sections"]["drop_pressure"] == {
        "status": "unavailable",
        "decision_supported": False,
        "current_not_delta": True,
        "source_path": str(missing_roster_cut),
        "aborted_reason": "missing_structural_artifact",
    }


def test_report_guardrails_banned_terms_and_no_model_market_keys(tmp_path) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    report_path = tmp_path / "what_changed_latest_report.json"
    paths = _fixture_paths(tmp_path)
    _seed_fc_store(fc_db)
    _seed_one_day_model_store(model_db)

    report = emit_daily_what_changed_report(
        fc_db_path=fc_db,
        model_db_path=model_db,
        report_path=report_path,
        now_fn=lambda: GENERATED_AT,
        top_n=25,
        **paths,
    )

    report_text = json.dumps(report, sort_keys=True).lower()
    for forbidden in (
        "buy",
        "sell",
        " win",
        " loss",
        "tiering",
        "tradeable edge",
    ):
        assert forbidden not in report_text

    model_text = json.dumps(report["daily_diff"]["model"], sort_keys=True).lower()
    for market_key in ("market_overlay", "divergence", "fantasycalc", "fc_native"):
        assert market_key not in model_text


def test_report_emitter_requires_injected_clock_and_paths(tmp_path) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    report_path = tmp_path / "what_changed_latest_report.json"
    paths = _fixture_paths(tmp_path)
    _seed_fc_store(fc_db)
    _seed_one_day_model_store(model_db)

    calls = 0

    def now_fn() -> datetime:
        nonlocal calls
        calls += 1
        return GENERATED_AT

    report = emit_daily_what_changed_report(
        fc_db_path=fc_db,
        model_db_path=model_db,
        report_path=report_path,
        now_fn=now_fn,
        top_n=1,
        **paths,
    )

    assert calls == 1
    assert report["daily_diff"]["market"]["total_movers_count"] == 2
    assert len(report["daily_diff"]["market"]["top_movers"]) == 1
    assert report_path.exists()
