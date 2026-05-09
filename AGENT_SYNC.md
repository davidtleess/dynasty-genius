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
- Identity resolver supports context escalation: name-only (95%), team, and team+jersey verification for conflicts.
- Codex added local-only roster risk math: age-cliff risk, biological debt, and liquidity risk in `app/services/roster_auditor.py`.
- Claude delivered `PlayerValueObject` + `RosterAuditSignals` models, `pvo_assembler.py`, live Sleeper roster ingestion (24 players), and dark-theme Roster Audit HTML dashboard. Dashboard loads from external JS artifact; position groups QB→RB→WR→TE; full `RosterAuditSignals` contract in expandable rows.
- Gemini added opponent fragility lens (`scripts/generate_league_audit.py`, `resources/league_fragility_report.json`) and counter-argument engine (`src/dynasty_genius/decision_logic/counter_arguments.py`), wired into PVO. Governance violation (verdict language) was caught and corrected.
- Claude connected Engine A trained models to PVO assembler (`src/dynasty_genius/scoring/engine_a.py`). Prospects with pick+round+age now receive a 0-100 `dynasty_value_score`, `model_grade=PROSPECT_C` (or PROSPECT_D for QB), and Engine A caveats. Veterans remain PRE_MODEL.
- `fuzzy_match.py` dead code deleted; `verify_conflicts.py` migrated to `identity.py`. 53 tests pass.

## Open Blockers

- Formal Gemini CLI bootstrap lock is not yet implemented; current enforcement is markdown bootstrap, CI validation, and local Git pre-commit.
- Databricks lineage tables and SCD Type 2 identity DDL are pending Genie architecture work.
- Opponent fragility lens uses mock league rosters — must be replaced with live Sleeper snapshot before surfacing in dashboard.

## Next Recommended Work

1. Gemini PM: review `LeagueContext` pick ownership and scoring propagation before Engine B ignition.
2. Genie: define `silver.player_identity` SCD Type 2 DDL — dry-run only, no cluster spin-up.
3. Wire Engine A scores into 2026 draft prospect cards: rebuild mock prospect identity fixture with pick + round + age fields, run `scripts/build_live_roster.py` with `is_prospect=True` for devy/rookie entries.
4. Replace mock league rosters with live Sleeper snapshot to activate the opponent fragility lens.

## Branch / Worktree Notes

Current branch: `codex/governance-seal`, reconciled with origin.

The shared Git hook at `/Users/davidleess/dynasty-genius/.git/hooks/pre-commit` points to `scripts/git-hooks/pre-commit`.

Databricks hard stop: no remote Databricks compute, warehouse, job, bundle deploy, or lineage sync should run if it risks exceeding $10 per 24 hours without David's manual override. Default to local tests and static review.

This sync file describes the current local repo state. Agents should also check `git status` before editing.
