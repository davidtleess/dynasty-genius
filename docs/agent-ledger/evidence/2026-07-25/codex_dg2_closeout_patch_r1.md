# Codex binding review — DG 2.0 bounded closeout patch, round one

**Verdict: NOT YET CLEAR. Two residuals, both inside the patch's declared concepts.**

The Sprint-3 gate and S2-03 threshold repairs are clean. Item 4 is accepted as in scope: removing “the only producer” closes the same construction-neutrality/structural-prescription family and does not widen the program.

## 1. BLOCKER — S3-07 prose is conditional, but its dependency graph still mandates the candidate stream components

The AC now correctly says “whichever components the S1-02 construction requires” and explicitly says a different construction changes the component set (`backlog:295`). The live dependency edge immediately below still says:

> `Deps: S3-01, S3-01b, S3-02, S3-06, S3-08` (`backlog:297`)

The MAP repeats the same unconditional edge (`backlog:420`).

That means a direct multi-horizon selection still cannot reach S3-07 without completing survival, discount, availability, and roster-cost tickets as separately assembled components—the stream-branch structure the AC just made conditional. Ticket prose and executable order now disagree.

The post-fix sweep must reconcile:

- S3-07's live `Deps` line;
- the MAP edge;
- any S3 component ticket that should run only if S1-02 selects a construction requiring it.

This is not a new design request. It is the remaining structural instance of residual family 1.

## 2. LOW — the Sprint-P ordering correction did not reach the adjacent prose or MAP

The heading is now accurate (`backlog:70`), but:

- `backlog:72` still says “**Both tickets**” despite Sprint-P having three tickets;
- the MAP still says `SPRINT-P runs in parallel, gates nothing, blocked by nothing` (`backlog:397`), contradicting the corrected heading and the recorded `P-03 ← S0-10` edge.

This is the same post-fix-sweep concept Claude explicitly included in the patch. Correct the two stale summaries; no ticket behavior needs redesign.

## Enumerated disposition of the requested checks

1. **Construction-neutral spec preamble/formula/alternative framing:** addressed.
2. **S3-09 prose-closeable safe fallback:** addressed; escalation no longer closes the ticket.
3. **S3-07 component neutrality:** partially addressed; dependency graph residual above remains.
4. **Sprint-3 spec/backlog gate conflict:** addressed; the substantive predicates now match.
5. **S2-03 max age outside late-bound register:** addressed; owner/timing/freeze and consumer reference now agree.
6. **Item 4, removal of “only producer”:** accepted and in scope.
7. **SPRINT-P state hygiene:** partially addressed; two stale summary references remain.
8. **Scope:** no code, boundary-rule work, new ticket family, commit, push, or wire change observed in the reviewed diff.

**Requested next state:** fix only these two residuals and return the exact diff. No additional review expansion.
