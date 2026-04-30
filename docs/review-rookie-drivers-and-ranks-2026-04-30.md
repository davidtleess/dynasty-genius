# Rookie Driver Attribution and Class Ranks Review — Session B (2026-04-30, second pass)

Subject: commit `fbe005e` ("Add rookie driver attribution and class ranks") on `agent/modeling-backend`, currently shared by `agent/product-strategy` after fast-forward.

Reference contract: `docs/decision-output-contracts.md` (Rookie decision card, `top_drivers`, class ranks).
Prior review: `docs/review-rookie-evaluator-2026-04-30.md`.

## TL;DR

**Recommend NO-MERGE for this commit as written.**

`top_drivers` ships a `direction` field that contradicts the prospect-level direction David's framework would expect — for **every realistic WR and RB profile**, the structured output reads "age hurts this prospect" and "draft capital barely matters", which is the inverse of David's stated mental model. The fix is small and local; it should land before this code moves further. `class_overall_rank` and `position_class_rank` are correct and useful and should ship as-is once `top_drivers` is fixed. Provisional notes are loud about *what* but not loud about *the one subtlety that actually causes the misread*.

## Method

I traced what `top_drivers` produces on real prospects using the saved coefficients in `app/data/models/runs/20260430T132748Z/<POS>_metadata.json`. The runtime crashed (sklearn/numpy version drift between the worktree-shared `venv` and the pickled artifacts), but the coefficients and intercepts are directly available, so I computed `coef × feature_value` on paper for representative prospects.

**WR coefficients:** `pick=-0.0356, round=+0.0274, age=-0.813, intercept=+28.26`
**RB coefficients:** `pick=-0.0309, round=-0.9155, age=-0.3886, intercept=+23.84`

## Worked examples

### A: Top-5 WR, age 21 (textbook elite WR profile per David's framework)

| Driver | `coef × feature` | Reported `direction` | Implied story |
| --- | --- | --- | --- |
| `model_baseline` | +28.26 | positive | "Most of this score is the position baseline." |
| `age_at_entry` | -0.813 × 21 = **-17.07** | **negative** | "Age dragged the score down." |
| `draft_capital` | -0.0356×5 + 0.0274×1 = -0.15 | negative | "Draft capital barely moved the score." |

Sorted by `abs(contribution)`: `model_baseline` > `age_at_entry` > `draft_capital`.

David's framework reading of an age-21 top-5 WR: "elite profile — draft capital is the dominant positive signal, age is a positive signal, this should be a top-of-class rookie." The structured `top_drivers` output tells him the opposite on three of three driver lines.

### B: Late WR, pick 160, age 24 (poor profile)

| Driver | `coef × feature` | Reported `direction` |
| --- | --- | --- |
| `model_baseline` | +28.26 | positive |
| `age_at_entry` | -0.813 × 24 = **-19.51** | **negative** |
| `draft_capital` | -0.0356×160 + 0.0274×5 = -5.56 | negative |

Same prospect-direction problem: the `negative` direction on `age_at_entry` for an age-24 WR is correct for "age is a problem" — but it's emitting `negative` for the age-21 WR for the same arithmetic reason, so the field can't actually distinguish the two cases for the reader.

### C: Top-10 RB, age 21

| Driver | `coef × feature` | Reported `direction` |
| --- | --- | --- |
| `model_baseline` | +23.84 | positive |
| `age_at_entry` | -0.3886 × 21 = **-8.16** | **negative** |
| `draft_capital` | -0.0309×8 + -0.9155×1 = -1.16 | negative |

Same pattern.

## Blocking issues

### B1. `direction` for `age_at_entry` is a constant for almost all prospects

Because `coef_age` is negative for every position and `feature_value` (age) is always positive (and bounded ~20-26), `coef × age` is always negative. The reported `direction: negative` therefore does not vary with whether the prospect's age is a *positive* or *negative* dynasty signal.

