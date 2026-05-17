"""Phase 9 contract tests: market_overlay shape and governance on all surfaces.

Verifies:
1.  FC adapter returns correct shape with sleeper_id present.
2.  combinedValue and redraftValue absent from overlay.
3.  divergence_flag is one of the five valid values.
4.  TE always receives divergence_flag == "model_unreliable".
5.  Rookie with no projection receives divergence_flag == "model_uninformative_rookie".
6.  RB age 26+ with model_higher_than_market receives rb_cliff_watch caveat.
7.  market_overlay is None when FC response is empty.
8.  source_timestamp_is_fetch_time_not_publish_time always present when overlay exists.
9.  source_timestamp_is_fetch_time_not_publish_time always present when overlay exists.
10. market_overlay.source == "fantasycalc" on all surfaces.
11. No banned fields (action, verdict, dynasty_tier, confidence) in surface responses.
12. model_percentile and market_percentile both present when divergence computed.
13. market_value matches the fixture value for a known player.
14. market_overlay fields combinedValue, redraftValue not stored.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.models.player_value_object import MarketOverlay, PlayerValueObject
from src.dynasty_genius.services.market_overlay_service import compute_divergence

FIXTURE = json.loads(
    Path("tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json").read_text()
)

BANNED_FIELDS = {"action", "verdict", "dynasty_tier", "confidence", "my_total", "their_total"}
VALID_FLAGS = {
    "aligned",
    "model_higher_than_market",
    "model_lower_than_market",
    "model_unreliable",
    "model_uninformative_rookie",
}


def _pvo(
    sleeper_id: str,
    position: str,
    projection_2y: float | None,
    model_grade: str = "ACTIVE_B",
    age: float = 25.0,
    is_prospect: bool = False,
) -> PlayerValueObject:
    return PlayerValueObject(
        player_id=f"dg_{sleeper_id}",
        full_name=f"Test {position}",
        position=position,
        sleeper_id=sleeper_id,
        signal_completeness=0.8,
        projection_2y=projection_2y,
        model_grade=model_grade,
        age=age,
        is_prospect=is_prospect,
    )


# ── Test 1: FC adapter shape ──────────────────────────────────────────────────

def test_adapter_normalized_entry_has_sleeper_id():
    from src.dynasty_genius.adapters.fantasycalc_adapter import normalize_fantasycalc_entry
    result = normalize_fantasycalc_entry(FIXTURE[0])
    assert "sleeper_id" in result
    assert result["sleeper_id"] == "9509"


# ── Test 2: Banned FC fields absent ──────────────────────────────────────────

def test_normalized_entry_excludes_combined_and_redraft_values():
    from src.dynasty_genius.adapters.fantasycalc_adapter import normalize_fantasycalc_entry
    result = normalize_fantasycalc_entry(FIXTURE[0])
    assert "combinedValue" not in result
    assert "redraftValue" not in result
    assert "redraftDynastyValueDifference" not in result


# ── Test 3: divergence_flag is always a valid value ───────────────────────────

def _rb_cohort(pvo: PlayerValueObject) -> list[PlayerValueObject]:
    """Pad to MIN_COHORT_SIZE so percentile math fires."""
    return [pvo] + [
        _pvo(f"NOFCMATCH_{i}", "RB", float(10 + i))
        for i in range(4)
    ]


def test_divergence_flag_is_valid_for_scored_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence(_rb_cohort(pvo), FIXTURE)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag in VALID_FLAGS


# ── Test 4: TE forced to model_unreliable ────────────────────────────────────

def test_te_divergence_flag_is_model_unreliable():
    pvo = _pvo("8888", "TE", 9.0, model_grade="EXPERIMENTAL")
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag == "model_unreliable"


# ── Test 5: Rookie with no projection ────────────────────────────────────────

def test_rookie_no_projection_gets_model_uninformative_flag():
    pvo = _pvo("11111", "WR", None, is_prospect=True)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag == "model_uninformative_rookie"


# ── Test 6: RB cliff watch ────────────────────────────────────────────────────

def test_rb_cliff_watch_caveat_when_model_above_market_at_27():
    veteran = _pvo("6543", "RB", 20.0, age=27.5)
    younger = _pvo("9509", "RB", 10.0, age=24.2)
    # Pad to MIN_COHORT_SIZE
    cohort = [veteran, younger] + [
        _pvo(f"NOFCMATCH_{i}", "RB", float(8 + i))
        for i in range(3)
    ]
    compute_divergence(cohort, FIXTURE)
    assert veteran.market_overlay is not None
    if veteran.market_overlay.divergence_flag == "model_higher_than_market":
        assert "rb_cliff_watch" in veteran.market_overlay.caveats


# ── Test 7: No FC data → overlay stays None ───────────────────────────────────

def test_no_fc_data_leaves_overlay_none():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], [])  # empty FC response
    assert pvo.market_overlay is None


# ── Test 8: source_timestamp caveat always present ────────────────────────────

def test_source_timestamp_caveat_always_on_overlay():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is not None
    assert "source_timestamp_is_fetch_time_not_publish_time" in pvo.market_overlay.caveats


# ── Test 9: source_timestamp on TE overlay too ───────────────────────────────

def test_source_timestamp_caveat_on_te_overlay():
    pvo = _pvo("8888", "TE", 9.0, model_grade="EXPERIMENTAL")
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is not None
    assert "source_timestamp_is_fetch_time_not_publish_time" in pvo.market_overlay.caveats


# ── Test 10: source == "fantasycalc" ──────────────────────────────────────────

def test_overlay_source_is_fantasycalc():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay.source == "fantasycalc"


# ── Test 11: No banned output fields ─────────────────────────────────────────

def test_no_banned_fields_in_overlay_model_dump():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    dumped = pvo.dict()
    found = BANNED_FIELDS & set(dumped.keys())
    assert not found, f"Banned fields found: {found}"


# ── Test 12: model_percentile and market_percentile both present ──────────────

def test_both_percentiles_present_for_scored_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence(_rb_cohort(pvo), FIXTURE)
    assert pvo.market_overlay.model_percentile is not None
    assert pvo.market_overlay.market_percentile is not None


# ── Test 13: market_value matches fixture ────────────────────────────────────

def test_market_value_matches_fixture_for_known_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay.market_value == 10503


# ── Test 14: combinedValue not stored on overlay ─────────────────────────────

def test_combined_value_not_stored_on_overlay():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    dumped = pvo.market_overlay.dict()
    assert "combinedValue" not in dumped
    assert "redraftValue" not in dumped
