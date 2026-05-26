# Draft Pick Valuation (Dynasty Rookie Slots) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
> **Cockpit note:** This project runs a TMUX Codex-test-driver / Claude-implementer loop. In that model, Codex authors each failing contract test (the "Write the failing test" steps) and Claude implements to green. The test code below is the contract to satisfy.

**Goal:** Value future/unknown dynasty rookie draft picks in `xVAR` (the unit players already use) via a versioned historical realized-value-by-slot curve, replacing the fake-player `value_draft_pick`.

**Architecture:** A build script rolls `app/data/training/prospects_with_outcomes.csv` (mature 2015–2022 classes) into a versioned curve artifact using David's "first-36-skill-players-in-NFL-order = FF rookie board" bridge, converting each player's realized `y24_ppg → DVS → xVAR` with their actual position constants and aggregating xVAR per FF slot (with an SF-QB ordering knob). A pure `value_pick()` function reads that artifact. Future-pick xVAR is surfaced in PVO but excluded from team-strength aggregates. Backend only; frontend HOLD intact.

**Tech Stack:** Python 3.14, pandas, Pydantic v2, pytest. Constants: P90 from `scoring/engine_a.py`, replacement/λ from `models/engine_b_contract.py`.

**Spec:** `docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md`

---

## File Structure

- **Create** `src/dynasty_genius/trade_lab/draft_pick_valuation.py` — pure valuation: `PickValue` model, `load_curve()`, `value_pick()`. Reads the curve artifact only; no model/PVO/market imports.
- **Create** `scripts/build_draft_pick_value_curve.py` — builds the versioned curve artifact from the training CSV (mature-year gate, 36-skill bridge, per-position xVAR, slot aggregation, monotonic smoothing, SF-QB ordering knob, stats).
- **Create** `app/data/valuation/draft_pick_value_curve_v1.json` — generated, versioned curve artifact (committed for reproducibility).
- **Modify** `src/dynasty_genius/scoring/engine_a.py` — export a public `ENGINE_A_P90_PPG` (alias of the existing private `_P90_PPG`) so the curve build doesn't import a private.
- **Modify** `src/dynasty_genius/trade_lab/evaluator.py:114-141` — turn `value_draft_pick` into a thin **deprecated compat wrapper**.
- **Modify** `src/dynasty_genius/sleeper_universe.py` — flip `PICK_VALUE_STATUS`; attach future-pick `xvar` to the `future_picks` block (`dynasty_value_score` stays null unless a display DVS is explicitly derived — see Task 9).
- **Modify** `src/dynasty_genius/team_value_matrix.py` — surface pick values in `future_picks`; **exclude** them from team-strength/posture aggregates; update the `future_picks_present_unvalued` contract.
- **Create** `tests/contract/test_draft_pick_valuation.py` — core valuation + curve contracts.
- **Create** `tests/contract/test_pick_valuation_inference_only.py` — model-training isolation guard.
- **Create** `docs/validation/2026-05-26-future-pick-valuation-reopening-decision.md` — PM decision memo (Phase 17.3 deferred→active).
- **Modify** `AGENT_SYNC.md` — record the lock reopening.

---

## Task 1: Export a public Engine-A P90 constant

**Files:**
- Modify: `src/dynasty_genius/scoring/engine_a.py`
- Test: `tests/contract/test_draft_pick_valuation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/contract/test_draft_pick_valuation.py
from src.dynasty_genius.scoring.engine_a import ENGINE_A_P90_PPG

def test_engine_a_p90_public_constant_present():
    # Public, governed P90 used by the pick-value curve (no private _P90_PPG import).
    assert ENGINE_A_P90_PPG["WR"] == 12.7
    assert set(ENGINE_A_P90_PPG) == {"QB", "RB", "WR", "TE"}
```

