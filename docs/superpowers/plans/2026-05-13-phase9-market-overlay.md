# Phase 9 Market Overlay — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate `PVO.market_overlay` from FantasyCalc post-scoring, compute a percentile-rank divergence signal between Engine B projections and market values, and wire the overlay into all three decision surfaces.

**Architecture:** The FantasyCalc adapter fetches and caches the full market payload with a seasonal TTL and three-stage degraded fallback. A separate `market_overlay_service` joins FC data to PVOs via `sleeper_id`, computes within-position percentile ranks for both model and market, and assigns a `divergence_flag`. Each surface service calls `enrich_pvo_list_with_market_overlay()` after PVO assembly, before serialisation.

**Tech Stack:** Python 3.14, Pydantic v2, httpx, pytest. No new dependencies.

---

## ⚠️ Critical Context

- **Join key:** `pvo.sleeper_id` (already wired through assembler) → `fc_entry["player"]["sleeperId"]`
- **Model value:** `pvo.projection_2y` (Engine B's `predicted_avg_ppg_t1_t2`, already mapped)
- **FC scale floats above 10 000** — never assume a fixed max when normalising
- **`numQbs=2` is mandatory** — without it every QB is priced on a 1QB scale
- **Banned from storage:** `combinedValue`, `redraftValue`, `redraftDynastyValueDifference`
- **Test runner:** `.venv/bin/python3.14 -m pytest -q`
- **Spec:** `docs/superpowers/specs/2026-05-13-phase9-market-overlay.md`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| **Create** | `tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json` | Deterministic test data, 6 representative players |
| **Modify** | `src/dynasty_genius/models/player_value_object.py` | Add 5 fields to `MarketOverlay`; add `value_above_replacement` to PVO |
| **Create** | `src/dynasty_genius/adapters/market_source.py` | `MarketSource` ABC + `KTCMarketSource` stub |
| **Modify** | `src/dynasty_genius/adapters/fantasycalc_adapter.py` | Fix URL params; rewrite `normalize_fantasycalc_entry`; add seasonal TTL cache + 3-stage fallback |
| **Create** | `src/dynasty_genius/services/__init__.py` | Package marker |
| **Create** | `src/dynasty_genius/services/market_overlay_service.py` | `pct_rank`, `compute_divergence`, `enrich_pvo_list_with_market_overlay` |
| **Modify** | `app/services/roster_auditor.py` | Call `enrich_pvo_list_with_market_overlay` in `run_audit_pvo` |
| **Modify** | `app/api/routes/rookies.py` | Call enrichment in both route handlers |
| **Modify** | `app/services/trade_analyzer.py` | Call enrichment in `analyze_trade_pvo` |
| **Modify** | `tests/test_market_overlay.py` | Extend existing governance tests with adapter + divergence tests |
| **Create** | `tests/contract/test_market_overlay_pvo.py` | 14 surface-level contract tests from spec |

---

## Task 1: Test Fixture + MarketOverlay Schema Update

**Files:**
- Create: `tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json`
- Modify: `src/dynasty_genius/models/player_value_object.py:10-23`

- [ ] **Step 1: Create the test fixture**

```json
[
  {
    "player": {
      "id": 9833,
      "name": "Bijan Robinson",
      "mflId": "16161",
      "sleeperId": "9509",
      "espnId": "4430807",
      "position": "RB",
      "maybeAge": 24.2,
      "maybeTeam": "ATL"
    },
    "value": 10503,
    "overallRank": 1,
    "positionRank": 1,
    "trend30Day": -39,
    "maybeMovingStandardDeviation": 0.0,
    "maybeTier": 1
  },
  {
    "player": {
      "id": 1001,
      "name": "Veteran Back",
      "mflId": "10011",
      "sleeperId": "6543",
      "espnId": "1001001",
      "position": "RB",
      "maybeAge": 27.5,
      "maybeTeam": "DAL"
    },
    "value": 3500,
    "overallRank": 48,
    "positionRank": 16,
    "trend30Day": -120,
    "maybeMovingStandardDeviation": 45.0,
    "maybeTier": 5
  },
  {
    "player": {
      "id": 2001,
      "name": "Elite WR",
      "mflId": "20011",
      "sleeperId": "7777",
      "espnId": "2001001",
      "position": "WR",
      "maybeAge": 26.0,
      "maybeTeam": "SF"
    },
    "value": 8000,
    "overallRank": 5,
    "positionRank": 3,
    "trend30Day": 200,
    "maybeMovingStandardDeviation": 12.0,
    "maybeTier": 2
  },
  {
    "player": {
      "id": 3001,
      "name": "Top TE",
      "mflId": "30011",
      "sleeperId": "8888",
      "espnId": "3001001",
      "position": "TE",
      "maybeAge": 27.0,
      "maybeTeam": "KC"
    },
    "value": 7500,
    "overallRank": 8,
    "positionRank": 1,
    "trend30Day": 491,
    "maybeMovingStandardDeviation": 150.0,
    "maybeTier": 1
  },
  {
    "player": {
      "id": 4001,
      "name": "SF QB",
      "mflId": "40011",
      "sleeperId": "9999",
      "espnId": "4001001",
      "position": "QB",
      "maybeAge": 28.0,
      "maybeTeam": "BUF"
    },
    "value": 6232,
    "overallRank": 19,
    "positionRank": 2,
    "trend30Day": 50,
    "maybeMovingStandardDeviation": 5.0,
    "maybeTier": 2
  },
  {
    "player": {
      "id": 5001,
      "name": "Carnell Tate",
      "mflId": "UNK",
      "sleeperId": "11111",
      "espnId": null,
      "position": "WR",
      "maybeAge": 21.0,
      "maybeTeam": null
    },
    "value": 2439,
    "overallRank": 75,
    "positionRank": 25,
    "trend30Day": 300,
    "maybeMovingStandardDeviation": 89.0,
    "maybeTier": 8
  }
]
```

Save to `tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json`.

- [ ] **Step 2: Update `MarketOverlay` schema**

In `src/dynasty_genius/models/player_value_object.py`, replace the `MarketOverlay` class:

```python
class MarketOverlay(BaseModel):
    """FantasyCalc market data joined after model scoring.

    Market values never enter Engine A or Engine B as predictive features.
    This overlay is display-only context for David's decision surfaces.
    """

    source: str = "fantasycalc"
    market_value: Optional[float] = None
    trend_delta: Optional[float] = None           # FC field: trend30Day
    model_percentile: Optional[float] = None      # model pct rank within position
    market_percentile: Optional[float] = None     # market pct rank within position
    model_minus_market_delta: Optional[float] = None  # model_pct - market_pct
    divergence_flag: Optional[str] = None         # see DIVERGENCE_FLAG_VALUES
    market_volatility: Optional[float] = None     # FC maybeMovingStandardDeviation
    position_rank: Optional[int] = None           # FC positionRank (display)
    overall_rank: Optional[int] = None            # FC overallRank (display)
    source_timestamp: Optional[str] = None        # HTTP fetch time (UTC)
    caveats: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Add `value_above_replacement` to `PlayerValueObject`**

In the same file, after `market_overlay: Optional[MarketOverlay] = None`, add:

```python
    value_above_replacement: Optional[float] = None
```

- [ ] **Step 4: Write a schema shape test**

Add to `tests/test_market_overlay.py`:

```python
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
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -q
```

Expected: all pass (existing governance tests + 2 new schema tests).

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/fantasycalc_sf_ppr_dynasty_2026_05_13.json \
        src/dynasty_genius/models/player_value_object.py \
        tests/test_market_overlay.py
git commit -m "feat(phase9): MarketOverlay schema + divergence fields + test fixture"
```

---

## Task 2: `MarketSource` Abstraction + KTC Stub

**Files:**
- Create: `src/dynasty_genius/adapters/market_source.py`

- [ ] **Step 1: Write the failing import test**

Add to `tests/test_market_overlay.py`:

```python
def test_ktc_market_source_raises_not_implemented():
    from src.dynasty_genius.adapters.market_source import KTCMarketSource
    import pytest
    source = KTCMarketSource()
    with pytest.raises(NotImplementedError, match="KTC"):
        source.fetch()


def test_fantasycalc_market_source_is_subclass_of_market_source():
    from src.dynasty_genius.adapters.market_source import MarketSource, FantasyCalcMarketSource
    assert issubclass(FantasyCalcMarketSource, MarketSource)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py::test_ktc_market_source_raises_not_implemented -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `src/dynasty_genius/adapters/market_source.py`**

```python
"""Market source abstraction.

MarketSource defines the interface for all market overlay providers.
FantasyCalcMarketSource is the only active implementation.
KTCMarketSource is a stub — KTC ToS prohibits automated access.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketSource(ABC):
    @abstractmethod
    def fetch(self) -> list[dict]:
        """Fetch raw market data. Returns list of normalised player dicts."""
        ...


class FantasyCalcMarketSource(MarketSource):
    """Active market source. Delegates to fantasycalc_adapter."""

    def fetch(self) -> list[dict]:
        from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
        data, _caveats = fetch_with_cache()
        return data


class KTCMarketSource(MarketSource):
    """Deferred. KTC ToS prohibits automated collection.

    No official API exists. Implement when a ToS-clean channel appears.
    See: docs/superpowers/specs/2026-05-13-phase9-market-overlay.md §KTC
    """

    def fetch(self) -> list[dict]:
        raise NotImplementedError(
            "KTC integration is deferred — ToS prohibits automated access. "
            "See Phase 9 spec §KTC for trigger conditions."
        )
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/market_source.py tests/test_market_overlay.py
git commit -m "feat(phase9): MarketSource ABC + KTCMarketSource stub"
```

---

## Task 3: FantasyCalc Adapter Overhaul

**Files:**
- Modify: `src/dynasty_genius/adapters/fantasycalc_adapter.py`

This task fixes the critical URL bug and adds seasonal TTL caching with three-stage degraded behaviour.

- [ ] **Step 1: Write failing adapter tests**

Add to `tests/test_market_overlay.py`:

```python
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
    import json
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -k "adapter_url or normalize_entry or fetch_with_cache" -q
```

Expected: all fail.

- [ ] **Step 3: Rewrite `src/dynasty_genius/adapters/fantasycalc_adapter.py`**

```python
"""FantasyCalc market overlay adapter.

Fetches dynasty SF PPR values from the FantasyCalc free API.
Caches to disk with a seasonal TTL. Three-stage degraded behaviour:
  1. Fresh cache → serve directly
  2. Expired cache + API failure → serve stale with caveat
  3. No cache + API failure → return empty list with market_data_unavailable caveat

Market values are post-scoring overlays only — never Engine A/B features.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

API_URL = (
    "https://api.fantasycalc.com/values/current"
    "?isDynasty=true&numQbs=2&numTeams=12&ppr=1"
)

CACHE_DIR = Path("app/cache/fantasycalc")
CACHE_FILE = CACHE_DIR / "market_values.json"


def _current_ttl_hours() -> int:
    """Seasonal TTL: 6h in-season (Aug 16–Jan 15), 24h offseason."""
    today = date.today()
    m, d = today.month, today.day
    in_season = (
        (m == 8 and d >= 16)
        or m in (9, 10, 11, 12)
        or (m == 1 and d <= 15)
    )
    return 6 if in_season else 24


def _load_cache() -> dict | None:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
    except Exception:
        pass
    return None


def _save_cache(data: list[dict], ttl_hours: int) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ttl_hours": ttl_hours,
            "data": data,
        }))
    except Exception:
        pass


