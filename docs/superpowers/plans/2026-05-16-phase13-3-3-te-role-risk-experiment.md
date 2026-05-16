# Phase 13.3.3 TE Role-Risk Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a controlled TE-only model-change experiment for the `role_risk_detector` family and determine whether it is strong enough to justify a later production model-change spec.

**Architecture:** Extend the Phase 13.3.2 validation path with a stricter TE-only experiment artifact. The experiment may fit fold-local Ridge models with baseline TE features plus only the approved role-risk feature family, then report RMSE, MAE, rank metrics, and acceptance gates. It must not alter production Engine B contracts, model artifacts, manifests, PVO scoring, decision surfaces, or TE promotion status.

**Tech Stack:** Python 3.14, pandas, numpy, sklearn Ridge, existing `src/dynasty_genius/eval/te_archetype_bakeoff.py`, pytest.

---

## Approved Source Decision

Decision note:

- `docs/validation/phase13-3-3-te-role-risk-decision.md`

Approved feature family:

- `te_role_risk`
- `te_blocking_specialist_or_role_risk`

This plan uses existing generated columns from `build_te_bakeoff_frame()`:

- `te_role_role_risk`
- `te_role_blocking_specialist`

Do not add broad role one-hot features to this experiment.

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

- `src/dynasty_genius/eval/te_role_risk_experiment.py`
  - Experiment-only evaluator.
  - Reuses `build_te_bakeoff_frame`.
  - Evaluates baseline vs role-risk candidate.
  - Computes RMSE, MAE, Spearman, Kendall, acceptance gates.

- `scripts/run_te_role_risk_experiment.py`
  - CLI/report builder.
  - Writes `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`.

- `tests/test_te_role_risk_experiment.py`
  - Unit and contract tests.

- `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`
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

### Task 1: Experiment Evaluator

**Files:**
- Create: `src/dynasty_genius/eval/te_role_risk_experiment.py`
- Test: `tests/test_te_role_risk_experiment.py`

- [ ] **Step 1: Write failing evaluator tests**

Create `tests/test_te_role_risk_experiment.py`:

```python
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.eval.te_role_risk_experiment import (
    ROLE_RISK_CANDIDATE_COLUMNS,
    evaluate_te_role_risk_experiment,
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


def test_evaluate_te_role_risk_experiment_is_validation_only():
    result = evaluate_te_role_risk_experiment(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )

    assert result["experiment_name"] == "te_role_risk_detector"
    assert result["candidate_columns"] == list(ROLE_RISK_CANDIDATE_COLUMNS)
    assert result["governance"]["model_features_changed"] is False
    assert result["governance"]["te_promotion_changed"] is False
    assert result["governance"]["market_data_used"] is False
    assert result["governance"]["pff_grades_used"] is False
    assert result["summary"]["rmse_delta_mean"] < 0
    assert result["summary"]["mae_delta_mean"] < 0


def test_acceptance_requires_error_improvement_and_no_rank_degradation():
    result = evaluate_te_role_risk_experiment(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )

    assert result["summary"]["rmse_win_folds"] >= 3
    assert result["summary"]["passes_acceptance"] is True
    assert result["acceptance"]["rmse_win_gate"] is True
    assert result["acceptance"]["mean_rmse_gate"] is True
    assert result["acceptance"]["mean_mae_gate"] is True
    assert result["acceptance"]["rank_degradation_gate"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_role_risk_experiment.py
```

Expected: FAIL with missing `src.dynasty_genius.eval.te_role_risk_experiment`.

- [ ] **Step 3: Implement evaluator**

Create `src/dynasty_genius/eval/te_role_risk_experiment.py`:

