# Phase 13.3.2 TE Archetype Feature Bake-Off Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether a two-axis TE archetype taxonomy improves held-out TE prediction quality over the current Engine B TE baseline without changing production model features or promoting TE.

**Architecture:** Add a validation-only taxonomy layer derived from the committed redacted Phase 13.3.1 artifact, then run an offline TE-only bake-off against the existing walk-forward prediction/training setup. The bake-off emits immutable aggregate reports under `app/data/identity/` or `app/data/backtest/phase13/`; it never writes promoted model artifacts, never touches Engine A/B production feature contracts, and never uses market data or PFF grades.

**Tech Stack:** Python 3.14, stdlib `json/csv/dataclasses/pathlib`, pandas/numpy/sklearn already used by the backtest harness, pytest.

---

## Current Evidence

Inputs already committed:

- `app/data/identity/te_archetype_rubric_20260516.json`
- `app/data/identity/te_archetype_validation_20260516.json`
- `docs/validation/phase13-te-human-archetype-review.md`
- `app/data/training/engine_b_features_v2.csv`
- `app/data/backtest/runs/25f9697d-f155-49e2-a6c7-384b7cec51c1/predictions_TE.csv`

Observed diagnostic signal:

| Comparison | Current Result |
|---|---:|
| Receiving-leaning minus blocking-leaning realized PPG mean | +3.6453 |
| Receiving-leaning minus blocking-leaning residual mean | +1.5922 |
| Receiving-leaning minus blocking-leaning positive residual rate | +0.3662 |

Human review conclusion:

- `receiving_leaning` is an alignment label, not a fantasy receiving-utility label.
- `ambiguous` mixes complete TEs with unclear role players.
- Task 13.3.2 must test a two-axis taxonomy, not directly consume the single Step 0 label.

## Governance Constraints

Hard constraints:

- No Engine A or Engine B production feature contract changes.
- No promoted model artifact writes.
- No TE promotion; TE remains `EXPERIMENTAL`.
- No market data.
- No PFF grades.
- No raw PFF rows, raw PFF IDs, source-native IDs, or local paths in committed artifacts.
- No player-level prediction rows in committed output unless separately approved.
- Any candidate lift is validation evidence only until David approves a later model-change spec.

## File Structure

Create:

- `src/dynasty_genius/audit/te_archetype_taxonomy.py`
  - Pure functions that convert the Step 0 rubric row into validation-only taxonomy candidates.
  - No file I/O.

- `src/dynasty_genius/eval/te_archetype_bakeoff.py`
  - Offline TE-only bake-off utilities.
  - Builds candidate feature frames, runs fold evaluation, computes deltas against baseline.
  - Does not import market stores or production model services.

- `scripts/run_te_archetype_bakeoff.py`
  - CLI that reads existing artifacts and writes an aggregate report.

- `tests/test_te_archetype_taxonomy.py`
  - Unit tests for candidate taxonomy labels and human-review conflict cases.

- `tests/test_te_archetype_bakeoff.py`
  - Validation-only bake-off tests with synthetic data and a real artifact contract test.

- `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`
  - Generated aggregate report if the real run succeeds.

Modify:

- `AGENT_SYNC.md`
  - Mark Task 13.3.2 as validation-only complete after implementation.

- `docs/agent-ledger/2026-05-16.md`
  - Add session entries.

Do not modify:

- `src/dynasty_genius/models/engine_b_contract.py`
- `scripts/train_engine_b.py`
- `scripts/assemble_engine_b_dataset.py`
- `app/data/models/engine_b/v2_manifest.json`
- Any promoted model pickle.

---

### Task 1: Two-Axis TE Taxonomy Module

**Files:**
- Create: `src/dynasty_genius/audit/te_archetype_taxonomy.py`
- Test: `tests/test_te_archetype_taxonomy.py`

- [ ] **Step 1: Write failing taxonomy tests**

Create `tests/test_te_archetype_taxonomy.py`:

