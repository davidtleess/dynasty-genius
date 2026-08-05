# Streams 2/3 corrective review — Codex v2

Date: 2026-08-05
Target: `7de9357156ac303c43519b26b20eaf1fc1dd8814`
Disposition: **NOT CLEAR**

## Accepted corrections

- Retaining all 47,282 `ff_opportunity` rows is the correct response to the falsified exclusion
  premise. The recovered 2022 Super Bowl row proves that guarding-and-dropping was the wrong design.
- The widened `(game_id, posteam, player_id)` grain is present in both the spec and its era.
- Schema drift confined to a residual row now refuses.
- The coverage fingerprint makes changed collapse evidence invalidate `unchanged`; the transfer
  regression for depth charts passes.
- `min_season` skip semantics are now exercised and match the accepted contract.
- The committed focused corrective/FF/FTN set passed independently: **52 passed**.
- Live last-good run `nflverse-usage-20260805T1259254581500000` is `ok`; FF has 47,282 rows,
  including 3,145 `unknown` residuals, and the existing NGS consumers remain intact.

## Blocking findings

### C1 — the widened FF grain still relies on an unenforced population premise

The source comment says `game_id` and `posteam` never null, then
`require_populated_grain=False` disables the population check for **all three** coordinates
(`7de9357:src/dynasty_genius/nflverse_usage.py:805-818`). That is the same measurement-as-contract
shape the retirement was meant to eliminate.

Reproducer: mutate one real residual row to `posteam=None`. Normalization succeeds with 41 rows and
emits the key:

```text
game_id=2024_01_BAL_KC|posteam=None|player_id=None
```

Required closure: express nullable grain coordinates rather than turning the whole check off. For
FF, only `player_id` may be blank; `game_id` and `posteam` must refuse when blank. The same mechanism
can serve depth charts, whose weekly era permits only `week` to be blank.

### C2 — the Boolean guard checks the result of integer coercion, not the explicit source domain

At `7de9357:src/dynasty_genius/nflverse_usage.py:1870-1877`, the guard first casts text to Int64 and
then checks whether the integer is 0/1. Numeric aliases outside the promised stored domain therefore
survive. End-to-end reproducers:

```text
source is_motion='01' -> status ok -> Boolean true
source is_motion='+1' -> status ok -> Boolean true
```

Non-numeric values such as `'true'` refuse only later under the generic
`nflverse_export_cast_lost_values`, not under the claimed Boolean-domain error. The committed test
at `tests/contract/test_ingestion_corrective_red.py:142-163` asserts only that some
`UsageCaptureError` occurs and does not exercise numeric aliases or the promised named error.

Required closure: validate the exact non-null stored/source Boolean representation before coercion
(`0` or `1`; null allowed), and pin the Boolean-specific error for numeric aliases and non-numeric
text. Prefer source-domain validation before persistence, with the export check retained as defense.

## Non-blocking cleanup

`exclude_unidentified_rows` is unarmed, but the corrective commit leaves that mechanism plus the
new `exclude_requires_zero_columns` field in production with no armed-stream contract. Removing the
retired surface is cleaner; if retained for future use, its constructor must fail closed when the
required guard declaration is empty.

