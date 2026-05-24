---
document: Phase 21 Specification — Roster Cut & Drop Candidate Engine
version: 0.1 (draft)
phase: 21
status: DRAFT — awaiting David approval
author: Claude Code
date: 2026-05-24
governance:
  constitution: docs/governance/00-product-constitution.md v1.0.0
  architecture: docs/governance/01-north-star-architecture.md v1.0.0
  operating_loop: docs/governance/02-agent-operating-loop.md v1.0.0
---

# Phase 21 — Roster Cut & Drop Candidate Engine

## Mission

David's active roster currently holds **28 players** against a Sleeper-enforced capacity of **26 slots** (20 active + 4 IR + 2 Taxi). He must cut at least 2 players before roster lock. Phase 21 builds the Roster Cut Engine: a decision-support layer that ranks active players by model-derived value, enforces protected-slot exemptions, and pairs every Waiver Radar pick-up with the optimal drop candidate.

This is decision *support*, not decision *authority*. Every output carries `decision_supported: false`. The cut list informs David; David makes the call.

---

## Current Roster State

**Source**: `sleeper_universe_snapshot_latest.json` + `universe_pvo_latest.json`
**Captured**: 2026-05-24

| Slot type | Capacity | In use | Headroom |
|-----------|----------|--------|----------|
| Active (roster_positions) | 20 | 23 | −3 |
| IR / Reserve | 4 | 3 | +1 |
| Taxi | 2 | 2 | 0 |
| **Total** | **26** | **28** | **−2** |

**Net over-limit: 2 cuts required.**

### Active Players — Current xVAR Ranking

Ranked ascending by `valuation.xvar_percentile_overall` (lowest = most cuttable). Taxi/IR are exempt and excluded.

| # | Player | Pos | Age | xVAR | xVAR% | DVS | Engine | Status |
|---|--------|-----|-----|------|--------|-----|--------|--------|
| 1 | AJ Barner | TE | 22 | −22.8 | 34.3 | 60.4 | ENGINE_B | ACTIVE |
| 2 | Adonai Mitchell | WR | 22 | −20.2 | 37.3 | 40.4 | ENGINE_B | ACTIVE |
| 3 | Mac Jones | QB | 26 | −19.1 | 39.3 | 50.4 | ENGINE_B | ACTIVE |
| 4 | Theo Johnson | TE | 23 | −16.9 | 43.6 | 69.6 | ENGINE_B | ACTIVE |
| 5 | Parker Washington | WR | 22 | −13.5 | 48.1 | 47.1 | ENGINE_B | ACTIVE |
| 6 | Chris Bell | WR | 21 | −6.7 | 58.9 | 62.5 | ENGINE_A | ACTIVE |
| 7 | Xavier Legette | WR | 23 | −2.1 | 64.2 | 58.5 | ENGINE_B | ACTIVE |
| 8 | Rome Odunze | WR | 22 | +2.4 | 70.4 | 63.0 | ENGINE_B | ACTIVE |
| 9 | Tyrone Tracy | RB | 25 | +11.8 | 78.9 | 57.3 | ENGINE_B | ACTIVE |
| 10 | Kaelon Black | RB | 24 | +13.4 | 79.9 | 61.5 | ENGINE_A | ACTIVE |
| — | Rasheen Ali | RB | 23 | N/A | N/A | N/A | ENGINE_B (xVAR gap) | ACTIVE |
| — | J.J. McCarthy | QB | 23 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Jaxson Dart | QB | 23 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Dillon Gabriel | QB | 25 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Ashton Jeanty | RB | 22 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | TreVeyon Henderson | RB | 23 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Luther Burden | WR | 22 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Elic Ayomanor | WR | 22 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Chimere Dike | WR | 24 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Tre' Harris | WR | 24 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Pat Bryant | WR | 23 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Kyle Williams | WR | 23 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |
| — | Tank Dell | WR | 26 | N/A | N/A | N/A | PRE_MODEL | ACTIVE |

**Protected (exempt from cuts):**
- **Taxi**: Fernando Mendoza (QB, xVAR% 77.9), Omar Cooper Jr. (WR, xVAR% 69.2)
- **IR**: Braelon Allen (RB, xVAR% 62.2), Tucker Kraft (TE, xVAR% 68.9), Garrett Wilson (WR, xVAR% 89.5)

---

## Architecture

### Layered Design

Phase 21 adds one new module and extends two existing modules. It does not touch Engine A, Engine B, any model artifact, or the PVO assembler.

