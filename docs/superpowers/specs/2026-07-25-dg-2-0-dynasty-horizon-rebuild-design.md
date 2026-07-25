# DG 2.0 — the dynasty-horizon rebuild (EPIC spec of record)

**Date:** 2026-07-25
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization. **No implementation authorized by this document.**
**Authoring lane:** Claude authors the spec/framing · **Codex** is the sole binding independent reviewer and RED author · **Gemini** is Operations & Telemetry (facts on request, awareness copies, no judgment).
**Epic name:** DG 2.0 — the dynasty-horizon rebuild (named by Tower, 2026-07-25).
**Scope:** the construction of a dynasty-horizon value for Dynasty Genius, and every consumer that depends on it. **It is NOT** a UI redesign, **NOT** a re-litigation of the QB-1 validation program, and **NOT** authorization to ingest, fit, commit, or push anything.

> **Epic-level spec.** This document is the program of record. It carries the measured problem, the sprint gates, the falsifiers, and the risks. **Each build sprint gets its own increment-level design spec** before its RED opens — this document names them, it does not replace them. The ticket backlog lives at `docs/superpowers/plans/2026-07-25-dg-2-0-ticket-backlog.md`.

**RULING SOURCE — IN REPO, retrievable from a clone.** David's Rulings A–J are cited as binding throughout this epic. They live at **`docs/governance/rulings/2026-07-25-dg2-rulings.md`** — committed on David's word, 2026-07-25, byte-identical (`b454e5574d16…`) to the source of record at `~/.claude/projects/-Users-davidleess/memory/david_rulings_2026-07-25_dg2.md`.

**Why this location:** `docs/governance/` is where binding authority already lives (`00`–`04`). A dated `rulings/` subdirectory keeps decision records separate from the numbered standing documents, so it adds authority without disturbing the authority-order numbering in `02`. **Any `/tmp` copy is a working copy and is not the source.**

**RISK-1 is now partly closed.** All three independent reviewers flagged that a developer with only a clone could not read the rulings the tickets cite. That is fixed for the rulings. **It is NOT fixed for the eleven `/tmp` research inputs** listed below, nor for the scratchpad artifacts the backlog cites (008 plan v2, the D3-d packets, the dynasty-horizon research document) — those remain outside any clone and `/tmp` is purged by the OS. That residue is named, not solved.

**STATUS REGISTER (records and process, deliberately NOT numbered tickets — they carry no engineering work and would corrupt the planning count):**
- **TEP — CLOSED AS VERIFIED (Ruling I satisfied).** Held values are **TEP-off**. `tep=0` is not a valid provider encoding (404); provider-off is `tep=none`; the omitted and explicit-off responses are identical on **475/475** rows and **68/68** TE values. **Tucker Kraft is not a TEP artifact.** Correction recorded: a TEP misconfiguration would corrupt currency and cross-position comparison, but **0 of 68 TE position ranks changed** under TEP+, so "every tight-end comparison would be wrong" was too broad for rank mode.
- **Redraft comparison — REFUSED and CLOSED (Ruling D.1).** A standing constraint, not a deferred option. Any proposal reopening it is a governance escalation.
- **`surplus_label` reading "deficit" at all four positions — REFUTED as an independent defect (Studio 009 P5, verified 2026-07-25). No ticket.** The four values reproduce, but the semantics are **intentional and correct**: each position is defined against the 12-team league distribution (`team_value_matrix.py:143-150,208-220`; recorded in `docs/strategies/Phase17-Research-Draft.md:191-195`), and `league_opportunity_map.py:154-175,249-299` matches a league-relative deficit to another roster's league-relative surplus. **An all-around weak roster can truthfully be below the league threshold at all four positions; fourteen WR slots do not prove a surplus.** Within-roster normalisation would force every team to show a "surplus" even when every group is weak, and would break counterparty fit. **The inputs are contaminated by `P-06` and `S3-04c` — correct those and recompute.** At most, rename to "league-relative value deficit" for clarity.
- **Adversarial review to CLEAR** — this is each sprint's **exit gate**, not a ticket.
- **QB-1 D3-d r3** — repairs complete and verified; packet parked at `<scratchpad>/msg_codex_d3d_green_review_r3.txt` (`96d98c51cd1d…`); awaiting Codex review, then **David's commit word**; the RED file rides in the same commit. Tracked here and in `AGENT_SYNC`, not as a planning ticket.
- **Silent-failure — the contradiction is resolved.** The *"state how this fails loudly"* line is **in force now** as a cross-cutting authoring requirement on every ticket in the backlog; it needs no decision. What remains **open for David** is only whether to *additionally* fund a thin epic owning a shared surfacing mechanism. One is binding, the other is a proposal — they are no longer the same item.

