# Regime A — Drafted-Class Pick Valuation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.
> **Cockpit note:** TMUX Codex-test-driver / Claude-implementer loop. Codex authors each failing contract test; Claude implements to green. The test code below is the contract.

**Goal:** Value dynasty rookie picks for an already-scored draft class from the actual prospect board (class-specific), as an alternative regime within `value_pick`, falling back bit-identically to the historical curve when no scored board exists.

**Architecture:** `value_pick` becomes a dispatcher → `_value_pick_from_prospect_board` (Regime A) / `_value_pick_from_curve` (Regime B, existing logic moved unchanged). A model-blind `load_prospect_board` reads `prospect_cards.json` into a `xvar_class_rank → xvar` map. Same Option-A floor-then-mean math as the curve. v1 = capability-only (no production consumer; `reconstruct_future_picks` untouched).

**Tech Stack:** Python 3.14, Pydantic v2, pytest.

**Spec:** `docs/superpowers/specs/2026-05-26-regime-a-drafted-class-pick-valuation-design.md`

---

## File Structure

- **Modify** `src/dynasty_genius/trade_lab/draft_pick_valuation.py` — `PickValue` (+ `valuation_regime`, board resolutions); `value_pick` → dispatcher; new `_value_pick_from_prospect_board`, `_value_pick_from_curve` (existing body moved), `load_prospect_board`, board caveat constants.
- **Modify** `scripts/build_draft_pick_value_curve.py` — `source.method` string clarifies "Option A floor-then-mean".
- **Regenerate** `app/data/valuation/draft_pick_value_curve_v1.json` — values unchanged; only the `method` string differs.
- **Create** `tests/contract/test_regime_a_pick_valuation.py` — Regime A contracts.
- Existing `tests/contract/test_draft_pick_valuation.py` + `tests/contract/test_pick_valuation_inference_only.py` stay green (curve path + guard unchanged).

---

## Task 1: source.method cleanup + curve regen (no new behavior)

**Files:** Modify `scripts/build_draft_pick_value_curve.py`; Regenerate `app/data/valuation/draft_pick_value_curve_v1.json`

- [ ] **Step 1: Edit the method string** — in `build_draft_pick_value_curve.py`, change the `source.method` value to:

```python
        "method": (
            "first-36-skill-NFL-order bridge; realized y24_ppg -> DVS -> xVAR; "
            "Option A option-value floor (priced=max(0,raw), mean of priced); "
            "monotonic clamp; median tiers"
        ),
```

- [ ] **Step 2: Regenerate the artifact**

Run: `.venv/bin/python3.14 scripts/build_draft_pick_value_curve.py`
Expected: writes the artifact; tiers identical to before (only `source.method` changed).

- [ ] **Step 3: Verify the curve artifact test still passes**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_draft_pick_valuation.py -q`
Expected: all pass (test asserts version/board_size/mature_years/slot, not the method string).

- [ ] **Step 4: Commit**

```bash
git add scripts/build_draft_pick_value_curve.py app/data/valuation/draft_pick_value_curve_v1.json
git commit -m "chore(phase24): clarify curve source.method (Option A floor-then-mean)"
```

---

## Task 2: PickValue `valuation_regime` + curve path tags it

**Files:** Modify `src/dynasty_genius/trade_lab/draft_pick_valuation.py`; Test `tests/contract/test_regime_a_pick_valuation.py`

- [ ] **Step 1: Write the failing test**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import PickValue, value_pick

_CURVE = {"version": "v1", "board_size": 4,
          "slots": {"2": {"expected_xvar_smoothed": 25.0}},
          "tiers": {"early_1st": 27.5, "round_1_generic": 18.0}}

def test_curve_path_sets_historical_curve_regime():
    pv = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)
    assert pv.valuation_regime == "historical_curve"

def test_pickvalue_supports_board_resolutions_and_regime():
    pv = PickValue(year=2027, round_=1, slot=2, xvar=5.0,
                   resolution="board_exact_slot", valuation_regime="prospect_board",
                   caveats=[])
    assert pv.resolution == "board_exact_slot"
    assert pv.valuation_regime == "prospect_board"
    assert pv.decision_supported is False
```

