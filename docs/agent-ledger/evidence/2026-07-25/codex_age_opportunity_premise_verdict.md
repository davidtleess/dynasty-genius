# Adversarial verdict: does Dynasty Genius systematically report AGE as OPPORTUNITY?

**Date:** 2026-07-25
**Lane:** Codex, independent research and verification
**Authority:** research/verification only; no implementation, fixes, commits, backup run, or wire action
**Binding context read first:** `/tmp/tower_david_rulings_2026-07-25.md`

## Bottom line

**REJECT TOWER'S CAUSAL PREMISE AS STATED.**

The production divergence is **not** a comparison of “roughly current-season” xVAR against a verified discounted-future-value market measure.

- **VERIFIED:** Engine B xVAR begins with a forecast of the average PPG in **T+1 and T+2**, then converts that forecast into a clamped, position-normalized rate score and finally into WR-equivalent points above a frozen replacement baseline.
- **VERIFIED:** Engine A xVAR begins with `y24_ppg`, whose source columns and values encode a game-weighted average over **Years 2–4**, then applies its own position normalization and replacement/scarcity constants.
- **VERIFIED:** the current full-universe divergence therefore compares a **hybrid of two short/medium future production-rate constructs** against FantasyCalc's **observed dynasty trade-price index**, within position.
- **REFUTED:** FantasyCalc is not shown by its source or our ingestion to be a discounted production stream. It is a recency-weighted market price inferred from actual dynasty trades.

There **is** a real age-related construct gap. It is stable, not just an 8-of-14 anecdote:

- on 2026-07-25, age is associated with **+1.73 percentile points of model-minus-market divergence per year** after position fixed effects (HC3 95% CI **+1.20 to +2.27 pp/year**, `n=338`);
- the estimate is **+1.74 pp/year** after additionally holding internal model percentile constant (95% CI **+1.19 to +2.28**);
- Engine-B-only is **+1.70 pp/year** with position controls (95% CI **+1.09 to +2.31**, `n=276`);
- the mean delta is **+2.92 pp** for age 23 or younger and **+17.37 pp** for age 29+, a **14.45 pp** gap.

That is decision-material in the age extremes and especially at RB/TE, although one population age standard deviation is only about **5.8 pp**, below the product's 10-point noise band. It is neither negligible nor proof of a defect.

**The evidence supports this narrower statement:** our short/medium-horizon production rank and the dynasty trade market disagree increasingly with age. The current artifact cannot adjudicate which side is right. Calling every positive old-player delta “opportunity” would be overstated; calling the association itself imaginary would also be wrong.

**TOWER'S PICK-SEQUENCING CLAIM IS WRONG IN BLANKET FORM.** Market-anchored pick pricing can and should be researched independently of a dynasty production stream. The stream is relevant to the intrinsic keep/player-production branch, but it cannot by itself value all three option branches David required.

## Evidence vocabulary

- **VERIFIED** — reproduced from code, a stored artifact, a deterministic calculation, or a named primary source.
- **ARGUED** — an analytical conclusion whose assumptions are stated.
- **UNKNOWN** — evidence available in this lane cannot settle it.

## 1. What our side actually measures

### 1.1 Engine B

**VERIFIED — not current-season, not a career value, not a discounted stream.**

The lineage is:

1. `src/dynasty_genius/models/engine_b_contract.py:1-5,15-16` defines the outcome as the two-year average PPG over T+1 and T+2, `avg_ppg_t1_t2`.
2. `src/dynasty_genius/pvo_assembler.py:378-410` maps `predicted_avg_ppg_t1_t2` to `projection_2y` and then computes:

   `DVS = clamp(projection_2y / position_P90 * 100, 0, 100)`.

3. `src/dynasty_genius/pvo_assembler.py:471-490` computes:

   `xVAR = (DVS - frozen_position_replacement_DVS) * position_lambda`.

4. The P90, replacement, and lambda constants are frozen in `src/dynasty_genius/models/engine_b_contract.py:19-89`.
5. Age and a fitted aging-curve value are explicit Engine B inputs: `src/dynasty_genius/models/engine_b_contract.py:126-144,153-170`.

