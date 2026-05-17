# Phase 15 Trade Lab & Cross-Positional Valuation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement cross-positional VAR (xVAR), Bayesian Dead Window blend, Trade Lab API v0, and dvs_pct nightly batch.

**Architecture:** All model scoring is market-free. xVAR translates DVS into WR-equivalent VAR points using frozen P90 ratios as positional multipliers. Trade fairness is xVAR-sum parity with geometric consolidation penalty. `dvs_pct` is within-position percentile against the active Engine B population, nightly batch only.

**Tech Stack:** Python 3.9, Pydantic v1, FastAPI, pytest. No Databricks, no market data in model paths.

**Spec:** `docs/superpowers/specs/2026-05-16-phase15-trade-lab.md` (APPROVED)

**Governance read before starting:** `docs/governance/02-agent-operating-loop.md`, `docs/governance/00-product-constitution.md`, `docs/governance/01-north-star-architecture.md`, `AGENT_SYNC.md`

---

## Status as of 2026-05-16

### COMPLETE (merged into working copy — not yet committed)

**Prerequisite (Task 0): VAR Baseline Refresh**
- Script: `scripts/refresh_var_baselines_15.py` ✓
- Validation artifact: `docs/validation/phase15-var-baseline-refresh.md` ✓
- TE Gate: PASS (replacement PPG ≤ TE P90 ceiling of 9.4) ✓
- `scripts/compute_var_batch.py` updated to handle inference DataFrames ✓

**Workstream 15.1: Cross-Positional Architecture (xVAR)**
- `engine_b_contract.py`: `XVAR_LAMBDA_ENGINE_B`, `XVAR_LAMBDA_ENGINE_A`, `XVAR_ANCHOR_POSITION`, `TRADE_PARITY_BAND`, `CONSOLIDATION_KAPPA`, `CONSOLIDATION_FLOOR`, `DVS_BLEND_K`, `ENGINE_B_REPLACEMENT_DVS`, `ENGINE_A_REPLACEMENT_DVS` all added ✓
- `player_value_object.py`: `xvar`, `xvar_lambda`, `xvar_anchor`, `xvar_ceiling_bound`, `dvs_pct`, `dvs_pct_as_of`, `dvs_blend_weight_b` added ✓; duplicate `value_above_replacement` removed ✓
- `pvo_assembler.py`: inline xVAR computation in Engine B path; uses Engine A Λ for `dvs_engine in ("A", "blend")` ✓
- Valuation tests in `tests/contract/test_phase15_valuation.py` ✓ (3 tests passing)

**Workstream 15.2: Bayesian Dead Window Blend**
- `pvo_assembler.py`: Bayesian blend logic; `w_B = n / (n + k_pos)`; `dvs_engine = "blend"` when both engines contribute ✓
- Phase 14 dead window test updated to reflect blend behavior (`dvs_engine == "blend"`) ✓
- **OUTSTANDING:** `docs/validation/phase15-blend-k-validation.md` — required gate before 15.2 is locked. k_pos defaults (QB=6, RB=5, WR=5, TE=7) are in place but NOT yet validated against Engine B per-position residual variance. David must review and approve k_pos values before this gate clears.

**Suite state:** 690 passed, 11 skipped, 0 failed (excluding 2 nflreadpy collection errors — pre-existing environment issue)

---

## Remaining Work for Codex

### Task 1: Blend k_pos Validation Artifact

**Files:**
- Create: `docs/validation/phase15-blend-k-validation.md`

This is a GATE before Workstream 15.2 is considered complete.

- [ ] **Step 1: Write the validation stub**

Create `docs/validation/phase15-blend-k-validation.md` with this content:

