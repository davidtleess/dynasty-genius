# Spec: T4 — F-feature-refresh gate-semantic correction — v2 DRAFT

Date: 2026-06-26. Branch: feature/f-feature-refresh-t4-gate-semantics (off merged main f4b4c99). Author: Claude. Status: DRAFT for cockpit review → David approval → cockpit-TDD. Resumes the original F-feature-refresh sprint (T4→T6) after the te_v3 contamination remediation.

## 1. Problem
The publish validation gate (`src/dynasty_genius/features/feature_validation.py`) has two semantics that fail-CLOSED on LEGITIMATE data (this is what blocked the T2 catch-up run):
- **Range gate** (lines 170-177): `_BOUNDED_UNIT_COLUMNS` must lie in `[0,1]`. But `air_yards_share` legitimately goes slightly NEGATIVE (committed seed: 344 values, min −0.041, max 0.476) → false fail.
- **Null gate** (lines 180-188): per-column max-null-rate on the WHOLE candidate. `snap_share` is 6.9% null OVERALL, but that is HISTORICAL TRAINING rows (2022 alone 23.9%); the INFERENCE rows actually published/scored are 0.2% null. The caller sets `snap_share: 0.0` (`feature_publish.py:34`) → 6.9% whole-candidate fails-closed on data that is clean where it matters.

## 2. Goal
Make the gate **fail-SAFE, not fail-on-legitimate-data**: legitimate values pass, but garbage/degradation on the rows we actually publish STILL fails-closed. No silent false-publish. `decision_supported` stays False.

## 3. Design (3-way converged)
**T4.1 — air_yards_share plausibility bound.**
- REMOVE `air_yards_share` from `_BOUNDED_UNIT_COLUMNS` (the strict `[0,1]` set; snap_share/snap_share_t_minus_1/route_participation/target_share_nfl STAY — verified all in [0,1]).
- ADD a distinct check for `air_yards_share`: **finite** AND within a **football-plausibility bound `[-0.5, 2.0]`** (passes the legit small negatives; a non-finite value or a 10.0 garbage value STILL fails-closed).

**T4.2 — snap_share inference-scoped null gate (the crux).**
- The BLOCKER threshold applies to the **INFERENCE rows only** (`feature_season == inference_season`), at a TIGHT floor **0.01** (current inference ≈0.002 passes; >1% inference-null fails-closed). This protects what we publish/score.
- The historical / all-row snap_share null rate is **DISCLOSURE-ONLY** (NOT a blocker). Gemini's rationale: a global floor would let the current week silently degrade while the historical average absorbs it — a silent-failure hole.
- The gate must receive the `inference_season` (passed in / derived) to scope the inference subset.
- **[Codex C1] API stability:** keep the public `max_null_rate_by_column: dict[str, float]` signature STABLE — special-case `snap_share`'s inference-scoping INSIDE `validate_feature_candidate` using the configured value (0.01); `games_t`/`ppg_t` etc. remain whole-candidate null gates at 0.0. No broad nested-threshold-dict churn unless a RED row proves it necessary.

**T4.3 — disclosure contract.**
- The `ValidationResult` + the publish report (`feature_refresh_latest_report.json`) + the ready marker (`engine_b_features_runtime.ready.json`) record explicit, unambiguous fields:
  - `null_rates.snap_share.inference`, `.all_rows`, `.non_inference` (record all three — Codex, to avoid semantic confusion)
  - `null_thresholds.snap_share.scope = "inference"`, `.max = 0.01`
- No false 100%-completeness certainty is projected.

## 4. Tasks (cockpit-TDD: Codex RED → Claude GREEN → dual-CLEAR → David commit)
- **T4a** — `feature_validation.py`: isolate air_yards_share (plausibility+finiteness bound); inference-scope the snap_share null blocker; compute the 3 null-rate fields; thread `inference_season`.
- **T4b** — `feature_publish.py`: update `max_null_rate_by_column` wiring (snap_share inference-scoped 0.01); write the null_rates/null_thresholds disclosure into the report + ready marker.

## 5. Acceptance / RED (Codex authors)
- R1: air_yards_share = −0.041 PASSES; a 10.0 value FAILS-closed; **[Codex C2] a non-numeric / non-finite air_yards_share (string, inf, ±inf) must fail EXPLICITLY** — it must NOT be silently coerced to NaN and bypass the semantic range gate.
- R2: snap_share inference-null 0.2% PASSES; an injected 2% inference-null FAILS-closed.
- R3: snap_share 6.9% all-row null does NOT block when inference is clean (disclosure-only).
- R4: report + ready marker carry null_rates.snap_share.{inference,all_rows,non_inference} + the threshold/scope; decision_supported=false.
- R5: a truly out-of-range / garbage value on ANY bounded col still fails-closed (no over-loosening).
- Full suite green; ruff src app clean.

## 6. Open questions
- Q1 inference floor: 0.01 (Codex) vs 0.02 (Gemini) — lean 0.01 (tighter/safer; inference ≈0.002). Confirm.
- Q2 air_yards bound: `[-0.5, 2.0]` — confirm it is justified (actual [−0.04, 0.48]; generous but catches garbage) + finiteness.
- Q3 do `route_participation` (13.6% null) / `snap_share_t_minus_1` (40% null) need any gate? Currently only snap_share is null-gated (feature_publish.py:34); they pass the range gate. Lean: out of T4 scope (not gated; not a publish blocker). Confirm.
- Q4 does the SAME gate run on the committed-seed build path vs the runtime-publish path? (T4 targets the publish gate; confirm no committed-seed regression.)
