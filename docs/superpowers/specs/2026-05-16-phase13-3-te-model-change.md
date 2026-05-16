---
document: TE Role-Risk and Regularization Model-Change Spec
version: 1.0.0
status: DRAFT — PENDING DAVID APPROVAL
date: 2026-05-16
owner: David
prepared_by: Claude
phase: 13.3
evidence_artifacts:
  - app/data/backtest/phase13/te_role_risk_experiment_20260516.json
  - app/data/backtest/phase13/te_regularization_bakeoff_20260516.json
decision_notes:
  - docs/validation/phase13-3-3-te-role-risk-decision.md
  - docs/validation/phase13-3-4-te-regularization-decision.md
governance_read:
  - docs/governance/02-agent-operating-loop.md
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - AGENT_SYNC.md
---

# TE Role-Risk and Regularization Model-Change Spec

Phase 13.3 — Production Implementation Authorization

## 1. Decision Summary

Two changes to the TE Ridge model are jointly authorized:

1. **Regularization correction:** increase alpha from 1.0 to 100.0.
2. **Role-risk feature:** add `te_role_is_risk_profile` as a single binary penalty feature.

TE remains `EXPERIMENTAL` until the retrained model passes the walk-forward promotion gates defined in Section 4. Updating the manifest and removing the EXPERIMENTAL flag are conditional on gate pass — they are not part of the initial implementation.

## 2. Evidence Basis

### Phase 13.3.3 — Role-Risk Controlled Experiment

- `unified_penalty` improved RMSE and MAE in 4/4 folds at alpha=1.0 (mean RMSE delta −0.0392, mean MAE delta −0.0518) and had a negative coefficient.
- Both candidates failed the rank-degradation gate at alpha=1.0.
- At sensitivity alpha=100.0, `unified_penalty` passed all gates — establishing that the signal is real but the TE model is under-regularized.

### Phase 13.3.4 — Regularization Bake-Off

Anchor: alpha=1.0, baseline features only.

| alpha | candidate | RMSE delta | MAE delta | Rank gate | Passes |
|-------|-----------|------------|----------|-----------|--------|
| 1.0 | unified_penalty | −0.0452 | −0.0527 | FAIL | No |
| 10.0 | unified_penalty | −0.0753 | −0.0919 | FAIL | No |
| 50.0 | unified_penalty | −0.0927 | −0.1042 | FAIL | No |
| **100.0** | **unified_penalty** | **−0.0959** | **−0.1040** | **PASS** | **Yes** |
| 250.0 | unified_penalty | −0.0782 | −0.0872 | PASS | Yes |
| 500.0 | unified_penalty | −0.0345 | −0.0520 | PASS | Yes |

`unified_penalty` at alpha=100.0 (fold-vs-same-fold-baseline deltas, 4 folds 2020–2023):
- RMSE improvement: 4/4 folds. Mean fold delta −0.0404. Smallest fold −0.0080 (no outlier dependency).
- MAE improvement: 4/4 folds. Mean fold delta −0.0459.
- Rank gate: max Spearman delta −0.0115, max Kendall delta −0.0161. Both above −0.02 floor.
- Coefficient: −0.199 (negative, stable across all folds).

alpha=100.0 is selected over 250.0 and 500.0: it produces the largest absolute error improvement while passing all acceptance gates.

## 3. Authorized Changes

### 3.1 Feature: `te_role_is_risk_profile`

**Definition:**

```python
te_role_is_risk_profile = int(
    (te_role_role_risk == 1) or (te_role_blocking_specialist == 1)
)
```

**Source artifact:** `app/data/identity/te_archetype_rubric_20260516.json`

**Join key:** `canonical_player_id` (Dynasty Genius identity anchor).

**Coverage note:** 105 of 116 TEs have archetype labels; 11 rows (6 PFF-excluded + 5 low_volume) have no label. For these rows, set `te_role_is_risk_profile = 0`. Do not drop, impute risk=1, or hold these rows out of training. Absence of archetype evidence is not evidence of risk.

**Materialization:** `scripts/assemble_engine_b_dataset.py` joins the rubric on `canonical_player_id` and emits the column before writing the training CSV.

### 3.2 Feature Contract

Add to the TE position feature contract in `src/dynasty_genius/models/engine_b_contract.py`:

```python
"te_role_is_risk_profile"  # binary penalty: 1 if role_risk or blocking_specialist label
```

