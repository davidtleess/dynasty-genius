# Dynasty Genius — Agent Execution Plan

Step-by-step playbook for developer agents. Each step has a single owner, concrete files, dependencies, and acceptance criteria. Agents pick up a step, execute it, and ship.

- Strategy and architecture: [system-design.md](system-design.md) — read first
- Adapter and identity contracts: [data-source-contracts.md](data-source-contracts.md)
- Phase advancement criteria: [validation-gates.md](validation-gates.md)

## How agents work this doc

1. Pick the lowest-numbered step whose dependencies are satisfied and which has no `owner_agent` claim. Stamp your claim in the step's frontmatter (`owner_agent: <id>`, `claimed_at: <timestamp>`) via PR.
2. Read the three companion docs above and the step itself. Do not start until you can name every file you will touch.
3. Implement against the acceptance criteria. Out-of-scope items are out of scope — flag them as new steps if needed, do not silently absorb them.
4. Open a PR referencing the step number. The phase gate (in `validation-gates.md`) is what decides phase advancement, not your PR alone.
5. All paths in this doc are **repo-relative** (e.g. `app/data/ras.py`). The canonical GitHub remote is `https://github.com/davidtleess/dynasty-genius`.

## Cross-cutting requirements

These bind every step. PRs that violate them are rejected.

1. **Repo-relative paths only.** No absolute paths in code or docs.
2. **Versioned artifacts only.** Models, calibration files, aging curves, and metric formulas write to versioned directories (e.g. `app/data/models/runs/<timestamp>/`). Existing artifacts are never mutated.
3. **Validation report mandatory.** Every retraining or recalibration run produces a `validation_report.json` conforming to the composite-gate schema.
4. **Tests live under `tests/` mirroring `app/`.** Contract tests under `tests/contract/`. Adapter tests under `tests/data/`. Identity tests under `tests/identity/`. League-context tests under `tests/league/`.
5. **Snapshots before parsing.** Every adapter writes a raw snapshot before parse logic runs.
6. **No silent substitution.** Source failures degrade to caveats, not fallbacks to a different source.
7. **Pre-NFL features (Engine A) and active-NFL features (Engine B) live in separate feature pipelines.** Cross-contamination is a leakage defect.
8. **Counter-argument and risk_flags are required output fields** on every player decision card; generated from the threshold flag set, not freeform.
9. **Trade and roster outputs stay quarantined** until they read from the unified Player Value Object (Phase 7).
10. **No hardcoded thresholds.** Every threshold is read from `app/data/calibration/thresholds.yaml` with provenance.
11. **Metric formulas are versioned hypotheses.** Every metric implementation cites its source and records a `metric_version` on every value it produces.
12. **Personal context is core data, not config.** League settings, roster, picks, posture, and risk tolerance are loaded via `LeagueContext` (Phase 1) and consumed as first-class model inputs by every downstream surface.

---

## Phase 0 — Foundation Safety

### Step 0.1 — Reincorporate `agent/modeling-backend` validation work

- **Why**: That branch has the validation grading and report shape Phase 0+ depends on. Until it merges, Phase 0 is half-done.
- **Files**: PR-level merge; no file authorship in this step.
- **Inputs**: Current state of branches `agent/modeling-backend`, `main`.
- **Outputs**: `main` has the latest validation harness, model_grade taxonomy hooks, and any contract tests already written there.
- **Dependencies**: none.
- **Acceptance criteria**:
  - `git log main` shows the merged commits.
  - All tests on `main` pass (`pytest`).
  - No regression in the existing rookie / roster / trade contract tests.
- **Out of scope**: feature work on either branch; only the merge.
- **Estimated agent sessions**: 1.

### Step 0.2 — Tests scaffolding, type checking, and CI

- **Why**: Composite gates and contract ratchets need a test harness that runs on every PR. Type checking on adapter-shape and PVO-shape files prevents an entire class of contract-drift defects.
- **Files**:
  - `tests/__init__.py`, `tests/conftest.py`
  - `tests/contract/__init__.py`, `tests/contract/test_no_unvalidated_in_production.py`, `tests/contract/test_ratchet.py`, `tests/contract/test_no_silent_substitution.py`
  - `.github/workflows/ci.yml` (extend existing)
  - `requirements.txt` (add `mypy`)
  - `pyproject.toml` or `mypy.ini` (configure mypy to check `app/data/source_adapter.py`, `app/models/`, `app/data/identity/`, `app/data/league/` — start narrow; expand over time)
- **Outputs**: failing-but-skippable scaffolds for the contract tests; CI runs `pytest tests/` and `mypy` on every PR.
- **Dependencies**: 0.1.
- **Acceptance criteria**:
  - `pytest tests/` runs and reports zero unexpected failures (skips allowed for not-yet-implemented pieces).
  - `mypy` runs in CI against the configured paths and reports zero errors.
  - CI badge in README shows green on `main`.
  - The three contract test files exist with at minimum a module docstring stating what they enforce and `pytest.mark.xfail` placeholders.
- **Out of scope**: implementing the actual contract logic; expanding mypy coverage beyond the listed paths (each subsequent phase adds its own paths to the mypy config as it lands).
- **Estimated agent sessions**: 1.

### Step 0.3 — `app/config.py` central config loader

