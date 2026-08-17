# QB-1 Round-21 validator-repr registration read (Codex v1)

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 129

## Independent measurement

At the Round-21 opening product pins, the new public-runner hostile-`__repr__`
contract fails before a named validation failure is constructed:

1. `run_qb1_study` calls `validate_registered_report_blocks` on the assembled
   success report (`execution.py:2413`).
2. The exclusion-row predicate correctly identifies the malformed `reasons`
   value (`execution.py:1288-1298`).
3. While constructing the refusal detail, `f"{entry!r}"` invokes the hostile
   value's `__repr__` (`execution.py:1301`).
4. `RuntimeError: r21-hostile-repr-sentinel` escapes the public function before
   `QBValidationFailure("report_schema_invalid", ...)` exists and before the
   terminal artifact is written.

Independent command:

`python -m pytest tests/contract/test_qb1_green_correction_contracts.py::test_r21_hostile_repr_end_to_end_named_failure -q --no-header --tb=short`

Observed: **1 failed** at the exact traceback above. This reproduces Claude's
RED measurement. `execution.py` remains at
`3fd4144c75544e0941a913ec93c1e6d428de409742e591afd7bbe32f209ba2ab`.

## Registration classification

**IMPLEMENTATION hardening, not a registration amendment.** The registered
predicate, closed reason vocabulary, comparison shape, status logic, and
terminal schema do not change. The correction changes only how the validator
constructs human-readable detail after the existing predicate has already
refused malformed input.

The bounded implementation is to remove payload representation from the two
refusal messages in the exclusion-row clause:

- non-list `excluded_folds`; and
- malformed exclusion entry / reasons.

Both messages become stable structural descriptions containing no payload
value, source text, exception text, or digest. The `_refuse` call and its
machine reason remain exactly `report_schema_invalid`. Sibling validator
clauses are outside this measured correction and remain unchanged.

## Round boundary

Round 21 cannot satisfy its end-to-end proof within its two-file scope and
must close stopped-before-GREEN. Round 22 may add only
`src/dynasty_genius/eval/qb_validation/execution.py` to the existing runner +
contract scope. Required RED/GREEN proof covers hostile representations for
both exclusion-container and exclusion-entry refusal branches, an atomic
six-key failure artifact on both public publication phases, zero sentinel
leakage, and all Round-20/21 adapter behavior. The broader correction, static,
suite, synthetic-publication, and metric-free real-composition projection
gates remain in force.

No registered execution is authorized by this classification. A fresh rerun
remains held for explicit Codex CLEAR after independent review. No commit or
push. H2 QB rushing remains **UNDER TEST with no result**.
