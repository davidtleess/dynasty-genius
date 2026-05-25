---
document: Phase 22 Specification — Trade Lab Roster Reconciler
version: 0.2
phase: 22
status: DRAFT — awaiting David approval
author: Claude Code
date: 2026-05-24
changelog:
  v0.1: Initial draft
  v0.2: Codex patch — fix side_a/side_b perspective mapping, add TradeAsset/TradeEvaluation coercion-lock requirement, fix endpoint path to /api/trade/reconcile, replace set-union mutation with order-preserving logic
governance:
  constitution: docs/governance/00-product-constitution.md v1.0.0
  architecture: docs/governance/01-north-star-architecture.md v1.0.0
  operating_loop: docs/governance/02-agent-operating-loop.md v1.0.0
---

# Phase 22 — Trade Lab: Roster Reconciler

## Mission

The current Trade Lab (`POST /trade/evaluate`) computes asset parity in xVAR units. It does not know whether the trade fits David's roster. A 1-for-3 trade that wins the xVAR comparison can still be a bad deal if David must immediately cut 2 players to make room — and those 2 players have meaningful xVAR he loses for free.

Phase 22 adds the **Roster Reconciler**: a layer that detects post-trade roster overflow, invokes the Phase 21 RosterCutEngine to identify which players would be forced out, and deducts their combined xVAR as a **Forced Cut Penalty** from David's received-value total. Both the base evaluation and the roster-adjusted evaluation are returned so David can see the full picture.

This is decision *support*, not decision *authority*. Every output carries `decision_supported: False`.

---

## Context — Where the Reconciler Plugs In

```
Existing flow:
  TradeAsset[] (side_a) ──┐
                          ├──▶ evaluate_trade() ──▶ TradeEvaluation
  TradeAsset[] (side_b) ──┘

Phase 22 extension:
  TradeAsset[] (side_a) ──┐    ← david_assets  (what David sends)
  TradeAsset[] (side_b) ──┤    ← received_assets (what David receives)
  players_out[]           ├──▶ reconcile_trade_roster() ──▶ TradeRosterReconciliation
  players_in[]            │        │
  universe_pvo            │        ├─ base_evaluation (existing logic, unchanged)
  sleeper_snapshot        │        ├─ roster_penalty (overflow + cut candidates)
                          ┘        └─ adjusted evaluation (base minus penalty)
```

### David-perspective convention

`evaluate_trade(side_a_assets, side_b_assets)` names sides generically. The Reconciler always
calls it with David's outgoing assets as `side_a` and David's incoming assets as `side_b`:

| Reconciler variable | `evaluate_trade` field | Meaning |
|---------------------|------------------------|---------|
| `david_assets` | `side_a` / `base.side_a` | What David sends |
| `received_assets` | `side_b` / `base.side_b` | What David receives |

All pseudo-code in this spec uses `base.side_a` and `base.side_b` to match the actual
`TradeEvaluation` model fields. There is no `side_sent` or `side_received` field on the model.

**Invariants carried forward from Phase 21:**
- RosterCutEngine is the single authoritative source for forced-cut ranking. The Reconciler does not re-implement cut logic.
- Market data (KTC, FantasyCalc) is never used for penalty calculation.
- `decision_supported: False` propagated at every level.

---

## Problem Statement

Given a proposed trade between David and a counterparty:

- David sends: `players_out` (non-pick roster slots freed) + `picks_out` (no roster impact)
- David receives: `players_in` (non-pick roster slots consumed) + `picks_in` (no roster impact)

After the trade settles:

```
post_trade_total = current_roster_count - len(players_out) + len(players_in)
post_trade_overflow = max(0, post_trade_total - total_capacity)
```

If `post_trade_overflow > 0`, David must cut `post_trade_overflow` players before roster lock. Those forced cuts represent real xVAR leaving his roster — a cost that vanilla `evaluate_trade` ignores.

The Reconciler makes that cost visible.

---

## Algorithm

### Step 0: Identify roster-affecting assets

Only non-pick assets consume roster slots. Picks are `TradeAsset.is_prospect == True`.

```python
players_out = [a.player_id for a in david_assets if not a.is_prospect]
players_in  = [a.player_id for a in received_assets if not a.is_prospect]
```

