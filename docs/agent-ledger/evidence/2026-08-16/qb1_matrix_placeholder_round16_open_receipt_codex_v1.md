# QB-1 shared matrix-placeholder Round 16 open receipt — Codex v1

Date: 2026-08-16 ET  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Transition: revision **94 → 95**, terminal `BLOCKED` → ACTIVE `green-review`  
Round: **16**

## Authority

David's exact word:

> approved - open one bounded round per your sanctioned mechanism: claude
> applies the ONE shared placeholder classifier at the matrix weekly records
> exactly per your registration read's boundary (pool and frame untouched
> through matrix entry, near misses fail-closed, all-position team rushing
> totals proven unchanged), and on your explicit clear a fresh rerun fires -
> the registered readout then comes to me for my ruling

## Sanctioned transition

- Transition script:
  `qb1_matrix_placeholder_round16_open_codex_v1.mjs`, SHA-256
  `416dec1fe8bf678360f2a1981724a69e9db86e46d147c5b7df4b0a689750afe3`.
- `node --check` passed.
- Non-mutating dry run pinned revision 94, Round-15 close/review, both
  unresolved blockers, exact opening files, and prospective snapshot.
- One `--apply` invocation persisted revision **95** through `persistRun`'s
  revision-guarded atomic writer.
- Independent post-write recomputation matched the stored open snapshot:
  `a9c212426e55cbcd08a96428c184703d2e273e821fe20406150fbc0f810fb542`.

## Exact four-file scope and opening pins

- `src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py`
  `c00c60ab66781d45cb79d0b122f8c3916167e4f435910385f0b4e7a1d1e74d39`
- `src/dynasty_genius/eval/qb_validation/study_matrix.py`
  `1d2a6296564dac288d50a69db61b6753afb7cd25219de29f8ac442cd04fc64a1`
- `scripts/run_qb1_study.py`
  `8d7d525c1f5da0fa9a7311d0d2fef72353ee63969324d27257cfbcf5c0d87c63`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `a75dbc64b1d90a5d2d505963ad8a8a50990c7834259cbfc30e497c9f14f74d17`

## Bounded implementation contract

1. There is one shared classifier for both label and matrix consumers:
   missing `player_id` AND missing `position` AND validated exact zero across
   all 17 D2 inputs; names are audit evidence only.
2. The admitted pool is unchanged through `build_study_matrix` entry. The
   defensive weekly frame remains unchanged through receipt/source,
   shape, and manifest gates. Classification occurs on defensive weekly
   records immediately before `_validated_weekly_row`.
3. Every near miss remains fail-closed. No missing, malformed, non-finite,
   unproven, negative, boolean, position-bearing, identified, or nonzero row
   is forgiven.
4. Contracts and real-surface proof must establish all-position team rushing
   totals are unchanged, all 192 exact placeholders classify at the matrix
   seam, and the pinned source/frame digests are unchanged.
5. The Round-15 census supports only “one observed next wall.” Its prior
   last-wall claim is not evidence and must not be repeated.

No execution, publication, provider fetch, input mutation, registered-value
change, commit, or push is authorized. The fresh rerun is granted but held
until Codex's explicit independent CLEAR. Any blocker re-parks. H2 QB rushing
remains **UNDER TEST** with no result.
