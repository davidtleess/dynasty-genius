---
document: Phase 15 Trade Lab & Cross-Positional Valuation
version: 1.0.0
status: APPROVED
date: 2026-05-16
owner: David
prepared_by: Claude
phase: 15
evidence_artifacts:
  - app/data/backtest/phase14/var_batch_20260516_190328.json
  - app/data/backtest/phase14/dvs_calibration_audit_20260516_190356.json
decision_notes:
  - docs/strategies/Dynasty Genius Phase 15 Research Brief.md
  - docs/strategies/compass_artifact_wf-9dd1ef2c-a9b6-4201-b712-fbf90658ca6b_text_markdown.md
  - docs/strategies/Dynasty Genius Framework Adoption.md
governance_read:
  - docs/governance/02-agent-operating-loop.md
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - AGENT_SYNC.md
---

# Phase 15 — Trade Lab & Cross-Positional Valuation

Phase 15 — Production Implementation Authorization

---

## 1. Decision Summary

Four changes are jointly authorized:

1. **Cross-positional VAR (xVAR):** introduce a common "WR-equivalent VAR points" unit derived from Engine B P90 ratios that makes QB, RB, WR, and TE value comparable without touching market data.

2. **Trade Lab API v0:** implement `POST /trade/evaluate`, evaluating multi-asset trades as xVAR-sum parity with a mild geometric consolidation premium. FastAPI endpoint only; no UI in Phase 15.

3. **Dead Window Bayesian blend:** replace the hard Engine A/B switch at `games_t = 8` with a precision-weighted blend that smoothly transitions Engine A prior toward Engine B signal as NFL games accumulate.

4. **`dvs_pct` auxiliary field:** compute within-position percentile rank nightly against the active Engine B population and store on the PVO.

**Architecture decisions locked:**
- Trade currency: xVAR (model-native, WR-equivalent VAR points). Reject E27 — it requires a market-anchored pick value.
- Cross-positional multiplier: `Λ_pos = P90[pos] / P90[WR]`, derived from frozen Engine B P90 constants. Multiplier is 1.386× for QB, not 2.5–3.0× — the larger figure requires market data as input.
- DVS scale: stays 0–100 float (one decimal place). Reject 0–1000.
- Fairness tolerance: new constant `TRADE_PARITY_BAND = 0.10`, separate from `NOISE_BAND`. These must be independently adjustable after mid-July 2026.
- Blend k_pos defaults (QB=6, RB=5, WR=5, TE=7) are empirical estimates that **must be fitted against Engine B per-position residual variance before locking**. The spec authorizes implementation with these defaults; the k_pos validation step is a required gate before Workstream 15.2 is considered complete.
- TE xVAR is computable but must not surface in any ranking widget or trade verdict without the G3-deferred caveat banner. `decision_supported` remains `False`.

---

## 2. Evidence Basis

### Research Inputs

Three research artifacts were reviewed: the Phase 15 Research Brief (questions), a Compass synthesis report (third-opinion reconciliation of the Response Brief), and a Framework Adoption evaluation report. The Compass synthesis is the primary technical source. The Framework Adoption report contributed governance framing, Engine A threshold tables, and aging cliff architecture confirmation.

**Two factual errors in the Framework Adoption report — corrected here and must not propagate:**
- Report claims DVS was expanded to 0–1000 in Phase 14. It was not. Phase 14 kept 0–100.
- Report claims TE remains on "experimental v1 fallback." TE was promoted to `ACTIVE_B` in Phase 13.3. `ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset()`.

### Phase 14 VAR Artifact — Prerequisite Note

The Phase 14 VAR batch (`var_batch_20260516_190328.json`) was computed against the training CSV's historical outcomes (`avg_ppg_t1_t2`), not against actual model inference predictions. This produces an approximate replacement baseline. Before xVAR can be reliably computed in Workstream 15.1, `scripts/compute_var_batch.py` must be re-run against a full Engine B inference pass over the active player population (not the training CSV). See Section 3.1 for the prerequisite gate.

