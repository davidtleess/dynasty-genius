# Phase A framing v19 — Codex round-19 review

Date: 2026-08-10 12:10 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v19.md`  
Submitted and reproduced SHA-256:
`58be646a95469609439ec4c894f84a2a19369fe2f38708eb96d8bd9c914cf67e`  
Measured size: 935 lines / 77,438 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — three findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v19 in full and diffed v18 to v19. All four round-18 repair blocks are present.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Traced option-3 identity through two sequential submissions, same-offering mutation, and both
   retention-mode transitions. The per-database constraints work locally; no rule composes the
   same acquisition across `observations.db` and `receipts.db`.
5. Traced both A paths to the promised last receipt transaction. The fresh path has one commit;
   the reuse path still says it commits in step 4 and again reaches step 6.
6. Tested the listed observation-identity REDs adversarially against alternative broken hash
   formulas. A hash over `offering_id` alone can satisfy every listed cardinality/conflict test.
7. Verified the Branch-A crash heading, conclusion, and parameterization prohibition are now
   options-1/2-only; the attempt-qualified B residue sentence is live.
8. Verified the single-owner descriptor rule and refusal-aware trace cardinalities are coherent.
9. Rechecked the qualified observation copy against the product register and status drawer. It
   remains truthful for distinct offerings; finding 1 covers the newly exposed same-offering
   cross-mode case.

## Findings

### 1. Critical — identical acquisition identities are unique only within each store, not across retention modes

v19 intentionally defines `observation_id` as the same acquisition-signature hash used for
`receipt_id`. But observations and receipts live in separate SQLite databases, and the new unique
constraints apply only inside `observations.db`.

This leaves both transition directions undefined for the **same offering**:

- option 3 → option 1/2: the observation remains, and a receipt with the identical signature hash
  can commit in the other database;
- option 1/2 → option 3: the retained receipt remains, and an observation with the identical
  signature can commit separately.

The read model then sees two records for one acquisition. They share source, offering,
`content_vintage_id`, retrieval instant, archive identity, and role records, but differ in retention,
readiness, and AR effect. Under the equal-instant rule, that can become a
`same_instant_conflict`—or, if treated as two independent candidates, make append/query behavior
matter. In the 1/2→3 direction, the observation copy can also say the latest archive was not
retained even though the identical receipt proves that it was. Per-database uniqueness cannot
enforce a cross-store acquisition invariant.

Required closure: define one cross-mode rule keyed by the shared acquisition-signature identity.
Acceptable designs include a reducer that coalesces identical cross-store identities and gives a
hash-verified receipt the retained/readiness state, or a single transactional acquisition ledger
with mode-specific payload tables. Do not invent a new `offering_id` for the same acquisition.
Define same-offering/different-signature conflict globally as well. RED both transition directions
for identical signature and conflicting signature, including crashes between the two stores,
asserting one effective clock candidate, deterministic AR/copy, and no false conflict. A test that
checks only each database separately must fail.

### 2. High — the reuse branch still commits the receipt before the declared last transaction

Line 534 says the verified-reuse path closes the staging descriptor and “receipt commits.” Line
568 then says either A path commits the offering receipt LAST. Read as the executable order v19 now
requires, reuse performs a premature commit and then reaches a second commit. Idempotency can hide
the duplicate row while still allowing transaction hooks, attempt state, or crash behavior to run
twice; it also falsifies the single last-state-advancing-act contract.

Required closure: delete “receipt commits” from step 4. Reuse should finish object verification and
staging cleanup, then flow to the one shared step-6 transaction. Add a transaction-call trace for
fresh and reuse paths asserting exactly one receipt transaction, after every filesystem invariant
and cleanup. A second idempotent insert must still fail the oracle rather than being treated as
harmless.

### 3. Medium — the observation identity REDs do not prove the frozen signature formula

The contract says `observation_id` hashes the complete frozen acquisition-signature bytes, but its
listed REDs assert only duplicate cardinality, same-offering conflict, and append-order stability.
A broken implementation using `SHA256(offering_id)` passes all of them:

- identical offering → identical id and one row;
- changed signed field under the same offering → `UNIQUE(offering_id)` plus the conflict check
  refuses;
- new offering → new id and a new observation.

It nevertheless fails to bind content, retrieval time, archive identity, and role records, and it
breaks the intended receipt/observation identity equality.

Required closure: promote the existing canonical signature vector to a named observation-ID
known-answer: the positive row must produce
`0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`.
Apply the existing signed-field negative vectors to observation identity too, using new offering
ids where needed so the offering conflict constraint cannot mask a bad formula. On every load,
recompute the id from the persisted signed fields and refuse/quarantine a mismatch; mutate each
signed field and the stored id independently.

## Standing disposition

All four round-18 local repairs are closed: matrix scope is explicit, descriptor ownership has one
close, trace cardinality accepts pre-stream refusals, and the observation store has a concrete local
identity/constraint contract. The blockers arise from composing that new identity across retention
modes and ensuring the RED proves the claimed hash rather than only its local uniqueness effects.
The A reuse branch also retains one premature-commit sibling.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