```
league_opportunity_map.py          ← W2: WAIVER_CANDIDATE cards get recommended_drop
                 ↑
scripts/build_roster_cut_report.py ← W3: CLI runner + artifact writer
                 ↑
src/dynasty_genius/roster_cut_engine.py   ← W1: pure computation
                 ↑
universe_pvo_latest.json + sleeper_universe_snapshot_latest.json
```

### Data Sources (read-only)

| Source | Path | Fields consumed |
|--------|------|-----------------|
| Universe PVO | `app/data/valuation/universe_pvo_latest.json` | `sleeper_player_id`, `player.full_name`, `player.position`, `player.age`, `valuation.xvar`, `valuation.xvar_percentile_overall`, `valuation.dynasty_value_score`, `valuation.engine_path`, `league_context.on_taxi`, `league_context.on_ir`, `league_context.roster_id` |
| Sleeper universe snapshot | `app/data/league_snapshots/sleeper_universe_snapshot_latest.json` | `league.roster_positions`, `league.settings.reserve_slots`, `league.settings.taxi_slots`, `rosters[].players`, `rosters[].taxi`, `rosters[].reserve`, `rosters[].roster_id` |
| David's league context | `resources/david_league_context.json` | `david_roster_id` |

---

## W1 — RosterCutEngine (pure function)

**File**: `src/dynasty_genius/roster_cut_engine.py`

### Inputs

```python
def compute_roster_cut_candidates(
    universe_pvo: dict,           # full universe_pvo_latest artifact
    sleeper_snapshot: dict,       # full sleeper_universe_snapshot_latest artifact
    david_roster_id: int = 1,     # from david_league_context.json
) -> RosterCutResult:
```

### Step 1 — Roster Limit Detection

```python
roster_positions = league["roster_positions"]       # e.g. 20 slots including BN
active_slots = len(roster_positions)                # count includes BN, FLEX, starters
reserve_slots = league["settings"]["reserve_slots"] # 4
taxi_slots    = league["settings"]["taxi_slots"]    # 2
total_capacity = active_slots + reserve_slots + taxi_slots   # 26

david_roster = rosters[david_roster_id]
total_players  = len(david_roster["players"])       # 28
taxi_ids       = set(david_roster["taxi"] or [])    # 2
ir_ids         = set(david_roster["reserve"] or []) # 3
active_players = total_players - len(taxi_ids) - len(ir_ids) # 23

over_limit = total_players - total_capacity         # 2
```

If `over_limit <= 0`: return result with `cuts_required: 0` and empty candidate list (no action needed).

### Step 2 — Score Lookup Per Active Player

For each `sleeper_player_id` in `david_roster["players"]`:

1. Look up PVO row by `sleeper_player_id`.
2. Mark **EXEMPT** if `on_taxi == True` OR `on_ir == True`.
3. For non-exempt players, extract scoring tier:

| Tier | Condition | Score field used |
|------|-----------|------------------|
| A | `valuation.xvar_percentile_overall is not None` | `xvar_percentile_overall` (0–100) |
| B | `valuation.dynasty_value_score is not None` AND tier A missing | `dynasty_value_score` (0–100) |
| C | `valuation.engine_path == "ENGINE_A"` AND tiers A+B missing | Engine A model score (from `valuation.dynasty_value_score` if present) |
| D | `valuation.engine_path == "PRE_MODEL"` | No score — ranked last, flagged for manual review |

### Step 3 — Age Cliff Warning

Apply the constitution's position cliff ages as **evidence flags only** — never as score modifiers:

```python
CLIFF_AGES = {"QB": 33, "RB": 26, "WR": 28, "TE": 30}
age_cliff_warning = (player.age is not None and
                     CLIFF_AGES.get(position) is not None and
                     player.age >= CLIFF_AGES[position])
```

A cliff warning adds `"age_at_or_past_cliff"` to the `cut_rationale` evidence list. It does not change the numeric ranking.

### Step 4 — Rank and Output

Sort active non-exempt players:
1. **Primary**: Tier (A < B < C < D — better tier = scored earlier)
2. **Secondary within tier**: Score ascending (lower = higher cut priority)
3. **Tertiary**: Age descending (older = higher cut priority, display only)

Output `cuts_required` (e.g. 2) candidates with `cut_priority = 1, 2, 3 ...`

### Output Schema

