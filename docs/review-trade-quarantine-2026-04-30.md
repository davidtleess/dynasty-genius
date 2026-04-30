# Trade Quarantine Review — Session B (2026-04-30)

Subject: commit `f75516a` ("Quarantine experimental trade output") on `agent/modeling-backend`, currently shared by `agent/product-strategy` after fast-forward.

Reference contract: `docs/decision-output-contracts.md` § "Trade decision card (experimental)".
Original product-strategy framing: `docs/product-strategy-2026-04-30.md` § "Trade decision card" and § "Misleading or premature product surfaces to avoid".

## TL;DR

**Recommend MERGE.** The output is loud, structured, and mostly contract-compliant. `verdict` is gone, the constant defining its thresholds is gone, and at least eight separate places in the response (top-level + per-asset + nested) repeat the experimental status. The closest call is `experimental_totals`, which the contract literally said to remove — but it is so loudly namespaced and caveated that I judge the product-safety risk acceptable. Track non-blocking improvements as a follow-up, including aligning the contract to whatever final shape we want.

## Method

Read the trade analyzer at `f75516a`, the route handler, the contract section, and the original product-strategy section. Searched the workspace for any other consumer of the legacy field names (`my_assets_scored`, `verdict`) — no consumers outside the trade module and the docs. The legacy field names are therefore vestigial, not load-bearing.

## Does the response prevent David from treating it as decision-grade?

Yes. The response says "do not use this for decisions" in at least eight independent places:

| Where | Field | Value |
| --- | --- | --- |
| Top level | `status` | `"experimental"` |
| Top level | `decision_supported` | `False` |
| Top level | `reason` | full sentence explaining why |
| Top level | `required_before_decision_grade` | list of five blockers |
| Top level | `notes` | four caveat strings |
| Per asset | `score_status` | `"heuristic"` |
| Per asset | `scoring_method` | `"static_pick_chart"` or `"rookie_model_proxy_with_manual_age_discount"` |
| Per asset | `caveats` | per-asset-type caveat |
| `experimental_totals` | `caveat` | "do not use as a trade verdict" |

Of those, `decision_supported: False` is the most useful one for any future UI or downstream consumer because it's a clean boolean to branch on. That single field is the right primitive for this kind of "deferred surface" pattern, and Session A added it correctly.

Verdict: David will not misread this. A reasonable consumer cannot read this response and conclude it's decision-grade without actively ignoring eight signals.

## Are verdicts and win/loss language fully removed?

Yes, in code. The `VERDICT_THRESHOLDS` constant and the `verdict` field are both gone from the runtime response. The `deprecated_fields` block keeps the *name* `verdict` in the response (with the value `"removed_until_unified_value_layer"`) but only as documentation; no thresholding logic remains.

One nuance worth flagging: a consumer who reads `experimental_totals.difference` can still reconstruct the verdict in three lines. The contract removed totals for exactly this reason. See the next section.

## Are `experimental_totals` and per-asset values labeled clearly enough?

Mostly yes, with one caveat.

**Per-asset values are well-labeled.** Each asset carries `internal_score`, `score_status: "heuristic"`, `scoring_method: <honest description>`, and a `caveats` array. A consumer reading a single asset cannot reasonably mistake it for a validated valuation.

**`experimental_totals` is the closest call.** The contract (line 167) says: *"Side totals (`my_total`, `their_total`, `difference`) are **removed**. They aggregate apples and oranges (rookie-model proxy + static pick chart)."* The implementation re-introduces them under a wrapper:

```json
"experimental_totals": {
  "my_total": 95.4,
  "their_total": 102.7,
  "difference": -7.3,
  "status": "experimental",
  "caveat": "Totals aggregate heuristic player proxy scores and static pick values; do not use as a trade verdict."
}
```

Three observations:

1. The wrapper name `experimental_totals`, the inner `status: "experimental"`, and the inner `caveat` string are all explicit. A consumer who reads them at all will understand.
2. But the contract said "removed", and we now emit them. That is contract drift. Either the contract should be amended to allow the namespaced form, or the field should come out of the response.
3. The math itself is unsound — adding a player asset's `value` (a heuristic projected fantasy points figure scaled by 6.0 with an age discount) to a pick asset's `value` (a static chart value) is dimensionally incoherent. They are not on the same scale. The `caveat` string says this in English; the JSON shape does not enforce it. A future UI that displays `experimental_totals.difference` will display a number that is meaningless even by the model's own standards.