```markdown
# Phase 15 — Bayesian Blend k_pos Validation

**Status:** PENDING — k_pos defaults not yet validated against Engine B residual variance.

**Current defaults (from engine_b_contract.py DVS_BLEND_K):**
- QB: k_pos = 6
- RB: k_pos = 5
- WR: k_pos = 5
- TE: k_pos = 7

**Required validation:** Fit k_pos from Engine B per-position residual variance
before locking. Document methodology and results here.

**Gate:** David reviews and approves before phase 15.2 is considered complete.
```

- [ ] **Step 2: Commit**

```bash
git add docs/validation/phase15-blend-k-validation.md
git commit -m "docs(phase15): add blend-k validation stub — gate requires David approval"
```

---

### Task 2: Trade Lab Module

**Files:**
- Create: `src/dynasty_genius/trade_lab/__init__.py`
- Create: `src/dynasty_genius/trade_lab/evaluator.py`
- Test: `tests/contract/test_phase15_trade_lab.py`

**Imports needed in evaluator.py:**

```python
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from src.dynasty_genius.models.engine_b_contract import (
    TRADE_PARITY_BAND, CONSOLIDATION_KAPPA, CONSOLIDATION_FLOOR,
    XVAR_LAMBDA_ENGINE_A, XVAR_ANCHOR_POSITION,
)
from src.dynasty_genius.scoring.engine_a import score_prospect
```

- [ ] **Step 1: Write the failing tests**

Create `tests/contract/test_phase15_trade_lab.py`:

```python
"""Phase 15 Trade Lab contract tests — spec sections 5.3, 5.5, 5.6, 5.7, 5.12, 5.13."""
from __future__ import annotations
import pytest
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset, evaluate_trade, _consolidation_factor, value_draft_pick,
)
from src.dynasty_genius.models.engine_b_contract import (
    TRADE_PARITY_BAND, CONSOLIDATION_KAPPA, CONSOLIDATION_FLOOR,
)
from src.dynasty_genius.services.market_overlay_service import NOISE_BAND


def _asset(pos: str, xvar: Optional[float], dvs_engine: str = "B") -> TradeAsset:
    return TradeAsset(
        player_id=f"test_{pos}",
        xvar=xvar,
        dvs=None,
        dvs_engine=dvs_engine,
        position=pos,
    )


def test_sub_replacement_contributes_zero():
    """5.3: xVAR ≤ 0 contributes 0 to side value."""
    bench = _asset("WR", -5.0)
    starter = _asset("WR", 20.0)
    result = evaluate_trade([bench, starter], [_asset("QB", 25.0)])
    # bench filler excluded: side_a_value = 20.0 * 1.0 (1 starter, factor=1.0)
    assert result.side_a.xvar_sum == 20.0
    assert result.side_a.consolidation_factor == 1.0


def test_consolidation_factor_1_asset():
    """5.5: 1-starter side: factor = 1.000."""
    assert _consolidation_factor(1) == 1.0


def test_consolidation_factor_2_assets():
    """5.5: 2 starters: factor = 1.0 - 0.04 * 1 = 0.960."""
    assert _consolidation_factor(2) == pytest.approx(0.960)


def test_consolidation_factor_3_assets():
    """5.5: 3 starters: factor = 1.0 - 0.04 * 2 = 0.920."""
    assert _consolidation_factor(3) == pytest.approx(0.920)


def test_consolidation_factor_floor():
    """5.5: 6 starters: factor = max(0.80, 1.0 - 0.04 * 5) = 0.80."""
    assert _consolidation_factor(6) == pytest.approx(CONSOLIDATION_FLOOR)


def test_trade_within_parity_band():
    """5.6: delta=2.0, max=32.0 → 2.0 ≤ 0.10 * 32.0 = 3.2 → within band."""
    # side_a_value = 30.0, side_b_value = 32.0 (single assets, factor=1.0)
    result = evaluate_trade([_asset("WR", 30.0)], [_asset("WR", 32.0)])
    assert result.within_parity_band is True
    assert result.favors == "neutral"


def test_trade_outside_parity_band():
    """5.7: delta=20.0, max=40.0 → 20.0 > 0.10 * 40.0 = 4.0 → favors side_b."""
    result = evaluate_trade([_asset("WR", 20.0)], [_asset("WR", 40.0)])
    assert result.within_parity_band is False
    assert result.favors == "side_b"


def test_draft_pick_uses_engine_a():
    """5.12: Draft pick via value_draft_pick → dvs_engine == 'A', is_prospect True."""
    pick_asset = value_draft_pick(round_=1, pick_bucket="mid", position="WR", age=21.5)
    assert pick_asset.dvs_engine == "A"
    assert pick_asset.is_prospect is True
    assert pick_asset.decision_supported is False


def test_trade_parity_band_not_noise_band():
    """5.13: TRADE_PARITY_BAND and NOISE_BAND are separate constants."""
    assert TRADE_PARITY_BAND == 0.10
    assert NOISE_BAND == 0.10
    # Verify they are distinct objects in distinct modules
    from src.dynasty_genius.models.engine_b_contract import TRADE_PARITY_BAND as TPB
    from src.dynasty_genius.services.market_overlay_service import NOISE_BAND as NB
    # Same value, independent constants — changing one must not affect the other
    assert TPB is not NB


def test_decision_supported_false_on_evaluation():
    """TradeEvaluation.decision_supported must always be False."""
    result = evaluate_trade([_asset("WR", 20.0)], [_asset("QB", 25.0)])
    assert result.decision_supported is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/contract/test_phase15_trade_lab.py -v
```