This field is TE-only. It must not appear in the QB, RB, or WR feature contracts. The contract must include a comment identifying the source rubric artifact so the field is traceable without reading training code.

### 3.3 Model Retraining

Retrain the TE model with:

- **Alpha:** 100.0
- **Feature set:** existing nine baseline TE features + `te_role_is_risk_profile`
- **Artifact path:** a new versioned directory, e.g., `app/data/models/engine_b/runs/YYYYMMDDTHHMMSSZ/te_v3.pkl`
- **Do not overwrite** `te_v2.pkl` or any prior artifact

The manifest (`app/data/models/engine_b/v2_manifest.json`) is updated only if the model passes the promotion gate in Section 4. If the gate fails, the manifest is unchanged and TE continues to route through the existing EXPERIMENTAL fallback.

### 3.4 Files That Must Not Change

- QB, RB, WR model artifacts, alphas, or feature contracts
- PVO scoring logic or surface routing
- `decision_supported` on any surface (remains False)
- Market overlay logic and NOISE_BAND (locked at 0.10 until mid-July 2026)
- Engine A contracts or training scripts
- DVS (remains unimplemented)

## 4. Promotion Gate

After retraining, run the existing walk-forward backtest harness:

```bash
.venv/bin/python3.14 scripts/run_backtest.py --position TE --model <path_to_te_v3_pkl>
```

Apply the existing `ACTIVE_B_VALIDATED` promotion logic (pass ≥ 2 of 3 gates: RMSE, R², Spearman).

**If gates pass:**

1. Update `app/data/models/engine_b/v2_manifest.json` TE entry to point to the new artifact.
2. Remove TE from `ENGINE_B_EXPERIMENTAL_POSITIONS` in `engine_b_contract.py`.
3. Write a promotion decision note to `docs/validation/phase13-3-te-promotion-decision.md`.
4. Update AGENT_SYNC and daily ledger.

**If gates fail:**

1. Do not update the manifest.
2. Write a failure decision note recording the gate results.
3. TE remains EXPERIMENTAL on the existing fallback.
4. Do not retry with a different alpha or widen the gate — record the failure and stop.

## 5. Required Tests

1. **TE feature contract:** assert `te_role_is_risk_profile` is present in the TE required feature set and absent from QB, RB, and WR feature sets.
2. **Coverage imputation:** assert that TEs with no archetype record receive `te_role_is_risk_profile = 0` (not NaN, not dropped, not 1).
3. **Coefficient sign:** assert the trained TE model's coefficient for `te_role_is_risk_profile` is negative.
4. **Training CSV redaction:** assert that the training CSV emitted by `assemble_engine_b_dataset.py` contains no `pff_id`, `gsis_id`, `sleeper_id`, `/Users/`, `Downloads`, `grades_offense`, or `grades_pass_route` values.

Existing TE contract tests must remain green. No test may be removed or weakened.

## 6. Governance Constraints

- No raw PFF rows, raw PFF IDs, or local PFF paths may be committed at any point in this implementation.
- `te_role_is_risk_profile` is derived from the committed redacted rubric artifact, not from raw PFF data directly.
- The archetype rubric join is a feature engineering step only. The rubric remains read-only — do not modify it.
- All new artifacts are aggregate or model-level only; no player-level rows.
- PFF grade columns remain in PROHIBITED_COLUMNS and must not enter the feature matrix under any name.

## 7. Implementation Sequence

1. **Feature engineering:** update `assemble_engine_b_dataset.py` to join the archetype rubric and emit `te_role_is_risk_profile`.
2. **Feature contract:** add `te_role_is_risk_profile` to the TE contract in `engine_b_contract.py`.
3. **Tests (failing):** write the four contract tests listed in Section 5.
4. **Retrain:** run `scripts/train_engine_b.py` for TE with alpha=100.0.
5. **Validate:** run the backtest harness on the new artifact.
6. **Promote or record:** update manifest if gates pass; write a decision note regardless.
7. **Governance sync:** full test suite, AGENT_SYNC, daily ledger entry.

## 8. Out of Scope

- TE promotion before gate pass
- Any Engine A changes
- Any PFF grade columns in the feature set
- Any market-derived columns in the feature set
- DVS implementation
- QB, RB, or WR model changes
- New PFF data exports or changes to the archetype rubric
- Additional candidate features beyond `te_role_is_risk_profile`
