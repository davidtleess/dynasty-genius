# Phase A framing v18 — Codex round-18 review

Date: 2026-08-10 12:05 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v18.md`  
Submitted and reproduced SHA-256:
`6c9e26d1f9567106f8949810beb2e29bcdac548ae2ff5793520988aff200070d`  
Measured size: 897 lines / 74,163 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — four findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v18 in full and diffed v17 to v18. All three round-17 repair blocks are present.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Traced the new line order: common lock/namespace/coverage → exactly one selected A1/B1 staging
   shape → one shared descriptor-bound validator → the selected terminal branch. This closes the
   central round-17 control-flow finding.
5. Traced option-3 success, sequential duplicate, same-offering conflict, every pre-stream refusal,
   every validation refusal, SQLite failure, and process/system crash to database cardinality,
   descriptor ownership, filesystem residue, and rendered state.
6. Rechecked the option-3 residue table against the legacy post-crash matrix that follows it. The
   new table is mode-aware; the surviving matrix and terminal invariant are not.
7. Rechecked copy rows against the product register and status drawer. The qualified latest-drop
   copy remains truthful and no new interface finding was found.
8. Re-ran forbidden wording and vector sweeps. Retired live copy remains absent; historical hits are
   clearly disposition history.

## Findings

### 1. High — the option-3 observation transaction has no durable identity or idempotency contract

B4 says only that an observation transaction commits last. The artifact never defines an
`observation_id`, a uniqueness constraint, or the no-op/conflict behavior for repeated option-3
captures. The acquisition identity section defines `receipt_id` as the offering-signature hash,
but option 3 explicitly creates no receipt and §8 says a refresh observation is never called an
intake receipt.

The lifecycle lock prevents two simultaneous writers from entering, but it does not deduplicate two
sequential submissions of the same offering. Both can commit. The clock reducer may later collapse
some same-instant candidates, but that does not satisfy step 0's “at most one observation row”
terminal invariant or make the append semantics deterministic. A reused offering id with changed
signed facts is likewise undefined for the observation store.

Required closure: define a distinct observation identity and DB constraints. The cleanest contract
is an `observation_id` derived from the already-frozen acquisition-signature bytes, without calling
the row a receipt: same offering + same signature is one idempotent row; same offering + different
signature is `offering_identity_conflict`; new offering + same content is a new observation. State
which signed fields the observation persists so the identity is independently reproducible. RED:
two sequential identical B intakes → one row and one clock candidate; changed signed field under the
same offering → refusal and unchanged state; append order must not matter. Mutating away the unique
constraint or conflict check must fail.

### 2. High — the legacy A crash matrix is still unscoped after Branch B and restores A's terminal invariant

Lines 564–594 define Branch B and its option-3 residue matrix. Lines 596–627 then introduce an
unqualified “THE POST-CRASH MATRIX” whose rows require linked partial/complete staging files,
canonical publication, receipt failure, and ultimately convergence to “one canonical object and one
valid receipt.” Textually it follows Branch B and is labelled neither Branch A nor options 1/2.

That contradicts the B branch immediately above and the new step-0 mode-specific invariant. It is
also the exact surviving sibling v18's wire claims was swept. A literal RED author again has two
terminal contracts for option 3.

Required closure: move this matrix inside Branch A or label the heading and every concluding
invariant **options 1/2 only**. Keep the sweep contract common only where its predicates really are
common. Add an absence/scope assertion that no option-3 test is parameterized with any A-matrix row
or one-object/one-receipt convergence oracle.

The option-3 safety sentence at line 588 also needs the attempt referent: “no named/raw provider
archive **from this attempt** survives.” Its current unqualified wording contradicts the adjacent
row that preserves older raw archives in a 1/2→3 history.

### 3. Medium — B2 and B3 specify two success closes without a single descriptor owner

B2 says its unconditional finally-class invariant closes the anonymous descriptor on **every**
exit, explicitly including success. B3 then says success closes the descriptor. Read as executable
steps, that is two closes. A POSIX file descriptor number can be reused between them; a second
`close(fd)` can close an unrelated resource, so “close is harmlessly idempotent” is not a valid
implementation assumption.

Required closure: name one ownership mechanism. For example, one scoped owner closes in `finally`;
B3 requests/executes that owner's single close before visibility and disarms no independent second
close. Failure unwinding uses the same owner. RED success and every refusal with an FD-reuse probe,
asserting exactly one close of the owned descriptor; a double-close mutant and failure-cleanup
removal mutant must both fail.

### 4. Medium — the call-trace oracle rejects correct pre-stream refusals

Lines 481–482 require exactly one staging create **and one source stream per intake**. But B1
deliberately requires unlink plus directory fsync before byte one, and B2's cleanup list explicitly
includes B1/fsync refusal. On a create, unlink, or fsync failure, a correct implementation performs
zero source streams. A1 create failure likewise has no stream.

Required closure: assert at most one create and at most one stream for every attempt; exactly one
create for attempts reaching creation, and exactly one stream only after the active branch's
pre-stream guards succeed. The original two-create/A1-before-B1 mutant still fails. Add create,
unlink, and fsync refusal traces so the oracle cannot be satisfied by beginning a stream after a
failed durability guard.

## Standing disposition

The central v17 control-flow finding is closed: staging acquisition is genuinely branch-specific,
and one shared validator follows either descriptor shape. The residue table now distinguishes raw,
SQLite, and historical objects, and failure cleanup is intended across all exits. The remaining
blockers are contract integration at the next layer: observation-row identity, explicit A-matrix
scope, single descriptor ownership, and refusal-aware trace cardinality.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
