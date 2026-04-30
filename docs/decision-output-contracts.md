# Decision Output Contracts

Companion to `docs/product-strategy-2026-04-30.md`. This document is the canonical source for the field shape of every David-facing decision output. Engineering should treat the JSON shapes here as the API contract Session A and Session B converge on.

These contracts wrap and extend Session A's `app/models/valuation.py::DynastyValuation`. Where this doc and Session A's `DynastyValuation` overlap, `DynastyValuation` is the source of truth for `dynasty_value_score`, `confidence_band`, `projection_1y/2y/3y`, `engine`, and `model_version`. The fields below are the David-facing wrapping fields.

## Status legend

- **required** — must be present on every record.
- **deferred** — intentionally omitted until the unblocking gate is met. Emit as `null` or omit; do not fake.
- **removed** — fields that existed in earlier prototype output and are deprecated. Do not emit.

## Model valuation envelope

Model-backed David-facing endpoints return objects sharing this envelope:

```json
{
  "engine": "rookie_forecast | active_player_forecast",
  "model_version": "yyyy-mm-dd_<hash>",
  "model_grade": "A | B | C | D | unvalidated",
  "signal_completeness": "draft_capital_only | partial_pre_nfl | full_pre_nfl | nfl_year1 | nfl_multi_year",
  "horizon_years": 1 | 2 | 3,
  "dynasty_value_score": 0.0,
  "projection_1y": 0.0,
  "projection_2y": 0.0,
  "projection_3y": 0.0,
  "confidence_band": null,
  "display_precision": 1,
  "rmse_position_holdout": 0.0,
  "notes": []
}
```

### Field rules

| Field | Status | Source |
| --- | --- | --- |
| `engine` | required | `ValuationEngine` enum |
| `model_version` | required | written at training time, read from artifact metadata |
| `model_grade` | required | derived from latest position validation report; `unvalidated` when no holdout exists yet |
| `signal_completeness` | required | computed from which features were actually populated for this player |
| `horizon_years` | required | endpoint-level; rookie cards use 3, roster cards default 2 |
| `dynasty_value_score` | required | `DynastyValuation.dynasty_value_score` |
| `projection_1y/2y/3y` | required | `DynastyValuation.projection_1y/2y/3y` |
| `confidence_band` | deferred | populated only when calibrated quantile error exists |
| `display_precision` | required | decimal places permitted; computed from RMSE per [Confidence rule 2 in product strategy] |
| `rmse_position_holdout` | required | last validation report, by position |
| `notes` | required | free-text caveats from `DynastyValuation.notes` |

## Heuristic surface envelope

Some current surfaces are intentionally not model-backed. They should not fake the model valuation envelope. Use this smaller envelope for experimental heuristic surfaces such as roster age signals and trade quarantine output:

```json
{
  "status": "experimental",
  "engine": "roster_age_curve_auditor | trade_analyzer",
  "decision_supported": false,
  "model_version": null,
  "reason": "Plain-English explanation of why this is not decision-grade.",
  "required_before_decision_grade": [],
  "caveats": [],
  "notes": []
}
```

### Heuristic field rules

| Field | Status | Source |
| --- | --- | --- |
| `status` | required | Always `"experimental"` until the surface is decision-grade |
| `engine` | required where applicable | Descriptive method label, not a claim of model quality |
| `decision_supported` | required | Always `false` for heuristic surfaces |
| `model_version` | optional | Latest model version only when a model proxy is actually used |
| `reason` | required | Plain-English caveat for David and future API consumers |
| `required_before_decision_grade` | required where applicable | Structured blockers before recommendations/verdicts can return |
| `caveats` | required | Machine-readable limitations |
| `notes` | optional | Additional caveats or migration notes |

## Rookie decision card

Endpoint: `POST /api/rookies/score` and `POST /api/rookies/score-class`.