```python
"""Controlled TE role-risk detector experiment for Phase 13.3.3."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.eval.te_archetype_bakeoff import BASELINE_TE_FEATURES

OUTCOME_COLUMN = "avg_ppg_t1_t2"
ROLE_RISK_CANDIDATE_COLUMNS = (
    "te_role_role_risk",
    "te_role_blocking_specialist",
)


def _prepare_matrix(train: pd.DataFrame, test: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[columns])
    x_test = imputer.transform(test[columns])
    return scaler.fit_transform(x_train), scaler.transform(x_test)


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, columns: list[str]) -> np.ndarray:
    x_train, x_test = _prepare_matrix(train, test, columns)
    y_train = train[OUTCOME_COLUMN].to_numpy(dtype=float)
    model = Ridge(alpha=1.0)
    model.fit(x_train, y_train)
    return model.predict(x_test)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _rank_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    spearman = spearmanr(y_pred, y_true).statistic
    kendall = kendalltau(y_pred, y_true).statistic
    return {
        "spearman_rho": 0.0 if np.isnan(spearman) else round(float(spearman), 4),
        "kendall_tau": 0.0 if np.isnan(kendall) else round(float(kendall), 4),
    }


def _evaluate_fold(frame: pd.DataFrame, test_year: int, baseline_columns: list[str], candidate_columns: list[str]) -> dict[str, Any]:
    train = frame[(frame["feature_season"] < test_year) & (frame["training_eligible"] == True)]
    test = frame[(frame["feature_season"] == test_year) & (frame["training_eligible"] == True)]
    y_test = test[OUTCOME_COLUMN].to_numpy(dtype=float)
    baseline_pred = _fit_predict(train, test, baseline_columns)
    candidate_pred = _fit_predict(train, test, baseline_columns + candidate_columns)
    baseline_rank = _rank_metrics(y_test, baseline_pred)
    candidate_rank = _rank_metrics(y_test, candidate_pred)
    return {
        "test_year": test_year,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "baseline_rmse": round(_rmse(y_test, baseline_pred), 4),
        "candidate_rmse": round(_rmse(y_test, candidate_pred), 4),
        "baseline_mae": round(float(mean_absolute_error(y_test, baseline_pred)), 4),
        "candidate_mae": round(float(mean_absolute_error(y_test, candidate_pred)), 4),
        "baseline_spearman_rho": baseline_rank["spearman_rho"],
        "candidate_spearman_rho": candidate_rank["spearman_rho"],
        "baseline_kendall_tau": baseline_rank["kendall_tau"],
        "candidate_kendall_tau": candidate_rank["kendall_tau"],
    }


def evaluate_te_role_risk_experiment(
    frame: pd.DataFrame,
    *,
    test_years: list[int],
) -> dict[str, Any]:
    baseline_columns = [column for column in BASELINE_TE_FEATURES if column in frame.columns]
    candidate_columns = [column for column in ROLE_RISK_CANDIDATE_COLUMNS if column in frame.columns]
    folds = []
    for test_year in test_years:
        fold = _evaluate_fold(frame, test_year, baseline_columns, candidate_columns)
        fold["rmse_delta"] = round(fold["candidate_rmse"] - fold["baseline_rmse"], 4)
        fold["mae_delta"] = round(fold["candidate_mae"] - fold["baseline_mae"], 4)
        fold["spearman_delta"] = round(fold["candidate_spearman_rho"] - fold["baseline_spearman_rho"], 4)
        fold["kendall_delta"] = round(fold["candidate_kendall_tau"] - fold["baseline_kendall_tau"], 4)
        folds.append(fold)

    rmse_deltas = [fold["rmse_delta"] for fold in folds]
    mae_deltas = [fold["mae_delta"] for fold in folds]
    spearman_deltas = [fold["spearman_delta"] for fold in folds]
    kendall_deltas = [fold["kendall_delta"] for fold in folds]
    rmse_win_folds = sum(delta < 0 for delta in rmse_deltas)
    mean_rmse_gate = float(np.mean(rmse_deltas)) < 0
    mean_mae_gate = float(np.mean(mae_deltas)) < 0
    rmse_win_gate = rmse_win_folds >= 3
    rank_degradation_gate = min(spearman_deltas) >= -0.02 and min(kendall_deltas) >= -0.02
    acceptance = {
        "rmse_win_gate": rmse_win_gate,
        "mean_rmse_gate": mean_rmse_gate,
        "mean_mae_gate": mean_mae_gate,
        "rank_degradation_gate": rank_degradation_gate,
    }
    return {
        "experiment_name": "te_role_risk_detector",
        "candidate_columns": candidate_columns,
        "folds": folds,
        "summary": {
            "fold_count": len(folds),
            "rmse_win_folds": int(rmse_win_folds),
            "rmse_delta_mean": round(float(np.mean(rmse_deltas)), 4),
            "mae_delta_mean": round(float(np.mean(mae_deltas)), 4),
            "spearman_delta_mean": round(float(np.mean(spearman_deltas)), 4),
            "kendall_delta_mean": round(float(np.mean(kendall_deltas)), 4),
            "passes_acceptance": all(acceptance.values()),
        },
        "acceptance": acceptance,
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
.venv/bin/python3.14 -m pytest -q tests/test_te_role_risk_experiment.py
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/dynasty_genius/eval/te_role_risk_experiment.py tests/test_te_role_risk_experiment.py
git commit -m "feat(phase13): add TE role-risk experiment evaluator"
```

