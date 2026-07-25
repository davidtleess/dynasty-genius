# Claude's DIFF against its own independent reviewer

**Companion to:** `docs/agent-ledger/2026-07-25-claude-independent-ticket-review.md`
**Predictions sealed BEFORE dispatch:** `docs/agent-ledger/2026-07-25-claude-sealed-predictions.md` — written so this diff is falsifiable rather than hindsight. Tower and David can check what I claimed to already know against what I actually wrote down first.

**Reviewer verdict: 13 PASS / 23 WEAK / 5 FAIL over 41 tickets** (v1 was 5/17/15 over 37).

---

## 1. What it found that I would NOT have found

Checked against my sealed list. **I predicted 6 of its findings. These I did not:**

**(a) The S3-05 ← S5-02 DEADLOCK. Its best catch, and it is mine to own.**
I predicted only that my "separable" claim was *loose*. It found an actual cycle: `S3-04 ← S3-05 ← S5-02 ∈ Sprint 5`, against the spec's own "no sprint may start until the previous gate closes." **Verified — line 232: `Deps: DG2-S5-02`.** Sprint 3 cannot complete without work that cannot start until Sprint 3 completes. I wrote both the edge and the ordering rule and never composed them. **This is the only defect that halts the epic outright and I would not have found it.**

**(b) S0-09's locator does not resolve — and following it up, I found something worse.**
It reported: no `PRODUCT_BRIEFING` exists; `PRODUCT_BRIEFING_CODEX.md` §4 is "Data Boundaries" with no such grouping. **Verified.** Then I checked further, and **the repo says the opposite of the ticket's premise**:
- `docs/system-design.md:102` — "Paid source access | **In scope.** PFF, PlayerProfiler, KTC subscriptions assumed."
- `docs/system-design.md:403` — "**Paid subscriptions for PFF, PlayerProfiler, and KTC are available.**"

So the claim that a briefing marks PFF and PlayerProfiler *unusable* is unsupported at the cited location and contradicted elsewhere. **I inherited that claim from Tower's relay and never checked it. That is the third time today I have propagated an unverified number or claim** (after Studio's "11 of 16" on 07-24 and the three load-bearing figures I flagged in the accountability probe). The ticket may be describing a real problem in a different file, or may be describing a problem that does not exist. **UNKNOWN, and it should not have shipped as a FAIL-worthy locator in a document whose defining strength is locators.**

**(c) S2-04 has no Problem statement at all.** It opens at `AC:`. The first field David's standard names, missing entirely, and I read that ticket several times.

**(d) Five tickets have no `Deps` line** (S2-01a/b/c, S5-01b/c) while others write "Deps: none" explicitly — so absence is ambiguous, not empty. I would not have caught the asymmetry.

**(e) The escape-hatch AC as a CLASS.** I predicted one instance (S5-01b). It generalised to four and named the mechanism: *"each of these can be closed by writing a paragraph."* That is a sharper diagnosis than mine.

**(f) Sprint 4's gate never mentions S4-03**, and Sprint 5's is silent on S5-01c/d and S5-03. Ruling F's entire purpose — the contention-window lens — can be absent and Sprint 4 still closes. I checked gates for *testability* and never for *coverage of their own sprint*.

**(g) S0-01 AC(3) "reproduced by a second lane" is staffing prescribed as acceptance criteria.** I would have defended this as rigour. It is right: the requirement is independent reproduction to ±2 rows; *who* does it is process.

**(h) The stranger-cannot-start finding, connected.** I flagged scratchpad/`/tmp` durability in my accountability probe as a *loss* risk. I never connected it to *"a new developer cannot read the reasoning any of this rests on"* — that the rulings live in a personal home directory outside any clone, and two named inputs resolve nowhere in the repo. Same facts, a consequence I missed.

**Where I actively disagreed on first read and then conceded:** S0-08 as a **FAIL**. My instinct was that an open-ended sweep is legitimately open-ended. Its argument is unanswerable: *a ticket with no completion criterion cannot gate anything*, and I made it block S1-01, the epic's keystone. Either it stops gating or it gets a bound. Conceded.

---

## 2. Where I think it is WRONG (with reasons — not capitulating)

**(a) S0-06 "no note saying it was removed" — partly wrong. Verified.**
There **is** a removal note at line 95 ("Moved out of the numbered backlog (records, not work): the TEP finding…"). Its narrower point survives: the note never says **"S0-06"**, so a reader tracking IDs cannot connect the gap to the note. **Correction accepted in substance, rejected as stated.**

