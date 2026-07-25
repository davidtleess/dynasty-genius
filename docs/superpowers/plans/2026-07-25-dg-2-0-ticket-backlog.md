# DG 2.0 — ticket backlog v3 (EPIC → SPRINTS → TICKETS)

**Date:** 2026-07-25 · **Revision v3**, authored after **three independent fresh-engineer reviews** returned **5 / 9 / 26 FAILs** on the same 41 tickets against the same standard.
**Epic:** DG 2.0 — the dynasty-horizon rebuild · **Spec of record:** `docs/superpowers/specs/2026-07-25-dg-2-0-dynasty-horizon-rebuild-design.md`
**Status:** DRAFT — awaiting Codex binding review. **No implementation, ingestion, commit, push, or wire action authorized.**
**Flow:** Claude authors · **Codex gives the binding review** · iterate to an enumerated CLEAR. Tower carries packets and reports the outcome; it does not arbitrate substance.

> **The spread was a definition problem, not a quality problem.** The three reviewers disagreed almost entirely about **where "necessary constraint" ends and "prescribing the HOW" begins** — two lanes independently rejected their own reviewer on that axis. That question is **NOT settled here**: it is a separate PROPOSAL for David at `docs/superpowers/specs/2026-07-25-constraint-vs-how-boundary-proposal.md`. **v3 is written to the strictest defensible reading (Candidate B)** so that a permissive ruling can only *relax* it, never invalidate it.

## What v3 fixes — the six defects all three reviewers converged on

1. **Safe-fallback ACs repaired.** No AC may be closed by writing a statement. The floored-at-zero *product behaviour* is correct and **stays** — it is a runtime safe default, never an acceptance criterion.
2. **Problem statements added** to every ticket that lacked one (S2-04, S4-01, S4-03, S5-01a).
3. **Execution order fixed — and I say which.** See "The ordering fix" below.
4. **Stream pre-answering neutralised.** Construction-neutral ticket names; the alternative construction now has build tickets; the Ruling F/J contradiction is escalated to David rather than resolved by me again.
5. **Assembly and `rent_t` now have owners** (S3-07, S3-08) — the epic previously had no ticket that produced the thing it exists to produce.
6. **Late-bound thresholds** now name **WHO** declares, **WHEN**, and that the value is **frozen before any result is seen**. Pre-registration, not improvisation.

Plus: reciprocal dependency edges repaired, the spec/backlog gate conflict resolved, S2-05's unrelated market dependency removed, and the S0-06 numbering gap annotated.

---

## THE ORDERING FIX — I fixed the order, not the law

**The deadlock:** `S3-04 ← S3-05 ← S5-02 ∈ Sprint 5`, against the spec's *"No sprint may start until the previous sprint's exit gate is closed."* Sprint 3 could not finish without work that could not start until Sprint 3 finished.

**Decision: the law stands; the edge goes.** The law is a real quality control and weakening it to unblock one edge would trade a permanent safeguard for a local convenience. All three reviewers independently judged `S3-05 ← S5-02` to be **a data-currency preference dressed as a build dependency** — defining eligibility semantics does not require a fresh file; only reconciliation *counts* consume freshness, and reconciling against a 2026-06-23 snapshot is still a valid reconciliation.

**Therefore:** `S3-05` no longer depends on `S5-02`. `S5-02` and `S5-04` move to **SPRINT-P, a pre-sprint track that runs in parallel with everything and gates nothing** — they were already the two defects with no dependency on the dynasty-horizon value, and the sequencing note claimed they were separable while the graph said otherwise. Now the graph agrees.

---

## LATE-BOUND THRESHOLDS — the register

Some numbers are empirical results that cannot honestly be known in advance. Those are **late-bound**, not undefined — and every one is listed here with its owner, its deadline, and its freeze rule. **A late-bound threshold not in this register is a defect.**

| Threshold | Ticket | WHO declares | WHEN | Freeze rule |
|---|---|---|---|---|
| Primary metric, margin, direction (×3 benchmarks) | S1-04 | Claude, Codex binding review | Sprint 1, before any fit | Hash-frozen in the ledger; changing it after a result is void |
| Currency calibration tolerance, per decile | S1-04 *(moved from S4-02)* | Claude, Codex binding review | **Sprint 1**, not Sprint 4 | Same freeze; **declared before any calibration is run** |
| Survival calibration metric + tolerance | S1-04 | Claude, Codex binding review | Sprint 1 | Same freeze |
| Availability minimum resolution | S1-04 *(moved from S3-06)* | Claude, Codex binding review | Sprint 1 | Same freeze; the ticket may **not** declare the number that judges it |
| Discount sensitivity range | S1-03 | Claude, Codex binding review | Sprint 1 | Frozen with the decomposition |
| Join-rate floor for availability data | S1-04 | Claude, Codex binding review | Sprint 1 | Same freeze |

**Rule of record:** every threshold above is declared in Sprint 1 **before the work it judges is performed**. No ticket declares the number that grades it.

---

## NAMED ARTIFACTS

| Thing | Locator |
|---|---|
| Divergence artifact | producer `scripts/build_universe_market_divergence.py` → `src/dynasty_genius/universe_market_divergence.py` → `app/data/valuation/universe_market_divergence_latest.json` (**12,202 `players` rows**; **338** is the *matched comparable subset*, not the file count) · PIT `app/data/market_divergence_history.db` · refresh `scripts/run_market_divergence_refresh.py` |
| Pinned league snapshot | `app/data/league_snapshots/sleeper_universe_snapshot_latest.json` — observed mtime **2026-06-23 11:36** |
| Its four consumers | `src/dynasty_genius/league_capture.py:39,301` · `scripts/run_league_intelligence_refresh.py:68,99` · `scripts/build_roster_cut_report.py:26` · `scripts/build_team_value_matrix.py:24` (writer `src/dynasty_genius/sleeper_universe.py:352`) |
| CI defect sites | `src/dynasty_genius/eval/backtest_metrics.py:84-111` · `src/dynasty_genius/eval/qb_v3_walk_forward.py:211-258,260-293` · consumers `backtest_harness.py:593`, `composite_gate.py:42` |
| Scale clamp | `src/dynasty_genius/pvo_assembler.py:405-407` |
| Outcome table | `app/data/training/prospects_with_outcomes_v3.csv` (874 rows, 358 complete arcs, terminates at Year 4, no Year-1 columns) |
| Pick curve + SF knob | `scripts/build_draft_pick_value_curve.py:34` (`_SF_QB_PROMOTE_SLOTS = 0`) · `src/dynasty_genius/trade_lab/draft_pick_valuation.py:68-80` |
| Rulings A–J | `~/.claude/projects/-Users-davidleess/memory/david_rulings_2026-07-25_dg2.md` — **outside any clone. See RISK-1.** |

