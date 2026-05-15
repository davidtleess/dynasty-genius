---
document: Phase 12 — Operational Artifacts + Trust Surface v2
version: 1.0.0
status: APPROVED
date: 2026-05-15
author: Claude Code
governance_read:
  - docs/governance/02-agent-operating-loop.md v1.0.0
  - docs/governance/00-product-constitution.md v1.0.0
  - docs/governance/01-north-star-architecture.md v1.0.0
phase_sequence_position: 12
prior_phase: "Phase 10/11 — Backtest Harness (PR #27, merged 91c91d1)"
research_brief: "docs/strategies/Phase 12 Research Brief - Merged.md"
---

# Phase 12 — Operational Artifacts + Trust Surface v2

## 0. Why This Phase Exists

Phase 10/11 built the validation infrastructure. Phase 12 makes it speak.

The backtest harness currently exists as working code with 479 passing tests. The Trust Surface route returns JSON. But `app/data/backtest/runs/` is empty, every `GET /trust-surface/{position}` returns 404, and `dynasty_value_score` is `None` on every PVO. The system has a trust layer that has not yet produced any evidence.

Phase 12 closes that gap in strict sequence:

1. Run the harness operationally — generate the first versioned artifacts for QB, RB, WR, and TE.
2. Extend the artifact schema to include per-fold prediction logs, calibration reports, subgroup slices, and a market-comparison ledger.
3. Generate Model Cards per position (Mitchell et al., 2018 schema).
4. Extend Trust Surface v2 to serve model cards alongside the raw BacktestResult.
5. Build a passive divergence ledger v0 (model rank vs. market rank, no signal claim yet).
6. Document every artifact in `docs/ARTIFACTS.md`.

**What Phase 12 does not do:**
- It does not implement `dynasty_value_score`. That field remains `None`. The calibration data produced here is the prerequisite for the DVS spec, which requires David's review and a separate approval.
- It does not retrain any model or touch any feature column.
- It does not promote any position to `DECISION_GRADE`.
- It does not touch `NOISE_BAND` or any Phase 9 market overlay logic.

---

## 1. Scope

### 1.1 In Scope

- Task 12.0: Operational first backtest run — `run_backtest.py --all`, artifacts on disk, Trust Surface unblocked
- Task 12.1: `ModelCard` Pydantic schema + `save()` / `load()` methods + contract tests
- Task 12.2: `CalibrationReport` schema — per-decile ECE, extended calibration data beyond the existing `calibration_by_decile` list; subgroup slice computation (age buckets, draft-capital buckets)
- Task 12.3: Per-fold prediction log — player-level `(player_id, fold_index, feature_season, predicted_ppg, realized_ppg, model_rank, residual, age)` saved per run
- Task 12.4: Market-comparison ledger — player-level `(player_id, fold_index, model_rank, fc_rank, realized_rank)` saved per run
- Task 12.5: Model card generation script — `scripts/generate_model_cards.py` reads latest BacktestResult artifacts, populates all 9 Mitchell sections, writes to `app/data/backtest/model_cards/`
- Task 12.6: Trust Surface v2 route expansion — new `GET /trust-surface/{position}/model-card` endpoint; `experimental` boolean hoisted to main route response
- Task 12.7: Divergence ledger v0 — passive JSON storage of model-vs-market disagreement rows; `scripts/build_divergence_ledger.py`
- Task 12.8: `docs/ARTIFACTS.md` — every artifact, location, schema, and which gate it informs

### 1.2 Deferred

| Item | Reason |
|---|---|
| `dynasty_value_score` implementation | Requires Act 1 artifact review + David's spec approval. Field stays `None`. |
| `within_position_percentile` field | Conditional on DVS spec approval. Not in Phase 12. |
| TE model retraining | Phase 13 after diagnosis artifacts confirm failure mode |
| RB feature expansion (WO, HVT) | Requires Phase 12 baseline metrics to make the test measurable |
| Divergence validity signal (G4 execution) | Requires ~6 months native FC snapshots |
| `DECISION_GRADE` promotion | Requires G4 |
| 2024 fold extension | Requires confirming 2025 PPG outcome data is settled in the CSV — verify before implementing; treat as optional in Task 12.0 |
| Trust Surface HTML frontend | Frontend is last per constitution |

### 1.3 Hard Constraints

- No market data enters Engine B training, imputation, scaling, or feature columns at any point.
- No production model artifact is retrained, replaced, or modified in this phase. The harness refits Ridge within each fold by design — that is the intended backtest evaluation behavior, not a constraint violation.
- All artifacts are immutable once written. The Trust Surface route reads files only — no recomputation on the read path.
- `dynasty_value_score` stays `None` on all PVO objects. Do not populate it.
- TE remains `EXPERIMENTAL` regardless of what Phase 12 artifacts show. Only a re-run through the promotion gate after TE remodeling can change that.
- `NOISE_BAND=0.10` is locked until mid-July 2026.

