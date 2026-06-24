# Dual Daily PIT Capture — FC First Brick — T3 Operational Plan (v2 — cockpit-CLEARED)

**Spec:** `docs/superpowers/specs/2026-06-24-dual-daily-pit-capture-fc-first-brick-design.md` (§8.3 T3).
**Branch:** `feature/dual-daily-pit-capture-fc` (spec `00dc754` → T1 `bedc143` → T2 `3478f82` committed).
**Status:** v2 draft — **execution HELD pending cockpit CLEAR + David's per-step authorization.** No tree mutation, no live fetch, no launchctl action authorized by this draft. v2 integrates Gemini's Scope-A governance CLEAR + Codex C1–C3 (Scope A settled; Scope-B blast radius corrected; docs-sweep narrowed to active state docs).

## 0. Cockpit-converged decisions ratified into this plan
- **Scheduling = REPLACE, not parallel** (Gemini governance ruling + Codex technical concurrence). Rewire the live `com.davidleess.dynasty-fc-snapshot` agent from the legacy script onto the committed T2 capture path. Parallel rejected (double daily fetch against an endpoint with no confirmed cadence entitlement; two stores with different survivorship semantics).
- **Continuity = freeze-and-supersede** (Gemini governance CONCUR). `app/data/fc_snapshots.db` (462 `fc_native` rows, Gate-4 clock since 2026-06-12) is **preserved read-only as a frozen archive.** The new survivorship-complete store is canonical going forward. **Any legacy→new migration/backfill is a SEPARATE, explicitly-planned roadmap item — out of T3.**
- **Stale WIP** already removed from the working tree via `git stash` (`stash@{0}`, two code files only: `scripts/snapshot_fantasycalc.py`, `src/dynasty_genius/eval/market_snapshot_store.py`) — recoverable; docs/ledger diffs untouched. (David-authorized 2026-06-24.)
- **Four separated, individually David-gated actions:** (1) tree/code changes commit, (2) this plan draft [done], (3) launchctl relink/reload, (4) first live FC fetch. Reload ≠ live-fetch — distinct authorizations.

## 1. Scope A — SETTLED (Gemini governance CLEAR + Codex technical CONCUR, 2026-06-24)
**Ruling: Scope A — retire the legacy collector from active scheduling; do NOT physically delete legacy code in T3.** Rewire the plist + scheduler test to the new entrypoint; docs declare the legacy script/db a frozen read-only archive. The legacy `scripts/snapshot_fantasycalc.py` + `src/dynasty_genius/eval/market_snapshot_store.py` and their tests stay in place and green — they keep the frozen `fc_snapshots.db` archive reproducible/readable **and** support live eval/backtest consumers. Preserve `app/data/fc_snapshots.db` byte-unchanged.

**Why Scope B (physical full-removal) is out of T3 — verified blast radius (Codex C2):** deletion is materially larger than the 3 scheduler/script tests. Confirmed live dependencies:
- `scripts/backfill_market_archive.py:28` imports `LEAGUE_SETTINGS_HASH` from `scripts.snapshot_fantasycalc`.
- `MarketSnapshotStore` has **4 non-test consumers** — `src/dynasty_genius/eval/backtest_harness.py`, `scripts/run_backtest.py`, `scripts/ingest_market_archive.py`, `scripts/backfill_market_archive.py` — plus **10 test files**.
- The 3 directly script-coupled tests: `tests/contract/test_harness_trust_w2a_scheduler.py:18`, `tests/contract/test_harness_trust_w2a_script.py:7`, `tests/test_snapshot_script.py:12-13`.

Physical removal therefore requires a **separate, broader eval/backtest cleanup/migration plan** (retire/relocate `LEAGUE_SETTINGS_HASH`, re-home or deprecate `MarketSnapshotStore` across its consumers, cascade the 10+ tests) — explicitly **NOT** a 3-test update, and **NOT** part of operational T3. Filed as a follow-on roadmap candidate.

## 2. Build sequence (each: Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit → zero-divergence)

