from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_trust_surface_exposes_quarantined_model_status():
    response = client.get("/api/trust-surface/WR")
    assert response.status_code == 200
    body = response.json()

    assert body["model_status"] in ("VALIDATED", "PROVISIONAL", "EXPERIMENTAL")
    assert "overall_grade" in body

    def walk(obj):
        if isinstance(obj, dict):
            if "decision_supported" in obj:
                assert obj["decision_supported"] is False
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(body)