- **Why**: Today, league, season, and credentials live in env vars read at multiple points. A central loader prevents drift and simplifies testing.
- **Files**:
  - `app/config.py` (new)
  - `app/services/roster_auditor.py` (modify — read config via loader)
  - `tests/test_config.py` (new)
- **Outputs**: a typed `AppConfig` Pydantic model with explicit fields (`sleeper_username`, `sleeper_league_id`, `season`, etc.) and a `load_config()` function. Roster auditor consumes it.
- **Dependencies**: 0.1.
- **Acceptance criteria**:
  - `pytest tests/test_config.py` passes.
  - No code outside `app/config.py` reads `os.environ` for league / season / username.
- **Out of scope**: secret management for paid sources (handled in adapter steps); league context modeling (Phase 1).
- **Estimated agent sessions**: 1.

### Step 0.4 — `app/data/calibration/thresholds.yaml` with provenance

- **Why**: Removes hardcoded thresholds from code; gives each one provenance and a review date.
- **Files**:
  - `app/data/calibration/thresholds.yaml` (new)
  - `app/data/calibration/__init__.py`, `app/data/calibration/loader.py`
  - `app/services/rookie_evaluator.py` (modify — read thresholds via loader)
  - `app/services/roster_auditor.py` (modify — read `CLIFF_AGES` via loader; cliff ages remain heuristic until Phase 5 fitted curves replace them)
  - `tests/test_calibration.py` (new)
- **Outputs**:
  - YAML with at least: WR/RB/TE/QB cliff ages, age-at-entry flags, Dominator floors, RAS bands, YPRR floors. Each entry has `id`, `value`, `position`, `provenance` (`personal_calibration | fitted | published_source`), `source` (string), `last_reviewed` (date).
  - Loader returns typed objects.
- **Dependencies**: 0.3.
- **Acceptance criteria**:
  - No grep hits for the old constants in code paths.
  - `pytest tests/test_calibration.py` asserts every entry has all required fields and a non-null `provenance`.
  - `provenance: personal_calibration` thresholds carry through to decision cards as a `caveats` entry on any card that uses them.
- **Out of scope**: fitting curves (Phase 5); changing the actual numeric values.
- **Estimated agent sessions**: 1.

### Step 0.5 — Composite gate measurement script

- **Why**: Phases close on composite criteria, not single-number R². The script makes them measurable on every run.
- **Files**:
  - `app/data/pipeline/validation/__init__.py`, `app/data/pipeline/validation/composite.py`
  - `app/data/pipeline/train_models.py` (modify — invoke `composite.measure(run_dir)` after training)
  - `tests/data/test_composite_gates.py` (new)
- **Inputs**: definitions in `validation-gates.md`.
- **Outputs**: `validation_report.json` per run extended with: `r2`, `spearman`, `top_k_hit_rate`, `rmse_stability`, `null_coverage`, `caveat_hygiene`, `bootstrap_ci_90` for each numeric metric.
- **Dependencies**: 0.1, 0.2.
- **Acceptance criteria**:
  - `python -m app.data.pipeline.train_models` produces a new versioned run directory whose `validation_report.json` includes all composite-gate fields per position.
  - For positions with holdout rows < 30 (TE, QB), the report explicitly marks `r2: informational_only` and the gate logic ignores R² for them.
  - `pytest tests/data/test_composite_gates.py` passes.
- **Out of scope**: changing model training; only measurement around it.
- **Estimated agent sessions**: 2.

### Step 0.6 — `model_grade` gating in API

- **Why**: A model artifact that fails composite gates must not silently feed production decision cards.
- **Files**:
  - `app/services/rookie_evaluator.py` (modify — read `model_grade` from validation report; if `D` or `unvalidated`, set `caveats: ["model_grade_d_not_decision_grade"]`).
  - `app/api/routes/rookies.py` (modify — surface `model_grade` in response).
  - `tests/contract/test_no_unvalidated_in_production.py` (implement against current API).
- **Dependencies**: 0.5.
- **Acceptance criteria**:
  - `pytest tests/contract/test_no_unvalidated_in_production.py` passes.
  - Manual API call to `/api/rookies/...` returns `model_grade`. QB is currently `D` (production-gated). TE is currently `C` with the `low_sample_holdout` caveat — TE is **not** production-gated. Only `D` and `unvalidated` block production cards; `C` with caveats is decision-usable with a visible warning.
- **Out of scope**: UI gating (handled in Phase 11).
- **Estimated agent sessions**: 1.

**Phase 0 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 0 section.

---

## Phase 1 — League Context Foundation

David's league is core data, not configuration. This phase creates the typed object every downstream surface consumes for personalized reasoning.

### Step 1.1 — `LeagueContext` schema and loader

- **Why**: Without this, every downstream surface re-derives "what does David's league look like" inconsistently.
- **Files**:
  - `app/data/league/__init__.py`
  - `app/data/league/context.py` — Pydantic `LeagueContext` model
  - `app/data/league/loader.py` — `load_league_context() -> LeagueContext`
  - `app/data/league/david_league.yaml` — committed (no secrets); David's manually curated settings (posture, risk tolerance, taxi rules not in Sleeper)
  - `tests/league/__init__.py`, `tests/league/test_league_context.py`