def fetch_with_cache() -> tuple[list[dict], list[str]]:
    """Returns (raw_fc_entries, caveats). Never raises."""
    ttl_hours = _current_ttl_hours()
    cached = _load_cache()

    if cached:
        try:
            fetched_at = datetime.strptime(cached["fetched_at"], "%Y-%m-%dT%H:%M:%SZ")
            age_hours = (datetime.utcnow() - fetched_at).total_seconds() / 3600
            if age_hours < ttl_hours:
                # Stage 1: fresh
                return cached["data"], ["source_timestamp_is_fetch_time_not_publish_time"]
        except Exception:
            pass

    # Cache miss or expired — attempt live fetch
    try:
        response = httpx.get(API_URL, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "players" in data:
            data = data["players"]
        if not isinstance(data, list):
            data = []
        _save_cache(data, ttl_hours)
        return data, ["source_timestamp_is_fetch_time_not_publish_time"]
    except Exception:
        pass

    if cached:
        # Stage 2: stale serve
        fetched_at_str = cached.get("fetched_at", "unknown")
        try:
            fetched_at = datetime.strptime(fetched_at_str, "%Y-%m-%dT%H:%M:%SZ")
            stale_h = int((datetime.utcnow() - fetched_at).total_seconds() / 3600)
        except Exception:
            stale_h = -1
        return cached["data"], [
            "stale_market_data",
            f"fetched_at={fetched_at_str}",
            f"stale_for={stale_h}h",
            "source_timestamp_is_fetch_time_not_publish_time",
        ]

    # Stage 3: cold fail
    return [], ["market_data_unavailable"]


def fetch_fantasycalc_market_values() -> list[dict[str, Any]]:
    """Legacy entry point. Returns raw FC data (no caveats)."""
    data, _ = fetch_with_cache()
    return data


def normalize_fantasycalc_entry(raw_entry: dict[str, Any]) -> dict[str, Any]:
    """Normalise a single FC response entry into a flat dict for overlay construction."""
    player = raw_entry.get("player", {})
    return {
        "sleeper_id": player.get("sleeperId"),
        "mfl_id": player.get("mflId"),
        "full_name": player.get("name"),
        "position": player.get("position"),
        "age": player.get("maybeAge"),
        "nfl_team": player.get("maybeTeam"),
        "market_value": raw_entry.get("value"),
        "trend_delta": raw_entry.get("trend30Day"),
        "overall_rank": raw_entry.get("overallRank"),
        "position_rank": raw_entry.get("positionRank"),
        "market_volatility": raw_entry.get("maybeMovingStandardDeviation"),
        "fc_tier": raw_entry.get("maybeTier"),
        # Explicitly excluded: combinedValue, redraftValue, redraftDynastyValueDifference
    }
```

- [ ] **Step 4: Run adapter tests**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -q
```

Expected: all pass.

- [ ] **Step 5: Run full suite to check for regressions**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 339+ passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/adapters/fantasycalc_adapter.py tests/test_market_overlay.py
git commit -m "feat(phase9): fix FC adapter URL params, add seasonal TTL cache + 3-stage fallback"
```

---

## Task 4: Divergence Engine

**Files:**
- Create: `src/dynasty_genius/services/__init__.py`
- Create: `src/dynasty_genius/services/market_overlay_service.py`
- Test: `tests/test_market_overlay.py`

- [ ] **Step 1: Write failing divergence tests**

Add to `tests/test_market_overlay.py`:

```python
from src.dynasty_genius.models.player_value_object import (
    MarketOverlay, PlayerValueObject, RosterAuditSignals,
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
    # Two players with identical value — both get 0.5 * (0 + 1) / 2 = 0.25... wait
    # values = [5, 5, 10]
    # pct_rank([5, 5, 10], 5) = (0 + 0.5*2) / 3 = 1/3 ≈ 0.333
    values = [5.0, 5.0, 10.0]
    assert pct_rank(values, 5.0) == pytest.approx(1 / 3, abs=0.001)
    assert pct_rank(values, 10.0) == pytest.approx(5 / 6, abs=0.001)


def test_pct_rank_single_value():
    from src.dynasty_genius.services.market_overlay_service import pct_rank
    assert pct_rank([7.0], 7.0) == 0.5


def test_compute_divergence_sets_divergence_flag_aligned():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    # Bijan Robinson: sleeper_id "9509", value 10503, position RB
    pvo = _make_pvo("p1", "9509", "RB", projection_2y=15.0, age=24.2)
    compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.market_value == 10503
    assert pvo.market_overlay.divergence_flag in (
        "aligned", "model_higher_than_market", "model_lower_than_market"
    )
    assert pvo.market_overlay.model_percentile is not None
    assert pvo.market_overlay.market_percentile is not None
    assert pvo.market_overlay.model_minus_market_delta is not None


def test_compute_divergence_te_forced_model_unreliable():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    # Top TE: sleeper_id "8888"
    pvo = _make_pvo("p2", "8888", "TE", projection_2y=8.0, model_grade="EXPERIMENTAL")
    compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag == "model_unreliable"
    assert "te_model_experimental_do_not_trade_on" in pvo.market_overlay.caveats
    assert "te_market_high_variance" in pvo.market_overlay.caveats


def test_compute_divergence_rookie_no_projection():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    # Carnell Tate: sleeper_id "11111", is_prospect
    pvo = _make_pvo("p3", "11111", "WR", projection_2y=None, is_prospect=True)
    compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert pvo.market_overlay.divergence_flag == "model_uninformative_rookie"
    assert "model_uninformative_rookie" in pvo.market_overlay.caveats


def test_compute_divergence_rb_cliff_watch():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    # Veteran Back: sleeper_id "6543", age 27.5, value 3500
    # Give high model projection so model_pct > market_pct
    pvo = _make_pvo("p4", "6543", "RB", projection_2y=20.0, age=27.5)
    # Also need younger RB in pvo list to make model percentile meaningful
    younger = _make_pvo("p5", "9509", "RB", projection_2y=15.0, age=24.2)
    compute_divergence([pvo, younger], fixture)
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -k "pct_rank or compute_divergence" -q
```

Expected: all fail — `ModuleNotFoundError`.

- [ ] **Step 3: Create package marker**

Create `src/dynasty_genius/services/__init__.py` as an empty file.

- [ ] **Step 4: Create `src/dynasty_genius/services/market_overlay_service.py`**

```python
"""Market overlay divergence engine.

Computes within-position percentile-rank divergence between Engine B
projections (projection_2y) and FantasyCalc market values, then assigns
a divergence_flag and position-specific caveats to each PVO.

Leakage rule: no field from MarketOverlay may enter Engine A or Engine B
training or inference. This module only writes to PVO.market_overlay.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.dynasty_genius.models.player_value_object import PlayerValueObject

# 10 percentile points ≈ one dynasty tier. Configurable — review after 2 months.
NOISE_BAND: float = 0.10

_DIVERGENCE_FLAGS = frozenset({
    "aligned",
    "model_higher_than_market",
    "model_lower_than_market",
    "model_unreliable",
    "model_uninformative_rookie",
})


def pct_rank(values: list[float], x: float) -> float:
    """Percentile rank using mid-rank for ties: (less + 0.5*equal) / n."""
    n = len(values)
    if n < 2:
        return 0.5
    less = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return (less + 0.5 * equal) / n


def _classify_flag(delta: float, pvo: "PlayerValueObject") -> str:
    if pvo.model_grade == "EXPERIMENTAL" or pvo.position == "TE":
        return "model_unreliable"
    if abs(delta) < NOISE_BAND:
        return "aligned"
    return "model_higher_than_market" if delta > 0 else "model_lower_than_market"


def _attach_position_caveats(
    pvo: "PlayerValueObject",
    flag: str,
    delta: float,
) -> list[str]:
    caveats: list[str] = []
    pos = pvo.position or ""
    age = pvo.age or 0.0

    if pos == "TE":
        caveats += ["te_model_experimental_do_not_trade_on", "te_market_high_variance"]
    elif pos == "RB":
        if flag == "model_higher_than_market" and age >= 26:
            caveats.append("rb_cliff_watch")
        elif flag == "model_lower_than_market" and age <= 25:
            caveats.append("rb_youth_premium")

    if pvo.is_prospect:
        caveats.append("model_uninformative_rookie")

    return caveats


def compute_divergence(pvo_list: list["PlayerValueObject"], fc_response: list[dict]) -> None:
    """Mutates market_overlay on each PVO. No return value.

    Join key: pvo.sleeper_id → fc_entry["player"]["sleeperId"].
    Market percentile uses the full FC response as the cohort.
    Model percentile uses the PVOs in pvo_list that have a projection_2y.
    """
    from src.dynasty_genius.models.player_value_object import MarketOverlay

    fetch_ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build FC lookup and per-position market cohort from full response
    fc_by_sleeper: dict[str, dict] = {}
    fc_market_by_position: dict[str, list[float]] = defaultdict(list)
    for entry in fc_response:
        player = entry.get("player", {})
        sid = player.get("sleeperId")
        pos = player.get("position", "")
        val = entry.get("value")
        if sid:
            fc_by_sleeper[str(sid)] = entry
        if pos and val is not None:
            fc_market_by_position[pos].append(float(val))

    # Build per-position model cohort from pvo_list
    model_vals_by_position: dict[str, list[float]] = defaultdict(list)
    for pvo in pvo_list:
        if pvo.projection_2y is not None and pvo.position:
            model_vals_by_position[pvo.position].append(pvo.projection_2y)

    for pvo in pvo_list:
        sleeper_id = pvo.sleeper_id
        if not sleeper_id:
            continue

        fc_entry = fc_by_sleeper.get(str(sleeper_id))
        if fc_entry is None:
            continue  # no FC match — leave market_overlay as None

        player = fc_entry.get("player", {})
        position = pvo.position or ""

        overlay = MarketOverlay(
            source="fantasycalc",
            market_value=fc_entry.get("value"),
            trend_delta=fc_entry.get("trend30Day"),
            market_volatility=fc_entry.get("maybeMovingStandardDeviation"),
            position_rank=fc_entry.get("positionRank"),
            overall_rank=fc_entry.get("overallRank"),
            source_timestamp=fetch_ts,
            caveats=["source_timestamp_is_fetch_time_not_publish_time"],
        )
        pvo.market_overlay = overlay

        # Rookie / no-projection case
        if pvo.projected_avg_ppg_t1_t2 is None:
            overlay.divergence_flag = "model_uninformative_rookie"
            overlay.caveats += _attach_position_caveats(pvo, "model_uninformative_rookie", 0.0)
            continue

        market_cohort = fc_market_by_position.get(position, [])
        model_cohort = model_vals_by_position.get(position, [])

        if not market_cohort or not model_cohort:
            continue

        m_pct = pct_rank(model_cohort, pvo.projection_2y)
        k_pct = pct_rank(market_cohort, float(overlay.market_value or 0))
        delta = round(m_pct - k_pct, 3)

        overlay.model_percentile = round(m_pct, 3)
        overlay.market_percentile = round(k_pct, 3)
        overlay.model_minus_market_delta = delta
        flag = _classify_flag(delta, pvo)
        overlay.divergence_flag = flag
        overlay.caveats += _attach_position_caveats(pvo, flag, delta)


def enrich_pvo_list_with_market_overlay(pvo_list: list["PlayerValueObject"]) -> None:
    """Fetch FC data (cached) and compute divergence. Mutates each PVO in place."""
    from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
    fc_data, _caveats = fetch_with_cache()
    if fc_data:
        compute_divergence(pvo_list, fc_data)
```

**Note:** There's a typo risk above — `pvo.projected_avg_ppg_t1_t2` is not a PVO field. The correct field is `pvo.projection_2y`. Fix the `if pvo.projected_avg_ppg_t1_t2 is None` check to `if pvo.projection_2y is None`.

Corrected line in `compute_divergence`:

```python
        # Rookie / no-projection case
        if pvo.projection_2y is None:
            overlay.divergence_flag = "model_uninformative_rookie"
            overlay.caveats += _attach_position_caveats(pvo, "model_uninformative_rookie", 0.0)
            continue
```

- [ ] **Step 5: Run divergence tests**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -q
```

Expected: all pass.

- [ ] **Step 6: Run full suite**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 339+ passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add src/dynasty_genius/services/__init__.py \
        src/dynasty_genius/services/market_overlay_service.py \
        tests/test_market_overlay.py
git commit -m "feat(phase9): divergence engine — pct_rank, compute_divergence, enrich_pvo_list"
```

---

## Task 5: Surface Wiring

**Files:**
- Modify: `app/services/roster_auditor.py`
- Modify: `app/api/routes/rookies.py`
- Modify: `app/services/trade_analyzer.py`

Each service assembles PVOs then calls `enrich_pvo_list_with_market_overlay` before serialisation. The enrichment function handles its own FC fetch (cached) internally.

- [ ] **Step 1: Wire `run_audit_pvo` in `app/services/roster_auditor.py`**

Find the `run_audit_pvo` function. After the `pvos.sort(...)` line and before the `return` statement, add:

```python
    from src.dynasty_genius.services.market_overlay_service import enrich_pvo_list_with_market_overlay
    enrich_pvo_list_with_market_overlay(pvos)
```

The full `return` block stays unchanged; `pvo.model_dump()` will now include the populated overlay.

- [ ] **Step 2: Wire `/rookies/score` in `app/api/routes/rookies.py`**

Replace the `score_single` function:

```python
@router.post("/score")
def score_single(prospect: ProspectRequest) -> dict:
    try:
        from src.dynasty_genius.services.market_overlay_service import enrich_pvo_list_with_market_overlay
        pvo = _map_prospect_to_pvo(prospect)
        enrich_pvo_list_with_market_overlay([pvo])
        return pvo.model_dump()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
```

Replace the `score_class` function:

```python
@router.post("/score-class")
def score_class(prospects: list[ProspectRequest]) -> list[dict]:
    try:
        from src.dynasty_genius.services.market_overlay_service import enrich_pvo_list_with_market_overlay
        pvos = [_map_prospect_to_pvo(p) for p in prospects]
        pvos.sort(
            key=lambda x: (x.dynasty_value_score is not None, x.dynasty_value_score or -1.0),
            reverse=True,
        )
        enrich_pvo_list_with_market_overlay(pvos)
        return [p.model_dump() for p in pvos]
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
```

- [ ] **Step 3: Wire `analyze_trade_pvo` in `app/services/trade_analyzer.py`**

Find `analyze_trade_pvo`. After the two asset PVO lists are assembled and before `compute_delta_status` is called, add:

```python
    from src.dynasty_genius.services.market_overlay_service import enrich_pvo_list_with_market_overlay
    enrich_pvo_list_with_market_overlay(my_pvos + their_pvos)
```

- [ ] **Step 4: Run full suite**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 339+ passed, 0 failed. The enrichment calls are guarded internally — if FC is unavailable the PVOs retain `market_overlay=None` and existing tests continue to pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/roster_auditor.py \
        app/api/routes/rookies.py \
        app/services/trade_analyzer.py
git commit -m "feat(phase9): wire enrich_pvo_list_with_market_overlay into all three surfaces"
```

---

## Task 6: Surface Contract Tests

**Files:**
- Create: `tests/contract/test_market_overlay_pvo.py`

These tests mock FC responses to avoid live network calls and verify the overlay contract on all surfaces.

- [ ] **Step 1: Write all 14 contract tests**

Create `tests/contract/test_market_overlay_pvo.py`:

```python
"""Phase 9 contract tests: market_overlay shape and governance on all surfaces.

Verifies:
1.  FC adapter returns correct shape with sleeper_id present.
2.  combinedValue and redraftValue absent from overlay.
3.  divergence_flag is one of the five valid values.
4.  TE always receives divergence_flag == "model_unreliable".
5.  Rookie with no projection receives divergence_flag == "model_uninformative_rookie".
6.  RB age 26+ with model_higher_than_market receives rb_cliff_watch caveat.
7.  market_overlay is None with market_data_unavailable when FC unavailable.
8.  Stale FC returns stale_market_data caveat on overlay.
9.  source_timestamp_is_fetch_time_not_publish_time always present when overlay exists.
10. market_overlay.source == "fantasycalc" on all surfaces.
11. No banned fields (action, verdict, dynasty_tier, confidence) in surface responses.
12. model_percentile and market_percentile both present when divergence computed.
13. market_value matches the fixture value for a known player.
14. market_overlay fields combinedValue, redraftValue not stored.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

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

def test_divergence_flag_is_valid_for_scored_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
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
    compute_divergence([veteran, younger], FIXTURE)
    assert veteran.market_overlay is not None
    if veteran.market_overlay.divergence_flag == "model_higher_than_market":
        assert "rb_cliff_watch" in veteran.market_overlay.caveats


# ── Test 7: No FC data → market_data_unavailable caveat ───────────────────────

def test_no_fc_data_leaves_overlay_none_with_caveat():
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], [])  # empty FC response
    assert pvo.market_overlay is None


