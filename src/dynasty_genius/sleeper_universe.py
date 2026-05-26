from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve, value_pick

FANTASY_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})

PHASE17_DEFAULTS: dict[str, Any] = {
    "pick_reconstruction_mode": "automated_only",
    "divergence_noise_band": 0.10,
    "fantasycalc_params": {
        "isDynasty": "true",
        "numQbs": "2",
        "numTeams": "12",
        "ppr": "1",
    },
    "bench_depth_decay": 0.5,
    "bench_weighting_scope": "team_strength_after_best_legal_lineup",
    "player_level_value_decay_allowed": False,
}

SCHEMA_VERSION = "sleeper_universe_snapshot.v1"
# Phase 24: future-pick valuation reopened (was "deferred" in Phase 17.3). Picks are now
# valued in xVAR via the historical slot curve. David-approved 2026-05-26.
PICK_VALUE_STATUS = "active_v1_historical"

_PICK_CURVE_PATH = (
    Path(__file__).resolve().parents[2]
    / "app" / "data" / "valuation" / "draft_pick_value_curve_v1.json"
)
_PICK_CURVE_CACHE: dict[str, Any] | None = None


def _pick_curve() -> dict[str, Any]:
    global _PICK_CURVE_CACHE
    if _PICK_CURVE_CACHE is None:
        _PICK_CURVE_CACHE = load_curve(_PICK_CURVE_PATH)
    return _PICK_CURVE_CACHE


def _stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _player_name(player: dict[str, Any]) -> str | None:
    full_name = player.get("full_name")
    if full_name:
        return str(full_name)
    first = str(player.get("first_name") or "").strip()
    last = str(player.get("last_name") or "").strip()
    return f"{first} {last}".strip() or None


def _normalize_status(status: Any) -> str:
    return str(status or "unknown").strip().lower() or "unknown"


def _classify_player(
    player_id: str,
    player: dict[str, Any] | None,
    *,
    rostered_ids: set[str],
    draft_player_ids: set[str],
    prospect_ids: set[str],
    market_ids: set[str],
) -> str:
    if player is None:
        return "UNRESOLVED_IDENTITY"

    position = str(player.get("position") or "").upper()
    if player_id in rostered_ids and position not in FANTASY_POSITIONS:
        return "CONTEXT_ONLY"
    if position in FANTASY_POSITIONS:
        return "FANTASY_RELEVANT"
    if player_id in draft_player_ids or player_id in prospect_ids or player_id in market_ids:
        return "FANTASY_RELEVANT"
    status = _normalize_status(player.get("status"))
    if status in {"retired", "inactive"}:
        return "INACTIVE"
    return "EXCLUDED"


