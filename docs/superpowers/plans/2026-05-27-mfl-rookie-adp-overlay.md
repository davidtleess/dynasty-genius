# MFL Rookie ADP Overlay (Increment 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only MFL rookie-ADP market-overlay adapter, mirroring the FantasyCalc adapter, that fetches real completed-draft dynasty rookie ADP, joins it to MFL's player map, and emits normalized overlay rows — fully unwired (no consumer/Engine/PVO/endpoint).

**Architecture:** New `mfl_adp_adapter.py` does two independent cached fetches (ADP + `TYPE=players`), each 3-stage degraded, then `normalize_mfl_adp_entry` joins them by `mfl_id`. `MflAdpMarketSource(season=None)` wraps it and returns `list[dict]` (rows only), preserving the `MarketSource` contract. Governance is fail-closed first: register `mfl_rookie_adp` as `market_overlay` and extend the leakage gate before the adapter exists.

**Tech Stack:** Python 3.14, `httpx`, `pytest` (run via `.venv/bin/python3.14 -m pytest`), `monkeypatch` + `unittest.mock.patch` for cache/network isolation.

**Spec:** `docs/superpowers/specs/2026-05-27-mfl-rookie-adp-overlay-design.md`

**Cockpit execution:** Codex test-drives the RED contract test for each task; Claude implements to green. One agent edits at a time (tmux focus is the lock). Run after every task:
`./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py tests/test_market_overlay.py tests/test_market_leakage_gate.py -q`
(plus the `AGENT_SYNC.md` exclusion list for full-suite runs).

**Scope fences (do NOT do these):** not for SF-QB calibration · no endpoint/Engine/PVO/frontend wiring · no MFL→Sleeper cross-walk · no veteran feed · **do NOT modify `tests/contract/test_market_overlay_pvo.py`**.

---

## File Structure

- **Create** `src/dynasty_genius/adapters/mfl_adp_adapter.py` — fetch + cache + sanitize + normalize. One responsibility: turn the two MFL endpoints into normalized overlay rows.
- **Modify** `src/dynasty_genius/adapters/market_source.py` — add `MflAdpMarketSource(MarketSource)`.
- **Modify** `src/dynasty_genius/sources/source_registry.py` — add the `mfl_rookie_adp` entry.
- **Modify** `src/dynasty_genius/models/engine_a_contract.py` — add 2 field names to `PROHIBITED_COLUMNS`.
- **Create** `tests/fixtures/mfl_rookie_adp_2026_05_27.json`, `tests/fixtures/mfl_players_2026_05_27.json` — small, shape-faithful captures.
- **Create** `tests/test_mfl_adp_adapter.py` — adapter unit tests.
- **Modify** `tests/test_market_overlay.py` — add the `MflAdpMarketSource` subclass test + registry assertions.
- **Modify** `tests/test_market_leakage_gate.py` — add `mfl_rookie_adp` field coverage.

---

## Task 1: Capture the live MFL fixtures

**Files:**
- Create: `tests/fixtures/mfl_rookie_adp_2026_05_27.json`
- Create: `tests/fixtures/mfl_players_2026_05_27.json`

This is a data-capture task (no TDD). Fixtures must be **small and shape-faithful** (raw MFL shape, pre-normalization), and must include: ≥3 ADP rows, **one ADP row whose `id` is absent from the players fixture** (the unmatched-identity case), and a players fixture covering the other ids.

- [ ] **Step 1: Probe both endpoints live and verify the shape**