---

## 2. New File Map

```
src/dynasty_genius/eval/
    model_card.py               ← NEW: ModelCard + CalibrationReport Pydantic schemas
    backtest_report.py          ← NEW: FoldPredictionLog, MarketComparisonEntry schemas

scripts/
    generate_model_cards.py     ← NEW: reads BacktestResult → writes ModelCard JSON
    build_divergence_ledger.py  ← NEW: joins predictions + market snapshots → ledger JSON

app/api/routes/
    trust_surface.py            ← UPDATED: /model-card sub-route + experimental flag

app/data/backtest/
    runs/{run_id}/
        backtest_result_{POS}.json     ← existing (Phase 10/11)
        predictions_{POS}.csv          ← NEW: per-fold player-level prediction log
        market_comparison_{POS}.json   ← NEW: per-fold player-level market comparison
    model_cards/
        QB_model_card.json             ← NEW: generated model card
        RB_model_card.json
        WR_model_card.json
        TE_model_card.json
    divergence_ledger_{POS}.json       ← NEW: passive model-vs-market rows

docs/
    ARTIFACTS.md                ← NEW: artifact index

tests/
    test_model_card.py          ← NEW
    test_backtest_report.py     ← NEW
    contract/
        test_trust_surface_v2.py ← UPDATED: model-card endpoint + experimental flag tests
```

---

## 3. Pydantic Schemas

### 3.1 ModelCard (`src/dynasty_genius/eval/model_card.py`)

```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import json


class ModelCardMetrics(BaseModel):
    rmse_mean: float
    rmse_per_fold: List[float]
    kendall_tau_mean: float
    kendall_tau_per_fold: List[float]
    spearman_rho_mean: float
    spearman_rho_per_fold: List[float]
    ece: Optional[float] = None                 # Expected Calibration Error; None until computed
    ndcg_at_24_model_mean: Optional[float] = None
    ndcg_at_24_market_mean: Optional[float] = None
    g1_pass: bool
    g2_pass: bool
    g3_pass: Any                                # bool | "deferred"
    g4_pass: Any                                # bool | "deferred" | "insufficient_data"
    overall_grade: str


class ModelCardSubgroup(BaseModel):
    label: str                                  # e.g. "age_under_26", "round_1_pick"
    n: int
    rmse: float
    kendall_tau: float
    note: Optional[str] = None


class ModelCard(BaseModel):
    """Mitchell et al. (2018) model card schema — 9 sections."""
    schema_version: str = "1.0.0"
    generated_at: datetime
    position: Literal["QB", "RB", "WR", "TE"]
    backtest_run_id: str                        # UUID of the source BacktestResult
    git_sha: Optional[str] = None

    # Section 1: Model Details
    model_version: str                          # "engine_b_v2"
    model_artifact_hash: str
    ridge_alpha: float
    training_window: str                        # "2018–2023 (expanding; 4 folds)"
    feature_list: List[str]
    retrain_mode: str

    # Section 2: Intended Use
    intended_use: str                           # filled by generator; position-specific
    out_of_scope_uses: List[str]

    # Section 3: Factors
    relevant_factors: List[str]                 # ["position", "age", "sample_size", "draft_capital"]
    evaluation_factors: List[str]

    # Section 4: Metrics
    metrics: ModelCardMetrics

    # Section 5: Evaluation Data
    evaluation_data: str                        # fold table as string

    # Section 6: Training Data
    training_data: str

    # Section 7: Quantitative Analyses
    subgroup_results: List[ModelCardSubgroup]

    # Section 8: Ethical Considerations
    ethical_considerations: str

    # Section 9: Caveats and Recommendations
    caveats: List[str]
    known_failure_modes: List[str]
    is_experimental: bool

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "ModelCard":
        return cls.model_validate_json(path.read_text())
```

### 3.2 CalibrationReport (`src/dynasty_genius/eval/model_card.py`)

```python
class CalibrationDecile(BaseModel):
    decile: int                                 # 1–10 (1 = lowest predicted PPG)
    predicted_mean: float
    observed_mean: float
    n: int
    residual_mean: float                        # observed - predicted


class CalibrationReport(BaseModel):
    """Per-position calibration summary across all 4 folds (pooled)."""
    position: str
    backtest_run_id: str
    ece: float                                  # Expected Calibration Error = mean |predicted_mean - observed_mean| weighted by n
    deciles: List[CalibrationDecile]            # length 10
    note: Optional[str] = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))
```

### 3.3 FoldPredictionLog (`src/dynasty_genius/eval/backtest_report.py`)

The prediction log is written as CSV (not JSON) for ease of analysis in pandas/Excel.

