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

### Task 5: Historical never-appeared population builder (coverage work allowed before root confirms; NO fitting)

**Files:** create `src/dynasty_genius/rookie/cold_start_model.py`; test file.

**Interfaces:**
- `never_appeared_population(*, rosters: DataFrame, draft_evidence_fn, outcomes: DataFrame, forecast_year: int, listed_statuses=("ACT","DEV","RES")) -> DataFrame` — one row per skill-position player LISTED on a season-`forecast_year` roster row (earliest week of that season's roster file, statuses ACT/DEV/RES) with NO championship-window appearance in any season < forecast_year (artifact rows 2001–forecast_year−1; a player whose entry season is ≥ 2001 so the absence is inside artifact coverage), with columns `gsis_id, forecast_year, position, age_at_forecast, entry_season, seasons_since_entry (k), draft_status, log_pick, round, listed_status` and labels for horizons 1–5: `appear_h, points_h, games_h` from the artifact (NaN when season > 2025), `label_source` (artifact | convention_zero as in the transition audit).
- Determinism and closure pinned: the roster file used is season `forecast_year`'s (point-in-time, not today's); labels only from seasons ≥ forecast_year; an entry season < 2001 row is excluded with a counted reason.

- [ ] Step 1 failing tests with a synthetic roster/artifact: a player listed in 2020 with no artifact rows before 2020 and a 2020 row → in population with `appear_1 == 1`; a player who appeared in 2018 → excluded; a player listed only in 2021 → not in the 2020 population; today's roster never read (the function receives only the rosters frame filtered by season inside; test passes a 2026 row and asserts it is ignored for forecast_year 2020); label for 2026 at forecast_year 2025 horizon 2 is NaN not 0.
- [ ] Steps 2–5; then run the builder on the real rosters/artifact for forecast years 2002–2025 and record the counts by k and draft status in the ticket as part of the candidate specification (root confirms before Task 6).

---

### Task 6 (only after root confirms the specification): candidate fit, evaluation, immutable run

Specification to send root (exact text in the ticket; repeated here so the plan carries it):

- **Population (historical):** skill-position players (QB/RB/WR/TE by season-T roster position) listed on the season-T roster file (ACT/DEV/RES, earliest week) with no championship-window appearance in seasons 2001..T−1 and entry season ≥ 2001; forecast years T = 2002–2025. Stratified by draft status (`drafted_verified` with draft features; `no_draft_record_*` without) and k = T − entry_season (1..5, capped at 5).
- **2026 candidates:** the ledger's `never_appeared_drafted` (11) and `never_appeared_no_draft_record` (58) rows, listed active/PS/IR in the 2026 census; the 15 dormant players are NOT in this candidate (a second, separately specified experiment: last observed production + absence length).
- **Target:** DG-179 championship-window outcomes (`049d2229…`): `appear_h` (≥1 window stat row in season T+h−1), `points_h` window PPR, `games_h`; horizons 1–5; no-appearance convention identical to both accepted producers (no stat row in a covered season = 0 / 0 / not appeared, tagged `convention_zero`).
- **Cutoffs:** at forecast year T the fit uses rows with forecast year ≤ T−h whose horizon-h labels are complete (season ≤ T−1); walk-forward T = 2011–2025 for evaluation (≥ 9 training years); every feature dated at T (roster listing, entry season, age, draft record — all fixed at or before T).
- **Features:** position, k (seasons since entry, as indicator 1/2/3/4/5+), age at forecast, and for drafted rows `log_pick, round` (draft-capital block × drafted indicator); nothing else. No market, no athletic score, no youth bonus.
- **Model:** per horizon h: logistic `P(appear_h)` (L2, C=1.0, StandardScaler) and ridge `E[points_h | appear_h]` (alpha 1.0) on appearers — the accepted rookie chain's estimators, pooled across positions with position main effects; `E[points_h] = P × E[·|appear]`. Per-season chain not needed for a start estimate (cumulative coherence follows from per-horizon fits reported separately; stated as a limitation).
- **Baselines (training-only, same rows):** B1 position × k mean appearance rate and mean points (the "position/experience mean"); B2 draft-capital logistic/ridge on `log_pick, round, position` for drafted rows only.
- **Primary comparison:** paired out-of-time Brier of `appear_1` and RMSE of unconditional `points_1` vs B1 on the pooled 2011–2025 rows, 2,000-draw player-cluster bootstrap of the difference (90%); secondaries: h = 2, 3; by position; by draft status; calibration (reliability, slope/intercept); vs B2 on drafted rows.
- **Acceptance (declared now):** the candidate is exported for a stratum (drafted / no draft record) only if its Brier and RMSE differences vs B1 at h=1 both have 90% intervals excluding zero in the candidate's favour AND no position within the stratum is harmed beyond its interval; otherwise that stratum's players are reported unresolved with the measured bound and the smallest next experiment. Zero-record players stay in every denominator with provenance.
- **Runtime:** ≈ 15 outer years × 5 horizons × 2 fits on ≤ 3,000 rows: seconds; bootstrap seconds. Whole run < 2 minutes.

Implementation steps (test-first, code written when root confirms; interfaces fixed now): `ColdStartCandidate.fit(train) / predict(frame)`, `evaluate_candidate(population, *, forecast_years, seed, draws) -> dict`, `export_sidecar(run_dir, candidates_2026, predictions, *, accepted_strata, manifest_binding)` → `cold_start_estimates.csv` (`sleeper_id, gsis_id, name, position, route, draft_status, estimate_class="cold_start_candidate", p_appear_year{j}, e_points_year{j}_given_appear, e_points_year{j}, e_games_year{j}` for j = 1..5 = seasons 2026–2030) + `unresolved.csv` (player, route, why, smallest next experiment) + `manifest.json` binding the coverage run, the accepted report sha, the artifact sha, the rookie run's input hashes, seed, draws, acceptance rule and the evaluation sha.

### Task 7: Final checks and handoff

- Full lane suite bare (no pipe), ruff, `git diff --check`, push; ticket entries with `date`; root reads the ticket; lane 25057 consumes the sidecar only after root's acceptance.
