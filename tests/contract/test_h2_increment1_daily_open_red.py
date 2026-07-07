from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.routes.league_what_changed_models import (
    WhatChangedMarketDelta,
    WhatChangedModelDelta,
    WhatChangedResponse,
)
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
)
from src.dynasty_genius.what_changed.report import emit_daily_what_changed_report

from .test_daily_what_changed_report import (
    _fixture_paths,
    _seed_fc_store,
    _write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_COLORS_JSON = REPO_ROOT / "app" / "config" / "team_colors.json"
TEAM_COLOR_GENERATOR = REPO_ROOT / "scripts" / "generate_team_color_module.py"
TEAM_COLOR_MODULE = REPO_ROOT / "frontend" / "src" / "generated" / "teamColors.ts"

GENERATED_AT = datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)


def _canonical_team_color_sha() -> str:
    payload = json.loads(TEAM_COLORS_JSON.read_text(encoding="utf-8"))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_team_color_generated_module_has_drift_gate_and_no_runtime_json_import() -> None:
    assert TEAM_COLOR_GENERATOR.exists(), (
        "Increment 1 requires scripts/generate_team_color_module.py as the single "
        "regeneration path for frontend team-color data."
    )
    assert TEAM_COLOR_MODULE.exists(), (
        "Increment 1 requires committed frontend/src/generated/teamColors.ts output."
    )

    text = TEAM_COLOR_MODULE.read_text(encoding="utf-8")
    assert "schema_version" in text
    assert "team_colors.v1" in text
    assert "source_sha256" in text
    assert _canonical_team_color_sha() in text
    assert "team_colors.json" not in text
    assert re.search(r"export const TEAM_COLORS\b", text)


def test_what_changed_delta_dtos_accept_increment1_optional_row_fields() -> None:
    series = {
        "basis": "fc_forward_capture_joinable.value",
        "points": [
            {"date": "2026-07-05", "value": 100.0},
            {"date": "2026-07-06", "value": 108.0},
        ],
    }
    market = WhatChangedMarketDelta.model_validate(
        {
            "sleeper_id": "9509",
            "player_key": "sleeper:9509",
            "player_name": "Bijan Robinson",
            "position": "RB",
            "team_id": "ATL",
            "market_series": series,
            "model_series": None,
            "value_delta": 8,
            "value_delta_direction": "rose",
            "overall_rank_delta": -2,
            "overall_rank_delta_direction": "improved",
            "position_rank_delta": -1,
            "position_rank_delta_direction": "improved",
        }
    )
    assert market.team_id == "ATL"
    assert market.market_series == series
    assert market.model_series is None

    model = WhatChangedModelDelta.model_validate(
        {
            "sleeper_id": "9509",
            "player_key": "sleeper:9509",
            "player_name": "Bijan Robinson",
            "position": "RB",
            "team_id": "ATL",
            "model_series": {
                "basis": "model_forward_capture_joinable.dynasty_value_score",
                "points": [
                    {"date": "2026-07-05", "value": 96.0},
                    {"date": "2026-07-06", "value": 98.5},
                ],
            },
            "market_series": None,
            "dynasty_value_score_delta": 2.5,
            "dynasty_value_score_delta_direction": "rose",
            "dvs_pct_delta": 0.02,
            "xvar_delta": 0.7,
        }
    )
    assert model.team_id == "ATL"
    assert model.model_series["points"][-1]["date"] == "2026-07-06"


def test_what_changed_series_schema_rejects_structurally_malformed_points() -> None:
    # Intrinsic series checks (shape, ordering, count, numeric) are enforced at
    # the field level and hold regardless of when validation runs — no wall-clock.
    base = {
        "sleeper_id": "9509",
        "player_key": "sleeper:9509",
        "player_name": "Bijan Robinson",
        "position": "RB",
        "value_delta": 8,
        "value_delta_direction": "rose",
        "overall_rank_delta": -2,
        "overall_rank_delta_direction": "improved",
        "position_rank_delta": -1,
        "position_rank_delta_direction": "improved",
    }

    for bad_series in [
        {"basis": "fc", "points": [{"date": "2026-07-06", "value": 1.0}]},
        {
            "basis": "fc",
            "points": [
                {"date": "2026-07-06", "value": 1.0},
                {"date": "2026-07-05", "value": 2.0},
            ],
        },
        {"basis": "", "points": [{"date": "2026-07-05", "value": 1.0}] * 31},
    ]:
        with pytest.raises(ValidationError):
            WhatChangedMarketDelta.model_validate({**base, "market_series": bad_series})


