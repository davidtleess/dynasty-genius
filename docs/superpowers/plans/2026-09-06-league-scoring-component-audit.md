# League Scoring Component Audit (DG-177, 2025) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested, reproducible tool that builds a 2025 player-week scoring-component ledger from the retained weekly stats, play-by-play and Sleeper matchup records, scores it under the saved league rules crediting individual keys only, reconciles it against Sleeper's actual player-week points, and writes one immutable run with every mismatch and every unresolved case named.

**Architecture:** One pure module (`src/dynasty_genius/eval/league_scoring_audit.py`) of DataFrame-in / DataFrame-out functions with no I/O except two loaders; one CLI (`scripts/dg177/run_league_scoring_audit.py`) that hashes inputs, calls the module, and writes a new run directory; one small provenance helper (`src/dynasty_genius/eval/run_provenance.py`) that captures git HEAD and dirty state at LAUNCH, wired into the two existing forecast runners. Weekly nflverse totals are the authority for component COUNTS; play-by-play provides the event grain and the special-teams / own-vs-opponent / lost split; any disagreement between the two is `unresolved`, never patched.

**Tech Stack:** Python 3.14, pandas, pyarrow, pytest (`.venv/bin/python -m pytest`), ruff via pre-commit.

**Spec:** `/Users/davidleess/dg-build/PLAYER-COMPARISON-BUILD-2026-09-06.md` (Lane 23481) and `/Users/davidleess/dg-build/NEXT-INCREMENT-PROPOSAL-2026-09-06.md` (DG-177 section). Preflight evidence: DG-177 ticket, "READ-ONLY PREFLIGHT" entry.

## Global Constraints

- No full-history labels, no model refit, no revised player forecasts; frozen runs and companions stay byte-identical.
- No shared writes, installs, merges, promotion, publication, production restart; outputs only under a NEW `runs/<UTC ts>/dg177_league_scoring_audit/` directory.
- Credit individual scoring keys only. `fum_rec`, `ff`, `int`, `sack`, `safe`, `blk_kick`, `def_*`, `pts_allow_*` are team-defense keys and never become individual bonuses. No IDP setting is inferred from a DST key.
- Event grain is `(game_id, play_id, event_slot, player_id)`; every event carries a status.
- Full 2025 REG weeks 1–18 are audited for source comparison; the championship window is weeks 1–17 and is labelled separately; week 18 is never silently included.
- Never hardcode player names; never patch the eight residuals observed in preflight; unexplained differences are `unresolved`.
- Any unsupported applicable key, unknown key, or required unresolved attribution forbids exact-league qualification (`league_scoring_exact` stays `false`). The rostered comparison is never called full-universe proof.
- Test first: every production function has a RED test before it exists.
- Root's independent counterexamples are regression fixtures (synthetic ids, same structure): a play with more fumbles in its description than structured slots (slot capacity is NOT a universal ledger); an OWN-team special-teams recovery that Sleeper paid nothing for (uncredited, not unresolved); a recovery touchdown paid +6 with no +2; an extra lost fumble paid −2 with the opponent-ball recovery on the same offensive play uncredited; an end-zone out-of-bounds loss with no recovery id (lost, no invented recovery player); a special-teams classifier conflict (`special_teams_play` vs play-type family); equal duplicate Sleeper observations collapsed explicitly, conflicting ones flagged; week-18 rows kept with the championship flag false; the one −0.5 provider residual stays visible and unresolved.
- Recovery touchdowns and special-teams touchdowns are separate nflverse stat ids: never subtract one weekly count from the other; a recovery touchdown on a special-teams play has no ground truth and is unresolved.
- Sources (read-only, hashed into the manifest):
  - weekly `/Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/identified_weekly.parquet` (sha `6f7c76cc…`)
  - quarantine `/Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/quarantine.parquet` (sha `a0f4d9c6…`)
  - play-by-play `/Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/pbp/pbp_2025.parquet` (sha `5ed293fd…`)
  - Sleeper matchups `/Users/davidleess/dynasty-genius-product/app/data/research/league_behavior/raw/2026-07-19/season_2025_1183088915091423232/` (`matchups_week_01..18.json`, `league.json`)
  - league snapshot `/Users/davidleess/dynasty-genius-product/app/data/league_runtime/runs/league-20260906T130052Z/snapshot.json` (scoring settings sha `3ffeb558…`)
  - identity map `/Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/ff_playerids/ff_playerids_full.parquet` (columns `sleeper_id`, `gsis_id`; 6 duplicated sleeper ids must be treated as ambiguous)

## File Structure

- Create `src/dynasty_genius/eval/run_provenance.py` — `launch_provenance()`: git HEAD, branch, dirty flag, UTC time, argv, captured when called.
- Modify `scripts/experiments/dg177_basic_horizons.py` and `scripts/experiments/dg177_annual_forecasts.py` — call `launch_provenance()` first thing in `main()`, use its HEAD for the manifest, record both launch and finish blocks.
- Create `src/dynasty_genius/eval/league_scoring_audit.py` — pure scoring/attribution functions, loaders for Sleeper matchups and the identity map, manifest builder.
- Create `scripts/dg177/run_league_scoring_audit.py` — CLI: hash inputs, run, write immutable run.
- Create `tests/test_dg177_run_provenance.py`, `tests/contract/test_league_scoring_audit.py`.

Shared fixture helpers live at the top of the contract test file (no conftest edits):

```python
# tests/contract/test_league_scoring_audit.py (header; every task appends tests below it)
"""DG-177 league scoring component audit: pure attribution/scoring contract tests.

Fixtures use synthetic ids (P1, P2, ...) and teams (AAA, BBB). No player names, no real data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval import league_scoring_audit as lsa

SETTINGS = {  # the saved league settings, verbatim from league-20260906T130052Z/snapshot.json
    "blk_kick": 2.0, "def_st_ff": 1.0, "def_st_fum_rec": 1.0, "def_st_td": 6.0, "def_td": 6.0, "ff": 1.0,
    "fgm_0_19": 3.0, "fgm_20_29": 3.0, "fgm_30_39": 3.0, "fgm_40_49": 4.0, "fgm_50p": 5.0, "fgmiss": -1.0,
    "fum": 0.0, "fum_lost": -2.0, "fum_rec": 2.0, "fum_rec_td": 6.0, "int": 2.0, "pass_2pt": 2.0,
    "pass_int": -2.0, "pass_td": 4.0, "pass_yd": 0.04, "pts_allow_0": 10.0, "pts_allow_14_20": 1.0,
    "pts_allow_1_6": 7.0, "pts_allow_21_27": 0.0, "pts_allow_28_34": -1.0, "pts_allow_35p": -4.0,
    "pts_allow_7_13": 4.0, "rec": 1.0, "rec_2pt": 2.0, "rec_td": 6.0, "rec_yd": 0.1, "rush_2pt": 2.0,
    "rush_td": 6.0, "rush_yd": 0.1, "sack": 1.0, "safe": 2.0, "st_ff": 1.0, "st_fum_rec": 1.0, "st_td": 6.0,
    "xpm": 1.0, "xpmiss": -1.0,
}

WEEKLY_ZERO = {c: 0 for c in lsa.WEEKLY_COMPONENT_COLUMNS}


def weekly_row(player_id, week, *, season_type="REG", position="RB", **over):
    row = {"player_id": player_id, "season": 2025, "week": week, "season_type": season_type, "position": position,
           **WEEKLY_ZERO}
    row.update(over)
    return row


def weekly(rows):
    return pd.DataFrame([weekly_row(**r) if isinstance(r, dict) else r for r in rows])


PBP_DEFAULTS = {"season_type": "REG", "play_type": "run", "special_teams_play": 0, "fumble": 1, "fumble_lost": 0,
                "fumble_out_of_bounds": 0, "play_deleted": 0, "touchdown": 0, "rush_touchdown": 0, "pass_touchdown": 0,
                "return_touchdown": 0, "td_player_id": None, "td_team": None,
                "fumbled_1_player_id": None, "fumbled_1_team": None, "fumbled_2_player_id": None, "fumbled_2_team": None,
                "forced_fumble_player_1_player_id": None, "forced_fumble_player_1_team": None,
                "forced_fumble_player_2_player_id": None, "forced_fumble_player_2_team": None,
                "fumble_recovery_1_player_id": None, "fumble_recovery_1_team": None,
                "fumble_recovery_2_player_id": None, "fumble_recovery_2_team": None, "desc": ""}


def play(game_id, play_id, week, **over):
    row = {"game_id": game_id, "play_id": play_id, "week": week, **PBP_DEFAULTS}
    row.update(over)
    return row


def pbp(rows):
    return pd.DataFrame(rows)
```

---

### Task 1: Launch provenance captured at start, not at finish

**Files:**
- Create: `src/dynasty_genius/eval/run_provenance.py`
- Modify: `scripts/experiments/dg177_basic_horizons.py` (top of `main()`, the `build_manifest(... git_head=...)` call, the `provenance = {...}` block)
- Modify: `scripts/experiments/dg177_annual_forecasts.py` (same three places)
- Test: `tests/test_dg177_run_provenance.py`

**Interfaces:**
- Produces: `launch_provenance(repo_root: Path | None = None, argv: list[str] | None = None) -> dict` with keys `git_head` (str), `git_branch` (str), `git_dirty` (bool), `captured_at_utc` (ISO str), `argv` (list[str]), `python` (str). Task 8's CLI calls it too.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dg177_run_provenance.py
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from src.dynasty_genius.eval.run_provenance import launch_provenance


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    return repo


def test_launch_provenance_reports_head_branch_and_clean_state(tmp_path):
    repo = _repo(tmp_path)
    p = launch_provenance(repo_root=repo, argv=["run.py", "--x"])
    assert p["git_head"] == _git(repo, "rev-parse", "HEAD")
    assert p["git_branch"] == "main"
    assert p["git_dirty"] is False
    assert p["argv"] == ["run.py", "--x"]
    assert re.match(r"\d{4}-\d{2}-\d{2}T", p["captured_at_utc"])


def test_launch_provenance_flags_a_dirty_tree_and_does_not_move_with_later_commits(tmp_path):
    repo = _repo(tmp_path)
    (repo / "a.txt").write_text("changed\n")
    before = launch_provenance(repo_root=repo, argv=[])
    assert before["git_dirty"] is True
    _git(repo, "commit", "-q", "-am", "two")
    assert before["git_head"] == _git(repo, "rev-parse", "HEAD~1")   # a captured value, not a live lookup


