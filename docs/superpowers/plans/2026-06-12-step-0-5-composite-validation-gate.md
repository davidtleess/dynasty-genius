# Step 0.5 — Unified Composite Validation Gate (Engine B v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: this project uses the **cockpit TDD loop** (Codex authors RED tests → Claude makes them GREEN → Codex technical + Gemini governance dual-CLEAR → David-authorized commit → zero-divergence post-commit audit), NOT the superpowers subagent dispatch. Steps use checkbox (`- [ ]`) syntax for tracking. Route each task's RED and GREEN through the cockpit before the next.

**Goal:** Drive the Engine B walk-forward harness's model status from an explicit, conjunctive, validity-only composite gate (the recency-aware rule) instead of the current G3-coupled `overall_grade`, surfacing a quarantined `VALIDATED/PROVISIONAL/EXPERIMENTAL` status.

**Architecture:** Additive schema (`model_status` + validity-gate fields + `status_explanation` on `GateResult`; `overall_grade` kept public-but-deprecated). A new pure status function applies the recency-aware rule (all folds pass except the cold-start fold may be excused; most-recent fold must pass; per-fold Spearman-CI-width adequacy; null-coverage + leakage hard floors). G3 market-superiority is demoted to disclosed-only. The Trust Surface route surfaces `model_status` under the existing T9/T11 quarantine.

**Null-coverage v1 disclosure:** Engine B v1's `_build_fold_data` uses median imputation with `keep_empty_features=True`; it does not currently drop feature-null rows. Therefore real v1 folds are expected to report `null_coverage == 1.0` structurally. This step still wires the gate end-to-end so future row-dropping feature work is immediately governed, but reports must disclose that null coverage has no current-state bite under the imputing harness.

**Tech Stack:** Python 3.14, Pydantic v2, pytest (`.venv/bin/python3.14 -m pytest`). Spec: `docs/superpowers/specs/2026-06-12-step-0-5-composite-validation-gate-design.md`.

**Constants (spec §10, locked):** `SPEARMAN_THRESHOLD = 0.55`, `R2_FLOOR = 0.0`, `CI_WIDTH_MAX = 0.30`, `NULL_COVERAGE_MIN = 0.90`. `STATUS_VERSION = "0.5.0"`.

**Verified target outcome (current artifacts):** WR/RB/TE → `VALIDATED`, QB → `PROVISIONAL`.

**v2 cockpit corrections integrated:** F1 first-class validity fields on `GateResult`; F2 real null-coverage harness wiring + cross-component RED test; F3 reusable `build_mock_fold` / `build_mock_stability` helpers matching current gate-test shape; F4 real `/api/trust-surface/{position}` route + absent-or-false `decision_supported` contract + correct OpenAPI/client commands; F5-plan model-card propagation from the committed spec (`ModelCardMetrics.model_status`, generator wiring, tests).

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `src/dynasty_genius/eval/backtest_artifact.py` | `GateResult` + new `StatusExplanation`; add `model_status`, `status_version`, validity-gate fields, `status_explanation`. | Modify |
| `src/dynasty_genius/eval/composite_gate.py` | NEW — pure helpers: `identify_cold_start_fold`, `fold_rank_pass`, `fold_ci_adequate`, `ci_width`, `compute_model_status`, effective gate-field helpers. | Create |
| `src/dynasty_genius/eval/backtest_metrics.py` | NEW `compute_null_coverage` producer. | Modify |
| `src/dynasty_genius/eval/backtest_harness.py` | `evaluate_promotion_gates`: compute validity gates + `model_status` + `status_explanation`; demote G3 to disclosed. | Modify |
| `src/dynasty_genius/eval/model_card.py` | Add `ModelCardMetrics.model_status` beside public-but-deprecated `overall_grade`. | Modify |
| `scripts/generate_model_cards.py` | Populate model-card `model_status` from `BacktestResult.promotion_gate.model_status`. | Modify |
| `app/api/routes/trust_surface.py` | Hoist `model_status` (quarantined); keep `overall_grade` deprecated. | Modify |
| `tests/test_composite_gate.py` | NEW — unit tests for the pure status logic + falsification matrix. | Create |
| `tests/test_backtest_gates.py` | Extend — `evaluate_promotion_gates` now emits `model_status`; G3 no longer gates it. | Modify |
| `tests/test_model_card.py` | Extend — model-card schema and generator carry `model_status`. | Modify |
| `tests/contract/test_trust_surface_status.py` | NEW — route surfaces quarantined `model_status`; `overall_grade` still present. | Create |
| `tests/helpers/backtest_gate_builders.py` | NEW — canonical `build_mock_fold` / `build_mock_stability` / `build_mock_divergence` helpers extracted from existing gate tests and reused by Step 0.5 tests. | Create |

---

## Task 1: Schema — additive `model_status` + `StatusExplanation` + validity fields

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_artifact.py:97-107` (`GateResult`)
- Test: `tests/test_composite_gate.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_composite_gate.py
from src.dynasty_genius.eval.backtest_artifact import GateResult, StatusExplanation