---

### Task 2: Experiment CLI And Artifact

**Files:**
- Create: `scripts/run_te_role_risk_experiment.py`
- Modify: `tests/test_te_role_risk_experiment.py`
- Create: `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`

- [ ] **Step 1: Add failing CLI/report contract test**

Append to `tests/test_te_role_risk_experiment.py`:

```python
import json
from pathlib import Path

from scripts.run_te_role_risk_experiment import build_role_risk_report


def test_real_role_risk_report_is_aggregate_redacted_and_governed(tmp_path: Path):
    out = tmp_path / "role_risk.json"

    report = build_role_risk_report(
        training_path=Path("app/data/training/engine_b_features_v2.csv"),
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        out_path=out,
        run_id="te_role_risk_experiment_test",
        generated_at="2026-05-16T15:30:00Z",
    )

    assert out.exists()
    assert report["metadata"]["position"] == "TE"
    assert report["result"]["experiment_name"] == "te_role_risk_detector"
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    assert report["governance"]["market_data_used"] is False
    assert report["governance"]["pff_grades_used"] is False
    assert report["decision"]["production_change_approved"] is False
    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_role_risk_experiment.py::test_real_role_risk_report_is_aggregate_redacted_and_governed
```

Expected: FAIL with missing `scripts.run_te_role_risk_experiment`.

- [ ] **Step 3: Implement CLI/report builder**

Create `scripts/run_te_role_risk_experiment.py`:

```python
#!/usr/bin/env python3
"""Run the Phase 13.3.3 TE role-risk controlled experiment."""
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
from src.dynasty_genius.eval.te_role_risk_experiment import (  # noqa: E402
    evaluate_te_role_risk_experiment,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path)["eligible"])


def build_role_risk_report(
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
    result = evaluate_te_role_risk_experiment(frame, test_years=[2020, 2021, 2022, 2023])
    report = {
        "metadata": {
            "schema_version": "0.1.0",
            "run_id": run_id,
            "generated_at": generated_at or _utc_timestamp(),
            "position": "TE",
            "source_training": training_path.as_posix(),
            "source_archetype_artifact": archetype_path.as_posix(),
            "eligible_count": int(archetype_artifact["metadata"]["eligible_count"]),
            "te_training_rows": int(len(te_training)),
            "test_years": [2020, 2021, 2022, 2023],
        },
        "result": result,
        "governance": result["governance"],
        "decision": {
            "production_change_approved": False,
            "te_status": "EXPERIMENTAL",
            "next_step": "If accepted, write a separate production model-change spec for David approval.",
        },
        "audit_caveats": [
            "Repo-relative source paths are provenance references and may become stale if files move.",
            "No production model artifact was written by this experiment.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE role-risk experiment.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_role_risk_experiment_20260516")
    args = parser.parse_args(argv)
    report = build_role_risk_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
    )
    accepted = report["result"]["summary"]["passes_acceptance"]
    print(f"TE role-risk experiment written: {args.out} accepted={accepted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_role_risk_experiment.py
```

Expected: tests pass.

- [ ] **Step 5: Generate real artifact**

Run:

```bash
.venv/bin/python3.14 scripts/run_te_role_risk_experiment.py \
  --training app/data/training/engine_b_features_v2.csv \
  --archetype app/data/identity/te_archetype_rubric_20260516.json \
  --eligible-manifest app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json \
  --out app/data/backtest/phase13/te_role_risk_experiment_20260516.json \
  --run-id te_role_risk_experiment_20260516
```