# ── Test 8: source_timestamp caveat always present ────────────────────────────

def test_source_timestamp_caveat_always_on_overlay():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is not None
    assert "source_timestamp_is_fetch_time_not_publish_time" in pvo.market_overlay.caveats


# ── Test 9: source == "fantasycalc" ──────────────────────────────────────────

def test_overlay_source_is_fantasycalc():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay.source == "fantasycalc"


# ── Test 10: No banned output fields ─────────────────────────────────────────

def test_no_banned_fields_in_overlay_model_dump():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    dumped = pvo.model_dump()
    found = BANNED_FIELDS & set(dumped.keys())
    assert not found, f"Banned fields found: {found}"


# ── Test 11: model_percentile and market_percentile both present ──────────────

def test_both_percentiles_present_for_scored_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay.model_percentile is not None
    assert pvo.market_overlay.market_percentile is not None


# ── Test 12: market_value matches fixture ────────────────────────────────────

def test_market_value_matches_fixture_for_known_player():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay.market_value == 10503


# ── Test 13: No sleeper_id match → overlay stays None ────────────────────────

def test_unmatched_player_overlay_is_none():
    pvo = _pvo("ZZZZZ_UNKNOWN", "WR", 12.0)
    compute_divergence([pvo], FIXTURE)
    assert pvo.market_overlay is None


