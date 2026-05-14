"""Phase 9.5 contract tests: prospect identity resolver.

Verifies the three-stage resolution path:
  Stage 1 — explicit sleeper_id on request
  Stage 2 — alias bridge lookup
  Stage 3 — unresolved: log to review file, return None
"""
from __future__ import annotations

import json

import pytest

import src.dynasty_genius.adapters.prospect_identity_resolver as resolver_mod
from src.dynasty_genius.adapters.prospect_identity_resolver import (
    normalize_name,
    resolve_prospect_sleeper_id,
)

_FIXTURE_ENTRY = {
    "dg_name": "Carnell Tate",
    "normalized_name": "carnell tate",
    "position": "WR",
    "draft_class": 2026,
    "sleeper_id": "13279",
    "verification": "sleeper_api_confirmed",
}


@pytest.fixture(autouse=True)
def _reset_bridge_cache():
    resolver_mod._bridge_cache = None
    yield
    resolver_mod._bridge_cache = None


@pytest.fixture
def bridge_file(tmp_path):
    f = tmp_path / "prospect_alias_bridge.json"
    f.write_text(json.dumps({
        "bridge_version": "test",
        "notes": "contract-test fixture",
        "entries": [_FIXTURE_ENTRY],
    }))
    return f


@pytest.fixture
def review_log(tmp_path):
    return tmp_path / "review.jsonl"


# ── Test 1: normalize_name strips punctuation and lowercases ──────────────────

def test_normalize_name_strips_punctuation_and_lowercases():
    assert normalize_name("Carnell Tate") == "carnell tate"
    assert normalize_name("Fernando Mendoza") == "fernando mendoza"
    assert normalize_name("Omar Cooper Jr.") == "omar cooper jr"
    assert normalize_name("Chris Brazzell II") == "chris brazzell ii"


# ── Test 2: normalize_name removes apostrophes ────────────────────────────────

def test_normalize_name_removes_apostrophes():
    assert normalize_name("De'Zhaun Stribling") == "dezhaun stribling"
    assert normalize_name("Ja'Kobi Lane") == "jakobi lane"


# ── Test 3: Stage 1 — explicit sleeper_id bypasses bridge ────────────────────

def test_explicit_sleeper_id_bypasses_bridge(bridge_file, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    sid, method = resolve_prospect_sleeper_id(
        "Anyone", "RB", 2026, explicit_sleeper_id="9999"
    )
    assert sid == "9999"
    assert method == "explicit"


# ── Test 4: Stage 2 — alias bridge hit returns correct sleeper_id ─────────────

def test_alias_bridge_hit_returns_sleeper_id(bridge_file, review_log, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    monkeypatch.setattr(resolver_mod, "_REVIEW_LOG", review_log)
    sid, method = resolve_prospect_sleeper_id("Carnell Tate", "WR", 2026)
    assert sid == "13279"
    assert method == "alias_bridge"
    assert not review_log.exists()


# ── Test 5: Stage 2 — misspelled name falls through, no fuzzy match ──────────

def test_alias_bridge_miss_on_misspelled_name(bridge_file, review_log, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    monkeypatch.setattr(resolver_mod, "_REVIEW_LOG", review_log)
    sid, method = resolve_prospect_sleeper_id("Carnel Tate", "WR", 2026)
    assert sid is None
    assert method == "unresolved_logged"


# ── Test 6: Stage 3 — unresolved miss writes review log entry ────────────────

def test_unresolved_miss_writes_review_log(bridge_file, review_log, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    monkeypatch.setattr(resolver_mod, "_REVIEW_LOG", review_log)
    resolve_prospect_sleeper_id("Unknown Prospect", "TE", 2026)
    assert review_log.exists()
    lines = review_log.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["name"] == "Unknown Prospect"
    assert entry["position"] == "TE"
    assert entry["draft_class"] == 2026
    assert entry["sleeper_id_resolved"] is None
    assert entry["stage_reached"] == "alias_bridge_miss"


# ── Test 7: Stage 3 — two misses append two lines ────────────────────────────

def test_two_misses_append_two_review_lines(bridge_file, review_log, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    monkeypatch.setattr(resolver_mod, "_REVIEW_LOG", review_log)
    resolve_prospect_sleeper_id("Unknown Player A", "RB", 2026)
    resolve_prospect_sleeper_id("Unknown Player B", "WR", 2026)
    lines = review_log.read_text().strip().splitlines()
    assert len(lines) == 2


# ── Test 8: Integration — _map_prospect_to_pvo sets pvo.sleeper_id ────────────

def test_map_prospect_to_pvo_sets_sleeper_id_from_bridge(bridge_file, review_log, monkeypatch):
    monkeypatch.setattr(resolver_mod, "_BRIDGE_FILE", bridge_file)
    monkeypatch.setattr(resolver_mod, "_REVIEW_LOG", review_log)
    from app.api.routes.rookies import ProspectRequest, _map_prospect_to_pvo
    prospect = ProspectRequest(
        name="Carnell Tate", position="WR", pick=4, round=1, age=21.0
    )
    pvo = _map_prospect_to_pvo(prospect)
    assert pvo.sleeper_id == "13279"
