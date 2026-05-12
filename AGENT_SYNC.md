# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Phase 5 (Engine B) in progress. Task 5.1 (Dataset Assembly) REMEDIATED: `engine_b_features_v2.csv` generated and verified via `tests/test_engine_b_dataset_gate.py`. All 4 blockers from Claude's audit resolved.

Next: Task 5.4 (Training MVP).

## Current Sprint Objective

Phase 5 / Engine B MVP. Training dataset assembled (v2), verified for integrity (QB eff, Route metrics, 2024 cutoff). Transitioning to Ridge/LightGBM model training.

- PR #22 (Claude): Aging Curves and Engine B Contract. 65 tests pass.
- PR #21: Engine B Decision Record merged.
- PR #18 (`infra/adapter-test-gates`): MERGED. 4 adapter gates (RAS, manual export, FantasyCalc, leakage).
- PR #19 (`stage4/qb-professional-context`): MERGED. EPA/CPOE/DAKOTA context layer, QB identity bridge, roster qb_context_cards.
- PR #20 (`feature/qb-context-annotations`): MERGED. Display-only bust flags (TD/INT <0.7), mobility signal (APY >3,700), P2S/college caveats.
