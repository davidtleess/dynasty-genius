"""Dashboard contract verification.

Checks:
1. All live cards are PRE_MODEL.
2. market_overlay is null on every card.
3. No banned recommendation words in caveats or risk_flags.
4. Card count in JSON matches the JS artifact.
5. A fixture with internal_value produces non-null biological_debt_score.
6. A fixture with roster_context produces non-null liquidity_risk.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CARDS_JSON = ROOT / "resources" / "live_roster_cards.json"
CARDS_JS   = ROOT / "resources" / "roster_audit_cards.js"

BANNED_WORDS = re.compile(
    r"\b(buy|sell|hold|verdict|recommend|dynasty_tier|trade_verdict|action)\b",
    re.IGNORECASE,
)


@pytest.fixture
def cards() -> list[dict]:
    return json.loads(CARDS_JSON.read_text())


# ── 1. All PRE_MODEL ─────────────────────────────────────────────────────────

def test_all_cards_pre_model(cards):
    bad = [c["full_name"] for c in cards if c.get("model_grade") != "PRE_MODEL"]
    assert not bad, f"Non-PRE_MODEL cards: {bad}"


# ── 2. No market overlay ─────────────────────────────────────────────────────

def test_no_market_overlay(cards):
    bad = [c["full_name"] for c in cards if c.get("market_overlay") is not None]
    assert not bad, f"Cards with market_overlay: {bad}"


# ── 3. No banned recommendation words ────────────────────────────────────────

def test_no_banned_words(cards):
    hits = []
    for c in cards:
        for text in (c.get("caveats") or []) + (c.get("risk_flags") or []):
            if BANNED_WORDS.search(text):
                hits.append((c["full_name"], text))
    assert not hits, f"Banned words found: {hits}"


# ── 4. JS artifact matches JSON artifact (content parity, not just count) ────

def test_js_artifact_matches_json(cards):
    js_text = CARDS_JS.read_text()
    match = re.search(r"window\.ROSTER_AUDIT_CARDS\s*=\s*(\[.*\]);", js_text, re.DOTALL)
    assert match, "Could not parse ROSTER_AUDIT_CARDS from JS artifact"
    js_cards = json.loads(match.group(1))

    assert len(js_cards) == len(cards), (
        f"JS artifact has {len(js_cards)} cards, JSON has {len(cards)}"
    )

    # Index both by player_id so order differences don't mask stale content.
    json_by_id = {c["player_id"]: c for c in cards}
    js_by_id   = {c["player_id"]: c for c in js_cards}

    extra   = set(js_by_id) - set(json_by_id)
    missing = set(json_by_id) - set(js_by_id)
    assert not extra,   f"Players in JS but not JSON: {extra}"
    assert not missing, f"Players in JSON but not JS: {missing}"

    drift = []
    for pid, json_card in json_by_id.items():
        js_card = js_by_id[pid]
        if json_card != js_card:
            drift.append(json_card.get("full_name", pid))
    assert not drift, (
        f"JS artifact content diverges from JSON for: {drift}. "
        "Re-run scripts/build_live_roster.py to regenerate both artifacts."
    )


# ── 5. Biological debt non-null when internal_value is provided ───────────────

def test_biological_debt_non_null_with_internal_value():
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    identity = PlayerIdentity(
        dg_id=generate_dg_id("Test Player", "RB"),
        full_name="Test Player",
        position="RB",
        nfl_team="KC",
    )
    features = {"age": 25.0, "dynasty_value_score": 100.0}
    pvo = assemble_pvo(identity, features, is_prospect=False)

    assert pvo.roster_audit is not None
    assert pvo.roster_audit.biological_debt_score is not None, (
        "biological_debt_score should be non-null when dynasty_value_score is provided"
    )
    # RB age 25, cliff 26: risk = (25-23)/3 ≈ 0.6667; debt = 0.6667 * 100 ≈ 66.67
    assert pvo.roster_audit.biological_debt_score == pytest.approx(66.67, abs=0.01)


# ── 6. Liquidity risk non-null when roster_context is provided ────────────────

def test_liquidity_risk_non_null_with_roster_context():
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    identity = PlayerIdentity(
        dg_id=generate_dg_id("Test Player", "WR"),
        full_name="Test Player",
        position="WR",
        nfl_team="KC",
    )
    features = {"age": 24.0}
    roster_context = {"has_2026_2nd": True, "has_2027_2nd": False}
    pvo = assemble_pvo(identity, features, is_prospect=False, roster_context=roster_context)

    assert pvo.roster_audit is not None
    assert pvo.roster_audit.liquidity_risk is not None, (
        "liquidity_risk should be non-null when roster_context is provided"
    )
    assert pvo.roster_audit.liquidity_risk == "MEDIUM_LIMITED_ESCAPE_HATCH"
