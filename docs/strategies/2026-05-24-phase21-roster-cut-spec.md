---
document: Phase 21 Specification — Roster Cut & Drop Candidate Engine
version: 0.2
phase: 21
status: DRAFT — awaiting David approval
author: Claude Code
date: 2026-05-24
changelog:
  v0.2: Codex architecture review — five blockers resolved (IR eligibility, taxi lock rules,
        defensive capacity math, edge-case roster occupancy tests, recursive decision_supported
        guard). Source-path note corrected.
  v0.1: Initial draft
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

### Relevant League Settings (from `league.settings`)

| Setting | Value | Meaning |
|---------|-------|---------|
| `reserve_slots` | 4 | IR capacity |
| `reserve_allow_out` | 0 | |
| `reserve_allow_doubtful` | 0 | |
| `reserve_allow_sus` | 0 | |
| `reserve_allow_na` | 0 | |
| `reserve_allow_cov` | 0 | |
| `reserve_allow_dnr` | 0 | All six = 0 → **unrestricted reserve** — no injury designation required |
| `taxi_slots` | 2 | Taxi capacity |
| `taxi_years` | 1 | Players with `years_exp` ≤ 1 are taxi-eligible |
| `taxi_allow_vets` | 0 | Veterans (`years_exp` > `taxi_years`) cannot be added to taxi |
| `taxi_deadline` | 4 | Taxi assignments lock at week 4 of the NFL season |
| `bench_lock` | 1 | Bench players are locked when their game starts |

### Protected Players (Exempt from Cuts)

**IR / Reserve** (all three are `sleeper_status = Active`; `reserve_unrestricted = True` → compliant):

| Player | Pos | xVAR% | IR Compliance |
|--------|-----|--------|---------------|
| Braelon Allen | RB | 62.2 | COMPLIANT (unrestricted reserve) |
| Tucker Kraft | TE | 68.9 | COMPLIANT (unrestricted reserve) |
| Garrett Wilson | WR | 89.5 | COMPLIANT (unrestricted reserve) |

**Taxi** (both `years_exp = 0`, eligible per `taxi_years = 1`):

| Player | Pos | xVAR% | Taxi Eligibility |
|--------|-----|--------|-----------------|
| Fernando Mendoza | QB | 77.9 | ELIGIBLE (2026 rookie) |
| Omar Cooper Jr. | WR | 69.2 | ELIGIBLE (2026 rookie) |

### Active Players — Current xVAR Ranking

Ranked ascending by `valuation.xvar_percentile_overall` (lowest = most cuttable). Taxi/IR are exempt and excluded.

| # | Player | Pos | Age | xVAR | xVAR% | DVS | Engine |
|---|--------|-----|-----|------|--------|-----|--------|
| 1 | AJ Barner | TE | 22 | −22.8 | 34.3 | 60.4 | ENGINE_B |
| 2 | Adonai Mitchell | WR | 22 | −20.2 | 37.3 | 40.4 | ENGINE_B |
| 3 | Mac Jones | QB | 26 | −19.1 | 39.3 | 50.4 | ENGINE_B |
| 4 | Theo Johnson | TE | 23 | −16.9 | 43.6 | 69.6 | ENGINE_B |
| 5 | Parker Washington | WR | 22 | −13.5 | 48.1 | 47.1 | ENGINE_B |
| 6 | Chris Bell | WR | 21 | −6.7 | 58.9 | 62.5 | ENGINE_A |
| 7 | Xavier Legette | WR | 23 | −2.1 | 64.2 | 58.5 | ENGINE_B |
| 8 | Rome Odunze | WR | 22 | +2.4 | 70.4 | 63.0 | ENGINE_B |
| 9 | Tyrone Tracy | RB | 25 | +11.8 | 78.9 | 57.3 | ENGINE_B |
| 10 | Kaelon Black | RB | 24 | +13.4 | 79.9 | 61.5 | ENGINE_A |
| — | Rasheen Ali | RB | 23 | N/A | N/A | N/A | ENGINE_B (xVAR gap) |
| — | J.J. McCarthy | QB | 23 | N/A | N/A | N/A | PRE_MODEL |
| — | Jaxson Dart | QB | 23 | N/A | N/A | N/A | PRE_MODEL |
| — | Dillon Gabriel | QB | 25 | N/A | N/A | N/A | PRE_MODEL |
| — | Ashton Jeanty | RB | 22 | N/A | N/A | N/A | PRE_MODEL |
| — | TreVeyon Henderson | RB | 23 | N/A | N/A | N/A | PRE_MODEL |
| — | Luther Burden | WR | 22 | N/A | N/A | N/A | PRE_MODEL |
| — | Elic Ayomanor | WR | 22 | N/A | N/A | N/A | PRE_MODEL |
| — | Chimere Dike | WR | 24 | N/A | N/A | N/A | PRE_MODEL |
| — | Tre' Harris | WR | 24 | N/A | N/A | N/A | PRE_MODEL |
| — | Pat Bryant | WR | 23 | N/A | N/A | N/A | PRE_MODEL |
| — | Kyle Williams | WR | 23 | N/A | N/A | N/A | PRE_MODEL |
| — | Tank Dell | WR | 26 | N/A | N/A | N/A | PRE_MODEL |

