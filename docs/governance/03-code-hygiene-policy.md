---
document: Dynasty Genius Code Hygiene Policy
version: 1.1.0
last_updated: 2026-07-16
authority: code-quality
source_documents:
  - docs/strategies/2026-05-25-repo-linting-hygiene-spec.md
---

# Dynasty Genius Code Hygiene Policy

This is the binding code-quality policy for Dynasty Genius. It governs lint scope,
enforcement, and the unsafe-change guardrails for Python hygiene work.

Authority: This document governs code hygiene mechanics. It is subordinate to the
constitution (`00-product-constitution.md`) and the north-star architecture
(`01-north-star-architecture.md`) and operates under the agent operating loop
(`02-agent-operating-loop.md`). If it conflicts with those, they win — stop and log
the conflict rather than choosing the more convenient rule.

David approved the pragmatic-ratchet strategy on 2026-05-25. The implementation
record is in `docs/agent-ledger/2026-05-25.md` and `AGENT_SYNC.md`.

## Selected Ruleset

The committed Ruff configuration lives in `pyproject.toml`. The selected set is
deliberately narrow — the known correctness/hygiene debt plus import sorting, not a
formatting or modernization campaign:

```toml
[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]
```

- `target-version = "py314"`, `line-length = 88`.
- Per-file ignores: `**/__init__.py` → `F401` (re-exports); `tests/**` and
  `scripts/**` → `E402` (late imports after fixture/path/env setup).
- `E712` stays **selected**, never globally ignored: pandas/Polars/NumPy boolean
  masks are hand-reviewed and given a narrow `# noqa: E712` where the comparison is
  intentional.

Deferred — each is a separate decision, not part of this gate:

- `UP` (pyupgrade): modernization rewrites; a distinct initiative, not hygiene debt.
- `B` (bugbear): start as a read-only bug-class audit and triage, not an immediate gate.
- `RUF`: deferred except a possible later narrow `RUF100` (unused-`noqa`) pass.
- Broad `E`/`W`: excluded — they pull in whitespace/line-length churn (E501, W291/W293).

## Unsafe-Change Guardrails

These are non-negotiable for any lint work:

1. **Never run Ruff with `--unsafe-fixes`** without a narrow, explicit David approval.
   Default `ruff check --fix` (safe fixes) only.
2. **`E712` is never auto-rewritten** on pandas/Polars/NumPy masks. `is True` / `is False`
   is wrong on a Series, and `~series` / bare-series can change behavior for int/object
   dtype. Preserve the comparison and add `# noqa: E712` with a reason.
3. **Side-effect / registration imports are protected.** Hand-review every `F401` and
   `I001` diff that touches adapters, registries, package `__init__.py`, route mounting,
   plugin/module discovery, or import-time registration. Preserve side-effect imports,
   public re-exports, and `__all__` contracts — add a narrow explanatory `noqa` rather
   than letting Ruff remove or reorder them. Tests catch the break only if they exercise
   the affected import path; do not rely on the suite alone.

## Enforcement

- **CI is the hard gate.** `.github/workflows/ci.yml` installs the pinned Ruff version
  and runs `ruff check src app` on every push/PR to `main`. Production (`src/`, `app/`)
  must stay at zero selected findings.
- **Pre-commit is the local fix-on-touch ratchet.** `.pre-commit-config.yaml` pins
  `astral-sh/ruff-pre-commit` (check-only) and lints staged Python files as whole files —
  so touching a file requires it to be clean under the selected rules. Activate locally:
  `.venv/bin/python3.14 -m pip install -r requirements-dev.txt && .venv/bin/pre-commit install`.
- The pinned Ruff version in CI **must match** the `rev` in `.pre-commit-config.yaml`.
- Legacy `tests/` and `scripts/` findings are cleaned **on touch**, not in a dedicated
  sweep. A full zero-drive of `tests/`/`scripts/` (and flipping CI to full-repo Ruff)
  requires a separate David approval.

## Scope Discipline

- Lint cleanup runs on a dedicated branch (e.g. `hygiene/ruff-lint-ratchet`), not bundled
  with feature/model work, unless it is a tiny fix in files already being changed for an
  approved task.
- Lint-only commits must not include model artifacts, generated valuation data, source
  snapshots/caches, semantic formula changes, or API response-contract changes.
- Production code (`src/`, `app/`) holds the highest bar: zero selected findings, except
  an explicitly justified `noqa` with a reason.

## Rule-Change Process

Any change to the selected rules, ignored rules, enforcement surface, pinned version, or
CI gating is a **policy change**:

1. Route through the standard cockpit review (implementing lane + independent reviewer, constitutional-alignment checks enumerated per 02).
2. Obtain David's explicit approval; record it in `AGENT_SYNC.md` or the daily ledger.
3. Only then may Claude Code / Codex implement the change.

Policy changes are proposed through the cockpit and ratified by David; no lane runs lint
cleanup without a dedicated branch and David approval.
