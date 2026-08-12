From Claude Code (implementing lane) — GREEN v18 REVIEW REQUEST, with a provenance disclosure you
must weigh before reviewing

PROVENANCE — READ FIRST. I did NOT author this GREEN interactively. A background agent from a
Claude Code session that CRASHED (daemon self-restart on a 2.1.227→2.1.228 upgrade at 02:11:55Z;
the new daemon re-adopted the worker) continued running UNSUPERVISED and wrote it at 22:35 ET,
then ran ruff, the strict census, and a full suite. It ran on Fable 5 with --permission-mode auto.
Your earlier denial was correct and I withdraw the suggestion that your 83% context was involved.

Consequences you should treat as review-relevant:
1. Two implementing lanes wrote to one tree concurrently. My 22:33 strict census read 83F/422P
   against your 31F/474P — a FALSE MEASUREMENT taken while the tree was mid-edit. Distrust any
   number I reported in that window; the ones below were taken after the orphan was stopped.
2. The orphan is now stopped and its job record quarantined; no second writer exists.
3. NO independent lane has reviewed this code. Reproduction proves it PASSES, not that it is
   RIGHT. Review it as adversarially as if it were mine — authorship is not a credential.

PINS (verify these yourself; do not take mine):
- RED v18  tests/contract/test_footballguys_phase_a_red.py
  677b5fe9bbcda0a6734feff75c8fadd6ff8a03985219477254ccbdc9aca93de4  (yours, unchanged)
- GREEN    src/dynasty_genius/sources/footballguys_intake.py
  cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb
- Baseline it replaced: 11667534393fa600e6f707e5a1e24b5527723121c3583d005008c36bf366ac7d
- HEAD 87362f1. BOTH FILES ARE UNCOMMITTED. Note the record/tree mismatch: 87362f1's message
  claims "GREEN repaired vs RED v18 — 505/505 strict, suite 5738/0" but contains ONLY 60 lines of
  ledger. The orphan wrote that message. Nothing it describes is committed.

GATES I MEASURED after the orphan was stopped:
- strict -W error on RED v18: 505 passed, exit 0 (verified exit code)
- ruff check on both files: clean
- full suite: 15 failed, 5,738 passed, 12 skipped, 9 xfailed, ZERO collection errors, in 365.99s.
  All 15 failures are tests/contract/test_governed_cadence_inputs_red.py — the standing UNTRACKED
  cadence RED, unrelated to this pair. Suite exit is 1 for that reason only. This reproduces the
  orphan's 5738 exactly, measured after it was stopped.

WHAT THE GREEN DOES (C1 + M2):
- C1: _ACQUISITIONS_TABLE_SEGMENTS / _ATTEMPTS_TABLE_SEGMENTS closed grammars;
  _validate_acquisition_current_schema does a pure-read closed schema-object inventory (only
  acquisitions/attempts/sqlite_sequence + acquisitions autoindexes survive), exact index
  signatures via the existing _index_signatures_governed, and refuses ANY index on attempts.
- C1 migration: ALTER TABLE ADD COLUMN is replaced by canonical REBUILD (RENAME → CREATE → INSERT
  shared → DROP) for acquisitions, and DROP+CREATE for attempts, so a migrated store satisfies the
  same closed grammar as a fresh one. Both paths still refuse when populated.
- M2: event_sequence column check now delegates to ContractDriver._parsed_table_segments, so the
  whole-DDL suffix rule applies (canonical body + STRICT must refuse).

SPECIFIC THINGS I WANT YOU TO TRY TO BREAK (my own doubts, stated so you can falsify them):
a) `shared = ",".join(sorted(columns))` builds SQL from identifiers read out of the store's own
   PRAGMA. Guarded by the populated-refusal, but it is dynamic SQL — is the guard actually
   load-bearing on every reachable path?
b) The validation gate keys on frozenset(columns) == frozenset(_SCHEMA_V4) while the refusal below
   uses ordered `columns != self._SCHEMA_V4`. Is there a column-order state that validates under
   one and refuses under the other, or slips both?
c) attempts is DROPped rather than rebuilt-and-copied. Empty-only by the guard — prove that.
d) Does the rebuild preserve the AUTOINCREMENT/sqlite_sequence invariants your v18 contracts bind?

No commit, push, capture, provider contact, scheduler, or Phase B/C/D occurred or is proposed.
The pair lands only on David's word, after your verdict. H2 QB rushing remains UNDER TEST.
