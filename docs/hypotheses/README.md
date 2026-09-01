# Hypothesis Register

**These are beliefs, not laws.** Everything here is a claim about football that we intend to test
against what actually happened, keep if it survives, and kill if it does not. A belief that has been
repeated for months and never measured is not knowledge — it is inherited confidence.

This register exists because the governance documents accumulated real football insight and then
hardened into doctrine. The insight is worth keeping. The hardening is not. **David, 2026-09-01:**
*"I do not want to get into the same cycle of being lazy about something and losing creativity,
brainstorming, and critical thinking... note the things we believe to be true... we should continue
to make more hypotheses."*

## Status vocabulary

| status | meaning |
|---|---|
| `UNTESTED` | believed, never measured here |
| `SUPPORTED` | measured, survived; note the test and its limits |
| `REFUTED` | measured, failed. Keep the entry — a dead hypothesis stops others re-proposing it |
| `PARTIAL` | true in a narrower form than originally stated |
| `UNTESTABLE_TODAY` | needs data or a scoreboard we do not have |

A test result is only as good as its design. Every entry records **how** it was tested, so a weak
test can be re-run rather than mistaken for a settled answer.

---

## Tested 2026-09-01

### H1 — Usage/role signals lead; box-score production lags · `REFUTED` (as an annual predictor)
Inherited from the constitution v1.1.0. **Test:** Spearman of `ppg_t` vs `snap_share` against
`avg_ppg_t1_t2`, n=2,055 player-seasons.

    pos    ppg_t    snap_share
    QB     0.672    0.467
    RB     0.742    0.672
    WR     0.772    0.687
    TE     0.712    0.571

Production wins at every position. Incremental test (5-fold CV R², ppg+age vs +snap_share):
QB +0.013, RB −0.005, WR −0.000, TE −0.004 — **usage adds essentially nothing on top of production.**

⚠ **Limit — this does not fully refute the constitution's actual claim.** Its wording concerns
*in-season responsiveness* (how fast a daily estimate should move), not annual prediction. That
narrower claim needs weekly data and is still `UNTESTED`. What IS refuted is the strong reading, and
the strong reading is what would justify re-weighting the model toward usage.

### H2 — Dual-threat QBs are materially more valuable · `SUPPORTED`, strongly
David, 2026-09-01. **Test:** predicting next-season QB ppg, 5-fold CV R², n=183 QB seasons.

    passing production only            0.176
    + binary dual-threat flag          0.256      <- current model
    + continuous rushing yards         0.221
    + both                             0.245

Rushing lifts predictive power ~45%. Rushing yards correlate 0.629 with QB fantasy ppg.
It is worth 3.9% of the current QB model's weight — **the open question is whether that is too low.**

### H3 — The binary 400-yard flag discards most of the rushing signal · `REFUTED`
Proposed by Claude, 2026-09-01, and killed by H2's own test. The binary BEATS continuous rushing
(0.256 vs 0.221) and adding continuous on top HURTS (0.245). The threshold captures a real regime
effect. **Recorded because it was a confident, plausible, wrong claim** — Lamar Jackson and Baker
Mayfield really are more alike than their rushing totals suggest, for predicting next-season points.
Residual signal does exist within the flagged group (rho 0.328, n=38), so a refinement may still pay,
but not by replacing the flag.

### H4 — Durability is a persistent trait · `PARTIAL` — real but far weaker than the market prices
**Test:** games_t vs games_t+1, n=1,733 consecutive pairs. Overall rho 0.371
(QB 0.492, TE 0.397, RB 0.326, WR 0.324).

    missed significant time (games_t<8)  ->  10.1 games the next season
    stayed healthy (games_t>=8)          ->  13.1 games the next season

**The correct penalty for an injury season is roughly 23% fewer games.** The system currently applies
a 100% penalty — `ENGINE_B_MIN_GAMES_T=8` refuses a score entirely. An infinite discount for a 23%
effect. This is the quantified core of DG-128 and the strongest argument that the gate is wrong.

---

## Untested beliefs, inherited from the governance documents

| # | belief | source | how to test |
|---|---|---|---|
| H5 | Draft capital is the strongest single rookie predictor | constitution | join contracts `draft_overall` to rookie outcomes; measure lift over production alone |
| H6 | YPRR predicts WR/TE value beyond raw production | constitution | incremental CV R² over ppg+age. Already a model input at 8.4% (WR) — measure its actual lift |
| H7 | Breakout age / dominator rating predicts WR success | constitution | needs college stats + team totals + birth dates; confirm all three exist first |
| H8 | Age cliffs: RB 26, WR 28, TE 30, QB 33 | constitution | test for a discontinuity at each age vs a smooth curve. Constitution says display-only until validated |
| H9 | Picks appreciate as rookie drafts approach; veterans depreciate | constitution | needs market history over time — `fc_snapshots.db` may support this |
| H10 | RAS is a downside/risk signal, not an upside boost | constitution | no RAS data on disk today; acquisition required |
| H11 | Bias to stability beats responsiveness | David-ratified 2026-06-27 | simulate a responsive vs stable policy against realized outcomes |
| H12 | Position-varying responsiveness (RB fastest → QB slowest) | constitution | weekly data; measure optimal update half-life per position |

## New hypotheses — 2026-09-01

| # | hypothesis | why it might pay | testable today? |
|---|---|---|---|
| H13 | **The market over-discounts injured veterans.** H4 says the true penalty is ~23% fewer games; dynasty markets punish far harder | Directly monetizable. This is the Garrett Wilson trade, generalized | needs market history joined to outcomes |
| H14 | **Draft capital decays with evidence.** It should dominate years 1–2 and fall toward zero by year 4 once real production exists | Reconciles "draft capital matters" with "production is core" — as a time-varying weight, not a flat term. Also the principled way to give the DG-128 taper a prior without over-weighting veterans | yes, once contracts data joins |
| H15 | **Touchdown rate mean-reverts and the market prices it as skill.** High-TD seasons relative to yardage are sell-high candidates | Classic regression-to-mean edge; needs no new data | yes, weekly data on hand |
| H16 | **Superflex amplifies the rushing premium** beyond what raw points imply, because QB scarcity raises the marginal QB point | League-specific edge nobody else in the league prices | yes, with league scoring + roster rules |
| H17 | **TE breakout is a step function, not a curve** (the "year 3 TE leap") | If real, changes hold/sell timing for every young TE | yes |
| H18 | **Career aggregation beats season windows.** One row per player-career with explicit availability outperforms compartmentalized seasons | David's core 2026-09-01 thesis; H4 is the first supporting evidence | yes — build the career view and compare |

---

## The loop

A hypothesis register is worthless without a scoreboard. The practice is:

1. **State** the belief as a falsifiable claim, with the number that would kill it.
2. **Test** against realized outcomes — not against a holdout of the training data, which only proves
   the model learned its own training set.
3. **Record** the result here, including refutations, and especially our own.
4. **Promote** survivors into the model as fitted weights — never as hand-set multipliers.
5. **Re-test** as seasons accumulate. A hypothesis that held in 2023 may not hold now.

**Step 2 does not exist yet.** Nothing in this product has ever compared a prediction to what a player
actually did. `model_forward_capture.db` records ~12,226 predictions daily and market snapshots are
stored, so the raw material is present — but nothing joins prediction, market, and outcome. Until it
does, every entry above is measured against history rather than against our own forecasts, and
"continuously get better" has no instrument.

**Building that join is the highest-leverage work in the product.** It converts this register from a
list of opinions into a system that learns.