**(b) "'declared tolerance' appears exactly twice" — wrong, it is three.** Verified by count. Trivial, and it does not touch the substance: no ticket declares the number, which is the real defect. Noting it only because a reviewer's arithmetic should be checked like anyone's.

**(c) S3-02 ← S3-01a is "not real" — I disagree, and I have the text.**
Its reasoning: parameters are "declared (never fit)", so the estimator is not needed. True for *declaring*. But S3-02's AC also requires **"the sensitivity range from S1-03 tested and its ranking impact reported."** A ranking impact requires rankings, which require the estimator. **The dependency is real for the AC as written.** I hold this one.

**(d) S1-01 ← S0-08 "not real" — mostly right, and I concede the substance while narrowing it.**
It is correct that a mathematical *form* does not depend on an exhaustive external sweep. But S1-01's AC requires naming "the two forms it was chosen over," and form feasibility does depend on obtainable data. **The correct fix is to re-point the dep at S0-07 (bounded, known sources), not to delete it** — which is a better outcome than either of us proposed alone.

**(e) The worst-problem call — I accept the substance and narrow the severity. See §3.**

---

## 3. Does its worst-problem call match mine?

**No. And its call is better than mine — I am saying so plainly rather than defending my own.**

**My sealed call:** the undeclared tolerances and thresholds that survived my v2 pass — Sprint 4's tolerance, S2-03's max age, S3-01a's seed. I had claimed in v2 to have put a number on every threshold word carrying a decision. I had not, and that is the exact defect I was asked to fix.

**Its call:** the backlog **pre-answers S1-02 through its own ticket structure** — five stream-branch tickets named for one construction (`E[v_i,t]`, `S_i,t`, `A_i,t`, "per-season estimator", "the stream"), and **zero** build tickets for the alternative the spec says "must be benchmarked, not dismissed."

**Why its call beats mine.** Mine is a defect *class* — real, but each instance is fixable in a line. Its is a structural fault that would waste a sprint: if S1-02 resolves against the stream, five tickets across three sprints need re-authoring. And it caught the thing I was actively trying to prevent, by a mechanism I did not consider — **ticket titles function as commitments**. I wrote "resolve, do not pre-answer" in the ticket and then pre-answered it in every downstream heading.

**Where I narrow it, with evidence.** The reviewer's framing is that the decision is *foreclosed*. The Sprint 3 tickets are **gated behind** S1-02 and S1-04, and S1-02 states *"an unresolved shape blocks Sprint 3 rather than defaulting to the mandate"* — a clause the reviewer itself credits in §6. So the true cost is **re-authoring**, not an unmakeable decision. That distinction matters for how urgently David must act: this is "the plan is biased and would need rework," not "the plan has already decided."

**But the bias is real and it compounds a governance problem I have already reported:** Rulings F and J contradict each other (F calls the per-season stream a HARD DESIGN REQUIREMENT, J says "not yet a mandate"), I resolved that contradiction myself without escalating, and then — as the reviewer found — encoded the F reading into the ticket structure anyway. **Two independent errors pointing the same direction is not a coincidence; it is a bias in my authoring, and the reviewer detected it from the artifact alone.**

**My revised worst-problem ranking:**
1. **The S1-02 pre-answering** (reviewer's call, adopted — structural, sprint-scale cost, and it compounds the F/J contradiction)
2. **The S3-05 ← S5-02 deadlock** (reviewer's runner-up — halts the epic, but one edge to fix)
3. **The unretrievable evidence base** (my addition, raised above the reviewer's placement — the rulings and eleven cited inputs are unreachable from any clone; this blocks *everyone*, not just a stranger, and it is the only item on this list that gets worse with time as `/tmp` is purged)
4. Undeclared tolerances (my original call, demoted)

---

## 4. Honest note on this exercise

The reviewer verified every code locator in the NAMED ARTIFACTS table independently and confirmed they resolve — including the snapshot mtime. That is the part of v2 I was most confident in and it held. **Everything it broke was in the parts I wrote from judgement rather than from reading the code**, which is the same split that has held all day: my locator work survives independent attack, my reasoning does not survive it unaided.

**Per the constraint, no ticket was edited from this order.** Findings are recorded for Tower to consolidate across all lanes' reviewers before any rewrite.