```
player_id, position, fold_index, feature_season, predicted_ppg, realized_ppg,
model_rank, residual, age_at_feature_season, draft_round
```

One row per player per fold. Written to `app/data/backtest/runs/{run_id}/predictions_{POSITION}.csv`.

### 3.4 MarketComparisonEntry (`src/dynasty_genius/eval/backtest_report.py`)

```python
class MarketComparisonEntry(BaseModel):
    player_id: str
    sleeper_id: Optional[str]
    position: str
    fold_index: int
    feature_season: int
    snapshot_date: str                          # "YYYY-MM-DD"
    predicted_ppg: float
    model_rank: int
    fc_value: Optional[int] = None
    fc_rank: Optional[int] = None
    realized_ppg: Optional[float] = None
    realized_rank: Optional[int] = None
    rank_delta: Optional[int] = None           # model_rank - fc_rank; positive = model ranked higher
```

Written to `app/data/backtest/runs/{run_id}/market_comparison_{POSITION}.json` as a JSON array.

### 3.5 DivergenceLedgerEntry (`src/dynasty_genius/eval/backtest_report.py`)

```python
class DivergenceLedgerEntry(BaseModel):
    player_id: str
    sleeper_id: Optional[str]
    position: str
    feature_season: int
    engine_b_pred_ppg: float
    engine_b_rank: int
    fc_value: Optional[int]
    fc_rank: Optional[int]
    snapshot_date: Optional[str]
    realized_avg_ppg_t1_t2: Optional[float]
    realized_rank: Optional[int]
    rank_delta: Optional[int]                  # engine_b_rank - fc_rank
    flagged_direction: Optional[str]           # "model_higher" | "model_lower" | None
```

Written to `app/data/backtest/divergence_ledger_{POSITION}.json` as a JSON array.

---

## 4. WalkForwardDriver Extensions

The `WalkForwardDriver.run()` signature gains optional parameters to emit the new artifacts. Market store and id_map are already supported from Phase 10/11; the new parameters control additional output:

```python
def run(
    self,
    market_store: Optional[MarketSnapshotStore] = None,
    id_map: Optional[dict[str, str]] = None,
    emit_prediction_log: bool = False,          # NEW: write predictions CSV when True
    emit_market_comparison: bool = False,       # NEW: write market comparison JSON when True
) -> BacktestResult:
```

When `emit_prediction_log=True`, after each fold the driver appends rows to an in-memory list. After `run()` completes, the driver exposes `prediction_rows: list[dict]` as an attribute (not on BacktestResult — kept separate to avoid schema bloat). The CLI script writes the CSV.

When `emit_market_comparison=True`, the driver exposes `market_comparison_rows: list[dict]` similarly.

**Calibration deciles** — already present in `FoldResult.calibration_by_decile`. Phase 12 adds ECE computation in `backtest_metrics.py` and pools deciles across all folds in `generate_model_cards.py` to produce the `CalibrationReport`.

**Subgroup slices** — computed in `generate_model_cards.py` by joining the prediction log CSV back to the feature CSV on `player_id` + `feature_season`, then bucketing by age and draft_round.

Age buckets: `under_26`, `age_26_to_28`, `age_29_plus`.
Draft-capital buckets: `round_1`, `round_2`, `round_3_plus`, `undrafted`.

---

## 5. Statistical Function Additions (`backtest_metrics.py`)

### 5.1 Expected Calibration Error

```python
def compute_ece(
    calibration_deciles: list[tuple[float, float, int]],
    # Each tuple: (predicted_mean, observed_mean, n)
) -> float:
    """
    ECE = sum(n_i / N * |predicted_mean_i - observed_mean_i|) across deciles.
    Returns nan if list is empty or total n = 0.
    """
```

### 5.2 Subgroup Rank Correlation

```python
def compute_subgroup_metrics(
    predicted: list[float],
    realized: list[float],
) -> dict[str, float]:
    """
    Returns {"kendall_tau": ..., "spearman_rho": ..., "rmse": ..., "n": ...}.
    Returns all-None if n < 5 (too small for meaningful correlation).
    """
```

---

## 6. Model Card Generator (`scripts/generate_model_cards.py`)

```bash
.venv/bin/python3.14 scripts/generate_model_cards.py --position WR
.venv/bin/python3.14 scripts/generate_model_cards.py --all
```

The script:
1. Loads the latest `BacktestResult` for the position from `app/data/backtest/runs/`
2. Loads the corresponding `predictions_{POSITION}.csv` from the same run directory
3. Joins predictions to `app/data/training/engine_b_features_v2.csv` on `player_id` + `feature_season` to get `age_at_feature_season` and `draft_round`
4. Computes subgroup slices per age bucket and draft-capital bucket
5. Pools calibration deciles across folds; computes ECE
6. Populates all 9 ModelCard sections using position-specific templates (see Section 6.1)
7. Writes `app/data/backtest/model_cards/{POSITION}_model_card.json`
8. Writes `app/data/backtest/model_cards/{POSITION}_calibration_report.json`

