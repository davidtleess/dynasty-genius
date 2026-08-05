# Contracts third RED challenge — Codex v6

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **NOT CLEAR for GREEN**

## Independent execution

- Focused RED: 57 collected, 54 failed, 3 passed, zero collection errors.
- Ruff on the test and generator: pass.
- The reported full-tree increase from 4,621 to 4,630 is consistent with the nine added tests.

S4's full durable-state capture, S5's exact zero-argument assertion, S6's empty-grain control, the
strict encoder/generator, and the emitted snapshot-context checks are accepted. The following tests
can still pass for the wrong reason or fail a correct implementation.

## T1 — the revised deep round-trip silently skips unmatched rows

`tests/contract/test_contracts_ingestion_red.py:979-1007` builds a full-source digest map, but a
normalized row normally has no `source_digest`, so it falls back to a search. If neither route
matches, line 993 silently `continue`s. The only positive control is `compared >= 1`.

The test therefore passes when one nested row matches and every other non-null `cols` row is
unmatched or corrupted. Require every normalized row to match exactly one exact-unique source row,
and reconcile matched non-null, matched-null, collapsed, and total counts. The source and normalized
test-side digest multisets should agree before the deep comparison.

## T2 — the emitted type pin still omits all ten string dtypes

Lines 217-223 explicitly pin six integer, seven float, one Boolean and one JSON dtype. Exact values
are now checked for all 25 columns, which is useful, but a categorical/enum/object representation of
a string column can return the same Python values and pass. The empty-frame test at lines 793-802
has the same gap and additionally does not pin the three metadata dtypes.

Define the ten expected string columns and require `Utf8` for each in both populated and empty
Parquet. Pin `content_sha256`, `snapshot_id`, and `observed_at` types in the empty artifact too.

## T3 — normalization-to-source integrity is still not established

The exact emitted comparison at lines 227-244 pairs the publisher with **production-normalized**
rows. The digest oracle at lines 508-522 also hashes production-normalized rows. If normalization
changes a scalar source value and then hashes that changed value, both tests pass. The nested test
checks only `cols` for the rows it happens to match.

Independently canonicalize the exact-unique fixture source, including strict `cols` JSON, and assert
the complete 25-column normalized projection equals it before using normalized rows as the publisher
oracle.

## T4 — three digest assertions remain weaker than their names

1. `_test_side_digest` at lines 96-106 hashes every present key except a metadata deny-list. The
   cleared contract is an allow-list of the pinned 25 source columns. An unrecognized derived field
   would incorrectly enter the hash, while future metadata requires editing the deny-list. Build the
   payload explicitly from the pinned source columns.
2. The row-key test at lines 546-561 requires only that both strings occur somewhere in `row_key`.
   Prefixes, suffixes, duplicated fields, or another coordinate pass. Assert the exact composite
   representation.
3. The snapshot-digest test at lines 564-578 accepts any constant 64-character value not equal to a
   row digest. It does not prove sensitivity to rows, projection, coverage, observed-at or raw hash.
   Add one-field mutation tests for the facts the v3 idempotence digest must cover, plus a stability
   control for identical inputs.

## T5 — the fetch-boundary clock test measures the wrong boundary

At lines 886-898 the fetch records only its **entry** time, sleeps, and the test requires
`observed_at > entered`. A timestamp taken one microsecond after fetch entry but before fetch return
passes. D4-2 requires the stamp immediately **after fetch returns**.

Record a `returning` mark immediately before the fetch returns and require `observed_at` to be later
than that mark. This needs no arbitrary sleep once the correct boundary is observed.

## T6 — mixed seasonal content is still checked only by row count

Lines 750-755 are described as a content assertion but execute only `SELECT COUNT(*)`. Replacing
every NGS value while preserving 169 rows passes. Compare the mixed-run NGS table/export with a
seasonal-only baseline by exact canonical row/content hash.

## T7 — the seasonal unresolved branch is provably vacuous

Lines 763-773 guard every assertion with `if`. Independent normalization of the actual
`nflverse_usage_2025_slice.json` NGS-passing fixture gives:

- 169 rows;
- 169 `canonical_resolved`;
- zero `source_only`, conflict or unknown rows.

Thus `ngs_passing` can never appear in `unresolved_identity.parquet`; the seasonal-season assertion
does not execute. Mutate or add a measured-shape seasonal row to force a non-canonical identity,
assert both stream classes are present, then require their exact partition context. Never guard a
required test path with `if`.

## T8 — export recovery still does not assert the expected observations

Lines 831-862 collect snapshot IDs but require only that the recovery ID is among them, that all
remaining groups have equal counts, and that the export equals their sum. A system that deletes the
original and failed observations and retains only the recovery observation passes. The
`durable_after_failure` comparison is merely `old_length <= new_length`.

Capture the original successful ID, the durable IDs after the induced export failure, and the
recovery ID. Assert the exact final ID set and per-ID content hashes/coverage, and assert the prior
successful observation remains byte-identical. Then compare the emitted snapshot set exactly.

## T9 — durable coverage and failure vocabulary are searched rather than asserted

- Lines 927-942 stringify an arbitrary capture record with `default=str` and search its blob for the
  snapshot ID. The ID can occur in an unrelated field; `capture_axis`, `observed_at`, and coverage
  are not asserted by name/value.
- Lines 945-963 assert only failed status/stream and an empty `failed_season`. They do not require
  snapshot-axis vocabulary or inspect captured-before-failure state, despite the test docstring.

Assert named schema fields and exact values in the durable capture record and failed marker. Add a
failure after at least one stream is captured so `captured_before_failure` is non-empty and its
snapshot partition can be inspected.

No GREEN, commit, live landing or push is cleared by this disposition.
