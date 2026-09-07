# Stash-Selection Evaluation (DG-177) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested evaluator that answers, on frozen historical forecasts and common outcomes, whether the frozen future-production ordering identifies later contributors among low-production developmental candidates better than current production or draft capital do, at declared stash budgets, with player-resampled uncertainty and every convention named.

**Architecture:** One pure module (`src/dynasty_genius/eval/stash_selection.py`) of DataFrame-in / DataFrame-out functions plus one CLI (`scripts/dg177/run_stash_selection.py`) that hashes its inputs and the frozen definitions file, builds the candidate origin tables, attaches closed outcomes, computes the paired orderings and metrics, and writes one immutable run. No model is fitted; the frozen producer's out-of-fold forecasts are read as they are. Definitions are frozen in `docs/experiments/stash_selection_definitions_v1.json` BEFORE any result is inspected and hashed into the manifest.

**Tech Stack:** Python 3.14, pandas, numpy, pytest, ruff via pre-commit.

**Spec:** `/Users/davidleess/dg-build/AVAILABLE-PLAYERS-BUILD-2026-09-06.md`, section "DG177 / PID23481 — Stash-selection evaluation".

## Global Constraints

- Frozen inputs only; no retraining, no change to accepted forecasts, no new labels: `runs/20260906T195728Z/dg177_basic_horizons/historical_predictions.csv` (sha `f4fe6644…`, out-of-fold forecasts and closed labels per horizon), `basic_cohort.csv.gz` (sha `46e1fc01…`, origin features), DG-179 `outcomes.csv` (sha `199a48be…`, realized championship-window points 2001–2025), `app/data/backtest/qb_validation/raw/draft_picks/draft_picks_full.parquet` (sha `6be2a640…`, draft capital, joined by gsis id; only picks with draft season ≤ origin are visible).
- Candidate definition and outcome are frozen in `stash_selection_definitions_v1.json` before the first actual-data run; the CLI refuses to run without the file and hashes it into the manifest.
- Only origin-available evidence defines candidates and orderings: production through the origin season, NFL experience at the origin, draft facts with draft season ≤ origin. No contemporary roster membership, no post-outcome dates.
- Closed horizons only (`origin + j <= 2025`); censored years are excluded, never zero. Every outcome row carries `label_source` = `artifact_row` or `no_record_zero` (the artifact's zero convention for an identified player-season without an in-window stat record).
- This is a **historical low-production candidate screen**, not a waiver backtest: no point-in-time ownership source exists, so no fantasy-availability claim is made. No calibrated breakout probability is produced. A selection budget is a declared scenario, not David's optimal bench allocation.
- Exact ties are handled honestly: ranks are average ranks; a tie across a selection-budget boundary is disclosed and given fractional credit, never broken by an arbitrary order.
- No player names in code or tests; ids only.
- Outputs only under a NEW `runs/<UTC ts>/dg177_stash_selection/`; nothing else written.

## Frozen definitions (proposed to root before the first experiment; the JSON file is the record)

- **Origins:** basic-cohort rows with feature season t in 2011–2024, positions QB/RB/WR/TE.
- **Low production at origin:** DG-179 championship-window points in season t (authoritative, same window as the target; absent row = 0) below the position's starter line L(pos, t), where L is the N-th highest window points among the season-t cohort rows of that position and N is a declared 12-team starting-lineup scenario: QB 24, RB 36, WR 48, TE 18. Sensitivity: N × 0.5, N × 1.5, and DG-165's deep-roster relevance line (QB 37, RB 45, WR 71, TE 21), which is not a starting cutoff.
- **Developmental (observed-history stratum, not NFL experience):** `seasons_played <= 3`, i.e. stat-row seasons observed since 2005 at the origin. Sensitivity: `<= 2`, `<= 4`, no cut; alternative stratum `nfl_years_since_draft <= 3` for players with a verified draft season ≤ origin, reported separately.
- **Outcome, horizon j in {1, 2, 3}:** realized window points in season t + j; **contributor** = realized points ≥ L(pos, t + j), the realized starter line of that later season. Sensitivity: line scaled × 0.5 and × 1.5, and an absolute line of 100 window points. Cumulative variant: contributor in any of years 1–3 (origins ≤ 2022).
- **Orderings, paired on identical candidates within origin × position:** (a) current production = origin window points from DG-179 (sensitivity `total_points_t`, the all-games model feature, and `ppg_t`); (b) draft capital: overall pick ascending, undrafted after all drafted, ties averaged; (c) frozen future-production `policy_e_points_year{j}` (sensitivity `policy_p_appear_year{j}`, `candidate_e_points_year{j}`); (d) the frozen position-marginal `baseline_e_points_year{j}` is reported as a null reference since it cannot discriminate inside a cell.
- **Metrics:** Spearman rank correlation with realized points and AUC for the contributor flag, per cell and pooled; selection at fixed budget B in {2, 4, 8} per position per origin season: picks, hits (contributors picked), realized points captured, misses (contributors not picked), busts (picks with zero appearances in year j). Paired differences between orderings with a player-cluster bootstrap (1,000 draws, seed 20260906), per-origin-season tables disclosed, repeated-player counts disclosed.

## File Structure

- Create `docs/experiments/stash_selection_definitions_v1.json` — the frozen definitions (this task writes it; the CLI hashes it).
- Create `src/dynasty_genius/eval/stash_selection.py` — pure functions: definitions loading, starter lines, candidates, outcomes, orderings, metrics, selection at budget, paired bootstrap, manifest.
- Create `scripts/dg177/run_stash_selection.py` — CLI, immutable run.
- Create `tests/contract/test_stash_selection.py` — contract tests (synthetic ids).
- Create `docs/experiments/2026-09-06-dg177-stash-selection.md` — the record (Task 8).

Shared test header (every task appends below it):

```python
# tests/contract/test_stash_selection.py
"""DG-177 stash-selection evaluation: contract tests on synthetic ids (P1, P2, ...). No names, no real data."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval import stash_selection as ss

DEFS = json.loads(Path("docs/experiments/stash_selection_definitions_v1.json").read_text())


def cohort_row(player_id, season, *, position="WR", total_points_t=50.0, ppg_t=5.0, games_t=10, age=24, seasons_played=1, **over):
    row = {"player_id": player_id, "feature_season": season, "position": position, "total_points_t": total_points_t, "ppg_t": ppg_t,
           "games_t": games_t, "age": age, "seasons_played": seasons_played}
    row.update(over)
    return row


def outcome_row(player_id, season, points, games=None, appeared=None):
    games = int(round(points / 10)) if games is None else games
    return {"player_id": player_id, "season": season, "points": points, "games": games,
            "appeared": (games >= 1) if appeared is None else appeared}


def hist_row(player_id, origin, horizon, *, policy_points, p_appear=0.5, candidate_points=None, baseline_points=1.0, **over):
    j = horizon
    row = {"horizon": j, "player_id": player_id, "position": "WR", "feature_season": origin, "forecast_season": origin + j,
           f"policy_e_points_year{j}": policy_points, f"policy_p_appear_year{j}": p_appear,
           f"candidate_e_points_year{j}": policy_points if candidate_points is None else candidate_points,
           f"baseline_e_points_year{j}": baseline_points}
    row.update(over)
    return row
```

---

### Task 1: Frozen definitions file and its loader

**Files:**
- Create: `docs/experiments/stash_selection_definitions_v1.json`
- Create: `src/dynasty_genius/eval/stash_selection.py`
- Test: `tests/contract/test_stash_selection.py`

**Interfaces:**
- Produces: `DEFINITIONS_VERSION = "stash_selection_definitions_v1"`; `REQUIRED_DEFINITION_KEYS`; `load_definitions(path: Path) -> dict` (validates keys, returns the dict with `sha256` and `bytes` added under `_file`); `StashSelectionError(ValueError)`.

- [ ] **Step 1: Write the definitions file** (verbatim; this IS the pre-registration)

```json
{
  "version": "stash_selection_definitions_v1",
  "frozen_before_first_result": true,
  "origins": {"feature_seasons": [2011, 2024], "positions": ["QB", "RB", "WR", "TE"]},
  "low_production": {"rule": "realized championship-window points in the origin season below the position starter line",
                     "starter_slots": {"QB": 24, "RB": 36, "WR": 48, "TE": 18},
                     "sensitivity_slot_multipliers": [0.5, 1.0, 1.5]},
  "developmental": {"rule": "seasons_played at origin (observed since 2005) <= max_seasons_played",
                    "max_seasons_played": 3, "sensitivity": [2, 3, 4, null]},
  "outcome": {"horizons": [1, 2, 3], "points": "realized championship-window points in origin + horizon",
              "contributor": "realized points >= the realized starter line of that later season",
              "sensitivity_line_multipliers": [0.5, 1.0, 1.5], "absolute_line_points": 100.0,
              "cumulative": "contributor in any of years 1-3 (origins <= 2022)",
              "label_sources": ["artifact_row", "no_record_zero"], "censored_years": "excluded, never zero"},
  "orderings": {"current_production": ["total_points_t", "ppg_t"],
                "draft_capital": "overall pick ascending; undrafted after all drafted; ties averaged; draft season <= origin only",
                "future_production": ["policy_e_points_year{j}", "policy_p_appear_year{j}", "candidate_e_points_year{j}"],
                "null_reference": "baseline_e_points_year{j} (position marginal; no within-cell discrimination)"},
  "metrics": {"rank": ["spearman_vs_points", "auc_contributor"], "budgets_per_position_per_origin": [2, 4, 8],
              "selection": ["picks", "hits", "points_captured", "misses", "busts"],
              "ties": "average ranks; boundary ties get fractional credit and are counted",
              "uncertainty": {"method": "paired player-cluster bootstrap of ordering differences", "draws": 1000, "seed": 20260906}},
  "claims_not_made": ["waiver or availability backtest (no point-in-time ownership source)",
                      "calibrated breakout probability", "David's optimal bench allocation"]
}
```

- [ ] **Step 2: Write the failing test**

```python
def test_definitions_file_is_frozen_complete_and_hashed():
    d = ss.load_definitions(Path("docs/experiments/stash_selection_definitions_v1.json"))
    assert d["version"] == ss.DEFINITIONS_VERSION and d["frozen_before_first_result"] is True
    assert set(ss.REQUIRED_DEFINITION_KEYS) <= set(d)
    assert len(d["_file"]["sha256"]) == 64 and d["_file"]["bytes"] > 0
    assert d["low_production"]["starter_slots"] == {"QB": 24, "RB": 36, "WR": 48, "TE": 18}
    assert d["outcome"]["horizons"] == [1, 2, 3] and d["metrics"]["budgets_per_position_per_origin"] == [2, 4, 8]


def test_definitions_loader_refuses_a_file_missing_a_required_section(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"version": ss.DEFINITIONS_VERSION, "frozen_before_first_result": True}))
    with pytest.raises(ss.StashSelectionError, match="outcome"):
        ss.load_definitions(p)
```

- [ ] **Step 3: Run to verify RED** — `.venv/bin/python -m pytest -q tests/contract/test_stash_selection.py` → ImportError.

- [ ] **Step 4: Implement**

```python
"""DG-177 stash-selection evaluation: can the frozen future-production ordering find later contributors among
low-production developmental candidates? Frozen inputs only; definitions frozen before any result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


class StashSelectionError(ValueError):
    """A definitions, source or chronology condition under which the evaluator refuses."""


DEFINITIONS_VERSION = "stash_selection_definitions_v1"
REQUIRED_DEFINITION_KEYS = ("version", "frozen_before_first_result", "origins", "low_production", "developmental",
                            "outcome", "orderings", "metrics", "claims_not_made")


def load_definitions(path: Path) -> dict:
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    missing = [k for k in REQUIRED_DEFINITION_KEYS if k not in d]
    if missing:
        raise StashSelectionError(f"definitions file lacks {missing}")
    if d.get("version") != DEFINITIONS_VERSION or d.get("frozen_before_first_result") is not True:
        raise StashSelectionError("definitions must be the frozen v1 file")
    d["_file"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return d
```

- [ ] **Step 5: GREEN, lint, commit** — `git add docs/experiments/stash_selection_definitions_v1.json src/dynasty_genius/eval/stash_selection.py tests/contract/test_stash_selection.py && git commit -m "DG-177: stash-selection definitions frozen before any result; loader"`

---

### Task 2: Starter lines and the candidate cohort (origin-available only)

**Interfaces:**
- `starter_lines(cohort, outcomes, *, slots: dict, multiplier: float = 1.0) -> pd.DataFrame` columns `position, season, slots, line_points, rows_in_cell`; line = the N-th highest realized window points among that position's cohort rows in that season (absent outcome row → 0 under the artifact convention); a cell with fewer rows than N has `line_points = 0` and `rows_in_cell` disclosed.
- `candidates(cohort, outcomes, draft, *, definitions, slot_multiplier=1.0, max_seasons_played=3) -> pd.DataFrame` one row per (player_id, origin): `position, origin, total_points_t, ppg_t, games_t, age, seasons_played, origin_points, origin_label_source, origin_line, draft_season, draft_round, draft_pick, draft_visible (bool: draft_season <= origin), draft_capital_rank_key`; refuses a cohort row whose `feature_season` is outside the frozen origins; never reads any column dated after the origin.

Tests: a player above the line is excluded; below the line with `seasons_played` 4 is excluded under the default cut and included with `max_seasons_played=None`; an absent origin outcome is `no_record_zero` and counts as 0; a draft pick with draft season > origin is `draft_visible False` and treated as undrafted for ordering (ordering test in Task 4); a cell with fewer rows than the slot count has line 0 and everyone counts as above the line (excluded) — disclosed.

Commit: `DG-177: stash candidates from origin-available production, experience and visible draft facts`

---

### Task 3: Closed outcomes with label sources

**Interfaces:**
- `attach_outcomes(cands, outcomes, lines, *, horizons, last_complete_season=2025, absolute_line=100.0) -> pd.DataFrame` one row per (player_id, origin, horizon) with `target_season, realized_points, realized_games, appeared, label_source ("artifact_row"|"no_record_zero"), later_line, contributor (points >= later_line), contributor_abs (points >= absolute_line)`; rows with `target_season > last_complete_season` are DROPPED with a count returned in `.attrs["censored_dropped"]`; refuses if any target season lacks a starter line for the position.
- `cumulative_contributor(rows, horizons=(1, 2, 3)) -> pd.DataFrame` per (player_id, origin) with `any_contributor_1_3` only when all three horizons are closed.

Tests: censored year dropped and counted, never zero; absent later row → `no_record_zero`, points 0, contributor False; a contributor at ×1.0 that is not at ×1.5 (multiplier sensitivity via `lines` from Task 2); cumulative flag None/absent when a horizon is censored.

Commit: `DG-177: closed future outcomes with artifact-row / no-record labels and starter-line contributor flags`

---

### Task 4: Paired orderings from the frozen history

**Interfaces:**
- `attach_forecasts(rows, history) -> pd.DataFrame` joins `policy_e_points_year{j}`, `policy_p_appear_year{j}`, `candidate_e_points_year{j}`, `baseline_e_points_year{j}` from `history` on (player_id, feature_season=origin, horizon); refuses a candidate-horizon row with no history row (the producer scored every cohort row it could; a missing one is a chronology or source error, not a zero).
- `orderings(rows) -> pd.DataFrame` adds average-rank columns within (origin, position, horizon): `rank_current` (higher `total_points_t` first), `rank_current_ppg`, `rank_draft` (lower pick first; not visible/undrafted share the last average rank), `rank_future` (higher `policy_e_points_year{j}` first), `rank_future_appear`, `rank_future_candidate`, `rank_null` (baseline; constant → all tied).

Tests: draft ordering puts an invisible pick with the undrafted; exact ties share an average rank; missing history row refuses; ranks computed within cells only.

Commit: `DG-177: paired orderings (current production, draft capital, frozen future production, null reference)`

---

### Task 5: Rank discrimination and selection at a fixed budget

**Interfaces:**
- `spearman_by_cell(rows, rank_col) -> pd.DataFrame` and `auc_by_cell(rows, rank_col, flag_col) -> pd.DataFrame` per (origin, position, horizon) with `n`, `n_positive`, value (NaN when undefined: fewer than 3 rows or a single class), plus pooled rows weighted by n.
- `select_at_budget(rows, rank_col, budget, flag_col="contributor") -> pd.DataFrame` per cell: `budget, picks (= min(budget, n)), hits, points_captured, misses (= positives − hits), busts (picks with appeared False), boundary_ties (count of rows tied at the budget boundary), fractional_credit_applied (bool)`; with boundary ties, hits and points are credited fractionally in proportion to the tied rows selected.
- `compare_orderings(rows, ordering_cols, budgets) -> dict` pooled per horizon and position, and per origin season.

Tests: a perfect ordering has Spearman 1 and AUC 1; a constant ordering has NaN Spearman and AUC 0.5 with `all_tied` disclosed; budget larger than the cell picks everyone; a boundary tie gives fractional credit and is counted; busts counted from `appeared`; misses = positives − hits.

Commit: `DG-177: rank discrimination and selection-at-budget with honest ties, misses and busts`

---

### Task 6: Paired player-cluster bootstrap of ordering differences

**Interfaces:**
- `paired_difference_bootstrap(rows, metric_fn, ordering_a, ordering_b, *, draws, seed) -> dict` resamples players (all of a player's origins and horizons move as a block, drawn from the union of both arms — the same rows), returns `point, ci90, draws, clusters, rows, repeated_players (players with > 1 origin)`.
- `season_table(rows, metric_fn, ordering_cols) -> pd.DataFrame` per origin season, so the season clustering is visible.

Tests: identical orderings give a zero difference with a degenerate interval; the seed makes draws reproducible; clusters equal unique players; repeated players counted.

Commit: `DG-177: paired player-cluster bootstrap and per-season disclosure`

---

### Task 7: Manifest and CLI, immutable run

**Interfaces:**
- `build_manifest(*, definitions, sources, launch, counts, outputs) -> dict` with `schema_version = "dg177_stash_selection_v1"`, `claim = "historical low-production candidate screen; not a waiver backtest; no breakout probability"`.
- CLI `scripts/dg177/run_stash_selection.py --history … --cohort … --outcomes … --draft … --definitions docs/experiments/stash_selection_definitions_v1.json --out-root runs [--run-id]` reads every input once (`CapturedSource` from `league_scoring_audit`), writes `candidates.csv`, `outcome_rows.csv`, `metrics.json` (all sensitivities), `season_tables.csv`, `selection.csv`, `report.md`, `manifest.json`; refuses an existing run directory; refuses when the definitions sha differs from the one committed in this plan's Task 1 file.

Tests: end-to-end on tmp fixtures; refuses overwrite; manifest carries the definitions sha and every source sha; a history file that lacks a candidate row refuses.

Commit: `DG-177: stash-selection CLI writes an immutable hashed run`

---

### Task 8: Actual run, record, UI wording, DG-178 cross-check

- Run on the frozen files; verify hashes; write `docs/experiments/2026-09-06-dg177-stash-selection.md` with interpretation: per horizon and position, Spearman/AUC for the three orderings, selection at B ∈ {2, 4, 8} with hits/misses/busts, bootstrap intervals for future-minus-current and future-minus-draft, per-season tables, sensitivity grid, repeated-player disclosure, and the named limitations.
- Concise truthful UI wording for DG-178 (e.g., "Future ordering = expected championship-window points in the named years from the frozen model; on the 2011–2024 historical screen of low-production developmental players it found later starters [better / no better] than current production at a stash budget of N, with intervals; this is not a waiver backtest and not a breakout probability").
- Cross-check DG-178's current/future projected points for available players against `basic_forecasts.csv` rows to the third decimal.
- Commit the run and record, push, report to root.

## Self-review

Spec coverage: pre-registered cohort/outcome before the first experiment (Task 1 file + ticket note); origin-available evidence only (Task 2 draft visibility, no post-origin columns); paired comparison of current production, draft-capital baseline and frozen future ordering (Task 4); closed horizons, chronology, source hashes, label conventions (Tasks 3, 7); league-relevant contribution with sensitivity (definitions + Task 3); rank discrimination and selection-at-budget with misses and busts (Task 5); player resampling, origin tables preserved, repeated-player and season disclosure (Task 6); no availability claim, no breakout probability (constraints, manifest claim); tested evaluator, immutable audit, command/hashes, interpretation, UI wording, DG-178 cross-check (Tasks 7–8); no retraining (constraints). Placeholder scan: none. Type consistency: `rows` frames carry `origin, horizon, position, player_id, realized_points, appeared, contributor, label_source` from Task 3 and rank columns from Task 4, consumed by Tasks 5–7.
