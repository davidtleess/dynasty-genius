# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Pydantic hygiene PR open (#13). Awaiting CI + merge.

## Current Sprint Objective

Stabilize `main` CI before resuming Engine A v2 Phase 2.

- PR #11 (Data Foundation + Identity): MERGED → main `423979e`.
- PR #12 (Rookie Board v1): MERGED → main `7f6f590`.
- PR C (Governance Reconciliation): deferred, human-reviewed only.
- Engine A v2 PP remediation: committed `4afb1c7` on `engine-a/v2-enrichment-pipeline`.

## Latest Activity

- Claude Code (2026-05-11, Session 4): `hygiene/pydantic-compat` — added `model_dump` shim to `DynastyValuation` (pops `mode=`), `ProspectRequest` (defensive), guarded `computed_field` import in `Player`. 84 pass, 0 fail. PR #13 open.
- Claude Code (2026-05-11, Session 3): Fixed PR #11 CI failure (`PlayerValueObject.model_dump` recursion on Pydantic v2). Pushed `fbedfca`. CI passed. PR #11 and PR #12 subsequently merged.
- Claude Code (2026-05-11, Session 2): PP remediation complete — removed imputation (258 fabricated rows), fixed `year_stats` typo, renamed `yprr` → `yptt` internally, added name normalization. Gate rewritten as clean-artifact promotion tripwire. Coverage: target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. 40 targeted tests pass.

## Open Blockers

1. **PR #13 awaiting CI + merge** — `hygiene/pydantic-compat` → `main`. 84 pass locally. `cfbd` pins `pydantic<2` (root cause) — not solved here.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not run PP-inclusive backtest or promote PP without explicit instruction.
3. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work

1. Review and merge PR #13 (`hygiene/pydantic-compat`). CI gate must pass.
2. After PR #13 lands on main: replan Engine A v2 Phase 2 around context/risk layers.

## Branch / Worktree Notes

- `main`: current at `7f6f590` — 84 pass, 0 fail after hygiene fixes (PR #13 pending merge).
- `hygiene/pydantic-compat`: `1f477d6` — Pydantic compat fixes, PR #13 open.
- `engine-a/v2-enrichment-pipeline`: PP remediation committed, not merged to main yet.
- `cleanup/pr-a-data-foundation`: merged to main.
- `cleanup/pr-b-rookie-board`: merged to main.
- `engine-a/historical-enrichment` (PR #10): closed without merge.
- `codex/governance-seal`: superseded.
- Main worktree: `/Users/davidleess/dynasty-genius` (up to date at `7f6f590`).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (on `engine-a/v2-enrichment-pipeline`).
- PR A worktree: `/private/tmp/dg-pr-a` (cleanup/pr-a-data-foundation, merged).
