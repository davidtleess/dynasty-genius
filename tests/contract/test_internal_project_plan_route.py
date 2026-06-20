from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_route_returns_plan_ok():
    r = client.get("/api/internal/project-plan")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}  # real seed file present -> ok
    assert "phases" in body and "warnings" in body
    assert body["parser_version"] == "v1"


def test_route_excluded_from_openapi():
    schema = client.get("/openapi.json").json()
    assert "/api/internal/project-plan" not in schema.get("paths", {})


def test_route_accepts_no_path_param():
    # Fixed source only: a path-style suffix must 404 (SPA fallback excludes api/).
    r = client.get("/api/internal/project-plan/etc/passwd")
    assert r.status_code == 404


def test_route_degrades_when_source_missing(monkeypatch, tmp_path):
    import app.api.routes.internal_project_plan as mod

    monkeypatch.setattr(mod, "PROJECT_PLAN_PATH", tmp_path / "absent.json")
    r = client.get("/api/internal/project-plan")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"
    assert "project_plan_source_missing" in r.json()["warnings"]
