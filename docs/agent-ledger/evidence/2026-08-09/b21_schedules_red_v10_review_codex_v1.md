# B21 schedules RED v10 review — NOT CLEAR

Date: 2026-08-09  
Reviewer: Codex, independent review lane  
Layer: Layer 1 retained source integrity and replay

## Reviewed pin

- `tests/contract/test_b21_schedules_capture_red.py`
- Submitted SHA-256: `3295af53813caf73b971d1e29d561304416f05da58a24eee006efb9a15caec99`
- Recomputed SHA-256: `3295af53813caf73b971d1e29d561304416f05da58a24eee006efb9a15caec99`

The four new contracts are non-vacuous against shipped module `901a756`: focused pytest produced
`4 failed / 73 passed`, exit 1, with exactly F0b–F0e failing. Ruff and `git diff --check` are clean;
full-suite collection is clean at 5,262 tests.

## Verdict

**NOT CLEAR.** The new tests cover the four reported examples, but they do not yet force the full
content-and-metadata identity rule their prose claims. A GREEN can pass v10 while accepting three
silent substitution/corruption classes.

## Consolidated findings

### F1 — P0: the content substitution fixture permits a byte-count-only validator

F0c says the retained object must be verified by full SHA-256, but substitutes a one-row Parquet for
the original three-row Parquet. Measured fixture sizes are 13,499 and 13,319 bytes. A GREEN that
compares only `byte_count` and raises `content_integrity_mismatch` passes F0c without hashing any
bytes.

There is a stronger same-length counterexample already available from the fixture: changing only the
third row's `away_score` from 27 to 28 yields a valid 13,499-byte Parquet with the same row count,
column count, ordered dtypes and schema hash, but a different SHA-256
(`a0478281...` versus `f84cc9f6...`). F0c must use, or add, a substitution whose byte length and
derived shape equal the original and whose full hash differs. Its fixture should assert those
preconditions.

### F2 — P0: one mutated claim does not prove the four-claim metadata rule

F0d's docstring requires agreement for row count, column count, ordered dtypes and schema hash, but
the test mutates only `row_count`. A GREEN that checks only `row_count` passes. This repeats the
special-case-as-rule defect already documented in this contract's own history.

Parametrize independent mutants for at least `row_count`, `column_count`, the full ordered `dtypes`,
and `schema_hash`, with a positive control and fixture preconditions proving each mutation changed
only the intended claim. Every mutant should require `vintage_metadata_inconsistent`.

### F3 — P0: vintage identity is not bound to the content identity

Neither F0c nor F0d verifies that the requested/path vintage ID, stored `vintage_id`, and
`raw_sha256` identify the same object. I recorded two valid same-schema three-row offerings, then
changed vintage A's metadata to point to vintage B's retained object and copied B's byte/count/schema
claims while leaving A's `vintage_id` intact. The read returned B's score 28 under requested vintage
A (`v-a04782812da063d0`), and every derived claim matched B. A reader that implements every v10
content and metadata comparison still accepts this unless it checks the identity relationship.

Add mutants that bind:

- the requested/path ID to stored `vintage_id`; and
- `vintage_id == "v-" + raw_sha256[:16]` (or the module's declared equivalent).

The two-valid-vintage pointer swap is the strongest fixture because content SHA, byte count, row
count, column count, ordered dtypes and schema hash all remain internally valid.

## Disposition of the submitted four cases

- F0b missing object: adequate.
- F0c wrong object: right error class, inadequate falsification strength until F1 is repaired.
- F0d metadata disagreement: right error class, incomplete mutation matrix until F2 is repaired.
- F0e unsupported parser version: adequate for the stated current-version refusal boundary.

No GREEN, source, provider, canonical store, config, commit, or push was changed by this review.
