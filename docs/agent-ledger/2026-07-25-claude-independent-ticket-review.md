# Independent fresh-engineer review — DG 2.0 backlog v2 (Claude lane's reviewer)

**Dispatched by:** Claude lane, 2026-07-25, per David's order that each lane run its own reviewer.
**Reviewer context:** a subagent given **only** the two files and David's ticket standard. No session context, no access to Claude's reasoning, no knowledge that any other review exists, and no defence of the backlog offered to it.
**Agent id:** `a0fa7293f368af58f`.

> Claude's note on fidelity: this is the reviewer's own output, reproduced. Claude's agreements, disagreements and verifications are in the **separate** diff document and are deliberately not mixed into this file.

---

## Headline (reviewer's words)

> This is better than a typical backlog, and materially better than the v1 it replaces. I independently checked **every code locator cited in the NAMED ARTIFACTS table and in the tickets** — all of them resolve, including line numbers and the `2026-06-23 11:36` snapshot mtime. That is rare and it is the single strongest thing about this document. The remaining problems are not sloppiness; they are three structural faults (one open question pre-answered by the ticket structure, one backwards dependency that deadlocks the epic, one sprint gate with no number) plus a recurring habit of acceptance criteria that any outcome satisfies.

## 1. Verdict per ticket — **13 PASS · 23 WEAK · 5 FAIL (41 tickets)**

**Sprint 0 — 5 PASS / 2 WEAK / 2 FAIL**

| Ticket | Verdict | Reason |
|---|---|---|
| S0-01 rank-population | **PASS** | The model ticket — measured problem, four numbered ACs, numbered falsifier, deps both directions |
| S0-02 two engines pooled | **PASS** | The conditional block (`only if ≥5%`) is exactly right; "any consumer doc" unenumerated |
| S0-03 y24 doc defect | **WEAK** | Requires a grep for "the stale phrasing" — **the phrasing is never quoted**, so the grep string is unknown |
| S0-04 consumer audit | **PASS** | Table with named columns and a named minimum set of four fixes |
| S0-05 roster/lineup shape | **WEAK** | Rank mode has a number; currency mode is handed to "**its own number**", which does not exist |
| S0-07 data-asset inventory | **PASS** | Terms **quoted**, UNKNOWN required rather than assumed, countable |
| S0-08 open-ended sweep | **FAIL** | Unbounded by design ("a floor, not a ceiling") **and it blocks S1-01**. A ticket with no completion criterion cannot gate anything |
| S0-09 briefing correction | **FAIL** | **Locator does not resolve.** No `PRODUCT_BRIEFING` exists; `PRODUCT_BRIEFING_CODEX.md` §4 is "Data Boundaries" and contains no such grouping |
| S0-10 injury obtainability | **PASS** | "reachable only if a read has actually been performed" is a genuine bar |

**Sprint 1 — 2 PASS / 2 WEAK**

| S1-01 value form | **WEAK** | No falsifier at all; blocked by S0-08 which has no finish line, so it can never be provably unblocked; sized L for what the legend calls XL |
| S1-02 horizon shape | **WEAK** | AC ends "in a form **David can rule on**" — not third-party testable; its falsifier E1 needs S3-01a, the ticket it blocks |
| S1-03 discount decomposition | **PASS** | Six components → one of five buckets is countable; "never FIT" is a constraint; falsifier numbered |
| S1-04 frozen falsifiers | **PASS** | Metric + margin + direction + ledger hash. Supplies half the backlog's missing numbers |

**Sprint 2 — 1 PASS / 7 WEAK.** S2-01a/S2-02 carry **escape-hatch ACs** ("…**or a written statement of the true ceiling**"). S2-01b "mature class" undefined. S2-01c "censoring flag **correct**" undefined. S2-01d "**joinable**" with no join-rate threshold. S2-03 is three deliverables and its staleness mechanism overlaps S5-02 and the unfunded silent-failure epic. **S2-04 has no Problem statement at all — the ticket opens at `AC:`.** S2-05 **PASS**.

**Sprint 3 — 0 PASS / 5 WEAK / 2 FAIL**

| S3-01a estimator | **WEAK** | Calibration "**reported**", not passed; no bar in the ticket |
| S3-01b survival | **WEAK** | "**useful**" defined inside the ticket judged by it; "**calibrated**" carries no metric or tolerance |
| S3-02 positional discount | **WEAK** | Falsifier turns on S1-04 outputs; deps omit S1-04, contradicting S1-04's "Blocks: all of Sprint 3" |
| S3-03 retire ceiling | **WEAK** | "the trade-math regression suite passes **unchanged**" — the ticket's gate, **no path**, in a document whose strength is locators |
| S3-04 optimal lineup | **WEAK** | Constraint exemplary; "**the existing refresh budget**" has no number or locator; inherits the S3-05 deadlock |
| S3-05 IR/taxi | **FAIL** | **Cannot be scheduled** — its sole dep points forward to a Sprint 5 ticket. Also two problems in one |
| S3-06 availability | **FAIL** | **Self-grading**: differ by "≥ the term's own declared minimum resolution, **which the ticket declares**" |

