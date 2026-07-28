# TW28-IDENTITY-10 — Units A/B/D RED contract and falsification matrix v1

**RED author:** Codex  
**Date:** 2026-07-28  
**Authority:** David's verbatim word, `"split it"`  
**Test artifact:** `tests/contract/test_identity_crosswalk_hardening_red.py`  
**Test SHA-256:** `1b75f20b87675ac7ad8f50d6227557ce4e30b13f6e940285383dd400fa50ba6c`  
**RED result:** **18 failed · 1 passed**  
**Sibling regression slice:** **22 passed**  
**Ruff:** clean

## Split boundary

This contract covers only:

- **Unit A:** missing, corrupt, empty-output, or conflicting identity input fails
  closed before runtime publication.
- **Unit B:** the Phase-17.2 coverage artifact carries deterministic Engine-B
  identity-join accounting.
- **Unit D:** the exact production dependency is tracked, present, and byte-pinned.

It contains no API or frontend copy, no player-row targeting, no name matching, no
I-5 bridge, no sentinel filtering, no canonical-key work, no Compliance Audit work,
and no DG2-S0-01 work. Unit C remains a separate challenged thread and cannot share
this commit.

## Contract-conformance surface

1. `_load_ff_playerids` raises a named `ValueError` on:
   - missing path: `ff_playerids_crosswalk_missing`;
   - invalid JSON: `ff_playerids_crosswalk_invalid_json`;
   - non-object root: `ff_playerids_payload_not_object`;
   - absent/non-list `entries`: `ff_playerids_entries_not_list`;
   - non-object entry: `ff_playerids_entry_not_object`;
   - non-string, non-null `gsis_id` or `sleeper_id`:
     `ff_playerids_identifier_wrong_type`;
   - conflicting GSIS→Sleeper:
     `ff_playerids_conflicting_gsis_mapping`;
   - conflicting Sleeper→GSIS:
     `ff_playerids_conflicting_sleeper_mapping`.
2. JSON-null identifiers remain absent. They are never stringified to `"None"`.
3. Parsed-object-identical crosswalk entries are tolerated and counted. “Identical”
   means Python mapping equality after JSON parsing, not serialized-slice identity.
4. Engine-B prediction accounting is emitted at
   `coverage.engine_b_identity_join` with:
   - `prediction_count`;
   - `join_success_count`;
   - `orphan_count`;
   - `orphan_records`;
   - `crosswalk_duplicate_count`;
   - `prediction_duplicate_count`.
5. Every orphan record has exactly the available descriptive join-side facts:
   `gsis_id`, `name`, `position`, and a machine reason. A missing value is JSON null,
   never a fabricated athlete fact. Records sort by `gsis_id` ascending, and
   `orphan_count == len(orphan_records)`.
6. A successful zero-orphan run still emits an empty accounting block.
7. An empty prediction collection raises `engine_b_predictions_empty`.
8. A nonempty prediction collection with zero successful joins raises
   `engine_b_identity_join_zero_success`.
9. Parsed-object-identical prediction rows are tolerated and counted once; conflicting
   repeated predictions for one GSIS raise `engine_b_prediction_conflict`. The old
   `seen_sleepers` silent skip is not an acceptable terminal state.
10. The scheduled refresh converts the producer exception into the governed report:
    `status=aborted`, `aborted_stage=refresh`, named `aborted_reason`,
    `decision_supported=False`; the prior runtime PVO, coverage, and ready marker stay
    byte-identical.
11. `FF_PLAYERIDS_PATH` still resolves exactly to
    `app/data/identity/_runs/ff_playerids_20260516.json`; that file is tracked,
    present, and hashes to
    `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
    Other `_runs/` files remain ignored. The contract chooses the invariant, not a
    particular `.gitignore` implementation.

## Deliberately unresolved coverage boundary

The RED tests **zero** successful joins because David's split rationale explicitly
names the empty-board publication risk. It does **not** encode the framing's proposed
“502 of 503 publishes” behavior or any other partial-coverage threshold.

`>=1` is itself a 1/503 threshold, and the constitution requires low-coverage inputs
to block, report unavailable, or widen uncertainty. The exact partial-coverage floor
remains a David-owned policy question. GREEN must not add a numeric threshold or
claim that one does not exist.

## Falsification matrix

| Input class | RED probe | Current result | GREEN requirement / boundary |
| :-- | :-- | :-- | :-- |
| Valid nominal | one prediction, one mapping | fails: accounting block absent | join=1, orphan=0, empty records present |
| Boundary | one joined + two orphans | fails: accounting block absent | publishes candidate with complete sorted accounting |
| Zero boundary | predictions exist, zero join | fails: publishes | named fail-closed error |
| Partial low coverage | 1..502 joins of 503 | not encoded | **out of scope pending David; owner David** |
| Missing | crosswalk path absent | fails: refresh reports success | abort report + prior runtime byte-preserved |
| Missing field | root lacks `entries` | fails: treated as empty | named shape failure |
| Null / None | both ids JSON null | passes | remain absent; never `"None"` |
| Wrong type | integer GSIS, boolean Sleeper | fails: coerced/ignored | named type failure |
| Malformed syntax | invalid JSON | fails with raw parser text | named invalid-JSON failure |
| Malformed shape | root list, entries object, scalar row | fails silently or generically | distinct named shape failures |
| Duplicate identical | equal parsed crosswalk objects | fails: duplicate uncounted | tolerate + count |
| Duplicate conflict | conflicting bidirectional mappings | fails: last-write-wins | fail closed with directional reason |
| Prediction duplicate | equal and conflicting repeated GSIS rows | fails: silent `seen_sleepers` skip | equal count/tolerate; conflict abort |
| Empty collection | zero predictions | fails: publishes | named empty-prediction abort |
| Cross-component | producer failure through runtime publisher | fails: publication succeeds | governed abort report; prior pair+marker unchanged |
| Production-state positive control | real frozen path/hash | hash and presence pass; tracking fails | exact loader dependency tracked; siblings ignored |
| Numeric / non-finite | N/A | N/A | IDs and counts only; no numeric model value is validated here |
| API misuse | non-Path internal call | not encoded | out of scope: typed internal API; ordinary Python failure is acceptable |
| Synthetic / override | temp snapshot, crosswalk, predictions | exercised | fixtures do not touch production artifacts |

## Attribution evidence

Focused RED:

```text
FFFFFFFFFF.FFFFFFFF
18 failed, 1 passed
```

The failures are attributable to current production behavior:

- missing crosswalk returns empty maps;
- malformed structures are accepted, coerced, or raise unnamed incidental errors;
- dict comprehensions overwrite conflicting mappings;
- `seen_sleepers` silently skips;
- coverage has no Engine-B identity-join block;
- empty and zero-join output publishes;
- the exact file is present and hash-correct but absent from `git ls-files`.

Existing sibling contract surface:

```text
tests/contract/test_pvo_refresh_runner.py
tests/test_phase17_universe_pvo_batch.py
22 passed
```

No production script, refresh, model training, frontend test, or Unit C test was run.
H2 QB rushing is unrelated and remains **UNDER TEST**.
