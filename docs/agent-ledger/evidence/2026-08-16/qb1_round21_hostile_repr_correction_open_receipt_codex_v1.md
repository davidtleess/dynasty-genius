# QB-1 Round-21 hostile-repr correction — open receipt (Codex v1)

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## Authority and durable transition

- David's fresh continuation word: `ok lets get it fixed and keep going`.
- Revision-guarded transition script:
  `qb1_round21_hostile_repr_correction_open_codex_v1.mjs`, SHA-256
  `d27f2edaea7376653cc814fb605291e003be81c510a3888b00b7de847d3e5ada`.
- Guarded dry run succeeded at revision 128. Its sole `--apply` moved the run
  to revision **129**, ACTIVE `green-review`, `terminalState=null`, with no
  reason codes.
- Round 20 was closed without a reviewer verdict, preserving unresolved
  BLOCKER `finding-green-review-20-1`; Round 21 opened at the same current
  two-file snapshot
  `607b377acddedaa708c09a45f24ab0775f5a43aa26e65a123142655013f6b2e4`.

## Exact correction boundary

- Layer served: Layer 3 terminal-publication adapter. Frozen input and
  producer evidence show no Layer 1/2 correction is needed or authorized.
- Writable scope only:
  `scripts/run_qb1_study.py` and
  `tests/contract/test_qb1_green_correction_contracts.py`.
- Opening pins: runner
  `ec19067ca428c72b7ea6852d67fb553d63fa3cb679120f8d44639e5e747e60dc`;
  contracts
  `9661c5363b88c8a3f0b067fc3ae02cfc2e0f9465eca4b4d015ad78a094652cd1`.
- Remove every `repr`/stringification inspection from the exclusion adapter.
  Inspect `empty_common_pool` only when an entry is a Mapping and `reasons`
  is a list/tuple. Pass unreadable shapes unchanged to the registered
  validator, which must refuse them as `report_schema_invalid`.
- Preserve the Round-20 exact-token rule: remove only one exact
  `empty_common_pool` when `fold_starved` co-occurs; refuse a duplicate or a
  readable missing-`fold_starved` occurrence; preserve all other unknown
  words for the unchanged gate; never mutate the internal inference record.

## Required proof and execution hold

- RED first: hostile `__repr__`, end-to-end `report_schema_invalid` with no
  `execution_error`, and unrelated-metadata false-positive regression.
- Keep all original Round-20 contracts green; run the focused and five-file
  bundles, full suite, scoped Ruff/compile, synthetic terminal publication,
  and one fresh metric-free real-composition projection with mandatory
  before/after digests.
- Resolve the carried finding only after independent proof and review.
- No registered runner in Round 21. Exactly one fresh registered rerun remains
  held for a subsequent explicit Codex CLEAR. No commit or push.
- H2 QB rushing remains **UNDER TEST with no result**.