```python
from __future__ import annotations

from src.dynasty_genius.audit.te_archetype_taxonomy import (
    classify_alignment_archetype,
    classify_fantasy_role_archetype,
    derive_te_taxonomy_features,
)


def _row(**overrides):
    base = {
        "player_id": "te_test",
        "labeling_status": "labeled",
        "archetype": "ambiguous",
        "coverage_status": "pff_alignment_available",
        "detached_rate_from_snaps": 0.33,
        "inline_rate_from_snaps": 0.67,
        "alignment_snap_total": 240.0,
        "routes": 210.0,
        "yprr_computed": 2.2,
        "tprr_computed": 0.21,
    }
    base.update(overrides)
    return base


def test_alignment_archetype_separates_detached_balanced_inline():
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.50, inline_rate_from_snaps=0.50)) == "detached"
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67)) == "balanced"
    assert classify_alignment_archetype(_row(detached_rate_from_snaps=0.20, inline_rate_from_snaps=0.80)) == "inline"


def test_complete_te_requires_balanced_alignment_and_receiving_utility():
    row = _row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67, yprr_computed=2.2, tprr_computed=0.21)

    assert classify_fantasy_role_archetype(row) == "complete_te"


def test_receiving_specialist_requires_detached_alignment_and_receiving_utility():
    row = _row(detached_rate_from_snaps=0.55, inline_rate_from_snaps=0.45, yprr_computed=2.0, tprr_computed=0.22)

    assert classify_fantasy_role_archetype(row) == "receiving_specialist"


def test_detached_low_efficiency_becomes_role_risk_not_receiving_specialist():
    row = _row(detached_rate_from_snaps=0.54, inline_rate_from_snaps=0.46, yprr_computed=1.16, tprr_computed=0.11)

    assert classify_fantasy_role_archetype(row) == "role_risk"


def test_inline_low_efficiency_becomes_blocking_specialist():
    row = _row(detached_rate_from_snaps=0.33, inline_rate_from_snaps=0.67, yprr_computed=1.2, tprr_computed=0.12)

    assert classify_fantasy_role_archetype(row) == "blocking_specialist"


def test_null_status_rows_remain_unlabeled():
    row = _row(labeling_status="excluded", archetype=None, detached_rate_from_snaps=None, inline_rate_from_snaps=None)

    features = derive_te_taxonomy_features(row)

    assert features["alignment_archetype"] is None
    assert features["fantasy_role_archetype"] is None
    assert features["taxonomy_status"] == "unavailable"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_taxonomy.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.dynasty_genius.audit.te_archetype_taxonomy'`.

- [ ] **Step 3: Implement the pure taxonomy module**

Create `src/dynasty_genius/audit/te_archetype_taxonomy.py`:

```python
"""Validation-only TE taxonomy features for Phase 13.3.2."""
from __future__ import annotations

from typing import Any

TAXONOMY_VERSION = "0.1.0"

DETACHED_ALIGNMENT_MIN = 0.40
INLINE_ALIGNMENT_MIN = 0.70
BALANCED_INLINE_MIN = 0.55
BALANCED_INLINE_MAX = 0.70
RECEIVING_YPRR_MIN = 1.80
RECEIVING_TPRR_MIN = 0.18
ROLE_RISK_YPRR_MAX = 1.40
ROLE_RISK_TPRR_MAX = 0.16


def _num(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _has_receiving_utility(row: dict[str, Any]) -> bool:
    yprr = _num(row.get("yprr_computed"))
    tprr = _num(row.get("tprr_computed"))
    return (
        yprr is not None
        and tprr is not None
        and yprr >= RECEIVING_YPRR_MIN
        and tprr >= RECEIVING_TPRR_MIN
    )


def _has_low_receiving_utility(row: dict[str, Any]) -> bool:
    yprr = _num(row.get("yprr_computed"))
    tprr = _num(row.get("tprr_computed"))
    return (
        yprr is not None
        and tprr is not None
        and yprr <= ROLE_RISK_YPRR_MAX
        and tprr <= ROLE_RISK_TPRR_MAX
    )


def classify_alignment_archetype(row: dict[str, Any]) -> str | None:
    detached = _num(row.get("detached_rate_from_snaps"))
    inline = _num(row.get("inline_rate_from_snaps"))
    if detached is None or inline is None:
        return None
    if detached >= DETACHED_ALIGNMENT_MIN and inline < BALANCED_INLINE_MIN:
        return "detached"
    if inline >= INLINE_ALIGNMENT_MIN:
        return "inline"
    return "balanced"


def classify_fantasy_role_archetype(row: dict[str, Any]) -> str | None:
    if row.get("labeling_status") != "labeled":
        return None
    alignment = classify_alignment_archetype(row)
    has_receiving_utility = _has_receiving_utility(row)
    has_low_receiving_utility = _has_low_receiving_utility(row)
    if alignment == "detached" and has_receiving_utility:
        return "receiving_specialist"
    if alignment == "detached" and has_low_receiving_utility:
        return "role_risk"
    if alignment == "balanced" and has_receiving_utility:
        return "complete_te"
    if alignment in {"balanced", "inline"} and has_low_receiving_utility:
        return "blocking_specialist"
    if alignment == "inline":
        return "blocking_specialist"
    return "unclear_role"


def derive_te_taxonomy_features(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("labeling_status") != "labeled":
        return {
            "alignment_archetype": None,
            "fantasy_role_archetype": None,
            "taxonomy_status": "unavailable",
            "taxonomy_version": TAXONOMY_VERSION,
        }
    return {
        "alignment_archetype": classify_alignment_archetype(row),
        "fantasy_role_archetype": classify_fantasy_role_archetype(row),
        "taxonomy_status": "labeled",
        "taxonomy_version": TAXONOMY_VERSION,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_taxonomy.py
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/dynasty_genius/audit/te_archetype_taxonomy.py tests/test_te_archetype_taxonomy.py
git commit -m "feat(phase13): add validation-only TE taxonomy candidates"
```