---

## Architecture

### Layered Design

Phase 21 adds one new standalone module and extends two existing modules. It does not touch Engine A, Engine B, any model artifact, or the PVO assembler.

```
league_opportunity_map.py               ← W2: WAIVER_CANDIDATE cards get recommended_drop
                    ↑
scripts/build_roster_cut_report.py      ← W3: CLI runner + artifact writer
                    ↑
src/dynasty_genius/roster_cut_engine.py ← W1: pure computation (new standalone module)
                    ↑
universe_pvo_latest.json + sleeper_universe_snapshot_latest.json
```

**Existing related code (read-only reference, not modified by Phase 21):**
- `app/services/roster_auditor.py` — live roster audit service; Phase 21 does not modify it
- `src/dynasty_genius/sleeper_universe.py` — populates `league_context.on_taxi` and `league_context.on_ir` per player; Phase 21 reads these fields but does not extend this module
- `scripts/build_sleeper_universe_snapshot.py` — fetches and writes the Sleeper snapshot; Phase 21 reads its output

There is no `src/dynasty_genius/roster_audit/` package; the new `roster_cut_engine.py` is a flat module under `src/dynasty_genius/`.

### Data Sources (read-only)

| Source | Path | Fields consumed |
|--------|------|-----------------|
| Universe PVO | `app/data/valuation/universe_pvo_latest.json` | `sleeper_player_id`, `player.full_name`, `player.position`, `player.age`, `player.sleeper_status`, `valuation.xvar`, `valuation.xvar_percentile_overall`, `valuation.dynasty_value_score`, `valuation.engine_path`, `league_context.on_taxi`, `league_context.on_ir`, `league_context.roster_id` |
| Sleeper universe snapshot | `app/data/league_snapshots/sleeper_universe_snapshot_latest.json` | `league.roster_positions`, `league.settings` (full settings dict), `rosters[].players`, `rosters[].taxi`, `rosters[].reserve`, `rosters[].roster_id` |
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

### Step 1 — Parse League Settings

Extract and validate all roster-limit and eligibility settings from `league.settings`:

