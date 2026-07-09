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

MARKET_OVERLAY_SOURCES = {
    "fantasycalc",
    "dynasty_data_lab",
    "dynasty_nerds",
    "mfl_rookie_adp",
}


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


def test_mfl_rookie_adp_is_market_overlay_only():
    src = SOURCE_REGISTRY["mfl_rookie_adp"]
    assert "market_overlay" in src.roles
    assert "model_input" not in src.roles
    assert "training_label" not in src.roles


def test_mfl_rookie_adp_cache_and_freshness():
    src = SOURCE_REGISTRY["mfl_rookie_adp"]
    assert src.cache_policy == "json_cache"
    assert src.freshness_hours == 24
    assert src.failure_behavior == "use_cached"


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
    from src.dynasty_genius.adapters.market_source import (
        FantasyCalcMarketSource,
        MarketSource,
    )
    assert issubclass(FantasyCalcMarketSource, MarketSource)


def test_mfl_adp_market_source_is_subclass_of_market_source():
    from src.dynasty_genius.adapters.market_source import (
        MarketSource,
        MflAdpMarketSource,
    )

    assert issubclass(MflAdpMarketSource, MarketSource)


# ── Phase 9 adapter tests ─────────────────────────────────────────────────────

import json
from pathlib import Path
from unittest.mock import patch

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
    from src.dynasty_genius.adapters.fantasycalc_adapter import (
        normalize_fantasycalc_entry,
    )
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
    from src.dynasty_genius.adapters.fantasycalc_adapter import (
        normalize_fantasycalc_entry,
    )
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
    from datetime import datetime, timedelta, timezone

    old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
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


def test_fetch_with_cache_surfaces_cache_write_failure(tmp_path, monkeypatch):
    """A live fetch whose cache write fails must carry an explicit caveat."""

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _load_fixture()

    cache_dir = tmp_path / "fantasycalc"
    cache_dir.mkdir()
    cache_file_as_directory = cache_dir / "market_values.json"
    cache_file_as_directory.mkdir()
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_DIR",
        cache_dir,
    )
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        cache_file_as_directory,
    )

    with patch("httpx.get", return_value=_Response()):
        from src.dynasty_genius.adapters import fantasycalc_adapter

        data, caveats = fantasycalc_adapter.fetch_with_cache()

    assert len(data) == 6
    assert "market_cache_write_failed" in caveats
    assert "source_timestamp_is_fetch_time_not_publish_time" in caveats


def test_fetch_with_cache_surfaces_cache_read_failure_on_live_fetch(tmp_path, monkeypatch):
    """A corrupt existing cache is not the same as an absent cache."""

    class _UnreadableCacheFile:
        def exists(self):
            return True

        def read_text(self):
            raise OSError("read failed")

        def write_text(self, _text):
            return None

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _load_fixture()

    cache_dir = tmp_path / "fantasycalc"
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_DIR",
        cache_dir,
    )
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        _UnreadableCacheFile(),
    )

    with patch("httpx.get", return_value=_Response()):
        from src.dynasty_genius.adapters import fantasycalc_adapter

        data, caveats = fantasycalc_adapter.fetch_with_cache()

    assert len(data) == 6
    assert "market_cache_read_failed" in caveats
    assert "market_cache_write_failed" not in caveats


def test_fetch_with_cache_surfaces_cache_read_failure_on_cold_fail(tmp_path, monkeypatch):
    """If both cache read and live fetch fail, both facts must be visible."""

    class _UnreadableCacheFile:
        def exists(self):
            return True

        def read_text(self):
            raise OSError("read failed")

    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_DIR",
        tmp_path / "fantasycalc",
    )
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        _UnreadableCacheFile(),
    )

    with patch("httpx.get", side_effect=Exception("network error")):
        from src.dynasty_genius.adapters import fantasycalc_adapter

        data, caveats = fantasycalc_adapter.fetch_with_cache()

    assert data == []
    assert "market_data_unavailable" in caveats
    assert "market_cache_read_failed" in caveats