- **Inputs**: Sleeper API (via existing `app/data/sleeper.py`); David's manual settings.
- **Outputs**: typed `LeagueContext` exposing:
  - `scoring`: PPR settings, bonus rules, etc.
  - `lineup_requirements`: starter slots per position, flex configuration, Superflex slot
  - `roster_size`, `taxi_size`, `ir_size`, `taxi_eligibility_rules`
  - `david.roster`: list of `RosterPlayer` (player_id, slot, contract status)
  - `david.draft_picks`: list across all known years × rounds
  - `david.posture`: enum `contender | sustained_contender | soft_rebuild`
  - `david.risk_tolerance`: enum `low | medium | high`
  - `league_mates`: list of `Team` (each with their own roster, picks, posture inferred from roster age curve)
  - `season`: int
- **Dependencies**: 0.6.
- **Acceptance criteria**:
  - `pytest tests/league/test_league_context.py` covers: cold load from Sleeper + YAML, posture override, missing-league-mate edge case, taxi/IR edge cases.
  - All fields populated for David's actual league on a live load.
  - YAML fields have `last_reviewed` dates.
- **Out of scope**: trade-partner-history (Step 1.3); opponent posture inference is a roster-age proxy in this step.
- **Estimated agent sessions**: 2.

### Step 1.2 — Wire `LeagueContext` into existing services

- **Why**: Roster auditor and any other current consumer must read `LeagueContext`, not env vars or ad-hoc Sleeper calls.
- **Files**:
  - `app/services/roster_auditor.py` (refactor)
  - `app/services/rookie_evaluator.py` (accept optional `LeagueContext` for needs-mode)
  - `tests/services/test_roster_auditor_with_context.py`
- **Outputs**: `LeagueContext` is the single source of truth for league-state reads.
- **Dependencies**: 1.1.
- **Acceptance criteria**:
  - Grep for `os.environ.get("DYNASTY_SLEEPER_LEAGUE_ID")` etc. returns zero hits outside `app/config.py` and `app/data/league/loader.py`.
  - Posture change in `david_league.yaml` (e.g., `contender` → `soft_rebuild`) flows through to at least one decision-card caveat or weight.
- **Estimated agent sessions**: 1.

### Step 1.3 — Trade-partner history seed (deferred-friendly)

- **Why**: Opponent-fit trade targeting in Phase 8 needs a history. This step seeds an empty history that David can populate manually as trades happen.
- **Files**:
  - `app/data/league/trade_history.yaml` (committed, append-only)
  - `app/data/league/history.py` — readers
  - `tests/league/test_trade_history.py`
- **Outputs**: an empty but well-typed history file; service path that returns zero-history gracefully.
- **Dependencies**: 1.1.
- **Acceptance criteria**: history file exists; reader returns empty list cleanly; schema validated by tests.
- **Out of scope**: actually populating history; opponent-fit modeling (Phase 8).
- **Estimated agent sessions**: 1.

**Phase 1 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 1 section.

---

## Phase 2 — Identity Resolution

Identity resolution exists *before* any external feature adapter so that every adapter consumes one canonical `player_id`. The seed pulls from `LeagueContext` (Phase 1) so David's league is fully resolved on day one.

### Step 2.1 — Identity layer skeleton

- **Why**: One canonical `player_id` table, one resolution function, one staging path.
- **Files**:
  - `app/data/identity/__init__.py`
  - `app/data/identity/canonical_mapping.csv` (initial seed from existing data)
  - `app/data/identity/resolution.py` — `resolve(source_name, source_player_id) -> player_id | None`
  - `app/data/identity/staging.py` — fuzzy match writes
  - `app/data/identity/triage/` (gitignored writes here)
  - `scripts/identity/promote.py` — staged → production with audit log
  - `tests/identity/test_resolution_exact.py`, `test_resolution_ambiguous.py`, `test_resolution_missing.py`, `test_id_conflict.py`, `test_promotion_audit.py`
