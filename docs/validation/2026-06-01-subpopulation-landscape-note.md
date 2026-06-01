# Subpopulation / Axis-of-Edge Study — Landscape Note

**DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.**

- **Date:** 2026-06-01
- **Initiative:** Harness Trust Completion → Task B follow-up to the Step-5b.2 G3 result (`docs/validation/2026-05-31-step5b2-g3-ecr-validation.md`).
- **Spec:** `docs/superpowers/specs/2026-05-31-subpopulation-axis-of-edge-study-design.md` (dual-CLEARED; aggregate-p + id-map-robustness refinements 2026-06-01).
- **Code:** `src/dynasty_genius/eval/subpopulation_landscape.py` + `scripts/run_subpopulation_landscape.py` (commit `072264e`). Artifact: `app/data/backtest/subpopulation/subpopulation_landscape_g3_subpop_consolidated.{json,md}` (local/gitignored).

## What this is

A **model-blind, descriptive** characterization of how Engine B's ranking quality compares to DynastyProcess expert consensus (`fc_rank`, derived from `fc_value`) against realized PPG, across **three pre-registered subpopulations**, for the **whole player universe** (not David's roster). It answers exactly one question — *which model-quality hypotheses, if any, deserve a powered confirmatory follow-up* — and it is **not** a "trust this pocket" signal. It surfaces hypotheses, not actions; no decision-grade output.

## Method (as pre-registered)

- Per `(axis, slice, position, fold)`: Spearman ρ of model vs consensus rank against realized rank, lower-is-better both sides; `rho_diff = rho_model − rho_consensus` (positive ⇒ model aligns better). Spearman gated at n ≥ 30; NDCG@primary-k cross-check gated independently at n ≥ k.
- Aggregate across the 4 annual folds (2020–2023 feature seasons): **median `rho_diff`** (point estimate, no pooling) + `folds_covered`.
- Category by sign + `NEUTRAL_BAND = 0.05`, CI-independent.
- Aggregate p-value: **exact fold-level sign-flip permutation test** (fold as the unit of inference); BH FDR over the aggregate per-(axis,slice,position) tests; `powered_followup_candidate = q ≤ 0.10`, **hypothesis-generating only**.

## Coverage & integrity (id-map: DynastyProcess `db_playerids`)

- **draft_year coverage: 1702 / 1702 (100%)** of the G3 comparison rows; `db_season_snapshot = 2026`.
- Fail-closed id-map diagnostics (auditable, surfaced in provenance):
  - **9 gsis_ids excluded** for genuinely conflicting draft years (ambiguous identity → excluded, never "latest wins"): `00-0022828, 00-0022888, 00-0026515, 00-0027349, 00-0028488, 00-0029435, 00-0030653, 00-0031636, 00-0032050`.
  - **4,484 null-marker (`NA`) gsis_id rows skipped** (unjoinnable keys).
- High-disagreement denominators (|model_rank − consensus_rank| ≥ 12 within position): QB 29, RB 128, TE 272, WR 262.

## Findings (balanced; all directions shown)

Lower `rho_diff` ⇒ consensus aligns better; higher ⇒ model aligns better. `folds_covered` = annual folds with n ≥ 30.

