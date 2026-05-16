---
document: Phase 14 DVS Normalization, Prospect-to-Veteran Bridge, and VAR Activation
version: 1.0.0
status: APPROVED
date: 2026-05-16
owner: David
prepared_by: Claude
phase: 14
evidence_artifacts:
  - app/data/training/engine_b_features_v2.csv (P90 diagnostic, May 2026)
  - app/data/backtest/runs/eba2c2e4-9742-44ed-945a-8b46a0cb670f/backtest_result_TE.json
decision_notes:
  - docs/strategies/Dynasty Genius Phase 14 Research Brief.md
  - docs/strategies/Dynasty Genius Phase 14 Execution Roadmap.md
  - docs/strategies/compass_artifact_wf-a3216f2e-80ba-4c04-8488-e03aa2afa80c_text_markdown.md
  - docs/strategies/Dynasty Genius Product Development Framework.pdf
governance_read:
  - docs/governance/02-agent-operating-loop.md
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - AGENT_SYNC.md
---

# Phase 14 DVS Normalization, Prospect-to-Veteran Bridge, and VAR Activation

Phase 14 — Production Implementation Authorization

---

## 1. Decision Summary

Three changes are jointly authorized:

1. **DVS normalization for Engine B:** implement a per-position P90-ceiling formula that populates `dynasty_value_score` for all `ACTIVE_B` players. Currently `dynasty_value_score` is `None` for all Engine B players (`pvo_assembler.py` line 316 comment).

2. **Prospect-to-veteran bridge:** implement the Dead Window fallback that retains Engine A DVS with an explicit caveat for players who have exited prospect status but have insufficient Engine B data.

3. **VAR activation for veterans:** implement within-position `value_above_replacement` computation for Engine B players using inference-time replacement baselines.

All three depend on the identity gate in Subphase 14.1 clearing first.

**Scale decision:** DVS stays on the 0–100 scale, surfaced as a float with one decimal place (e.g., `84.1`). The 0–1000 expansion is deferred to Phase 15 and is only warranted when DVS feeds E27 trade math directly.

**VAR scope:** Phase 14 VAR is within-position only. A TE VAR of +20 and a QB VAR of +20 are not cross-positionally equivalent. Cross-positional scarcity-adjusted VAR (Superflex QB premium) is Phase 15 scope.

---

## 2. Evidence Basis

### Engine B P90 Diagnostic (May 2026)

P90 of `avg_ppg_t1_t2` from `app/data/training/engine_b_features_v2.csv`, full training distribution per position:

| Position | n     | Engine B P90 | Engine A P90 | Gap    |
|----------|-------|--------------|--------------|--------|
| QB       | 309   | 20.07        | 16.7         | +20.2% |
| RB       | 660   | 15.71        | 14.6         | +7.6%  |
| WR       | 1,059 | 14.46        | 12.7         | +13.9% |
| TE       | 849   | 9.36         | 9.1          | +2.8%  |

DVS simulation under Option A (reuse Engine A P90) vs. Option C (Engine B P90):

| Position | Option A capped at 100 | Option C capped at 100 |
|----------|------------------------|------------------------|
| QB       | 29.4%                  | 10.0%                  |
| RB       | 13.0%                  | 10.0%                  |
| WR       | 16.8%                  | 10.0%                  |
| TE       | 10.8%                  | 10.0%                  |

Option A is disqualified at QB and WR. 29% of active QBs indistinguishable at DVS=100 destroys top-tier rank discrimination. Option C is selected.

### Research Inputs

Three independent research artifacts converged on Option C (Engine B P90 constants), Option B (explicit caveat bridge), and within-position VAR first. All three agree on VAR thresholds QB25/RB33/WR53/TE13. The Compass artifact and PDF framework diverged on scale (0–100 vs. 0–1000) — resolved by keeping 0–100 with float precision, which addresses the tie-clustering concern without implying KTC-style additivity.

---

## 3. Authorized Changes

### 3.1 Engine B P90 Constants and MIN_GAMES Threshold

Add to `src/dynasty_genius/models/engine_b_contract.py`:

