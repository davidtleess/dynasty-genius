# Seeded falsification matrix v2 — PFR advanced stats RED (batch stream 1 of 6)

**Supersedes** `pfr_advstats_falsification_matrix_claude_v1.md`, which Codex S7 correctly called
**wholly stale**: it still advertised 23 tests / 18 failures / 5 passes, "two whole games per stat
type", declaration-only export typing, capture-stage failure only, and the retired empty /
wrong-type / non-finite semantics. **That was the worst defect of the round.** The matrix is the
durable falsification surface the GREEN implementer works from, so a stale matrix silently
reinstates the exact contracts the revised RED had just rejected. v1 is retained for audit and
must not be worked from.

**RED:** `tests/contract/test_pfr_advstats_ingestion_red.py`
**Generator:** `build_pfr_fixture_claude_v1.py` (`--check` covers fixture, manifest, injury seed,
injury manifest)
**Fixtures:** `pfr_advstats_2024_slice.json` (+ manifest) · `nflverse_injuries_2024_seed.json`
(+ manifest)

## Measured state

```
focused RED : 31 collected · 22 failed · 9 passed
full tree   : 4,485 collected · ZERO collection errors
ruff        : src app <test> <generator> -> All checks passed
generator   : --check -> ALL ARTIFACTS MATCH SOURCE (exit 0)
nflreadpy   : 0.1.5 (now recorded in both manifests)
```

Counts are measurements of THIS tree, never targets — `CLAUDE.md` forbids pinning one. The
invariant is zero collection errors.

## Provenance of the fixtures

| Artifact | Rows | Upstream rows | Selection rule |
| :-- | --: | --: | :-- |
| `pfr_pass` | 4 | 697 | two lowest `game_id`s |
| `pfr_rush` | 16 | 2,359 | two lowest `game_id`s |
| `pfr_rec` | 35 | 4,453 | two lowest `game_id`s **+ 1 appended row from `2024_02_CIN_KC`** |
| `pfr_def` | 60 | 7,992 | two lowest `game_id`s **+ 1 appended row from `2024_01_PIT_ATL`** |
| injuries seed | 10 | 6,215 | every row of week 1 for ARI, ATL |

The appended rows exist so the unresolved-identity path is always exercised; `pfr_pass` and
`pfr_rush` have no unresolved 2024 rows, so they are exactly two games. **Every manifest carries the
upstream sha256 and the nflreadpy version**, so "the fixture is real" is checkable rather than
asserted.

## Matrix — 22 RED rows (fail by design)

| # | Input class | Probe | Expectation | Test |
| --: | :-- | :-- | :-- | :-- |
| 1 | valid-nominal | Real 2024 slice, four types | Coverage reconciles on governed keys | `test_coverage_uses_the_governed_vocabulary_and_reconciles` |
| 2 | registration | `build_streams()` default path | All four registered **exactly once**, each bound to `nflreadpy.load_pfr_advstats` | `test_the_default_build_streams_registers_all_four_exactly_once` |
| 3 | registration | Four specs declared | Four distinct names, four distinct tables | `test_four_streams_are_declared_one_per_stat_type` |
| 4 | loader-kwarg trap | `stat_type` per spec | Pinned explicitly — the loader defaults it | `test_each_stream_declares_its_stat_type_explicitly` |
| 5 | contract shape | Declared vs independently pinned columns | Exact set equality (24/16/17/29) | `test_declared_columns_match_the_independently_pinned_live_shape` |
| 6 | grain | `(game_id, pfr_player_id)` | Declared; measured zero-null, zero-dup | `test_the_declared_grain_is_game_id_and_player` |
| 7 | identity wiring | `identity_column`/`identity_kind` | `pfr_player_id` / `pfr` | `test_identity_is_the_pfr_bridge_not_a_gsis_assumption` |
| 8 | typing (declared) | `season`, `week` | Declared integers | `test_season_and_week_are_declared_as_integers` |
| 9 | typing (declared) | Every metric column | Declared int or float | `test_every_metric_column_is_declared_with_a_type` |
| 10 | typing (**emitted**) | Read the four published Parquets | Runtime `Int64`/`Float64`, **plus exact non-null count reconciliation vs source, every numeric column** | `test_the_emitted_parquet_is_typed_at_runtime_not_merely_declared` |
| 11 | duplicate | Append an exact repeat at the grain | REFUSE — never last-wins | `test_a_duplicate_at_the_declared_grain_refuses` |
| 12 | missing | Drop `carries` from every rush row | REFUSE, naming the column | `test_a_missing_declared_column_refuses_by_name` |
| 13 | malformed — additive | Add `receiving_air_yards` | REFUSE (gap **G1**) | `test_an_additive_provider_column_refuses_rather_than_being_dropped` |
| 14 | heterogeneous | Extra field on the LAST record only | REFUSE | `test_a_heterogeneous_batch_refuses` |
| 15 | empty collection | Loader returns `[]` | **Succeeds** with `status == "ok"`, explicit zero per stream, all governed keys incl. the derived count | `test_an_empty_loader_result_records_an_explicit_zero_per_stream` |
| 16 | wrong type | `["not a mapping", 42]` | `UsageCaptureError` matching `record` | `test_a_wrong_record_type_refuses_with_the_defined_boundary_error` |
| 17 | numeric edge | `inf`, `-inf`, `nan` | **REFUSE** (single-valued; see below) | `test_a_non_finite_metric_refuses` |
| 18 | provenance | Raw snapshot hashing | `raw_sha256` present **and** matching the bytes (gap **G2**) | `test_the_raw_snapshot_is_recorded_with_a_sha256_not_only_a_path` |
| 19 | existing-table gate | Seed **all five** live tables, land PFR | Row count **and** content hash unchanged per table; seed asserted non-empty first | `test_landing_pfr_leaves_all_five_existing_tables_byte_identical` |
| 20 | synthetic failure — capture stage | `pfr_def` fetch raises | Prior marker + every referenced file byte-identical | `test_a_capture_stage_failure_preserves_the_prior_ready_marker_and_files` |
| 21 | synthetic failure — **export stage** | Fail the **2nd** `write_parquet` **inside the real publisher** | Partial run dir exists, yet prior marker + files byte-identical; asserts the failure genuinely reached a 2nd write | `test_an_export_stage_failure_preserves_the_prior_ready_marker_and_files` |
| 22 | replay | Normalize the same snapshot twice | Identical rows and coverage | `test_normalization_is_deterministic_on_replay` |