def _base_gate_kwargs():
    return dict(
        g1_rank_correlation_pass=True,
        g2_rmse_stability_pass=True,
        g3_market_superiority_pass=False,
        g4_divergence_validity_pass="deferred",
        overall_grade="ACTIVE_B",
        promotion_justification="x",
    )


def test_gateresult_defaults_are_fail_closed_and_additive():
    g = GateResult(**_base_gate_kwargs())
    # New fields default fail-closed / non-breaking
    assert g.model_status == "EXPERIMENTAL"
    assert g.status_version == "0.5.0"
    assert g.status_explanation is None
    assert g.validity_spearman_pass is False
    assert g.validity_r2_pass is False
    assert g.validity_ci_adequacy_pass is False
    assert g.validity_rmse_stability_pass is False
    assert g.validity_null_coverage_pass is False
    assert g.validity_leakage_pass is False
    assert g.validity_cold_start_fold_index is None
    assert g.validity_cold_start_tolerated is False
    assert g.validity_most_recent_fold_index is None
    assert g.validity_most_recent_fold_pass is None
    assert g.null_coverage_min is None
    # Existing fields untouched
    assert g.overall_grade == "ACTIVE_B"
    assert g.gate_version == "1.0"


def test_status_explanation_round_trips():
    se = StatusExplanation(
        failed_rank_folds=[1],
        failed_ci_folds=[1],
        cold_start_fold_index=1,
        cold_start_tolerated=True,
        most_recent_fold_index=4,
        most_recent_fold_pass=True,
        null_coverage_min=0.97,
        leakage_clean=True,
        reason="cold-start fold excused; most-recent passes",
    )
    g = GateResult(**_base_gate_kwargs(), model_status="VALIDATED", status_explanation=se)
    dumped = g.model_dump_json()
    reloaded = GateResult.model_validate_json(dumped)
    assert reloaded.model_status == "VALIDATED"
    assert reloaded.status_explanation.cold_start_tolerated is True
    assert reloaded.status_explanation.failed_rank_folds == [1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -v`
Expected: FAIL — `ImportError: cannot import name 'StatusExplanation'` / `GateResult` has no `model_status`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/dynasty_genius/eval/backtest_artifact.py` (above `GateResult`):

```python
class StatusExplanation(BaseModel):
    """Auditable record of why a model_status was assigned (spec §6.5)."""
    failed_rank_folds: List[int] = Field(default_factory=list)      # fold_index list
    failed_ci_folds: List[int] = Field(default_factory=list)
    cold_start_fold_index: Optional[int] = None                    # None = fail-loud (no excuse)
    cold_start_tolerated: bool = False
    most_recent_fold_index: Optional[int] = None
    most_recent_fold_pass: Optional[bool] = None
    null_coverage_min: Optional[float] = None
    leakage_clean: Optional[bool] = None
    reason: str = ""
```

Extend `GateResult` (additive — keep all existing fields):

```python
class GateResult(BaseModel):
    g1_rank_correlation_pass: bool
    g2_rmse_stability_pass: bool
    g3_market_superiority_pass: Literal[True, False, "deferred"]
    g4_divergence_validity_pass: Literal[True, False, "deferred", "insufficient_data"]
    overall_grade: Literal[
        "PRE_MODEL", "EXPERIMENTAL", "ACTIVE_B",
        "ACTIVE_B_VALIDATED", "DECISION_GRADE",
    ]
    gate_version: str = "1.0"
    promotion_justification: str

    # Step 0.5 — unified validity status (additive; overall_grade kept public-but-deprecated)
    model_status: Literal["VALIDATED", "PROVISIONAL", "EXPERIMENTAL"] = "EXPERIMENTAL"
    status_version: str = "0.5.0"
    validity_spearman_pass: bool = False
    validity_r2_pass: bool = False
    validity_ci_adequacy_pass: bool = False
    validity_rmse_stability_pass: bool = False
    validity_null_coverage_pass: bool = False
    validity_leakage_pass: bool = False
    validity_cold_start_fold_index: Optional[int] = None
    validity_cold_start_tolerated: bool = False
    validity_most_recent_fold_index: Optional[int] = None
    validity_most_recent_fold_pass: Optional[bool] = None
    null_coverage_min: Optional[float] = None
    status_explanation: Optional[StatusExplanation] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit** (after cockpit dual-CLEAR + David authorization)

```bash
git add src/dynasty_genius/eval/backtest_artifact.py tests/test_composite_gate.py
git commit -m "feat(step-0.5): additive model_status + StatusExplanation schema"
```

---

## Task 2: Cold-start identification (fail-loud) + per-fold predicates

**Files:**
- Create: `src/dynasty_genius/eval/composite_gate.py`
- Test: `tests/test_composite_gate.py`
- Test helper setup: extract the existing `tests/test_backtest_gates.py` builders into `tests/helpers/backtest_gate_builders.py` and import them from both test modules. This is test-only setup to prevent the helper drift F3 is meant to catch.

- [ ] **Step 0: Extract canonical test builders**

Create `tests/helpers/backtest_gate_builders.py` by moving the existing helpers from `tests/test_backtest_gates.py`. Extend `build_mock_fold` additively so old gate tests keep their current `tau` / NDCG parameters while Step 0.5 tests can pass explicit fold identity and Spearman/R²/CI/null-coverage fields:

```python
def build_mock_fold(
    tau: float = 0.45,
    tau_ci_low: float = 0.25,
    model_ndcg: Optional[float] = 0.85,
    market_ndcg: Optional[float] = 0.80,
    model_ndcg_12: Optional[float] = 0.85,
    market_ndcg_12: Optional[float] = 0.80,
    *,
    idx: int = 1,
    test_year: int = 2020,
    train_years: Optional[list[int]] = None,
    spear: float = 0.60,
    r2: Optional[float] = None,
    ci: tuple[float, float] = (0.50, 0.70),
    null_coverage: Optional[float] = None,
) -> FoldResult:
    ...
```

Do not leave a second local `build_mock_fold` in `tests/test_composite_gate.py`; the helper module is the single source used by both test files.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_composite_gate.py
from tests.helpers.backtest_gate_builders import build_mock_fold
from src.dynasty_genius.eval.composite_gate import (
    ci_width, fold_rank_pass, fold_ci_adequate, identify_cold_start_fold,
    SPEARMAN_THRESHOLD, R2_FLOOR, CI_WIDTH_MAX,
)


def test_ci_width():
    assert ci_width((0.40, 0.70)) == 0.30


def test_fold_predicates():
    good = build_mock_fold(
        idx=2, test_year=2021, train_years=[2018, 2019, 2020],
        spear=0.79, r2=0.46, ci=(0.69, 0.85),
    )
    assert fold_rank_pass(good) is True
    assert fold_ci_adequate(good) is True
    weak_rank = build_mock_fold(
        idx=1, test_year=2020, train_years=[2018, 2019],
        spear=0.44, r2=0.24, ci=(0.24, 0.59),
    )
    assert fold_rank_pass(weak_rank) is False
    assert fold_ci_adequate(weak_rank) is False  # width 0.35 > 0.30


def test_cold_start_unique_min_year_and_thinnest_train():
    folds = [
        build_mock_fold(idx=1, test_year=2020, train_years=[2018, 2019], spear=0.44, r2=0.24, ci=(0.24, 0.59)),
        build_mock_fold(idx=2, test_year=2021, train_years=[2018, 2019, 2020], spear=0.79, r2=0.46, ci=(0.69, 0.85)),
    ]
    assert identify_cold_start_fold(folds) == 1


def test_cold_start_fail_loud_when_not_unique():
    # two folds share the min test_year -> no unique cold-start -> None (fail-loud)
    folds = [
        build_mock_fold(idx=1, test_year=2020, train_years=[2018, 2019], spear=0.44, r2=0.24, ci=(0.24, 0.59)),
        build_mock_fold(idx=2, test_year=2020, train_years=[2017, 2018, 2019], spear=0.79, r2=0.46, ci=(0.69, 0.85)),
    ]
    assert identify_cold_start_fold(folds) is None


def test_cold_start_fail_loud_when_min_year_not_thinnest_train():
    # min test_year fold is NOT the thinnest-train fold -> fail-loud None
    folds = [
        build_mock_fold(idx=1, test_year=2020, train_years=[2016, 2017, 2018, 2019], spear=0.44, r2=0.24, ci=(0.24, 0.59)),
        build_mock_fold(idx=2, test_year=2021, train_years=[2018, 2019], spear=0.79, r2=0.46, ci=(0.69, 0.85)),
    ]
    assert identify_cold_start_fold(folds) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -k "ci_width or predicate or cold_start" -v`
Expected: FAIL — `ModuleNotFoundError: ...composite_gate`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/dynasty_genius/eval/composite_gate.py
"""Step 0.5 — pure helpers for the unified composite validity gate (spec 2026-06-12)."""
from __future__ import annotations

from typing import List, Optional, Tuple

from src.dynasty_genius.eval.backtest_artifact import FoldResult

SPEARMAN_THRESHOLD = 0.55
R2_FLOOR = 0.0
CI_WIDTH_MAX = 0.30


def ci_width(ci: Tuple[float, float]) -> float:
    return round(ci[1] - ci[0], 10)


def fold_rank_pass(fold: FoldResult) -> bool:
    """Spearman >= threshold AND R² > floor (R² None => fail-closed)."""
    return (
        fold.spearman_rho >= SPEARMAN_THRESHOLD
        and fold.r2_oos is not None
        and fold.r2_oos > R2_FLOOR
    )


def fold_ci_adequate(fold: FoldResult) -> bool:
    """Per-fold Spearman BCa CI-width <= max (sample adequacy, spec §10.1)."""
    return ci_width(fold.spearman_rho_bca_ci95) <= CI_WIDTH_MAX


def identify_cold_start_fold(folds: List[FoldResult]) -> Optional[int]:
    """Return the fold_index that is UNIQUELY both min test_year AND min train length.

    Fail-loud (spec §3.3/§6.6): if the min-test_year fold is not uniquely the
    thinnest-train fold, return None — no cold-start excuse is granted.
    """
    if not folds:
        return None
    min_year = min(f.test_year for f in folds)
    year_min = [f for f in folds if f.test_year == min_year]
    if len(year_min) != 1:
        return None
    candidate = year_min[0]
    min_train = min(len(f.train_years) for f in folds)
    train_min = [f for f in folds if len(f.train_years) == min_train]
    if len(train_min) != 1 or train_min[0].fold_index != candidate.fold_index:
        return None
    return candidate.fold_index
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -k "ci_width or predicate or cold_start" -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add src/dynasty_genius/eval/composite_gate.py tests/test_composite_gate.py
git commit -m "feat(step-0.5): cold-start fail-loud + per-fold validity predicates"
```

---

## Task 3: `compute_model_status` — the recency-aware rule

**Files:**
- Modify: `src/dynasty_genius/eval/composite_gate.py`
- Test: `tests/test_composite_gate.py`

- [ ] **Step 1: Write the failing test** (covers the 4 real outcomes + the rule's edges)

```python
# append to tests/test_composite_gate.py
from src.dynasty_genius.eval.composite_gate import (
    NULL_COVERAGE_MIN,
    compute_model_status,
    effective_ci_adequacy_gate_pass,
    effective_rank_gate_pass,
)


def _four_folds(spears, r2s, cis):
    train = [[2018, 2019], [2018, 2019, 2020], [2018, 2019, 2020, 2021],
             [2018, 2019, 2020, 2021, 2022]]
    return [
        build_mock_fold(
            idx=i + 1,
            test_year=2020 + i,
            train_years=train[i],
            spear=spears[i],
            r2=r2s[i],
            ci=cis[i],
        )
        for i in range(4)
    ]


def test_status_wr_validated():
    folds = _four_folds([0.763, 0.785, 0.816, 0.794], [0.602, 0.680, 0.693, 0.666],
                        [(0.69, 0.84), (0.71, 0.85), (0.74, 0.88), (0.73, 0.85)])
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "VALIDATED"


def test_status_te_validated_cold_start_excused():
    # fold-1 (cold-start) fails both rank (0.436) and CI-width (0.344); later folds strong
    folds = _four_folds([0.436, 0.792, 0.714, 0.706], [0.244, 0.457, 0.472, 0.558],
                        [(0.24, 0.585), (0.69, 0.85), (0.61, 0.81), (0.57, 0.81)])
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "VALIDATED"
    assert expl.cold_start_tolerated is True
    assert expl.failed_rank_folds == [1] and expl.failed_ci_folds == [1]
    assert effective_rank_gate_pass(expl) is True
    assert effective_ci_adequacy_gate_pass(expl) is True


def test_status_qb_provisional_middle_ci_breach():
    # all rank-pass, but CI-width breaches at fold-1(cold-start) AND fold-3(middle) -> not excusable
    folds = _four_folds([0.678, 0.721, 0.693, 0.755], [0.141, 0.298, 0.287, 0.286],
                        [(0.42, 0.82), (0.54, 0.83), (0.43, 0.84), (0.61, 0.86)])
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "PROVISIONAL"
    assert 3 in expl.failed_ci_folds


def test_status_experimental_when_leakage_dirty():
    folds = _four_folds([0.80, 0.80, 0.80, 0.80], [0.6, 0.6, 0.6, 0.6],
                        [(0.7, 0.8)] * 4)
    status, _ = compute_model_status(folds, null_coverage_min_obs=0.99, leakage_clean=False)
    assert status == "EXPERIMENTAL"


def test_status_experimental_when_null_coverage_below_floor():
    folds = _four_folds([0.80, 0.80, 0.80, 0.80], [0.6, 0.6, 0.6, 0.6], [(0.7, 0.8)] * 4)
    status, _ = compute_model_status(folds, null_coverage_min_obs=0.80, leakage_clean=True)
    assert status == "EXPERIMENTAL"


def test_status_provisional_when_most_recent_fold_fails():
    # most-recent (fold-4) fails rank -> never VALIDATED even though 3/4 pass
    folds = _four_folds([0.80, 0.80, 0.80, 0.40], [0.6, 0.6, 0.6, 0.6],
                        [(0.7, 0.8)] * 4)
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "PROVISIONAL"
    assert expl.most_recent_fold_pass is False


def test_status_provisional_when_middle_fold_fails_not_cold_start():
    # only fold-2 (middle) fails rank; cold-start tolerance does NOT cover it
    folds = _four_folds([0.80, 0.40, 0.80, 0.80], [0.6, 0.6, 0.6, 0.6],
                        [(0.7, 0.8)] * 4)
    status, _ = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "PROVISIONAL"


def test_status_provisional_when_cold_start_not_unique():
    # fail-loud cold-start (None) -> a failing oldest fold is NOT excused
    folds = _four_folds([0.40, 0.80, 0.80, 0.80], [0.6, 0.6, 0.6, 0.6], [(0.7, 0.8)] * 4)
    folds[1].test_year = 2020  # duplicate min year -> identify returns None
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.97, leakage_clean=True)
    assert status == "PROVISIONAL"
    assert expl.cold_start_fold_index is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -k status -v`
Expected: FAIL — `cannot import name 'compute_model_status'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/dynasty_genius/eval/composite_gate.py
from src.dynasty_genius.eval.backtest_artifact import StatusExplanation