```json
{
  "...envelope": "...",
  "name": "Player Name",
  "position": "WR",
  "pick": 18,
  "round": 1,
  "age_at_entry": 21.4,
  "position_class_rank": 3,
  "class_overall_rank": 9,
  "threshold_flags": {
    "draft_capital_top_32": true,
    "draft_capital_top_64": true,
    "age_below_position_line": true,
    "dominator_above_position_line": null,
    "ras_above_8": null,
    "yprr_above_position_line": null
  },
  "roster_fit_signal": "fits_need | position_surplus | neutral | unknown",
  "top_drivers": [
    {"feature": "draft_capital", "contribution": 8.4, "direction": "positive"},
    {"feature": "age_at_entry",  "contribution": 1.6, "direction": "positive"}
  ],
  "risk_flags": [
    "low_sample_year_1"
  ],
  "counter_argument": "Score is dominated by draft capital; pre-NFL athleticism and college production are not yet ingested.",
  "projected_outcome_band": "Elite | Starter | Depth | Bust",
  "market_overlay": null
}
```

### Rules

- `confidence` (the old pick-bucket field) is **removed**. Do not emit.
- `dynasty_tier` is **removed** under that name; use `projected_outcome_band` only after `model_grade ≥ B`. While the model is `unvalidated` or `D`, omit `projected_outcome_band` entirely.
- `threshold_flags` keys are always present. A `null` value means "input not yet ingested"; the frontend renders this differently from `false`.
- `top_drivers` uses display-safe precision and should not include the model intercept as a prospect-specific driver. With the current Ridge model, contributions are `coef * (feature - feature_mean)` and `pick`/`round` are combined into `draft_capital`. When SHAP-style attributions ship, they replace this without a schema change.
- `counter_argument` is generated from `risk_flags` via a fixed template, not from a language model.
- `roster_fit_signal` defaults to `"unknown"` until league/roster config is wired.
- `market_overlay` is `null` until KTC ingestion ships; the field key is reserved.

## Roster decision card

Endpoint: `GET /api/roster/audit`.

```json
{
  "status": "experimental",
  "engine": "roster_age_curve_auditor",
  "decision_supported": false,
  "reason": "Roster audit is age-curve-only until Engine B usage, efficiency, and market signals are available.",
  "caveats": [
    "age_curve_only",
    "no_usage_signal",
    "no_market_overlay"
  ],
  "players": [
    {
      "player_id": "1234",
      "full_name": "Player Name",
      "position": "RB",
      "team": "KC",
      "age": 27,
      "cliff_age": 26,
      "years_to_cliff": -1,
      "cliff_status": "Past cliff | At cliff | Approaching | No age signal",
      "signal": "past_cliff | at_cliff | approaching_cliff | no_age_signal",
      "signal_drivers": [
        "age_past_position_cliff"
      ],
      "caveats": [
        "age_curve_only",
        "no_usage_signal",
        "no_market_overlay"
      ],
      "decision_supported": false
    }
  ]
}
```

### Rules

- `action` (`"Sell now"` etc.) is **removed**. Use `signal` only.
- `signal` values are neutral observed states. The frontend translates them to user-facing strings; the API does not.
- While Engine B is missing, `caveats` MUST include at least `"age_curve_only"` and `"no_usage_signal"`. The roster card is allowed to ship in this caveated form because age curve alone is a real signal — but it must declare its limits.
- Hardcoded league/user fallback is **removed**. If config is missing or the named league is not found, the endpoint returns 422 with a structured error. Silently auditing the wrong league is worse than failing.
- The roster response intentionally uses the heuristic surface envelope, not the model valuation envelope. Do not emit fake model grades, projections, or confidence bands.

## Trade decision card (experimental)

Endpoint: `POST /api/trade/analyze`. Marked experimental until trade reads from the unified valuation schema.

```json
{
  "status": "experimental",
  "decision_supported": false,
  "model_version": "yyyy-mm-dd_<hash> | null",
  "reason": "Trade output is experimental...",
  "required_before_decision_grade": [
    "unified_valuation_layer_for_all_assets",
    "engine_b_active_player_forecast",
    "calibrated_uncertainty_by_position",
    "pick_values_from_slot_weighted_expected_rookie_scores",
    "market_overlay_available_for_sanity_checks",
    "verdict_thresholds_calibrated_to_rmse"
  ],
  "notes": [
    "trade_engine_internal_only",
    "no_verdict_until_unified_value_layer"
  ],
  "my_assets_breakdown": [
    {
      "asset_type": "player | pick",
      "label": "Player Name | 2026 R2",
      "internal_score": 0.0,
      "engine": "rookie_forecast | active_player_forecast",
      "model_grade": "A | B | C | D | unvalidated",
      "caveats": [
        "veteran_value_uses_rookie_model_proxy",
        "pick_value_from_static_chart"
      ]
    }
  ],
  "their_assets_breakdown": []
}
```

