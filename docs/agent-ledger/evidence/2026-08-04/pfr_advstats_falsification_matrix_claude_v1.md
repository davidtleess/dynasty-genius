# Seeded falsification matrix — PFR advanced stats RED (batch stream 1 of 6)

**RED artifact:** `tests/contract/test_pfr_advstats_ingestion_red.py` (23 tests; 18 fail, 5 pass)
**Fixture:** `tests/fixtures/pfr_advstats_2024_slice.json` — a **real** 2024 slice (two whole games
per stat type, 115 rows), not a synthetic shape.
**Seeded by:** Claude Code (RED author), per `02` §Falsification #1 — *"the RED author seeds the
matrix with initial coverage; the GREEN implementer updates it when implementation reveals new
boundaries; reviewers challenge it."*
**Author's own falsification pass on the RED:** one defect found and fixed before routing — the
consumer-boundary test shelled out to `rg`, which is absent from the pytest environment and from CI.
Rewritten as a pure-Python tree walk deriving its own repo root. This is the machine-bound-probe
class the 2026-07-26 closeout amendment names, caught by running the RED rather than reading it.

## RED status (measured, not predicted)

```
23 collected · 0 collection errors · 18 failed · 5 passed
ruff check src app <this file> → All checks passed
full tree: 4,477 collected, ZERO collection errors
```

*(4,477 is a measurement of THIS tree, not a target. `CLAUDE.md` forbids pinning a count: the
historical 4,335 was measured at `292c582` with three NGS paths untracked, and that tree no longer
exists. The invariant is zero collection errors, and it holds.)*

Every one of the 18 failures names the same cause — `PFR_PASS is not defined in nflverse_usage` —
which is what a RED should look like. The **5 that pass are deliberate**: they verify the measured
basis independently of any implementation (the fixture is real; the three global bridge conflicts
exist; none appears in these rows; unresolved ids stay `source_only`; nothing consumes the stream).

## Matrix

| # | Input class | Probe | Result / expectation | Test |
| --: | :-- | :-- | :-- | :-- |
| 1 | **valid-nominal** | Real 2024 two-game slice per stat type | Ingests; coverage reconciles | `test_coverage_reconciles_and_never_reports_one_reassuring_number` |
| 2 | **contract shape** | Declared columns vs live column set | Exact set equality per type (24/16/17/29) | `test_the_declared_columns_match_the_live_shape_exactly` |
| 3 | **boundary — grain** | `(game_id, pfr_player_id)` declared | Zero-null, zero-dup measured across all four types 2018-2025 | `test_the_declared_grain_is_game_id_and_player_not_season_week_team` |
| 4 | **duplicate / conflict** | Append an exact repeat row at the declared grain | **REFUSE** — never last-wins | `test_a_duplicate_at_the_declared_grain_refuses` |
| 5 | **missing** | Drop `carries` from every rush row | **REFUSE**, naming the column | `test_a_missing_declared_column_refuses_by_name` |
| 6 | **malformed shape — additive** | Add `receiving_air_yards` to every rec row | **REFUSE** (see gap G1 below) | `test_an_additive_provider_column_refuses_rather_than_being_dropped` |
| 7 | **heterogeneous batch** | Extra field on the *last* record only | **REFUSE** — first-row validation is not enough | `test_a_heterogeneous_batch_refuses` |
| 8 | **empty collection** | Loader returns `[]` | Visible as zero rows, not indistinguishable from success | `test_an_empty_loader_result_is_not_silently_a_successful_capture` |
| 9 | **wrong type (API misuse)** | Loader returns a `str` | **FAIL LOUD** — programming error, not a data path | `test_a_wrong_return_type_fails_loud_not_closed` |
| 10 | **numeric edge — non-finite** | `receiving_rat = inf` | Refuse **or** normalize to null; never persist as a number | `test_a_non_finite_metric_is_refused_or_stored_as_null_never_as_a_number` |
| 11 | **identity — conflict** | Resolve every fixture id | **Zero** conflict rows; global bridge ids absent | `test_no_pfr_row_in_this_range_carries_conflict_status`, `test_the_global_bridge_conflicts_exist_but_do_not_appear_here` |
| 12 | **identity — unresolved** | Rows whose PFR id is outside the governed universe | `source_only`, `dg_player_id is None`, never promoted | `test_an_unresolved_player_is_source_only_never_silently_canonical` |
| 13 | **provenance** | Raw snapshot hashing | `raw_sha256` present **and** matching the snapshot bytes | `test_the_raw_snapshot_is_recorded_with_a_sha256_not_only_a_path` |
| 14 | **synthetic failure — capture stage** | `pfr_def` fetch raises mid-run | Prior ready marker **and every referenced file** byte-identical | `test_a_failed_run_leaves_the_prior_ready_marker_and_its_whole_file_set_intact` |
| 15 | **replay determinism** | Normalize the same snapshot twice | Identical rows and identical coverage | `test_recapturing_identical_content_is_deterministic` |
| 16 | **export typing** | `season`/`week` and every metric column | Integers/floats, never `Utf8` (E1 regression) | `test_season_and_week_are_typed_as_integers_not_floats`, `test_every_measured_metric_column_is_typed` |
| 17 | **loader-kwarg trap** | `stat_type` per spec | Pinned explicitly — the loader defaults it | `test_each_stream_declares_its_stat_type_explicitly` |
| 18 | **cross-component / boundary** | Tree scan of `src`, `scripts`, `app` | No consumer outside the adapter; `substrate_only` holds | `test_landing_pfr_adds_no_engine_consumer` |
| 19 | **fixture integrity** | Real games, real ids, measured column counts | Fixture must not agree only with itself | `test_the_fixture_is_a_real_pfr_capture_not_a_synthetic_shape` |