**Binding inputs read in full:** the rulings file above (Rulings A–J + Tower synthesis + external research) · Claude research `research-dynasty-horizon-construction-claude.md` (`9ef71a31260a…`) · `/tmp/codex_age_opportunity_premise_verdict.md` · `/tmp/codex_market_measurement_verdict.md` · `/tmp/gemini_dynasty_horizon_data_floor.md` · `/tmp/gemini_freshness_audit.md` · `/tmp/gemini_bca_blast_radius.md` + `/tmp/codex_bca_blast_radius_review.md` · `/tmp/gemini_backup_coverage.md` + `/tmp/gemini_backup_requirements.md` + `/tmp/codex_backup_change_surface_review.md` · `/tmp/gemini_compression_pressure_test.md` · Studio `009-WORKING-NOTES.md` findings 1–3.

**Evidence legend used throughout:** **[VERIFIED]** reproduced with a locator · **[ARGUED]** reasoning, falsifiable · **[UNKNOWN]** not settled, with what would settle it.

---

## 1. Problem (measured, not inferred)

David, 2026-07-25, verbatim: *"absolutely no redraft market analysis - this is a dynasty tool we must go EXTREMELY deep and diligent on the shape the thinking the thesis and the build of a dynasty-horizon value."* And: *"lets get all of the information we talked about ticketed - and tracked - we must be thourough here this is a hugely important update to DG - in some ways we are about to create version 2.0."*

**The product has no dynasty-horizon value of its own.** Every downstream defect below is a consequence of that one gap.

### 1.1 Reproduced — what our side actually measures

**[VERIFIED — Claude lane, this session, read from code]**

| Step | Locator | Value |
|---|---|---|
| Engine B target | `src/dynasty_genius/models/engine_b_contract.py:15` | `OUTCOME_COLUMN = "avg_ppg_t1_t2"` |
| → projection | `src/dynasty_genius/pvo_assembler.py:382` | `projection_2y = engine_b_resolved["predicted_avg_ppg_t1_t2"]` |
| → DVS | `src/dynasty_genius/pvo_assembler.py:405,407` | `clamp(projection_2y / P90_B × 100, 0, 100)` |
| → xVAR | `src/dynasty_genius/pvo_assembler.py:487` | `(DVS − frozen_replacement_DVS) × Λ_pos` |
| age is an input | `src/dynasty_genius/models/engine_b_contract.py:153-157` | `age`, `aging_curve_value` in `ENGINE_B_BASE_FEATURES` |
| no per-season stream | `src/dynasty_genius/pvo_assembler.py:517` | `projection_1y=None` — hardcoded |

**xVAR is a two-season-forward, age-aware, undiscounted, position-normalised PPG-*rate* surplus.** Corroborated independently by Codex (`codex_age_opportunity_premise_verdict.md` §1.1) and in the design record (`docs/strategies/Dynasty Genius Phase 14 Research Brief.md:46`).

**Consequence — the relayed premise was wrong and must be corrected on the record.** Tower told David xVAR is "roughly current-season," taken on trust from an outside report. **Both independent lanes reject that.** The mismatch is real but it is **horizon length and shape**, not now-vs-future.