### 6.1 Position-Specific Card Templates

Pre-defined strings for Sections 2, 8, 9 (not computed — authored):

**QB:**
- *Intended use:* "Forecast 2-year average PPG for active NFL quarterbacks. Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
- *Out-of-scope:* ["Single-season redraft start/sit decisions", "Keeper cap valuations without manager review", "TE scoring (TE model is EXPERIMENTAL)"]
- *Ethical considerations:* "Decision aid only. Market overlay (FantasyCalc) is a post-scoring reference — it is not a training input and must not be treated as ground truth. Model outputs carry uncertainty bands that must be exposed to end users."
- *Caveats:* ["Sample size: ~43–49 QB rows per fold. Folds involving roster turnover years (e.g., 2020 COVID) carry elevated noise.", "Mobile QB rushing floors depreciate sharply after age 33. Model does not encode a hard cliff — age is a continuous feature — but predictions near this threshold carry higher uncertainty.", "Superflex format premiums are not modeled directly. Value-above-replacement comparisons across positions require a separate normalization layer (deferred to DVS spec)."]
- *Known failure modes:* ["Injury-year outliers distort PPG labels for players who missed significant games. The model has no games-played filter in v2.", "Historical regime shifts (2020 COVID, rules changes) can widen fold-to-fold RMSE."]

**RB:**
- *Intended use:* "Forecast 2-year average PPG for active NFL running backs. Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
- *Out-of-scope:* Same as QB.
- *Caveats:* ["RB age cliff begins ~26. The model encodes age as a continuous feature; users should interpret high-confidence predictions for players ≥26 with increased skepticism.", "Role volatility (committee backfields, mid-season usage shifts) creates floor risk not captured in PPG-based training labels.", "Weighted Opportunity and High-Value Touches are not yet in the feature set. Current features rely on PPG and snap-share proxies. See Phase 13 research brief."]
- *Known failure modes:* ["Low-snap, high-efficiency backs on poor offenses may be undervalued by a PPG-trained label.", "Committee backs show high variance that PPG smooths over."]

**WR:**
- *Intended use:* "Forecast 2-year average PPG for active NFL wide receivers. Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
- *Caveats:* ["Age cliff begins ~29. WR prime window is broad (25–29), making mid-career predictions most reliable.", "Quarterback volatility (team changes, QB injuries) creates landing-spot risk that YPRR-adjacent features cannot capture in a pure efficiency model."]
- *Known failure modes:* ["Slot vs. outside receiver distinctions are not explicitly modeled. A slot receiver moving to a vertical role will be mispredicted until the new role PPG accumulates."]

**TE:**
- *Intended use:* "EXPERIMENTAL — not for trade decisions. Diagnostic only."
- *is_experimental:* True
- *Caveats:* ["TE model failed Phase 10/11 promotion gates (0/3). Alpha=1.0 indicates severe overfitting; model cannot beat a naive prior-PPG baseline.", "Role heterogeneity (inline blocker vs. receiving specialist) is not segmented. A single model trained on mixed archetypes cannot capture either reliably.", "Sample size is the tightest of any position: ~30–35 TE starters per fold."]
- *Known failure modes:* ["TD variance dominates short-window PPG, making calibration unstable. The model's calibration_by_decile will show large residuals.", "Draft capital selects for inline blockers who have zero fantasy utility. Model trained on overall_rank overweights pick number for non-fantasy TEs."]

---

## 7. Trust Surface v2 Route (`app/api/routes/trust_surface.py`)

### 7.1 Existing Route — Additions

`GET /trust-surface/{position}` — no breaking change. Additions to the response:
- `experimental: bool` hoisted to top level (already derivable from `promotion_gate.overall_grade` but now explicit)
- `model_card_available: bool` — True if the model card file exists on disk

```python
data["experimental"] = (result.promotion_gate.overall_grade == "EXPERIMENTAL")
data["model_card_available"] = (MODEL_CARDS_DIR / f"{pos_upper}_model_card.json").exists()
```

### 7.2 New Route

```python
MODEL_CARDS_DIR = Path("app/data/backtest/model_cards")

@router.get("/{position}/model-card")
async def get_model_card(position: str) -> dict[str, Any]:
    """
    Returns the latest ModelCard JSON for the position.
    404 if model card has not been generated yet.
    Read-only. No recomputation.
    """
    pos_upper = position.upper()
    if pos_upper not in _VALID_POSITIONS:
        raise HTTPException(status_code=404, detail=f"Unknown position: {pos_upper}")
    card_path = MODEL_CARDS_DIR / f"{pos_upper}_model_card.json"
    if not card_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No model card found for position {pos_upper}. Run scripts/generate_model_cards.py first."
        )
    return ModelCard.load(card_path).model_dump(mode="json")
```

