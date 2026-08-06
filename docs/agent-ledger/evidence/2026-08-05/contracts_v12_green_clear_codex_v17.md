# Contracts V12 fresh GREEN review — Codex v17

Date: 2026-08-05  
Layer: 1 ingestion  
Target: uncommitted v16 working tree  
Disposition: **GREEN CLEAR**

## Target pinned

- `src/dynasty_genius/nflverse_usage.py` sha256
  `f2a62bad99b51618fe8f80c57e652d57092527de8e368bd027a4541921c9a957`
- `tests/contract/test_contracts_ingestion_red.py` sha256
  `62c3073050f00b4e6e1168a5f7d9f5f0a41397bea3b6083f3646454561ef89f0`
- Implementer evidence `contracts_v12_green_claude_v16.md` sha256
  `4bd67eb4bb15d1c34a093413e99fd49e99139cd042022dc29a582e3dbd1e0179`

This review covers the narrow fresh GREEN answering F1-F3 in
`contracts_v12_green_review_codex_v15.md`. It does not reopen accepted V12 mechanisms or authorize
any runtime/product action.

## Independent checks

- Contracts contract: **103 passed**.
- Board-named prior-ingestion slice: **147 passed**.
- `.venv/bin/ruff check src app`: **passed**.
- `git diff --check`: **passed**.
- Controlled direct probe: illegal snapshot partition refused, named every extra key, and wrote
  zero files; legal partition preserved authoritative stream/count/time/schema and two records.
- Controlled SQLite probe: fully populated seasonal-axis row failed specifically with
  `CHECK constraint failed: capture_axis = 'snapshot'`; the otherwise identical snapshot-axis row
  was accepted.
- Caller scan: exactly one production snapshot-axis `write_raw_snapshot(..., partition=...)` call,
  in `_run_locked_capture`; it supplies exactly `capture_axis`, `snapshot_id`, and `observed_at`.

Claude reported the full suite as 4,655 passed / 12 skipped / 9 xfailed with pytest exit 0. Codex
did not rerun the full suite in this narrow review; the independent CLEAR rests on the focused
changed-surface and frozen-stream regression checks above, not on re-attributing that reported
count.

## F1 — CLOSED

The snapshot partition key set is now exact. After the existing axis/required-value checks,
`write_raw_snapshot` computes every key outside
`{capture_axis, snapshot_id, observed_at}` and refuses before creating the raw directory or file.
Collisions with writer-owned metadata are named separately.

The six refusal controls cover one arbitrary key, each of the four authoritative collisions, and
all four collisions together; each names every offending key and proves no file was written. The
positive control verifies writer-owned stream, row count, captured-at, and schema version. The
independent probe reproduced both halves.

**Behavioral boundary:** the only production snapshot-axis caller already uses the exact set, so
its nominal behavior is unchanged. Direct/test/external callers that supplied extra snapshot
metadata now fail closed; that is the ruled V12-3 exact-envelope contract, not an accidental
compatibility break. Seasonal callers never pass a partition and are untouched by this branch.

## F2 — CLOSED

The axis-CHECK control now populates every column. Only `capture_axis='seasonal'` is invalid, and
the assertion matches SQLite's CHECK-specific error. The same populated row with
`capture_axis='snapshot'` is accepted. The independent discriminator reproduced the CHECK failure
and positive insertion, so the test no longer passes via unrelated NOT NULL constraints.

## F3 — CLOSED

The repaired matrix isolates every v15 gap:

1. An all-required-NOT-NULL ledger with no axis CHECK refuses specifically because the CHECK is
   absent.
2. A ledger with the axis CHECK but nullable `raw_sha256` refuses and names that column.
3. Blank provenance covers all four guarded fields with both empty and whitespace-only values,
   while every surrounding input is valid. Removing the code guard would let those TEXT values
   through SQLite, so the controls are discriminating.
4. First/later and added/missing exact-column controls pin the literal record index plus both
   unexpected and missing sets.
5. Seasonal stability pins filename and literal bytes, including object/record key order,
   separators, and trailing newline; the parsed-record assertion separately proves source record
   order.

No remaining control in the reviewed F1-F3 surface was found to pass vacuously.

## Final disposition and boundaries

**GREEN CLEAR on the contracts V12-1..5 corrective implementation and its durable controls at the
pinned hashes above.** The v14 NOT CLEAR is superseded by this reviewed v16 state.

This CLEAR does **not** authorize or clear landing, capture, export, scheduler, consumer,
model/feature use, commit, or push. `contracts` remains `substrate_only` with zero rows in the
product store. Any later commit requires David's word and a post-commit divergence audit; any live
landing remains a separate David-gated act covering all prior streams plus contracts. Stream 6
`ff_rankings` is outside this review and remains a separate market-overlay design question. H2 QB
rushing remains a registered hypothesis **UNDER TEST** with no result.
