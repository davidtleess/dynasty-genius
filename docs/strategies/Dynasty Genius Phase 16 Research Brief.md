# Dynasty Genius Phase 16 Research Brief
*Engine A Rookie Signal Upgrade*

Date: 2026-05-17
Status: DRAFT — for research agent input
Prepared by: Claude

---

## System Context

Dynasty Genius is a machine learning asset management system for a 12-team Superflex Full PPR dynasty league. The system scores players using two engines:

- **Engine A** (prospects): `pick`, `round`, `age` → Ridge regression → peak PPG projection. P90 constants: QB 16.7 / RB 14.6 / WR 12.7 / TE 9.1. Output normalized to DVS 0–100. Fires only when all three inputs present.
- **Engine B** (veterans): NFL usage signals → 2-year average PPG projection. ACTIVE_B for QB/RB/WR/TE (Phase 13.3).

**What Phase 15 delivered:**
- **xVAR**: `(DVS - ENGINE_A_REPLACEMENT_DVS[pos]) × XVAR_LAMBDA_ENGINE_A[pos]` — WR-equivalent points above replacement. Engine A replacement anchors: QB=77.3, RB=49.9, WR=69.2, TE=98.8. All 2026 TEs negative xVAR (correct Superflex behavior).
- **Rookie Board**: sorted by `xvar_class_rank` with DVS rank + Δ visible; live draft-state banner; available-now panel.
- **2026 prospect_cards**: 80 picks scored (74 ACTIVE, 6 PRE_MODEL age-data blockers).

**What Phase 16 must address:**
- 6 2026 picks are unscored because `age=None` in `prospect_identity_2026.json`.
- Engine A produces clusters of identically-ranked prospects within a round because it has no within-tier separation signal beyond pick number.
- The Phase 13 draft-capital bake-off validated harness machinery but never ran against a real historical cohort.

**Locked constraints that must not change:**
- Market data (KTC, FantasyCalc, ADP) is overlay-only. It cannot enter the DVS formula, Engine A feature set, or Engine B feature set under any circumstances.
- `decision_supported` remains False on all surfaces.
- `NOISE_BAND = 0.10` locked until mid-July 2026.
- `ENGINE_B_P90_PPG` constants frozen at May 2026 values.
- xVAR is display/decision currency only — it is not a model input and must not enter training data.
- No PFF grades as model features — permanently banned.

---

## Engine A Production State

Current scoring function (see `src/dynasty_genius/scoring/engine_a.py`):

```python
X = np.array([[pick, round_, age]])
y24_ppg = model.predict(X)[0]
dynasty_value_score = clamp(y24_ppg / P90[pos] * 100, 0, 100)
```

Current `POSITION_FEATURE_MATRIX` (from `engine_a_contract.py`) — defines what is **contractually allowed** as a model input, but not yet in production scoring:

| Position | Currently in production | Allowed in contract but not yet scoring |
|---|---|---|
| WR | pick, round, age | dominator_rating, receiving_yards_share |
| RB | pick, round, age | dominator_rating |
| TE | pick, round, age | dominator_rating, receiving_yards_share |
| QB | pick, round, age | completion_pct, yards_per_attempt, td_int_ratio, sack_rate, all_purpose_yards, passing_yards_share, ppa, wepa, rushing_yards, rushing_tds |

**Model grade:** WR/RB/TE = PROSPECT_C; QB = PROSPECT_D (negative R²).