| Axis | Slice | Pos | n | folds | median rho_diff | category | q | powered candidate |
|---|---|---|---|---|---|---|---|---|
| aging-cliff | aging_cliff | RB | 182 | 4 | +0.018 | statistically_indistinguishable | 1.0 | False |
| aging-cliff | aging_cliff | WR | 175 | 4 | −0.034 | statistically_indistinguishable | 1.0 | False |
| aging-cliff | aging_cliff | QB | 35 | 0 | — | insufficient_n | — | False |
| aging-cliff | aging_cliff | TE | 49 | 0 | — | insufficient_n | — | False |
| early-career | eligible | RB | 173 | 4 | −0.083 | consensus_leads_point_estimate | 1.0 | False |
| early-career | eligible | WR | 246 | 4 | −0.028 | statistically_indistinguishable | 1.0 | False |
| early-career | eligible | TE | 236 | 3 | −0.020 | statistically_indistinguishable | 1.0 | False |
| early-career | eligible | QB | 59 | 0 | — | insufficient_n | — | False |
| high-disagreement | model_bullish | WR | 121 | 2 | −0.063 | consensus_leads_point_estimate | 1.0 | False |
| high-disagreement | model_bullish | TE | 135 | 2 | +0.009 | statistically_indistinguishable | 1.0 | False |
| high-disagreement | model_bearish | WR | 141 | 4 | −0.036 | statistically_indistinguishable | 1.0 | False |
| high-disagreement | model_bearish | TE | 137 | 1 | +0.357 | model_leads_point_estimate | 1.0 | False |
| high-disagreement | model_bullish | QB | 12 | 0 | — | insufficient_n | — | False |
| high-disagreement | model_bearish | QB | 17 | 0 | — | insufficient_n | — | False |
| high-disagreement | model_bullish | RB | 56 | 0 | — | insufficient_n | — | False |
| high-disagreement | model_bearish | RB | 72 | 0 | — | insufficient_n | — | False |

## Reading the landscape

- **`statistically_indistinguishable` dominates.** On the well-powered slices (folds_covered ≥ 3), model and rational expert consensus are statistically tied. The only point-estimate leans toward *consensus* are early-career RB (−0.083) and high-disagreement WR-bullish (−0.063); the lone lean toward *model* is high-disagreement TE-bearish (+0.357) — and that is a **single fold** (folds_covered = 1), not a stable pattern.
- **No powered follow-up candidate fired — and none could.** Every `q_value = 1.0`, every `powered_followup_candidate = False`. This is a **structural fold-count power limit**: with ≤ 4 annual folds the exact sign-flip permutation null has a minimum two-sided p of 0.25, so `q ≤ 0.10` is **unreachable by construction**. **This is a power limitation, not evidence of "no signal,"** and it is not the model "having arrived."
- **QB and small-position slices are `insufficient_n`** (no single fold reached n ≥ 30) — descriptive counts only, no claim either way.

## Summary Finding (descriptive)

The subpopulation landscape is **consistent with the whole-population G3 result** (`consensus-competitive, edge unproven`): Engine B tracks rational expert consensus across the aging-cliff, high-disagreement, and early-career cohorts, with no powered pocket where the model demonstrably out-ranks consensus. Nothing here authorizes a "trust this slice" claim.

**Where the analytical superiority hypothesis still lives (unchanged, not advanced by this study):** the model is a *verified rational anchor*; its potential value is in (1) decision-context translation for David's specific Superflex league and (2) divergence against the **emotional trade market** (KTC / FantasyCalc) — the deferred **Task C** point-in-time trade-market baseline, which is the real mispricing test. This study measured against *rational* consensus and, as expected, did not beat it.

## Caveats

- Descriptive / diagnostic only; `decision_supported` absent; no actionable guidelines or value-bin classifications. The word "edge" appears only referentially — this study's title, the no-edge-claim header, the spec filename, and the quoted prior G3 verdict ("edge unproven") — never as a new claim that the model has an edge.
- Powered candidates are structurally unreachable at ≤ 4 folds (disclosed above); a confirmatory study needs more point-in-time archive years.
- NDCG cross-check uses rank-derived relevance (the contract takes realized ranks, not PPG); a PPG-graded NDCG is a deliberate later contract change.
- Market/identity data is read-only, joined after scoring; no Engine A/B feature or training change; frontend HOLD intact.

## Provenance

- Run: `run_subpopulation_landscape.py --run-dir <4 consolidated G3 dirs> --id-map-csv db_playerids.csv`; run_id `g3_subpop_consolidated`.
- G3 source run dirs (per-position): QB `483f87f9`, RB `e639a40c`, WR `fc1e6e1c`, TE `6ba3a451`.
- Folds: 2020–2023 feature seasons (4 annual folds). Code commit `072264e`. Full suite at write: 1686 passed, 11 skipped, 0 failed.
