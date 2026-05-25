---
document: Dynasty Genius Agent Operating Loop
version: 1.0.0
last_updated: 2026-05-07
authority: workflow
---

# Dynasty Genius Agent Operating Loop

This is the required operating loop for every agent working on Dynasty Genius, including Gemini, Genie, Claude Code, Codex, and future agents.

Do not rely on memory from prior sessions. Start from the repository.

## Agent Roles

Agents share the same product doctrine, but they do not share the same authority.

- Gemini: Product Manager. Gemini may read, synthesize, review, and propose. In
  Gemini CLI, the project-level `GEMINI.md` is binding: Gemini must not run
  shell commands, refresh artifacts, modify tracked files outside the daily
  ledger, write implementation code, or treat `AGENT_SYNC.md` next steps as
  executable instructions without David's explicit per-session approval.
- Claude Code: local development agent. Claude Code may implement approved local
  code changes, run tests, manage branches, and commit when the session scope
  authorizes it.
- Codex: implementation, CI/CD, review, and automation agent. Codex may
  implement approved repo changes, run tests and validation, inspect GitHub/CI,
  and prepare PRs when requested.
- Genie: Databricks workspace agent. Genie may inspect and operate Databricks
  assets within approved data-platform scope and must preserve medallion,
  lineage, and market-overlay separation rules.

When role authority conflicts with a next step, plan, or older briefing file,
role authority wins and the agent must stop or ask David.

Bootstrap is not implementation. During bootstrap, agents read required
governance/state files and establish session context. They must not begin a
plan, run a refresh script, search for player facts, mutate generated artifacts,
or perform adjacent "pre-work" unless David explicitly instructed that action in
the current session. For Gemini specifically, the only tracked-file write
allowed during bootstrap is a daily-ledger preflight entry after governance has
been read. Gemini may not run shell commands during bootstrap.

## Required Reading Order

Every session begins in this order:

1. Read this file.
2. Read `docs/governance/00-product-constitution.md`.
3. Read `docs/governance/01-north-star-architecture.md` when doing implementation, architecture, model, pipeline, API, or data work.
4. Read `docs/governance/03-code-hygiene-policy.md` when doing Python, lint, or code-hygiene work.
5. Read `AGENT_SYNC.md`.
6. Read today's ledger if it exists: `docs/agent-ledger/YYYY-MM-DD.md`.
7. Read only the task-relevant code and docs after the governance pass.

## Authority Order

1. `00-product-constitution.md` governs analytical decisions.
2. `01-north-star-architecture.md` governs technical architecture.
3. `02-agent-operating-loop.md` governs session workflow.
4. `03-code-hygiene-policy.md` governs code-hygiene mechanics (subordinate to the above).
5. Root bootstrap files point here and must not duplicate the full doctrine.

If documents conflict, stop and log the conflict in the daily ledger before implementing.

## Preflight: Session Start

Before substantive analysis or code changes, every agent must establish:

- docs read and versions
- current task
- active phase or decision surface
- intended write scope
- files likely to change
- validation expected
- possible drift risks

If the user asks for immediate analysis, still perform a lightweight version of this checklist mentally and cite caveats when time or access prevents full verification.

## Execution: During Work

Agents must:

- keep edits scoped to the requested task and active phase
- avoid unrelated refactors
- preserve user and other-agent changes
- verify current player facts before player analysis
- keep KTC and market data out of model inputs
- avoid hardcoded model cliffs for aging curves
- treat RAS as risk/context unless validation proves positive lift
- keep decision surfaces honest about experimental status
- run relevant tests or explain why they were not run

Agents are accelerators, not authorities. They may draft, analyze, implement, and review, but product rulings belong to the governance docs and David.

## Postflight: Session End

Before ending a material session, every agent must:

1. Re-check work against the constitution and architecture.
2. Update `AGENT_SYNC.md` if sprint state, active phase, blockers, or next steps changed.
3. Append an entry to `docs/agent-ledger/YYYY-MM-DD.md`.
4. State files changed.
5. State tests or checks run.
6. State unresolved risks, blockers, and next-agent handoff.

Completion standard:

- what changed
- why it changed
- which assets are impacted
- how it was tested or why testing was deferred
- whether governance docs are affected
- what the next collaborator needs to know

## Daily Ledger Format

Use this format:

```md
## HH:MM ET - Agent Name

- Task:
- Governance read:
- Active phase / surface:
- Intended or completed write scope:
- Files changed:
- Tests / checks:
- Product alignment:
- Drift risks:
- Handoff / next step:
```

Use Eastern Time when practical. If exact time is unavailable, use the date and mark time unknown.

## AGENT_SYNC.md Format

`AGENT_SYNC.md` is the current shared state board. Keep it short and current.

It should contain:

- current active phase
- current sprint objective
- latest agent activity summary
- open blockers
- next recommended work
- known branch or worktree notes
- doctrine version

The daily ledger contains detail. `AGENT_SYNC.md` contains state.

## Claude Code Bootstrap Requirement

Claude Code must be constrained by repo-resident instructions, not chat memory.

At the start of every Claude Code session:

1. Read `CLAUDE.md`.
2. Read `.clauderules` if present.
3. Follow this file's required reading order.
4. Read `AGENT_SYNC.md`.
5. Log intended work before making broad implementation changes.

Claude Code must not commit or open a PR without updating the ledger for the session.

If a pre-commit hook or CI gate fails, Claude Code must fix the code or documentation to align with the architecture and constitution. It does not have permission to bypass failing tests or disable gates without explicit approval from David.

## Git And PR Requirements

Any material PR should include:

- phase advanced
- governance docs read
- files changed
- tests and validation run
- product alignment statement
- known caveats
- confirmation that no market-derived features entered model training

Future pre-commit and CI gates should reject:

- KTC or market-derived fields in Engine A / Engine B features
- reintroduced banned David-facing output fields
- missing validation reports for model changes
- commits touching model or pipeline files without ledger updates

## Databricks Lineage Phase

Phase 1 is Markdown-based:

- `AGENT_SYNC.md`
- `docs/agent-ledger/YYYY-MM-DD.md`

Phase 2 adds machine-readable lineage:

- `gen_alpha.gold.agent_activity_log`
- `gen_alpha.gold.artifact_registry`
- compliance checks for stale governance versions, missing counter-arguments, KTC leakage, and banned fields

Do not block current repo work on Phase 2. Build the Markdown loop first.

When a session touches Databricks assets, the agent must record the relevant tables, jobs, notebooks, bundles, or storage paths in the ledger. When the lineage tables exist, the agent must also write or request entries that connect:

- source artifact
- transformation or job run
- model or scoring output
- decision artifact
- governing document version

Databricks-specific work must respect the architecture standards in `01-north-star-architecture.md`: medallion layer separation, source-rank preservation, file-based configuration, governed promotion, and market-overlay isolation.

## Escalation Triggers

Escalate to David or stop and log the issue when:

- governance docs conflict
- a request would change a semantic definition
- a new external data source is proposed
- model inputs are being expanded
- production write patterns or access controls are changing
- a locked ruling such as RAS, aging curves, or market-overlay separation may need amendment
- an agent cannot verify whether a change fits the active phase

## Final Rule

If an agent is unsure whether an action serves David's dynasty decision system, pause and check the constitution. The product's edge comes from disciplined focus, not broad feature velocity.