**Known weaknesses exposed by the 2026 draft:**
- Within-tier separation: Caleb Douglas (xVAR#19), Zachariah Branch (xVAR#20), Ja'Kobi Lane (xVAR#21) have essentially identical DVS scores because they have similar pick numbers and ages. Engine A cannot separate them.
- Late-round RB breakouts (Kaelon Black, Jonah Coleman) were visible only in xVAR delta, not in DVS rank — meaning draft-capital rank was not capturing their separation from the pack. The xVAR delta (↑19, ↑23) is display evidence, not model evidence.
- 6 picks remain unscored due to `age=None`.

---

## Research Question 1: Age-Data Blockers — Source and Validation

**The problem:**

6 verified 2026 NFL draftees have `birth_date=None` and `age=None` in `resources/prospect_identity_2026.json`. Engine A requires `pick + round + age` and produces no score without all three.

| Player | Position | Pick | Round |
|---|---|---|---|
| Omar Cooper Jr. | WR | 30 | 1 |
| Chris Brazzell II | WR | 83 | 3 |
| Mike Washington Jr. | RB | 122 | 4 |
| Kevin Coleman Jr. | WR | 177 | 5 |
| Emmanuel Henderson Jr. | WR | 199 | 6 |
| Jam Miller | RB | 245 | 7 |

Age is computed as `(draft_date - birth_date).days / 365.25` and stored as a float (e.g., `22.57`). The identity file records `birth_date` as ISO string (e.g., `"2003-10-14"`).

**Questions to answer:**

1. For each of the 6 players, what is the confirmed birth date? Primary sources in order of preference: Pro Football Reference player pages, Sports Reference, NFL.com official profile, ESPN player page. Provide the birth date and source URL for each.

2. Are any of these players FCS/small-school prospects where birth-date data is less reliable? What is the confidence level for each entry?

3. Omar Cooper Jr. is a 1st-round pick (pick 30). How does his expected age (likely early 2000s birth year) compare to the typical age range for WR prospects picked in round 1? Would his resulting DVS place him in the top 10 or outside it?

4. How should the refresh script (`scripts/refresh_prospect_cards.py`) validate that a newly added `birth_date` is internally consistent (i.e., age at draft date is within the expected 20–26 range for a 2026 NFL draftee)?

---

## Research Question 2: College Production Signal Candidates for WR and RB

**The problem:**

Engine A currently separates prospects only by pick, round, and age. Within a round, players with the same pick number and similar age produce nearly identical DVS scores regardless of college production. The 2026 board showed three WRs within 2 DVS points of each other at picks 37–41.

The contract already allows `dominator_rating` and `receiving_yards_share` for WR/TE, and `dominator_rating` for RB. These signals exist in the enrichment pipeline (CFBD data) but have not been added to production scoring.

**Important constraint:** Engine A is trained on historical draft classes. Any new feature must be available for BOTH the historical training cohort (2015–2023 approximately) AND incoming 2026 prospects. Features that are only available for post-2020 prospects cannot be used.

**Questions to answer:**

1. **Dominator rating**: What is the published predictive validity of dominator rating (share of team receiving yards + TDs vs. team totals) for NFL WR production? What sample sizes support the claim? Does it separate players within a round or only across rounds? Cite dynasty community sources (Sigmund Bloom, PlayerProfiler, RotoBaller, etc.) and any academic research if applicable.

2. **Receiving yards share**: Independent of dominator rating, does a player's receiving yards share as a percentage of team totals add predictive signal for NFL WR success beyond what dominator rating captures? Are they collinear?

3. **RB dominator rating**: Is dominator rating defined consistently for RBs (share of team rushing yards + TDs vs. team totals)? Does it have equivalent predictive validity for RBs as for WRs? Is it more or less useful for dynasty (where RB aging cliffs matter) vs. redraft?

4. **Breakout age** (PlayerProfiler): What is the evidence for breakout age as a predictive signal for dynasty WR/RB value? The contract lists it under `PLAYERPROFILER_CONTEXT_COLUMNS` as "context signal only." What would it take to upgrade it to a model input? What are the coverage risks (how many 2015–2023 draft prospects have breakout age recorded)?

5. **Data availability for 2026 prospects**: Which of the 6 available signal candidates (dominator_rating, receiving_yards_share, breakout_age for WR; dominator_rating for RB) are available from the CFBD API or cfbfastr for the 2026 prospects? Are there known data gaps for FCS players, early declarations, or transfers?

6. **Overfitting risk**: Engine A's training set is small — approximately 150–200 WR rows, 100–150 RB rows, 40–60 TE rows across draft classes. With Ridge regression and a 4-fold LOOCV evaluation, what is the minimum observable R² improvement that would justify adding a feature to this model? At what point does adding features with a training set this small produce spurious lift on LOOCV?

7. **Recommendation**: Which signals should be candidates in a Phase 16 bake-off? Rank by expected signal-to-noise, data availability, and implementation complexity. Be specific: which CFBD endpoint, which field name, and whether historical coverage back to 2015 is confirmed.

---

## Research Question 3: Draft-Capital Transform — Real Historical Bake-Off Path

**The problem:**

Phase 13 built and validated bake-off machinery (LOOCV harness, candidate manifest, promotion gate) but never ran against a real historical cohort. All bake-off tests used synthetic/fixture data. The promotion decision (Task 13.2.3) is `VALIDATION_ONLY / NO PRODUCTION CHANGE`.

The current production feature is raw `pick` (linear). Candidates defined in the manifest include: log-decay, position-bucketed, isotonic-step. The draft exposed that raw pick does not separate late-round value appropriately — both Kaelon Black (pick 177) and Jonah Coleman (pick 244) showed large positive xVAR deltas, suggesting the current model may underweight late-round upside for RBs.

The Phase 13 promotion gates require:
- Immutable `identity_snapshot_{run_id}.json` for the real historical cohort
- Persisted bake-off result artifact by position
- Confidence intervals for primary rank metrics
- Pick-jitter sensitivity report
- Explicit comparison against current baseline and log-decay

**Questions to answer:**

1. **Within-dynasty evidence for log-decay**: Is there dynasty community evidence that a log transform of pick number better predicts long-term fantasy value than linear pick? The argument is intuitive (marginal value between pick 1 and pick 2 is larger than between pick 100 and pick 101), but is it validated? Cite sources.

2. **Position-bucketed transform**: Should draft-capital bucketing be different by position? RBs drafted in the 4th–6th round have historically produced differently than WRs at the same range. Does a position-specific bucketing scheme (e.g., RB: rounds 1–2, 3–4, 5+; WR: rounds 1–3, 4–6, 7+) have dynasty evidence?

3. **Isotonic step vs. continuous transform**: What is the trade-off between a continuous transform (log, sqrt) vs. a step function (isotonic) for a Ridge model trained on pick number? Does the Ridge's L2 penalty interact differently with a step-function input vs. a continuous one?

4. **Historical cohort scope**: Engine A is trained on draft classes where we have NFL outcomes (y2–y4 PPG). For a LOOCV where each fold holds out one draft class, how many usable draft classes are available for WR, RB, and TE? What is the approximate row count per fold? Is this sample large enough for confidence intervals on Spearman ρ to be meaningful?

5. **What to actually run**: To meet the Phase 13 promotion gate, describe the exact sequence of steps: which data file, which snapshot command, which bake-off invocation, which artifact to inspect. The machinery exists in `src/dynasty_genius/eval/`; the question is whether the inputs are ready.

---

## Research Question 4: Feature Coverage and Missing-Data Strategy

**The problem:**

If college production signals are added to Engine A, some prospects will lack data — FCS players, transfers with limited CFBD coverage, players who declared without completing a full season. The current handling of missing data is all-or-nothing: if any required feature is absent, the player gets no score (PRE_MODEL).

The 6 age-data blockers demonstrate this cost: a 1st-round WR (pick 30) is unscored because one field is missing.

**Questions to answer:**

1. **Fallback tiers**: If a college production signal is missing for a prospect, should Engine A fall back to the pick/round/age-only model (producing a score from the 3-feature baseline), or produce no score (PRE_MODEL)? What are the user-facing risks of each approach? Would a scored player with imputed production features be misleading?

2. **Imputation approaches**: What are the options — median imputation by position-class, zero-fill (treats missing as "no production"), or explicitly setting a `production_data_absent` flag and using the 3-feature model as fallback? Which approach preserves the most auditability without hiding data gaps?

3. **FCS coverage**: What fraction of historical draft classes (2015–2023) contain FCS or non-FBS prospects with limited CFBD coverage? Is this fraction large enough to affect model validity?

4. **Transfer portal complexity**: The 2026 draft class includes players with 2–3 college stops. Should dominator rating use only the final season, a career aggregate, or a peak-season value? What does the dynasty literature say about transfer portal players specifically?

5. **Recommendation**: What is the minimum viable missing-data strategy for a Phase 16 bake-off? Define clearly: which features are gating (must have or player is PRE_MODEL), which features are optional (can fall back to baseline model if absent), and how the distinction is represented in the PVO output.

---

## Research Question 5: xVAR Replacement Anchors — Post-Draft Recalibration Trigger

**The problem:**

`ENGINE_A_REPLACEMENT_DVS` anchors are currently set at: QB=77.3, RB=49.9, WR=69.2, TE=98.8. These represent the DVS of the player at the replacement threshold in a 12-team Superflex league. They are not derived from the 2026 draft — they reflect the long-run average of the Engine A training distribution.

The 2026 draft exposed that RB replacement is unusually interesting: Black (pick 177) and Coleman (pick 244) both show large positive xVAR. If Engine A features improve and DVS values shift, the replacement anchors may need updating.

**Questions to answer:**

1. How should `ENGINE_A_REPLACEMENT_DVS` be recalibrated after an Engine A model change? Is replacement DVS a function of the model's distribution (recomputed automatically) or a fixed governance constant set by position-scarcity analysis?

2. For a 12-team Superflex PPR league, what are the theoretically correct replacement thresholds — how many QBs, RBs, WRs, and TEs are starters? Is the current threshold (QB25, RB33, WR53, TE13) correct for a 12-team league with typical starting lineup requirements?

3. If Engine A RB scores shift meaningfully after adding dominator rating, should `ENGINE_A_REPLACEMENT_DVS["RB"]` be updated in the same release or in a separate governance step? What is the risk of updating DVS anchors without updating replacement anchors simultaneously?

---

## Deliverable Format

For each research question, provide:

1. **Recommendation** — a specific, actionable answer with any formula, threshold, or implementation detail needed
2. **Alternatives considered** — other approaches and why they are rejected
3. **Implementation complexity** — new PVO fields, new scripts, data source changes, schema migrations
4. **Dependencies** — what must exist before this can be built
5. **Risk flags** — what could go wrong; which player archetypes or edge cases require special handling

---

## Non-Negotiable Constraints for All Recommendations

The following must not appear in any Phase 16 recommendation:

- Market data (KTC, FantasyCalc, ADP, any dynasty consensus value) entering the DVS formula, Engine A feature set, Engine B feature set, or training data
- PFF grades or PFF-derived features as model inputs — permanently banned
- xVAR as a model input (it is display/decision currency only)
- Any recommendation that sets `decision_supported = True` on any surface
- Any recommendation that retrains or replaces Engine B production artifacts without a separate validated spec
- Age imputation for the 6 blockers that produces ages outside the 20–26 range for a 2026 NFL draftee
- Feature additions to Engine A without a LOOCV gate showing measurable lift over the 3-feature baseline

---

## Current Working Repo State

For agent context:

- Test suite: 730 passed, 11 skipped, 0 failed
- Commits ahead of origin: 8 (Phase 15.1–15.3 + closeout docs)
- `resources/draft_state.js`: modified (live draft, 26/36 picks, `status=drafting`) — not yet committed
- Live draft: Kaelon Black (RB, pick 26) is David's pick
- Age-data blocker players are confirmed 2026 NFL draftees with verified pick/round; only `birth_date` is missing

---

*Hand this brief to research agents independently. Each agent should cover all five research questions. Claude will compare responses, identify conflicts, and synthesize a corrected roadmap before the Phase 16 spec is written.*
