from fastapi.testclient import TestClient

from app.main import app
from app.services import roster_auditor
from src.dynasty_genius.models.league_context import LeagueContext


def test_roster_audit_missing_username_returns_structured_422(monkeypatch) -> None:
    monkeypatch.delenv("DYNASTY_SLEEPER_USERNAME", raising=False)
    monkeypatch.setenv("DYNASTY_SEASON", "2025")
    monkeypatch.setenv("DYNASTY_SLEEPER_LEAGUE_ID", "test-league")

    client = TestClient(app)
    response = client.get("/api/roster/audit")

    assert response.status_code == 422
    payload = response.json()
    assert "detail" in payload
    detail = payload["detail"]
    assert detail["error"] == "roster_config_error"
    assert "DYNASTY_SLEEPER_USERNAME" in detail["message"]


def test_get_my_roster_uses_league_context_without_username_env(monkeypatch) -> None:
    import asyncio

    monkeypatch.delenv("DYNASTY_SLEEPER_USERNAME", raising=False)
    monkeypatch.delenv("DYNASTY_SLEEPER_LEAGUE_ID", raising=False)

    async def fail_user_lookup(username: str) -> dict:
        raise AssertionError("username lookup should not run when LeagueContext is provided")

    async def fake_get_rosters(league_id: str) -> list[dict]:
        assert league_id == "ctx-league"
        return [{"owner_id": "ctx-user", "players": ["p1"]}]

    async def fake_get_all_players() -> dict[str, dict]:
        return {
            "p1": {
                "first_name": "Context",
                "last_name": "Player",
                "position": "WR",
                "team": "MIN",
                "age": 24,
            }
        }

    monkeypatch.setattr(roster_auditor, "get_user", fail_user_lookup)
    monkeypatch.setattr(roster_auditor, "get_rosters", fake_get_rosters)
    monkeypatch.setattr(roster_auditor, "get_all_players", fake_get_all_players)

    context = LeagueContext(
        league_id="ctx-league",
        league_name="Context League",
        season="2026",
        david_user_id="ctx-user",
        david_display_name="David",
        david_roster_id=1,
    )

    players = asyncio.run(roster_auditor.get_my_roster(context))

    assert players == [
        {
            "player_id": "p1",
            "full_name": "Context Player",
            "position": "WR",
            "team": "MIN",
            "age": 24,
        }
    ]