def _minimal_response_with_market_series(
    *, generated_at: str, series: dict[str, Any]
) -> dict[str, Any]:
    """A valid What-Changed payload carrying one market roster delta + series."""
    return {
        "schema_version": "war_room_2_what_changed_v1",
        "generated_at": generated_at,
        "decision_supported": False,
        "overall_status": "ok",
        "daily_diff": {
            "decision_supported": False,
            "overall_status": "ok",
            "market": {
                "status": "ok",
                "decision_supported": False,
                "market_source": "fantasycalc_overlay",
                "roster_deltas": [
                    {
                        "sleeper_id": "9509",
                        "player_key": "sleeper:9509",
                        "market_series": series,
                        "value_delta": 8,
                        "value_delta_direction": "rose",
                        "overall_rank_delta": -2,
                        "overall_rank_delta_direction": "improved",
                        "position_rank_delta": -1,
                        "position_rank_delta_direction": "improved",
                    }
                ],
                "top_movers": [],
                "entered": [],
                "exited": [],
            },
            "model": {
                "status": "baseline_holding",
                "decision_supported": False,
                "comparison_window": {"status": "insufficient_history"},
                "deltas": [],
            },
        },
        "structural_context": {
            "status": "ok",
            "decision_supported": False,
            "current_not_delta": True,
            "sections": {
                name: {
                    "status": "ok",
                    "decision_supported": False,
                    "current_not_delta": True,
                }
                for name in (
                    "team_posture",
                    "team_value",
                    "league_opportunity",
                    "drop_pressure",
                    "sleeper_snapshot",
                )
            },
        },
    }


def test_series_hard_right_edge_is_anchored_on_report_date_not_wall_clock() -> None:
    # Finding F3: the "no point past the edge" invariant is enforced at the
    # response root against generated_at, so the same artifact validates the
    # same way on any machine on any day. A point ON the report date is fine;
    # a point AFTER it is a producer defect.
    on_edge = {
        "basis": "fc",
        "points": [
            {"date": "2026-07-05", "value": 1.0},
            {"date": "2026-07-06", "value": 2.0},
        ],
    }
    past_edge = {
        "basis": "fc",
        "points": [
            {"date": "2026-07-05", "value": 1.0},
            {"date": "2026-07-07", "value": 2.0},
        ],
    }
    generated_at = "2026-07-06T14:30:00+00:00"

    WhatChangedResponse.model_validate(
        _minimal_response_with_market_series(generated_at=generated_at, series=on_edge)
    )
    with pytest.raises(ValidationError):
        WhatChangedResponse.model_validate(
            _minimal_response_with_market_series(
                generated_at=generated_at, series=past_edge
            )
        )


def _model_entry(
    *,
    capture_date: str,
    sleeper_id: str,
    player_name: str,
    position: str,
    team_value: float,
    vintage: str,
) -> dict[str, Any]:
    return {
        "capture_date": capture_date,
        "source": MODEL_PVO_SOURCE,
        "semantic_output_hash": f"semantic-{vintage}",
        "provenance_hash": f"provenance-{vintage}",
        "player_key": f"sleeper:{sleeper_id}",
        "sleeper_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player_name": player_name,
        "position": position,
        "engine_path": "ENGINE_B",
        "dynasty_value_score": team_value,
        "dvs_pct": team_value / 100,
        "xvar": team_value / 10,
        "model_grade": "MODEL",
        "model_version": "engine_b_v2",
        "artifact_vintage": f"{capture_date}T14:00:00+00:00",
        "row_index": 0,
        "semantic_row_hash": f"row:{sleeper_id}:{capture_date}:{team_value}",
        "payload_hash": f"row:{sleeper_id}:{capture_date}:{team_value}",
    }


