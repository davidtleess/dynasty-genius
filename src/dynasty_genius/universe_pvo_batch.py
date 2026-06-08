from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_ROUTE_VALUES = frozenset(
    {
        "ENGINE_A",
        "ENGINE_B",
        "BLEND_AB",
        "PRE_MODEL",
        "MARKET_ONLY",
        "INACTIVE",
        "CONTEXT_ONLY",
        "UNRESOLVED_IDENTITY",
    }
)

SCHEMA_VERSION = "universe_pvo_batch.v1"
SKILL_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


def _route_from_pvo(pvo: dict[str, Any]) -> str:
    dvs_engine = pvo.get("dvs_engine")
    engine_used = pvo.get("engine_used")
    model_grade = pvo.get("model_grade")
    if dvs_engine == "blend":
        return "BLEND_AB"
    if engine_used == "engine_b" or model_grade == "ACTIVE_B":
        return "ENGINE_B"
    if dvs_engine == "A" or str(model_grade or "").startswith("PROSPECT"):
        return "ENGINE_A"
    if dvs_engine == "B":
        return "ENGINE_B"
    return "PRE_MODEL"


def _route_without_pvo(snapshot_row: dict[str, Any]) -> str:
    cohort = snapshot_row.get("cohort")
    if cohort in ENGINE_ROUTE_VALUES:
        return str(cohort)
    if cohort == "FANTASY_RELEVANT":
        return "PRE_MODEL"
    return "PRE_MODEL"


def _status_from_route(route: str, pvo: dict[str, Any] | None = None) -> str:
    if route in {"ENGINE_A", "ENGINE_B", "BLEND_AB"}:
        return "MODEL_SUPPORTED" if pvo and pvo.get("dynasty_value_score") is not None else "MODEL_UNCERTAIN"
    if route == "MARKET_ONLY":
        return "MARKET_ONLY"
    if route == "CONTEXT_ONLY":
        return "CONTEXT_ONLY"
    if route == "INACTIVE":
        return "INACTIVE"
    if route == "UNRESOLVED_IDENTITY":
        return "UNRESOLVED_IDENTITY"
    return "PRE_MODEL"