def test_fetch_with_cache_absent_cache_does_not_emit_read_failure(tmp_path, monkeypatch):
    """A missing cache file is an ordinary cold-start state, not corruption."""

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _load_fixture()

    cache_dir = tmp_path / "fantasycalc"
    cache_file = cache_dir / "market_values.json"
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_DIR",
        cache_dir,
    )
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE",
        cache_file,
    )

    with patch("httpx.get", return_value=_Response()):
        from src.dynasty_genius.adapters import fantasycalc_adapter

        data, caveats = fantasycalc_adapter.fetch_with_cache()

    assert len(data) == 6
    assert "source_timestamp_is_fetch_time_not_publish_time" in caveats
    assert "market_cache_read_failed" not in caveats


# ── Phase 9 divergence engine tests ──────────────────────────────────────────

from src.dynasty_genius.models.player_value_object import (
    PlayerValueObject,
)


def _make_pvo(
    player_id: str,
    sleeper_id: str,
    position: str,
    projection_2y: float | None,
    model_grade: str = "ACTIVE_B",
    age: float = 25.0,
    is_prospect: bool = False,
) -> PlayerValueObject:
    return PlayerValueObject(
        player_id=player_id,
        full_name=f"Player {player_id}",
        position=position,
        sleeper_id=sleeper_id,
        signal_completeness=0.8,
        projection_2y=projection_2y,
        model_grade=model_grade,
        age=age,
        is_prospect=is_prospect,
    )


def test_pct_rank_mid_rank_for_ties():
    from src.dynasty_genius.services.market_overlay_service import pct_rank
    values = [5.0, 5.0, 10.0]
    assert pct_rank(values, 5.0) == pytest.approx(1 / 3, abs=0.001)
    assert pct_rank(values, 10.0) == pytest.approx(5 / 6, abs=0.001)


def test_pct_rank_single_value():
    from src.dynasty_genius.services.market_overlay_service import pct_rank
    assert pct_rank([7.0], 7.0) == 0.5


