# Rookie Evaluator Output Review — Session B (2026-04-30)

Subject: `app/services/rookie_evaluator.py` and `app/api/routes/rookies.py` at commit `5428bba` ("Wire rookie outputs to valuation contract").

Reference contract: `docs/decision-output-contracts.md` (Common envelope + Rookie decision card).

## TL;DR

**Recommend merge.** The output is product-safe: every field the contract bans is gone, every required deferral is honored, and humility is loud. The remaining gaps are quality/coverage gaps against the contract, not product-safety bugs. They should be tracked as follow-ups rather than blockers.

## What is product-safe (good)

These were the riskiest things to get right. Session A got them right.

1. **`confidence` (the pick-bucket field) is gone.** A `notes` entry says so explicitly: `"Legacy confidence was pick-bucket logic and is intentionally not emitted."` This was the single most misleading legacy field; its removal is the most important product-safety win in this commit.
2. **`dynasty_tier` is renamed to `projected_outcome_band` and gated.** The band only emits when `model_grade not in {"D", "unvalidated"}`, exactly matching the contract rule. With current models, WR/RB/TE meet the gate and QB does not — which is correct: QB has R² = −0.208 on holdout.
3. **`confidence_band` is `null`.** Numeric uncertainty is correctly deferred until calibrated quantile error exists.
4. **`model_grade` is conservatively floored at C even when R² ≥ 0.30.** WR's R² = 0.408 would qualify for grade A under the contract's literal thresholds, but the code keeps it at C because coverage_80 is not yet calibrated. The inline comment makes this intentional. This is exactly the right call: A-grade language without calibration coverage would invite false confidence. Keep it.
5. **`threshold_flags` keys all present, with `null` for not-yet-ingested inputs.** Frontend can distinguish "input missing" from "input present and false". Matches contract.
6. **`roster_fit_signal: "unknown"`, `market_overlay: null`** — correctly placeholdered, fields reserved.
7. **Display precision = 1.** With WR RMSE = 4.11 and TE RMSE = 2.15, one decimal is honest; sub-decimal precision would imply differences smaller than RMSE matter.
8. **`engine`, `signal_completeness`, `horizon_years`, `model_version` envelope fields all present.** Loaded from the latest pointer / metadata, not hardcoded.
9. **`source_projection` retains the raw `predicted_y24_ppg`** so model output is traceable.
10. **`notes` are loud about model limits** ("predicts aggregate Y2-Y4 PPG, not calibrated year-specific projections").

## Blocking issues

None.

I looked specifically for: misleading certainty, fake confidence numbers, removed fields sneaking back in, model_grade overstating fit, banned verdict/tier language, or projections presented as horizon-specific when they aren't.

