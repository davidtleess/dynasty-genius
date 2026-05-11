# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Post-draft cleanup complete. Main is current. Immediate next task: Pydantic hygiene PR.

## Current Sprint Objective

Stabilize `main` CI before resuming Engine A v2 Phase 2.

- PR #11 (Data Foundation + Identity): MERGED → main `423979e`.
- PR #12 (Rookie Board v1): MERGED → main `7f6f590`.
- PR C (Governance Reconciliation): deferred, human-reviewed only.
- Engine A v2 PP remediation: committed `4afb1c7` on `engine-a/v2-enrichment-pipeline`.

## Latest Activity

- Claude Code (2026-05-11, Session 3): Fixed PR #11 CI failure (`DynastyValuation`-unrelated `PlayerValueObject.model_dump` recursion on Pydantic v2). Pushed `fbedfca`. CI passed. PR #11 and PR #12 subsequently merged.
- Claude Code (2026-05-11, Session 2): PP remediation complete — removed imputation (258 fabricated rows), fixed `year_stats` typo, renamed `yprr` → `yptt` internally, added name normalization. Gate rewritten as clean-artifact promotion tripwire. Coverage: target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. 40 targeted tests pass.
- Claude Code (2026-05-11, Session 1): Reconciled AGENT_SYNC.md with corrected PP status (stale 0% probe superseded; governance violations documented).

## Open Blockers

1. **Pydantic hygiene PR** — 5 tests failing on `main`: `DynastyValuation.model_dump` in `rookie_evaluator.py:249`. Affects `test_rookie_drivers` (4) and `test_trade_quarantine` (1). Also: `ProspectRequest`, `computed_field` in `player.py` may need fixes. Branch: `hygiene/pydantic-compat` from `main`. `cfbd` package pins `pydantic<2` — investigate but don't solve inside this PR.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not run PP-inclusive backtest or promote PP without explicit instruction.
3. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work

1. `hygiene/pydantic-compat` PR from `main` — fix `DynastyValuation`, `ProspectRequest`, `computed_field`. Target: 5 → 0 failures, 78 → 83 passing. Do not mix in other changes.
2. After hygiene PR lands: replan Engine A v2 Phase 2 around context/risk layers.

## Branch / Worktree Notes

- `main`: current at `7f6f590` — 78 pass, 5 fail (Pydantic), 1 error (FastAPI import).
- `engine-a/v2-enrichment-pipeline`: PP remediation committed, not merged to main yet.
- `cleanup/pr-a-data-foundation`: merged to main.
- `cleanup/pr-b-rookie-board`: merged to main.
- `engine-a/historical-enrichment` (PR #10): closed without merge.
- `codex/governance-seal`: superseded.
- Main worktree: `/Users/davidleess/dynasty-genius` (up to date at `7f6f590`).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (on `engine-a/v2-enrichment-pipeline`).
- PR A worktree: `/private/tmp/dg-pr-a` (cleanup/pr-a-data-foundation, merged).
