import os
from typing import Optional

import httpx

from app.data.sleeper import get_user, get_leagues, get_rosters, get_all_players
from app.utils.compliance import RANK_1_GROUND_TRUTH, calculate_compliance_ratio

USERNAME_ENV = "DYNASTY_SLEEPER_USERNAME"
LEAGUE_ID_ENV = "DYNASTY_SLEEPER_LEAGUE_ID"
LEAGUE_NAME_ENV = "DYNASTY_SLEEPER_LEAGUE_NAME"
SEASON_ENV = "DYNASTY_SEASON"

CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}
ELITE_RB_YAC_PER_ATTEMPT = 3.0
SKILL_POSITIONS = set(CLIFF_AGES.keys())
ENGINE = "roster_age_curve_auditor"
ROSTER_CAVEATS = ["age_curve_only", "no_usage_signal", "no_market_overlay"]
SIGNAL_DRIVERS = {
    "past_cliff": "age_past_position_cliff",
    "at_cliff": "age_at_position_cliff",
    "approaching_cliff": "age_within_two_years_of_position_cliff",
    "no_age_signal": "age_not_near_position_cliff",
    "elite_exception_hold": "elite_yards_after_contact_exception",
}
NOT_DECISION_GRADE_REASON = (
    "Roster audit is age-curve-only until Engine B usage, efficiency, and market "
    "signals are available."
)
ASSET_SIGNAL_LIQUIDATE = "LIQUIDATE"
ASSET_SIGNAL_ELITE_HOLD = "ELITE_HOLD"


class RosterConfigError(ValueError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RosterConfigError(f"Missing required environment variable: {name}")
    return value


def _roster_config() -> dict:
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


async def get_my_roster() -> list[dict]:
    config = _roster_config()
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
    yac_per_attempt = player.get("yards_after_contact_per_attempt")
    if yac_per_attempt is None:
        yac_per_attempt = player.get("yac_per_attempt")

    elite_rb_exception = (
        position == "RB"
        and years_to_cliff <= 0
        and yac_per_attempt is not None
        and float(yac_per_attempt) >= ELITE_RB_YAC_PER_ATTEMPT
    )

    if elite_rb_exception:
        cliff_status = "Elite Exception: HOLD"
        signal = "elite_exception_hold"
        asset_management_signal = ASSET_SIGNAL_ELITE_HOLD
    elif years_to_cliff < 0:
        cliff_status = "Past cliff"
        signal = "past_cliff"
        asset_management_signal = ASSET_SIGNAL_LIQUIDATE
    elif years_to_cliff == 0:
        cliff_status = "At cliff"
        signal = "at_cliff"
        asset_management_signal = ASSET_SIGNAL_LIQUIDATE
    elif years_to_cliff <= 2:
        cliff_status = "Approaching"
        signal = "approaching_cliff"
        asset_management_signal = None
    else:
        cliff_status = "No age signal"
        signal = "no_age_signal"
        asset_management_signal = None

    compliance_metrics = [
        {
            "name": "age_curve",
            "kind": "quantitative",
            "source_rank": RANK_1_GROUND_TRUTH,
            "weight": 1.0,
        }
    ]
    if yac_per_attempt is not None:
        compliance_metrics.append(
            {
                "name": "yards_after_contact_per_attempt",
                "kind": "quantitative",
                "source_rank": RANK_1_GROUND_TRUTH,
                "weight": 1.0,
            }
        )

    return {
        **player,
        "compliance_header": calculate_compliance_ratio(compliance_metrics, []),
        "cliff_age":      cliff_age,
        "years_to_cliff": years_to_cliff,
        "cliff_status":   cliff_status,
        "signal":         signal,
        "asset_management_signal": asset_management_signal,
        "signal_drivers": [SIGNAL_DRIVERS[signal]],
        "elite_exception_thresholds": {
            "rb_yards_after_contact_per_attempt_top_decile": ELITE_RB_YAC_PER_ATTEMPT,
        } if elite_rb_exception else None,
        "caveats":        [
            *ROSTER_CAVEATS,
            *(["elite_exception_requires_current_yac_verification"] if elite_rb_exception else []),
        ],
        "decision_supported": False,
    }


async def run_audit() -> dict:
    players = await get_my_roster()
    audited = [audit_player(p) for p in players]
    audited = [a for a in audited if a is not None]
    audited.sort(key=lambda p: p["years_to_cliff"])
    return {
        "compliance_header": calculate_compliance_ratio(
            [
                {
                    "name": "roster_age_curve_audit",
                    "kind": "quantitative",
                    "source_rank": RANK_1_GROUND_TRUTH,
                    "weight": 1.0,
                }
            ],
            [],
        ),
        "status": "experimental",
        "engine": ENGINE,
        "decision_supported": False,
        "reason": NOT_DECISION_GRADE_REASON,
        "caveats": ROSTER_CAVEATS,
        "players": audited,
    }