NULL_COVERAGE_MIN = 0.90


def effective_rank_gate_pass(expl: StatusExplanation) -> bool:
    return not expl.failed_rank_folds or all(
        fi == expl.cold_start_fold_index for fi in expl.failed_rank_folds
    )


def effective_ci_adequacy_gate_pass(expl: StatusExplanation) -> bool:
    return not expl.failed_ci_folds or all(
        fi == expl.cold_start_fold_index for fi in expl.failed_ci_folds
    )


def compute_model_status(
    folds: List[FoldResult],
    null_coverage_min_obs: Optional[float],
    leakage_clean: bool,
) -> Tuple[str, StatusExplanation]:
    """Recency-aware validity status (spec §3.3). Returns (status, explanation)."""
    cold = identify_cold_start_fold(folds)
    most_recent = max(folds, key=lambda f: f.test_year) if folds else None

    failed_rank = [f.fold_index for f in folds if not fold_rank_pass(f)]
    failed_ci = [f.fold_index for f in folds if not fold_ci_adequate(f)]
    mr_pass = bool(most_recent) and fold_rank_pass(most_recent) and fold_ci_adequate(most_recent)

    expl = StatusExplanation(
        failed_rank_folds=failed_rank,
        failed_ci_folds=failed_ci,
        cold_start_fold_index=cold,
        most_recent_fold_index=most_recent.fold_index if most_recent else None,
        most_recent_fold_pass=mr_pass if most_recent else None,
        null_coverage_min=null_coverage_min_obs,
        leakage_clean=leakage_clean,
    )

    # Hard safety floors first (spec §3.3 #4, §6.3)
    if not leakage_clean:
        expl.reason = "leakage not clean -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl
    if null_coverage_min_obs is None or null_coverage_min_obs < NULL_COVERAGE_MIN:
        expl.reason = "null-coverage below floor -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl
    if len(folds) < 2:
        expl.reason = "insufficient folds -> EXPERIMENTAL"
        return "EXPERIMENTAL", expl

    # Cold-start tolerance: only the cold-start fold may appear in failures.
    rank_ok = effective_rank_gate_pass(expl)
    ci_ok = effective_ci_adequacy_gate_pass(expl)
    expl.cold_start_tolerated = bool(cold is not None and (cold in failed_rank or cold in failed_ci))

    if rank_ok and ci_ok and mr_pass:
        expl.reason = "all folds pass (cold-start excused); most-recent passes -> VALIDATED"
        return "VALIDATED", expl
    expl.reason = "non-cold-start fold failure or most-recent failure -> PROVISIONAL"
    return "PROVISIONAL", expl
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -k status -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add src/dynasty_genius/eval/composite_gate.py tests/test_composite_gate.py
git commit -m "feat(step-0.5): recency-aware compute_model_status"
```

---

## Task 4: Null-coverage producer (spec §3.1, F2)

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_metrics.py`
- Test: `tests/test_backtest_metrics.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_backtest_metrics.py
from src.dynasty_genius.eval.backtest_metrics import compute_null_coverage


def test_null_coverage_scored_over_eligible():
    # eligible (identity-valid) = 100; scored (survived feature-null drops) = 95
    cov = compute_null_coverage(n_eligible=100, n_scored=95)
    assert cov == 0.95


def test_null_coverage_zero_eligible_is_fail_closed():
    # no eligible rows -> 0.0 (fail-closed, not div-by-zero)
    assert compute_null_coverage(n_eligible=0, n_scored=0) == 0.0


def test_null_coverage_rejects_scored_above_eligible():
    # cross-component shape mismatch: scored rows cannot exceed the fold universe
    with pytest.raises(ValueError, match="n_scored cannot exceed n_eligible"):
        compute_null_coverage(n_eligible=95, n_scored=100)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_backtest_metrics.py -k null_coverage -v`
