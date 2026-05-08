# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-08

## Active Phase

Phase 2: League Context Foundation and Identity Resolution.

## Current Sprint Objective

Establish the canonical identity and league context:

- `src/dynasty_genius/models/player_identity.py`
- `src/dynasty_genius/models/league_context.py`
- `src/dynasty_genius/identity.py`
- `silver.player_identity` mapping table

## Latest Activity

- Successfully verified the Governance Seal (Phase 1) and active pre-commit hooks.
- Transitioned to Phase 2: Identity & Context Foundation.
- Defined `PlayerIdentity` and `LeagueContext` models for cross-source unification.
- Implemented `dg_id` generation utility and Identity Resolution pipeline stub.
- Mapped market-overlay surface under `resources/` for post-scoring joins.
- Codex pressure-tested identity governance: added suffix/alias normalization, deterministic collision suffixing, market-column vetoes in the identity pipeline, and focused identity governance tests.
- Claude implemented fuzzy name confidence, ID resolver lookups, and mock PlayerProfiler identity fixtures; Codex reviewed and removed `ktc_id` from canonical identity fixtures while preserving the 95% conflict rule.
- Identity resolver now supports context escalation: name-only verification at 95%, team verification for strong near-matches, and team+jersey verification for weaker conflicts such as `Cam Thomas` vs. `Cameron Thomas`.
- Codex added local-only roster risk math for the Roster Audit Dashboard: age-cliff risk, internal-value biological debt, and second-round-pick liquidity risk.

## Open Blockers

- Formal Gemini CLI bootstrap lock is not yet implemented; current enforcement is markdown bootstrap, CI validation, and local Git pre-commit.
- Databricks lineage tables and SCD Type 2 identity DDL are pending Genie architecture work.

## Next Recommended Work

1. Have Genie define `silver.player_identity` SCD Type 2 DDL and Databricks deployment wiring.
2. Have Claude assemble PVO/decision-card JSON using the local roster risk helpers before any UI polish.
3. Have Gemini review `LeagueContext` pick ownership and scoring propagation before Engine B ignition.

## Branch / Worktree Notes

Current branch: `codex/governance-seal`, reconciled with origin.

The shared Git hook at `/Users/davidleess/dynasty-genius/.git/hooks/pre-commit` points to `scripts/git-hooks/pre-commit`.

Databricks hard stop: no remote Databricks compute, warehouse, job, bundle deploy, or lineage sync should run if it risks exceeding $10 per 24 hours without David's manual override. Default to local tests and static review.

This sync file describes the current local repo state. Agents should also check `git status` before editing.
