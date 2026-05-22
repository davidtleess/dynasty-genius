from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "team_value.v1"
SKILL_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
FLEX_ELIGIBLE = frozenset({"RB", "WR", "TE"})
SUPER_FLEX_ELIGIBLE = frozenset({"QB", "RB", "WR", "TE"})
BENCH_DEPTH_DECAY = 0.5
BENCH_REPLACEMENT_XVAR = 0.0


def _xvar(player: dict[str, Any]) -> float:
    value = (player.get("valuation") or {}).get("xvar")
    return float(value) if value is not None else 0.0


def _position(player: dict[str, Any]) -> str:
    return str((player.get("player") or {}).get("position") or "").upper()


def _slot_eligible(slot: str, position: str) -> bool:
    if slot == "FLEX":
        return position in FLEX_ELIGIBLE
    if slot == "SUPER_FLEX":
        return position in SUPER_FLEX_ELIGIBLE
    return position == slot


def _starter_slots(roster_positions: list[str]) -> list[str]:
    return [slot for slot in roster_positions if slot not in {"BN", "IR", "TAXI"}]


def _active_lineup_candidates(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for player in players:
        position = _position(player)
        context = player.get("league_context") or {}
        if position not in SKILL_POSITIONS:
            continue
        if context.get("on_taxi") or context.get("on_ir"):
            continue
        candidates.append(player)
    return candidates


def optimize_best_legal_lineup(
    players: list[dict[str, Any]],
    roster_positions: list[str],
) -> dict[str, Any]:
    """Return a legal lineup that prioritizes required slots before flex slots."""
    slots = _starter_slots(roster_positions)
    candidates = sorted(_active_lineup_candidates(players), key=_xvar, reverse=True)

    ordered_slots = (
        [slot for slot in slots if slot not in {"FLEX", "SUPER_FLEX"}]
        + [slot for slot in slots if slot == "FLEX"]
        + [slot for slot in slots if slot == "SUPER_FLEX"]
    )
    assignments: list[tuple[str, dict[str, Any]]] = []
    used_ids: set[str] = set()

    for slot in ordered_slots:
        for player in candidates:
            sleeper_id = str(player.get("sleeper_player_id"))
            if sleeper_id in used_ids:
                continue
            if not _slot_eligible(slot, _position(player)):
                continue
            used_ids.add(sleeper_id)
            assignments.append((slot, player))
            break

    starters = [
        {
            "slot": slot,
            "sleeper_player_id": str(player.get("sleeper_player_id")),
            "full_name": (player.get("player") or {}).get("full_name"),
            "position": _position(player),
            "xvar": _xvar(player),
        }
        for slot, player in assignments
    ]
    return {
        "starter_slots": slots,
        "starters": starters,
        "starter_xvar": round(sum(starter["xvar"] for starter in starters), 3),
        "unfilled_slots": max(0, len(slots) - len(starters)),
    }


def _depth_credit(bench_players: list[dict[str, Any]]) -> tuple[float, dict[str, float]]:
    credits: dict[str, float] = {}
    total = 0.0
    for rank, player in enumerate(sorted(bench_players, key=_xvar, reverse=True), start=1):
        credit = max(0.0, _xvar(player) - BENCH_REPLACEMENT_XVAR) * (BENCH_DEPTH_DECAY ** rank)
        credit = round(credit, 3)
        credits[str(player.get("sleeper_player_id"))] = credit
        total += credit
    return round(total, 3), credits


def _future_picks_for_roster(future_picks: list[dict[str, Any]], roster_id: int) -> dict[str, list[dict[str, Any]]]:
    owned = []
    outgoing = []
    for pick in future_picks:
        clean = {k: v for k, v in pick.items() if k not in {"xvar", "dynasty_value_score"}}
        if pick.get("current_roster_id") == roster_id:
            owned.append(clean)
        if pick.get("original_roster_id") == roster_id and pick.get("current_roster_id") != roster_id:
            outgoing.append(clean)
    key = lambda p: (p.get("season") or 9999, p.get("round") or 99, p.get("original_roster_id") or 99)
    return {"owned": sorted(owned, key=key), "outgoing": sorted(outgoing, key=key)}


def _age_profile(players: list[dict[str, Any]]) -> dict[str, Any]:
    ages = [
        float((player.get("player") or {}).get("age"))
        for player in players
        if (player.get("player") or {}).get("age") is not None
    ]
    valued = [
        (float((player.get("player") or {}).get("age")), max(0.0, _xvar(player)))
        for player in players
        if (player.get("player") or {}).get("age") is not None and _xvar(player) > 0
    ]
    total_value = sum(value for _, value in valued)
    return {
        "value_weighted_age": round(sum(age * value for age, value in valued) / total_value, 2) if total_value else None,
        "median_age": round(statistics.median(ages), 2) if ages else None,
        "pct_value_over_28": round(sum(value for age, value in valued if age > 28) / total_value, 4) if total_value else None,
    }


def _label_from_z(z_score: float | None) -> str:
    if z_score is None:
        return "neutral"
    if z_score > 0.75:
        return "surplus"
    if z_score < -0.75:
        return "deficit"
    return "neutral"


def _position_summary(
    team_players: list[dict[str, Any]],
    starters: list[dict[str, Any]],
    depth_credits: dict[str, float],
) -> dict[str, dict[str, Any]]:
    starter_ids = {starter["sleeper_player_id"] for starter in starters}
    summary: dict[str, dict[str, Any]] = {}
    for position in sorted(SKILL_POSITIONS):
        rostered = [player for player in team_players if _position(player) == position]
        starter_xvar = sum(_xvar(player) for player in rostered if str(player.get("sleeper_player_id")) in starter_ids)
        depth_xvar = sum(depth_credits.get(str(player.get("sleeper_player_id")), 0.0) for player in rostered)
        summary[position] = {
            "n_rostered": len(rostered),
            "starter_xvar": round(starter_xvar, 3),
            "depth_xvar_adj": round(depth_xvar, 3),
            "z_score": None,
            "surplus_label": "neutral",
        }
    return summary


def _annotated_players(
    team_players: list[dict[str, Any]],
    starters: list[dict[str, Any]],
    depth_credits: dict[str, float],
) -> list[dict[str, Any]]:
    starter_ids = {starter["sleeper_player_id"] for starter in starters}
    rows = []
    for player in sorted(team_players, key=_xvar, reverse=True):
        context = player.get("league_context") or {}
        sleeper_id = str(player.get("sleeper_player_id"))
        if context.get("on_taxi"):
            role = "taxi"
        elif context.get("on_ir"):
            role = "ir"
        elif sleeper_id in starter_ids:
            role = "starter"
        else:
            role = "bench"
        row = {
            "sleeper_player_id": sleeper_id,
            "full_name": (player.get("player") or {}).get("full_name"),
            "position": _position(player),
            "raw_xvar": _xvar(player),
            "lineup_role": role,
            "depth_credit_xvar": depth_credits.get(sleeper_id, 0.0),
            "starter_weight_multiplier_current_year": 1.0 if role == "starter" else 0.0,
            "long_term_value_multiplier": 1.0,
        }
        if role == "taxi":
            row["taxi_activation_cost"] = "requires_active_roster_spot_and_irreversible_taxi_loss"
        rows.append(row)
    return rows


def _apply_position_z_scores(teams: list[dict[str, Any]]) -> None:
    for position in sorted(SKILL_POSITIONS):
        values = [
            team["positional_summary"][position]["starter_xvar"]
            + team["positional_summary"][position]["depth_xvar_adj"]
            for team in teams
        ]
        mean = statistics.mean(values) if values else 0.0
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        for team, value in zip(teams, values):
            z_score = round((value - mean) / stdev, 3) if stdev else 0.0
            team["positional_summary"][position]["z_score"] = z_score
            team["positional_summary"][position]["surplus_label"] = _label_from_z(z_score)


def build_team_value_matrix(
    *,
    universe_pvo: dict[str, Any],
    league_snapshot: dict[str, Any],
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    roster_positions = (league_snapshot.get("league") or {}).get("roster_positions") or []
    players_by_roster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for player in universe_pvo.get("players") or []:
        context = player.get("league_context") or {}
        if context.get("rostered") and context.get("roster_id") is not None:
            players_by_roster[int(context["roster_id"])].append(player)

    users_by_id = {str(user.get("user_id")): user for user in league_snapshot.get("users") or []}
    teams: list[dict[str, Any]] = []
    for roster in sorted(league_snapshot.get("rosters") or [], key=lambda r: int(r.get("roster_id", 0))):
        roster_id = int(roster["roster_id"])
        owner_id = str(roster.get("owner_id"))
        owner = users_by_id.get(owner_id, {})
        team_players = players_by_roster.get(roster_id, [])
        lineup = optimize_best_legal_lineup(team_players, roster_positions)
        starter_ids = {starter["sleeper_player_id"] for starter in lineup["starters"]}
        bench_players = [
            player for player in team_players
            if _position(player) in SKILL_POSITIONS
            and str(player.get("sleeper_player_id")) not in starter_ids
            and not (player.get("league_context") or {}).get("on_taxi")
            and not (player.get("league_context") or {}).get("on_ir")
        ]
        depth_credit_total, depth_credits = _depth_credit(bench_players)
        lineup_xvar = lineup["starter_xvar"]
        positive_total = round(sum(max(0.0, _xvar(player)) for player in team_players if _position(player) in SKILL_POSITIONS), 3)
        top_n_total = round(sum(sorted([max(0.0, _xvar(player)) for player in team_players if _position(player) in SKILL_POSITIONS], reverse=True)[: len(_starter_slots(roster_positions))]), 3)
        team = {
            "schema_version": SCHEMA_VERSION,
            "league_id": universe_pvo.get("league_id") or league_snapshot.get("league_id"),
            "captured_at": captured,
            "roster_id": roster_id,
            "owner": {
                "user_id": owner_id,
                "display_name": owner.get("display_name"),
                "team_name": (owner.get("metadata") or {}).get("team_name"),
            },
            "team_value_views": {
                "starter_weighted_xvar": round(lineup_xvar + depth_credit_total, 3),
                "lineup_xvar": lineup_xvar,
                "depth_credit_xvar": depth_credit_total,
                "total_xvar_capped": positive_total,
                "top_n_xvar": top_n_total,
                "market_overlay_total": None,
            },
            "lineup": lineup,
            "positional_summary": _position_summary(team_players, lineup["starters"], depth_credits),
            "age_profile": _age_profile(team_players),
            "future_picks": _future_picks_for_roster(league_snapshot.get("future_picks") or [], roster_id),
            "posture": {
                "label": "UNCLASSIFIED",
                "score": None,
                "manual_override_allowed": True,
            },
            "players": _annotated_players(team_players, lineup["starters"], depth_credits),
            "decision_supported": False,
        }
        teams.append(team)

    _apply_position_z_scores(teams)
    return {
        "schema_version": "team_value_matrix.v1",
        "league_id": universe_pvo.get("league_id") or league_snapshot.get("league_id"),
        "captured_at": captured,
        "bench_weighting_guardrail": {
            "player_level_value_decay_allowed": False,
            "lineup_selection": "best_legal_lineup_from_raw_player_xvar",
            "depth_weighting_scope": "non_starters_after_lineup_selection",
            "bench_depth_decay": BENCH_DEPTH_DECAY,
        },
        "teams": teams,
        "coverage": {
            "team_count": len(teams),
            "all_teams_emitted": len(teams) == len(league_snapshot.get("rosters") or []),
            "future_picks_present_unvalued": all(
                "xvar" not in pick and "dynasty_value_score" not in pick
                for team in teams
                for bucket in ("owned", "outgoing")
                for pick in team["future_picks"][bucket]
            ),
            "taxi_activation_cost_represented": any(
                player.get("lineup_role") == "taxi" and player.get("taxi_activation_cost")
                for team in teams
                for player in team["players"]
            ),
        },
    }


def write_team_value_matrix_artifacts(
    matrix: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(matrix["captured_at"]).replace(":", "").replace("-", "")
    matrix_path = output_dir / f"team_value_matrix_{safe_run_id}.json"
    latest_path = output_dir / "team_value_matrix_latest.json"
    payload = json.dumps(matrix, indent=2, sort_keys=True) + "\n"
    matrix_path.write_text(payload)
    latest_path.write_text(payload)
    return {"matrix": matrix_path, "matrix_latest": latest_path}