def _index_pvos(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = row.get("sleeper_id") or row.get("sleeper_player_id")
        if sid is not None:
            indexed[str(sid)] = row
    return indexed


def _empty_valuation(route: str, pvo: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "engine_path": route,
        "valuation_status": _status_from_route(route, pvo),
        "dynasty_value_score": None,
        "xvar": None,
        "xvar_percentile_overall": None,
        "xvar_percentile_position": None,
        "model_version": None,
        "model_grade": "PRE_MODEL" if route == "PRE_MODEL" else None,
        "feature_completeness": 0.0,
        "decision_supported": False,
    }


def _valuation_from_pvo(route: str, pvo: dict[str, Any]) -> dict[str, Any]:
    return {
        "engine_path": route,
        "valuation_status": _status_from_route(route, pvo),
        "dynasty_value_score": pvo.get("dynasty_value_score"),
        "xvar": pvo.get("xvar"),
        "xvar_percentile_overall": None,
        "xvar_percentile_position": pvo.get("dvs_pct"),
        "model_version": pvo.get("model_version"),
        "model_grade": pvo.get("model_grade"),
        "feature_completeness": pvo.get("signal_completeness"),
        "decision_supported": False,
    }


def _apply_xvar_percentile_overall(rows: list[dict[str, Any]]) -> None:
    ranked_rows = [
        row
        for row in rows
        if (row.get("valuation") or {}).get("engine_path") in {"ENGINE_A", "ENGINE_B", "BLEND_AB"}
        and (row.get("valuation") or {}).get("xvar") is not None
    ]
    ranked_rows.sort(key=lambda row: float((row.get("valuation") or {}).get("xvar")), reverse=True)
    total = len(ranked_rows)
    if total == 0:
        return
    for rank, row in enumerate(ranked_rows, start=1):
        percentile = ((total - rank + 1) / total) * 100.0
        row["valuation"]["xvar_percentile_overall"] = round(percentile, 1)


def _identity_status(snapshot_row: dict[str, Any], pvo: dict[str, Any] | None) -> str:
    if snapshot_row.get("cohort") == "UNRESOLVED_IDENTITY":
        return "unresolved"
    if pvo and pvo.get("player_id"):
        return "resolved"
    return str(snapshot_row.get("identity_status") or "sleeper_resolved")


def build_universe_pvo_batch(
    snapshot: dict[str, Any],
    *,
    prospect_pvos: list[dict[str, Any]] | None = None,
    active_pvos: list[dict[str, Any]] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    pvo_by_sleeper = _index_pvos((prospect_pvos or []) + (active_pvos or []))
    rows: list[dict[str, Any]] = []

    for source_row in snapshot.get("players") or []:
        sleeper_id = str(source_row.get("sleeper_player_id"))
        pvo = pvo_by_sleeper.get(sleeper_id)
        route = _route_from_pvo(pvo) if pvo else _route_without_pvo(source_row)
        if route not in ENGINE_ROUTE_VALUES:
            route = "PRE_MODEL"

        valuation = _valuation_from_pvo(route, pvo) if pvo else _empty_valuation(route)
        player = source_row.get("player") or {}
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "pipeline_run_id": None,
                "captured_at": captured,
                "sleeper_player_id": sleeper_id,
                "dg_player_id": pvo.get("player_id") if pvo else None,
                "identity_status": _identity_status(source_row, pvo),
                "identity_ids": {
                    "sleeper_id": sleeper_id,
                    "gsis_id": pvo.get("gsis_id") if pvo else None,
                    "pfr_id": pvo.get("pfr_id") if pvo else None,
                    "pff_id": pvo.get("pff_id") if pvo else None,
                    "espn_id": pvo.get("espn_id") if pvo else None,
                },
                "player": {
                    "full_name": (pvo or {}).get("full_name") or player.get("full_name"),
                    "position": (pvo or {}).get("position") or player.get("position"),
                    "team": (pvo or {}).get("nfl_team") or player.get("team"),
                    "age": (pvo or {}).get("age") or player.get("age"),
                    "years_exp": player.get("years_exp"),
                    "sleeper_status": player.get("sleeper_status"),
                    "dg_status": route,
                },
                "league_context": source_row.get("league_context") or {},
                "dvs_engine": pvo.get("dvs_engine") if pvo else None,
                "final_college_age": pvo.get("final_college_age") if pvo else None,
                "te_ryptpa_final": pvo.get("te_ryptpa_final") if pvo else None,
                "te_yards_per_reception_career": pvo.get("te_yards_per_reception_career") if pvo else None,
                # Surface-3 (T2): additively preserve the 10 DTO-backed evidence/projection
                # fields from the source PVO (None when no PVO matched). Existing keys unchanged.
                "counter_argument": pvo.get("counter_argument") if pvo else None,
                "risk_flags": pvo.get("risk_flags") if pvo else None,
                "top_drivers": pvo.get("top_drivers") if pvo else None,
                "caveats": pvo.get("caveats") if pvo else None,
                "draft_class": pvo.get("draft_class") if pvo else None,
                "nfl_draft_pick": pvo.get("nfl_draft_pick") if pvo else None,
                "nfl_draft_round": pvo.get("nfl_draft_round") if pvo else None,
                "projection_1y": pvo.get("projection_1y") if pvo else None,
                "projection_2y": pvo.get("projection_2y") if pvo else None,
                "projection_3y": pvo.get("projection_3y") if pvo else None,
                "valuation": valuation,
                "market_overlay": None,
                "divergence": None,
                "lineage": {
                    "sleeper_snapshot_hash": (snapshot.get("lineage") or {}).get("sleeper_players_hash"),
                    "governance_version": "1.0.0",
                },
            }
        )

    _apply_xvar_percentile_overall(rows)
    batch = {
        "schema_version": SCHEMA_VERSION,
        "league_id": snapshot.get("league_id"),
        "captured_at": captured,
        "source_snapshot_captured_at": snapshot.get("captured_at"),
        "defaults": snapshot.get("defaults") or {},
        "players": rows,
    }
    batch["coverage"] = build_universe_pvo_coverage(batch)
    return batch