`players_out` and `players_in` are the raw Sleeper player IDs used to mutate the snapshot.

### Step 1: Compute post-trade capacity state

```python
league = sleeper_snapshot["league"]
settings = league["settings"]
active_slots  = len(league["roster_positions"])
reserve_slots = int(settings.get("reserve_slots") or 0)
taxi_slots    = int(settings.get("taxi_slots") or 0)
total_capacity = active_slots + reserve_slots + taxi_slots

roster = next(r for r in sleeper_snapshot["rosters"] if r["roster_id"] == david_roster_id)
current_total = len(roster.get("players") or [])

post_trade_total    = current_total - len(players_out) + len(players_in)
post_trade_overflow = max(0, post_trade_total - total_capacity)
```

### Step 2: Early-return — no overflow

```python
if post_trade_overflow == 0:
    base = evaluate_trade(david_assets, received_assets)
    # side_a = david_assets (sent), side_b = received_assets
    return TradeRosterReconciliation(
        base_evaluation=base,
        roster_penalty=RosterPenaltySummary(
            post_trade_total_players=post_trade_total,
            post_trade_overflow=0,
            forced_cut_candidates=[],
            forced_cut_penalty_xvar=0.0,
            penalty_caveats=[],
        ),
        adjusted_david_received_value=base.side_b.side_value,
        adjusted_fairness_delta=base.fairness_delta,
        adjusted_within_parity_band=base.within_parity_band,
        adjusted_favors=base.favors,
        caveats=base.caveats,
    )
```

### Step 3: Construct post-trade snapshot

Deep-copy the live snapshot and mutate David's roster to reflect the trade.
Use order-preserving logic — do not use `set` union on the players list, which would
destroy ordering and produce non-deterministic output:

```python
import copy

modified = copy.deepcopy(sleeper_snapshot)
modified_roster = next(r for r in modified["rosters"] if r["roster_id"] == david_roster_id)

out_set = set(players_out)

# Remove outgoing players from all slot lists (order-preserving filter)
modified_roster["players"] = [p for p in (modified_roster["players"] or []) if p not in out_set]
modified_roster["taxi"]    = [p for p in (modified_roster.get("taxi") or [])    if p not in out_set]
modified_roster["reserve"] = [p for p in (modified_roster.get("reserve") or []) if p not in out_set]

# Append incoming players not already present (order-preserving, no duplicates)
existing_ids = set(modified_roster["players"])
for pid in players_in:
    if pid not in existing_ids:
        modified_roster["players"].append(pid)
        existing_ids.add(pid)
```

Incoming players are placed on the active roster in the order received. The engine does not auto-assign taxi or IR slots.

### Step 4: Run RosterCutEngine on post-trade roster

```python
post_trade_result = compute_roster_cut_candidates(
    universe_pvo, modified, david_roster_id
)
# Slice the top N candidates matching the overflow count
forced_cuts = post_trade_result.cut_candidates[:post_trade_overflow]
```

The cut engine's existing priority ordering applies:
1. Forced-compliance players (`cut_priority = 0`) appear first
2. Tier A (lowest xVAR%) → Tier B/C (lowest DVS) → Tier D (PRE_MODEL)

### Step 5: Compute forced-cut penalty

The penalty must be in the same xVAR units as `evaluate_trade`. `RosterCutCandidate` carries `xvar_pct` (percentile), not raw xVAR. Raw xVAR is fetched from `universe_pvo`:

```python
pvo_lookup: dict[str, dict] = {
    p["sleeper_player_id"]: p for p in universe_pvo["players"]
}

penalty_xvar = 0.0
penalty_caveats: list[str] = []

for candidate in forced_cuts:
    entry = pvo_lookup.get(candidate.sleeper_player_id, {})
    raw_xvar = (entry.get("valuation") or {}).get("xvar")
    if raw_xvar is not None and raw_xvar > 0:
        penalty_xvar += raw_xvar
    else:
        penalty_caveats.append(
            f"{candidate.full_name} ({candidate.sleeper_player_id}): "
            f"xVAR unavailable ({candidate.scoring_tier}) — excluded from penalty"
        )
```

PRE_MODEL candidates and players with no raw xVAR contribute 0 to the penalty. Caveats surface them.

### Step 6: Compute adjusted evaluation