- [ ] **Step 2: Run, verify fail** — `... -k "historical_curve_regime or board_resolutions" -v` → FAIL (no `valuation_regime` field; resolution literal lacks board values).

- [ ] **Step 3: Implement** — in `draft_pick_valuation.py`, extend `PickValue` and the curve path:

```python
class PickValue(BaseModel):
    year: int
    round_: int
    slot: Optional[int] = None
    tier: Optional[str] = None
    xvar: Optional[float]
    resolution: Literal[
        "board_exact_slot", "board_round",
        "exact_slot", "tier", "round_tier", "unresolved",
    ]
    valuation_regime: Literal["prospect_board", "historical_curve"] = "historical_curve"
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False
```

Move the **current** `value_pick` body verbatim into `_value_pick_from_curve(year, round_, *, slot, tier, curve, sf_qb_knob_active=False)`, adding `valuation_regime="historical_curve"` to every `PickValue(...)` it returns. (Dispatcher added in Task 4 — for now have `value_pick` delegate to `_value_pick_from_curve`.)

- [ ] **Step 4: Run, verify pass** — same `-k`. Expected: PASS. Also run the full existing curve suite: `.venv/bin/python3.14 -m pytest tests/contract/test_draft_pick_valuation.py -q` → all green (curve behavior unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/trade_lab/draft_pick_valuation.py tests/contract/test_regime_a_pick_valuation.py
git commit -m "feat(regime-a): PickValue valuation_regime + board resolutions; curve path tagged"
```

---

## Task 3: `load_prospect_board` (model-blind loader)

**Files:** Modify `src/dynasty_genius/trade_lab/draft_pick_valuation.py`; Test `tests/contract/test_regime_a_pick_valuation.py`

- [ ] **Step 1: Write the failing tests** (use a tiny fixture file written in the test, not the real artifact)

```python
import json
import pytest
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_prospect_board

def _write_cards(tmp_path, rows):
    p = tmp_path / "cards.json"
    p.write_text(json.dumps(rows))
    return p

def test_load_prospect_board_filters_class_rank_and_xvar(tmp_path):
    rows = [
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 30.0},
        {"draft_class": 2026, "xvar_class_rank": 2, "xvar": 12.0},
        {"draft_class": 2026, "xvar_class_rank": None, "xvar": 5.0},   # unranked -> excluded
        {"draft_class": 2027, "xvar_class_rank": 1, "xvar": 99.0},     # other class -> excluded
        {"draft_class": 2026, "xvar_class_rank": 3, "xvar": None},     # no xvar -> excluded
    ]
    board = load_prospect_board(2026, path=_write_cards(tmp_path, rows))
    assert board == {1: 30.0, 2: 12.0}

def test_load_prospect_board_raises_on_duplicate_rank(tmp_path):
    rows = [
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 30.0},
        {"draft_class": 2026, "xvar_class_rank": 1, "xvar": 28.0},
    ]
    with pytest.raises(ValueError):
        load_prospect_board(2026, path=_write_cards(tmp_path, rows))
```

- [ ] **Step 2: Run, verify fail** — `... -k load_prospect_board -v` → FAIL (function missing).

- [ ] **Step 3: Implement** — add to `draft_pick_valuation.py` (no scorer/Engine/market imports):

```python
_DEFAULT_CARDS_PATH = (
    Path(__file__).resolve().parents[3] / "resources" / "prospect_cards.json"
)

def load_prospect_board(draft_class: int, path: str | Path = _DEFAULT_CARDS_PATH) -> dict[int, float]:
    """Parse prospect_cards.json into a {xvar_class_rank: xvar} board for one class.

    Model-blind: reads only the inference artifact. Filters to the requested
    draft_class with a non-null integer rank and numeric xvar. Raises on duplicate
    ranks (never silently picks one).
    """
    cards = json.loads(Path(path).read_text())
    board: dict[int, float] = {}
    for card in cards:
        if card.get("draft_class") != draft_class:
            continue
        rank = card.get("xvar_class_rank")
        xvar = card.get("xvar")
        if rank is None or not isinstance(xvar, (int, float)):
            continue
        rank = int(rank)
        if rank in board:
            raise ValueError(
                f"duplicate xvar_class_rank {rank} in prospect board for class {draft_class}"
            )
        board[rank] = float(xvar)
    return board
