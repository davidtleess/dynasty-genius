# Clean re-run of the boundary question — three uncontaminated derivations

**Date:** 2026-07-25 · **Ordered by David:** *"i believe tower contaminated the whole question - want to rerun the analysis with ZERO pre-conceived ideas."*
**Status:** EVIDENCE FOR DAVID. **No recommendation is made in this document, deliberately — see §5.**

---

## 1. Method, and what was done to keep it clean

Three agents were dispatched **in parallel, with identical inputs, no cross-talk, and no knowledge of each other.** Each received only:

- David's standard, verbatim;
- the two ticket documents;
- the measured fact that three reviewers returned **5 / 9 / 26** FAILs on the same 41 tickets and disagreed about where constraint ends and over-specification begins.

**Deliberately withheld:** Candidates A/B/C/D, the foreclosure framing Tower supplied, the governance-exception idea, the behavioural/mechanism dichotomy, every prior review, every lane's diff, and my own reasoning. Each was told not to read prior proposals.

**All three independently reported encountering the proposal files and NOT opening them.** Two noted that the backlog itself leaks the strings "Candidate B" and "Candidate C" — a leak I did not anticipate. Neither knew what those candidates said.

**Each was told the answer need not take any particular form** — that it could conclude the question was malformed, that no single rule works, or that the cause was something other than a missing definition. That instruction matters: it left room for them to reject the premise, and two of them partly did.

---

## 2. What the three produced

| | **Run 1** | **Run 2** | **Run 3** |
|---|---|---|---|
| **Name** | Named-Force Rule | Named-Alternative Test | Compliant-Alternative Test |
| **The rule** | Every binding line must name **the specific external fact that forces it**; a binding line that cannot is a solution preference. | May constrain HOW only where the ticket names **the specific alternative a competent developer would otherwise choose and the concrete harm** — a harm **the ticket's own ACs would not already catch**. | State the properties; you may forbid an approach only if the ticket names **the harm that would follow from an alternative which met every one of those properties**. |
| **Discriminator** | External force present / absent | Named alternative + harm, **not already caught by ACs** | Harm from an **AC-compliant** alternative |
| **Closest reviewer** | **26** | **9** | **9** |
| **Est. failures / 41** | ~26–29 | ~10 | ~11 |

### The convergence is real, and it is 2-of-3 on the mechanism

**Runs 2 and 3 derived substantially the same rule independently.** Both say: construct the alternative that *satisfies every acceptance criterion*, then ask what harm follows. Both place the burden on the author, not the reviewer. Both estimate ~10 failures and both name **9** as the closest reading. Neither saw the other.

**Run 1 is genuinely different** — it asks for an external *force* (a domain rule, a ruling, a measured property, a downstream obligation) rather than a compliant alternative.

**And here is the sharpest part of the result: Runs 2 and 3 each independently considered Run 1's approach and rejected it by name.**
- Run 2: *"Rejected — the provenance test… it launders **authority into entailment**."* It notes Ruling E is a genuine external authority that would have licensed "exactly one module," which v3 removed as over-specification.
- Run 3: *"Provenance tells you a constraint has a sponsor. It does not tell you it binds."*

So the minority position was not merely outvoted — it was examined and refused by both others, for the same stated reason, without coordination.

### All three rejected the framing the original question was built on

Every run independently concluded that a pure *what-versus-how* test cannot work, and each gave the same reason: **"how" is not a property of a sentence.**

- Run 3: *"'how' is not a property of a sentence — it is a property of a sentence relative to a chosen altitude… A rule you can satisfy by rephrasing is not a rule."*
- Run 2: *"it is defeated by rephrasing — 'exactly one module' restates as 'the result contains exactly one derivation module'."*
- Run 1: *"any list of banned words, any what/how taxonomy… is trying to classify an object using a feature the object doesn't carry."*

**Candidates A, B and C were all text-classification rules.** Three independent readers say that entire family cannot work. That is a finding about the original proposal, not about D.

### Where they diverge, and it matters

**The count.** Run 1 says the 26-reviewer was closest; Runs 2 and 3 say 9. Run 1's reason is specific and checkable: it makes **unexplained numbers** the dominant failure and lists them — `26 hours`, `±2 rows`, `< 34 of 338`, `< 5%`, `< 1.0 pp`, `two days`, `≥30 player-seasons`, `≥12 capture dates`, `≥30 rows`, `~60%` — noting *"Not one states its basis. Every one of them binds."* Runs 2 and 3 do not treat an unexplained threshold as a boundary defect at all.

