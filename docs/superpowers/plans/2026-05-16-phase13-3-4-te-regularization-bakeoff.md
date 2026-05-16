# Phase 13.3.4 TE Regularization Bake-Off Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a validation-only TE-only regularization bake-off over an alpha grid to determine whether stronger regularization preserves rank stability while retaining the role-risk error improvement.

**Architecture:** Extend the Phase 13.3.3 experiment logic to iterate over a grid of Ridge alphas. The bake-off evaluates three candidate sets: baseline features only, baseline + `unified_penalty`, and baseline + `sparse_duo`. It reports RMSE, MAE, rank metrics, and acceptance gates for every (alpha, candidate) pair. It must not alter production Engine B contracts, model artifacts, manifests, PVO scoring, decision surfaces, or TE promotion status.

**Tech Stack:** Python 3.14, pandas, numpy, sklearn Ridge, existing `src/dynasty_genius/eval/te_role_risk_experiment.py`, pytest.

---

## Approved Source Decision

Decision note:

- `docs/validation/phase13-3-4-te-regularization-decision.md`

Approved alpha grid:

- `1.0`, `10.0`, `50.0`, `100.0`, `250.0`, `500.0`

Approved candidates:

- `baseline_only`: (existing Engine B TE features)
- `unified_penalty`: baseline + `te_role_is_risk_profile`
- `sparse_duo`: baseline + `te_role_role_risk` + `te_role_blocking_specialist`

## Hard Constraints

The implementation must preserve all constraints below:

- TE remains `EXPERIMENTAL`.
- No production model artifact promotion.
- No writes to `app/data/models/engine_b/v2_manifest.json`.
- No changes to `src/dynasty_genius/models/engine_b_contract.py`.
- No changes to PVO scoring or surface routing.
- No market-derived fields.
- No PFF grades.
- No raw PFF rows, raw PFF IDs, source-native IDs, local PFF paths, or player-level PFF artifacts committed.
- Output artifact is aggregate only.

## File Structure

Create:

- `src/dynasty_genius/eval/te_regularization_bakeoff.py`
  - Bake-off evaluator.
  - Reuses `build_te_bakeoff_frame` and `_with_unified_penalty`.
  - Iterates over the alpha grid and candidates.
  - Computes RMSE, MAE, Spearman, Kendall, candidate coefficients, and acceptance gates.

- `scripts/run_te_regularization_bakeoff.py`
  - CLI/report builder.
  - Writes `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`.

- `tests/test_te_regularization_bakeoff.py`
  - Unit and contract tests.

- `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`
  - Generated aggregate artifact.

Modify:

- `AGENT_SYNC.md`
- `docs/agent-ledger/2026-05-16.md`

Do not modify:

- `src/dynasty_genius/models/engine_b_contract.py`
- `scripts/train_engine_b.py`
- `scripts/assemble_engine_b_dataset.py`
- `app/data/models/engine_b/v2_manifest.json`
- Any `.pkl` model artifact.

---

### Task 1: Bake-Off Evaluator

**Files:**
- Create: `src/dynasty_genius/eval/te_regularization_bakeoff.py`
- Test: `tests/test_te_regularization_bakeoff.py`

- [ ] **Step 1: Write failing evaluator tests**

Create `tests/test_te_regularization_bakeoff.py`:

```python
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.eval.te_regularization_bakeoff import (
    ALPHA_GRID,
    evaluate_te_regularization_bakeoff,
)


def _synthetic_frame() -> pd.DataFrame:
    rows = []
    for season in [2019, 2020, 2021, 2022, 2023]:
        rows.extend(
            [
                {
                    "player_id": f"safe_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 25,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.13,
                    "yprr": 1.4,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.30,
                    "snap_share": 0.60,
                    "avg_ppg_t1_t2": 8.0,
                    "te_role_role_risk": 0,
                    "te_role_blocking_specialist": 0,
                },
                {
                    "player_id": f"risk_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 25,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.13,
                    "yprr": 1.4,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.30,
                    "snap_share": 0.60,
                    "avg_ppg_t1_t2": 3.0,
                    "te_role_role_risk": 1,
                    "te_role_blocking_specialist": 0,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_evaluate_te_regularization_bakeoff_is_validation_only():
    result = evaluate_te_regularization_bakeoff(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )

    assert result["experiment_name"] == "te_regularization_bakeoff"
    assert result["alpha_grid"] == list(ALPHA_GRID)
    assert "baseline_only" in result["results_by_alpha"]["1.0"]
    assert "unified_penalty" in result["results_by_alpha"]["100.0"]
    assert result["governance"]["model_features_changed"] is False
    assert result["governance"]["te_promotion_changed"] is False


def test_bakeoff_reports_deltas_vs_baseline_alpha_1():
    result = evaluate_te_regularization_bakeoff(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )
    
    # Check a specific alpha result
    res_100 = result["results_by_alpha"]["100.0"]["unified_penalty"]
    assert "rmse_delta_vs_baseline_a1" in res_100["summary"]
    assert "mae_delta_vs_baseline_a1" in res_100["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_regularization_bakeoff.py
```

Expected: FAIL with missing `src.dynasty_genius.eval.te_regularization_bakeoff`.

- [ ] **Step 3: Implement evaluator**

Create `src/dynasty_genius/eval/te_regularization_bakeoff.py`:

```python
"""TE regularization bake-off evaluator for Phase 13.3.4."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.dynasty_genius.eval.te_role_risk_experiment import (
    ROLE_RISK_CANDIDATES,
    _evaluate_candidate,
    _with_unified_penalty,
)

ALPHA_GRID = (1.0, 10.0, 50.0, 100.0, 250.0, 500.0)

BAKEOFF_CANDIDATES = {
    "baseline_only": [],
    **ROLE_RISK_CANDIDATES,
}


def evaluate_te_regularization_bakeoff(
    frame: pd.DataFrame,
    *,
    test_years: list[int],
) -> dict[str, Any]:
    experiment_frame = _with_unified_penalty(frame)
    
    # First, compute the anchor baseline: alpha=1.0, baseline_only
    anchor_baseline = _evaluate_candidate(
        experiment_frame,
        candidate_name="baseline_only",
        candidate_columns=[],
        test_years=test_years,
        alpha=1.0,
    )
    # Compute absolute means from fold data (avoids KeyError on nonexistent summary keys)
    anchor_rmse = float(np.mean([fold["baseline_rmse"] for fold in anchor_baseline["folds"]]))
    anchor_mae = float(np.mean([fold["baseline_mae"] for fold in anchor_baseline["folds"]]))

    results_by_alpha: dict[str, dict[str, Any]] = {}
    for alpha in ALPHA_GRID:
        alpha_str = str(float(alpha))
        results_by_alpha[alpha_str] = {}
        for name, columns in BAKEOFF_CANDIDATES.items():
            res = _evaluate_candidate(
                experiment_frame,
                candidate_name=name,
                candidate_columns=list(columns),
                test_years=test_years,
                alpha=alpha,
            )
            # Compute absolute means for this cell to calculate deltas vs anchor baseline
            cell_rmse = float(np.mean([fold["candidate_rmse"] for fold in res["folds"]]))
            cell_mae = float(np.mean([fold["candidate_mae"] for fold in res["folds"]]))
            res["summary"]["rmse_delta_vs_baseline_a1"] = round(cell_rmse - anchor_rmse, 4)
            res["summary"]["mae_delta_vs_baseline_a1"] = round(cell_mae - anchor_mae, 4)
            results_by_alpha[alpha_str][name] = res

    return {
        "experiment_name": "te_regularization_bakeoff",
        "alpha_grid": list(ALPHA_GRID),
        "anchor_baseline_alpha": 1.0,
        "results_by_alpha": results_by_alpha,
        "governance": {
            "diagnostic_only": True,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
            "pff_grades_used": False,
            "player_level_rows_emitted": False,
        },
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_regularization_bakeoff.py
```

