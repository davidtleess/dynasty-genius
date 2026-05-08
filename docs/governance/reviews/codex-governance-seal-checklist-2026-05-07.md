# Codex Governance Seal Checklist - 2026-05-07

## Objective

Prepare the first implementation package that seals the Dynasty Genius governance operating system before product build resumes.

## Files In Scope

- `docs/governance/00-product-constitution.md`
- `docs/governance/01-north-star-architecture.md`
- `docs/governance/02-agent-operating-loop.md`
- `docs/governance/archive/originals/*`
- `docs/governance/reviews/gemini-product-signoff-2026-05-07.md`
- `docs/governance/platform/databricks-lineage-plan.md`
- `.clauderules`
- `CLAUDE.md`
- `AGENTS.md`
- `AI_CONTEXT.md`
- `README.md`
- `docs/README.md`
- `AGENT_SYNC.md`
- `docs/agent-ledger/2026-05-07.md`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`
- `scripts/validate_governance.py`

## Files Out Of Scope

- unrelated Databricks scaffold not required by this governance seal
- existing `.gitignore` or mission recalibration edits not created for this package
- Engine A or Engine B implementation changes
- frontend work

## Validation

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache_tmp python -m compileall app
python scripts/validate_governance.py
```

Expected result: both commands pass.

## Handoff To Claude Code

Claude Code should begin by reading `CLAUDE.md`, `.clauderules`, `02-agent-operating-loop.md`, the constitution, architecture, `AGENT_SYNC.md`, and the daily ledger.

Claude Code should stage only the files in scope above unless David explicitly expands the package.