- **Inputs**: existing IDs in `prospects_with_outcomes.csv`; players surfaced by `LeagueContext` (David's roster + league-mate rosters).
- **Outputs**: `canonical_mapping.csv` covering all players in the seed sets with deterministic IDs.
- **Dependencies**: Phase 1 closed.
- **Acceptance criteria**:
  - All 5 `tests/identity/*` files pass.
  - `canonical_mapping.csv` covers ≥ 95% of (`LeagueContext` players ∪ training set players ∪ last-3-seasons active players from nfl_data_py).
  - Fuzzy matches never write to `canonical_mapping.csv` directly. Verified by `test_promotion_audit.py`.
- **Out of scope**: source-specific IDs from PFF / PlayerProfiler / RAS / KTC — those columns are added when those adapters land.
- **Estimated agent sessions**: 2.

### Step 2.2 — Cross-source consistency check

- **Files**:
  - `app/data/identity/consistency.py`
  - `app/api/routes/identity.py` — read-only endpoint exposing the latest consistency report
  - `tests/identity/test_consistency.py`
- **Outputs**: a runnable script + cached report at `app/data/identity/consistency_report.json`.
- **Dependencies**: 2.1.
- **Acceptance criteria**:
  - Running `python -m app.data.identity.consistency` produces a JSON report with zero unresolved conflicts after 2.1's seed; or, conflicts are written to triage with explicit reasons.
  - `pytest tests/identity/test_consistency.py` passes.
- **Estimated agent sessions**: 1.

**Phase 2 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 2 section.

---

## Phase 3 — Source Adapter Contract + Raw Snapshots

Adapter shape is fully specified in [data-source-contracts.md](data-source-contracts.md). This phase implements the protocol and two adapters against it.

### Step 3.1 — `SourceAdapter` protocol and `RawSnapshot` types

- **Files**: `app/data/source_adapter.py` — Protocol class and dataclasses.
- **Outputs**: typed Protocol + `RawSnapshot` dataclass + `FreshnessReport` dataclass.
- **Dependencies**: Phase 2 closed.
- **Acceptance criteria**: `mypy app/data/source_adapter.py` passes; type used by both Sleeper and nfl_data_py adapters.
- **Estimated agent sessions**: 1.

### Step 3.2 — Sleeper adapter conforms to contract

- **Files**: `app/data/sleeper.py` (refactor); `tests/data/test_sleeper_parser.py`, `tests/data/test_sleeper_failure_modes.py`; fixtures under `tests/fixtures/sleeper/`.
- **Outputs**: Sleeper adapter implements `SourceAdapter`; emits normalized rows with all common columns; `LeagueContext` loader uses the new normalized rows.
- **Dependencies**: 3.1.
- **Acceptance criteria**:
  - Tests pass; `LeagueContext` reads through adapter, not raw API.
  - Sleeper has `fetch_automated()` plus a fixture-replay path used in tests. Manual export is **not implemented** for Sleeper — it's a free public API; outage is handled via stale-cache caveat surfacing, not manual ingest.
- **Estimated agent sessions**: 2.

### Step 3.3 — `nfl_data_py` adapter conforms to contract

- **Files**: `app/data/nfl_data_py_adapter.py` (new, may replace existing `pipeline/collect_draft_prospects.py` data path); fixtures under `tests/fixtures/nfl_data_py/`; tests parallel to 3.2.
- **Outputs**: adapter exposes historical and active-player rows behind one interface.
- **Dependencies**: 3.1.
- **Acceptance criteria**: parser + manual-export tests pass; `prospects_with_outcomes.csv` regeneration uses the adapter rather than ad-hoc package calls.
- **Estimated agent sessions**: 2.

### Step 3.4 — Snapshot caching layer + `app/data/cache/raw/` policy

- **Files**: `app/data/snapshots.py`; `.gitignore` update (ignore `app/data/cache/`); `tests/data/test_snapshots.py`.
- **Outputs**: any adapter `fetch_automated()` writes to `app/data/cache/raw/<source>/<season>/<timestamp>/`. Snapshots are immutable. No root-level `data/` directory is created.
- **Dependencies**: 3.1, 3.2.
- **Acceptance criteria**: snapshot directory layout matches `data-source-contracts.md`; tests assert no in-place mutation.
- **Estimated agent sessions**: 1.

### Step 3.5 — Freshness reports surfaced as caveats

- **Files**: modify `app/services/rookie_evaluator.py` and `app/services/roster_auditor.py` to consume `FreshnessReport`s.
- **Outputs**: any decision card whose source is stale carries a `caveats` entry like `"sleeper_stale_72h"`.
- **Dependencies**: 3.2, 3.3.
- **Acceptance criteria**: stale fixture produces stale-caveat in decision card response; `pytest tests/contract/test_no_silent_substitution.py` passes.
- **Estimated agent sessions**: 1.

**Phase 3 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 3 section.

---

## Phase 4 — Engine A Feature Expansion

Each metric step **except RAS** adds a model feature, backfills the training set, retrains, and runs composite gates. **Every metric is a versioned hypothesis** — implementation cites a published source, alternative formulations coexist where they exist, and the model run records `metric_version`.

**RAS is the explicit exception.** It does not enter the scoring feature set. Step 4.1 ingests RAS data; Step 4.2 derives risk/context flags (`ras_below_position_floor`, `ras_missing`, `ras_context_available`) but does not retrain the model on RAS columns. RAS does not positively contribute to `dynasty_value_score` under any circumstance.

### Step 4.1 — RAS adapter (red-flag/context only)

- **Files**:
  - `app/data/ras.py` — adapter conforming to `SourceAdapter`.
  - `tests/data/test_ras_parser.py`, `test_ras_manual_export.py`, `test_ras_failure_modes.py`.
  - Fixtures under `tests/fixtures/ras/`.
- **Outputs**: per-player RAS score + percentile + composite component scores.
- **Dependencies**: Phase 3 closed.
- **Acceptance criteria**: parser tests pass; identity layer resolves ≥ 95% of RAS rows for the 2015–2025 draft classes.
- **Estimated agent sessions**: 2.

### Step 4.2 — RAS into Engine A as risk-flag input only

- **Why**: RAS is a red-flag/context signal, not a floor metric. Published research finds no correlation between high RAS and WR fantasy success; treating high RAS as a positive feature would let it raise `dynasty_value_score` in a way the data does not support.
- **Files**:
  - `app/data/pipeline/train_models.py` — RAS is **not added** as a continuous positive feature into the trained model.
  - `prospects_with_outcomes.csv` regeneration — adds raw `ras_score` and `ras_percentile` columns for downstream flag derivation, but the model's training feature set does not include them.
  - `app/services/rookie_evaluator.py` — emits the following RAS-derived signals on the decision card: `ras_below_position_floor` (boolean risk flag, threshold from `thresholds.yaml`), `ras_missing` (boolean caveat), `ras_context_available` (boolean indicating the score is present for transparency).
  - `tests/services/test_rookie_evaluator_ras.py` — asserts that high RAS does not produce a higher `dynasty_value_score` than low RAS when all other features are held equal.
- **Outputs**: RAS signals appear in `risk_flags` and `caveats` only. The raw `ras_score` is shown on the card as context but does not contribute to `dynasty_value_score`.
- **Dependencies**: 4.1.
- **Acceptance criteria**:
  - The model artifact's feature list (in the run's `validation_report.json`) does not contain RAS columns.
  - Unit test in `tests/services/test_rookie_evaluator_ras.py` constructs two prospects identical except for RAS (one at 9.5, one at 5.0) and asserts their `dynasty_value_score` values are equal. The lower-RAS prospect carries `risk_flags: ["ras_below_position_floor"]` if below the threshold; otherwise both cards are equal in score and differ only in displayed context.
  - Decision card `top_drivers` never includes a RAS-positive contribution.