This is the contract drift identified in the previous review's follow-up #4: the contract specified the transitional formula as `coef × (feature − feature_mean)`. The current implementation uses `coef × feature` (raw, uncentered). With centering:

- Age-21 WR (mean ≈ 22.5): `-0.813 × (21 − 22.5) = +1.22` → **positive**
- Age-26 WR: `-0.813 × (26 − 22.5) = -2.85` → **negative**

Centered attribution gives David a `direction` field that means what he expects: positive when this prospect's age is a *better-than-average* dynasty signal, negative when worse.

**Why this is product-safety, not styling:** the `direction` field is a structured signal David could read in any future card, table, or filter. Today it sometimes does not vary across prospects with opposite real-world dynasty signals. That's the "fake precision" failure mode David's framework Rule 7 explicitly forbids.

### B2. `model_baseline` (intercept) is the largest "driver" on every WR/RB/TE card

The intercept is a constant per position (~28 for WR, ~24 for RB). In every real prospect, it's larger in absolute value than any per-feature contribution, so the `top_drivers` list is almost always sorted with `model_baseline` first. That tells David nothing about *this* prospect — every WR has the same intercept — and crowds out actually-distinguishing signals.

Two acceptable resolutions:

1. Drop `model_baseline` from `top_drivers` entirely. The intercept is a position-level constant, not a per-prospect explanation. Rename it `position_baseline` and emit it as a separate top-level field on the response if it's useful, but don't list it as a driver.
2. Keep it but never let it occupy the first slot — sort by `abs(contribution)` only across non-baseline terms.

Option 1 is cleaner. Option 2 papers over the issue.

### B3. Combined effect: `top_drivers` directly contradicts David's stated framework

David's framework, Rule 3: *"Draft Capital First, Landing Spot Last."* And, more emphatically: *"NFL Draft Capital (Pick Position) — the single most predictive variable in dynasty football, bar none."*

What David's UI/API will currently say for a top-5 WR at age 21:

> 1. model_baseline +28.26 (positive)
> 2. age_at_entry -17.07 (negative)
> 3. draft_capital -0.15 (negative)

This communicates "draft capital barely matters; age is hurting this prospect; the score is mostly a baseline." That is the inverse of what David's framework says. Even with the loud `notes` strings explaining methodology, a structured field set this misleading is the kind of premature surface our own product-strategy doc warns against.

I'm calling this a blocker because:

- The contract specified the centered formula. The implementation deviated. That's a contract bug, not a contract ambiguity.
- Both root causes (uncentered attribution, intercept-as-driver) are small fixes — they don't require new data sources, new training, or schema changes.
- Letting this land in `main` and then "fixing it later" is exactly the failure pattern the product-strategy doc names: shipping a product surface that is more confident than the model warrants.

## Non-blocking improvements

### N1. Sort key for `class_overall_rank` is `predicted_y24_ppg`, not `dynasty_value_score`

Today these are equal (`dynasty_value_score == round(predicted_y24_ppg, 1)`). When the unified value layer normalizes the score in a future iteration, the ranks would silently lag if the sort key isn't updated. Switch the sort key to `dynasty_value_score` now to harden the contract. One-line change.

### N2. `class_overall_rank` does not account for positional scarcity

A WR with 11 PPG outranks a TE with 7 PPG even though, per David's framework, the TE is often the more valuable dynasty asset due to scarcity. This is acceptable as a transitional limitation — the unified value layer is the right place to fix it — but it should be **loudly disclaimed** in `notes`. Suggested: `"class_overall_rank uses raw model PPG and does not yet account for positional scarcity; cross-position comparison is provisional."`

### N3. `risk_flags` and `counter_argument` still boilerplate

