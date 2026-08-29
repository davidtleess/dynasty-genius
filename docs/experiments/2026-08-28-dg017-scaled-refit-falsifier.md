# DG-017 falsifier — scaled refit with an honestly tuned alpha (report-only)

**Date:** 2026-08-28 (run `20260829T000753Z` UTC) · **Ticket:** DG-017 · **Bears on:** DG-001
**Lane:** report-only experiment branch `ticket/DG-017`. Nothing here lands; no deployed
artifact, model store, or serving path was touched. Deployed pkls were read from the trunk
model store read-only.

---

## Verdict

**The DG-001 attribution falls as a statement about football. It stands as a description
of the shipped artifact. The behavioral conclusion — Engine B predicts like a PPG
autoregression with an age term — stands untouched.**

DG-017 named the criterion in advance: *"If the ppg family still carries 52–86%, this
hypothesis is dead and DG-001 stands as measured. If the rate stats come up materially,
DG-001's conclusion was about the fit, not the sport."*

The rate stats came up materially. With a train-fitted StandardScaler and an alpha tuned
on a grid that never binds, the usage/rate family goes from numerical noise to
**12–35% of standardized coefficient weight** at every position:

| Position | usage share, deployed fit | usage share, scaled fit | ppg family, deployed | ppg family, scaled |
|---|---|---|---|---|
| QB | 8.9% (almost all of it cpoe) | **30.4%** | 50.0% | 40.2% |
| RB | 0.3% | **12.4%** | 84.4% | 75.2% |
| WR | 3.4% | **31.6%** | 74.2% | 53.9% |
| TE | 1.4% | **35.1%** | 75.8% | 51.7% |

The features DG-017 called "not weak — inert" are inert no longer once the fit lets them in:

| Feature (1-SD move → PPG shift) | Deployed unscaled fit | Scaled, tuned fit |
|---|---|---|
| WR `snap_share` | 0.018 (the ticket's "0.019") | 0.083 — and the usage block around it wakes up: `weighted_opportunity` **1.16** (the #2 WR feature outright), `yprr` 0.31, `snap_share_t_minus_1` 0.37 |
| TE `tprr` | 0.00002 (the ticket's "0.00004") | **0.116** — 5,000× larger; TE `weighted_opportunity` 0.012 → **1.04** (#2 TE feature) |
| RB `snap_share` | 0.001 | **0.33** (`snap_share_t_minus_1` likewise 0.001 → 0.33) |
| QB `snap_share` | 0.004 | **0.72**; `is_dual_threat` 0.017 → 0.77 |

**And yet holdout accuracy does not move.** Same split, same imputer, same CV protocol,
scaling the only difference — the scaled fits are within noise of the unscaled ones
(WR slightly better, QB/RB/TE slightly worse; details below). Both fits describe the same
predictions with different words. That is the deepest result of the experiment: **on
season-averaged rows, coefficient attribution for this model family is fit-dependent, and
no decomposition of these artifacts should be quoted as a fact about what drives fantasy
production.** The season-averaged rate stats are nearly collinear with season-averaged
points, so the penalty geometry — not the data — decides which family wears the weight.
DG-001's closing inference stands and gets sharper: week-level rows (DG-006, decided
through DG-025) are the only design on the table that can actually answer the
what-drives-it question.

What survives of DG-001, replay-verified:

1. **As a description of the shipped model, DG-001 stands.** The deployed artifacts were
   reproduced from today's dataset under their stated recipe — selected alpha matches at
   all four positions, max |Δcoef| ≤ 0.015 (TE exact to 2.6e-15). The ppg family really
   does carry 50–84% of the shipped models' weight, and their usage features really are
   inert. Every number DG-001 published about the pkls on disk is correct.
2. **The behavioral core stands.** Scaling + honest tuning buys essentially zero holdout
   accuracy. Nobody left performance on the table by shipping unscaled; they left
   *interpretability* on the table.
3. **One DG-017 inference is corrected by measurement:** the QB alpha=1000 boundary
   selection was read as "the search wanted more regularisation than it was allowed to ask
   for." On a grid extended to 10,000, unscaled QB still selects exactly 1000 — now
   interior, zero widenings. The ceiling happened to *be* the optimum, not to bind it.
   The saturation symptom was real to worry about; it just turns out benign here.
4. The 1000× per-position alpha spread does compress under scaling, as the unscaled-inputs
   theory predicts: scaled selections are 3.16–31.6 (10×) vs 100–1000 unscaled.

**What this means for the DG-017 fix (unbuilt, post-freeze):** the pipeline-parity work is
still right — the thing measured must be the thing shipped — but there is no accuracy
regression hiding in the scaling gap. The stakes of the parity fix are honesty and
attribution, not RMSE.

---

## Tables

### 1. Holdout metrics (seasons 2022–2023; RMSE/R²/Spearman vs the ppg_t baseline)

| Pos | Arm | alpha | RMSE | R² | Spearman |
|---|---|---|---|---|---|
| QB | baseline ppg_t | — | 5.461 | 0.177 | 0.634 |
| QB | deployed (unscaled) | 1000 (grid ceiling) | 4.507 | 0.439 | 0.696 |
| QB | refit unscaled, honest grid | 1000 (interior) | 4.507 | 0.439 | 0.696 |
| QB | **refit scaled, honest grid** | 31.6 | 4.514 | 0.438 | 0.669 |
| RB | baseline ppg_t | — | 4.033 | 0.482 | 0.762 |
| RB | deployed | 500 | 3.583 | 0.591 | 0.783 |
| RB | refit unscaled | 1000 | 3.601 | 0.587 | 0.782 |
| RB | **refit scaled** | 3.16 | 3.605 | 0.586 | 0.780 |
| WR | baseline ppg_t | — | 3.470 | 0.543 | 0.778 |
| WR | deployed | 200 | 2.886 | 0.684 | 0.810 |
| WR | refit unscaled | 316 | 2.895 | 0.682 | 0.809 |
| WR | **refit scaled** | 31.6 | **2.848** | **0.692** | **0.811** |
| TE | baseline ppg_t | — | 2.475 | 0.554 | 0.759 |
| TE | deployed (⚠ trained on ALL eligible rows, holdout included — its row is in-sample-flattered) | 100 fixed | 2.235 | 0.636 | 0.787 |
| TE | refit unscaled (honest TE comparison) | 100 | 2.255 | 0.630 | 0.782 |
| TE | **refit scaled** | 31.6 | 2.275 | 0.623 | 0.776 |

Reading: the largest accuracy move anywhere is WR, −0.047 RMSE in the scaled fit's favor.
QB gives back 0.027 Spearman scaled. Nothing here clears the bar of "different model";
everything clears the bar of "different attribution."

### 2. Family shares of standardized coefficient weight (|coef × SD_train|, share of total)

| Pos | Arm | ppg* | age | volume (games_t) | usage/rate |
|---|---|---|---|---|---|
| QB | deployed | 0.500 | 0.081 | 0.331 | 0.089 |
| QB | scaled | 0.402 | 0.063 | 0.231 | **0.304** |
| RB | deployed | 0.844 | 0.115 | 0.038 | 0.003 |
| RB | scaled | 0.752 | 0.097 | 0.027 | **0.124** |
| WR | deployed | 0.742 | 0.117 | 0.106 | 0.034 |
| WR | scaled | 0.539 | 0.098 | 0.048 | **0.316** |
| TE | deployed | 0.758 | 0.086 | 0.142 | 0.014 |
| TE | scaled | 0.517 | 0.067 | 0.065 | **0.351** |

`ppg*` = every feature with the ppg name prefix (values + availability flags). The ppg
family remains the single largest family at every position even scaled — Engine B is still
mostly autoregression — but the "everything else is numerical noise" half of the DG-001
headline does not survive.

### 3. Top-6 features by standardized weight, scaled fit

| Pos | Top 6 (1-SD effect in PPG) |
|---|---|
| QB | ppg_t 1.94 · games_t 1.93 · is_dual_threat 0.77 · snap_share 0.72 · ppg_t_minus_2_available 0.67 · ppg_t_minus_1 0.65 |
| RB | ppg_t 3.82 · age 0.63 · ppg_t_minus_2 0.61 · ppg_t_minus_1 0.49 · snap_share 0.33 · snap_share_t_minus_1 0.33 |
| WR | ppg_t 2.32 · **weighted_opportunity 1.16** · ppg_t_minus_1 0.86 · age 0.59 · snap_share_t_minus_1 0.37 · games_t 0.32 |
| TE | ppg_t 1.54 · **weighted_opportunity 1.04** · games_t 0.30 · snap_share 0.28 · ppg_t_minus_1 0.27 · ppg_t_minus_2 0.24 |

For the deployed fits the top of every table is ppg_t / games_t / ppg_t_minus_1 / age with
usage absent (full per-arm tables in `results.json`).

### 4. Replay check — the deployed artifacts reproduce from their stated recipe

| Pos | Deployed alpha | Replay alpha (deployed grid, today's dataset) | max abs coef delta |
|---|---|---|---|
| QB | 1000.0 | 1000.0 ✓ | 4.7e-03 |
| RB | 500.0 | 500.0 ✓ | 6.6e-03 |
| WR | 200.0 | 200.0 ✓ | 1.5e-02 |
| TE | 100.0 (fixed) | 100.0 ✓ | 2.6e-15 |

The small QB/RB/WR deltas are consistent with minor dataset drift since the May training
runs; TE (June) reproduces bit-for-bit. This is the replay evidence DG-017's "done looks
like" asks for, produced on the way past.

### 5. Alpha honesty

| Pos | Deployed grid selection | Honest unscaled (grid 1e-3…1e4, widen-on-pin) | Honest scaled |
|---|---|---|---|
| QB | 1000 — grid ceiling | 1000 — interior, 0 widenings | 31.6 |
| RB | 500 | 1000 — interior, 0 widenings | 3.16 |
| WR | 200 | 316 | 31.6 |
| TE | 100 fixed (v3); v2 had selected 1.0 | 100 | 31.6 |

No fit in this experiment selected a boundary alpha; the widening machinery was armed
(two extra decades per pin, up to six times) and never needed. Scaled alpha spread: 10×.
Unscaled: 1000× across the deployed family — the spread itself was a scale artifact, as
predicted.

---

## Method

- **Data:** `app/data/training/engine_b_features_v2.csv` as tracked on `main`
  (2,741 rows; 2,236 training-eligible; no NGS columns present, so both refit arms saw
  exactly the deployed feature lists). Holdout = feature seasons 2022–2023, identical to
  `train_engine_b.py`.
- **Arms, per position:**
  **A — deployed:** the manifest artifacts (`qb/rb/wr_v2.pkl` run `20260513T012309Z`,
  `te_v3.pkl` run `20260626T165649Z`) loaded read-only from the trunk store; predictions
  through their own pickled imputers.
  **B — refit unscaled:** median SimpleImputer → RidgeCV, train split only.
  **C — refit scaled:** median SimpleImputer → StandardScaler (train-fitted) → RidgeCV.
  B and C differ by the scaler and nothing else.
- **Honest alpha:** base grid `logspace(-3, 4, 15)`; whenever RidgeCV selects a grid
  boundary the pinned side is extended two decades and the search re-runs (cap 6). CV kept
  at `cv=5` exactly as the deployed trainer — one variable changed per DG-017's design.
  (DG-027's separate impeachment of this CV protocol — random folds over repeated players —
  is acknowledged and deliberately NOT fixed here; it biases both arms identically.)
- **Decomposition (DG-001's method):** a feature's weight is the prediction shift per 1-SD
  move of the raw feature, |coef × SD| with SD taken on the imputed training matrix the
  model actually saw (for TE-deployed that is all eligible rows, per its recipe). In the
  scaled arm this is |coef| by construction. Shares are weights over their sum; families
  group by name: `ppg*` / age (`age`, `aging_curve_value`) / volume (`games_t`) / usage
  (snap_share block, tprr, yprr, weighted_opportunity, epa_per_dropback, cpoe, dakota,
  is_dual_threat).
- **Code:** `scripts/experiments/dg017_scaled_refit_falsifier.py`; unit tests
  (decomposition, family grouping, widen-on-pin tuning — written first, watched RED) in
  `tests/test_dg017_scaled_refit_falsifier.py`, 8 passed.
- **Full numbers:** `runs/20260829T000753Z/dg017_scaled_refit/results.json` in this
  worktree/branch.
- **Not re-run, still standing:** the no-usage-features ladder ("a model with NO usage
  features matches or beats the shipped model at RB/WR/TE") was not re-executed scaled.
  Given the accuracy parity measured here it would very likely hold under scaling too —
  the usage weight is substitutive, not additive — but that is inference, not measurement.

## What would change this verdict

If someone shows a scaled, honestly tuned fit whose usage family stays under ~2% of
weight, or a decomposition method that is fit-invariant on these rows, the "attribution is
fit-dependent" conclusion weakens. If a scaled fit ever beats the unscaled one by a margin
that survives DG-026/DG-027's eval repairs, the "no accuracy on the table" conclusion
falls and the DG-017 fix becomes a performance ticket, not just an honesty ticket.