def test_forecast_runners_capture_provenance_before_any_fitting():
    """Tested without rerunning the forecasts: the runners must call launch_provenance() before
    the cohort/fits are built and must not read HEAD again at the end."""
    for path in ("scripts/experiments/dg177_basic_horizons.py", "scripts/experiments/dg177_annual_forecasts.py"):
        src = Path(path).read_text()
        body = src[src.index("def main("):]
        assert "launch_provenance(" in body, path
        assert body.index("launch_provenance(") < body.index("build_manifest("), path
        assert '_git("rev-parse", "HEAD")' not in body, path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/test_dg177_run_provenance.py`
Expected: FAIL — `ModuleNotFoundError: src.dynasty_genius.eval.run_provenance`.

- [ ] **Step 3: Write the helper**

```python
# src/dynasty_genius/eval/run_provenance.py
"""Launch-time provenance for report-only runs.

A run's manifest must name the code that RAN. HEAD read at finish time names whatever the branch
had moved to meanwhile (run 20260906T195728Z recorded 39545f8e while running older code). So the
runner captures this block as its first action and reuses it; it never asks git again.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()


def launch_provenance(repo_root: Path | None = None, argv: list[str] | None = None) -> dict:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    return {
        "git_head": _git(root, "rev-parse", "HEAD"),
        "git_branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git(root, "status", "--porcelain", "--untracked-files=no")),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "argv": list(sys.argv if argv is None else argv),
        "python": sys.version.split()[0],
    }
```

- [ ] **Step 4: Wire both runners**

In each runner, add `from src.dynasty_genius.eval.run_provenance import launch_provenance` next to the other `src.dynasty_genius.eval` imports. At the top of `main()` (first statement after `args = parser.parse_args()`), add `launch = launch_provenance()`. Replace `git_head=_git("rev-parse", "HEAD")` in the `build_manifest(...)` call with `git_head=launch["git_head"]`. Replace the provenance block's `"git_head": _git("rev-parse", "HEAD"), "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),` with `"launch": launch, "git_head": launch["git_head"], "git_branch": launch["git_branch"], "git_dirty_at_launch": launch["git_dirty"],`. In `dg177_basic_horizons.py` also add `manifest["launch"] = launch` immediately after `manifest["exports"] = {...}` (inside the finalize-before-writing block) so the embedded and final manifests agree.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/test_dg177_run_provenance.py tests/test_dg177_basic_horizons.py tests/test_dg177_annual_forecasts.py`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/eval/run_provenance.py tests/test_dg177_run_provenance.py scripts/experiments/dg177_basic_horizons.py scripts/experiments/dg177_annual_forecasts.py
git commit -m "DG-177: runners capture git HEAD and dirty state at launch, never at finish"
```

---

### Task 2: Key classification and exact research-PPR reproduction from components

**Files:**
- Create: `src/dynasty_genius/eval/league_scoring_audit.py`
- Test: `tests/contract/test_league_scoring_audit.py` (create with the header above, then these tests)

**Interfaces:**
- Produces: `WEEKLY_COMPONENT_COLUMNS: tuple[str, ...]`; `RESEARCH_PPR_PRESET: dict[str, float]`; `INDIVIDUAL_KEYS`, `KICKER_KEYS`, `TEAM_KEYS: frozenset[str]`; `ScoringAuditError(ValueError)`; `classify_scoring_keys(settings: dict) -> dict` with keys `individual`, `kicker`, `team`, `unknown` (each a sorted list); `research_ppr_from_components(weekly: pd.DataFrame) -> pd.Series` (float, index aligned with `weekly`).

- [ ] **Step 1: Write the failing tests**

```python
def test_every_saved_key_is_classified_and_unknown_keys_are_named():
    c = lsa.classify_scoring_keys(SETTINGS)
    assert set(c["individual"]) == {"fum", "fum_lost", "fum_rec_td", "pass_2pt", "pass_int", "pass_td", "pass_yd",
                                    "rec", "rec_2pt", "rec_td", "rec_yd", "rush_2pt", "rush_td", "rush_yd",
                                    "st_ff", "st_fum_rec", "st_td"}
    assert set(c["kicker"]) == {"fgm_0_19", "fgm_20_29", "fgm_30_39", "fgm_40_49", "fgm_50p", "fgmiss", "xpm", "xpmiss"}
    assert {"ff", "fum_rec", "int", "sack", "safe", "blk_kick", "def_td"} <= set(c["team"])
    assert c["unknown"] == []
    assert lsa.classify_scoring_keys({**SETTINGS, "bonus_rec_te": 0.5})["unknown"] == ["bonus_rec_te"]


def test_research_ppr_reproduces_exactly_from_the_component_columns():
    w = weekly([
        dict(player_id="P1", week=1, passing_yards=250, passing_tds=2, passing_interceptions=1, rushing_yards=12,
             sack_fumbles_lost=1, passing_2pt_conversions=1, fantasy_points_ppr=250 * 0.04 + 8 - 2 + 1.2 - 2 + 2),
        dict(player_id="P2", week=1, receptions=5, receiving_yards=63, receiving_tds=1, receiving_fumbles_lost=1,
             special_teams_tds=1, fantasy_points_ppr=5 + 6.3 + 6 - 2 + 6),
    ])
    got = lsa.research_ppr_from_components(w)
    assert np.allclose(got.to_numpy(), w["fantasy_points_ppr"].to_numpy(), atol=1e-9)


def test_research_ppr_does_not_use_fumbles_lost_total_or_recovery_fields():
    w = weekly([dict(player_id="P1", week=1, fumbles_lost_total=1, fumble_recovery_own=2, fumble_recovery_tds=1,
                     def_fumbles_forced=1, fantasy_points_ppr=0.0)])
    assert float(lsa.research_ppr_from_components(w).iloc[0]) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: FAIL — `ImportError` on `league_scoring_audit`.

- [ ] **Step 3: Write the module head**

```python
# src/dynasty_genius/eval/league_scoring_audit.py
"""DG-177 league scoring component audit (2025): pure attribution + scoring + reconciliation.

Weekly nflverse totals are the authority for component COUNTS; play-by-play supplies the event
grain (game_id, play_id, event_slot, player_id) and the special-teams / own-vs-opponent / lost
split. Whenever the two disagree the player-week is `unresolved`; nothing is patched.

Only INDIVIDUAL keys are ever credited to a player. Team-defense keys (ff, fum_rec, int, sack,
safe, blk_kick, def_*, pts_allow_*) are classified `team` and never applied to an individual;
no IDP setting is inferred from them (Sleeper scores defensive stats for individuals only under
idp_* keys, which this league does not set).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


class ScoringAuditError(ValueError):
    """A source or settings condition under which the audit refuses to proceed."""


WEEKLY_COMPONENT_COLUMNS = (
    "passing_yards", "passing_tds", "passing_interceptions", "passing_2pt_conversions",
    "rushing_yards", "rushing_tds", "rushing_2pt_conversions",
    "receptions", "receiving_yards", "receiving_tds", "receiving_2pt_conversions",
    "sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost", "special_teams_tds",
    "fumbles_total", "fumbles_lost_total", "fumble_recovery_own", "fumble_recovery_opp", "fumble_recovery_tds",
    "def_fumbles_forced", "fantasy_points_ppr",
)

# nflverse's saved research preset, written out so a test can prove the reproduction is exact.
RESEARCH_PPR_PRESET = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "fum_lost_offense": -2.0,     # sack + rushing + receiving fumbles lost ONLY
    "st_td": 6.0,
}

INDIVIDUAL_KEYS = frozenset({
    "pass_yd", "pass_td", "pass_int", "pass_2pt", "rush_yd", "rush_td", "rush_2pt",
    "rec", "rec_yd", "rec_td", "rec_2pt", "fum", "fum_lost", "fum_rec_td", "st_td", "st_ff", "st_fum_rec",
})
KICKER_KEYS = frozenset({"fgm_0_19", "fgm_20_29", "fgm_30_39", "fgm_40_49", "fgm_50p", "fgmiss", "xpm", "xpmiss"})
TEAM_KEYS = frozenset({
    "ff", "fum_rec", "int", "sack", "safe", "blk_kick", "def_td",
    "def_st_ff", "def_st_fum_rec", "def_st_td",
    "pts_allow_0", "pts_allow_1_6", "pts_allow_7_13", "pts_allow_14_20", "pts_allow_21_27", "pts_allow_28_34", "pts_allow_35p",
})


def classify_scoring_keys(settings: dict) -> dict:
    keys = set(settings)
    return {
        "individual": sorted(keys & INDIVIDUAL_KEYS),
        "kicker": sorted(keys & KICKER_KEYS),
        "team": sorted(keys & TEAM_KEYS),
        "unknown": sorted(keys - INDIVIDUAL_KEYS - KICKER_KEYS - TEAM_KEYS),
    }


