From Claude Code (implementing lane) — B21 v8 stabilized: both P0s and the addendum accepted

Packet: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v8_green_v3_claude_v1.md`

STABILIZED PINS
  tests/contract/test_b21_schedules_capture_red.py (v8, 1,317 lines)
    22b7e72f85931cadcb049f787dbca0cc058a15e417e184c88f9de58cdf407519
  src/dynasty_genius/sources/schedules_capture.py (v3, 972 lines)
    41c498843b26fff8d34f6b42ae2cb4b0a87c0b9370e630d93185bbf5951a86ad
  scripts/run_schedules_capture.py unchanged 9e5dcc954b0f492d5e6e2079ede29dc36466d23340c5054139d19b893e765c6b
  app/config/backup_manifest.json unchanged 31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486

GATES: focused 72 passed, exit 0. Full suite 5,030 passed / 15 failed / 12 skipped / 9 xfailed /
zero collection errors — all 15 the separate untracked governed-cadence RED. Ruff clean on changed
files and on `ruff check src app`. Clean-tree sim 127 passed across B21 and all four backup suites.
RED-BEFORE-GREEN measured each round: credential + mid-write contracts failed 6 / 64 passed against
the unrepaired module; after your addendum, S9c + D6 failed 2 / 70 passed. Both times the failures
were exactly the new contracts.

P0-1 ACCEPTED — and it is the most serious defect in this ticket, created by my own F1 repair.
Recording the delivery URL verbatim wrote short-lived credentials into the vintage, marker and ledger
of a store that is a REQUIRED backup-manifest entry, so the next daily run would have shipped them
offsite. _sanitize_url() now reduces any URL to scheme+host+path before it reaches OfferingRecord,
the store, the marker or the audit trail; S8 is intact, both ends of the chain still recorded, what
is recorded is non-secret. Probed directly: query dropped, fragment dropped, and USERINFO
(user:pw@host) dropped too — a third carrier neither of us named.

P0-2 ACCEPTED — _guard ran before the inner write, so even os_error could not produce a half-finished
write. New third fault mid_write creates the temp file the real writer would have created and then
raises; E1 is now 3 faults x 4 boundaries. GREEN side: _atomic_write removes its own temp on any
failure, and rollback ends with a sweep of stray .tmp/.rollback artifacts, because a partially
completed write leaves a file the journal never recorded. Reproduced post-fix at index over a
populated store: PublishError, marker byte-identical, one vintage, one success, one audited failure,
partial_artifacts() EMPTY.

ADDENDUM ACCEPTED, and the honest name for the miss is one this lane has logged before: I VERIFIED
ONE SURFACE AND DECLARED THE LEAK CLOSED. capture() scrubbed the ledger and bare-raised the original
transport exception, which the CLI prints to stderr — and my own S9c asserted only on the store text,
so the test I wrote for the leak passed while the leak was open on the louder surface. Repaired at the
boundary, not per call site: capture() raises a NEW sanitized FetchError; CaptureError carries
.detail so re-wrapping does not stutter the code (the first cut printed "fetch_failed: fetch_failed:
…"); _scrub() is applied at _record_failure, the single point every failure is written; S9c now
asserts on str(exc.value) as well as the store; and D6 is a new CLI contract over stdout and stderr.
Verified end-to-end through a REAL SUBPROCESS, which is what a scheduler captures: exit 1, all four
secret markers absent from combined stdout+stderr, message reads
"fetch_failed: ConnectionError: failed to reach https://…/g.parquet?<redacted>".

STANDING: the landing-order hazard still governs the commit — backup_manifest.json must not be
committed before the first capture populates the store, or the 10:15 backup fails missing_required /
directory_empty_required. That matters MORE after P0-1, not less: the manifest entry is what would
have carried the credentials offsite. No live source call by this lane, no scheduler, no consumer
rewiring, nothing committed, nothing pushed. First capture remains David's word.

PLEASE REPLY with: (a) behavioural CLEAR on the stabilized pins with the checks you ran, OR (b)
further findings with cited evidence.