Expected: all fail with ImportError (module not found)

- [ ] **Step 3: Create `src/dynasty_genius/trade_lab/__init__.py`**

```python
"""Trade Lab — cross-positional asset evaluation. Phase 15."""
```

- [ ] **Step 4: Create `src/dynasty_genius/trade_lab/evaluator.py`**

```python
"""Trade Lab evaluator — xVAR-sum parity with consolidation premium."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from src.dynasty_genius.models.engine_b_contract import (
    CONSOLIDATION_FLOOR,
    CONSOLIDATION_KAPPA,
    TRADE_PARITY_BAND,
    XVAR_LAMBDA_ENGINE_A,
    XVAR_ANCHOR_POSITION,
    ENGINE_A_REPLACEMENT_DVS,
)
from src.dynasty_genius.scoring.engine_a import score_prospect


class TradeAsset(BaseModel):
    player_id: str
    xvar: Optional[float]        # None = PRE_MODEL / unscored
    dvs: Optional[float] = None
    dvs_engine: Optional[str] = None
    position: str
    is_prospect: bool = False
    decision_supported: bool = False
    caveat: Optional[str] = None


class TradeSide(BaseModel):
    assets: List[TradeAsset]
    xvar_sum: float
    consolidation_factor: float
    side_value: float


class TradeEvaluation(BaseModel):
    side_a: TradeSide
    side_b: TradeSide
    fairness_delta: float
    within_parity_band: bool
    favors: Optional[str]        # "side_a" | "side_b" | "neutral"
    favors_xvar_margin: Optional[float]
    decision_supported: bool = False
    caveats: List[str]


def _consolidation_factor(n_starter_assets: int) -> float:
    if n_starter_assets <= 1:
        return 1.0
    raw = 1.0 - CONSOLIDATION_KAPPA * (n_starter_assets - 1)
    return max(CONSOLIDATION_FLOOR, raw)


def _evaluate_side(assets: List[TradeAsset]) -> TradeSide:
    starter_xvars = [a.xvar for a in assets if a.xvar is not None and a.xvar > 0]
    xvar_sum = sum(starter_xvars)
    factor = _consolidation_factor(len(starter_xvars))
    return TradeSide(
        assets=assets,
        xvar_sum=round(xvar_sum, 2),
        consolidation_factor=round(factor, 4),
        side_value=round(xvar_sum * factor, 2),
    )


def evaluate_trade(
    side_a_assets: List[TradeAsset],
    side_b_assets: List[TradeAsset],
) -> TradeEvaluation:
    side_a = _evaluate_side(side_a_assets)
    side_b = _evaluate_side(side_b_assets)
    delta = abs(side_a.side_value - side_b.side_value)
    max_side = max(side_a.side_value, side_b.side_value)
    within_band = delta <= TRADE_PARITY_BAND * max_side if max_side > 0 else True

    favors = "neutral"
    margin = None
    if not within_band:
        favors = "side_a" if side_a.side_value > side_b.side_value else "side_b"
        margin = round(delta, 2)

    caveats = []
    for asset in side_a_assets + side_b_assets:
        if asset.caveat and asset.caveat not in caveats:
            caveats.append(asset.caveat)
        if asset.xvar is None:
            caveats.append(
                f"{asset.player_id}: unscored (PRE_MODEL) — excluded from trade math"
            )

    return TradeEvaluation(
        side_a=side_a,
        side_b=side_b,
        fairness_delta=round(delta, 2),
        within_parity_band=within_band,
        favors=favors,
        favors_xvar_margin=margin,
        decision_supported=False,
        caveats=caveats,
    )


def value_draft_pick(
    round_: int,
    pick_bucket: str,  # "early" (1–4) | "mid" (5–8) | "late" (9–12)
    position: str,
    age: float = 21.5,
) -> TradeAsset:
    """Score a pick via Engine A. No market data used."""
    SLOT_MAP = {"early": 3.0, "mid": 6.5, "late": 10.5}
    pick = SLOT_MAP.get(pick_bucket, 6.5)
    result = score_prospect(position, pick, float(round_), age)
    dvs = result.get("dynasty_value_score")
    repl = ENGINE_A_REPLACEMENT_DVS.get(position.upper(), 0.0)
    lambda_ = XVAR_LAMBDA_ENGINE_A.get(position.upper(), 1.0)
    xvar_val = round((dvs - repl) * lambda_, 2) if dvs is not None else None
    return TradeAsset(
        player_id=f"pick_{round_}_{pick_bucket}_{position}",
        xvar=xvar_val,
        dvs=dvs,
        dvs_engine="A",
        position=position.upper(),
        is_prospect=True,
        decision_supported=False,
        caveat=f"Draft pick estimate: {round_}.{pick_bucket} slot, {position}, age={age}",
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/contract/test_phase15_trade_lab.py -v
```