The TE replacement PPG of 9.76 (above the TE P90 ceiling of 9.4) in the Phase 14 artifact is a direct symptom of this — a single-season training-data proxy produced an outlier. A proper inference run will resolve it.

---

## 3. Authorized Changes

### 3.1 New Constants — `engine_b_contract.py`

Add to `src/dynasty_genius/models/engine_b_contract.py`:

```python
# ── Cross-Positional xVAR Multipliers ────────────────────────────────────────
# Λ_pos = P90[pos] / P90[WR_anchor] for each engine.
# WR is the anchor (Λ_WR = 1.000) because WR is the deepest roster position.
# Engine B multipliers use ENGINE_B_P90_PPG constants (frozen May 2026).
# Engine A multipliers use Engine A P90 constants from scoring/engine_a.py _P90_PPG.
# Apply Engine B Λ when dvs_engine == "B"; Engine A Λ when dvs_engine == "A" or "blend".
XVAR_ANCHOR_POSITION: str = "WR"

XVAR_LAMBDA_ENGINE_B: dict[str, float] = {
    "QB": 1.386,   # 20.1 / 14.5
    "RB": 1.083,   # 15.7 / 14.5
    "WR": 1.000,   # anchor
    "TE": 0.648,   # 9.4 / 14.5
}

XVAR_LAMBDA_ENGINE_A: dict[str, float] = {
    "QB": 1.315,   # 16.7 / 12.7
    "RB": 1.150,   # 14.6 / 12.7
    "WR": 1.000,   # anchor
    "TE": 0.717,   # 9.1 / 12.7
}

# ── Trade Evaluation Constants ────────────────────────────────────────────────
# TRADE_PARITY_BAND: fractional tolerance for trade fairness verdict.
# Separate from NOISE_BAND (veteran divergence suppression) — these values
# must be independently adjustable. Do not alias NOISE_BAND here.
TRADE_PARITY_BAND: float = 0.10

# Geometric consolidation factor: each additional starter-quality asset
# (xVAR > 0) in a package reduces that side's total by κ, floored at 0.80.
CONSOLIDATION_KAPPA: float = 0.04
CONSOLIDATION_FLOOR: float = 0.80

# ── Dead Window Bayesian Blend Constants ──────────────────────────────────────
# k_pos: effective number of games at which Engine B likelihood equals Engine A prior.
# w_B(n) = n / (n + k_pos); higher k_pos = slower transition to Engine B.
# DEFAULTS: educated estimates from fantasy football week-to-week residual variance.
# REQUIRED: fit these from Engine B per-position residual variance before Phase 15.2
# ships. Do not lock without a validated residual analysis artifact.
DVS_BLEND_K: dict[str, int] = {
    "QB": 6,
    "RB": 5,
    "WR": 5,
    "TE": 7,   # TE shrinks slowest — highest small-sample noise
}
```

### 3.2 PVO Schema — New Fields

Add to `PlayerValueObject` in `src/dynasty_genius/models/player_value_object.py`:

```python
# ── Cross-positional VAR ──────────────────────────────────────────────────────
xvar: Optional[float] = None              # WR-equivalent VAR points
xvar_lambda: Optional[float] = None      # Λ_pos applied at scoring time
xvar_anchor: Optional[str] = None        # anchor position ("WR")
xvar_ceiling_bound: Optional[bool] = None  # True if DVS was clamped before xVAR

# ── Within-position percentile ────────────────────────────────────────────────
dvs_pct: Optional[float] = None          # 0–100, Engine B active population
dvs_pct_as_of: Optional[str] = None     # UTC ISO timestamp of last batch run

# ── Bayesian blend provenance ─────────────────────────────────────────────────
dvs_blend_weight_b: Optional[float] = None  # w_B when in blend window; null outside
```

Note: `dvs_engine` already exists and now supports a third value: `"blend"`. No type change needed (it is `Optional[str]`).