Expected: FAIL — `cannot import name 'compute_null_coverage'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/dynasty_genius/eval/backtest_metrics.py
def compute_null_coverage(n_eligible: int, n_scored: int) -> float:
    """Fold-local null coverage = scored / eligible (spec §3.1, F2).

    `n_eligible` = identity-valid player-season rows BEFORE feature-null drops.
    `n_scored`   = rows that survived feature-null drops (actually evaluated).
    Fail-closed to 0.0 when there are no eligible rows.
    """
    if n_eligible <= 0:
        return 0.0
    if n_scored > n_eligible:
        raise ValueError("n_scored cannot exceed n_eligible")
    return round(n_scored / n_eligible, 6)
```

Task 5 wires this producer into the harness. Do not leave `compute_null_coverage()` as an isolated pure helper.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_backtest_metrics.py -k null_coverage -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add src/dynasty_genius/eval/backtest_metrics.py tests/test_backtest_metrics.py
git commit -m "feat(step-0.5): null-coverage producer (scored/eligible)"
```

---

## Task 5: Wire into `evaluate_promotion_gates` — status + G3 demotion

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_harness.py:227-354` (`evaluate_promotion_gates`)
- Modify: `src/dynasty_genius/eval/backtest_artifact.py` (add `FoldResult.null_coverage`)
- Test: `tests/test_backtest_gates.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
from src.dynasty_genius.eval.backtest_metrics import compute_null_coverage
from tests.helpers.backtest_gate_builders import build_mock_fold, build_mock_stability


def _step05_four_folds(spears, r2s, cis, null_coverage=0.97):
    train = [[2018, 2019], [2018, 2019, 2020], [2018, 2019, 2020, 2021],
             [2018, 2019, 2020, 2021, 2022]]
    return [
        build_mock_fold(
            idx=i + 1,
            test_year=2020 + i,
            train_years=train[i],
            spear=spears[i],
            r2=r2s[i],
            ci=cis[i],
            null_coverage=null_coverage,
        )
        for i in range(4)
    ]


def test_model_status_is_emitted_and_g3_does_not_gate_it():
    # TE-like: cold-start weak, later strong; G3 fails/defers but validity status clears.
    folds = _step05_four_folds(
        [0.436, 0.792, 0.714, 0.706],
        [0.244, 0.457, 0.472, 0.558],
        [(0.24, 0.585), (0.69, 0.85), (0.61, 0.81), (0.57, 0.81)],
    )
    stability = build_mock_stability()
    result = evaluate_promotion_gates(
        position="TE", folds=folds, stability=stability, divergence=None, leakage_clean=True,
    )
    # G3 still computed + disclosed, but it does NOT gate model_status
    assert result.g3_market_superiority_pass in (False, "deferred")
    assert result.model_status == "VALIDATED"          # validity-only, G3 demoted
    assert result.status_explanation is not None
    assert result.status_explanation.cold_start_tolerated is True
    # overall_grade (deprecated) is still populated, unchanged contract
    assert result.overall_grade in (
        "PRE_MODEL", "EXPERIMENTAL", "ACTIVE_B", "ACTIVE_B_VALIDATED", "DECISION_GRADE",
    )


def test_evaluate_promotion_gates_uses_fold_null_coverage_min_fail_closed():
    folds = _step05_four_folds(
        [0.80, 0.80, 0.80, 0.80],
        [0.60, 0.60, 0.60, 0.60],
        [(0.70, 0.80)] * 4,
        null_coverage=0.95,
    )
    folds[2].null_coverage = 0.89
    result = evaluate_promotion_gates(
        position="WR", folds=folds, stability=build_mock_stability(), leakage_clean=True,
    )
    assert result.null_coverage_min == 0.89
    assert result.validity_null_coverage_pass is False
    assert result.model_status == "EXPERIMENTAL"


def test_harness_fold_null_coverage_uses_test_mask_and_scored_frame_shape():
    # Cross-component shape test: eligible comes from the fold test_mask before feature handling;
    # scored comes from the X_test rows actually returned by _build_fold_data.
    # Current harness imputes feature nulls instead of dropping rows, so real v1 folds are expected
    # to report 1.0. This helper-level mismatch proves the wiring uses the two component shapes and
    # will fail if the harness later drops rows but forgets to propagate the scored shape.
    import pandas as pd
    from src.dynasty_genius.eval import backtest_harness as harness

    test_mask = pd.Series([True, True, True, False])
    scored_frame = pd.DataFrame({"feature": [1.0, 2.0]})

    assert harness._compute_fold_null_coverage(test_mask, scored_frame) == (
        compute_null_coverage(n_eligible=3, n_scored=2)
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_backtest_gates.py -k "model_status or null_coverage" -v`
Expected: FAIL — `FoldResult` has no `null_coverage` / `evaluate_promotion_gates()` has no `leakage_clean` / `GateResult` has no `model_status`.

