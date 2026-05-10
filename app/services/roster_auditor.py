import os
from typing import Optional, Union

import httpx

from app.data.sleeper import get_user, get_leagues, get_rosters, get_all_players
from src.dynasty_genius.models.league_context import LeagueContext

USERNAME_ENV = "DYNASTY_SLEEPER_USERNAME"
LEAGUE_ID_ENV = "DYNASTY_SLEEPER_LEAGUE_ID"
LEAGUE_NAME_ENV = "DYNASTY_SLEEPER_LEAGUE_NAME"
SEASON_ENV = "DYNASTY_SEASON"

CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}
SKILL_POSITIONS = set(CLIFF_AGES.keys())
ENGINE = "roster_age_curve_auditor"
ROSTER_CAVEATS = ["age_curve_only", "no_usage_signal", "no_market_overlay"]
INTERNAL_VALUE_KEYS = ("internal_valuation", "internal_value", "dynasty_value_score")
SIGNAL_DRIVERS = {
    "past_cliff": "age_past_position_cliff",
    "at_cliff": "age_at_position_cliff",
    "approaching_cliff": "age_within_two_years_of_position_cliff",
    "no_age_signal": "age_not_near_position_cliff",
}
NOT_DECISION_GRADE_REASON = (
    "Roster audit is age-curve-only until Engine B usage, efficiency, and market "
    "signals are available."
)


class RosterConfigError(ValueError):
    pass


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def age_cliff_risk(position: str, age: Optional[Union[float, int]]) -> Optional[float]:
    """
    Calculate the roster-audit display risk for proximity to the position cliff.

    This mirrors the Gold SQL formula:
    LEAST(1, GREATEST(0, (age - (cliff_age - 3)) / 3)).
    It is a decision-surface warning, not an Engine B model feature.
    """
    if age is None or position not in CLIFF_AGES:
        return None
    cliff_age = CLIFF_AGES[position]
    return round(_clamp((float(age) - (cliff_age - 3.0)) / 3.0), 4)


def _internal_value(player: dict) -> Optional[float]:
    for key in INTERNAL_VALUE_KEYS:
        value = player.get(key)
        if value is not None:
            return float(value)
    return None


def biological_debt_score(player: dict) -> Optional[float]:
    """
    Value-weighted age-curve risk for a roster asset.

    This intentionally uses internal value only. KTC, ADP, FantasyPros, and
    other market-derived prices are excluded by design.
    """
    risk = age_cliff_risk(player.get("position", ""), player.get("age"))
    internal_value = _internal_value(player)
    if risk is None or internal_value is None:
        return None
    return round(risk * max(internal_value, 0.0), 4)


def liquidity_risk(has_2026_2nd: bool, has_2027_2nd: bool) -> str:
    """
    Classify roster escape-hatch risk from second-round pick inventory.

    Second-round picks are treated as liquidity buffers for patching depth,
    not as market-derived valuation inputs.
    """
    if not has_2026_2nd and not has_2027_2nd:
        return "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"
    if not has_2026_2nd or not has_2027_2nd:
        return "MEDIUM_LIMITED_ESCAPE_HATCH"
    return "LOW"


def roster_biological_debt(players: list[dict]) -> dict:
    debt_value = 0.0
    total_internal_value = 0.0
    debt_players: list[str] = []
    incomplete_players: list[str] = []

    for player in players:
        if player.get("position") not in SKILL_POSITIONS:
            continue

        internal_value = _internal_value(player)
        debt_score = biological_debt_score(player)
        if internal_value is None or debt_score is None:
            incomplete_players.append(player.get("full_name") or player.get("player_id", "UNKNOWN"))
            continue

        total_internal_value += max(internal_value, 0.0)
        debt_value += debt_score
        if debt_score > 0:
            debt_players.append(player.get("full_name") or player.get("player_id", "UNKNOWN"))

    debt_ratio = None
    if total_internal_value > 0:
        debt_ratio = round(debt_value / total_internal_value, 4)

    return {
        "biological_debt_value": round(debt_value, 4),
        "biological_debt_ratio": debt_ratio,
        "biological_debt_players": debt_players,
        "incomplete_biological_debt_players": incomplete_players,
        "total_internal_roster_value": round(total_internal_value, 4),
    }


def roster_risk_summary(
    players: list[dict],
    has_2026_2nd: bool,
    has_2027_2nd: bool,
) -> dict:
    debt = roster_biological_debt(players)
    return {
        **debt,
        "liquidity_risk": liquidity_risk(has_2026_2nd, has_2027_2nd),
        "decision_supported": False,
        "caveats": [
            "internal_value_only",
            "age_curve_only",
            "no_market_derived_inputs",
        ],
    }


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RosterConfigError(f"Missing required environment variable: {name}")
    return value


