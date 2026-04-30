# Product Strategy Review — Session B (2026-04-30)

Status: Recommendations. Locked-in decisions are listed under "Highest-value product decisions" and "Misleading surfaces to retire". Output contracts live in `docs/decision-output-contracts.md`.

## Frame

Dynasty Genius is a personal decision system, not a public app. Every product surface should be judged by one question:

> Will this output change a decision David is about to make, and is it honest about what it knows?

Two failure modes are equally bad:

1. Useful-looking output that is more confident than the model warrants. (Misleads.)
2. Honest output that fails to reach a decision. (Useless.)

The current code leans toward failure mode 1: the rookie evaluator emits `dynasty_tier` and `confidence` from a 3-feature model, the trade analyzer emits `Strong win` / `Strong loss` verdicts, and the roster auditor emits `Sell now` from age alone. Those labels reach decisions before the underlying model can support them. Session B's job is to pull those surfaces back in line with the validation reality without removing decision support entirely.

## Highest-value product decisions

These are recommendations to lock in now. They are scoped to docs and output contracts; they should drive Session A's modeling priorities and the eventual route-handler changes.

1. **Treat the rookie board as the only David-facing decision surface for this iteration.** Rookie draft is the most concrete decision David has to make, has the strongest validated predictive signals (draft capital, age, dominator, RAS, YPRR), and is the one place where Engine A — even in its current 3-feature form — can produce useful comparative ordering. Roster, trade, and waiver should all be downgraded to "preview" or "internal" until they consume the unified valuation schema.
2. **Make every David-facing output a structured decision card, not a single score.** A decision card is: score + horizon + signal_completeness + threshold_flags + counter_argument + a deferred-fields list. This matches David's own protocol from `Strategy/DYNASTY DOMAIN EXPERTISE FRAMEWORK` (Counter-Argument Protocol, Decision Hierarchy, 65/35 Q:Qual). Single-number outputs are banned for decisions; they're allowed only inside debug/diagnostic endpoints.
3. **Retire the `confidence: High/Medium/Low` field that is actually `pick ≤ 32 / ≤ 96 / else`.** Replace it with `signal_completeness` (categorical, describes which inputs were present) and `model_grade` (categorical, loaded from the position's most recent validation report). Numeric `confidence_band` is deferred until Session A's temporal holdout produces calibrated quantile errors per position.
4. **Quarantine `/api/trade/analyze` behind an `experimental` flag and remove all verdict labels.** The current route mixes a static pick chart, a rookie model misused for veterans, and a manual age discount, then emits `Strong win` / `Loss`. That is the most misleading surface in the app today. Until trade reads from the unified valuation layer, the route should return a valuation breakdown only — no verdict, no recommendation. Codex's review reached the same conclusion; this just makes it product policy.
5. **Make the roster auditor emit signals, not actions.** Replace `action: "Sell now" / "Shop actively" / "Monitor" / "Hold"` with `signal: "trade_window_open" / "approaching_cliff" / "no_signal"`. Action language reaches a decision the current data cannot support (no market value, no replacement-cost view, no horizon). Signal language tells David where to look.
6. **Anchor every output to a horizon.** Every David-facing record must declare `horizon_years` (1, 2, 3) or `horizon: "draft_class_year_2_to_4"`. David's framework explicitly forbids conflating dynasty and redraft; the schema should enforce that distinction.
7. **Lock numeric precision to validation error.** If a position's holdout RMSE is 4.2 PPG, the output rounds projections to 1 decimal max and never displays a difference smaller than the position's RMSE as meaningful. The frontend (when it ships) bins scores into ordinal buckets with bucket boundaries documented per position. This kills "Strong win, +0.3 PPG" type outputs.
8. **Keep market data out of the model and only use it for sanity-check overlays.** KTC and similar should never feed the dynasty value score. They can power a separate `market_overlay` field (`market_value`, `market_delta_vs_model`) once ingested, so David can spot model-vs-market disagreements but the model never collapses into market consensus. KTC ingestion stays deferred per `docs/next-sprint.md`.

## Misleading or premature product surfaces to avoid

Listed in priority order. Treat the first three as "do not ship to David's UI in current form".

1. **`/api/trade/analyze` `verdict` field.** Emits `Strong win` / `Win` / `Fair` / `Loss` / `Strong loss` from a static pick chart and a rookie-model-as-veteran proxy. Veteran age is fed into a pick/round/age model trained on rookies. Output is presented as if validated. **Action:** strip the verdict, mark route experimental, hide from any frontend.
2. **`rookie.confidence` mapped from pick bucket.** A pick of 32 is not the same as model uncertainty for a Round-1 prospect. It is also not symmetric: a high pick can still be a busted profile if age, athleticism, or college production are weak. **Action:** delete the field name `confidence`. Replace with `signal_completeness` (enum) and `model_grade` (enum from validation).
3. **`rookie.dynasty_tier` ("Elite" / "Starter" / "Depth" / "Bust").** Tiers are derived from PPG cutoffs on a model that only sees pick, round, age. The label sounds market-grounded but is just a coarse re-projection of pick value. **Action:** keep the field but rename to `projected_outcome_band` and pair it with `signal_completeness` so it reads as "this is what a pick/age-only prior says, with most of David's tier-1 features still missing".
4. **`/api/roster/audit` `action: "Sell now"`.** Triggered by age past cliff alone. No usage signal, no market value, no replacement candidate, no horizon. A 27-year-old WR1 with elite usage can have higher dynasty value than a 24-year-old WR3 in the same league; the current rule cannot tell the difference. **Action:** rename `action` to `signal`, neutral language only, and add `caveats: ["age_curve_only", "no_usage_signal"]` until Engine B is online.
5. **Any "buy" or cross-roster surface.** Buy logic requires a model of opponent intent, opponent roster construction, and shared value scale. None of those exist. Do not ship anything labeled "Buy targets" until Engine B + unified value layer are live.
6. **Waiver prioritization.** Should not exist yet. The right input set for waiver is Year-1 snap%, route participation, target share — David's most time-sensitive signal, per the framework. None of those features are ingested. Building a waiver surface from Sleeper's available-player list alone would just rank by name recognition.
7. **League-wide rankings UI.** Premature — the unified value layer must exist for both rookies and active players first, and Engine B does not exist yet. Premature rankings invite trust calibration errors that are hard to undo.
8. **Hardcoded league/user fallback.** `roster_auditor.py` hardcodes username, league, season, and silently falls back to `leagues[0]` if the named league is missing. From a product-trust standpoint, silently auditing the wrong league is worse than failing loudly. **Action:** explicit failure if config is missing or league not found.

## Recommended output fields for David-facing decisions

The complete schemas live in `docs/decision-output-contracts.md`. This is the rationale for the field set and which fields are required vs. deferred.

### Universal fields (every David-facing record)

| Field | Type | Required | Why |
| --- | --- | --- | --- |
| `engine` | enum | yes | Which engine produced this — rookie_forecast or active_player_forecast. Forces honesty about input class. |
| `model_version` | string | yes | Lets David diagnose surprise outputs by tying them to a specific artifact. |
| `model_grade` | enum (`A`/`B`/`C`/`D`/`unvalidated`) | yes | Loaded from the latest validation report for this position+engine. Tells David whether to trust the score before reading it. |
| `signal_completeness` | enum (`draft_capital_only` / `partial_pre_nfl` / `full_pre_nfl` / `nfl_year1` / `nfl_multi_year`) | yes | What inputs the model actually had. Replaces the misleading `confidence`. |
| `horizon_years` | int | yes | 1, 2, or 3. Forbids conflating dynasty and redraft. |
| `dynasty_value_score` | float | yes | Unified scale from the valuation schema (Session A `DynastyValuation`). |
| `projection_1y`, `projection_2y`, `projection_3y` | float | yes | From the unified schema. Round to 1 decimal. |
| `confidence_band` | object (`low`, `median`, `high`) | deferred | Populated only after Session A produces calibrated quantile error per position. Until then, omit rather than fake. |

### Rookie decision card additions

| Field | Type | Required | Why |
| --- | --- | --- | --- |
| `pick`, `round`, `age_at_entry` | numeric | yes | Primary inputs are the primary explanation. |
| `position_class_rank` | int | yes | Rank within position in the draft class. The actual decision unit at a rookie pick is "this WR vs. the next WR", not absolute PPG. |
| `class_overall_rank` | int | yes | Same reason, BPA mode. |
| `threshold_flags` | object | yes | Boolean flags against David's tier-1 lines: `age_above_position_threshold`, `draft_capital_top_32`, `draft_capital_top_64`, `dominator_above_position_line`, `ras_above_8`, `yprr_above_position_line`. Deferred flags are emitted as `null`, not silently absent. |
| `roster_fit_signal` | enum (`fits_need` / `position_surplus` / `neutral` / `unknown`) | yes (Needs-Based mode) | Powers the BPA vs. Needs-Based toggle from `CLAUDE.md`. |
| `top_drivers` | list of `{feature, contribution, direction}` | yes | Three-item explanation of what moved the score. Until SHAP-style attributions are wired, can be coefficient × feature for the linear model. |
| `risk_flags` | list of strings | yes | Counter-argument input. Examples: `"age_above_wr_23_line"`, `"crowded_depth_chart"`, `"low_sample_year_1"`. |
| `counter_argument` | string | yes | One short sentence stating the strongest case against this score. Generated from the `risk_flags` set, not freeform. |
| `market_overlay` | object | deferred | `market_value`, `market_rank`, `model_minus_market`. Filled only when KTC ingestion ships. |

### Roster decision card additions

| Field | Type | Required | Why |
| --- | --- | --- | --- |
| `cliff_age`, `years_to_cliff` | int | yes | Already present; keep. |
| `signal` | enum (`hold` / `monitor` / `approaching_cliff` / `trade_window_open` / `no_signal`) | yes | Replaces `action`. Neutral, signal-only. |
| `signal_drivers` | list of strings | yes | Why this signal fired. Examples: `"age_past_position_cliff"`, `"value_above_replacement"`. |
| `caveats` | list of strings | yes | Examples while Engine B is missing: `"age_curve_only"`, `"no_usage_signal"`, `"no_market_overlay"`. Forces honesty. |
| `replacement_archetype` | string | deferred | "find a young WR2 with year-1 route participation > 65%". Engine B + waiver feature dependency. |
| `trade_window_months` | int | deferred | Only emitted once trade analyzer reads from the unified value layer. |

### Trade decision card

Until trade consumes the unified valuation layer:

| Field | Type | Required | Why |
| --- | --- | --- | --- |
| `status` | enum, fixed value `experimental` | yes | Hardcoded; surfaces in API and any UI banner. |
| `my_assets_breakdown`, `their_assets_breakdown` | list of `{asset, internal_score, model_grade, caveats}` | yes | Show the inputs. Do not aggregate. |
| `verdict` | — | **removed** | Banned until both sides of the trade can be valued by the unified schema. |
| `notes` | list of strings | yes | Always include `"trade_engine_internal_only"` and `"veteran_values_use_rookie_model_proxy"` until that is no longer true. |

### Waiver decision card

Deferred entirely. Do not define a waiver schema until route participation and snap% are ingested. Rationale: waiver value is dominated by Year-1 opportunity signals; building it on roster availability alone produces noise, not signal.

## Confidence and uncertainty presentation rules

These are product rules. They apply to every David-facing surface, including any future frontend.

1. **No numeric confidence until validation supports it.** `confidence_band: {low, median, high}` from the unified schema is deferred until Session A's temporal holdout produces calibrated per-position quantile errors. Today, every output instead carries `model_grade` and `signal_completeness`, both categorical.
2. **Display precision tracks RMSE.** A position's projection display rounds to a precision no finer than `RMSE / 4`. Differences smaller than RMSE are flagged as "within model error" and the UI must not rank them as if separated. This kills false-precision outputs like `Strong win, +0.3 PPG`.
3. **Counter-argument is mandatory on rookie decision cards.** Generated from the `risk_flags` set, not freeform. This implements David's Rule 4 directly.
4. **Bust outcomes stay encoded as zeros, not omitted.** Already correct in `collect_draft_prospects.py` (`y24_ppg = 0.0` when `total_games == 0`). Keep that, and surface the `low_sample_flag` in the rookie card so David sees when a "Bust" prediction is actually "we have almost no data on the post-draft outcome class for this profile".
5. **Model_grade is loaded, not assumed.** When Session A produces a per-position validation JSON, the API loads it and stamps `model_grade`. If a position's grade is `D` or `unvalidated`, the frontend should render the card greyed-out with an "unvalidated" banner — David should see it but should not act on it.

## What to defer until model validation improves

Validation gates Session B is committing to:

- Engine A holdout temporal split is in place and reports per-position metrics.
- TE position has non-negative R² on holdout (current `next-sprint.md` "TE non-negative" gate).
- Quantile or bootstrap intervals are calibrated to within ±15% of empirical coverage on holdout.
- Engine B MVP exists (even if only target share + snap% + age curve).

Before all four are met, defer:

| Surface | Blocked by |
| --- | --- |
| Numeric `confidence_band` in any output | Calibrated quantile intervals |
| Trade `verdict` and aggregated `difference` total | Engine B exists; unified value layer wired into trade |
| Any "Buy" surface, opponent-roster scan | Engine B + unified value layer |
| Waiver prioritization | Year-1 snap% / route participation features |
| League-wide rankings UI | Engine B + unified layer for both engines |
| Frontend expansion | All of the above; per `roadmap.md` Phase 4 ordering |

After all four gates are met:

## The next three product features after model validation improves

These are the next three product features Session B recommends, in order. Each has an explicit unblocking gate.

### 1. Rookie decision card with full tier-1 inputs and BPA/Needs toggle

**Unlocked when:** Engine A trains on draft capital + age + RAS + dominator + YPRR (or the highest-quality college proxy available from `nfl_data_py` for now), AND temporal holdout reports `model_grade ≥ B` for at least WR and RB.

**What ships:**
- Decision card schema from this doc, fully populated.
- BPA mode (sorted by `dynasty_value_score`) and Needs-Based mode (filtered to `roster_fit_signal == "fits_need"`).
- Per-prospect `top_drivers`, `risk_flags`, `counter_argument`.
- Class rankings within position and overall.

**Why first:** Rookie draft is the closest concrete decision David makes, has the highest signal-to-noise ratio, and is what the existing model is closest to supporting. It also happens to be the surface least dependent on Engine B.

### 2. Active-player projection card for David's roster (read-only)

**Unlocked when:** Engine B MVP exists and produces `dynasty_value_score`, `projection_1y/2y/3y`, and `signal_completeness ≥ partial_nfl_year1` for QB/RB/WR/TE on David's roster.

**What ships:**
- Roster page becomes a list of active-player decision cards using the same schema as rookie cards (the unified value layer pays off here).
- `signal: "trade_window_open" | "approaching_cliff" | "monitor" | "hold" | "no_signal"` driven by Engine B output, not age alone.
- `caveats` field carries the still-missing inputs (e.g., `"no_market_overlay"`).
- Hold/sell logic is "value above replacement at position" rather than "past age cliff".

**Why second:** This is where the unified value layer earns its keep. Rookie and active-player cards on the same scale lets David ask "is the next pick worth more than this veteran" — the central dynasty question. Cannot ship before Engine A is credible (gate 1) because cross-engine comparison amplifies any miscalibration.

### 3. Trade decision card backed by the unified value layer

**Unlocked when:** features 1 and 2 ship, AND the trade analyzer is rewritten to read from the unified valuation schema rather than reuse the rookie evaluator.

**What ships:**
- Trade card lists each asset's `dynasty_value_score`, `model_grade`, `signal_completeness`, and the side totals on the unified scale.
- Verdict returns, but in calibrated language tied to validation error: e.g., `"likely_win"` only fires when the gap exceeds the larger side's RMSE band.
- Pick valuation no longer uses a static chart; picks are valued via expected-pick rookie scores at slot-weighted positions.
- `market_overlay` (KTC) is shown alongside the model output once ingested, never replacing it.

**Why third:** Trade is the highest-stakes surface, so it ships last. It is also the surface that most needs both engines on the same scale; doing it before features 1 and 2 reproduces the current misleading state with prettier outputs.

## Open questions for David

These are decisions that should be made by the user, not Session B:

1. **Roster fit definition.** What is "need" — by depth chart slot, by projected starter gap in 2 years, or by cliff-driven replacement timing? Affects `roster_fit_signal` semantics.
2. **Contender vs. rebuilder posture.** David's framework treats this as the master switch for many recommendations. The system should accept it as explicit config, not infer it from roster age.
3. **League settings (Superflex, PPR scoring, taxi/IR rules).** Current scoring target is `fantasy_points_ppr`. If the league is Superflex or non-PPR, this is wrong by default. Needs to be encoded in config alongside username/league/season.

These should land in `docs/league-config.md` once decided.