Expected: all pass

- [ ] **Step 6: Run full suite to verify no regressions**

```bash
python -m pytest --ignore=tests/test_prospect_ingestion.py --ignore=tests/contract/test_phase13_te_model_change.py -q
```

Expected: 690+ passed, 0 failed

- [ ] **Step 7: Commit**

```bash
git add src/dynasty_genius/trade_lab/ tests/contract/test_phase15_trade_lab.py
git commit -m "feat(phase15): Trade Lab evaluator — xVAR-sum parity with consolidation premium"
```

---

### Task 3: Trade Lab API Route

**Files:**
- Modify: `app/api/routes/trade.py` (add `POST /trade/evaluate` — do NOT remove existing `/trade/analyze`)
- Test: the integration tests in `tests/contract/test_trade_delta_status.py` must still pass

- [ ] **Step 1: Write the failing integration test**

Add to `tests/contract/test_phase15_trade_lab.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_evaluate_trade_endpoint_returns_evaluation():
    """POST /trade/evaluate returns TradeEvaluation with decision_supported=False."""
    payload = {
        "side_a": [{"player_id": "p1", "xvar": 20.0, "position": "WR", "dvs_engine": "B"}],
        "side_b": [{"player_id": "p2", "xvar": 25.0, "position": "QB", "dvs_engine": "B"}],
    }
    resp = client.post("/trade/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_supported"] is False
    assert "side_a" in data
    assert "side_b" in data
    assert "within_parity_band" in data
```

- [ ] **Step 2: Run test to verify it fails**

