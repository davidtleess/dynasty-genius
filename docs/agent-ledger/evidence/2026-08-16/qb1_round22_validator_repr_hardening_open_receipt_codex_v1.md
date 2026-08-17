# QB-1 Round-22 validator-repr hardening — open receipt (Codex v1)

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

- Independent RED reproduced the public-path artifact-less escape at
  `execution.py:2413 -> :1301`: hostile `__repr__` runs while the validator
  formats its refusal detail, before `QBValidationFailure` exists.
- Registration read **IMPLEMENTATION, not amendment**:
  `qb1_round21_validator_repr_registration_read_codex_v1.md`, SHA-256
  `063f8453efc1b829786a1f1c3ec68a59098241fcae34aeb677aa0f97f7642453`.
- Revision-guarded transition
  `qb1_round22_validator_repr_hardening_open_codex_v1.mjs`, SHA-256
  `1f1c3c543455900264df4a018f85fd21e8b1874945cc1b648118b9b886e7157e`,
  passed syntax + dry run and was applied once: revision **130**, ACTIVE
  `green-review`, Round 22 open at snapshot
  `eaf819adf64f4e6d0a64764da007c711029d694dde221840f3b28d1f93c79015`.
- Round 21 closed stopped-before-GREEN at snapshot
  `d36a430e998ddd943ebf04adb011d6d7aae5829a060d26c476ca49f21d237f83`;
  `finding-green-review-21-1` records the validator-detail failure. R20-G1
  remains carried and unresolved.
- Exact three-file scope: runner adapter, `execution.py`, and correction
  contracts. In `execution.py`, only the non-list `excluded_folds` and
  malformed exclusion-entry refusal details may lose payload representation;
  predicates, machine reason, vocabulary, registration, sibling clauses,
  inference, metrics, statuses, and claims are frozen.
- Required proof includes hostile entry and hostile container representations,
  atomic six-key `report_schema_invalid` artifacts on both publication phases,
  zero sentinel leakage, all prior adapter contracts, focused/five-file/full
  suites, static checks, synthetic publication, and one fresh metric-free
  real-composition projection with before/after hashes.
- No registered execution now. A fresh registered rerun remains held for
  explicit Codex CLEAR after independent review. No commit or push. H2 QB
  rushing remains **UNDER TEST with no result**.