### 3.3 xVAR Computation — `pvo_assembler.py`

Compute xVAR immediately after `dynasty_value_score` is finalized and `value_above_replacement` (replacement-level DVS) is available. Add imports:

```python
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_BY_POSITION,
    ENGINE_B_P90_PPG,
    ENGINE_B_MIN_GAMES_T,
    XVAR_LAMBDA_ENGINE_B,
    XVAR_LAMBDA_ENGINE_A,
    XVAR_ANCHOR_POSITION,
    TRADE_PARITY_BAND,
    CONSOLIDATION_KAPPA,
    CONSOLIDATION_FLOOR,
    DVS_BLEND_K,
)
```

xVAR logic (after DVS and replacement DVS are both available):

```python
# xVAR: cross-positional VAR in WR-equivalent points.
# Requires both dynasty_value_score and replacement_dvs to be non-null.
# Applies the correct Λ based on which engine produced the DVS.
xvar_val: Optional[float] = None
xvar_lambda_val: Optional[float] = None
xvar_anchor_val: Optional[str] = None
xvar_ceiling_bound_val: Optional[bool] = None

replacement_dvs = features.get("replacement_dvs")  # populated by batch scoring path

if dynasty_value_score is not None and replacement_dvs is not None:
    if dvs_engine == "B":
        _lambda = XVAR_LAMBDA_ENGINE_B.get(pos_upper)
    else:
        # Engine A or blend: use Engine A Λ (Engine A P90 denominator)
        _lambda = XVAR_LAMBDA_ENGINE_A.get(pos_upper)

    if _lambda is not None:
        xvar_val = round((dynasty_value_score - replacement_dvs) * _lambda, 2)
        xvar_lambda_val = _lambda
        xvar_anchor_val = XVAR_ANCHOR_POSITION
        xvar_ceiling_bound_val = bool(dvs_clamped_val)
```

**TE governance constraint:** xVAR is computed for TE players. However, any route or surface that ranks or sorts by xVAR must exclude TE from cross-positional rankings (or display TE with the G3-deferred caveat banner) until the market superiority gate clears.

### 3.4 Dead Window Bayesian Blend — `pvo_assembler.py`

Replace the current Dead Window hard-fallback block (lines ~364–386) with the precision-weighted blend. The blend requires computing Engine B DVS independently of the games gate, then merging with Engine A.

**Prerequisite:** Both `engine_a_result` and `engine_b_resolved` must be non-null for blending to activate. If only one engine has data, the existing single-engine path applies (no change).

```python
# Dead Window Bayesian blend: 1 ≤ games_t ≤ ENGINE_B_MIN_GAMES_T - 1
# Replaces the hard Engine A fallback with a precision-weighted blend.
if engine_b_resolved and _below_games_gate:
    _k = DVS_BLEND_K.get(pos_upper, 5)
    _n = int(float(games_t))  # games_t is guaranteed non-None here

    if engine_a_result and projection_2y is not None and _b_p90 is not None:
        # Compute Engine B DVS independently (ignoring games gate for blend only)
        _dvs_b_raw = projection_2y / _b_p90 * 100.0
        _dvs_b = round(min(100.0, max(0.0, _dvs_b_raw)), 1)
        _dvs_a = engine_a_result["dynasty_value_score"]

        # Precision-weighted blend
        _w_b = _n / (_n + _k)
        _w_a = 1.0 - _w_b
        dynasty_value_score = round(_w_a * _dvs_a + _w_b * _dvs_b, 1)
        dvs_engine = "blend"
        dvs_blend_weight_b_val = round(_w_b, 3)
        # Provenance: use Engine A P90 ref (prior dominates early in blend window)
        dvs_p90_ref_val = _P90_PPG.get(pos_upper)
        dvs_clamped_val = dynasty_value_score >= 100.0

        _blend_caveat = (
            f"Low professional sample (games={_n}) — "
            f"Engine A/B blend active (w_B={dvs_blend_weight_b_val:.2f}); "
            "interpret with caution"
        )
        if _blend_caveat not in caveats:
            caveats.append(_blend_caveat)

    else:
        # Only one engine available — fall back to Engine A prior with original caveat
        if engine_a_result:
            dynasty_value_score = engine_a_result["dynasty_value_score"]
            dvs_engine = "A"
            dvs_p90_ref_val = _P90_PPG.get(pos_upper)
            dvs_clamped_val = engine_a_result["dynasty_value_score"] >= 100.0
        _dw_caveat = (
            "Insufficient professional season data — Engine A prospect score used as prior"
        )
        if _dw_caveat not in caveats:
            caveats.append(_dw_caveat)
```

