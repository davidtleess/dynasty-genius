"""DG-121 — /api/health carries the served bundle's two facts, and no verdict.

The presentation is a live design question (David, 2026-09-04: status is "glyphs
and symbols, not full sentences"), so the endpoint publishes FACTS and leaves the
word to whatever he picks. A status enum here would have to collapse two
independent axes into one dimension and would pre-commit that choice.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

import app.api.routes.system_health as health_route
from app.main import app as main_app

_VERDICT_WORDS = re.compile(
    r"\b(current|drifted|drift|stale|fresh|dirty|healthy|ok_bundle|out_of_date)\b"
)


def _body() -> dict:
    response = TestClient(main_app).get("/api/health")
    assert response.status_code == 200, response.text
    return response.json()


def test_health_publishes_both_axes():
    served = _body()["served_bundle"]
    assert set(served) == {"bundle_vs_checkout", "checkout_vs_origin"}
    assert set(served["bundle_vs_checkout"]) == {
        "manifest_present",
        "manifest_source_sha",
        "manifest_source_dirty",
        "manifest_built_at",
        "manifest_sha_known_to_repo",
        "head_sha",
        "sha_matches_head",
        "commits_head_ahead_of_bundle",
    }
    assert set(served["checkout_vs_origin"]) == {
        "head_sha",
        "remote_ref",
        "remote_sha",
        "commits_behind_remote",
        "remote_last_fetched_at",
    }


def test_the_payload_names_no_verdict_and_no_cause():
    """States and facts only — the design has not been chosen yet."""
    served = _body()["served_bundle"]
    for axis in served.values():
        for key, value in axis.items():
            assert not _VERDICT_WORDS.search(key), key
            if isinstance(value, str):
                assert not _VERDICT_WORDS.search(value.lower()), (key, value)


def test_a_detector_that_raises_cannot_take_the_health_light_down(monkeypatch):
    """Guard-of-guards, the standing rule on this endpoint: a crashing check
    reads as unknown and can never 500 the light or leak exception text."""
    def _boom(*_args, **_kwargs):
        raise RuntimeError("secret path /Users/someone/private")

    monkeypatch.setattr(health_route, "bundle_vs_checkout", _boom)
    monkeypatch.setattr(health_route, "checkout_vs_origin", _boom)
    response = TestClient(main_app).get("/api/health")

    assert response.status_code == 200
    assert "secret path" not in response.text
    served = response.json()["served_bundle"]
    assert served["bundle_vs_checkout"]["manifest_present"] is False
    assert served["bundle_vs_checkout"]["sha_matches_head"] is None
    assert served["checkout_vs_origin"]["commits_behind_remote"] is None


def test_the_facts_are_required_by_the_contract():
    schemas = main_app.openapi()["components"]["schemas"]
    assert "served_bundle" in schemas["SystemHealthResponse"]["required"]
    assert set(schemas["ServedBundleFacts"]["required"]) == {
        "bundle_vs_checkout",
        "checkout_vs_origin",
    }
    for name in ("BundleVsCheckout", "CheckoutVsOrigin"):
        assert name in schemas
