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


# ── Phase 9 schema tests ──────────────────────────────────────────────────────

from src.dynasty_genius.models.player_value_object import MarketOverlay


def test_market_overlay_schema_has_divergence_fields():
    overlay = MarketOverlay(
        market_value=10503.0,
        trend_delta=-39.0,
        model_percentile=0.90,
        market_percentile=0.95,
        model_minus_market_delta=-0.05,
        divergence_flag="aligned",
        market_volatility=0.0,
        position_rank=1,
        overall_rank=1,
        source_timestamp="2026-05-13T18:30:00Z",
    )
    assert overlay.source == "fantasycalc"
    assert overlay.divergence_flag == "aligned"
    assert overlay.model_percentile == 0.90
    assert overlay.market_volatility == 0.0
    assert "source_timestamp_is_fetch_time_not_publish_time" not in overlay.caveats


def test_market_overlay_default_source_is_fantasycalc():
    overlay = MarketOverlay()
    assert overlay.source == "fantasycalc"


def test_ktc_market_source_raises_not_implemented():
    from src.dynasty_genius.adapters.market_source import KTCMarketSource
    source = KTCMarketSource()
    with pytest.raises(NotImplementedError, match="KTC"):
        source.fetch()


def test_fantasycalc_market_source_is_subclass_of_market_source():
    from src.dynasty_genius.adapters.market_source import MarketSource, FantasyCalcMarketSource
    assert issubclass(FantasyCalcMarketSource, MarketSource)


# ── Phase 9 adapter tests ─────────────────────────────────────────────────────

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

FIXTURE_PATH = Path("tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json")


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


def test_adapter_url_includes_sf_params():
    from src.dynasty_genius.adapters.fantasycalc_adapter import API_URL
    assert "numQbs=2" in API_URL, "Missing numQbs=2 — QB values will be wrong in Superflex"
    assert "numTeams=12" in API_URL
    assert "ppr=1" in API_URL
    assert "isDynasty=true" in API_URL


def test_normalize_entry_captures_sleeper_id():
    from src.dynasty_genius.adapters.fantasycalc_adapter import normalize_fantasycalc_entry
    raw = _load_fixture()[0]  # Bijan Robinson
    result = normalize_fantasycalc_entry(raw)
    assert result["sleeper_id"] == "9509"
    assert result["market_value"] == 10503
    assert result["trend_delta"] == -39
    assert result["position"] == "RB"
    assert result["overall_rank"] == 1
    assert result["position_rank"] == 1
    assert result["market_volatility"] == 0.0


def test_normalize_entry_excludes_banned_fields():
    from src.dynasty_genius.adapters.fantasycalc_adapter import normalize_fantasycalc_entry
    raw = _load_fixture()[0]
    result = normalize_fantasycalc_entry(raw)
    assert "combinedValue" not in result
    assert "redraftValue" not in result
    assert "redraftDynastyValueDifference" not in result


def test_fetch_with_cache_stage3_cold_fail(tmp_path, monkeypatch):
    """Stage 3: no cache + API failure → empty list + market_data_unavailable caveat."""
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        tmp_path / "nonexistent.json",
    )
    with patch("httpx.get", side_effect=Exception("network error")):
        from src.dynasty_genius.adapters import fantasycalc_adapter
        data, caveats = fantasycalc_adapter.fetch_with_cache()
    assert data == []
    assert "market_data_unavailable" in caveats


def test_fetch_with_cache_stage2_stale_serve(tmp_path, monkeypatch):
    """Stage 2: expired cache + API failure → stale data + stale_market_data caveat."""
    from datetime import datetime, timedelta

    old_ts = (datetime.utcnow() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_file = tmp_path / "market_values.json"
    cache_file.write_text(json.dumps({
        "fetched_at": old_ts,
        "ttl_hours": 24,
        "data": _load_fixture(),
    }))
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        cache_file,
    )
    with patch("httpx.get", side_effect=Exception("network error")):
        from src.dynasty_genius.adapters import fantasycalc_adapter
        data, caveats = fantasycalc_adapter.fetch_with_cache()
    assert len(data) == 6
    assert "stale_market_data" in caveats
    assert any("fetched_at=" in c for c in caveats)