Pass `dvs_blend_weight_b_val` to the PVO constructor (initialize as `None` before the Engine A/B blocks).

### 3.5 Trade Lab Evaluator — New Module

Create `src/dynasty_genius/trade_lab/evaluator.py`:

**Data model:**

```python
class TradeAsset(BaseModel):
    player_id: str
    xvar: Optional[float]          # None = PRE_MODEL / unscored
    dvs: Optional[float]
    dvs_engine: Optional[str]
    position: str
    is_prospect: bool = False
    caveat: Optional[str] = None   # required for TE G3-deferred assets

class TradeSide(BaseModel):
    assets: list[TradeAsset]
    xvar_sum: float                # sum of max(xvar, 0) for starter-quality assets
    consolidation_factor: float    # geometric decay applied
    side_value: float              # xvar_sum × consolidation_factor

class TradeEvaluation(BaseModel):
    side_a: TradeSide
    side_b: TradeSide
    fairness_delta: float          # |side_a.side_value − side_b.side_value|
    within_parity_band: bool       # fairness_delta ≤ TRADE_PARITY_BAND × max(sides)
    favors: Optional[str]          # "side_a" | "side_b" | "neutral"
    favors_xvar_margin: Optional[float]
    decision_supported: bool = False
    caveats: list[str]
```

**Core logic:**

```python
def _consolidation_factor(n_starter_assets: int) -> float:
    """Geometric decay for multi-asset packages. Bench fillers (xVAR ≤ 0) not counted."""
    if n_starter_assets <= 1:
        return 1.0
    raw = 1.0 - CONSOLIDATION_KAPPA * (n_starter_assets - 1)
    return max(CONSOLIDATION_FLOOR, raw)

def evaluate_side(assets: list[TradeAsset]) -> TradeSide:
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
    side_a_assets: list[TradeAsset],
    side_b_assets: list[TradeAsset],
) -> TradeEvaluation:
    side_a = evaluate_side(side_a_assets)
    side_b = evaluate_side(side_b_assets)
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
```

**Draft pick valuation (locked-constraint-safe):**

When a trade side includes a draft pick asset (no existing player_id in the PVO store), create a synthetic prospect via Engine A:

```python
def value_draft_pick(
    round_: int,
    pick_bucket: str,  # "early" (1–4) | "mid" (5–8) | "late" (9–12)
    position: str,
    age: float = 21.5,  # modal rookie draft age
) -> TradeAsset:
    """Score a pick via Engine A with age prior. No market data used."""
    SLOT_MAP = {"early": 3.0, "mid": 6.5, "late": 10.5}
    pick = SLOT_MAP.get(pick_bucket, 6.5)
    result = score_prospect(position, pick, float(round_), age)
    ...
```

The `age=21.5` prior is the modal NFL rookie draft age (historical aggregate). If the pick slot is known (e.g., 1.07 slotted), use the exact slot.

### 3.6 Trade Lab Route — `app/api/routes/trade.py`

Create new route file:

```python
@router.post("/trade/evaluate")
def evaluate_trade_endpoint(request: TradeRequest) -> TradeEvaluation:
    ...
```

