# Dynasty Genius Phase 14 Research Brief

**Dynasty Value Score (DVS) Normalization and Prospect-to-Veteran Bridge**

Date: 2026-05-16
Author: Claude
Status: RESEARCH — pending David review and spec approval

---

## 1. The Core Problem

`dynasty_value_score` is the unified valuation field every decision surface reads from.
Engine A populates it for prospects. Engine B never populates it.

The comment in `pvo_assembler.py` line 316 is the blocker:

```python
# dynasty_value_score stays None — no calibrated A/B normalization exists yet.
```

This means:
- All Engine B players (active veterans: QB/RB/WR/TE after Phase 13.3) show `dynasty_value_score: null`
- `value_above_replacement` stays `null` for all veterans (VAR computes from DVS only)
- The Rookie Board sorts scored cards by DVS descending — veterans have no comparable score
- Divergence flags that reference DVS rank cannot fire for veterans

Phase 14 needs to define and implement the normalization that makes Engine B predictions
appear on the same 0–100 scale as Engine A, and establish when/how players route from
Engine A to Engine B as they transition from rookies to active veterans.

---

## 2. What Exists

### Engine A Output
- Input: draft pick, round, age
- Output: `y24_ppg_raw` → normalized to `dynasty_value_score` via `y24_ppg / POSITION_P90_PPG * 100`
- P90 ceilings: WR 12.7, RB 14.6, TE 9.1, QB 16.7 (from training distribution)
- Scale: 0–100, clamped at 100
- Model grade: `PROSPECT_C` (WR/RB/TE), `PROSPECT_D` (QB)
- Fires only for `is_prospect=True` with pick, round, and age present

### Engine B Output
- Input: per-season usage, snap share, route participation, YPRR, age, etc.
- Output: `predicted_avg_ppg_t1_t2` — predicted PPG average over next 2 seasons
- Scale: raw PPG (no 0–100 normalization)
- Model grade: `ACTIVE_B` (QB/RB/WR/TE after Phase 13.3 promotion)
- Fires only for active NFL players with feature-season data present

### VAR Thresholds (Phase 9.3)
- Replacement level computed from `dynasty_value_score` only
- Position thresholds: QB25, RB33, WR53, TE13 (based on Engine A scoring scale)
- Currently produces `null` for all veterans — thresholds are theoretically defined
  but practically unused

---

## 3. Problem 1 — DVS Normalization for Engine B

### The Question

How do we put Engine B's `predicted_avg_ppg_t1_t2` on a 0–100 scale comparable
to Engine A's `dynasty_value_score`?

### Option A: Same P90 Normalization (Match Engine A's Formula)

```python
dvs = min(100.0, max(0.0, predicted_avg_ppg_t1_t2 / POSITION_P90_PPG * 100.0))
```

Using the same `POSITION_P90_PPG` as Engine A.

**Pro:** Mechanically comparable. A TE scoring 9.1 PPG → DVS 100; a TE at 4.5 PPG → DVS ~50.
**Con:** Engine A predicts y24 PPG (one season); Engine B predicts avg PPG over T+1 and T+2
(two seasons). These are not the same outcome concept. A veteran in the middle of a career
is being compared against a prospect's peak-season ceiling.

**Key question:** Are Engine A's P90 values still the right ceiling for Engine B predictions?
Engine B's T+1/T+2 average is expected to be lower than a draft-class peak — veterans regress
toward mean, and the 2-year average smooths out peak season effects. The P90 of Engine B's
training outcomes (`avg_ppg_t1_t2`) should be computed and compared against Engine A's P90
before assuming the same ceiling applies.

### Option B: Engine B Distribution Percentile

Normalize against the actual distribution of Engine B predictions (or training outcomes)
at each position. DVS = percentile rank among all current active players at the position.

```python
dvs = stats.percentileofscore(active_position_predictions, predicted_avg_ppg_t1_t2)
```

**Pro:** Self-calibrating. Reflects true rank among active players.
**Con:** Score changes as the active roster changes (relative, not absolute). An elite WR
could go from DVS 95 to DVS 85 if three other elite WRs become active. Not stable across
seasons.

