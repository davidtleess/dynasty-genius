# QB-1 exclusion-row registration read — Codex v1

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 125  
Diagnostic script: `d83f5be183917e75f8e8d83f184d1e564c309d53445847941b926d7997f4550e`  
Diagnostic output: `37d935dd4c8d372931ad92639045b7da6b392b3a7f74c5b48c11ce45b771ce61`  
Classification: **IMPLEMENTATION, not amendment — only at the terminal-report adapter boundary**

## Independent evidence read

The diagnostic stayed within the revision-125 boundary. Codex reproduced both
evidence hashes, audited the projection code, read the complete projection,
and independently matched all 33 current code/input/artifact digests to the
diagnostic map with zero mismatches.

Measured facts:

- one composition replay; one intercept; abort before the validator returned;
- 14 comparison rows, all with list-shaped `excluded_folds`;
- c01–c10 have no exclusion entries;
- c11–c14 each have three entries, for registered seasons 2021–2023;
- all 12 entries have valid mapping shape, valid season, non-empty reasons,
  and exactly one failed conjunct: `reason_word_outside_vocabulary`;
- all 12 reason tuples are exactly
  `empty_common_pool`, `fold_starved`, `degenerate_input`; only
  `empty_common_pool` is outside the publication vocabulary;
- the 33 before/after digests are identical.

No additional data measurement is required to classify this seam.

## Registration authority

The frozen registration does not register `empty_common_pool` as a terminal
fold flag. It does register the applicable terminal semantics:

- `fold_floors.below_min_n_flag` is literally `fold_starved`;
- `fold_min_evaluable_n` is 20, so a zero common pool is necessarily below
  that registered floor;
- §7 says a fold below 20 emits `fold_starved`, and degenerate inputs emit
  named degenerate states;
- the H5 join failure states separately name `join_reconciliation_failed`,
  `join_coverage_low`, and `identity_join_empty`.

The internal comparison/inference layer intentionally carries a richer,
lossless reason. `score_comparisons` emits `empty_common_pool` when the exact
pair intersection is empty, and the inference contracts explicitly require
that word to survive in the internal `pool_paired_deltas` exclusion record.
That internal fact is useful and must not be erased.

The defect is therefore the missing translation between two legitimate
surfaces: the internal inference record and the frozen terminal report. The
report adapter currently copies `pooled.excluded_folds` verbatim into the
terminal comparison row. Mapping the internal zero-pool detail onto its
already-co-occurring registered terminal state `fold_starved` changes no
registered threshold, cohort, fold, contrast, metric, inference value,
status, or claim. It is implementation alignment.

Adding `empty_common_pool` to `_FOLD_FLAG_VOCABULARY` is **not authorized** by
this read: that would widen the frozen terminal vocabulary with a word absent
from the registration. Removing `empty_common_pool` from the internal
comparison/inference producer is also out of scope: it would break the
lossless internal diagnostic contract and its existing tests.

## Bounded Round-20 implementation

Exact product/test scope:

1. `scripts/run_qb1_study.py`
2. `tests/contract/test_qb1_green_correction_contracts.py`

No change is authorized to the registration, `execution.py` publication
vocabulary/gate, `comparisons.py`, `inference.py`, status logic, data inputs,
or any metric-producing code.

The implementation belongs at `contrast_status`'s terminal-report adaptation
seam, preferably through one small helper. Its closed behavior:

1. Preserve `None` and empty exclusion collections exactly.
2. Preserve entry order, `test_season`, `decision_supported`, and every
   registered reason word.
3. Remove only the exact internal word `empty_common_pool`, and only when that
   same entry also carries `fold_starved`. This is the registered implication
   `common_pool_n == 0` → `common_pool_n < 20` without reading or serializing
   the count.
4. Refuse `report_schema_invalid` if `empty_common_pool` appears without
   `fold_starved`, appears more than once, or sits in an unreadable entry /
   reasons shape. Never silently generalize.
5. Preserve every other unknown word unchanged so the existing publication
   gate still rejects schema drift. Do not implement a generic allow-list
   filter in the producer.
6. Leave the internal inference output byte-for-byte semantically unchanged;
   only the terminal comparison row is canonicalized.

## Required RED and proof matrix

RED before product code must cover:

- the measured H5 shape maps
  `[empty_common_pool, fold_starved, degenerate_input]` to
  `[fold_starved, degenerate_input]` and passes the unchanged gate;
- all 12 measured entry positions across c11–c14 / 2021–2023 canonicalize;
- `empty_common_pool` without `fold_starved` refuses by name;
- duplicate `empty_common_pool` refuses by name;
- an unrelated unknown reason is not stripped and the unchanged gate rejects
  it;
- registered reason order and entry metadata are preserved;
- `None` and empty exclusions are unchanged;
- `pool_paired_deltas` still carries `empty_common_pool` losslessly;
- terminal comparison metrics, uncertainty fields, statuses, and
  `decision_supported` are unchanged aside from the exact reasons projection.

Verification requires the focused correction contract, the five-file QB-1
bundle, scoped Ruff and strict compile, and an end-to-end synthetic terminal
publication probe.

One final read-only real-surface composition projection is allowed after GREEN,
outside the registered runner and under the same metric-free projection law as
revision 125. It must prove the 14 terminal comparison rows contain only the
unchanged publication vocabulary and that the 12 measured entries now satisfy
the exclusion-row clause; it aborts at the validator seam and persists no
metric or payload content. Before/after digests are mandatory.

No registered runner, terminal artifact write, registered rerun, provider
fetch, input mutation, registration change, implementation outside the two
files, commit, or push. A fresh registered rerun remains held until Round 20
closes with Codex's explicit CLEAR. Any completed readout returns untouched to
David for his separate ruling.

H2 QB rushing remains **UNDER TEST with no result**.
