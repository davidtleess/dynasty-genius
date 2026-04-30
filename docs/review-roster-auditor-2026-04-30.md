# Roster Auditor Review — Session B (2026-04-30)

Subject: commit `64fbef2` ("Clean up roster audit config and signals") on `agent/modeling-backend`, currently shared by `agent/product-strategy` after fast-forward.

Reference contract: `docs/decision-output-contracts.md` § "Roster decision card".
Original product-strategy framing: `docs/product-strategy-2026-04-30.md` § "Roster decision card additions" and § "Misleading or premature product surfaces to avoid" item 4.

## TL;DR

**Recommend MERGE.** Action language is fully removed, the hardcoded league fallback is gone, the explicit 422 path is in place, and `decision_supported: False` is loud at both response and per-player levels. The contract drift here is *toward* honesty, not away from it — the implementation's `signal` enum is structurally better than what the contract originally specified, and several missing envelope fields reflect that the auditor is heuristic, not model-driven. Track non-blocking improvements as a contract-update pass plus a few surfacing additions.

## Method

Read `app/services/roster_auditor.py` and `app/api/routes/roster.py` at `64fbef2`, the contract section, the original strategy doc, and the codex baseline (`docs/codex-review-2026-04-30.md`) which originally flagged the hardcoded fallback. Compared field-by-field against the contract.

## Does the response prevent David from treating it as decision-grade?

Yes. The response carries decision-safety signals at both the response level and the per-player level:

| Where | Field | Value |
| --- | --- | --- |
| Top level | `status` | `"experimental"` |
| Top level | `decision_supported` | `false` |
| Top level | `reason` | "Roster audit is age-curve-only until Engine B usage, efficiency, and market signals are available." |
| Top level | `engine` | `"roster_age_curve_auditor"` (descriptive of the heuristic, not pretending to be a model engine) |
| Top level | `caveats` | `["age_curve_only", "no_usage_signal", "no_market_overlay"]` |
| Per player | `decision_supported` | `false` |
| Per player | `caveats` | same three strings |
| Per player | `signal` / `signal_drivers` | neutral, no action implied |

Per-player `decision_supported: false` is slightly redundant with the top-level field, but it is the right kind of redundancy — a consumer iterating over `players` and rendering each one in isolation does not need to remember to read the parent. Useful.

## Are directive action phrases fully removed?

Yes. The previous shape emitted `action: "Sell now" | "Shop actively" | "Monitor" | "Hold"`. None of those strings appear in the new code anywhere — not as values, not as constants, not in test stubs. ✓

The `engine` name `"roster_age_curve_auditor"` is also descriptive without being prescriptive — it names the method, not the recommendation. Good naming.

## Are the neutral signals clear and useful?

Mostly yes, with one important note.

The implementation's `signal` enum:

| Signal | Trigger | Reading |
| --- | --- | --- |
| `past_cliff` | `years_to_cliff < 0` | "Player is past the position aging curve cliff." |
| `at_cliff` | `years_to_cliff == 0` | "Player is at the cliff age." |
| `approaching_cliff` | `1 ≤ years_to_cliff ≤ 2` | "Player is within two years of the cliff." |
| `no_age_signal` | `years_to_cliff > 2` | "Age curve does not flag this player." |

This is **better** than what the contract originally specified. The contract's enum was `trade_window_open | approaching_cliff | monitor | hold | no_signal`. Three of those (`trade_window_open`, `monitor`, `hold`) are subtly action-suggestive — they describe what David should *do*, not where the player *is*. The implementation's enum describes pure observed state and lets David do the action mapping himself. That matches the strategy doc's stated principle ("emit signals, not actions") more cleanly than the contract did.

The `cliff_status` field (capitalized human label: `"Past cliff" / "At cliff" / "Approaching" / "Safe"`) is a parallel friendly version of the same enum — good for direct UI display. One nit: the `"Safe"` label for `no_age_signal` is mildly evaluative. A 22-year-old WR isn't truly "safe" — they have other risks the auditor doesn't see (depth chart, scheme fit, injury). Calling them "Safe" subtly implies "no action needed", which is the kind of action language the strategy doc retired. Recommend renaming the human label to `"No age signal"` to match the signal name. Non-blocking, cosmetic.