```python
class RosterCutCandidate(BaseModel):
    sleeper_player_id: str
    full_name: str | None
    position: str | None
    age: float | None
    engine_used: str | None          # ENGINE_B, ENGINE_A, PRE_MODEL, etc.
    xvar: float | None
    xvar_percentile_overall: float | None
    dynasty_value_score: float | None
    scoring_tier: str                # "A", "B", "C", "D"
    cut_priority: int                # 1 = highest cut priority
    cut_rationale: list[str]         # evidence strings, not instructions
    age_cliff_warning: bool
    caveats: list[str]


class RosterCutResult(BaseModel):
    schema_version: str = "roster_cut.v1"
    captured_at: str
    david_roster_id: int
    total_players: int
    total_capacity: int
    cuts_required: int
    active_players: int
    active_slots: int
    taxi_count: int
    ir_count: int
    exempt_players: list[RosterCutCandidate]    # taxi + IR, for display
    cut_candidates: list[RosterCutCandidate]    # ranked, non-exempt
    caveats: list[str]
    decision_supported: bool = False
```

### Governance Constraints

- `decision_supported = False` always.
- No market data enters the scoring computation.
- Cliff age is evidence text only — it must not change a player's numeric score.
- PRE_MODEL players (2026 rookies with no NFL games) are ranked last and explicitly caveated — these are high-upside players who haven't played, not confirmed low-value assets.
- No player is labeled "cut", "drop", or "release". The field is `cut_priority` (an ordinal rank of evidence) and `cut_rationale` (a list of neutral evidence strings).

---

## W2 — Waiver-Drop Integration

**File**: `src/dynasty_genius/league_opportunity_map.py` (extend existing `_waiver_cards()`)

Every `WAIVER_CANDIDATE` card gets a new optional field:

```python
"recommended_drop": {
    "sleeper_player_id": str,
    "full_name": str | None,
    "position": str | None,
    "xvar_percentile_overall": float | None,
    "cut_priority": int,
    "cut_rationale": list[str],
    "scoring_tier": str,
    "caveats": list[str],
} | None
```

### Pairing Logic

For each WAIVER_CANDIDATE card:

1. **Same-position first**: Find the highest-priority cut candidate (lowest `cut_priority` int) whose `position` matches the waiver candidate's position. This represents a direct positional swap.
2. **Fallback — lowest overall**: If no same-position match, use the highest-priority cut candidate regardless of position.
3. **No match**: If `cuts_required == 0` (roster not over limit), set `recommended_drop: null` and add caveat `"roster_not_over_limit"`.

The pairing is **advisory only**. It does not constrain which player David actually picks up or drops. The same drop candidate may appear on multiple waiver cards (many-to-one is allowed).

### Modified `build_opportunity_cards()` Signature

```python
def build_opportunity_cards(
    team_matrix: dict,
    market_divergence: dict,
    *,
    perspective_roster_id: int,
    roster_cut_result: RosterCutResult | None = None,   # NEW — optional
    max_cards: int = DEFAULT_MAX_CARDS,
) -> list[dict]:
```

When `roster_cut_result` is provided, waiver cards are enriched with `recommended_drop`. When `None`, `recommended_drop` is omitted (backwards-compatible — existing callers unaffected).

---

## W3 — Build Script

**File**: `scripts/build_roster_cut_report.py`

### CLI

```bash
.venv/bin/python3.14 scripts/build_roster_cut_report.py
.venv/bin/python3.14 scripts/build_roster_cut_report.py --with-waiver-integration
```

`--with-waiver-integration` re-runs `build_league_opportunity_map.py` logic with the drop pairings attached and writes an enriched opportunity artifact alongside the cut report.

### Artifacts Written

| File | Description |
|------|-------------|
| `app/data/valuation/roster_cut_report_latest.json` | Full `RosterCutResult` JSON |
| `app/data/valuation/roster_cut_report_latest.md` | Human-readable cut candidate card |
| `app/data/valuation/league_opportunity_cut_latest.json` | Optional — opportunity map with `recommended_drop` on waiver cards |

All three are canonical (`_latest`) overwrite targets. Run-id–stamped copies follow the existing `*_phase[0-9]*.json` gitignore pattern.

### `.gitignore` Extension

Add alongside existing phase-stamped valuation artifacts:
```
app/data/valuation/roster_cut_report_phase*.json
app/data/valuation/league_opportunity_cut_phase*.json
```
Canonical `_latest.*` files are committed (same pattern as `universe_pvo_latest.json`).

---

## Tests

### W1 Tests (`tests/test_phase21_roster_cut.py`)