**VERIFIED characterization:** xVAR is a position-adjusted **two-season-forward expected PPG-rate surplus proxy**. It is not a season total because it has no games/availability multiplier. It is not a multi-season sum because T+1 and T+2 are averaged into one rate. It has no time discount and no seasons after T+2.

### 1.2 Engine A

**VERIFIED — a different future horizon, so the shipped xVAR population is hybrid.**

`src/dynasty_genius/scoring/engine_a.py:1-11,91-124` predicts `y24_ppg` from pick, round, and age, then normalizes that prediction into DVS. The baseline contract contains Y2, Y3, and Y4 games/points (`src/dynasty_genius/models/engine_a_contract.py:8-14`). The repository's target construction states that `y24_ppg` is the game-weighted average of Y2–Y4 (`scripts/build_head_b_targets.py:14-25`), and a direct row-level check of `app/data/training/prospects_with_outcomes.csv` reproduces it: for Jameis Winston, `(256.10 + 201.66 + 195.78) / (16 + 13 + 11) = 16.3385`, stored as `16.338`.

**VERIFIED documentation defect:** `scripts/build_draft_pick_value_curve.py:30-31` and `src/dynasty_genius/trade_lab/draft_pick_valuation.py:39-44` call this Year-2+3 PPG, while the actual baseline has and uses Y2–Y4. That inconsistency does not turn the measure into current-season value, but it should prevent casual horizon claims from relying on the `y24` label alone.

Engine A DVS becomes xVAR through the same assembler formula, but with Engine-A-specific P90, replacement, and lambda constants (`src/dynasty_genius/pvo_assembler.py:471-490`; constants at `engine_b_contract.py:54-89`).

The 2026-07-25 eligible divergence population contains **276 Engine B rows and 62 Engine A rows**. Thus the thing colloquially called “xVAR” in this artifact does not have one uniform forecast horizon.

### 1.3 `dynasty_value_score`

**VERIFIED:** despite its name, DVS is not an independently trained dynasty-price or career-value target. It is the route-specific future PPG-rate prediction divided by a position P90 and clamped to `[0,100]`:

- Engine B: `src/dynasty_genius/pvo_assembler.py:389-410`;
- Engine A: `src/dynasty_genius/scoring/engine_a.py:106-124`.

**VERIFIED:** the current universe divergence does not read DVS directly. It builds within-position model cohorts from `valuation.xvar` and ranks xVAR (`src/dynasty_genius/universe_market_divergence.py:37-50,207-222`). DVS is nevertheless indirectly load-bearing because xVAR is algebraically derived from it.

**ARGUED:** the DVS clamp can erase production headroom at the elite end and therefore alter rank ties, but this analysis does not establish that it causes the age slope. That would require an unclamped counterfactual.

### 1.4 A sibling basis inconsistency

**VERIFIED:** not every shipped divergence caller uses the universe artifact's xVAR basis.

- The current full-universe artifact and player-detail route use `universe_market_divergence_latest.json`: `scripts/run_market_divergence_refresh.py:438-555` and `app/api/routes/players.py:35-37,150-152,200-235,262-276`.
- The older `compute_divergence` implementation ranks `projection_2y` directly, not xVAR: `src/dynasty_genius/services/market_overlay_service.py:102-180`.
- That older wrapper is still reached by the trade analyzer and rookie scoring routes: `app/services/trade_analyzer.py:236-245` and `app/api/routes/rookies.py:60-85`.

**ARGUED:** the headline artifact audited here is xVAR-based, but “our divergence” is not a single construct across all product paths. Any foundational plan must name which consumer it repairs and avoid assuming a single replacement will automatically reconcile the sibling path.

## 2. What the FantasyCalc side actually measures

### 2.1 Settings we genuinely pin

**VERIFIED:** both the cache adapter and forward-capture driver call:

`isDynasty=true&numQbs=2&numTeams=12&ppr=1`

Locators:

- `src/dynasty_genius/adapters/fantasycalc_adapter.py:20-23`;
- `src/dynasty_genius/capture/fc_forward_capture_driver.py:30-32`.

The deterministic settings hash is `e27351d720e9fcf0`, and the current refresh report records that same value at `app/data/valuation_runtime/market_divergence_refresh_latest_report.json:17`.

Therefore:

- **VERIFIED:** dynasty mode is explicitly on.
- **VERIFIED:** two-QB is explicitly requested; this is our Superflex-market proxy.
- **VERIFIED:** 12 teams and full PPR are explicitly requested.
- **REFUTED:** roster size is pinned. `numTeams=12` is league size, not roster size; the request has no roster-size parameter.
- **REFUTED:** TE premium is explicitly pinned. No TE-premium parameter appears in either request.
- **UNKNOWN:** whether omission of a TE-premium API parameter is guaranteed by FantasyCalc's API contract to mean TEP-off. The public web UI currently presents TEP as a setting, but no local or public API schema reviewed here establishes the omitted-parameter default.

### 2.2 Price type stored

**VERIFIED:** we store FantasyCalc's dynasty `value`, not its redraft or combined fields.

- `isDynasty=true` is explicit.
- The adapter removes `combinedValue`, `redraftValue`, and `redraftDynastyValueDifference` before caching: `src/dynasty_genius/adapters/fantasycalc_adapter.py:28-35,155-170`.
- Forward capture maps only `row["value"]` plus rank/trend/volatility metadata: `src/dynasty_genius/capture/fc_forward_capture_driver.py:44-90`.

FantasyCalc describes its dynasty rankings as being generated from real dynasty trades, with recency weighting and setting-specific regression/adjustment. Primary sources:

- <https://fantasycalc.com/frequently-asked-questions>
- <https://www.fantasycalc.com/dynasty-rankings>
- <https://fantasycalc.com/trade-value-chart>

**VERIFIED characterization:** our stored value is a **dynasty market trade-price index** under the four explicit query settings. It is not a stored redraft price and not a stored redraft/dynasty blend.

**REFUTED:** the source establishes that the value is a discounted future-production present value. Managers may implicitly price expected future production, liquidity, scarcity, risk, contention preference, and sentiment, but FantasyCalc's published construction is trade-derived, not a discounted cash-flow analogue.

**UNKNOWN:** the effective roster-size assumption embodied by FantasyCalc's market and waiver adjustment for this request. Its FAQ discusses an average dynasty roster and waiver-player adjustment; that is not an explicit pin to David's roster.

## 3. Quantifying the age artifact

### 3.1 Population and method

**VERIFIED:** the latest committed artifact is `app/data/valuation/universe_market_divergence_latest.json`, captured `2026-07-25T13:40:00.197837+00:00` from the 2026-07-25 market snapshot.

- total Sleeper-universe rows: **12,202**;
- rows with a model xVAR: **468**;
- rows with a market overlay: **399**;
- rows with both percentiles and a delta: **338**.

The analysis grain is one comparable player. Delta is `within-position xVAR percentile - within-position FantasyCalc-value percentile`. I used ordinary least squares with HC3 heteroskedasticity-robust confidence intervals. Position fixed effects control for mean position differences; adding model percentile asks whether age still predicts a lower market rank at the same internal rank. Engine-B-only estimates remove the Engine A/B horizon mixture.

The deterministic read-only reproducer is `/tmp/codex_age_divergence_analysis.py`. Inputs are the current JSON and `app/data/market_divergence_history.db`; it writes nothing.

### 3.2 Full-population effect sizes

| Snapshot | Sample | Pearson age/delta | Position-adjusted age slope | Position + model-percentile slope | 1 age-SD effect |
|---|---:|---:|---:|---:|---:|
| 2026-07-22 | 340 | `r=0.260` | **+1.870 pp/year** `[+1.307,+2.432]` | **+1.880** `[+1.309,+2.452]` | +6.25 pp |
| 2026-07-25 | 338 | `r=0.222` | **+1.732 pp/year** `[+1.199,+2.265]` | **+1.738** `[+1.195,+2.281]` | +5.77 pp |

