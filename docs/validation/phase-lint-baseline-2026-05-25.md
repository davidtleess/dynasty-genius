# Repo Lint Hygiene — Phase 0 Baseline (2026-05-25)

Initiative: `hygiene/ruff-lint-ratchet` · Strategy: **Option A (Pragmatic Ratchet)**, David-approved 2026-05-25.
Policy/spec: `docs/strategies/2026-05-25-repo-linting-hygiene-spec.md`.

This is the Phase 0 baseline capture. **No source files were modified in P0** — config + measurement only.

## Tooling / version of record

- Ruff **0.15.12** (matches `.venv/bin/ruff`) — recorded here as the version of record.
- The enforcing `astral-sh/ruff-pre-commit` hook (pinned at this `rev`) is **deferred to P3**, after `src/`+`app/` are clean, so the whole-file ratchet cannot block the P1/P2 cleanup commits.
- `target-version = "py314"` is accepted/validated by ruff 0.15.12 (rejects invalid values such as `py999`).

## Config summary (`pyproject.toml`)

```toml
[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]   # E712 stays SELECTED (manual review), never --unsafe-fixes

[tool.ruff.lint.per-file-ignores]
"**/__init__.py" = ["F401"]   # package re-exports
"tests/**" = ["E402"]          # late imports after fixture/path/env setup
"scripts/**" = ["E402"]        # one-shot scripts set up sys.path / env first
```

Scope rationale: the broad `E,W,UP,B,RUF` set explodes to ~2,600 findings on this repo (mostly whitespace/line-length + modernization churn). The selected set keeps the baseline at the known correctness/hygiene debt plus import sorting. `UP` (392), `B` (29), `RUF` (136) are deferred.

## Baseline — `ruff check . --statistics` (config applied)

**Total: 317 findings** (255 safe-fixable; 24 hidden *unsafe* fixes that are intentionally NOT applied).

| Count | Rule | Description | Notes |
|------:|------|-------------|-------|
| 125 | I001 | unsorted-imports | **P1b** dedicated mechanical commit |
| 112 | F401 | unused-import | P1a; review adapter/registry/`__all__` diffs |
| 29  | E701 | multiple-statements-on-one-line (colon) | P2 (manual) |
| 17  | F541 | f-string-missing-placeholders | P1a |
| 13  | F841 | unused-variable | P2 (manual; check for dropped assertions) |
| 10  | E712 | true-false-comparison | P2 (manual; pandas masks → `# noqa: E712`) |
| 4   | E702 | multiple-statements-on-one-line (semicolon) | P2 (manual) |
| 3   | F821 | undefined-name | P2 (annotation forward-refs → add import) |
| 2   | E722 | bare-except | P2 (manual; choose real exception) |
| 1   | E731 | lambda-assignment | P1a |
| 1   | F811 | redefined-while-unused | P1a |

## Per-directory totals

| Area | Findings | Phase |
|------|---------:|-------|
| `src/`     | 25  | P2 (production → zero) |
| `app/`     | 24  | P2 (production → zero) |
| `tests/`   | 155 | ratchet on-touch (P4 only if separately approved) |
| `scripts/` | 113 | ratchet on-touch (P4 only if separately approved) |

Production (`src`+`app`) = **49**; tests+scripts = **268**.

## Reconciliation note

- `E4,E7,E9,F` alone = **226**; adding `I` = **351** (the +125 `I001` import-order findings).
- The config nets **317** because `tests/**` + `scripts/**` `E402` (34 findings) are per-file-ignored.
- `I001` is isolated into the dedicated **P1b** import-sort commit so it never masks logic diffs.

## Exit criteria (met)

- `pyproject.toml` config exists.
- Baseline documented (this file).
- `.venv/bin/python3.14 scripts/validate_governance.py` → **passed**.
- No source files changed (config/docs/ledger only).
- Stop after P0 and checkpoint with David before P1.