`signal_drivers` is correctly populated with one driver string per signal (`"age_past_position_cliff"` etc.). The driver strings are descriptive of *why* the signal fired, not *what to do*. ✓

## Are the caveats loud enough?

Yes. `caveats: ["age_curve_only", "no_usage_signal", "no_market_overlay"]` appears in three places in the response (top level + per-player twice if you count the `caveats` list embedded in each player record). Both contract-required strings (`age_curve_only`, `no_usage_signal`) are present. `no_market_overlay` is present even though the contract didn't strictly require it — that's a useful addition.

The caveats are also concise enums, not free-text. A consumer can branch on them. Good.

The top-level `reason` field reinforces the same point in plain English: "Roster audit is age-curve-only until Engine B usage, efficiency, and market signals are available." Loud enough.

## Does env config behavior avoid silent wrong-league risk?

Yes. The previous code had:

```python
league = next(
    (lg for lg in leagues if lg["name"] == MY_LEAGUE_NAME),
    leagues[0],   # silent fallback
)
```

That was the codex baseline's `docs/codex-review-2026-04-30.md` finding "Hardcoded config can break or silently use the wrong league". The new code raises `RosterConfigError(f"League named {league_name!r} was not found...")` with no fallback. ✓

Three explicit failure modes:

1. Missing `DYNASTY_SLEEPER_USERNAME` or `DYNASTY_SEASON` → `RosterConfigError`.
2. Missing both `DYNASTY_SLEEPER_LEAGUE_ID` and `DYNASTY_SLEEPER_LEAGUE_NAME` → `RosterConfigError("Set either ... or ...; refusing to guess a league.")`. The "refusing to guess" wording is exactly the right tone.
3. League name configured but not found in user's league list → `RosterConfigError`.

Plus a fourth: roster not found for the configured user in the resolved league → `RosterConfigError`.

All four return 422 with `{error: "roster_config_error", message: ...}` via the route handler. Silent wrong-league risk is fully eliminated for the named-config paths. ✓

## Is 422 product/API-safe?

Acceptable for this app, with one caveat.

422 is conventionally "Unprocessable Entity" — request data is syntactically valid but semantically invalid. Server-side config errors are arguably 503 ("Service Unavailable") or 500. The contract said 422; the implementation matches.

For a single-user app where David is the operator and the consumer, 422 is fine because David is going to read the structured `error` and `message` fields and fix the env. The HTTP status code is secondary to the structured payload.

If this ever becomes a multi-user surface, 422 would mislead callers into thinking they sent a bad request body when really the server is misconfigured. Non-blocking for now. Worth a contract note.

## Contract drift (the substantive issue)

The implementation diverges from `docs/decision-output-contracts.md` § Roster decision card in three places. In all three, the implementation is more honest than the contract; the contract should be updated rather than the implementation rolled back.

### D1. `signal` enum values

- Contract: `trade_window_open | approaching_cliff | monitor | hold | no_signal`
- Implementation: `past_cliff | at_cliff | approaching_cliff | no_age_signal`

Implementation is purely descriptive. Contract values were action-suggestive in three of five slots. **Update the contract to match the implementation.**

### D2. Top-level envelope fields

The contract specified the universal envelope (`model_grade`, `signal_completeness`, `horizon_years`, `dynasty_value_score`, `projection_1y/2y/3y`, `confidence_band`, `display_precision`, `rmse_position_holdout`, `notes`) as required for every David-facing record. The roster response carries only `engine`, plus the new `status` / `decision_supported` / `reason` / `caveats` / `players` keys.

Strictly this is contract drift. But the universal envelope was designed assuming a model-driven projection. The roster auditor is a heuristic with no projection, no confidence band, no model grade, no RMSE. Faking those fields would be worse than omitting them. The implementation made the right call.

