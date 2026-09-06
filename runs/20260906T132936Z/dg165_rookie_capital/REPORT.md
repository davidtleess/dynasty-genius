# DG-165 — draft-capital rookie candidate: what was built, what it measured, what it is not

**Run:** `runs/20260906T132936Z/dg165_rookie_capital/` · branch `ticket/DG-165` from `ecc260ef` · session `davidleess-a3`
**Status:** research candidate. Not served, not promoted, not merged. Nothing under `app/data` was written.

## 1. The estimand, stated so it can be argued with

For a drafted QB/RB/WR/TE and a fixed horizon h = 1..5 NFL seasons (rookie season = season 1):

| symbol | event | how it is labelled |
|---|---|---|
| `P(played_h)` | at least one regular-season game in seasons 1..h | appears in nflverse weekly skill-position stats |
| `P(Q_h)` | at least one **qualifying** season in 1..h | finished at or above the bar rank for his position by regular-season PPR total: **QB37 / RB45 / WR71 / TE21**, tie-robust N-th largest — identical to the canonical DG-164 cells |
| `E[N_h]` | expected number of qualifying seasons in 1..h | Σ_{j≤h} P(qualifies in season j); bounded by h |

Inputs to the model: **pick, round, age at draft, position** (log-pick, position terms, position × log-pick). No college column, no market column, no projection, no contract. The leakage guard runs on the cohort frame.

**Information cutoff.** At forecast year T the model is fitted only on labels that existed at T: draft class c contributes at horizon h only if c + h − 1 ≤ T − 1. The preserved study's "true out-of-time" split trained on labels observed through 2025 while forecasting 2019; this build cannot do that (asserted in `walk_forward_splits`, tested by a leak canary).

## 2. Reproduction of the preserved study — identical

`runs/20260906T131535Z/dg165_reproduction/`: the preserved `rookie.py` re-run on hashed copies of the same `panel.parquet` (2026-09-05 06:21) and `prospects_with_outcomes_v3.csv`. Output diffs empty against the preserved `RESULTS.txt`: 478 / 85 zero-game / 203 qualified, AUC 0.813 / 0.655 / 0.817.

## 3. Cohort — nflverse draft picks 1999–2026, and two survivorship traps in the join

- 2,238 skill-position picks in classes 1999–2026 → **2,237 in the cohort**; 80 of them are the 2026 class (all with gsis_id).
- **108 picks have no gsis_id, and 107 of them have zero PFR career games.** A gsis id is assigned when a player reaches an NFL roster system; the ones who never did never got one. Dropping id-less rows deletes washouts — the feasibility gate's landmine in a third costume. They are **kept under a synthetic id and label 0**. The one id-less pick who played (Bill Baber, 2001, 30 games) cannot be joined and is dropped, counted.
- **All 107 also lack a birth date.** An "age missing" indicator therefore learns "missing age ⇒ washout", an artifact of PFR's data collection, and it scored a 2026 seventh-round QB with no birth date on file at P(Q_5) = 0.00 (artifact-free: 0.10). The design carries **no missingness indicator**; age is imputed by position median and a test pins that a missing age scores exactly like the median age.
- 66 kept picks with PFR career games > 0 never appear in the skill-position weekly stats (fullbacks, long snappers, position changes — none found under another id by name). They label not-played / not-qualified, which is right for the fantasy question and slightly understates `P(played)`.
- Age at draft: nflverse agrees with `prospects_with_outcomes_v3.csv` on **871 of 871** overlapping rows (max difference 0.0). Three 2026 rookies have no age on file (Koziol, CJ Williams, Nussmeier) and are flagged `scored_age_imputed`.

## 4. Out-of-time results (forecast years 2005–2025, 95 (T, h) pairs; 10 pairs cannot be graded yet)

| horizon | classes graded | n | prevalence | AUC (90% CI) | Brier model / no-model | E[N_h] RMSE model / no-model |
|---|---|---:|---:|---|---|---|
| h = 1 | 2005–2025 | 1,676 | 0.17 | 0.842 (0.824, 0.861) | 0.120 / 0.169 | 0.35 / 0.41 |
| h = 2 | 2005–2024 | 1,590 | 0.27 | 0.831 (0.813, 0.850) | 0.148 / 0.217 | 0.61 / 0.76 |
| h = 3 | 2005–2023 | 1,513 | 0.32 | 0.827 (0.808, 0.845) | 0.157 / 0.230 | 0.86 / 1.09 |
| h = 4 | 2005–2022 | 1,433 | 0.35 | 0.819 (0.801, 0.838) | 0.165 / 0.238 | 1.09 / 1.40 |
| h = 5 | 2005–2021 | 1,354 | 0.36 | 0.818 (0.798, 0.838) | 0.166 / 0.241 | 1.30 / 1.67 |

"No-model" is the training prevalence applied to the test class. The honest evaluable horizon is **h = 5 on classes through 2021**; the 2022–2025 classes are graded only at the horizons that have completed (`EVALUATION.md` lists every ungradable pair).

**Calibration, out-of-time (P(Q_3)):** six bins, max |predicted − actual| = 0.044. By round at h = 3, predicted vs actual: R1 0.88 / 0.88 · R2 0.65 / 0.63 · R3 0.43 / 0.48 · R4 0.29 / 0.28 · R5 0.18 / 0.23 · R6 0.13 / 0.15 · R7 0.08 / 0.06.