### Rules

- `verdict` is **removed**. Do not emit `"Strong win" / "Win" / "Fair" / "Loss" / "Strong loss"` in any form. Re-introduce only when both sides can be valued by the unified schema, AND `model_grade` is at least `B` for both engines.
- Side totals (`my_total`, `their_total`, `difference`) are **removed**. They aggregate apples and oranges (rookie-model proxy + static pick chart).
- Every player asset MUST carry `"veteran_value_uses_rookie_model_proxy"` in `caveats` until that is no longer true.
- Every pick asset MUST carry `"pick_value_from_static_chart"` until pick valuation is rewritten to slot-weighted expected rookie scores.
- `decision_supported` MUST remain `false` while the response uses heuristic player proxies or static pick values.
- Do not emit legacy duplicate fields such as `my_assets_scored`, `their_assets_scored`, per-asset `value`, `deprecated_fields`, or `experimental_totals`.
- The route SHOULD be hidden from any UI surface during this period. Internal use only.

## Waiver decision card

**Deferred.** No schema is defined yet. Do not ship a waiver endpoint until Year-1 snap%, route participation, and target share are ingested. The right schema cannot be designed before those features exist.

## Validation report contract

Session A is producing a validation report per training run. To make `model_grade` loading deterministic, the report should include this minimum shape:

```json
{
  "model_version": "yyyy-mm-dd_<hash>",
  "trained_at": "2026-04-30T12:00:00Z",
  "training_cutoff_year": 2022,
  "holdout_years": [2023, 2024, 2025],
  "feature_list": ["pick", "round", "age"],
  "target": "y24_ppg",
  "row_counts": {"train": 0, "holdout": 0},
  "per_position": {
    "WR": {
      "rmse": 0.0,
      "mae": 0.0,
      "r2": 0.0,
      "calibration_coverage_80": null,
      "model_grade": "A | B | C | D | unvalidated"
    },
    "RB": {},
    "TE": {},
    "QB": {}
  },
  "gates": {
    "te_non_negative_r2": true,
    "all_positions_validated": true
  }
}
```

`model_grade` thresholds (initial proposal, tune as data accumulates):

| Grade | Position-level criteria |
| --- | --- |
| A | R² ≥ 0.30 on holdout AND coverage_80 within ±5% AND row count ≥ 80 |
| B | R² ≥ 0.15 OR (R² ≥ 0.0 AND row count ≥ 80 AND coverage usable) |
| C | R² ≥ 0.0 |
| D | R² < 0.0 |
| unvalidated | no holdout report exists |

The API loads the latest validation report at startup and stamps `model_grade` per position.

## Changelog

### 2026-04-30

- Added the heuristic surface envelope for experimental roster and trade responses.
- Updated roster signals to `past_cliff`, `at_cliff`, `approaching_cliff`, and `no_age_signal`.
- Clarified that roster and trade must not fake model grades, projections, confidence bands, verdicts, or totals before Engine B and unified valuation are ready.
- Clarified current rookie `top_drivers` attribution: centered Ridge terms, combined `draft_capital`, no intercept-as-driver, display-safe precision.

## Versioning

This contract document is versioned by the date in its sibling product-strategy doc. When the contract changes, append a `## Changelog` section here rather than rewriting in place; David's frame is "model credibility over feature breadth", and contract drift erodes credibility.

## Cross-references

- `docs/product-strategy-2026-04-30.md` — rationale and product decisions behind every field above.
- `app/models/valuation.py` — Session A's source-of-truth pydantic for `DynastyValuation` and `ConfidenceBand`.
- `docs/model-architecture.md` — Engine A / Engine B / unified value layer.
- `docs/codex-review-2026-04-30.md` — independent review that triggered this contract work.