Carried over from prior review (#2 and #3). Not addressed in this commit. Acceptable as a future-iteration item, but worth re-flagging because `top_drivers` was added without its companion per-prospect risk derivation, so the explanation triad (drivers + risk_flags + counter_argument) is one-third wired and two-thirds boilerplate. The full product value of the explanation surface is not delivered until all three are per-prospect.

### N4. Provisional notes — loud about everything except the one thing that actually misleads

The two new note strings:

- `"top_drivers and per-prospect risk_flags are provisional this iteration"`
- `"top_drivers are Ridge coefficient terms from the current sparse model; pick and round are combined as draft_capital because they are collinear."`

These cover provenance and collinearity. They do **not** warn that:

- `direction` is the sign of `coef × feature_value`, not whether the feature is above or below average for the position; therefore `direction` may not match dynasty intuition.
- `model_baseline` is a constant per position and will dominate the magnitude of every driver list.

If B1 and B2 are not addressed in code, those two facts must be added to `notes` before merge — but my recommendation is to fix them rather than ship them with disclaimers.

### N5. `display_precision: 1` vs. `contribution: round(..., 3)`

Driver contributions are rounded to 3 decimals while `dynasty_value_score` and projections are rounded to 1 decimal (per `display_precision`). Three-decimal contributions imply more precision than the underlying RMSE supports (WR RMSE = 4.11). Consider rounding contributions to `display_precision` too. Cosmetic, not blocking.

## What's good

- `position_class_rank` and `class_overall_rank` are correctly computed: sort by predicted PPG descending, walk in order, increment a per-position counter, assign 1-indexed ranks. Algorithm is right.
- The `top_drivers` schema (`{feature, contribution, direction}` × 3, sorted by `abs(contribution)`) matches the contract shape.
- Combining `pick` and `round` into a single `draft_capital` driver is the right call, and the `DRIVER_ATTRIBUTION_NOTE` documents why.
- `PROVISIONAL_DYNASTY_VALUE_NOTE` and `PROVISIONAL_DRIVERS_NOTE` are exactly the two extra notes requested in the previous review's "Mark provisional" section.
- No banned fields reintroduced; the deferred fields stay correctly null/gated.

## Suggested fix sketch (for Session A to action)

The fix is local to `app/services/rookie_evaluator.py` and one training-time addition.

1. **Persist position-level feature means at training time.** In `train_models.py`, after fitting, save `feature_means: {pick: ..., round: ..., age: ...}` into each `<POS>_metadata.json`. Re-run training to refresh metadata; pickles do not need to change.
2. **Use centered attribution in `_top_drivers`.** Replace `coef × feature_value` with `coef × (feature_value − feature_mean)` for `pick`, `round`, and `age`. `draft_capital` becomes the sum of the centered `pick` and `round` terms.
3. **Drop `model_baseline` from the drivers list.** The intercept is a constant; it doesn't belong in a per-prospect explanation. Optionally expose it as a separate top-level `position_baseline` field if useful for diagnostic curl-ing.
4. **Add a notes string** describing the centered formula explicitly: `"top_drivers are coef × (feature − position_mean) terms; positive direction means this prospect's feature is better than the position's training-set average."`

After that, this turn's worked examples become:

- Age-21 WR: `age_at_entry` direction → `positive` (better than mean), `draft_capital` direction → `positive` and largest absolute contribution.
- Age-26 WR: `age_at_entry` direction → `negative`, `draft_capital` direction → depends on pick.

That is the field semantics David's framework expects.

## Merge recommendation

**NO-MERGE** for `fbe005e` until B1 and B2 are addressed. B3 follows automatically once those land. Class ranks (the second half of the commit) are correct and should ride along with the fix.

Severity context: this is the first iteration where the rookie response carries a structured per-prospect *explanation* surface. The product cost of shipping a wrong-direction explanation to David is meaningfully higher than the engineering cost of fixing it before it lands in `main`.

## What was not changed

No code changes were made by Session B in this review. The driver-attribution and metadata-mean changes belong in Session A's modeling lane (`train_models.py` + `rookie_evaluator.py`). Tracking this review on `agent/product-strategy` as a follow-up doc; Session A should pick up the fix on `agent/modeling-backend`.

`docs/mission-recalibration-2026-04-29.md` was not touched (still has the pre-existing local modification in this worktree).
