# B21 schedules RED v11 review — NOT CLEAR

Date: 2026-08-09  
Reviewer: Codex, independent review lane  
Layer: Layer 1 retained source integrity and replay

## Reviewed pin and gates

- `tests/contract/test_b21_schedules_capture_red.py`
- Submitted and recomputed SHA-256:
  `e7b25324f049f7688a0ac7ff21beee0987cf8fcdc3faaa7e80344f68773be0be`
- Focused RED against shipped GREEN: `9 failed / 73 passed`, exit 1. The nine failures are exactly
  F0b, F0c, F0d ×4, F0f ×2 and F0e.
- Ruff and `git diff --check`: clean.
- Full-suite collection: 5,267 tests, exit 0.

## Prior findings disposition

F1–F3 from the v10 review are accepted in substance. F0c now proves same length/same schema/different
SHA, F0d has independent top-level claim cases, and F0f correctly binds requested/stored/content
identity from both directions.

## Verdict

**NOT CLEAR.** Two residual P0 falsification gaps remain. Both are consequences of strengthening the
v10 examples and can be repaired without changing the intended behavior.

## Consolidated findings

### R1 — P0: v11 forces full SHA but no longer forces the separate byte-count check

F0c's same-length replacement is the correct counterexample for a hash-only omission: a reader must
compute SHA to reject it. But because both byte strings are 13,499 bytes, a reader that ignores
stored `byte_count`, verifies SHA-256, and verifies every derived claim passes all nine v11 cases.

The vintage writes and returns `byte_count` as an integrity claim, and F0f even copies it as part of
the internally consistent replacement metadata. No current read-corruption test mutates that claim.
Add an independent case that leaves the retained bytes untouched, changes only stored `byte_count`,
asserts the mutation precondition, and requires a named refusal. Together, the existing same-length
case and this claim-drift case force both checks rather than trading one for the other.

### R2 — P0: the dtype mutant lets a one-entry validator pass and does not test order

F0d's `dtypes` case replaces **every** dtype value with `Utf8Bogus`. A reader that recomputes and
compares only the first dtype catches that fixture and passes v11 while ignoring the other 45 — the
same one-sampled-dtype defect the contract's own F2 history says is inadequate. The blanket mutation
therefore does not force a full ordered-sequence comparison.

Use minimally different counterexamples:

- change exactly one non-sentinel dtype pair while keeping all others byte-identical; and
- reorder two pairs without changing their names or values.

For exhaustive enforcement of the claimed full map, mutate each pair position independently (the
fixture has 46 columns); at minimum, cover more than one position plus order and assert every
unchanged pair remains identical. The `schema_hash` mutant should likewise change one valid hex
nibble rather than replace the entire value with zeros, so a prefix-only comparison cannot satisfy
the test.

## Non-blocking factual corrections

- F0c's docstring still says the replacement is a valid **one-row** Parquet although the fixture is
  now a same-shape three-row Parquet.
- The test file is tracked and modified in the working tree, not untracked (`git status --short`
  reports `M tests/contract/test_b21_schedules_capture_red.py`). It is correctly uncommitted.

No GREEN, source, provider, canonical store, config, commit, or push was changed by this review.
