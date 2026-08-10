# Phase A framing v13 — Codex round-13 review

Date: 2026-08-10 11:38 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v13.md`  
Submitted and reproduced SHA-256:
`d3f5686a2e6e0641f9ed85cb24e63a2b8d32d23e93f628b12af4132192bfd4e1`  
Measured size: 698 lines / 57,603 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — four findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v13 in full and diffed v12 to v13. All five round-12 disposition blocks are present in the
   live sections.
2. Recomputed the artifact SHA and size above.
3. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Searched the final artifact for the claims v13 says it retired or narrowed. Both superseded
   claims still occur as live instructions in §6, not only as historical narrative.
5. Evaluated the proposed fork control against a broken implementation and the underlying
   descriptor lifecycle. The control demonstrates the operating-system hazard but does not invoke
   or falsify the production no-fork rule.
6. Rechecked the unchanged surface contract against the product register and `DailyTape.tsx`:
   drawer-only detail, neutral freshness pill, no global-health inheritance, and “refresh recorded”
   copy remain aligned. No new interface finding.

## Findings

### 1. High — v13 still promises guaranteed post-fact detection in the live reuse contract

The header and §6 step 0 say v12's “detected after the fact” guarantee was weakened to behavior
outside all guarantees and only *potentially* detectable. But lines 360–364 still instruct:

> a non-cooperating process mutating the private namespace is OUTSIDE the contract — detected after
> the fact by verification failures

That is the exact guarantee the disposition says was removed. It is live inside the reuse-branch
contract, so an implementation or RED can follow either rule. The stable lock-path replacement
probe already demonstrates out-of-model mutation that causes no verification failure, and the
verify/unlink counterexample has no guaranteed post-fact detector.

Required closure: replace the live reuse text with the single standing boundary: out-of-model
namespace mutation is outside every guarantee and may only be detected later. Add a forbidden-
phrase sweep over the operational sections so this repair cannot pass merely because the new
sentence is also present elsewhere.

### 2. High — the superseded “process death releases the lock” rule also survives beside its correction

Lines 293–296 still say “Kernel lock release on process death is the staleness rule.” Lines
310–316 later say the opposite, correctly: release occurs only after the last inherited reference
closes, and process death is sufficient only when no descendant inherited the descriptor. Both are
live within the same step-0 contract.

A broken implementation can therefore cite the first sentence, assume parent death clears
staleness, and omit the descendant-inheritance policy while remaining text-conforming.

Required closure: delete the unconditional process-death sentence and retain only the last-reference
rule. Test the final artifact for the obsolete unconditional formulation, not just for presence of
the replacement text.

### 3. High — the proposed fork RED proves the hazard but cannot fail an implementation that violates the no-fork rule

V13 freezes “the intake process MUST NOT fork while holding the lifecycle lock,” then defines RED
as a standalone parent/fork/child probe showing that the child keeps the lock alive. That probe
passes identically whether production intake obeys the rule, calls `fork()` itself, leaks a
duplicated descriptor, or allows the descriptor to survive an `exec()`. It validates an OS fact,
not the implementation boundary. This is the previously named species of seed that passes broken
code.

The contract also names only fork. It does not require close-on-exec or forbid duplicating/passing
the descriptor, even though any extra reference can strand the lock under the correctly stated
last-reference rule.

Required closure: define an enforceable descriptor-ownership boundary and a mutation-backed test.
At minimum, open/set the lock descriptor close-on-exec, forbid duplication or descriptor passing,
and choose how child inheritance is prevented (for example, a registered child-side close hook if
fork-capable code is in scope, or a production-path assertion/architecture proving no fork-capable
call occurs while locked). The RED must mutate/remove that actual guard and fail; retain the current
fork probe only as an explanatory OS-semantics control.

### 4. Medium — “fixed path” is not a self-contained namespace bootstrap contract

Lines 317–323 add strong load checks once a root descriptor exists, but the supposedly fixed path
is never named and the missing-root path is unspecified. The contract does not state whether the
intake creates the directory or requires provisioning, what trusted parent anchors it, or how
creation avoids following a symlinked ancestor. `O_DIRECTORY|O_NOFOLLOW` protects the final
component only; it does not by itself fix the identity of a multi-component parent chain.

This matters to both the threat boundary and the retention/manifest law: a RED author cannot assert
the exact protected namespace or its backup coverage while the address and creation lifecycle are
left to implementation choice.

Required closure: pin the repository/config-relative namespace identity and trusted parent, then
freeze missing-root behavior. If intake creates it, specify descriptor-relative no-follow creation,
mode, fsync, and post-create verification; if it must already exist, missing means fail closed and
the provisioning owner is named. Add missing-root and symlinked-ancestor controls alongside the
final-component symlink/mode/owner cases.

## Standing disposition

The five round-12 repairs are directionally correct, and the observation and sweep repairs are
internally closed. V13 fails on two old sentences that survived beside their replacements, one
non-falsifying no-fork seed, and one incomplete security-boundary bootstrap. Plan v4 remains CLEAR.
No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word; Phase B waits; Phases
C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and
is unrelated.
