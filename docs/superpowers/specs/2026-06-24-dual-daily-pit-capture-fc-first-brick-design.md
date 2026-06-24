# Dual Daily PIT Capture — FantasyCalc First Brick (A) — Design Spec

**Status:** DRAFT v2 for cockpit dual-CLEAR (round 2 — integrates Codex C1–C6: mandatory sidecar, raw/joinable report split + `decision_supported=false`, explicit retry/backoff, locked source-aware namespace, softened model-brick "without rework", expanded falsification matrix; Gemini governance CLEAR on v1). Roadmap item `wr-dual-capture` (War Room #1, the keystone). This is the **first brick** — the **market** side (FantasyCalc) daily forward-capture; the paired **model-output** brick (PVO/DVS/xVAR) is the next increment, and the store is architected to host both. Governance: `docs/governance/02-agent-operating-loop.md` → Compounding-product lens. Roadmap: `docs/superpowers/plans/2026-06-24-war-room-compounding-roadmap.md`.

## 0. Compounding-product lens (required by governance)
- **Daily-login value:** even week 1, a dated FC series enables descriptive *market trend* (1d/7d/30d value/rank deltas) on the surfaces, and seeds the model-vs-market divergence-over-time view.
- **Refresh cadence:** **daily** — FC trade-derived values move daily and David logs in daily. Daily is a **documented assumption** with backoff + fail-loud, not a confirmed entitlement (no public FC rate-limit/ToS rate page found). Scheduling lives **outside** model/surface code (cron/launchd/GitHub Action — a separate operational decision).
- **Compounding:** **capture-and-accumulate, never overwrite.** Each day appends an immutable snapshot; the series' value grows (longer trend context, an accruing benchmark, and — paired with the model brick — the vintage series that forward-resolves `MODEL_PIT_INADEQUATE` for Gate-4 over time).

## 1. Scope
Capture FantasyCalc current values **daily** into an append-only, survivorship-complete, point-in-time store, with a machine-readable capture report. **Market-only this brick.** No surface/UI change is required to land the capture; a minimal descriptive trend-read (§5) is a follow-on.

## 2. Capture contract
- Endpoint: `GET https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` (the locked Superflex settings; `settings_hash` is the existing hash of that query).
- Source family: `fc_native` (single source; never blended).
- Cadence: daily; **fail-loud** on non-200 / parse error / empty payload (no silent partial write); the run is idempotent (§3) so a retry is safe.
- **Retry/backoff (Codex C3):** transient failures (HTTP 429 / 5xx / connection timeout) → **bounded retry with exponential backoff** (`max_attempts=3`, with jitter). On **retry exhaustion** or a **fatal** error (other 4xx, malformed/empty payload) → **abort with an `aborted` capture report and NO write** (the prior snapshot stays the latest; the daily archive is never left half-written).
- Reuse `scripts/snapshot_fantasycalc.py` + the store as the base; this spec hardens them for recurring capture.

## 3. Storage contract (append-only, survivorship-complete, PIT)
- **Append-only**: a new `snapshot_date` (UTC) row-set per capture; existing snapshots are **immutable** (never overwritten/recomputed).
- **Survivorship-complete (critical) — mandatory raw sidecar:** persist **every player returned**, including those with no `sleeperId`. The current `MarketSnapshotStore` schema keys on `sleeper_id NOT NULL`, which would **silently drop** no-ID rows — that breaks survivorship. Fix (Codex C1): a **mandatory raw sidecar** (nullable-`sleeper_id` raw table) recording `source_player_key` / name / position / value for **every** returned row, with the Sleeper-keyed table as the resolved/**joinable** view. A no-`sleeperId` row is persisted in the sidecar and counted — it **never** aborts the daily archive. Fail closed **only** if a row lacks a stable `source_player_key` or is malformed beyond capture.
- **Provenance per row/run:** `snapshot_date`, `retrieved_at` (distinct UTC), `source=fc_native`, `settings_hash`.
- **Idempotency (same date + settings + source):** identical row → no-op; a **changed** value for an existing (date, player, settings, source) → **conflict hard-fail** (an immutable snapshot must not mutate); a duplicate `sleeperId` within one payload → hard-fail unless byte-identical.
- **Single-source isolation + locked namespace (Codex C4):** FC forward capture writes to a **dedicated append-only table/namespace** with a **source-aware composite key** (`snapshot_date`, `source`, `settings_hash`, `player_key`) — **NOT** the legacy `fc_snapshots` `INSERT OR REPLACE` path (whose PK omits `source` and can mix families). Never mix source families in one series (`assert_single_source_family`).

## 4. Capture report (machine-readable, every run)
Fields (Codex C2): `snapshot_date` (UTC), `retrieved_at` (UTC), **`raw_entries_written`** (every returned row → sidecar) + **`joinable_rows_written`** (resolved Sleeper-keyed rows) — both required so the report can never hide the no-Sleeper gap this spec exists to fix; `missing_sleeper_count`, `duplicate_count`, `source=fc_native`, `settings_hash`, `endpoint`, `payload_hash` + `store_hash`, `status` (`ok` / `aborted`), `aborted_reason` (when aborted), and `decision_supported=false` (this recurring benchmark artifact asserts it explicitly even though it is a utility). This is the audit surface for a scheduled run.

## 5. Surface trend-read (descriptive overlay only — follow-on increment)
Once ≥2 snapshots exist, expose **descriptive deltas** (1d/7d/30d FC value/rank change, with a missing-source caveat + sample-count/date-coverage) for the live surfaces to consume. **No buy/sell/action score, no composite, no Engine input.** This is the compounding payoff, gated by the §6 guardrail.

## 6. Guardrails (inseparable from the compounding lens)
Capture/trend is **overlay-only** — cordoned from Engine A/B decision mechanics, never folded into a buy/sell or composite score, **quarantined until a pre-registered validation (Gate-4) earns promotion.** Market data stays **out of model inputs**. No model/PVO/Engine/training/`.pkl`/UI/contract change in this brick. The capture is a data utility (not a decision surface), and its recurring **report asserts `decision_supported=false` explicitly** (§4) — consistent, not contradictory. Banned-language discipline holds. **"Daily refresh" must never become "daily false certainty."**

## 7. Architected-for-dual (the model brick next)
The model-output series (PVO/DVS/xVAR, each snapshot stamped with `model_version`/training-cutoff/provenance) reuses the **same append-only / PIT / idempotency / capture-report conventions** (Codex C5) — but, because its value/field shape differs from FC market rows, the model brick **may use a parallel table/namespace** rather than the FC table verbatim (no claim of "zero rework"). That parallel brick is what accrues the vintage model series for the eventual divergence verdict (it does not by itself guarantee a powered/passing study).

## 8. Build sequence (post-CLEAR, each its own RED→GREEN→dual-CLEAR→David-authorized commit)
1. **T1** — store/schema migration: survivorship sidecar (no silent no-Sleeper drop), append-only + idempotency conflict rules, single-source isolation. (Codex's in-tree prototype reconciles to this contract.)
2. **T2** — capture script hardening: `retrieved_at`, idempotent same-day write, fail-loud/backoff, the §4 capture report.
3. **T3 (operational, gated)** — scheduling decision + first live daily capture under the report; David authorizes the live run.
4. Follow-on increments: §5 surface trend-read; then the paired model-output brick.

## 9. Falsification matrix seeds
non-200 / empty / malformed payload → fail-loud no-write; **429/5xx/timeout retry exhaustion → `aborted` report + NO write** (prior snapshot stays latest); same-day identical re-run → no-op; same-day changed value → conflict hard-fail; duplicate `sleeperId` in payload → hard-fail unless byte-identical; row with no `sleeperId` → persisted in sidecar + counted, **never dropped**, archive not aborted; row with no stable `source_player_key` / malformed beyond capture → fail-closed; **second source family written into the FC namespace → reject** (source-aware composite key); capture report **missing any of `raw_entries_written` / `joinable_rows_written` / `decision_supported=false` / `aborted_reason`-when-aborted → fail**.
