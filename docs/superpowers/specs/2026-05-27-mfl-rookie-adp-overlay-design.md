---
title: MFL Rookie ADP Overlay (Increment 1) — Design Spec
status: APPROVED design (David, 2026-05-27) — reviewed by Codex (must-fixes folded in)
date: 2026-05-27
author: Claude Code (brainstormed with David; design-reviewed by Codex)
parent: docs/strategies/Dynasty Genius — Phase 24 Follow-up Scoping- Mock-Draft & Dynasty ADP Sources.md (Follow-up B); team convergence in docs/agent-ledger/2026-05-27.md
governance_hold: Frontend remains on the Phase 12 HOLD; backend only. NOISE_BAND lock untouched.
---

# MFL Rookie ADP Overlay — Increment 1

## 0. What we're building

A read-only market-overlay adapter for **MyFantasyLeague's public rookie ADP**, mirroring the existing
FantasyCalc adapter. It fetches real-draft dynasty rookie ADP, joins it to MFL's player map for
name/position, and emits normalized overlay rows. This is the first increment of Follow-up B (dynasty
ADP ingestion). It is **pure plumbing**: the adapter exists and is tested, but is **not wired into any
decision surface, Engine, PVO consumer, or endpoint**.

The new value over FantasyCalc (already integrated) is that MFL ADP is **real completed-draft** rookie
data — a distinct, real-draft-derived signal — not crowd trade values.

## 1. Scope & non-goals

**In scope (Increment 1):**
- `src/dynasty_genius/adapters/mfl_adp_adapter.py` — adapter (fetch + cache + normalize), structural twin of `fantasycalc_adapter.py`.
- `MflAdpMarketSource(MarketSource)` in `src/dynasty_genius/adapters/market_source.py`.
- `mfl_rookie_adp` registration in `src/dynasty_genius/sources/source_registry.py` (role `market_overlay`).
- Tests: dedicated adapter unit tests; a `MarketSource` wrapper test in `tests/test_market_overlay.py`; an extension to `tests/test_market_leakage_gate.py`; committed fixtures.

**Explicit non-goals (scope fences — do NOT do these in Increment 1):**
- **Not used for SF-QB calibration** (MFL aggregate cannot filter SF QB-count or TE-premium; a 1QB/SF blend would bias the QB-promotion axis). Sleeper corpus expansion is a **separate Increment 2**.
- No consumer/endpoint/Engine/PVO wiring. **Do NOT touch `tests/contract/test_market_overlay_pvo.py`** — it is FantasyCalc/PVO-consumer-specific, and editing it would imply MFL is wired into PVO surfaces.
- No MFL→Sleeper-id cross-walk. MFL IDs stay **source-local identity only**; a later consumer increment performs the universe join via the Phase 9.5 prospect-identity-join (`docs/superpowers/specs/2026-05-14-phase9-5-prospect-identity-join.md`).
- No veteran/startup feed (rookie-only). No per-league drill-down. No NOISE_BAND or frontend change.

## 2. Source contract (live-probed; re-verify at build)

The research brief's `IS_KEEPER=Rookie Only` param is **invalid** (returns `{error: Invalid value for IS_KEEPER}`). The params below were locked from a live probe on 2026-05-27 and **must be re-verified live before the fixture is captured**.

**ADP endpoint** (per season `{year}`):
```
https://api.myfantasyleague.com/{year}/export?TYPE=adp&PERIOD=RECENT&FCOUNT=12&IS_PPR=1&ROOKIES=1&IS_MOCK=No&JSON=1
```
Live-probed response shape (2026, 122 rookies across 628 drafts):
```jsonc
{ "adp": {
    "timestamp": "<unix or string publish time>",
    "totalDrafts": "628",
    "totalPicks": "...",
    "player": [ { "id": "17472", "rank": "1", "averagePick": "1.43",
                  "minPick": "1", "maxPick": "38",
                  "draftSelPct": "95", "draftsSelectedIn": "628" }, ... ]
} }
```
Note: all values arrive as **strings**; the adapter coerces numerics. When a single player matches, MFL
may return `player` as a **bare object rather than a list** — the adapter normalizes list-vs-singleton.

**Players endpoint** (authoritative id→name/position/team map; near-static):
```
https://api.myfantasyleague.com/{year}/export?TYPE=players&JSON=1
```
Yields `players.player[]` of `{id, name, position, team, ...}`. Same list-vs-singleton normalization;
**fixture-lock the exact field names** during the build. We keep only `id, name, position, team`.

**Settings match:** `FCOUNT=12` (team count) + `IS_PPR=1` + `ROOKIES=1` match three of four league constraints. **SF QB-count and TE-premium are NOT filterable** → the binding format-blend caveats (§4).

## 3. Components & data flow

### 3.1 `mfl_adp_adapter.py` (mirrors `fantasycalc_adapter.py`)