---

## 8. Divergence Ledger Script (`scripts/build_divergence_ledger.py`)

```bash
.venv/bin/python3.14 scripts/build_divergence_ledger.py --position WR
.venv/bin/python3.14 scripts/build_divergence_ledger.py --all
```

The script:
1. Loads the latest BacktestResult for the position
2. Loads `market_comparison_{POSITION}.json` from the same run directory
3. For each MarketComparisonEntry where both `model_rank` and `fc_rank` are not None:
   - Computes `rank_delta = model_rank - fc_rank`
   - Sets `flagged_direction = "model_higher"` if delta > 0, `"model_lower"` if delta < 0, else None
4. Writes `app/data/backtest/divergence_ledger_{POSITION}.json`
5. Prints a summary: n_entries, n_model_higher, n_model_lower, n_unmatched

**Critical constraint:** This script is read-only relative to model training. It joins artifacts that already exist. It does not compute any new predictions, does not call any model, and does not write to fc_snapshots.db.

---

## 9. ARTIFACTS.md (`docs/ARTIFACTS.md`)

```markdown
# Dynasty Genius — Artifact Index

All artifacts are immutable once written. The Trust Surface serves them read-only.
No artifact should be hand-edited. To regenerate, re-run the relevant script.

## Backtest Run Artifacts

Location: `app/data/backtest/runs/{run_id}/`

| File | Schema | Generated by | Gate |
|---|---|---|---|
| `backtest_result_{POS}.json` | `BacktestResult` (Pydantic) | `scripts/run_backtest.py` | G1–G4 |
| `predictions_{POS}.csv` | columns: player_id, position, fold_index, feature_season, predicted_ppg, realized_ppg, model_rank, residual, age_at_feature_season, draft_round | `scripts/run_backtest.py --emit-logs` | G1 calibration substrate |
| `market_comparison_{POS}.json` | `list[MarketComparisonEntry]` | `scripts/run_backtest.py --emit-market` | G3 |

## Model Card Artifacts

Location: `app/data/backtest/model_cards/`

| File | Schema | Generated by | Gate |
|---|---|---|---|
| `{POS}_model_card.json` | `ModelCard` (Pydantic, Mitchell 9-section) | `scripts/generate_model_cards.py` | All gates summarized |
| `{POS}_calibration_report.json` | `CalibrationReport` (Pydantic) | `scripts/generate_model_cards.py` | G2 calibration |

## Divergence Ledger

Location: `app/data/backtest/`

| File | Schema | Generated by | Gate |
|---|---|---|---|
| `divergence_ledger_{POS}.json` | `list[DivergenceLedgerEntry]` | `scripts/build_divergence_ledger.py` | G4 substrate |

## Market Snapshot Store

Location: `app/data/fc_snapshots.db` (gitignored)

SQLite. Schema in Phase 10/11 spec §2.3. Written by `scripts/snapshot_fantasycalc.py` (daily)
and `scripts/ingest_market_archive.py` (one-time backfill).
```

---

## 10. TDD Task Sequence

All tasks: write RED test → implement GREEN → full suite passes → commit. No exceptions.

---

### Task 12.0 — Operational First Run

**No new code.** This is an operational verification task.

`scripts/run_backtest.py` defines `ACTIVE_POSITIONS = ("QB", "RB", "WR")`. `--all` runs those three only. Run TE separately in EXPERIMENTAL mode:

```bash
.venv/bin/python3.14 scripts/run_backtest.py --all
.venv/bin/python3.14 scripts/run_backtest.py --position TE
```

**Verification checklist (manual, before proceeding to Task 12.1):**
1. `app/data/backtest/runs/{run_id}/` exists with `backtest_result_QB.json`, `backtest_result_RB.json`, `backtest_result_WR.json`
2. Each file deserializes to `BacktestResult` without validation errors
3. `GET /trust-surface/WR` returns 200 (not 404)
4. `GET /trust-surface/QB` returns 200
5. `GET /trust-surface/RB` returns 200
6. `result.promotion_gate.overall_grade` is `"ACTIVE_B"` or better for QB/RB/WR (not `"PRE_MODEL"`)
7. TE: `backtest_result_TE.json` exists with `overall_grade == "EXPERIMENTAL"` — required for Phase 12 failure diagnosis
8. `market_source` is `"unavailable"` (expected — no archive ingested yet)

**2024 fold:** Check whether `feature_season == 2024` rows in `engine_b_features_v2.csv` have `training_eligible = True` and non-null `avg_ppg_t1_t2`. Document the finding in the commit message. Adding a 2024 fold requires harness code changes — document and defer to a separate approved task; do not add code in Task 12.0.

**Commit message:** `ops(phase12): first operational backtest run — artifacts on disk, Trust Surface unblocked`

