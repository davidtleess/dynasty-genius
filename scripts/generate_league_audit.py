"""Generate a league-wide fragility lens using internal valuations.

This intentionally emits signals and caveats, not trade instructions. It is a
pre-model opponent context artifact until live rosters, pick inventory, and
valuation gates are verified.

Live mode (default when DYNASTY_SLEEPER_LEAGUE_ID and DYNASTY_SLEEPER_USERNAME
are set): fetches all league rosters from Sleeper.

Mock mode (--mock flag or missing env vars): reads resources/mock_league_rosters.json.

Usage:
    .venv/bin/python scripts/generate_league_audit.py
    .venv/bin/python scripts/generate_league_audit.py --mock
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(ROOT / ".env")

from app.services.roster_auditor import roster_biological_debt

SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}


def _opportunity_type(status: str) -> str:
    if status == "FRAGILE":
        return "aging_asset_liquidity_pressure"
    if status == "DEBT_HEAVY":
        return "aging_asset_concentration"
    return "no_fragility_signal"


def _why_flagged(debt_ratio: float | None, has_liquidity: bool) -> list[str]:
    flags: list[str] = []
    if debt_ratio is not None and debt_ratio > 0.40:
        flags.append("biological_debt_ratio_above_40pct")
    if not has_liquidity:
        flags.append("limited_first_round_pick_liquidity")
    if not flags:
        flags.append("no_current_fragility_signal")
    return flags


def _fragility_status(debt_ratio: float | None, has_liquidity: bool) -> str:
    if debt_ratio is not None and debt_ratio > 0.40 and not has_liquidity:
        return "FRAGILE"
    if debt_ratio is not None and debt_ratio > 0.40:
        return "DEBT_HEAVY"
    return "HEALTHY"


# ── Mock data helpers ─────────────────────────────────────────────────────────

# Mock internal values (0-10000 scale) — only used in mock mode.
_MOCK_PLAYER_VALUES = {
    'tyreek_hill_wr_1994': 8500,
    'davante_adams_wr_1992': 7800,
    'travis_kelce_te_1989': 7200,
    'jeremiah_smith_wr_2005': 9200,
    'arch_manning_qb_2005': 9500,
}


def _players_from_mock(team: dict) -> list[dict]:
    players = []
    for pid in team['players']:
        parts = pid.split('_')
        pos = parts[2].upper()
        birth_year = int(parts[3])
        age = 2026 - birth_year
        players.append({
            'full_name': pid,
            'position': pos,
            'age': age,
            'internal_value': _MOCK_PLAYER_VALUES.get(pid, 500),
        })
    return players


def _load_mock_rosters() -> list[dict]:
    roster_path = ROOT / 'resources' / 'mock_league_rosters.json'
    with open(roster_path, 'r') as f:
        return json.load(f)


# ── Live Sleeper helpers ──────────────────────────────────────────────────────

def _has_pick(roster_picks: list[dict], season: str, round_: int) -> bool:
    for pk in roster_picks:
        try:
            if str(pk.get("season")) == season and int(pk.get("round", 0)) == round_:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _has_first_round_liquidity(team: dict) -> bool:
    if "has_future_1st_liquidity" in team:
        return bool(team["has_future_1st_liquidity"])
    return bool(team.get('has_2026_1st', True) or team.get('has_2027_1st', True))


def _compute_pick_ownership(
    rosters: list[dict],
    traded_picks: list[dict],
    future_seasons: list[str],
    future_rounds: list[int],
) -> dict[int, dict[tuple[str, int], bool]]:
    """Return {roster_id: {(season, round): True}} for picks each roster currently owns.

    Each roster starts owning its own picks for every future season/round combination.
    Traded picks transfer ownership from the original roster to the receiving roster.
    """
    roster_ids = [r["roster_id"] for r in rosters]
    # {roster_id: {(season, round): bool}}
    ownership: dict[int, dict[tuple[str, int], bool]] = {
        rid: {(s, rnd): True for s in future_seasons for rnd in future_rounds}
        for rid in roster_ids
    }

    for pk in traded_picks:
        try:
            season = str(pk.get("season"))
            round_ = int(pk.get("round", 0))
            original_roster = int(pk.get("roster_id", 0))
            owner_roster = int(pk.get("owner_id", 0))  # in traded_picks, owner_id is roster_id
        except (TypeError, ValueError):
            continue

        key = (season, round_)
        if key not in {(s, r) for s in future_seasons for r in future_rounds}:
            continue

        # Original roster no longer owns it; receiving roster does.
        if original_roster in ownership:
            ownership[original_roster][key] = False
        if owner_roster in ownership:
            ownership[owner_roster][key] = True

    return ownership


async def _fetch_live_rosters() -> list[dict]:
    from app.data.sleeper import get_leagues, get_rosters, get_traded_picks, get_users, get_all_players, get_user

    username = os.getenv("DYNASTY_SLEEPER_USERNAME")
    league_id = os.getenv("DYNASTY_SLEEPER_LEAGUE_ID")
    season = os.getenv("DYNASTY_SEASON", "2026")

    if not league_id:
        user = await get_user(username)
        user_id = user["user_id"]
        leagues = await get_leagues(user_id, season)
        league_name = os.getenv("DYNASTY_SLEEPER_LEAGUE_NAME")
        league = next((lg for lg in leagues if lg.get("name") == league_name), None)
        if not league:
            raise ValueError(f"League {league_name!r} not found for season {season}")
        league_id = league["league_id"]

    current_year = int(season)
    future_seasons = [str(current_year + 1), str(current_year + 2)]

    rosters, users, all_players, traded_picks = await asyncio.gather(
        get_rosters(league_id),
        get_users(league_id),
        get_all_players(),
        get_traded_picks(league_id),
    )

    user_map = {u["user_id"]: u.get("display_name", u["user_id"]) for u in users}
    pick_ownership = _compute_pick_ownership(rosters, traded_picks, future_seasons, [1, 2])

    result = []
    for roster in rosters:
        owner_id = roster.get("owner_id")
        roster_id = roster.get("roster_id")
        display_name = user_map.get(owner_id, owner_id or "unknown")

        picks_for_roster = pick_ownership.get(roster_id, {})

        players_out = []
        for pid in (roster.get("players") or []):
            p = all_players.get(str(pid))
            if not p:
                continue
            pos = p.get("position", "")
            if pos not in SKILL_POSITIONS:
                continue
            full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            players_out.append({
                'full_name': full_name,
                'position': pos,
                'age': p.get("age"),
                'internal_value': None,  # PRE_MODEL until Engine B
            })

        result.append({
            'owner_id': owner_id,
            'display_name': display_name,
            'players': players_out,
            'future_first_round_picks': [
                s for s in future_seasons
                if picks_for_roster.get((s, 1), False)
            ],
            'has_future_1st_liquidity': any(
                picks_for_roster.get((s, 1), False)
                for s in future_seasons
            ),
        })

    return result


# ── Report generation ─────────────────────────────────────────────────────────

def _build_report(teams: list[dict], *, live: bool) -> list[dict]:
    report = []
    for team in teams:
        if live:
            players = team['players']
        else:
            players = _players_from_mock(team)

        debt = roster_biological_debt(players)
        debt_ratio = debt['biological_debt_ratio']

        has_liquidity = _has_first_round_liquidity(team)
        status = _fragility_status(debt_ratio, has_liquidity)

        caveats = [
            "replace_mock_rosters_with_live_sleeper_snapshot" if not live else "live_sleeper_roster",
            "verify_opponent_pick_inventory",
            "review_counter_argument",
            "confirm_market_overlay_remains_post_model_only",
        ]
        if live and debt_ratio is None:
            caveats.append("biological_debt_unavailable_engine_b_pre_model")

        report.append({
            'owner': team['display_name'],
            'debt_ratio': debt_ratio,
            'total_value': debt['total_internal_roster_value'],
            'liquidity': 'HIGH' if has_liquidity else 'NONE',
            'fragility_status': status,
            'opportunity_type': _opportunity_type(status),
            'why_flagged': _why_flagged(debt_ratio, has_liquidity),
            'decision_supported': False,
            'required_before_action': [
                'verify_opponent_pick_inventory',
                'review_counter_argument',
                'confirm_market_overlay_remains_post_model_only',
            ],
        })
    return report


def generate_report(use_mock: bool = False) -> None:
    live = False
    teams: list[dict]

    has_env = bool(os.getenv("DYNASTY_SLEEPER_USERNAME")) and (
        bool(os.getenv("DYNASTY_SLEEPER_LEAGUE_ID")) or
        bool(os.getenv("DYNASTY_SLEEPER_LEAGUE_NAME"))
    )

    if not use_mock and has_env:
        print("Fetching live league rosters from Sleeper…")
        try:
            teams = asyncio.run(_fetch_live_rosters())
            live = True
            print(f"Fetched {len(teams)} team rosters.")
        except Exception as e:
            print(f"Live fetch failed ({e}); falling back to mock rosters.")
            teams = _load_mock_rosters()
    else:
        if use_mock:
            print("Mock mode requested — using mock_league_rosters.json.")
        else:
            print("Sleeper env vars not set — using mock_league_rosters.json.")
        teams = _load_mock_rosters()

    report = _build_report(teams, live=live)

    output_path = ROOT / 'resources' / 'league_fragility_report.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Report generated ({len(report)} teams): {output_path}")


if __name__ == "__main__":
    use_mock = "--mock" in sys.argv
    generate_report(use_mock=use_mock)