Request body: `{side_a: [asset_id...], side_b: [asset_id...]}`. The route resolves each asset_id to its current PVO, extracts xVAR, and calls `evaluate_trade`. Returns `TradeEvaluation` with `decision_supported=False`.

**Internal trade verdicts are permitted now.** The NOISE_BAND lock (mid-July 2026) prohibits market-divergence flags, not internal model comparisons. The response may include "favors side_a by 14.2 xVAR." It must not include any language comparing DVS to KTC, FantasyCalc, or ADP.

### 3.7 `dvs_pct` Nightly Batch — `scripts/compute_dvs_pct_batch.py`

**Definition:**
```
dvs_pct[player] = (rank_within_position_descending − 1) / (N_position_active − 1) × 100
```

- Reference population: active Engine B players at the position (same population that defines `replacement_dvs`). Prospects and Dead Window blends are ranked against this Engine B population — they compete on the same position scale even if their DVS came from Engine A.
- Computed nightly. Store `dvs_pct` (float) and `dvs_pct_as_of` (UTC ISO timestamp) in the PVO store or supplement table.
- Small position groups (TE) have coarse percentile granularity by construction — acceptable, document but do not fix.

### 3.8 Files That Must Not Change

- Engine A/B model artifacts (`qb_v2.pkl`, `rb_v2.pkl`, `wr_v2.pkl`, `te_v3.pkl`) or training pipelines
- Engine B P90 constants (`ENGINE_B_P90_PPG`) — frozen at May 2026 values
- `ENGINE_B_EXPERIMENTAL_POSITIONS` — remains `frozenset()`
- `NOISE_BAND` — locked at 0.10 until mid-July 2026; **not the same as `TRADE_PARITY_BAND`**
- `decision_supported` on any surface — remains `False`
- Market overlay join order — market data joins the PVO after all model scoring, never before
- Walk-forward harness or backtest infrastructure

---

## 4. Prerequisite Gate — Inference-Time VAR Baseline

**Phase 15.1 is blocked until this gate clears.**

Re-run `scripts/compute_var_batch.py` against a full Engine B inference pass over the active player population (not the training CSV). The script already supports this when passed a DataFrame with a `predicted_avg_ppg_t1_t2` column. The gate requires:

1. Score all active Engine B-eligible players using `predict_player_season_b`.
2. Pass the scored DataFrame (with `predicted_avg_ppg_t1_t2`) to `compute_var_batch`.
3. Verify TE replacement PPG is ≤ 9.4 (the TE P90 ceiling). If it still exceeds the ceiling, log the anomaly and use DVS_repl_TE = 100.0 with an explicit artifact note.
4. Write the new artifact and record the gate pass in `docs/validation/phase15-var-baseline-refresh.md`.

This gate replaces the approximated Phase 14 VAR baselines with model-native replacement-level DVS values, which are required for xVAR to be meaningful.

---

## 5. Required Tests

### 5.1 Engine B xVAR Formula

For a WR with DVS=80 and replacement_dvs=60:
- `xvar = (80 − 60) × 1.000 = 20.0`
- `xvar_lambda = 1.000`
- `xvar_anchor = "WR"`

For a QB with DVS=80 and replacement_dvs=60:
- `xvar = (80 − 60) × 1.386 = 27.72`

### 5.2 Engine A Λ Applied for Prospects

For a WR prospect with `dvs_engine="A"`:
- `xvar_lambda = XVAR_LAMBDA_ENGINE_A["WR"] = 1.000` (same anchor)

For a QB prospect with `dvs_engine="A"`:
- `xvar_lambda = XVAR_LAMBDA_ENGINE_A["QB"] = 1.315` (not 1.386)

### 5.3 Sub-Replacement Assets Contribute Zero to Trade Math

For a player with `xvar = −5.0`: `max(xvar, 0) = 0`. Trade side value unchanged by adding them.

### 5.4 xvar_ceiling_bound

For a player with `dvs_clamped=True` (raw DVS exceeded 100): `xvar_ceiling_bound=True`.