- **Out of scope**:
  - Adding RAS as a continuous positive feature (forbidden by `system-design.md`).
  - A low-RAS-only penalty feature in the model — explicitly **not** done in this step. If a future analysis shows a low-RAS penalty improves composite gates, it lands as a separate step with explicit acceptance criteria; until then, RAS lives only in flags and caveats.
- **Estimated agent sessions**: 2.

### Step 4.3 — Metric versioning pattern (Dominator first)

- **Why**: Demonstrates the formula-as-versioned-hypothesis discipline that every Phase 4 metric must follow.
- **Files**:
  - `app/data/metrics/__init__.py`, `app/data/metrics/dominator.py` — `dominator_v1_dupont`, `dominator_v2_rotoviz`, `dominator_v3_playerprofiler` coexist.
  - `app/data/metrics/registry.py` — registry mapping `metric_version` → callable.
  - `tests/data/test_metrics_dominator.py` — known-input known-output tests for each version, plus a comparison test.
- **Outputs**: training rows record which `metric_version` they consumed.
- **Dependencies**: 4.2.
- **Acceptance criteria**: All three Dominator versions return values for the same player; comparison test asserts the values differ in expected directions on edge cases; `prospects_with_outcomes.csv` regeneration writes a `dominator_metric_version` column.
- **Out of scope**: choosing a winner; that comes from backtest.
- **Estimated agent sessions**: 2.

### Step 4.4 — College Dominator + Breakout Age adapter

- **Files**:
  - `app/data/playerprofile.py` (refactor existing) — Dominator + Breakout Age columns.
  - `tests/data/test_playerprofile_*` — full set.
  - `app/data/metrics/breakout_age.py` — versioned formula (`breakout_age_v1` based on Dominator threshold by season).
- **Outputs**: training rows have `college_dominator` and `breakout_age` columns with `metric_version` recorded.
- **Dependencies**: 4.3.
- **Acceptance criteria**: parser + identity tests pass; ≥ 90% coverage on the training set.
- **Estimated agent sessions**: 3.

### Step 4.5 — Add Dominator + Breakout Age to Engine A

- **Files**: `train_models.py`, `rookie_evaluator.py`.
- **Outputs**: composite gates report on the new model. Top-3 drivers in the rookie card now include Dominator / Breakout Age where appropriate.
- **Dependencies**: 4.4.
- **Acceptance criteria**: WR composite gate satisfies Phase 4 floors at point estimate; lower bound improvement vs. baseline reported.
- **Estimated agent sessions**: 1.

### Step 4.6 — YPRR adapter + ingestion

- **Files**:
  - `app/data/pff.py` — full adapter conforming to contract; both automated scrape and manual-CSV-export paths.
  - `app/data/pff_manual_export_schema.md` — required CSV columns.
  - `tests/data/test_pff_*` — full set.
- **Outputs**: per-player season-level YPRR, route_pct, snap counts, grades.
- **Dependencies**: 4.5. (PFF adapter also unblocks Engine B.)
- **Acceptance criteria**: parser + manual-export tests pass; identity coverage ≥ 90%; freshness report populated.
- **Estimated agent sessions**: 3.

### Step 4.7 — Add YPRR to Engine A (WR / TE)

- **Files**: training pipeline; rookie evaluator.
- **Outputs**: YPRR is a model feature for WR/TE. Driver attribution updates.
- **Dependencies**: 4.6.
- **Acceptance criteria**: WR composite gate improves vs. 4.5 by at least one criterion; TE Spearman ≥ 0.30 point estimate.
- **Estimated agent sessions**: 1.

### Step 4.8 — Weighted Opportunity (RB) — versioned formulas