### 1.2 Reproduced — the age association is real and measured

**[VERIFIED — Codex lane]** After position fixed effects, age is associated with **+1.73 percentile points of model-minus-market divergence per year of age** (HC3 95% CI **+1.20 to +2.27**, n=338); **+1.74** additionally holding internal model percentile constant; Engine-B-only **+1.70** (n=276). Mean delta **+2.92 pp** at age ≤23 vs **+17.37 pp** at 29+ — a **14.45 pp** gap. One population age SD ≈ 5.8 pp, **below** the product's 10-point noise band.

**Honest reading, and it is neither lane's headline:** the association is stable and decision-material at the age extremes and at RB/TE; it is **not** proof that the market is right and we are wrong. The current artifact **cannot adjudicate which side is correct** — which is precisely why a dynasty-horizon value on our own side is the remedy rather than a re-weighting.

### 1.3 Reproduced — four further construct defects underneath the comparison

1. **[VERIFIED — Codex]** **Rank-population mismatch.** Each side is ranked against a different cohort. Rebasing on the common cohort moves the average delta **10.67 percentile points** and changes **127 of 338** noise-band classifications. *This is larger than the age effect it is being used to investigate.*
2. **[VERIFIED — Codex]** **Two engines, two horizons, pooled.** Engine B is T+1..T+2; Engine A's `y24_ppg` encodes a game-weighted **Years 2–4** average. The divergence pools both into one comparison.
3. **[VERIFIED — Codex]** **Documentation defect.** The `y24` label is described as Year-2+3 while the baseline uses **Y2–Y4**.
4. **[VERIFIED — Tower external research + Codex]** **The market is not a production forecast.** FantasyCalc is a recency-weighted index inferred from ~3.6M completed trades, on an **exponential** curve, with a **bench-spot value already priced in**, calibrated to an average **11.3-team, 26.7-spot** league. We pin 12 teams and send **no roster shape**. A linear xVAR→price conversion is therefore invalid at the top and bottom of the market.

### 1.4 Reproduced — the value is a RATE with no availability term

**[ARGUED, from 1.1]** `avg_ppg_t1_t2` is points **per game**. There is no games-played or availability multiplier anywhere in the chain. **A player expected to miss half a season carries the same value as one who plays every week.** David's order — *"we need to track injuries"* — lands exactly here. This is a **second** gap alongside horizon length, and it is the one injury data fixes.

### 1.5 Reproduced — the scale destroys ordering at the top

**[VERIFIED]** DVS is clamped at 100 (`pvo_assembler.py:407`) **before** xVAR is computed. **[VERIFIED — Studio/Tower]** Twelve players sit tied at exactly 100, spanning the market's #3 to its #137. Ties break rank comparison, which is the entire mechanism of the product's core analysis. The 0–1000 expansion was deferred in May **conditional on trade math**; that condition is now met.

### 1.6 Reproduced — the data floor will not carry a naive thesis

**[VERIFIED — Gemini]** `prospects_with_outcomes_v3.csv`: 874 rows, 2015–2025, only **358** complete non-censored arcs. **Zero** Year-1 outcome columns. **Zero** Year-5+ outcomes (terminates at Year 4). **Zero** NFL snap/route share, **zero** starts/role, **zero** injury history. **Zero player-seasons at age 30+.**

**Consequence, stated plainly:** an age curve fitted on today's data would be fitted on players who **have not yet aged**. If the data will not carry the thesis, **the thesis changes — not the standard.**

### 1.7 Reproduced — surfaces serve stale answers

**[VERIFIED — Studio finding 1, David Ruling B]** Four league-snapshot surfaces are pinned to a **2026-06-23** capture while a daily run exists through **07-24**. Measured cost: **4 of 12** team posture labels are wrong on served data, including the labels used to choose a trade counterparty; **David's own rebuild progress is hidden from him.**

---

## 2. Design — the shape of the program

