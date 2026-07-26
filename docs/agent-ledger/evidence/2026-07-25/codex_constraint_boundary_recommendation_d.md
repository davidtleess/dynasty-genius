# Codex independent recommendation — Candidate D

**Date:** 2026-07-25
**Scope:** Independent reconsideration before Claude consolidates the crew recommendation. No ticket or spec rewrite.

## Recommendation

**D. Candidate B does not survive reconsideration.**

### One sentence David can ratify verbatim

> **An engineering ticket may name a mechanism only when it cites a pre-existing, independently verifiable constraint that makes nonconforming alternatives unacceptable; otherwise it must define the problem, evidence, required outcomes, and bounds while leaving technical design, implementation, and test method to the developer.**

This serves David's standard more directly than A, B, or C. It protects the developer's opportunity to find a better solution, while retaining mechanisms that are genuinely imposed by an existing interface, safety law, interoperability contract, ratified methodology, or operating rule.

## Why B fails

B makes governance text dispositive: if a governance document names a mechanism, a ticket may name it. That has two defects.

1. **It permits mechanism laundering.** An author can move a preference into governance and then cite it back as a “constraint,” without establishing that alternatives are invalid. The rule tests document location, not necessity or preserved solution space.
2. **Its own examples are internally inconsistent.** B treats “fails a contract test” as a constraint because cockpit TDD is mandated by `02` (`docs/governance/02-agent-operating-loop.md:109`), but treats “reproduced by a second lane” as HOW even though the same document mandates an independent technical reviewer (`02-agent-operating-loop.md:260`). B therefore does not actually convert the dispute into a lookup; it still requires an unstated judgment about which governed mechanisms count.

The same sentence can legitimately be classified differently in two repositories, but only because their real constraints differ—not merely because one repository happened to write the preferred mechanism into a governance file. D preserves that legitimate context sensitivity while requiring evidence of necessity.

## The stranger test

Someone who did not write the ticket applies D without asking its author:

1. Mark every named tool, library, algorithm, module boundary, storage layout, test type, staffing step, and implementation sequence.
2. For each, find the cited constraint that predates the ticket or was separately ratified. An assertion in the same ticket is not evidence.
3. Ask whether a materially different mechanism could satisfy the cited constraint and every acceptance criterion. If yes—or if the evidence does not settle it—the named mechanism is HOW and comes out. If no, it is a necessary constraint and may stay.

Ambiguity defaults to developer freedom. A product or architecture authority can still mandate a mechanism, but that is a separate decision and must be visible as such.

## What D classifies differently from B

| Text | B | D | Reason under D |
|---|---|---|---|
| “pin SciPy” | DEPENDS on whether governance happens to govern dependency declaration | **HOW in this repo** | `03-code-hygiene-policy.md` governs Ruff/pre-commit pin parity, not general dependency declaration. The required property can be “a fresh clone resolves the study's registered SciPy version”; direct pin, constraints file, lockfile, or another packaging mechanism remain possible. |
| “fails a contract test” | CONSTRAINT | **SPLIT: process gate, not artifact acceptance criterion** | `02:109` requires RED-first TDD, so “a failing RED exists before GREEN” is a valid process constraint. The particular test class, file, assertions, fixtures, and way the developer proves the fix remain HOW. “Fails a contract test” alone is not a finish line for the product problem. |
| “reproduced by a second lane” | HOW | **GOVERNED PROCESS CONSTRAINT, but not a substitute for ticket AC** | `02:260` requires independent technical review. It belongs in the program Definition of Done or review gate; it does not define the implementation or prove the ticket's outcome. |
| “backup manifest contains the new irreplaceable store in the same change” | CONSTRAINT | **CONSTRAINT** | The pre-existing manifest-coverage law mandates the exact destination and same-change timing (`02:313`); a different destination is nonconforming until David changes that law. |
| “a degenerate input produces a named unavailable state and the promotion gate refuses it” | CONSTRAINT | **CONSTRAINT** | These are observable safety outcomes and consumer semantics. Representation, control flow, and storage remain open. If an exact string were required, that string would need a pre-existing schema/consumer contract. |
| “computed in exactly one module” | HOW | **HOW** | Centralization is the desired property; module granularity is not shown necessary. A package boundary, service, memoized function, or generated artifact could satisfy the problem. |
| “reproducible from a pinned seed” | HOW | **HOW unless a separately ratified stochastic protocol requires that seed** | Bit-identical replay is the outcome. A deterministic closed-form method should not fail merely because it has no seed. |
| “calibration error reported by decile” | HOW | **HOW unless deciles were pre-registered as the acceptance population** | Deciles are one diagnostic. If a pre-registered study made decile behavior part of the estimand or safety contract, they become necessary; otherwise the developer chooses the demonstration. |
| “no ceiling artifact may reach any downstream consumer” | CONSTRAINT | **CONSTRAINT** | It states a consumer-boundary outcome and leaves the implementation open. |

## Which fresh-review reading D predicts

Of the reported **4 / 9 / 26 FAIL** spread, the **9-FAIL reading is closest, but not correct wholesale**.

- The 26-FAIL reading is effectively Candidate A: it over-classifies internal safety and governed process requirements as HOW merely because they are not product-output behavior.
- The 4-FAIL reading is effectively Candidate C: it lets the author call a mechanism “the requirement,” which preserves too much of the author's imagined solution.
- The 9-FAIL reading correctly treats the dependency pin as a design choice and catches real undefined finish lines, but it overreaches when it calls an observable fail-closed state an implementation mechanism.

D predicts a middle result by rule, not by target count: reject `pin SciPy`; retain the fail-closed/unavailable consumer contract; retain pre-existing backup-manifest law; separate RED-first and independent-review process gates from artifact acceptance criteria; remove uncited module/library/algorithm/test-detail prescriptions.

## What changed from my prior B position

I previously valued B because it appeared to turn disagreement into a fact lookup. Reconsideration showed that the lookup does not decide the examples consistently, and that even a consistent lookup would answer the wrong question. David's standard protects the developer's ability to outperform the ticket author's imagined solution. Necessity, supported by a prior independent constraint, is the relevant test; the mere presence of mechanism language in governance is not.

## Incentive disclosure

Claude authored the backlog, so a permissive rule flatters Claude's work and reduces rewrites. Codex's fresh reviewer returned 26 FAILs, so an extremely strict rule would flatter my lane's adversarial posture and make its review look prescient. D rejects both incentives: it is stricter than Claude's intent-based reading and materially less strict than Codex's observable-only review.

## Repository-state correction

The prompt says this proposal is committed in `99826d0`. At the reviewed state, that is false:

- `HEAD` is `99826d0`;
- `git ls-tree -r --name-only 99826d0 -- docs/superpowers/specs/2026-07-25-constraint-vs-how-boundary-proposal.md` returns no path;
- `git status --short` reports the proposal as untracked (`??`);
- the reviewed untracked file's SHA-256 is `2fbcc7bb3850fdcd3b086b93fe332b7ea0179710d28b29539de42e9cbbfe1bd9`.

This does not change the recommendation, but David should not be told that `99826d0` contains the proposal.

## Codex lane position for consolidation

**Recommend D. Dissent from the prior joint recommendation of B.** Claude should carry this dissent explicitly if the consolidated recommendation selects another candidate.
