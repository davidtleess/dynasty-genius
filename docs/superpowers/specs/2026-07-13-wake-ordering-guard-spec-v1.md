# Wake-Ordering Guard — Spec v1 (post-Codex RED, 2026-07-13)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store 3s before the fresh capture landed and degraded honestly (`market_source_prior_date`). Fix = a bounded same-day retry, specified below to the RED's five contracts. **Implementation + schedule changes are David-gated; this spec is the build RED's input.**

## C1 — Retry state machine (exact, executable)
- On start: pin `target_snapshot_date` = the runner's calendar day (local, at process start; never re-derived mid-run).
- Read the market store. If fresh (source date == target) → proceed (retries_used=0).
- **Retryable condition: `market_source_prior_date` ONLY.** Missing, corrupt, ambiguous, or unreadable stores FAIL IMMEDIATELY (current behavior preserved — no retry can mask a broken store).
- Poll loop: `deadline = monotonic_start + WINDOW` (WINDOW=30min, config); sleep INTERVAL=60s (config); each iteration does a FULL fresh read + freshness evaluation with a fresh wall-clock sample. `retries_used` = number of polling reads AFTER the initial read (0 when the first read is fresh).
- Oversleep-safe: the loop conditions on `monotonic() < deadline`, never on iteration count; a final read is performed AT deadline expiry before declaring exhaustion.
- Exhaustion → the existing honest degraded path, with `retries_used` recorded.

## C2 — Clock model (no stale `now`)
- `target_snapshot_date` pinned once (C1). Every freshness check uses a FRESH wall-clock read. `captured_at`/build timestamps are sampled AFTER the wait completes (post-gate). `finished_at` is sampled at terminal write time.
- **Cross-midnight rule:** if a poll's fresh wall-clock date != `target_snapshot_date`, the run exits via the degraded path immediately ("window crossed midnight; target day unreachable") — the guard never publishes day-N data as day-N+1.

## C3 — PVO re-verification after the gate (the RED-discovered race)
- The PVO bundle is re-resolved AND hash-re-verified AFTER the market gate opens (immediately before read/consumption). A PVO that changed during the wait is re-verified on its NEW content; verification failure = the existing PVO fail-close. No verified-then-swapped read is possible.

## C4 — Single-flight ownership (no double writes)
- The runner takes a crash-released exclusive lock (O_EXCL lockfile with PID + monotonic start; stale-lock recovery on age > 2×WINDOW) covering polling through terminal publication.
- A second invocation while locked exits 0 with a distinct `skipped_concurrent` marker (never queues, never overwrites).
- Build → publish → history-append execute EXACTLY ONCE, outside the polling loop, only after the gate resolves. Temp paths become per-invocation (suffix = pid).

## C5 — Capture-health terminal-only contract
- Polling iterations emit structured log lines only; the PREVIOUS terminal marker is untouched during the window (a watcher mid-wait sees the last true terminal state, never a partial).
- Exactly one terminal marker write per run: success OR exhaustion OR post-gate failure. `retries_used` (nonnegative int) appears on EVERY terminal path, including downstream failures after a successful wait. Health registration (#148 semantics) unchanged: status evaluated before freshness; `ok`/`noop` accepted.

## Out of scope (named)
LaunchAgent schedule changes (the 09:00/09:40 offsets), a capture-completion sentinel file as an alternative trigger (evaluated in the RED as a future option), and any change to capture-side code.

## Verification plan (build RED seeds)
Injected-stale-store retry-success test; retry-exhaustion test; corrupt-store fail-fast test; PVO-swap-during-wait test (C3); concurrent-invocation test (C4); cross-midnight test (C2); terminal-marker-untouched-during-poll test (C5).
