"""Governance contract tests for the 2026 Rookie Board.

Tests HTML structure, banned directive language, artifact shapes,
and parity between the verified prospect manifest and generated cards.
Artifact-dependent tests are skipped if the artifact does not exist yet.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOARD_HTML     = ROOT / "src" / "dynasty_genius" / "dashboard" / "rookie_board.html"
CARDS_JS       = ROOT / "resources" / "prospect_cards.js"
CARDS_JSON     = ROOT / "resources" / "prospect_cards.json"
DRAFT_STATE_JS = ROOT / "resources" / "draft_state.js"
ROSTER_NEED_JS = ROOT / "resources" / "roster_need_signals.js"
IDENTITY_2026  = ROOT / "resources" / "prospect_identity_2026.json"

BANNED_PHRASES = [
    "draft target",
    "draft this",
    "trade candidate",
    "verdict",
    "confidence",
]

# ── HTML structure ─────────────────────────────────────────────────────────────

def test_board_loads_prospect_cards_js():
    html = BOARD_HTML.read_text()
    assert "prospect_cards.js" in html


def test_board_loads_draft_state_js():
    html = BOARD_HTML.read_text()
    assert "draft_state.js" in html


def test_board_loads_roster_need_js():
    html = BOARD_HTML.read_text()
    assert "roster_need_signals.js" in html


def test_board_displays_decision_supported_false():
    html = BOARD_HTML.read_text()
    assert "decision_supported: false" in html


# ── Banned directive language ──────────────────────────────────────────────────

@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_board_html_no_banned_phrase(phrase):
    html = BOARD_HTML.read_text().lower()
    assert phrase.lower() not in html, f"Banned phrase in board HTML: {phrase!r}"


@pytest.mark.skipif(not CARDS_JS.exists(), reason="prospect_cards.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_prospect_cards_js_no_banned_phrase(phrase):
    body = CARDS_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in prospect_cards.js: {phrase!r}"


@pytest.mark.skipif(not DRAFT_STATE_JS.exists(), reason="draft_state.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_draft_state_js_no_banned_phrase(phrase):
    body = DRAFT_STATE_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in draft_state.js: {phrase!r}"


@pytest.mark.skipif(not ROSTER_NEED_JS.exists(), reason="roster_need_signals.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_roster_need_js_no_banned_phrase(phrase):
    body = ROSTER_NEED_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in roster_need_signals.js: {phrase!r}"


# ── prospect_cards.json governance ────────────────────────────────────────────

@pytest.mark.skipif(not CARDS_JSON.exists(), reason="prospect_cards.json not yet generated")
def test_all_cards_have_decision_supported_false():
    cards = json.loads(CARDS_JSON.read_text())
    assert cards, "prospect_cards.json is empty"
    failures = [c["full_name"] for c in cards if c.get("decision_supported") is not False]
    assert not failures, f"Cards missing decision_supported: false -> {failures}"


@pytest.mark.skipif(not CARDS_JSON.exists(), reason="prospect_cards.json not yet generated")
def test_all_2026_cards_have_sleeper_id():
    cards = json.loads(CARDS_JSON.read_text())
    class_2026 = [c for c in cards if c.get("draft_class") == 2026]
    missing = [c["full_name"] for c in class_2026 if not c.get("sleeper_id")]
    assert not missing, f"2026 prospects missing sleeper_id -> {missing}"


# ── Parity: manifest vs generated cards ───────────────────────────────────────

@pytest.mark.skipif(
    not (CARDS_JSON.exists() and IDENTITY_2026.exists()),
    reason="artifacts not yet generated",
)
def test_all_2026_manifest_players_have_cards():
    cards = json.loads(CARDS_JSON.read_text())
    manifest = json.loads(IDENTITY_2026.read_text())
    manifest_names = {p["full_name"] for p in manifest["players"]}
    card_names = {c["full_name"] for c in cards}
    missing = manifest_names - card_names
    assert not missing, f"In 2026 manifest but not in cards: {missing}"


# ── draft_state.js shape ──────────────────────────────────────────────────────

@pytest.mark.skipif(not DRAFT_STATE_JS.exists(), reason="draft_state.js not yet generated")
def test_draft_state_shape():
    body = DRAFT_STATE_JS.read_text()
    match = re.search(r'window\.DRAFT_STATE\s*=\s*(\{.*?\});', body, re.DOTALL)
    assert match, "window.DRAFT_STATE assignment not found in draft_state.js"
    state = json.loads(match.group(1))
    assert isinstance(state.get("taken"), list), "DRAFT_STATE.taken must be a list"
    assert "refreshed_at" in state, "DRAFT_STATE must carry refreshed_at"
    assert isinstance(state["refreshed_at"], str), "DRAFT_STATE.refreshed_at must be a string"


# ── roster_need_signals.js shape ──────────────────────────────────────────────

@pytest.mark.skipif(not ROSTER_NEED_JS.exists(), reason="roster_need_signals.js not yet generated")
def test_roster_need_shape():
    body = ROSTER_NEED_JS.read_text()
    match = re.search(r'window\.ROSTER_NEED\s*=\s*(\{.*?\});', body, re.DOTALL)
    assert match, "window.ROSTER_NEED assignment not found in roster_need_signals.js"
    need = json.loads(match.group(1))
    valid = {"HIGH", "MEDIUM", "LOW"}
    for pos in ["WR", "RB", "QB", "TE"]:
        assert pos in need, f"ROSTER_NEED missing position: {pos}"
        assert need[pos] in valid, f"ROSTER_NEED[{pos}]={need[pos]!r} not in {valid}"