```

- [ ] **Step 4: Run, verify pass** — `... -k load_prospect_board -v` → PASS. Also smoke the real artifact:

Run: `.venv/bin/python3.14 -c "from src.dynasty_genius.trade_lab.draft_pick_valuation import load_prospect_board as l; b=l(2026); print(len(b), 'ranks; min/max rank', min(b), max(b))"`
Expected: ~80 ranks (2027 watchlist excluded), no exception.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/trade_lab/draft_pick_valuation.py tests/contract/test_regime_a_pick_valuation.py
git commit -m "feat(regime-a): model-blind load_prospect_board"
```

---

## Task 4: Board path + dispatcher

**Files:** Modify `src/dynasty_genius/trade_lab/draft_pick_valuation.py`; Test `tests/contract/test_regime_a_pick_valuation.py`

Round rank ranges: R1=1–12, R2=13–24, R3=25–36 (reuse a shared constant).

- [ ] **Step 1: Write the failing tests**

```python
from src.dynasty_genius.trade_lab.draft_pick_valuation import value_pick

# board with a negative (sub-replacement) rank to prove flooring
_BOARD = {1: 30.0, 2: 12.0, 3: -5.0}  # ranks 1..3

def test_board_exact_slot_uses_floored_rank_value():
    pv = value_pick(year=2026, round_=1, slot=3, curve=_CURVE, prospect_board=_BOARD)
    assert pv.valuation_regime == "prospect_board"
    assert pv.resolution == "board_exact_slot"
    assert pv.xvar == 0.0  # max(0, -5.0)
    assert "pick_value_board_class_specific" in pv.caveats
    assert "pick_value_historical_expected" not in pv.caveats

def test_board_round_only_is_mean_of_floored_over_range():
    # round 1 ranks present = 1,2,3 -> floored [30,12,0] -> mean 14.0; partial (only 3 of 12)
    pv = value_pick(year=2026, round_=1, curve=_CURVE, prospect_board=_BOARD)
    assert pv.resolution == "board_round"
    assert pv.xvar == 14.0
    assert "pick_value_board_partial_round_coverage" in pv.caveats

def test_board_exact_slot_beyond_board_is_unresolved_not_curve():
    pv = value_pick(year=2026, round_=1, slot=9, curve=_CURVE, prospect_board=_BOARD)
    assert pv.resolution == "unresolved"
    assert pv.xvar is None
    assert pv.valuation_regime == "prospect_board"
    assert "pick_value_board_slot_beyond_coverage" in pv.caveats

def test_empty_board_falls_back_to_curve_bit_identical():
    with_empty = value_pick(year=2027, round_=1, slot=2, curve=_CURVE, prospect_board={})
    curve_only = value_pick(year=2027, round_=1, slot=2, curve=_CURVE)
    assert with_empty.model_dump() == curve_only.model_dump()
    assert with_empty.valuation_regime == "historical_curve"

def test_tier_with_board_routes_to_curve():
    pv = value_pick(year=2027, round_=1, tier="early_1st", curve=_CURVE, prospect_board=_BOARD)
    assert pv.valuation_regime == "historical_curve"
    assert pv.resolution == "tier"
```

- [ ] **Step 2: Run, verify fail** — `... tests/contract/test_regime_a_pick_valuation.py -v` → board tests FAIL (no board path).

- [ ] **Step 3: Implement** — add board caveats, the board helper, and the dispatcher:

```python
_ROUND_RANK_RANGES = {1: range(1, 13), 2: range(13, 25), 3: range(25, 37)}

_BOARD_PICK_CAVEATS = [
    "pick_value_board_class_specific",
    "pick_value_floored_at_replacement",
    "pick_value_board_model_output",
    "decision_supported_false",
]

def _value_pick_from_prospect_board(year, round_, *, slot, board, sf_qb_knob_active=False):
    caveats = list(_BOARD_PICK_CAVEATS)
    if sf_qb_knob_active:
        caveats.append("sf_qb_ordering_assumption")
    if slot is not None:
        raw = board.get(int(slot))
        if raw is None:
            return PickValue(year=year, round_=round_, slot=slot, xvar=None,
                             resolution="unresolved", valuation_regime="prospect_board",
                             caveats=caveats + ["pick_value_board_slot_beyond_coverage"])
        return PickValue(year=year, round_=round_, slot=slot, xvar=round(max(0.0, raw), 4),
                         resolution="board_exact_slot", valuation_regime="prospect_board",
                         caveats=caveats)
    # round-only
    ranks = _ROUND_RANK_RANGES.get(int(round_))
    present = [board[r] for r in ranks if r in board] if ranks else []
    if not present:
        return PickValue(year=year, round_=round_, xvar=None, resolution="unresolved",
                         valuation_regime="prospect_board",
                         caveats=caveats + ["pick_value_board_slot_beyond_coverage"])
    priced = [max(0.0, v) for v in present]
    if ranks is not None and len(present) < len(list(ranks)):
        caveats = caveats + ["pick_value_board_partial_round_coverage"]
    return PickValue(year=year, round_=round_, xvar=round(statistics.fmean(priced), 4),
                     resolution="board_round", valuation_regime="prospect_board",
                     caveats=caveats)
```

Then make `value_pick` the dispatcher:

```python
def value_pick(year, round_, *, slot=None, tier=None, curve, prospect_board=None,
               sf_qb_knob_active=False) -> PickValue:
    # Regime A only when a non-empty board exists and this is slot/round-only (not tier).
    if prospect_board and tier is None:
        return _value_pick_from_prospect_board(
            year, round_, slot=slot, board=prospect_board, sf_qb_knob_active=sf_qb_knob_active
        )
    return _value_pick_from_curve(
        year, round_, slot=slot, tier=tier, curve=curve, sf_qb_knob_active=sf_qb_knob_active
    )
```

- [ ] **Step 4: Run, verify pass** — `... tests/contract/test_regime_a_pick_valuation.py -v` → all PASS. Then the existing curve suite: `.venv/bin/python3.14 -m pytest tests/contract/test_draft_pick_valuation.py -q` → unchanged/green.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/trade_lab/draft_pick_valuation.py tests/contract/test_regime_a_pick_valuation.py
git commit -m "feat(regime-a): prospect-board pick valuation path + dispatcher"
```

---

## Task 5: Guard + full-suite verification

**Files:** Test (existing) `tests/contract/test_pick_valuation_inference_only.py`

- [ ] **Step 1: Confirm the model-blind guard still passes** (the loader added no banned imports)

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_pick_valuation_inference_only.py -q`
Expected: PASS (no `fantasycalc`/`mock`/`adp`/`WalkForwardDriver`/`score_prospect` in the module).

- [ ] **Step 2: Ruff on the changed module + script**

Run: `.venv/bin/ruff check src/dynasty_genius/trade_lab/draft_pick_valuation.py scripts/build_draft_pick_value_curve.py tests/contract/test_regime_a_pick_valuation.py`
Expected: All checks passed. (If `I001`, run `ruff check --select I --fix` on the file.)

- [ ] **Step 3: Full suite**

Run: `.venv/bin/python3.14 -m pytest -q`
Expected: prior baseline (1236) + the new Regime A tests, 0 failed.

- [ ] **Step 4: validate_governance**

Run: `.venv/bin/python3.14 scripts/validate_governance.py`
Expected: passed.

- [ ] **Step 5:** Then branch is ready — open the PR (Codex review → Gemini governance → merge).

---

## Self-Review

- **Spec coverage:** §1 trigger (Task 4 dispatcher + AUTO load-then-pass note) · §2 method floor+mean (Task 4) · §3 API dispatcher + valuation_regime (Tasks 2,4) · §4 loader (Task 3) · §5 edges: empty→curve (T4), beyond-board (T4), partial round (T4), tier+board→curve (T4) · §6 caveats (T4) · §7 capability-only, reconstruct_future_picks untouched (no task touches it), source.method bundled (T1) · §8 tests (Tasks 2–5). All covered.
- **No placeholders:** every step has concrete code/commands.
- **Type consistency:** `value_pick`/`_value_pick_from_curve`/`_value_pick_from_prospect_board`/`load_prospect_board` signatures + `PickValue` fields consistent across tasks; `_ROUND_RANK_RANGES` reused.
