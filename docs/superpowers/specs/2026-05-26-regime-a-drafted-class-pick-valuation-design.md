---
title: Regime A — Drafted-Class Pick Valuation (board-based) — Design Spec
status: APPROVED design (David, 2026-05-26) — Codex engineering review CLEAR with refinements (folded in)
date: 2026-05-26
author: Claude Code (brainstormed with David; Codex review folded in)
parent: docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md (Phase 24; Regime A was deferred there)
governance_hold: Frontend remains on the Phase 12 HOLD; backend only.
scope: v1 = capability only (board loader + board path in value_pick + tests). No production consumer wiring; reconstruct_future_picks untouched.
---

# Regime A — Drafted-Class Pick Valuation (board-based)

## 0. What we're building

Value a dynasty rookie pick for an **already-scored draft class** from the **actual prospect
board** (class-specific), instead of the generic historical slot curve (Regime B). Once a
class's NFL draft has happened and Engine A has scored its prospects (`prospect_cards.json`
carries per-prospect `xvar` + `xvar_class_rank`), a pick's value reflects *that specific class*
— the precise "this class is loaded/weak" signal the historical average can't give.

This is the deferred "Regime A" from the Phase 24 spec (§3). **v1 is capability-only**: the
board loader + the `value_pick` board path + tests. No production consumer is wired, and
`reconstruct_future_picks` is **not** touched (future picks remain Regime B / round-only curve).

## 1. Trigger (regime dispatch)

