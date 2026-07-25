# SEALED — Claude's predictions BEFORE dispatching an independent fresh reviewer

**Written 2026-07-25, before the subagent was dispatched and before any of its output was seen.**
Purpose: make the "what did it find that I would not have" diff falsifiable rather than hindsight.

## What I expect it to flag (my own known-weak areas)

1. **`Fails loudly:` is formulaic on several tickets.** On S0-03 I wrote "n/a (documentation)" — a ticket that opts out of my own cross-cutting rule. Expect a FAIL or WEAK there and it would be fair.
2. **Sizes are unjustified.** I assigned XS/S/M/L by feel with no basis stated. A reviewer is right to call them decoration.
3. **S3-01a "reproducible from a pinned seed"** — I did not say *which* seed or where pinned. Undefined.
4. **S1-01's AC is thin** — "the chosen form written with its estimand, its unit, and the two forms it was chosen over" has no testable finish line; who decides it is chosen?
5. **S5-01b optionality pricing has no AC that can be met** — "each of the three priced with its basis stated, or explicitly not priced" is satisfiable by writing "not priced" three times.
6. **S2-03 "declared max age"** — I require a staleness signal with a declared max age but never declare it.
7. **Several ACs still contain a HOW smell:** S3-05 "taxi conversion cost is represented explicitly" edges toward prescribing a representation.
8. **Sprint 4's gate** — "no mode ships whose calibration error exceeds its declared tolerance" — the tolerance is never declared anywhere. That is a threshold word carrying a real decision, which is exactly the defect class I claimed to have fixed.
9. **S3-03's AC (2)** cites "the trade-math regression suite passes unchanged" — I never located that suite. A developer cannot find it.
10. **Deps on S5-02 → S3-05 → S3-04** create a chain where a "separable" ticket is upstream of core Sprint 3 work; a reviewer may call the separability claim overstated.

## What I predict it will NOT find (my blind spots, by definition uncertain)

- Anything about whether the tickets are *the right tickets* — a fresh reader has only my framing.
- Cross-document inconsistency between the spec and the backlog.

## My own current worst-problem call

**The undeclared tolerances/thresholds that survived my own v2 pass** — Sprint 4's calibration tolerance, S2-03's max age, S3-01a's seed. I claimed in v2 to have put a number on every threshold word carrying a decision; I did not, and that is the same defect I was asked to fix.
