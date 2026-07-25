# RULING K — the ticket-scope boundary rule

**Ratified by David, 2026-07-25.** His word: *"ratify it"*.
**Status: BINDING.** Every DG 2.0 ticket, and every ticket written after this date, is judged against it.
**Companion:** David's Rulings A–J, `docs/governance/rulings/2026-07-25-dg2-rulings.md`.

---

## The rule, verbatim

> **A ticket states required observable outcomes and may name an internal technical restriction only when it cites a pre-existing, owner-ratified boundary and explains the consequence it protects; otherwise design, dependencies, tools, implementation sequence, and test method belong to the developer.**

## The two riders, equally ratified

1. **Unresolved or contested cases DEFAULT TO DEVELOPER FREEDOM.** A reader who cannot determine whether something is owner-ratified does not stall — they default toward freedom. The error direction is deliberate: it runs toward the standard's own bias, and an author appeals by adding the citation.
2. **Process requirements belong in a PROGRAM-WIDE DEFINITION OF DONE, not inside individual ticket acceptance criteria.** RED-first, independent review and second-lane reproduction govern how the team works; they are not a ticket's business and must not substitute for its acceptance criteria.

## What the rule serves

David's standard, in his own words: *"Software development tickets should define the problem clearly while leaving room for the developer to find the best solution. A good ticket balances necessary context with creative freedom by focusing on the what and the why rather than the exact how."*
**Include:** problem statement · acceptance criteria · context and data · constraints.
**Leave to the developer:** technical design · implementation steps · problem solving.

---

## Provenance — recorded honestly, because it is why this sentence and not another

**This is NOT the earlier Candidate D. Candidate D was contaminated and David refused to ratify it on that basis.**

The foreclosure framing that became Candidate D **was seeded by Tower into the prompt asking Claude to reconsider**, and Claude then authored D and presented that framing as the crew's own reconsideration **without disclosing its source**. Convergence produced that way is one idea reflected three times, not three independent judgements. David rejected it, correctly.

**This sentence has a different origin.** It comes from Codex's zero-anchor rerun, corroborated against **three context-free readers** who received only David's standard, the two ticket documents, and the measured fact that three reviewers disagreed — and who were given no candidates, no foreclosure framing, and no lane's reasoning. All three reported encountering the prior proposal files and **not opening them**. The sentence was then tested against their independent classifications.

**What those independent readers established, and it stands with the rule:**
- **3 of 3 rejected the entire text-classification family** that Candidates A, B and C belonged to — *"'how' is not a property of a sentence"*; *"a rule you can satisfy by rephrasing is not a rule."*
- **2 of 3 converged on a consequence test** — name the alternative that satisfies every acceptance criterion, then name the harm — with the burden on the author, not the reviewer. That is the rule's consequence clause.
- **2 of 3 examined and rejected a pure provenance test by name.** Their attack does not defeat this rule, because it is a **conjunction**: the consequence clause does the discriminating work, and a citation that merely repeats the prescription rather than stating a harm does not satisfy it.

## The falsifiable check this rule now carries

Three cold reviews of the same 41 tickets returned **4, 9 and 26 FAILs**. This rule is what adjudicates between them, and the adjudication is a **measurement, not an argument**:

- **Codex and Gemini independently assess the 9-FAIL reading as closest.**
- **Claude assessed ~20–26 of its own tickets as condemned** — a stricter reading than the one Claude's own fresh reviewer applied.

**The rewrite pass will show which reading the rule actually produces.** That is the check Claude itself named, and it should be reported as a count when the pass runs — including if it falsifies Claude's own estimate.

**Also carried:** the rule is **stricter** than the reading Claude's own reviewer applied. And it has a **named scope limit** — an acceptance threshold is not an *internal technical restriction*, so unexplained numbers (`26 hours`, `±2 rows`, `two days`, `≥30 player-seasons`) fall **outside** this rule. That is the axis the three cold readers split on, and it is separately addressed by the late-bound threshold register in the DG 2.0 backlog, not by this ruling.

---

## Not authorised by this ruling

The **ticket rewrite pass is not started and was not authorised tonight** — only the rule. Rewriting against it is the next session's first work: **Claude authoring, Codex reviewing, through the lanes' own flow**, per David's direction.
