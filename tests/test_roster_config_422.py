from fastapi.testclient import TestClient

from app.main import app


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
