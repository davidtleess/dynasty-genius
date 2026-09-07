# Unowned Cold-Start Forecasts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested coverage/resolution tool that proves, per player, who the 84 unowned default-pool players without a forecast are and why (identity, NFL/fantasy status, draft evidence, NFL history, route), then a separately labelled cold-start candidate — population, target and evaluation confirmed by root BEFORE any fit — exported as a manifest-bound sidecar for the 2026 candidates only if its evidence passes the declared acceptance rule.

**Architecture:** One pure module `src/dynasty_genius/rookie/cold_start.py` for coverage (hash-verified loaders → default-pool reconciliation against the accepted report → three-source draft evidence → NFL history from the DG-179 artifact → route classification → immutable ledger), a second module `src/dynasty_genius/rookie/cold_start_model.py` for the candidate (historical never-appeared population builder → walk-forward fit/evaluation against two baselines → sidecar export), two thin CLIs. Fail-closed throughout: an unverifiable byte, an unreconciled count, an absent identity or a non-finite value refuses.

**Tech Stack:** Python 3.14, pandas 3.0.5, numpy, scikit-learn 1.8.0 (LogisticRegression / Ridge, as in the accepted rookie chain), pytest (`PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest`), ruff at `~/.cache/pre-commit/repocesie9_t/py_env-python3.14/bin/ruff`. Imports use the repo convention `from src.dynasty_genius…`.

**Spec:** `/Users/davidleess/dg-build/AVAILABLE-PLAYERS-BUILD-2026-09-06.md` (DG165 / PID24974 section).

## Global Constraints

- Worktree `~/dg-wt/DG-165`, branch `ticket/DG-165`, start `d625923b`. Own DG-165 files only; DG-178 / DG-177 / DG-179 runs are read-only inputs.
- "Never overwrite 825 accepted rows or alter original source exceptions." Every prior run and frozen forecast preserved; new outputs only under `runs/<UTC>/…` via `create_run_dir`.
- "Do not label absence from draft table UDFA or zero appearance as observed individual-complete truth." Draft status is `drafted_verified` only on a positive draft record; absence across sources is `no_draft_record_<n>_sources`, never "UDFA".
- "Never equate an NFL free agent with an unowned fantasy player." Fantasy ownership comes from the census `league_owned`; NFL status from `availability_class`.
- Candidate: "Before fitting a new candidate, send root its exact population, target, training/held-out years, no-appearance convention, baseline, features, acceptance criteria and runtime estimate." No fit until root confirms. "No arbitrary youth bonus, athletic score boost, position uplift, market input or global refit." "No contemporary NFL roster membership in historical selection, no post-outcome feature dates, no future-cutoff labels."
- Sidecar keyed by verified Sleeper + GSIS identity, forecast years 2026–2030, definitions compatible with the accepted producers (appearance = ≥1 stat row in the championship window; season points = window PPR; conditional output = points given appearance), `estimate_class = "cold_start_candidate"`, exported only for accepted routes; unresolved players listed with reason.
- Commit explicit paths only; `date` before every ticket stamp; a test command gating a commit runs bare (no pipe) — a piped summary is not a gate.

---

## File structure

| File | Responsibility |
|---|---|
| `src/dynasty_genius/rookie/cold_start.py` (create) | `load_census_run`, `load_accepted_report`, `missing_default_pool`, `draft_evidence`, `nfl_history`, `route_for`, `build_ledger`, `write_coverage` |
| `scripts/dg165/audit_cold_start_coverage.py` (create) | CLI → `runs/<UTC>/dg165_cold_start_coverage/{ledger.csv, summary.json, REPORT.md, manifest.json}` |
| `src/dynasty_genius/rookie/cold_start_model.py` (create, Task 5 population builder now; Tasks 6–7 after root confirms) | `never_appeared_population`, `ColdStartCandidate`, `evaluate_candidate`, `export_sidecar` |
| `scripts/dg165/run_cold_start_candidate.py` (create, Task 6) | CLI → `runs/<UTC>/dg165_cold_start_candidate/` |
| `tests/contract/test_dg165_cold_start.py` (create) | contract tests for both modules with synthetic fixtures |

