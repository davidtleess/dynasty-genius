# Phase A framing v24 — Codex round-24 review

Date: 2026-08-10 12:37 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v24.md`  
Submitted and reproduced SHA-256:
`b8cd59d7ff0825b807a621fa8ce9392fe0e39ec1adbbe5c5a025a198dd94abc4`  
Measured size: 1,123 lines / 93,917 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — one High finding.** The derived-state-only response to R23-1 is coherent.
No RED, build, intake, store, scheduler, provider contact, comparison, or surface opens. David's
retention choice remains a separate hard gate.

## Checks run

1. Diffed v23 to v24 and verified that the live delta is confined to the title/disposition,
   derived-state-only integrity block, and final reply request.
2. Recomputed the artifact SHA and size above; verified the v24 title and round-23 disposition.
3. Rehashed the embedded canonical preimages independently:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Traced each v24 integrity transition: failing receipt/object → rows 19a-c; exact receipt-bound
   restore → valid evidence; wrong/unverified replacement → integrity failure; application flags
   and semantic adjudication → no acquisition-state override.
5. Reconciled the direct-delete mutant's retirement with the declared rounds-11/12 threat model.
   The derived-only choice no longer claims memory that no governed store possesses.
6. Re-read the frozen acquisition identity formula, positive/negative vectors, observation
   identity, cross-store conflict rule, readiness calculation, and every occurrence of “outcome.”
7. Rechecked rows 19a-c and the exact status-drawer copy. They remain truthful while current
   governed evidence fails validation.

## Finding

### 1. High — the “changed outcome replay” RED requires a conflict the frozen identity cannot express

The in-model RED list says “a replayed row with a changed outcome refuses
(`offering_identity_conflict`).” But the frozen `offering_signature` covers acquisition fields
only: source, offering id, content-vintage id, validated retrieval instant, archive hash/bytes,
and ordered role records. It deliberately excludes semantic fields, and it does not contain a
readiness, retention, analysis-ready, validation-outcome, or reducer-outcome field.

Consequently, a replay that changes only an “outcome” while preserving every signed field has the
same canonical preimage and identity. Under the standing rules it is an idempotent same-signature
row, not an `offering_identity_conflict`. Conversely, a replay that changes any signed field does
conflict, but that tests the already-frozen signed-field rule—not a changed outcome. The artifact
uses “outcome” elsewhere only generically for crash results; it never defines a persisted field
that closes this oracle.

This is the exact passes-broken-code species the framing has been excluding: a future test can
mutate an arbitrary signed field, observe a conflict, and claim the “changed outcome” control is
green while an implementation that changes readiness/analysis state under the same acquisition
identity remains untested.

Required closure: choose one of these precise contracts.

1. **Delete/narrow the RED.** Replace “changed outcome replay” with a named signed-field mutation
   and its canonical before/after bytes (or point to the existing per-signed-field negative
   vectors and global offering-conflict controls). State that derived readiness/outcome is not part
   of acquisition identity.
2. **If outcome persistence is intended, frame it separately.** Name the exact immutable field or
   versioned evaluation record, its identity and provenance, allowed transitions, conflict/reducer
   behavior, and a fixture that changes only that field. Do not silently widen the acquisition
   signature, whose acquisition-only boundary is load-bearing for freshness and later semantic
   evidence.

In either case, the RED must name the exact mutated field, the unchanged fields, and the expected
identity/reducer result. “Outcome” cannot remain an undefined proxy.

## Standing disposition

The R23-1 remedy is accepted on substance: integrity is a current-evidence predicate, no
application override exists, a verified exact-byte restore may legitimately heal it, and
out-of-band same-uid mutation is outside every guarantee. Only the contradictory replay oracle
prevents CLEAR.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
