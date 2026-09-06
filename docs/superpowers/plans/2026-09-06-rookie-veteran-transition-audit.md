# Rookie → Veteran Transition Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reusable, tested audit that joins the accepted rookie forecast (DG-165 run `20260906T195904Z`) to the accepted veteran forecast (DG-177 run `20260906T195728Z`) on the same realized outcome, by verified identity and years, and reports paired errors, calibration and an exclusions ledger — without changing any player value.

**Architecture:** One pure module `src/dynasty_genius/rookie/transition_audit.py` (load-and-verify both frozen runs → classify draft status → join per NFL-experience stratum with label-identity assertions → metrics + seeded player-cluster bootstrap → immutable writer). A thin CLI `scripts/dg165/audit_rookie_transition.py` wires it. A second small module `src/dynasty_genius/rookie/definitions.py` builds manifest prose from the authoritative outcome block (the logged future-writer fix). Everything is fail-closed: a hash, target, key or label mismatch raises; nothing falls back.

**Tech Stack:** Python 3.14, pandas 3.0.5, numpy, pytest (`PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest`), ruff (pre-commit). No new dependencies.

**Spec:** `/Users/davidleess/dg-build/PLAYER-COMPARISON-BUILD-2026-09-06.md` (Lane 24974 section) and `/Users/davidleess/dg-build/NEXT-INCREMENT-PROPOSAL-2026-09-06.md` (DG-165 section). Preflight facts: DG-165 ticket, entry "PREFLIGHT (read-only)" 2026-09-06 17:08 EDT.

## Global Constraints

- Work only in `~/dg-wt/DG-165` on `ticket/DG-165`, starting from `e5151cda`. Never edit another lane's code; DG-177's run directory is read-only input.
- "Accepted rookie/veteran outputs stay frozen": no byte under `runs/20260906T195904Z/` or `~/dg-wt/DG-177/runs/20260906T195728Z/` changes. No refit. No model correction, no QB uplift, no blend, no market input, no youth bonus, no added production feature.
- Outputs go to a NEW `runs/<UTC>/dg165_transition_audit/` via `create_run_dir` (refuses to overwrite). Raw inputs are referenced by path + sha256, not copied.
- "Join … by verified identity and draft/feature/target years, not row order." "Verify actual input hashes, same target and identical labels; assert unique keys."
- "Record both forecast origins because the veteran has one more year of NFL information."
- "Capture players who lack a rookie-year veteran cohort row, especially no-stat/zero-appearance cases; do not hide them from the denominator or fabricate forecasts." "Do not treat the 885 paired records as all drafted players. Drafted, undrafted and unknown identity are different cases."
- "Report bias separately from accuracy." "Deterministic seeded uncertainty grouped by a justified unit, preserve temporal folds and state what the interval is conditional on."
- Never fabricate a missing value as zero; unknown stays NaN and is counted.
- Experience k for drafted players = `feature_season − draft_season + 1` from the draft table, NEVER DG-177's `seasons_played` (left-censored at 2005).
- Commit with explicit paths only (never `git add -A`); commit message ends with the session attribution lines; use `date` before writing any timestamp into a ticket.
- Prose fix: `definitions` must derive its window from the outcome block's `window_rule`; test it; frozen runs untouched.

---

## File structure