Ledger column contract (`ledger.csv`, exactly 84 rows on the real data, one per missing player; asserted against the report's coverage block):

```
sleeper_id, name, league_position, fantasy_positions, availability_class, nfl_team, nfl_status_raw,
gsis_id, join_basis, sleeper_gsis_agrees, identity_status,
draft_status, draft_sources_positive, draft_sources_checked, draft_season, draft_round, draft_pick, draft_position, draft_sources_agree,
birth_date, age_2026, entry_season, rookie_season, college,
nfl_appearance_seasons, first_appearance_season, last_appearance_season, seasons_since_last_appearance, window_points_last_season,
dg177_2025_feature_row, dg177_2025_forecast_row, dg177_last_feature_season, dg165_rookie_2026_row,
route, route_reason, inputs_available
```

Draft-status strings: `drafted_verified`, `no_draft_record_3_sources`, `no_draft_record_2_sources`, `no_draft_record_1_source`, `draft_sources_conflict`, `unknown_identity`.
Route strings: `existing_forecast_join_failure`, `never_appeared_drafted`, `never_appeared_no_draft_record`, `dormant_drafted`, `dormant_no_draft_record`, `unknown_identity`.

---

### Task 1: Hash-verified loaders and the default-pool reconciliation

**Files:**
- Create: `src/dynasty_genius/rookie/cold_start.py`
- Test: `tests/contract/test_dg165_cold_start.py`

**Interfaces:**
- `load_census_run(run_dir) -> CensusRun(run_dir, report: dict, census: DataFrame, uncovered: DataFrame, census_sha256: str)` — reads `report.json`, then `census.csv` and `uncovered.csv` as bytes, hashes them, compares to `report["census_csv_sha256"]` / `report["uncovered_csv_sha256"]`; raises `ValueError` on mismatch or missing declaration; asserts `sleeper_id` unique.
- `load_accepted_report(path) -> AcceptedReport(path, report: dict, sha256: str, forecast_sleeper_ids: frozenset[str], forecast_player_ids: frozenset[str])` — hashes the bytes as parsed; `forecast_*` from `report["comparable_board"]["all_inspectable"]`; raises if `report["current_census"]["census_csv_sha256"]` differs from the census run's sha when both are given to `missing_default_pool`.
- `missing_default_pool(census: CensusRun, accepted: AcceptedReport) -> DataFrame` — unowned (`league_owned == False`) rows with `availability_class in DEFAULT_POOL = ("active", "practice_squad", "injured_reserve")` and no forecast by `sleeper_id`; RECONCILES against `accepted.report["current_census"]["coverage"]` (default pool total, with-forecast, missing) and raises if any count differs; returns the missing rows sorted by `(availability_class, league_position, name)`.

- [ ] **Step 1: Write the fixture builder and failing tests**

```python
# tests/contract/test_dg165_cold_start.py
"""Contract tests for the unowned cold-start coverage tool (DG-165, available-players build 2026-09-06)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_census_run(root: Path, *, census: pd.DataFrame | None = None) -> Path:
    run = root / "census"
    run.mkdir(parents=True)
    if census is None:
        census = pd.DataFrame({
            "sleeper_id": ["1", "2", "3", "4", "5", "6", "7"],
            "name": ["Owned Vet", "Active NoFc", "PS NoFc", "IR HasFc", "Cut NoFc", "Active HasFc", "Unknown"],
            "league_position": ["WR", "QB", "RB", "TE", "WR", "WR", "TE"],
            "fantasy_positions": ["WR", "QB", "RB", "TE", "WR", "WR", "TE"],
            "sleeper_status": ["Active"] * 7, "sleeper_team": ["A"] * 7,
            "sleeper_gsis_id": [None, "00-B", None, "00-D", None, "00-F", None],
            "nfl_team": ["A", "B", "C", "D", None, "F", None], "nfl_position": ["WR", "QB", "RB", "TE", None, "WR", None],
            "nfl_status_raw": ["ACT", "ACT", "DEV", "RES", None, "ACT", None],
            "nfl_gsis_id": ["00-A", "00-B", "00-C", "00-D", None, "00-F", None],
            "availability_class": ["active", "active", "practice_squad", "injured_reserve", "cut", "active", "unknown"],
            "join_basis": ["sleeper_id"] * 6 + ["none"], "identity_conflict": [False] * 7,
            "league_owned": [True, False, False, False, False, False, False], "roster_id": [3, None, None, None, None, None, None],
            "contested_nfl_gsis_id": [None] * 7,
        })
    uncovered = pd.DataFrame({"sleeper_id": ["99"], "name": ["Nobody"], "league_position": ["WR"], "sleeper_status": ["Inactive"],
                              "sleeper_team": [None], "sleeper_gsis_id": [None], "reason": ["not_listed"]})
    cb = census.to_csv(index=False).encode(); ub = uncovered.to_csv(index=False).encode()
    (run / "census.csv").write_bytes(cb); (run / "uncovered.csv").write_bytes(ub)
    report = {"run": "20260906T000000Z", "season": 2026, "census_csv_sha256": _sha(cb), "uncovered_csv_sha256": _sha(ub),
              "counts": {"members": len(census)}, "sources": {}}
    (run / "report.json").write_text(json.dumps(report, sort_keys=True))
    return run


def make_accepted_report(root: Path, census_dir: Path, *, coverage: dict | None = None) -> Path:
    rows = [{"player_id": "00-A", "sleeper_id": "1", "name": "Owned Vet", "position": "WR", "producer": "vet"},
            {"player_id": "00-D", "sleeper_id": "4", "name": "IR HasFc", "position": "TE", "producer": "vet"},
            {"player_id": "00-F", "sleeper_id": "6", "name": "Active HasFc", "position": "WR", "producer": "vet"}]
    census_sha = json.loads((census_dir / "report.json").read_text())["census_csv_sha256"]
    report = {"run": "20260906T000001Z", "comparable_board": {"all_inspectable": rows},
              "current_census": {"census_csv_sha256": census_sha,
                                 "coverage": coverage or {"default_pool_unowned": 4, "with_forecast": 2, "missing_forecast": 2}}}
    path = root / "accepted_report.json"
    path.write_text(json.dumps(report, sort_keys=True))
    return path


def test_census_loader_verifies_bytes_and_unique_ids(tmp_path):
    from src.dynasty_genius.rookie.cold_start import load_census_run
    run = make_census_run(tmp_path)
    c = load_census_run(run)
    assert len(c.census) == 7 and c.census_sha256 == json.loads((run / "report.json").read_text())["census_csv_sha256"]
    (run / "census.csv").write_text((run / "census.csv").read_text().replace("Owned Vet", "Owned Vet!"))
    with pytest.raises(ValueError, match="sha256"):
        load_census_run(run)


def test_missing_default_pool_reconciles_with_the_accepted_report(tmp_path):
    from src.dynasty_genius.rookie.cold_start import load_accepted_report, load_census_run, missing_default_pool
    census = load_census_run(make_census_run(tmp_path))
    accepted = load_accepted_report(make_accepted_report(tmp_path, tmp_path / "census"))
    miss = missing_default_pool(census, accepted)
    assert miss["name"].tolist() == ["Active NoFc", "PS NoFc"]  # cut and unknown are NOT in the default pool; owned excluded
    bad = load_accepted_report(make_accepted_report(tmp_path / "b", tmp_path / "census",
                                                    coverage={"default_pool_unowned": 4, "with_forecast": 2, "missing_forecast": 3}))
    with pytest.raises(ValueError, match="reconcile"):
        missing_default_pool(census, bad)
```

- [ ] **Step 2: Run to verify failure** — `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_cold_start.py -q -x` → `ModuleNotFoundError: No module named 'src.dynasty_genius.rookie.cold_start'`.

- [ ] **Step 3: Implement** — dataclasses + the three functions exactly as in Interfaces; `DEFAULT_POOL` constant; reconciliation compares `len(default)`, `int(has_forecast.sum())`, `len(missing)` with the coverage block's `default_pool_unowned`, `with_forecast`, `missing_forecast` (the real report's key names are confirmed in Task 4 Step 1 before the real run; if they differ, the adapter maps them explicitly and a test pins the mapping).