def _build_roster_context(rosters: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for roster in rosters:
        roster_id = roster.get("roster_id")
        owner_id = roster.get("owner_id")
        starters = {str(pid) for pid in roster.get("starters") or [] if pid}
        taxi = {str(pid) for pid in roster.get("taxi") or [] if pid}
        reserve = {str(pid) for pid in roster.get("reserve") or [] if pid}
        players = {str(pid) for pid in roster.get("players") or [] if pid}
        for player_id in players | starters | taxi | reserve:
            context[player_id] = {
                "rostered": True,
                "roster_id": roster_id,
                "owner_user_id": owner_id,
                "in_starters": player_id in starters,
                "on_taxi": player_id in taxi,
                "on_ir": player_id in reserve,
            }
    return context


def reconstruct_future_picks(
    *,
    season: int,
    roster_ids: list[int],
    rounds: int,
    traded_picks: list[dict[str, Any]],
    seasons_ahead: int = 3,
) -> list[dict[str, Any]]:
    """Reconstruct full future-pick ownership from Sleeper traded-pick deltas.

    Sleeper emits only moved picks. Phase 17 initializes baseline ownership and
    applies those deltas, without assigning numeric pick value.
    """
    seasons = range(int(season) + 1, int(season) + seasons_ahead + 1)
    curve = _pick_curve()
    picks: dict[tuple[int, int, int], dict[str, Any]] = {}
    for pick_season in seasons:
        for roster_id in sorted(int(rid) for rid in roster_ids):
            for round_no in range(1, int(rounds) + 1):
                # Round-only valuation: a future pick knows only (season, round).
                pv = value_pick(year=pick_season, round_=round_no, curve=curve)
                picks[(pick_season, round_no, roster_id)] = {
                    "season": pick_season,
                    "round": round_no,
                    "original_roster_id": roster_id,
                    "current_roster_id": roster_id,
                    "pick_value_status": PICK_VALUE_STATUS,
                    "xvar": pv.xvar,
                    "dynasty_value_score": None,
                    "pick_value_resolution": pv.resolution,
                    "caveats": list(pv.caveats),
                    "reconstruction_method": "automated_sleeper_traded_picks",
                }

    caveats: list[str] = []
    for traded in traded_picks:
        try:
            pick_season = int(traded["season"])
            round_no = int(traded["round"])
            original_roster_id = int(traded.get("roster_id") or traded.get("previous_owner_id"))
            current_roster_id = int(traded["owner_id"])
        except (KeyError, TypeError, ValueError):
            caveats.append(f"unmatched_traded_pick:{traded}")
            continue

        key = (pick_season, round_no, original_roster_id)
        if key not in picks:
            caveats.append(
                f"traded_pick_outside_reconstruction_window:{pick_season}-R{round_no}-orig{original_roster_id}"
            )
            continue
        picks[key]["current_roster_id"] = current_roster_id

    ordered = sorted(picks.values(), key=lambda row: (row["season"], row["round"], row["original_roster_id"]))
    if caveats:
        ordered.append(
            {
                "season": None,
                "round": None,
                "original_roster_id": None,
                "current_roster_id": None,
                "pick_value_status": PICK_VALUE_STATUS,
                "reconstruction_method": "automated_sleeper_traded_picks",
                "caveats": caveats,
            }
        )
    return ordered


def build_universe_snapshot(
    *,
    league_id: str,
    league: dict[str, Any],
    players: dict[str, dict[str, Any]],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    traded_picks: list[dict[str, Any]],
    draft_state: dict[str, Any] | None = None,
    draft_picks: list[dict[str, Any]] | None = None,
    captured_at: str | None = None,
    prospect_ids: set[str] | None = None,
    market_ids: set[str] | None = None,
    david_roster_id: int | None = None,
) -> dict[str, Any]:
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    prospect_ids = {str(pid) for pid in prospect_ids or set()}
    market_ids = {str(pid) for pid in market_ids or set()}
    draft_player_ids = {
        str(pick["player_id"])
        for pick in draft_picks or []
        if pick.get("player_id") is not None
    }
    roster_context = _build_roster_context(rosters)
    rostered_ids = set(roster_context)
    all_player_ids = set(players) | rostered_ids | draft_player_ids | prospect_ids | market_ids
    user_by_id = {str(user.get("user_id")): user for user in users}

    rows: list[dict[str, Any]] = []
    for player_id in sorted(str(pid) for pid in all_player_ids):
        player = players.get(player_id)
        league_context = roster_context.get(
            player_id,
            {
                "rostered": False,
                "roster_id": None,
                "owner_user_id": None,
                "in_starters": False,
                "on_taxi": False,
                "on_ir": False,
            },
        ).copy()
        if league_context.get("owner_user_id") is not None:
            owner = user_by_id.get(str(league_context["owner_user_id"]), {})
            league_context["owner_display_name"] = owner.get("display_name")
        league_context["in_current_draft"] = player_id in draft_player_ids

        cohort = _classify_player(
            player_id,
            player,
            rostered_ids=rostered_ids,
            draft_player_ids=draft_player_ids,
            prospect_ids=prospect_ids,
            market_ids=market_ids,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "sleeper_player_id": player_id,
                "cohort": cohort,
                "identity_status": "unresolved" if player is None else "sleeper_resolved",
                "player": {
                    "full_name": _player_name(player or {}),
                    "position": (player or {}).get("position"),
                    "team": (player or {}).get("team"),
                    "age": (player or {}).get("age"),
                    "years_exp": (player or {}).get("years_exp"),
                    "sleeper_status": (player or {}).get("status"),
                },
                "league_context": league_context,
            }
        )

    roster_ids = sorted(int(r["roster_id"]) for r in rosters if r.get("roster_id") is not None)
    settings = league.get("settings") or {}
    rounds = int(settings.get("draft_rounds") or settings.get("rounds") or 3)
    season = int(league.get("season") or datetime.now(timezone.utc).year)

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "league_id": league_id,
        "david_roster_id": david_roster_id,
        "league": {
            "name": league.get("name"),
            "season": league.get("season"),
            "roster_positions": league.get("roster_positions") or [],
            "scoring_settings": league.get("scoring_settings") or {},
            "settings": settings,
        },
        "captured_at": captured,
        "defaults": PHASE17_DEFAULTS,
        "users": users,
        "rosters": rosters,
        "future_picks": reconstruct_future_picks(
            season=season,
            roster_ids=roster_ids,
            rounds=rounds,
            traded_picks=traded_picks,
        ),
        "draft_state": draft_state or {},
        "players": rows,
        "lineage": {
            "sleeper_players_hash": _stable_hash(players),
            "league_hash": _stable_hash(league),
            "rosters_hash": _stable_hash(rosters),
            "users_hash": _stable_hash(users),
            "traded_picks_hash": _stable_hash(traded_picks),
            "governance_version": "1.0.0",
        },
    }
    snapshot["coverage"] = build_coverage_report(snapshot)
    return snapshot


