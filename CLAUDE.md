# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# STOP. DYNASTY GENIUS BOOTSTRAP PROTOCOL.

You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

You do not rely on prior chat memory. You do not rely on summaries. Before executing any command, writing any code, reviewing any pull request, or making any analytical recommendation, you must read the following files in this exact order:

1. `docs/governance/02-agent-operating-loop.md` (How you must work and log your session)
2. `docs/governance/00-product-constitution.md` (The immutable football rules)
3. `docs/governance/01-north-star-architecture.md` (The codebase structure)
4. `docs/governance/03-code-hygiene-policy.md` (Lint scope, enforcement, and unsafe-change guardrails — for Python work)
5. `AGENT_SYNC.md` (The current sprint state — contains active blockers and script run gates)

If you attempt to write code or analyze players without logging your work in `docs/agent-ledger/` and adhering to the governance files, you are failing your prime directive.

## Environment

The project uses Python 3.14. Always invoke the project venv explicitly:

```bash
.venv/bin/python3.14 -m pytest          # run tests
uvicorn app.main:app --reload           # run the API server
```

Two test files have pre-existing collection errors and must be excluded from standard runs — check `AGENT_SYNC.md` for the current exclusion list.

## Developer Quick Reference

After completing the governance reads, see `docs/development/quick-reference.md` for the module map, key scripts, and architecture overview.