---

### Task 2: Bake-Off Feature Frame Builder

**Files:**
- Modify: `src/dynasty_genius/eval/te_archetype_bakeoff.py`
- Test: `tests/test_te_archetype_bakeoff.py`

- [ ] **Step 1: Write failing tests for redacted feature joining**

Create `tests/test_te_archetype_bakeoff.py`:

```python
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.eval.te_archetype_bakeoff import build_te_bakeoff_frame


def _archetype_artifact():
    return {
        "players": {
            "te_a": {
                "player_id": "te_a",
                "labeling_status": "labeled",
                "archetype": "ambiguous",
                "coverage_status": "pff_alignment_available",
                "detached_rate_from_snaps": 0.33,
                "inline_rate_from_snaps": 0.67,
                "alignment_snap_total": 240.0,
                "routes": 210.0,
                "yprr_computed": 2.2,
                "tprr_computed": 0.21,
            },
            "te_b": {
                "player_id": "te_b",
                "labeling_status": "labeled",
                "archetype": "receiving_leaning",
                "coverage_status": "pff_alignment_available",
                "detached_rate_from_snaps": 0.54,
                "inline_rate_from_snaps": 0.46,
                "alignment_snap_total": 260.0,
                "routes": 220.0,
                "yprr_computed": 1.1,
                "tprr_computed": 0.11,
            },
        }
    }


def test_build_frame_joins_taxonomy_by_canonical_player_id_without_source_ids():
    training = pd.DataFrame(
        [
            {"player_id": "00-a", "position": "TE", "feature_season": 2021, "avg_ppg_t1_t2": 9.0, "training_eligible": True},
            {"player_id": "00-b", "position": "TE", "feature_season": 2021, "avg_ppg_t1_t2": 4.0, "training_eligible": True},
            {"player_id": "00-x", "position": "TE", "feature_season": 2021, "avg_ppg_t1_t2": 6.0, "training_eligible": True},
        ]
    )
    eligible_rows = [
        {"player_id": "te_a", "gsis_id": "00-a"},
        {"player_id": "te_b", "gsis_id": "00-b"},
    ]

    frame = build_te_bakeoff_frame(training, _archetype_artifact(), eligible_rows=eligible_rows)

    assert frame.shape[0] == 3
    assert "gsis_id" not in frame.columns
    assert "pff_id" not in frame.columns
    assert "fantasy_role_archetype" in frame.columns
    assert frame.loc[frame["player_id"] == "00-a", "fantasy_role_archetype"].item() == "complete_te"
    assert frame.loc[frame["player_id"] == "00-b", "fantasy_role_archetype"].item() == "role_risk"
    assert frame.loc[frame["player_id"] == "00-x", "fantasy_role_archetype"].item() == "taxonomy_missing"


def test_build_frame_adds_one_hot_candidate_columns():
    training = pd.DataFrame(
        [{"player_id": "00-a", "position": "TE", "feature_season": 2021, "avg_ppg_t1_t2": 9.0, "training_eligible": True}]
    )
    eligible_rows = [{"player_id": "te_a", "gsis_id": "00-a"}]

    frame = build_te_bakeoff_frame(training, _archetype_artifact(), eligible_rows=eligible_rows)

    assert frame["te_role_complete_te"].item() == 1
    assert frame["te_role_blocking_specialist"].item() == 0
    assert frame["te_align_balanced"].item() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_bakeoff.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.dynasty_genius.eval.te_archetype_bakeoff'`.