---

### Task 12.1 — ModelCard + CalibrationReport Schemas

**Files:** `src/dynasty_genius/eval/model_card.py`, `tests/test_model_card.py`

RED tests (write first):

```python
# test_model_card.py

def test_model_card_validates_all_9_sections():
    """A fully populated ModelCard validates without error."""

def test_model_card_save_and_load_round_trips(tmp_path):
    """save() then load() produces identical card."""

def test_model_card_is_experimental_flag_true_for_te():
    """is_experimental must be True when position == "TE"."""

def test_model_card_is_experimental_flag_false_for_wr():
    """is_experimental must be False for non-TE positions that pass gates."""

def test_calibration_report_ece_computation():
    """ECE = weighted mean of |predicted_mean - observed_mean| across deciles."""

def test_calibration_report_save_and_load_round_trips(tmp_path):
    """save() then load() produces identical report."""

def test_model_card_subgroup_results_allow_empty_list():
    """subgroup_results may be empty (e.g., missing age column in CSV)."""
```

Implement `ModelCard`, `CalibrationReport`, `ModelCardMetrics`, `ModelCardSubgroup`, `CalibrationDecile` per Section 3.1–3.2. All models use Pydantic v2.

**Commit:** `feat(phase12): ModelCard + CalibrationReport schemas (task 12.1)`

---

### Task 12.2 — ECE Metric + Subgroup Metric Functions

**Files:** `src/dynasty_genius/eval/backtest_metrics.py`, `tests/test_backtest_metrics.py` (extend)

RED tests:

```python
def test_compute_ece_perfect_calibration():
    """When predicted_mean == observed_mean for all deciles, ECE == 0.0."""

def test_compute_ece_known_case():
    """Manual calculation: 3 equal-n deciles, known |diff| → known ECE."""

def test_compute_ece_returns_nan_on_empty_input():
    """Empty list → nan, not exception."""

def test_compute_subgroup_metrics_returns_all_keys():
    """Returns dict with keys: kendall_tau, spearman_rho, rmse, n."""

def test_compute_subgroup_metrics_returns_nones_below_min_n():
    """n < 5 → all metric values are None."""
```

Implement `compute_ece()` and `compute_subgroup_metrics()` per Section 5.

**Commit:** `feat(phase12): ECE + subgroup metric functions (task 12.2)`

---

### Task 12.3 — Per-Fold Prediction Log

**Files:** `src/dynasty_genius/eval/backtest_report.py`, `src/dynasty_genius/eval/backtest_harness.py` (update `run()`), `tests/test_backtest_report.py`

RED tests:

```python
def test_emit_prediction_log_produces_rows(tmp_path):
    """run(emit_prediction_log=True) exposes driver.prediction_rows as a non-empty list."""

def test_prediction_rows_have_required_keys():
    """Each row has: player_id, fold_index, feature_season, predicted_ppg, realized_ppg, model_rank, residual."""

def test_prediction_rows_residual_equals_realized_minus_predicted():
    """residual = realized_ppg - predicted_ppg for every row."""

def test_prediction_log_has_no_future_data_in_train_rows():
    """All rows in prediction_rows come from the test fold only (feature_season == test_year)."""

def test_prediction_csv_writes_correctly(tmp_path):
    """CSV written from prediction_rows is readable by pandas with correct dtypes."""
```

In `WalkForwardDriver.run()`, add `emit_prediction_log` parameter. After each fold, append test-fold rows to `self._prediction_rows`. Expose as `self.prediction_rows` after the loop. Do not store on `BacktestResult`.

Update `scripts/run_backtest.py` to pass `emit_prediction_log=True` and write the CSV artifact.

**Commit:** `feat(phase12): per-fold prediction log (task 12.3)`

---

### Task 12.4 — Market-Comparison Ledger

**Files:** `src/dynasty_genius/eval/backtest_report.py` (add `MarketComparisonEntry`), `src/dynasty_genius/eval/backtest_harness.py` (update `run()`), `tests/test_backtest_report.py` (extend)

RED tests:

```python
def test_emit_market_comparison_with_empty_store_produces_no_rows(tmp_path):
    """run(market_store=empty_store, emit_market_comparison=True) → driver.market_comparison_rows == []."""

def test_emit_market_comparison_with_populated_store_produces_rows(tmp_path):
    """With synthetic market rows, market_comparison_rows is non-empty."""

def test_market_comparison_entry_rank_delta_is_model_minus_fc():
    """rank_delta = model_rank - fc_rank. Positive = model ranked player higher."""

def test_market_comparison_unmatched_players_have_null_fc_fields():
    """Players with no sleeper_id match have fc_value=None, fc_rank=None."""

def test_market_comparison_json_serializes(tmp_path):
    """List of MarketComparisonEntry serializes to valid JSON."""
```