- [ ] **Step 4: Run to verify pass** — 2 passed. **Step 5: Commit** (`git add` the two files + this plan).

---

### Task 2: Three-source draft evidence, positively labelled

**Files:** modify `cold_start.py`; test file.

**Interfaces:**
- `draft_evidence(gsis_ids: pd.Series, *, draft_picks: DataFrame, players: DataFrame, rosters: DataFrame) -> DataFrame` with columns `gsis_id, draft_status, draft_sources_positive, draft_sources_checked, draft_season, draft_round, draft_pick, draft_position, draft_sources_agree, entry_season, rookie_season, birth_date, college`.
- Sources: (1) `draft_picks` row by `gsis_id` (season, round, pick, position); (2) `players` row `draft_year / draft_round / draft_pick / draft_team`; (3) latest `rosters` row `draft_number / draft_club / entry_year / rookie_year`. A source is positive when its draft fields are non-null. `draft_status = drafted_verified` if ≥1 positive source AND all positive sources agree on season and pick (`draft_number` is the overall pick); `draft_sources_conflict` if positive sources disagree; else `no_draft_record_<n>_sources` where n = sources that HAVE a row for the id (0 rows → `unknown_identity`).
- `entry_season` = players `rookie_season` else rosters `entry_year`; `birth_date` from players else rosters; `age_2026` = age on 2026-09-01.