Brackets are HC3 95% confidence intervals.

**VERIFIED:** the association is not just composition by position and is not removed by conditioning on our own percentile. It is stable over these snapshots.

### 3.3 Engine-B-only decomposition

On 2026-07-25, Engine B alone (`n=276`) gives:

- delta on age + position: **+1.703 pp/year**, 95% CI `[+1.095,+2.311]`;
- delta on age + position + model percentile: **+1.735 pp/year**, CI `[+1.107,+2.363]`;
- internal model percentile on age + position: **+0.326 pp/year**, CI `[-0.515,+1.167]`, `p=.446`;
- market percentile on age + position: **-1.377 pp/year**, CI `[-2.366,-0.388]`, `p=.0065`.

The 2026-07-22 decomposition is nearly identical:

- controlled delta: **+1.846 pp/year**, or **+1.880** with model percentile;
- model percentile: **+0.310 pp/year**, CI includes zero;
- market percentile: **-1.536 pp/year**, CI excludes zero.

**VERIFIED interpretation of the arithmetic, not of truth:** among Engine B players, the age association arises mainly because the market ranks older players lower at comparable internal two-year rank. The internal model does not measurably rank older players higher after position control.

**ARGUED:** that pattern is exactly what rational dynasty longevity pricing would look like when compared with a two-year rate forecast. It is also what an excessive market age discount would look like. This cross-section cannot distinguish those hypotheses.

### 3.4 Within-position effects

Engine-B-only 2026-07-25 slopes:

| Position | n | Divergence change per age year | HC3 95% CI |
|---|---:|---:|---:|
| QB | 36 | +0.815 pp | `[-0.092,+1.723]` |
| RB | 78 | **+2.534 pp** | `[+1.131,+3.937]` |
| TE | 52 | **+2.804 pp** | `[+1.184,+4.424]` |
| WR | 110 | **+1.293 pp** | `[+0.167,+2.418]` |

**VERIFIED:** the artifact is not only a TE-composition fingerprint. It survives within RB, TE, and WR. The Engine-B QB estimate is smaller and does not exclude zero at 95%.

### 3.5 Tail claim and practical materiality

**VERIFIED:** the reported 8-of-14 result reproduces on the 2026-07-22 immutable history:

- 49 of 340 comparable players were age 29+ (14.4%);
- 8 of the top 14 positive deltas were age 29+;
- one-sided hypergeometric probability under random selection: `0.000165`.

That probability is descriptive, unadjusted, and tied to an arbitrary top-14/age-29 cutoff. Tail membership is not stable: the age-29+ count in the top 14 was **8, 4, 7, 7** on July 22–25 respectively.

The broad effect is more useful:

| Age bin, 2026-07-25 | n | Mean model-minus-market delta |
|---|---:|---:|
| 23 or younger | 130 | +2.92 pp |
| 24–25 | 77 | +9.21 pp |
| 26–28 | 84 | +9.96 pp |
| 29+ | 47 | +17.37 pp |

**ARGUED materiality:** a one-year difference is small; a six-year difference implies about 10.4 percentile points and crosses the current noise-band scale. The extreme old/young mean gap is 14.45 points. This is a material tail/roster-construction issue, not a dominant explanation of every player's divergence.

**REFUTED:** the market-preferred tail is literally “uniformly young.” On 2026-07-22 its bottom 14 included age-29 Joe Burrow; on 2026-07-25 it included Burrow and age-37 Kirk Cousins. “Overwhelmingly younger” is supportable; “uniformly” is not.

## 4. The prior within-position control

**VERIFIED:** the current artifact already performs the requested within-position control by construction:

- per-position market cohorts: `src/dynasty_genius/universe_market_divergence.py:22-34`;
- per-position xVAR cohorts: `src/dynasty_genius/universe_market_divergence.py:37-50`;
- both percentiles and their delta: `src/dynasty_genius/universe_market_divergence.py:207-222`.