def _seed_model_series_store(db_path: Path) -> None:
    store = ModelForwardCaptureStore(db_path)
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-07-05",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                team_value=96.0,
                vintage="old",
            )
        ]
    )
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-07-06",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                team_value=98.5,
                vintage="new",
            )
        ]
    )


def _write_increment1_sleeper_snapshot(path: Path) -> Path:
    return _write_json(
        path,
        {
            "captured_at": "2026-07-06T14:00:00+00:00",
            "david_roster_id": 1,
            "rosters": [{"roster_id": 1, "players": ["9509"]}],
            "players": [
                {
                    "sleeper_player_id": "9509",
                    "player": {
                        "full_name": "Bijan Robinson",
                        "position": "RB",
                        "team": "ATL",
                    },
                    "league_context": {"roster_id": 1, "rostered": True},
                }
            ],
        },
    )


def test_report_emitter_adds_increment1_row_assets_and_baseline_rows(tmp_path: Path) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    report_path = tmp_path / "what_changed" / "what_changed_latest_report.json"
    paths = _fixture_paths(tmp_path)
    paths["sleeper_snapshot_path"] = _write_increment1_sleeper_snapshot(
        tmp_path / "league_snapshots" / "sleeper_universe_snapshot_latest.json"
    )

    _seed_fc_store(fc_db)
    _seed_model_series_store(model_db)

    report = emit_daily_what_changed_report(
        fc_db_path=fc_db,
        model_db_path=model_db,
        report_path=report_path,
        now_fn=lambda: GENERATED_AT,
        top_n=25,
        **paths,
    )

    market_row = next(
        row
        for row in report["daily_diff"]["market"]["roster_deltas"]
        if row["sleeper_id"] == "9509"
    )
    model_row = report["daily_diff"]["model"]["deltas"][0]

    assert market_row["team_id"] == "ATL"
    assert market_row["market_series"]["basis"] == "fc_forward_capture_joinable.value"
    assert [p["date"] for p in market_row["market_series"]["points"]] == [
        "2026-06-23",
        "2026-06-24",
    ]
    assert market_row["model_series"] is None

    assert model_row["team_id"] == "ATL"
    assert model_row["model_series"]["basis"] == (
        "model_forward_capture_joinable.dynasty_value_score"
    )
    assert [p["date"] for p in model_row["model_series"]["points"]] == [
        "2026-07-05",
        "2026-07-06",
    ]
    assert model_row["market_series"] is None

    baseline_rows = report["structural_context"]["baseline_roster_rows"]
    assert baseline_rows[0]["sleeper_id"] == "9509"
    assert baseline_rows[0]["team_id"] == "ATL"
    assert baseline_rows[0]["model_lane_value"] == 0
    assert baseline_rows[0]["market_lane_value"] == 0

    WhatChangedResponse.model_validate(report)


def test_old_what_changed_artifacts_remain_loadable_without_increment1_fields() -> None:
    payload = {
        "schema_version": "war_room_2_what_changed_v1",
        "generated_at": "2026-07-06T14:00:00+00:00",
        "decision_supported": False,
        "overall_status": "ok",
        "daily_diff": {
            "decision_supported": False,
            "overall_status": "ok",
            "market": {
                "status": "ok",
                "decision_supported": False,
                "market_source": "fantasycalc_overlay",
                "comparison_window": {"from_date": "2026-07-05", "to_date": "2026-07-06"},
                "roster_deltas": [],
                "top_movers": [],
                "total_movers_count": 0,
                "entered": [],
                "exited": [],
            },
            "model": {
                "status": "baseline_holding",
                "decision_supported": False,
                "comparison_window": {"status": "insufficient_history"},
                "deltas": [],
            },
        },
        "structural_context": {
            "status": "ok",
            "decision_supported": False,
            "current_not_delta": True,
            "sections": {
                name: {
                    "status": "ok",
                    "decision_supported": False,
                    "current_not_delta": True,
                }
                for name in (
                    "team_posture",
                    "team_value",
                    "league_opportunity",
                    "drop_pressure",
                    "sleeper_snapshot",
                )
            },
        },
    }

    validated = WhatChangedResponse.model_validate(payload)
    assert validated.daily_diff.market.roster_deltas == []
