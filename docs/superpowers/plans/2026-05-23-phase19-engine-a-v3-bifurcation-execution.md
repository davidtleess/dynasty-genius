# Phase 19 Engine A v3 Bifurcation Execution Plan

## Status

Approved by David on 2026-05-23. This plan replaces the unavailable Gemini `brain/implementation_plan.md` and `brain/task.md` handoff files as the repo-native execution contract.

## Governing Spec

- `docs/strategies/2026-05-23-engine-a-bifurcation-design-spec-v0.2.md`
- `docs/governance/00-product-constitution.md`
- `docs/governance/01-north-star-architecture.md`
- `src/dynasty_genius/models/engine_a_contract.py`

## Objective

Build Engine A v3 as a bifurcated rookie forecast:

- **Head A — Absolute Ranking:** predicts best-3-of-first-4-seasons PPR PPG and may use NFL draft capital.
- **Head B — Market Edge:** predicts residual PPG versus expected draft-slot outcome and must not use draft capital or derived draft-capital features.

No production model promotion occurs in this plan unless the validation gates pass and David approves a promotion decision.

## Locked Phase 19 Decisions

1. PFF intake: manual annual CSV exports for v3.
2. TE RAS floor: UI warning plus severe negative modifier below 3.76, no hard zero.
3. Naming: Phase 19.
4. Model class: position-specific GBT vs. Ridge bake-offs.
5. Holdout: 2022-2023 with censoring flags.
6. Combine-decline: pro-day data with `pro_day_only_flag` and standard discount.
7. Head B outlier sensitivity: strict >25% coefficient drift demotes feature to Candidate.

## Workstreams

### W1 — Head B Target Pipeline

Create the target-generation pipeline.

Required outputs:
- `app/data/training/prospects_with_outcomes_v3.csv` with `expected_ppg_at_pick`, `residual_ppg`, censoring flags, and target provenance columns.
- `app/data/training/expected_ppg_curves_v3.json` with per-position curve metadata and source hashes.

Implementation requirements:
- Fit position-specific expected PPG curves from historical draft cohorts.
- Use isotonic regression for WR/RB and hierarchical pooling or shrinkage for TE.
- Preserve existing training data; do not overwrite `prospects_with_outcomes.csv`.
- Do not add market-derived fields.

Validation:
- Unit tests for monotonic expected PPG by pick.
- Tests for TE pooling behavior on sparse cohorts.
- Contract test proving Head B target generation does not include market fields.
- Artifact files must be gitignored unless explicitly approved for tracked validation output.

### W2 — Feature Pipeline Build-Out

Extend college and combine feature production.

Required outputs:
- `prospects_with_outcomes_v3.csv` populated with required Engine A v3 feature columns.
- Missingness/provenance flags for every candidate feature.

Implementation requirements:
- Extend CFBD-derived features: dominator, RYPTPA, school SP+, returning production, deep-yard share, transfer/covid flags.
- Confirm RAS and Combine ingestion paths for required fields.
- Add `HEAD_B_PROHIBITED_COLUMNS` and tests banning `nfl_pick`, `nfl_round`, `pick`, `round`, and derived draft-capital features from Head B.

Validation:
- Feature contract tests for all required Head A and Head B columns.
- Leakage tests for market fields and draft-capital fields in Head B.
- No subjective PFF grades in any model feature contract.

### W3 — Head A v3 Bake-Off

Train and validate absolute-ranking candidates.

Required outputs:
- Per-position Ridge vs. GBT validation artifacts.
- Promotion decision documents for any promoted Head A position.

Validation gates:
- Beat Engine A v2 on at least 2 of 3: RMSE, Spearman, NDCG@10.
- Position-specific promotion only.
- No production pkl update without David approval.

### W4 — Head B v3 Bake-Off

Train and validate market-edge candidates.

Required outputs:
- Per-position residual model validation artifacts.
- `head_b_outlier_sensitivity_report.json`.
- Promotion decision documents for any promoted Head B position.

Validation gates:
- Residual R2 > 0 is required.
- Pass at least 2 of 4 Head B metrics: residual R2, within-tier pairwise accuracy, top-5 Day 3 sleeper precision, residual calibration monotonicity.
- Head B must pass without quarantined PFF-only candidate features before those features can be credited as marginal lift.
- Any feature with >25% coefficient drift under leave-one-outlier-out sensitivity is demoted to Candidate.

### W5 — Service Layer And Rookie Board Integration

Expose bifurcated scoring only after model promotion approval.

Required outputs:
- `EngineAScorer` head routing.
- PVO fields for absolute and market-edge outputs.
- Rookie board columns and caveats.

Validation:
- Existing Engine A v2 behavior remains stable when v3 artifacts are unavailable.
- No David-facing decision-grade language unless validation gates justify it.

### W6 — Era Drift Monitoring

Add monitoring for the new era-sensitive assumptions.

Required outputs:
- Transfer portal and COVID flag distribution report by class.
- TE coefficient stability check.
- Deferred monitor for zone/man split drift if quarantined PFF route-context features are later activated.

## First Execution Step

Start W1 on a clean feature branch after this planning state is committed. Do not begin W2 until W1 target artifacts and tests pass.

## Non-Negotiable Boundaries

- Market data remains overlay-only and never enters Engine A features or targets.
- Head B never receives NFL draft capital or derived draft-capital features as inputs.
- Raw PFF rows and local PFF manifests remain gitignored.
- No production model pkl, latest pointer, PVO decision-supported status, or rookie board confidence language changes without a passing validation artifact and David approval.
