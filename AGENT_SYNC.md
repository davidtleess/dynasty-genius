# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-07

## Active Phase

Phase 1: governance foundation and closed-loop agent operating system.

## Current Sprint Objective

Install the canonical governance doctrine:

- `docs/governance/00-product-constitution.md`
- `docs/governance/01-north-star-architecture.md`
- `docs/governance/02-agent-operating-loop.md`
- `docs/agent-ledger/`
- root bootstrap locks

After this refactor, agents should resume product work only through the operating loop.

## Latest Activity

- Codex created the initial governance document structure, archived the three founding documents, initialized `AGENT_SYNC.md`, and prepared the bootstrap lock pattern.
- Codex added Gemini PM signoff, Genie Databricks lineage plan, Codex governance-seal checklist, PR template, governance validator, and CI governance validation.

## Open Blockers

- Optional local pre-commit enforcement is not yet implemented.
- Databricks lineage tables are future Phase 2 work.

## Next Recommended Work

1. Review and commit the governance refactor on `codex/governance-seal`.
2. Add optional local pre-commit checks for ledger updates and banned model leakage.
3. Resume model/product implementation according to the phase sequence in `01-north-star-architecture.md`.

## Branch / Worktree Notes

Current governance branch: `codex/governance-seal`.

This sync file describes the current local repo state. Agents should also check `git status` before editing.