def _num(frame: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(frame[col], errors="coerce").fillna(0.0).astype(float)


def research_ppr_from_components(weekly: pd.DataFrame) -> pd.Series:
    p = RESEARCH_PPR_PRESET
    w = weekly
    lost = _num(w, "sack_fumbles_lost") + _num(w, "rushing_fumbles_lost") + _num(w, "receiving_fumbles_lost")
    two = _num(w, "passing_2pt_conversions") + _num(w, "rushing_2pt_conversions") + _num(w, "receiving_2pt_conversions")
    return (p["pass_yd"] * _num(w, "passing_yards") + p["pass_td"] * _num(w, "passing_tds")
            + p["pass_int"] * _num(w, "passing_interceptions") + p["rush_yd"] * _num(w, "rushing_yards")
            + p["rush_td"] * _num(w, "rushing_tds") + p["rec"] * _num(w, "receptions")
            + p["rec_yd"] * _num(w, "receiving_yards") + p["rec_td"] * _num(w, "receiving_tds")
            + p["pass_2pt"] * two + p["fum_lost_offense"] * lost + p["st_td"] * _num(w, "special_teams_tds"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: scoring-audit key classification and exact research-PPR reproduction"
```

---

### Task 3: Fumble events at event grain from play-by-play

**Files:**
- Modify: `src/dynasty_genius/eval/league_scoring_audit.py` (append)
- Test: `tests/contract/test_league_scoring_audit.py` (append)

**Interfaces:**
- Produces: `extract_fumble_events(pbp: pd.DataFrame) -> pd.DataFrame` with columns `game_id, play_id, event_slot (int), event_type ("fumble"|"forced_fumble"|"recovery"|"recovery_td"), player_id, team, week, season_type, special_teams (bool), own_team (bool or NA), lost (bool or NA), status ("attributed"|"nullified"|"missing_id"|"ambiguous"), desc`. Grain `(game_id, play_id, event_slot, event_type, player_id)` is unique (the same player can fumble AND recover in one slot, so the event type is part of the key); rows sorted by that grain.

Rules: a play with `play_deleted == 1` or `play_type == "no_play"` yields one row per named participant with `status="nullified"` and no credit downstream. Slot `k` pairs `fumbled_k` with `fumble_recovery_k`. `lost` for a fumble event = recovery team ≠ fumbling team when a recovery exists; when the slot has no recovery at all, `lost` = the play-level `fumble_lost` flag (an end-zone out-of-bounds loss is a touchback: lost, no invented recovery player) and status stays `attributed`; a recovery with a team but a null `player_id` is `missing_id`. `own_team` for a recovery = recovery team == fumbled_k team. `recovery_td` is emitted when `touchdown == 1`, `td_player_id == recovery player`, `td_team == recovery team`, and neither `rush_touchdown` nor `pass_touchdown` is set; if a rush/pass touchdown is also set on that play the recovery row is `ambiguous` (overlapping touchdown categories). The description text is never used to infer a touchdown.

Slot capacity: the two numbered slots are not a universal ledger. When the description contains more `FUMBLES` tokens than structured fumbled slots, or a recovery slot has no paired fumbled slot, or the play-level `fumble_lost` flag disagrees with every slot's derived `lost`, every event of that play gets `status="ambiguous"` and `ambiguity_reason="slot_capacity"`; the weekly lost total remains the scoring authority downstream.

Special-teams classification: `special_teams` is `True` only when `special_teams_play == 1` AND the play type is in the special-teams family (`punt`, `kickoff`, `field_goal`, `extra_point`); when exactly one of the two says special teams, every event of the play is `ambiguous` with `ambiguity_reason="st_classifier_conflict"`. Column `ambiguity_reason` is `""` otherwise.

- [ ] **Step 1: Write the failing tests**

```python
def test_events_have_unique_grain_and_deterministic_order():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 20, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", forced_fumble_player_1_player_id="D1",
             forced_fumble_player_1_team="BBB", fumble_recovery_1_player_id="D2", fumble_recovery_1_team="BBB", fumble_lost=1),
        play("G1", 10, 1, fumbled_1_player_id="P2", fumbled_1_team="AAA", fumble_recovery_1_player_id="P2",
             fumble_recovery_1_team="AAA"),
    ]))
    assert not ev.duplicated(["game_id", "play_id", "event_slot", "player_id"]).any()
    assert ev[["game_id", "play_id"]].drop_duplicates().play_id.tolist() == [10, 20]
    assert set(ev.event_type) == {"fumble", "forced_fumble", "recovery"}


def test_multi_fumble_play_pairs_slot_two_with_its_own_recovery():
    ev = lsa.extract_fumble_events(pbp([play(
        "G1", 5, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
        fumbled_2_player_id="D1", fumbled_2_team="BBB", fumble_recovery_2_player_id="P3", fumble_recovery_2_team="AAA", fumble_lost=0)]))
    f = ev[ev.event_type == "fumble"].set_index("event_slot")
    assert bool(f.loc[1, "lost"]) is True and f.loc[1, "player_id"] == "P1"
    assert bool(f.loc[2, "lost"]) is True and f.loc[2, "player_id"] == "D1"
    r = ev[ev.event_type == "recovery"].set_index("event_slot")
    assert bool(r.loc[1, "own_team"]) is False and bool(r.loc[2, "own_team"]) is False


def test_nullified_plays_yield_nullified_events_and_no_credit():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, play_type="no_play", fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1),
        play("G1", 2, 1, play_deleted=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA"),
    ]))
    assert set(ev.status) == {"nullified"} and len(ev) == 4


def test_missing_recovery_id_is_recorded_not_dropped():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                                               fumble_recovery_1_player_id=None, fumble_recovery_1_team="BBB", fumble_lost=1)]))
    rec = ev[ev.event_type == "recovery"]
    assert len(rec) == 1 and rec.iloc[0].status == "missing_id" and pd.isna(rec.iloc[0].player_id)
    assert bool(ev[ev.event_type == "fumble"].iloc[0].lost) is True


def test_muffed_punt_is_a_special_teams_lost_fumble_and_out_of_bounds_kept_ball_is_not_lost():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1, desc="MUFFS catch"),
        play("G1", 2, 1, fumbled_1_player_id="P2", fumbled_1_team="AAA", fumble_out_of_bounds=1, fumble_lost=0),
    ]))
    f = ev[ev.event_type == "fumble"].set_index("player_id")
    assert bool(f.loc["P1", "special_teams"]) and bool(f.loc["P1", "lost"]) is True
    assert bool(f.loc["P2", "lost"]) is False and f.loc["P2", "status"] == "attributed"


def test_end_zone_out_of_bounds_loss_is_lost_with_no_invented_recovery_player():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_out_of_bounds=1,
                                               fumble_lost=1, desc="FUMBLES, ball out of bounds in End Zone, TOUCHBACK. TOUCHDOWN REVERSED")]))
    assert len(ev) == 1 and ev.iloc[0].event_type == "fumble"
    assert bool(ev.iloc[0].lost) is True and ev.iloc[0].status == "attributed"


def test_fumble_with_no_recovery_and_no_play_level_flag_is_ambiguous():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_lost=None)]))
    assert ev.iloc[0].status == "ambiguous" and pd.isna(ev.iloc[0].lost)


def test_three_fumbles_in_two_slots_is_a_capacity_ambiguity_for_every_event_of_the_play():
    ev = lsa.extract_fumble_events(pbp([play(
        "G1", 1501, 17, play_type="pass", fumble_lost=1,
        fumbled_1_player_id="P1", fumbled_1_team="AAA", fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
        fumbled_2_player_id="P1", fumbled_2_team="AAA", fumble_recovery_2_player_id="D1", fumble_recovery_2_team="BBB",
        desc="P1 FUMBLES, recovers. P1 FUMBLES, RECOVERED by BBB-D1. D1 FUMBLES, RECOVERED by AAA-P7.")]))
    assert set(ev.status) == {"ambiguous"} and set(ev.ambiguity_reason) == {"slot_capacity"}


def test_recovery_slot_without_a_paired_fumbled_slot_is_a_capacity_ambiguity():
    ev = lsa.extract_fumble_events(pbp([play("G1", 2, 1, fumbled_1_player_id="P1", fumbled_1_team="AAA",
                                               fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB",
                                               fumble_recovery_2_player_id="P3", fumble_recovery_2_team="AAA", fumble_lost=0)]))
    assert set(ev.status) == {"ambiguous"} and set(ev.ambiguity_reason) == {"slot_capacity"}


def test_special_teams_classifier_conflict_is_ambiguous_and_agreement_is_special_teams():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 2504, 10, play_type="field_goal", special_teams_play=0, fumbled_1_player_id="P1", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1, desc="blocked, MUFFS"),
        play("G1", 2600, 10, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="P2", fumbled_1_team="AAA",
             fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1),
    ]))
    a = ev[ev.play_id == 2504]
    assert set(a.status) == {"ambiguous"} and set(a.ambiguity_reason) == {"st_classifier_conflict"}
    b = ev[ev.play_id == 2600]
    assert set(b.status) == {"attributed"} and b.special_teams.all()


def test_recovery_touchdown_is_emitted_only_without_an_overlapping_rush_or_pass_touchdown():
    ev = lsa.extract_fumble_events(pbp([
        play("G1", 1, 1, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P1",
             fumble_recovery_1_team="AAA", touchdown=1, return_touchdown=1, td_player_id="P1", td_team="AAA"),
        play("G1", 2, 1, fumbled_1_player_id="P9", fumbled_1_team="AAA", fumble_recovery_1_player_id="P2",
             fumble_recovery_1_team="AAA", touchdown=1, rush_touchdown=1, td_player_id="P2", td_team="AAA"),
    ]))
    td = ev[ev.event_type == "recovery_td"]
    assert td.player_id.tolist() == ["P1"] and td.iloc[0].status == "attributed"
    p2 = ev[(ev.player_id == "P2") & (ev.event_type == "recovery")]
    assert p2.iloc[0].status == "ambiguous"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py -k events`
Expected: FAIL — `AttributeError: extract_fumble_events`.

- [ ] **Step 3: Write the extractor**

```python
EVENT_GRAIN = ["game_id", "play_id", "event_slot", "player_id"]
ST_PLAY_TYPES = frozenset({"punt", "kickoff", "field_goal", "extra_point"})
AMBIGUITY_CAPACITY = "slot_capacity"
AMBIGUITY_ST_CONFLICT = "st_classifier_conflict"
AMBIGUITY_OVERLAPPING_TD = "overlapping_touchdown"
AMBIGUITY_NO_RECOVERY_INFO = "no_recovery_and_no_lost_flag"


def _flag(row, col) -> bool:
    v = row.get(col)
    return bool(v) and not pd.isna(v)


