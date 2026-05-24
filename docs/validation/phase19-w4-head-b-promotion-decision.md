# Phase 19 W4 — Head B v3 Promotion Decision

**Status: NO PROMOTION — All positions fail mandatory residual R² gate**

**Bakeoff Artifact**: `app/data/backtest/phase19/head_b_bakeoff_20260524T145953Z_595f073d.json`
**Sensitivity Artifact**: `app/data/backtest/phase19/head_b_outlier_sensitivity_report_20260524T145953Z_595f073d.json`
**Branch**: `feature/phase19-w4-head-b-bakeoff`
**Date**: 2026-05-24

---

## Executive Summary

The W4 Head B bakeoff evaluated Ridge and GBT candidates against `residual_ppg` (actual PPG minus expected PPG at draft slot) across 4-fold temporal walk-forward splits (classes 2018–2021). No position cleared the mandatory gate.

**Passing candidates: none.**

Every position-candidate combination fails the mandatory residual R² > 0 gate, meaning no Head B model predicts `residual_ppg` better than a mean-zero baseline. No Head B model artifact has been trained, serialized, or promoted. No manifest, PVO scorer, or `decision_supported` flag has been changed.

---

## Gate Results

**Method**: 4-fold temporal walk-forward (train ≤ year Y, test = year Y+1 for Y ∈ {2017, 2018, 2019, 2020}). Gates evaluated on pooled OOF predictions across all folds.

**Mandatory gate**: Residual R² > 0 (model beats a mean-zero / mean-residual baseline).
**Secondary gates (≥2 of 3 required, evaluated only when mandatory passes)**: within-tier pairwise accuracy > 0.5, top-5 Day 3 sleeper precision > 0.5, residual calibration monotonicity.

| Position | Candidate | OOF R² | Pairwise Acc | Day 3 Prec | Monotone | Secondary | Mandatory | Decision |
|---|---|---|---|---|---|---|---|---|
| **QB** | — | — | — | — | — | — | — | **SKIPPED** (no W4 features) |
| **RB** | Ridge | −0.260 | 0.430 | 0.400 | False | 0/3 | **FAIL** | **NOT PROMOTED** |
| **RB** | GBT | −0.555 | 0.449 | 0.200 | False | 0/3 | **FAIL** | **NOT PROMOTED** |
| **WR** | Ridge | −0.012 | 0.369 | 0.600 | False | 1/3 | **FAIL** | **NOT PROMOTED** |
| **WR** | GBT | −0.270 | 0.481 | 0.800 | False | 1/3 | **FAIL** | **NOT PROMOTED** |
| **TE** | Ridge | −0.082 | 0.597 | 0.000 | False | 1/3 | **FAIL** | **NOT PROMOTED** |
| **TE** | GBT | −0.326 | 0.583 | 0.000 | False | 1/3 | **FAIL** | **NOT PROMOTED** |

Note: WR Day 3 precision (0.6 Ridge, 0.8 GBT) and TE pairwise accuracy (0.597 Ridge, 0.583 GBT) show marginal signal in specific secondary metrics, but these are moot — no candidate enters secondary gate evaluation because none clears the mandatory R² threshold.

---

## LOOO Outlier Sensitivity Report

Ridge coefficient drift (leave-one-outlier-out, max % shift across folds):

| Position | Features | Max Drift | LOOO Verdict |
|---|---|---|---|
| **RB** | final_college_age, rb_final_dominator, rb_school_sp_plus | >25% on all | **All features quarantined** |
| **WR** | final_college_age, wr_dominator_final, wr_breakout_age, wr_market_share_yds, wr_yards_per_reception_career, ryptpa | >25% on all | **All features quarantined** |
| **TE** | final_college_age, te_ryptpa_final, te_yards_per_reception_career | >25% on all | **All features quarantined** |

All available Head B features exceeded the 25% LOOO drift threshold across positions. This is consistent with sparse per-fold training sets (typically 20–50 rows per position-fold) where a single outlier can dominate the Ridge coefficient. The quarantine enforcement means no candidate would appear in `passing_candidates` even if one cleared the R² gate.

---

## Head B Feature Vectors Used

Per W4 spec §1. All features verified clean via `check_head_b_feature_leakage()` before any training.

| Position | Features |
|---|---|
| QB | — (skipped) |
| RB | final_college_age, rb_final_dominator, rb_school_sp_plus |
| WR | final_college_age, wr_dominator_final, wr_breakout_age, wr_market_share_yds, wr_yards_per_reception_career, ryptpa |
| TE | final_college_age, te_ryptpa_final, te_yards_per_reception_career |

---

## Structural Interpretation

`residual_ppg` is constructed as `actual_best3of4_ppg − expected_ppg_at_pick`. The expected curve is isotonic-fitted on training data so the mean residual within each pick band is close to zero by construction. A Ridge or GBT predicting `residual_ppg` from college features can only achieve R² > 0 if college features carry **systematic signal about who over- or under-performs their draft slot** that is not already captured by pick position itself.

The near-zero or negative R² values across all positions suggest the current W4 feature sets do not carry that incremental signal — not that the harness is incorrect. The harness passed all 23 TDD tests and ran cleanly; the result is an honest evaluation of the signal available in the current feature envelope.

Possible interpretations (for David to adjudicate):
1. **Signal absence is real**: College efficiency features at this scale cannot reliably predict who beats their draft slot in this league-year window. The Head B concept may need a different target formulation, a larger sample, or positional enrichment not yet available.
2. **Feature gap**: The current W4 features (dominator, age, RYPTPA, school SP+) may lack the specific within-slot discriminators needed. Candidates such as production consistency, team offensive tier, or combine athleticism relative to peer pick range could be investigated in a future Head B feature expansion spec.
3. **Target noise floor**: With 4-fold temporal splits and 20–50 eligible rows per position-fold, the `residual_ppg` target has high variance. A longer training window or pooled multi-position approach might surface latent signal.

No remediation action is taken here. This document records the bakeoff result as-is.

---

## Governance Checklist

- [x] No market data used as model inputs
- [x] No draft-capital features used as training features (`check_head_b_feature_leakage` enforced)
- [x] `expected_ppg_at_pick` and all expectation/curve derivatives banned from Head B features
- [x] `residual_ppg` used as target only — never as a training feature
- [x] No model pkl trained, serialized, or promoted
- [x] No `app/data/models/head_a/v3_manifest.json` changed
- [x] No `app/data/models/engine_b/v2_manifest.json` changed
- [x] No `app/data/models/latest.json` changed
- [x] No PVO scorer path touched
- [x] No `decision_supported` flag changed
- [x] Both output artifacts are gitignored under `app/data/backtest/phase19/`
- [x] Full test suite: 1067 passed, 11 skipped, 0 failed

---

## Promotion Decision

**NO PROMOTION.**

No Head B model artifact is approved for production. The W4 bakeoff is closed with a null result. The Head B track remains inactive pending David's decision on next steps (see below).

---

## Next Decision Required (David)

W5 (Service Layer wiring for Head A v3 scorer) is ready to proceed independently of Head B — it wires `app/data/models/head_a/v3_manifest.json` into the Engine A scorer and does not depend on a Head B model existing.

**Decision options:**

1. **Proceed to W5 now** — Wire TE Head A v3 scorer into the Engine A service layer. Head B remains inactive. W5 is independent of the Head B null result.
2. **Head B feature-gap remediation first** — Before W5, define a new Head B feature expansion spec addressing the signal-absence findings above. W5 would follow.
3. **Defer both** — Park Phase 19 at this checkpoint; move to a different phase priority.

David's ruling on this choice gates the next session scope.