**Where it is wrong, by position × round at h = 5** (out-of-time; `out_of_time_predictions.csv`):
- **Mid-round quarterbacks are over-predicted:** rounds 4–5, n = 50, predicted 0.32 vs actual 0.16. The single log-pick slope per position does not bend fast enough after round 3 for QBs. Rounds 1–3 and 6–7 are within 0.05.
- Rounds 4–5 running backs are under-predicted (0.36 predicted vs 0.43 actual, n = 110). Seventh-round tight ends: 0.07 predicted, 0 of 44 actual.
- **Young QB/TE (age ≤ 23, rounds 1–2, h = 3), the DG-176 cells:** QB n = 72, predicted 0.83 vs actual 0.83, E[N_3] 1.89 vs 2.00; TE n = 47, 0.70 vs 0.66, 1.38 vs 1.34. Well calibrated.
- **Rookie-year production is rising over time** and a model fitted on the past lags it: h = 1 actual vs predicted by era 2005–10 0.17 / 0.16 · 2011–16 0.21 / 0.17 · 2017–20 0.24 / 0.20 · 2021–25 0.25 / 0.21. That is a trend, not a fit error; a class-year term is the obvious refinement and was deliberately not added without a measured test.

## 5. The 2026 class (`rookie_scores_2026.csv`, `ROOKIES_2026.md`) — 80 rows, 80 drafted rookies

| pick | player | pos | P(Q_1) | P(Q_3) | P(Q_5) | E[N_5] (90% fit interval) |
|---|---|---|---:|---:|---:|---|
| 1 | Fernando Mendoza | QB | 0.89 | 0.99 | 0.99 | 4.42 (4.15–4.64) |
| 3 | Jeremiyah Love | RB | 0.89 | 0.99 | 0.99 | 4.53 (4.32–4.67) |
| 13 | Ty Simpson | QB | 0.64 | 0.86 | 0.91 | 3.01 (2.73–3.28) |
| 16 | Kenyon Sadiq | TE | 0.51 | 0.92 | 0.94 | 3.44 (3.14–3.73) |
| 32 | Jadarian Price | RB | 0.67 | 0.89 | 0.91 | 3.16 (2.98–3.36) |
| 249 | Garrett Nussmeier | QB | 0.02 | 0.06 | 0.10 | 0.19 (0.13–0.26) |

The intervals are **fit uncertainty** (200 refits on player-resampled training sets), not outcome spread: a first-round pick with P(Q_3) = 0.86 still misses one time in seven, and that is in the probability. Class totals: mean P(Q_5) = 0.38; Σ E[N_5] = 85.8 qualifying seasons over five years.

DG-176's three names (Mendoza, Simpson, Sadiq) are 2026 picks 1, 13 and 16 and each carries a row; `E[N_h]` for them needs no retention cell.

## 6. What this is NOT, and how it composes

- **It is not a value and not a ranking.** It is three probabilities/expectations per horizon in football units (seasons). Turning it into a dynasty number is DG-178's composition, with David's replacement ruling and posture, not this lane's.
- **`P(Q_h)` and `P(played_h)` are different events and must not be substituted for each other.** Engine A's rate (`best3of4_ppg`) is conditional on ≥ 8 career games and non-censored rows (`build_head_b_targets.py:84`, `run_head_a_bakeoff.py:125`); if anyone composes it with a probability, that probability is `P(played)`, never `P(Q)`.
- **`E[N_h]` is already unconditional.** It is not to be multiplied by a survival curve or by `P(Q_h)`; `E[N_h | Q_h]` is published separately for anyone who needs the conditional.
- **Undrafted rookies are not modelled.** There is no undrafted-prospect population table in the product; inventing one from the survivors on rosters would be the survivorship error again. Their coverage on David's board is a roster-audit question for the integration lane; this run names the gap rather than filling it.
- The bar is the availability bar. A starter-bar variant (DG-171) is a parameter (`bar=`), not a code change, and was not run.

## 7. Candidate refinements, none built, each needs its own measured test

1. A class-year trend term for the rising rookie-year contribution (§4).
2. A steeper QB curve past round 3 (§4) — a round × position term or a two-piece log-pick.
3. Delayed breakout for players already in the league: the same labels support P(Q_h | no qualifying season in the first k) for second- and third-year players, which is what the DG-176 young-QB/TE gap actually needs beyond rookies.
4. Undrafted coverage from roster history, if a defensible population can be defined.
5. College features on top of draft capital — measured at +0.004 AUC in the preserved study; not re-run here and not needed for the baseline.

## 8. Files

`manifest.json` (definitions, cutoff rule, input sha256s, git sha, versions) · `evaluation.json` / `EVALUATION.md` · `out_of_time_predictions.csv` (7,566 graded forecasts) · `rookie_scores_2026.csv` / `ROOKIES_2026.md` · `training_descriptives.json` (in-sample, descriptive only) · `inputs/` (gitignored copies; hashes in the manifest).
Code: `src/dynasty_genius/rookie/` · runner `scripts/dg165/run_rookie_capital.py` · tests `tests/contract/test_dg165_rookie_capital.py` (17, all synthetic, no network).