## The 9 GREEN rows — measured basis, independent of the implementation

None is vacuous; each would fail on a real change.

| Probe | Test |
| :-- | :-- |
| Fixture provenance: upstream rows, sha256, column counts, manifest/fixture agreement | `test_the_fixture_carries_generator_provenance_not_just_self_agreement` |
| Selection rule asserted, **including the appended rows** | `test_the_slice_selection_rule_is_recorded_including_the_appended_rows` |
| Rows are real games and real ids | `test_the_fixture_rows_are_real_not_synthetic` |
| Five existing streams each registered **exactly once** (counted, not set-membership) | `test_the_default_registration_does_not_displace_the_existing_streams` |
| Independent column pin agrees with the committed fixture | `test_the_pinned_shape_still_matches_the_committed_fixture` |
| Zero conflict rows in range | `test_no_pfr_row_in_this_range_carries_conflict_status` |
| Three global bridge conflicts exist but appear in no PFR row | `test_the_global_bridge_conflicts_exist_but_do_not_appear_here` |
| Unresolved ids stay `source_only`, never promoted | `test_an_unresolved_player_is_source_only_never_silently_canonical` |
| No consumer anywhere outside the exact adapter | `test_landing_pfr_adds_no_engine_consumer` |

**Positive control on the consumer scanner** (a scan finding nothing is indistinguishable from a
broken scan): substituting `load_nextgen_stats` / `load_snap_counts` returns **five** non-adapter
files — `outcome_forward_capture_store.py`, `run_realized_outcome_scoring.py`,
`generate_qb_role_occupancy_labels.py`, `assemble_engine_b_dataset.py`, `run_feature_refresh.py`.
*(I earlier reported **six** by counting `nflverse_usage.py`, which the test exempts. Codex's
counterprobe found five. Corrected: in the test's own terms the control yields five.)*

## Single-valued semantics chosen where v1 forked

| Question | v1 | v2 — chosen |
| :-- | :-- | :-- |
| Non-finite metric | refuse **or** null (unfalsifiable) | **REFUSE.** The export already refuses loss of non-null values (`:1223-1247`); nulling an `inf` would contradict it and needs its own loss accounting and authority |
| Empty capture | tautological | **Succeeds**, `status == "ok"`, explicit zero per stream + derived count |
| Wrong type | any of three exceptions | `UsageCaptureError` matching `record` |

## Rows out of scope — owner and boundary named, never omitted

| Row | Owner | Boundary |
| :-- | :-- | :-- |
| Seasonless loader API misuse | `contracts`, `ff_rankings` | Needs the C5 capture/effective-date axis; PFR is season-keyed |
| Nested serialization | `contracts` | Only contracts carries `List(Struct(...))` |
| Invalid identity-mode combinations | `ftn_charting` | Only FTN needs the C7 applicability mode |
| Market destination → Engine A/B consumer | `ff_rankings` | PFR is not market data |
| Exact vs conflicting duplicate classes | `contracts` | PFR has **zero** duplicates at its grain; contracts has 2,513 exact-duplicate groups |
| Two-era grain resolution | `depth_charts` | PFR column counts are identical 2018-2025 — no eras |

## Gaps the RED exists to expose

**G1** — the additive-column invariant does not exist on the non-era path (`:571` gates exact
equality on `if spec.eras:`; `:618` checks only missing columns). PFR has no eras. GREEN must give
each spec an exact era **or** extend the invariant, and must exercise **both** paths.

**G2** — raw provenance records a path, not a hash (`:1070-1098`, `:1541-1548`). **Batch-wide:** no
block-C stream can meet the ratified reduced gate until it lands.

## What this RED does not claim

No predictive value. No consumer, model use, scheduler, commit, push, merge, or batch landing.
`substrate_only`, owner and use-gate recorded in disposition v2 §2. Completing Layer 1 will not
produce edge — *"fuel landed, none of it burning yet."* **H2 QB rushing remains a registered
hypothesis UNDER TEST with no result.**