- [ ] Step 1 failing test: a drafted id agreed by 3 sources → `drafted_verified`, `draft_sources_agree True`; an id absent from all three draft fields but present in players/rosters → `no_draft_record_3_sources`; an id with `draft_picks` pick 40 and rosters `draft_number` 41 → `draft_sources_conflict`; an id in no table → `unknown_identity`; the word "UDFA"/"undrafted" appears in no status string (`assert not any("udfa" in s or "undrafted" in s for s in statuses)`).
- [ ] Step 2 red → Step 3 implement → Step 4 green → Step 5 commit.

---

### Task 3: NFL history, existing-forecast join check, route, ledger

**Files:** modify `cold_start.py`; test file.

**Interfaces:**
- `nfl_history(gsis_ids, *, outcomes: DataFrame (DG-179 rows), basic_cohort: DataFrame, basic_forecasts: DataFrame, rookie_scores: DataFrame) -> DataFrame` with `nfl_appearance_seasons` (count of artifact rows with `appeared`), `first_appearance_season`, `last_appearance_season`, `seasons_since_last_appearance` (2025 − last, NaN when never), `window_points_last_season`, `dg177_2025_feature_row` (bool), `dg177_2025_forecast_row` (bool), `dg177_last_feature_season`, `dg165_rookie_2026_row` (bool).
- `route_for(row) -> tuple[str, str]` (route, reason), in order: `unknown_identity` if draft_status is unknown_identity; `existing_forecast_join_failure` if `dg177_2025_forecast_row or dg165_rookie_2026_row` (a forecast exists for this GSIS but the board has none for this Sleeper id — a join to investigate, never a new estimate); `never_appeared_*` if `nfl_appearance_seasons == 0`; else `dormant_*`; suffix `drafted` / `no_draft_record` from draft_status (conflict → `no_draft_record` with reason naming the conflict).
- `build_ledger(missing: DataFrame, evidence: DataFrame, history: DataFrame) -> DataFrame` — exactly `len(missing)` rows (asserted), the column contract above, `inputs_available` = comma-joined list of non-null input fields per player.

