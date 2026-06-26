# TE role-risk feature: contamination-propped coefficient — finding & deferred review

Date: 2026-06-26. Status: **te_v3 retrain HARD-STOPPED; feature-validity review DEFERRED (David-ruled).**
Branch context: `fix/engine-b-crosswalk-fanout` (T1 crosswalk fix `6365382`, T2 deduped seed `04dc0f1`).
Cockpit: Claude (impl) + Codex (technical) + Gemini (governance), 3-way converged. David ruled "pause + open feature-validity review."

## Summary
The T1/T2 fix (season-aware crosswalk + deduped engine_b seed) removed a 35%-one-player
contamination (Tyler Conklin, gsis 00-0034270, duplicated up to 128× per season). Removing it
**flipped the `te_role_is_risk_profile` Ridge coefficient** in the TE walk-forward model from
consistently negative to mostly positive — revealing that the feature's expected
"risk-role → lower value" relationship, the **Phase 13.3 basis for promoting te_v3**, was
**largely a contamination artifact**.

## Verified evidence (both lanes, reproduced)
- `tests/contract/test_phase13_te_model_change.py::test_te_run_records_negative_role_risk_coefficients`
  asserts the `te_role_is_risk_profile` coefficient is < 0 across all 4 walk-forward folds.
- `WalkForwardDriver(position="TE")` reads the **real seed** `app/data/training/engine_b_features_v2.csv`.
- Coefficient per fold (te_role_is_risk_profile):
  - **Pre-T2 (contaminated seed `623122a`):** `[-0.0062, -0.0997, -0.2044, -0.2531]` — all negative → test passed.
  - **Post-T2 (deduped seed `04dc0f1`):** `[+0.1000, +0.1261, +0.0456, -0.0290]` — 3 of 4 positive → test fails.
  - Fold train sizes: 167 / 246 / 329 / 412.
- **Mechanism (Codex):** the duplicated Conklin rows had `te_role_is_risk_profile = 0` (NON-risk).
  128× copies of a non-risk TE **inflated the non-risk outcome baseline**, making the risk
  coefficient look reliably negative by contrast. On clean data, risk-profile TEs still have a
  lower *raw* mean outcome (the feature is not meaningless), but the **multivariate Ridge
  coefficient is small and unstable**.

## Ruling (David + cockpit)
1. **HARD STOP on the te_v3 retrain.** Do not retrain/promote te_v3 on a basis that has been
   shown to be partly a contamination artifact (truth over convenience; be right, not fast).
2. **Do NOT silently flip the contract test to pass.** The all-negative invariant is no longer
   valid evidence after dedup; flipping it would hide the finding.
3. **Interim test handling:** `xfail(strict=True)` with a reason linking to this record and an
   explicit removal condition (remove when the feature-validity review resolves the invariant).
   Keeps the branch CI-honest (draft PR #84) without a silent pass; `strict=True` forces a
   revisit if the test ever passes again.
4. **T1 + T2 stand.** The crosswalk fix and the deduped seed are correct; the contamination was
   real and the dedup is the right fix. This finding is a *consequence we must honor*, not a
   reason to revert the data fix.

## Deferred review scope (open initiative)
- Is `te_role_is_risk_profile` a valid signal on clean data? Characterize the raw risk-row vs
  non-risk-row outcome gap, the multivariate contribution, and stability across folds/seasons.
- Does te_v3's Phase 13.3 promotion still hold on clean data, or does te_v3 need re-derivation
  (with the feature re-validated, re-weighted, or dropped) and re-promotion through the gates?
- Only after that review: the te_v3 retrain (T3) + the contract-test invariant disposition.

## Process note
T2's commit (`04dc0f1`) carried this failing contract test uncaught — the Q5 acceptance ran a
focused matrix, not the full suite. Mid-build full-gate runs catch deferred failures on locked
surfaces (the focused-slice verification gap). The retrain S0 pre-check is what surfaced it.
