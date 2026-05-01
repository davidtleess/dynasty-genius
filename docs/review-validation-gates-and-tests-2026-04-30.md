# Validation Gates and Lock-Safety Tests Review — Session B (2026-04-30)

Subject: `agent/modeling-backend` ahead of `main` by three commits:

- `7394930` Implement composite validation grading and report contract.
- `ebb6455` Add backend safety contract pytest coverage.
- `b71c91c` Document football-aware composite model grading.

Cycle: **Lock Safety Contracts** (5 new pytest files) and **Football-aware Composite Grading**
(`docs/decision-output-contracts.md` validation report contract, `app/data/pipeline/train_models.py` grading,
new validation report `app/data/models/runs/20260501T014544Z/validation_report.json`,
`app/services/rookie_evaluator.py::_validation_metadata` switching from re-derivation to report load).

Reference contract: `docs/decision-output-contracts.md` § "Validation report contract" + § "Rookie decision card".
Prior reviews: `docs/review-rookie-evaluator-2026-04-30.md`, `docs/review-rookie-drivers-and-ranks-2026-04-30.md`,
`docs/review-trade-quarantine-2026-04-30.md`, `docs/review-roster-auditor-2026-04-30.md`.

## TL;DR

**Recommend MERGE.** The composite grade table is internally consistent, the position ceilings are defensible
(slightly conservative for WR/RB, realistic for TE/QB — biased toward the safe error of cautious grading),
the validation report shape matches the contract, all four football caveats fire as advertised on the current
holdout data, and the rookie evaluator no longer re-derives the grade. The five new tests all genuinely lock
the regressions they advertise (verified by tracing each assertion against its target bug). Non-blocking
follow-ups are documentation polish and a few test gaps that catch *most* but not every drift case.

I ran the test suite on `agent/modeling-backend` with the cycle's `pytest==8.4.2`: **9 passed in 14.34s**.

## Method

1. Diffed `main..agent/modeling-backend` (20 files, +642/−33).
2. Read the new validation report, `train_models.py`, and the report-loading path in `rookie_evaluator.py`.
3. Traced each cycle-specific verification item against the actual code/data.
4. Walked the four grade rows for overlap and gaps.
5. Cross-checked position ceilings against published rookie projection model performance (PFF, PlayerProfiler,
   4for4, Football Outsiders QBASE/KUBIAK-style work).
6. Read each new test, then reasoned about which specific regression each assertion would and would not catch.
7. Ran the rookie evaluator at runtime against the current report to verify per-position grade, caveats, and
   `projected_outcome_band` suppression behavior.

## 1. Composite grade contract — internal consistency

The four grade rows in the new contract:

| Grade | Criteria |
| --- | --- |
| A | R² ≥ (ceiling × 0.7) AND Spearman ≥ 0.60 AND top-12 hit rate ≥ 0.50 AND holdout rows ≥ 80 |
| B | R² ≥ (ceiling × 0.5) AND Spearman ≥ 0.45 AND holdout rows ≥ 30 |
| C | R² ≥ 0.0 AND Spearman ≥ 0.0 |
| D | R² < 0.0 OR Spearman < 0.0 |

Walked through edge cases:

- Negative R², positive Spearman → fails A (R² too low) → fails B (R² < 0.5×ceiling) → matches D ✓
- Positive R², negative Spearman → matches D ✓
- R² = 0.5×ceiling, Spearman = 0.45, rows = 30 → exactly satisfies B with `≥` everywhere ✓
- R² = 0.7×ceiling, Spearman = 0.60, top-12 ≥ 0.50, rows ≥ 80 → exactly satisfies A ✓
- High-quality numbers but rows < 30 → fails A AND B → falls to C ✓
- Both signals exactly at zero → C ✓