- [ ] **Step 3: Write minimal implementation**

Add `null_coverage: Optional[float] = None` to `FoldResult`. In `evaluate_promotion_gates` (before the `return GateResult(...)` at :347): add `leakage_clean: bool = True` to the signature, compute `null_coverage_min` fail-closed when no folds report it, and compute status:

```python
from src.dynasty_genius.eval.composite_gate import (
    NULL_COVERAGE_MIN,
    compute_model_status,
    effective_ci_adequacy_gate_pass,
    effective_rank_gate_pass,
)
# ... after grade/justification are computed, before return:
null_coverage_values = [f.null_coverage for f in folds if f.null_coverage is not None]
null_coverage_min = min(null_coverage_values) if null_coverage_values else None
model_status, status_explanation = compute_model_status(
    folds=folds,
    null_coverage_min_obs=null_coverage_min,
    leakage_clean=leakage_clean,
)
```

And pass them into the `GateResult(...)` constructor:

```python
    return GateResult(
        g1_rank_correlation_pass=g1_pass,
        g2_rmse_stability_pass=g2_pass,
        g3_market_superiority_pass=g3_result,      # still DISCLOSED, no longer gates model_status
        g4_divergence_validity_pass=g4_status,
        overall_grade=grade,                        # deprecated, unchanged
        promotion_justification=justification,
        model_status=model_status,
        validity_spearman_pass=effective_rank_gate_pass(status_explanation),
        # rank gate is Spearman + R² jointly, with cold-start tolerance applied once in composite_gate
        validity_r2_pass=effective_rank_gate_pass(status_explanation),
        validity_ci_adequacy_pass=effective_ci_adequacy_gate_pass(status_explanation),
        validity_rmse_stability_pass=g2_pass,
        validity_null_coverage_pass=(
            null_coverage_min is not None and null_coverage_min >= NULL_COVERAGE_MIN
        ),
        validity_leakage_pass=leakage_clean,
        validity_cold_start_fold_index=status_explanation.cold_start_fold_index,
        validity_cold_start_tolerated=status_explanation.cold_start_tolerated,
        validity_most_recent_fold_index=status_explanation.most_recent_fold_index,
        validity_most_recent_fold_pass=status_explanation.most_recent_fold_pass,
        null_coverage_min=null_coverage_min,
        status_explanation=status_explanation,
    )
```