**RISK-1, unresolved and escalated:** the Rulings are cited as binding by ~12 tickets and live in a machine-local personal directory. Eleven further cited inputs live in `/tmp`, which macOS purges. **A developer with a fresh clone cannot read the reasoning this epic rests on.** A durable in-repo home is **proposed, not taken** — it is a David commit decision. *(All three reviewers reached this independently; Claude ranks it the epic's third-worst problem and the only one that worsens with time.)*

**Numbering note:** there is no S0-06. It was the TEP record, moved to the spec's status register in v2. The gap is deliberate.

---

## SPRINT-P — runs in parallel, gates nothing, blocked by nothing

*Both tickets have zero dependency on the dynasty-horizon value. David has been asked whether to run them immediately; they are structured so that answer changes nothing else.*

### DG2-P-01 — Surfaces read the freshest capture · Size M
- **Problem:** the four consumers above read a snapshot whose observed mtime is **2026-06-23 11:36** while a daily capture exists. **4 of 12 team posture labels are wrong on served data, including the labels used to choose a trade counterparty, and David's own rebuild progress is hidden from him.**
- **AC:** (1) all four consumers read the newest capture present on disk; (2) the posture labels are recomputed and the before/after published for all 12 teams — **the count of corrected labels is whatever it is on the day; the AC is that all 12 are recomputed and published, not that exactly 4 change**; (3) a capture older than **26 hours** surfaces a staleness signal at every consumer.
- **Deps:** none. **Fails loudly:** stale beyond 26h renders a staleness signal rather than a confident label.

### DG2-P-02 — Current injury/IR state on value surfaces · Size M
- **Problem:** a player on IR whose value reads as if healthy is a **live wrong answer** every time David opens the app, independent of any modelling. It compounds the invisible-IR defect in starter strength.
- **AC:** (1) the surfaces that display player value are **enumerated in the ticket before work starts** (the four consumers above plus any the S0-04 audit adds); (2) every enumerated surface shows current injury/IR state; (3) a player on IR is never presented as an available starter.
- **Deps:** DG2-P-03. **Visual surface ⇒ design-foundation load + framing pass before implementation.**
- **Fails loudly:** unknown injury state renders as unknown, never as healthy.

### DG2-P-03 — Current injury/IR feed · Size M
- **Problem:** *(added — no ticket owned a **current, refreshable** injury source; the epic had only a historical ingest path.)* There is no live injury/IR feed for any value surface.
- **AC:** (1) a current injury/IR state is available for every rostered player; (2) refresh cadence is declared and its staleness is visible; (3) coverage gaps are reported as gaps.
- **Deps:** DG2-S0-10 (obtainability). **Fails loudly:** a stale or partial feed surfaces as such.

---

## SPRINT 0 — KNOW WHAT WE ARE MEASURING

**Exit gate (binary):** S0-01…S0-05 have each **produced their measured result** — not merely a statement that one exists — and S0-07/08/09/10 have each delivered their document. **Any missing ⇒ Sprint 4 does not open and the divergence surface ships no change.**
*(v2's gate required only that a statement exist, which was strictly weaker than the tickets' own ACs, and it omitted S0-09 entirely. Both fixed.)*

### DG2-S0-01 — Rank-population mismatch ⚑ HIGHEST · Size M
- **Problem:** our side and the market side are ranked over different populations, so the divergence is not like-for-like.
- **Context:** rebasing moves the average delta **10.67 pp** and changes **127 of 338** noise-band classifications — larger than the age effect it is used to investigate.
- **AC:** (1) the common cohort is defined with its inclusion rule; (2) a rebased divergence exists for the same snapshot date; (3) the reclassification count is **independently reproduced to within ±2 rows** *(who reproduces it is not specified — the requirement is independent reproduction)*; (4) current and rebased average delta both reported.
- **Falsifier:** < 34 of 338 reclassified ⇒ cosmetic, drops priority.
- **Deps:** none. **Blocks:** S4-01, S4-02, and any age conclusion. **Fails loudly:** a non-common-cohort run refuses by name.

### DG2-S0-02 — Quantify the engine mix · Size S
- **Problem:** Engine B is T+1..T+2 and Engine A is Years 2–4; the divergence pools both, so the compared quantity is not one construct.
- **AC:** the per-engine share of the compared cohort is counted exactly and published. *(v2 bundled documentation and a re-run here; both are now separate — see S0-03 and S0-02b.)*
- **Falsifier:** Engine-A share < 5% ⇒ labelling defect only.
- **Deps:** none. **Blocks (conditional):** S1-01 **only if** share ≥ 5%. **Fails loudly:** a mixed-horizon comparison publishes the per-engine share alongside its result.

### DG2-S0-02b — Age association re-run by engine · Size S
- **Problem:** the +1.73 pp/year age association was measured on the pooled cohort; if the engines differ it may be an artifact of mixing.
- **AC:** the association is reported separately per engine with its interval.
- **Deps:** S0-02. **Fails loudly:** an underpowered per-engine slice reports its n and declines to conclude.

### DG2-S0-03 — `y24` documentation defect · Size XS
- **Problem:** `y24` is described as Year-2+3; the baseline uses **Y2–Y4**.
- **AC:** (1) the incorrect phrasing is **quoted in the ticket before work starts** and every occurrence corrected; (2) no occurrence of the incorrect phrasing remains in the repo.
- **Deps:** none. **Fails loudly:** n/a — documentation. *(The one ticket exempt from the fail-loudly rule, and it says so rather than writing a formula.)*

### DG2-S0-04 — Divergence-consumer audit · Size S
- **Problem:** the divergence may not be one construct across consumers, so a fix may repair one surface and not another.
- **AC:** every consumer of `universe_market_divergence_latest.json` and `market_divergence_history.db` is enumerated with the field it reads and its basis, and each is mapped to which of these fixes repairs it: **S0-01, S4-01, S4-02, S3-03**. *(The four consumers in the artifact table are a starting set, not asserted exhaustive.)*
- **Deps:** none. **Blocks:** S4-01, S4-02, S3-03. **Fails loudly:** a consumer reading an unlisted basis fails a check rather than rendering.

### DG2-S0-05 — Roster-size and lineup-shape mismatch · Size M
- **Problem:** market prices embed a bench-spot value calibrated to an average **11.3-team, 26.7-spot** league; we pin 12 teams and send no roster shape.
- **AC:** (1) the provider's accepted parameters enumerated from its documentation; (2) a shape-matched request compared to the current one on the same date; (3) the delta reported separately for rank mode and currency mode, as max and mean absolute change.
- **Falsifier:** rank-mode change < 1.0 pp mean absolute ⇒ immaterial to rank mode. **Currency-mode materiality is judged against the S1-04 tolerance** *(v2 promised "its own number" and never supplied one)*.
- **Deps:** none. **Blocks:** S4-02. **Fails loudly:** an unshaped request is stamped unshaped in provenance.

### DG2-S0-07 — Data-asset inventory *(Gemini)* · Size M
- **Problem:** no single list of what David pays for or may legitimately use.
- **AC:** one row per named source (PFF · collegefootballdata · PlayerProfiler · FantasyPros · Footballguys · Next Gen Stats · FantasyCalc) with: what it provides · terms **quoted** · obtainability · which S2 gap it fills. Access status is recorded as **known / unknown**, not asserted.
- **Deps:** none. **Fails loudly:** terms that cannot be established are recorded UNKNOWN, never as permitted.

### DG2-S0-08 — Bounded data-source sweep *(Codex)* · Size M
- **Problem:** the named source list may miss sources that fill S2's gaps.
- **AC (bounded — v2 was unbounded and therefore ungateable):** the five gap areas (multi-season outcomes · age 27+/30+ · injury/availability · snap/route share · roster-role history) are each searched, and for each the ticket records either **≥1 candidate with licence and obtainability, or a statement that the search found none**. **The search is time-boxed to two days; the stopping rule is the five gap areas, not exhaustiveness.**
- **Deps:** none. **Blocks:** nothing *(v2 wrongly let an unbounded ticket gate the epic's keystone)*. **Feeds:** S1-01 as information.
- **Fails loudly:** a candidate whose licence is unknown is listed as unusable-pending-verification.

### DG2-S0-09 — Verify the paid-source constraint before acting on it · Size XS
- **Problem — RESTATED, because v2's premise did not verify.** v2 asserted that `PRODUCT_BRIEFING` §4 groups PFF and PlayerProfiler with KeepTradeCut as unusable. **No file named `PRODUCT_BRIEFING` exists.** `PRODUCT_BRIEFING_CODEX.md` §4 is "Data Boundaries" and contains no such grouping. Worse, the repo appears to say the **opposite**: `docs/system-design.md:102` — *"Paid source access | **In scope.** PFF, PlayerProfiler, KTC subscriptions assumed"*; `:403` — *"Paid subscriptions for PFF, PlayerProfiler, and KTC are available."*
- **AC:** (1) establish whether any repo document actually marks PFF or PlayerProfiler unusable — **quoting file and line, or recording that none does**; (2) if such a document exists, correct it and sweep documents that inherited it; (3) if none exists, **record that the constraint was never real** so no further agent designs around it.
- **Deps:** none. **Fails loudly:** n/a — documentation.
- **Provenance note, recorded against myself:** the v2 claim came from a relay I did not verify. It is the third unverified claim I propagated today, and it is why this ticket now begins with *verify*, not *correct*.

### DG2-S0-10 — Injury data obtainability ⚑ DAVID ORDER · Size M
- **Problem:** David: *"we need to track injuries."* A prior audit concluded injury/IR history "requires a new source"; that conclusion is challenged, not accepted.
- **AC:** for each of a **named candidate set** (nflverse injury reports · the official NFL injury report · any candidate S0-08 surfaces), a statement of **granularity** (weekly designation · games missed · IR stints · body part · recurrence), **history depth in seasons**, licence, and the gap it fills. **A source counts as reachable only if a read has actually been performed.** The candidate set is the stopping rule.
- **Falsifier:** if reachable data is designation-only with **no games-missed linkage to player-seasons**, S3-06 is rescoped explicitly and S2-04's AC changes with it.
- **Deps:** none. **Blocks:** S2-04, S3-06, DG2-P-03. **Fails loudly:** unreachable granularity is UNKNOWN with what would settle it.

---

## SPRINT 1 — THE THESIS

**Exit gate (binary):** all S1 artifacts hash-frozen in the ledger, **the late-bound threshold register above fully populated**, and Codex has issued an **enumerated** CLEAR. **An artifact recording "unresolved" satisfies the hash but NOT the gate — S1-02 must return a decision or escalate to David.**

### DG2-S1-01 — The value construction · Size XL *(needs its own increment spec — v2 sized this L against its own legend)*
- **Problem:** decide the mathematical form of dynasty-horizon value: its estimand, its unit, and how a window is taken over it.
- **AC:** the chosen construction is written with its estimand and unit; the constructions it was chosen over are named with the reason each was rejected. **No property of the answer is pre-specified by this ticket** *(v2's AC pre-committed to a summation property, which pre-answered S1-02)*.
- **Deps:** S0-02 *(conditional)*, S0-07, S0-10. **Informed by:** S0-08. **Blocks:** S3-01, S3-09.
- **Fails loudly:** a construction whose data prerequisites are unmet is recorded blocked, not adopted provisionally.

### DG2-S1-02 — Horizon shape ⚑ THE OPEN QUESTION · Size M
- **Problem:** how many seasons, and per-season or aggregate? **This ticket decides it and carries no answer.**
- **Context, all positions, none endorsed:** David leans year-by-year full-career, updating as data lands (Ruling J), and **invited dissent with reasons**. Ruling F states a per-season stream as a hard design requirement. Claude's research argues that is over-stated on identifiability, additivity and pick-value grounds; Codex reached the pick-value conclusion independently. A direct multi-horizon construction `V(k)` is the named alternative.
- **⚠ ESCALATION TO DAVID, REQUIRED BEFORE THIS TICKET STARTS:** **Rulings F and J contradict each other** — F calls the stream a HARD DESIGN REQUIREMENT, J says "not yet a mandate." **I resolved that contradiction myself in v1/v2 and encoded the F reading structurally. That was David's call, not mine.** This ticket cannot proceed honestly until he says which ruling governs, or confirms the question is open.
- **AC:** a written resolution naming the chosen shape and the rejected shapes with reasons, **or** an escalation recording why the lanes cannot decide it.
- **Falsifier E1:** summed `V(1..2)` vs a directly-fit `V(2)` differing by more than the S1-04 margin rejects the per-season decomposition rather than tuning it. *(Evaluated in Sprint 3 against this frozen rule — the falsifier is frozen here, tested there.)*
- **Deps:** S1-01. **Blocks:** S3-01, S3-09. **Fails loudly:** an unresolved shape blocks Sprint 3 rather than defaulting to the mandate.

### DG2-S1-03 — Discount decomposition · Size M
- **Problem:** decide what, if anything, a discount rate does — separately from the window.
- **AC:** each of the six bundled components (outcome uncertainty · injury/career-end · role loss · roster scarcity · league/world risk · manager time preference) is assigned to exactly one destination; the window/discount double-counting question is answered; **if a rate exists, its sensitivity range is declared and frozen here.** A decision of "no rate" is a valid outcome.
- **Constraint:** **the discount is never FIT.**
- **Falsifier:** if the declared range moves any top-50 ranking by more than the S1-04 margin, the rate is load-bearing and escalates to David.
- **Deps:** S1-01. **Blocks:** S3-02. **Fails loudly:** a fitted rate fails a check.

### DG2-S1-04 — Freeze the falsifiers, benchmarks and every late-bound threshold · Size M
- **Problem:** thresholds declared after seeing results can be chosen to pass. Everything that grades Sprint 3 must be fixed before Sprint 3 runs.
- **AC:** the register above is fully populated — **every row has a number, an owner and a freeze timestamp**; falsifiers E1–E10 instantiated; the three benchmarks named with **metric, margin and direction** each; the document hash recorded in the ledger.
- **Amendment path (new — v2 froze a market benchmark that S2-02 could later make impossible):** if S2 proves a frozen benchmark unobtainable, the benchmark is **re-frozen by the same procedure with the reason recorded**; a silent change is void.
- **Deps:** S1-01, S1-02, S1-03. **Blocks:** all of Sprint 3 and Sprint 4. **Fails loudly:** a fit run against unfrozen thresholds is void.

---

## SPRINT 2 — DATA FOUNDATION

**Exit gate (binary):** for every position × age band the Sprint-1 construction relies on, **≥30 player-seasons**, and **≥1 observed season** in any band the construction extrapolates into (today: **0 at age 30+**). Failing bands are declared **out-of-support** and the thesis is amended to stop there — **the standard does not move.**

*Every S2 ticket's source and destination are named in the artifact table; "the outcome table" means `prospects_with_outcomes_v3.csv`.*

### DG2-S2-01a — Player-seasons at ages 27+ · Size M
- **Problem:** we hold **zero player-seasons at age 30+**, so any age curve would be fitted on players who have not aged.
- **AC:** **≥30 player-seasons per position at each of the 27–29 and 30+ bands, ingested and joined.** *(v2 allowed "or a written statement of the true ceiling" — closeable by writing a paragraph. Removed.)* **If the ceiling proves lower, the ticket does not close: it escalates to S2-05, which amends the thesis.** Provenance stamped per row.
- **Context:** `nfl_data_py` is archived — do not spend a day discovering that. Library choice is the developer's.
- **Deps:** S0-07. **Fails loudly:** a silent year-range truncation fails a row-count check.

### DG2-S2-01b — Year-1 outcomes · Size S
- **Problem:** the outcome table has **no Year-1 columns**, so a rookie's debut season cannot be valued — which pick value requires.
- **AC:** Year-1 games and points present for every arc in the outcome table that has Year-2 data; the null rate reported and **below the S1-04 join-rate floor**.
- **Deps:** S0-07. **Fails loudly:** missing Year-1 rows are recorded missing, **never zero-filled** — the existing file pre-fills censored arcs with `0.0` and that pattern must not be repeated.

### DG2-S2-01c — Year-5+ outcomes · Size M
- **Problem:** the outcome table terminates at Year 4, so no long-horizon target exists.
- **AC:** outcomes present through the last played season for every arc the source covers; **the censoring flag is defined in the ticket** (an arc is censored iff the player's career had not ended by the last covered season) and correct on a hand-checked sample of ≥30 rows.
- **Deps:** S0-07. **Fails loudly:** a censored arc that reads as complete fails a check.

### DG2-S2-01d — Games-played / availability history · Size M
- **Problem:** the value is a **rate** with no availability term; availability history is the input that fixes it.
- **AC:** games played and **games available** (defined in the ticket as team games in the player's active roster window) per player-season across the ingested range, joined to the outcome table on the canonical `player_id` at **≥ the S1-04 join-rate floor**.
- **Deps:** S0-07. **Blocks:** S3-06. **Fails loudly:** unjoinable rows are counted and surfaced, never silently dropped.

### DG2-S2-02 — Deepen the market time series · Size M
- **Problem:** only **4 annual snapshots** exist; a dynasty benchmark needs depth.
- **AC:** **≥12 distinct capture dates** obtained. *(Escape hatch removed.)* **If the obtainable ceiling is lower, the ticket escalates to S1-04's amendment path** — the benchmark is re-frozen with the reason recorded, and this ticket closes only when that amendment is complete.
- **Deps:** S0-07. **Fails loudly:** a gap in the series is visible in the artifact, never interpolated.

### DG2-S2-03 — Manual-export path for subscription sources · Size M
- **Problem:** some sources have no legitimate automated route; David has accepted manual exports for edge cases.
- **AC:** a documented export→ingest procedure that a second person can execute from the document alone; a provenance stamp per import; **staleness visible against a max age declared in this ticket before the first import** *(not after)*.
- **Scope note:** the staleness *mechanism* is DG2-P-01's; this ticket consumes it rather than building a second one.
- **Deps:** S0-07, S0-09. **Fails loudly:** an export past its max age surfaces stale rather than current.

### DG2-S2-04 — Ingest injury and availability data ⚑ DAVID ORDER · Size M
- **Problem:** *(added — v2 had no problem statement.)* No injury or availability history exists on disk, so neither the attrition side of the value nor any availability multiplier can be built.
- **AC:** injury records joined to player-seasons at the granularity S0-10 established, with per-season games-missed derivable; coverage reported per season and per position and **at or above the S1-04 join-rate floor**; null and zero distinguished.
- **Falsifier:** if games-missed cannot be linked, **S3-06 is rescoped explicitly** and this ticket closes against the rescoped target, not the original.
- **Deps:** S0-10, S2-01d. **Fails loudly:** unlinkable rows are counted and surfaced.

### DG2-S2-05 — Adequacy verdict · Size S
- **Problem:** prove the sample supports what the construction assumes before anything is fit.
- **AC:** per-position × per-age-band counts published against the gate thresholds with a **PASS or AMEND** verdict per band; every AMEND carries the thesis change it forces. **AMEND is a legitimate outcome.**
- **Deps:** S2-01a–d, S2-04. *(v2 depended on S2-02; market-series depth does not bear on production-sample adequacy — removed.)* **Blocks:** all of Sprint 3.
- **Fails loudly:** an out-of-support band is marked as such and any consumer evaluating into it refuses by name.

---

## SPRINT 3 — BUILD THE QUANTITY

**Exit gate (binary):** the built quantity **wins or ties on the frozen primary metric against all three frozen benchmarks**, with wins and losses named. **If it loses to any benchmark, the current artifact stays in production and the result publishes as a negative finding.**
**Spec/backlog conflict resolved:** the spec's Sprint-3 gate previously said "benchmarked, naming wins and losses"; this gate is the binding one and the spec now points here. *(A result could previously pass one gate and fail the other.)*

> **Construction-neutral naming.** v2 named these tickets for one branch (`E[v_i,t]`, "per-season estimator", "the stream"), which pre-answered S1-02. **v3 names them by role.** If S1-02 selects the direct multi-horizon construction, S3-01/S3-07 change shape but do not disappear; **S3-09 exists so the alternative has a build ticket rather than existing only as a yardstick.**

### DG2-S3-01 — The value estimator, in the form S1-02 selects · Size L
- **Problem:** produce the per-player value quantity the construction defines, in an unclamped unit.
- **AC:** the quantity produced for every player in the compared cohort across the supported horizon; a rerun reproduces it exactly; calibration **meets the S1-04 tolerance** at each horizon *(v2 required only that it be "reported")*.
- **Deps:** S1-01, S1-02, S1-04, S2-05. **Blocks:** S3-07. **Fails loudly:** a horizon beyond the supported band refuses rather than extrapolating.

### DG2-S3-01b — Survival / attrition · Size L
- **Problem:** produce the probability a player is still useful in a future season.
- **AC:** survival **meets the S1-04 calibration tolerance** against realized attrition by age band and position; the definition of "useful" is declared **in this ticket before fitting** and is **not derived from the value measure**.
- **Falsifier E3:** survivorship bias must be shown within the S1-04 tolerance against the full cohort **including exits** — the bias runs the same direction as the artifact under investigation.
- **Deps:** S1-01, S1-02, S2-01a, S2-01c, S2-05. **Blocks:** S3-07. **Fails loudly:** a cohort with unrecoverable exits is declared out-of-support rather than fitted on survivors.

### DG2-S3-02 — Discount application, per S1-03 · Size M
- **Problem:** apply whatever S1-03 decided — including "no rate", which is a valid outcome this ticket must support.
- **AC:** the decided treatment implemented; the S1-03 sensitivity range tested and its ranking impact reported. *(v2 asserted a single rate is wrong and mandated per-position parameters, pre-empting S1-03.)*
- **Deps:** S1-03, S1-04, S3-01. **Fails loudly:** a fitted rate fails a check.

### DG2-S3-03 — Retire the ceiling artifact · Size M
- **Problem:** the current scale destroys ordering at the top — twelve players tied at exactly 100, spanning the market's #3 to its #137. Ties break rank comparison, the product's core mechanism. `pvo_assembler.py:405-407`.
- **Constraint:** **no ceiling artifact — no tie created by a bound, no bound-truncated value — may reach any downstream consumer.** Range and any presentation bound are the developer's design choice.
- **AC:** (1) zero bound-induced ties in the compared cohort; (2) **the trade-math behaviour is unchanged against a baseline captured before the change** — the tests that cover it are named in the ticket before work starts, and if none exist that is the first deliverable; (3) every consumer from S0-04 verified against the new unit.
- **Deps:** S0-04, S1-04, S3-01. **Fails loudly:** a value at any bound is stamped bounded in its record.

### DG2-S3-04 — Starter strength from the optimal lineup · Size L
- **Problem:** starter strength is computed from actual starters. David: *"people often don't start their best players, especially if they are rebuilding."* It drives ~60% of the posture score and every positional z-score, surplus/deficit label and partner ranking.
- **AC:** (1) **"optimal" is defined in the ticket** as the league-legal lineup maximising summed player value under the slot rules, with ties broken deterministically; (2) computed for all 12 rosters; (3) an optimal-but-illegal lineup is rejected; (4) runtime within the **existing refresh budget, whose current value is measured and recorded in the ticket before work starts**.
- **Constraint:** deterministic for a given roster; league-legal; within budget. If an existing library satisfies those, use it — the criteria select it.
- **Deps:** S3-05. *(The 12-label impact publication moved to S3-04b.)* **Fails loudly:** an infeasible roster refuses by name rather than emitting a partial lineup.

### DG2-S3-04b — Publish the starter-strength basis change · Size S
- **Problem:** changing the basis moves every downstream label; shipping that silently would hide it.
- **AC:** before/after published for all 12 posture labels, every positional z-score and every partner ranking.
- **Deps:** S3-04. **Fails loudly:** an unpublished basis change fails the gate.

### DG2-S3-05 — Roster eligibility states · Size M
- **Problem:** IR and taxi players are invisible to starter strength.
- **Context — David's league rules, domain truth:** a taxi player may be promoted **at any point in the season**; promotion does **not** create a roster spot; **nobody may be added to taxi until after the rookie draft**.
- **AC:** every rostered player carries an eligibility state (active / IR / taxi); counts per state reconcile exactly against the league snapshot in use.
- **Deps:** none. *(v2's dependency on the snapshot-freshness ticket caused the deadlock and was a data-currency preference, not a build dependency. Removed — see "The ordering fix".)* **Blocks:** S3-04, S3-08, DG2-P-02.
- **Fails loudly:** an undeterminable state surfaces as unknown, never defaults to active.

### DG2-S3-06 — Availability term · Size M
- **Problem:** the value is a **rate**: a player expected to miss half a season carries the same value as one who plays every week. A second gap alongside horizon length.
- **AC:** an availability term produced per player-season; **an IR / expected-to-miss player and an every-week player at the same rate differ by at least the S1-04 minimum resolution** *(v2 let this ticket declare the number that judged it)*.
- **Deps:** S1-04, S2-04, S3-01. **Interaction:** test jointly with S4-03 — injury risk prices differently over two seasons than ten. **Fails loudly:** a player with no availability history gets a declared cohort default **visible in the record**, never an invisible 1.0.

### DG2-S3-07 — Assemble the final value ⚑ NEW — the epic had no owner for its own product · Size L
- **Problem:** *(found by one reviewer, conceded by Codex as a real miss.)* Sprint 3 produced the value estimate, survival, availability, the discount treatment and the roster cost **separately, and no ticket combined them.* The quantity the epic exists to produce had no builder.
- **AC:** a single assembled value per player per window, composed from the S3-01/S3-01b/S3-02/S3-06/S3-08 components; the assembly is the **only** producer of that quantity; every consumer reads it rather than recombining parts.
- **Deps:** S3-01, S3-01b, S3-02, S3-06, S3-08. **Blocks:** S4-01, S4-02, S4-03, S5-01a.
- **Fails loudly:** a missing component blocks assembly by name rather than being defaulted.

### DG2-S3-08 — Roster-spot cost ⚑ NEW — the `rent_t` term had no owner · Size M
- **Problem:** the spec's value carries a roster-spot opportunity cost and **no ticket produced it.** Ruling C makes it concrete: a taxi promotion costs a roster spot.
- **AC:** a per-season roster-spot cost derived and stated with its basis; the taxi conversion cost expressed in the same unit as the value it reduces.
- **Deps:** S3-05, S1-01. **Blocks:** S3-07. **Fails loudly:** an underivable cost is surfaced as unavailable rather than set to zero.

### DG2-S3-09 — The alternative construction, as a built comparator ⚑ NEW · Size M
- **Problem:** the spec says the alternative construction **"must be benchmarked, not dismissed"**, and v2 gave it **zero build tickets** while giving the stream five — which pre-answered S1-02 structurally.
- **AC:** the alternative selected in S1-02's rejected set is built to the point where it can be scored on the same frozen benchmark as S3-07, or S1-02's record explains why it cannot be.
- **Deps:** S1-02, S1-04, S2-05. **Fails loudly:** a benchmark run with a missing comparator reports the gap rather than scoring against two.

---

## SPRINT 4 — THE COMPARISON LAYER

**Exit gate (binary):** both modes reproduce on the common cohort with deltas published; **no mode ships whose calibration error exceeds the tolerance frozen in S1-04**; **and S4-03 exists and is exercised** *(v2's gate never mentioned it, so Ruling F's whole purpose could be absent and the gate still passed)*.

### DG2-S4-01 — Rank-vs-rank on the common cohort · Size M
- **Problem:** *(added.)* The two sides are ranked over different populations, so today's rank comparison is not like-for-like and its noise-band classifications are unreliable.
- **AC:** ranks computed on the S0-01 common cohort; the reclassification delta vs today published; a non-common-cohort run refuses.
- **Deps:** S0-01, S0-04, S3-07. **Fails loudly:** refusal, not a delta.

### DG2-S4-02 — Currency calibration · Size L
- **Problem:** converting our value to market currency on a linear basis is invalid where the market curve is exponential and already prices bench value.
- **AC:** calibration error is within the **S1-04 tolerance across the whole range, including the top and bottom** — the tails meet the same bar as the middle. **How that is demonstrated is the developer's choice** *(v2 mandated decile reporting)*. League shape from S0-05 applied.
- **Falsifier E5:** if a linear conversion meets the tolerance, the exponential premise is wrong and is revisited rather than the tolerance relaxed.
- **Deps:** S0-04, S0-05, S1-04, S3-03, S3-07. **Fails loudly:** an out-of-tolerance region blocks the mode rather than shipping under an average that hides it.

### DG2-S4-03 — Contention-window lens · Size M
- **Problem:** *(added.)* David asked to value a player over a chosen window — *"two seasons i think i can win the championship"* — and the product cannot express it. Ruling F makes the window a lens over dynasty-horizon value, never a replacement.
- **AC:** value summable over a user-selected window; two players that invert under two windows are shown **both ways, each labelled with its window**; dynasty-horizon remains the default view. **"Without contradiction" is defined as: both orderings are simultaneously visible and each is labelled with the window that produces it.**
- **Deps:** S3-07. **Fails loudly:** a window outside the supported horizon refuses rather than truncating silently.

---

## SPRINT 5 — PICKS

**Exit gate (binary, the model the other gates copy):** the three pick tests are **demonstrably priced, or picks stay floored at zero**; **and S5-01c and S5-01d are closed** *(v2's gate was silent on both)*.

### DG2-S5-01a — Production branch of pick value · Size M
- **Problem:** *(added.)* A pick's value is the value of a player who does not exist yet, and the product has no way to express a value stream that begins in a future season — which is why picks cannot currently be priced.
- **AC:** a pick's expected-production value derived from the assembled value beginning at the rookie's debut season, with uncertainty expressed to the S1-04 standard.
- **Deps:** S3-07, S2-01b, S5-01d. **Fails loudly:** a debut season out-of-support refuses.

### DG2-S5-01b — Optionality and liquidity branch · Size L
- **Problem:** Ruling A's three tests — **draft-and-cut**, the **pick's own trade value**, the **rookie-as-trade-chip option** — are not summations over a production stream, so the production branch cannot satisfy them.
- **AC:** **all three priced, each with its basis stated.** *(v2 allowed "or explicitly not priced", closeable by writing the phrase three times. Removed.)* **If a branch cannot be priced, the ticket does not close — it escalates to David with what is missing**, and picks stay floored at zero meanwhile. **The floor is the runtime safe default, not the acceptance criterion.**
- **Context — David's words:** *"if the valuation of picks is considering all of those things and STILL showing its worth less than zero, i would be okay with that being surfaced. but if it's not thinking like that - then its not valuing picks correctly."*
- **Deps:** S3-07, S3-08, S5-01d. **Fails loudly:** an unpriced branch keeps the floor on and says so on the surface.

### DG2-S5-01c — NFL-order → SF-rookie-slot bridge · Size M
- **Problem:** the pick curve's unit is the Nth skill player in NFL draft order, not rookie pick 2.01, and **`_SF_QB_PROMOTE_SLOTS = 0`** — the one built-in superflex correction is off. In a superflex league the proxy is weakest exactly where the league differs most.
- **AC:** the bridge is **quantified against observed rookie-draft slots** — the error between NFL-order position and actual rookie-draft position is measured and reported per round. *(v2 allowed "or declared an unvalidated error source", which let the problem go unsolved. Removed; the caveat remains a runtime behaviour, not the finish line.)* **If no observed slot data is obtainable, the ticket escalates** — that is a data finding, not a completed ticket.
- **Deps:** S0-07. **Blocks:** S5-01a, S5-01b. **Fails loudly:** an unquantified bridge is stamped on every emitted pick value.

### DG2-S5-01d — Pick-valuation plan v3 · Size M
- **Problem:** plan v2 carries **5 HIGH + 1 MEDIUM** unresolved Codex residuals; no candidate may be fit before a newly hashed v3.
- **Artifact:** `<session-scratchpad>/pick-valuation-plan-v2.md`, SHA-256 `98bfe11806bc…` — **see RISK-1; this file is not in any clone.**
- **⚠ BLOCKED PENDING DAVID:** a semantic ruling on **floored vs unfloored value** before either becomes the primary estimand.
- **AC:** every residual dispositioned in writing; v3 hashed and recorded.
- **Deps:** David's ruling. **Blocks:** S5-01a, S5-01b. **Fails loudly:** a fit run against v2 is void.

### DG2-S5-03 — One authoritative answer per computed quantity · Size M
- **Problem:** surfaces derive their own versions of computed quantities instead of reading one answer (Ruling E).
- **AC:** for starter strength, posture and assembled value, **all consumers return identical results for identical inputs**, and adding a second independent derivation is detected. **The code structure that achieves this is the developer's choice** *(v2 mandated "exactly one module")*.
- **Deps:** S3-04, S3-07, S0-04, DG2-P-01. **Fails loudly:** a divergent derivation is detected at CI, not in David's session.

---

## SEPARATE TRACK

### DGX-02 — Backup coverage expansion · Size M
- **Problem:** irreplaceable stores sit outside the backup manifest. Sleeper's players API exposes only the current date, so unbacked past snapshots are **gone forever**.
- **Scope:** four named files (`prospect_identity_review.jsonl` · `pff_exports/phase16_wr_manual_review.csv` · `phase16_wr_manifest.json` · `phase13_te_v10_plus_manifest.json`) **plus** the `app/data/league_snapshots/` snapshot + coverage globs. **Five entries: four files and one glob set.** *(v2's count did not match its own scope.)*
- **Constraints:** restore verification must not weaken below its current strength; the run must complete within its existing window, **whose current duration is measured and recorded before work starts**; no irreplaceable store may remain uncovered.
- **AC:** all five entries covered; a restore drill passes end-to-end with them included.
- **Fails loudly:** an uncovered irreplaceable store fails the coverage check.

### DGX-03 — SciPy version reproducibility · Size XS
- **Problem:** `scipy` is undeclared in `requirements.txt`, arriving transitively via `scikit-learn==1.8.0` (accepts `>=1.10.0`). The installed 1.17.1 satisfies the QB-1 study's registered runtime gate **by resolution luck**; a fresh clone can resolve differently and trip the study's own gate mid-run.
- **AC:** a fresh environment resolves the version the study's registration requires, reproducibly. **How that is achieved is the developer's choice.** *(Restated from v2's "pin SciPy" — but note this ticket is the contested case in the boundary proposal; if David ratifies Candidate C, v2's wording was already clean.)*
- **Constraint:** must land **before study execution**.
- **Fails loudly:** a mismatch already fails the study's registered `dependency_version_drift` gate; this ticket ensures that gate is never reached by accident.

### DGX-04 — Confidence-interval fail-open hardening · Size M
- **Problem:** two helpers can return a zero-width interval on failure, which reads as maximum certainty at the moment the computation failed. Sites: `backtest_metrics.py:84-111` · `qb_v3_walk_forward.py:211-258,260-293`. Consumers: `backtest_harness.py:593`, promotion gate `composite_gate.py:42`, where a zero-width CI auto-passes a width check.
- **Scope discipline:** the supporting report was **materially overstated** — the claimed collapse does not reproduce on the live path under the installed SciPy, and no current artifact or past promotion is corrupted. **Preventive, not remedial.**
- **AC:** a degenerate input does not produce a zero-width interval, and the promotion gate does not pass on it.
- **Constraint:** land before either the Engine-B trust-surface validation or the QB-v3 validation is rerun — **in particular before the QB promotion decision reads those intervals**.
- **Fails loudly:** that is the entire ticket.

---

## MAP

```
DG 2.0 — 44 numbered tickets (v2: 41; +5 new, −2 merged/moved)
│
├─ SPRINT-P  runs in parallel, gates nothing, blocked by nothing
│   P-01 freshest capture M · P-02 injury on surfaces ⚑DAVID M ← P-03 · P-03 live injury feed M ← S0-10
│
├─ S0  gate: measured RESULTS (not statements) for S0-01..05 + four documents delivered
│   S0-01 rank-population ⚑HIGHEST M → S4-01,S4-02   S0-02 engine mix S → S1-01(cond)  S0-02b age by engine S
│   S0-03 y24 doc XS   S0-04 consumer audit S → S4-01,S4-02,S3-03   S0-05 league shape M → S4-02
│   S0-07 inventory M   S0-08 bounded sweep M (gates nothing)   S0-09 VERIFY paid-source claim XS
│   S0-10 injury obtainability ⚑DAVID M → S2-04,S3-06,P-03
│
├─ S1  gate: artifacts hashed + threshold register FULL + enumerated CLEAR; "unresolved" does NOT pass
│   S1-01 construction XL ← S0-02(cond),S0-07,S0-10
│   S1-02 horizon shape ⚑OPEN M ← S1-01   ⚠ESCALATE F-vs-J TO DAVID FIRST
│   S1-03 discount M ← S1-01 → S3-02      S1-04 freeze thresholds M ← S1-01..03 → ALL S3, ALL S4
│
├─ S2  gate: ≥30 player-seasons per position×age band; ≥1 observed in any extrapolated band
│   S2-01a age27+ M · S2-01b Year-1 S · S2-01c Year-5+ M · S2-01d availability M → S3-06   (all ← S0-07)
│   S2-02 market series M ← S0-07   S2-03 manual export M ← S0-07,S0-09
│   S2-04 injury ingest ⚑DAVID M ← S0-10,S2-01d      S2-05 adequacy S ← S2-01a-d,S2-04 → ALL S3
│
├─ S3  gate: win-or-tie vs all three FROZEN benchmarks, else current artifact stays in production
│   S3-01 estimator L · S3-01b survival L · S3-02 discount M · S3-03 retire ceiling M
│   S3-04 optimal lineup L ← S3-05 · S3-04b publish basis change S ← S3-04 · S3-05 eligibility M (no deps)
│   S3-06 availability ⚑DAVID M ← S1-04,S2-04,S3-01
│   S3-07 ASSEMBLE THE VALUE L ⚑NEW ← S3-01,S3-01b,S3-02,S3-06,S3-08 → S4-01,S4-02,S4-03,S5-01a
│   S3-08 ROSTER-SPOT COST M ⚑NEW ← S3-05,S1-01 → S3-07
│   S3-09 ALTERNATIVE CONSTRUCTION M ⚑NEW ← S1-02,S1-04,S2-05
│
├─ S4  gate: both modes within FROZEN tolerance + S4-03 exercised
│   S4-01 rank-vs-rank M ← S0-01,S0-04,S3-07   S4-02 currency L ← S0-04,S0-05,S1-04,S3-03,S3-07
│   S4-03 window lens M ← S3-07
│
├─ S5  gate: three tests priced OR floored at zero; S5-01c and S5-01d closed
│   S5-01a production M ← S3-07,S2-01b,S5-01d   S5-01b optionality L ← S3-07,S3-08,S5-01d
│   S5-01c NFL-order bridge M ← S0-07 → S5-01a,S5-01b   S5-01d plan v3 M ← DAVID RULING
│   S5-03 one authoritative answer M ← S3-04,S3-07,S0-04,P-01
│
└─ SEPARATE  DGX-02 backup M · DGX-03 SciPy XS (before study execution) · DGX-04 CI hardening M
```

**Cross-cutting on every ticket:** `decision_supported=false` recursively · no market data in Engine A/B training features · no verdict or nominated target in running-software output · **`Fails loudly:` stated** (S0-03 exempt and says so) · reviewers CLEAR content, **David authorizes actions**.

**Open for David, not decided here:** the constraint-vs-HOW boundary rule (separate proposal) · the **Ruling F vs J** contradiction blocking S1-02 · floored-vs-unfloored estimand blocking S5-01d · whether SPRINT-P runs now · a durable in-repo home for the rulings (RISK-1).