- [ ] **Step 3: Implement frame builder**

Create `src/dynasty_genius/eval/te_archetype_bakeoff.py` with:

```python
"""Offline TE archetype feature bake-off utilities for Phase 13.3.2."""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.dynasty_genius.audit.te_archetype_taxonomy import derive_te_taxonomy_features

ALIGNMENT_VALUES = ("detached", "balanced", "inline", "taxonomy_missing")
ROLE_VALUES = (
    "receiving_specialist",
    "complete_te",
    "blocking_specialist",
    "role_risk",
    "unclear_role",
    "taxonomy_missing",
)


def _canonical_by_gsis(eligible_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["gsis_id"]): str(row["player_id"])
        for row in eligible_rows
        if row.get("gsis_id") and row.get("player_id")
    }


def _taxonomy_by_canonical(archetype_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for player_id, row in archetype_artifact["players"].items():
        features = derive_te_taxonomy_features(row)
        if features["taxonomy_status"] == "labeled":
            out[player_id] = features
    return out


def build_te_bakeoff_frame(
    training: pd.DataFrame,
    archetype_artifact: dict[str, Any],
    *,
    eligible_rows: list[dict[str, Any]],
) -> pd.DataFrame:
    frame = training.copy()
    canonical_by_gsis = _canonical_by_gsis(eligible_rows)
    taxonomy_by_canonical = _taxonomy_by_canonical(archetype_artifact)

    alignments: list[str] = []
    roles: list[str] = []
    for gsis_player_id in frame["player_id"].astype(str):
        canonical = canonical_by_gsis.get(gsis_player_id)
        taxonomy = taxonomy_by_canonical.get(canonical or "")
        if taxonomy is None:
            alignments.append("taxonomy_missing")
            roles.append("taxonomy_missing")
            continue
        alignments.append(taxonomy["alignment_archetype"] or "taxonomy_missing")
        roles.append(taxonomy["fantasy_role_archetype"] or "taxonomy_missing")

    frame["alignment_archetype"] = alignments
    frame["fantasy_role_archetype"] = roles
    for value in ALIGNMENT_VALUES:
        frame[f"te_align_{value}"] = (frame["alignment_archetype"] == value).astype(int)
    for value in ROLE_VALUES:
        frame[f"te_role_{value}"] = (frame["fantasy_role_archetype"] == value).astype(int)
    return frame
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_taxonomy.py tests/test_te_archetype_bakeoff.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/dynasty_genius/eval/te_archetype_bakeoff.py tests/test_te_archetype_bakeoff.py
git commit -m "feat(phase13): build TE archetype bakeoff frame"
```

---

### Task 3: Offline Fold Evaluation

**Files:**
- Modify: `src/dynasty_genius/eval/te_archetype_bakeoff.py`
- Modify: `tests/test_te_archetype_bakeoff.py`

- [ ] **Step 1: Add failing tests for baseline vs taxonomy candidate evaluation**

Append to `tests/test_te_archetype_bakeoff.py`:

```python
from src.dynasty_genius.eval.te_archetype_bakeoff import evaluate_te_taxonomy_candidate


def test_evaluate_candidate_reports_metric_deltas_without_model_promotion():
    rows = []
    for season in [2019, 2020, 2021, 2022]:
        rows.extend(
            [
                {
                    "player_id": f"rec_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 24,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.12,
                    "yprr": 1.3,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.3,
                    "snap_share": 0.6,
                    "avg_ppg_t1_t2": 9.0,
                    "te_role_complete_te": 1,
                    "te_role_blocking_specialist": 0,
                    "te_role_role_risk": 0,
                },
                {
                    "player_id": f"block_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 24,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.12,
                    "yprr": 1.3,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.3,
                    "snap_share": 0.6,
                    "avg_ppg_t1_t2": 3.0,
                    "te_role_complete_te": 0,
                    "te_role_blocking_specialist": 1,
                    "te_role_role_risk": 0,
                },
            ]
        )
    frame = pd.DataFrame(rows)

    result = evaluate_te_taxonomy_candidate(
        frame,
        candidate_name="fantasy_role_one_hot",
        candidate_columns=["te_role_complete_te", "te_role_blocking_specialist", "te_role_role_risk"],
        test_years=[2021, 2022],
    )

    assert result["candidate_name"] == "fantasy_role_one_hot"
    assert result["model_features_changed"] is False
    assert result["te_promotion_changed"] is False
    assert result["market_data_used"] is False
    assert result["folds"][0]["baseline_rmse"] > result["folds"][0]["candidate_rmse"]
    assert result["summary"]["rmse_delta_mean"] < 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_bakeoff.py::test_evaluate_candidate_reports_metric_deltas_without_model_promotion
```

Expected: FAIL with `ImportError` or missing `evaluate_te_taxonomy_candidate`.

- [ ] **Step 3: Implement validation-only fold evaluation**

Append to `src/dynasty_genius/eval/te_archetype_bakeoff.py`:

```python
import math

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

BASELINE_TE_FEATURES = (
    "ppg_t",
    "games_t",
    "age",
    "route_participation",
    "target_share_nfl",
    "yprr",
    "tprr",
    "weighted_opportunity",
    "snap_share",
)
OUTCOME_COLUMN = "avg_ppg_t1_t2"


def _prepare_matrix(train: pd.DataFrame, test: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[columns])
    x_test = imputer.transform(test[columns])
    return scaler.fit_transform(x_train), scaler.transform(x_test)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _evaluate_columns(frame: pd.DataFrame, columns: list[str], test_year: int) -> dict[str, Any]:
    train = frame[(frame["feature_season"] < test_year) & (frame["training_eligible"] == True)]
    test = frame[(frame["feature_season"] == test_year) & (frame["training_eligible"] == True)]
    x_train, x_test = _prepare_matrix(train, test, columns)
    y_train = train[OUTCOME_COLUMN].to_numpy(dtype=float)
    y_test = test[OUTCOME_COLUMN].to_numpy(dtype=float)
    model = Ridge(alpha=1.0)
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    return {
        "test_year": test_year,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "rmse": _rmse(y_test, pred),
        "mae": float(mean_absolute_error(y_test, pred)),
    }


def evaluate_te_taxonomy_candidate(
    frame: pd.DataFrame,
    *,
    candidate_name: str,
    candidate_columns: list[str],
    test_years: list[int],
) -> dict[str, Any]:
    baseline_columns = [column for column in BASELINE_TE_FEATURES if column in frame.columns]
    full_columns = baseline_columns + candidate_columns
    folds: list[dict[str, Any]] = []
    for test_year in test_years:
        baseline = _evaluate_columns(frame, baseline_columns, test_year)
        candidate = _evaluate_columns(frame, full_columns, test_year)
        folds.append(
            {
                "test_year": test_year,
                "n_train": baseline["n_train"],
                "n_test": baseline["n_test"],
                "baseline_rmse": round(baseline["rmse"], 4),
                "candidate_rmse": round(candidate["rmse"], 4),
                "rmse_delta": round(candidate["rmse"] - baseline["rmse"], 4),
                "baseline_mae": round(baseline["mae"], 4),
                "candidate_mae": round(candidate["mae"], 4),
                "mae_delta": round(candidate["mae"] - baseline["mae"], 4),
            }
        )
    rmse_deltas = [fold["rmse_delta"] for fold in folds]
    mae_deltas = [fold["mae_delta"] for fold in folds]
    return {
        "candidate_name": candidate_name,
        "candidate_columns": candidate_columns,
        "folds": folds,
        "summary": {
            "rmse_delta_mean": round(float(np.mean(rmse_deltas)), 4),
            "mae_delta_mean": round(float(np.mean(mae_deltas)), 4),
            "improved_rmse_folds": int(sum(delta < 0 for delta in rmse_deltas)),
            "fold_count": len(folds),
        },
        "model_features_changed": False,
        "te_promotion_changed": False,
        "market_data_used": False,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_bakeoff.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/dynasty_genius/eval/te_archetype_bakeoff.py tests/test_te_archetype_bakeoff.py
git commit -m "feat(phase13): evaluate TE archetype bakeoff candidates"
```