Add a small harness helper near `_compute_market_ndcg`:

```python
def _compute_fold_null_coverage(test_mask: pd.Series, x_test: pd.DataFrame) -> float:
    return compute_null_coverage(
        n_eligible=int(test_mask.sum()),
        n_scored=int(x_test.shape[0]),
    )
```

In `WalkForwardDriver.run`, call `_compute_fold_null_coverage(test_mask, X_test)` after `test_mask` and `X_test` exist; set `null_coverage=...` on each `FoldResult`. Leakage is `True` in v1 (Engine B training is market-blind by contract; the existing leakage tests guard prohibited features) — pass `leakage_clean=True` and wire it to a real leakage-audit boolean only when that producer lands.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_backtest_gates.py -v`
Expected: PASS (new + existing gate tests).

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add src/dynasty_genius/eval/backtest_harness.py src/dynasty_genius/eval/backtest_artifact.py tests/test_backtest_gates.py
git commit -m "feat(step-0.5): evaluate_promotion_gates emits model_status; G3 demoted to disclosed"
```

---

## Task 6: Trust Surface — surface quarantined `model_status`

**Files:**
- Modify: `app/api/routes/trust_surface.py:30-38,106,130-147`
- Test: `tests/contract/test_trust_surface_status.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/contract/test_trust_surface_status.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_trust_surface_exposes_quarantined_model_status():
    r = client.get("/api/trust-surface/WR")
    assert r.status_code == 200
    body = r.json()
    # New primary status present and from the allowed set
    assert body["model_status"] in ("VALIDATED", "PROVISIONAL", "EXPERIMENTAL")
    # Deprecated overall_grade still present (F1: public-but-deprecated, non-breaking)
    assert "overall_grade" in body
    # Backend shape preserves current contract: decision_supported is absent or false, never true.
    def walk(obj):
        if isinstance(obj, dict):
            if "decision_supported" in obj:
                assert obj["decision_supported"] is False
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_trust_surface_status.py -v`
Expected: FAIL — `KeyError: 'model_status'` (route does not yet hoist it).