```python
settings = snapshot["league"]["settings"]

# Reserve settings
reserve_slots = int(settings.get("reserve_slots") or 0)
RESERVE_ALLOW_FLAGS = {
    "OUT":       "reserve_allow_out",
    "DOUBTFUL":  "reserve_allow_doubtful",
    "SUS":       "reserve_allow_sus",
    "NA":        "reserve_allow_na",
    "COV":       "reserve_allow_cov",
    "DNR":       "reserve_allow_dnr",
}
reserve_unrestricted = all(int(settings.get(v) or 0) == 0 for v in RESERVE_ALLOW_FLAGS.values())
# When ALL flags are 0: unrestricted reserve — any player may occupy a reserve slot
# regardless of injury designation. This is the standard dynasty off-season setting.
# When one or more flags are 1: only players with matching injury status are eligible.

# Taxi settings
taxi_slots      = int(settings.get("taxi_slots") or 0)
taxi_years      = int(settings.get("taxi_years") or 0)   # max years_exp eligible
taxi_allow_vets = int(settings.get("taxi_allow_vets") or 0)  # 0 = no vets
taxi_deadline   = int(settings.get("taxi_deadline") or 0)    # lock week (NFL season)
bench_lock      = int(settings.get("bench_lock") or 0)       # 1 = bench locks on kickoff
```

### Step 2 — Defensive Roster Capacity Math

```python
roster_positions = snapshot["league"].get("roster_positions") or []

# REQUIRED: verify roster_positions does not include "IR" or "TAXI" slot strings.
# If it did, adding reserve_slots and taxi_slots would double-count protected capacity.
protected_in_positions = [s for s in roster_positions if s in {"IR", "TAXI"}]
if protected_in_positions:
    raise ValueError(
        f"roster_positions contains protected slot types {protected_in_positions}. "
        "Cannot add reserve_slots + taxi_slots on top — capacity math would be wrong."
    )

# Safe to count all positions as active slots
active_slots = len(roster_positions)                             # 20 in David's league
total_capacity = active_slots + reserve_slots + taxi_slots       # 26
```

In David's league `roster_positions` is confirmed to contain only `QB`, `RB`, `WR`, `TE`, `FLEX`, `SUPER_FLEX`, and `BN` — no `IR` or `TAXI` strings. The validation guard will pass silently.

### Step 3 — Roster Over-Limit Detection

```python
david_roster = {r["roster_id"]: r for r in rosters}[david_roster_id]
all_player_ids = set(david_roster.get("players") or [])
taxi_ids       = set(david_roster.get("taxi") or [])
ir_ids         = set(david_roster.get("reserve") or [])
total_players  = len(all_player_ids)

over_limit = total_players - total_capacity
```

If `over_limit <= 0`: return `RosterCutResult` with `cuts_required = 0`, `cut_candidates = []`. No further computation needed.

### Step 4 — IR Compliance Check

For each player in `ir_ids`, look up their PVO row and check eligibility:

```python
def _ir_compliance_status(
    sleeper_status: str | None,
    reserve_unrestricted: bool,
    reserve_allow_flags: dict[str, str],
    settings: dict,
) -> str:
    if reserve_unrestricted:
        return "COMPLIANT"  # off-season unrestricted — any status allowed
    if sleeper_status is None:
        return "UNKNOWN_STATUS"
    # Map Sleeper injury status strings to setting keys
    STATUS_TO_FLAG = {
        "Out": "reserve_allow_out",
        "Doubtful": "reserve_allow_doubtful",
        "Suspended": "reserve_allow_sus",
        "NA": "reserve_allow_na",
        "COVID-19": "reserve_allow_cov",
        "DNR": "reserve_allow_dnr",
    }
    flag_key = STATUS_TO_FLAG.get(sleeper_status)
    if flag_key and int(settings.get(flag_key) or 0) == 1:
        return "COMPLIANT"
    return "ILLEGAL_RESERVE"
```

Players with `ir_compliance_status = "ILLEGAL_RESERVE"` are **NOT simply exempt**. They are added to `cut_candidates` with `cut_priority = 0` (forced compliance, ahead of all model-ranked candidates) and a `cut_rationale` entry of `"reserve_slot_ineligible_must_comply"`. They also appear in the top-level `forced_compliance_caveats` list on the result.

In David's current roster: `reserve_unrestricted = True` → all three IR players are `COMPLIANT` and exempt.

### Step 5 — Taxi Eligibility Check