Expected: report writes and prints `accepted=true` or `accepted=False`.

- [ ] **Step 6: Redaction scan**

Run:

```bash
rg -n "pff_id|sleeper_id|gsis_id|/Users|Downloads|overall_grade|receiving_grade|run_block_grade|pass_block_grade" app/data/backtest/phase13/te_role_risk_experiment_20260516.json
```

Expected: no output and exit code 1.

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/run_te_role_risk_experiment.py tests/test_te_role_risk_experiment.py app/data/backtest/phase13/te_role_risk_experiment_20260516.json
git commit -m "feat(phase13): run TE role-risk controlled experiment"
```

---

### Task 3: Sync, Ledger, And Verification

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-16.md`

- [ ] **Step 1: Update AGENT_SYNC**

Add under Phase 13.3:

```md
- Task 13.3.3 COMPLETE: TE role-risk controlled experiment artifact at `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`.
    - Tested only the approved role-risk feature family: `te_role_role_risk` and `te_role_blocking_specialist`.
    - Validation-only: no production Engine B contract changes, model artifact promotion, TE promotion, PVO scoring change, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
    - Result determines whether to draft a later production model-change spec; it does not itself change scoring.
```

- [ ] **Step 2: Update daily ledger**

Append:

```md
## HH:MM ET - Codex

- Task: Implement Phase 13.3.3 TE role-risk controlled experiment.
- Governance read: docs/governance/02-agent-operating-loop.md, docs/governance/00-product-constitution.md, docs/governance/01-north-star-architecture.md, AGENT_SYNC.md, daily ledger, 13.3.3 decision note.
- Active phase / surface: Phase 13.3 TE Remodel controlled experiment.
- Intended or completed write scope: TE role-risk evaluator, CLI, aggregate artifact, tests, AGENT_SYNC, daily ledger.
- Files changed: `src/dynasty_genius/eval/te_role_risk_experiment.py`, `scripts/run_te_role_risk_experiment.py`, `tests/test_te_role_risk_experiment.py`, `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`, `AGENT_SYNC.md`, `docs/agent-ledger/2026-05-16.md`.
- Tests / checks: Focused tests, redaction scan, full suite.
- Product alignment: Controlled experiment only. No production Engine B contract changes, promoted model artifacts, TE promotion, PVO scoring changes, DVS, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
- Drift risks: Experiment artifact source paths are repo-relative provenance references and may become stale if files move.
- Handoff / next step: Review the experiment artifact and decide whether to draft a production model-change spec.
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_role_risk_experiment.py tests/test_te_archetype_bakeoff.py tests/test_te_archetype_taxonomy.py
```

Expected: all pass.

- [ ] **Step 4: Run full suite**

Run:

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: full suite passes with existing skips unchanged.

- [ ] **Step 5: Commit docs**

Run:

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-16.md
git commit -m "docs(phase13): close TE role-risk experiment"
```

- [ ] **Step 6: Push**

Run:

```bash
git push
```

Expected: branch pushes cleanly.

---

## Acceptance Criteria

Task 13.3.3 is complete only if:

- `app/data/backtest/phase13/te_role_risk_experiment_20260516.json` exists.
- The artifact reports:
  - fold-level RMSE/MAE deltas;
  - fold-level Spearman/Kendall deltas;
  - aggregate acceptance gates;
  - `production_change_approved: false`;
  - TE status remains `EXPERIMENTAL`.
- Redaction scan finds no source-native IDs, private paths, PFF grade fields, raw PFF content, or player-level rows.
- No production model contract, manifest, model pickle, PVO scoring, or TE promotion logic is changed.
- Focused tests pass.
- Full suite passes.

## Explicit Non-Acceptance

Do not mark this task complete if:

- the experiment writes a `.pkl`;
- the experiment edits `engine_b_contract.py`;
- the experiment edits `v2_manifest.json`;
- the report contains source-native IDs or player-level rows;
- TE status changes from `EXPERIMENTAL`;
- market data appears in any input or output;
- the feature is presented as production-ready without a separate David-approved model-change spec.

## Post-Implementation Decision

After implementation, the decision is:

> Does the controlled role-risk experiment justify drafting a production TE model-change spec?

A passing experiment is permission to write a spec, not permission to deploy.