## Rows OUT OF SCOPE for this stream — named with owner and boundary, never by omission

`02` §Falsification #1 permits an out-of-scope row **only** with an explicit owner and contract
boundary. These belong to later streams in the same batch and are listed so the batch-level review
can see they are deferred deliberately:

| Row | Owner (stream) | Boundary |
| :-- | :-- | :-- |
| Seasonless loader API misuse | `contracts`, `ff_rankings` | Needs the C5 capture/effective-date axis; PFR is season-keyed and unaffected |
| Nested serialization failure | `contracts` | Only `contracts` carries a `List(Struct(...))` column |
| Invalid identity-mode combinations | `ftn_charting` | Only FTN needs the C7 identity-applicability mode; PFR resolves normally via the PFR bridge |
| Market destination crossed into an Engine A/B consumer | `ff_rankings` | PFR is not market data; the negative-consumer gate lands with the rankings stream |
| Exact-duplicate vs conflicting-duplicate classes | `contracts` | PFR has **zero** duplicates at its declared grain; contracts has 2,513 exact-duplicate groups |
| Two-era grain resolution | `depth_charts` | PFR has identical column counts in every season 2018-2025 — no eras |

## Known gaps this RED deliberately exposes (they are why it is RED)

**G1 — the additive-column invariant does not exist on the path PFR uses.** Verified at
`nflverse_usage.py:571`: exact column-set equality runs **only** when `spec.eras` is non-empty. A
non-era spec checks for *missing* columns at `:618` and then projects the declared ones, so a NEW
upstream field is accepted and silently discarded. PFR has no eras, so matrix row 6 fails by design.
GREEN must either give each PFR spec an exact era or extend the invariant deliberately — **and the
test must exercise both paths**, per Codex C9.

**G2 — raw provenance is a path, not a hash.** `write_raw_snapshot` returns a path (`:1070-1098`) and
the capture result records only that path (`:1541-1548`). The reduced per-stream gate requires
"raw snapshot **+ manifest/hash**", so matrix row 13 fails by design. This is the small mechanism
extension Codex C6 named, and it is a **batch-wide** prerequisite: no stream in block C can satisfy
the ratified gate until it lands.

## What this RED does NOT claim

No predictive value for PFR advanced stats. No consumer. No model or feature use. `substrate_only`,
with the decision owner and the separate use gate recorded in disposition v2 §2. Landing this stream
does not move Engine A or Engine B, and **completing Layer 1 will not produce edge** — the honest
headline stays *"fuel landed, none of it burning yet."*