```python
def _taxi_eligibility(
    years_exp: int | None,
    taxi_years: int,
    taxi_allow_vets: int,
) -> str:
    if years_exp is None:
        return "UNKNOWN"
    if years_exp <= taxi_years:
        return "ELIGIBLE"      # rookie / early-career player
    if taxi_allow_vets == 1:
        return "ELIGIBLE"      # league allows vets on taxi
    return "INELIGIBLE_VET"    # veteran, taxi_allow_vets = 0
```

Currently-on-taxi players are **exempt from cuts regardless of eligibility** — they already occupy a taxi slot. Eligibility governs whether a player *not yet on taxi* could be moved there; it does not retroactively change status for players already assigned.

Add to `RosterCutResult.caveats` when applicable:
- `"taxi_deadline_approaching"` — if the current NFL week >= `taxi_deadline - 1`
- `"taxi_player_ineligible_vet"` — if any currently-on-taxi player has `taxi_eligibility = "INELIGIBLE_VET"` (surface for David review, not a forced cut)

In David's current roster: both taxi players are 2026 rookies (`years_exp = 0`), eligible per `taxi_years = 1`. Deadline has not passed (May 2026).

### Step 6 — Score Lookup Per Active Player

For each `player_id` in `all_player_ids` that is neither in `taxi_ids` nor `ir_ids`:

| Tier | Condition | Score field |
|------|-----------|-------------|
| A | `valuation.xvar_percentile_overall is not None` | `xvar_percentile_overall` (0–100) |
| B | `valuation.dynasty_value_score is not None` AND xvar_pct is None | `dynasty_value_score` (0–100) |
| C | Engine A path AND tiers A+B both missing | Treated same as tier B; `dynasty_value_score` if present |
| D | `valuation.engine_path == "PRE_MODEL"` or score entirely absent | No numeric score — ranked last with explicit caveat |

### Step 7 — Age Cliff Warning

Apply constitution cliff ages as **evidence text only** — never as score modifiers:

```python
CLIFF_AGES = {"QB": 33, "RB": 26, "WR": 28, "TE": 30}
age_cliff_warning = (
    player.age is not None
    and position is not None
    and CLIFF_AGES.get(position) is not None
    and player.age >= CLIFF_AGES[position]
)
```

A cliff warning appends `"age_at_or_past_position_cliff"` to `cut_rationale`. It does not change the numeric rank.

### Step 8 — Rank and Output

Sort active non-exempt players:
1. **Forced compliance first** (`cut_priority = 0`): any `ILLEGAL_RESERVE` players moved to active
2. **Tier A** (xvar_pct scored): ascending by `xvar_percentile_overall`
3. **Tier B/C** (dvs scored, no xvar_pct): ascending by `dynasty_value_score`
4. **Tier D** (PRE_MODEL / unscored): ascending by age descending as tiebreak
5. **Tertiary for equal scores**: age descending (older = higher cut priority, display only)

Assign `cut_priority = 1, 2, 3 ...` after forced-compliance entries.

### Output Schema

```python
class RosterCutCandidate(BaseModel):
    sleeper_player_id: str
    full_name: str | None
    position: str | None
    age: float | None
    years_exp: int | None
    engine_used: str | None
    xvar: float | None
    xvar_percentile_overall: float | None
    dynasty_value_score: float | None
    scoring_tier: str                # "A", "B", "C", "D", or "FORCED"
    cut_priority: int                # 0 = forced compliance; 1+ = model-ranked
    cut_rationale: list[str]         # neutral evidence strings
    age_cliff_warning: bool
    ir_compliance_status: str | None # "COMPLIANT", "ILLEGAL_RESERVE", "UNKNOWN_STATUS", None
    taxi_eligibility: str | None     # "ELIGIBLE", "INELIGIBLE_VET", "UNKNOWN", None
    exempt: bool
    exempt_reason: str | None        # "taxi" | "ir_compliant" | None
    decision_supported: bool = False  # always False — per-candidate lock
    caveats: list[str]


class RosterCutResult(BaseModel):
    schema_version: str = "roster_cut.v1"
    captured_at: str
    david_roster_id: int
    total_players: int
    total_capacity: int
    active_slots: int
    reserve_slots: int
    taxi_slots: int
    reserve_unrestricted: bool
    taxi_years: int
    taxi_allow_vets: int
    taxi_deadline: int
    cuts_required: int
    active_players: int
    taxi_count: int
    ir_count: int
    forced_compliance_caveats: list[str]   # non-empty only when ILLEGAL_RESERVE players exist
    exempt_players: list[RosterCutCandidate]    # taxi + compliant IR, for display
    cut_candidates: list[RosterCutCandidate]    # ranked (includes forced-compliance at priority 0)
    caveats: list[str]
    decision_supported: bool = False            # always False — top-level lock
```

