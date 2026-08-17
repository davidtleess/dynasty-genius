# Addendum — round-9 frozen-bundle interpreter isolation

Date: 2026-08-15 ET  
Parent review: `qb1_green_round9_review_codex_v1.md`

This addendum supersedes only the parent review's statement that the frozen
reinforcement collection failure was an additional unresolved verification
blocker. The two publication-gate BLOCKERs and the NOT CLEAR disposition are
unchanged.

## Measured cause

The active venv now resolves to Homebrew Python **3.14.7**, installed/upgraded
at 08:28 ET during round 9. Under 3.14.7, iterating
`decimal.Context().traps` raises `ValueError: invalid signal dict`, which causes
the unchanged reinforcement file to fail during collection.

The prior interpreter used by earlier round measurements remains installed at:

```text
/usr/local/Cellar/python@3.14/3.14.4_1/bin/python3.14
```

An isolated decimal probe succeeds under 3.14.4_1. No venv symlink,
`pyvenv.cfg`, package, or machine configuration was changed.

## Fresh comparable census

The complete correction + execution/program/inference + reinforcement bundle
was run under 3.14.4_1 while reusing the existing venv site packages without
mutating the venv:

```bash
PYTHONPATH=.venv/lib/python3.14/site-packages:. \
  /usr/local/Cellar/python@3.14/3.14.4_1/bin/python3.14 -m pytest -q \
  tests/contract/test_qb1_green_correction_contracts.py \
  tests/contract/test_qb1_execution_red.py \
  tests/contract/test_qb_validation_program_red.py \
  tests/contract/test_qb_validation_inference_red.py \
  tests/contract/test_qb_validation_green_reinforcement_red.py
```

Result: **660 passed, 14 warnings in 131.74s**, exit 0.

Therefore the frozen-bundle collection failure is interpreter drift, not a
round-9 code/test regression, and the comparable 3.14.4_1 census is green. The
round-9 verdict remains NOT CLEAR solely on the two grouped content findings
proved by the independent 5/5 public-runner probe.