**One missing quantity, several features.** The epic builds **a dynasty-horizon value whose construction `DG2-S1-02` selects**, and derives from it: dynasty-horizon value, the contention-window lens, the comparison layer, and the production branch of pick value. **Which construction — a per-season stream, a direct multi-horizon family, or another — is open and is decided in Sprint 1, not here.**

### 2.1 The quantity (thesis-gated, NOT settled here)

**One candidate shape, shown to make the terms concrete — NOT the selected construction.** `DG2-S1-02` decides the construction; if it selects the direct multi-horizon family, the terms below are re-expressed and the formula below does not apply. Nothing downstream may treat this as settled:

```
V_i(W) = Σ_{t ∈ W}  A_i,t · S_i,t · E[v_i,t]  −  rent_t
```

- `E[v_i,t]` expected per-season production value (unit TBD — see the scale ticket)
- `S_i,t` survival: probability the player is still *useful* in season t
- `A_i,t` **availability**: expected share of the season actually played — **the injury term (§1.4)**
- `rent_t` roster-spot opportunity cost (Ruling C makes this real via the taxi conversion cost)
- `W` the summation window: **all remaining seasons = dynasty-horizon value; a user-selected sub-range = the contention window** (Ruling F)

**Deliberately absent: a discount rate.** Whether one exists at all is a Sprint-1 decision, not a design assumption — see §2.3.

### 2.2 The horizon-shape question is OPEN and must be resolved with reasons

**David's lean (Ruling J):** year-by-year full-career projection, updating as real data lands. **He explicitly invited crew dissent WITH REASONS.**

**Tower's position (Ruling F, currently written as a HARD DESIGN REQUIREMENT):** a per-season stream, because one construction then yields all three features as summations.

**Claude's position, carried in from research and belonging in the thesis, not a scratchpad — Tower's claim is directionally right and OVER-STATED:**
1. **Identifiability.** A stream asserts T free quantities per player. We fit **one** number for two seasons and `projection_1y` is hardcoded `None`. This is the pick-curve failure at greater scale — 36 free per-slot parameters from 288 noisy observations, monotonicity violated in 15 of 35 adjacent pairs. **Resolution that looks like signal.**
2. **Additivity is an assumption.** A championship is a threshold event, not a sum. Two seasons of 18 PPG and one of 36 are not interchangeable to a contender — and the stream is exactly the form that cannot express that, while being the form mandated to serve the contention lens.
3. **Pick value needs more than the stream.** Ruling A requires draft-and-cut, pick trade value, and the rookie-as-chip option. **None is a summation over a production stream.** So "pick value = the same stream from the debut season" is insufficient **by David's own standard in the same document**. **Codex independently reached the same conclusion** ("Tower's pick-sequencing claim is wrong in blanket form"), from a different direction — market-anchored pick pricing can be researched *independently* of the stream.
4. **Per-season error is never validated if only sums are checked** — and the window lens reads a *sub*-range, so it would be unvalidated exactly where it is used.

**The alternative construction, which `DG2-S1-02` weighs on equal terms:** direct multi-horizon regression (`V(k)` fit against realized k-season outcomes). **Argued** better at validation honesty and sample efficiency; **argued** weaker at pricing a pick and at internal consistency. **Those are positions entering the Sprint-1 decision, not findings — neither construction is recommended here.** One consequence holds whichever wins: if a summed `V(1..2)` disagrees materially with a directly-fit `V(2)`, the decomposition is wrong. That is a falsifier the stream cannot generate for itself, and it should be frozen before any fit.

### 2.3 The discount, decomposed (Sprint 1 deliverable)

A "discount rate" imported from finance silently bundles six distinct things. Decomposed:

| Component | What it is | Where it belongs |
|---|---|---|
| Outcome uncertainty | Variance of the projection | **Nowhere in the mean** — an expectation already integrates it |
| Injury / career end | P(player gone) | **Survival `S_t`** — estimable |
| Role loss / displacement | P(useless while rostered) | Survival of *usefulness* |
| Roster-spot scarcity | Opportunity cost of the slot | **A subtracted rent**, not a rate |
| League / world risk | The league may not exist | The **only** genuine exponential discount, and small |
| Manager time preference | "I want to win in two years" | **The window** (Ruling F), not a rate |