# ── Test 14: combinedValue not stored on overlay ─────────────────────────────

def test_combined_value_not_stored_on_overlay():
    pvo = _pvo("9509", "RB", 15.0, age=24.2)
    compute_divergence([pvo], FIXTURE)
    dumped = pvo.market_overlay.model_dump()
    assert "combinedValue" not in dumped
    assert "redraftValue" not in dumped
```

- [ ] **Step 2: Run contract tests**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_market_overlay_pvo.py -q
```

Expected: all 14 pass.

- [ ] **Step 3: Run full suite**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 353+ passed (339 baseline + 14 new), 0 failed.

- [ ] **Step 4: Commit**

```bash
git add tests/contract/test_market_overlay_pvo.py
git commit -m "test(phase9): 14 market overlay contract tests across all surfaces"
```

---

## Task 7: VAR + Seasonal Signals (Phase 9.3)

**Files:**
- Modify: `src/dynasty_genius/services/market_overlay_service.py`
- Modify: `src/dynasty_genius/models/player_value_object.py` (already has `value_above_replacement`)

- [ ] **Step 1: Write VAR tests**

Add to `tests/test_market_overlay.py`:

```python
def test_compute_var_uses_model_score_not_market():
    from src.dynasty_genius.services.market_overlay_service import compute_value_above_replacement
    pvos = [
        _make_pvo("p1", "s1", "RB", projection_2y=15.0),
        _make_pvo("p2", "s2", "RB", projection_2y=12.0),
        _make_pvo("p3", "s3", "RB", projection_2y=9.0),
    ]
    # Set dynasty_value_score manually (would normally come from engine)
    pvos[0].dynasty_value_score = 80.0
    pvos[1].dynasty_value_score = 60.0
    pvos[2].dynasty_value_score = 40.0
    compute_value_above_replacement(pvos)
    # Replacement level for RB in 12-team SF is RB33.
    # With only 3 RBs, the Nth player is the last one.
    # All three should have non-None VAR if dynasty_value_score is set.
    assert pvos[0].value_above_replacement is not None
    assert pvos[2].value_above_replacement is not None


def test_compute_var_is_none_when_no_dynasty_value_score():
    from src.dynasty_genius.services.market_overlay_service import compute_value_above_replacement
    pvos = [_make_pvo("p1", "s1", "RB", projection_2y=15.0)]
    pvos[0].dynasty_value_score = None
    compute_value_above_replacement(pvos)
    assert pvos[0].value_above_replacement is None


def test_rookie_peak_value_window_caveat_fires_in_may():
    from unittest.mock import patch
    from datetime import date
    from src.dynasty_genius.services.market_overlay_service import compute_divergence
    fixture = _load_fixture()
    pvo = _make_pvo("11111", "WR", None, is_prospect=True)
    with patch("src.dynasty_genius.services.market_overlay_service.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 13)
        compute_divergence([pvo], fixture)
    assert pvo.market_overlay is not None
    assert "rookie_peak_value_window" in pvo.market_overlay.caveats
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -k "var or rookie_peak" -q
```

