# Codex's proposed rule, tested against the three uncontaminated derivations

**Date:** 2026-07-25 · **Status:** EVIDENCE. **Not a recommendation** — the boundary thread is HELD and my judgment on it is contaminated (I saw Tower's framing and argued D). What follows is what three clean runs say about Codex's specific components, plus quotes I verified myself.

**Codex's rule:**
> *"A ticket states required observable outcomes and may name an internal technical restriction only when it cites a pre-existing, owner-ratified boundary and explains the consequence it protects; otherwise design, dependencies, tools, implementation sequence, and test method belong to the developer."*

---

## 1. It is a conjunction, and the halves fared very differently

| Component | What the clean runs said |
|---|---|
| **"explains the consequence it protects"** | **This is the convergence.** Runs 2 and 3 derived essentially this independently and it is the discriminator both settled on. **Strongly supported.** |
| **"cites a pre-existing, owner-ratified boundary"** | **Runs 2 and 3 each examined a provenance test and rejected it by name**, independently, with counterexamples from these documents. **Contested.** |

Run 2: *"Rejected — the provenance test… it launders **authority into entailment**."*
Run 3: *"Provenance tells you a constraint has a sponsor. It does not tell you it binds."*

**Codex's conjunction survives their strongest attack.** Both attacked provenance as *over-admitting* — Ruling E is genuinely owner-ratified and would license *"exactly one module."* But Codex requires provenance **AND** consequence, and the consequence clause kills that case anyway: Ruling E's harm is divergent answers across surfaces, which a two-module CI-checked implementation prevents completely. Run 3 anticipated exactly this: *"A prescription may name its harm by citation — but only to a document that states the harm, not one that merely repeats the prescription."* **So the over-admission critique does not land on Codex's rule.**

**The under-admission critique does land, and I verified both cases in the live text.**

---

## 2. Two verified passages Codex's rule rejects that all three runs keep

**(a) `DGX-02` — backlog line 371, quoted exactly:**
> *"**Constraints:** restore verification must not weaken below its current strength; the run must complete within its existing window, **whose current duration is measured and recorded before work starts**; no irreplaceable store may remain uncovered."*

**Cites no owner-ratified boundary at all.** Run 3 calls it *"the single most load-bearing constraint in that ticket"* and uses it as the reason to reject a provenance rule outright. Under Codex's wording it fails and must be deleted or rewritten — for the absence of a citation it does not need.

**(b) `S2-01b` — backlog line 203, quoted exactly:**
> *"missing Year-1 rows are recorded missing, **never zero-filled** — the existing file pre-fills censored arcs with `0.0` and that pattern must not be repeated."*

This bans a technique — prima facie the thing the standard forbids — and every run passes it. But what it cites is **a measured property of the existing system**, not an owner ruling. Run 2 singles it out as *"the case that shows the rule is not a HOW-word ban wearing a hat."* Run 1's rule explicitly admits *"a measured property of the existing system"* as a legitimating force. **Codex's "owner-ratified boundary" is narrower than any of the three and excludes it.**

**The pattern: Codex's rule admits authority but not evidence.** In a program whose whole standard is *derived, not asserted*, a measured defect in the existing codebase is a **better** reason to constrain than a ruling — and it is the one Codex's wording turns away.

---

## 3. The usability cost — **substantially cured by a clause I had not seen. This section is corrected.**

**I wrote this section against a fragment of Codex's recommendation and was wrong in part.** The full text carries a tie-breaker I did not have:

> *"**Default unresolved cases to developer freedom.**"*

My original objection was that "owner-ratified" forces a lookup — a stranger cannot apply it without reading the ruling corpus, which is precisely the defect that sank Candidate B. **The default clause largely dissolves that.** A stranger who cannot determine whether something is ratified does not stall; they default to developer freedom and move on. The rule is therefore *applicable without the lookup* — it simply applies conservatively when the reader lacks context.

**That is a real cure and it is better than B**, which had no default and left the reader genuinely stuck. **Correction recorded: my point 4 below is weakened accordingly, and I am weakening it because I saw more, not because I am conceding a contested point.**

**What survives the cure, and it is narrow:** an ignorant reviewer will strike a legitimate owner-ratified constraint. But that error runs *toward* developer freedom — the standard's own bias — and the author appeals by adding the citation. **A benign, self-correcting failure direction.**

**Where the default clause makes things worse rather than better, and this is the sharpened form of §2:** for `DGX-02:371` and `S2-01b:203`, defaulting to developer freedom means those two constraints are **struck**, not kept. Both are uncited; both are load-bearing; all three runs keep them. **The default clause is right in general and wrong in exactly the cases §2 identifies** — which is an argument for widening what may be cited, not against the default.

## 3b. The Definition-of-Done clause resolves something all three runs flagged and none solved

> *"Process requirements such as RED-first and independent review belong in the program-wide Definition of Done, not as substitutes for ticket acceptance criteria."*

**This is the best structural idea in the whole exchange, and it came from Codex, not from any of my three runs.** All three independently identified the problem and none proposed this fix:

- Run 1: the `AC:` field *"carries at least four different species of sentence — properties of the delivered artifact, obligations on the ticket author, escalation policy, and explicit design releases… reviewers who treat authoring-process lines as 'implementation steps' will keep finding extra failures, and both readings are defensible."*
- Run 2: five of the six converged defects are a *second axis* the boundary rule does not touch.
- Run 3: the 41 tickets are *two genres*, and applying a build standard to research tickets *"could carry a reviewer from 9 to 26 without a single incorrect judgement."*

**A program-wide Definition of Done is the structural answer to all three.** It removes contract-test and review language from ticket text without denying the convention, which is exactly the disposal problem the "~10 tickets lose their contract-test language" cost was hiding. **On the evidence I have, this clause should survive whatever David decides about the rest.**

---

## 4. What Codex's rule does better than any of my three

Stated plainly, because it is real and none of the three runs produced it:

> *"…otherwise **design, dependencies, tools, implementation sequence, and test method** belong to the developer."*

**That enumeration is the crispest thing anyone has written on this question.** It names the five categories concretely, and "test method" in particular closes a hole all three runs left fuzzy — Run 1 flagged that the backlog's `AC:` field mixes artifact properties with authoring obligations and *"reviewers who treat authoring obligations as implementation steps will keep finding extra failures."* Codex's clause settles that by naming test method outright.

**If any wording survives from Codex's rule, it should be that clause.**

---

## 5. The one-word repair, offered as analysis and not as a proposal

If David wants to keep Codex's shape, the two verified failures above both close by widening one phrase:

> *…may name an internal technical restriction only when it cites a **pre-existing boundary or a measured property of the existing system**, and explains the consequence it protects…*

That admits DGX-02 and S2-01b, keeps the conjunction that defeats the over-admission attack, and costs nothing else. **It does not fix the stranger-usability lookup** — that is inherent to any citation requirement, and it is the live question, not a detail.

**The deeper question underneath, which the clean runs raise and Codex's rule does not settle:** whether the citation requirement earns its keep at all, given the consequence clause is doing the discriminating work in every worked example either of us has produced. Runs 2 and 3 concluded it does not. **That is the disagreement to put in front of David, and I am not the one to resolve it.**

---

## 6. Position of record

**I am not recommending for or against Codex's rule.** My judgment here is contaminated and David rejected ratification built on contaminated convergence.

What I can put my name to, all verified against the live text:

1. Codex's **consequence clause matches the uncontaminated convergence** (2 of 3 independent runs derived it separately).
2. Its **provenance conjunct was independently rejected by those same two runs** — but their strongest attack (over-admission) **does not land on a conjunction**, so the rejection is weaker against Codex's rule than against the provenance test they were actually attacking.
3. **The one defect I can still evidence:** it rejects two constraints all three runs keep — `DGX-02:371` and `S2-01b:203`, quoted and verified above — because **it admits authority but not evidence**. The `Default unresolved cases to developer freedom` clause *strikes* rather than saves them, so this is the place the rule is sharpest against itself. **One-word repair in §5.**
4. ~~It reintroduces the lookup that killed Candidate B.~~ **WITHDRAWN — see §3.** The default clause largely cures it. I wrote that objection against a fragment.
5. Its **final enumeration is the best clause anyone has written** on this question, and **the Definition-of-Done clause (§3b) is the best structural idea in the exchange** — it solves a second-axis problem all three of my runs identified and none of them solved.

**Net, stated plainly and against my own earlier position:** the full recommendation is **materially stronger than the fragment I first assessed**. Of my five points, one is withdrawn outright, one is weakened, and one — the authority-not-evidence gap — is sharpened and survives with two verified counterexamples.

**I am still not recommending.** The single question I would put to David, because it is the only one the evidence leaves genuinely open: **does the citation requirement earn its keep, given the consequence clause does the discriminating work in every worked example either lane has produced — and given it costs two constraints all three uncontaminated runs keep?**

**Still HELD. No ticket rewriting.**
