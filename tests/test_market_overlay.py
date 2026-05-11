"""Market overlay governance tests.

Covers FantasyCalc, DynastyDataLab, and DynastyNerds.

Enforces:
- All three are market_overlay only — never model inputs or training labels.
- No market overlay source provides fields in ALLOWED_ENRICHMENT_COLUMNS.
- FantasyCalc is the primary market signal (free API, actual trade data).
- FantasyCalc freshness is 24h — stale cache must be flagged, not silently used.
- DynastyDataLab and DynastyNerds are deferred (no clean API / cost concern).

API integration tests are skipped until market overlay adapter is implemented.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_a_contract import ALLOWED_ENRICHMENT_COLUMNS
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

MARKET_OVERLAY_SOURCES = {"fantasycalc", "dynasty_data_lab", "dynasty_nerds"}


def test_all_market_overlay_sources_have_market_overlay_role():
    for name in MARKET_OVERLAY_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "market_overlay" in src.roles, (
            f"Source '{name}' must have market_overlay role. Got: {src.roles}"
        )


def test_no_market_overlay_source_is_model_input():
    for name in MARKET_OVERLAY_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "model_input" not in src.roles, (
            f"Source '{name}' must not be model_input. "
            "Market values are price discovery, not truth — they must never enter "
            "Engine A or Engine B training features."
        )


def test_no_market_overlay_source_is_training_label():
    for name in MARKET_OVERLAY_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "training_label" not in src.roles, (
            f"Source '{name}' must not be training_label. Market prices cannot be "
            "prediction targets — they reflect consensus bias, not ground truth outcomes."
        )


def test_market_overlay_sources_have_no_enrichment_column_overlap():
    """Market overlay sources must not provide columns that could reach Engine A/B features."""
    for name in MARKET_OVERLAY_SOURCES:
        src = SOURCE_REGISTRY[name]
        overlap = set(src.allowed_fields) & ALLOWED_ENRICHMENT_COLUMNS
        assert not overlap, (
            f"Source '{name}' allowed_fields overlaps with ALLOWED_ENRICHMENT_COLUMNS: {overlap}. "
            "Market overlay fields must be physically separated from model feature space."
        )


def test_fantasycalc_is_primary_market_signal():
    """FantasyCalc is the active market source — verify it has correct freshness and cache policy."""
    fc = SOURCE_REGISTRY["fantasycalc"]
    assert fc.freshness_hours == 24, (
        f"FantasyCalc freshness_hours must be 24. Got: {fc.freshness_hours}. "
        "Market values decay quickly — stale data must be flagged."
    )
    assert fc.cache_policy == "json_cache"
    assert fc.failure_behavior == "use_cached", (
        "FantasyCalc must degrade gracefully to cache on API failure — "
        "market overlay is non-blocking."
    )


def test_deferred_market_sources_have_no_cache_policy():
    """DynastyDataLab and DynastyNerds are deferred — they should not have active cache pipelines."""
    for name in {"dynasty_data_lab", "dynasty_nerds"}:
        src = SOURCE_REGISTRY[name]
        assert src.cache_policy == "none", (
            f"Deferred source '{name}' must have cache_policy='none'. "
            f"Got: '{src.cache_policy}'. Build the adapter before wiring the cache."
        )


@pytest.mark.skip(reason="FantasyCalc adapter not yet implemented — Phase 2")
def test_fantasycalc_api_returns_expected_schema():
    pass


@pytest.mark.skip(reason="Market overlay join not yet implemented — Phase 2")
def test_market_overlay_values_do_not_appear_in_engine_a_feature_rows():
    pass