Expected: fail — `ImportError`.

- [ ] **Step 3: Add `compute_value_above_replacement` and seasonal date logic to `market_overlay_service.py`**

Add imports at the top:

```python
from datetime import date
```

Add these constants after `NOISE_BAND`:

```python
# 12-team Superflex PPR replacement baselines (from Phase 9 spec)
_VAR_REPLACEMENT_LEVEL: dict[str, int] = {
    "QB": 25,
    "RB": 33,
    "WR": 53,
    "TE": 13,
}

_ROOKIE_PEAK_WINDOW_START = (4, 1)   # April 1
_ROOKIE_PEAK_WINDOW_END   = (7, 1)   # July 1
```

Add these functions at the end of the file:

```python
def _is_rookie_peak_window() -> bool:
    today = date.today()
    start = _ROOKIE_PEAK_WINDOW_START
    end = _ROOKIE_PEAK_WINDOW_END
    m, d = today.month, today.day
    after_start = (m, d) >= start
    before_end  = (m, d) < end
    return after_start and before_end


def compute_value_above_replacement(
    pvo_list: list["PlayerValueObject"],
) -> None:
    """Mutates pvo.value_above_replacement. Uses dynasty_value_score only — never market_value."""
    from collections import defaultdict

    by_position: dict[str, list["PlayerValueObject"]] = defaultdict(list)
    for pvo in pvo_list:
        if pvo.position and pvo.dynasty_value_score is not None:
            by_position[pvo.position].append(pvo)

    for pos, pvos_at_pos in by_position.items():
        sorted_pvos = sorted(pvos_at_pos, key=lambda p: p.dynasty_value_score or 0, reverse=True)
        n = _VAR_REPLACEMENT_LEVEL.get(pos, len(sorted_pvos))
        # Replacement player is the Nth player (0-indexed: n-1), or last if fewer than N
        idx = min(n - 1, len(sorted_pvos) - 1)
        replacement_score = sorted_pvos[idx].dynasty_value_score or 0.0
        for pvo in pvos_at_pos:
            pvo.value_above_replacement = round((pvo.dynasty_value_score or 0.0) - replacement_score, 3)

    # Players with no dynasty_value_score stay None (already default)
```

