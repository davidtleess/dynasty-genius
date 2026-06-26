# Spec: te_v3 Re-Derivation (drop role-risk; stability-justified) — v3 DRAFT

Date: 2026-06-26. Branch: fix/engine-b-crosswalk-fanout. Author: Claude (impl). Status: DRAFT for cockpit review → David approval → cockpit-TDD.

## 1. Context
The F-feature-refresh go-live uncovered a te_v3 training-data contamination (one player = 35.3% of TE rows; T1 crosswalk fix + T2 deduped seed shipped). The deferred feature-validity review (read-only, pre-registered) concluded — 3-way converged:
- **`te_role_is_risk_profile` is null on clean data** — re-running the original Phase-13.3 bake-off on the deduped seed: 2/4 folds, `passes_acceptance=False` (was 4/4 contaminated); ablating it leaves the model marginally better. Its Phase-13.3 justification was a contamination artifact.
- **te_v3 has no beyond-noise accuracy edge over legacy te_v2** — paired BCa CIs all cross zero (RMSE Δ −0.031 CI [−0.102, +0.054]; rank Δ cross zero).
- **The only categorical justification** for the te_v3 (α=100) form over te_v2 (α=1.0) is **G2 stability**: legacy α1.0 FAILS the ≤25% gate at 26.21%; α100 passes at 15.87%.

Finding record: `docs/validation/2026-06-26-te-role-risk-contamination-finding.md`.

## 2. Goal
Re-derive the active-player te_v3 as the **14-feature, α=100** model with `te_role_is_risk_profile` **dropped**, justified **solely by G2 regularization stability** on clean data — honestly, with the role-risk narrative abandoned. Close the T3 pause on a clean model so the F-feature-refresh sprint (T4→T6) can resume.

## 3. Scope (David + cockpit ruled)
- **CONTRACT-ONLY** (D1): drop the feature from the Engine B TE *model contract*. Do NOT touch the data pipeline (`assemble_engine_b_dataset.py` keeps computing the column; the seed keeps it computed-but-unused — training selects only contract features). Full pipeline/experiment-harness removal = a SEPARATE downstream cleanup ticket, not gating this.
- **Local-only model artifacts** (the existing gitignored pattern): the re-derived te_v3.pkl + manifest stay local; T-b commits a committed acceptance/validation report, not the binary.
- **No** market features, no `decision_supported` change (stays False), no QB/RB/WR change.

