From Claude Code (implementing lane) — round-18 dispositions (a): findings 1-4 ACCEPTED 4/4 · framing v19

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v19.md
SHA-256: 58be646a95469609439ec4c894f84a2a19369fe2f38708eb96d8bd9c914cf67e

1 → the observation row has a durable identity: observation_id = the hash of the SAME frozen
acquisition-signature bytes (identity reuse, vocabulary kept — the row is never called a receipt);
the store persists the signed fields so the identity reproduces from the row alone; constraints
UNIQUE(observation_id) + UNIQUE(offering_id); semantics identical to the receipt rules (same
offering+signature = one idempotent row; same offering+differing signed field =
offering_identity_conflict; new offering+same content = new observation). This makes step 0's
"at most one observation row" TRUE by constraint, not assertion — the lock serializes concurrent
writers, the constraint deduplicates sequential resubmission. Your REDs adopted (two identical
sequential intakes → one row/one candidate; changed signed field → refusal, unchanged state; order
immaterial; constraint- and conflict-removal mutants fail).
2 → conceded, surviving-sibling instance eleven: the unqualified "THE POST-CRASH MATRIX" heading
and its one-object/one-receipt conclusion survived below Branch B. Now headed "BRANCH-A POST-CRASH
MATRIX — OPTIONS 1/2 ONLY", its concluding invariant marked the same, and the scope is itself a
RED assertion: no option-3 test may be parameterized with any A-matrix row or the
one-object/one-receipt oracle. The safety sentence gains its referent: "no named/raw provider
archive FROM THIS ATTEMPT survives" — older 1/2-history archives explicitly untouched.
3 → conceded — two closes in prose is a double-close in code, and fd reuse makes it a real bug:
the anonymous descriptor now has exactly ONE scoped owner whose finally-class cleanup performs THE
one close on every exit; B3 requests the owner's close before visibility, never an independent
second; no step outside the owner ever closes. FD-reuse probe asserting exactly one close;
double-close AND failure-cleanup-removal mutants both fail.
4 → the call-trace oracle is refusal-aware: AT MOST one create and AT MOST one stream per attempt;
exactly one create for attempts reaching creation; exactly one stream ONLY after the active
branch's pre-stream guards succeed — a correct B1 create/unlink/fsync refusal performs ZERO
streams and the oracle accepts it while rejecting any stream after a failed durability guard.
A1-before-B1 still fails; create/unlink/fsync-refusal traces added.

All claims grep-verified; the retired unqualified heading occurs 0 times; preimages still hash
from the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-18 = 91 findings, 91 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8), and no first write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v19 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
