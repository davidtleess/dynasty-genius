# Wake-Ordering Guard — Spec v3 (post-RED round 3, 2026-07-13)

Mechanism (RED-CLEAR, both rounds): **bounded polling of the transactional FC SQLite store**; the capture report is rejected as a sentinel. Carried from v2 unchanged: kernel advisory fd ownership, non-owner canonical silence, aware-UTC source comparison (retry only `source_date < target`; future fails fast; the reader's prior/future mislabel = named build fix), exact-byte PVO loading, target-day PVO gating. Implementation + schedule remain David-gated.

## C6 — Generation commit for the two-file publish (v2 finding 1)
The tracked pair (`*_latest.json` + coverage) is TWO renames, not an atomic unit. v3 protocol:
- Both artifacts are stamped with a shared `generation_id` (the run id) before any rename.
- Rename order: latest, then coverage. A crash between them leaves a DETECTABLE mixed state.
- The health check (and any consumer) verifies generation equality; mismatch ⇒ **degraded until one generation matches across both** — a mixed pair can never sit under a healthy marker. Restart reconciliation: the next owning run republishes both from its own generation (idempotent by construction).

## C7 — History exact-set reconciliation (v2 finding 2)
Per-day upsert cannot delete: replaying {A,B} as {A} leaves stale B. v3: the day's history write is **one transaction: DELETE rows for (day) THEN INSERT the full candidate set**. Restart replay of any candidate set is exact-set idempotent. (The immutable-bundle alternative is rejected: it silently freezes wrong data on a corrected rerun.)

## C8 — Marker as canonical truth; qualified agreement (v2 finding 3)
- Write ordering: **shared report first, marker LAST** — the marker write is the commit point of the run.
- Report-write failure ⇒ the terminal marker records `status=failed, failure_reason=report_write_failed` (one marker write, still last).
- The `retries_used` agreement claim is QUALIFIED to paths where both writes succeed; the marker alone is authoritative wherever they diverge.
- **Every** terminal path gets a marker, including immediate pre-gate failures (config error, future source_date, corrupt store) — no silent exits.

## C9 — Lock semantics, complete taxonomy (v2 finding 4)
- Acquisition is **non-blocking** (`LOCK_NB`).
- `EWOULDBLOCK` (a live owner) ⇒ the non-owner path: canonical silence, structured log, exit 0.
- **Any other acquisition failure** (permissions, IO, missing dir) is NOT contention ⇒ loud immediate failure with its own terminal marker — an error can never masquerade as "another run has it."

## C10 — Timing pinned exactly (v2 finding 5)
- Defaults: `WINDOW=1800s`, `INTERVAL=60s` (config; validated finite positive ints, INTERVAL ≤ WINDOW).
- Loop, normatively: after each wake — (1) UTC-rollover check FIRST (fresh wall sample; date != target ⇒ degraded exit); (2) if `now_mono ≥ deadline` ⇒ perform the FINAL read, then terminal; (3) else read + classify; (4) sleep `min(INTERVAL, deadline − now_mono)`.
- Large overshoot (wake past deadline by any amount) collapses to step (2): one final read, then terminal — never a negative sleep, never an extra cycle.

## C11 — PVO timestamp contract (v2 finding 6)
`source_as_of` must be **non-null, parseable, timezone-aware, normalized to UTC** before the vintage gate runs; malformed or missing ⇒ immediate PVO fail-close (not retryable — the market wait cannot fix a PVO defect). The terminal marker carries BOTH consumed-bytes hashes (PVO + market) as metadata, binding the published pair to the exact verified bytes.

## Verification matrix (v2's required additions folded)
All v2 seeds, plus: kill after rename-1 and after rename-2, each followed by successful AND failed restart; marker/report write failure at each ordering point; `{A,B}→{A}` same-day history replay (exact-set proof); non-blocking lock contention AND non-contention acquisition failure; default-timing validation; cross-midnight at each loop stage; wall-clock jumps (backward/forward) with monotonic deadline unaffected; immediate-fresh (retries_used=0); retryable→fatal transition mid-window (store turns corrupt during polling); malformed PVO timestamps; generation-mismatch health degradation.
