# DG-165 — draft-capital rookie candidate: what was built, what it measured, what it is not

**Run:** `runs/20260906T133904Z/dg165_rookie_capital/` · branch `ticket/DG-165` (base `ecc260ef`) · session `davidleess-a3`
**Status:** research candidate. Not served, not promoted, not merged. Nothing under `app/data` was written.
**Supersedes** `20260906T132936Z` (five horizons, no level), `133648Z` and `133820Z` (identical numbers; missing the comparator table / the adapter manifest blocks). All kept with `SUPERSEDED.md`.

## 1. The estimands, stated so they can be argued with

For a drafted QB/RB/WR/TE, NFL season j = 1..6 (rookie season = 1 = forecast year) and horizon h = 1..6:

| column | event / quantity | how it is labelled |
|---|---|---|
| `p_played_h{h}` | at least one regular-season game in seasons 1..h | appears in nflverse weekly skill-position stats |
| `p_qual_year{j}` | **qualifies** in season j | finished at or above the bar rank by regular-season PPR total: **QB37 / RB45 / WR71 / TE21**, tie-robust N-th largest — identical to the canonical DG-164 cells |
| `p_qual_h{h}` | at least one qualifying season in 1..h | as above, any season in the window |
| `e_qual_seasons_h{h}` | E[number of qualifying seasons in 1..h] | Σ_{j≤h} `p_qual_year{j}`; bounded by h; already unconditional |
| `e_ppg_given_qual_year{j}` | **E[ppg in season j \| qualifies in season j]** | ridge on the same design, fitted **only** on qualifying player-seasons; ppg = REG PPR points / games with a weekly stat row |

Model inputs: **pick, round, age at draft, position** (log-pick, position terms, position × log-pick). No college, market, projection or contract column; the leakage guard runs on the cohort frame. Nothing here multiplies a probability by a level — `p_qual_year{j} × max(0, e_ppg_given_qual_year{j} − R)` is the integration lane's act (DG-178), on its side, with its replacement rate R.

**Information cutoff.** At forecast year T the model is fitted only on labels that existed at T: class c contributes at horizon h (or season j) only if c + h − 1 ≤ T − 1. Asserted in `walk_forward_splits`; a leak-canary test pins it. The preserved study trained on labels observed through 2025 while "forecasting" 2019; this build cannot.

**Unit warning for the consumer.** The level's denominator is games with a weekly stat row, not the served all-games ppg (DG-024). The served replacement rates the assembler subtracts are on the served denominator. The manifest's `units.ppg_denominator` says so; reconcile, do not absorb.

## 2. Reproduction of the preserved study — identical

`runs/20260906T131535Z/dg165_reproduction/`: the preserved `rookie.py` re-run on hashed copies of the same `panel.parquet` (2026-09-05 06:21) and `prospects_with_outcomes_v3.csv`. Diff against the preserved `RESULTS.txt` is empty: 478 / 85 zero-game / 203 qualified, AUC 0.813 / 0.655 / 0.817.

## 3. Cohort — nflverse draft picks 1999–2026, and two survivorship traps in the join

- 2,238 skill-position picks in classes 1999–2026 → **2,237 in the cohort**; 80 are the 2026 class (all with gsis_id).
- **108 picks have no gsis_id; 107 of them have zero PFR career games.** A gsis id is assigned when a player reaches an NFL roster system, so dropping id-less rows deletes washouts (1999–2004 kept rows read 0.5% washouts against 6–10% later). They are **kept under a synthetic id and labelled 0**. The one who played (Bill Baber, 2001, 30 games) cannot be joined and is dropped, counted.
- **All 107 also lack a birth date.** An "age missing" indicator learns "missing age ⇒ washout" (a PFR data-collection artifact) and scored a 2026 seventh-round QB with no birth date on file at P(Q_5) = 0.00 (artifact-free: 0.10). The design carries **no missingness indicator**; a test pins that a missing age scores exactly like the position-median age.
- 66 kept picks with PFR games > 0 never appear in the skill-position weekly stats (fullbacks, long snappers, position changes; none found under another id by name). They label not-played / not-qualified — right for the fantasy question, slightly understating `P(played)`.
- Age at draft: nflverse agrees with `prospects_with_outcomes_v3.csv` on **871 of 871** overlapping rows. Three 2026 rookies have no age on file (Koziol, CJ Williams, Nussmeier) → `scored_age_imputed`.