- [ ] **Step 2: Run test, verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_draft_pick_valuation.py::test_engine_a_p90_public_constant_present -v`
Expected: FAIL — `ImportError: cannot import name 'ENGINE_A_P90_PPG'`

- [ ] **Step 3: Implement** — in `engine_a.py`, immediately after the existing `_P90_PPG` definition, add a public alias:

```python
# Public, governed alias of the Engine-A training P90 PPG ceilings, so downstream
# governed consumers (e.g. the draft-pick value curve) need not import a private name.
ENGINE_A_P90_PPG = dict(_P90_PPG)
```

- [ ] **Step 4: Run test, verify pass** — same command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/scoring/engine_a.py tests/contract/test_draft_pick_valuation.py
git commit -m "feat(pick-value): export public ENGINE_A_P90_PPG constant"
```

---

## Task 2: Per-player realized-PPG → xVAR helper

**Files:**
- Create: `src/dynasty_genius/trade_lab/draft_pick_valuation.py`
- Test: `tests/contract/test_draft_pick_valuation.py`

The conversion (spec §4): `DVS = clamp(y24_ppg / P90_pos * 100, 0, 100)`; `xVAR = (DVS − ENGINE_A_REPLACEMENT_DVS[pos]) × XVAR_LAMBDA_ENGINE_A[pos]`. Computed with each player's **actual** position constants. **No `score_prospect()`.**

- [ ] **Step 1: Write the failing test**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import player_xvar_from_ppg

def test_player_xvar_from_ppg_uses_position_constants():
    # WR: P90=12.7, replacement_DVS=69.2, lambda=1.0
    # DVS = min(100, 12.7/12.7*100) = 100.0 ; xVAR = (100-69.2)*1.0 = 30.8
    assert round(player_xvar_from_ppg(12.7, "WR"), 2) == 30.8

def test_player_xvar_from_ppg_clamps_dvs_at_100():
    assert player_xvar_from_ppg(50.0, "WR") == player_xvar_from_ppg(12.7, "WR")

def test_player_xvar_from_ppg_zero_ppg_is_negative_or_floor():
    # DVS=0 -> xVAR=(0-69.2)*1.0 = -69.2 (sub-replacement; not clamped here)
    assert round(player_xvar_from_ppg(0.0, "WR"), 1) == -69.2