```python
# ── Engine B DVS Normalization Constants ──────────────────────────────────────
# P90 of avg_ppg_t1_t2 from engine_b_features_v2.csv, May 2026 diagnostic.
# Used as position-specific ceiling for dynasty_value_score normalization.
# Frozen at May 2026 values. Recompute only when Engine B training distribution
# materially changes — requires a new diagnostic run and David approval.
ENGINE_B_P90_PPG: dict[str, float] = {
    "QB": 20.1,
    "RB": 15.7,
    "WR": 14.5,
    "TE": 9.4,
}

# ── VAR Replacement Baselines (12-team Superflex Full PPR) ────────────────────
# Rank N such that the Nth active player by predicted PPG defines replacement level.
# QB: 12 × 2 slots = 24 starters + 1 = QB25 (Superflex-native; NOT 1QB-derived).
# RB: 12 × 2 = 24 + ~9 flex (40% RB in Full PPR) = RB33.
# WR: 12 × 3 = 36 + ~7 flex (60% WR in Full PPR) + buffer = WR53.
# TE: 12 × 1 = 12 + 1 buffer = TE13.
ENGINE_B_VAR_THRESHOLDS: dict[str, int] = {
    "QB": 25,
    "RB": 33,
    "WR": 53,
    "TE": 13,
}

# Minimum games in feature season required for Engine B DVS eligibility.
# Below this threshold, a player is in the Dead Window: retain Engine A DVS
# with explicit caveat, or stay PRE_MODEL if Engine A data is also absent.
ENGINE_B_MIN_GAMES_T: int = 8
```

### 3.2 PVO Schema — New DVS Provenance Fields

Add to `PlayerValueObject` in `src/dynasty_genius/models/player_value_object.py`:

```python
# ── DVS provenance — populated when dynasty_value_score is non-null ───────────
dvs_engine: Optional[str] = None      # "A" | "B" — which engine produced DVS
dvs_p90_ref: Optional[float] = None   # P90 constant used at scoring time
dvs_clamped: Optional[bool] = None    # True if raw DVS exceeded 100 before clamping
```

These fields are None when `dynasty_value_score` is None. They are populated on every scoring path that produces a non-null DVS.

### 3.3 DVS Formula — Engine B Path in pvo_assembler.py

Replace the blocking comment at line 316 and implement DVS in the Engine B path:

```python
# Engine B: populate active-player metadata from resolved score.
if engine_b_resolved:
    engine_used = "engine_b"
    model_version = engine_b_resolved["engine"]
    source_season = engine_b_resolved.get("feature_season")
    projection_2y = engine_b_resolved.get("predicted_avg_ppg_t1_t2")
    is_experimental = engine_b_resolved.get("experimental", False)
    model_grade = "EXPERIMENTAL" if is_experimental else "ACTIVE_B"
    caveats = [c for c in caveats if not c.startswith("dynasty_value_score unavailable:")]
    for caveat in engine_b_resolved.get("caveats", []):
        if caveat not in caveats:
            caveats.append(caveat)

    # DVS normalization — Engine B path.
    # Formula: clamp(predicted_avg_ppg_t1_t2 / POSITION_P90_PPG_B * 100, 0, 100)
    # P90 constants are Engine B-native (May 2026 diagnostic from engine_b_features_v2.csv).
    # Veterans with games_t below ENGINE_B_MIN_GAMES_T are routed to the Dead Window
    # fallback below; this block runs only for Engine B-eligible players.
    games_t = features.get("games_t")
    pos_upper = identity.position.upper()
    _b_p90 = ENGINE_B_P90_PPG.get(pos_upper)
    _below_games_gate = (
        games_t is not None
        and float(games_t) < ENGINE_B_MIN_GAMES_T
    )

    if (projection_2y is not None
            and _b_p90 is not None
            and not _below_games_gate):
        dvs_raw = projection_2y / _b_p90 * 100.0
        dvs_clamped_flag = dvs_raw > 100.0
        dynasty_value_score = round(min(100.0, max(0.0, dvs_raw)), 1)
        dvs_engine = "B"
        dvs_p90_ref_val = _b_p90
        dvs_clamped_val = dvs_clamped_flag

    # TE-specific caveat: G3 (market superiority) deferred; decision_supported = False.
    if pos_upper == "TE" and model_grade == "ACTIVE_B":
        _te_caveat = "TE market superiority gate deferred — projection-quality score only"
        if _te_caveat not in caveats:
            caveats.append(_te_caveat)

    # QB low-volume flag (unchanged from Phase 12.5).
    if pos_upper == "QB":
        if games_t is not None and float(games_t) < 3:
            backup_caveat = "High-Efficiency / Low-Volume Anomaly (Backup Profile)"
            if backup_caveat not in caveats:
                caveats.append(backup_caveat)
```

The local variables `dvs_engine`, `dvs_p90_ref_val`, and `dvs_clamped_val` are passed to the PVO constructor alongside `dynasty_value_score` (see Section 3.5).

### 3.4 Dead Window Bridge — Engine A Fallback for Year-1 Veterans

Insert immediately after the Engine B DVS block. This fires when Engine B exists but `games_t < ENGINE_B_MIN_GAMES_T`:

