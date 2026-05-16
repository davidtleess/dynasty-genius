# Dynasty Genius Phase 14 Execution Roadmap
*Unified Valuation (DVS), Prospect Bridging, and Superflex VAR*

Date: 2026-05-16
Status: APPROVED — ready for spec

---

## 1. Executive Strategy

Phase 14 represents the critical leap from isolated machine learning models (Engine A vs. Engine B) to a unified asset management system. The objective is to calculate a within-position Dynasty Value Score (DVS) and establish the Value Over Replacement Player (VAR) layer required for trade evaluation.

This phase prioritizes auditability and calibration over complexity. We reject Bayesian blended priors for rookies in favor of transparent caveat flags, and we reject cross-engine P90 unification in favor of engine-native scaling.

---

## 2. DVS Architecture & Scale Resolution

Both research inputs confirm that forcing Engine B (veteran 2-year averages) to use Engine A (rookie peak projections) P90 constants artificially suppresses elite veteran scores.

### The Normalization Math (Option C)

DVS is normalized using engine-native, position-specific P90 ceilings.

**Engine B P90 constants** (derived from `app/data/training/engine_b_features_v2.csv`, May 2026 diagnostic):

| Position | P90 (avg_ppg_t1_t2) |
|----------|----------------------|
| QB       | 20.1                 |
| RB       | 15.7                 |
| WR       | 14.5                 |
| TE       | 9.4                  |

**Formula:**
```
DVS_raw = (predicted_avg_ppg_t1_t2 / POSITION_P90_AVG_PPG_B) * 100.0
DVS     = clamp(DVS_raw, 0.0, 100.0)
```

**Display precision:** Surface DVS as a float to one decimal place (e.g., `84.1`). This resolves tie-clustering in rank-sorted surfaces without implying the additive trade-liquidity semantics of KTC's 0–9999 scale. Internal storage: full float precision.

**Scale decision:** Maintain the 0–100 scale. A DVS of 84.1 translates cleanly to "84.1% of the elite positional ceiling." Expanding to 0–1000 is deferred — it is only warranted if DVS feeds E27 trade math directly, which is Phase 15 scope.

**Engine A:** Existing formula and P90 constants (WR 12.7, RB 14.6, TE 9.1, QB 16.7) remain unchanged for prospects.

### PVO Fields Populated

| Field | Type | Description |
|-------|------|-------------|
| `dynasty_value_score` | float \| None | 0–100.0, one decimal precision |
| `dvs_engine` | str | `"A"` or `"B"` — provenance flag |
| `dvs_p90_ref` | float | P90 constant used at scoring time (for audit) |
| `dvs_clamped` | bool | True when raw DVS exceeded 100 |
| `dvs_caveat` | str \| None | Populated for PRE_MODEL, Dead Window, or TE G3-deferred cases |

---

## 3. The Prospect-to-Veteran Bridge (Years 1–3)

### The Dead Window

A systemic gap occurs when a rookie completes their first season. They are no longer a prospect, but may lack the minimum `games_t` threshold for Engine B to generate a reliable projection. If forcefully routed to Engine B, they receive a null or heavily penalized score.

### Approach: Option B — Explicit Caveat Protocol

Players in the Dead Window (Years 1–2, insufficient `games_t` for Engine B) retain their Engine A score as the baseline prior. Their PVO is flagged with:

```
dvs_caveat = "Insufficient professional season data — Engine A prospect score used as prior"
```

**Rejected alternative:** Bayesian blending (weighting Engine A and B by `games_t`) is mathematically appealing but operationally premature. It obscures provenance, makes decision-card explanation harder, and is not justified at current single-league data volume. Defer to Phase 15+.

### TE Caveat

TE was promoted to `ACTIVE_B` in Phase 13.3. G1 (rank correlation) and G2 (RMSE stability) both passed. G3 (market superiority) was **deferred** — not failed. `ENGINE_B_EXPERIMENTAL_POSITIONS` is `frozenset()`.

TE veterans receive DVS via the Engine B formula (TE P90 = 9.4). They do not receive an "experimental fallback" caveat. The correct TE-specific caveat is:

```
dvs_caveat = "TE market superiority gate deferred — projection-quality score only"
```

This caveat remains until G3 is cleared in a future validation cycle. `decision_supported` stays False for TE.

### Hard Identity Gate

Phase 14 cannot ship until an automated identity reconciliation report verifies 100% lossless handoff between Engine A's canonical player IDs and Engine B's player IDs for the 2024 and 2025 draft classes. Silent identity failure (a player re-IDing at engine transition) is the highest-risk regression vector — it can cause a player to appear permanently PRE_MODEL or to display two DVS entries.

**Required artifact:** cohort reconciliation report showing 100% continuity for both classes, archived before 14.2 implementation begins.

---

## 4. Superflex VAR (Value Over Replacement)

### Replacement Baselines