- **Files**:
  - `app/data/metrics/weighted_opportunity.py` — `weighted_opp_v1_barrett` (Scott Barrett's published formula) and `weighted_opp_v2_pff` (PFF variant).
  - Tests parallel to 4.3.
  - Modify pipeline to populate `weighted_opportunity` for RB rows in the training set, recording `metric_version`.
- **Outputs**: an RB feature whose published R² (~0.82 vs. RB fantasy points, per Barrett) is recorded as **provenance/context** in metric metadata, not as a pass/fail gate.
- **Dependencies**: 4.6.
- **Acceptance criteria** (composite-gate style):
  - Adding `weighted_opportunity` to the RB feature set produces a measurable lift versus the current RB baseline on at least one of: Spearman rank correlation, top-K hit rate, RMSE.
  - No regression beyond composite-gate tolerance on the other criteria (RMSE stability, null coverage).
  - Both formula versions are computable on the same training rows; comparison report exists in the run dir.
  - Published external R² is recorded in `metric_provenance` JSON for each version; not enforced as a pass/fail.
- **Out of scope**: choosing `barrett` vs. `pff` as the canonical version — that is decided by backtest in Phase 10.
- **Estimated agent sessions**: 2.

### Step 4.9 — Add Weighted Opportunity to Engine A (RB)

- **Files**: pipeline + rookie_evaluator for RB.
- **Acceptance criteria**: RB composite gate satisfies Phase 4 floors; driver attribution surfaces `weighted_opportunity` as a top driver where applicable.
- **Estimated agent sessions**: 1.

### Step 4.10 — TPRR (WR / TE)

- **Files**: `app/data/metrics/tprr.py` (versioned); pipeline + rookie_evaluator.
- **Outputs**: leading-indicator feature for receivers; surfaces in cards as `tprr_above_threshold` flag from `thresholds.yaml`.
- **Dependencies**: 4.6, 4.7.
- **Acceptance criteria**: WR holdout Spearman improves vs. 4.7.
- **Estimated agent sessions**: 2.

### Step 4.11 — Model family swap if gradient-boosted beats Ridge

- **Files**: `train_models.py` — gate the swap on a head-to-head composite-gate comparison; both artifacts written, `latest.json` points to the winner.
- **Outputs**: a documented swap (or a documented decision to stay with Ridge) in the run's metadata.
- **Dependencies**: 4.10.
- **Acceptance criteria**: comparison report exists in the run dir; the chosen family wins on ≥ 3 of the 6 composite criteria for at least 2 positions.
- **Estimated agent sessions**: 2.

**Phase 4 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 4 section.

---

## Phase 5 — Fitted Aging Curves

Aging curves are continuous fitted artifacts, not hardcoded cliff constants. Engine B (Phase 6) consumes them; Phase 8 decision surfaces consume them.

### Step 5.1 — Fit per-position aging curves from `nfl_data_py`

- **Files**:
  - `app/data/calibration/aging_curves/` — versioned fitted curves per position (`wr_v1.parquet`, etc.) and `latest.json` pointer.
  - `app/data/pipeline/fit_aging_curves.py` — fits per-position decline curves from `nfl_data_py` historicals (GAM or LOESS with bootstrap CIs).
  - `app/services/aging.py` — `years_to_decline(player) -> {expected, lower, upper}` reads the curve.
  - `tests/data/test_aging_curves.py`.
- **Inputs**: `nfl_data_py` PPG-by-age data for last 15 seasons.
- **Outputs**: a fitted continuous artifact per position; `app/services/aging.py` consumed by roster auditor in place of `CLIFF_AGES` constants.
- **Dependencies**: Phase 4 closed.
- **Acceptance criteria**:
  - Roster auditor no longer references hardcoded cliff ages.
  - The curves' implied half-decline ages are recorded in artifact metadata and diff'd against the framework's heuristic ages (RB 26 / WR 28 / TE 30 / QB 33). Whatever the curves say is the system's source of truth from this point.
  - `pytest tests/data/test_aging_curves.py` passes.
- **Out of scope**: rebuilding the roster auditor's decision card (Phase 8).
- **Estimated agent sessions**: 2.

**Phase 5 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 5 section.

---

## Phase 6 — Engine B MVP (Active Player Forecast)

Engine B is a separate model and a separate feature pipeline. Cross-contamination with Engine A's pre-NFL features is a leakage defect.

### Step 6.1 — Active-player feature collection pipeline

- **Files**: `app/data/pipeline/collect_active_features.py`; tests under `tests/data/`.
- **Inputs**: PFF (4.6), nfl_data_py (3.3), aging curves (5.1).
- **Outputs**: per-player season rows with `target_share`, `route_pct`, `snap_share`, `weighted_opportunity` (RB), `aging_curve_state`. Rows are forward-looking: feature year `T`, target year `T+1` (no leakage).
- **Dependencies**: Phase 5 closed.
- **Acceptance criteria**: training set covers 2018–2024 with ≥ 90% null coverage per position.
- **Estimated agent sessions**: 3.

### Step 6.2 — Engine B model training

- **Files**: `app/data/pipeline/train_engine_b.py`; tests; new run directory under `app/data/models/runs/`.
- **Outputs**: per-position Engine B Ridge model (or gradient-boosted, decided as in 4.11) with composite-gate report.
- **Dependencies**: 6.1.
- **Acceptance criteria**: composite gates as defined in Phase 6 of `validation-gates.md`.
- **Estimated agent sessions**: 2.

### Step 6.3 — Engine B service skeleton

- **Files**: `app/services/active_player_forecast.py`; route stub at `app/api/routes/active_player.py` returning experimental responses.
- **Outputs**: a typed service that returns Engine B projections in the unified valuation shape (defined in Phase 7).
- **Dependencies**: 6.2.
- **Acceptance criteria**: service is callable; route returns experimental flag and `model_grade` per position.
- **Estimated agent sessions**: 1.

**Phase 6 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 6 section.

---

## Phase 7 — Unified Player Value Object

### Step 7.1 — `PlayerValueObject` schema

- **Files**: `app/models/pvo.py`; `tests/contract/test_pvo_schema.py`.
- **Inputs**: shape from `system-design.md`; `LeagueContext` (Phase 1) for league-context fields; `app/models/valuation.py` (existing `DynastyValuation`).
- **Outputs**: a Pydantic model that supersedes the rookie-only valuation shape and includes league-context fields (`roster_fit_signal`, `position_scarcity`, `championship_window_weight`, `trade_liquidity`).
- **Dependencies**: Phase 6 closed.
- **Acceptance criteria**: model defined and used in unit tests; round-trip JSON serializable; league-context fields populate when `LeagueContext` is provided.
- **Estimated agent sessions**: 1.

### Step 7.2 — `value_for(player_ref, context)` resolver

- **Files**: `app/services/unified_valuation.py`; tests under `tests/services/`.
- **Outputs**: `value_for(player_id, league_context)` returns a fully-populated PVO using Engine A or B (or a hybrid handoff at age 24 ± 1 year). Resolver respects `inputs_present` / `inputs_missing` discipline and joins league context.
- **Dependencies**: 7.1.
- **Acceptance criteria**: every active player in `LeagueContext` and every prospect from the last 5 seasons has exactly one PVO row; coverage gate satisfied.
- **Estimated agent sessions**: 2.

**Phase 7 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 7 section.

---

## Phase 8 — Decision Surfaces

Every surface decomposes its outputs into the layers required by the "No Mystery Rankings" rule (model / market / roster context / counterargument / missing data).

### Step 8.1 — Rookie Board (BPA / Needs)

- **Files**: refactor `app/api/routes/rookies.py` to read from `value_for()` with `LeagueContext`; add `mode=bpa|needs` query param; add roster-fit post-filter for `mode=needs`.
- **Acceptance criteria**: rookie cards conform to the universal decision card schema; switching modes does not change the underlying score, only the ordering / filtering.
- **Estimated agent sessions**: 2.

### Step 8.2 — Roster Audit upgrade

- **Files**: refactor `app/services/roster_auditor.py` to read PVOs; add `value_minus_replacement` and `years_to_cliff` (from fitted curve, not constant); incorporate David's posture from `LeagueContext`.
- **Acceptance criteria**: ratchet test passes (no `action` field comes back); cards include caveats for any signal_completeness below `nfl_year1`; recommendations weighted by posture.
- **Estimated agent sessions**: 2.

### Step 8.3 — Trade Lab over PVO

- **Files**: refactor `app/services/trade_analyzer.py` and `app/api/routes/trade.py`; extend `tests/contract/test_ratchet.py` to assert `verdict` is never emitted.
- **Acceptance criteria**:
  - Trade endpoint returns per-asset PVO + delta + uncertainty band.
  - Endpoint emits `delta_status` (enum: `within_model_error | likely_favors_me | likely_favors_them | insufficient_confidence`), computed from the uncertainty band on the delta and the `model_grade` of the assets involved. `insufficient_confidence` is returned when any asset on either side has `model_grade` worse than `C`.
  - The banned `verdict` field is never emitted. Ratchet test asserts this.
  - No aggregated `total` or `difference` field — only per-asset PVOs and the structured `delta_status`.
- **Estimated agent sessions**: 2.

### Step 8.4 — Waiver Radar (gated)

- **Files**: `app/services/waiver_radar.py`; `app/api/routes/waiver.py`.
- **Dependencies**: PFF route_pct + snap_share live (from 4.6).
- **Acceptance criteria**: top-N candidates by `dynasty_value_score` filtered to available players (per `LeagueContext.league_mates`); cards explicitly note Year-1 route_pct as the headline driver.
- **Estimated agent sessions**: 1.

### Step 8.5 — League Pulse + opponent-fit trade targeting

- **Files**: `app/services/league_pulse.py`, `app/services/opponent_fit.py`; `app/api/routes/league.py`.
- **Outputs**: every team in David's league scored on the same scale, with team-level dynasty_value_total and contender/rebuilder classification. Opponent-fit suggests which league-mate values a given player most.
- **Dependencies**: 7.2, 1.3.
- **Acceptance criteria**: every Sleeper roster in the league produces a PVO list and a team total; opponent-fit returns ≥ 1 plausible trade target for any David asset.
- **Estimated agent sessions**: 3.

**Phase 8 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 8 section.

---

## Phase 9 — Market Overlay (KTC)

### Step 9.1 — KTC adapter

- **Files**: `app/data/ktc.py` (refactor existing); manual-export path = saved HTML dump; tests parallel to PFF.
- **Acceptance criteria**: adapter conforms to contract; identity coverage ≥ 90% of `LeagueContext` rosters.
- **Estimated agent sessions**: 2.

### Step 9.2 — `market_overlay` field on PVO

- **Files**: `app/models/pvo.py`; `app/services/unified_valuation.py`; `tests/contract/test_ktc_not_in_features.py` (the critical anti-leak test).
- **Acceptance criteria**: `market_overlay` populated when KTC coverage exists; `null` otherwise. Contract test passes — no model artifact's feature list contains a KTC column.
- **Estimated agent sessions**: 1.

**Phase 9 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 9 section.

---

## Phase 10 — Backtest Harness

The backtest harness is a David-facing product surface, not internal QA.

### Step 10.1 — Backtest dataset builder

- **Files**: `app/data/pipeline/build_backtest.py`; output at `app/data/backtest/<run_version>/<position>.parquet`.
- **Outputs**: time series joining model predictions, KTC market values, realized fantasy outcomes.
- **Dependencies**: Phase 9 closed.
- **Estimated agent sessions**: 2.

### Step 10.2 — Backtest API

- **Files**: `app/services/backtest.py`; `app/api/routes/backtest.py`.
- **Outputs**: `/api/backtest/<position>?model_version=...` returns the time series for charting.
- **Acceptance criteria**: tests under `tests/backtest/` exercise the endpoint against fixture data.
- **Estimated agent sessions**: 1.

### Step 10.3 — Engine B backtest extension

- **Files**: extend 10.1 to include Engine B predictions vs. realized.
- **Acceptance criteria**: Engine B time series joinable with Engine A on the same position chart.
- **Estimated agent sessions**: 1.

**Phase 10 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 10 section.

---

## Phase 11 — Frontend (last, intentionally)

Default recommendation: Next.js + TypeScript + Tailwind, served alongside the FastAPI backend. Confirm with David before scaffolding.

### Step 11.0 — Frontend tech choice + scaffolding

- **Files**: `web/` directory; `web/package.json`; `web/README.md`.
- **Outputs**: minimal app that fetches `/api/rookies/...` and renders one decision card with all required fields.
- **Acceptance criteria**: dev server runs; one card visible end-to-end; design system documented.
- **Estimated agent sessions**: 2.

### Step 11.1–11.5 — Page-by-page

| Page | Source | Acceptance criteria |
| --- | --- | --- |
| 11.1 Rookie Board | `/api/rookies` | BPA / Needs toggle works; cards greyed when `model_grade=D` |
| 11.2 Roster | `/api/roster/audit` | All caveats visible; no `action` language; posture-weighted recommendations |
| 11.3 Trade Lab | `/api/trade/analyze` | `delta_status` leaves `within_model_error` only when the band excludes zero; opponent-fit suggestions |
| 11.4 Backtest | `/api/backtest` | Per-position chart with model / KTC / realized lines |
| 11.5 League Pulse + Waiver | `/api/league`, `/api/waiver` | Read-only, gated until prerequisites land |

Each page is one agent session; design system is shared.

**Phase 11 advancement gate**: see [validation-gates.md](validation-gates.md) — Phase 11 section.

---

## Risks and Mitigations

### 1. PFF / PlayerProfiler scraper breakage or block

- **Likelihood**: high over a 12+ month horizon.
- **Mitigation**: every paid-source adapter has a `ingest_manual_export(path)` path day one. If automated breaks, the operator drops a CSV / HTML dump into a watched directory. Every adapter test exercises both paths.

### 2. KTC silent influence on the model

- **Likelihood**: medium — feels harmless to "just add it as a feature."
- **Mitigation**: `tests/contract/test_ktc_not_in_features.py` fails CI if any model artifact's feature list contains a KTC column. Architectural rule, machine-enforced.

### 3. Train / holdout leakage on Engine B target offset

- **Likelihood**: medium.
- **Mitigation**: feature year `T`, target year ≥ `T+1`. Validation-report schema records both fields; gate refuses to ship a run where they overlap.

### 4. Overfitting on small TE / QB samples

- **Likelihood**: high — TE has 11 holdout rows, QB has 10.
- **Mitigation**: composite gates explicitly mark TE / QB R² as informational below 30 holdout rows; advancement is on Spearman + Top-K, not R². QB cards remain `model_grade: D` until QB lower-bound R² > 0.

### 5. Identity drift across sources

- **Likelihood**: medium — common players will resolve cleanly, but every source has long-tail mismatches.
- **Mitigation**: cross-source consistency check (Step 2.2). Any mismatch triages, never silently re-resolves. Promotions are audited.

### 6. League Context staleness

- **Likelihood**: medium — David trades, league-mates trade, posture changes mid-season.
- **Mitigation**: `LeagueContext` is loaded fresh per request from Sleeper; manual settings in `david_league.yaml` carry `last_reviewed` dates; staleness is surfaced as a card caveat.

---

## Do-Not-Do (premature features explicitly deferred)

Per `system-design.md` non-goals. Restating here so step-implementers see them in their working doc:

- Multi-league abstraction unless it directly supports David's primary league
- Authentication, multi-user, billing, roles
- Public API or SaaS exposure
- Mobile app
- Real-time draft mode
- Mock draft simulator
- League chat or trade chat assistant
- Social features (followers, comments, sharing)
- Push notifications
- DFS / best-ball-specific tooling
- Public leaderboards / premium tiers
- A free-form AI chat surface that bypasses the structured decision-card layer

If David revises the non-goals list, that change happens in `system-design.md`, not by an in-line PR here.

---

## Workstream ownership for parallel agents

- One agent at a time inside any single step. Claim via PR before starting.
- Multiple agents can work in parallel only on disjoint adapters within the same phase (e.g., RAS adapter and Dominator adapter), with disjoint write paths.
- Cross-cutting files (`thresholds.yaml`, `app/models/pvo.py`, `app/data/identity/canonical_mapping.csv`, `app/data/league/context.py`, `app/data/league/david_league.yaml`) are owned by one agent at a time. Touch one of these → blocking lock.
- Every agent commit message references the step number it is executing (`Step 5.1: fit aging curves for WR/RB`).
