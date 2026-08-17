# QB-1 Round-20 independent review finding — Codex v1

Date: 2026-08-16 (America/New_York)
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 126, green-review Round 20

## Verdict

**NOT CLEAR — one blocking failure-surface defect.** Registered execution remains held.

## Reviewed pins

- `scripts/run_qb1_study.py` — `ec19067ca428c72b7ea6852d67fb553d63fa3cb679120f8d44639e5e747e60dc`
- `tests/contract/test_qb1_green_correction_contracts.py` — `9661c5363b88c8a3f0b067fc3ae02cfc2e0f9465eca4b4d015ad78a094652cd1`

Forbidden Round-20 files and the registered terminal artifact/receipt were independently re-pinned unchanged before this finding.

## Blocking finding

`scripts/run_qb1_study.py:621` searches for the internal word with:

```python
if "empty_common_pool" in repr(entry):
```

This calls arbitrary representation code precisely on the unreadable-shape path. An exclusion Mapping whose `reasons` value has a raising `__repr__` causes `_canonical_excluded_folds` to raise that arbitrary exception, not `QBValidationFailure("report_schema_invalid", ...)`. In the real runner this can therefore route to the generic `execution_error` catch, violating Round 20's named fail-closed boundary and bypassing the R19 two-catch failure-origin diagnostic.

Independent probe at the reviewed pins:

```text
invalid-reasons-repr raised RuntimeError review-sentinel-repr
unrelated-field-false-positive raised QBValidationFailure report_schema_invalid: internal reason empty_common_pool sits in an unreadable exclusion entry/reasons shape
```

The second line also demonstrates that the representation scan is not confined to the `reasons` field: an unrelated metadata value containing the token triggers the adapter refusal.

## Required correction boundary

- Remove all `repr`/stringification inspection from this adapter.
- Inspect `empty_common_pool` only when `entry` is a Mapping and `reasons` is a structurally readable list/tuple.
- Pass unreadable entry/reasons shapes through unchanged to the existing registered validator; it already refuses them as `report_schema_invalid`, preserving gate authority without evaluating arbitrary local representations.
- Replace the current direct-helper unreadable-shape expectations with an end-to-end assertion that malformed shapes, including a hostile `__repr__`, terminate as `report_schema_invalid` and never `execution_error`.
- Re-run the Round-20 focused/bundle/static/synthetic/final-projection evidence at stable corrected pins and route for re-review. No registered rerun.

## Checks completed before verdict

- Complete scoped diff inspected against the Round-20 open snapshot.
- Focused correction contracts: `175 passed` under the repository Python environment.
- Scoped Ruff and strict compilation: clean.
- Independent hostile-representation probe: reproduced the blocker above.
- H2 QB rushing remains **UNDER TEST with no result**.