**Sprint 4 — 2 PASS / 1 FAIL.** S4-01 **PASS**, S4-03 **PASS**. **S4-02 FAIL** — "held to the same **declared tolerance**", a number that exists nowhere and **no ticket is assigned to declare it**; it is also the Sprint 4 gate's only term.

**Sprint 5 — 1 PASS / 6 WEAK.** S5-02 **PASS** ("alongside S0-01, the best ticket here"). S5-01b/c carry escape-hatch ACs. S5-01d is "Blocked pending David" and silently blocks S5-01a/b. S5-03 "**exactly one module**" prescribes structure. S5-04 "wherever player value is shown" is unenumerated two tickets after four consumers were named at file:line.

**Separate track — 2 PASS / 1 WEAK.** DGX-03 "the cleanest ticket in the backlog." DGX-04 PASS, noted for stating its own supporting evidence "was materially overstated." DGX-02 **WEAK** — AC says "**all five entries**" but Scope lists four files plus globs; "past **its window**" has no number.

## 2. Remaining HOW prescriptions (quoted)

- **S5-03:** "computed in **exactly one module**" — one package / one service / one memoised function all satisfy the constraint
- **S4-02:** "calibration error reported **by decile**" — quantile regression or a top-N/bottom-N split would serve equally
- **S3-01a:** "reproducible from **a pinned seed**" — a closed-form estimator has no seed and would fail this AC while meeting the requirement
- **S0-01:** "reproduced by **a second lane**" — staffing prescribed as acceptance criteria
- **S0-03:** names **grep** while withholding the string
- **S2-01d:** "goes to **triage**"
- **The "contract test" family** (~10 tickets) — flagged but **explicitly not weighted heavily**, as it is this repo's established cockpit-TDD convention. The one place it crosses: **S3-04 AC(2)**, where the *existence of a test* is the criterion rather than the behaviour.

**Named as model constraint-not-mandate rewrites:** S3-03 ("no ceiling artifact … the range and where any presentation bound is applied are the developer's design choice"), S3-04 ("the criteria select it, not this ticket"), S2-01a ("`nfl_data_py` is archived — do not spend a day discovering that. The library choice is the developer's").

## 3. Threshold words carrying real decisions, with no number

`declared tolerance` (S4-02) · `unchanged` + `verified` (S3-03) · `useful` + `calibrated` (S3-01b) · `correct` (S2-01c) · `joinable` (S2-01d) · `mature class` (S2-01b) · `the existing refresh budget` (S3-04) · `past its window` (DGX-02) · `judged on its own number` (S0-05) · `explicitly` (S0-10) · `wherever player value is shown` (S5-04) · `either validation` (DGX-04, no antecedent) · `its own uncertainty` (S5-01a).

**A distinct and more serious class — ACs any outcome satisfies:** S2-01a, S2-02, S5-01b, S5-01c ("…**or a written statement of / or explicitly not priced / or declared an unvalidated error source**"). *"Each of these can be closed by writing a paragraph."*

**Not third-party testable:** S1-02 ("in a form David can rule on"), S3-06 (circular by construction, and the ticket says so), S1-01 (no falsifier; AC certifies a document exists, not that a decision is sound).

## 4. Two-or-more-problems tickets