| File | Responsibility |
|---|---|
| `src/dynasty_genius/rookie/transition_audit.py` (create) | `load_rookie_run`, `load_veteran_run` (bytes verified against each run's `manifest.json["outputs_sha256"]`), `verify_same_target`, `classify_draft_status`, `join_transition`, `coverage_ledger`, `veteran_population_ledger`, `paired_metrics`, `paired_bootstrap`, `write_audit` |
| `scripts/dg165/audit_rookie_transition.py` (create) | argparse CLI: `--rookie-run --veteran-run --experience --seed --draws --runs-root`; prints the run dir |
| `src/dynasty_genius/rookie/definitions.py` (create) | `manifest_definitions(*, outcome_block, bar, last_completed_season)` — prose derived from `window_rule` |
| `scripts/dg165/run_rookie_capital.py:359-366` (modify) | call `manifest_definitions` instead of the inline dict |
| `tests/contract/test_dg165_transition_audit.py` (create) | contract tests for the audit module and CLI (synthetic fixture runs) |
| `tests/contract/test_dg165_rookie_capital.py` (modify, append) | prose-derivation test |

Column contract of `joined_rows.csv` (used by Tasks 3–6, exact names):

```
player_id, name, draft_season, pick, round, draft_position, veteran_position, experience,
target_season, rookie_forecast_year, rookie_information_through_season,
veteran_feature_season, veteran_information_through_season, information_gap_seasons,
appeared, points, games,
rookie_p_appear, rookie_e_points, rookie_e_points_given_appear, rookie_e_games,
veteran_p_appear, veteran_e_points, veteran_e_points_given_appear, veteran_e_games,
veteran_games_t, thin_history, veteran_row_without_window_appearance,
err_rookie, err_veteran, abs_err_rookie, abs_err_veteran, sq_err_rookie, sq_err_veteran, veteran_closer
```

Coverage-ledger categories (exact strings): `paired`, `no_veteran_row_no_window_appearance`,
`no_veteran_row_despite_window_appearance`, `veteran_row_without_rookie_forecast`, `label_unknown`,
`outside_overlap_classes`, `identity_unresolved`.

Draft-status categories (exact strings): `drafted_skill`, `drafted_skill_unresolved`, `drafted_skill_outside_cohort`,
`drafted_other_position`, `no_draft_record`, `unknown_identity`. (Root finding 2026-09-06: absence from the raw draft table is NOT positive
undrafted evidence while coverage/ID matching is incomplete, so the category is "no draft record", never "undrafted".)

`label_basis` in the real cohort is the SOURCE that resolved the identity — `nflverse_gsis` (1,994),
`players:name+year` (47), `players:draft_year+pick` (4), `rosters:entry_year+draft_number` (3) — and `unresolved` (35).
Every rule below tests `label_basis == "unresolved"` (the `LABEL_BASIS_UNRESOLVED` constant in `rookie/labels.py`),
never `== "resolved"`. The modelling cohort has 2,083 rows; the raw source population was 2,238 (155 excluded, classes
1999/2000, documented in the frozen run's companion). The ledger denominator is the 2,083-row cohort, and the 155 are
named separately from `manifest["cohort"]["coverage"]["rows"] − len(cohort)`, never forced into the ledger.

---

### Task 1: Fixture builder + verified loaders

**Files:**
- Create: `src/dynasty_genius/rookie/transition_audit.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) RookieRun(run_dir: Path, manifest: dict, cohort: pd.DataFrame, out_of_time: pd.DataFrame, draft_picks: pd.DataFrame, verified: dict[str, str])`
  - `@dataclass(frozen=True) VeteranRun(run_dir: Path, manifest: dict, historical: pd.DataFrame, cohort: pd.DataFrame, verified: dict[str, str])`
  - `load_rookie_run(run_dir) -> RookieRun`, `load_veteran_run(run_dir) -> VeteranRun` — each reads bytes once, hashes them, compares to `manifest["outputs_sha256"][name]` (rookie) / `manifest["outputs_sha256"][name]` (veteran), raises `ValueError` on any mismatch or missing declaration, then parses the same bytes. The rookie loader also hashes `inputs/nflverse_draft_picks.parquet` against `manifest["inputs"]["nflverse_draft_picks"]["sha256"]`.
  - `verify_same_target(rookie: RookieRun, veteran: VeteranRun) -> dict` — asserts `rookie.manifest["outcomes"]["target_identity"] == veteran.manifest["label_source"]["target_identity"]`, same `csv_sha256`, same `manifest_sha256`, same `scoring_preset`; returns `{"status": "same_target", "target_identity": ..., "outcomes_csv_sha256": ..., "outcomes_manifest_sha256": ..., "scoring_preset": ...}`; raises `ValueError` otherwise.

- [ ] **Step 1: Write the fixture builder and the first failing tests**

```python
# tests/contract/test_dg165_transition_audit.py
"""Contract tests for the rookie -> veteran transition audit (DG-165, build released 2026-09-06).

Fixtures are two tiny synthetic frozen runs with the same shapes as
runs/20260906T195904Z/dg165_rookie_capital and DG-177's dg177_basic_horizons.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TARGET = "0" * 64
CSV_SHA = "1" * 64
MAN_SHA = "2" * 64
PRESET = "nflverse_default_ppr_championship_window_v1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha(data)


def make_rookie_run(root: Path, *, oot: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                    target: str = TARGET) -> Path:
    run = root / "rookie"
    run.mkdir(parents=True)
    if cohort is None:
        cohort = pd.DataFrame({
            # 4 drafted skill players in class 2015 + one unresolved identity
            "gsis_id": ["00-A", "00-B", "00-C", "00-D", "unresolved:2015:250"],
            "draft_season": [2015, 2015, 2015, 2015, 2015],
            "position": ["QB", "RB", "WR", "TE", "WR"],
            "pick": [1, 40, 90, 150, 250],
            "round": [1, 2, 3, 5, 7],
            "age_at_draft": [22.0, 21.5, 22.3, 23.0, np.nan],
            "team": ["X"] * 5,
            "name": ["Ann", "Bob", "Cy", "Dee", "Eve"],
            "label_basis": ["resolved", "resolved", "resolved", "resolved", "unresolved"],
            "position_current": ["QB", "RB", "WR", "TE", None],
        })
    if oot is None:
        oot = pd.DataFrame({
            "gsis_id": ["00-A", "00-B", "00-C", "00-D"],
            "draft_season": [2015] * 4, "position": ["QB", "RB", "WR", "TE"],
            "pick": [1, 40, 90, 150], "round": [1, 2, 3, 5], "age_at_draft": [22.0, 21.5, 22.3, 23.0],
            "team": ["X"] * 4, "name": ["Ann", "Bob", "Cy", "Dee"], "label_basis": ["resolved"] * 4,
            "position_current": ["QB", "RB", "WR", "TE"],
            "forecast_year": [2015] * 4,
            # season-1 labels: Dee never appeared in the window
            "appear_1": [1.0, 1.0, 1.0, 0.0], "points_1": [200.0, 100.0, 50.0, 0.0], "games_1": [16.0, 12.0, 8.0, 0.0],
            # season-2 labels (target for k=1)
            "appear_2": [1.0, 1.0, 1.0, 0.0], "points_2": [250.0, 90.0, 40.0, 0.0], "games_2": [17.0, 10.0, 6.0, 0.0],
            "appear_3": [1.0, 1.0, np.nan, 0.0], "points_3": [240.0, 80.0, np.nan, 0.0], "games_3": [16.0, 9.0, np.nan, 0.0],
            "p_appear_year2": [0.95, 0.85, 0.70, 0.40], "e_points_year2": [230.0, 100.0, 60.0, 20.0],
            "e_points_year2_given_appear": [242.1, 117.6, 85.7, 50.0], "e_games_year2": [15.0, 11.0, 8.0, 4.0],
            "p_appear_year3": [0.93, 0.80, 0.65, 0.35], "e_points_year3": [225.0, 95.0, 55.0, 18.0],
            "e_points_year3_given_appear": [241.9, 118.8, 84.6, 51.4], "e_games_year3": [14.0, 10.0, 7.0, 3.0],
        })
    hashes = {}
    hashes["cohort.csv"] = _write(run / "cohort.csv", cohort.to_csv(index=False).encode())
    hashes["out_of_time_predictions.csv"] = _write(run / "out_of_time_predictions.csv", oot.to_csv(index=False).encode())
    picks = pd.DataFrame({
        "season": [2015, 2015, 2015, 2015, 2015, 2014],
        "round": [1, 2, 3, 5, 7, 4], "pick": [1, 40, 90, 150, 250, 120],
        "gsis_id": ["00-A", "00-B", "00-C", "00-D", None, "00-LB"],
        "position": ["QB", "RB", "WR", "TE", "WR", "LB"], "pfr_player_name": ["Ann", "Bob", "Cy", "Dee", "Eve", "Lou"],
    })
    (run / "inputs").mkdir()
    picks.to_parquet(run / "inputs" / "nflverse_draft_picks.parquet", index=False)
    picks_sha = _sha((run / "inputs" / "nflverse_draft_picks.parquet").read_bytes())
    manifest = {
        "model_version": "dg165_rookie_capital_v3_chain", "git_sha": "deadbeef", "scoring_arm_id": "dg165_rookie_capital_v3_chain:inner_menu:trend",
        "forecast_date": {"forecast_year": 2026, "labels_through": 2025, "last_completed_season": 2025},
        "outcomes": {"target_identity": target, "csv_sha256": CSV_SHA, "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "inputs": {"nflverse_draft_picks": {"path": "inputs/nflverse_draft_picks.parquet", "sha256": picks_sha, "rows": len(picks)}},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


def make_veteran_run(root: Path, *, hist: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                     target: str = TARGET) -> Path:
    run = root / "veteran"
    run.mkdir(parents=True)
    if hist is None:
        # horizon-1 rows at feature season 2015 (= rookie season of class 2015) for A, B, C;
        # D has no row (never appeared); an undrafted player U and a drafted linebacker LB also have rows.
        hist = pd.DataFrame({
            "horizon": [1, 1, 1, 1, 1, 1, 1],
            "player_id": ["00-B", "00-A", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "position": ["RB", "QB", "WR", "WR", "RB", "QB", "RB"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "forecast_season": [2016, 2016, 2016, 2016, 2016, 2017, 2017],
            "policy_p_appear_year1": [0.90, 0.97, 0.75, 0.5, 0.5, 0.96, 0.88],
            "policy_e_points_year1_given_appear": [111.1, 247.4, 66.7, 40.0, 40.0, 250.0, 100.0],
            "policy_e_games_year1_given_appear": [12.0, 16.0, 9.0, 8.0, 8.0, 15.0, 11.0],
            "policy_e_points_year1": [100.0, 240.0, 50.0, 20.0, 20.0, 240.0, 88.0],
            "policy_e_games_year1": [10.8, 15.5, 6.75, 4.0, 4.0, 14.4, 9.7],
            "appeared_year1": [1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0],
            "games_year1": [10.0, 17.0, 6.0, 5.0, 0.0, 16.0, 9.0],
            "points_year1": [90.0, 250.0, 40.0, 30.0, 0.0, 240.0, 80.0],
        })
    if cohort is None:
        cohort = pd.DataFrame({
            "player_id": ["00-A", "00-B", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "position": ["QB", "RB", "WR", "WR", "RB", "QB", "RB"],
            "identity_status": ["resolved"] * 7,
            "games_t": [16.0, 12.0, 3.0, 4.0, 1.0, 17.0, 10.0],
            "seasons_played": [1, 1, 1, 1, 1, 2, 2],
        })
    hashes = {}
    hashes["historical_predictions.csv"] = _write(run / "historical_predictions.csv", hist.to_csv(index=False).encode())
    gz = gzip.compress(cohort.to_csv(index=False).encode(), mtime=0)
    hashes["basic_cohort.csv.gz"] = _write(run / "basic_cohort.csv.gz", gz)
    manifest = {
        "producer": "DG-177 veteran annual forecast candidate (report-only)", "candidate_arm": "basic_cohort_3col_plus_lags",
        "git_head": "cafebabe", "last_complete_season": 2025,
        "label_source": {"kind": "common_outcome_artifact", "target_identity": target, "csv_sha256": CSV_SHA,
                          "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "forecast_cutoff": {"rule": "features observed through the feature season; a year-j label trains only when feature_season + j <= last complete season"},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


@pytest.fixture
def runs(tmp_path):
    return make_rookie_run(tmp_path), make_veteran_run(tmp_path)


def test_rookie_loader_verifies_every_declared_byte(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    loaded = load_rookie_run(rookie_dir)
    assert set(loaded.verified) >= {"cohort.csv", "out_of_time_predictions.csv", "inputs/nflverse_draft_picks.parquet"}
    assert len(loaded.cohort) == 5 and len(loaded.out_of_time) == 4 and len(loaded.draft_picks) == 6


def test_rookie_loader_refuses_altered_bytes(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    path = rookie_dir / "out_of_time_predictions.csv"
    path.write_text(path.read_text().replace("250.0", "251.0", 1))
    with pytest.raises(ValueError, match="sha256"):
        load_rookie_run(rookie_dir)


def test_veteran_loader_refuses_missing_declaration(runs):
    from src.dynasty_genius.rookie.transition_audit import load_veteran_run
    _, vet_dir = runs
    m = json.loads((vet_dir / "manifest.json").read_text())
    del m["outputs_sha256"]["basic_cohort.csv.gz"]
    (vet_dir / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="basic_cohort.csv.gz"):
        load_veteran_run(vet_dir)


def test_same_target_is_asserted_not_assumed(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run, load_veteran_run, verify_same_target
    r = load_rookie_run(make_rookie_run(tmp_path))
    v = load_veteran_run(make_veteran_run(tmp_path, target="f" * 64))
    with pytest.raises(ValueError, match="target_identity"):
        verify_same_target(r, v)
    v2 = load_veteran_run(make_veteran_run(tmp_path / "again"))
    block = verify_same_target(r, v2)
    assert block["status"] == "same_target" and block["target_identity"] == TARGET
```

- [ ] **Step 2: Run the tests to verify they fail for the right reason**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.dynasty_genius.rookie.transition_audit'`

- [ ] **Step 3: Write the loaders**

```python
# src/dynasty_genius/rookie/transition_audit.py
"""Rookie -> veteran transition audit (DG-165 build 2026-09-06): join the accepted rookie forecast
to the accepted veteran forecast on the same realized outcome and report paired errors, calibration
and an exclusions ledger. An AUDIT: it changes no player value and proposes no correction.

Fail-closed everywhere: an undeclared or altered input byte, a different outcome target, a
duplicate key or a label that differs between the two producers RAISES. Nothing falls back.

Experience k of a drafted player is feature_season - draft_season + 1 from the draft table.
DG-177's ``seasons_played`` is left-censored at 2005 and is never used for it.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "RookieRun", "VeteranRun", "load_rookie_run", "load_veteran_run", "verify_same_target",
]

ROOKIE_FILES = ("cohort.csv", "out_of_time_predictions.csv")
ROOKIE_INPUT_FILES = {"inputs/nflverse_draft_picks.parquet": "nflverse_draft_picks"}
VETERAN_FILES = ("historical_predictions.csv", "basic_cohort.csv.gz")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_verified(run_dir: Path, name: str, declared: str | None) -> bytes:
    if not declared:
        raise ValueError(f"{run_dir}: manifest declares no sha256 for {name}")
    path = run_dir / name
    if not path.exists():
        raise ValueError(f"{run_dir}: declared file missing: {name}")
    data = path.read_bytes()
    actual = _sha(data)
    if actual != declared:
        raise ValueError(f"{run_dir}: sha256 mismatch for {name}: declared {declared[:12]}…, actual {actual[:12]}…")
    return data


@dataclass(frozen=True)
class RookieRun:
    run_dir: Path
    manifest: dict
    cohort: pd.DataFrame
    out_of_time: pd.DataFrame
    draft_picks: pd.DataFrame
    verified: dict[str, str]


@dataclass(frozen=True)
class VeteranRun:
    run_dir: Path
    manifest: dict
    historical: pd.DataFrame
    cohort: pd.DataFrame
    verified: dict[str, str]


def load_rookie_run(run_dir: Path | str) -> RookieRun:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    declared = manifest.get("outputs_sha256") or {}
    verified: dict[str, str] = {}
    raw: dict[str, bytes] = {}
    for name in ROOKIE_FILES:
        raw[name] = _read_verified(run_dir, name, declared.get(name))
        verified[name] = declared[name]
    for rel, key in ROOKIE_INPUT_FILES.items():
        sha = ((manifest.get("inputs") or {}).get(key) or {}).get("sha256")
        raw[rel] = _read_verified(run_dir, rel, sha)
        verified[rel] = sha
    cohort = pd.read_csv(io.BytesIO(raw["cohort.csv"]))
    oot = pd.read_csv(io.BytesIO(raw["out_of_time_predictions.csv"]))
    picks = pd.read_parquet(io.BytesIO(raw["inputs/nflverse_draft_picks.parquet"]))
    return RookieRun(run_dir, manifest, cohort, oot, picks, verified)


def load_veteran_run(run_dir: Path | str) -> VeteranRun:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    declared = manifest.get("outputs_sha256") or {}
    verified: dict[str, str] = {}
    raw: dict[str, bytes] = {}
    for name in VETERAN_FILES:
        raw[name] = _read_verified(run_dir, name, declared.get(name))
        verified[name] = declared[name]
    historical = pd.read_csv(io.BytesIO(raw["historical_predictions.csv"]))
    cohort = pd.read_csv(io.BytesIO(gzip.decompress(raw["basic_cohort.csv.gz"])))
    return VeteranRun(run_dir, manifest, historical, cohort, verified)


def verify_same_target(rookie: RookieRun, veteran: VeteranRun) -> dict:
    r = rookie.manifest.get("outcomes") or {}
    v = veteran.manifest.get("label_source") or {}
    pairs = {
        "target_identity": (r.get("target_identity"), v.get("target_identity")),
        "outcomes_csv_sha256": (r.get("csv_sha256"), v.get("csv_sha256")),
        "outcomes_manifest_sha256": (r.get("manifest_sha256"), v.get("manifest_sha256")),
        "scoring_preset": (r.get("scoring_preset"), v.get("scoring_preset")),
    }
    for key, (a, b) in pairs.items():
        if not a or not b:
            raise ValueError(f"{key}: missing on one side (rookie={a!r}, veteran={b!r})")
        if a != b:
            raise ValueError(f"{key}: rookie {str(a)[:16]}… != veteran {str(b)[:16]}…")
    return {"status": "same_target", **{k: a for k, (a, _) in pairs.items()}}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py tests/contract/test_dg165_transition_audit.py docs/superpowers/plans/2026-09-06-rookie-veteran-transition-audit.md
git commit -m "DG-165: transition audit — verified loaders and same-target assertion (test-first)"
```

---

### Task 2: Draft-status classification

**Files:**
- Modify: `src/dynasty_genius/rookie/transition_audit.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Consumes: `RookieRun.cohort` (columns `gsis_id, draft_season, position, label_basis`), `RookieRun.draft_picks` (columns `season, round, pick, gsis_id, position`).
- Produces: `classify_draft_status(player_ids: pd.Series, identity_status: pd.Series, rookie: RookieRun) -> pd.Series` of category strings aligned to `player_ids`.

Rules, in order: `identity_status != "resolved"` → `unknown_identity`; id in cohort with `label_basis != "unresolved"` → `drafted_skill`; id in cohort with `label_basis == "unresolved"` → `drafted_skill_unresolved` (cannot occur for a veteran row — such ids never reach nflverse — but the category exists so the ledger can count cohort rows); id in the raw draft table (1980–2026) but not in the modelling cohort (2001–2026): raw draft `position` in {QB, RB, WR, TE} → `drafted_skill_outside_cohort` (root finding: genuine pre-2001 skill veterans exist; classify the raw draft position POSITIVELY and record outside-coverage separately), any other raw position → `drafted_other_position`; otherwise → `no_draft_record` (unknown draft status; not evidence of going undrafted).

Role caveat (root finding, frozen sources): DG-177's basic cohort trusts the offensive STATLINE position, and the weekly snapshot carries historic role disagreements with the roster source (e.g. Jordan Matthews 2014 TE vs WR, Logan Thomas 2014 TE vs QB, N'Keal Harry 2019 TE vs WR, Patterson 2013 RB vs WR). The audit retains `draft_position` and `veteran_position` as attributes, never uses position as a join key, counts disagreements, and states in `metrics.json["definitions"]["role_caveat"]` and the report that equal targets do not prove historic role integrity; no role repair, no refit.

- [ ] **Step 1: Write the failing test**

```python
def test_draft_status_distinguishes_drafted_undrafted_and_unknown(runs):
    from src.dynasty_genius.rookie.transition_audit import classify_draft_status, load_rookie_run
    rookie_dir, _ = runs
    r = load_rookie_run(rookie_dir)
    ids = pd.Series(["00-A", "00-LB", "00-U", "00-Z", "unresolved:2015:250"])
    status = pd.Series(["resolved", "resolved", "resolved", "unresolved_in_source", "resolved"])
    out = classify_draft_status(ids, status, r)
    assert out.tolist() == ["drafted_skill", "drafted_other_position", "undrafted", "unknown_identity", "drafted_skill_unresolved"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py::test_draft_status_distinguishes_drafted_undrafted_and_unknown -q`
Expected: FAIL with `ImportError: cannot import name 'classify_draft_status'`

- [ ] **Step 3: Implement**

```python
DRAFT_STATUS = ("drafted_skill", "drafted_skill_unresolved", "drafted_other_position", "undrafted", "unknown_identity")


def classify_draft_status(player_ids: pd.Series, identity_status: pd.Series, rookie: RookieRun) -> pd.Series:
    """Drafted at a skill position, drafted elsewhere, undrafted, or unknown — never conflated."""
    cohort = rookie.cohort
    skill_resolved = set(cohort.loc[cohort["label_basis"] == "resolved", "gsis_id"].astype(str))
    skill_unresolved = set(cohort.loc[cohort["label_basis"] != "resolved", "gsis_id"].astype(str))
    any_pick = set(rookie.draft_picks["gsis_id"].dropna().astype(str))
    out = []
    for pid, status in zip(player_ids.astype(str), identity_status.astype(str)):
        if status != "resolved":
            out.append("unknown_identity")
        elif pid in skill_resolved:
            out.append("drafted_skill")
        elif pid in skill_unresolved:
            out.append("drafted_skill_unresolved")
        elif pid in any_pick:
            out.append("drafted_other_position")
        else:
            out.append("undrafted")
    return pd.Series(out, index=player_ids.index, dtype="object")
```

Add `"classify_draft_status", "DRAFT_STATUS"` to `__all__`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py tests/contract/test_dg165_transition_audit.py
git commit -m "DG-165: transition audit — draft-status classification (drafted / other position / undrafted / unknown)"
```

---

### Task 3: The join — keys, origins, label identity

**Files:**
- Modify: `src/dynasty_genius/rookie/transition_audit.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Consumes: `RookieRun`, `VeteranRun`.
- Produces: `join_transition(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame` with exactly the joined-row column contract listed in "File structure". Raises `ValueError` on duplicate keys on either side, on a label mismatch, or on `experience < 1`.

Definitions (k = experience):
- rookie side: rows of `out_of_time` with `forecast_year == draft_season` (the draft-time forecast), rookie season index j = k + 1; forecast columns `p_appear_year{j}`, `e_points_year{j}`, `e_points_year{j}_given_appear`, `e_games_year{j}`; labels `appear_{j}`, `points_{j}`, `games_{j}`; also `appear_{k}` (window appearance in the veteran's feature season) and `games_{k}`.
- veteran side: rows of `historical` with `horizon == 1`; key `(player_id, feature_season)`; join condition `player_id == gsis_id and feature_season == draft_season + k − 1`; forecast columns `policy_*_year1`; labels `appeared_year1, games_year1, points_year1`; `games_t` from `VeteranRun.cohort` on the same key.
- origins: `rookie_forecast_year = draft_season`; `rookie_information_through_season = draft_season − 1`; `veteran_feature_season = draft_season + k − 1`; `veteran_information_through_season = veteran_feature_season`; `information_gap_seasons = k`; `target_season = draft_season + k`.
- `thin_history = veteran_games_t <= 4`; `veteran_row_without_window_appearance = (veteran_games_t >= 1) & (appear_k == 0)`.
- label identity: on joined rows, `appear_j == appeared_year1`, `points_j ≈ points_year1` (atol 1e-6), `games_j == games_year1`; rows with NaN on the rookie label side are NOT joined rows (they are ledger rows, Task 4); a NaN on one side only is a mismatch and raises.
- errors: `err_* = *_e_points − points`; `abs_err_*`, `sq_err_*`; `veteran_closer = abs_err_veteran < abs_err_rookie`.
- output sorted by `(experience, draft_season, pick, player_id)`; index reset.

- [ ] **Step 1: Write the failing tests**

```python
def test_join_is_by_key_not_row_order_and_records_both_origins(runs):
    from src.dynasty_genius.rookie.transition_audit import join_transition, load_rookie_run, load_veteran_run
    rookie_dir, vet_dir = runs
    j = join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    # the veteran fixture lists B before A; the join must pair by id, so A's veteran forecast is 240 not 100
    assert j.set_index("player_id").loc["00-A", "veteran_e_points"] == 240.0
    assert j.set_index("player_id").loc["00-A", "rookie_e_points"] == 230.0
    assert sorted(j["player_id"]) == ["00-A", "00-B", "00-C"]          # D has no veteran row; U and LB are not drafted skill
    row = j.set_index("player_id").loc["00-A"]
    assert row["experience"] == 1 and row["target_season"] == 2016
    assert row["rookie_forecast_year"] == 2015 and row["rookie_information_through_season"] == 2014
    assert row["veteran_feature_season"] == 2015 and row["veteran_information_through_season"] == 2015
    assert row["information_gap_seasons"] == 1
    assert row["points"] == 250.0 and row["appeared"] == 1.0 and row["games"] == 17.0
    assert row["err_rookie"] == pytest.approx(-20.0) and row["err_veteran"] == pytest.approx(-10.0)
    assert bool(row["veteran_closer"]) is True
    c = j.set_index("player_id").loc["00-C"]
    assert bool(c["thin_history"]) is True and c["veteran_games_t"] == 3.0


def test_join_refuses_label_disagreement(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import join_transition, load_rookie_run, load_veteran_run
    rookie_dir = make_rookie_run(tmp_path)
    vet_dir = make_veteran_run(tmp_path)
    hist = pd.read_csv(vet_dir / "historical_predictions.csv")
    hist.loc[hist.player_id == "00-A", "points_year1"] = 249.0      # same target, different label = a broken input
    import shutil; shutil.rmtree(vet_dir)
    vet_dir = make_veteran_run(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="label"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_refuses_duplicate_keys(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import join_transition, load_rookie_run, load_veteran_run
    rookie_dir = make_rookie_run(tmp_path)
    vet_dir = make_veteran_run(tmp_path)
    hist = pd.read_csv(vet_dir / "historical_predictions.csv")
    hist = pd.concat([hist, hist.iloc[[1]]], ignore_index=True)     # A twice at 2015
    import shutil; shutil.rmtree(vet_dir)
    vet_dir = make_veteran_run(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="unique"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_experience_two_uses_the_next_feature_season(runs):
    from src.dynasty_genius.rookie.transition_audit import join_transition, load_rookie_run, load_veteran_run
    rookie_dir, vet_dir = runs
    j = join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=2)
    assert sorted(j["player_id"]) == ["00-A", "00-B"]                # C's season-3 label is unknown (NaN) -> not a joined row
    a = j.set_index("player_id").loc["00-A"]
    assert a["veteran_feature_season"] == 2016 and a["target_season"] == 2017 and a["rookie_e_points"] == 225.0
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q -k join`
Expected: FAIL with `ImportError: cannot import name 'join_transition'`

- [ ] **Step 3: Implement**

```python
JOINED_COLUMNS = [
    "player_id", "name", "draft_season", "pick", "round", "draft_position", "veteran_position", "experience",
    "target_season", "rookie_forecast_year", "rookie_information_through_season",
    "veteran_feature_season", "veteran_information_through_season", "information_gap_seasons",
    "appeared", "points", "games",
    "rookie_p_appear", "rookie_e_points", "rookie_e_points_given_appear", "rookie_e_games",
    "veteran_p_appear", "veteran_e_points", "veteran_e_points_given_appear", "veteran_e_games",
    "veteran_games_t", "thin_history", "veteran_row_without_window_appearance",
    "err_rookie", "err_veteran", "abs_err_rookie", "abs_err_veteran", "sq_err_rookie", "sq_err_veteran", "veteran_closer",
]
THIN_HISTORY_MAX_GAMES = 4


def _assert_unique(frame: pd.DataFrame, keys: list[str], what: str) -> None:
    dup = frame.duplicated(keys, keep=False)
    if dup.any():
        sample = frame.loc[dup, keys].head(5).to_dict("records")
        raise ValueError(f"{what}: keys {keys} are not unique; {int(dup.sum())} rows involved, e.g. {sample}")


def rookie_draft_time_frame(rookie: RookieRun, *, experience: int) -> pd.DataFrame:
    """Draft-time forecast for NFL season j = experience + 1 with its label, one row per player."""
    j = experience + 1
    oot = rookie.out_of_time
    frame = oot.loc[oot["forecast_year"] == oot["draft_season"]].copy()
    needed = [f"p_appear_year{j}", f"e_points_year{j}", f"e_points_year{j}_given_appear", f"e_games_year{j}",
              f"appear_{j}", f"points_{j}", f"games_{j}", f"appear_{experience}", f"games_{experience}"]
    missing = [c for c in needed if c not in frame.columns]
    if missing:
        raise ValueError(f"rookie out_of_time_predictions lacks {missing} for experience {experience}")
    out = pd.DataFrame({
        "player_id": frame["gsis_id"].astype(str), "name": frame["name"], "draft_season": frame["draft_season"].astype(int),
        "pick": frame["pick"].astype(int), "round": frame["round"].astype(int), "draft_position": frame["position"],
        "rookie_forecast_year": frame["forecast_year"].astype(int),
        "rookie_p_appear": frame[f"p_appear_year{j}"], "rookie_e_points": frame[f"e_points_year{j}"],
        "rookie_e_points_given_appear": frame[f"e_points_year{j}_given_appear"], "rookie_e_games": frame[f"e_games_year{j}"],
        "rookie_label_appeared": frame[f"appear_{j}"], "rookie_label_points": frame[f"points_{j}"], "rookie_label_games": frame[f"games_{j}"],
        "feature_season_window_appearance": frame[f"appear_{experience}"],
    })
    out["veteran_feature_season"] = out["draft_season"] + experience - 1
    _assert_unique(out, ["player_id", "draft_season"], "rookie draft-time forecasts")
    return out


def veteran_horizon1_frame(veteran: VeteranRun) -> pd.DataFrame:
    h = veteran.historical
    frame = h.loc[h["horizon"] == 1].copy()
    out = pd.DataFrame({
        "player_id": frame["player_id"].astype(str), "veteran_feature_season": frame["feature_season"].astype(int),
        "veteran_position": frame["position"],
        "veteran_p_appear": frame["policy_p_appear_year1"], "veteran_e_points": frame["policy_e_points_year1"],
        "veteran_e_points_given_appear": frame["policy_e_points_year1_given_appear"], "veteran_e_games": frame["policy_e_games_year1"],
        "veteran_label_appeared": frame["appeared_year1"], "veteran_label_points": frame["points_year1"], "veteran_label_games": frame["games_year1"],
    })
    _assert_unique(out, ["player_id", "veteran_feature_season"], "veteran horizon-1 predictions")
    c = veteran.cohort
    games = pd.DataFrame({"player_id": c["player_id"].astype(str), "veteran_feature_season": c["feature_season"].astype(int), "veteran_games_t": c["games_t"]})
    _assert_unique(games, ["player_id", "veteran_feature_season"], "veteran basic cohort")
    return out.merge(games, on=["player_id", "veteran_feature_season"], how="left")


def join_transition(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame:
    if experience < 1:
        raise ValueError("experience must be >= 1 (seasons of NFL information the veteran side has)")
    r = rookie_draft_time_frame(rookie, experience=experience)
    r = r.loc[r["rookie_label_points"].notna() & r["rookie_label_appeared"].notna()]   # unknown labels are ledger rows, not joined rows
    v = veteran_horizon1_frame(veteran)
    j = r.merge(v, on=["player_id", "veteran_feature_season"], how="inner")
    bad_a = (j["rookie_label_appeared"] != j["veteran_label_appeared"])
    bad_p = ~np.isclose(j["rookie_label_points"], j["veteran_label_points"], atol=1e-6, equal_nan=False)
    bad_g = (j["rookie_label_games"] != j["veteran_label_games"])
    bad = bad_a | bad_p | bad_g
    if bad.any():
        sample = j.loc[bad, ["player_id", "veteran_feature_season", "rookie_label_points", "veteran_label_points"]].head(5).to_dict("records")
        raise ValueError(f"label mismatch between producers on {int(bad.sum())} joined rows, e.g. {sample}")
    j["experience"] = experience
    j["target_season"] = j["draft_season"] + experience
    j["rookie_information_through_season"] = j["draft_season"] - 1
    j["veteran_information_through_season"] = j["veteran_feature_season"]
    j["information_gap_seasons"] = experience
    j["appeared"] = j["rookie_label_appeared"]; j["points"] = j["rookie_label_points"]; j["games"] = j["rookie_label_games"]
    j["thin_history"] = j["veteran_games_t"] <= THIN_HISTORY_MAX_GAMES
    j["veteran_row_without_window_appearance"] = (j["veteran_games_t"] >= 1) & (j["feature_season_window_appearance"] == 0)
    for side in ("rookie", "veteran"):
        j[f"err_{side}"] = j[f"{side}_e_points"] - j["points"]
        j[f"abs_err_{side}"] = j[f"err_{side}"].abs()
        j[f"sq_err_{side}"] = j[f"err_{side}"] ** 2
    j["veteran_closer"] = j["abs_err_veteran"] < j["abs_err_rookie"]
    j = j.sort_values(["experience", "draft_season", "pick", "player_id"]).reset_index(drop=True)
    return j[JOINED_COLUMNS]
```

Add `"join_transition", "rookie_draft_time_frame", "veteran_horizon1_frame", "JOINED_COLUMNS", "THIN_HISTORY_MAX_GAMES"` to `__all__`.

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py tests/contract/test_dg165_transition_audit.py
git commit -m "DG-165: transition audit — keyed join with origins, thin-history flag and label-identity assertion"
```

---

### Task 4: Coverage ledger and veteran population ledger

**Files:**
- Modify: `src/dynasty_genius/rookie/transition_audit.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Consumes: `rookie_draft_time_frame`, `veteran_horizon1_frame`, `classify_draft_status`, `join_transition`.
- Produces:
  - `coverage_ledger(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame` — ONE ROW PER COHORT PLAYER (all classes, resolved and unresolved) with columns `player_id, name, draft_season, pick, draft_position, experience, category, feature_season_window_appearance, veteran_games_t`. Row count == `len(rookie.cohort)` always.
  - `veteran_population_ledger(rookie, veteran, joined: pd.DataFrame, *, experience: int) -> pd.DataFrame` — one row per `(veteran_feature_season, draft_status)` over the veteran horizon-1 rows in the overlap feature seasons, with `rows` and `paired_rows`; drafted-skill rows split into `drafted_skill_paired` / `drafted_skill_unpaired` via the joined frame.
  - `overlap_classes(rookie, veteran, *, experience) -> list[int]` — classes c with `c in rookie forecast years` and `c + k − 1 in veteran feature seasons`.

Category rule per cohort player (k fixed):
1. `label_basis != "resolved"` → `identity_unresolved`
2. class not in `overlap_classes` → `outside_overlap_classes`
3. joined → `paired`
4. rookie label for season k+1 is NaN → `label_unknown`
5. no veteran row at `draft_season + k − 1` and `appear_k == 0` → `no_veteran_row_no_window_appearance`
6. no veteran row and `appear_k == 1` → `no_veteran_row_despite_window_appearance`
7. veteran row exists but no draft-time rookie forecast row → `veteran_row_without_rookie_forecast`

- [ ] **Step 1: Write the failing tests**

```python
def test_coverage_ledger_keeps_every_cohort_player_in_the_denominator(runs):
    from src.dynasty_genius.rookie.transition_audit import coverage_ledger, load_rookie_run, load_veteran_run
    rookie_dir, vet_dir = runs
    led = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    assert len(led) == 5                                            # every cohort row, unresolved included
    cat = led.set_index("player_id")["category"]
    assert cat["00-A"] == "paired" and cat["00-B"] == "paired" and cat["00-C"] == "paired"
    assert cat["00-D"] == "no_veteran_row_no_window_appearance"     # missed his rookie season: counted, not dropped, not forecast
    assert cat["unresolved:2015:250"] == "identity_unresolved"
    assert led["category"].value_counts().sum() == 5


def test_veteran_population_ledger_separates_drafted_undrafted_unknown(runs):
    from src.dynasty_genius.rookie.transition_audit import join_transition, load_rookie_run, load_veteran_run, veteran_population_ledger
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    j = join_transition(r, v, experience=1)
    pop = veteran_population_ledger(r, v, j, experience=1)
    row = pop.set_index(["veteran_feature_season", "draft_status"])["rows"]
    assert row[(2015, "drafted_skill_paired")] == 3
    assert row[(2015, "drafted_other_position")] == 1               # the linebacker
    assert row[(2015, "undrafted")] == 1                            # 00-U
    assert (2015, "unknown_identity") not in row.index or row[(2015, "unknown_identity")] == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q -k ledger`
Expected: FAIL with `ImportError: cannot import name 'coverage_ledger'`

- [ ] **Step 3: Implement**

```python
LEDGER_CATEGORIES = ("paired", "no_veteran_row_no_window_appearance", "no_veteran_row_despite_window_appearance",
                     "veteran_row_without_rookie_forecast", "label_unknown", "outside_overlap_classes", "identity_unresolved")


def overlap_classes(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> list[int]:
    oot = rookie.out_of_time
    rookie_years = set(oot.loc[oot["forecast_year"] == oot["draft_season"], "draft_season"].astype(int))
    vet_years = set(veteran.historical.loc[veteran.historical["horizon"] == 1, "feature_season"].astype(int))
    return sorted(c for c in rookie_years if c + experience - 1 in vet_years)


def coverage_ledger(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame:
    """One row per cohort player; the denominator is the cohort, never the paired set."""
    classes = set(overlap_classes(rookie, veteran, experience=experience))
    r = rookie_draft_time_frame(rookie, experience=experience).set_index("player_id")
    v = veteran_horizon1_frame(veteran).set_index(["player_id", "veteran_feature_season"])
    joined_ids = set(join_transition(rookie, veteran, experience=experience)["player_id"])
    rows = []
    for row in rookie.cohort.itertuples(index=False):
        pid = str(row.gsis_id); cls = int(row.draft_season); fs = cls + experience - 1
        appear_k = r["feature_season_window_appearance"].get(pid, np.nan) if pid in r.index else np.nan
        games_t = v["veteran_games_t"].get((pid, fs), np.nan) if (pid, fs) in v.index else np.nan
        if str(row.label_basis) != "resolved":
            cat = "identity_unresolved"
        elif cls not in classes:
            cat = "outside_overlap_classes"
        elif pid in joined_ids:
            cat = "paired"
        elif pid in r.index and pd.isna(r.loc[pid, "rookie_label_points"]):
            cat = "label_unknown"
        elif (pid, fs) not in v.index:
            cat = "no_veteran_row_despite_window_appearance" if appear_k == 1 else "no_veteran_row_no_window_appearance"
        else:
            cat = "veteran_row_without_rookie_forecast"
        rows.append({"player_id": pid, "name": row.name, "draft_season": cls, "pick": int(row.pick), "draft_position": row.position,
                     "experience": experience, "category": cat, "feature_season_window_appearance": appear_k, "veteran_games_t": games_t})
    out = pd.DataFrame(rows)
    if len(out) != len(rookie.cohort):
        raise AssertionError("ledger rows must equal cohort rows")
    return out


def veteran_population_ledger(rookie: RookieRun, veteran: VeteranRun, joined: pd.DataFrame, *, experience: int) -> pd.DataFrame:
    seasons = {c + experience - 1 for c in overlap_classes(rookie, veteran, experience=experience)}
    v = veteran_horizon1_frame(veteran)
    v = v.loc[v["veteran_feature_season"].isin(seasons)].copy()
    ident = veteran.cohort.set_index(["player_id", "feature_season"])["identity_status"] if "identity_status" in veteran.cohort.columns else None
    status = pd.Series(["resolved"] * len(v), index=v.index) if ident is None else pd.Series(
        [ident.get((p, s), "unknown") for p, s in zip(v["player_id"], v["veteran_feature_season"])], index=v.index)
    v["draft_status"] = classify_draft_status(v["player_id"], status, rookie)
    paired_keys = set(zip(joined["player_id"], joined["veteran_feature_season"]))
    is_paired = pd.Series([(p, s) in paired_keys for p, s in zip(v["player_id"], v["veteran_feature_season"])], index=v.index)
    v.loc[(v["draft_status"] == "drafted_skill") & is_paired, "draft_status"] = "drafted_skill_paired"
    v.loc[(v["draft_status"] == "drafted_skill") & ~is_paired, "draft_status"] = "drafted_skill_unpaired"
    out = v.groupby(["veteran_feature_season", "draft_status"]).size().rename("rows").reset_index()
    out["experience_note"] = "experience is computed from the draft table for drafted players only; undrafted rows carry no experience (seasons_played is left-censored)"
    return out
```

Add the three names and `LEDGER_CATEGORIES` to `__all__`.

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py tests/contract/test_dg165_transition_audit.py
git commit -m "DG-165: transition audit — coverage ledger over the whole cohort and veteran population ledger"
```

---

### Task 5: Metrics (bias apart from accuracy, calibration) and the seeded player-cluster bootstrap

**Files:**
- Modify: `src/dynasty_genius/rookie/transition_audit.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Produces:
  - `paired_metrics(joined: pd.DataFrame) -> dict` with keys `n`, `rookie` / `veteran` blocks each `{rmse, mae, bias, brier_appear, appear_base_rate, mean_p_appear, points_calibration_slope, points_calibration_intercept}`, `paired` block `{mean_sq_err_diff, mean_abs_err_diff, brier_diff, share_veteran_closer}` where diff = veteran − rookie (negative favours the veteran), and `reliability` = list of decile rows `{decile, n, mean_p_rookie, mean_p_veteran, observed}`.
  - `metrics_by(joined, by: str) -> dict[str, dict]` grouping on a column (`draft_position`, `draft_season`, `experience`, `thin_history`).
  - `paired_bootstrap(joined, *, seed: int, draws: int, unit: str = "player_id") -> dict` — resamples UNITS with replacement (a player's rows across experience strata move together), returns for each of `mean_sq_err_diff`, `mean_abs_err_diff`, `brier_diff`: `{point, lo, hi}` at the 5th/95th percentiles, plus `{seed, draws, unit, level: 0.90, conditional_on: "...", folds: "..."}`.
  - `fold_sign_summary(joined) -> dict` — per draft class (temporal fold): n, mean_sq_err_diff, and `classes_veteran_better` / `classes_total`.

- [ ] **Step 1: Write the failing tests**

```python
def _toy_joined(errors_rookie, errors_veteran, players=None, experience=None):
    n = len(errors_rookie)
    pts = np.full(n, 100.0)
    d = pd.DataFrame({
        "player_id": players or [f"p{i}" for i in range(n)], "draft_season": [2015] * n, "draft_position": ["WR"] * n,
        "experience": experience or [1] * n, "thin_history": [False] * n,
        "appeared": [1.0] * n, "points": pts,
        "rookie_e_points": pts + np.asarray(errors_rookie), "veteran_e_points": pts + np.asarray(errors_veteran),
        "rookie_p_appear": [0.8] * n, "veteran_p_appear": [0.9] * n,
    })
    for side in ("rookie", "veteran"):
        d[f"err_{side}"] = d[f"{side}_e_points"] - d["points"]; d[f"abs_err_{side}"] = d[f"err_{side}"].abs(); d[f"sq_err_{side}"] = d[f"err_{side}"] ** 2
    d["veteran_closer"] = d["abs_err_veteran"] < d["abs_err_rookie"]
    return d


def test_bias_is_reported_apart_from_accuracy():
    from src.dynasty_genius.rookie.transition_audit import paired_metrics
    m = paired_metrics(_toy_joined([10, 10, 10, 10], [10, -10, 10, -10]))
    assert m["rookie"]["bias"] == pytest.approx(10.0) and m["rookie"]["rmse"] == pytest.approx(10.0)
    assert m["veteran"]["bias"] == pytest.approx(0.0) and m["veteran"]["rmse"] == pytest.approx(10.0)
    assert m["paired"]["mean_sq_err_diff"] == pytest.approx(0.0)
    assert m["n"] == 4 and m["rookie"]["brier_appear"] == pytest.approx((1 - 0.8) ** 2)


def test_bootstrap_is_deterministic_and_resamples_players_as_units():
    from src.dynasty_genius.rookie.transition_audit import paired_bootstrap
    # each player has one row at k=1 with diff +d and one at k=2 with diff -d: cluster resampling gives exactly 0 every draw
    players = ["a", "b", "c", "d", "a", "b", "c", "d"]
    d = _toy_joined([0] * 8, [3, 5, 7, 9, 3, 5, 7, 9], players=players, experience=[1, 1, 1, 1, 2, 2, 2, 2])
    d.loc[d.experience == 2, "err_veteran"] *= -1
    d["sq_err_veteran"] = d["err_veteran"] ** 2            # symmetric: sq diff per player pair is +x and +x -> not zero; use abs of signed err diff
    d["signed_diff"] = d["err_veteran"]                       # +x at k=1, -x at k=2 for the same player
    d["sq_err_rookie"] = 0.0
    one = paired_bootstrap(d, seed=7, draws=50, statistic_columns={"signed": "signed_diff"})
    two = paired_bootstrap(d, seed=7, draws=50, statistic_columns={"signed": "signed_diff"})
    assert one == two
    assert one["signed"]["lo"] == pytest.approx(0.0) and one["signed"]["hi"] == pytest.approx(0.0)
    assert one["unit"] == "player_id" and one["draws"] == 50 and one["level"] == 0.90
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q -k "bias or bootstrap"`
Expected: FAIL with `ImportError: cannot import name 'paired_metrics'`

- [ ] **Step 3: Implement**

```python
def _calibration_line(pred: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    if len(pred) < 3 or np.nanstd(pred) == 0:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(pred, actual, 1)
    return float(slope), float(intercept)


def paired_metrics(joined: pd.DataFrame) -> dict:
    n = int(len(joined))
    out: dict = {"n": n}
    if n == 0:
        return out
    actual = joined["points"].to_numpy(float); appeared = joined["appeared"].to_numpy(float)
    for side in ("rookie", "veteran"):
        err = joined[f"err_{side}"].to_numpy(float); p = joined[f"{side}_p_appear"].to_numpy(float)
        slope, intercept = _calibration_line(joined[f"{side}_e_points"].to_numpy(float), actual)
        out[side] = {
            "rmse": float(np.sqrt(np.mean(err ** 2))), "mae": float(np.mean(np.abs(err))), "bias": float(np.mean(err)),
            "brier_appear": float(np.mean((p - appeared) ** 2)), "appear_base_rate": float(np.mean(appeared)), "mean_p_appear": float(np.mean(p)),
            "points_calibration_slope": slope, "points_calibration_intercept": intercept,
        }
    out["paired"] = {
        "mean_sq_err_diff": float(np.mean(joined["sq_err_veteran"] - joined["sq_err_rookie"])),
        "mean_abs_err_diff": float(np.mean(joined["abs_err_veteran"] - joined["abs_err_rookie"])),
        "brier_diff": float(np.mean((joined["veteran_p_appear"] - appeared) ** 2 - (joined["rookie_p_appear"] - appeared) ** 2)),
        "share_veteran_closer": float(np.mean(joined["veteran_closer"].astype(float))),
        "sign_convention": "veteran minus rookie; negative favours the veteran forecast",
    }
    deciles = pd.qcut(joined["veteran_p_appear"].rank(method="first"), q=min(10, n), labels=False)
    rel = []
    for d, g in joined.groupby(deciles):
        rel.append({"decile": int(d), "n": int(len(g)), "mean_p_rookie": float(g["rookie_p_appear"].mean()),
                    "mean_p_veteran": float(g["veteran_p_appear"].mean()), "observed": float(g["appeared"].mean())})
    out["reliability"] = rel
    return out


def metrics_by(joined: pd.DataFrame, by: str) -> dict[str, dict]:
    return {str(key): paired_metrics(g) for key, g in joined.groupby(by, sort=True)}


def fold_sign_summary(joined: pd.DataFrame) -> dict:
    folds = {}
    for cls, g in joined.groupby("draft_season", sort=True):
        folds[str(int(cls))] = {"n": int(len(g)), "mean_sq_err_diff": float(np.mean(g["sq_err_veteran"] - g["sq_err_rookie"])),
                                "mean_abs_err_diff": float(np.mean(g["abs_err_veteran"] - g["abs_err_rookie"]))}
    better = sum(1 for f in folds.values() if f["mean_sq_err_diff"] < 0)
    return {"by_draft_class": folds, "classes_veteran_better": better, "classes_total": len(folds),
            "meaning": "each draft class is one temporal fold; the count of classes where the veteran side has lower mean squared error preserves the fold structure the bootstrap does not resample"}


DEFAULT_STATISTICS = {"mean_sq_err_diff": None, "mean_abs_err_diff": None, "brier_diff": None}


def paired_bootstrap(joined: pd.DataFrame, *, seed: int, draws: int, unit: str = "player_id",
                     statistic_columns: dict[str, str] | None = None) -> dict:
    """Percentile interval of mean paired differences, resampling UNITS (players) with replacement.

    Justification of the unit: a player contributes one row per experience stratum and those rows
    share his career; resampling rows would treat them as independent. The interval is conditional on
    both frozen fits and on the realized seasons; it is player-sampling variability only — not model,
    selection or season uncertainty, and not a forecast interval. Temporal folds are reported beside it
    (fold_sign_summary), not resampled.
    """
    frame = joined.copy()
    if statistic_columns is None:
        frame["mean_sq_err_diff"] = frame["sq_err_veteran"] - frame["sq_err_rookie"]
        frame["mean_abs_err_diff"] = frame["abs_err_veteran"] - frame["abs_err_rookie"]
        frame["brier_diff"] = (frame["veteran_p_appear"] - frame["appeared"]) ** 2 - (frame["rookie_p_appear"] - frame["appeared"]) ** 2
        statistic_columns = {k: k for k in DEFAULT_STATISTICS}
    units = frame[unit].astype(str).to_numpy()
    uniq, inverse = np.unique(units, return_inverse=True)
    rng = np.random.default_rng(seed)
    n_units = len(uniq)
    sums = {name: np.bincount(inverse, weights=frame[col].to_numpy(float), minlength=n_units) for name, col in statistic_columns.items()}
    counts = np.bincount(inverse, minlength=n_units).astype(float)
    result = {"seed": int(seed), "draws": int(draws), "unit": unit, "level": 0.90, "n_units": int(n_units), "n_rows": int(len(frame)),
              "conditional_on": "both frozen fits and the realized seasons; player-sampling variability only, not model, selection or season uncertainty",
              "folds": "draft classes are not resampled; see fold_sign_summary"}
    for name, col in statistic_columns.items():
        point = float(frame[col].mean())
        stats = np.empty(draws)
        for b in range(draws):
            idx = rng.integers(0, n_units, n_units)
            stats[b] = sums[name][idx].sum() / counts[idx].sum()
        result[name] = {"point": point, "lo": float(np.percentile(stats, 5)), "hi": float(np.percentile(stats, 95))}
    return result
```

Add `"paired_metrics", "metrics_by", "fold_sign_summary", "paired_bootstrap"` to `__all__`.

- [ ] **Step 4: Run to verify pass**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py tests/contract/test_dg165_transition_audit.py
git commit -m "DG-165: transition audit — paired metrics with bias apart from accuracy, reliability, fold summary, seeded player-cluster bootstrap"
```

---

### Task 6: Immutable writer, rendered report, CLI

**Files:**
- Modify: `src/dynasty_genius/rookie/transition_audit.py`
- Create: `scripts/dg165/audit_rookie_transition.py`
- Test: `tests/contract/test_dg165_transition_audit.py`

**Interfaces:**
- Produces:
  - `run_audit(rookie: RookieRun, veteran: VeteranRun, *, experiences: tuple[int, ...], seed: int, draws: int) -> dict` returning `{"joined": DataFrame, "coverage": DataFrame, "population": DataFrame, "metrics": dict, "binding": dict}`.
  - `write_audit(run_dir: Path, result: dict, *, rookie, veteran, seed, draws, experiences, git_sha: str) -> dict` writing `joined_rows.csv`, `coverage_ledger.csv`, `veteran_population_ledger.csv`, `metrics.json`, `REPORT.md`, `manifest.json`; returns the manifest. `manifest["outputs_sha256"]` covers every written file except itself.
  - `render_report(metrics: dict, coverage: pd.DataFrame, population: pd.DataFrame, binding: dict) -> str` — every number read from the dicts/frames, none typed.
  - CLI `scripts/dg165/audit_rookie_transition.py --rookie-run DIR --veteran-run DIR [--experience 1 2 3] [--seed 20260906] [--draws 2000] [--runs-root runs]` → prints the run dir path; exit code non-zero on any raise.

`metrics.json` layout:

```json
{"experiences": {"1": {"overall": {...paired_metrics...}, "by_position": {...}, "by_draft_class": {...}, "by_thin_history": {...},
                       "folds": {...fold_sign_summary...}, "bootstrap": {...}, "coverage_counts": {"paired": 885, ...},
                       "flags": {"veteran_row_without_window_appearance": 14, "position_disagreement": 16}}, "2": {...}},
 "pooled_bootstrap": {...paired_bootstrap over all experiences, unit player_id...},
 "definitions": {"experience": "...", "thin_history": "veteran games_t <= 4", "origins": "...", "sign_convention": "..."}}
```

- [ ] **Step 1: Write the failing tests**

```python
def test_write_audit_is_immutable_and_hashes_every_output(runs, tmp_path):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run, load_veteran_run, run_audit, write_audit
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    result = run_audit(r, v, experiences=(1, 2), seed=3, draws=20)
    out = tmp_path / "runs" / "20990101T000000Z" / "dg165_transition_audit"
    out.mkdir(parents=True)
    manifest = write_audit(out, result, rookie=r, veteran=v, seed=3, draws=20, experiences=(1, 2), git_sha="abc")
    for name, sha in manifest["outputs_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
    assert {"joined_rows.csv", "coverage_ledger.csv", "veteran_population_ledger.csv", "metrics.json", "REPORT.md"} <= set(manifest["outputs_sha256"])
    assert manifest["inputs"]["rookie"]["verified"]["out_of_time_predictions.csv"] == r.verified["out_of_time_predictions.csv"]
    assert manifest["binding"]["status"] == "same_target"
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["experiences"]["1"]["overall"]["n"] == 3 and metrics["experiences"]["1"]["coverage_counts"]["no_veteran_row_no_window_appearance"] == 1
    report = (out / "REPORT.md").read_text()
    assert "n = 3" in report and "no_veteran_row_no_window_appearance" in report
    with pytest.raises(FileExistsError):
        from src.dynasty_genius.rookie.run_dir import create_run_dir
        create_run_dir(tmp_path / "runs", run_id="20990101T000000Z", name="dg165_transition_audit")


def test_cli_end_to_end(runs, tmp_path):
    import subprocess, sys
    rookie_dir, vet_dir = runs
    proc = subprocess.run([sys.executable, "scripts/dg165/audit_rookie_transition.py", "--rookie-run", str(rookie_dir), "--veteran-run", str(vet_dir),
                           "--experience", "1", "--seed", "1", "--draws", "10", "--runs-root", str(tmp_path / "runs")],
                          capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2], env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 0, proc.stderr
    run_dir = Path(proc.stdout.strip().splitlines()[-1])
    assert (run_dir / "manifest.json").exists() and run_dir.name == "dg165_transition_audit"
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q -k "write_audit or cli"`
Expected: FAIL with `ImportError: cannot import name 'run_audit'` and, for the CLI, a non-zero return code (file not found)

- [ ] **Step 3: Implement the writer and report**

```python
from datetime import datetime, timezone


def run_audit(rookie: RookieRun, veteran: VeteranRun, *, experiences: tuple[int, ...], seed: int, draws: int) -> dict:
    binding = verify_same_target(rookie, veteran)
    joined_all, coverage_all, population_all = [], [], []
    per_k: dict[str, dict] = {}
    for k in experiences:
        j = join_transition(rookie, veteran, experience=k)
        cov = coverage_ledger(rookie, veteran, experience=k)
        pop = veteran_population_ledger(rookie, veteran, j, experience=k)
        joined_all.append(j); coverage_all.append(cov); population_all.append(pop.assign(experience=k))
        per_k[str(k)] = {
            "overall": paired_metrics(j), "by_position": metrics_by(j, "draft_position"), "by_draft_class": metrics_by(j, "draft_season"),
            "by_thin_history": metrics_by(j, "thin_history"), "folds": fold_sign_summary(j),
            "bootstrap": paired_bootstrap(j, seed=seed, draws=draws) if len(j) else {"n_rows": 0},
            "coverage_counts": {c: int((cov["category"] == c).sum()) for c in LEDGER_CATEGORIES},
            "overlap_classes": overlap_classes(rookie, veteran, experience=k),
            "flags": {"veteran_row_without_window_appearance": int(j["veteran_row_without_window_appearance"].sum()),
                      "position_disagreement": int((j["draft_position"] != j["veteran_position"]).sum())},
        }
    joined = pd.concat(joined_all, ignore_index=True) if joined_all else pd.DataFrame(columns=JOINED_COLUMNS)
    metrics = {
        "experiences": per_k,
        "pooled_bootstrap": paired_bootstrap(joined, seed=seed, draws=draws) if len(joined) else {"n_rows": 0},
        "definitions": {
            "experience": "feature_season - draft_season + 1 from the draft table; never DG-177 seasons_played (left-censored at 2005)",
            "thin_history": f"veteran games_t <= {THIN_HISTORY_MAX_GAMES} in the feature season",
            "origins": "rookie forecast made at draft time with NFL information through draft_season - 1; veteran forecast made after the feature season with information through it; the gap is the experience in seasons",
            "sign_convention": "diff = veteran minus rookie; negative favours the veteran forecast",
            "not": "an audit of two frozen forecasts on one realized target; no correction, blend, uplift or feature is proposed here",
        },
    }
    return {"joined": joined, "coverage": pd.concat(coverage_all, ignore_index=True), "population": pd.concat(population_all, ignore_index=True),
            "metrics": metrics, "binding": binding}


def _fmt(x, nd=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def render_report(metrics: dict, coverage: pd.DataFrame, population: pd.DataFrame, binding: dict) -> str:
    lines = ["# DG-165 rookie → veteran transition audit", "",
             f"Same realized target on both sides: `{binding['target_identity'][:16]}…` ({binding['scoring_preset']}).", "",
             "An audit of two frozen forecasts. Nothing here changes a player value; " + metrics["definitions"]["not"] + ".", ""]
    for k, block in metrics["experiences"].items():
        o = block["overall"]; lines += [f"## Experience {k} (veteran has {k} more season(s) of NFL information)", ""]
        if o.get("n", 0) == 0:
            lines += ["No paired rows.", ""]; continue
        lines += [f"Paired rows: n = {o['n']} over draft classes {block['overlap_classes'][0]}–{block['overlap_classes'][-1]}.", "",
                  "| forecast | RMSE | MAE | bias | Brier(appear) | calib slope |", "|---|---|---|---|---|---|"]
        for side in ("rookie", "veteran"):
            s = o[side]; lines.append(f"| {side} | {_fmt(s['rmse'])} | {_fmt(s['mae'])} | {_fmt(s['bias'], 1)} | {_fmt(s['brier_appear'], 3)} | {_fmt(s['points_calibration_slope'], 2)} |")
        p = o["paired"]; b = block["bootstrap"]
        lines += ["", f"Paired difference (veteran − rookie): mean squared error {_fmt(p['mean_sq_err_diff'])} "
                  f"[90% player-bootstrap {_fmt(b['mean_sq_err_diff']['lo'])}, {_fmt(b['mean_sq_err_diff']['hi'])}]; "
                  f"mean absolute error {_fmt(p['mean_abs_err_diff'])} [{_fmt(b['mean_abs_err_diff']['lo'])}, {_fmt(b['mean_abs_err_diff']['hi'])}]; "
                  f"veteran closer on {_fmt(100 * p['share_veteran_closer'])}% of rows; classes where the veteran side is better: "
                  f"{block['folds']['classes_veteran_better']} of {block['folds']['classes_total']}.", "",
                  f"Interval is conditional on: {b['conditional_on']}.", "", "| position | n | rookie RMSE | veteran RMSE | rookie bias | veteran bias |", "|---|---|---|---|---|---|"]
        for pos, m in block["by_position"].items():
            lines.append(f"| {pos} | {m['n']} | {_fmt(m['rookie']['rmse'])} | {_fmt(m['veteran']['rmse'])} | {_fmt(m['rookie']['bias'])} | {_fmt(m['veteran']['bias'])} |")
        lines += ["", "| thin history (games_t ≤ 4) | n | rookie RMSE | veteran RMSE |", "|---|---|---|---|"]
        for flag, m in block["by_thin_history"].items():
            lines.append(f"| {flag} | {m['n']} | {_fmt(m['rookie']['rmse'])} | {_fmt(m['veteran']['rmse'])} |")
        lines += ["", "Coverage of the WHOLE draft cohort at this experience (paired rows are not all drafted players):", ""]
        for cat, n in block["coverage_counts"].items():
            lines.append(f"- {cat}: {n}")
        lines += ["", f"Flags: veteran rows without a window appearance {block['flags']['veteran_row_without_window_appearance']}; "
                  f"draft/role position disagreements {block['flags']['position_disagreement']}.", ""]
    lines += ["## Veteran population at the overlap feature seasons, by draft status", ""]
    for (k, status), g in population.groupby(["experience", "draft_status"]):
        lines.append(f"- experience {k}, {status}: {int(g['rows'].sum())} rows")
    lines += ["", f"_{population['experience_note'].iloc[0] if len(population) else ''}_", ""]
    return "\n".join(lines)


def write_audit(run_dir: Path, result: dict, *, rookie: RookieRun, veteran: VeteranRun, seed: int, draws: int,
                experiences: tuple[int, ...], git_sha: str) -> dict:
    run_dir = Path(run_dir)
    started = datetime.now(timezone.utc).isoformat()
    result["joined"].to_csv(run_dir / "joined_rows.csv", index=False)
    result["coverage"].to_csv(run_dir / "coverage_ledger.csv", index=False)
    result["population"].to_csv(run_dir / "veteran_population_ledger.csv", index=False)
    (run_dir / "metrics.json").write_text(json.dumps(result["metrics"], indent=2, sort_keys=True, allow_nan=True))
    (run_dir / "REPORT.md").write_text(render_report(result["metrics"], result["coverage"], result["population"], result["binding"]))
    outputs = {name: _sha((run_dir / name).read_bytes()) for name in ("joined_rows.csv", "coverage_ledger.csv", "veteran_population_ledger.csv", "metrics.json", "REPORT.md")}
    manifest = {
        "schema_version": "dg165_transition_audit_v1", "ticket": "DG-165", "git_sha": git_sha, "run_dir": str(run_dir),
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "rookie": {"run_dir": str(rookie.run_dir), "model_version": rookie.manifest.get("model_version"), "scoring_arm_id": rookie.manifest.get("scoring_arm_id"),
                       "git_sha": rookie.manifest.get("git_sha"), "verified": rookie.verified},
            "veteran": {"run_dir": str(veteran.run_dir), "producer": veteran.manifest.get("producer"), "candidate_arm": veteran.manifest.get("candidate_arm"),
                        "git_head": veteran.manifest.get("git_head"), "verified": veteran.verified,
                        "forecast_columns": "policy_* (what the board consumes); candidate_* and baseline_* not audited here"},
        },
        "binding": result["binding"], "experiences": list(experiences), "seed": seed, "draws": draws,
        "definitions": result["metrics"]["definitions"], "outputs_sha256": outputs,
        "frozen_inputs_untouched": True,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
```

Add `"run_audit", "render_report", "write_audit"` to `__all__`.

- [ ] **Step 4: Write the CLI**

```python
#!/usr/bin/env python
"""Audit the rookie -> veteran forecast transition on the same realized target (DG-165, 2026-09-06).

Reads two FROZEN runs (bytes verified against their manifests), writes a NEW immutable run
directory. Changes no player value. Exit code is non-zero on any refusal.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from src.dynasty_genius.rookie.run_dir import create_run_dir
from src.dynasty_genius.rookie.transition_audit import load_rookie_run, load_veteran_run, run_audit, write_audit


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001 - provenance is recorded as unknown, never invented
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rookie-run", required=True)
    ap.add_argument("--veteran-run", required=True)
    ap.add_argument("--experience", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--seed", type=int, default=20260906)
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args(argv)
    rookie = load_rookie_run(args.rookie_run)
    veteran = load_veteran_run(args.veteran_run)
    result = run_audit(rookie, veteran, experiences=tuple(args.experience), seed=args.seed, draws=args.draws)
    run_dir = create_run_dir(args.runs_root, name="dg165_transition_audit")
    write_audit(run_dir, result, rookie=rookie, veteran=veteran, seed=args.seed, draws=args.draws, experiences=tuple(args.experience), git_sha=git_sha())
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run to verify pass, then the whole lane suite and ruff**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_transition_audit.py -q`
Expected: 15 passed

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_rookie_capital.py tests/contract/test_dg165_common_outcomes_adapter.py tests/contract/test_dg165_sleeper_eligibility.py tests/contract/test_dg165_weekly_source_capture.py tests/contract/test_dg165_source_preparation.py tests/contract/test_dg165_transition_audit.py -q`
Expected: 75 passed

Run: `$(ls -d ~/.cache/pre-commit/*/bin/ruff | head -1) check src/dynasty_genius/rookie/transition_audit.py scripts/dg165/audit_rookie_transition.py tests/contract/test_dg165_transition_audit.py`
Expected: All checks passed

- [ ] **Step 6: Commit**

```bash
git add src/dynasty_genius/rookie/transition_audit.py scripts/dg165/audit_rookie_transition.py tests/contract/test_dg165_transition_audit.py
git commit -m "DG-165: transition audit — immutable writer, rendered report and CLI"
```

---

### Task 7: The logged prose fix — definitions derived from the outcome block

**Files:**
- Create: `src/dynasty_genius/rookie/definitions.py`
- Modify: `scripts/dg165/run_rookie_capital.py:359-366` (replace the inline `"definitions": {...}` with a call)
- Test: `tests/contract/test_dg165_rookie_capital.py` (append)

**Interfaces:**
- Produces: `manifest_definitions(*, outcome_block: dict | None, bar: dict, last_completed_season: int) -> dict` with keys `qualifying_season, appearance, season_points, games, identity_unresolved`. With an outcome block, every string that names the scoring scope says "outcome window (<window_rule>)" and none contains "regular-season"; without one (legacy, no artifact bound) the previous wording is kept verbatim.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/contract/test_dg165_rookie_capital.py

def test_manifest_definitions_derive_their_window_from_the_outcome_block():
    from src.dynasty_genius.rookie.definitions import manifest_definitions
    rule = "Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021; POST records do not contribute outcomes."
    d = manifest_definitions(outcome_block={"window_rule": rule, "scoring_preset": "nflverse_default_ppr_championship_window_v1"},
                             bar={"QB": 37, "RB": 45, "WR": 71, "TE": 21}, last_completed_season=2025)
    assert set(d) == {"qualifying_season", "appearance", "season_points", "games", "identity_unresolved"}
    for key in ("qualifying_season", "appearance", "season_points", "games"):
        assert "regular-season" not in d[key], key
        assert rule in d[key], key
    assert "2025" in d["identity_unresolved"]
    legacy = manifest_definitions(outcome_block=None, bar={"QB": 37}, last_completed_season=2025)
    assert "regular-season" in legacy["season_points"]
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_rookie_capital.py::test_manifest_definitions_derive_their_window_from_the_outcome_block -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.dynasty_genius.rookie.definitions'`

- [ ] **Step 3: Implement the module and wire the writer**

```python
# src/dynasty_genius/rookie/definitions.py
"""Manifest prose for the rookie run, derived from the AUTHORITATIVE outcome block.

The logged 2026-09-06 follow-up: the legacy ``definitions`` text said "regular-season" while
``outcomes`` and ``units`` specified the championship window. Prose is now generated from the
bound outcome block's ``window_rule`` so the two cannot disagree. The legacy wording survives only
when no outcome artifact is bound (no window exists to name)."""
from __future__ import annotations

from collections.abc import Mapping

__all__ = ["manifest_definitions"]


def manifest_definitions(*, outcome_block: Mapping | None, bar: Mapping[str, int], last_completed_season: int) -> dict[str, str]:
    if outcome_block:
        rule = outcome_block["window_rule"]
        scope = f"the outcome window ({rule})"
        return {
            "qualifying_season": (f"finished at or above the bar rank for the position by points inside {scope}; bar = {dict(bar)}; "
                                  "tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance; "
                                  "cohort players are ranked at their DRAFT role every season, others at their weekly-stats position"),
            "appearance": (f"at least one weekly stat row inside {scope} (not 'dressed', not 'took a snap'); "
                           "a player without a stat row in the window scored zero window points that season"),
            "season_points": f"PPR points (nflverse weekly fantasy_points_ppr) summed inside {scope}, exactly 0 without an appearance",
            "games": f"weeks with a weekly stat row inside {scope}, exactly 0 without an appearance",
            "identity_unresolved": _identity_text(last_completed_season),
        }
    return {
        "qualifying_season": (f"finished at or above the bar rank for the position by regular-season PPR total; bar = {dict(bar)}; "
                              "tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance; "
                              "cohort players are ranked at their DRAFT role every season, others at their weekly-stats position"),
        "appearance": ("at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); "
                       "a player without a stat row scored zero fantasy points that season"),
        "season_points": "regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance",
        "games": "weeks with a weekly stat row, exactly 0 without an appearance",
        "identity_unresolved": _identity_text(last_completed_season),
    }


def _identity_text(last_completed_season: int) -> str:
    return (f"no gsis_id in nflverse draft picks and no match in the players table or 1999-{last_completed_season} rosters by draft key "
            "or name+year; labels NaN, never zero, except in the named sensitivity arm")
```

In `scripts/dg165/run_rookie_capital.py`, replace the whole `"definitions": { ... },` literal (lines 359–366) with:

```python
        "definitions": manifest_definitions(outcome_block=outcome_block, bar=bar, last_completed_season=last_completed),
```

and add `from src.dynasty_genius.rookie.definitions import manifest_definitions` to the imports. Do not run the writer.

- [ ] **Step 4: Run to verify pass and that the writer still imports**

Run: `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp .venv/bin/python -m pytest tests/contract/test_dg165_rookie_capital.py -q`
Expected: all passed (previous count + 1)

Run: `PYTHONPATH=. .venv/bin/python -c "import ast,sys; ast.parse(open('scripts/dg165/run_rookie_capital.py').read()); print('parses')"` and `PYTHONPATH=. .venv/bin/python scripts/dg165/run_rookie_capital.py --help | head -3`
Expected: `parses`, then the help text (no fit is run)

Run: `git status --short runs/ && shasum -a 256 runs/20260906T195904Z/dg165_rookie_capital/manifest.json`
Expected: no change under `runs/`; manifest hash unchanged from the frozen run

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/rookie/definitions.py scripts/dg165/run_rookie_capital.py tests/contract/test_dg165_rookie_capital.py
git commit -m "DG-165: manifest definitions prose derived from the bound outcome block's window rule (logged follow-up, test-first)"
```

---

### Task 8: Real-data run, self-review of the artifact, ticket record

**Files:**
- Create (by the CLI): `runs/<UTC>/dg165_transition_audit/`
- Modify: `/Users/davidleess/dg-build/tickets/DG-165-the-horizon-term-cannot-price-a-rookie.md` (append)

- [ ] **Step 1: Run the audit on the two frozen runs**

```bash
cd ~/dg-wt/DG-165 && PYTHONPATH=. .venv/bin/python scripts/dg165/audit_rookie_transition.py \
  --rookie-run runs/20260906T195904Z/dg165_rookie_capital \
  --veteran-run /Users/davidleess/dg-wt/DG-177/runs/20260906T195728Z/dg177_basic_horizons \
  --experience 1 2 3 --seed 20260906 --draws 2000
```

Expected: prints `runs/<UTC>/dg165_transition_audit`; exit 0.

- [ ] **Step 2: Verify the artifact against the preflight facts (the preflight was the old build; re-derive, do not carry over)**

```bash
PYTHONPATH=. .venv/bin/python - <<'EOF'
import json, glob, pandas as pd
d = sorted(glob.glob("runs/*/dg165_transition_audit"))[-1]
m = json.load(open(f"{d}/metrics.json")); k1 = m["experiences"]["1"]
print("k=1 n:", k1["overall"]["n"], "| rookie RMSE/bias:", round(k1["overall"]["rookie"]["rmse"],1), round(k1["overall"]["rookie"]["bias"],1),
      "| veteran RMSE/bias:", round(k1["overall"]["veteran"]["rmse"],1), round(k1["overall"]["veteran"]["bias"],1))
print("coverage k=1:", k1["coverage_counts"]); print("flags:", k1["flags"]); print("bootstrap sq diff:", k1["bootstrap"]["mean_sq_err_diff"])
cov = pd.read_csv(f"{d}/coverage_ledger.csv"); print("ledger rows per k == cohort rows:", cov.groupby("experience").size().to_dict())
EOF
```

Expected: k=1 n = 885 with identical labels (the join raised otherwise); coverage counts sum to the MODELLING cohort size (2,083) per experience, with the 155 raw-source exclusions reported separately in the manifest; root's independent join: overlap classes 2011–2024 hold 1,107 rookie rows, 1,102 complete year-2 labels, 885 pairs, 222 omissions = 210 no rookie-window appearance + 7 with appearance + 5 unknown labels; 16 pairs with draft position ≠ veteran feature position (both attributes retained, position is never a join key); `veteran_row_without_window_appearance` = 14. Any departure from these is a finding to record, not a number to force.

- [ ] **Step 3: Commit the run (outputs are small CSV/JSON/MD; the frozen inputs are referenced by hash, not copied)**

```bash
git add runs/<UTC>/dg165_transition_audit
git commit -m "DG-165: transition audit run <UTC> on frozen rookie 195904Z and veteran 195728Z (immutable)"
```

- [ ] **Step 4: Record in the ticket with a checked clock**

Run `date`, then append to the DG-165 ticket: run dir, exact command, every input sha (from `manifest.json["inputs"]`), the binding block, k=1/2/3 headline numbers read from `metrics.json`, the coverage counts, the flags, and the sentence "An audit; no value changed; no correction proposed."

---

### Task 9: Cross-check DG-178's candidate against the frozen rookie export (after lane 25057 publishes it)

**Files:** none modified (read-only); ticket appended.

- [ ] **Step 1: Locate lane 25057's new audit run** (`ls -t ~/dg-wt/DG-178/runs | head -3`) and its API run id; if none newer than `203007Z` exists yet, record "pending" in the ticket and continue to Task 10.

- [ ] **Step 2: Rookie expected-point details** — for each of the 80 rookies, compare the page's per-season player expected points (the new Why details) with `rookie_scores_2026.csv` columns `e_points_year1..e_points_year5` at full precision (`np.isclose(atol=1e-9)`), keyed by `player_id`. Report count equal / count differing with examples.

- [ ] **Step 3: All-league search and placement** — confirm every rookie owned in the league appears in the search collection with `position == Sleeper fantasy_positions` (my eligibility capture `runs/20260906T164442Z/eligibility_capture/reconciliation.csv`).

- [ ] **Step 4: Record** the result in the ticket with a `date` clock; any mismatch is reported to lane 25057 by message, never patched.

---

### Task 10: Final checks and handoff

- [ ] Run the full lane suite once more and ruff on every touched file (commands in Task 6 Step 5).
- [ ] `git log --oneline e5151cda..HEAD` — every commit explicit-path; `git status --short` clean; `git diff --check` clean.
- [ ] `git push origin ticket/DG-165` (checkpoint only; no merge, no promotion).
- [ ] Ticket entry (date-checked): commits, plan path, run dir, test counts, cross-check result or "pending", and the line "Blocker: none; waiting on root review."

---

## Self-review against the spec

- **Join by identity and years, verify hashes, same target, identical labels, unique keys:** Tasks 1, 3.
- **Record both forecast origins:** Task 3 (`rookie_information_through_season`, `veteran_information_through_season`, `information_gap_seasons`).
- **Capture players lacking a veteran row, no-stat cases, no hidden denominators, no fabricated forecasts:** Task 4 (ledger over the whole cohort; `no_veteran_row_no_window_appearance`; ledger rows == cohort rows asserted).
- **Immutable joined rows, exclusions/coverage ledger, metrics by position, class, experience, thin history:** Tasks 5–6.
- **Paired errors + appearance/points calibration; bias separate from accuracy:** Task 5 (`bias` vs `rmse`/`mae`; Brier, reliability, calibration line).
- **Deterministic seeded uncertainty, justified unit, temporal folds preserved, conditional statement:** Task 5 (`paired_bootstrap` unit = player, `fold_sign_summary`, `conditional_on`).
- **885 ≠ all drafted players; drafted / undrafted / unknown distinct:** Tasks 2, 4.
- **No correction / uplift / blend / market / youth bonus / feature / refit:** no task fits any model; `definitions.not` states it in the artifact.
- **Prose fix with a test, frozen bytes preserved:** Task 7 (writer not run; hash check).
- **Actual-data run, cross-check DG-178:** Tasks 8–9.
- Placeholder scan: none. Type consistency: `RookieRun`/`VeteranRun` fields, `JOINED_COLUMNS`, ledger category strings and `paired_bootstrap` return keys are used with the same names in Tasks 3–6 and the report renderer.