Expected: 404 or ImportError

- [ ] **Step 3: Add `POST /trade/evaluate` to `app/api/routes/trade.py`**

Add AFTER the existing `@router.post("/analyze")` endpoint (do NOT modify it):

```python
from src.dynasty_genius.trade_lab.evaluator import TradeAsset, TradeEvaluation, evaluate_trade
from pydantic import BaseModel

class TradeEvaluateRequest(BaseModel):
    side_a: list[dict]
    side_b: list[dict]

@router.post("/evaluate")
def evaluate_trade_endpoint(request: TradeEvaluateRequest) -> dict:
    """Evaluate a multi-asset trade using xVAR-sum parity.
    
    Accepts lists of asset dicts with at minimum: player_id, xvar, position.
    Returns TradeEvaluation with decision_supported=False.
    Market data must not enter this endpoint — xVAR is model-native.
    """
    side_a = [TradeAsset(**a) for a in request.side_a]
    side_b = [TradeAsset(**b) for b in request.side_b]
    result = evaluate_trade(side_a, side_b)
    return result.dict()
```

- [ ] **Step 4: Verify existing `/trade/analyze` still works**

```bash
python -m pytest tests/contract/test_trade_delta_status.py -v
```

Expected: all pass

- [ ] **Step 5: Run the new endpoint test**

```bash
python -m pytest tests/contract/test_phase15_trade_lab.py::test_evaluate_trade_endpoint_returns_evaluation -v
```

Expected: pass

- [ ] **Step 6: Commit**

```bash
git add app/api/routes/trade.py tests/contract/test_phase15_trade_lab.py
git commit -m "feat(phase15): POST /trade/evaluate endpoint — xVAR parity verdict"
```

---

### Task 4: dvs_pct Nightly Batch

**Files:**
- Create: `scripts/compute_dvs_pct_batch.py`
- Test: add to `tests/contract/test_phase15_trade_lab.py` (or create `tests/contract/test_phase15_dvs_pct.py`)

**NOTE:** Gemini created `scripts/compute_dvs_percentiles.py` which uses the training CSV — wrong input. The correct script takes a list of PVOs and computes percentile against `ACTIVE_B` population. Delete or ignore `compute_dvs_percentiles.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/contract/test_phase15_dvs_pct.py`:

```python
"""Phase 15 dvs_pct batch — spec section 5.14."""
from __future__ import annotations
from scripts.compute_dvs_pct_batch import compute_dvs_pct_batch
from src.dynasty_genius.models.player_value_object import PlayerValueObject


def _pvo(pos: str, dvs: float, grade: str = "ACTIVE_B") -> PlayerValueObject:
    return PlayerValueObject(
        player_id=f"test_{pos}_{dvs}",
        full_name="Test Player",
        position=pos,
        model_grade=grade,
        dynasty_value_score=dvs,
        signal_completeness=1.0,
    )


def test_dvs_pct_reference_population_active_b_only():
    """5.14: PRE_MODEL players are NOT in the reference population denominator."""
    pvos = [
        _pvo("WR", 90.0),   # rank 1 of 3 ACTIVE_B
        _pvo("WR", 60.0),   # rank 2 of 3 ACTIVE_B
        _pvo("WR", 30.0),   # rank 3 of 3 ACTIVE_B
        _pvo("WR", 50.0, grade="PRE_MODEL"),   # excluded from denominator
    ]
    compute_dvs_pct_batch(pvos)
    wr_pvos = [p for p in pvos if p.model_grade == "ACTIVE_B"]
    # Percentile formula: (rank - 1) / (N - 1) * 100
    # rank 1: (0) / 2 * 100 = 100.0
    # rank 2: (1) / 2 * 100 = 50.0
    # rank 3: (2) / 2 * 100 = 0.0
    sorted_pvos = sorted(wr_pvos, key=lambda x: x.dynasty_value_score, reverse=True)
    assert sorted_pvos[0].dvs_pct == pytest.approx(100.0)
    assert sorted_pvos[1].dvs_pct == pytest.approx(50.0)
    assert sorted_pvos[2].dvs_pct == pytest.approx(0.0)
    # PRE_MODEL player has no dvs_pct
    pre_model = next(p for p in pvos if p.model_grade == "PRE_MODEL")
    assert pre_model.dvs_pct is None


def test_dvs_pct_timestamp_set():
    """dvs_pct_as_of is set after batch runs."""
    pvos = [_pvo("QB", 75.0), _pvo("QB", 50.0)]
    compute_dvs_pct_batch(pvos)
    for p in pvos:
        assert p.dvs_pct_as_of is not None
```

