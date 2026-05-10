# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-09

## Active Phase

Phase 2: League Context Foundation and Identity Resolution.

## Current Sprint Objective

Finalize the canonical identity and live league context:

- `src/dynasty_genius/models/player_identity.py`
- `src/dynasty_genius/models/league_context.py`
- `silver.player_identity` mapping table
- Verified 2026 Rookie Board for May 11th draft

## Latest Activity

- Successfully verified the Governance Seal (Phase 1) and active pre-commit hooks.
- Transitioned to Phase 2: Identity & Context Foundation.
- Defined `PlayerIdentity` and `LeagueContext` models for cross-source unification.
- **Verified Live League Context:** Fetched real settings for "Redzone Champions League". Confirmed Superflex, PPR (1.0), and 0.0 TE Premium.
- **Reconstructed Real Pick Inventory:** Confirmed David owns multiple 2026 and 2027 1st-round picks via `traded_picks` reconstruction.
- **Aligned 2026 Rookie Draft:** Set context for May 11th slow draft. 2026 rookies are now "Prospects with NFL Draft Capital".
- Implemented `dg_id` generation utility and Identity Resolution pipeline stub.
- Identity resolver supports context escalation: name-only (95%), team, and team+jersey verification for conflicts.
- Codex added local-only roster risk math: age-cliff risk, biological debt, and liquidity risk in `app/services/roster_auditor.py`.
- Claude delivered `PlayerValueObject` + `RosterAuditSignals` models, `pvo_assembler.py`, live Sleeper roster ingestion (24 players), and dark-theme Roster Audit HTML dashboard.
- Gemini added opponent fragility lens (`scripts/generate_league_audit.py`, `resources/league_fragility_report.json`) and counter-argument engine.
- Claude connected Engine A trained models to PVO assembler. Prospects with pick+round+age now receive scores.
- **Strategic Pivot:** Approved "Do it right, not fast" roadmap for QB valuation. QBs will remain at `PROSPECT_D` (Pick/Round/Age only) for the May 11th draft. Phase 3 will involve historical enrichment (874 players) and transition to Quantile Regression for high-fidelity ceiling/floor signals.
- Current local verification: 61 tests pass; governance validation passes; `git diff --check` passes; no Databricks commands run.

## Phase 3 Roadmap (Post-Draft)

- **Historical Enrichment:** Fetch AY/A, Rushing Share, and Breakout Age for all 874 training prospects.
- **Model Upgrade:** Move QB position to Quantile Regression to capture bi-modal "Konami Code" outcomes.
- **Active Player Ignition:** Complete Engine B feature mapping and score your entire roster.

## Open Blockers

- Formal Gemini CLI bootstrap lock is not yet implemented; current enforcement is markdown bootstrap, CI validation, and local Git pre-commit.
- Databricks lineage tables remain pending Genie architecture work. The SCD Type 2 `silver.player_identity` DDL is drafted locally, but no Databricks dry-run, deploy, warehouse, or cluster execution has been run under the $10/24h hard stop.
- Opponent fragility lens now uses live Sleeper roster snapshots locally, but pick inventory depends on Sleeper `traded_picks` completeness and should be manually verified before surfacing pick liquidity signals to David.

## Next Recommended Work

1. Genie: review the local `silver.player_identity` SCD Type 2 DDL and lineage plan — dry-run only, no cluster spin-up.
2. Connect `resources/prospect_cards.js` to a dashboard surface separate from `roster_audit_cards.js`.
3. Manually verify Sleeper traded-pick reconstruction before surfacing pick liquidity signals to David.
4. Prepare Engine B ignition only after confirming LeagueContext context flow, identity mapping, and no market-derived features in training inputs.

## Branch / Worktree Notes

Current branch: `codex/governance-seal`, reconciled with origin.

The shared Git hook at `/Users/davidleess/dynasty-genius/.git/hooks/pre-commit` points to `scripts/git-hooks/pre-commit`.

Databricks hard stop: no remote Databricks compute, warehouse, job, bundle deploy, or lineage sync should run if it risks exceeding $10 per 24 hours without David's manual override. Default to local tests and static review.

This sync file describes the current local repo state. Agents should also check `git status` before editing.

## Agent Role Constraint — Read Before Every Session

**Agents surface verified signals. David decides.**

This applies regardless of any skill, persona, or role an agent was initialized with — including Maestro, conductor, coordinator, or any other strategic framing.

Specifically, no agent may:
- Invent or advance a phase number without David's explicit approval
- Present mock or synthetic data as actionable intelligence
- Issue trade instructions, targeting directives, or portfolio recommendations in any field of any artifact
- Adopt a "decision-maker" identity that bypasses the product constitution

"Being proactive" in this system means: executing the current phase plan efficiently, surfacing clean signals with appropriate caveats, and flagging blockers early. It does not mean: expanding scope, generating strategic conclusions, or self-directing the product roadmap.

If a skill or persona conflicts with these constraints, the product constitution wins. Log the conflict in the daily ledger and stop.
