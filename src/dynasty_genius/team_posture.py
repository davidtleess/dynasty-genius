from __future__ import annotations

import copy
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "team_posture.v1"
MARKET_FIELD_TOKENS = ("market", "fantasycalc", "ktc", "adp")


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _team_strength(team: dict[str, Any]) -> float:
    return _safe_float((team.get("team_value_views") or {}).get("starter_weighted_xvar"))


def _z_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    stdev = statistics.pstdev(values)
    if not stdev:
        return [0.0 for _ in values]
    mean = statistics.mean(values)
    return [round((value - mean) / stdev, 3) for value in values]


def _early_pick_balance(team: dict[str, Any]) -> float:
    future_picks = team.get("future_picks") or {}
    owned = future_picks.get("owned") or []
    outgoing = future_picks.get("outgoing") or []

    def weight(pick: dict[str, Any]) -> float:
        round_no = pick.get("round")
        if round_no == 1:
            return 1.0
        if round_no == 2:
            return 0.5
        return 0.0

    return max(-1.0, min(1.0, sum(weight(pick) for pick in owned) - sum(weight(pick) for pick in outgoing)))


def _development_stash_score(team: dict[str, Any]) -> float:
    taxi_positive_xvar = sum(
        max(0.0, _safe_float(player.get("raw_xvar")))
        for player in team.get("players") or []
        if player.get("lineup_role") == "taxi"
    )
    return max(0.0, min(1.0, taxi_positive_xvar / 20.0))


def _age_window_score(team: dict[str, Any]) -> float:
    age_profile = team.get("age_profile") or {}
    age = age_profile.get("value_weighted_age")
    if age is None:
        return 0.0
    age_value = _safe_float(age)
    if age_value <= 25.5:
        return 1.0
    if age_value <= 27.0:
        return 0.4
    if age_value >= 28.5:
        return -0.8
    return -0.2


def _market_fields_absent(payload: Any) -> bool:
    serialized = json.dumps(payload, sort_keys=True).lower()
    return not any(token in serialized for token in MARKET_FIELD_TOKENS)


def _label_for(*, strength_z: float, age_score: float, pick_score: float, stash_score: float) -> str:
    future_score = (age_score * 0.45) + (pick_score * 0.35) + (stash_score * 0.20)
    if strength_z >= 0.75:
        return "CONTENDER"
    if strength_z <= -0.75 and future_score >= 0.25:
        return "REBUILDING"
    if -0.75 < strength_z < 0.75 and future_score >= 0.45:
        return "ASCENDING"
    if strength_z < 0.75 and future_score <= -0.25:
        return "TRANSITIONAL"
    return "BALANCED"


def build_team_posture_artifact(
    team_matrix: dict[str, Any],
    *,
    captured_at: str | None = None,
) -> dict[str, Any]:
    source = copy.deepcopy(team_matrix)
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    teams = source.get("teams") or []
    strengths = [_team_strength(team) for team in teams]
    strength_z_scores = _z_scores(strengths)
    posture_rows: list[dict[str, Any]] = []

    for team, strength_z in zip(teams, strength_z_scores):
        age_score = _age_window_score(team)
        pick_score = _early_pick_balance(team)
        stash_score = _development_stash_score(team)
        label = _label_for(
            strength_z=strength_z,
            age_score=age_score,
            pick_score=pick_score,
            stash_score=stash_score,
        )
        posture_score = round((strength_z * 0.60) + (age_score * 0.20) + (pick_score * 0.15) + (stash_score * 0.05), 3)
        posture_rows.append(
            {
                "roster_id": int(team["roster_id"]),
                "owner": copy.deepcopy(team.get("owner") or {}),
                "posture": {
                    "label": label,
                    "score": posture_score,
                    "manual_override_allowed": True,
                    "classification_basis": "internal_team_matrix_v1",
                    "decision_supported": False,
                    "components": {
                        "starter_weighted_xvar_z": strength_z,
                        "age_window_score": round(age_score, 3),
                        "early_pick_balance_score": round(pick_score, 3),
                        "development_stash_score": round(stash_score, 3),
                    },
                    "caveats": [
                        "phase18_heuristic_posture",
                        "future_pick_values_deferred",
                    ],
                },
                "decision_supported": False,
            }
        )

    decision_supported_true_count = sum(
        1
        for row in posture_rows
        if row.get("decision_supported") is True or (row.get("posture") or {}).get("decision_supported") is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "league_id": source.get("league_id"),
        "captured_at": captured,
        "source_artifacts": {
            "team_matrix_schema_version": source.get("schema_version"),
            "team_matrix_captured_at": source.get("captured_at"),
        },
        "teams": posture_rows,
        "decision_supported": False,
        "coverage": {
            "team_count": len(posture_rows),
            "all_teams_classified": all((row.get("posture") or {}).get("label") != "UNCLASSIFIED" for row in posture_rows),
            "decision_supported_true_count": decision_supported_true_count,
            "market_fields_absent": _market_fields_absent(posture_rows),
        },
    }


def apply_team_postures(team_matrix: dict[str, Any], team_posture: dict[str, Any] | None) -> dict[str, Any]:
    updated = copy.deepcopy(team_matrix)
    if not team_posture:
        return updated
    posture_by_roster = {
        int(row["roster_id"]): row
        for row in team_posture.get("teams") or []
        if row.get("roster_id") is not None and row.get("posture")
    }
    for team in updated.get("teams") or []:
        roster_id = int(team["roster_id"])
        posture_row = posture_by_roster.get(roster_id)
        if not posture_row:
            continue
        posture = copy.deepcopy(posture_row["posture"])
        posture["source_artifact_schema_version"] = team_posture.get("schema_version")
        posture["source_artifact_captured_at"] = team_posture.get("captured_at")
        team["posture"] = posture
    return updated


def write_team_posture_artifacts(
    posture_artifact: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(posture_artifact["captured_at"]).replace(":", "").replace("-", "")
    posture_path = output_dir / f"team_posture_{safe_run_id}.json"
    latest_path = output_dir / "team_posture_latest.json"
    payload = json.dumps(posture_artifact, indent=2, sort_keys=True) + "\n"
    posture_path.write_text(payload)
    latest_path.write_text(payload)
    return {"posture": posture_path, "posture_latest": latest_path}