- [ ] **Step 3: Write minimal implementation**

In `app/api/routes/trust_surface.py`: add `model_status: str` to the response model, hoist it next to the existing `overall_grade` hoist (~:106/:132): `model_status = result.promotion_gate.model_status`, and include it in the response construction. Keep `overall_grade` field (deprecated). Do **not** add backend `decision_supported` in this task; the route contract is absent-or-false / never true, while the visible non-dismissible `decision_supported=false` state remains enforced by the existing frontend/published-surface tests. Regenerate the OpenAPI snapshot + TS/Zod client and re-run the drift guard + the frontend `banned-language` linter against the new `model_status` literals.

```bash
# regen + drift guard (per repo convention)
.venv/bin/python3.14 scripts/dump_openapi.py
npm --prefix frontend run openapi-gen
npm --prefix frontend run banned-language
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_trust_surface_status.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add app/api/routes/trust_surface.py frontend/openapi.json frontend/src tests/contract/test_trust_surface_status.py
git commit -m "feat(step-0.5): trust surface hoists quarantined model_status; overall_grade deprecated"
```

---

## Task 7: ModelCard propagation — `model_status` alongside `overall_grade` (F5-plan)

**Files:**
- Modify: `src/dynasty_genius/eval/model_card.py:28-45` (`ModelCardMetrics`)
- Modify: `scripts/generate_model_cards.py:289-306` (`ModelCardMetrics(...)`)
- Test: `tests/test_model_card.py`

- [ ] **Step 1: Write the failing tests**

```python
# append/update in tests/test_model_card.py
def test_model_card_metrics_carries_model_status():
    metrics = _metrics().model_copy(update={"model_status": "VALIDATED"})
    assert metrics.model_status == "VALIDATED"
    assert metrics.overall_grade == "ACTIVE_B"


def test_generate_model_card_populates_model_status_from_gate(tmp_path):
    result = _make_result("WR")
    result.promotion_gate.model_status = "PROVISIONAL"
    run_dir = tmp_path / "runs" / str(result.run_id)
    result.save(run_dir)

    card, _ = generate_card_for_position(
        position="WR",
        runs_dir=tmp_path / "runs",
        output_dir=tmp_path / "cards",
    )

    assert card.metrics.model_status == "PROVISIONAL"
    assert card.metrics.overall_grade == result.promotion_gate.overall_grade
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/test_model_card.py -k model_status -v`
Expected: FAIL — `ModelCardMetrics` has no `model_status` / generated card does not populate it.

