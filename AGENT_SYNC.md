# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-12

## Active Phase

Phase 5 (Engine B) COMPLETE. All tasks 5.1–5.6 closed and audited.

Next: Phase 6 — Engine B v2 (feature refinement, TE improvement, position-stratified models).

## Current Sprint Objective

Phase 6 planning. Engine B v1 is in production as an experimental signal layer. No active implementation sprint.

## Merged PRs (complete history)

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`.
- PR #14 (`hygiene/pydantic-v2-upgrade`): MERGED → main `f54ba11`.
- PR #15 (`hygiene/nflreadpy-migration`): MERGED → main `fa995624`.
- PR #17 (`engine-a/v2-enrichment-pipeline`): MERGED → main. QB CFBD adapter, ID map (95.2%), TDD tests, backtest gate (FAIL 0/3).
- PR #18 (`infra/adapter-test-gates`): MERGED. 4 adapter gates (RAS, manual export, FantasyCalc, leakage).
- PR #19 (`stage4/qb-professional-context`): MERGED. EPA/CPOE/DAKOTA context layer, QB identity bridge, qb_context_cards.
- PR #20 (`feature/qb-context-annotations`): MERGED. Display-only bust flags, mobility signal, P2S caveats.
- PR #21 (`docs/phase5-engine-b-plan`): MERGED. Phase 5 planning doc.
- PR #22 (`phase5/engine-b-contracts`): OPEN. Aging curves + Engine B contract (65 tests). Pending merge.

## Open PRs / Branches

- `engine-b/service-integration`: Engine B v1 complete — dataset (v2, 2,877 rows), training (alpha=100, 19 features), service layer, API route, 261 tests. Pending PR and merge.
- `governance/engine-b-decision-record`: Engine B Q1–Q6 decision record. Pending PR and merge.
- `phase5/engine-b-contracts`: PR #22 — aging curves + Engine B contract. Pending merge.

## Engine B v1 Final State

- **Artifact**: `app/data/models/engine_b/runs/20260512T032635Z/engine_b_v1.pkl`
- **Features**: 19 (removed `target_share_nfl`, `air_yards_share` — r=0.95–0.98 collinear with WOPR)
- **Alpha**: 100.0 (stronger regularisation for collinear feature set)
- **Holdout**: 2022–2023 seasons (752 rows, 30% — more conservative than Q5 spec of 20%)
- **Gate**: PASS 3/3 — RMSE 3.346, R² 0.621, Spearman 0.775
- **TE**: `ENGINE_B_EXPERIMENTAL_POSITIONS = {"TE"}` — does not beat baseline, caveat enforced
- **Suite**: 261 passed, 11 skipped, 0 failed

## Open Blockers

1. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds.
2. **PR C** — governance reconciliation is human-reviewed only.
3. **Local Python mismatch** — use `.venv/bin/python3.14` for nflreadpy work.

## Next Recommended Work (Phase 6)

1. **Merge open PRs** — governance/engine-b-decision-record, phase5/engine-b-contracts, engine-b/service-integration (in that order).
2. **Engine B v2 feature fix** — drop `route_participation` (r=0.785 with `snap_share`); re-evaluate TE sub-gate.
3. **Position-stratified models** — separate Ridge per position eliminates cross-position imputation noise for QB-specific metrics (EPA/CPOE/DAKOTA).
4. **Hyperparameter search** — validate alpha=100 via cross-validation rather than single holdout inspection.
5. **Roster Auditor integration** — surface Engine B predictions alongside the existing age-curve audit output.

## QB Strategy (unchanged)

- CFBD Tier 3 via httpx — registered in contract, NOT promoted to model_input (backtest FAIL 0/3)
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only)
- `is_dual_threat = True` if rushing yards > 400/season in any T-2 to T