```python
# Dead Window bridge: player has exited prospect status and Engine B feature data
# exists, but games_t is below the reliability threshold. Retain Engine A DVS as
# a prior if draft capital is present; otherwise stay PRE_MODEL.
# The caveat is mandatory — the user must know the score rests on draft capital,
# not verified professional efficiency.
if engine_b_resolved and _below_games_gate:
    _dw_caveat = (
        "Insufficient professional season data — Engine A prospect score used as prior"
    )
    # Try Engine A fallback
    pick = features.get("pick")
    round_ = features.get("round")
    age = features.get("age")
    if pick is not None and round_ is not None and age is not None:
        _a_result = score_prospect(identity.position, float(pick), float(round_), float(age))
        if _a_result:
            dynasty_value_score = _a_result["dynasty_value_score"]
            dvs_engine = "A"
            dvs_p90_ref_val = _P90_PPG.get(pos_upper)
            dvs_clamped_val = _a_result["dynasty_value_score"] >= 100.0
    # Caveat is appended regardless of whether Engine A data was available.
    if _dw_caveat not in caveats:
        caveats.append(_dw_caveat)
```

**Constraint:** The Dead Window bridge must not silently fall through. If Engine A data is also absent, `dynasty_value_score` stays None and the caveat is still appended. No inference without caveat.

### 3.5 PVO Constructor Update

Pass the new fields to `PlayerValueObject(...)`:

```python
pvo = PlayerValueObject(
    ...
    dynasty_value_score=dynasty_value_score,
    dvs_engine=dvs_engine,           # new
    dvs_p90_ref=dvs_p90_ref_val,     # new
    dvs_clamped=dvs_clamped_val,     # new
    ...
)
```

Initialize the new local variables before the Engine A / Engine B blocks:

```python
dvs_engine: Optional[str] = None
dvs_p90_ref_val: Optional[float] = None
dvs_clamped_val: Optional[bool] = None
```

### 3.6 VAR Computation — Batch Scoring Script

**Architecture note:** `value_above_replacement` requires knowing the replacement-level player's predicted PPG for the full active population at scoring time. This is a population-level operation that cannot be performed in single-player `assemble_pvo`. VAR is computed in a batch scoring step after DVS is populated for all active players.

Create `scripts/compute_var_batch.py`:

**Logic:**

1. Load all active Engine B player PVOs (or score from feature store if PVOs are not persisted).
2. For each position in `{QB, RB, WR, TE}`:
   a. Filter to `ACTIVE_B` players with non-null `dynasty_value_score`.
   b. Sort by `dynasty_value_score` descending.
   c. Replacement rank N = `ENGINE_B_VAR_THRESHOLDS[position]`.
   d. If fewer than N players exist for the position, log a warning and skip VAR for that position.
   e. Replacement DVS = `dynasty_value_score` of the player at rank N (zero-indexed: `sorted_players[N - 1]`).
3. For each player in the position:
   - `value_above_replacement = round(player_dvs - replacement_dvs, 1)`
   - Players ranked below replacement: VAR will be negative; this is expected and correct.
4. Write updated PVO records (or a VAR supplement table) with `value_above_replacement` populated.
5. Players with `dynasty_value_score = None` (PRE_MODEL, Dead Window without Engine A fallback): `value_above_replacement` stays `None`.

**Veteran divergence flags:** Do not activate in Phase 14. `value_above_replacement` computes and stores internally. User-facing veteran divergence flags wait for NOISE_BAND release (mid-July 2026). The batch script must not emit divergence signals.

**VAR is within-position only:** Do not rank QBs against WRs by VAR in Phase 14. Cross-positional comparison requires a scarcity multiplier that is Phase 15 scope.

### 3.7 Calibration Audit — Isotonic Regression (14.3)

Create a one-time offline audit script `scripts/audit_dvs_calibration.py`:

1. Pull KTC Superflex Full PPR consensus and FantasyCalc dynasty values (overlay only — these must not enter Engine B features or the DVS formula).
2. Join market ranks against DVS ranks by position.
3. Fit isotonic regression of DVS rank against market rank per position.
4. Produce a calibration plot per position; flag any position where the fit is non-monotonic or shows extreme tail divergence.
5. Output: a static audit artifact at `docs/validation/phase14-dvs-calibration-audit.md`. This is not a code change to the scoring pipeline.

Market data pulled for this audit must be sourced through the existing market overlay adapter and must not be committed to the training CSV or any model input path.

### 3.8 Files That Must Not Change