`value_pick` dispatches by **board presence**:
- **`prospect_board` provided** (a scored board for the pick's class) → **Regime A** (board pricing).
- **`prospect_board` is None/empty** → **Regime B** (existing historical-curve path, unchanged).

**The intended flow is AUTO** (David's trigger decision), not a manual/optional policy: any
production caller MUST first attempt `load_prospect_board(draft_class)` and pass the result as
`prospect_board`; a non-empty board auto-selects Regime A, and an empty/None board is the
automatic Regime B fallback. (v1 is capability-only, so no production caller is wired yet — but
the plan/implementers must treat the load-then-pass as the required pattern, not "caller's
choice.") `curve` stays **required** so the fallback is always deterministic.

## 2. Valuation method (Option-A parity with the curve)

Every prospect is priced with the option-value floor `priced_xvar = max(0, raw_xvar)` (a busted
pick is benched/cut → contributes 0, never negative). Dynasty slot identity = **`xvar_class_rank`**
(the board ordering already used by the Rookie Board).

- **Exact slot `N`** → `priced_xvar` of the prospect with `xvar_class_rank == N`
  (the **floored** value, not raw). resolution `board_exact_slot`.
- **Round-only `R`** → **`statistics.fmean`** of `priced_xvar` over the round's rank range
  (R1 = ranks 1–12, R2 = 13–24, R3 = 25–36). Mean, **not** median — the mean of floored payoffs
  is the option value. resolution `board_round`.

## 3. API shape

One public entry point, dispatching to private helpers (curve logic moved mostly unchanged):

```
value_pick(year, round_, *, slot=None, tier=None, curve, prospect_board=None,
           sf_qb_knob_active=False) -> PickValue
    -> _value_pick_from_prospect_board(...)   # Regime A
    -> _value_pick_from_curve(...)            # Regime B (existing)
```

`PickValue` gains:
- `resolution: Literal["board_exact_slot", "board_round", "exact_slot", "tier", "round_tier", "unresolved"]`
- `valuation_regime: Literal["prospect_board", "historical_curve"]` — so downstream filters the
  regime **without parsing caveat strings**.

`decision_supported` stays coercion-locked `False`.

## 4. Board loader

`load_prospect_board(draft_class: int, path=resources/prospect_cards.json) -> dict[int, float]`
returns a **`xvar_class_rank → xvar`** map (raw xVAR; flooring happens at pricing time).

- **Model-blind:** parses only the `prospect_cards.json` inference artifact — **no** imports of
  scorers, `pvo_assembler`, Engine A/B services, or market/ADP/mock code. The guard test
  (`test_pick_valuation_inference_only`) continues to forbid `fantasycalc`/`mock`/`adp`/
  `WalkForwardDriver`/`score_prospect` in the module.
- Filters strictly to rows with `draft_class == requested`, **non-null `xvar_class_rank`**, and
  **numeric `xvar`** (so the 2 unscored 2027 watchlist rows are excluded; ~80 scored 2026 rows
  remain).
- **Duplicate `xvar_class_rank`** → raise in the loader (surfaced by a loader test); never
  silently pick one of the duplicates.

## 5. Edge cases (binding)

- **Empty / zero-scored board** after filtering → **fall through to Regime B** (curve).
- **Exact slot beyond board coverage** → **`unresolved` / `xvar=None` + caveat
  `pick_value_board_slot_beyond_coverage`** — NOT a curve fallback. Once a class-specific board
  exists, silently filling a missing exact slot from the generic curve would mislead.
- **Round range partially covered** (board < 36, or sparse ranks) → mean over the **present**
  ranks + caveat `pick_value_board_partial_round_coverage` (with observed count). **Zero present
  → `unresolved`/null.**
- **`tier` supplied with a board** → route to the **curve** path for v1 (board-tier mapping is
  undefined; Regime A covers only exact-slot and round-only).

## 6. Caveats / governance

Board-path caveats (replace the curve-specific ones):
- `pick_value_board_class_specific` (replaces `pick_value_historical_expected`)
- `pick_value_floored_at_replacement` (kept — same option-value floor)
- `pick_value_board_model_output` (replaces `pick_value_thin_sample`, which is a historical-curve
  caution; board values come from current-class model output)
- `decision_supported_false`
- (+ `pick_value_board_partial_round_coverage` on a partially-covered round;
  + `pick_value_board_slot_beyond_coverage` on an exact slot beyond the board)

`decision_supported=False` coercion lock + banned-language guard preserved. Board values are
**class-specific model-output expectations**, still `decision_supported=False`. No market/ADP into
training; no Engine A/B pkl/manifest/contract change; frontend HOLD intact.

## 7. v1 scope

**In:** `load_prospect_board`; the `value_pick` board path + dispatcher refactor + `valuation_regime`
field; contract tests; the trivial Phase-24 `source.method` string cleanup (clarify "Option A
floor-then-mean") bundled into this branch.

**Out (deferred):** production consumer wiring (which surface values current-class picks
pre-dynasty-draft — fuzzy target); any change to `reconstruct_future_picks` (future picks stay
Regime B); board-tier mapping; near-class projection / ADP / decision-rule (separate follow-ups).

## 8. Contract-test intent (for the TDD pass)

- Board **exact slot** uses the **floored** rank-N xVAR; resolution `board_exact_slot`;
  `valuation_regime == "prospect_board"`; caveat `pick_value_board_class_specific`.
- Board **round-only** = **mean of floored** values across the rank range; resolution `board_round`.
- Board path **never** includes `pick_value_historical_expected`.
- **Empty board → curve result bit-identical** to the Regime B path (regime dispatch correctness).
- **Exact slot beyond board → `unresolved`/null** (no curve fallback) + board caveat.
- **Partial round coverage → mean of present ranks + `pick_value_board_partial_round_coverage`**;
  zero present → unresolved.
- `load_prospect_board(2026)` returns the ~80 scored/ranked rows and **excludes** the 2027
  watchlist rows; **duplicate rank raises**.
- Existing curve-path contracts (`test_draft_pick_valuation.py`) remain **unchanged/green**.
- Model-blind guard test (`test_pick_valuation_inference_only`) remains green.
- `decision_supported=False` recursively on board output.

## 9. Counter-argument (Rule 5 — mandatory)

1. **Board xVAR is model output (Engine A), so Regime A values inherit Engine A's rookie-forecast
   error.** Unlike the curve (realized outcomes), the board is a *projection*. Mitigation: the
   `pick_value_board_model_output` caveat + `decision_supported=False`; this is acknowledged as a
   class-specific *projection*, not realized history.
2. **`xvar_class_rank` as dynasty-slot identity assumes the board order = the actual dynasty draft
   order**, which managers don't follow exactly (esp. SF QBs). Mitigation: it is the same ordering
   the Rookie Board already surfaces; v1 is capability-only and not yet wired to drive a decision
   surface; the assumption is disclosed.
3. **Two valuation regimes risk inconsistency.** Mitigation: identical Option-A floor-then-mean
   math in both; `valuation_regime` field makes the source explicit; empty-board falls back
   bit-identically to the curve.