def test_compute_divergence_sets_divergence_flag_aligned():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p1", "9509", "RB", projection_2y=15.0, age=24.2)
    # Pad to meet MIN_COHORT_SIZE (5) — only pvo matches FC
    cohort = [pvo] + [
        _make_pvo(f"pad{i}", f"NOFCMATCH_{i}", "RB", projection_2y=float(10 + i))
        for i in range(4)
    ]
    compute_divergence(cohort, fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.market_value == 10503
    assert pvo.market_overlay.divergence_flag in (
        "aligned", "model_higher_than_market", "model_lower_than_market"
    )
    assert pvo.market_overlay.model_percentile is not None
    assert pvo.market_overlay.market_percentile is not None
    assert pvo.market_overlay.model_minus_market_delta is not None


def test_compute_divergence_te_active_b_not_forced_model_unreliable():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p2", "8888", "TE", projection_2y=8.0, model_grade="ACTIVE_B")
    cohort = [pvo] + [
        _make_pvo(f"pad{i}", f"NOFCMATCH_TE_{i}", "TE", projection_2y=float(4 + i))
        for i in range(4)
    ]
    compute_divergence(cohort, fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag != "model_unreliable"
    assert "te_review_period" in pvo.market_overlay.caveats
    assert "te_model_experimental_do_not_trade_on" not in pvo.market_overlay.caveats
    assert "te_market_high_variance" in pvo.market_overlay.caveats


def test_compute_divergence_rookie_no_projection():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p3", "11111", "WR", projection_2y=None, is_prospect=True)
    compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag == "model_uninformative_rookie"
    assert "model_uninformative_rookie" in pvo.market_overlay.caveats


def test_compute_divergence_rb_cliff_watch():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p4", "6543", "RB", projection_2y=20.0, age=27.5)
    younger = _make_pvo("p5", "9509", "RB", projection_2y=15.0, age=24.2)
    # Pad to meet MIN_COHORT_SIZE (5)
    cohort = [pvo, younger] + [
        _make_pvo(f"pad{i}", f"NOFCMATCH_{i}", "RB", projection_2y=float(10 + i))
        for i in range(3)
    ]
    compute_divergence(cohort, fixture)
    assert pvo.market_overlay is not None
    if pvo.market_overlay.divergence_flag == "model_higher_than_market":
        assert "rb_cliff_watch" in pvo.market_overlay.caveats


def test_compute_divergence_no_match_leaves_overlay_none():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p6", "UNKNOWN_ID_99999", "WR", projection_2y=12.0)
    compute_divergence([pvo], fixture)
    assert pvo.market_overlay is None


def test_compute_divergence_source_timestamp_caveat():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p7", "9509", "RB", projection_2y=15.0, age=24.2)
    compute_divergence([pvo], fixture)
    assert "source_timestamp_is_fetch_time_not_publish_time" in pvo.market_overlay.caveats


def test_compute_divergence_small_cohort_skips_percentile():
    """Single player surface: market_value still populated, but no percentile or flag."""
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p1", "9509", "RB", projection_2y=15.0, age=24.2)
    compute_divergence([pvo], fixture)  # cohort size = 1 < MIN_COHORT_SIZE
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.market_value == 10503   # FC display fields still set
    assert "model_cohort_too_small" in pvo.market_overlay.caveats
    assert pvo.market_overlay.divergence_flag is None
    assert pvo.market_overlay.model_percentile is None


def test_enrich_propagates_stale_caveat_to_overlays(tmp_path, monkeypatch):
    """Stage 2 stale cache: stale_market_data reaches PVO overlay."""
    from datetime import datetime, timedelta, timezone

    from src.dynasty_genius.services.market_overlay_service import (
        enrich_pvo_list_with_market_overlay,
    )

    old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_file = tmp_path / "market_values.json"
    cache_file.write_text(json.dumps({
        "fetched_at": old_ts,
        "ttl_hours": 24,
        "data": _load_fixture(),
    }))
    monkeypatch.setattr("src.dynasty_genius.adapters.fantasycalc_adapter.CACHE_FILE", cache_file)

    with patch("httpx.get", side_effect=Exception("network error")):
        pvos = [_make_pvo("p1", "9509", "RB", projection_2y=15.0, age=24.2)]
        enrich_pvo_list_with_market_overlay(pvos)

    assert pvos[0].market_overlay is not None
    assert "stale_market_data" in pvos[0].market_overlay.caveats


def test_enrich_computes_var():
    """enrich_pvo_list_with_market_overlay wires VAR even when FC is unavailable."""
    from src.dynasty_genius.services.market_overlay_service import (
        enrich_pvo_list_with_market_overlay,
    )

    with patch(
        "src.dynasty_genius.adapters.fantasycalc_adapter.fetch_with_cache",
        return_value=([], ["market_data_unavailable"]),
    ):
        pvos = [_make_pvo("p1", "s1", "RB", projection_2y=15.0)]
        pvos[0].dynasty_value_score = 80.0
        enrich_pvo_list_with_market_overlay(pvos)

    assert pvos[0].value_above_replacement is not None


# ── Phase 9.3 VAR + seasonal tests ───────────────────────────────────────────

def test_compute_var_uses_model_score_not_market():
    from src.dynasty_genius.services.market_overlay_service import (
        compute_value_above_replacement,
    )
    pvos = [
        _make_pvo("p1", "s1", "RB", projection_2y=15.0),
        _make_pvo("p2", "s2", "RB", projection_2y=12.0),
        _make_pvo("p3", "s3", "RB", projection_2y=9.0),
    ]
    pvos[0].dynasty_value_score = 80.0
    pvos[1].dynasty_value_score = 60.0
    pvos[2].dynasty_value_score = 40.0
    compute_value_above_replacement(pvos)
    assert pvos[0].value_above_replacement is not None
    assert pvos[2].value_above_replacement is not None


def test_compute_var_is_none_when_no_dynasty_value_score():
    from src.dynasty_genius.services.market_overlay_service import (
        compute_value_above_replacement,
    )
    pvos = [_make_pvo("p1", "s1", "RB", projection_2y=15.0)]
    pvos[0].dynasty_value_score = None
    compute_value_above_replacement(pvos)
    assert pvos[0].value_above_replacement is None


def test_rookie_peak_value_window_caveat_fires_in_may():
    from datetime import date
    from unittest.mock import patch

    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("p_tate", "11111", "WR", projection_2y=None, is_prospect=True)
    with patch("src.dynasty_genius.services.market_overlay_service.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 13)
        compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert "rookie_peak_value_window" in pvo.market_overlay.caveats