def _isna(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA


def _play_events(p: pd.Series) -> list[dict]:
    """Events of ONE fumble play. Slot k pairs fumbled_k with fumble_recovery_k; the numbered
    slots are not a universal ledger, so capacity problems mark the whole play ambiguous."""
    nullified = _flag(p, "play_deleted") or p.get("play_type") == "no_play"
    st_flag, st_type = _flag(p, "special_teams_play"), p.get("play_type") in ST_PLAY_TYPES
    base = {"game_id": p["game_id"], "play_id": int(p["play_id"]), "week": int(p["week"]), "season_type": p.get("season_type"),
            "special_teams": bool(st_flag and st_type), "desc": p.get("desc", "") or ""}
    lost_flag = p.get("fumble_lost")
    rows: list[dict] = []
    slot_lost: list[bool | None] = []
    n_fumbled = n_rec_unpaired = 0
    for k in (1, 2):
        fum_id, fum_team = p.get(f"fumbled_{k}_player_id"), p.get(f"fumbled_{k}_team")
        rec_id, rec_team = p.get(f"fumble_recovery_{k}_player_id"), p.get(f"fumble_recovery_{k}_team")
        has_fum, has_rec = not _isna(fum_id), not (_isna(rec_id) and _isna(rec_team))
        if not has_fum and not has_rec:
            continue
        if has_rec and not has_fum:
            n_rec_unpaired += 1
        if has_rec:
            lost = None if _isna(rec_team) or _isna(fum_team) else bool(rec_team != fum_team)
        elif not _isna(lost_flag):
            lost = bool(lost_flag)                      # touchback / out of bounds: the play-level flag decides
        else:
            lost = None
        if has_fum:
            n_fumbled += 1
            slot_lost.append(lost)
            rows.append({**base, "event_slot": k, "event_type": "fumble", "player_id": fum_id, "team": fum_team,
                         "own_team": pd.NA, "lost": pd.NA if lost is None else lost,
                         "status": "attributed" if lost is not None else "ambiguous",
                         "ambiguity_reason": "" if lost is not None else AMBIGUITY_NO_RECOVERY_INFO})
        if has_rec:
            own = None if _isna(rec_team) or _isna(fum_team) else bool(rec_team == fum_team)
            is_td = _flag(p, "touchdown") and not _isna(rec_id) and p.get("td_player_id") == rec_id and p.get("td_team") == rec_team
            overlapping = is_td and (_flag(p, "rush_touchdown") or _flag(p, "pass_touchdown"))
            status, reason = "attributed", ""
            if _isna(rec_id):
                status = "missing_id"
            elif overlapping:
                status, reason = "ambiguous", AMBIGUITY_OVERLAPPING_TD
            rows.append({**base, "event_slot": k, "event_type": "recovery", "player_id": rec_id, "team": rec_team,
                         "own_team": pd.NA if own is None else own, "lost": pd.NA, "status": status, "ambiguity_reason": reason})
            if is_td and not overlapping:
                rows.append({**base, "event_slot": k, "event_type": "recovery_td", "player_id": rec_id, "team": rec_team,
                             "own_team": pd.NA if own is None else own, "lost": pd.NA, "status": "attributed", "ambiguity_reason": ""})
        ff_id, ff_team = p.get(f"forced_fumble_player_{k}_player_id"), p.get(f"forced_fumble_player_{k}_team")
        if not (_isna(ff_id) and _isna(ff_team)):
            rows.append({**base, "event_slot": k, "event_type": "forced_fumble", "player_id": ff_id, "team": ff_team,
                         "own_team": pd.NA, "lost": pd.NA, "status": "missing_id" if _isna(ff_id) else "attributed", "ambiguity_reason": ""})
    tokens = base["desc"].upper().count("FUMBLES")
    derived_lost = [x for x in slot_lost if x is not None]
    flag_disagrees = (not _isna(lost_flag)) and derived_lost and (bool(lost_flag) != any(derived_lost))
    capacity = tokens > n_fumbled or n_rec_unpaired > 0 or flag_disagrees
    conflict = st_flag != st_type
    for r in rows:
        if nullified:
            r["status"], r["ambiguity_reason"] = "nullified", ""
        elif capacity:
            r["status"], r["ambiguity_reason"] = "ambiguous", AMBIGUITY_CAPACITY
        elif conflict:
            r["status"], r["ambiguity_reason"] = "ambiguous", AMBIGUITY_ST_CONFLICT
    return rows


def extract_fumble_events(pbp: pd.DataFrame) -> pd.DataFrame:
    plays = pbp[pd.to_numeric(pbp["fumble"], errors="coerce").fillna(0) == 1]
    rows = [r for _, p in plays.iterrows() for r in _play_events(p)]
    cols = ["game_id", "play_id", "event_slot", "event_type", "player_id", "team", "week", "season_type", "special_teams",
            "own_team", "lost", "status", "ambiguity_reason", "desc"]
    out = pd.DataFrame(rows, columns=cols)
    out = out.sort_values(["game_id", "play_id", "event_slot", "event_type", "player_id"], na_position="last").reset_index(drop=True)
    dup = out.dropna(subset=["player_id"]).duplicated(EVENT_GRAIN + ["event_type"])
    if dup.any():
        raise ScoringAuditError(f"{int(dup.sum())} duplicate events at the event grain")
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: fumble events at (game, play, slot, player) grain with nullified/missing/ambiguous statuses"
```

---

### Task 4: Player-week components with cross-checks and the championship label

**Files:**
- Modify: `src/dynasty_genius/eval/league_scoring_audit.py` (append)
- Test: `tests/contract/test_league_scoring_audit.py` (append)

**Interfaces:**
- Produces: `CHAMPIONSHIP_WEEKS = range(1, 18)
UNRESOLVED_LOST = "pbp_lost_count_disagrees_with_weekly"
UNRESOLVED_TD = "pbp_recovery_td_count_disagrees_with_weekly"
UNRESOLVED_ST_TD = "recovery_td_on_special_teams_no_ground_truth"
UNRESOLVED_EVENT = "event_ambiguous_or_missing_id"
SPLIT_COLUMNS = ("pbp_fumbles_lost", "pbp_recovery_tds", "st_forced_fumbles", "st_opp_recoveries", "st_own_recoveries",
                 "non_st_forced_fumbles", "non_st_opp_recoveries", "own_recoveries", "st_recovery_tds",
                 "problem_events", "capacity_plays", "capacity_plays_needing_split")


def _count(events: pd.DataFrame, mask: pd.Series) -> pd.Series:
    sub = events[mask].dropna(subset=["player_id"])
    return sub.groupby(["player_id", "week"]).size()


def player_week_components(weekly: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    w = weekly[weekly["season_type"] == "REG"].copy()
    if w.duplicated(["player_id", "week"]).any():
        raise ScoringAuditError("duplicate (player_id, week) rows in the weekly source")
    for c in WEEKLY_COMPONENT_COLUMNS:
        w[c] = _num(w, c)
    w["extra_fumbles_lost"] = (w["fumbles_lost_total"] - w["sack_fumbles_lost"] - w["rushing_fumbles_lost"]
                              - w["receiving_fumbles_lost"]).clip(lower=0)
    idx = pd.MultiIndex.from_frame(w[["player_id", "week"]])

    def col(series: pd.Series) -> np.ndarray:
        return series.reindex(idx).fillna(0).to_numpy(dtype=int) if len(series) else np.zeros(len(w), dtype=int)

    live = events[events["status"] != "nullified"] if len(events) else events
    ok = live[live["status"] == "attributed"] if len(live) else live
    if len(ok):
        is_fum, is_rec, is_ff, is_td = (ok.event_type == t for t in ("fumble", "recovery", "forced_fumble", "recovery_td"))
        st = ok.special_teams.astype(bool)
        own = ok.own_team.fillna(False).astype(bool)
        w["pbp_fumbles_lost"] = col(_count(ok, is_fum & ok.lost.fillna(False).astype(bool)))
        w["pbp_recovery_tds"] = col(_count(ok, is_td))
        w["st_recovery_tds"] = col(_count(ok, is_td & st))
        w["st_forced_fumbles"] = col(_count(ok, is_ff & st))
        w["st_opp_recoveries"] = col(_count(ok, is_rec & st & ~own))
        w["st_own_recoveries"] = col(_count(ok, is_rec & st & own))
        w["non_st_forced_fumbles"] = col(_count(ok, is_ff & ~st))
        w["non_st_opp_recoveries"] = col(_count(ok, is_rec & ~st & ~own))
        w["own_recoveries"] = col(_count(ok, is_rec & own))
    else:
        for c in ("pbp_fumbles_lost", "pbp_recovery_tds", "st_recovery_tds", "st_forced_fumbles", "st_opp_recoveries",
                  "st_own_recoveries", "non_st_forced_fumbles", "non_st_opp_recoveries", "own_recoveries"):
            w[c] = 0
    if len(live):
        cap = live[(live.status == "ambiguous") & (live.ambiguity_reason == AMBIGUITY_CAPACITY)]
        cap_needs_split = cap[cap.special_teams.astype(bool) | cap.event_type.isin(["recovery", "recovery_td", "forced_fumble"])]
        other_bad = live[live.status.isin(["missing_id", "ambiguous"]) & (live.ambiguity_reason != AMBIGUITY_CAPACITY)]
        w["capacity_plays"] = col(cap.dropna(subset=["player_id"]).groupby(["player_id", "week"]).size()) if len(cap) else 0
        w["capacity_plays_needing_split"] = col(cap_needs_split.dropna(subset=["player_id"]).groupby(["player_id", "week"]).size()) if len(cap_needs_split) else 0
        w["problem_events"] = col(other_bad.dropna(subset=["player_id"]).groupby(["player_id", "week"]).size()) if len(other_bad) else 0
    else:
        w["capacity_plays"] = w["capacity_plays_needing_split"] = w["problem_events"] = 0
    w["championship_window"] = w["week"].isin(list(CHAMPIONSHIP_WEEKS))
    skip = w["capacity_plays"] > 0
    lost_ok = w["pbp_fumbles_lost"] == w["fumbles_lost_total"]
    w["cross_check"] = np.select([skip, lost_ok], ["skipped_capacity_ambiguity", "ok"], default="disagrees")
    reason = pd.Series("", index=w.index, dtype=object)
    reason[((w["problem_events"] > 0) | (w["capacity_plays_needing_split"] > 0)) & (reason == "")] = UNRESOLVED_EVENT
    reason[(w["cross_check"] == "disagrees") & (reason == "")] = UNRESOLVED_LOST
    reason[(~skip) & (w["pbp_recovery_tds"] != w["fumble_recovery_tds"]) & (reason == "")] = UNRESOLVED_TD
    reason[(w["st_recovery_tds"] > 0) & (reason == "")] = UNRESOLVED_ST_TD
    w["unresolved_reason"] = reason
    w["attribution_status"] = np.where(reason == "", "attributed", "unresolved")
    return w.reset_index(drop=True)
```

Note on the lost-count cross-check: a week whose fumbles all sit on plays the play-by-play does not carry (no events at all) still cross-checks, because `pbp_fumbles_lost` is 0 and `fumbles_lost_total` is compared to it; a weekly-only lost fumble is therefore `unresolved`, never silently credited. Recovery touchdowns and special-teams touchdowns are never subtracted from each other; both weekly counts are scored under their own keys, and the one case with no ground truth (a recovery touchdown on a special-teams play) is unresolved.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: player-week components cross-checked against play-by-play; championship window labelled"
```

---

### Task 5: League points crediting individual keys only

**Files:**
- Modify: `src/dynasty_genius/eval/league_scoring_audit.py` (append)
- Test: `tests/contract/test_league_scoring_audit.py` (append)

**Interfaces:**
- Produces: `league_points(components: pd.DataFrame, settings: dict) -> pd.Series` (float, aligned with `components`); weights are read from `settings` every call, never from constants; team and kicker keys are ignored for individuals; `fum_rec_td` × weekly `fumble_recovery_tds`, `fum_lost` × (`sack+rush+rec` lost + `extra_fumbles_lost`), `st_ff` × `st_forced_fumbles`, `st_fum_rec` × `st_opp_recoveries`, `st_td` × `special_teams_tds`, `fum` × `fumbles_total`.

- [ ] **Step 1: Write the failing tests**

```python
def _components(rows, events=None):
    return lsa.player_week_components(weekly(rows), events if events is not None else lsa.extract_fumble_events(pbp([])))


def test_own_recovery_is_never_a_bonus_and_fum_rec_key_is_never_applied_to_an_individual():
    c = _components([dict(player_id="P1", week=1, rushing_yards=50, fumble_recovery_own=2)])
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == 5.0
    assert float(lsa.league_points(c, {**SETTINGS, "fum_rec": 99.0}).iloc[0]) == 5.0


def test_team_defense_keys_do_not_reach_a_two_way_player():
    c = _components([dict(player_id="P1", week=1, position="CB", receptions=3, receiving_yards=42,
                          def_fumbles_forced=0)])
    c["def_interceptions"] = 1
    assert float(lsa.league_points(c, {**SETTINGS, "int": 50.0, "ff": 50.0}).iloc[0]) == 3 + 4.2


def test_recovery_touchdown_scores_fum_rec_td_without_a_recovery_bonus():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 15, fumbled_1_player_id="P9", fumbled_1_team="AAA",
                                             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA",
                                             touchdown=1, return_touchdown=1, td_player_id="P1", td_team="AAA")]))
    c = _components([dict(player_id="P1", week=15, rushing_yards=30, receptions=1, receiving_yards=8,
                          fumble_recovery_own=1, fumble_recovery_tds=1)], ev)
    assert c.iloc[0].attribution_status == "attributed"
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == pytest.approx(3 + 1 + 0.8 + 6)


def test_special_teams_keys_credit_individuals_and_weights_come_from_settings():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 13, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="R1",
                                             fumbled_1_team="BBB", forced_fumble_player_1_player_id="P1", forced_fumble_player_1_team="AAA",
                                             fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=1)]))
    c = _components([dict(player_id="P1", week=13, def_fumbles_forced=1, fumble_recovery_opp=1)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == 2.0
    assert float(lsa.league_points(c, {**SETTINGS, "st_ff": 3.0, "st_fum_rec": 0.5}).iloc[0]) == 3.5


def test_own_team_special_teams_recovery_scores_nothing():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1358, 5, play_type="kickoff", special_teams_play=1, fumbled_1_player_id="P5",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="P1", fumble_recovery_1_team="AAA", fumble_lost=0)]))
    c = _components([dict(player_id="P1", week=5, receptions=2, receiving_yards=27, fumble_recovery_own=1, fantasy_points_ppr=4.7)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == pytest.approx(4.7)


def test_muffed_return_lost_fumble_costs_fum_lost_and_negative_totals_are_preserved():
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="P1",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1)]))
    c = _components([dict(player_id="P1", week=1, fumbles_lost_total=1)], ev)
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == -2.0
    assert float(lsa.research_ppr_from_components(c).iloc[0]) == 0.0


def test_league_points_ignore_fumble_lost_count_disagreements_only_through_status_not_by_guessing():
    c = _components([dict(player_id="P1", week=3, fumbles_lost_total=2, rushing_fumbles_lost=1)])
    assert c.iloc[0].attribution_status == "unresolved"
    assert float(lsa.league_points(c, SETTINGS).iloc[0]) == -4.0   # the weekly count is still applied; the row stays unresolved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py -k "league_points or bonus or two_way or recovery_touchdown or special_teams_keys or muffed"`
Expected: FAIL — `AttributeError: league_points`.

- [ ] **Step 3: Write the scorer**

```python
def league_points(components: pd.DataFrame, settings: dict) -> pd.Series:
    """Individual keys only. A team or kicker key present in `settings` is ignored for a player;
    an IDP setting is never inferred from a DST key."""
    s = {k: float(v) for k, v in settings.items() if k in INDIVIDUAL_KEYS}
    c = components
    g = lambda k: s.get(k, 0.0)  # noqa: E731
    lost = _num(c, "sack_fumbles_lost") + _num(c, "rushing_fumbles_lost") + _num(c, "receiving_fumbles_lost") + _num(c, "extra_fumbles_lost")
    return (g("pass_yd") * _num(c, "passing_yards") + g("pass_td") * _num(c, "passing_tds")
            + g("pass_int") * _num(c, "passing_interceptions") + g("pass_2pt") * _num(c, "passing_2pt_conversions")
            + g("rush_yd") * _num(c, "rushing_yards") + g("rush_td") * _num(c, "rushing_tds")
            + g("rush_2pt") * _num(c, "rushing_2pt_conversions")
            + g("rec") * _num(c, "receptions") + g("rec_yd") * _num(c, "receiving_yards") + g("rec_td") * _num(c, "receiving_tds")
            + g("rec_2pt") * _num(c, "receiving_2pt_conversions")
            + g("fum") * _num(c, "fumbles_total") + g("fum_lost") * lost
            + g("fum_rec_td") * _num(c, "fumble_recovery_tds") + g("st_td") * _num(c, "special_teams_tds")
            + g("st_ff") * _num(c, "st_forced_fumbles") + g("st_fum_rec") * _num(c, "st_opp_recoveries"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: league points credit individual keys only, weights read from the saved settings"
```

---

### Task 6: Sleeper ground truth, identity mapping and reconciliation

**Files:**
- Modify: `src/dynasty_genius/eval/league_scoring_audit.py` (append)
- Test: `tests/contract/test_league_scoring_audit.py` (append)

**Interfaces:**
- Produces:
  - `load_sleeper_week_points(season_dir: Path) -> pd.DataFrame` columns `week, sleeper_id (str), sleeper_points (float), roster_id, status ("ok"|"conflicting_duplicate")`; reads `matchups_week_NN.json` files whose top level is `{"payload": [...]}`; identical duplicates collapse to one row; conflicting duplicates keep the first value with status `conflicting_duplicate`.
  - `load_sleeper_settings(season_dir: Path) -> dict` — `league.json` → `payload.scoring_settings`.
  - `settings_sha256(settings: dict) -> str` — sha256 of `json.dumps(settings, sort_keys=True, separators=(",", ":"))`.
  - `assert_settings_match(saved: dict, season: dict) -> None` — raises `ScoringAuditError` naming differing keys.
  - `map_sleeper_ids(sleeper_ids: pd.Series, idmap: pd.DataFrame) -> pd.DataFrame` columns `sleeper_id, gsis_id, identity_status ("resolved"|"unmapped"|"ambiguous")`; `idmap` has `sleeper_id`, `gsis_id`; a sleeper id with two distinct gsis ids is `ambiguous`.
  - `reconcile(components: pd.DataFrame, sleeper: pd.DataFrame, identity: pd.DataFrame, settings: dict) -> pd.DataFrame` — one row per Sleeper player-week: `week, sleeper_id, gsis_id, identity_status, sleeper_points, research_ppr, league_points, diff_vs_research, diff_vs_league, attribution_status, championship_window, status` where `status` is one of `exact` (league == sleeper and research == sleeper), `attributed_difference` (league == sleeper, research != sleeper), `unresolved` (anything else, including unmapped ids with nonzero points, no weekly row with nonzero points, `attribution_status == "unresolved"`), `absent_zero` (no weekly row and 0 points). Tolerance 0.005.

- [ ] **Step 1: Write the failing tests**

```python
def _season_dir(tmp_path, weeks, settings=SETTINGS):
    d = tmp_path / "season_2025_1"
    d.mkdir()
    (d / "league.json").write_text(json.dumps({"payload": {"season": "2025", "scoring_settings": settings}}))
    for wk, matchups in weeks.items():
        (d / f"matchups_week_{wk:02d}.json").write_text(json.dumps({"payload": matchups}))
    return d


def test_sleeper_points_load_with_identical_duplicates_collapsed_and_conflicts_flagged(tmp_path):
    d = _season_dir(tmp_path, {1: [{"roster_id": 1, "players_points": {"11": 4.5, "12": 0.0}},
                                   {"roster_id": 2, "players_points": {"11": 4.5, "13": 2.0}},
                                   {"roster_id": 3, "players_points": {"13": 7.0}}]})
    s = lsa.load_sleeper_week_points(d)
    assert len(s) == 3
    assert s.set_index("sleeper_id").loc["11", "status"] == "ok" and int(s.set_index("sleeper_id").loc["11", "duplicates_collapsed"]) == 1
    assert s.set_index("sleeper_id").loc["13", "status"] == "conflicting_duplicate"


def test_settings_mismatch_is_refused_by_key(tmp_path):
    d = _season_dir(tmp_path, {}, settings={**SETTINGS, "rec": 0.5})
    with pytest.raises(lsa.ScoringAuditError, match="rec"):
        lsa.assert_settings_match(SETTINGS, lsa.load_sleeper_settings(d))
    assert lsa.settings_sha256(SETTINGS) == lsa.settings_sha256(dict(reversed(list(SETTINGS.items()))))


def test_identity_map_marks_unmapped_and_ambiguous_ids():
    idmap = pd.DataFrame({"sleeper_id": ["11", "12", "12"], "gsis_id": ["00-1", "00-2", "00-3"]})
    m = lsa.map_sleeper_ids(pd.Series(["11", "12", "99"]), idmap).set_index("sleeper_id")
    assert m.loc["11", "identity_status"] == "resolved" and m.loc["11", "gsis_id"] == "00-1"
    assert m.loc["12", "identity_status"] == "ambiguous" and pd.isna(m.loc["12", "gsis_id"])
    assert m.loc["99", "identity_status"] == "unmapped"


def test_reconciliation_statuses_cover_exact_attributed_unresolved_and_absent_zero(tmp_path):
    ev = lsa.extract_fumble_events(pbp([play("G1", 1, 1, play_type="punt", special_teams_play=1, fumbled_1_player_id="00-2",
                                             fumbled_1_team="AAA", fumble_recovery_1_player_id="D1", fumble_recovery_1_team="BBB", fumble_lost=1)]))
    comps = _components([dict(player_id="00-1", week=1, receptions=2, receiving_yards=20, fantasy_points_ppr=4.0),
                         dict(player_id="00-2", week=1, receptions=3, receiving_yards=12, fumbles_lost_total=1, fantasy_points_ppr=4.2),
                         dict(player_id="00-3", week=1, rushing_yards=10, fantasy_points_ppr=1.0)], ev)
    sleeper = pd.DataFrame({"week": [1, 1, 1, 1, 1], "sleeper_id": ["11", "12", "13", "14", "15"],
                            "sleeper_points": [4.0, 2.2, 1.5, 0.0, 3.0], "roster_id": 1, "status": "ok"})
    identity = pd.DataFrame({"sleeper_id": ["11", "12", "13", "14", "15"], "gsis_id": ["00-1", "00-2", "00-3", None, None],
                             "identity_status": ["resolved", "resolved", "resolved", "unmapped", "unmapped"]})
    r = lsa.reconcile(comps, sleeper, identity, SETTINGS).set_index("sleeper_id")
    assert r.loc["11", "status"] == "exact"
    assert r.loc["12", "status"] == "attributed_difference" and r.loc["12", "diff_vs_research"] == pytest.approx(-2.0)
    assert r.loc["13", "status"] == "unresolved"                 # provider discrepancy: 1.5 vs 1.0, no component explains it
    assert r.loc["14", "status"] == "absent_zero"
    assert r.loc["15", "status"] == "unresolved"                 # nonzero points, no identity


def test_reconciliation_never_credits_an_unresolved_attribution_as_exact():
    comps = _components([dict(player_id="00-1", week=3, fumbles_lost_total=2, rushing_fumbles_lost=1, fantasy_points_ppr=-2.0)])
    sleeper = pd.DataFrame({"week": [3], "sleeper_id": ["11"], "sleeper_points": [-4.0], "roster_id": 1, "status": "ok"})
    identity = pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"], "identity_status": ["resolved"]})
    assert lsa.reconcile(comps, sleeper, identity, SETTINGS).iloc[0].status == "unresolved"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py -k "sleeper or settings or identity or reconcil"`
Expected: FAIL — `AttributeError: load_sleeper_week_points`.

- [ ] **Step 3: Write the loaders and reconciliation**

```python
TOL = 0.005


def load_sleeper_week_points(season_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(season_dir).glob("matchups_week_*.json")):
        week = int(f.stem.rsplit("_", 1)[1])
        for m in json.loads(f.read_bytes())["payload"]:
            for pid, pts in (m.get("players_points") or {}).items():
                rows.append({"week": week, "sleeper_id": str(pid), "sleeper_points": float(pts), "roster_id": m.get("roster_id")})
    df = pd.DataFrame(rows, columns=["week", "sleeper_id", "sleeper_points", "roster_id"])
    if not len(df):
        df["status"] = pd.Series(dtype=object)
        return df
    n_distinct = df.groupby(["week", "sleeper_id"])["sleeper_points"].transform("nunique")
    n_obs = df.groupby(["week", "sleeper_id"])["sleeper_points"].transform("size")
    df["status"] = np.where(n_distinct > 1, "conflicting_duplicate", "ok")
    df["duplicates_collapsed"] = (n_obs - 1).astype(int)     # equal observations collapsed EXPLICITLY, never double counted
    return df.drop_duplicates(["week", "sleeper_id"], keep="first").reset_index(drop=True)


def load_sleeper_settings(season_dir: Path) -> dict:
    return json.loads((Path(season_dir) / "league.json").read_bytes())["payload"]["scoring_settings"]


def settings_sha256(settings: dict) -> str:
    return hashlib.sha256(json.dumps(settings, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def assert_settings_match(saved: dict, season: dict) -> None:
    diff = sorted(k for k in set(saved) | set(season) if saved.get(k) != season.get(k))
    if diff:
        raise ScoringAuditError(f"season scoring settings differ from the saved snapshot on {diff}")


def map_sleeper_ids(sleeper_ids: pd.Series, idmap: pd.DataFrame) -> pd.DataFrame:
    m = idmap.dropna(subset=["sleeper_id", "gsis_id"]).astype({"sleeper_id": str, "gsis_id": str})
    m = m.drop_duplicates(["sleeper_id", "gsis_id"])
    counts = m.groupby("sleeper_id")["gsis_id"].nunique()
    one = m[m.sleeper_id.map(counts) == 1].set_index("sleeper_id")["gsis_id"]
    ids = pd.Series(sleeper_ids.astype(str).unique(), name="sleeper_id")
    out = pd.DataFrame({"sleeper_id": ids})
    out["gsis_id"] = out.sleeper_id.map(one)
    out["identity_status"] = np.select([out.sleeper_id.isin(counts[counts > 1].index), out.gsis_id.notna()],
                                       ["ambiguous", "resolved"], default="unmapped")
    return out


def reconcile(components: pd.DataFrame, sleeper: pd.DataFrame, identity: pd.DataFrame, settings: dict) -> pd.DataFrame:
    comps = components.copy()
    comps["research_ppr"] = research_ppr_from_components(comps)
    comps["league_points"] = league_points(comps, settings)
    keep = ["player_id", "week", "research_ppr", "league_points", "attribution_status", "unresolved_reason", "championship_window"]
    r = sleeper.merge(identity, on="sleeper_id", how="left")
    r = r.merge(comps[keep], left_on=["gsis_id", "week"], right_on=["player_id", "week"], how="left")
    r["championship_window"] = r["week"].isin(list(CHAMPIONSHIP_WEEKS))
    r["diff_vs_research"] = r.sleeper_points - r.research_ppr
    r["diff_vs_league"] = r.sleeper_points - r.league_points
    has_row = r.player_id.notna()
    league_ok = has_row & (r.diff_vs_league.abs() <= TOL) & (r.attribution_status == "attributed") & (r.status == "ok")
    research_ok = has_row & (r.diff_vs_research.abs() <= TOL)
    absent_zero = ~has_row & (r.sleeper_points.abs() <= TOL)
    r["status"] = np.select([league_ok & research_ok, league_ok & ~research_ok, absent_zero],
                            ["exact", "attributed_difference", "absent_zero"], default="unresolved")
    cols = ["week", "sleeper_id", "gsis_id", "identity_status", "roster_id", "sleeper_points", "research_ppr", "league_points",
            "diff_vs_research", "diff_vs_league", "attribution_status", "unresolved_reason", "championship_window", "status"]
    return r[cols].sort_values(["week", "sleeper_id"]).reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: Sleeper ground truth, fail-closed identity map, settings check and reconciliation statuses"
```

---

### Task 7: Quarantine re-audit, coverage counts, exact qualification and manifest

**Files:**
- Modify: `src/dynasty_genius/eval/league_scoring_audit.py` (append)
- Test: `tests/contract/test_league_scoring_audit.py` (append)

**Interfaces:**
- Produces:
  - `audit_quarantine(quarantine: pd.DataFrame, settings: dict) -> pd.DataFrame` — the quarantine rows with `league_points_if_scored` (via `league_points` on a components frame built with zero play-by-play splits), `nonzero_under_league_keys` (bool) and every original column kept.
  - `coverage_counts(components, reconciliation, sleeper, identity) -> dict` with integer keys `weekly_player_weeks_reg`, `weekly_player_weeks_championship`, `sleeper_player_weeks`, `sleeper_player_weeks_championship`, `sleeper_players`, `identity_resolved`, `identity_unmapped`, `identity_ambiguous`, `status_exact`, `status_attributed_difference`, `status_absent_zero`, `status_unresolved`, `components_unresolved_by_reason` (dict), `sleeper_duplicate_observations_collapsed` (int, equal duplicates), `sleeper_conflicting_duplicates` (int), and `population_note` (str, verbatim: `"rostered player-weeks only; not full-universe proof"`).
  - `exact_qualification(classification: dict, counts: dict, kicker_rows_present: bool) -> dict` `{ "league_scoring_exact": False, "reasons": [...] }` — always `False` in this increment; reasons always include the population note, and add `"unknown_scoring_keys: [...]"`, `"unresolved_player_weeks: N"`, `"kicker_keys_unsupported_for_present_kickers"` when applicable.
  - `build_audit_manifest(*, sources: dict, settings: dict, classification: dict, counts: dict, qualification: dict, launch: dict, outputs: dict) -> dict` with `schema_version = "dg177_league_scoring_audit_v1"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_quarantine_rows_are_rescored_under_league_keys_with_original_columns_kept():
    q = weekly([dict(player_id=None, week=14, team="AAA", fumbles_lost_total=1, fantasy_points_ppr=-2.0),
                dict(player_id=None, week=1, team="BBB", special_teams_tds=1, fantasy_points_ppr=6.0),
                dict(player_id=None, week=2, team="CCC", fantasy_points_ppr=0.0)])
    q["quarantine_reason"] = ["unattributed", "unattributed", "placeholder"]
    a = lsa.audit_quarantine(q, SETTINGS)
    assert a.nonzero_under_league_keys.tolist() == [True, True, False]
    assert a.league_points_if_scored.tolist() == [-2.0, 6.0, 0.0]
    assert a.quarantine_reason.tolist() == ["unattributed", "unattributed", "placeholder"]


def test_exact_qualification_is_never_granted_in_this_increment_and_names_its_reasons():
    q = lsa.exact_qualification({"unknown": ["bonus_x"], "kicker": ["xpm"]}, {"status_unresolved": 3}, kicker_rows_present=True)
    assert q["league_scoring_exact"] is False
    assert "rostered player-weeks only; not full-universe proof" in q["reasons"]
    assert any(r.startswith("unknown_scoring_keys") for r in q["reasons"])
    assert "unresolved_player_weeks: 3" in q["reasons"]
    assert "kicker_keys_unsupported_for_present_kickers" in q["reasons"]
    assert lsa.exact_qualification({"unknown": [], "kicker": []}, {"status_unresolved": 0}, kicker_rows_present=False)["league_scoring_exact"] is False


def test_coverage_counts_separate_the_championship_window_and_every_status():
    comps = _components([dict(player_id="00-1", week=17), dict(player_id="00-1", week=18)])
    sleeper = pd.DataFrame({"week": [17, 18], "sleeper_id": ["11", "11"], "sleeper_points": [0.0, 0.0], "roster_id": 1, "status": "ok"})
    identity = pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"], "identity_status": ["resolved"]})
    rec = lsa.reconcile(comps, sleeper, identity, SETTINGS)
    c = lsa.coverage_counts(comps, rec, sleeper, identity)
    assert c["weekly_player_weeks_reg"] == 2 and c["weekly_player_weeks_championship"] == 1
    assert c["sleeper_player_weeks"] == 2 and c["sleeper_player_weeks_championship"] == 1
    assert c["status_exact"] == 2 and c["status_unresolved"] == 0
    assert c["population_note"] == "rostered player-weeks only; not full-universe proof"


def test_manifest_carries_schema_sources_settings_sha_and_qualification():
    m = lsa.build_audit_manifest(sources={"weekly": {"path": "w", "sha256": "a" * 64, "bytes": 1}}, settings=SETTINGS,
                                 classification=lsa.classify_scoring_keys(SETTINGS), counts={"status_exact": 1},
                                 qualification={"league_scoring_exact": False, "reasons": ["x"]},
                                 launch={"git_head": "h"}, outputs={"components.csv": "b" * 64})
    assert m["schema_version"] == "dg177_league_scoring_audit_v1"
    assert m["settings_sha256"] == lsa.settings_sha256(SETTINGS)
    assert m["league_scoring_exact"] is False and m["championship_window"] == {"weeks": [1, 17], "week_18_included": False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py -k "quarantine or qualification or coverage or manifest"`
Expected: FAIL — `AttributeError: audit_quarantine`.

- [ ] **Step 3: Write the functions**

```python
POPULATION_NOTE = "rostered player-weeks only; not full-universe proof"
SCHEMA_VERSION = "dg177_league_scoring_audit_v1"


def audit_quarantine(quarantine: pd.DataFrame, settings: dict) -> pd.DataFrame:
    q = quarantine.copy()
    for c in WEEKLY_COMPONENT_COLUMNS:
        q[c] = _num(q, c) if c in q else 0.0
    q["extra_fumbles_lost"] = (q["fumbles_lost_total"] - q["sack_fumbles_lost"] - q["rushing_fumbles_lost"] - q["receiving_fumbles_lost"]).clip(lower=0)
    for c in SPLIT_COLUMNS:
        q[c] = 0            # no play-by-play split is attempted for quarantined (unidentified) rows
    q["league_points_if_scored"] = league_points(q, settings)
    q["nonzero_under_league_keys"] = q["league_points_if_scored"].abs() > TOL
    return q


def coverage_counts(components: pd.DataFrame, reconciliation: pd.DataFrame, sleeper: pd.DataFrame, identity: pd.DataFrame) -> dict:
    st = reconciliation["status"].value_counts()
    return {
        "weekly_player_weeks_reg": int(len(components)),
        "weekly_player_weeks_championship": int(components["championship_window"].sum()),
        "sleeper_player_weeks": int(len(sleeper)),
        "sleeper_player_weeks_championship": int(sleeper["week"].isin(list(CHAMPIONSHIP_WEEKS)).sum()),
        "sleeper_players": int(sleeper["sleeper_id"].nunique()),
        "identity_resolved": int((identity["identity_status"] == "resolved").sum()),
        "identity_unmapped": int((identity["identity_status"] == "unmapped").sum()),
        "identity_ambiguous": int((identity["identity_status"] == "ambiguous").sum()),
        "status_exact": int(st.get("exact", 0)), "status_attributed_difference": int(st.get("attributed_difference", 0)),
        "status_absent_zero": int(st.get("absent_zero", 0)), "status_unresolved": int(st.get("unresolved", 0)),
        "components_unresolved_by_reason": {k: int(v) for k, v in components.loc[components["attribution_status"] == "unresolved", "unresolved_reason"].value_counts().items()},
        "sleeper_duplicate_observations_collapsed": int(sleeper["duplicates_collapsed"].sum()) if "duplicates_collapsed" in sleeper else 0,
        "sleeper_conflicting_duplicates": int((sleeper["status"] == "conflicting_duplicate").sum()),
        "population_note": POPULATION_NOTE,
    }


def exact_qualification(classification: dict, counts: dict, kicker_rows_present: bool) -> dict:
    reasons = [POPULATION_NOTE]
    if classification.get("unknown"):
        reasons.append(f"unknown_scoring_keys: {classification['unknown']}")
    reasons.append(f"unresolved_player_weeks: {int(counts.get('status_unresolved', 0))}")
    if kicker_rows_present and classification.get("kicker"):
        reasons.append("kicker_keys_unsupported_for_present_kickers")
    return {"league_scoring_exact": False, "reasons": reasons}


def build_audit_manifest(*, sources: dict, settings: dict, classification: dict, counts: dict, qualification: dict,
                         launch: dict, outputs: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "producer": "DG-177 league scoring component audit (report-only)",
        "sources": sources, "settings_sha256": settings_sha256(settings), "scoring_settings": settings,
        "key_classification": classification, "research_preset": RESEARCH_PPR_PRESET,
        "individual_keys_credited": sorted(INDIVIDUAL_KEYS & set(settings)),
        "team_keys_never_applied_to_individuals": sorted(TEAM_KEYS & set(settings)),
        "championship_window": {"weeks": [CHAMPIONSHIP_WEEKS.start, CHAMPIONSHIP_WEEKS.stop - 1], "week_18_included": False},
        "coverage": counts, "league_scoring_exact": qualification["league_scoring_exact"],
        "qualification_reasons": qualification["reasons"], "launch": launch, "outputs": outputs,
        "meaning": "Counts come from the weekly source; play-by-play supplies the special-teams / own-vs-opponent / lost split. "
                   "A disagreement is unresolved, never patched. The Sleeper comparison covers rostered players only.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/eval/league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: quarantine re-audit, coverage counts, exact qualification always refused with reasons, manifest"
```

---

### Task 8: CLI, immutable run on the actual 2025 files, report

**Files:**
- Create: `scripts/dg177/run_league_scoring_audit.py`
- Test: `tests/contract/test_league_scoring_audit.py` (append an end-to-end test on tmp fixtures)

**Interfaces:**
- Consumes every function above plus `launch_provenance()`.
- Produces `runs/<UTC ts>/dg177_league_scoring_audit/` with `manifest.json`, `components.csv`, `event_ledger.csv`, `reconciliation.csv`, `unresolved.csv`, `quarantine_reaudit.csv`, `report.md`. The run directory must not pre-exist. `manifest.outputs` holds sha256 of every written file. The CLI exits 1 on `ScoringAuditError`.

- [ ] **Step 1: Write the failing end-to-end test**

```python
def test_cli_writes_an_immutable_run_with_hashed_sources_and_refuses_to_overwrite(tmp_path):
    import subprocess, sys
    weekly_p, pbp_p, quar_p = tmp_path / "w.parquet", tmp_path / "p.parquet", tmp_path / "q.parquet"
    weekly([dict(player_id="00-1", week=1, receptions=2, receiving_yards=20, fantasy_points_ppr=4.0)]).to_parquet(weekly_p)
    pbp([play("G1", 1, 1, fumble=0)]).to_parquet(pbp_p)
    q = weekly([dict(player_id=None, week=1, fantasy_points_ppr=0.0)]); q["quarantine_reason"] = "placeholder"; q.to_parquet(quar_p)
    season = _season_dir(tmp_path, {1: [{"roster_id": 1, "players_points": {"11": 4.0}}]})
    snap = tmp_path / "snapshot.json"; snap.write_text(json.dumps({"league": {"scoring_settings": SETTINGS}}))
    idmap = tmp_path / "ids.parquet"; pd.DataFrame({"sleeper_id": ["11"], "gsis_id": ["00-1"]}).to_parquet(idmap)
    out_root = tmp_path / "runs"
    cmd = [sys.executable, "scripts/dg177/run_league_scoring_audit.py", "--weekly", str(weekly_p), "--pbp", str(pbp_p),
           "--quarantine", str(quar_p), "--sleeper-season-dir", str(season), "--league-snapshot", str(snap),
           "--idmap", str(idmap), "--season", "2025", "--out-root", str(out_root), "--run-id", "20260101T000000Z"]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0
    run = out_root / "20260101T000000Z" / "dg177_league_scoring_audit"
    m = json.loads((run / "manifest.json").read_text())
    assert set(m["outputs"]) == {"components.csv", "event_ledger.csv", "reconciliation.csv", "unresolved.csv", "quarantine_reaudit.csv", "report.md"}
    assert m["sources"]["weekly"]["sha256"] and m["coverage"]["status_exact"] == 1 and m["league_scoring_exact"] is False
    assert m["launch"]["git_head"]
    second = subprocess.run(cmd, capture_output=True, text=True)
    assert second.returncode == 1 and "exists" in (second.stderr + second.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py -k cli`
Expected: FAIL — script not found (returncode 2).

- [ ] **Step 3: Write the CLI**

```python
#!/usr/bin/env python
"""DG-177 league scoring component audit — actual-data runner.

    .venv/bin/python scripts/dg177/run_league_scoring_audit.py \
      --weekly     /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/identified_weekly.parquet \
      --quarantine /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/quarantine.parquet \
      --pbp        /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/pbp/pbp_2025.parquet \
      --sleeper-season-dir /Users/davidleess/dynasty-genius-product/app/data/research/league_behavior/raw/2026-07-19/season_2025_1183088915091423232 \
      --league-snapshot /Users/davidleess/dynasty-genius-product/app/data/league_runtime/runs/league-20260906T130052Z/snapshot.json \
      --idmap      /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/ff_playerids/ff_playerids_full.parquet \
      --season 2025 --out-root runs

Writes a NEW runs/<ts>/dg177_league_scoring_audit/ (refuses an existing one). Report-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval import league_scoring_audit as lsa  # noqa: E402
from src.dynasty_genius.eval.run_provenance import launch_provenance  # noqa: E402

OUTPUTS = ("components.csv", "event_ledger.csv", "reconciliation.csv", "unresolved.csv", "quarantine_reaudit.csv", "report.md")


def _sha(path: Path) -> dict:
    b = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def _read(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def _render(m: dict, rec: pd.DataFrame, comps: pd.DataFrame) -> str:
    c = m["coverage"]
    lines = [f"# DG-177 league scoring component audit — season {m['season']}\n",
             f"Settings sha `{m['settings_sha256'][:12]}…` · individual keys credited {m['individual_keys_credited']} · "
             f"team keys never applied {m['team_keys_never_applied_to_individuals']} · launch git `{m['launch']['git_head'][:8]}` "
             f"dirty={m['launch']['git_dirty']}\n",
             "## Coverage (rostered Sleeper player-weeks vs weekly source)\n",
             f"- weekly REG player-weeks {c['weekly_player_weeks_reg']} (championship weeks 1–17: {c['weekly_player_weeks_championship']})",
             f"- Sleeper player-weeks {c['sleeper_player_weeks']} (championship: {c['sleeper_player_weeks_championship']}), players {c['sleeper_players']}; "
             f"identity resolved {c['identity_resolved']} / unmapped {c['identity_unmapped']} / ambiguous {c['identity_ambiguous']}",
             f"- exact {c['status_exact']} · attributed difference {c['status_attributed_difference']} · absent-zero {c['status_absent_zero']} · "
             f"unresolved {c['status_unresolved']}",
             f"- component weeks unresolved by reason: {c['components_unresolved_by_reason']}",
             f"- {c['population_note']}\n",
             f"## Exact-league qualification: {m['league_scoring_exact']}\n", *[f"- {r}" for r in m['qualification_reasons']], "",
             "## Differences vs research PPR (attributed) and unresolved rows\n"]
    show = rec[rec.status.isin(["attributed_difference", "unresolved"])]
    lines.append(show[["week", "sleeper_id", "gsis_id", "sleeper_points", "research_ppr", "league_points", "diff_vs_research",
                       "diff_vs_league", "unresolved_reason", "status"]].to_string(index=False) if len(show) else "none")
    lines.append("\n## Championship-window population deltas (all weekly rows, weeks 1–17; league − research)\n")
    w = comps[comps.championship_window]
    delta = (lsa.league_points(w, m["scoring_settings"]) - lsa.research_ppr_from_components(w))
    lines.append(f"- player-weeks with a nonzero delta: {int((delta.abs() > lsa.TOL).sum())} of {len(w)}; sum {round(float(delta.sum()), 2)}; "
                 f"min {round(float(delta.min()), 2)} max {round(float(delta.max()), 2)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("--weekly", "--quarantine", "--pbp", "--sleeper-season-dir", "--league-snapshot", "--idmap"):
        ap.add_argument(a, required=True, type=Path)
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--out-root", type=Path, default=ROOT / "runs")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    launch = launch_provenance(repo_root=ROOT)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_root / run_id / "dg177_league_scoring_audit"
    if out_dir.exists():
        print(f"refusing: {out_dir} exists (runs are immutable)", file=sys.stderr)
        return 1
    try:
        sources = {"weekly": _sha(args.weekly), "quarantine": _sha(args.quarantine), "pbp": _sha(args.pbp),
                   "league_snapshot": _sha(args.league_snapshot), "idmap": _sha(args.idmap),
                   "sleeper_matchups": {str(p.name): _sha(p) for p in sorted(args.sleeper_season_dir.glob("matchups_week_*.json"))},
                   "sleeper_league": _sha(args.sleeper_season_dir / "league.json")}
        settings = json.loads(args.league_snapshot.read_bytes())["league"]["scoring_settings"]
        lsa.assert_settings_match(settings, lsa.load_sleeper_settings(args.sleeper_season_dir))
        classification = lsa.classify_scoring_keys(settings)
        weekly = _read(args.weekly)
        weekly = weekly[(pd.to_numeric(weekly["season"], errors="coerce") == args.season)]
        pbp = _read(args.pbp)
        if "season" in pbp:
            pbp = pbp[pd.to_numeric(pbp["season"], errors="coerce") == args.season]
        pbp = pbp[pbp["season_type"] == "REG"] if "season_type" in pbp else pbp
        events = lsa.extract_fumble_events(pbp)
        comps = lsa.player_week_components(weekly, events)
        sleeper = lsa.load_sleeper_week_points(args.sleeper_season_dir)
        identity = lsa.map_sleeper_ids(sleeper["sleeper_id"], _read(args.idmap)[["sleeper_id", "gsis_id"]])
        rec = lsa.reconcile(comps, sleeper, identity, settings)
        quar = _read(args.quarantine)
        quar = quar[pd.to_numeric(quar["season"], errors="coerce") == args.season] if "season" in quar else quar
        quar_audit = lsa.audit_quarantine(quar, settings)
        counts = lsa.coverage_counts(comps, rec, sleeper, identity)
        kickers = bool(weekly["position"].isin(["K", "P"]).any()) if "position" in weekly else False
        qual = lsa.exact_qualification(classification, counts, kicker_rows_present=kickers)
    except lsa.ScoringAuditError as err:
        print(f"refusing: {err}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True)
    comps.to_csv(out_dir / "components.csv", index=False)
    events.to_csv(out_dir / "event_ledger.csv", index=False)
    rec.to_csv(out_dir / "reconciliation.csv", index=False)
    pd.concat([rec[rec.status == "unresolved"].assign(source="reconciliation"),
               comps[comps.attribution_status == "unresolved"].assign(source="components")], ignore_index=True).to_csv(out_dir / "unresolved.csv", index=False)
    quar_audit.to_csv(out_dir / "quarantine_reaudit.csv", index=False)
    manifest = lsa.build_audit_manifest(sources=sources, settings=settings, classification=classification, counts=counts,
                                        qualification=qual, launch=launch, outputs={})
    manifest["season"] = args.season
    (out_dir / "report.md").write_text(_render(manifest, rec, comps))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in OUTPUTS}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(f"wrote {out_dir}")
    print((out_dir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes, then lint**

Run: `.venv/bin/python -m pytest -q tests/contract/test_league_scoring_audit.py tests/test_dg177_run_provenance.py && /Users/davidleess/.cache/pre-commit/repocesie9_t/py_env-python3.14/bin/ruff check src/dynasty_genius/eval/league_scoring_audit.py src/dynasty_genius/eval/run_provenance.py scripts/dg177/run_league_scoring_audit.py tests/contract/test_league_scoring_audit.py tests/test_dg177_run_provenance.py`
Expected: all PASS, "All checks passed!".

- [ ] **Step 5: Commit the tool**

```bash
git add scripts/dg177/run_league_scoring_audit.py tests/contract/test_league_scoring_audit.py
git commit -m "DG-177: league scoring audit CLI writes an immutable hashed run"
```

- [ ] **Step 6: Run on the actual 2025 files** (the exact command in the CLI docstring). Expected from preflight, to be re-derived from the run itself, never quoted from memory: about 3,225 championship-window rostered player-weeks, most `exact`, single-digit `attributed_difference`, single-digit `unresolved`; 19 `st_own_recovery_no_ground_truth` component weeks; qualification `false`.

- [ ] **Step 7: Verify the run** — `manifest.outputs` hashes match `shasum -a 256` of the files; every reconciliation row with status `unresolved` appears in `unresolved.csv`; no player names anywhere in `src/` or `tests/`.

- [ ] **Step 8: Commit the run (all files; they are small) and push**

```bash
git add runs/<ts>/dg177_league_scoring_audit docs/superpowers/plans/2026-09-06-league-scoring-component-audit.md
git commit -m "DG-177: league scoring audit run <ts> on the actual 2025 sources"
git push origin ticket/DG-177
```

- [ ] **Step 9: Report** to root: exact command, every source sha, output shas, coverage counts, every attributed difference and unresolved row (ids, not names), the population note, and the qualification reasons. Append the same to the DG-177 ticket.

---

## Self-review

**Spec coverage.** Pure module + CLI + contract tests (Tasks 2–8). Source manifest with hashes, per-player-week components, event ledger at the required grain, reconciliation rows, explicit unresolved/excluded counts (Tasks 7–8). Full 2025 REG with weeks 1–17 labelled and week 18 never silently included (Task 4 `championship_window`, Task 7 manifest, Task 8 report). League-matched comparison with denominator and every mismatch, never called full-universe proof (Tasks 6–7 `POPULATION_NOTE`). Individual keys only, team keys never individual bonuses (Tasks 2, 5). Own-recovery counterexample, multi-event plays, event ordering, nullified plays, missing ids, muffs/out-of-bounds, negative scores, overlapping touchdowns, settings mismatch, duplicate player-weeks, unknown source coverage: each has a named test (Tasks 3–6). No names, no patching of the eight residuals: statuses derive from rules only. Quarantine re-audit preserving original columns (Task 7). Unsupported/unknown keys and unresolved attribution forbid exact qualification (Task 7). Launch provenance fix tested without rerunning forecasts (Task 1). No refit, no new labels: the tool never touches forecasts.

**Placeholder scan.** None.

**Type consistency.** `extract_fumble_events` → columns consumed by `player_week_components` (`event_type`, `special_teams`, `own_team`, `lost`, `status`, `player_id`, `week`); `player_week_components` → columns consumed by `league_points` (`extra_fumbles_lost`, `st_forced_fumbles`, `st_opp_recoveries`, weekly components) and `reconcile` (`attribution_status`, `unresolved_reason`, `championship_window`); `reconcile` output statuses consumed by `coverage_counts`; `audit_quarantine` sets the two play-by-play split columns to zero before calling `league_points`. `WEEKLY_COMPONENT_COLUMNS` includes `fumbles_total` so `fum` (weight 0.0 here) is modelled, not dropped.