`evaluate_trade` was called once in Step 2 (early-return) or must be called here.
Call it exactly once and reuse:

```python
base = evaluate_trade(david_assets, received_assets)
# base.side_a = david_assets (sent); base.side_b = received_assets

# David's received side (side_b), reduced by the forced-cut penalty
adjusted_received_value = max(0.0, base.side_b.side_value - penalty_xvar)
adjusted_delta    = abs(base.side_a.side_value - adjusted_received_value)
adjusted_max_side = max(base.side_a.side_value, adjusted_received_value)
adjusted_within_band = (
    adjusted_delta <= TRADE_PARITY_BAND * adjusted_max_side
    if adjusted_max_side > 0 else True
)
if adjusted_within_band:
    adjusted_favors = "neutral"
elif adjusted_received_value > base.side_a.side_value:
    adjusted_favors = "david"
else:
    adjusted_favors = "counterparty"
```

### Step 7: Assemble output

```python
return TradeRosterReconciliation(
    base_evaluation=base,
    roster_penalty=RosterPenaltySummary(
        post_trade_total_players=post_trade_total,
        post_trade_overflow=post_trade_overflow,
        forced_cut_candidates=[_cut_summary(c) for c in forced_cuts],
        forced_cut_penalty_xvar=round(penalty_xvar, 2),
        penalty_caveats=penalty_caveats,
    ),
    adjusted_david_received_value=round(adjusted_received_value, 2),
    adjusted_fairness_delta=round(adjusted_delta, 2),
    adjusted_within_parity_band=adjusted_within_band,
    adjusted_favors=adjusted_favors,
    decision_supported=False,
    caveats=base.caveats + penalty_caveats,
)
```

---

## Data Contract

### Input: `TradeReconcileRequest` (API schema)

```python
class TradeReconcileRequest(BaseModel):
    david_assets: list[dict]      # TradeAsset dicts — what David sends
    received_assets: list[dict]   # TradeAsset dicts — what David receives
    # david_side is always David (no ambiguity — reconciler is David-perspective only)
```

The reconciler does not need `david_side` as a parameter — it is always David's perspective. The caller provides David's outgoing assets (`david_assets`) and David's incoming assets (`received_assets`).

### Output models

```python
class _CutSummary(TypedDict):
    sleeper_player_id: str
    full_name: str
    position: str
    cut_priority: int
    scoring_tier: str
    xvar_raw: float | None
    xvar_pct: float | None
    ir_compliance_status: str
    decision_supported: bool  # always False


class RosterPenaltySummary(BaseModel):
    post_trade_total_players: int
    post_trade_overflow: int
    forced_cut_candidates: list[dict]   # _CutSummary dicts
    forced_cut_penalty_xvar: float
    penalty_caveats: list[str]
    decision_supported: bool = False    # coerced-locked


class TradeRosterReconciliation(BaseModel):
    base_evaluation: TradeEvaluation    # existing model, unchanged
    roster_penalty: RosterPenaltySummary
    adjusted_david_received_value: float
    adjusted_fairness_delta: float
    adjusted_within_parity_band: bool
    adjusted_favors: str                # "david", "counterparty", "neutral"
    decision_supported: bool = False    # coerced-locked
    caveats: list[str]
```

Both `RosterPenaltySummary` and `TradeRosterReconciliation` receive the same `_lock_decision_supported` validator pattern established in Phase 21.

### W1 prerequisite: coercion-lock existing Trade Lab models

Before implementing the Reconciler, W1 must also add `_lock_decision_supported` validators
to the **existing** Trade Lab Pydantic models in `src/dynasty_genius/trade_lab/evaluator.py`:

```python
from pydantic import BaseModel, field_validator

class TradeAsset(BaseModel):
    ...
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class TradeEvaluation(BaseModel):
    ...
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False
```

`TradeSide` has no `decision_supported` field and does not require a validator.

This is required because a caller who constructs `TradeAsset(…, decision_supported=True)` or
`TradeEvaluation(…, decision_supported=True)` would currently bypass the governance lock.
The Reconciler's nested output contains both model types and must be recursively safe.

### Entry point

```python
# src/dynasty_genius/trade_lab/reconciler.py

def reconcile_trade_roster(
    david_assets: list[TradeAsset],
    received_assets: list[TradeAsset],
    universe_pvo: dict,
    sleeper_snapshot: dict,
    david_roster_id: int = 1,
) -> TradeRosterReconciliation:
    ...
```

