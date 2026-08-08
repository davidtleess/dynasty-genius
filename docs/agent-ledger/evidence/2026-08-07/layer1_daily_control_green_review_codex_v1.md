# Layer 1 daily-control GREEN review — Codex v1

Date: 2026-08-07 ET  
Layer: Layer 1  
GREEN reviewed: `src/dynasty_genius/sources/daily_control.py`  
GREEN SHA-256: `16a2e12d16656b19010dfa8b694970ce34c94ee622d23fec93564a5f41151895`  
RED SHA-256: `85f601551940e1820e8ccb9b09e31506d3580d3a81853ef68b2e886014941ea8`

## Accepted

- The reviewed RED is 44/44 GREEN.
- The full-suite cordon failure was real, correctly attributed, and repaired without weakening the
  guard. Claude's final full run reports 4,733 passed, 12 skipped, 9 xfailed, zero failures.
- Source isolation, paid-gate ordering, exact ownership, atomic report replacement, mode taxonomy,
  and total connection-method coverage are sound at this pin.

## G1 — preflight does not verify routes or credentials

The aligned contract says preflight verifies entrypoints and credentials exist before execution.
The implementation calls `entry_status`, which checks only whether strings are populated. A
synthetic automatic entry with command `/definitely/not/a/real/command`, destination
`/definitely/not/a/real/destination`, and marker `/definitely/not/a/real/marker` returns
`EntryStatus(ok=True, missing=())`.

Required repair: verify command executable/script paths and declared importer/scheduler paths;
declare `CFBD_API_KEY` as CFBD's required credential and report its presence/absence without network
or filesystem mutation. Execution must refuse an owned route whose preflight route check fails,
naming the missing component.

## G2 — fresh failed markers are reported as current successes

`_freshness`, `_mtime_iso`, and `_age_days` inspect only filesystem mtime. A freshly written marker
containing `{"status":"failed"}` produces `freshness="current"` and a non-null
`last_success_at` for an externally scheduled source. This is a direct false-success result.

Required repair: parse marker JSON; accept only the entry's declared success statuses (currently
`ok` for the five automatic routes); use semantic timestamps such as `finished_at`, `captured_at`,
or `retrieved_at` when present; and report a failed/running/malformed marker as non-current without
inventing a last-success time. Add a regression test with a fresh failed marker.

## G3 — the controller has no runnable operator entrypoint

There is no CLI or `__main__`, and `execute()` writes no canonical report unless a caller supplies a
`report_root`. The controller therefore cannot yet be invoked reliably by a human or scheduler
without bespoke Python import code.

Required repair: add a thin checked-in CLI with preflight, dry-run, optional owned-source narrowing,
default execution, aggregate exit propagation, and one default canonical report root. Do not expose
paid execution in v1 and do not install a scheduler in this repair.

## G4 — source isolation swallows operator interruption

`execute()` catches `BaseException`, converting `KeyboardInterrupt` and `SystemExit` into an ordinary
source failure and continuing. Isolation should cover source/runtime failures, not make the
controller physically difficult to stop.

Required repair: catch `Exception` at the source-isolation boundary. The cleanup handler in
`write_report`, which re-raises after cleanup, may remain broad.

No provider contact, paid call, subscriber-data access, source execution, scheduler installation,
commit, or push is authorized by this review. QB rushing remains a registered hypothesis under test
with no result.
