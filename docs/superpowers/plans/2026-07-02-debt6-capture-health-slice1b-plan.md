# DEBT-6 Slice 1b — Capture-Health / Gap Detector — Build Plan

**Spec:** `docs/superpowers/specs/2026-07-02-debt6-capture-health-slice1b-design.md`.
**Branch:** `feature/debt6-capture-health` (to be created on David's authorization).
**Status:** DRAFT — execution HELD pending cockpit spec CLEAR + Codex RED + David per-step authorization.

## 0. Ratified working decisions (kickoff round 2026-07-02)
- Both PIT stores in one slice, one shared contract; fc lane is the falsification-priority fixture set (unreconstructable market clock).
- Checked-in `app/config/capture_cadence.json` = the expectations source of truth (fail-closed loader → 503; empty/duplicate store_id invalid — the Slice-1 empty-registry ruling carries over).
- Freshness NEVER blocks: `overall_status ∈ {ok, degraded}`; missed capture = caveat lane (Gemini Integrity-vs-Freshness split).
- Committed tests: temp SQLite + temp config + injected clock ONLY. Real-store smoke = session activity, not CI dependency.
- No backfill/repair; no Gate-4 certification vocabulary; `decision_supported=false` recursive.

## 1. Build sequence
Each task: **Codex RED (test-only) → Claude GREEN → adversarial dual-CLEAR → David-authorized commit → both-lane post-commit zero-divergence.** Focused slices mid-build; full closeout gate at T4.

### T1 — Cadence config loader + Pydantic models
- `app/api/routes/system_capture_health_models.py`: `ConfigDict(extra="forbid")` models — `CadenceStoreConfig` (incl `expected_settings_hash`, `companion_tables`), `CompanionTableConfig`, `CaptureCadenceConfig` (incl root `timezone`), `StoreTimeline` (incl `missing_ranges_total`), `StoreStaleness`, `StoreDensity`, `StoreFlags`, `StoreHealth`, `CaptureHealthResponse`, `CaptureHealthErrorResponse` (`decision_supported: Literal[False]` everywhere).
- Fail-closed `load_capture_cadence(config_path=...)` → typed `CaptureHealthConfigError` on absent/malformed/schema-invalid/empty-stores/duplicate-store_id **/ absolute-or-escaping `db_path` / non-identifier `table`/`date_column`/companion identifiers (R3)** (503 family).
- **RED:** loader happy/absent/malformed/empty/duplicate (seed 14); path/identifier safety (seed 23); `extra="forbid"` + `gate_4_ready` injection rejection (seed 15).

### T2 — Pure timeline/gap/density/staleness analyzer
- Pure function over constructed inputs (no disk): `(store_config, date→row_count map, companion date sets, now, timezone, season_windows) → StoreHealth` — expected-window derivation (`capture_start_date` → today-if-past-deadline **in the config timezone, R4**), missing ranges + `missing_ranges_total` + max contiguous gap + consecutive-current (full-series totals under display cap, R8), density floor vs trailing-median baseline (**eligible-priors only — excludes current/future/invalid/sub-floor dates, R5**; sub-floor → gap + listed), staleness with grace, future-date exclusion + caveat, **malformed-date exclusion + caveat (R6)**, **companion coverage from per-companion start date (R1)**, **settings-hash mismatch caveat (R2)**, season-aware warn flag + window-risk flag with disclosed bases, **Class-A/Class-B caveat mapping with fail-closed default (R7)**.
- **RED:** seeds 1–11, 16, 20–22, 24–27 via constructed inputs + injected clock.

### T3 — Read-only SQLite reader + assembly
- `mode=ro` URI open; absent file → `store_absent` (never created); 0-byte/missing-table/SQLite errors → `store_unreadable` (seed 13); `source_filter` + `expected_settings_hash` grouping applied (seeds 17, 22); companion-table date extraction (seed 21); DISTINCT-date + per-date count extraction; read-only guarantee (seed 18).
- **RED:** temp SQLite fixtures mirroring the real schemas (both stores' real column names incl `settings_hash` and the companion `model_forward_prediction_snapshot`), absent/corrupt/filtered cases.

### T4 — Route + wiring + OpenAPI codegen + full closeout
- `system_capture_health.py`: `GET /api/system/capture-health`, monkeypatchable `_CONFIG_PATH`/`_REPO_ROOT`/`_CLOCK`, sanitized fixed 503 (`CaptureHealthErrorResponse`), `app/main.py` wiring, `npm run openapi-gen`.
- **RED:** end-to-end HTTP over temp config + temp stores — CI shape (both stores absent → 200 degraded, seed 12), 503 config family (seed 14, sanitized: no absolute paths/tracebacks), banned-vocabulary scan (seed 19), OpenAPI 200/503 schema refs.
- **Full closeout:** `verify_sprint_closeout.py --base origin/main` ENFORCE PASS; real-store smoke (live endpoint over the real dbs → expect `ok` with 9-day contiguous timeline as of 2026-07-02); push/PR checkpoint.

## 2. Ship shape
Spec+plan commit first on the feature branch (David-gated), then T1–T4 task commits, single PR at T4 closeout (Slice-1 pattern). Real `app/config/capture_cadence.json` ships in T4 GREEN (defaults from the spec §2; David reviews thresholds at spec CLEAR — no separate promotion assertion needed: cadence expectations are policy, not byte approvals).

## 3. Open micro-decisions for the RED to pin
- ~~`store_status=ok` ⇔ caveat mapping~~ RESOLVED (spec §3 Class-A/B + fail-closed default; pending Codex acceptance of the two-class compromise — if Codex holds any-caveat→degraded, the fork escalates to David).
- ~~Endpoint name~~ RESOLVED (`/api/system/capture-health`; Gemini + Codex both concur).
- ~~Truncation~~ RESOLVED (R8: full-series totals + `missing_ranges_truncated`).
- Whether `checked_at` uses the injected clock (test determinism) — RED pins.