| Test | What it verifies |
|------|-----------------|
| `test_over_limit_is_computed_correctly` | 28 players, 26 capacity → `cuts_required = 2` |
| `test_taxi_players_are_exempt` | Fernando Mendoza and Omar Cooper Jr. never appear in `cut_candidates` |
| `test_ir_players_are_exempt` | Braelon Allen, Tucker Kraft, Garrett Wilson never appear in `cut_candidates` |
| `test_cut_candidates_ranked_by_xvar_percentile` | Tier A players ranked lowest-xvar-pct first; AJ Barner (34.3%) appears before Mac Jones (39.3%) |
| `test_pre_model_players_ranked_last` | PRE_MODEL players appear after all tier A/B/C players in cut list |
| `test_cliff_age_is_evidence_not_score` | Mac Jones (QB, 26) has `age_cliff_warning = False`; a synthetic RB age 27 has `age_cliff_warning = True` but same rank position if score is equal |
| `test_decision_supported_is_false` | `result.decision_supported == False` always |
| `test_no_market_features_in_cut_scoring` | No `ktc_value`, `fantasycalc_value`, or market field present in any `RosterCutCandidate` |
| `test_roster_at_limit_returns_empty_candidates` | When total_players == total_capacity, `cuts_required = 0` and `cut_candidates = []` |

### W2 Tests (extend `tests/test_phase17_league_opportunity_map.py` or new file)

| Test | What it verifies |
|------|-----------------|
| `test_waiver_card_gets_recommended_drop_same_position` | A WAIVER_CANDIDATE WR card recommends a WR cut candidate |
| `test_waiver_card_falls_back_to_lowest_overall` | When no WR cut candidate exists, falls back to any position's top cut candidate |
| `test_waiver_card_drop_is_null_when_roster_at_limit` | `recommended_drop = null` when `cuts_required == 0` |
| `test_recommended_drop_never_set_decision_supported` | `recommended_drop` dict never contains `decision_supported: true` |
| `test_backwards_compat_when_no_cut_result_passed` | Existing callers passing `roster_cut_result=None` get cards without `recommended_drop` key |

---

## Workstream Sequence

| Workstream | Scope | Dependency |
|-----------|-------|------------|
| W1 — RosterCutEngine | New module, pure computation, 9 TDD tests | None |
| W2 — Waiver-Drop integration | Extend league_opportunity_map.py, 5 TDD tests | W1 complete |
| W3 — Build script | CLI + artifact writer, manual smoke test | W1 + W2 complete |

Each workstream follows Red-Green-Refactor. Tests are written first and confirmed failing before any production code is written.

---

## Governance Constraints Summary

| Constraint | Enforcement |
|-----------|-------------|
| `decision_supported = False` always | Schema-level default; contract test |
| No market data in cut scoring | `test_no_market_features_in_cut_scoring` |
| Cliff age is evidence only, not score modifier | `test_cliff_age_is_evidence_not_score` |
| Taxi/IR players are always exempt | `test_taxi_players_are_exempt`, `test_ir_players_are_exempt` |
| No imperative language ("cut", "drop", "release") | Field named `cut_priority` (ordinal rank) + `cut_rationale` (evidence list); banned language list in module |
| PRE_MODEL rookies flagged as unscored, not low-value | Explicit caveat `"pre_model_no_nfl_games_insufficient_signal"` on tier D candidates |
| No Engine A/B model artifacts changed | W1–W3 are read-only consumers of existing scoring outputs |
| No `latest.json`, `v2_manifest.json`, PVO assembler changes | Out of scope |

---

## Non-Goals (Phase 21)

- Automatic roster submission to Sleeper API — display only
- Trade-away suggestions for players above the cut line — Trade Lab scope
- Waiver wire rankings or add-priority scoring — Waiver Radar scope is limited to WAIVER_CANDIDATE pairing
- Refreshing the PVO batch — run `build_universe_pvo_batch.py` manually before this script if staleness is a concern
- Changing the definition of PRE_MODEL — Phase 22+ decision

---

## Open Questions (David's call before W1 implementation)

1. **PRE_MODEL ranking**: Should PRE_MODEL active players (2026 rookies with no NFL data) be exempt from the cut list entirely, or should they appear in tier D with a strong caveat? Tier D means they can appear if all scored players are ranked highly. Recommended: **include in tier D with explicit caveat** — David should see them explicitly rather than have the engine hide them.

2. **Roster limit source**: Should the engine read `roster_positions` directly from the live Sleeper snapshot, or should we lock the capacity constants (26 total, 20 active, 4 IR, 2 taxi) in `resources/david_league_context.json` for reproducibility? Recommended: **read live from snapshot** — if Sleeper changes the league settings, the engine stays correct.

3. **Waiver card enrichment scope**: Should the `recommended_drop` pairing also appear on `ROSTER_SURPLUS_DEFICIT_MATCH` and `DIVERGENCE_MODEL_HIGH` cards (where the pickup would be via trade, not waiver)? Recommended: **WAIVER_CANDIDATE only** — the drop pairing only makes sense for a direct add/drop transaction.
