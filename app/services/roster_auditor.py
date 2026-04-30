from typing import Optional

from app.data.sleeper import get_user, get_leagues, get_rosters, get_all_players

MY_USERNAME = "Dleess"
MY_LEAGUE_NAME = "Redzone Champions League"
SEASON = "2025"

CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}
SKILL_POSITIONS = set(CLIFF_AGES.keys())


async def get_my_roster() -> list[dict]:
    user = await get_user(MY_USERNAME)
    user_id = user["user_id"]

    leagues = await get_leagues(user_id, SEASON)
    league = next(
        (lg for lg in leagues if lg["name"] == MY_LEAGUE_NAME),
        leagues[0],
    )
    league_id = league["league_id"]

    rosters = await get_rosters(league_id)
    my_roster = next(r for r in rosters if r["owner_id"] == user_id)

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

    if years_to_cliff < 0:
        cliff_status = "Past cliff"
        action = "Sell now"
    elif years_to_cliff == 0:
        cliff_status = "At cliff"
        action = "Shop actively"
    elif years_to_cliff <= 2:
        cliff_status = "Approaching"
        action = "Monitor"
    else:
        cliff_status = "Safe"
        action = "Hold"

    return {
        **player,
        "cliff_age":      cliff_age,
        "years_to_cliff": years_to_cliff,
        "cliff_status":   cliff_status,
        "action":         action,
    }


async def run_audit() -> list[dict]:
    players = await get_my_roster()
    audited = [audit_player(p) for p in players]
    audited = [a for a in audited if a is not None]
    audited.sort(key=lambda p: p["years_to_cliff"])
    return audited