### 5.5 Consolidation Factor

- 1-asset side: factor = 1.000
- 2-asset side (2 starters): factor = `1.0 − 0.04 × 1 = 0.960`
- 3-asset side (3 starters): factor = `1.0 − 0.04 × 2 = 0.920`
- 6-asset side: factor = `max(0.80, 1.0 − 0.04 × 5) = max(0.80, 0.80) = 0.800` (floor)

### 5.6 Trade Fairness — Within Band

side_a_value = 30.0, side_b_value = 32.0, delta = 2.0.
`within_parity_band = 2.0 ≤ 0.10 × 32.0 = 3.2` → True.

### 5.7 Trade Fairness — Outside Band

side_a_value = 20.0, side_b_value = 40.0, delta = 20.0.
`within_parity_band = 20.0 ≤ 0.10 × 40.0 = 4.0` → False. `favors = "side_b"`.

### 5.8 Bayesian Blend — Weight Monotonicity

For a WR (k_pos=5): w_B at games_t=1 < w_B at games_t=4 < w_B at games_t=7.
- games_t=1: w_B = 1/6 = 0.167
- games_t=4: w_B = 4/9 = 0.444
- games_t=7: w_B = 7/12 = 0.583

### 5.9 Bayesian Blend — dvs_engine Provenance

For a player with `1 ≤ games_t ≤ 7` and both Engine A and Engine B data available:
- `dvs_engine == "blend"`
- `dvs_blend_weight_b` is non-null and equals `games_t / (games_t + k_pos[position])`
- Blend caveat is present in `caveats`

### 5.10 Bayesian Blend — Single Engine Fallback

For a Dead Window player with Engine B data but no Engine A data (no pick/round/age):
- `dvs_engine != "blend"` (blend requires both engines)
- Original Dead Window caveat still present

### 5.11 TE xVAR Computable but Decision-Supported False

For a TE with `model_grade="ACTIVE_B"` and non-null DVS:
- `xvar` is non-null
- `decision_supported == False`
- G3-deferred caveat present

### 5.12 Draft Pick Valuation Uses Engine A

For a 2027 1st-round pick (mid bucket, WR, age=21.5):
- Asset returned has `dvs_engine == "A"`
- `is_prospect == True`
- `decision_supported == False`

### 5.13 TRADE_PARITY_BAND Is Not NOISE_BAND

Assert `TRADE_PARITY_BAND` and `NOISE_BAND` are separate constants. Changing one must not affect the other.

### 5.14 dvs_pct Reference Population

Assert `dvs_pct` is computed only against active Engine B players (those with `model_grade == "ACTIVE_B"` and non-null `dynasty_value_score`). PRE_MODEL players are not in the reference population denominator.

---

## 6. Governance Constraints

- `TRADE_PARITY_BAND = 0.10` is a separate constant from `NOISE_BAND = 0.10`. They must never be aliased. Reason: NOISE_BAND governs veteran market-divergence flag suppression (a UI governance constraint tied to mid-July 2026 recalibration). TRADE_PARITY_BAND governs trade math parity tolerance. Both start at 0.10 but must be independently adjustable.
- xVAR is computed using Engine B Λ when `dvs_engine == "B"`, and Engine A Λ when `dvs_engine == "A"` or `"blend"`. Do not mix Engine A DVS with Engine B Λ.
- TE xVAR must not surface in cross-positional ranking widgets without the G3-deferred caveat banner. It may appear in per-asset trade breakdowns with the caveat string.
- Internal trade verdicts ("model favors side A by X xVAR") are permitted now. Market-divergence comparisons (DVS vs KTC, model vs market) remain suppressed until NOISE_BAND is released (mid-July 2026).
- DVS scale stays 0–100 float (one decimal place). No expansion to 0–1000 in Phase 15.
- `decision_supported` remains `False` on all surfaces and on every `TradeEvaluation` response.
- DVS_BLEND_K constants (QB=6, RB=5, WR=5, TE=7) must be validated against Engine B per-position residual variance before Phase 15.2 is considered complete. The validation artifact must be written to `docs/validation/phase15-blend-k-validation.md` and reviewed by David before k_pos values are locked.
- Market data (KTC, FantasyCalc, ADP, any consensus value) must not enter xVAR math, trade evaluation math, or any Engine A/B model feature at any point.