### T3.1 — Concrete capture entrypoint (the CLI Codex flagged)
New `scripts/run_fc_forward_capture.py` wrapping the library-style `capture_fantasycalc_snapshot(*, db_path, report_path, fetch_json, now_fn, sleep_fn, jitter_fn)` (driver `fc_forward_capture_driver.py:135`) with **real** dependencies:
- `fetch_json` → real `httpx.get(FC_ENDPOINT)` with `.raise_for_status()` then `.json()` (so the driver's HTTPStatusError/timeout retry/backoff fires for real).
- `now_fn` → `lambda: datetime.now(timezone.utc)` (UTC, per spec §3).
- `sleep_fn` → `time.sleep`; `jitter_fn` → bounded random jitter.
- `db_path` (proposed `app/data/fc_forward_capture.db`, gitignored, parallel to `fc_snapshots.db`); `report_path` (proposed dated `app/data/capture/fc_forward_capture_report_<snapshot_date>.json`, run-provenance gitignored).
- `argparse`: `--db-path`, `--report-path`, `--preflight` (build wiring + print resolved config, NO network — always-safe dry path).
- RED: preflight emits config + no network; success path writes §4 report (all required fields incl `decision_supported=false`); non-200 → `aborted` report + NO store write; report path is written.
- Guardrail: entrypoint imports only the committed `capture/` package + stdlib + httpx; **no** legacy `snapshot_fantasycalc`/`MarketSnapshotStore` import.

### T3.2 — LaunchAgent plist rewire + scheduler contract test
- `ops/launchd/com.davidleess.dynasty-fc-snapshot.plist`: ProgramArguments → `.venv/bin/python3.14 scripts/run_fc_forward_capture.py`; update the header comment (legacy → new capture path; legacy db = frozen archive); keep `StartCalendarInterval` 09:00, `RunAtLoad=false`; log paths may move to `app/data/logs/fc_forward_capture.{out,err}.log` (ensure committed placeholder dir exists).
- Update `tests/contract/test_harness_trust_w2a_scheduler.py` to assert the **new** entrypoint path (this is the cockpit-reviewed contract change).

### T3.3 — Docs + legacy-status wording (ACTIVE state docs only — Codex C3)
Update **only active state documents** so the new capture path is identified as the active collector and the legacy script/db as a **frozen read-only legacy archive**:
- `docs/ARTIFACTS.md`, `AGENT_SYNC.md` (Gate-4 clock line → REPLACE + freeze-and-supersede), the plist header comment, and the new plan/ledger.
- **Do NOT rewrite historical specs / validation notes** (e.g. archived W2a/Gate-4 decision records) that exist to record prior state — editing them creates history drift. Scope A retains the legacy code, so no test changes here beyond T3.2's scheduler-test rewire.

### T3.4 — launchctl reload (OPERATIONAL — separately David-gated, NOT bundled with code)
Repo plist ≠ installed plist: the live agent is loaded from `~/Library/LaunchAgents/com.davidleess.dynasty-fc-snapshot.plist`. After T3.2 lands, the live job is unchanged until: copy/symlink repo plist → `~/Library/LaunchAgents/`, then `launchctl unload` + `launchctl load`. **David authorizes this reload explicitly and separately.**

### T3.5 — First live FC fetch (OPERATIONAL — separately David-gated)
Run `scripts/run_fc_forward_capture.py` live once. Validate: §4 report has every required field (`snapshot_date`, `retrieved_at`, `raw_entries_written`, `joinable_rows_written`, `missing_sleeper_count`, `duplicate_count`, `source=fc_native`, `settings_hash`, `endpoint`, `payload_hash`, `store_hash`, `status`, `aborted_reason`-when-aborted, **`decision_supported=false`**); append-only write to the new `fc_forward_capture_raw`/`_joinable` namespace; no source-family mixing; legacy `fc_snapshots.db` byte-unchanged. **David authorizes the live network fetch explicitly and separately** (distinct from T3.4).

## 3. Closeout gate
`scripts/verify_sprint_closeout.py --base origin/main` ENFORCE PASS (full Python suite + `ruff check src app` + standalone-script checks) before any commit/claim. The verifier is a commit/closeout gate, NOT a substitute for David's T3.4/T3.5 authorizations.

## 4. Guardrails (spec §6, inseparable)
Overlay-only; market data out of model inputs; **no** model/PVO/Engine A/B/training/`.pkl`/UI/contract change; `decision_supported=false` asserted by the report; banned-language discipline; "daily refresh must never become daily false certainty." Capture remains descriptive — divergence is unvalidated, not a tradeable edge.

## 5. Falsification matrix seeds (carry spec §9 + entrypoint-specific)
non-200/empty/malformed → `aborted` report + no write; 429/5xx/timeout retry exhaustion → `aborted` + no write (prior snapshot stays latest); same-day identical re-run → no-op; same-day changed value → conflict hard-fail; duplicate `sleeperId` → hard-fail unless byte-identical; no-`sleeperId` row → persisted in sidecar + counted, never dropped; second source family into FC namespace → reject; report missing any required §4 field → fail. **Entrypoint-specific:** real httpx error → correct HTTPStatusError/timeout mapping into the driver's retry path; UTC date boundary correctness; report-path parent created + written; `--preflight` performs zero network I/O.