### Governance Constraints

- `decision_supported = False` on every field at every level — schema default on both `RosterCutCandidate` and `RosterCutResult`.
- No market data enters the scoring computation.
- Cliff age is evidence text only — it must not change a player's numeric score.
- PRE_MODEL players (2026 rookies with no NFL games) are tier D and explicitly caveated — not confirmed low-value.
- No player is labeled "cut", "drop", or "release". The field is `cut_priority` (an ordinal rank of evidence) and `cut_rationale` (a list of neutral evidence strings).
- `ILLEGAL_RESERVE` players surface as forced compliance evidence, not as model-ranked cuts.

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
    "decision_supported": False,       # always False — nested lock
} | None
```

The `decision_supported: False` field is **required** inside `recommended_drop`, not just at the top-level card level.

### Pairing Logic

For each WAIVER_CANDIDATE card:

1. **Same-position first**: Find the highest-priority cut candidate (lowest `cut_priority` int) whose `position` matches the waiver candidate's position.
2. **Fallback — lowest overall**: If no same-position match, use the `cut_priority = 1` candidate regardless of position.
3. **Forced compliance overrides**: If any `cut_priority = 0` (ILLEGAL_RESERVE) candidates exist, they appear first regardless of position match.
4. **No match**: If `cuts_required == 0`, set `recommended_drop: null` and add caveat `"roster_not_over_limit"`.

Many-to-one is allowed: the same drop candidate may appear on multiple waiver cards.

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

When `roster_cut_result` is `None`, `recommended_drop` is omitted entirely from cards — backwards-compatible with all existing callers.

---

## W3 — Build Script

**File**: `scripts/build_roster_cut_report.py`

### CLI

```bash
.venv/bin/python3.14 scripts/build_roster_cut_report.py
.venv/bin/python3.14 scripts/build_roster_cut_report.py --with-waiver-integration
```

### Artifacts Written

| File | Description |
|------|-------------|
| `app/data/valuation/roster_cut_report_latest.json` | Full `RosterCutResult` JSON |
| `app/data/valuation/roster_cut_report_latest.md` | Human-readable cut candidate card |
| `app/data/valuation/league_opportunity_cut_latest.json` | Optional — opportunity map with `recommended_drop` on waiver cards |

Run-id–stamped copies are gitignored (see §gitignore below). Canonical `_latest.*` files are committed on the same pattern as `universe_pvo_latest.json`.

### `.gitignore` Extension

```
app/data/valuation/roster_cut_report_phase*.json
app/data/valuation/league_opportunity_cut_phase*.json
```

---

## Tests

### W1 Tests (`tests/test_phase21_roster_cut.py`)

**Blocker 1 — IR eligibility:**

| Test | What it verifies |
|------|-----------------|
| `test_unrestricted_reserve_exempts_all_ir_players` | When all `reserve_allow_*` = 0, all IR players have `ir_compliance_status = "COMPLIANT"` and `exempt = True` |
| `test_restricted_reserve_illegal_player_surfaces_as_forced_compliance` | When `reserve_allow_out = 1` and a reserve player has `sleeper_status = "Active"`, their `ir_compliance_status = "ILLEGAL_RESERVE"` and they appear in `cut_candidates` with `cut_priority = 0` |
| `test_illegal_reserve_not_simply_exempt` | Player with `ILLEGAL_RESERVE` status does NOT appear in `exempt_players` |

**Blocker 2 — Taxi eligibility:**

| Test | What it verifies |
|------|-----------------|
| `test_taxi_player_is_exempt_regardless_of_eligibility` | A synthetic player with `years_exp = 5` (vet) who is already on taxi is still `exempt = True` |
| `test_vet_not_on_taxi_is_ineligible` | A synthetic player with `years_exp = 5` not on taxi has `taxi_eligibility = "INELIGIBLE_VET"` in their candidate record |
| `test_rookie_on_taxi_has_eligible_status` | A 2026 rookie on taxi has `taxi_eligibility = "ELIGIBLE"` |

**Blocker 3 — Defensive capacity math:**

| Test | What it verifies |
|------|-----------------|
| `test_ir_taxi_slots_not_in_roster_positions_passes_validation` | David's actual `roster_positions` (no IR/TAXI strings) does not raise |
| `test_roster_positions_containing_ir_raises` | A synthetic `roster_positions` including `"IR"` raises `ValueError` before computing capacity |
| `test_active_slots_equals_non_protected_positions` | `active_slots = len(roster_positions)` for a positions list with no IR/TAXI entries |

**Blocker 4 — Edge-case roster occupancy:**

| Test | What it verifies |
|------|-----------------|
| `test_over_limit_is_computed_correctly` | 28 players, 26 capacity → `cuts_required = 2` |
| `test_roster_below_capacity_returns_no_cuts` | 20 total players, 26 capacity → `cuts_required = 0`, `cut_candidates = []` |
| `test_roster_exactly_at_capacity_returns_no_cuts` | 26 total players, 26 capacity → `cuts_required = 0`, `cut_candidates = []` |
| `test_partial_occupancy_with_taxi_ir_present` | 15 total players (2 taxi, 2 IR), 26 capacity → `cuts_required = 0`, `cut_candidates = []` |

**Scoring and governance:**

| Test | What it verifies |
|------|-----------------|
| `test_taxi_players_are_exempt` | Fernando Mendoza and Omar Cooper Jr. never appear in `cut_candidates` |
| `test_ir_players_exempt_when_compliant` | Braelon Allen, Tucker Kraft, Garrett Wilson never in `cut_candidates` (unrestricted reserve) |
| `test_cut_candidates_ranked_by_xvar_percentile` | Tier A players ranked lowest-xvar-pct first; AJ Barner (34.3%) before Mac Jones (39.3%) |
| `test_pre_model_players_ranked_last` | PRE_MODEL players appear after all tier A/B/C players |
| `test_cliff_age_is_evidence_not_score` | A synthetic RB age 27 has `age_cliff_warning = True` but retains its numeric rank position |
| `test_decision_supported_false_on_result` | `result.decision_supported == False` |
| `test_no_market_features_in_cut_scoring` | No `ktc_value`, `fantasycalc_value`, or market field in any `RosterCutCandidate` |

**Blocker 5 — Recursive decision_supported lock:**

| Test | What it verifies |
|------|-----------------|
| `test_no_nested_decision_supported_true_in_cut_result` | Walks all nested dicts/lists in the serialized `RosterCutResult` JSON and asserts no `decision_supported: True` anywhere |

### W2 Tests (new file `tests/test_phase21_waiver_drop_integration.py`)

| Test | What it verifies |
|------|-----------------|
| `test_waiver_card_gets_recommended_drop_same_position` | A WAIVER_CANDIDATE WR card recommends a WR cut candidate (same-position match) |
| `test_waiver_card_falls_back_to_lowest_overall` | When no same-position cut candidate exists, card falls back to priority-1 candidate |
| `test_forced_compliance_candidate_always_surfaces_first` | When a `cut_priority = 0` (ILLEGAL_RESERVE) candidate exists, it appears in `recommended_drop` before any model-ranked candidates |
| `test_waiver_card_drop_is_null_when_roster_at_limit` | `recommended_drop = null` when `cuts_required == 0` |
| `test_recommended_drop_always_has_decision_supported_false` | Every non-null `recommended_drop` dict contains `decision_supported: False` |
| `test_no_nested_decision_supported_true_in_opportunity_cut_artifact` | Walks all nested dicts/lists in the serialized opportunity-cut JSON and asserts no `decision_supported: True` anywhere |
| `test_backwards_compat_when_no_cut_result_passed` | Callers passing `roster_cut_result=None` get cards without a `recommended_drop` key |

---

## Workstream Sequence

| Workstream | Scope | TDD tests | Dependency |
|-----------|-------|-----------|------------|
| W1 — RosterCutEngine | New standalone module | 20 | None |
| W2 — Waiver-Drop integration | Extend `league_opportunity_map.py` | 7 | W1 complete |
| W3 — Build script | CLI + artifact writer | Manual smoke test | W1 + W2 complete |

Each workstream follows Red-Green-Refactor. Tests are written first and confirmed failing before any production code is written.

---

## Governance Constraints Summary

| Constraint | Enforcement |
|-----------|-------------|
| `decision_supported = False` at all levels | Schema default on `RosterCutCandidate`, `RosterCutResult`, and `recommended_drop`; recursive contract test |
| No market data in cut scoring | `test_no_market_features_in_cut_scoring` |
| Cliff age is evidence only, not score modifier | `test_cliff_age_is_evidence_not_score` |
| Taxi players always exempt | `test_taxi_player_is_exempt_regardless_of_eligibility` |
| Compliant IR players exempt | `test_ir_players_exempt_when_compliant` |
| ILLEGAL_RESERVE players surface as forced compliance, not exempt | `test_illegal_reserve_not_simply_exempt` |
| Defensive capacity math (no double-counting) | `test_roster_positions_containing_ir_raises` |
| No imperative language | `cut_priority` (ordinal rank) + `cut_rationale` (evidence list); banned language list in module |
| PRE_MODEL rookies ranked last with explicit caveat | Tier D with `"pre_model_no_nfl_games_insufficient_signal"` caveat |
| No Engine A/B model artifacts changed | W1–W3 are read-only consumers of existing scoring outputs |
| No `latest.json`, `v2_manifest.json`, PVO assembler, `roster_auditor.py` changes | Out of scope |

---

## Non-Goals (Phase 21)

- Automatic roster submission to Sleeper API — display only
- Trade-away suggestions — Trade Lab scope
- Waiver wire rankings or add-priority scoring — Waiver Radar is limited to drop pairing
- Refreshing the PVO batch — run `build_universe_pvo_batch.py` manually beforehand if data is stale
- Changing the PRE_MODEL definition — Phase 22+ decision
- Modifying `app/services/roster_auditor.py` — the live audit service is independent of Phase 21

---

## Open Questions (David's call before W1 implementation)

1. **PRE_MODEL ranking**: Should PRE_MODEL active players (2026 rookies with no NFL data) be exempt from the cut list entirely, or appear in tier D with a strong caveat? Recommended: **include in tier D** — David should see them rather than have the engine hide them.

2. **Roster limit source**: Should the engine read `roster_positions` live from the Sleeper snapshot (auto-adjusting to any league settings change), or should capacity constants be locked in `resources/david_league_context.json`? Recommended: **read live from snapshot**.

3. **Waiver card enrichment scope**: Should `recommended_drop` appear on WAIVER_CANDIDATE cards only, or also on trade-type cards (ROSTER_SURPLUS_DEFICIT_MATCH, DIVERGENCE_MODEL_HIGH)? Recommended: **WAIVER_CANDIDATE only** — the drop pairing is only meaningful for an add/drop transaction.