Pure function. No file I/O. No market data.

### API endpoint

```
POST /api/trade/reconcile
```

The router is mounted at `/api` in `app/main.py` (same prefix as existing `/api/trade/evaluate`).
The route handler registers the path as `/trade/reconcile` inside `app/api/routes/trade.py`,
which resolves externally to `/api/trade/reconcile`.

Accepts `TradeReconcileRequest`. The route handler loads `universe_pvo_latest.json` and
`sleeper_universe_snapshot_latest.json` from the standard artifact paths, then calls the pure
`reconcile_trade_roster()` function. Returns `TradeRosterReconciliation` serialized to JSON.

This is a **new endpoint** — `POST /api/trade/evaluate` is unchanged for backwards compatibility.

---

## Validation Scenarios

### Multi-player packages

| Test ID | Scenario | players_out | players_in | current / capacity | Expected overflow | Expected penalty |
|---------|----------|-------------|------------|--------------------|-------------------|-----------------|
| V1 | Balanced swap | 2 | 2 | 26/26 | 0 | 0.0 |
| V2 | 1-for-3 at capacity | 1 | 3 | 26/26 | 2 | xVAR of top-2 cuts |
| V3 | 2-for-1 (David consolidates) | 2 | 1 | 26/26 | 0 | 0.0 |
| V4 | At capacity, 1-for-2 | 1 | 2 | 26/26 | 1 | xVAR of #1 cut |
| V5 | Under capacity, 0-for-2 | 0 | 2 | 24/26 | 0 | 0.0 |
| V6 | Under capacity, 0-for-4 | 0 | 4 | 24/26 | 2 | xVAR of top-2 cuts |

### Pick-heavy deals

| Test ID | Scenario | roster_assets_out | roster_assets_in | picks | Expected overflow |
|---------|----------|-------------------|------------------|-------|-------------------|
| P1 | 1 player + 2 picks for 1 player + 1 pick | 1 | 1 | mixed | 0 |
| P2 | 2 players for 3 picks only | 2 | 0 | 3 in | 0 (net -2 roster slots freed) |
| P3 | 1 player for 1 player + 2 picks | 1 | 1 | 2 in | 0 |
| P4 | 0 players out + 1 player in for picks, at capacity | 0 | 1 | picks out | 1 |

### Edge cases

| Test ID | Scenario | Expected behavior |
|---------|----------|------------------|
| E1 | Incoming player not in PVO | PRE_MODEL treatment; caveat added; 0 xVAR contribution to penalty |
| E2 | Forced-compliance IR player in post-trade roster | Surfaces at cut_priority=0 in forced_cut_candidates |
| E3 | All forced cuts are PRE_MODEL | penalty_xvar=0.0; caveats list all missing xVAR |
| E4 | decision_supported=True passed to any model | Coerced to False by validator |

---

## Test Harness

### W1 — Reconciler pure function (12 tests)

Location: `tests/test_phase22_trade_reconciler.py`

| # | Test name | What it verifies |
|---|-----------|-----------------|
| 1 | `test_balanced_trade_no_overflow` | 1-for-1 at capacity → overflow=0, penalty=0.0 |
| 2 | `test_one_for_two_at_capacity_overflows` | 1-for-2 at capacity → overflow=1, penalty > 0 |
| 3 | `test_two_for_one_no_overflow` | 2-for-1 → David consolidates, no overflow |
| 4 | `test_picks_excluded_from_headcount` | `is_prospect=True` assets don't affect roster count |
| 5 | `test_penalty_equals_top_n_cut_xvar` | overflow=2 → penalty = sum of top-2 cut candidates' raw xVAR |
| 6 | `test_forced_compliance_player_surfaces_in_penalty` | ILLEGAL_RESERVE player in post-trade roster → cut_priority=0, first in forced_cut_candidates |
| 7 | `test_pre_model_penalty_candidate_caveat` | No xVAR → penalty unchanged, caveat added |
| 8 | `test_adjusted_value_less_than_base_when_penalty_nonzero` | `adjusted_david_received_value < base.side_b.side_value` |
| 9 | `test_no_overflow_adjusted_equals_base` | zero penalty → adjusted value equals base (`base.side_b.side_value`) |
| 10 | `test_decision_supported_false_throughout` | Recursive walk: no `decision_supported: True` anywhere in reconciler output |
| 11 | `test_trade_asset_decision_supported_coerced_false` | `TradeAsset(…, decision_supported=True)` → field is `False` |
| 12 | `test_trade_evaluation_decision_supported_coerced_false` | `TradeEvaluation(…, decision_supported=True)` → field is `False` |