**Resolution:** the contract should formalize a "heuristic surface" envelope — the subset of the universal envelope that applies to non-model surfaces. Required fields for a heuristic surface: `engine`, `status`, `decision_supported`, `reason`, `caveats`. Optional: `notes`, `model_version` (for the heuristic's revision). Banned: anything that implies model uncertainty (`confidence_band`, `model_grade`, `rmse_position_holdout`).

This generalizes — the trade quarantine surface from the previous review uses essentially the same shape, so the heuristic-surface envelope is the right contract pattern for both.

### D3. Deferred fields not emitted as `null`

Contract said `replacement_archetype`, `trade_window_months`, `market_overlay` are deferred (`null` until Engine B / KTC). Implementation omits them entirely.

The contract's status legend technically allows this: *"Emit as null or omit; do not fake."* So this is contract-compliant. Stylistic preference: explicit `null` would tell future consumers "we know this field exists, we just don't have data for it yet" rather than leaving them to wonder. Non-blocking.

## Blocking issues

None.

## Non-blocking improvements (priority order)

1. **Update `docs/decision-output-contracts.md` § Roster decision card** to match the implementation's `signal` enum (D1) and to introduce a "heuristic surface" envelope spec (D2). Both are contract changes that codify the implementation's correct choices.
2. **Rename the `cliff_status` human label `"Safe"` to `"No age signal"`.** Matches the signal name and removes the mild evaluative tone. One-line change.
3. **Add a top-level `excluded_count` summary** so David can see if any roster spots were silently dropped:

   ```json
   "excluded_count": {
     "non_skill_position": 5,
     "missing_age": 0
   }
   ```

   Today, kickers/defenses are silently filtered out (fine for dynasty), and any skill player with `age == None` from Sleeper is also silently filtered out (potentially not fine — a real WR with a Sleeper data gap becomes invisible). The summary lets David see what got dropped without changing the per-player shape.
4. **Wrap upstream Sleeper errors in `RosterConfigError`** so that a bad username (Sleeper raises `ValueError("No user found for username: ...")`) becomes a 422 with the structured envelope rather than propagating as a 500. Currently the route only catches `RosterConfigError`, and `RosterConfigError` is only raised inside the auditor itself.
5. **Emit deferred fields as explicit `null`** (`replacement_archetype`, `trade_window_months`, `market_overlay`) for forward compatibility (D3). Stylistic, but it would make the per-player shape match the contract's deferred-fields rule literally.
6. **Add `notes` array to the response** carrying the same provisional strings the rookie evaluator does (`"Roster signal is heuristic age-curve-only; no usage data, no market overlay, no model uncertainty."`). Aligns the envelope across surfaces. Non-blocking; the existing `reason` string covers the same ground.

## Where the response is strong

- Configuration via env vars with explicit failure modes. Four distinct failure paths all produce structured 422 responses.
- `engine: "roster_age_curve_auditor"` is descriptive of method, not pretending to be a model.
- `decision_supported: false` at two levels.
- Loud, structured `reason` string.
- `signal` enum strictly observational, not prescriptive.
- `signal_drivers` populated with one driver per signal — symmetric with rookie card pattern.
- `cliff_age` and `years_to_cliff` are present so a consumer can render the underlying numbers without re-deriving them from `position` + `age`.
- Sorted ascending by `years_to_cliff`, so highest-attention players surface at the top.

## Merge recommendation

**MERGE.** This is a substantial product-safety improvement over the previous shape:

- Action language fully removed.
- Silent league fallback fully removed; structured 422 path in place.
- Required contract caveats present.
- `decision_supported: false` and `engine: "roster_age_curve_auditor"` both establish honest framing.

The contract drift in `signal` enum and envelope shape is the implementation choosing honesty over compliance, and the right next step is a contract update — not an implementation rollback.

After this merges, the highest-leverage follow-up is the contract update (item 1 above) so the trade quarantine surface and the roster auditor surface can both be formalized under a shared "heuristic surface" envelope spec. That doubles the value of the work Session A has done across the two reviews.

## What was not changed

No code changes were made by Session B in this review. None of the findings rise to a clear product-safety bug that justifies cross-lane edits.

`docs/mission-recalibration-2026-04-29.md` was not touched (still has the pre-existing local modification in this worktree).