## 4. Out-of-time results — forecast years 2005–2025, 110 (T, h) pairs graded, 16 not yet gradable

| horizon | classes graded | n | prevalence | AUC (90% CI) | Brier model / no-model | E[N_h] RMSE model / no-model |
|---|---|---:|---:|---|---|---|
| h = 1 | 2005–2025 | 1,676 | 0.17 | 0.842 (0.824, 0.861) | 0.120 / 0.169 | 0.35 / 0.41 |
| h = 2 | 2005–2024 | 1,590 | 0.27 | 0.831 (0.813, 0.850) | 0.148 / 0.217 | 0.61 / 0.76 |
| h = 3 | 2005–2023 | 1,513 | 0.32 | 0.827 (0.808, 0.845) | 0.157 / 0.230 | 0.86 / 1.09 |
| h = 4 | 2005–2022 | 1,433 | 0.35 | 0.819 (0.801, 0.838) | 0.165 / 0.238 | 1.09 / 1.40 |
| h = 5 | 2005–2021 | 1,354 | 0.36 | 0.818 (0.798, 0.838) | 0.166 / 0.241 | 1.30 / 1.67 |
| h = 6 | 2005–2020 | 1,202 | 0.37 | 0.821 (0.801, 0.842) | 0.167 / 0.243 | 1.51 / 1.93 |

"No-model" = training prevalence applied to the test class. Six-bin calibration of P(Q_3) is within 0.044. By round at h = 3, predicted / actual: R1 0.88 / 0.88 · R2 0.65 / 0.63 · R3 0.43 / 0.48 · R4 0.29 / 0.28 · R5 0.18 / 0.23 · R6 0.13 / 0.15 · R7 0.08 / 0.06.

**The level, out-of-time, graded on qualifiers only** (`EVALUATION.md` §The LEVEL):

| season j | n qualifiers | mean actual ppg | mean predicted | RMSE model / position-mean | bias |
|---|---:|---:|---:|---|---:|
| 1 | 362 | 11.64 | 10.50 | 3.49 / 3.64 | −1.13 |
| 2 | 429 | 12.66 | 12.06 | 3.91 / 4.02 | −0.61 |
| 3 | 382 | 13.10 | 12.55 | 3.92 / 4.19 | −0.55 |
| 4 | 334 | 13.21 | 12.51 | 4.10 / 4.15 | −0.70 |
| 5 | 260 | 13.60 | 12.92 | 4.05 / 4.19 | −0.68 |
| 6 | 201 | 13.56 | 12.77 | 4.20 / 4.07 | −0.80 |

**Where it is wrong, said plainly:**
- **Scoring is rising over time and everything fitted on the past lags it.** The level under-predicts by 0.6–1.1 ppg at every season, and the position-mean comparator carries the **same** bias (−0.5 to −1.0), so the trend is in the data, not the fit. Same shape on the probability side: h = 1 actual vs predicted by era 2005–10 0.17 / 0.16 · 2011–16 0.21 / 0.17 · 2017–20 0.24 / 0.20 · 2021–25 0.25 / 0.21. For a consumer subtracting a replacement rate of 7–9 ppg, a −1 ppg bias on the level understates a rookie's margin materially. **A class-year trend term is the first refinement, not built here without its own test.**
- **The level adds little over "mean rate of qualifiers at the position":** 2–6% of RMSE in seasons 1–5, and it is worse at season 6. The comparator table is published in `training_descriptives.json` (`level_qualifier_mean_ppg_by_position_and_season`) so the consumer can see what the fit adds. Season 1 by round shows the capital slope the ridge under-fits: round-1 qualifiers average 13.0 ppg, predicted 11.1.
- **Mid-round quarterbacks are over-predicted on qualification:** rounds 4–5 at h = 5, n = 50, predicted 0.32 vs actual 0.16. Rounds 4–5 RBs under-predicted (0.36 vs 0.43); seventh-round TEs 0.07 vs 0 of 44.
- **Young QB/TE (age ≤ 23, rounds 1–2, h = 3):** QB n = 72, predicted 0.83 vs actual 0.83; TE n = 47, 0.70 vs 0.66. Well calibrated.