**[ARGUED] Once decomposed, little is left for a rate to do**, and if `S_t → 0` fast enough **the infinite sum converges with no discount rate at all** — meaning Ruling F's "discounted sum across all remaining seasons" may not need a discount parameter to be well-defined.

**The double-counting tension is real and is a Sprint-1 decision:** if the window expresses time preference, a global rate double-counts it. Four options are on the table (window-only · discount-as-uncertainty-only · two explicit parameters · no top-level aggregation). **Not resolved here by assertion.**

**One thing argued hard regardless: the discount must never be FIT.** On ~9 usable cohort-years it would absorb age effects and become unfalsifiable. Set it, declare it, sensitivity-test it.

### 2.4 Architecture principle carried in (Ruling E)

Optimal-lineup determination is **computed once as product logic**; data feeds it; every surface **displays the single answer**. No per-surface reimplementation. This binds starter strength, posture, z-scores, surplus/deficit labels, and partner rankings — changing the basis changes all of them, and that consequence is to be respected, not glossed.

---

## 3. Out of scope (named, not hidden)

1. **Redraft comparison in any form.** REFUSED and CLOSED by Ruling D.1. Not deferred — closed.
2. **The QB-1 validation program (D3-d and successors).** Tracked on a separate track so DG 2.0 cannot swallow it. Its commit gate is unaffected by this epic.
3. **Any UI redesign beyond correctness.** Surfaces must read the freshest capture and display the single computed answer; the *visual* redesign is Studio's own track and routes through the design foundation + framing.
4. **Model promotion.** Nothing in this epic promotes a model. Promotion remains human-gated, pre-registered, per `00`.
5. **Re-opening TEP.** **CLOSED AS VERIFIED** — held values are TEP-off, matching David's league; Kraft is not a TEP artifact. Recorded, no work.
6. **Fitting anything to the market.** The market is a benchmark and a comparison target, never a training input. The `00` KTC/market wall holds throughout.

---

## 4. Falsification seeds — epic-level

Increment-level RED matrices belong to each sprint's own spec. These are the **epic-level falsifiers**, to be frozen by hash before any fit (Sprint 1 deliverable):

| # | Seed | Required behaviour |
|---|---|---|
| **E1** | Stream summed over `W={1,2}` vs a directly-fit `V(2)` | Materially disagree ⇒ the per-season decomposition is **rejected**, not tuned |
| **E2** | Age curve evaluated beyond the observed age support (30+) | Must refuse or widen uncertainty by name — **never extrapolate silently** |
| **E3** | Survival estimated on survivors only | Must be shown unbiased against the full cohort incl. exits, or the tail is flattering to old players — **the same direction as the artifact under investigation** |
| **E4** | Comparison run on non-common cohorts | Must refuse; the 10.67 pp rebasing effect proves this is not cosmetic |
| **E5** | Linear xVAR→market-price conversion | Must fail its own benchmark at the top and bottom of the exponential curve |
| **E6** | Two players, opposite ranks under two windows | Product must show **both without contradicting itself**, each labelled with its window |
| **E7** | Pick priced by production stream alone | Must **refuse to price**, or floor at zero, until draft-and-cut + trade value + chip option are all priced (Ruling A) |
| **E8** | A player on IR / expected to miss games | Value must differ from an every-week player at the same rate — if identical, the availability term is absent |
| **E9** | Any emitted value | `decision_supported=false` recursively; no verdict, no nominated target; calibrated tier labels only where the ratified amendment allows |
| **E10** | Any degraded input (stale capture, failed job, missing source) | Must surface the degradation **by name** — never serve a confident number over a silent failure |

---

## 5. Sequence — sprints and their exit gates