| Position | Threshold | Derivation |
|----------|-----------|------------|
| QB | QB25 | 12 teams × 2 QB slots (QB + Superflex) = 24 starters; QB25 is first replacement |
| RB | RB33 | 12 × 2 = 24 primary + ~9 flex (40% RB allocation in Full PPR) = ~33 |
| WR | WR53 | 12 × 3 = 36 primary + ~7 flex (60% WR allocation) + variance buffer = 53 |
| TE | TE13 | 12 × 1 = 12 primary + 1 buffer = 13 |

### Replacement Baseline Derivation — Inference Time, Not Training CSV

The replacement PPG for each position is **not** extracted from the training CSV historical outcomes. It is derived from the current Engine B scoring run:

1. Score all active Engine B players at scoring time.
2. For each position, sort by `predicted_avg_ppg_t1_t2` descending.
3. The replacement baseline PPG = `predicted_avg_ppg_t1_t2` of the player at rank N (QB25, RB33, WR53, TE13).
4. Replacement DVS = `replacement_PPG / POSITION_P90_AVG_PPG_B * 100.0`.
5. `value_above_replacement = player_DVS - replacement_DVS`.

The training CSV P90 values (section 2) are constants for normalization. The replacement baseline PPG is a live value recomputed each scoring cycle.

### Scope: Within-Position VAR

Phase 14 VAR is **within-position only**. A TE `value_above_replacement` of +20 and a QB `value_above_replacement` of +20 are not cross-positionally equivalent — they reference different P90 denominators (TE=9.4 vs QB=20.1) and different positional scarcity conditions.

Cross-positional comparability (Superflex QB scarcity multiplier applied over VAR) is Phase 15 scope. Phase 14 delivers within-position VAR, which enables:
- Sorting and ranking within a position on the Rookie Board and Trade Lab
- Within-position buy/sell signal generation once NOISE_BAND clears

**Do not surface VAR as a cross-positional trade currency in Phase 14 UI.** Defer that framing to Phase 15.

---

## 5. Calibration & Market Divergence

### Isotonic Regression

Rejected as a primary DVS normalization method — it produces a piecewise constant function that introduces ties and destroys the ordinal ranking required for the Rookie Board.

Reserved for use as an **offline calibration audit artifact only**: fit isotonic regression of DVS rank against market rank (KTC Superflex Full PPR / FantasyCalc dynasty) by position to verify DVS rank-order is not pathologically misaligned with market consensus. This is a one-time validation artifact, not a code change to the scoring pipeline.

### NOISE_BAND Governance

Divergence flags for active veterans must remain suppressed until the scheduled NOISE_BAND recalibration window closes in mid-July 2026. Emitting veteran divergence flags before NOISE_BAND is calibrated will flood the UI with false positives. VAR may compute and store internally; veteran-side divergence flags do not surface.

---

## 6. Gated Workstreams

### Subphase 14.1: Empirical Constants & Identity Gate

1. Confirm Engine B P90 constants (QB 20.1, RB 15.7, WR 14.5, TE 9.4) are hardcoded into the configuration layer.
2. Execute the 2024–2025 identity reconciliation report. 100% match required before 14.2 begins.
3. Confirm the `games_t` threshold for Engine B eligibility is defined and documented.

### Subphase 14.2: DVS Assembly & Bridge

1. Update `pvo_assembler.py` line 316: implement Engine B P90 DVS formula for `ACTIVE_B` players.
2. Populate `dvs_engine`, `dvs_p90_ref`, `dvs_clamped`, `dvs_caveat` fields on the PVO.
3. Implement Dead Window fallback routing: players below `games_t` threshold retain Engine A DVS with mandatory caveat string.
4. Implement TE-specific caveat for G3-deferred state.
5. Validation tests: ceiling fraction (~10% per position by construction), field population, caveat strings, Engine A fallback path asserted absent from veterans.

### Subphase 14.3: VAR & Calibration Audit

1. Implement within-position VAR: at scoring time, rank active Engine B players per position, extract replacement baseline PPG at threshold rank, compute `value_above_replacement = player_DVS - replacement_DVS`.
2. Activate `value_above_replacement` generation for all `ACTIVE_B` players.
3. Update Rookie Board and any DVS-sorted surfaces to handle mixed Engine A / Engine B populations without null-sort errors.
4. Generate isotonic regression calibration plot (DVS rank vs. KTC Superflex Full PPR rank, per position) as a static audit artifact. Flag any non-monotonic or extreme-tail divergence for David review.
5. Keep veteran divergence flags dark — awaiting NOISE_BAND release (mid-July 2026).

---

## 7. Explicit Out-of-Scope for Phase 14

- Cross-positional VAR (scarcity-adjusted, Superflex QB premium) — Phase 15
- DVS scale expansion to 0–1000 — Phase 15, conditional on E27 trade math integration
- Bayesian blended Engine A/B prior for Dead Window — Phase 15+
- TE model refactoring or re-validation — separate future cycle
- UI polish on DVS surface — Phase 15 (trust before polish)
- Market features as model inputs — permanently banned
- Trade Lab DVS-based cross-position valuation — Phase 15

---

*Roadmap approved. Spec may proceed on Subphase 14.1 immediately upon identity gate feasibility confirmation.*