---

### Task 4: CLI And Aggregate Report

**Files:**
- Create: `scripts/run_te_archetype_bakeoff.py`
- Modify: `tests/test_te_archetype_bakeoff.py`
- Create: `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`

- [ ] **Step 1: Add failing real-artifact contract test**

Append to `tests/test_te_archetype_bakeoff.py`:

```python
import json
from pathlib import Path

from scripts.run_te_archetype_bakeoff import build_bakeoff_report


def test_real_bakeoff_report_is_aggregate_redacted_and_governed(tmp_path: Path):
    out = tmp_path / "te_bakeoff.json"

    report = build_bakeoff_report(
        training_path=Path("app/data/training/engine_b_features_v2.csv"),
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        out_path=out,
        run_id="te_archetype_bakeoff_test",
        generated_at="2026-05-16T14:30:00Z",
    )

    assert out.exists()
    assert report["metadata"]["position"] == "TE"
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    assert report["governance"]["market_data_used"] is False
    assert report["governance"]["pff_grades_used"] is False
    assert set(report["candidates"]) == {
        "snap_alignment_one_hot",
        "fantasy_role_one_hot",
        "complete_te_detector",
        "role_risk_detector",
    }
    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_bakeoff.py::test_real_bakeoff_report_is_aggregate_redacted_and_governed
```

Expected: FAIL with missing `scripts.run_te_archetype_bakeoff`.

- [ ] **Step 3: Implement CLI/report builder**

Create `scripts/run_te_archetype_bakeoff.py`:

```python
#!/usr/bin/env python3
"""Run the Phase 13.3.2 TE archetype feature bake-off."""
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

from src.dynasty_genius.eval.te_archetype_bakeoff import (  # noqa: E402
    build_te_bakeoff_frame,
    evaluate_te_taxonomy_candidate,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path)["eligible"])


def build_bakeoff_report(
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
    test_years = [2020, 2021, 2022, 2023]
    candidates = {
        "snap_alignment_one_hot": ["te_align_detached", "te_align_balanced", "te_align_inline"],
        "fantasy_role_one_hot": [
            "te_role_receiving_specialist",
            "te_role_complete_te",
            "te_role_blocking_specialist",
            "te_role_role_risk",
            "te_role_unclear_role",
        ],
        "complete_te_detector": ["te_role_complete_te"],
        "role_risk_detector": ["te_role_role_risk", "te_role_blocking_specialist"],
    }
    results = {
        name: evaluate_te_taxonomy_candidate(
            frame,
            candidate_name=name,
            candidate_columns=columns,
            test_years=test_years,
        )
        for name, columns in candidates.items()
    }
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
            "test_years": test_years,
        },
        "candidates": results,
        "governance": {
            "diagnostic_only": True,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
            "pff_grades_used": False,
            "player_level_rows_emitted": False,
        },
        "decision_policy": {
            "acceptance": "Candidate must improve mean RMSE and MAE, improve RMSE in at least 3 of 4 folds, and pass redaction/governance checks before a later David-approved model-change spec.",
            "te_status": "TE remains EXPERIMENTAL regardless of this bake-off result.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE archetype bake-off.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_archetype_bakeoff_20260516")
    args = parser.parse_args(argv)
    report = build_bakeoff_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
    )
    print(f"TE archetype bake-off written: {args.out} candidates={len(report['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_bakeoff.py
```

Expected: all tests pass.

- [ ] **Step 5: Generate real report**

Run:

```bash
.venv/bin/python3.14 scripts/run_te_archetype_bakeoff.py \
  --training app/data/training/engine_b_features_v2.csv \
  --archetype app/data/identity/te_archetype_rubric_20260516.json \
  --eligible-manifest app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json \
  --out app/data/backtest/phase13/te_archetype_bakeoff_20260516.json \
  --run-id te_archetype_bakeoff_20260516
```

Expected: report is written with four candidate entries and aggregate metrics only.

- [ ] **Step 6: Run redaction scan**

Run:

```bash
rg -n "pff_id|sleeper_id|gsis_id|/Users|Downloads|overall_grade|receiving_grade|run_block_grade|pass_block_grade" app/data/backtest/phase13/te_archetype_bakeoff_20260516.json
```