**No sprint may start until the previous sprint's exit gate is closed.** Gates are David's to call; reviewers CLEAR content.

| Sprint | Name | Exit gate |
|---|---|---|
| **0** | Know what we are measuring | **No comparison work proceeds until closed.** Every measurement question answered with a locator; data-asset inventory and injury-obtainability delivered |
| **1** | The thesis | **Adversarial enumerated CLEAR** on the thesis of record, with falsifiers frozen by hash **before** anything is fit. No code. |
| **2** | Data foundation | **Hard adequacy gate** — prove the sample supports what the thesis assumes, per position and per age band. If it does not, **the thesis changes** |
| **3** | Build the quantity | **Win or tie on the frozen primary metric against all three frozen benchmarks** (market curve · current artifact · ≥1 alternative), **naming losses as well as wins**. **If it loses to any benchmark, the current artifact stays in production and the result publishes as a negative finding.** The backlog's Sprint-3 gate is the binding text; this row restates it and must not diverge from it. |
| **4** | The comparison layer | Both modes correct on a common cohort; currency calibration validated on the exponential curve |
| **5** | Picks and surfaces | Ruling A's three-test gate demonstrably priced, or picks stay floored at zero; surfaces read freshest and display the single answer |

**Per-increment loop inside each build sprint** (unchanged cockpit TDD): Claude framing → Codex written challenge → Claude written disposition → Codex CLEAR → **David authorizes RED** → Codex authors RED (red on `main`) → Claude GREEN + self-probe → Codex independent CLEAR → **David authorizes commit/push**. CI is the merge gate, never local-green.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **The stream fabricates resolution the data cannot support** | E1 + the Sprint-2 adequacy gate are *gates before adoption*, not findings after |
| **A fitted discount absorbs the age effect and hides it** | The discount is set and declared, never fit; sensitivity-tested across a declared range |
| **Survivorship bias flatters old players — the same direction as the artifact** | E3 makes it an explicit falsifier rather than a footnote |
| **Fixing the comparison "fixes" only one consumer** | The consumer audit (S0-04) names which consumer each fix repairs, before any fix |
| **Changing starter-strength basis silently changes every downstream label** | Ruling E's single-computation principle + an explicit blast-radius ticket |
| **Scale expansion breaks trade math** | The 0–1000 expansion was deferred conditional on trade math; the condition is now met, and the ticket carries the trade-math regression as its gate |
| **DG 2.0 swallows the separate track** | The separate track has its own IDs and its own gates and is reported independently |
| **Silent failure** | See the cross-cutting requirement below — every ticket declares its failure-visibility |

### The silent-failure question — my recommendation

Tower named five instances today of the system degrading without telling David: idle-vs-broken jobs indistinguishable · a backup that can fail closed unnoticed · a deferred scale limitation coming due silently · a confidence interval that reports certainty on failure · stale surfaces served with no staleness signal.

**[ARGUED] Recommend BOTH, not one:**
1. **A cross-cutting requirement on every ticket in this epic and the separate track** — each ticket must state *how this fails loudly*. Making it only an epic would let five subsystems ship without it while the epic queues.
2. **Plus one thin epic** owning the shared surfacing mechanism (a health/staleness signal surfaces can read), because a purely cross-cutting requirement has no owner and nothing to build against.

Making it *only* an epic serialises unrelated work behind one thread; making it *only* cross-cutting means nobody builds the mechanism. **David's call; this is a recommendation with its reason.**

---

## 7. What this spec does NOT prove

- It does not prove the age artifact means the market is right. **[UNKNOWN]** — the current artifact cannot adjudicate, and Sprint 0 exists to make the question answerable.
- It does not prove a per-season stream is achievable on our data. **[UNKNOWN]** — E1 and the Sprint-2 adequacy gate are designed to find out, and a negative answer is a legitimate result that changes the thesis.
- It does not establish any QB-1 finding. **H2 QB rushing production remains UNDER TEST**; the study has not run and there is no result.