- [ ] **Step 2: Run test to verify it fails**

Expected: ImportError (script doesn't exist)

- [ ] **Step 3: Create `scripts/compute_dvs_pct_batch.py`**

```python
"""Compute within-position dvs_pct for a list of PVOs.

Reference population: ACTIVE_B players with non-null dynasty_value_score.
Formula: (rank_desc - 1) / (N_pos - 1) * 100
Mutates pvos in-place: sets dvs_pct and dvs_pct_as_of.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.dynasty_genius.models.player_value_object import PlayerValueObject


def compute_dvs_pct_batch(pvos: List[PlayerValueObject]) -> None:
    """Set dvs_pct and dvs_pct_as_of on each PVO in-place."""
    now_utc = datetime.now(timezone.utc).isoformat()
    positions = {p.position.upper() for p in pvos}

    for pos in positions:
        active_b = [
            p for p in pvos
            if p.position.upper() == pos
            and p.model_grade == "ACTIVE_B"
            and p.dynasty_value_score is not None
        ]
        n = len(active_b)
        if n == 0:
            continue
        sorted_pop = sorted(active_b, key=lambda x: x.dynasty_value_score, reverse=True)
        for rank_0, pvo in enumerate(sorted_pop):
            pvo.dvs_pct = round((rank_0 / max(n - 1, 1)) * 100.0, 1) if n > 1 else 100.0
            pvo.dvs_pct_as_of = now_utc


if __name__ == "__main__":
    print("compute_dvs_pct_batch: import and call compute_dvs_pct_batch(pvos) directly.")
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/contract/test_phase15_dvs_pct.py -v
```

Expected: all pass

- [ ] **Step 5: Run full suite**

```bash
python -m pytest --ignore=tests/test_prospect_ingestion.py --ignore=tests/contract/test_phase13_te_model_change.py -q
```

Expected: 690+ passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add scripts/compute_dvs_pct_batch.py tests/contract/test_phase15_dvs_pct.py
git commit -m "feat(phase15): dvs_pct nightly batch — within-position percentile against ACTIVE_B population"
```

---

### Task 5: xVAR Contract Tests (Phase 15.1 and 15.2)

**Files:**
- Create: `tests/contract/test_phase15_xvar.py`
- Create: `tests/contract/test_phase15_blend.py`

These test the full spec tests 5.1, 5.2, 5.4, 5.8, 5.9, 5.10, 5.11.

**NOTE:** `tests/contract/test_phase15_valuation.py` has 3 tests from Gemini that cover parts of 5.1, 5.2, 5.8. Write the remaining tests to fill gaps per spec.

- [ ] **Step 1: Write `tests/contract/test_phase15_xvar.py`**

```python
"""Phase 15 xVAR contract tests — spec sections 5.1, 5.2, 5.4, 5.11."""
from __future__ import annotations
import pytest
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.engine_b_contract import (
    XVAR_LAMBDA_ENGINE_B, XVAR_LAMBDA_ENGINE_A, ENGINE_B_REPLACEMENT_DVS, ENGINE_A_REPLACEMENT_DVS,
)


def _mock_identity(position: str, is_prospect: bool = False) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test", full_name="Test", position=position,
        is_prospect=is_prospect, verification_status="VERIFIED_NFL_DRAFT"
    )


