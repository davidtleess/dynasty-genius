---
title: Step 0.5 — Unified Composite Validation Gate (Engine B v1) — Design Spec
status: DESIGN SPEC v2 — DRAFT, in cockpit review. v1 brainstorm rulings David-ruled + team-CLEARED; recency-aware threshold policy = three-way consensus. v2 integrates the cockpit adversarial round: Gemini governance CLEAR + §10 picks; Codex 5 technical findings (F1 overall_grade public-deprecated not audit-internal; F2 null-coverage denominator defined; F3 QB-PROVISIONAL rationale = sample-adequacy not R²; F4 cold-start fail-loud uniqueness validation; F5 falsification-matrix rows). Re-routing v2 for CLEAR before writing-plans → TDD. NOT approved; NO implementation started.
changelog:
  - v1 (2026-06-12): initial draft from David brainstorm + recency-aware consensus.
  - v2 (2026-06-12): Codex round-1 findings F1–F5 integrated (§5/§7, §3.1, §3.5, §3.3/§6, §11); §10.1 sample-adequacy specified as per-fold Spearman-CI-width with cold-start tolerance (non-cold-start + most-recent fold must clear); Gemini governance CLEAR recorded.
date: 2026-06-12
author: Claude Code (impl), via cockpit brainstorm with David, Codex, Gemini
governance_hold: decision_supported=False throughout. No Engine A/B model .pkl / manifest / feature / training change. Market/FantasyCalc data overlay-only, never a feature/training input. The T9/T11 grade-quarantine + qualifier shipped with the Model Trust Console is preserved and extended, never weakened. Frontend changes (if any) are contract-typing only.
scope_guard: This extends the EXISTING Phase 10/11 + Phase 12 Engine B walk-forward harness (src/dynasty_genius/eval/: backtest_harness.py, backtest_metrics.py, backtest_artifact.py, model_card.py; app/api/routes/trust_surface.py). It is NOT the rookie-forecast Engine A pipeline (app/data/pipeline/train_models.py); the original agent-execution-plan.md Step 0.5 paths (app/data/pipeline/validation/composite.py) were never created and are explicitly superseded by this spec (see §1).
supersedes: docs/agent-execution-plan.md "Step 0.5 — Composite gate measurement script" (stale paths; rookie-pipeline framing).
related:
  - docs/superpowers/specs/2026-05-30-harness-trust-completion-design.md (§8.1 R²=disclose-only "until the Step 0.5 composite gate" — this is that gate)
  - docs/validation-gates.md (prior threshold values; RB low_sample_holdout item)
  - docs/decision-output-contracts.md (model-grade gating contract)
---

# Step 0.5 — Unified Composite Validation Gate (Engine B v1)

> "v1" means the **first build increment** of this feature (Engine B wiring), not a doc revision. Doc version is in the frontmatter `status`.

## 0. Why this exists

Dynasty Genius has two distinct model-grading systems, and "Step 0.5" has been ambiguously referenced against both:

1. **Engine A — rookie forecast** (`app/data/pipeline/train_models.py`): grades **A/B/C/D**, floored at C by `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5 = True`. The original Step 0.5 spec targeted this, but its file paths were **never created**.
2. **Engine B — active-player walk-forward harness** (`src/dynasty_genius/eval/`): grades **ACTIVE_B / ACTIVE_B_VALIDATED / EXPERIMENTAL** via `promotion_gate.overall_grade`. **This is what the shipped Model Trust Console reads.** It already has G1/G2/G3 gates and computes R²/Spearman/Kendall/RMSE-stability/NDCG/bootstrap-CIs.

The harness-trust spec (`2026-05-30-harness-trust-completion-design.md` §8.1) deferred **R²-as-gate** to "the Step 0.5 composite gate." Today R² is *disclosed* but does not gate; `overall_grade` is driven by a G1/G2/G3 subset with no documented composite policy; and the grade is quarantined in the Trust Console precisely because no rigorous composite stands behind it.

**This spec builds that composite gate for Engine B**, so the model status is driven by an explicit, documented, conjunctive validity policy — making the status *earnable* and the rigor real, while preserving the anti-overclaim quarantine.

## 1. Scope (David-ruled, team-CLEARED)