## 5. The 2026 class (`rookie_scores_2026.csv`, `ROOKIES_2026.md`) — 80 rows, 80 drafted rookies

| pick | player | pos | P(Q y1) | E[ppg\|Q y1] | P(Q y3) | E[ppg\|Q y3] | P(Q_6) | E[N_6] (90% fit interval) |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | Fernando Mendoza | QB | 0.89 | 13.7 | 0.86 | 16.1 | 0.99 | 5.08 |
| 3 | Jeremiyah Love | RB | 0.89 | 16.0 | 0.90 | 19.1 | 0.99 | 5.30 |
| 4 | Carnell Tate | WR | 0.79 | 12.5 | 0.83 | 15.1 | 0.95 | 4.65 |
| 13 | Ty Simpson | QB | 0.64 | 12.2 | 0.58 | 14.6 | 0.91 | 3.43 |
| 16 | Kenyon Sadiq | TE | 0.51 | 9.7 | 0.77 | 10.9 | 0.94 | 3.96 |
| 32 | Jadarian Price | RB | 0.67 | 12.4 | 0.68 | 14.5 | 0.91 | 3.60 |
| 249 | Garrett Nussmeier | QB | 0.02 | 11.0 | 0.03 | 13.0 | 0.10 | 0.24 |

Intervals in the CSV are **fit uncertainty** (200 refits on player-resampled training sets), not outcome spread: a pick with P(Q y1) = 0.89 still misses one time in nine, and that is in the probability. Join keys for the served artifact, which carries no gsis_id for 2026 rookies: (position, draft_season, pick), unique for drafted players.

**Measured by the integration lane on the 2026-09-06 13:00 artifact (their finding, quoted, not re-measured here):** all 80 Engine A rookie rows carry a pick; 0 undrafted rookies among the 45 league-rostered Engine A rows and 0 among David's four (Mendoza 1, Cooper 30, Bell 94, Black 90); none of the 364 unscored `years_exp == 0` rows is rostered by anyone in the league. So the undrafted gap costs nothing on any roster today; it stays a named gap. They also found that Mendoza, Simpson and Sadiq never reach the DG-164 cells (Engine A rows with no `projection_2y`); the suppressed young-QB cell bites Jaxson Dart, who is not a rookie and remains a DG-176 question.

## 6. What this is NOT, and how it composes

- **Not a value, not a ranking.** Probabilities and conditional rates per season in football units. The dynasty number is DG-178's composition with David's replacement ruling and posture.
- **`p_qual` and `p_played` are different events.** Engine A's rate is conditional on ≥ 8 career games and non-censored rows (`build_head_b_targets.py:84`, `run_head_a_bakeoff.py:125`); it composes with `p_played`, never with `p_qual`.
- **`e_qual_seasons_h` is already unconditional** — never multiply it by a survival curve or by `p_qual_h`.
- **The level is conditional on qualifying in that season**; multiplying it by `p_qual_year{j}` is the consumer's act, once, with the denominator mismatch reconciled first.
- **Undrafted rookies are not modelled.** No population table exists; inventing one from roster survivors would be the survivorship error again.
- The bar is the availability bar; a starter-bar variant (DG-171) is a parameter (`bar=`), not run.

## 7. Candidate refinements — none built; each needs its own measured test

1. A class-year trend term (probability and level both lag a rising rookie contribution).
2. A steeper QB curve past round 3.
3. Delayed breakout for players already in the league: P(Q_h | no qualifying season in the first k) is supported by the same labels; that is what the DG-176 gap needs beyond rookies.
4. Undrafted coverage from roster history, if a defensible population can be defined.
5. College features on top of capital: +0.004 AUC in the preserved study; not re-run, not needed for the baseline.

## 8. Files

`manifest.json` (definitions, units, cutoff rule, input sha256s, git sha, versions) · `evaluation.json` / `EVALUATION.md` · `out_of_time_predictions.csv` (every graded forecast row incl. the level) · `rookie_scores_2026.csv` / `ROOKIES_2026.md` · `training_descriptives.json` (in-sample, descriptive; includes the level comparator) · `inputs/` (gitignored copies; hashes in the manifest).
Code: `src/dynasty_genius/rookie/` · runner `scripts/dg165/run_rookie_capital.py` · tests `tests/contract/test_dg165_rookie_capital.py` (20, synthetic, no network).