- [ ] **Step 3: Write minimal implementation**

In `src/dynasty_genius/eval/model_card.py`, add:

```python
class ModelCardMetrics(BaseModel):
    ...
    overall_grade: str
    model_status: str = "EXPERIMENTAL"
```

In `scripts/generate_model_cards.py`, pass the field next to `overall_grade`:

```python
    metrics = ModelCardMetrics(
        ...
        overall_grade=gate.overall_grade,
        model_status=gate.model_status,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/test_model_card.py -k model_status -v`
Expected: PASS.

- [ ] **Step 5: Commit** (after dual-CLEAR)

```bash
git add src/dynasty_genius/eval/model_card.py scripts/generate_model_cards.py tests/test_model_card.py
git commit -m "feat(step-0.5): propagate model_status into model cards"
```

---

## Task 8: Falsification matrix + republish + verification

**Files:**
- Modify: `tests/test_composite_gate.py` (falsification rows, spec §11)
- Test/verify: full suite + republish trust artifacts

- [ ] **Step 1: Write the failing falsification tests**

```python
# append to tests/test_composite_gate.py
import pytest
from pydantic import ValidationError


def test_wrong_type_metric_fails_closed():
    with pytest.raises(ValidationError):
        build_mock_fold(
            idx=1, test_year=2020, train_years=[2018, 2019],
            spear="high", r2=0.2, ci=(0.2, 0.5),
        )  # spearman str


def test_empty_folds_is_experimental():
    status, expl = compute_model_status([], null_coverage_min_obs=0.99, leakage_clean=True)
    assert status == "EXPERIMENTAL"


def test_duplicate_test_year_disables_cold_start_excuse():
    folds = _four_folds([0.40, 0.80, 0.80, 0.80], [0.6] * 4, [(0.7, 0.8)] * 4)
    folds[1].test_year = 2020  # conflict
    status, expl = compute_model_status(folds, null_coverage_min_obs=0.99, leakage_clean=True)
    assert expl.cold_start_fold_index is None
    assert status == "PROVISIONAL"


def test_r2_none_fails_rank():
    f = build_mock_fold(
        idx=2, test_year=2021, train_years=[2018, 2019, 2020],
        spear=0.79, r2=None, ci=(0.69, 0.85),
    )
    assert fold_rank_pass(f) is False
```

- [ ] **Step 2: Run to verify they fail / then pass**

Run: `.venv/bin/python3.14 -m pytest tests/test_composite_gate.py -v`
Expected: the new rows pass against the Task 2–3 implementation (they assert already-built fail-closed behavior); fix any gap surfaced.

- [ ] **Step 3: Republish trust artifacts with `model_status`**

Run the backtest republish path (the Trust-Console publication script used in the Model Trust Console build) so `app/data/backtest/trust_surface/latest/*.json` carry `model_status`. Confirm: WR/RB/TE → `VALIDATED`, QB → `PROVISIONAL`.

- [ ] **Step 4: Full verification**

Run:
```bash
.venv/bin/python3.14 -m pytest    # full suite, minus the AGENT_SYNC-excluded collection-error files
ruff check src app
cd frontend && npm run tsc && npm run biome && npm run vitest && npm run banned-language && npm run build && cd ..
```
Expected: full Python suite green; FE gate green; S4 byte-audit unaffected (no inviolate path touched).

- [ ] **Step 5: Commit + closeout** (after dual-CLEAR)

```bash
git add tests/test_composite_gate.py app/data/backtest/trust_surface/latest
git commit -m "test(step-0.5): falsification matrix + republish artifacts with model_status"
```

---

## Self-review checklist (run before cockpit handoff)
- [ ] Spec coverage: §3.1 (T4/T5), §3.3 recency rule (T2/T3), §3.5 outcome (T3/T8), §5 schema/F1 (T1/T6/T7), §6 guardrails/F4 (T2/T6), §10 thresholds (constants in T2/T3), §11 falsification (T8), model-card propagation/F5-plan (T7). G3-demotion (T5). Engine A deferred — no task (correct).
- [ ] No placeholders: every code step has real code; constants concrete; outcomes verified against live data.
- [ ] Type consistency: `model_status`/`status_version`/`status_explanation` names identical across T1, T3, T5, T6, T7; `compute_model_status` signature `(folds, null_coverage_min_obs, leakage_clean)` identical in T3 and T5.

## Open wiring notes for the GREEN author (not placeholders — explicit handoffs)
- T5 wires the real per-fold `n_eligible`/`n_scored` out of `WalkForwardDriver.run`; the pure gate logic (T1–T4) is fully testable before this wiring, but v2 is not complete until the harness helper and fold-min gate test pass.
- T6 route path is `/api/trust-surface/{position}` (`app/main.py` mounts `trust_surface.router` with `/api`, and the router prefix is `/trust-surface`).
- Leakage-clean is `True` by contract in v1 (market-blind Engine B); wire to a real leakage-audit boolean when/if that producer is added.