- **Constants:** `ADP_API_URL_TEMPLATE`, `PLAYERS_API_URL_TEMPLATE` (both `{year}`-parameterized), `CACHE_DIR = Path("app/cache/mfl_adp")`.
- **Season resolution:** `_current_season() -> int` (calendar year; rookie-draft data is keyed to the NFL/season year). Callers may override.
- **Season-scoped cache files** (Codex must-fix #2): `adp_{season}.json` and `players_{season}.json`. A bare `adp.json` is forbidden — season must be encoded in the filename so a stale prior-class cache can never be served for the current class. Cache payload stores `fetched_at`, `source_timestamp` (from `adp.timestamp`; `null` for the players map), `ttl_hours`, and `data`.
- **TTL:** ADP `freshness_hours=24`; players map `freshness_hours=168` (7d). The two fetches **degrade independently** — a players-map failure must not blank out ADP.
- **`fetch_adp_with_cache(season) -> tuple[list[dict], list[str]]`** — 3-stage degrade (§5). Returns raw (sanitized) ADP rows + transient caveats. Never raises.
- **`fetch_players_with_cache(season) -> tuple[dict[str, dict], list[str]]`** — id→{name,position,team} map + transient caveats. Never raises.
- **Allowlist sanitizer** `_sanitize_*` — on cache write, keep only known fields (ADP: `id, rank, averagePick, minPick, maxPick, draftSelPct, draftsSelectedIn`; players: `id, name, position, team`). MFL has no redraft-contamination fields; this is a forward-safety allowlist, parity with FC's banned-field strip.
- **`normalize_mfl_adp_entry(adp_row, players_map) -> dict`** → one self-describing overlay row:
  ```python
  {
    "mfl_id": str,
    "full_name": str | None,      # from players_map; None if unmatched
    "position": str | None,
    "nfl_team": str | None,
    "market_adp_rank": int,
    "market_average_pick": float,
    "market_min_pick": int,
    "market_max_pick": int,
    "draft_selection_pct": float,
    "drafts_selected_in": int,
    "source": "mfl_rookie_adp",
    "decision_supported": False,
    "caveats": [ "mfl_adp_format_blended_qb_count",
                 "mfl_adp_te_premium_unfiltered" ],   # intrinsic; see §4
  }
  ```

### 3.2 `MflAdpMarketSource(MarketSource)` (in `market_source.py`)

- **Constructor takes the season** (Codex must-fix #1): `__init__(self, season: int | None = None)` → defaults to current season. `fetch()` has no args, matching the ABC.
- **`fetch(self) -> list[dict]`** returns **rows only** — preserving the `MarketSource.fetch() -> list[dict]` contract (FantasyCalcMarketSource also drops the adapter's transient caveats here). Flow:
  1. `adp_rows, adp_caveats = fetch_adp_with_cache(self.season)`
  2. `players_map, players_caveats = fetch_players_with_cache(self.season)`
  3. join each ADP row to `players_map` by `mfl_id`; `normalize_mfl_adp_entry`.
  4. return the normalized rows (each already carries `decision_supported=False` + intrinsic caveats).

**Caveat split (Codex must-fix #1):** *intrinsic* caveats (format-blend) ride **on every row** so they survive the wrapper boundary; *transient* caveats (stale/unavailable/timestamp) are returned only by the adapter-level `fetch_*_with_cache()` functions for callers that want them.

## 4. Caveats & governance

- **Intrinsic (every row):** `mfl_adp_format_blended_qb_count`, `mfl_adp_te_premium_unfiltered` — MFL ADP blends 1QB+2QB and TEP+non-TEP leagues; disclosed, not hidden. `decision_supported=False` on every row.
- **Transient (adapter caveat channel):** `stale_market_data` + cache age; `market_data_unavailable`; `mfl_players_map_unavailable`; `mfl_adp_timestamp_unavailable` when `adp.timestamp` is missing/unparseable (Codex must-fix #4).
- **Freshness — two distinct clocks (Codex must-fix #4 + plan clarification):** cache **both** `fetched_at` and `source_timestamp`.
  - **`fetched_at` is the cache-refresh clock only:** the adapter decides whether to attempt a live refresh when `now - fetched_at >= ttl_hours`. It governs local cache staleness, nothing else.
  - **`source_timestamp` (MFL's `adp.timestamp`, the real publish time) is the market-data freshness disclosure:** the adapter always surfaces the **source publish age** as the freshness signal. If `adp.timestamp` is missing/unparseable, fall back to disclosing only cache age and emit `mfl_adp_timestamp_unavailable`.
  - A **`stale_market_data`** caveat (emitted when an expired cache is served after a failed refresh) carries **both** the cache age (from `fetched_at`) and the source publish age (from `source_timestamp`) when both are known — the two are never conflated.
- **Constitution:** market data is price discovery, not truth. MFL ADP fields **never** enter Engine A/B training dataframes. Read-only public API, no auth, no Databricks. Frontend HOLD + NOISE_BAND lock untouched. No model pkl/manifest/contract change.

## 5. Error handling — 3-stage degrade (per fetch, never raises)

1. **Fresh cache** (`now - fetched_at < ttl_hours`) → serve cached `data`; disclose source publish age from `source_timestamp` (or `mfl_adp_timestamp_unavailable` if absent).
2. **Expired/absent cache + live fetch fails** → if a prior cache exists, serve **stale** with `stale_market_data` + age; else cold-fail.
3. **Cold fail** (no cache, fetch fails) → ADP: `[]` + `market_data_unavailable`. Players: `{}` + `mfl_players_map_unavailable` (ADP rows then emit with `full_name/position=None`).

The two fetches fail independently; ADP can succeed while the players map cold-fails (rows still emitted, just unnamed).

## 6. Source registry & test/governance wiring

- **Registry:** add to `source_registry.py`, mirroring the `fantasycalc` entry:
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
      notes=("Public documented MFL ADP API (TYPE=adp, ROOKIES=1). Real completed-draft "
             "rookie ADP. Overlay only — never enters Engine A/B training. Aggregate blends "
             "SF QB-count and TE-premium (not API-filterable); not for SF-QB calibration."),
  )
  ```
- **Leakage gate:** extend `tests/test_market_leakage_gate.py` so `mfl_rookie_adp` fields are asserted overlay-only (never in training CSVs/columns/modules), the same way FantasyCalc is gated. **Plan clarification (Codex):** `market_adp_rank` / `market_average_pick` are already caught by the existing broad `market_*` / `*rank*` patterns, but **`draft_selection_pct` and `drafts_selected_in` are NOT** — the gate must add explicit protection for those two field names.

## 7. Testing / contract intent

All tests use **committed fixtures** (small, shape-faithful — not full raw exports); **no network** in tests.

- **Fixtures:** `tests/fixtures/mfl_rookie_adp_2026_05_27.json` + `tests/fixtures/mfl_players_2026_05_27.json`, captured from a live probe (a few representative rows each, incl. one matched and one unmatched id, and a singleton case).
- **Normalize:** string→numeric coercion; matched id → name/position present; unmatched id → `full_name/position=None`; `decision_supported=False` and both intrinsic caveats on every row.
- **List-vs-singleton:** a bare `player` object normalizes to a one-element list (both ADP and players).
- **Sanitizer:** unknown/extra fields dropped on cache write; allowlist preserved.
- **Cache (monkeypatched `httpx` + tmp cache dir):** fresh serve; expired+fail → stale + age caveat; cold fail → empty + unavailable caveat; **season-scoped filename** verified (a `players_2025.json` is not served for `season=2026`).
- **Freshness:** `source_timestamp` preferred; missing/unparseable → `fetched_at` fallback + `mfl_adp_timestamp_unavailable`.
- **Independent degrade:** players cold-fail while ADP succeeds → rows emitted unnamed + `mfl_players_map_unavailable`.
- **Wrapper:** `MflAdpMarketSource(season=2026).fetch()` returns `list[dict]` (rows only), constructor season honored, default = current season.
- **Leakage gate:** `mfl_rookie_adp` fields never present in training-CSV columns (extend existing gate), **with an explicit assertion for `draft_selection_pct` and `drafts_selected_in`** (not caught by the broad `market_*`/`*rank*` patterns).
- **DO NOT** modify `tests/contract/test_market_overlay_pvo.py`.

## 8. Counter-argument (Rule 5 — mandatory)

1. **The format blend is a real signal-quality cost.** MFL can't filter to SF/non-TEP, so the rookie ADP mixes 1QB and SF leagues. Mitigation: it is an *overlay*, never a model input or a decision signal; the two intrinsic caveats + `decision_supported=False` make the skew explicit on every row; and we explicitly bar it from SF-QB calibration (where the QB-axis bias would actually matter).
2. **Two network dependencies (ADP + players) double the failure surface.** Mitigation: independent 3-stage degrade — a players-map failure only costs names, not the ADP signal; ADP cold-fail returns empty cleanly. Nothing raises.
3. **MFL string-typed, loosely-documented fields could drift.** Mitigation: fixture-lock the exact shape, allowlist-sanitize on write, coerce defensively, and normalize list-vs-singleton. Re-verify params live before capturing the fixture.
4. **"Why build an overlay nothing consumes yet?"** Increment 1 is deliberately unwired so the adapter, caching, governance, and leakage gating are proven in isolation before any consumer (a later increment) joins it into the universe via the Phase 9.5 identity-join. This keeps each increment independently testable and reviewable.