Expected: no output and exit code 1.

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/run_te_archetype_bakeoff.py app/data/backtest/phase13/te_archetype_bakeoff_20260516.json tests/test_te_archetype_bakeoff.py
git commit -m "feat(phase13): run TE archetype feature bakeoff"
```

---

### Task 5: Documentation, Sync, And Final Verification

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-16.md`

- [ ] **Step 1: Update AGENT_SYNC**

Add this under the Phase 13 section after the 13.3 human calibration note:

```md
- Task 13.3.2 COMPLETE: TE Archetype Feature Bake-Off validation artifact at `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`.
    - Tested snap-alignment, two-axis fantasy-role taxonomy, complete-TE detector, and role-risk detector candidates.
    - Output is validation-only and aggregate-redacted. No Engine A/B production feature changes, model artifact promotion, TE promotion, market data, PFF grades, raw PFF rows, or player-level rows.
    - Result informs whether David should approve a later TE model-change spec; it does not itself change production scoring.
```

- [ ] **Step 2: Update daily ledger**

Append:

```md
## HH:MM ET - Codex

- Task: Implement Phase 13.3.2 TE archetype feature bake-off.
- Governance read: docs/governance/02-agent-operating-loop.md, docs/governance/00-product-constitution.md, docs/governance/01-north-star-architecture.md, AGENT_SYNC.md, daily ledger.
- Active phase / surface: Phase 13.3 TE Remodel validation.
- Intended or completed write scope: TE taxonomy module, bake-off evaluator, CLI, aggregate artifact, tests, AGENT_SYNC, daily ledger.
- Files changed: `src/dynasty_genius/audit/te_archetype_taxonomy.py`, `src/dynasty_genius/eval/te_archetype_bakeoff.py`, `scripts/run_te_archetype_bakeoff.py`, `tests/test_te_archetype_taxonomy.py`, `tests/test_te_archetype_bakeoff.py`, `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`, `AGENT_SYNC.md`, `docs/agent-ledger/2026-05-16.md`.
- Tests / checks: Focused taxonomy/bake-off tests; redaction scan; full suite.
- Product alignment: Validation-only. No Engine A/B production feature changes, model training artifact promotion, TE promotion, DVS, PFF grades, raw PFF data, player-level rows, or market data.
- Drift risks: If candidate lift is positive, it remains evidence for a later David-approved model-change spec, not an automatic production change.
- Handoff / next step: Review candidate deltas and decide whether to approve a TE model-change spec.
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
.venv/bin/python3.14 -m pytest -q tests/test_te_archetype_taxonomy.py tests/test_te_archetype_bakeoff.py tests/test_te_archetype_validation.py tests/test_te_archetype_rubric.py
```

Expected: all pass.

- [ ] **Step 4: Run full suite**

Run:

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: all pass, with the existing skipped tests unchanged.

- [ ] **Step 5: Commit final docs**

Run:

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-16.md
git commit -m "docs(phase13): close TE archetype bakeoff validation"
```

- [ ] **Step 6: Push branch**

Run:

```bash
git push
```

Expected: branch pushes cleanly.

---

## Acceptance Criteria

Task 13.3.2 is complete only if all are true:

- `te_archetype_bakeoff_20260516.json` exists and is aggregate-only.
- The report includes all four candidates:
  - `snap_alignment_one_hot`
  - `fantasy_role_one_hot`
  - `complete_te_detector`
  - `role_risk_detector`
- The report has governance flags:
  - `model_features_changed: false`
  - `te_promotion_changed: false`
  - `market_data_used: false`
  - `pff_grades_used: false`
  - `player_level_rows_emitted: false`
- Redaction scan finds no source-native IDs, local paths, PFF grade fields, or raw PFF content.
- Focused tests pass.
- Full suite passes.
- `AGENT_SYNC.md` and the daily ledger are updated.

## Explicit Non-Acceptance

Do not claim production lift if:

- the candidate improves only one fold;
- the candidate improves RMSE but worsens MAE materially;
- the report contains player-level rows;
- any source-native ID or local PFF path appears in committed output;
- any production Engine B feature contract is changed;
- TE promotion logic changes.

## Post-Implementation Review Question

After implementation, the review decision is:

> Does any taxonomy candidate improve TE held-out error enough to justify a later David-approved TE model-change spec?

The answer can be "no." A no-lift result is still a successful validation outcome.