The four rows partition the (R², Spearman, top-12, rows) space without overlap or gap (the implementation's
A → B → D → C → unvalidated fall-through in `train_models.py::_model_grade` matches the table's intent).
✓

The implementation order in `_model_grade` checks `D` *after* A and B for the negative-signal short-circuit
case. That matters because a position could in principle satisfy B's R² threshold but have a negative
Spearman — for that case the implementation correctly assigns D, not B, because B requires Spearman ≥ 0.45
which is incompatible with Spearman < 0. ✓

## 2. Position ceilings — football reality check

| Position | Cycle ceiling | Industry rookie-model R² (typical, pre-NFL features) | Read |
| --- | --- | --- | --- |
| WR | 0.50 | 0.20–0.30 baseline; 0.30–0.40 with full feature set | Slightly generous as a "true ceiling"; defensible as an aspirational target |
| RB | 0.50 | 0.20–0.30 baseline; 0.30–0.40 with landing-spot/usage proxies | Same — slightly generous |
| TE | 0.30 | 0.10–0.15 typical; rarely >0.20 even with full features | Realistic-to-aspirational |
| QB | 0.20 | 0.05–0.15 typical; very low predictability | Realistic |

The 0.50 ceilings for WR and RB are defensible but not the most conservative choice available. The
implication: a future WR run with R² = 0.35 (industry-leading) would qualify for A's R² threshold
(0.7 × 0.50 = 0.35). That is exactly where you'd want A to start — so the ceilings match a sensible
"top of plausible NFL prediction" frame.

Critically, the slight optimism biases the system toward **harder-to-reach A grades**, i.e. toward
**cautious** rather than **overconfident** grading. That is the right direction for a system whose
explicit objective is to avoid misleading certainty. If the ceilings were 0.40 instead of 0.50 for WR/RB,
the same holdout numbers that currently land WR at B would push it toward A, which would be the
*dangerous* error direction.

QB = 0.20 is realistic. TE = 0.30 is on the optimistic end of TE-rookie reality but not absurd. The
"inherent low ceiling" caveat for QB explicitly carries the same point in product-facing language. ✓

**No blocking issue.** Recommend the contract changelog gain a one-line provenance note ("WR/RB 0.50,
TE 0.30, QB 0.20 — calibrated against published rookie-projection model performance with conservative
upward bias toward cautious A-grades") so the choice is auditable and not invisible policy.

## 3. Validation report shape

Spot-checked `app/data/models/runs/20260501T014544Z/validation_report.json` against the contract's
"Validation report contract" section.

Per-position fields present in every position object (`WR`, `RB`, `TE`, `QB`):

- `train_rows` ✓
- `holdout_rows` ✓
- `rmse` ✓
- `r2` ✓
- `spearman_rank_correlation` ✓
- `top_12_hit_rate` ✓
- `bust_avoidance_rate` ✓
- `position_ceiling` ✓
- `coverage_80: null` ✓
- `model_grade` ✓
- `caveats: [...]` ✓

Top-level gates block:

```json
"gates": {
  "te_non_negative_r2": true,
  "all_positions_validated": true
}
```

✓

## 4. Football caveats actually fire

Verified against `validation_report.json`:

| Position | Holdout rows | Always-on caveat | Low-sample caveat (n < 30) |
| --- | --- | --- | --- |
| WR | 35 | none required | not fired (correct, n=35 ≥ 30) |
| RB | 19 | `rb_career_arc_capped_by_aging_cliff` ✓ | `low_sample_holdout` ✓ |
| TE | 11 | `te_population_per_class_small` ✓ | `low_sample_holdout` ✓ |
| QB | 10 | `qb_rookie_signal_inherently_low_ceiling` ✓ | `low_sample_holdout` ✓ |

All four cycle-required caveats fire as advertised, and the WR-doesn't-need-an-always-on-caveat case is
also handled correctly (empty list, not an error). ✓

I also verified at runtime that the rookie evaluator surfaces these as `model_caveats` on every record:

```text
WR grade=B caveats=[]                                                            band=Starter
RB grade=C caveats=['rb_career_arc_capped_by_aging_cliff', 'low_sample_holdout'] band=Elite
TE grade=C caveats=['te_population_per_class_small',     'low_sample_holdout']   band=Depth
QB grade=D caveats=['qb_rookie_signal_inherently_low_ceiling','low_sample_holdout'] band=None
```

The `model_caveats` field is the per-record surfacing of the per-position validation caveats. It is *not*
documented as a field in `docs/decision-output-contracts.md` § "Rookie decision card". This is contract
drift in the honest-toward-honesty direction (the implementation surfaces real explanation that the contract
forgot to spec), but the contract should be amended in a follow-up. See non-blocking improvement [B] below.

## 5. Grade is loaded, not re-derived

In `app/services/rookie_evaluator.py::_validation_metadata` on `agent/modeling-backend`:

```python
model_grade = report_metrics.get("model_grade", "unvalidated")
caveats = report_metrics.get("caveats", [])
```

The previous re-derivation:

```python
if r2 is None:
    model_grade = "unvalidated"
elif r2 < 0:
    model_grade = "D"
else:
    model_grade = "C"
```

is removed. ✓

This is the right architecture: the grade is computed once (in `train_models.py::_model_grade` from the
holdout) and read by every consumer. The service can no longer accidentally disagree with the report.

`_load_validation_report` was also updated to read the new `per_position` dict shape, with a fallback to the
legacy `positions` list shape so the loader is forward-compatible if any in-flight artifact still uses the
older shape. ✓

## 6. Tests genuinely lock the contract

Walked each new test against the specific regression it advertises:

### `tests/test_rookie_drivers.py`

- `test_top_pick_low_age_has_positive_draft_capital_direction` (WR pick=1, round=1, age=20).
  - With **centered** drivers: `coef_pick × (1 − mean_pick) + coef_round × (1 − mean_round)`. Since both
    `coef_pick` and `coef_round` are negative (lower pick = higher PPG) and `(pick − mean)` is large
    negative for pick=1, the contribution is large **positive**. Direction = "positive". ✓
  - With **non-centered** drivers (`coef × pick`): `coef_pick × 1 + coef_round × 1` is small **negative**.
    Direction = "negative". Test fails. ✓ **Test catches the regression.**
- `test_late_pick_high_age_has_negative_draft_capital_direction` (pick=220, round=7, age=25). This passes in
  both the centered and non-centered worlds (because both give a large negative contribution for a UDFA).
  By itself this assertion would *not* catch a non-centering regression, but combined with the top-pick test
  above, the pair brackets the centering invariant.
- `test_rookie_response_has_no_confidence_key`. Reintroducing `confidence` as a top-level key would fail.
  ✓ **Catches the regression.**
- `test_top_drivers_exclude_intercept_terms`. Catches a regression where the model intercept leaks into the
  driver list. ✓

### `tests/test_trade_quarantine.py`

Asserts the absence of all of `verdict`, `my_total`, `their_total`, `difference`, `experimental_totals`,
`deprecated_fields`, `my_assets_scored`, `their_assets_scored`. Reintroducing **any** of those would fail
the test immediately. ✓ Asserts `decision_supported is False`. ✓ Asserts every player asset has
`veteran_value_uses_rookie_model_proxy` and every pick asset has `pick_value_from_static_chart`. ✓
**Catches every reintroduction listed in the contract.**

### `tests/test_roster_signals.py`

- Locks the signal vocabulary to `{past_cliff, at_cliff, approaching_cliff, no_age_signal}`. Any regression
  to `trade_window_open` / `monitor` / `hold` would fail.
- Asserts `"action" not in item`. Reintroducing the legacy `action` key fails the test. ✓
- `assert "Sell now" not in str(item)` and `"Hold" not in str(item)`. Catches action language reappearing
  anywhere inside any field of the response. ✓ (Minor fragility caveat: this is a substring check; a future
  fixture player named "Holden" or a position string containing "Hold" would false-positive. None of the
  current test fixtures trigger that. Non-blocking.)
- Locks the required caveats `age_curve_only` and `no_usage_signal`. ✓

### `tests/test_roster_config_422.py`

Removes `DYNASTY_SLEEPER_USERNAME`, asserts the route returns **422** with structured payload
(`detail.error == "roster_config_error"`, `"DYNASTY_SLEEPER_USERNAME"` in `detail.message`). If the route
silently fell back to a default user/league, no 422 would be raised and the test would fail. ✓ **Catches
the regression.**

### `tests/test_validation_report_shape.py`

Locks per-position `{spearman_rank_correlation, top_12_hit_rate, bust_avoidance_rate, position_ceiling,
model_grade, caveats}` and the three football caveats (`qb_rookie_signal_inherently_low_ceiling`,
`te_population_per_class_small`, `rb_career_arc_capped_by_aging_cliff`).

**Gap [A]** (non-blocking): the cycle spec listed a longer required field set:

> `train_rows, holdout_rows, rmse, r2, spearman_rank_correlation, top_12_hit_rate,
>  bust_avoidance_rate, position_ceiling, coverage_80 (null), model_grade, caveats`
> And at the top level: `gates` block with `te_non_negative_r2` and `all_positions_validated`.

The shipped `required_fields` set in `test_validation_report_per_position_shape` is a strict subset — it
omits `train_rows`, `holdout_rows`, `rmse`, `r2`, `coverage_80`, and the top-level `gates` block. The
report itself contains all of these (verified by inspection), but a future regression that drops any of
them would not be caught by the test. Recommend extending the test in a small follow-up commit.

**Gap [B]** (non-blocking): `test_validation_report_position_caveats` does **not** assert
`low_sample_holdout` for positions with `holdout_rows < 30`. Today RB/TE/QB all have `low_sample_holdout`
in the report, but a regression that removed the auto-fire (`if holdout_rows < 30:` in `_position_caveats`)
would not be caught.

## 7. Honesty of the resulting grades

| Position | R² | Spearman | Holdout n | Grade | Cycle expectation | Read |
| --- | --- | --- | --- | --- | --- | --- |
| WR | 0.408 | 0.729 | 35 | **B** | "should land B" | ✓ Hits 0.5×ceiling=0.25 and Spearman ≥ 0.45 with n ≥ 30; misses A only because n < 80 |
| RB | 0.509 | 0.719 | 19 | **C** | implicit (n < 30 → low sample) | ✓ Falls below B's n ≥ 30; correctly carries `low_sample_holdout` |
| TE | 0.197 | 0.545 | 11 | **C** | implicit (n < 30 → low sample) | ✓ Same; correctly carries `low_sample_holdout` |
| QB | −0.208 | 0.517 | 10 | **D** | "land D *and* surface inherent-low-ceiling caveat" | ✓ D triggered by R² < 0; `qb_rookie_signal_inherently_low_ceiling` AND `low_sample_holdout` both surface |

The QB-specific verification ("the surface should explain why D, not just emit D") is satisfied: the
service exposes `model_grade: "D"` together with `model_caveats: ["qb_rookie_signal_inherently_low_ceiling",
"low_sample_holdout"]` on every QB record, plus suppresses `projected_outcome_band` so the consumer cannot
display a tier label for a D-grade QB.

The RB R²=0.509 number is suspiciously high for 19 rows on draft-capital-only features — that is almost
certainly noise. The fact that it lands C instead of B because of the row-count gate is exactly the right
behavior; the row-count gate is doing the work of catching false confidence here. The grading scheme is
robust to small-sample noise. ✓

No false confidence detected. No false pessimism detected.

## 8. Existing safety rules still hold

- `projected_outcome_band` is suppressed when grade is D or unvalidated.
  Verified at runtime: QB (D) → `band=None`. WR (B), RB (C), TE (C) all emit. ✓
- Roster and trade still use the heuristic envelope.
  `git diff main..agent/modeling-backend -- app/services/trade_analyzer.py app/services/roster_auditor.py app/api/routes/roster.py`
  is empty. No code change in the experimental surfaces this cycle. ✓
- No new decision-grade claim has appeared in any user-facing surface.
  The new `model_caveats` field is honesty-additive; the new `validation` sub-dict carries metrics
  alongside their caveats; no new "verdict", "tier", "buy", "sell", "hold" language anywhere. ✓

## 9. Subtle observations worth recording

### Top-12 hit rate is degenerate at small n

`_top_k_hit_rate(y_true, y_pred, k=12)` clamps `k = min(12, len(y_true))`. For TE (n=11) and QB (n=10),
`k = n`, so the metric trivially returns 1.0 because the predicted top-n and the actual top-n are both
"the entire holdout". That's why the report shows TE `top_12_hit_rate: 1.0` and QB `top_12_hit_rate: 1.0`
even though the underlying R² for TE is moderate and for QB is negative.

This does not affect grading: A requires `holdout_rows ≥ 80` so degenerate top-12 numbers cannot promote
a small-sample position. The metric is correctly defended against in the grade table.

But the reported number is misleading on its own. A consumer reading `validation_report.json` and seeing
QB `top_12_hit_rate: 1.0` could mistakenly read it as evidence of strong QB rookie signal. Recommend either:

1. Setting `top_12_hit_rate` to `null` when `n < 24` (k cannot meaningfully be 12), OR
2. Adding a caveat string like `top_k_hit_rate_degenerate_below_n_24` next to the metric.

Non-blocking — A is correctly defended. Worth a small clarity improvement.

### Contract has a residual self-contradiction on `projected_outcome_band` gating

`docs/decision-output-contracts.md` § Rookie decision card says:

> use `projected_outcome_band` only after `model_grade ≥ B`. While the model is `unvalidated` or `D`, omit
> `projected_outcome_band` entirely.

These two clauses disagree about C-grade. Clause 1 → only emit for A or B. Clause 2 → emit for everything
except D and unvalidated.

The implementation matches **clause 2**. The cycle's own verification item #7 also matches clause 2. So this
is consistent within the cycle, but the contract has an unresolved internal conflict. The honest reading is
either:

- (a) Suppress for C as well (stricter; what clause 1 implies). RB and TE would no longer emit
  `projected_outcome_band` until they hit B.
- (b) Allow for C (current behavior). This is more permissive but defensible because C requires positive
  R² and positive Spearman.

For the current cycle's data, (b) means TE (R²=0.197, RMSE=2.152) emits a "Depth" / "Starter" tier label
on a model whose typical error is ±2.2 PPG — i.e. the tier label can be off by at least one bucket. That's
the kind of false-precision risk this contract was written to prevent.

This issue **predates this cycle** (the suppression rule was already on `main`), so I don't block on it.
But it is the next-most-important contract follow-up, alongside item [B] below.

### `model_caveats` naming

The new field on the rookie response is called `model_caveats`. A consumer might read this as "caveats
about the model in general" rather than "caveats specifically attached to this position's grade". A name
like `grade_caveats` or `validation_caveats` would more clearly link it to `model_grade`.

This matters because the field is the *only* place a consumer can find out *why* a QB is graded D. If a
future surface reads `model_grade` but ignores `model_caveats`, the consumer gets D with no explanation.

Non-blocking; rename can land alongside the contract update.

## Blocking issues

**None.**

## Non-blocking improvements (priority order)

1. **Document `model_caveats` in `docs/decision-output-contracts.md` § Rookie decision card.** Add it to
   the rookie envelope JSON example and to the field rules table. Optionally rename to `grade_caveats` for
   clarity. (Without this contract update, a future consumer might forget to surface the per-position
   caveats and would lose the only structured explanation of why a QB is D.)
2. **Extend `tests/test_validation_report_shape.py` to lock the full required field set listed in the
   cycle spec.** Add `train_rows`, `holdout_rows`, `rmse`, `r2`, `coverage_80` to `required_fields`, and
   add a top-level assertion for `report["gates"]["te_non_negative_r2"]` and
   `report["gates"]["all_positions_validated"]`.
3. **Add an assertion in `test_validation_report_position_caveats` that any position with
   `holdout_rows < 30` carries `low_sample_holdout`.** Today's data has three such positions; a regression
   in `_position_caveats` would silently disappear without this.
4. **Add a contract changelog note explaining the position ceiling provenance** (e.g., "WR/RB ceilings of
   0.50 are conservative aspirational — they intentionally make A grades hard to reach so the system
   biases toward cautious rather than overconfident grading"). This makes the calibration auditable.
5. **Resolve the contract's internal conflict on `projected_outcome_band` for C-grade.** Pick one clause
   and remove the other. If keeping the current implementation, also add an explicit note:
   `"projected_outcome_band may be off by one bucket when model_grade == 'C' due to position RMSE"`.
6. **Mark `top_12_hit_rate` as `null` (or `degenerate_at_n_below_24`) when `n < 24`.** Prevents the
   misleading "1.0 hit rate" reading on small-sample positions. One-line change in `_top_k_hit_rate`.
7. **Consider tightening `test_roster_signals` substring checks** (`"Hold" not in str(item)`) to a
   per-field structural check rather than a stringified-dict scan, to avoid a fragile false positive when
   future fixtures or player names contain those substrings.

## Where the cycle is strong

- The grade is now computed in exactly one place (`train_models.py::_model_grade`) and read by every
  consumer — the service can no longer disagree with the report.
- The composite grade table forces both error-fit (R²) and rank-ordering (Spearman) to agree before
  awarding any positive grade, which matches dynasty draft-board reality (you care about ordering, not
  just absolute PPG fit).
- Position ceilings are calibrated in the safe direction: slight optimism makes A harder to reach, biasing
  away from false confidence. QB=0.20 + the inherent-low-ceiling caveat together create a structural floor
  that no amount of QB feature work can ever spuriously inflate to A.
- Position-specific always-on caveats (`qb_*`, `te_*`, `rb_*`) encode football reality directly into the
  validation report — these are dynasty truths (small TE class population per year, RB aging-cliff, QB
  context-dominance) that no future model improvement can erase, and the report correctly never erases
  them.
- The `low_sample_holdout` caveat is a real safety belt: today three of four positions carry it, which is
  honest about the size of holdout class 2021.
- The five new tests are not "increase coverage" tests — each one locks a specific past regression that
  this codebase has actually shipped at some point. The selection is decisively product-safety oriented.
- CI now runs pytest on push/PR (`.github/workflows/ci.yml`), so the contract locks are enforced upstream.
- Trade and roster surfaces are untouched; the cycle stayed in scope.

## Merge recommendation

**MERGE to `main`.**

Smallest concrete change set if any of this had been blocking (it isn't): if the no-merge had to be
flipped, the minimum would be (a) extend `test_validation_report_shape` to cover the full field set the
cycle spec listed including the top-level `gates` block, and (b) add the `low_sample_holdout`
auto-fire assertion. Both are < 20 lines of test code. Neither is required for this merge — the field
shape is already correct in the report and the caveat already fires correctly in the data; the gap is
only that the *test* doesn't lock those specific fields. Treat as follow-up.

## Review doc commit

This review is committed to `agent/product-strategy` at:

`docs/review-validation-gates-and-tests-2026-04-30.md`

## What was not changed

No code changes were made by Session B in this review. No contract or test changes were made by Session B
either; all proposed contract amendments and test extensions are listed as non-blocking follow-ups for
Session A or a future product review cycle.

`docs/mission-recalibration-2026-04-29.md` was not touched (still has the pre-existing local modification
in this worktree).