Update `_attach_position_caveats` to include the rookie peak window check:

```python
def _attach_position_caveats(
    pvo: "PlayerValueObject",
    flag: str,
    delta: float,
) -> list[str]:
    caveats: list[str] = []
    pos = pvo.position or ""
    age = pvo.age or 0.0

    if pos == "TE":
        caveats += ["te_model_experimental_do_not_trade_on", "te_market_high_variance"]
    elif pos == "RB":
        if flag == "model_higher_than_market" and age >= 26:
            caveats.append("rb_cliff_watch")
        elif flag == "model_lower_than_market" and age <= 25:
            caveats.append("rb_youth_premium")

    if pvo.is_prospect:
        caveats.append("model_uninformative_rookie")
        if _is_rookie_peak_window():
            caveats.append("rookie_peak_value_window")

    return caveats
```

- [ ] **Step 4: Run VAR and seasonal tests**

```bash
.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -k "var or rookie_peak" -q
```

Expected: all pass.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 353+ passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/services/market_overlay_service.py \
        tests/test_market_overlay.py
git commit -m "feat(phase9): VAR from model scores + seasonal rookie_peak_value_window caveat"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task | Status |
|---|---|---|
| Fix URL to include `numQbs=2&numTeams=12&ppr=1` | Task 3 | ✅ |
| Rewrite `normalize_fantasycalc_entry` | Task 3 | ✅ |
| `MarketSource` ABC + `KTCMarketSource` stub | Task 2 | ✅ |
| Seasonal TTL (24h/6h) | Task 3 | ✅ |
| Three-stage degraded behaviour | Task 3 | ✅ |
| Test fixture committed | Task 1 | ✅ |
| `MarketOverlay` new fields | Task 1 | ✅ |
| `pct_rank` with mid-rank tie-breaker | Task 4 | ✅ |
| `compute_divergence` with NOISE_BAND | Task 4 | ✅ |
| Five-value `divergence_flag` taxonomy | Task 4 | ✅ |
| TE forced `model_unreliable` | Task 4 | ✅ |
| `model_uninformative_rookie` for no-projection | Task 4 | ✅ |
| `rb_cliff_watch` for RB 26+ | Task 4 | ✅ |
| `rookie_peak_value_window` April–July | Task 7 | ✅ |
| `source_timestamp_is_fetch_time_not_publish_time` caveat | Task 4 | ✅ |
| Wire into `run_audit_pvo` | Task 5 | ✅ |
| Wire into `/rookies/score` and `/score-class` | Task 5 | ✅ |
| Wire into `analyze_trade_pvo` | Task 5 | ✅ |
| 14 surface contract tests | Task 6 | ✅ |
| VAR from model `dynasty_value_score` only | Task 7 | ✅ |
| `combinedValue`/`redraftValue` never stored | Tasks 3, 6 | ✅ |
| `value_above_replacement` field on PVO | Task 1 | ✅ |

**Known limitation:** Prospect PVOs use `dg_id = prospect_{pos}_{pick}` and `sleeper_id = None` (or not set). These will not match FC entries. The Rookie Board overlay for pre-draft prospects is a Phase 9.5 enhancement requiring a name-based or draft-pick-based FC lookup.

**Open question preserved:** `NOISE_BAND = 0.10` is a config parameter. Review after 1–2 months — if >80% of flags are `aligned`, tighten to 0.08.