**(U) Unified, decomposed — Engine B first.** "Unified" = a **shared definition layer** (governance, status taxonomy, output contract, threshold *policy*) with **engine-specific measurement adapters** (Engine A LOOCV/low-sample vs Engine B walk-forward have different validation shapes — uniform thresholds are *not* blindly forced onto incompatible regimes).

Build order (each its own increment / spec-plan):
1. **This spec** = the shared definition + the **Engine B adapter wiring** (highest leverage; metrics already compute; it is the §8.1 "R² disclose→gate" item; backs the shipped Trust Console).
2. **Engine A adapter wiring = DEFERRED** to a later increment (off-season; single-fold/low-sample rookie models; low current decision value). This spec defines the shared taxonomy Engine A will later adopt; it does **not** flip `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5`.

**Hard constraint (governance collision):** the unified status MUST NOT re-introduce decision-grade tiering onto David-facing surfaces. It is rendered behind the T9/T11 quarantine + `MODEL_GRADE_QUALIFIER`, never as a verdict/badge/action. This is the binding guard against the constitution's banned output patterns (north-star "Banned David-Facing Output Patterns": `Elite/Starter/Depth/Bust`, trade verdicts).

### Current-state ground truth (verified on `origin/main`, 2026-06-12)

Touch surface:

| File | Role in this spec |
|---|---|
| `src/dynasty_genius/eval/backtest_artifact.py` | `GateResult` today carries only `g1/g2/g3/g4_*_pass` + `overall_grade` + `gate_version`. **Add first-class validity-gate fields + `model_status` + `status_version`** (§5). |
| `src/dynasty_genius/eval/backtest_harness.py` | `evaluate_promotion_gates` computes the gate. **Add the conjunctive validity composite + recency-aware rule** (§3); G3 demoted from gating to disclosed (§3). |
| `src/dynasty_genius/eval/backtest_metrics.py` | R²/Spearman/Kendall/RMSE-stability/NDCG/BCa-CI already compute. **Add a null-coverage producer** (§3, currently absent). |
| `src/dynasty_genius/eval/model_card.py` | `overall_grade` lives here. **Add `model_status`** (§5). |
| `app/api/routes/trust_surface.py` | hoists `overall_grade`. **Surface `model_status`** as the primary status (quarantined); keep `overall_grade` public-but-deprecated + quarantined (§5/§7, F1). |

Real current Engine B per-fold metrics (`app/data/backtest/trust_surface/latest/`), which ground every threshold below:

| Pos | folds (test_year) | n_test | R²ₒₒₛ per fold | Spearman per fold | Spearman CI width (worst fold) | G1 | G2 | G3 |
|-----|-------------------|--------|----------------|-------------------|-------------------------------|----|----|----|
| WR | 2020–2023 | 147–160 | .602/.680/.693/.666 | .763/.785/.816/.794 | ~0.14 | ✓ | ✓ | **pass** |
| RB | 2020–2023 | 90–98 | .441/.524/.495/.558 | .718/.807/.743/.808 | ~0.25 | ✓ | ✓ | fail |
| TE | 2020–2023 | 206/146/90/81 | **.244**/.457/.472/.558 | **.436**/.792/.714/.706 | ~0.35 (fold-1) | ✓ | ✓ | fail |
| QB | 2020–2023 | **43–49** | .141/.298/.287/**.286** | .678/.721/.693/.755 | **~0.40** | ✓ | ✓ | fail |

Key facts: (a) **all four already pass G1 (rank) + G2 (stability)**; only WR passes G3. (b) Every position's **fold-1 (test 2020) is the walk-forward cold-start** — trained on only 2018–2019. (c) **TE's weakness is cold-start-only** (fold-1) and **recovers** 2021–2023. (d) **QB's R² is persistently weak** (incl. most-recent fold 2023 = .286) **and** QB has the thinnest sample (n=43–49) with the **widest rank-correlation CIs** (~0.40 vs WR ~0.14).

## 2. The four brainstorm rulings (David-ruled, team-CLEARED)

1. **Composition = CONJUNCTIVE (all-must-pass).** Each *gating* metric has a hard threshold; status = the highest tier where ALL gating metrics clear. Non-gating metrics are *disclosed*, never averaged in. (Rejected: weighted-score — can mask a critical failure / false precision.)
2. **Grade scope = VALIDITY-ONLY.** The status claims *internal validity* (trustworthy rankings), gated on R²/Spearman/RMSE-stability/null-coverage/leakage. **Market-superiority (G3 / NDCG-vs-FantasyCalc) is DISCLOSED beside the status but does NOT gate it.** Rationale (Gemini, governance-CLEAR): gating validity on beating the market would implicitly treat the market as ground truth, violating "market is price discovery, not truth"; a model that mirrors consensus without beating it is still a valid model.
3. **Vocabulary = 3-tier STATUS, engine-neutral:** `VALIDATED` / `PROVISIONAL` / `EXPERIMENTAL`. Status-framed (not quality-letter), low overclaim risk, rendered quarantined.
4. **Thresholds = recency-aware (§3), uniform across positions for v1.** (Per-position thresholds deferred; positional noise is disclosed, not given a softer bar.)

## 3. The validity gate — definition

### 3.1 Gating metrics (conjunctive)
A position is graded on these **validity** gates only:
- **Spearman ρ** (rank correlation) — per fold.
- **R²ₒₒₛ** — per fold, treated as a **floor with magnitude disclosed** (see §10 resolved threshold).
- **RMSE-stability** across folds (existing G2) — ≤ 30% CV.
- **Null-coverage** — ≥ 90% per fold (NEW producer to build; currently absent in the harness). **Definition (F2, Codex):** per fold, denominator = the fold's **eligible evaluation universe** = player-season rows passing identity validity **before** model-feature-null drops; numerator = rows actually **scored/evaluable** (survived feature-null drops). `null_coverage = scored / eligible`. Exclusions are **reported by reason** (identity-invalid, feature-null, injury-excluded already tracked as `n_excluded_injury`). Aggregate coverage = min across folds for the gate (fail-closed). This makes the gate falsifiable; the denominator is fold-local, never the global PVO/active universe.
- **Leakage-clean** — binary, always required (market features in training = defect).

### 3.2 Disclosed-only metrics (never gate)
- **G3 market-superiority** (NDCG model vs FantasyCalc at primary-k) — shown beside status as a separate signal (`market_higher`/`model_higher`/`inside_band`), per Ruling 2.
- Kendall τ-b, NDCG@k, precision@k, BCa-CI widths, per-fold caveats.

### 3.3 The recency-aware rule (three-way consensus)
**`VALIDATED`** requires ALL of:
1. **Every fold passes** (Spearman ≥ threshold AND R² > floor), **except** the single **cold-start fold** (min `test_year`, thinnest train) may be excused **if it is the only failing fold**. No other fold may be excused — a failing middle or recent fold is never tolerated. AND
2. **the most-recent fold passes** — "most recent" = **max `test_year`** (mechanical, not `fold_index`), AND
3. **sample adequate** (see §10 resolved threshold — per-fold Spearman CI-width ≤ 0.30, cold-start-tolerant), AND
4. **null-coverage clears** AND **leakage clean**.

> **Relationship to "≥3/4":** on the current 4-fold layout this is *at most one* tolerated failure and it **must be the cold-start fold** — strictly *stronger* than a generic ≥3/4 rule, which would wrongly tolerate a weak *middle* fold. "≥3/4" was the discussion shorthand; this cold-start-specific form is the binding rule (guardrail §6.2). On a 4-fold layout the practical effect: all four pass → VALIDATED; only the oldest/cold-start fails → VALIDATED; any other single fold (or 2+) fails → PROVISIONAL/EXPERIMENTAL.

**Cold-start fail-loud derivation (F4, Codex).** The cold-start fold is identified as the fold that is **uniquely both** the minimum `test_year` **and** the minimum train-window length. The implementation MUST verify this uniqueness/consistency; if the min-`test_year` fold is not also uniquely the thinnest-train fold (e.g. after a future fold-layout change), it **fails closed** — no cold-start excuse is granted (the would-be-excused fold is treated as a normal failing fold → PROVISIONAL/EXPERIMENTAL), and the condition is logged. This prevents the narrow cold-start exception from silently degrading into a generic "tolerate any old fold" rule.

**`PROVISIONAL`**: clears safety floors (leakage + null-coverage) and is not EXPERIMENTAL, but fails a VALIDATED condition for a *non-safety* reason — e.g. sample inadequate, or a weak fold that is not the cold-start fold, or the most-recent fold fails on rank/R².

**`EXPERIMENTAL`** (hard floor): leakage fails OR null-coverage fails OR insufficient evaluable data — **regardless** of rank/R²/recency.

### 3.4 Why this rule (rationale of record)
It dominates both the pure-3/4 and the per-fold-all-must-pass postures on honesty: all-must-pass over-penalizes the structurally-disadvantaged cold-start fold; pure-3/4 could tolerate a weak *recent* fold (a real risk to "win now" decisions). Recency-aware does neither — it protects the fold most relevant to David's current decisions while forgiving documented learning-curve noise. The cold-start asymmetry is evidence-grounded (§1): TE recovers, QB does not.

### 3.5 Outcome on current artifacts
With the resolved §10 thresholds (Spearman ≥ 0.55, R² > 0 floor, per-fold Spearman-CI-width ≤ 0.30 with cold-start tolerance, null-coverage ≥ 0.90): **WR / RB / TE → VALIDATED**, **QB → PROVISIONAL**.
- **TE → VALIDATED:** its only sub-threshold fold (fold-1: Spearman 0.436, CI-width 0.344) is the cold-start fold → excused; all later folds clear.
- **QB → PROVISIONAL** is gated **solely by sample-adequacy** (its middle fold-3 Spearman-CI-width 0.413 > 0.30 — a non-cold-start fold, not excusable). QB's low R² (0.286 most-recent) is **NOT** a gating reason — it clears the R² > 0 floor; it is **disclosed supporting context only** (F3, Codex: do not encode a non-gating rationale as a gate).
- Market-superiority disclosed beside: WR established; QB/RB/TE not-established.

This is the honest outcome — the gate is not designed to fail positions for sport, nor to flatter them; rigor lives in the decomposition + the disclosed market result + the quarantine.

## 4. Status vocabulary + quarantine
- `model_status ∈ {VALIDATED, PROVISIONAL, EXPERIMENTAL}` is the canonical engine-neutral status.
- Rendered behind the shipped `MODEL_GRADE_QUALIFIER` ("internal model grade — not a market-edge or decision-support claim") and the T9/T11 neutralized styling. **Never** a colored badge, verdict, tier, or action.
- `decision_supported=False` remains recursive + non-dismissible across the surface.

## 5. Schema & migration (Codex round-1 fixes — accepted)
1. **New first-class validity-gate fields** on `GateResult` (R², Spearman, RMSE-stability, null-coverage, leakage as explicit pass/measured fields) — today's `GateResult` is only G1–G4 + `overall_grade`.
2. **Add a new `model_status` field**; **keep `overall_grade` PUBLIC-BUT-DEPRECATED + quarantined** (do NOT overload it, do NOT remove it in v1). **(F1, Codex):** today `TrustSurfaceResponse` extends `BacktestResult` and returns `model_dump()`, so nested `promotion_gate.overall_grade` is structurally exposed and the top-level field is hoisted — "audit-internal" is therefore NOT achievable in v1 without a response-shape change. v1 choice: `overall_grade` **remains in the response, marked deprecated**, still rendered under the existing T9/T11 quarantine; `model_status` becomes the new primary status binding. A curated public response that *excludes* `overall_grade` is a **deferred** option (§14), requiring an OpenAPI/client migration. This keeps v1 additive and non-breaking to existing Pydantic + generated TS/Zod literals (`ACTIVE_B`/`ACTIVE_B_VALIDATED`/`EXPERIMENTAL`).
3. **Versioning + non-retroactivity:** bump `gate_version` and add `status_version`. Removing G3 from gating is a **semantic migration** — old artifacts retain their old `gate_version` semantics and are NOT silently reinterpreted. Status is comparable only within a `status_version`.
4. **PROVISIONAL computed from current sample adequacy** (§10), NOT hardcoded by position (the "TE/QB n<30" assumption is stale, from the 2026-04-30 rookie table).
5. **Quarantine contract tests** asserting the T9/T11 qualifier is preserved and `model_status` never renders as a David-facing badge/tier/verdict/action.

## 6. Guardrails (Codex — accepted, binding)
1. "Most recent" = **max `test_year`** (mechanical).
2. Cold-start tolerance = oldest/thinnest-train fold **only**, never an arbitrary weak fold.
3. Hard floors: leakage OR null-coverage failure → EXPERIMENTAL regardless; insufficient sample → PROVISIONAL (not VALIDATED).
4. G3 disclosed beside status, never gating.
5. Status output **records which fold(s) failed and whether the failure was cold-start-tolerated** — auditable, not a vibes exception.
6. **Cold-start fail-loud (F4):** the cold-start fold must be *uniquely* min-`test_year` AND min-train-length; otherwise no cold-start excuse is granted (fail closed → PROVISIONAL/EXPERIMENTAL) and the inconsistency is logged. Same per-fold cold-start tolerance applies to the §10.1 CI-width adequacy gate (one mechanism, all gates).

## 7. Output contract changes
- `BacktestResult.promotion_gate` gains `model_status`, `status_version`, the validity-gate fields, and a `status_explanation` block (which folds failed / cold-start-tolerated flag).
- `trust_surface.py` hoists `model_status` (quarantined) as the primary status; `overall_grade` retained **public-but-deprecated** + quarantined (F1; not removed in v1). A curated response excluding `overall_grade` is deferred (§14).
- OpenAPI + generated TS/Zod client regenerated additively; drift guard re-run. No banned-language exposure (FE banned-language linter must pass on any new literals).

## 8. Engine A (deferred) + the shared definition
Engine A keeps `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5 = True` (unchanged). A later increment will give Engine A a measurement adapter that emits the **same** `model_status` taxonomy under the **same** policy, with thresholds re-calibrated to its LOOCV/low-sample regime. This spec's taxonomy + output contract are authored to be engine-neutral so Engine A adopts them without redefinition.

## 9. RB `low_sample_holdout` reconciliation
The inherited `validation-gates.md` RB `low_sample_holdout` caveat is reconciled under the unified sample-adequacy criterion (§10): "low sample" becomes a single, uniformly-computed adequacy test (CI-width / n-based), not a position-specific hardcoded caveat. RB's current Engine B sample (n=90–98) is adequate; the legacy caveat does not apply to Engine B and is documented as superseded for this engine.

## 10. Thresholds — RESOLVED (three-way cockpit consensus 2026-06-12)
All four resolved through the cockpit (Codex + Gemini + Claude); pending David's final sign-off.
1. **Sample-adequacy criterion (decides QB's label) — LOCKED:** **per-fold Spearman 95% BCa CI-width ≤ 0.30, with the SAME cold-start tolerance as §3.3** — i.e. the *only* fold allowed to exceed 0.30 is the mechanically-verified cold-start fold; any **middle or most-recent** fold with CI-width > 0.30 → PROVISIONAL. Grounds adequacy in measured rank-uncertainty already in the artifact (not a raw-`n` cutoff; the rejected n≥50 was outcome-targeting). Per-fold preferred over mean (Codex): mean can wash out a wide middle/recent fold; per-fold is auditable + falsifiable. On current data → TE adequate (only cold-start fold-1 = 0.344 exceeds, excused), QB inadequate (middle fold-3 = 0.413 exceeds) → QB PROVISIONAL.
2. **R²-floor — LOCKED:** `> 0` (model beats a naive mean), magnitude disclosed. NOT ≥0.30 — a magnitude gate would contradict the rank-first, recency-aware policy (Codex F3/§10).
3. **Spearman threshold — LOCKED:** ≥ 0.55 per fold, with cold-start tolerance (§3.3 / `validation-gates.md` prior).
4. **Null-coverage threshold — LOCKED:** ≥ 0.90 per fold, on the §3.1 (F2) denominator definition (eligible evaluation universe). Gate uses min-across-folds (fail-closed).

## 11. Testing strategy (falsification-matrix seed)
Contract tests (RED-first, per cockpit TDD) covering at minimum:
- Conjunctive logic: any single gating metric below threshold drops the tier (per-metric probes).
- Recency-aware: a weak **most-recent** fold → PROVISIONAL even with 3/4 passing; a weak **cold-start** fold (min test_year) → tolerated → VALIDATED.
- Cold-start tolerance narrowness: a weak **middle** fold (not oldest) is NOT tolerated.
- Hard floors: leakage=fail → EXPERIMENTAL regardless of strong rank/R²; null-coverage=fail → EXPERIMENTAL.
- Sample-adequacy: thin/wide-CI position → PROVISIONAL not VALIDATED.
- Schema/migration: `model_status` added without breaking `overall_grade` literals; `status_version` present; old-artifact non-retroactivity.
- Quarantine: `model_status` never renders as badge/tier/verdict/action; qualifier present; `decision_supported=False` recursive.
- Falsification-matrix rows (per operating-loop): valid-nominal, boundary (exactly-at-threshold), missing fold, null R²/Spearman, NaN/inf metric, single-fold (insufficient data), all-folds-fail.
- Falsification-matrix rows added (F5, Codex): **wrong-type** metric (string where float expected), **malformed fold shape** (missing `test_year`/`train_years`), **duplicate/conflicting** `fold_index` or `test_year`, **empty folds collection**, **cross-component-shape mismatch** (null-coverage denominator rows not matching the fold's evaluation universe), **synthetic/override** artifact (injected status must not bypass the gate). Each row gets a probe/test OR an explicit out-of-scope rationale with owner + contract boundary.

## 12. Honest-outcome framing
This gate may grade models **out** — QB lands PROVISIONAL; if thresholds tighten, TE could too. That is success, not failure. The product doctrine is "be right, not fast / avoid false confidence." A gate that correctly catches a sample-limited or unstable model is working as designed. v1 sets the precedent **conservatively** (PROVISIONAL is cheap and promotable as more folds/evidence accrue; walking back a VALIDATED label is worse).

## 13. Constitution / north-star alignment
- Composite validation gates ("not vibes and not a single metric") — north-star Validation Gates. ✓
- Market overlay never feeds/ gates the predictive grade — market is price discovery, not truth. ✓
- Banned David-facing patterns avoided via the status taxonomy + quarantine. ✓
- `decision_supported=False`; no Engine A/B feature/training change; market overlay-only. ✓
- Uncertainty/honesty required — CI-grounded adequacy, disclosed magnitude, auditable status explanation. ✓

## 14. Non-goals (v1)
- Engine A adapter wiring (deferred).
- Flipping `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5`.
- Per-position thresholds (uniform v1).
- Any new David-facing surface beyond the Trust Console status binding.
- R²-as-gate for Engine A; G4 producer (still W2b-deferred); any market-into-training change.

## 15. Build sequence (for writing-plans, AFTER spec CLEAR)
T1 schema (validity-gate fields + `model_status` + `status_version` + `status_explanation`, additive, non-breaking) → T2 null-coverage producer → T3 conjunctive validity composite + recency-aware rule in `evaluate_promotion_gates` (G3 demoted to disclosed) → T4 status_explanation + cold-start audit record → T5 trust_surface surfacing (quarantined) + OpenAPI/client regen + banned-language gate → T6 quarantine + falsification contract tests → T7 republish artifacts + verification. Each: Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit → zero-divergence audit.

## 16. Open questions for cockpit + David
- §10.1 sample-adequacy + §10.2 R²-floor + §10.3 Spearman + §10.4 null-coverage — **RESOLVED** (three-way consensus §10), pending David sign-off.
- Codex F1–F5 — **RESOLVED** in v2 (§3.1, §3.3/§6.6, §3.5, §5.2/§7, §11).
Remaining for David / final CLEAR:
1. Is `model_status` the right field name, or reuse/rename for the eventual Engine-A unification?
2. Migration: additive `model_status` (recommended) vs atomic literal migration of `overall_grade`?
3. Any banned-language exposure in `VALIDATED/PROVISIONAL/EXPERIMENTAL` rendering not covered by the FE linter? (Gemini governance-CLEAR'd the taxonomy; confirm on the rendered literals at T5 implementation.)
4. David sign-off on the §10 thresholds + the WR/RB/TE→VALIDATED, QB→PROVISIONAL outcome.