- Engine A model artifacts, training scripts, or P90 constants (Engine A's `_P90_PPG` in `scoring/engine_a.py` is separate from the new Engine B constants)
- Engine B model artifacts (`qb_v2.pkl`, `rb_v2.pkl`, `wr_v2.pkl`, `te_v3.pkl`) or their training pipeline
- `ENGINE_B_EXPERIMENTAL_POSITIONS` (remains `frozenset()` — TE is `ACTIVE_B`)
- NOISE_BAND (locked at 0.10 until mid-July 2026)
- `decision_supported` on any surface (remains `False`)
- Market overlay join order (market data joins the PVO after DVS scoring, never before)
- Walk-forward harness or backtest infrastructure

---

## 4. Subphase 14.1 Hard Gate — Identity Reconciliation

**Phase 14 cannot advance to Subphase 14.2 until this gate clears.**

Run an identity reconciliation report for the 2024 and 2025 draft classes:

1. Extract canonical `player_id` records for all players with `draft_class` 2024 or 2025 from the Engine A scoring records (or identity snapshot at `app/data/identity/`).
2. For each player, verify that a matching record exists in the Engine B feature store (`engine_b_features_v2.csv`) or equivalent feature source, keyed on `canonical_player_id`.
3. Flag any player who:
   - Has an Engine A record but no Engine B feature store entry (expected for players not yet in their second NFL season — acceptable, confirm as Dead Window candidates)
   - Has mismatched IDs between Engine A records and Engine B feature store entries (critical: silent ID mismatch will cause duplicate DVS entries or permanent PRE_MODEL state)
   - Has a null or missing `canonical_player_id` on either side (critical)
4. Required output: `docs/validation/phase14-identity-reconciliation-2024-2025.md`

**Pass criteria:** 100% of players with Engine B feature store entries have a matching, non-null `canonical_player_id` that resolves to the same player in Engine A records. ID mismatches = 0. Players present in Engine A but absent from Engine B feature store are expected (Dead Window) and logged, not failed.

**Failure action:** Stop. Do not proceed to 14.2. Log the conflict in the daily ledger and escalate to David.

---

## 5. Required Tests

### 5.1 DVS Formula

```python
def test_engine_b_dvs_formula_wr():
    # WR P90 = 14.5; 14.5 PPG → DVS 100.0 (at ceiling)
    # 7.25 PPG → DVS 50.0
    # Verify formula: clamp(ppg / p90 * 100, 0, 100)
```

Tests must cover: correct output for known PPG inputs at each position, clamping at 100, clamping at 0 for negative predictions, float precision to one decimal.

### 5.2 DVS Ceiling Fraction

After scoring a representative batch of Engine B training players, assert that no more than ~12% of players at any position have `dvs_clamped = True`. The P90 normalization is designed so exactly 10% of the training distribution hits the ceiling; allow 2% tolerance for inference-set variation.

### 5.3 DVS Provenance Fields

Assert that for any Engine B player with a non-null `dynasty_value_score`:
- `dvs_engine == "B"`
- `dvs_p90_ref == ENGINE_B_P90_PPG[position]`
- `dvs_clamped` is a bool (not None)

### 5.4 Dead Window Caveat — Engine A Fallback Present

For a player with `is_prospect=False`, `games_t < ENGINE_B_MIN_GAMES_T`, and Engine A inputs (pick, round, age) present:
- `dynasty_value_score` is non-null (Engine A value)
- `dvs_engine == "A"`
- `"Insufficient professional season data — Engine A prospect score used as prior"` is in `caveats`

### 5.5 Dead Window Caveat — Engine A Fallback Absent

For a player with `is_prospect=False`, `games_t < ENGINE_B_MIN_GAMES_T`, and no Engine A inputs:
- `dynasty_value_score` is None
- `"Insufficient professional season data — Engine A prospect score used as prior"` is in `caveats`

### 5.6 TE G3-Deferred Caveat

For any `ACTIVE_B` TE player with a non-null Engine B score:
- `"TE market superiority gate deferred — projection-quality score only"` is in `caveats`

### 5.7 Engine B DVS Does Not Fire Below Games Gate

For a player with `is_prospect=False`, `games_t = 4` (below threshold), and Engine B prediction present:
- Engine B DVS formula does not run (player routes through Dead Window logic)
- `dvs_engine` is not `"B"` unless the Engine A fallback was used (in which case `"A"`)

### 5.8 Engine A DVS Path Unchanged

For a prospect with pick, round, and age present:
- `dynasty_value_score` still computed via Engine A formula
- `dvs_engine == "A"`
- `dvs_p90_ref` matches the Engine A P90 constant for the position
- No regression from Engine A to Engine B path

### 5.9 VAR Null for PRE_MODEL

For any player where `dynasty_value_score is None`:
- `value_above_replacement is None`

### 5.10 VAR Below-Replacement Is Negative

For a player ranked below the replacement threshold at their position:
- `value_above_replacement < 0.0`

### 5.11 Market Data Does Not Appear in DVS Formula

Assert that `ENGINE_B_P90_PPG` constants contain no reference to KTC, FantasyCalc, or ADP values. Assert that `pvo_assembler.py` DVS computation path accesses no market overlay fields before DVS is assigned.

---

## 6. Governance Constraints

- Engine B P90 constants (`ENGINE_B_P90_PPG`) are frozen at May 2026 values. They must not be updated without a new diagnostic run and David's explicit approval. Version the constants in `dvs_p90_ref` per player-row at scoring time.
- Market-derived values must not enter the DVS formula or Engine B feature matrix at any point.
- Veteran divergence flags must remain suppressed until NOISE_BAND is released (mid-July 2026). `value_above_replacement` may be computed internally but must not trigger user-facing buy/sell signals in Phase 14.
- `decision_supported` remains `False` on all surfaces. DVS activation does not change this.
- TE DVS is computed using the Engine B formula. The TE caveat is the G3-deferred string defined in Section 3.3. Do not use "experimental v1 fallback" language — TE was promoted to `ACTIVE_B` in Phase 13.3 with G1 and G2 passing; G3 was deferred, not failed.
- Engine A P90 constants in `scoring/engine_a.py` (`_P90_PPG`) are separate from Engine B constants. Do not merge or alias them.
- Dead Window bridge must never silently suppress the caveat. If a player is in the Dead Window, the caveat string is appended regardless of whether Engine A data is available.

---

## 7. Implementation Sequence

### Subphase 14.1 — Constants and Identity Gate

1. Add `ENGINE_B_P90_PPG`, `ENGINE_B_VAR_THRESHOLDS`, `ENGINE_B_MIN_GAMES_T` to `engine_b_contract.py`.
2. Run the 2024–2025 identity reconciliation report. **Do not proceed past this step until the gate clears.** Write `docs/validation/phase14-identity-reconciliation-2024-2025.md`.
3. Write failing tests for DVS formula, provenance fields, Dead Window caveat, TE caveat, VAR null, and market isolation (tests 5.1–5.11).

### Subphase 14.2 — DVS Assembly and Bridge

4. Add `dvs_engine`, `dvs_p90_ref`, `dvs_clamped` to `PlayerValueObject` in `player_value_object.py`.
5. In `pvo_assembler.py`:
   a. Import `ENGINE_B_P90_PPG`, `ENGINE_B_MIN_GAMES_T` from `engine_b_contract`.
   b. Initialize `dvs_engine`, `dvs_p90_ref_val`, `dvs_clamped_val` as `None` before the Engine A/B blocks.
   c. Remove the blocking comment at line 316.
   d. Implement Engine B DVS formula (Section 3.3).
   e. Implement Dead Window bridge (Section 3.4).
   f. Implement TE G3-deferred caveat (Section 3.3).
   g. Update PVO constructor call (Section 3.5).
6. Run full test suite. All 14.1 and 14.2 tests must pass. No existing tests may regress.

### Subphase 14.3 — VAR and Calibration Audit

7. Implement `scripts/compute_var_batch.py` (Section 3.6). VAR writes internally; veteran divergence flags remain dark.
8. Implement `scripts/audit_dvs_calibration.py` (Section 3.7). Produce static audit artifact. No pipeline code changes.
9. Update AGENT_SYNC.md and daily ledger entry.
10. Update `docs/validation/` with any audit findings from step 8.

---

## 8. Out of Scope for Phase 14

- Cross-positional VAR (scarcity multiplier, Superflex QB premium) — Phase 15
- DVS scale expansion to 0–1000 — Phase 15, conditional on E27 trade math integration
- Bayesian blended Engine A/B transition for Dead Window — Phase 15+
- `dvs_pct` auxiliary percentile field — Phase 15 (compute only, not display)
- Divergence flag expansion to veterans — post-NOISE_BAND (mid-July 2026)
- Trade Lab DVS-based cross-position valuation — Phase 15
- TE model refactoring or re-validation — separate future cycle
- UI polish on DVS surface — Phase 15 (trust before polish)
- Market features as model inputs — permanently banned
- Engine A P90 constant changes — any Engine A retraining is a separate phase
- Cross-engine isotonic remapping of prospect DVS onto veteran DVS scale — Phase 15+
  (requires 2024–2025 cohorts to have aged through both engines; not possible until end of 2026 season)