**VERIFIED:** independently fitting age effects within each position and with position fixed effects leaves a material positive association, as shown above. Therefore, within-position normalization does not remove this age pattern.

**UNKNOWN:** whether this is literally the same “005 artifact” under the same frozen data, population, and statistic. I found no identifiable 005 analysis packet with enough provenance to reproduce that historical claim. I can verify the stated condition—age association after within-position control—not equivalence to an unavailable prior analysis.

## 5. Attack on the mandated per-season discounted stream

David's per-season/explicit-discount ruling is binding. The following identifies what the construction must not be allowed to claim.

### 5.1 What a deterministic stream makes hard or false

**ARGUED:**

1. **PPG is a rate, not annual value.** A per-season PPG vector cannot be summed without games played, lineup availability, role, and survival/career-exit probabilities.
2. **A mean stream discards option value.** Picks and young players have skewed, state-contingent outcomes. The value of observing information and then starting, trading, taxiing, or cutting is not the discounted sum of unconditional means.
3. **Replacement and scarcity are time- and roster-dependent.** A fixed positional replacement baseline is not automatically the marginal lineup value in each future season.
4. **Market price includes non-production terms.** Liquidity, scarcity, manager beliefs, and trade-chip optionality need not equal production present value.
5. **Long-horizon precision can be cosmetic.** Current production targets collapse T+1/T+2 or Y2–Y4 into one average. Splitting them into many precise-looking annual values is not identified by the current production target.
6. **A terminal rule is unavoidable.** Any finite forecast horizon either assigns an explicit terminal value or silently treats later seasons as zero.

### 5.2 Where double counting occurs

**ARGUED:** forecast mechanics should carry age decline, injury/availability, role loss, and survival if those are modeled. A second “risk-adjusted discount rate” that also compensates for those same risks double-counts them. A pure time-preference or league/world-risk discount does not.

A user-selected contention window is not inherently double counting—it can simply select seasons. It becomes double counting when window weights already encode urgency/time preference and the same preference is also applied through the discount rate.

The contract should therefore name separately:

- production conditional on playing/role;
- games/availability/survival;
- uncertainty distribution and covariance over seasons;
- replacement/lineup marginal utility;
- time-preference discount;
- user window weights.

One opaque “dynasty discount” cannot honestly stand in for all six.

### 5.3 A construction that serves the three uses better

**ARGUED:** use a **per-season distribution/state vector as the common primitive**, not a single deterministic discounted stream as the common answer.

- **Dynasty intrinsic production value:** discounted expected per-season marginal lineup surplus, with explicit survival/availability and an explicit terminal rule.
- **Contention view:** selected-season lineup marginal utility under the user's window; display the discount policy separately.
- **Pick value:** an option envelope over the branches David required—keep the eventual player, trade the pick, draft-and-cut, and trade the rookie after information arrives.

This honors the per-season requirement while admitting that the three uses need different aggregators. It also preserves uncertainty and the state-contingent maximum. A scalar discounted sum can be derived for a named use, but it should not be treated as the primitive.

**VERIFIED contradiction with a one-stream claim:** Ruling A requires draft-and-cut, pick trade value, and rookie trade-chip optionality. Those market/decision branches are not produced by starting a player's production stream at debut.

## 6. Attack on Tower's pick sequencing

**VERDICT: TOWER'S “PICK VALUATION IS PREMATURE UNTIL A DYNASTY STREAM EXISTS” ADVICE IS OVERSTATED AND, AS A BLANKET SEQUENCE, WRONG.**

### What can proceed without the stream

**VERIFIED:** a FantasyCalc market lane already exists independently of intrinsic xVAR. `src/dynasty_genius/trade_lab/market_reconciler.py:171-215` resolves:

- current-year exact picks to `DP_{round-1}_{slot-1}`;
- generic future picks to `FP_{year}_{round}`.

Current early/mid/late buckets are explicitly unresolved at lines 200-206, but that is a mapping limitation—not dependence on a dynasty production stream.

Therefore:

- **ARGUED:** current exact-slot market pricing can proceed as a market-price track.
- **ARGUED:** projected finish converted into a transparent early/mid/late market-price range can proceed as a market scenario track.
- **ARGUED:** neither should be relabeled as intrinsic production value.

**VERIFIED:** the current realized-outcome curve is explicitly market-free and model-blind (`src/dynasty_genius/trade_lab/draft_pick_valuation.py:1-8`). It maps historical `y24_ppg` outcomes through DVS/xVAR (`:39-48`) and builds slot expectations (`:103-190`).

- **ARGUED:** that track can proceed as a realized-production benchmark.
- **ARGUED:** it cannot satisfy David's complete pick-value definition because it omits market liquidity and the state-contingent draft/cut/flip options, despite its zero floor.

### What genuinely depends on the stream

**ARGUED:** the intrinsic “keep the drafted player for future lineup production” branch benefits from a validated dynasty-horizon construction. Even then, the stream does not finish the other branches.

The honest sequence is therefore parallel, not blocked:

1. market-price track and projected-finish market ranges;
2. realized-outcome benchmark;
3. dynasty-horizon work for the intrinsic keep branch;
4. only after all branches exist, a governed option envelope that does not pretend unlike units are interchangeable.

“Premature” is justified only if someone proposes calling one partial track the unified intrinsic dynasty price. It is not justified for the three already-authorized research/valuation tracks.

## Recommendation to Tower

1. **Withdraw the statement that xVAR is roughly current-season.** It is false.
2. **Do not present “AGE as OPPORTUNITY” as a proven defect or root cause.** Present a verified age-related disagreement between a two-/three-season production-rate rank and a dynasty trade-price rank.
3. **Do not describe FantasyCalc as a verified discounted future-value stream.** It is a dynasty trade-derived market index.
4. **Keep the foundational dynasty-horizon research on its own merits**—product coherence, contention framing, and intrinsic-value needs—not as a statistically proven repair for this artifact.
5. **Do not gate all pick work behind that build.** Run the market and realized-outcome tracks independently; reserve the stream for the intrinsic branch and require a later option-aware synthesis.
6. Before any surface wording says “opportunity,” require forward validation: predeclare an age-stratified test of whether positive divergence predicts future realized production surplus, future market appreciation, or both. Without a named outcome, “opportunity” is not falsifiable.

## Limits and unknowns

- This is cross-sectional association, not causal proof or validation of either valuation lane.
- Only 338 current rows have both model and market ranks; conclusions apply to that modeled/market-covered population, not all 12,202 universe rows.
- The exact 005 packet was not locatable, so historical identity is unknown.
- FantasyCalc's omitted TE-premium default and effective roster-size assumption are unknown.
- No counterfactual career-value model exists here, so this analysis cannot measure how much of the age slope a longer horizon would remove.
- No user-decision or realized-outcome study was run. The analysis establishes construct mismatch and effect size, not which old players are buys.

## Reproducibility inventory

- Binding rulings: `/tmp/tower_david_rulings_2026-07-25.md`
- Read-only analysis: `/tmp/codex_age_divergence_analysis.py`
- Current divergence artifact: `app/data/valuation/universe_market_divergence_latest.json`
- Immutable daily history: `app/data/market_divergence_history.db`
- Refresh lineage: `app/data/valuation_runtime/market_divergence_refresh_latest_report.json`
- Engine B contract: `src/dynasty_genius/models/engine_b_contract.py`
- PVO/DVS/xVAR construction: `src/dynasty_genius/pvo_assembler.py`
- Engine A construction: `src/dynasty_genius/scoring/engine_a.py`
- Current divergence: `src/dynasty_genius/universe_market_divergence.py`
- FantasyCalc adapter/capture: `src/dynasty_genius/adapters/fantasycalc_adapter.py`, `src/dynasty_genius/capture/fc_forward_capture_driver.py`
- Sibling divergence: `src/dynasty_genius/services/market_overlay_service.py`
- Pick market lane: `src/dynasty_genius/trade_lab/market_reconciler.py`
- Realized pick curve: `src/dynasty_genius/trade_lab/draft_pick_valuation.py`
