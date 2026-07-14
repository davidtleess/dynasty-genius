# Wake-Ordering Guard — Spec v4 (STANDALONE; post-RED round 4, 2026-07-13)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly (`market_source_prior_date`). **Mechanism (RED-CLEAR rounds 2–4): bounded polling of the transactional FC SQLite store.** The capture report is REJECTED as a sentinel. Implementation and schedule changes are David-gated; this document is the complete, self-contained normative contract for the build RED — it supersedes drafts v0–v3 and imports nothing.

## Named build-fix prerequisites (defects found by this spec's RED cycle)
- **BF-1:** the current reader labels ALL source-date inequality as `market_source_prior_date`; the classifier must split prior vs future before the guard lands.
- **BF-2:** player/trade consumers read `*_latest.json` directly with no marker/coverage validation; a **centralized verified loader** (G4) is required or generation checking is bypassable.

## G1 — Retry state machine
- Pin `target_snapshot_date` = timezone-aware **UTC** date at process start; never re-derived.
- Classification of every read (initial, polling, and final): `source_date == target` → FRESH (proceed); `source_date < target` → RETRYABLE (only this); `source_date > target` → FATAL (clock skew/misconfig; fail immediately); missing/corrupt/ambiguous/unreadable → FATAL.
- Config: `WINDOW=1800s`, `INTERVAL=60s` defaults; validated finite positive integers with `INTERVAL ≤ WINDOW`; violation = config-error terminal (G6) with no run.
- Loop, normative, per wake: (1) fresh UTC wall sample — if its date != target → CROSS-MIDNIGHT terminal ("target day unreachable"); (2) resample `now_mono`; if `now_mono ≥ deadline` (`deadline = start_mono + WINDOW`, in-process only, never persisted) → perform the FINAL read; (3) else read + classify; (4) sleep `min(INTERVAL, deadline − now_mono)` (never negative).
- **The final read is classified normally**: FRESH → proceed to publication; RETRYABLE → exhaustion terminal; FATAL → fatal terminal. Monotonic time is resampled immediately before and after each read (reads themselves may be slow).
- Large overshoot collapses to the final read — one read, one terminal, no extra cycles.
- `retries_used` = count of reads after the initial one (0 on immediate-fresh), recorded on every terminal.

## G2 — PVO contract
- Resolved and re-verified AFTER the market gate opens, immediately before consumption.
- **Verified-bytes consumption:** hash and load from the same read bytes/fd; hash-then-reopen-by-path is banned.
- `source_as_of`: non-null, parseable, timezone-aware, normalized to UTC, and ON the target UTC day; malformed/missing/prior-day = immediate PVO fail-close (not retryable).
- **Canonical hash inputs (pinned):** SHA-256 over (a) the exact consumed PVO bytes; (b) the exact consumed PVO-coverage bytes; (c) the ordered market rows serialized as sorted-key JSON sorted by player id. **Output hashes** (the published latest + coverage bytes, post-serialization) are computed at publish and recorded on the marker (G3) — input hashes alone do not bind outputs.

## G3 — Generation commit (three-way)
- `generation_id` = unique per OWNING invocation (uuid4), regenerated on every restart — never reused.
- Both output artifacts are stamped with it pre-rename. Rename order: latest, then coverage.
- **Commit = the ok marker.** The run is committed only when `marker.generation_id == latest.generation_id == coverage.generation_id`. After rename-2 but before the marker, the pair is PROVISIONAL — the standing marker still names generation A, so health/consumers treat the B-pair as uncommitted.
- The marker records the generation id AND the output hashes (G2) — binding the committed pair to exact bytes.
- Restart reconciliation: the next owning run publishes its own full generation (renames + marker); any provisional predecessor is simply superseded.

## G4 — Enforcement surface (build scope, BF-2)
- A **centralized verified loader** is the only sanctioned read path for the pair: it checks marker status == ok AND the three-way generation match AND (optionally, config) output hashes before returning data; mismatch → the degraded/absent contract of the calling surface.
- **#148 health extension:** the market-divergence health facts gain `generation_id` and output-hash fields; the checker verifies the three-way match. Until the loader + facts land, generation checking is bypassable — this is why G4 is a named prerequisite, not an option.