def _roster_config(league_context: Optional[LeagueContext] = None) -> dict:
    if league_context is not None:
        return {
            "username": None,
            "user_id": league_context.david_user_id,
            "season": league_context.season,
            "league_id": league_context.league_id,
            "league_name": league_context.league_name,
        }

    username = _required_env(USERNAME_ENV)
    season = _required_env(SEASON_ENV)
    league_id = os.getenv(LEAGUE_ID_ENV)
    league_name = os.getenv(LEAGUE_NAME_ENV)

    if not league_id and not league_name:
        raise RosterConfigError(
            f"Set either {LEAGUE_ID_ENV} or {LEAGUE_NAME_ENV}; refusing to guess a league."
        )

    return {
        "username": username,
        "user_id": None,
        "season": season,
        "league_id": league_id,
        "league_name": league_name,
    }


async def _sleeper_config_lookup(description: str, lookup) -> object:
    try:
        return await lookup
    except ValueError as e:
        raise RosterConfigError(f"{description}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise RosterConfigError(
            f"{description} failed with Sleeper status {e.response.status_code}; check roster config."
        ) from e


async def get_my_roster(league_context: Optional[LeagueContext] = None) -> list[dict]:
    config = _roster_config(league_context)
    if config["user_id"]:
        user_id = config["user_id"]
    else:
        user = await _sleeper_config_lookup(
            "Sleeper username lookup",
            get_user(config["username"]),
        )
        user_id = user["user_id"]

    if config["league_id"]:
        league_id = config["league_id"]
    else:
        leagues = await _sleeper_config_lookup(
            "Sleeper league lookup",
            get_leagues(user_id, config["season"]),
        )
        league = next(
            (lg for lg in leagues if lg.get("name") == config["league_name"]),
            None,
        )
        if league is None:
            raise RosterConfigError(
                f"League named {config['league_name']!r} was not found for season {config['season']}."
            )
        league_id = league["league_id"]

    rosters = await _sleeper_config_lookup(
        "Sleeper roster lookup",
        get_rosters(league_id),
    )
    my_roster = next((r for r in rosters if r["owner_id"] == user_id), None)
    if my_roster is None:
        raise RosterConfigError(
            f"No roster found for configured user in league {league_id}."
        )

    all_players = await get_all_players()

    players = []
    for pid in my_roster["players"]:
        p = all_players.get(pid)
        if not p:
            continue
        players.append({
            "player_id": pid,
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "position":  p.get("position", ""),
            "team":      p.get("team") or "FA",
            "age":       p.get("age"),
        })

    return players


def audit_player(player: dict) -> Optional[dict]:
    position = player.get("position", "")
    if position not in SKILL_POSITIONS:
        return None

    age = player.get("age")
    if age is None:
        return None

    cliff_age = CLIFF_AGES[position]
    years_to_cliff = cliff_age - int(age)
    cliff_risk = age_cliff_risk(position, age)
    biological_debt = biological_debt_score(player)

    if years_to_cliff < 0:
        cliff_status = "Past cliff"
        signal = "past_cliff"
    elif years_to_cliff == 0:
        cliff_status = "At cliff"
        signal = "at_cliff"
    elif years_to_cliff <= 2:
        cliff_status = "Approaching"
        signal = "approaching_cliff"
    else:
        cliff_status = "No age signal"
        signal = "no_age_signal"

    caveats = list(ROSTER_CAVEATS)
    if biological_debt is None:
        caveats.append("no_internal_value_signal")

    audited = {
        **player,
        "cliff_age":      cliff_age,
        "years_to_cliff": years_to_cliff,
        "age_cliff_risk": cliff_risk,
        "biological_debt_score": biological_debt,
        "cliff_status":   cliff_status,
        "signal":         signal,
        "signal_drivers": [SIGNAL_DRIVERS[signal]],
        "caveats":        caveats,
        "decision_supported": False,
    }
    return audited


async def run_audit() -> dict:
    players = await get_my_roster()
    audited = [audit_player(p) for p in players]
    audited = [a for a in audited if a is not None]
    audited.sort(key=lambda p: p["years_to_cliff"])
    return {
        "status": "experimental",
        "engine": ENGINE,
        "decision_supported": False,
        "reason": NOT_DECISION_GRADE_REASON,
        "caveats": ROSTER_CAVEATS,
        "players": audited,
    }