```

- [ ] **Step 2: Run, verify fail** — `... -k player_xvar_from_ppg -v` → FAIL (module/function missing).

- [ ] **Step 3: Implement** — create `draft_pick_valuation.py`:

```python
"""Phase 24 — Dynasty rookie draft-pick valuation (historical slot curve).

Pure module: reads a versioned curve artifact and prices a pick in xVAR.
Model-blind beyond the curve artifact — no Engine A/B scoring, no PVO, no market.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_A_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_A,
)
from src.dynasty_genius.scoring.engine_a import ENGINE_A_P90_PPG


def player_xvar_from_ppg(y24_ppg: float, position: str) -> float:
    """Realized Y2+3 PPG -> DVS (clamped 0-100) -> xVAR, using position constants."""
    p90 = ENGINE_A_P90_PPG[position]
    dvs = max(0.0, min(100.0, y24_ppg / p90 * 100.0))
    return (dvs - ENGINE_A_REPLACEMENT_DVS[position]) * XVAR_LAMBDA_ENGINE_A[position]
```

- [ ] **Step 4: Run, verify pass** — `... -k player_xvar_from_ppg -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/trade_lab/draft_pick_valuation.py tests/contract/test_draft_pick_valuation.py
git commit -m "feat(pick-value): per-player realized-ppg to xVAR helper"
```

---

## Task 3: Curve builder — mature-year gate + 36-skill bridge + per-slot xVAR

**Files:**
- Create: `scripts/build_draft_pick_value_curve.py`
- Test: `tests/contract/test_draft_pick_valuation.py`

Logic (spec §4): for each **mature** class (default 2015–2022), order skill players (QB/RB/WR/TE) by NFL `pick`, take the first 36 → FF slots 1..36; convert each to xVAR via `player_xvar_from_ppg`; aggregate per slot across years; exclude immature classes (incomplete Y2+3) and record `low_sample_count`.

> **AMENDED 2026-05-26 (Option A — spec §4):** per-player **`priced_xvar = max(0, raw_xvar)`**
> (option-value floor); slot **`expected_xvar = MEAN of priced_samples`** (mean, NOT median —
> median zeroes deep slots). Store both `raw_samples` (negatives intact) and `priced_samples`.
> The monotonic clamp + median tier rollups then operate on the mean-priced `expected_xvar`.
> Codex authors a new RED test asserting: raw preserved (incl. a negative), priced floored to 0,
> `expected_xvar == mean(priced)`. Caveat `pick_value_floored_at_replacement` added to value_pick.

- [ ] **Step 1: Write the failing test** (uses a tiny in-memory DataFrame fixture, not the real CSV)

```python
import pandas as pd
from src.dynasty_genius.trade_lab.draft_pick_valuation import build_slot_curve

def _fixture_df():
    # 2 mature years, 3 skill players each (slots 1..3), known ppg + low_sample_flag.
    rows = []
    for year in (2015, 2016):
        for (pick, pos, ppg, low) in [
            (1, "QB", 16.7, 0), (2, "WR", 12.7, 0), (3, "RB", 7.3, 1)
        ]:
            rows.append({"draft_year": year, "pick": pick, "position": pos,
                         "y24_ppg": ppg, "low_sample_flag": low})
    return pd.DataFrame(rows)

def test_build_slot_curve_aggregates_xvar_per_slot():
    curve = build_slot_curve(_fixture_df(), mature_years=(2015, 2016), board_size=3)
    s1 = curve["slots"]["1"]
    # QB 16.7 -> DVS 100 -> xVAR (100-77.3)*1.315 = 29.85; same both years -> median 29.85
    assert round(s1["expected_xvar"], 2) == 29.85
    assert s1["n_years"] == 2
    assert s1["positions"] == {"QB": 2}  # both years QB at slot 1
    assert s1["low_sample_count"] == 0
    assert curve["slots"]["3"]["low_sample_count"] == 2  # RB flagged both years
    assert curve["mature_years_used"] == [2015, 2016]
```

- [ ] **Step 2: Run, verify fail** — `... -k build_slot_curve -v` → FAIL.

- [ ] **Step 3: Implement** — add to `draft_pick_valuation.py`:

```python
import statistics
from collections import Counter

_SKILL = ("QB", "RB", "WR", "TE")

def build_slot_curve(
    df,  # pandas DataFrame with columns: draft_year, pick, position, y24_ppg
    mature_years: tuple[int, ...],
    board_size: int = 36,
) -> dict:
    """Build the per-slot xVAR curve from mature classes via the 36-skill bridge."""
    per_slot_samples: dict[int, list[float]] = {k: [] for k in range(1, board_size + 1)}
    per_slot_positions: dict[int, Counter] = {k: Counter() for k in range(1, board_size + 1)}
    per_slot_lowflags: dict[int, int] = {k: 0 for k in range(1, board_size + 1)}
    years_used: list[int] = []

    for year in sorted(mature_years):
        cls = df[(df["draft_year"] == year) & (df["position"].isin(_SKILL))]
        cls = cls.sort_values("pick")
        board = cls.head(board_size)
        if board.empty:
            continue
        years_used.append(year)
        for slot, (_, row) in enumerate(board.iterrows(), start=1):
            xv = player_xvar_from_ppg(float(row["y24_ppg"]), str(row["position"]))
            per_slot_samples[slot].append(xv)
            per_slot_positions[slot][str(row["position"])] += 1
            per_slot_lowflags[slot] += int(bool(row.get("low_sample_flag", 0)))

    slots: dict[str, dict] = {}
    for slot in range(1, board_size + 1):
        samples = per_slot_samples[slot]
        if not samples:
            continue
        slots[str(slot)] = {
            "expected_xvar": round(statistics.median(samples), 4),
            "mean_xvar": round(statistics.fmean(samples), 4),
            "n_years": len(samples),
            "p25": round(_pctl(samples, 25), 4),
            "p75": round(_pctl(samples, 75), 4),
            "mad": round(_mad(samples), 4),
            "low_sample_count": per_slot_lowflags[slot],
            "positions": dict(per_slot_positions[slot]),
            "raw_samples": [round(v, 4) for v in samples],
        }
    return {
        "version": "v1",
        "board_size": board_size,
        "mature_years_used": years_used,
        "slots": slots,
    }

def _pctl(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    idx = (len(xs) - 1) * q / 100.0
    lo, hi = int(idx), min(int(idx) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (idx - lo)

def _mad(xs: list[float]) -> float:
    med = statistics.median(xs)
    return statistics.median([abs(x - med) for x in xs])
```

- [ ] **Step 4: Run, verify pass** — `... -k build_slot_curve -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/trade_lab/draft_pick_valuation.py tests/contract/test_draft_pick_valuation.py
git commit -m "feat(pick-value): per-slot xVAR curve builder (mature-year, 36-skill bridge)"
```

---

## Task 4: Monotonic smoothing + tier rollups

**Files:** Modify `src/dynasty_genius/trade_lab/draft_pick_valuation.py`; Test `tests/contract/test_draft_pick_valuation.py`

Generic future picks resolve to a **tier** (e.g. `early_1st`). Expose `expected_xvar_smoothed`
per slot — a **monotonic non-increasing clamp** (running-min; a slot N pick must not be worth more
than slot N-1). This is a conservative clamp, **not** statistical smoothing (Codex naming note); if
true isotonic regression is wanted later, isolate it as a separate helper. Tier value = **median**
(locked for v1; not trimmed-mean) of its member slots' **post-clamp** `expected_xvar_smoothed`.

- [ ] **Step 1: Failing test**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import smooth_and_tier

def test_smooth_is_monotonic_non_increasing():
    curve = {"board_size": 4, "slots": {
        "1": {"expected_xvar": 30.0}, "2": {"expected_xvar": 25.0},
        "3": {"expected_xvar": 28.0}, "4": {"expected_xvar": 10.0}}}
    out = smooth_and_tier(curve)
    sm = [out["slots"][str(k)]["expected_xvar_smoothed"] for k in range(1, 5)]
    assert sm == sorted(sm, reverse=True)  # 30, 25, 25, 10
    assert out["slots"]["3"]["expected_xvar_smoothed"] == 25.0

def test_tier_rollup_uses_member_slot_median():
    curve = {"board_size": 4, "slots": {
        "1": {"expected_xvar": 30.0}, "2": {"expected_xvar": 25.0},
        "3": {"expected_xvar": 20.0}, "4": {"expected_xvar": 10.0}},
        "tier_map": {"early_1st": [1, 2], "late_1st": [3, 4]}}
    out = smooth_and_tier(curve)
    assert out["tiers"]["early_1st"] == 27.5  # median(30,25) post-smoothing
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
def smooth_and_tier(curve: dict) -> dict:
    """Add monotonic-non-increasing expected_xvar_smoothed per slot + tier rollups."""
    board = curve["board_size"]
    running = None
    for slot in range(1, board + 1):
        s = curve["slots"].get(str(slot))
        if s is None:
            continue
        val = s["expected_xvar"] if running is None else min(s["expected_xvar"], running)
        s["expected_xvar_smoothed"] = round(val, 4)
        running = val
    tier_map = curve.get("tier_map", {})
    tiers: dict[str, float] = {}
    for tier, slots in tier_map.items():
        vals = [curve["slots"][str(k)]["expected_xvar_smoothed"]
                for k in slots if str(k) in curve["slots"]]
        if vals:
            tiers[tier] = round(statistics.median(vals), 4)
    curve["tiers"] = tiers
    return curve
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `feat(pick-value): monotonic clamp + tier rollups`

---

## Task 5: SF-QB ordering knob

**Files:** Modify builder/module; Test `tests/contract/test_draft_pick_valuation.py`

SF reorders the FF board: QBs are promoted ahead of their NFL-skill rank. Apply **before** slot aggregation (spec §4): within a class's first-N skill board, move QBs meeting a round threshold up by `k_slots`. Default `sf_qb_promote_slots=0` (off) with a `sf_qb_ordering_assumption` caveat when >0; calibrated later.

- [ ] **Step 1: Failing test**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import apply_sf_qb_ordering

def test_sf_qb_ordering_promotes_qb_by_k_slots():
    board = [  # (pick, position) pre-reorder, NFL order
        (5, "WR"), (8, "RB"), (40, "QB"), (12, "WR")]
    out = apply_sf_qb_ordering(board, k_slots=2, round_threshold_pick=64)
    # QB at index 2 promoted 2 slots -> front
    assert [p for _, p in out][:1] == ["QB"]

def test_sf_qb_ordering_multiple_qbs_stable():
    board = [(5, "WR"), (40, "QB"), (8, "RB"), (50, "QB"), (12, "WR")]
    out = apply_sf_qb_ordering(board, k_slots=1, round_threshold_pick=64)
    pos = [p for _, p in out]
    qb_idx = [i for i, p in enumerate(pos) if p == "QB"]
    assert pos[0] == "QB"            # first QB promoted ahead
    assert qb_idx[0] < qb_idx[1]     # original QB relative order preserved
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
def apply_sf_qb_ordering(board, k_slots: int = 0, round_threshold_pick: int = 256):
    """Promote qualifying QBs up by k_slots via a stable adjusted-index sort.
    board: ordered list of (pick, position). Returns reordered list.

    A qualifying QB gets sort key (i - k_slots - 0.5) so it edges just ahead of the
    incumbent at slot i-k; the half-offset guarantees no ties with integer-keyed
    non-QBs, and multiple QBs keep their original relative order."""
    if k_slots <= 0:
        return list(board)

    def _key(idx_item):
        i, (pick, pos) = idx_item
        if pos == "QB" and pick <= round_threshold_pick:
            return i - k_slots - 0.5
        return float(i)

    indexed = sorted(enumerate(board), key=_key)
    return [item for _, item in indexed]
```

Wire `apply_sf_qb_ordering` into `build_slot_curve` (apply to each class's board before slot enumeration; thread `sf_qb_promote_slots` param, default 0). Add caveat propagation when active.

- [ ] **Step 4: Run, verify pass** (add a `build_slot_curve(..., sf_qb_promote_slots=1)` assertion).
- [ ] **Step 5: Commit** — `feat(pick-value): SF-QB ordering knob`

---

## Task 6: `value_pick()` public API + `PickValue` model

**Files:** Modify `draft_pick_valuation.py`; Test `tests/contract/test_draft_pick_valuation.py`

`value_pick` resolves a pick (exact slot OR tier) against a loaded curve → `PickValue` (xVAR + caveats). **No position arg.** `decision_supported` coercion-locked False.

- [ ] **Step 1: Failing test**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import PickValue, value_pick

_CURVE = {"version": "v1", "board_size": 4,
          "slots": {"2": {"expected_xvar_smoothed": 25.0}},
          "tiers": {"early_1st": 27.5}}

def test_value_pick_exact_slot():
    pv = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)
    assert isinstance(pv, PickValue)
    assert pv.xvar == 25.0
    assert pv.decision_supported is False
    assert "pick_value_historical_expected" in pv.caveats

def test_value_pick_tier():
    pv = value_pick(year=2027, round_=1, tier="early_1st", curve=_CURVE)
    assert pv.xvar == 27.5

def test_value_pick_round_only_uses_round_generic_tier():
    # Reconstructed future picks know only (season, round) — no slot, no early/mid/late.
    curve = {"tiers": {"round_1_generic": 18.0}}
    pv = value_pick(year=2028, round_=1, curve=curve)
    assert pv.resolution == "round_tier"
    assert pv.xvar == 18.0
    assert "generic_future_pick_round_only" in pv.caveats

def test_value_pick_requires_no_position():
    import inspect
    assert "position" not in inspect.signature(value_pick).parameters

def test_value_pick_decision_supported_locked():
    pv = PickValue(year=2027, round_=1, slot=2, xvar=25.0, resolution="exact_slot",
                   caveats=[], decision_supported=True)
    assert pv.decision_supported is False
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
_BASE_PICK_CAVEATS = [
    "pick_value_historical_expected",
    "pick_value_thin_sample",
    "decision_supported_false",
]

class PickValue(BaseModel):
    year: int
    round_: int
    slot: Optional[int] = None
    tier: Optional[str] = None
    xvar: Optional[float]
    resolution: Literal["exact_slot", "tier", "round_tier", "unresolved"]
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock(cls, v: object) -> bool:
        return False

def value_pick(year: int, round_: int, *, slot: Optional[int] = None,
               tier: Optional[str] = None, curve: dict,
               sf_qb_knob_active: bool = False) -> PickValue:
    caveats = list(_BASE_PICK_CAVEATS)
    if sf_qb_knob_active:
        caveats.append("sf_qb_ordering_assumption")
    if slot is not None:
        s = curve.get("slots", {}).get(str(slot))
        xv = s.get("expected_xvar_smoothed") if s else None
        return PickValue(year=year, round_=round_, slot=slot, xvar=xv,
                         resolution="exact_slot" if xv is not None else "unresolved",
                         caveats=caveats)
    if tier is not None:
        xv = curve.get("tiers", {}).get(tier)
        return PickValue(year=year, round_=round_, tier=tier, xvar=xv,
                         resolution="tier" if xv is not None else "unresolved",
                         caveats=caveats)
    # Round-only path: reconstructed future picks know only (year, round). Map to the
    # round-generic tier (round_1_generic = slots 1-12, etc.).
    round_tier = f"round_{round_}_generic"
    xv = curve.get("tiers", {}).get(round_tier)
    if xv is not None:
        return PickValue(year=year, round_=round_, tier=round_tier, xvar=xv,
                         resolution="round_tier",
                         caveats=caveats + ["generic_future_pick_round_only"])
    return PickValue(year=year, round_=round_, xvar=None, resolution="unresolved",
                     caveats=caveats)

def load_curve(path) -> dict:
    return json.loads(Path(path).read_text())
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `feat(pick-value): value_pick API + PickValue model`

---

## Task 7: Build script + generate the committed curve artifact

**Files:** Create `scripts/build_draft_pick_value_curve.py`; Create `app/data/valuation/draft_pick_value_curve_v1.json`; Test `tests/contract/test_draft_pick_valuation.py`

- [ ] **Step 1: Failing test** (artifact existence + shape, after build)

```python
import json
from pathlib import Path

def test_curve_artifact_built_and_shaped():
    p = Path("app/data/valuation/draft_pick_value_curve_v1.json")
    assert p.exists(), "run scripts/build_draft_pick_value_curve.py first"
    curve = json.loads(p.read_text())
    assert curve["version"] == "v1"
    assert curve["board_size"] == 36
    assert all(int(y) <= 2022 for y in curve["mature_years_used"])  # mature gate
    assert "1" in curve["slots"] and "expected_xvar_smoothed" in curve["slots"]["1"]
```

- [ ] **Step 2: Run, verify fail** (artifact absent).

- [ ] **Step 3: Implement the script** — reads `app/data/training/prospects_with_outcomes.csv`.
  **Codex confirmed the season column is `season` (not `draft_year`); `pick`, `position`,
  `y24_ppg`, `low_sample_flag` all exist.** The loader **normalizes `season → draft_year`** before
  calling `build_slot_curve` (the builder + in-memory fixtures use `draft_year`). Then calls
  `build_slot_curve` → `smooth_and_tier`, writes the artifact. Defaults: `mature_years=range(2015, 2023)`,
  `board_size=36`, `sf_qb_promote_slots=0`. **`tier_map` MUST include both:**
  - granular: `early_1st=[1..4]`, `mid_1st=[5..8]`, `late_1st=[9..12]`, `early_2nd=[13..16]`, … `late_3rd=[33..36]`
  - **round-generic (required by Task 9): `round_1_generic=[1..12]`, `round_2_generic=[13..24]`,
    `round_3_generic=[25..36]`**

  Print coverage (years used, per-slot `low_sample_count` totals).

  - Sub-step done: header confirmed via Codex — `season` is the year column; normalize it.

- [ ] **Step 4: Run the build, then the test**

Run: `.venv/bin/python3.14 scripts/build_draft_pick_value_curve.py` then `... -k curve_artifact -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_draft_pick_value_curve.py app/data/valuation/draft_pick_value_curve_v1.json tests/contract/test_draft_pick_valuation.py
git commit -m "feat(pick-value): curve build script + committed v1 artifact"
```

---

## Task 8: Deprecate `value_draft_pick` (compat wrapper)

**Files:** Modify `src/dynasty_genius/trade_lab/evaluator.py:114-141`; Test `tests/contract/test_draft_pick_valuation.py`

- [ ] **Step 1: Failing test** — wrapper still returns a `TradeAsset` (Codex: existing callers +
`tests/contract/test_phase15_trade_lab.py` depend on the type/fields), but value is curve-backed
and position no longer changes xVAR.

```python
import warnings
from src.dynasty_genius.trade_lab.evaluator import value_draft_pick
from src.dynasty_genius.trade_lab.evaluator import TradeAsset

def test_value_draft_pick_returns_tradeasset_curve_backed():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        a = value_draft_pick(round_=1, pick_bucket="mid", position="WR", age=21)
        b = value_draft_pick(round_=1, pick_bucket="mid", position="RB", age=21)
    assert any(issubclass(x.category, DeprecationWarning) for x in w)
    assert isinstance(a, TradeAsset)
    assert a.is_prospect is True
    assert a.decision_supported is False
    assert a.dvs_engine == "pick_curve_v1"      # neutral curve provenance (not "A")
    assert a.xvar == b.xvar                       # position no longer changes the value
```

- [ ] **Step 2: Run, verify fail** (current impl differs by position; returns Engine-A asset; no warning).

- [ ] **Step 3: Implement** — read the current function and `TradeAsset`'s fields, then replace the
body so it: emits a `DeprecationWarning`; **ignores `position`/`age`**; loads the v1 curve once;
maps `pick_bucket`+`round_` to the granular tier (e.g. `mid`+round 1 → `mid_1st`); calls
`value_pick(...)`; and returns a **`TradeAsset`** with `xvar` from the `PickValue`,
`dvs_engine="pick_curve_v1"` (neutral provenance), `dvs=None`, `is_prospect=True`,
`decision_supported=False`, and the `PickValue.caveats` + a deprecation note. **Consciously update
`tests/contract/test_phase15_trade_lab.py`** where it asserts `dvs_engine == "A"` for a pick →
expect `"pick_curve_v1"` (note the change in the commit). Update other in-repo callers found via
`grep -rn "value_draft_pick" src/ app/` to prefer `value_pick` where a raw xVAR is wanted.

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `refactor(pick-value): deprecate value_draft_pick to curve-backed wrapper`

---

## Task 9: Wire future-pick xVAR into PVO; keep out of team-strength aggregates

**Files:** Modify `src/dynasty_genius/sleeper_universe.py` (`PICK_VALUE_STATUS`), `src/dynasty_genius/team_value_matrix.py`; Test `tests/contract/test_draft_pick_valuation.py`

- [ ] **Step 1: Read the integration points, then write the failing tests.** First
`grep -n "future_picks\|PICK_VALUE_STATUS" src/dynasty_genius/sleeper_universe.py` and read the
team-strength aggregation in `src/dynasty_genius/team_value_matrix.py` to find (a) where a
`future_picks` row is built and (b) the function that sums team strength. Then write two tests
asserting these exact invariants against a small snapshot+curve fixture (use the actual builder
function names found in the read):

```
Invariant 1 (values present): every future_pick row produced for a team has a numeric
            `xvar` (not None) sourced from value_pick(year, round)->tier.
Invariant 2 (excluded from strength): the team's team-strength/posture aggregate equals the
            players-only xVAR sum — pick xVAR is NOT added — preserving Phase 17.3 aggregate
            semantics. Assert by building the matrix twice (with and without future picks
            present) and confirming the strength figure is identical.
```

These two invariants are the contract; the concrete fixture + exact builder call are filled in
after the read (Codex authors them in the cockpit loop).

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** — flip `PICK_VALUE_STATUS` from `"deferred"` to `"active_v1_historical"`;
  in the future-pick assembly (`reconstruct_future_picks`, which emits only `season`+`round`) attach
  `xvar` via the **round-only path** `value_pick(year=season, round_=round)` → `round_tier`
  (resolution `"round_tier"`, caveat `generic_future_pick_round_only`). Leave `dynasty_value_score`
  null for picks (the curve produces xVAR, not a DVS) unless a display DVS is explicitly derived.
  In `team_value_matrix.py` ensure the team-strength/posture aggregate iterates **players only**
  (picks excluded — assert via the two invariants in Step 1). Update the old contract test that
  asserted `future_picks_present_unvalued` to the new
  `future_picks_present_valued_excluded_from_strength` semantics.

- [ ] **Step 4: Run, verify pass** + full phase suite: `.venv/bin/python3.14 -m pytest -k "phase17 or team_value or pick" -v`.
- [ ] **Step 5: Commit** — `feat(pick-value): surface future-pick xVAR in PVO, excluded from team strength`

---

## Task 10: Governance — model-training isolation + recursive decision_supported

**Files:** Create `tests/contract/test_pick_valuation_inference_only.py`

- [ ] **Step 1: Write the guard test**

```python
import inspect
import src.dynasty_genius.trade_lab.draft_pick_valuation as dpv

_BANNED_TOKENS = ("buy", "sell", "win", "loss", "verdict", "accept", "reject")

def test_pick_valuation_module_is_model_blind():
    src = inspect.getsource(dpv)
    # No market/ADP/mock or model-training imports in the valuation module.
    for needle in ("fantasycalc", "mock", "adp", "WalkForwardDriver", "score_prospect"):
        assert needle not in src, f"{needle} must not appear in pick valuation"

def test_pick_value_outputs_carry_no_banned_language():
    pv = dpv.value_pick(year=2027, round_=1, slot=1,
                        curve={"slots": {"1": {"expected_xvar_smoothed": 5.0}}})
    blob = " ".join(pv.caveats).lower() + pv.resolution.lower()
    assert not any(tok in blob for tok in _BANNED_TOKENS)
    assert pv.decision_supported is False
```

- [ ] **Step 2: Run, verify fail/pass** as written; fix module if any banned token/import leaks.
- [ ] **Step 3:** (no impl beyond keeping the module clean)
- [ ] **Step 4: Run** `... test_pick_valuation_inference_only -v` → PASS.
- [ ] **Step 5: Commit** — `test(pick-value): model-blind + banned-language guards`

---

## Task 11: Governance artifacts — PM memo + AGENT_SYNC lock reopening

**Files:** Create `docs/validation/2026-05-26-future-pick-valuation-reopening-decision.md`; Modify `AGENT_SYNC.md`

- [ ] **Step 1:** Write the PM decision memo (deferred→active rationale; reference the spec, this plan, Codex+Gemini consults; state caveats + `decision_supported=False`; record David's approval 2026-05-26). Follow the format of existing `docs/validation/*-decision.md`.
- [ ] **Step 2:** Update `AGENT_SYNC.md` active-phase area: note Phase 17.3 future-pick lock **reopened (David-approved 2026-05-26)** for v1 historical pick valuation; link the spec/plan/memo.
- [ ] **Step 3:** Run `.venv/bin/python3.14 scripts/validate_governance.py` → PASS.
- [ ] **Step 4: Commit** — `docs(pick-value): PM lock-reopening memo + AGENT_SYNC record`

---

## Final verification

- [ ] Full suite green: `.venv/bin/python3.14 -m pytest -q` (expect prior baseline + new tests, 0 failed).
- [ ] `ruff check src app scripts` clean on touched files.
- [ ] Then: branch + PR per the branch-and-PR rule → Codex review → Gemini governance → merge.