def test_xvar_formula_wr():
    """5.1: WR DVS=100, replacement=60.6, Λ=1.000 → xVAR = (100-60.6)*1.0 = 39.4"""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    # DVS = 100.0 (WR P90 = 14.5), replacement = ENGINE_B_REPLACEMENT_DVS["WR"] = 60.6
    expected_xvar = round((100.0 - ENGINE_B_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_B["WR"], 2)
    assert pvo.xvar == pytest.approx(expected_xvar, abs=0.1)
    assert pvo.xvar_anchor == "WR"


def test_xvar_formula_qb_higher_than_wr_at_same_dvs():
    """5.1: QB Λ=1.386 > WR Λ=1.000 → QB xVAR > WR xVAR at same VAR."""
    wr_id = _mock_identity("WR")
    qb_id = _mock_identity("QB")
    # Give both same raw DVS above replacement
    wr_pvo = assemble_pvo(wr_id, {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 14.5, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024,
    })
    qb_pvo = assemble_pvo(qb_id, {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 20.1, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024,
    })
    assert qb_pvo.xvar is not None and wr_pvo.xvar is not None
    # Both at DVS=100 but QB Λ > WR Λ → QB xVAR > WR xVAR
    assert qb_pvo.xvar > wr_pvo.xvar


def test_engine_a_lambda_applied_for_prospect():
    """5.2: WR prospect dvs_engine='A' → xvar_anchor='WR', Engine A Λ used."""
    identity = _mock_identity("WR", is_prospect=True)
    pvo = assemble_pvo(identity, {"pick": 5.0, "round": 1.0, "age": 21.0})
    assert pvo.dvs_engine == "A"
    assert pvo.xvar_anchor == "WR"
    # Engine A replacement used, not Engine B replacement
    if pvo.xvar is not None and pvo.dynasty_value_score is not None:
        expected = round((pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_A["WR"], 2)
        assert pvo.xvar == pytest.approx(expected, abs=0.1)


def test_xvar_ceiling_bound_when_clamped():
    """5.4: dvs_clamped=True → xvar_ceiling_bound=True."""
    identity = _mock_identity("QB")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 30.0, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_clamped is True
    assert pvo.xvar_ceiling_bound is True


def test_te_xvar_computable_decision_supported_false():
    """5.11: TE has computable xVAR but decision_supported=False."""
    identity = _mock_identity("TE")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 9.0, "engine": "test_v2"},
        "games_t": 10, "feature_season": 2024,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.xvar is not None
    assert pvo.decision_supported is False
    assert any("TE market superiority gate deferred" in c for c in pvo.caveats)
```

- [ ] **Step 2: Write `tests/contract/test_phase15_blend.py`**

```python
"""Phase 15 Bayesian blend contract tests — spec sections 5.8, 5.9, 5.10."""
from __future__ import annotations
import pytest
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.engine_b_contract import DVS_BLEND_K


def _mock_identity(position: str) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test", full_name="Test", position=position,
        verification_status="VERIFIED_NFL_DRAFT"
    )


def test_blend_weight_monotonicity_wr():
    """5.8: WR k_pos=5 → w_B at games=1 < games=4 < games=7."""
    k = DVS_BLEND_K["WR"]
    w1 = 1 / (1 + k)
    w4 = 4 / (4 + k)
    w7 = 7 / (7 + k)
    assert w1 < w4 < w7
    assert w1 == pytest.approx(1/6, rel=1e-3)
    assert w4 == pytest.approx(4/9, rel=1e-3)
    assert w7 == pytest.approx(7/12, rel=1e-3)