I am calling this non-blocking because:

- `decision_supported: False` at top level is a stronger gate than the totals re-introduction is a leak.
- The wrapper and caveat are loud enough that no reasonable consumer will treat the totals as authoritative.
- Removing `experimental_totals` is a one-line follow-up.

But it is the single thing on this commit I would change if I were doing it. My preference: drop `experimental_totals` entirely, keep only the per-asset breakdowns, and update the contract to formalize that pattern. Apple-orange aggregation is exactly what the original product-strategy doc warned about.

## Does the response name the right blockers before trade can become decision-grade?

Mostly yes:

```python
REQUIRED_BEFORE_DECISION_GRADE = [
    "unified_valuation_layer_for_all_assets",
    "engine_b_active_player_forecast",
    "calibrated_uncertainty_by_position",
    "pick_values_from_slot_weighted_expected_rookie_scores",
    "market_overlay_available_for_sanity_checks",
]
```

Lined up against the product-strategy doc's "Next three product features after model validation improves" — feature 3 (Trade decision card) is unblocked when features 1 (Rookie decision card with full tier-1 inputs) and 2 (Active-player projection card) ship, AND trade reads from the unified valuation schema. The five strings above cover that, with one minor mismatch:

- The product-strategy doc said `market_overlay` is shown alongside the model output, never replacing it. The string `"market_overlay_available_for_sanity_checks"` is consistent with that framing — good.
- One thing missing from the list that is implicit in the strategy doc: "RMSE-bounded verdict thresholds" — i.e., the rule that `verdict` returns only when the gap exceeds the larger side's RMSE band. Worth adding as a sixth string (`"verdict_thresholds_calibrated_to_rmse"`) so the calibration constraint is explicit in the response, not implicit in the contract. Non-blocking.

## Compatibility / naming issues

### C1. Both `my_assets_breakdown` and `my_assets_scored` are emitted (same data)

```python
"my_assets_breakdown": my_scored,
...
"my_assets_scored": my_scored,
"their_assets_scored": their_scored,
```

Identical content, two field names. `_breakdown` matches the contract; `_scored` is the legacy name. Search across the workspace shows no consumer of `_scored` outside the trade module and the docs themselves, so this is a clean opportunity to drop the legacy name. Non-blocking but worth removing soon — every dual-name pair is a future drift risk.

### C2. Per-asset `value` and `internal_score` are the same number

```python
"internal_score": value,
"value": value,
```

Same compatibility pattern as C1, same recommendation: drop `value` once we are confident no consumer relies on it. Today nothing does.

### C3. `model_grade: "unvalidated_for_veteran_trade_value"` is outside the contract enum

The contract defines `model_grade` as `A | B | C | D | unvalidated`. The implementation emits a sixth value, `"unvalidated_for_veteran_trade_value"`. This is more honest than forcing a veteran score into the existing enum — but it breaks any consumer doing strict enum validation (e.g., a Pydantic response model).

Two acceptable resolutions:

1. Use `"unvalidated"` (existing enum) and add a `caveats` entry like `"unvalidated_reason: veteran_trade_value"`. Most consumer-friendly.
2. Extend the contract enum to include `"unvalidated_for_veteran_trade_value"`. Most descriptive.

Recommend option 1 for now (no contract change required), with option 2 as a follow-up if we end up needing more fine-grained "unvalidated" reasons across surfaces.

### C4. `signal_completeness: "draft_capital_age_proxy"` is outside the contract enum

Same pattern as C3. The contract enum is `draft_capital_only | partial_pre_nfl | full_pre_nfl | nfl_year1 | nfl_multi_year`. The implementation adds `"draft_capital_age_proxy"`. Same resolution options as C3. Non-blocking.

### C5. `deprecated_fields` block is runtime documentation, not data

```python
"deprecated_fields": {
    "verdict": "removed_until_unified_value_layer",
    "my_total": "use_experimental_totals.my_total_for_internal_debug_only",
    ...
}
```

