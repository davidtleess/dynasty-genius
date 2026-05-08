# Dynasty Genius — Validation Gates

Composite advancement criteria, current measured status, and the rules for revising both.

- Strategy layer: [system-design.md](system-design.md)
- Implementation playbook: [agent-execution-plan.md](agent-execution-plan.md)
- Adapter contracts: [data-source-contracts.md](data-source-contracts.md)

## Why composite gates

Phase advancement is gated. The wrong way to gate is a single number on a single holdout — for example, "Phase 1 closes when WR holdout R² ≥ 0.55." With current sample sizes (WR holdout = 35 rows, RB = 19, TE = 11, QB = 10) a one-year-holdout R² is variance-driven half the time. Real model improvements will fail brittle gates, and noise will pass them.

The right way is a composite of several signals. Each gate below is a list of criteria the position must satisfy *jointly*. A position that fails one criterion does not block the phase outright — the team makes an explicit waiver decision (recorded in the run's `validation_report.json`) or revises the gate (PR-ed into this doc).

## Composite gate components

Every phase gate references a subset of these. Each component has a precise definition and a measurement script under `app/data/pipeline/validation/`.

### 1. R² on the temporal holdout

Standard coefficient of determination, computed per position on the holdout split defined by `train_models.py`. **Use is conditional**: R² is informative only when the holdout has ≥ 30 rows and ≥ 2 distinct ground-truth seasons. Below that, R² is a tiebreaker, not a gate.

### 2. Spearman rank correlation

Rank correlation between predicted and actual `y24_ppg` on the holdout. Captures whether the model gets the *ordering* right, which is what dynasty draft and trade decisions actually consume. Robust on small samples in a way R² is not.

### 3. Top-K hit rate

For each position, compute: of the actual top-K players in the holdout (by realized `y24_ppg`), how many are in the model's top-2K predictions? Default K per position:

| Position | K |
| --- | --- |
| QB | 6 |
| RB | 12 |
| WR | 18 |
| TE | 6 |

Hit rate ≥ 0.6 is the practical floor for a usable rookie board.

### 4. RMSE stability across a 3-year rolling holdout

Train on seasons `[start, end-1]`, hold out season `end`. Roll across the last three eligible seasons. Report mean RMSE and stddev across folds. A position whose RMSE stddev exceeds 30% of mean RMSE is unstable — block phase advancement until either more data or a different feature set stabilizes it.

When fewer than 3 mature seasons exist, this component is reported as `n/a` and treated as informational only.

### 5. Null coverage

Percentage of position rows in the league universe that received a non-null score this run. A model that scores 60% of WRs and silently drops the rest is failing on coverage even if its R² is great. Default floor: 90%.

### 6. Caveat hygiene

No production decision card may carry `model_grade: unvalidated`. Cards with `model_grade: D` may be emitted but must be visually de-emphasized in any UI. A run that emits any production unvalidated card fails this gate.

### 7. Bootstrap CI on metrics

For R², Spearman, and top-K hit rate, compute a 1,000-iteration bootstrap 90% CI on the holdout. Report alongside the point estimate. Phase advancement reads the lower bound, not the point estimate, on key criteria.

## Model grade taxonomy

Loaded into every Player Value Object. Used by both gates and UI.

| Grade | Meaning | When assigned |
| --- | --- | --- |
| A | Production-grade. Lower-bound metrics clearly above floor across all criteria. | Currently unattainable; reserved for post-Phase-6 calibration. |
| B | Decision-usable. All composite criteria satisfied at lower-bound. | After Engine A feature expansion + temporal holdout stability. |
| C | Useful but provisional. Point estimates pass, lower bounds borderline. | Current state for WR / RB. |
| D | Caveat-only. Numerically present, not decision-usable. UI greys these out. | Current state for QB on negative R² lower bound. |
| unvalidated | Cannot ship to production cards. | Default for any new model artifact until a validation report is generated. |

## Phase advancement criteria

These are the gates that close each phase. Every gate is a list of criteria; failure on one is recorded in the run's `validation_report.json` with explicit acknowledgment, not silently ignored.

### Phase 0 — Foundation Safety

Closes when:

- `tests/contract/` exists and runs in CI.
- `app/data/calibration/thresholds.yaml` exists with at least one entry per position and `provenance` declared.
- A composite-gate measurement script exists at `app/data/pipeline/validation/composite.py` and is invoked by `train_models.py` after each run.
- `model_grade` gating is enforced by `tests/contract/test_no_unvalidated_in_production.py`.

### Phase 1 — League Context Foundation

Closes when:

- `app/data/league/context.py` defines a typed `LeagueContext` exposing: scoring, lineup requirements, roster size, taxi/IR rules, David's roster, David's incoming picks (all years × rounds), every league-mate's roster, contender posture, risk tolerance.
- `app/data/league/david_league.yaml` is checked in with David's settings (no secrets); Sleeper-derived state is loaded fresh per request.
- `app/services/roster_auditor.py` and any other current consumer reads `LeagueContext` instead of env vars or ad-hoc Sleeper lookups.
- Posture (`contender | sustained_contender | soft_rebuild`) is settable and propagates to at least one downstream surface as a caveat or weight.
- `tests/league/test_league_context.py` passes — covers loading, posture changes, and missing-league-mate cases.

### Phase 2 — Identity Resolution

Closes when:

- `app/data/identity/canonical_mapping.csv` covers ≥ 95% of the union of:
  - All players appearing in any Sleeper roster in David's league (sourced from `LeagueContext`).
  - All players in `prospects_with_outcomes.csv`.
  - All players in nfl_data_py active rosters from the last 3 seasons.
- `tests/identity/` covers exact / ambiguous / missing / conflict / promotion-audit cases and passes.
- A nightly cross-source consistency check runs and reports zero unresolved conflicts.
- The fuzzy-match staging path is exercised end-to-end on at least one source.

### Phase 3 — Source Adapter Contract + Raw Snapshots

Closes when:

- Sleeper and nfl_data_py adapters conform to the `SourceAdapter` interface in [data-source-contracts.md](data-source-contracts.md).
- **Per-source ingestion paths**:
  - Sleeper: automated path + a fixture-replay / stale-cache path. Manual export is **not applicable** (free public API; if Sleeper is down the system surfaces stale-cache caveats).
  - nfl_data_py: automated path + manual export / fixture replay path producing identical normalized rows.
  - Paid or brittle sources (PFF, PlayerProfiler, RAS, KTC): automated path + manual export fallback. This requirement applies as those adapters land in their respective phases.
- `app/data/cache/raw/` is gitignored (no root-level `data/` directory); `tests/fixtures/<source>/` is checked in.
- Freshness reports are emitted by both Sleeper and nfl_data_py and consumed by at least one decision-card endpoint as a caveat source.
- `tests/contract/test_no_silent_substitution.py` passes.

### Phase 4 — Engine A Feature Expansion

Each new feature is a versioned hypothesis: implementation cites a published source, an alternative formula version coexists where one exists, and the model run records `metric_version` for every feature consumed.

Closes when, **for each of WR / RB**:

- R² on the latest temporal holdout has improved relative to the pick+round+age baseline (current: WR 0.41, RB 0.51).
- Spearman ≥ 0.55 (point estimate) and ≥ 0.40 (lower bound).
- Top-K hit rate ≥ 0.6 (point estimate).
- RMSE stability across 3-year rolling holdout: stddev / mean ≤ 0.3, OR explicit acknowledgment in the report that fewer than 3 mature seasons are available.
- Null coverage ≥ 0.9.

For TE and QB:

- TE: composite criteria reported but not gating; goal is `model_grade ≥ C`. Failure is acceptable, with explicit waiver in the report.
- QB: model artifact may exist with `model_grade: D`; production cards for QB are gated by `model_grade` and not user-visible until QB R² lower bound > 0.

A position that exits this phase with `model_grade: D` is allowed but its surfaces are greyed out in any UI.

### Phase 5 — Fitted Aging Curves

Closes when:

- `app/data/calibration/aging_curves/` contains a versioned fitted curve per position from `nfl_data_py` historicals, with an artifact pointer file and bootstrap CIs on the implied half-decline ages.
- No code path reads a hardcoded cliff age — all reads go through `app/services/aging.py`.
- The fitted curves' implied cliff ages are recorded in artifact metadata and diff'd against the framework's heuristic ages (RB 26 / WR 28 / TE 30 / QB 33) in a one-time report.
- `tests/data/test_aging_curves.py` passes.

### Phase 6 — Engine B MVP

Closes when, **for each of WR / RB**:

- An Engine B artifact exists with at least 5 features (target_share, route_pct, snap_share, weighted_opportunity, age_curve_state for RB / WR variants).
- Holdout split avoids same-season leakage (target year is at least 1 year forward of feature year).
- Composite criteria above point estimate floors.
- A backtest of "Engine A → Engine B handoff at age 24" produces no discontinuity exceeding 1.5× position RMSE.

### Phase 7 — Unified Player Value Object

Closes when:

- Every active player in David's league plus all players in `prospects_with_outcomes.csv` from the last 5 seasons has exactly one PVO row.
- `inputs_present` and `inputs_missing` are populated and disjoint on every row.
- `engine_used` is populated and matches the artifact actually used.
- PVO carries league context fields (roster fit signal, scarcity, championship-window weight) sourced from `LeagueContext`.
- `tests/contract/test_pvo_schema.py` passes.

### Phase 8 — Decision Surfaces

Closes when:

- Each surface (Rookie Board, Roster Audit, Trade Lab, Waiver Radar, League Pulse, opponent-fit trade targeting) reads exclusively from PVO + LeagueContext and emits no field outside the universal decision card schema in `system-design.md`.
- Every decision card decomposes into the layers required by the "No Mystery Rankings" rule (model, market, roster context, counterargument, missing data).
- Trade Lab returns `delta_status: within_model_error | likely_favors_me | likely_favors_them | insufficient_confidence`. The banned `verdict` field stays removed.
- `tests/contract/test_ratchet.py` passes — removed fields stay removed.

### Phase 9 — Market Overlay (KTC)

Closes when:

- KTC adapter conforms to the `SourceAdapter` interface.
- `market_overlay` is populated on PVOs with KTC coverage.
- `tests/contract/test_ktc_not_in_features.py` passes.

### Phase 10 — Backtest Harness

Closes when:

- A backtest endpoint exists that, given a model_version and a position, returns a time series of: model prediction, KTC market value, realized fantasy outcome.
- The endpoint is exercised by `tests/backtest/` against fixture data.
- The frontend phase has explicit visibility into this endpoint as a required surface.

### Phase 11 — Frontend

Closes when David has tested every decision surface against a real recent decision (a real rookie pick he made, a real trade he was offered) and the system's outputs are auditable end-to-end.

## Current measured status (as of 2026-04-30)

Latest validation report: `app/data/models/runs/20260430T211956Z/validation_report.json`

| Position | Train rows | Holdout rows | R² | Spearman | Top-K hit | RMSE stability | Null coverage | Model grade | Caveats |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WR | 193 | 35 | 0.408 | tbd | tbd | n/a (1 fold) | 1.0 within training | C | — |
| RB | 129 | 19 | 0.509 | tbd | tbd | n/a (1 fold) | 1.0 | C | — |
| TE | 87 | 11 | 0.197 | tbd | tbd | n/a (1 fold) | 1.0 | C | `low_sample_holdout` |
| QB | 68 | 10 | -0.208 | tbd | tbd | n/a (1 fold) | 1.0 | D — production-gated | `low_sample_holdout`, `negative_r2_lower_bound` |

TE is currently graded `C` with a `low_sample_holdout` caveat — its R² is positive and the modeling-backend review treated it as decision-usable with caveats, not production-gated. QB remains `D` because its R² lower bound is below zero. A position is demoted from `C` to `D` only when the composite gate explicitly fires (e.g., negative R² lower bound, Spearman below 0.30, top-K hit rate below 0.5), not because of sample size alone.

`tbd` cells become populated when Phase 0 ships the composite-gate script (`app/data/pipeline/validation/composite.py`). Until then, R² is the only gate component reported, and the gates above are treated as targets, not blockers.

## Revising a gate

A gate is not a sacred number. It is a current best estimate of "decision-usable enough." It is revised when:

1. New data shows a previous gate was too lenient (over-promoted to grade B too early), or
2. New data shows a previous gate was too strict (blocked a real improvement on small-sample noise), or
3. A new metric becomes available that makes an old criterion obsolete.

Revising a gate requires:

- A PR to this doc that names the old criterion, the new criterion, and the empirical reason for the change.
- A run of the composite-gate script demonstrating the new gate's behavior on the most recent training run.
- Acknowledgment that gate revisions are a soft form of "moving the goalposts" and should be rare.

Gates are not revised retroactively. A model artifact that passed an old gate keeps the model_grade it was assigned at the time, with the gate version recorded.
