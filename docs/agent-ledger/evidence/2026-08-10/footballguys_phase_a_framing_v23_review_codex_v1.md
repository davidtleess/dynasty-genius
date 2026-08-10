# Phase A framing v23 — Codex round-23 review

Date: 2026-08-10 12:32 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v23.md`  
Submitted and reproduced SHA-256:
`5ada58a6b36b5d8a6ede569ad9cb187b779ecfe16440f6a241f79b67047aafa5`  
Measured size: 1,098 lines / 92,101 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — one Critical finding.** No RED, build, intake, store, scheduler, provider
contact, comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Diffed v22 to v23 and verified the v23 title, round-22 disposition header, final reply request,
   byte-level WAL oracle, split rows 19a-c, and removal of the live acquisition repair escape.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages independently:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Reconciled the WAL oracle with the measured runtime: main and WAL `(size, SHA-256)` are now
   required byte-equal before/during/after; only SHM may appear/change; the former bookkeeping
   allowance is absent from live instructions. The three same-name mutations are load-bearing.
5. Evaluated rows 19a-c and their overlays. Their predicates, AR cells, pill values, and literal
   full copies are disjoint and complete; the optional-clause assembly is gone.
6. Traced each stated integrity-failure cause across consecutive loads: receipt metadata mismatch,
   object hash mismatch, direct source-row deletion/edit, and exact-byte object restoration.
7. Inventoried the durable stores and schemas named in the self-contained contract. No integrity
   incident/latch/tombstone store or append rule exists; integrity is recomputed from the current
   receipt/observation rows and current canonical object bytes.
8. Cross-read the required backup/restore path. A correct restore can replace an invalid object or
   database with governed valid bytes, after which the derived invalid predicate disappears without
   any future repair contract.
9. Rechecked the exact copy and status-drawer placement. The 19a-c copy is truthful while an
   integrity state exists; the finding is whether the implementation can remember that state under
   the v23 lifetime promise.

## Finding

### 1. Critical — “no clearing mechanism” requires a durable latch that v23 does not define

v23 says an integrity failure is load-bearing until a future separately framed repair and adopts
REDs in which direct row deletion/edit or replay must **not** clear it. But the integrity state is
currently only a derived result of validating rows and object bytes on each load. No durable
incident record, latch, tombstone, hash chain, or external row commitment exists in the named store
model.

That makes the promise unimplementable as written:

- delete the identity-invalid row and the next reducer invocation has no row from which to derive
  the failure;
- edit the signed fields and stored id together and no independent incident remains to show the
  earlier mismatch;
- restore a corrupt canonical object to its exact receipt-bound bytes and object verification now
  passes;
- restore a pre-corruption SQLite backup and the offending persisted state may disappear.

Each path clears the derived predicate without an acquisition repair API. The first is explicitly a
required mutant; the restore paths are also normal consequences of the backup contract. “Source
rows remain immutable” cannot by itself detect that a row is gone, and file mode/SQLite constraints
cannot make arbitrary restore or same-user database replacement observable after the fact.

Required closure: choose one coherent lifetime model.

1. **Durable no-clearing latch.** Before an integrity failure is exposed as rows 19a-c, append a
   durable incident record with its own identity, affected source/row/object identities, observed
   and expected hashes, reason, and first-observed provenance. It is immutable and has no cleared
   state in v1. Define transaction/crash ordering, idempotency, read failure behavior, runtime path,
   `.gitignore`, retention, and manifest/exception coverage before first write. The reducer reads
   all incidents even if the source row/object later disappears or becomes valid. RED crash before
   and after incident commit, deletion/edit/restore, duplicate detection, and incident-store
   unreadability.

2. **Derived-state-only contract.** Narrow the promise honestly: there is no application override,
   but integrity status lasts only while current governed evidence fails validation; a verified
   backup restoration may clear it. Then retire the direct-delete “state remains” mutant or define
   an enforceable row-immutability boundary and classify out-of-band deletion/restore explicitly.

Do not call the latch a repair mechanism: it records that failure occurred and is what makes “no
clearing in v1” true. Conversely, do not retain permanent/no-delete language if the intended state
is purely derived and self-healing.

## Standing disposition

The byte-level WAL oracle and rows 19a-c are clear. The acquisition repair escape is removed from
the API contract, but the replacement lifetime promise needs storage semantics: either persist an
unclearable incident or define integrity as a current-evidence predicate that can recover when the
evidence is restored.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