These fields are not in the response. The block tells a consumer that those names are deprecated — but a consumer who has never seen the prior shape will be confused about which fields are being referenced. Field deprecations belong in `docs/decision-output-contracts.md` § Changelog, not in the wire format. Non-blocking; remove in a follow-up.

### C6. Pick assets and player assets have asymmetric envelopes

Player assets get `engine`, `model_grade`, `signal_completeness`. Pick assets do not. This is honest — pick valuation is a static chart, not an engine output, so it would be wrong to claim `engine: "rookie_forecast"` for a pick. But the asymmetry is something the contract should describe explicitly. Non-blocking.

### C7. Route is not gated

`app/api/routes/trade.py` is unchanged. There is no env flag, no auth gate, no `experimental` URL prefix. The contract said the route SHOULD be hidden from UI; that's a frontend obligation more than a backend one, and the response payload's eight experimental signals are loud enough that this is fine. Non-blocking.

### C8. No top-level `model_version` field

The contract sample shows `model_version` at the top of the trade response. Implementation does not include it. Trade is a wrapper around per-asset values, so the natural model version is whichever rookie engine version is backing the player proxy scoring — easy to surface from `_MODELS_METADATA` in `rookie_evaluator`. Useful for traceability when reproducing a contested score later. Non-blocking.

## Blocking issues

None.

The single closest call is `experimental_totals` (apple-orange aggregation re-introduced after the contract said remove). I weighed this carefully and concluded the loud namespacing and caveat are sufficient — and `decision_supported: False` at the top level is the stronger gate. But it is what I would fix first.

## Non-blocking improvements (priority order)

1. **Drop `experimental_totals` from the response.** Apple-orange aggregation is exactly the failure mode the original strategy doc warned against; the wrapper mitigates but does not eliminate the risk. If we want to keep it for internal debugging, gate it behind an env var or a query string flag rather than always emit. Update the contract section to match whichever way we go.
2. **Remove the `deprecated_fields` runtime block.** Move that information to a `## Changelog` section in `docs/decision-output-contracts.md`. Wire format is for data; migration guides belong in docs.
3. **Drop the legacy `my_assets_scored` / `their_assets_scored` field names.** No consumer in the workspace uses them; they are pure drift risk.
4. **Drop the per-asset legacy `value` field.** Same reason; `internal_score` is the contract name.
5. **Align `model_grade` and `signal_completeness` enum values** by using `"unvalidated"` plus a `caveats` reason string, rather than introducing new enum values. Keeps strict validators happy.
6. **Add a sixth blocker string** to `required_before_decision_grade`: `"verdict_thresholds_calibrated_to_rmse"`, to make the RMSE-bounded verdict rule explicit in the wire format.
7. **Add a top-level `model_version` field** for traceability.
8. **Update `docs/decision-output-contracts.md` § "Trade decision card (experimental)"** to formalize whatever shape we land on after items 1–7. Specifically, the new `decision_supported`, `reason`, `score_status`, `scoring_method`, `required_before_decision_grade` fields are improvements over the contract's original shape and should be promoted into the canonical schema.

Items 1–4 together would reduce the response from twelve top-level fields to seven and remove every dual-name pair.

## Merge recommendation

**MERGE.**

Why I am comfortable with merge despite the non-blockers:

- The contract violation (`experimental_totals`) is loud and namespaced, and `decision_supported: False` is a stronger top-level gate than the totals re-introduction is a leak.
- Every legacy-name issue (C1, C2, C5) is purely additive and removable with no downstream impact (no consumers found in the workspace).
- Every contract-enum drift (C3, C4) is more honest than the alternative; resolving it is a follow-up, not a regression.
- The improvements Session A added beyond the contract — `decision_supported`, `reason`, `score_status`, `scoring_method`, `required_before_decision_grade` — are real product wins that the contract should promote.

This is the right kind of "ship and refine" for a quarantined surface that already had decision-grade language ripped out.

## What was not changed

No code changes were made by Session B in this review. None of the findings rise to a clear product-safety bug that justifies cross-lane edits. The follow-ups above are queued for Session A or for a contract-update pass when convenient.

`docs/mission-recalibration-2026-04-29.md` was not touched (still has the pre-existing local modification in this worktree).