def build_coverage_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    players = snapshot.get("players") or []
    counts_by_cohort = Counter(str(row.get("cohort")) for row in players)
    unresolved_rows = [
        row
        for row in players
        if row.get("identity_status") == "unresolved" or row.get("cohort") == "UNRESOLVED_IDENTITY"
    ]
    unresolved_ids = [
        str(row["sleeper_player_id"])
        for row in unresolved_rows
        if row.get("sleeper_player_id") is not None
    ]
    rostered_ids = {
        str(pid)
        for roster in snapshot.get("rosters") or []
        for pid in (roster.get("players") or [])
        if pid
    }
    snapshot_ids = {str(row.get("sleeper_player_id")) for row in players}
    rostered_missing = sorted(rostered_ids - snapshot_ids)
    david_roster_id = snapshot.get("david_roster_id")
    david_rostered_ids = {
        str(pid)
        for roster in snapshot.get("rosters") or []
        if roster.get("roster_id") == david_roster_id
        for pid in (roster.get("players") or [])
        if pid
    }

    return {
        "total_players": len(players),
        "counts_by_cohort": dict(sorted(counts_by_cohort.items())),
        "unresolved_identity_count": len(unresolved_rows),
        "unresolved_sleeper_player_ids": sorted(unresolved_ids),
        "rostered_player_count": len(rostered_ids),
        "rostered_players_missing_from_snapshot": rostered_missing,
        "david_roster_player_count": len(david_rostered_ids),
        "david_roster_players_missing_from_snapshot": sorted(david_rostered_ids - snapshot_ids),
        "section19_defaults": snapshot.get("defaults", PHASE17_DEFAULTS),
        "phase17_1_exit_criteria": {
            "every_sleeper_player_classified": all(row.get("cohort") for row in players),
            "every_rostered_player_present": not rostered_missing,
            "unresolved_identity_list_exists": True,
            "pvo_scoring_required": False,
        },
    }


def write_snapshot_artifacts(
    snapshot: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(snapshot["captured_at"]).replace(":", "").replace("-", "")
    snapshot_path = output_dir / f"sleeper_universe_snapshot_{safe_run_id}.json"
    latest_path = output_dir / "sleeper_universe_snapshot_latest.json"
    coverage_path = output_dir / f"sleeper_universe_coverage_{safe_run_id}.json"
    coverage_latest_path = output_dir / "sleeper_universe_coverage_latest.json"

    snapshot_payload = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    coverage_payload = json.dumps(snapshot["coverage"], indent=2, sort_keys=True) + "\n"
    snapshot_path.write_text(snapshot_payload)
    latest_path.write_text(snapshot_payload)
    coverage_path.write_text(coverage_payload)
    coverage_latest_path.write_text(coverage_payload)

    return {
        "snapshot": snapshot_path,
        "snapshot_latest": latest_path,
        "coverage": coverage_path,
        "coverage_latest": coverage_latest_path,
    }