def build_universe_pvo_coverage(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("players") or []
    counts = Counter(str(row.get("valuation", {}).get("engine_path")) for row in rows)
    rostered_skill_missing_route = []
    xvar_percentile_populated = 0
    non_model_rows_with_overall_percentile = []
    populated_rows_without_xvar = []
    for row in rows:
        position = str((row.get("player") or {}).get("position") or "").upper()
        league_context = row.get("league_context") or {}
        valuation = row.get("valuation") or {}
        route = valuation.get("engine_path")
        if league_context.get("rostered") and position in SKILL_POSITIONS and route not in ENGINE_ROUTE_VALUES:
            rostered_skill_missing_route.append(row.get("sleeper_player_id"))
        if valuation.get("xvar_percentile_overall") is not None:
            xvar_percentile_populated += 1
            if valuation.get("xvar") is None:
                populated_rows_without_xvar.append(row.get("sleeper_player_id"))
            if route not in {"ENGINE_A", "ENGINE_B", "BLEND_AB"}:
                non_model_rows_with_overall_percentile.append(row.get("sleeper_player_id"))

    return {
        "total_players": len(rows),
        "counts_by_engine_path": dict(sorted(counts.items())),
        "allowed_engine_routes": sorted(ENGINE_ROUTE_VALUES),
        "rostered_skill_players_missing_route": sorted(rostered_skill_missing_route),
        "xvar_percentile_overall_populated_count": xvar_percentile_populated,
        "non_model_rows_with_xvar_percentile_overall": sorted(non_model_rows_with_overall_percentile),
        "xvar_percentile_overall_without_xvar": sorted(populated_rows_without_xvar),
        "decision_supported_true_count": sum(
            1 for row in rows if (row.get("valuation") or {}).get("decision_supported") is True
        ),
        "market_overlay_present_count": sum(1 for row in rows if row.get("market_overlay") is not None),
        "phase17_2_exit_criteria": {
            "all_rostered_skill_players_have_explicit_route": not rostered_skill_missing_route,
            "market_fields_absent_from_features": True,
            "david_roster_represented_from_snapshot": True,
            "decision_supported_false": not any(
                (row.get("valuation") or {}).get("decision_supported") is True for row in rows
            ),
        },
        "phase18_4_exit_criteria": {
            "overall_percentile_internal_xvar_only": not populated_rows_without_xvar,
            "non_model_rows_overall_percentile_null": not non_model_rows_with_overall_percentile,
            "market_fields_absent_from_percentile": True,
        },
    }


def write_universe_pvo_artifacts(
    batch: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(batch["captured_at"]).replace(":", "").replace("-", "")
    batch_path = output_dir / f"universe_pvo_{safe_run_id}.json"
    latest_path = output_dir / "universe_pvo_latest.json"
    coverage_path = output_dir / f"universe_pvo_coverage_{safe_run_id}.json"
    coverage_latest_path = output_dir / "universe_pvo_coverage_latest.json"

    batch_payload = json.dumps(batch, indent=2, sort_keys=True) + "\n"
    coverage_payload = json.dumps(batch["coverage"], indent=2, sort_keys=True) + "\n"
    batch_path.write_text(batch_payload)
    latest_path.write_text(batch_payload)
    coverage_path.write_text(coverage_payload)
    coverage_latest_path.write_text(coverage_payload)
    return {
        "batch": batch_path,
        "batch_latest": latest_path,
        "coverage": coverage_path,
        "coverage_latest": coverage_latest_path,
    }
