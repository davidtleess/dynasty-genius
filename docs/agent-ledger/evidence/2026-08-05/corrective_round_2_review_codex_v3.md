# Corrective round 2 and depth-charts review — Codex v3

Date: 2026-08-05

Immutable corrective target: `36c813cb54a3a20259fa11b7bcb0b603c7093d4f`

Depth landing under review: `7654a199ddbf6f2e0b49e5c6ffe4a4a21bfe8692`, as corrected forward by
`7de9357` and `36c813c`

## Disposition

- Corrective commit `36c813c`: **NOT CLEAR** — one narrow Boolean-domain blocker remains.
- Stream 4 (`depth_charts`) at current head `36c813c`: **CLEAR**. The bare immutable commit
  `7654a19` remains superseded/NOT CLEAR on its own; this is a current-state stream CLEAR after the
  two forward corrections, not a retroactive CLEAR of the original commit.

## Independent positive evidence

- The four focused contract modules passed **86/86** from a detached worktree.
- Targeted Ruff passed. `git show --check 36c813c` found no source/test whitespace defect (only
  previously committed evidence files with an extra blank line at EOF).
- Live last-good run `nflverse-usage-20260805T1334216901700000` is `ok`; the product store contains
  **1,491,691** rows and the export contains all twelve data streams plus unresolved identity.
- Depth has **812,074** rows: 257,859 weekly and 554,215 daily. Published
  `season/week/pos_slot/pos_rank` are all `Int64`.
- The weekly export contains zero literal-whitespace `depth_position` values; after normalization
  and exact-duplicate collapse it contains 3,925 null `depth_position` values and 1,646 null weeks.
  Every daily grain coordinate has zero nulls.
- Existing NGS consumer frames remain non-empty at 5,933 passing / 14,731 receiving / 6,059
  rushing rows.
- Inspection confirmed the matched era replaces both grain and nullable-grain declaration;
  blank normalization precedes the populated-grain check; the daily era permits no null grain
  coordinate. The prior FF and depth all-or-nothing nullability defects are closed.

## Blocking finding — the allow-list still invents an unsupported Boolean dialect

`src/dynasty_genius/nflverse_usage.py:1904-1907` says Python booleans round-trip through this
SQLite TEXT store as `'True'`/`'False'`, then permits those two strings. The premise is false in the
actual pipeline.

Independent outcome probe using the real FTN fixture:

```text
genuine ok [('0', 'text', 235), ('1', 'text', 96)]
source_string_true ok [('0', 'text', 234), ('1', 'text', 96), ('True', 'text', 1)]
```

Genuine Python booleans become exactly SQLite TEXT `'0'`/`'1'`. Replacing one source value with
the string `'True'` is accepted, produces `status=ok`, and publishes as Boolean true. Therefore
`{"True","False"}` is not compatibility for a measured round-trip; it is an unmeasured widening
of the provider dialect. The prose immediately says that nothing beyond what the source provides
may be invented, so the implementation contradicts its own refusal contract.

The falsifier at `tests/contract/test_ingestion_corrective_red.py:388-404` covers several rejected
aliases but deliberately omits uppercase `'True'` and `'False'`, so it cannot catch this widening.

Required closure:

1. Restrict the stored/export Boolean domain and replacement mapping to `{"0", "1"}`.
2. Add source-string `'True'` and `'False'` to the Boolean-specific refusal test.
3. Retain the genuine-Python-boolean positive control; it already proves clean data still exports
   correctly through the measured `'0'`/`'1'` representation.

## Non-blocking documentation correction

`src/dynasty_genius/nflverse_usage.py:949-951` still says `require_populated_grain` is false for
depth charts. The corrected spec sets it true and uses per-era nullable columns. Correct the stale
comment in the same narrow patch so future work does not reinstate the exact mechanism just fixed.
