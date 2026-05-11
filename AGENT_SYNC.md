# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-10

## Active Phase

Engine A v2 enrichment pipeline — Phase 1 (Tasks 1, 3, 4) complete. Task 3 gate (PlayerProfiler probe) awaits David's manual run.

## Current Sprint Objective

Engine A v2: enrich historical training data with college stats (CFBD) and PlayerProfiler metrics to enable dominator_rating, YPRR, and RAS signal for post-2026 draft rookie scoring.

- Task 1 (Source Registry): complete — 12/12 tests passed.
- Task 2 (CFBD enrichment): hygiene patch committed (e14dfd7). CFBD backtest run (Task 4 below).
- Task 3 (PlayerProfiler probe): gate script committed; AWAITING David's manual probe run.
- Task 4 (CFBD-only backtest): complete — promotion NOT warranted (CFBD features did not improve Model A on held-out set).
- Tasks 5–8: deferred to Phase 2 (post Phase 1 gate resolution).

## Latest Activity

- Claude Code (2026-05-10, Session 3): Phase 1 execution complete.
  - Source registry (16 sources, 12 governance tests) committed.
  - PlayerProfiler probe script + decision gate tests committed (gate deferred to David).
  - CFBD-only backtest run: Model B (+ dominator_rating + receiving_yards_share) did NOT improve on Model A (baseline). Promotion: NO.
  - Held-out n=242. RMSE delta: -0.6% (worse). R² delta: -0.023 (worse). Spearman delta: -0.024 (worse).

## Open Blockers

- **David action required**: run `.venv/bin/python scripts/probe_playerprofiler.py` to resolve Task 3 PP gate.
  - Path A (≥80%): promote PP to model_input, implement adapter.
  - Path B (<80%): PP stays context_signal, remove PP fields from ALLOWED_ENRICHMENT_COLUMNS, no imputation.
- Phase 2 (Tasks 5–8) blocked until Task 3 gate resolves.
- Post-draft PR cleanup (PRs A/B/C) approved but not yet executed.
- PR #10 (engine-a/historical-enrichment): open, marked non-mergeable. Deferred.

## Next Recommended Work

1. David runs PP probe, logs Path A/B decision in `docs/agent-ledger/2026-05-10.md`.
2. Based on result: update `source_registry.py` PP role + ALLOWED_ENRICHMENT_COLUMNS.
3. Post-draft: execute PR A (Data Foundation) and PR B (Rookie Board) per cleanup plan in ledger.

## Branch / Worktree Notes

Active branch: engine-a/v2-enrichment-pipeline (up to date with origin).
PR #10 (engine-a/historical-enrichment): open, non-mergeable, deferred.
Governance branch codex/governance-seal: superseded by main's sealed governance (6d378d0).