### W2 — `POST /api/trade/reconcile` endpoint (4 tests)

Location: `tests/test_phase22_reconcile_endpoint.py`

| # | Test name | What it verifies |
|---|-----------|-----------------|
| 1 | `test_reconcile_endpoint_balanced_trade` | Happy path, no overflow, valid schema |
| 2 | `test_reconcile_endpoint_overflow_reduces_adjusted_value` | End-to-end: penalty flows through to adjusted fields |
| 3 | `test_reconcile_endpoint_picks_only_deal_no_overflow` | All assets are picks → players_in=[], no overflow |
| 4 | `test_reconcile_endpoint_decision_supported_false_throughout` | Governance: recursive walk on response JSON |

---

## Implementation Plan

### Workstreams

| WS | Scope | Tests | Blocked by |
|----|-------|-------|-----------|
| W1 | Coercion-lock `TradeAsset` + `TradeEvaluation`; implement `reconciler.py` | 12 | None |
| W2 | `app/api/routes/trade.py` — `POST /api/trade/reconcile` | 4 | W1 |

No model pkl, manifests, PVO scorer, market overlay, or `decision_supported` flags are touched beyond the evaluator and reconciler models.

### New files

```
src/dynasty_genius/trade_lab/reconciler.py    ← pure function, W1
tests/test_phase22_trade_reconciler.py        ← W1 TDD (12 tests)
tests/test_phase22_reconcile_endpoint.py      ← W2 TDD (4 tests)
```

### Modified files

```
src/dynasty_genius/trade_lab/evaluator.py    ← add _lock_decision_supported validators to TradeAsset + TradeEvaluation (W1 prereq)
app/api/routes/trade.py                      ← add POST /api/trade/reconcile route
```

---

## Open Questions

None. All design decisions resolved in spec:

| Question | Resolution |
|----------|-----------|
| Penalty units (xVAR percentile vs raw) | Raw xVAR from `valuation.xvar` in PVO — same units as `evaluate_trade` |
| Where incoming players land (active/taxi/IR) | Active only; Reconciler does not auto-assign slots |
| PRE_MODEL forced cuts | Contribute 0 to penalty xVAR; appear in `penalty_caveats` |
| New endpoint vs extend existing | New `POST /api/trade/reconcile`; existing `/api/trade/evaluate` unchanged |
| `david_side` parameter | Not needed — reconciler is always David's perspective; `side_a=sent, side_b=received` |
| Consolidation factor on penalty | Penalty is a raw subtraction from received value (`base.side_b.side_value`); does not interact with consolidation math |
| Roster mutation order | Order-preserving: filter out outgoing IDs, append incoming IDs not already present |
| Existing model coercion-lock | `TradeAsset` and `TradeEvaluation` get `field_validator` in W1 before reconciler is written |

---

## Governance

- All outputs carry `decision_supported: False` via Pydantic `field_validator` (same pattern as Phase 21)
- Existing Trade Lab models (`TradeAsset`, `TradeEvaluation`) gain the same coercion-lock in W1 before the reconciler is written
- No market data (KTC, FantasyCalc, ADP, FantasyPros) enters penalty calculation — raw xVAR from PVO only
- `reconcile_trade_roster()` is a pure function: receives `universe_pvo` and `sleeper_snapshot` as arguments, performs no file I/O
- Base `evaluate_trade` scoring/math is called unchanged; Reconciler is an additive layer. W1 only adds `decision_supported` coercion validators to evaluator models.
- Recursive `decision_supported` guard covers: `TradeRosterReconciliation`, `RosterPenaltySummary`, nested `_CutSummary` dicts, and the embedded `TradeEvaluation` / `TradeAsset` objects
- Legacy `app/services/trade_analyzer.py` heuristic scoring is not used