Update `scripts/run_backtest.py` to pass `emit_market_comparison=True` and write `market_comparison_{POSITION}.json`.

**Commit:** `feat(phase12): market-comparison ledger (task 12.4)`

---

### Task 12.5 — Model Card Generation Script

**Files:** `scripts/generate_model_cards.py`, `tests/test_model_card.py` (extend)

RED tests:

```python
def test_generate_model_card_reads_backtest_result(tmp_path):
    """Script reads BacktestResult artifact and produces a ModelCard without error."""

def test_generate_model_card_populates_metrics_from_result(tmp_path):
    """ModelCard.metrics.kendall_tau_mean matches mean of FoldResult.kendall_tau values."""

def test_generate_model_card_te_sets_is_experimental_true(tmp_path):
    """TE card always has is_experimental=True regardless of gate result."""

def test_generate_model_card_ece_requires_prediction_log(tmp_path):
    """If predictions CSV is missing, ece = None (no crash)."""

def test_generate_model_card_writes_calibration_report(tmp_path):
    """CalibrationReport JSON is written alongside ModelCard JSON."""

def test_generate_all_writes_four_cards(tmp_path):
    """--all writes one card per position (QB, RB, WR, TE)."""
```

The script fails gracefully (logs warning, skips subgroups) if the prediction log CSV is missing from the run directory. All 9 ModelCard sections must be populated.

**Commit:** `feat(phase12): model card generation script (task 12.5)`

---

### Task 12.6 — Trust Surface v2 Route

**Files:** `app/api/routes/trust_surface.py`, `tests/contract/test_trust_surface_v2.py`

RED tests (new file — do not modify existing `test_trust_surface_route.py`):

```python
def test_get_trust_surface_includes_experimental_flag_false_for_wr(mock_runs_dir):
    """`experimental` is False for non-TE positions that pass G1+G2."""

def test_get_trust_surface_includes_experimental_flag_true_for_te(mock_runs_dir):
    """`experimental` is True when overall_grade == "EXPERIMENTAL"."""

def test_get_trust_surface_includes_model_card_available_false_when_no_card(mock_runs_dir):
    """`model_card_available` is False when no card file exists."""

def test_get_trust_surface_includes_model_card_available_true_when_card_exists(mock_runs_dir, mock_cards_dir):
    """`model_card_available` is True when the card file exists."""

def test_get_model_card_404_when_no_card(mock_cards_dir):
    """`GET /trust-surface/WR/model-card` returns 404 when no card."""

def test_get_model_card_200_returns_valid_model_card(mock_cards_dir):
    """Returns 200 with all 9 ModelCard sections in response."""

def test_get_model_card_is_experimental_at_top_level(mock_cards_dir):
    """`is_experimental` is present at top level of response."""

def test_get_model_card_invalid_position_404(mock_cards_dir):
    """Unknown position (e.g., K) returns 404."""
```

Existing `test_trust_surface_route.py` tests must still pass after this change.

**Commit:** `feat(phase12): Trust Surface v2 — model-card endpoint + experimental flag (task 12.6)`

---

### Task 12.7 — Divergence Ledger v0

**Files:** `scripts/build_divergence_ledger.py`, `src/dynasty_genius/eval/backtest_report.py` (add `DivergenceLedgerEntry`), `tests/test_backtest_report.py` (extend)

RED tests:

```python
def test_build_divergence_ledger_requires_backtest_result(tmp_path):
    """Script raises FileNotFoundError if no BacktestResult exists."""

def test_build_divergence_ledger_with_no_market_comparison_produces_empty_ledger(tmp_path):
    """With no market_comparison JSON, ledger has zero entries."""

def test_divergence_ledger_entry_flagged_direction_model_higher():
    """rank_delta > 0 (model ranked player higher than FC) → flagged_direction == 'model_higher'."""

def test_divergence_ledger_entry_flagged_direction_none_for_zero_delta():
    """rank_delta == 0 → flagged_direction == None."""

def test_build_divergence_ledger_writes_json(tmp_path):
    """Output file is valid JSON deserializable to list[DivergenceLedgerEntry]."""
```

**Commit:** `feat(phase12): divergence ledger v0 (task 12.7)`

---

### Task 12.8 — ARTIFACTS.md + AGENT_SYNC Update

**Files:** `docs/ARTIFACTS.md` (new), `AGENT_SYNC.md` (update), `docs/agent-ledger/2026-05-15.md` (append)

1. Write `docs/ARTIFACTS.md` per Section 9 of this spec.
2. Update `AGENT_SYNC.md`: active phase → Phase 12 complete; test count; next recommended work.
3. Append ledger entry to `docs/agent-ledger/2026-05-15.md`.

**No tests for documentation files.** Verify `ARTIFACTS.md` links to real paths.