## 4. Tasks (cockpit-TDD: Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit, each)
**Ta — Contract drop (MODEL feature set only).**
- `engine_b_contract.py`: remove `te_role_is_risk_profile` from `ENGINE_B_FEATURES_TE` (15→14, the MODEL feature set). **`ENGINE_B_OUTPUT_COLUMNS` and `ENGINE_B_ALLOWED_FEATURES` stay UNCHANGED** — the column is still a computed builder output (contract-only; pipeline untouched [Codex C4]). Keep `te_role_is_risk_profile` in `ALLOWED_FEATURES` (it remains a legitimate computed column, just not a TE model input).
- Test updates — only the CONTRACT-set assertions change:
  - `tests/test_engine_b_contract.py` + `test_phase13_te_model_change.py`: update the `ENGINE_B_FEATURES_TE` membership assertions to the 14-feature set. [Codex: it's `test_engine_b_contract.py`, NOT `test_feature_validation.py`; leave the feature-validation fixture unchanged.]
  - `test_feature_engineering_extraction.py`: **UNCHANGED** — it asserts the builder still *computes* `te_role_is_risk_profile` (still true; pipeline untouched). [Codex C4]
  - `test_phase13_te_model_change.py::test_engine_b_output_columns_preserve_existing_dataset_gate_columns`: UNCHANGED (the column stays in `ENGINE_B_OUTPUT_COLUMNS`).
- **DELETE** `test_te_run_records_negative_role_risk_coefficients` (D2) + strip the now-orphaned `import pytest` (ruff F401). The feature-list parity tests already guarantee model-set absence; deletion + commit-msg + record is the honest path; removes the xfail.
- RED: `ENGINE_B_FEATURES_TE` == the 14 features (no role-risk); `ENGINE_B_OUTPUT_COLUMNS` + builder output unchanged; deleted/updated tests green; ruff clean.

**Tb — Re-derive te_v3 + formal revalidation. ORDER: validate-gates-FIRST, then deploy [Codex].**
- Fix `train_engine_b.py:151` (`features.index("te_role_is_risk_profile")` + its coef reporting) — guard/remove (only code break from the contract drop).
- **Tb.1 REVALIDATE FIRST** — `.venv/bin/python3.14 scripts/run_backtest.py --position TE --model engine_b_v3_te_rederived_clean --output-dir /tmp/te_v3_rederived_backtest` (the WalkForwardDriver refits per fold; it does NOT load a deployment .pkl). Gate (REQUIRED; a fail is itself a finding, not an auto-pass) [Codex C3]: **G1 rank-corr PASS, G2 stability ≤25% PASS, `overall_grade="ACTIVE_B"`, G3 DEFERRED**.
- **Tb.2 DEPLOY ONLY IF Tb.1 PASSES** — `train_engine_b.py --mode v2_stratified --position TE` on the deduped seed → new run (14f/α100 te_v3.pkl) + manual `v2_manifest.json` TE-pointer update (local). No deployment artifact is written before the gates pass.
- `decision_supported=false` is NOT a `run_backtest.py` artifact field [Codex] — it is asserted in OUR committed report + decision record (§ below), where it stays False.
- Committed acceptance report → `docs/validation/2026-06-26-te-v3-rederivation-report.json`. Sections [Codex C1]: `provenance` (old/new manifest+pkl+seed sha256, run id, 14-feature list), `gates` (G1/G2/G3/overall_grade verbatim from the backtest result), `metrics` (OLD-vs-NEW RMSE/Kendall/Spearman), `accuracy_vs_te_v2` (the BCa within-noise note), `justification` ("G2 stability only; role-risk dropped as contamination artifact"), `decision_supported: false`, `caveats` (local-only model artifact).
- **NO-PVO BOUNDARY [Codex C5]:** Tb does NOT regenerate `universe_pvo_latest.json` or any PVO/decision-surface artifact. Live TE valuations refresh only via the separate PVO regen (T3b), David-gated. Tb = model + manifest (local) + committed report ONLY.

**Tc — Records + supersession (D4).**
- New record `docs/validation/2026-06-26-te-v3-rederivation-decision.md`: top line "SUPERSEDES `phase13-3-3-te-role-risk-decision.md` and `phase13-3-te-promotion-decision.md`, invalidated by the Tyler Conklin data contamination." Honest: role-risk dropped as a contamination artifact; accuracy within BCa noise; justified entirely by G2 stability (α100) on clean data; `decision_supported=False`.
- Add a SUPERSEDED warning block atop the two old Phase-13 docs linking the new record (preserve, do not delete).

**Then:** F-feature-refresh sprint resumes — T4 gate-semantic correction → T5 scheduler Option B → T6 go-live — on the clean re-derived model.

## 5. Acceptance / guardrails
- TE contract is exactly the 14 features; no role-risk in any TE model X matrix.
- te_v3 re-derived (14f/α100); G1 PASS + G2 ≤25% PASS on clean data (else STOP + report).
- Full suite green (no silent xfail; the obsolete test deleted, not flipped). `ruff src app` clean.
- No pipeline/seed/market/`decision_supported` change; model artifacts local; records superseded honestly.
- No buy/sell/overclaim; stability-only justification stated; accuracy-within-noise disclosed.

## 6. Open questions — RESOLVED (v2/v3)
- Q1 `ENGINE_B_ALLOWED_FEATURES`: **KEEP** `te_role_is_risk_profile` (still a computed column; contract-only). [§4 Ta]
- Q2 Revalidation command + acceptance: `run_backtest.py --position TE`; G1 PASS + G2 ≤25% PASS + `overall_grade=ACTIVE_B` + G3 deferred + `decision_supported=false`. [§4 Tb, Codex C2/C3]
- Q3 Orphaned `import pytest` after deleting the xfail test: **stripped** (ruff F401). [§4 Ta]