Expected: tests pass.

---

### Task 2: Bake-Off CLI And Artifact

**Files:**
- Create: `scripts/run_te_regularization_bakeoff.py`
- Modify: `tests/test_te_regularization_bakeoff.py`
- Create: `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`

- [ ] **Step 1: Add failing CLI/report contract test**

Append to `tests/test_te_regularization_bakeoff.py`:

```python
import json
from pathlib import Path

from scripts.run_te_regularization_bakeoff import build_regularization_report


def test_real_bakeoff_report_is_aggregate_redacted_and_governed(tmp_path: Path):
    out = tmp_path / "regularization_bakeoff.json"

    report = build_regularization_report(
        training_path=Path("app/data/training/engine_b_features_v2.csv"),
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        out_path=out,
        run_id="te_reg_bakeoff_test",
        generated_at="2026-05-16T16:30:00Z",
    )

    assert out.exists()
    assert report["metadata"]["position"] == "TE"
    assert "100.0" in report["result"]["results_by_alpha"]
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered
    assert "grades_offense" not in rendered
    assert "grades_pass_route" not in rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_regularization_bakeoff.py::test_real_bakeoff_report_is_aggregate_redacted_and_governed
```

Expected: FAIL with missing `scripts.run_te_regularization_bakeoff`.

- [ ] **Step 3: Implement CLI/report builder**

Create `scripts/run_te_regularization_bakeoff.py`:

```python
#!/usr/bin/env python3
"""Run the Phase 13.3.4 TE regularization bake-off."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval.te_archetype_bakeoff import build_te_bakeoff_frame  # noqa: E402
from src.dynasty_genius.eval.te_archetype_bakeoff import BASELINE_TE_FEATURES  # noqa: E402
from src.dynasty_genius.eval.te_regularization_bakeoff import (  # noqa: E402
    evaluate_te_regularization_bakeoff,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path)["eligible"])


def build_regularization_report(
    *,
    training_path: Path,
    archetype_path: Path,
    eligible_path: Path,
    out_path: Path,
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    training = pd.read_csv(training_path)
    te_training = training[training["position"] == "TE"].copy()
    archetype_artifact = _load_json(archetype_path)
    eligible_rows = _load_eligible(eligible_path)
    frame = build_te_bakeoff_frame(te_training, archetype_artifact, eligible_rows=eligible_rows)
    result = evaluate_te_regularization_bakeoff(frame, test_years=[2020, 2021, 2022, 2023])
    report = {
        "metadata": {
            "schema_version": "0.1.0",
            "run_id": run_id,
            "generated_at": generated_at or _utc_timestamp(),
            "position": "TE",
            "source_training": training_path.as_posix(),
            "source_archetype_artifact": archetype_path.as_posix(),
            "source_eligible_manifest": eligible_path.as_posix(),
            "baseline_features": list(BASELINE_TE_FEATURES),
            "ridge_alpha": PRIMARY_ALPHA,
            "alpha_grid": list(ALPHA_GRID),
            "eligible_count": int(archetype_artifact["metadata"]["eligible_count"]),
            "te_training_rows": int(len(te_training)),
            "test_years": [2020, 2021, 2022, 2023],
        },
        "result": result,

        "decision_policy": {
            "production_change_approved": False,
            "te_status": "EXPERIMENTAL",
            "next_step": "Review artifact to determine whether stronger alpha + role-risk justifies a spec.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE regularization bake-off.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_reg_bakeoff_20260516")
    args = parser.parse_args(argv)
    report = build_regularization_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
    )
    print(f"TE regularization bake-off written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_regularization_bakeoff.py
```

Expected: tests pass.

- [ ] **Step 5: Generate real artifact**

Run:

```bash
.venv/bin/python3.14 scripts/run_te_regularization_bakeoff.py \
  --training app/data/training/engine_b_features_v2.csv \
  --archetype app/data/identity/te_archetype_rubric_20260516.json \
  --eligible-manifest app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json \
  --out app/data/backtest/phase13/te_regularization_bakeoff_20260516.json \
  --run-id te_reg_bakeoff_20260516
```

Expected: report writes to JSON.

- [ ] **Step 6: Run redaction scan**

Run:

```bash
rg -n "pff_id|sleeper_id|gsis_id|/Users|Downloads|overall_grade|receiving_grade|run_block_grade|pass_block_grade|grades_offense|grades_pass_route" app/data/backtest/phase13/te_regularization_bakeoff_20260516.json
```


Expected: no output and exit code 1.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/dynasty_genius/eval/te_regularization_bakeoff.py scripts/run_te_regularization_bakeoff.py tests/test_te_regularization_bakeoff.py app/data/backtest/phase13/te_regularization_bakeoff_20260516.json
git commit -m "feat(phase13): run TE regularization bake-off"
```

---

### Task 3: Sync, Ledger, And Verification

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-16.md`

- [ ] **Step 1: Update AGENT_SYNC**

Add under Phase 13.3:

```md
- Task 13.3.4 COMPLETE: TE regularization bake-off artifact at `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`.
    - Tested alpha grid (1.0 to 500.0) across baseline, unified-penalty, and sparse-duo candidates.
    - Result identifies whether stronger regularization preserves rank stability while retaining error improvement.
    - Validation-only: no production Engine B contract changes, model artifact promotion, TE promotion, PVO scoring change, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
```

- [ ] **Step 2: Update daily ledger**

Append:

```md
## HH:MM ET - Codex

- Task: Implement Phase 13.3.4 TE regularization bake-off.
- Governance read: docs/governance/02-agent-operating-loop.md, docs/governance/00-product-constitution.md, docs/governance/01-north-star-architecture.md, AGENT_SYNC.md, daily ledger, 13.3.4 decision note.
- Active phase / surface: Phase 13.3 TE Remodel regularization bake-off.
- Intended or completed write scope: TE regularization evaluator, CLI, aggregate artifact, tests, AGENT_SYNC, daily ledger.
- Files changed: `src/dynasty_genius/eval/te_regularization_bakeoff.py`, `scripts/run_te_regularization_bakeoff.py`, `tests/test_te_regularization_bakeoff.py`, `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`, `AGENT_SYNC.md`, `docs/agent-ledger/2026-05-16.md`.
- Tests / checks: Focused tests, redaction scan, full suite.
- Product alignment: Validation-only. No production Engine B contract changes, promoted model artifacts, TE promotion, PVO scoring changes, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
- Handoff / next step: Review artifact and determine if a production model-change spec is justified.
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_regularization_bakeoff.py tests/test_te_role_risk_experiment.py tests/test_te_archetype_bakeoff.py tests/test_te_archetype_taxonomy.py
```

Expected: all pass.

- [ ] **Step 4: Run full suite**

Run:

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: all pass.

- [ ] **Step 5: Commit final docs**

Run:

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-16.md
git commit -m "docs(phase13): close TE regularization bake-off validation"
```

- [ ] **Step 6: Push**

Run:

```bash
git push
```

Expected: branch pushes cleanly.

---

## Acceptance Criteria

Task 13.3.4 is complete only if:

- `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json` exists.
- The artifact reports aggregate metrics for all requested alpha/candidate pairs.
- Every candidate/alpha pair includes fold-level deltas vs. baseline alpha 1.0.
- Governance flags match 13.3.3 constraints.
- Redaction scan finds no source-native IDs or private data.
- No production model contract, manifest, or pickle is changed.
- Focused tests pass.
- Full suite passes.

## Explicit Non-Acceptance

- the experiment writes a `.pkl`;
- the experiment edits `engine_b_contract.py`;
- the experiment edits `v2_manifest.json`;
- the report contains source-native IDs or player-level rows;
- market data appears in any input or output.
