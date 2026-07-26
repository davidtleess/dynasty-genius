# From Codex (independent reviewing lane) — answer to David's ship question

## Answer

**YES, we are overthinking the boundary rule. Stop working that question.**

**YES, start the unaffected work: DG2-P-01 and Sprint 0 can begin under the solid rule already stated.**

**NO, do not declare the entire v3 backlog execution-ready yet.** This is reply **(b)**: one of the six uncontaminated defects is still structurally live, and the two Sprint-3 gates still disagree. Those are not boundary-philosophy disagreements.

## Claude's proposed one-word repair is not needed

The two examples do not establish an authority-versus-evidence gap:

1. **DGX-02 restore strength already has owner-ratified authority.** `docs/governance/02-agent-operating-loop.md:316` says the restore drill is part of the backup's definition and weakening it is a contract change requiring David's ratification. The ticket should cite that authority eventually; the constraint is not unsupported.
2. **S2-01b's “never zero-fill missing rows” is an observable data-integrity outcome.** The rule allows observable outcomes without requiring an owner ruling. Authority is required only when a ticket names an internal technical restriction.

Adding “OR A MEASURED PROPERTY OF THE EXISTING SYSTEM” would be too broad: a measured property can justify changing an outcome, but it does not by itself justify mandating a particular mechanism. I found no systemic authority/evidence class from these two cases.

## The specific residual that blocks full shipment

### 1. Construction neutrality is still not fixed

The spec says the question is open while deciding it structurally:

- spec `:88`: “The epic builds a **per-season value stream**”
- spec `:95`: fixes the summation formula
- spec `:118`: declares the direct multi-horizon construction “worse as the engine” and recommends it only as the stream's validator
- backlog `:294`: S3-07 hard-codes assembly from the stream-branch components
- backlog `:305`: S3-09 allows the alternative ticket to close when a record merely explains why it cannot be built

That last clause is also the safe-fallback defect in a new location: the alternative can still disappear by prose. This is the same mandatory defect all three reviews agreed had to be repaired, not a new perfection demand.

**Cost of shipping without it:** S1-02 is nominally open, but the epic, dependency graph, component ownership, and alternative's escape hatch all favor one answer before David rules. A developer can follow the tickets faithfully and reproduce the authoring bias.

### 2. The Sprint-3 gate conflict remains

- spec `:184` requires benchmarking against three classes and naming wins/losses.
- backlog `:242` requires the build to **win or tie against all three**.
- backlog `:243` says the spec now points to the backlog, but it does not.

**Cost of shipping without it:** the same result can pass the spec and fail the backlog. That is an execution gate, not wording polish.

### 3. One late-bound threshold is outside the register

Backlog `:35` says any late-bound threshold absent from the register is a defect. S2-03 `:222` lets “max age” be declared inside that ticket before first import, but the register supplies no owner, freeze timestamp, or amendment rule for it.

**Cost of shipping without it:** the staleness standard is chosen by the work it judges, exactly the class the register was created to prevent.

## Recommendation and scope

Do one bounded document repair for those three families, one Codex verification pass, and stop reviewing. Do **not** reopen the general boundary debate.

Work need not wait:

- **Start now:** DG2-P-01 and all Sprint-0 research/measurement tickets.
- **After S0-10:** DG2-P-03 may start; P-02 follows P-03. The backlog's “SPRINT-P … blocked by nothing” heading is factually too broad because P-03 explicitly depends on S0-10, but there is no cycle.
- **Do not start S1 as the final thesis track** until the construction-neutrality and gate text are coherent.

This is not a request for another broad review. It is a small, enumerated closeout patch. Shipping the unaffected work now captures the operational value; calling the whole backlog ready before these objective contradictions close would trade one day of review fatigue for months of biased execution.

## Incentive check

My lane benefits from finding residuals because it validates the harsh review. That is why I am not asking for another full pass, a new rule, or a redesign. I am naming three text-local contradictions with exact locators and explicitly clearing P-01/Sprint 0 to proceed.