The closest call was `projection_1y == projection_2y == projection_3y == dynasty_value_score` (see Non-Blocking #1), but the loud `notes` entry mitigates it for an internal API. Not a blocker.

## Non-blocking improvements (track for next iteration)

In rough priority order.

### 1. `projection_1y/2y/3y` are all the same number

The model predicts an aggregate Y2-Y4 PPG, but the response copies that single number into all three horizon fields. There is a `notes` entry that flags this, which is enough for an internal-only API today, but the field structure still presents three numbers that look horizon-specific.

**Risk:** any future UI that lays out three projection columns will visually imply three independent estimates. The mitigation note will not survive that translation.

**Suggested fix:** add a top-level field like `"projection_horizon_label": "y2_y4_aggregate"` so the shape is self-describing without removing the contract-required fields. Alternative: leave `projection_1y/2y/3y` populated but also emit `projections_are_aggregate: true`. Do not change the field set yet — that is a contract decision.

### 2. `risk_flags` is model-level boilerplate, not per-prospect

Every prospect today gets `risk_flags = ["draft_capital_age_only"]`. That describes the model, not the prospect. The contract specifies `risk_flags` as the per-prospect counter-argument input, with examples like `"age_above_wr_23_line"`, `"low_draft_capital"`, `"crowded_depth_chart"`.

**Risk:** the field's product purpose (give David a per-prospect steel-manned counter-argument, per his own framework Rule 4) is lost. A boilerplate flag also trains the user to ignore the field.

**Suggested fix:** derive risk flags from the existing `threshold_flags` and pipeline metadata — e.g. emit `"age_above_wr_23_line"` when `threshold_flags.age_below_position_line == False`, `"low_draft_capital"` when `pick > 96`, `"low_holdout_sample"` when the position's `holdout_rows < 20`. Keep the model-level caveat too, but move it to `notes` or a separate `model_caveats` array.

### 3. `counter_argument` is identical for every prospect

Same root cause as #2. Currently a hardcoded string. Once `risk_flags` is per-prospect, `counter_argument` should template from those flags (no LLM, just a fixed mapping).

### 4. `top_drivers` is missing entirely

The contract specifies `top_drivers: [{feature, contribution, direction}]` as a required field. The current Ridge model has saved coefficients in `<POS>_metadata.json` (e.g. `WR: pick=-0.036, round=+0.027, age=-0.813`) and the contract's transitional rule is `coef * (feature - feature_mean)`. Implementation is straightforward and within the existing model.

**Caveat for the implementer:** the WR `round` coefficient is positive due to collinearity with `pick`. Surfacing raw coefficient × deviation as a "driver" without a guardrail will sometimes show "later round → higher score" which will confuse a reader. Either combine `pick`+`round` into one `draft_capital` driver, or document the collinearity in a `notes` entry on cards where `round` flips direction.

### 5. `position_class_rank` and `class_overall_rank` missing in `score_draft_class`

Decisions in a rookie draft are comparative, not absolute. The contract requires both ranks. Current code only sorts the list. Adding ranks is one pass over the sorted result.

### 6. Field duplication: `valuation` and `validation` nested blocks

The current response carries:

- `model_version` at top level AND inside `valuation`
- `model_grade`, `rmse_position_holdout`, `r2_position_holdout` at top level AND inside `validation`
- `notes` at top level AND inside `valuation`
- full `DynastyValuation` dump as a `valuation` field

The flat envelope from the contract was deliberate. Two parallel sources of truth invite drift (e.g. `score_draft_class` already has to manually sync `result["valuation"]["name"] = p["name"]`).

**Suggested fix:** remove the nested `valuation` and `validation` blocks. Keep `source_projection` as the only nested block (it's a small named container for the raw model output). All other envelope fields stay flat.

### 7. `validation_report.json` shape vs. the contract

Contract specified `per_position` as a dict; Session A wrote `positions` as a list. The runtime code adapted to the list form, which works, but it's a contract drift. Either update `decision-output-contracts.md` to match the list-of-objects shape, or normalize at training time. Not user-visible; tracked here so it doesn't accumulate.

### 8. Model grading thresholds

The current grader collapses every non-negative R² to `C` because coverage_80 isn't computed. That is the right product-safety choice today. Once Session A adds bootstrap or quantile intervals and per-position calibration coverage, the grader can reach the full A/B/C/D ladder from the contract. Until then, leave it as-is.

## Should anything be renamed, removed, or marked provisional before merge?

- **Rename:** none required.
- **Remove:** none required as a blocker. The nested `valuation` and `validation` blocks should be removed in a follow-up (Non-Blocking #6) but their presence is not misleading.
- **Mark provisional:** the existing `notes` strings already do this for `dynasty_value_score`, projections, and `confidence_band`. Two extra notes would be cheap and worth adding in a follow-up:
  - `"dynasty_value_score is provisional pre-normalization Engine A output; not yet on a unified Engine A/Engine B scale."`
  - `"top_drivers and per-prospect risk_flags are not yet emitted; counter_argument is model-level boilerplate this iteration."`
  These two would close the gap between what the response promises and what it currently delivers.

## Are legacy compatibility fields acceptable?

Mixed.

**Acceptable as transitional legacy:**

- `position`, `pick`, `round`, `age` at top level — clients still want them; harmless duplicates of input echo.
- `age_at_entry` (alongside `age`) — the contract uses `age_at_entry`; emitting both during a rename window is fine.
- `predicted_y24_ppg` — the model's raw output is genuinely useful for debugging; keep, but it is already inside `source_projection`, so the top-level copy is duplicative. Mild noise, not confusion.

**Not legacy — actually new duplication:**

- The `valuation` block (full `DynastyValuation` dump) and the `validation` block. These didn't exist in the prior shape; they're new envelopes that mirror the flat top-level envelope. They are the duplication concern in Non-Blocking #6, not legacy.

Net assessment: legacy fields are fine and small. The duplication risk is the new nested blocks, not the legacy fields.

## Recommended merge decision

**MERGE.**

Rationale:

- Every banned field is gone (`confidence`, `dynasty_tier`, verdict-style language).
- Every deferred field is correctly null/gated (`confidence_band`, `projected_outcome_band` for QB, `market_overlay`, `roster_fit_signal`).
- Model humility is structurally enforced: `model_grade` floors at C without calibration coverage; WR's tempting R² = 0.408 doesn't get inflated to grade A.
- The remaining gaps are coverage and quality, not product-safety. They can be queued without blocking forward progress.

Suggested follow-up issues (in priority order, each maps to a section above): top_drivers (4), per-prospect risk_flags + counter_argument (2 + 3), projection horizon labeling (1), class ranks (5), field duplication cleanup (6), validation_report shape alignment (7), notes additions for `dynasty_value_score` and missing fields ("Mark provisional" above).

## What was NOT changed

No code changes were made by Session B in this review. The user asked Session B to make code changes only for clear product-safety bugs; there were none. All findings are tracked here for the next code-change session to pick up.

`docs/mission-recalibration-2026-04-29.md` was not touched (per instruction; it has a pre-existing local modification).