### Option C: Historical Training Outcome P90 (Recommended Starting Point)

Compute `POSITION_P90_AVG_PPG` from the Engine B training distribution
(`engine_b_features_v2.csv`, `avg_ppg_t1_t2` column, per position), then normalize:

```python
dvs = min(100.0, max(0.0, predicted_avg_ppg_t1_t2 / POSITION_P90_AVG_PPG_B * 100.0))
```

**Pro:** Absolute scale grounded in historical outcomes — stable across seasons.
**Con:** Introduces a second set of P90 constants (separate from Engine A's). The two
0–100 scales are conceptually comparable (both normalize by historical outcome ceiling)
but not mechanically identical.

**Trade-off vs Option A:** Option A reuses Engine A's P90 values. Option C computes new
P90 values from Engine B's actual training distribution. If Engine B's T+1/T+2 average
P90 is lower than Engine A's y24 P90 (likely), Option A understates veteran DVS; Option C
is calibrated to actual veteran outcomes.

### Decision Required

Before implementation: compute P90 of `avg_ppg_t1_t2` from the current Engine B training
CSV for each position and compare against the Engine A P90 constants. If they differ by
more than ~15%, Option A is miscalibrated for veterans.

---

## 4. Problem 2 — Prospect-to-Veteran Transition

### The Question

When does a player stop routing through Engine A and start routing through Engine B?

### Current Routing Logic (pvo_assembler.py)

Engine A fires when: `is_prospect=True AND pick AND round AND age are present`
Engine B fires when: `is_prospect=False AND feature-season data exists in feature store`

The `is_prospect` flag is set by the identity layer. Currently it reflects whether the
player has been drafted into the NFL and has had a full professional season recorded.

### The Gap

A player drafted in April 2026 is a prospect through the 2026 season. In 2027, after
their first NFL season, they should begin routing through Engine B — but only if:
1. Their feature data for 2026 exists in the feature store, AND
2. They have enough games to be in the training distribution (currently ≥ some games threshold)

If condition 1 or 2 fails, they fall to `PRE_MODEL` (no score). This means there is a
dead window between Engine A eligibility ending and Engine B eligibility beginning.

### The Bridge Requirement

The prospect-to-veteran bridge is the logic that prevents this dead window. Options:

**Option A: Engine A as Fallback for Year-1 Veterans**
If `is_prospect=False` but Engine B returns no score (insufficient games, not in feature
store), fall back to Engine A scoring if draft capital is still present.

**Pro:** No dead window. **Con:** Engine A scores on draft capital only — if the player's
rookie year revealed serious usage concerns, Engine A ignores that entirely.

**Option B: Explicit Caveat on Transition Players**
Allow dead window but surface it explicitly as a caveat: "Insufficient professional season
data — Engine A prospect score used as prior."

**Pro:** Honest about the model's limits. **Con:** Dead window is confusing on surfaces.

**Option C: Blended Prior (Advanced)**
Weight Engine A and Engine B by `games_t` for the first 1–2 seasons — as game count
grows, Engine B weight increases. Full Engine B after N games threshold.

**Pro:** Smooth transition. **Con:** Significantly more complex; harder to audit and
explain to David on a decision card.

**Recommended starting point:** Option B. Explicit caveat is honest and auditable.
The blended prior is a later enhancement if the dead window proves disruptive in practice.

### Identity Requirement

The transition protocol requires that a player's `canonical_player_id` is stable across
both the prospect phase (Sleeper-native, alias bridge) and the veteran phase (NFL GSIS,
Engine B feature store). Phase 13.1 (Identity Audit) built this foundation. Phase 14
should verify the identity handoff is complete for the 2024 and 2025 draft classes.

---

## 5. Problem 3 — VAR Threshold Review

The current VAR replacement thresholds (QB25, RB33, WR53, TE13) were set based on the
Engine A normalization scale. Once Engine B DVS is live, VAR is computed over a mixed
population (prospects on Engine A scale + veterans on Engine B scale).

Before Phase 14 can activate VAR for veterans, the following need to be resolved:

1. **Are the replacement thresholds position-rank or score-based?**
   Currently: position rank cutoff (25th QB by DVS = replacement level). If DVS is
   populated for veterans, the sort order changes and so does the replacement-level score.

2. **Can Engine A and Engine B DVS be safely sorted together?**
   Only if the normalization is truly comparable (see Problem 1). Mixing a prospect's
   Engine A DVS with a veteran's Engine B DVS in the same rank list requires confirmed
   scale alignment.

3. **Do the threshold counts still reflect David's league?**
   QB25, RB33, WR53, TE13 should be re-validated against the actual number of active
   starters in a 12-team Superflex PPR league across multiple seasons.

---

## 6. Downstream Impacts

Enabling DVS for veterans will cascade into:

- **Market divergence flags:** The divergence engine computes model-vs-market deltas.
  Currently these only fire for prospects (DVS non-null). Veterans will now have divergence
  flags — which means the NOISE_BAND calibration (locked until mid-July 2026) becomes
  more important to get right.

- **Trust Surface:** `model_grade` for Engine B players is `ACTIVE_B`. Once DVS is
  populated, the Trust Surface v2 model-card route may need a visual update to show DVS
  alongside the model card metrics.

- **Trade Lab:** Trade analysis currently can't compare veteran scores on a DVS basis.
  Once DVS is live, `delta_status` and trade comparison become more meaningful.

- **VAR in PVO:** `value_above_replacement` will go from `null` to a populated value for
  all Engine B players. Any display surface showing VAR needs to handle the transition
  from null to populated without breaking.

---

## 7. Open Questions for David

Before a spec can be written, the following need decisions:

1. **DVS normalization formula:** Option A (reuse Engine A P90), Option C (recompute from
   Engine B distribution), or something else? Requires looking at the actual P90 of
   `avg_ppg_t1_t2` in the training CSV.

2. **Prospect-to-veteran transition:** Explicit caveat on dead window (Option B) or
   Engine A fallback (Option A)?

3. **VAR activation:** Activate VAR for veterans in Phase 14, or defer until NOISE_BAND
   calibration window closes (mid-July 2026)? VAR and divergence flags are tightly
   coupled — activating DVS for veterans while NOISE_BAND is locked means new divergence
   signals under-calibrated noise tolerance.

4. **Scope of Phase 14:** DVS normalization only (Engine B → DVS), or also include
   the full prospect-to-veteran bridge logic, VAR threshold review, and divergence
   flag expansion?

---

## 8. Recommended Pre-Spec Investigation

Before writing the implementation spec, one diagnostic should be run locally:

```python
import pandas as pd
df = pd.read_csv("app/data/training/engine_b_features_v2.csv")
te = df[df["position"] == "TE"]
print(te["avg_ppg_t1_t2"].describe(percentiles=[0.5, 0.75, 0.9, 0.95]))
# Repeat for QB, RB, WR
```

Compare the P90 values against Engine A's `_P90_PPG` constants:
- WR: 12.7, RB: 14.6, TE: 9.1, QB: 16.7

If the Engine B P90 values are within ~10% of Engine A's, Option A (reuse existing
constants) is defensible. If they diverge significantly, new constants are required.

This is a 15-minute check that resolves the biggest open question before spec work begins.

---

## 9. Suggested Phase 14 Scope (Draft)

If David approves moving forward, the recommended spec scope is:

- **14.1 DVS Normalization:** compute Engine B P90 constants, add DVS formula to
  `pvo_assembler.py` for Engine B path, validation tests.
- **14.2 Prospect-Veteran Bridge:** define transition logic, explicit caveat, identity
  handoff validation for 2024–2025 draft classes.
- **14.3 VAR Activation:** re-validate replacement thresholds, activate VAR for veterans
  (conditional on NOISE_BAND timing).
- **14.4 Surface Polish:** update Trust Surface, Trade Lab, Rookie Board to handle
  populated veteran DVS without breakage.

DVS normalization (14.1) is the dependency for everything else. Start there.