## G5 — Ownership
- Lock: `LOCK_EX | LOCK_NB` on a **stable, never-unlinked** lock file path (config-pinned; created once, never deleted by runs), held on an open fd from acquisition through terminal publication; kernel releases on any process death. No age heuristics, no stealing.
- `EWOULDBLOCK` (live owner) → canonically SILENT (no marker, no report), structured log, **exit nonzero** (distinct code: contention).
- Any OTHER acquisition failure (permissions/IO/missing dir) → also canonically SILENT (ownership was not obtained; another owner may exist), structured log, **exit nonzero** (distinct code: lock-error). **No no-lock path ever writes shared state.**

## G6 — Terminal contract (marker-last, schema-compatible)
- Write ordering: shared report first, **marker last** — the marker is the commit point and canonical truth.
- **Schema compatibility (#148): the field is `reason`**, not `failure_reason` (a mismatch surfaces as `producer_failure:unreported`). Terminal statuses use the registered vocabulary (`ok`, plus failure statuses with `reason`).
- Report-write failure → the terminal marker records failed w/ `reason=report_write_failed` (single marker write, still last). A report-first "success" is PROVISIONAL until the ok marker with the same generation commits it.
- **One atomic marker attempt** (temp + rename). If the marker write ITSELF fails: no retry loop — structured log to stderr and **exit nonzero**; the standing (previous) marker remains canonical and the run reads as uncommitted. "Every terminal path gets a marker" is thereby qualified: every path ATTEMPTS exactly one marker; attempt-failure degrades to log+nonzero.
- `retries_used` (nonnegative int) on the marker for every successful marker write; marker/report agreement is claimed only where both writes succeed (marker authoritative otherwise).
- Pre-gate failures (config error, FATAL classification, PVO fail-close) follow the same single-attempt marker contract.

## G7 — History exact-set reconciliation
- The day's history write is ONE transaction: `DELETE WHERE capture_date = day` then INSERT the full candidate set. Replaying `{A,B}` as `{A}` leaves exactly `{A}`. Executed once per owning invocation, inside the publication phase (after the gate, before the marker).

## Expected-result verification matrix (complete; every row = a build-RED test)
| # | Scenario | Expected |
|---|----------|----------|
| 1 | Immediate fresh | proceed; retries_used=0; ok marker w/ generation + output hashes |
| 2 | Stale then fresh mid-window | proceed; retries_used=N |
| 3 | Stale through window | final read RETRYABLE → exhaustion terminal; degraded path; retries_used recorded |
| 4 | Final-at-deadline read FRESH | proceeds to publication |
| 5 | Future source_date (any read) | FATAL terminal immediately |
| 6 | Corrupt/missing store (any read, incl. mid-window transition) | FATAL terminal immediately |
| 7 | Config invalid (zero/negative/INTERVAL>WINDOW) | config-error terminal; no run |
| 8 | Cross-midnight at any wake | degraded terminal "target day unreachable" |
| 9 | Wall-clock jump either direction | monotonic deadline unaffected; classification uses fresh wall samples |
| 10 | Large oversleep past deadline | exactly one final read then terminal |
| 11 | PVO swapped during wait | re-verification consumes new bytes or fails close; no verify/load gap (bytes-consumption) |
| 12 | PVO hash-valid but prior-day source_as_of | PVO fail-close |
| 13 | PVO source_as_of malformed/missing/naive | PVO fail-close |
| 14 | Kill after rename-1 (latest=B, coverage=A, marker=A) | health degraded (three-way mismatch); verified loader refuses; restart publishes clean C |
| 15 | Kill after rename-2 pre-marker (pair=B, marker=A) | pair PROVISIONAL; health keyed to marker generation A; restart publishes clean C |
| 16 | Marker write fails | log + exit nonzero; previous marker canonical; run uncommitted |
| 17 | Report write fails | marker failed w/ reason=report_write_failed |
| 18 | {A,B}→{A} same-day history replay | exact set {A} (transactional delete+insert) |
| 19 | Lock contention (live owner) | silent, log, exit nonzero (contention code); no shared writes |
| 20 | Lock acquisition error (non-contention) | silent, log, exit nonzero (lock-error code); no shared writes |
| 21 | Owner crash mid-poll | kernel releases lock; next run acquires; no stale-lock handling needed |
| 22 | Restart after any kill point | at-most-once per invocation; boundaries idempotent (rename atomicity, G7 exact-set, single marker) |
| 23 | Verified loader vs each mixed state (14/15/16) | refuses/degrades per surface contract |
| 24 | retries_used marker/report agreement | equal where both written; marker authoritative otherwise |
