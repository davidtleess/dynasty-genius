from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.research_market_ranks import router


def test_disabled_and_configured_failure(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    monkeypatch.delenv("DG_MARKET_RANKS_MANIFEST", raising=False)
    assert client.get("/api/research/market-ranks").json() == {
        "status": "not_configured"
    }
    for path in ("", "relative.json", "/definitely-missing-dg183.json"):
        monkeypatch.setenv("DG_MARKET_RANKS_MANIFEST", path)
        response = client.get("/api/research/market-ranks")
        assert response.status_code == 503
        assert "No older scores" in response.json()["detail"]