**Commit:** `docs(phase12): ARTIFACTS.md + AGENT_SYNC + ledger (task 12.8)`

---

## 11. Acceptance Criteria

### Act 1 — Phase 12 Complete

- [ ] `app/data/backtest/runs/{run_id}/backtest_result_{QB,RB,WR}.json` exist and validate
- [ ] `GET /trust-surface/QB`, `/RB`, `/WR` return 200
- [ ] Each response includes `overall_grade`, `experimental`, `model_card_available`
- [ ] TE artifact exists (experimental) OR TE is explicitly excluded with documented reason
- [ ] `predictions_{QB,RB,WR}.csv` exist in run directory
- [ ] `market_comparison_{QB,RB,WR}.json` exist in run directory (may be empty lists)
- [ ] `{QB,RB,WR,TE}_model_card.json` exist in `app/data/backtest/model_cards/`
- [ ] TE model card has `is_experimental=True` and `known_failure_modes` populated
- [ ] `{QB,RB,WR,TE}_calibration_report.json` exist
- [ ] `GET /trust-surface/{pos}/model-card` returns 200 for QB/RB/WR
- [ ] `divergence_ledger_{QB,RB,WR}.json` exist (may be empty if no market data)
- [ ] `docs/ARTIFACTS.md` exists and describes every file above
- [ ] `dynasty_value_score` is `None` on all PVO objects — not populated
- [ ] All existing tests continue to pass
- [ ] New tests pass: ≥ 30 new tests across Tasks 12.1–12.7

### Gate: Act 2 Readiness (post-Phase 12 review — not Phase 12 acceptance)

After artifacts are generated and reviewed, David evaluates:
- CalibrationReport ECE per position: is predicted-decile mean approximately tracking observed-decile mean?
- Kendall τ-b per fold: do QB/RB/WR meet G1 thresholds?
- TE failure mode: is the diagnosis in the model card specific enough to scope a remodel?

If calibration diagnostics are satisfactory and David approves, the DVS spec can be written. That spec is Phase 13 or Phase 12 Act 2 — David decides.

---

## 12. Test Strategy

| Layer | What to test |
|---|---|
| **Unit** | ModelCard/CalibrationReport schema validation; ECE computation; subgroup metric functions; DivergenceLedgerEntry field logic |
| **Integration** | End-to-end: `run_backtest.py --all` produces artifacts + `generate_model_cards.py --all` produces cards → Trust Surface returns 200 for all cards |
| **Contract** | Trust Surface v2 response shape; new `experimental` and `model_card_available` fields; model-card endpoint 200/404 behavior |
| **Property** | CalibrationReport deciles length == 10; ECE ≥ 0; ModelCard serializes deterministically |
| **Golden** | Lock BacktestResult structure so schema changes are detected |

---

## 13. Hard Constraints Checklist (before any PR)

- [ ] `dynasty_value_score` is `None` everywhere — grep for any assignment
- [ ] No market field in `_compute_X` functions that touch training data
- [ ] No new features added to Engine B CSV or training pipeline
- [ ] BacktestResult artifacts not modified after write (no patch scripts)
- [ ] Trust Surface routes are read-only — no computation triggered on GET
- [ ] TE `overall_grade` cannot be promoted by any code path in this phase

---

## 14. Open Data Questions (resolve at Task 12.0)

1. **2024 fold:** Does `engine_b_features_v2.csv` have `feature_season == 2024` rows with `training_eligible = True` and non-null `avg_ppg_t1_t2`? If yes, add fold 5. If no, document and skip.
2. **Market archive:** Have any community KTC/FC CSV archives been ingested into `fc_snapshots.db`? If not, `market_comparison` artifacts will be empty — that is acceptable and expected. Document in ARTIFACTS.md.
3. **TE in `--all`:** Should `run_backtest.py --all` include TE? The harness runs TE in EXPERIMENTAL mode. Recommended: include TE so the failure diagnosis is documented in the first artifact run.

---

## 15. Deferred Items

| Item | Reason | Review trigger |
|---|---|---|
| `dynasty_value_score` / `within_position_percentile` | Requires Act 1 review + separate spec approval | After Phase 12 artifacts reviewed |
| DVS isotonic calibration pipeline | Requires calibration diagnostic data from this phase | DVS spec approval |
| TE remodel / archetype clustering | Phase 12 model card documents the failure; remodel is Phase 13 | After TE diagnosis confirmed |
| RB Weighted Opportunity + HVT features | Phase 12 baseline makes the feature gate measurable | Phase 13 after baseline established |
| G4 divergence validity signal | Requires ~6 months native FC snapshots | ~Q4 2026 |
| Trust Surface HTML frontend | Frontend is last per constitution | After DECISION_GRADE earned |
| NOISE_BAND calibration | Locked at 0.10 | Mid-July 2026 |
