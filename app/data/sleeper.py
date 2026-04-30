import httpx
from typing import Any

BASE_URL = "https://api.sleeper.app/v1"


async def _get(path: str) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{path}")
        response.raise_for_status()
        return response.json()


async def get_user(username: str) -> dict:
    data = await _get(f"/user/{username}")
    if not data:
        raise ValueError(f"No user found for username: {username}")
    return {"user_id": data["user_id"], "display_name": data["display_name"]}


async def get_leagues(user_id: str, season: str) -> list[dict]:
    data = await _get(f"/user/{user_id}/leagues/nfl/{season}")
    if data is None:
        raise ValueError(f"No leagues found for user_id: {user_id}, season: {season}")
    return data


async def get_league(league_id: str) -> dict:
    data = await _get(f"/league/{league_id}")
    if not data:
        raise ValueError(f"No league found for league_id: {league_id}")
    return data


async def get_rosters(league_id: str) -> list[dict]:
    data = await _get(f"/league/{league_id}/rosters")
    if data is None:
        raise ValueError(f"No rosters found for league_id: {league_id}")
    return data


async def get_users(league_id: str) -> list[dict]:
    data = await _get(f"/league/{league_id}/users")
    if data is None:
        raise ValueError(f"No users found for league_id: {league_id}")
    return data


async def get_all_players() -> dict[str, dict]:
    data = await _get("/players/nfl")
    if not data:
        raise ValueError("Failed to retrieve NFL player map")
    return data