---

## 7. Implementation Sequence

### Prerequisite: VAR Baseline Refresh

Run `compute_var_batch.py` against Engine B inference outputs. Verify TE replacement PPG ≤ TE P90. Write `docs/validation/phase15-var-baseline-refresh.md`. **Do not begin Workstream 15.1 until this passes.**

### Workstream 15.1 — Cross-Positional Architecture (xVAR)

1. Add constants (`XVAR_LAMBDA_ENGINE_B`, `XVAR_LAMBDA_ENGINE_A`, `XVAR_ANCHOR_POSITION`, `TRADE_PARITY_BAND`, `CONSOLIDATION_KAPPA`, `CONSOLIDATION_FLOOR`, `DVS_BLEND_K`) to `engine_b_contract.py`.
2. Add `xvar`, `xvar_lambda`, `xvar_anchor`, `xvar_ceiling_bound`, `dvs_pct`, `dvs_pct_as_of`, `dvs_blend_weight_b` to `PlayerValueObject`.
3. Implement xVAR computation in `pvo_assembler.py` (Section 3.3).
4. Update PVO constructor call to pass new fields.
5. Run full test suite. Tests 5.1–5.4 and 5.11 and 5.13 must pass. No existing tests may regress.

### Workstream 15.2 — Bayesian Dead Window Blend

6. Validate k_pos constants against Engine B per-position residual variance. Write `docs/validation/phase15-blend-k-validation.md`. **Gate: David reviews and approves k_pos values before step 7.**
7. Replace Dead Window hard-fallback block in `pvo_assembler.py` (Section 3.4).
8. Run full test suite. Tests 5.8–5.10 must pass. No existing tests may regress. Verify existing Dead Window tests (Phase 14 tests 5.4 and 5.5) still pass under the new blend path.

### Workstream 15.3 — Trade Lab API v0

9. Create `src/dynasty_genius/trade_lab/evaluator.py` (Section 3.5).
10. Create `app/api/routes/trade.py` with `POST /trade/evaluate` (Section 3.6).
11. Register route in the FastAPI app.
12. Run full test suite. Tests 5.5–5.7 and 5.12–5.13 must pass.

### Workstream 15.4 — `dvs_pct` Nightly Batch

13. Create `scripts/compute_dvs_pct_batch.py` (Section 3.7).
14. Run full test suite. Test 5.14 must pass.
15. Update AGENT_SYNC.md and daily ledger entry.

---

## 8. Out of Scope for Phase 15

- Region-dependent xVAR multipliers (Λ as a function of DVS region) — Phase 16
- E27 trade currency — permanently rejected as market-dependent
- 2.5–3.0× QB Superflex premium multiplier — rejected; unsupported and imports market data
- DVS scale expansion to 0–1000 — rejected
- Expected-wins-above-replacement parity (requires league-mate roster modeling) — Phase 17+
- UI for Trade Lab — Phase 16 (API endpoint only in Phase 15)
- Veteran market-divergence flags in Trade Lab output — post-NOISE_BAND (mid-July 2026)
- TE G3 market superiority gate — future validation cycle
- Full hierarchical Bayesian blend model — Phase 16+ (precision-weighted blend captures ~90% of the value)
- `dvs_pct` as a model input to trade math — display/UI context only
- PFF grades as model features — permanently banned
- Engine A/B retraining — separate phases
- Cross-engine isotonic remapping of Engine A DVS onto Engine B scale — requires 2024–2025 cohorts to age through both engines; not possible until end of 2026 season
