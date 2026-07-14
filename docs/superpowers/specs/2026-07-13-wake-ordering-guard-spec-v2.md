# Wake-Ordering Guard — Spec v2 (post-RED round 2, 2026-07-13)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly. Mechanism (RED-confirmed): **bounded polling of the transactional FC SQLite store** — the capture report is NOT a safe sentinel. Implementation + schedule changes are David-gated; this spec seeds the build RED.

## C1 — Retry state machine (UTC-exact)
- Pin `target_snapshot_date` = **timezone-aware UTC date** at process start (FC snapshot_date is UTC; local-date pinning was v1's error).
- Initial read; classify by comparing the store's source date to target:
  - `source_date == target` → fresh, proceed (retries_used = 0).
  - `source_date < target` → the ONLY retryable state.
  - `source_date > target` → **fail immediately** (future data = clock skew or misconfig; waiting cannot fix it).
  - Missing / corrupt / ambiguous / unreadable → fail immediately (unchanged fail-fast).
- BUILD-FIX ITEM (found by this RED): the current reader labels ALL inequality as `market_source_prior_date`; the classifier must split prior/future before any guard lands.
- Config validation at startup: WINDOW and INTERVAL are finite positive integers with INTERVAL ≤ WINDOW; violation = immediate config error, no run.
- Poll loop on a **monotonic deadline** (`start_mono + WINDOW`): each iteration sleeps `min(INTERVAL, deadline − now_mono)` (clipped final sleep), then re-checks the deadline BEFORE reading (oversleep-safe), then performs a full fresh read + classification. A final read executes at deadline expiry before exhaustion is declared. `retries_used` = polling reads after the initial read.
- Exhaustion → the existing honest degraded path with `retries_used` recorded.

## C2 — Clock model
- Fresh wall-clock (UTC) sample per classification; build timestamps sampled post-gate; `finished_at` at terminal write. Monotonic time is never persisted (invalid across reboot) — it lives only in-process.
- **Cross-midnight (UTC):** if a fresh sample's UTC date != target, exit via the degraded path ("target day unreachable") — day-N data is never published as day-N+1.

## C3 — PVO verified-bytes consumption + vintage gate
- The PVO bundle is resolved, opened, and **hashed and consumed from the same bytes**: read once into memory (or hold the open fd and load from it) — hash-then-reopen-by-path is banned; a swap between verify and load is structurally impossible.
- **Vintage gate:** PVO `source_as_of` must fall on the target UTC day; a hash-valid prior-day PVO fails the pair (wake coalescing can otherwise pair stale PVO with fresh market).
- Re-resolution + re-verification happen AFTER the market gate opens, immediately before consumption.

## C4 — Single-flight ownership (kernel-released)
- Exclusive **advisory lock held on an open fd** (`fcntl.flock`/`lockf`) for polling through terminal publication. The kernel releases it on any process death — no age heuristics, no stealing a live owner, no persisted timestamps.
- A non-owner invocation exits 0 having touched **nothing canonical**: no marker write, no shared-report write — a structured log line only (C5 conflict resolved: the owner's previous terminal marker survives untouched).
- Publication path: build → publish (atomic rename) → history append, exactly once **per owning invocation**, outside the polling loop.
- **Claim narrowed (v1 overclaimed):** the lock earns at-most-once per invocation, not exactly-once across crash/restart. Restart safety is carried by idempotence instead: re-running after a crash must be a no-op or a clean overwrite at each boundary — pair file (atomic rename), history (per-day upsert), marker (single terminal write), report (regenerated whole). Each boundary gets an explicit idempotent-restart test.

## C5 — Capture-health terminal-only contract
- Poll iterations: structured logs only; the previous terminal marker untouched until the single terminal write (success / exhaustion / post-gate failure).
- `retries_used` (nonnegative int) appears on EVERY terminal path and must AGREE between the marker and the shared report (single source populates both).
- Health semantics (#148) unchanged: status evaluated before freshness; market divergence accepts `status=ok` only — which is precisely why non-owners never write markers (finding 2).

## Verification seeds (build RED matrix)
Retry-success; retry-exhaustion; corrupt-store fail-fast; **future source_date fail-fast**; exact-deadline final read; clipped final sleep / oversleep; **stale-valid PVO (prior-day, hash-good) rejected**; **verify/load swap impossible (bytes-consumption)**; owner-crash lock release; **live-owner protection (no steal)**; non-owner leaves marker+report untouched; marker/report retries_used agreement per terminal path; **idempotent restart at pair/history/marker/report boundaries**; config validation (zero/negative/INTERVAL>WINDOW).