S3-05 (state model vs valuation semantic — splitting also removes half the deadlock) · S2-03 (procedure + provenance + staleness signal, the third overlapping S5-02 and the unfunded epic) · S3-04 (algorithm + downstream migration) · S4-02 (calibration + league-shape application) · S1-01 (under-sized: the epic's largest decision at L when the legend says XL needs its own spec).

**Named as textbook splits:** the S0-10 → S2-04 → S3-06 chain, the S2-01a–d and S5-01a–d splits, and keeping the scale decision in exactly one place.

## 5. Dependency defects

**The deadlock.** `S3-04 ← S3-05 ← S5-02 ∈ Sprint 5`, against the spec's *"No sprint may start until the previous sprint's exit gate is closed."* Sprint 3 cannot complete without work that cannot begin until Sprint 3 completes.

**Contradiction inside one paragraph:** the sequencing note claims both are liftable "**without touching any other ticket**" and then "S5-04 depends only on `DG2-S3-05`" — which depends on S5-02. Three tickets across two sprints.

**Falsifiers that require the tickets they gate:** S1-02's E1 and S1-03's falsifier both need S3-01a output; both tickets block S3-01a.

**Stated but not real:** S3-05←S5-02 (a data-currency preference dressed as a build dependency, and the sole cause of the deadlock) · S1-01←S0-08 (an unbounded sweep cannot gate a mathematical form) · S3-02←S3-01a (declared, never-fit parameters do not need the estimator) · S4-02←S3-03 names the wrong producer (should be S3-01a).

**Real but unstated:** four of seven Sprint-3 tickets omit S1-04 and S2-05 despite both claiming "Blocks: all of Sprint 3" · S5-01a/b ← S5-01d ("a fit run against v2 is void by contract") · **five tickets have no `Deps` line at all** (S2-01a/b/c, S5-01b/c) while others write "Deps: none" explicitly · S5-03 ← S5-02/S0-04 · S2-01a–d ← S0-07/S0-08 · **four tickets gated on David with no wait-state modelled** · DGX-03 ← study execution, which is deliberately not a ticket · S3-03 ← an artifact with no locator · S5-04 ← the design-foundation load, stated as a bullet not a dependency.

**Traceability:** numbering runs S0-05 → S0-07 with no S0-06 and no note; the arithmetic is correct but a reader will hunt for it.

## 6. Sprint gates — objectively testable?

| Sprint | Testable | Note |
|---|---|---|
| **0** | **YES**, mechanically | But **strictly weaker than its own ACs** — it requires a statement to exist, not the analysis to be done. **S0-09 is in the sprint but absent from the gate** |
| **1** | **YES** | Hashes and enumerated CLEARs are checkable. Passable while the goal fails — a document reading "we could not resolve" would hash and clear. S1-02's block-rather-than-default clause "deserves credit" |
| **2** | **YES — the best gate here** | Real numbers, a stated current value (0 at 30+), a safe default that is not an escape hatch. Cannot fail by construction — deliberate and correct |
| **3** | **CONDITIONALLY YES** | Testable once S1-04 supplies metric/margin/direction. The parenthetical naming what v1 got wrong "is the kind of honesty that makes a document trustworthy" |
| **4** | **NO** | "declared tolerance" is declared by no ticket. **Only gate not marked "(binary, safe default)"**, and it **never mentions S4-03** — Ruling F's whole purpose can be absent and the gate passes |
| **5** | **PARTIALLY** | Pick half binary and safe-defaulted; surface half testable for S5-02, not for S5-04. **Silent on S5-01c, S5-01d and S5-03** |

**Passable while the underlying goal fails: Sprints 0, 1, 4, 5. Sprints 2 and 3 are sound.**

## 7. The single worst remaining problem (reviewer's call)

> **The backlog answers `DG2-S1-02` in its own structure, while `DG2-S1-02` insists the question is open.**

S1-02 says *"This ticket exists to decide it; it does not carry the answer"* and *"none endorsed here."* But five downstream tickets are written for one branch **by name**: S3-01a "**per-season** estimator" producing `E[v_i,t]` · S3-01b `S_i,t` · S3-06 `A_i,t` "per player-season" · S4-03 "value **summable**" · S5-01a "derived from **the stream**." The rival construction — direct multi-horizon `V(k)`, which the spec says "**must be benchmarked, not dismissed**" — has **zero build tickets**.

> Why worse than the others: the Sprint 4 tolerance is one missing number. The S3-05 deadlock is one dependency edge. This is not a defect *in* a ticket — it is the plan's shape overriding the plan's own open question, and it is precisely the failure the spec warned about when it titled the ticket "resolve, do not pre-answer." It also runs against the governance record: David invited dissent with reasons, two lanes produced them, and the backlog encodes the mandate anyway — silently, through ticket titles rather than through a decision anyone can contest.

**Runner-up:** the S3-05 ← S5-02 deadlock, "the only defect that halts the epic outright."

## 8. Could a stranger start tomorrow?

> Mostly yes for the analysis work, and that is a genuine achievement. But they stall inside the first hour, and the stall is not in a ticket.

**Ready to ship in week one:** S0-01, S5-02, DGX-03 — all locators verified, traps pre-defused, targets given.

**First hard block: `DG2-S0-09`** — XS, no deps, flagged as an error every agent designed around, and *"exactly the warm-up a new developer grabs on day one."* Its locator does not resolve. Missing: the actual path, a section anchor, and **the quoted text of the false grouping** — "the same three things S5-02 supplies flawlessly for its four consumers, forty lines earlier in the same document."

**Same-day blocks:** S0-03 (the phrase to grep is never quoted) · S0-08 (unbounded by construction, and it blocks the epic's keystone).

**The deeper blocker:** Rulings A–J are cited as binding in ~12 tickets and live only at `~/.claude/projects/…/memory/…` — *"a machine-local personal directory, outside the repository, not in any clone."* The spec's eleven "Binding inputs read in full" are `/tmp/*.md` in a directory macOS purges, and two named inputs (`research-dynasty-horizon-construction-claude.md`, Studio `009-WORKING-NOTES.md`) **do not resolve anywhere in the repo.** *"A new developer cannot read the reasoning any of this rests on."*
