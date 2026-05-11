# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-10

## Active Phase

Engine A v2 enrichment pipeline — Phase 1 complete. Task 3 gate resolved Path B; PlayerProfiler remains context_signal.

## Current Sprint Objective

Engine A v2: validate which enrichment sources deserve model-input status before expanding rookie scoring.

- Task 1 (Source Registry): complete — 12/12 tests passed.
- Task 2 (CFBD enrichment): hygiene patch committed (e14dfd7). CFBD backtest run (Task 4 below).
- Task 3 (PlayerProfiler probe): resolved Path B — 0% non-null coverage; PP fields are deferred, not imputed.
- Task 4 (CFBD-only backtest): complete — promotion NOT warranted (CFBD features did not improve Model A on held-out set).
- Tasks 5–8: deferred to Phase 2 (post Phase 1 gate resolution).

## Latest Activity

- Claude Code (2026-05-10, Session 3): Phase 1 execution complete.
  - Source registry (16 sources, 12 governance tests) committed.
  - PlayerProfiler probe script + decision gate tests committed (gate deferred to David).
  - CFBD-only backtest run: Model B (+ dominator_rating + receiving_yards_share) did NOT improve on Model A (baseline). Promotion: NO.
  - Held-out n=242. RMSE delta: -0.6% (worse). R² delta: -0.023 (worse). Spearman delta: -0.024 (worse).
- Codex (2026-05-10): ran the PlayerProfiler probe and formal gate test.
  - Probe: 874 players, found=0, parse_error=874, target_share=0%, breakout_age=0%, speed_score=0%.
  - Gate test failed by design, selecting Path B.
  - Engine A contract now removes PP-only fields (`target_share`, `breakout_age`, `speed_score`) and defers `yprr` until a verified source exists.

## Open Blockers

- Phase 2 (Tasks 5–8) should not promote new model inputs until the failed PP gate and negative CFBD backtest are reflected in downstream plans.
- Post-draft PR cleanup (PRs A/B/C) approved but not yet executed.
- PR #10 (engine-a/historical-enrichment): open, marked non-mergeable. Deferred.

## Next Recommended Work

1. Commit the Path B contract/ledger update after verification.
2. Replan Phase 2 around context/risk layers and validation, not automatic source promotion.
3. Post-draft: execute PR A (Data Foundation) and PR B (Rookie Board) per cleanup plan in ledger.

## Branch / Worktree Notes

Active branch: engine-a/v2-enrichment-pipeline (up to date with origin).
PR #10 (engine-a/historical-enrichment): open, non-mergeable, deferred.
Governance branch codex/governance-seal: superseded by main's sealed governance (6d378d0).