```bash
UA="dynasty-genius/0.1 (personal dynasty tool; contact david.t.leess@gmail.com)"
curl -s -A "$UA" "https://api.myfantasyleague.com/2026/export?TYPE=adp&PERIOD=RECENT&FCOUNT=12&IS_PPR=1&ROOKIES=1&IS_MOCK=No&JSON=1" > /tmp/mfl_adp_raw.json
curl -s -A "$UA" "https://api.myfantasyleague.com/2026/export?TYPE=players&JSON=1" > /tmp/mfl_players_raw.json
.venv/bin/python3.14 -c "import json; a=json.load(open('/tmp/mfl_adp_raw.json'))['adp']; print('adp keys', list(a.keys())); print('first row', a['player'][0]); p=json.load(open('/tmp/mfl_players_raw.json'))['players']['player']; print('players first', p[0])"
```
Expected: `adp` has keys incl. `player`, `timestamp`, `totalDrafts`, `totalPicks`; ADP rows have `id, rank, averagePick, minPick, maxPick, draftSelPct, draftsSelectedIn`; player rows have `id, name, position, team`. **If the params error (e.g. `Invalid value for IS_KEEPER`), STOP and re-lock params before proceeding** (the spec's params are live-locked but re-verify).

- [ ] **Step 2: Write the trimmed ADP fixture (raw shape)**

Keep the first 4 ADP rows from the probe, then append one synthetic-but-shape-faithful row whose `id` will NOT be in the players fixture (unmatched case). Real probed top-3 ids were `17472, 17497, 17498`. Final file is the **raw `adp` object** (so the adapter's own parse is exercised):

```json
{
  "adp": {
    "timestamp": "1769900000",
    "totalDrafts": "628",
    "totalPicks": "200000",
    "player": [
      {"id": "17472", "rank": "1", "averagePick": "1.43", "minPick": "1", "maxPick": "38", "draftSelPct": "95", "draftsSelectedIn": "628"},
      {"id": "17497", "rank": "2", "averagePick": "3.67", "minPick": "1", "maxPick": "94", "draftSelPct": "95", "draftsSelectedIn": "633"},
      {"id": "17498", "rank": "3", "averagePick": "5.34", "minPick": "1", "maxPick": "114", "draftSelPct": "96", "draftsSelectedIn": "641"},
      {"id": "17500", "rank": "4", "averagePick": "7.10", "minPick": "2", "maxPick": "120", "draftSelPct": "94", "draftsSelectedIn": "620"},
      {"id": "99999", "rank": "5", "averagePick": "9.00", "minPick": "3", "maxPick": "130", "draftSelPct": "90", "draftsSelectedIn": "600"}
    ]
  }
}
```
Replace the four real rows with the actual probed values; keep id `99999` as the deliberate unmatched row. Verify the four real ids exist in the live players export so the matched rows are real.

- [ ] **Step 3: Write the trimmed players fixture (raw shape, covers the 4 matched ids only)**

Use the real `name/position/team` from the players probe for ids `17472, 17497, 17498, 17500`. Deliberately OMIT `99999` so the adapter's unmatched path is exercised. Final file is the **raw `players` object**:

```json
{
  "players": {
    "timestamp": "1769900000",
    "player": [
      {"id": "17472", "name": "Last, First", "position": "RB", "team": "FA"},
      {"id": "17497", "name": "Last, First", "position": "WR", "team": "FA"},
      {"id": "17498", "name": "Last, First", "position": "WR", "team": "FA"},
      {"id": "17500", "name": "Last, First", "position": "QB", "team": "FA"}
    ]
  }
}
```
Replace each `"Last, First"` and position/team with the real probed values for that id.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/mfl_rookie_adp_2026_05_27.json tests/fixtures/mfl_players_2026_05_27.json
git commit -m "test(mfl-adp): capture small shape-faithful MFL ADP + players fixtures"
```

---

## Task 2: Leakage-gate fail-closed (PROHIBITED_COLUMNS + tests)

Governance first. `draft_selection_pct` and `drafts_selected_in` are NOT caught by `LEAKAGE_REGEX` (`^ktc_|^adp|_rank$|^expert|^market_|^value_|^consensus`), so they must be added to `PROHIBITED_COLUMNS` explicitly.

**Files:**
- Modify: `src/dynasty_genius/models/engine_a_contract.py:59-66`
- Test: `tests/test_market_leakage_gate.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_market_leakage_gate.py`:

```python
def test_mfl_overlay_only_fields_are_prohibited():
    # market_adp_rank / market_average_pick are caught by LEAKAGE_REGEX (^market_ / _rank$),
    # but these two MFL field names match no regex pattern — they need explicit protection.
    assert "draft_selection_pct" in PROHIBITED_COLUMNS
    assert "drafts_selected_in" in PROHIBITED_COLUMNS


def test_mfl_overlay_only_fields_not_caught_by_regex_so_need_explicit_set():
    # Documents WHY they are in the explicit set: the broad regex misses them.
    assert not re.search(LEAKAGE_REGEX, "draft_selection_pct")
    assert not re.search(LEAKAGE_REGEX, "drafts_selected_in")
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_market_leakage_gate.py::test_mfl_overlay_only_fields_are_prohibited -v`
Expected: FAIL (`assert 'draft_selection_pct' in PROHIBITED_COLUMNS`).

- [ ] **Step 3: Add the two field names to PROHIBITED_COLUMNS**

In `src/dynasty_genius/models/engine_a_contract.py`, extend the set:

```python
PROHIBITED_COLUMNS = {
    "ktc_value", "ktc_rank", "adp", "fantasycalc_value",
    "dynastynerds_rank", "dynastydatalab_adp",
    "nfl_yards", "nfl_tds", "nfl_targets", "nfl_carries",
    "nfl_receptions", "nfl_air_yards", "nfl_yprr",
    "pff_grade", "pff_route_grade",
    "scout_note", "analyst_note", "narrative",
    # MFL rookie ADP overlay fields not caught by LEAKAGE_REGEX — overlay-only, never training:
    "draft_selection_pct", "drafts_selected_in",
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_market_leakage_gate.py -q`
Expected: PASS (all gate tests).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/models/engine_a_contract.py tests/test_market_leakage_gate.py
git commit -m "test(leakage): bar MFL draft_selection_pct/drafts_selected_in from training"
```

---

## Task 3: Register `mfl_rookie_adp` as a market_overlay source

**Files:**
- Modify: `src/dynasty_genius/sources/source_registry.py` (add entry after the `fantasycalc` `_make(...)`)
- Test: `tests/test_market_overlay.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_market_overlay.py` and update the set near the top:

```python
# update existing set:
MARKET_OVERLAY_SOURCES = {"fantasycalc", "dynasty_data_lab", "dynasty_nerds", "mfl_rookie_adp"}


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
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_market_overlay.py::test_mfl_rookie_adp_is_market_overlay_only -v`
Expected: FAIL with `KeyError: 'mfl_rookie_adp'`.

- [ ] **Step 3: Add the registry entry**

In `src/dynasty_genius/sources/source_registry.py`, add immediately after the `fantasycalc` `_make(...)` block (mirrors it):

```python
        _make(
            name="mfl_rookie_adp",
            roles=["market_overlay"],
            allowed_fields=[],
            prohibited_fields=list(PROHIBITED_COLUMNS),
            provenance_required=False,
            cache_policy="json_cache",
            freshness_hours=24,
            failure_behavior="use_cached",
            test_gate="tests/test_market_overlay.py",
            notes=(
                "Public documented MFL ADP API (TYPE=adp, ROOKIES=1). Real completed-draft "
                "rookie ADP. Overlay only — never enters Engine A/B training. Aggregate blends "
                "SF QB-count and TE-premium (not API-filterable); not for SF-QB calibration."
            ),
        ),
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_market_overlay.py -q`
Expected: PASS (incl. the existing `test_all_market_overlay_sources_have_market_overlay_role` which now also covers `mfl_rookie_adp`).

- [ ] **Step 5: Also extend the leakage-gate source set**

In `tests/test_market_leakage_gate.py`, update:

```python
MARKET_SOURCES = {"fantasycalc", "dynasty_data_lab", "dynasty_nerds", "ktc", "mfl_rookie_adp"}
```

Run: `./.venv/bin/python3.14 -m pytest tests/test_market_leakage_gate.py::test_no_market_source_is_model_input -q`
Expected: PASS (`mfl_rookie_adp` now asserted not-model_input).

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/sources/source_registry.py tests/test_market_overlay.py tests/test_market_leakage_gate.py
git commit -m "feat(sources): register mfl_rookie_adp as market_overlay"
```

---

## Task 4: Adapter module scaffold + constants + pure helpers

**Files:**
- Create: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mfl_adp_adapter.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

ADP_FIXTURE = Path("tests/fixtures/mfl_rookie_adp_2026_05_27.json")
PLAYERS_FIXTURE = Path("tests/fixtures/mfl_players_2026_05_27.json")


def _adp_player_rows() -> list[dict]:
    return json.loads(ADP_FIXTURE.read_text())["adp"]["player"]


def _players_rows() -> list[dict]:
    return json.loads(PLAYERS_FIXTURE.read_text())["players"]["player"]


def test_adp_url_has_locked_params():
    from src.dynasty_genius.adapters.mfl_adp_adapter import ADP_API_URL_TEMPLATE
    url = ADP_API_URL_TEMPLATE.format(year=2026)
    assert "TYPE=adp" in url
    assert "ROOKIES=1" in url          # NOT IS_KEEPER=Rookie Only (invalid)
    assert "FCOUNT=12" in url
    assert "IS_PPR=1" in url
    assert "IS_MOCK=No" in url
    assert "IS_KEEPER=Rookie" not in url


def test_as_list_normalizes_singleton_and_list():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _as_list
    assert _as_list([{"id": "1"}]) == [{"id": "1"}]
    assert _as_list({"id": "1"}) == [{"id": "1"}]   # MFL bare-object case
    assert _as_list(None) == []


def test_cache_files_are_season_scoped():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _adp_cache_file,
        _players_cache_file,
    )
    assert _adp_cache_file(2026).name == "adp_2026.json"
    assert _players_cache_file(2025).name == "players_2025.json"
    assert _adp_cache_file(2026) != _adp_cache_file(2025)


def test_sanitizers_keep_only_allowed_fields():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _sanitize_adp,
        _sanitize_players,
    )
    adp = _sanitize_adp([dict(_adp_player_rows()[0], junk="x")])
    assert "junk" not in adp[0]
    assert set(adp[0]) <= {"id", "rank", "averagePick", "minPick", "maxPick", "draftSelPct", "draftsSelectedIn"}
    players = _sanitize_players([dict(_players_rows()[0], junk="x")])
    assert "junk" not in players[0]
    assert set(players[0]) <= {"id", "name", "position", "team"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: FAIL with `ModuleNotFoundError: ...mfl_adp_adapter`.

- [ ] **Step 3: Create the module with constants + pure helpers**

Create `src/dynasty_genius/adapters/mfl_adp_adapter.py`:

```python
"""MyFantasyLeague rookie ADP market overlay adapter.

Fetches real completed-draft dynasty rookie ADP from MFL's public export API and
joins it to MFL's player map (TYPE=players) for name/position. Mirrors
fantasycalc_adapter. Two independent cached fetches, each 3-stage degraded:
  1. Fresh cache (now - fetched_at < TTL) -> serve
  2. Expired/absent cache + fetch fails -> serve stale with caveat (if cache exists)
  3. No cache + fetch fails -> empty + unavailable caveat

Market values are post-scoring overlays only — never Engine A/B features.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

_BASE = "https://api.myfantasyleague.com"
# Params live-locked 2026-05-27 (ROOKIES=1; IS_KEEPER=Rookie Only is INVALID).
ADP_API_URL_TEMPLATE = (
    _BASE + "/{year}/export?TYPE=adp&PERIOD=RECENT&FCOUNT=12&IS_PPR=1"
    "&ROOKIES=1&IS_MOCK=No&JSON=1"
)
PLAYERS_API_URL_TEMPLATE = _BASE + "/{year}/export?TYPE=players&JSON=1"

CACHE_DIR = Path("app/cache/mfl_adp")
ADP_TTL_HOURS = 24
PLAYERS_TTL_HOURS = 168  # player map is near-static

_USER_AGENT = "dynasty-genius/0.1 (personal dynasty tool; contact david.t.leess@gmail.com)"
_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

_ADP_ALLOWED = ("id", "rank", "averagePick", "minPick", "maxPick", "draftSelPct", "draftsSelectedIn")
_PLAYERS_ALLOWED = ("id", "name", "position", "team")

INTRINSIC_CAVEATS = ["mfl_adp_format_blended_qb_count", "mfl_adp_te_premium_unfiltered"]


def _current_season() -> int:
    return datetime.now(timezone.utc).year


def _as_list(node) -> list[dict]:
    """MFL returns a bare object for single-row responses; normalize to a list."""
    if node is None:
        return []
    return node if isinstance(node, list) else [node]


def _adp_cache_file(season: int) -> Path:
    return CACHE_DIR / f"adp_{season}.json"


def _players_cache_file(season: int) -> Path:
    return CACHE_DIR / f"players_{season}.json"


def _sanitize_adp(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in _ADP_ALLOWED if k in r} for r in rows]


def _sanitize_players(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in _PLAYERS_ALLOWED if k in r} for r in rows]
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): adapter scaffold — locked params, season-scoped cache, sanitizers"
```

---

## Task 5: Freshness clocks (`fetched_at` vs `source_timestamp`)

**Files:**
- Modify: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
def test_source_publish_age_parses_epoch():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _source_publish_age_hours
    import time
    one_hour_ago = str(int(time.time()) - 3600)
    age = _source_publish_age_hours(one_hour_ago)
    assert age is not None
    assert 0.9 < age < 1.2


def test_source_publish_age_unparseable_returns_none():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _source_publish_age_hours
    assert _source_publish_age_hours(None) is None
    assert _source_publish_age_hours("not-a-timestamp") is None


def test_freshness_caveats_flags_missing_timestamp():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _freshness_caveats
    assert "mfl_adp_timestamp_unavailable" in _freshness_caveats(None)
    assert "mfl_adp_timestamp_unavailable" not in _freshness_caveats(str(__import__("time").time().__trunc__()))
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py::test_source_publish_age_parses_epoch -v`
Expected: FAIL (`cannot import name '_source_publish_age_hours'`).

- [ ] **Step 3: Add the freshness helpers**

Append to `mfl_adp_adapter.py`:

```python
def _cache_age_hours(fetched_at: str) -> float | None:
    """Local cache age from fetched_at — governs whether to attempt a refresh."""
    try:
        fetched = datetime.strptime(fetched_at, _TS_FMT).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _source_publish_age_hours(source_timestamp) -> float | None:
    """Publish age from MFL adp.timestamp (epoch seconds) — the market freshness signal."""
    if source_timestamp is None:
        return None
    try:
        published = datetime.fromtimestamp(int(source_timestamp), tz=timezone.utc)
        return (datetime.now(timezone.utc) - published).total_seconds() / 3600
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _freshness_caveats(source_timestamp) -> list[str]:
    """Disclose source publish age; flag when the source timestamp is unusable."""
    age = _source_publish_age_hours(source_timestamp)
    if age is None:
        return ["mfl_adp_timestamp_unavailable"]
    return [f"source_publish_age_h={int(age)}"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): two freshness clocks (cache age vs source publish age)"
```

---

## Task 6: `fetch_adp_with_cache` — 3-stage degrade

**Files:**
- Modify: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def _write_adp_cache(path, fetched_at, source_ts, rows, ttl=24):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "fetched_at": fetched_at, "source_timestamp": source_ts,
        "ttl_hours": ttl, "data": rows,
    }))


def test_adp_stage1_fresh_cache_served(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m
    fresh = datetime.now(timezone.utc).strftime(m._TS_FMT)
    _write_adp_cache(m._adp_cache_file(2026), fresh, str(int(__import__("time").time())), _adp_player_rows())
    with patch("httpx.get", side_effect=AssertionError("must not hit network when fresh")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert any(c.startswith("source_publish_age_h=") for c in caveats)


def test_adp_stage2_stale_serve_carries_both_ages(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime(m._TS_FMT)
    _write_adp_cache(m._adp_cache_file(2026), old, str(int(__import__("time").time()) - 48 * 3600), _adp_player_rows())
    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert "stale_market_data" in caveats
    assert any(c.startswith("cache_age_h=") for c in caveats)
    assert any(c.startswith("source_publish_age_h=") for c in caveats)


def test_adp_stage3_cold_fail(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m
    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert rows == []
    assert "market_data_unavailable" in caveats


def test_adp_live_refresh_parses_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self): ...
        def json(self): return json.loads(ADP_FIXTURE.read_text())

    with patch("httpx.get", return_value=_Resp()):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert "junk" not in rows[0]                       # sanitized
    assert m._adp_cache_file(2026).exists()            # cached season-scoped


def test_adp_wrong_season_cache_not_served(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m
    fresh = datetime.now(timezone.utc).strftime(m._TS_FMT)
    _write_adp_cache(m._adp_cache_file(2025), fresh, str(int(__import__("time").time())), _adp_player_rows())
    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)   # asks for 2026, only 2025 cached
    assert rows == []
    assert "market_data_unavailable" in caveats
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -k adp_stage -q`
Expected: FAIL (`cannot import name 'fetch_adp_with_cache'`).

- [ ] **Step 3: Implement `fetch_adp_with_cache` + cache I/O**

Append to `mfl_adp_adapter.py`:

```python
def _load_cache(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def _save_cache(path: Path, data, ttl_hours: int, source_timestamp) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "fetched_at": datetime.now(timezone.utc).strftime(_TS_FMT),
            "source_timestamp": source_timestamp,
            "ttl_hours": ttl_hours,
            "data": data,
        }))
    except Exception:
        pass


def _get_json(url: str) -> dict:
    resp = httpx.get(url, headers={"User-Agent": _USER_AGENT}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_adp_with_cache(season: int | None = None) -> tuple[list[dict], list[str]]:
    """(sanitized ADP rows, transient caveats). 3-stage degrade. Never raises."""
    season = season or _current_season()
    path = _adp_cache_file(season)
    cached = _load_cache(path)

    # Stage 1: fresh cache (fetched_at clock)
    if cached:
        age = _cache_age_hours(cached.get("fetched_at", ""))
        if age is not None and age < cached.get("ttl_hours", ADP_TTL_HOURS):
            return cached["data"], _freshness_caveats(cached.get("source_timestamp"))

    # Attempt live refresh
    try:
        payload = _get_json(ADP_API_URL_TEMPLATE.format(year=season)).get("adp", {})
        rows = _sanitize_adp(_as_list(payload.get("player")))
        source_ts = payload.get("timestamp")
        _save_cache(path, rows, ADP_TTL_HOURS, source_ts)
        return rows, _freshness_caveats(source_ts)
    except Exception:
        pass

    # Stage 2: stale serve (cache present but refresh failed)
    if cached:
        caveats = ["stale_market_data"]
        cache_age = _cache_age_hours(cached.get("fetched_at", ""))
        if cache_age is not None:
            caveats.append(f"cache_age_h={int(cache_age)}")
        caveats += _freshness_caveats(cached.get("source_timestamp"))
        return cached["data"], caveats

    # Stage 3: cold fail
    return [], ["market_data_unavailable"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): fetch_adp_with_cache 3-stage degrade + season-scoped cache"
```

---

## Task 7: `fetch_players_with_cache` — id→{name,position,team} map

**Files:**
- Modify: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_players_live_refresh_builds_map(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self): ...
        def json(self): return json.loads(PLAYERS_FIXTURE.read_text())

    with patch("httpx.get", return_value=_Resp()):
        pmap, caveats = m.fetch_players_with_cache(2026)
    first = _players_rows()[0]
    assert pmap[first["id"]]["name"] == first["name"]
    assert pmap[first["id"]]["position"] == first["position"]
    assert m._players_cache_file(2026).exists()


def test_players_cold_fail_returns_empty_map_with_caveat(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m
    with patch("httpx.get", side_effect=Exception("network error")):
        pmap, caveats = m.fetch_players_with_cache(2026)
    assert pmap == {}
    assert "mfl_players_map_unavailable" in caveats


def test_players_handles_singleton(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self): ...
        def json(self):  # bare object, not a list
            return {"players": {"player": {"id": "1", "name": "Solo, Han", "position": "WR", "team": "FA"}}}

    with patch("httpx.get", return_value=_Resp()):
        pmap, _ = m.fetch_players_with_cache(2026)
    assert pmap["1"]["name"] == "Solo, Han"
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -k players -q`
Expected: FAIL (`cannot import name 'fetch_players_with_cache'`).

- [ ] **Step 3: Implement `fetch_players_with_cache`**

Append to `mfl_adp_adapter.py`:

```python
def _rows_to_player_map(rows: list[dict]) -> dict[str, dict]:
    return {r["id"]: {"name": r.get("name"), "position": r.get("position"), "team": r.get("team")}
            for r in rows if r.get("id") is not None}


def fetch_players_with_cache(season: int | None = None) -> tuple[dict[str, dict], list[str]]:
    """({mfl_id: {name,position,team}}, transient caveats). Independent 3-stage degrade. Never raises."""
    season = season or _current_season()
    path = _players_cache_file(season)
    cached = _load_cache(path)

    if cached:
        age = _cache_age_hours(cached.get("fetched_at", ""))
        if age is not None and age < cached.get("ttl_hours", PLAYERS_TTL_HOURS):
            return _rows_to_player_map(cached["data"]), []

    try:
        payload = _get_json(PLAYERS_API_URL_TEMPLATE.format(year=season)).get("players", {})
        rows = _sanitize_players(_as_list(payload.get("player")))
        _save_cache(path, rows, PLAYERS_TTL_HOURS, payload.get("timestamp"))
        return _rows_to_player_map(rows), []
    except Exception:
        pass

    if cached:
        return _rows_to_player_map(cached["data"]), ["stale_players_map"]

    return {}, ["mfl_players_map_unavailable"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): fetch_players_with_cache id->name/position map (independent degrade)"
```

---

## Task 8: `normalize_mfl_adp_entry` — join + coerce + intrinsic caveats

**Files:**
- Modify: `src/dynasty_genius/adapters/mfl_adp_adapter.py`
- Test: `tests/test_mfl_adp_adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_normalize_matched_row():
    from src.dynasty_genius.adapters.mfl_adp_adapter import normalize_mfl_adp_entry, _rows_to_player_map
    pmap = _rows_to_player_map(_players_rows())
    row = _adp_player_rows()[0]   # id 17472, matched
    out = normalize_mfl_adp_entry(row, pmap)
    assert out["mfl_id"] == row["id"]
    assert out["full_name"] == pmap[row["id"]]["name"]
    assert out["position"] == pmap[row["id"]]["position"]
    assert out["market_adp_rank"] == int(row["rank"])
    assert out["market_average_pick"] == float(row["averagePick"])
    assert out["market_min_pick"] == int(row["minPick"])
    assert out["market_max_pick"] == int(row["maxPick"])
    assert out["draft_selection_pct"] == float(row["draftSelPct"])
    assert out["drafts_selected_in"] == int(row["draftsSelectedIn"])
    assert out["source"] == "mfl_rookie_adp"
    assert out["decision_supported"] is False
    assert "mfl_adp_format_blended_qb_count" in out["caveats"]
    assert "mfl_adp_te_premium_unfiltered" in out["caveats"]


def test_normalize_unmatched_row_has_none_identity():
    from src.dynasty_genius.adapters.mfl_adp_adapter import normalize_mfl_adp_entry, _rows_to_player_map
    pmap = _rows_to_player_map(_players_rows())
    unmatched = [r for r in _adp_player_rows() if r["id"] == "99999"][0]
    out = normalize_mfl_adp_entry(unmatched, pmap)
    assert out["mfl_id"] == "99999"
    assert out["full_name"] is None
    assert out["position"] is None
    assert out["decision_supported"] is False        # still overlay-only
    assert out["market_adp_rank"] == int(unmatched["rank"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -k normalize -q`
Expected: FAIL (`cannot import name 'normalize_mfl_adp_entry'`).

- [ ] **Step 3: Implement `normalize_mfl_adp_entry`**

Append to `mfl_adp_adapter.py`:

```python
def _as_int(v):
    return int(float(v)) if v is not None else None


def _as_float(v):
    return float(v) if v is not None else None


def normalize_mfl_adp_entry(adp_row: dict, players_map: dict[str, dict]) -> dict:
    """One self-describing overlay row. Intrinsic caveats + decision_supported ride on the row."""
    mfl_id = adp_row.get("id")
    ident = players_map.get(mfl_id, {})
    return {
        "mfl_id": mfl_id,
        "full_name": ident.get("name"),
        "position": ident.get("position"),
        "nfl_team": ident.get("team"),
        "market_adp_rank": _as_int(adp_row.get("rank")),
        "market_average_pick": _as_float(adp_row.get("averagePick")),
        "market_min_pick": _as_int(adp_row.get("minPick")),
        "market_max_pick": _as_int(adp_row.get("maxPick")),
        "draft_selection_pct": _as_float(adp_row.get("draftSelPct")),
        "drafts_selected_in": _as_int(adp_row.get("draftsSelectedIn")),
        "source": "mfl_rookie_adp",
        "decision_supported": False,
        "caveats": list(INTRINSIC_CAVEATS),
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/mfl_adp_adapter.py tests/test_mfl_adp_adapter.py
git commit -m "feat(mfl-adp): normalize_mfl_adp_entry — join, coerce, intrinsic caveats"
```

---

## Task 9: `MflAdpMarketSource` wrapper

**Files:**
- Modify: `src/dynasty_genius/adapters/market_source.py`
- Test: `tests/test_mfl_adp_adapter.py` and `tests/test_market_overlay.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_market_overlay.py` (mirrors `test_fantasycalc_market_source_is_subclass_of_market_source`):

```python
def test_mfl_adp_market_source_is_subclass_of_market_source():
    from src.dynasty_genius.adapters.market_source import (
        MarketSource,
        MflAdpMarketSource,
    )
    assert issubclass(MflAdpMarketSource, MarketSource)
```

Add to `tests/test_mfl_adp_adapter.py`:

```python
def test_market_source_fetch_returns_rows_only(tmp_path, monkeypatch):
    monkeypatch.setattr("src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR", tmp_path)
    from src.dynasty_genius.adapters.market_source import MflAdpMarketSource

    def _resp_for(url, **kwargs):
        class _R:
            def raise_for_status(self): ...
            def json(self):
                if "TYPE=players" in url:
                    return json.loads(PLAYERS_FIXTURE.read_text())
                return json.loads(ADP_FIXTURE.read_text())
        return _R()

    with patch("httpx.get", side_effect=_resp_for):
        rows = MflAdpMarketSource(season=2026).fetch()
    assert isinstance(rows, list)
    assert all(isinstance(r, dict) for r in rows)
    assert all(r["decision_supported"] is False for r in rows)
    # matched row got a name; unmatched (99999) stayed None
    by_id = {r["mfl_id"]: r for r in rows}
    assert by_id["17472"]["full_name"] is not None
    assert by_id["99999"]["full_name"] is None
    # rows-only: no bare caveat list leaked into the return value
    assert not any("market_data_unavailable" == r for r in rows)


def test_market_source_default_season_is_current(monkeypatch):
    from src.dynasty_genius.adapters.market_source import MflAdpMarketSource
    src = MflAdpMarketSource()
    from src.dynasty_genius.adapters.mfl_adp_adapter import _current_season
    assert src.season == _current_season()
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py -k market_source tests/test_market_overlay.py -k mfl_adp_market_source -q`
Expected: FAIL (`cannot import name 'MflAdpMarketSource'`).

- [ ] **Step 3: Add the wrapper**

In `src/dynasty_genius/adapters/market_source.py`, add after `FantasyCalcMarketSource`:

```python
class MflAdpMarketSource(MarketSource):
    """MFL rookie ADP overlay. Season via constructor (default = current season).

    fetch() returns rows only (MarketSource contract); intrinsic caveats ride on each
    row, transient cache/source caveats stay on the adapter fetch_*_with_cache() calls.
    Overlay only — never an Engine A/B input. Not for SF-QB calibration.
    """

    def __init__(self, season: int | None = None) -> None:
        from src.dynasty_genius.adapters.mfl_adp_adapter import _current_season
        self.season = season if season is not None else _current_season()

    def fetch(self) -> list[dict]:
        from src.dynasty_genius.adapters.mfl_adp_adapter import (
            fetch_adp_with_cache,
            fetch_players_with_cache,
            normalize_mfl_adp_entry,
        )
        adp_rows, _adp_caveats = fetch_adp_with_cache(self.season)
        players_map, _players_caveats = fetch_players_with_cache(self.season)
        return [normalize_mfl_adp_entry(r, players_map) for r in adp_rows]
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_mfl_adp_adapter.py tests/test_market_overlay.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/market_source.py tests/test_mfl_adp_adapter.py tests/test_market_overlay.py
git commit -m "feat(mfl-adp): MflAdpMarketSource wrapper (season via constructor, rows-only fetch)"
```

---

## Task 10: Full-suite guard + governance validation + ledger

**Files:**
- Modify: `docs/agent-ledger/2026-05-27.md`
- Verify only: full test suite + `scripts/validate_governance.py`

- [ ] **Step 1: Run the full suite (with the AGENT_SYNC exclusion list)**

Run: `./.venv/bin/python3.14 -m pytest -q --ignore=<excluded files per AGENT_SYNC.md>`
Expected: PASS, 0 failed. Confirm no pre-existing test regressed.

- [ ] **Step 2: Confirm `tests/contract/test_market_overlay_pvo.py` is UNTOUCHED**

Run: `git status --porcelain tests/contract/test_market_overlay_pvo.py`
Expected: empty output (the PVO contract test must not be modified — MFL stays unwired from PVO).

- [ ] **Step 3: Run governance validation**

Run: `./.venv/bin/python3.14 scripts/validate_governance.py`
Expected: PASS.

- [ ] **Step 4: Confirm no MFL cache committed**

Run: `git status --porcelain app/cache/mfl_adp/`
Expected: empty (cache dir is runtime-only; add `app/cache/mfl_adp/` to `.gitignore` if not already covered by `app/cache/`).

- [ ] **Step 5: Append the ledger entry and commit**

Add a Claude Code entry to `docs/agent-ledger/2026-05-27.md` summarizing the build (adapter + registry + leakage gate; overlay-only, decision_supported=False, unwired, not-for-calibration; full suite + governance green), then:

```bash
git add docs/agent-ledger/2026-05-27.md
git commit -m "docs(ledger): MFL rookie ADP overlay (Increment 1) build complete"
```

---

## Self-Review

**1. Spec coverage:**
- §1 adapter/wrapper/registry/tests → Tasks 4–9, 3, 2. ✓
- §2 live-locked params (ROOKIES=1, not IS_KEEPER) → Task 1 probe + Task 4 URL test. ✓
- §3.1 season-scoped cache, allowlist sanitizer, two TTLs, `_as_list` singleton → Tasks 4, 6, 7. ✓
- §3.2 `MarketSource.fetch()→list[dict]`, season via constructor, intrinsic-on-row vs transient-on-channel → Task 9. ✓
- §4 freshness two-clock + `mfl_adp_timestamp_unavailable` + stale carries both ages → Tasks 5, 6. ✓
- §4 intrinsic caveats + `decision_supported=False` → Task 8. ✓
- §5 3-stage degrade (both fetches), independent degrade → Tasks 6, 7. ✓
- §6 registry entry + leakage gate (explicit `draft_selection_pct`/`drafts_selected_in`) → Tasks 3, 2. ✓
- §7 fixtures, list-vs-singleton, unmatched id, wrapper test, **PVO test untouched** → Tasks 1, 7, 8, 9, 10. ✓
- §1 non-goals (unwired, no PVO, no Sleeper crosswalk) → enforced by Task 10 Step 2 + no consumer tasks. ✓

**2. Placeholder scan:** Task 1 fixture values are captured live (real probed ids seeded; `"Last, First"` replaced from the live players export at execution) — concrete commands given, not a TODO. No "TBD"/"handle edge cases".

**3. Type consistency:** `fetch_adp_with_cache`/`fetch_players_with_cache` return `(data, caveats)` everywhere; `normalize_mfl_adp_entry(adp_row, players_map)` signature consistent across Tasks 8–9; field names (`market_adp_rank`, `draft_selection_pct`, `drafts_selected_in`) identical in normalize (Task 8), leakage gate (Task 2), and wrapper test (Task 9); `_current_season`/`_as_list`/`_rows_to_player_map` defined before use.
