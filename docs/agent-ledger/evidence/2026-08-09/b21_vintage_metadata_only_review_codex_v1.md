# B21 vintage metadata-only change — independent review and post-commit audit

Date: 2026-08-09
Layer: 1 — retained source provenance and replay
Reviewer: Codex
Commit reviewed: `901a7562c88f354b22b0bdf6299eda68929e61b1`
Verdict: **NOT CLEAR**

## Scope and exact committed state

The review covered the one behavioral change requested in
`vintage_metadata_only_review_request_claude_wire_v1.md`:

- `src/dynasty_genius/sources/schedules_capture.py`
- `tests/contract/test_b21_schedules_capture_red.py`
- `app/data/sources/nflverse_schedules/vintages/v-eeea1f47644cc498.json`

The three blobs are unchanged between `901a756` and current `HEAD`:

- module blob `75dddb9860737b48b96fee06716c01b367605864`
- RED blob `4033fa49f49d10e59c05d0ba69c21cf68beab3da`
- canonical vintage blob `0b7bc328f8a4471aef00b4890c8d6a5e2059cc07`

Exact-SHA GitHub Actions run `31315688634` succeeded for `901a756`: both Python and frontend jobs
completed successfully, including pytest and storage-policy verification.

## What is verified

The canonical data migration itself is lossless:

- old committed vintage: 9,504,385 bytes
- current metadata vintage: 2,801 bytes
- retained Parquet: 517,546 bytes; its SHA-256 still equals the vintage's
  `eeea1f47644cc498676be92b5ac0fb853fd4bce238348f0436aa786c1440d5c1`
- old stored rows: 7,548; newly derived rows: 7,548
- canonical sorted-JSON row digests: byte-identical
- all pre-existing metadata fields: byte-equivalent values
- added counts: 7,548 rows and 46 columns, matching the retained payload

The focused suite passes **73/73**, all four backup suites pass **55/55**, and Ruff is clean on the
module and RED.

These facts clear the destructive-migration question: the one canonical vintage was not changed
semantically by removing its duplicated `rows` array.

## Consolidated finding — P0: the new derived read is not content-addressed or fail-closed

The change makes the retained Parquet the only payload truth, but `get_vintage()` does not verify
that truth before returning it. At
`src/dynasty_genius/sources/schedules_capture.py:728-733`, it trusts the metadata's `raw_sha256`,
parses whatever file happens to be at that address, and returns the vintage. If the file is absent,
it returns the metadata dictionary without `rows`.

Two independent counterexamples pass all 73 committed contracts:

1. **Missing content.** After a valid three-row capture, deleting its content object makes
   `get_vintage()` return a dictionary that still claims `row_count=3` but has no `rows` key. This
   is silent partial success, not a named refusal.
2. **Valid substituted Parquet.** Replacing the content object with a valid one-row Parquet makes
   `get_vintage()` return the substituted row while retaining the original three-row count, raw
   hash, schema hash, and vintage identity. Measured output: metadata row count 3, returned rows 1,
   and the returned game changed to `2026_01_MIA_NE` with an injected away score of 99.

That is the exact second-source-of-truth drift the change says it removes, only now the disagreement
is between returned rows and the vintage's identity/metadata. The write path verifies pre-existing
content before reuse, but later loss/corruption/restoration is a real read-time state and cannot be
assumed away in a required backup store.

The repair must add RED-before-GREEN cases and make the canonical read atomically verify, before
returning rows:

- required content exists;
- byte count and full SHA-256 equal the vintage claims;
- freshly derived row count, column count, ordered dtypes, and schema hash equal the vintage;
- a missing or mismatched object raises one stable, named `CaptureError` and never returns a
  partial/mixed vintage.

## Residual P1: `parser_version` is recorded but not enforced

The docstring claims that `parser_version` plus retained bytes reconstructs a past parse
(`schedules_capture.py:716-721`), but `get_vintage()` always invokes the current `self.parse` and
never dispatches or refuses on the recorded version. Mutating only the metadata to
`unknown.future.parser` still returns all rows while reporting that unknown version.

Because rows are no longer stored, this version boundary is now load-bearing. The revised contract
must either pin/refuse unsupported parser versions or provide explicit version dispatch. It may not
silently interpret a historical vintage with a different parser while claiming reconstruction.

## Falsification matrix

| Input class | Probe/result |
|---|---|
| Valid nominal | 73 focused contracts pass; canonical 7,548-row derivation matches the removed rows |
| Size boundary | stored vintage is 2,801 bytes, below the contracted 16 KiB ceiling |
| Missing | **FAIL:** absent content returns partial metadata instead of refusing |
| Null/None | out of scope for the file object; provider null cell retention remains covered by existing GREEN |
| Wrong type / malformed bytes | malformed Parquet raises named `raw_unparseable`; positive refusal |
| Malformed shape but parseable | **FAIL:** valid one-row substituted Parquet is returned under stale three-row metadata |
| Duplicate/conflict | source duplicate `game_id` remains governed by existing G3; unchanged by this patch |
| Empty collection | capture-side empty offering remains refused by existing G1; unchanged by this patch |
| Cross-component shape | **FAIL:** row/column/schema/hash claims are not compared to newly derived rows |
| Numeric edge | score non-finite/type guards remain governed by existing G5; unchanged by this patch |
| Synthetic/override | **FAIL:** unsupported `parser_version` is silently accepted |
| Legacy stored `rows` | intentionally ignored by `pop("rows", None)`; correct positive compatibility behavior |

## Post-commit divergence disposition

There is zero byte divergence between the three current blobs and the blobs introduced by
`901a756`, and the canonical migration is lossless. There was no pre-commit behavioral CLEAR to
compare against; the actual committed state is therefore the reviewed artifact. It is **NOT CLEAR**
for the two reasons above. The post-commit loop remains open pending a revised RED, repaired module,
focused falsification rerun, and a new exact commit audit.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