- [ ] Step 1 failing tests: a player with a DG-177 2025 forecast row under his GSIS but missing on the board → `existing_forecast_join_failure`; a never-appeared drafted player → `never_appeared_drafted`; a player last seen 2023 with no draft record → `dormant_no_draft_record` and `seasons_since_last_appearance == 2`; ledger row count equals the missing count and NaN never becomes 0 (`nfl_appearance_seasons` is 0 only when the artifact has rows for other players in the same seasons — assert the absent-from-artifact player has `first_appearance_season` NaN and `nfl_appearance_seasons` 0 with reason text containing "no stat row"; the ledger must not call it "zero production" as observed truth — the `route_reason` for never-appeared says "no championship-window stat row in the artifact 2001–2025; not a claim of zero individual production").
- [ ] Steps 2–5 as before.

---

### Task 4: Immutable writer, CLI, real-data run, peer report

**Files:** modify `cold_start.py`; create `scripts/dg165/audit_cold_start_coverage.py`; test file.

- `write_coverage(run_dir, ledger, *, census, accepted, input_hashes: dict, git_sha) -> manifest` writing `ledger.csv`, `summary.json` (counts by route × draft_status × availability_class × position, join-failure ids, entry-season histogram of never-appeared), `REPORT.md` rendered from summary, `manifest.json` (schema `dg165_cold_start_coverage_v1`, every input path+sha, outputs sha; refuses if outputs exist).
- CLI args: `--census-run`, `--accepted-report`, `--rookie-run` (for the hashed nflverse inputs + rookie_scores), `--veteran-run` (basic cohort/forecasts, read-only), `--outcomes-csv` (must hash to the rookie manifest's bound sha), `--runs-root`.
- [ ] Step 1: confirm the real report's coverage key names (`python -c` read of `current_census.coverage`) and pin the mapping in a test; Step 2 red (writer/CLI); Step 3 implement; Step 4 green + ruff + lane suite; Step 5 commit.
- [ ] Step 6: real run:

```bash
PYTHONPATH=. .venv/bin/python scripts/dg165/audit_cold_start_coverage.py \
  --census-run /Users/davidleess/dg-wt/DG-178/runs/20260906T202057Z/dg178_current_census \
  --accepted-report /Users/davidleess/dg-wt/DG-178/runs/20260906T214512Z/dg178_audit/report.json \
  --rookie-run runs/20260906T195904Z/dg165_rookie_capital \
  --veteran-run /Users/davidleess/dg-wt/DG-177/runs/20260906T195728Z/dg177_basic_horizons
```

Expected (from the read-only preflight, re-derived not carried over): 84 rows = 20 active + 50 practice squad + 14 IR; WR 33 / RB 21 / QB 15 / TE 15; never appeared 69 (58 no draft record, 11 drafted), dormant 15 (8 drafted, 7 no record); 4 `existing_forecast_join_failure` candidates (a DG-177 2025 forecast row exists under the GSIS). Any departure is a finding.
- [ ] Step 7: commit the run; ticket entry (`date`); message lane 25057 with the join-failure ids (their board, their join — report, never patch).

---

### Task 5: Frozen never-record population builder from the raw REG captures (NO fitting)

> **WITHDRAWN 2026-09-06 (root's scientific gate):** the earlier "listed on the season-T roster file, earliest week" population. Annual roster files are end-of-season survivor rows (2018 rows are weeks 17–21; coverage jumps 2015→2016) — outcome-period survivor selection, not point-in-time eligibility. It must not be built.

**Files:** create `src/dynasty_genius/rookie/cold_start_model.py`; test file `tests/contract/test_dg165_cold_start_model.py`.

**Frozen definition (root, confirmed independently 20:51 EDT):** resolved skill draftees (draft position QB/RB/WR/TE) of classes 2001–2025 with NO full-regular-season stat record through the draft season, read from the raw weekly REG captures at `runs/20260906T191723Z/weekly_source_capture/` (27 parquet hashes verified against the capture manifest before any row is read). 424 players: WR 150 / QB 118 / RB 85 / TE 71. Origin T = c + 1 (career year 2); horizons h = 1..5 = career years 2–6; a class-c row's horizon-h label is usable at origin T only if c + h < T (season ≤ T − 1 complete); evaluation origins T = 2012–2025 with closed test rows 210 / 199 / 187 / 179 / 172 and first-origin (2012) training rows 199 / 184 / 164 / 141 / 119 at h = 1..5. Every washout stays regardless of any later roster. No roster membership at any date is used. The championship-window-absence definition (adds 35 final-week players) is kept only as a comparison column.

**Interfaces:**
- `verify_capture(capture_dir) -> dict[str, str]` — hashes every raw parquet against the capture manifest's `files` declarations; refuses a missing or altered file.
- `first_full_reg_season(capture_dir) -> pd.Series` — gsis_id → first season with any REG stat row (any week), from the verified files.
- `never_record_population(*, cohort: DataFrame (rookie cohort.csv), first_reg: Series, outcomes: DataFrame, players: DataFrame) -> DataFrame` — one row per eligible draftee with `gsis_id, name, draft_season, origin_year (= draft_season + 1), draft_position, pick, round, log_pick, age_at_origin (Sep 1 of origin year; NaN when no birth date), window_absent_through_draft_season (comparison column)` and labels `appear_h, points_h, games_h, label_source_h` for h = 1..5 from the artifact (NaN when the season is not complete ≤ 2025; `convention_zero` when the season is complete but the artifact has no row).
- `support_table(population, *, origins=range(2012, 2026), horizons=(1,2,3,4,5)) -> DataFrame` — per origin and horizon: training rows (c + h < T with complete labels), training appearers, per-position training rows/appearers, test rows (class T − 1 with complete label); recorded BEFORE any fit.

- [ ] Step 1 failing tests with a synthetic capture (two tiny parquets + a manifest with their hashes) and artifact: a 2015 draftee with a 2015 REG row → excluded; with a 2016 REG row only → eligible with `appear_1 == 1`; a draftee whose first REG row is in a week-18 game of the draft season → excluded (full-REG rule, unlike the window rule); an altered parquet → `verify_capture` refuses; a label for season 2026 is NaN; a complete season with no artifact row is `convention_zero`; support counts for a small hand-built population equal the hand count.
- [ ] Steps 2–5; then a test against the real files (skipped when absent) asserts the frozen counts (424 by position; 210/199/187/179/172; 199/184/164/141/119).

---

### Task 6: candidate fit, evaluation, immutable run (root authorized 2026-09-06 after the population/source contract tests pass)

Frozen by root before results (no variation on results):

- **Population/chronology:** exactly the Task 5 population; T = c + 1; c + h < T for training; evaluation T = 2012–2025; first-fold and per-horizon eligible/excluded/appearer support recorded before fitting.
- **Features at origin:** draft position dummies, `log_pick`, `round`, age as of Sep 1 of the origin year (birth date source-backed at the draft; missing → the fold's training-position median, no indicator). All scalers, medians and encoders fit on that fold's training rows only. No market, athletic, youth or roster features.
- **Candidate (hurdle, per horizon, independent):** logistic `P(appear_h)` (L2, C = 1.0, StandardScaler) on [log_pick, round, age, position dummies] — requires both appearance classes in training; ridge `E[points_h | appear_h]` (alpha 1.0) on [log_pick, position dummies] over training appearers; `E[points_h] = P × E[·|appear]`; games likewise. No hyperparameter search.
- **B1 (training-only, same cohort):** position-cell mean appearance rate and mean unconditional points/games (an empirical rate/mean may be 0); conditional severity for a position cell with ZERO training appearers is **unsupported** (no number; never NaN×0); a position cell needs ≥ 10 same-position training observations to carry a labelled rough baseline, and per-position denominators/appearers are reported — the pooled ≥ 60 / ≥ 15 rule is the candidate's floor, not evidence that every position has support.
- **B2 (exploratory, frozen):** logistic/ridge on [log_pick, round, position dummies] — age removed; reported only, never used for selection.
- **Comparison:** all metrics on the SAME paired supported player/origin rows with the same exclusions; per horizon: paired Brier(appear_h) and RMSE(unconditional points_h) vs B1, 2,000-draw player-cluster bootstrap, 90%; per-origin and per-position tables (sparse cells shown with their n); calibration (reliability, slope/intercept).
- **Selection (per horizon, declared):** both paired intervals favourable vs B1 → candidate for that horizon; otherwise B1's estimate for that horizon is a `baseline_research_candidate` with its measured out-of-time error and support — never advertised as a proven improvement. Selecting on this historical evaluation is retrospective model selection, NOT independent confirmation of the selected policy; both arms are reported. No per-position model shopping after results. Final UI acceptance waits for root's reading of the actual outputs.
- **Wording:** "not conditioned on remaining on a current roster; direction and size of this mismatch have not been measured." No calibrated breakout probability; P(appear) is appearance only.
- **Actual rules added by root before results and implemented (final tool `0e2db9e1`):** age missing → the fold's training POSITION median, then the overall TRAINING median only when that position has no observed age, unsupported when no training age exists (fallback counts recorded); conditional games (given appearance) bounded to [1, 17] after prediction, E[games] = P × bounded conditional, points never clamped; a B1 position cell needs ≥ 10 training rows and ≥ 1 appearer for its conditional mean — a selected baseline cell without a conditional mean exports the horizon as `unsupported`, never a partial path; the RMSE interval is computed in RMSE units per draw (sqrt of resampled mean squared errors for both arms), with the mean-squared-error interval reported separately; strict booleans on the artifact, incoherent closed rows refuse, duplicate cohort identity/draft keys refuse, the capture must affirm every season 2001–2025 exactly once with no failures; the exporter enforces verified identity, `drafted_verified`, route `never_appeared_drafted`, class 2025, skill draft position, origin exactly 2026 with seasons 2026–2030, complete binding, finite values, probabilities in [0, 1], the games bound and both P × conditional identities; launch git sha and launched_utc are captured before any input is read.
- **Runtime:** < 1 minute including the bootstrap.

Implementation (test-first): `ColdStartCandidate.fit(train) / predict(frame)`, `baseline_b1(train) / predict`, `baseline_b2`, `evaluate(population, *, origins, seed, draws) -> dict`, `export_sidecar(run_dir, seven, predictions, *, selected_per_horizon, binding)` → `cold_start_estimates.csv` (`sleeper_id, gsis_id, name, draft_position, route, draft_status, estimate_class_year{j} ∈ {cold_start_candidate, baseline_research_candidate, unsupported}, p_appear_year{j}, e_points_year{j}_given_appear, e_points_year{j}, e_games_year{j}, season_year{j}` for j = 1..5 = 2026–2030) + `unresolved.csv` (the other 77 ledger players with route, why, smallest valid next experiment) + `support.csv` + `evaluation.json` + `REPORT.md` + `manifest.json` binding the capture manifest hash, the 27 parquet hashes, the artifact sha, the cohort/inputs hashes, the coverage run, seed, draws, and the frozen acceptance rule verbatim.

---

### Task 7: Final checks and handoff

- Full lane suite bare (no pipe), ruff, `git diff --check`, push; ticket entries with `date`; root reads the ticket; lane 25057 consumes the sidecar only after root's acceptance.