**This is the live disagreement David should see:** whether an unjustified *number* is the same defect class as an unjustified *mechanism*. Run 1 says yes and gets 26; Runs 2 and 3 say no and get ~10.

---

## 3. Findings none of them were asked for — including defects in my own v3

Three cold readers found things I did not.

**(a) The S0-03 defect is located.** Run 1 found the stale phrasing live at **`scripts/build_draft_pick_value_curve.py:32`** — *"y24_ppg is realized Year-2+3 PPG"* — two lines from a locator the backlog already cites for something else. S0-03's AC requires the phrasing be quoted before work starts; nobody had quoted it. **That ticket can now be executed.**

**(b) All three found the same live inconsistency in v3, independently.** `DG2-S3-07`'s *"the assembly is the **only** producer of that quantity"* is the identical defect v3 removed from `S5-03` (*"v2 mandated 'exactly one module'"*) — surviving **one ticket away**, in a revision whose stated purpose was consistency. Run 2: *"The backlog contains its own fix and did not apply it to the ticket that matters most."*

**(c) The pre-answering defect I believed I had fixed is still live.** Run 2 found `DG2-S5-01a`'s *"derived from the assembled value"* forecloses, by AC wording, the market-anchored pick pricing the spec explicitly keeps open — *the same defect v3 spent a section eliminating from Sprint 3.*

**(d) The spread may not be one axis at all.** Run 2 tabulated v3's six converged defects and found **five are under-specification, not over-specification** (ungateable ACs, missing problem statements, self-grading thresholds, dependency deadlock, missing tickets). Its conclusion: *"a rule that only draws the constraint/over-specification line will not by itself reconcile the reviewers."* Run 3 reached the same place by a different route — that the 41 tickets are **two genres**, research versus build, and the standard is written for build; applying it uniformly *"could carry a reviewer from 9 to 26 without a single incorrect judgement."*

**(e) Run 3's diagnosis of the root cause, which is not a missing definition.** It found the rule **already stated six times in the backlog** — *"the criteria select it"*, *"library choice is the developer's"*, *"how that is demonstrated is the developer's choice"* — applied wherever an author happened to notice and nowhere else. *"A reviewer cannot tell whether the silence means 'deliberately constrained' or 'the author didn't think about it.'"*

---

## 4. Residual contamination — disclosed, not claimed away

**I will not claim this re-run is perfectly clean. Two leaks, both named:**

1. **The backlog leaks "Candidate B" and "Candidate C" in its own text** (v3's header and DGX-03's hedge). Two runs reported seeing those strings. Neither knew what the candidates said, and Run 3 explicitly stated it ignored them and derived independently — but the leak is real and I did not foresee it. **The permanent fix is to strip those references from the backlog before any future re-run.**

2. **Runs 2 and 3 landed in territory adjacent to Tower's foreclosure framing.** Honesty requires saying so. What is *materially different*: Tower's version asked whether a mechanism "forecloses a better alternative" — an unbounded judgement about what is better. The converged rule asks whether an **AC-compliant** alternative causes a **named** harm — bounded, checkable, and with the burden on the author. The "already caught by the acceptance criteria" clause is the whole discriminator and appears nowhere in Tower's prompt. **David should weigh whether that difference is enough; I am not the right judge of it.**

---

## 5. Why there is no recommendation in this document

David rejected ratifying D because convergence produced by a supplied idea is not evidence. **That reasoning applies to me.** I saw Tower's framing, authored D, and argued for it — my judgment on which of these three rules is right is contaminated in exactly the way his ruling identified. **A consolidator who picks the winner here would be re-running the failure with one more step of laundering.**

So this document reports and does not choose. What can be said factually:

- **2 of 3 independent runs converged on the same mechanism** and on the same reviewer reading (**9**), having each rejected the third's approach by name.
- **3 of 3 rejected the text-classification family** that A, B and C all belong to.
- **The live disagreement is whether an unjustified number is the same defect as an unjustified mechanism** — that alone moves the answer from ~10 to ~26.
- **The boundary rule, whichever is chosen, does not reconcile the reviewers on its own** — two runs found the spread is mostly a second, different axis.

**The thread remains HELD.** No ticket rewriting against any of these. The three full derivations are preserved verbatim in the agent transcripts; the operative text of each is quoted above.