def test_blend_dvs_engine_when_both_present():
    """5.9: 1 ≤ games_t ≤ 7 with Engine A and B inputs → dvs_engine='blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        "pick": 10.0, "round": 1.0, "age": 22.0,
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "blend"
    assert pvo.dvs_blend_weight_b is not None
    k = DVS_BLEND_K["WR"]
    expected_w = 4 / (4 + k)
    assert pvo.dvs_blend_weight_b == pytest.approx(expected_w, rel=1e-3)


def test_blend_single_engine_fallback():
    """5.10: Dead Window with no Engine A inputs → dvs_engine != 'blend'."""
    identity = _mock_identity("WR")
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
        "games_t": 4,
        "feature_season": 2024,
        # No pick/round/age → Engine A unavailable
    }
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine != "blend"
    assert pvo.dynasty_value_score is None
```

- [ ] **Step 3: Run all new tests**

```bash
python -m pytest tests/contract/test_phase15_xvar.py tests/contract/test_phase15_blend.py -v
```

**IMPORTANT:** `test_xvar_ceiling_bound_when_clamped` and `test_engine_a_lambda_applied_for_prospect` may reveal that `xvar_ceiling_bound` is not yet being set in the assembler. The assembler currently computes `xvar` but does not set `xvar_ceiling_bound`. Add this to the assembler's xVAR block:

```python
xvar_ceiling_bound = bool(dvs_clamped_val) if dvs_clamped_val is not None else None
```

And pass `xvar_ceiling_bound=xvar_ceiling_bound` to the PVO constructor.

- [ ] **Step 4: Fix assembler if xvar_ceiling_bound is not set**

In `src/dynasty_genius/pvo_assembler.py`, the xVAR block currently computes `xvar` and `xvar_anchor`. Add `xvar_ceiling_bound`:

```python
xvar_ceiling_bound: Optional[bool] = None  # initialize with other vars

# In the xVAR computation block:
xvar_ceiling_bound = bool(dvs_clamped_val) if dvs_clamped_val is not None else None
```

And add to the PVO constructor call:
```python
xvar_ceiling_bound=xvar_ceiling_bound,
```

- [ ] **Step 5: Run full suite**

```bash
python -m pytest --ignore=tests/test_prospect_ingestion.py --ignore=tests/contract/test_phase13_te_model_change.py -q
```

Expected: 700+ passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add tests/contract/test_phase15_xvar.py tests/contract/test_phase15_blend.py src/dynasty_genius/pvo_assembler.py
git commit -m "feat(phase15): xVAR and blend contract tests; fix xvar_ceiling_bound population"
```

---

### Task 6: Ledger, AGENT_SYNC, and Cleanup

- [ ] **Step 1: Delete Gemini's misplaced/broken artifacts**

```bash
rm -f scripts/compute_dvs_percentiles.py  # wrong input source, replaced by compute_dvs_pct_batch.py
```

- [ ] **Step 2: Update AGENT_SYNC.md**

Mark Phase 15 Workstreams 1–3 and 4 complete. Note blend-k gate pending David review.

- [ ] **Step 3: Write ledger entry `docs/agent-ledger/2026-05-16.md`**

Document: Phase 15 cleanup, xVAR, blend, trade lab, dvs_pct, Pydantic v1 compat fixes.

- [ ] **Step 4: Final commit**

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-16.md
git commit -m "docs(phase15): ledger and AGENT_SYNC updates — phase 15 workstreams complete"
```

---

## Hard Constraints (Governance)

- `TRADE_PARITY_BAND` and `NOISE_BAND` are separate constants — NEVER alias them
- `decision_supported = False` on all surfaces including `TradeEvaluation`
- Market data (KTC, FantasyCalc, ADP) must not enter xVAR or trade math
- Engine A Λ applies when `dvs_engine in ("A", "blend")` — NOT Engine B Λ
- TE xVAR is computable but must carry G3-deferred caveat; no cross-positional ranking widget
- DVS scale stays 0–100 float (no expansion to 0–1000)
- Engine B P90 constants frozen at May 2026 values
- `ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset()` — TE is ACTIVE_B
