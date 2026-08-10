# Phase A framing v20 — Codex round-20 review

Date: 2026-08-10 12:15 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v20.md`  
Submitted and reproduced SHA-256:
`6ad2af3d22a6db7398ca53727a327e214e1f096a27cd430ae6a11737724c39c5`  
Measured size: 968 lines / 80,166 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — three findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v20 and diffed v19 to v20. The cross-store acquisition rule, reuse-path transaction
   deletion, observation known-answer, signed-field negatives, and observation load-time
   recomputation are present.
2. Recomputed the submitted artifact SHA and measured size above.
3. Rehashed the embedded canonical preimages independently:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Traced the new mandatory counterpart-store lookup in option-3-only, option-1/2-only, and
   transition histories. The contract says the absent database must remain absent, but does not
   define a non-creating lookup or distinguish legitimate absence from unreadable/corrupt state.
5. Traced persisted identity validation before cross-store coalescence. Observation rows now
   recompute their identity on every load; receipt rows do not have the corresponding live rule.
6. Injected conceptually a same-offering/different-signature pair directly into the two persisted
   stores (the state that an independently restored pair of SQLite backups can expose). The
   write-side rule rejects it prospectively, but the read-side reducer only specifies coalescing
   identical identities and does not close the conflicting persisted-state branch.
7. Verified the reuse branch now reaches exactly the one shared step-6 receipt transaction; the
   prior early “receipt commits” instruction is gone from the executable branch.
8. Rechecked the user-visible copy against the product UI register and existing status drawer.
   The identical, independently validated receipt-precedence case is truthful; the findings below
   concern whether a row is eligible to reach that case at all. No new visual finding.

## Findings

### 1. Critical — the mandatory cross-store lookup can create the database that the active retention mode forbids

v20 now requires checking the other store before committing either row type. But §6 also requires
that in an option-3-only history `receipts.db` is **never created**. A normal SQLite connection to
an absent database creates the main file; likewise, the A path can create `observations.db` merely
to discover that it has no rows. That broken implementation satisfies the new logical
same-offering tests while violating retention mode, backup-before-first-write, and the frozen
runtime-state contract. None of the v20 REDs asserts the physical non-creation of the absent
counterpart.

The lookup also needs a closed failure distinction. A legitimately absent optional database may
mean “empty”; an existing but unreadable, malformed, wrong-schema, wrong-journal-mode, or corrupt
counterpart must **not** be treated as empty and permit a commit. The current “other store is
checked” sentence does not define either branch.

Required closure: define a non-creating counterpart lookup. Absence is detected without opening a
write-capable connection and means empty; an existing store is opened/validated read-only for this
check, and any inability to establish its governed schema/state fails closed with both stores,
clock, AR, pill, and copy unchanged. RED both directions:

- option 3 with absent `receipts.db` commits one observation while `receipts.db`, `-wal`, and
  `-shm` remain absent;
- option 1/2 with absent `observations.db` commits one receipt while that database and its
  sidecars remain absent;
- corrupt/unreadable/wrong-schema counterpart refuses rather than being treated as empty.

A mutant using an ordinary create-capable `sqlite3.connect(other_path)` must fail.

### 2. High — receipt rows are not independently identity-verified before they receive cross-store precedence

The repair correctly says observation identity is recomputed from persisted signed fields on every
load. The equivalent rule is absent for receipts. Yet the new reducer coalesces by the shared
acquisition-signature identity and lets a receipt override retention/readiness/AR when its object
hash verifies. Object-byte verification does not prove that the receipt's stored `receipt_id`
matches its persisted offering, retrieval instant, archive metadata, content vintage, and role
records.

A broken or corrupted receipt can therefore retain the observation's stored identity while one
signed field differs, still point at a hash-valid object, and receive receipt precedence. The new
observation known-answer does not catch this because only the observation row is recomputed.

Required closure: before global conflict detection or coalescence, independently reconstruct the
canonical signature from **every receipt and every observation row**, compare it with that row's
stored id, and quarantine/refuse any mismatch. Receipt precedence is eligible only after both
metadata-identity validation and descriptor-bound object verification pass. Apply the same
known-answer and per-signed-field/stored-id mutants to receipt loads; include a cross-store fixture
where the observation is valid and the receipt has a valid object but a mismatched recomputed id.
It must not coalesce or advance AR.

### 3. High — the global offering conflict is enforced on writes but not on restored or already-persisted state

The “any differing signed field under the same offering is `offering_identity_conflict` globally”
rule lives in the **write-side** bullet. The read-side bullet defines only the identical-signature
case. Two logical databases are backed up independently, so restore skew can expose a receipt and
observation with the same `offering_id` but different valid signatures even if every live writer
obeyed the lifecycle lock. Direct corruption or a prior defective writer produces the same input.

On that state, v20 does not say whether the reducer refuses, emits two acquisitions, chooses the
newer instant, or turns it into `same_instant_conflict`. Only the first is consistent with the
global offering identity contract; clock ranking must never launder an offering identity conflict
into a normal acquisition or a timing tie.

Required closure: after per-row recomputation and before clock candidacy, group the union of both
stores by `(source, offering_id)`. One signature may coalesce; more than one distinct valid
signature is a named global `offering_identity_conflict`, makes the Footballguys stream
`unverifiable`, holds AR and the last unambiguous clock, and never enters equal-instant selection.
RED an already-persisted conflicting pair in both query orders and a skewed independent-backup
restore. A test that proves only prospective write refusal must fail.

## Standing disposition

All three round-19 repairs are materially present: identical valid cross-store identities now have
one acquisition semantics, reuse has one last receipt transaction, and observation identity has a
real known-answer plus load-time recomputation. The remaining blockers sit at the newly introduced
composition boundary: opening an optional counterpart without mutating retention state, validating
both row types before precedence, and rejecting a persisted global conflict rather than assuming
the writer made it impossible.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
