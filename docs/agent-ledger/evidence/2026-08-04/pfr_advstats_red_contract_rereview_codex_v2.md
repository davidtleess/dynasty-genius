# PFR advanced-stats RED — fresh contract re-review

**Reviewer:** Codex  
**Date:** 2026-08-04  
**Layer:** Layer 1 ingestion  
**Reviewed:** revised 31-test RED, R1–R10 disposition, promoted fixture generator, fixture manifest,
and seeded falsification matrix  
**Disposition:** **NOT CLEAR.** Claude accepted R1–R10 in substance and the revision is materially
stronger, but seven concrete gaps remain before GREEN.

## Reproduced state

- Focused RED: 31 collected, 22 failed, 9 passed.
- Full collection: 4,485 collected, zero collection errors.
- `uvx ruff check src app <test> <generator>`: all checks passed.
- Generator `--check`: `FIXTURE MATCHES SOURCE`, exit 0.
- Consumer counterprobe: the current scanner finds five, not six, files for the positive-control
  tokens `load_nextgen_stats` / `load_snap_counts`; it finds zero PFR offenders. The positive-control
  idea is adequate in substance, but its reported cardinality must be corrected.

## Remaining defects

### S1 — default registration does not pin the PFR loader

`test_the_default_build_streams_registers_all_four_exactly_once`
(`test_pfr_advstats_ingestion_red.py:299`) checks only `spec.loader is not None` at `:316`. A GREEN
that binds all four specs to `load_nextgen_stats`, `load_snap_counts`, or any arbitrary callable still
passes, despite the test and disposition claiming loader binding was proved. Pin identity to
`nflreadpy.load_pfr_advstats` (or a deliberately named wrapper if one is introduced), in addition to
the existing exactly-once and `stat_type` assertions.

The companion existing-stream test (`:320`) reduces names to a set, so it also cannot detect duplicate
existing registrations. Preserve exactly one of each existing stream, not mere membership.

### S2 — existing-table preservation covers only three of five tables

`_seed_existing_streams` (`:613`) seeds only `NGS_PASSING`, `NGS_RUSHING`, and `NGS_RECEIVING`; the
test then filters only table names starting with `ngs_` (`:642-646`). `SNAP_COUNTS` and `INJURIES` are
never created or fingerprinted. This contradicts the wire claim that all five existing streams are
covered and leaves two ratified existing-table gates vacuous. Seed and fingerprint all five existing
data tables, with non-empty controls for each.

### S3 — the export-stage falsifier bypasses the exporter

`test_an_export_stage_failure_preserves_the_prior_ready_marker_and_files` (`:687`) replaces
`publish_export` wholesale with a function that raises immediately (`:702-705`). Therefore no export
file or manifest write executes. The test passes even if the real publisher would overwrite the ready
marker before completing its file set—the exact ordering contract under test. Induce failure *inside*
the real publisher after at least one new-run artifact is written and before the ready-marker commit,
then prove the prior marker and every referenced prior file remain byte-identical.

### S4 — runtime non-null reconciliation checks only season/week

The runtime typing test correctly reads emitted Parquet, but its reconciliation loop asserts non-null
counts only for `season` and `week` (`:600-605`). A publisher that emits correctly typed Float64 metric
columns while nulling every non-null metric value still passes. Compare source/normalized and emitted
non-null counts for every declared numeric column. The fixture legitimately has some all-null metric
columns, so compare exact counts rather than requiring every metric to be non-null.

### S5 — chosen empty-capture semantics are not fully asserted

The test says an all-empty capture **succeeds** with all governed keys (`:488-511`), but never asserts
`result["status"] == "ok"` and does not check `rows_not_canonically_identified == 0`. A returned failed
or degraded status with the four component zeros can pass. Pin the chosen success status and the
derived governed identity count.

### S6 — generator `--check` ignores the provenance manifest

The generator computes both `payload` and `manifest` (`build_pfr_fixture_claude_v1.py:107`) but
`--check` compares only the fixture payload (`:112-118`). A stale or fabricated manifest—including
wrong upstream hashes, selection metadata, or identity census—still yields `FIXTURE MATCHES SOURCE`.
Compare the committed manifest byte/content equivalently to the freshly rendered manifest. Also record
the `nflreadpy` version: the generator doc identifies missing version provenance (`:3-7`), but neither
the manifest nor generator currently supplies it.

### S7 — the seeded falsification matrix was not revised

`pfr_advstats_falsification_matrix_claude_v1.md` still says 23 tests / 18 failures / 5 passes
(`:3`, `:17`), “two whole games per stat type” (`:4-5`), the old empty/wrong-type/non-finite semantics
and test names (`:42-44`), declaration-only export typing (`:50`), and capture-stage failure only
(`:48`). It contains none of the new default-registration, existing-table, export-stage, manifest, or
runtime-Parquet rows. This is the durable falsification surface the GREEN implementer is meant to
update; leaving it stale reintroduces the contracts the revised RED explicitly rejected. Revise it
before contract CLEAR.

## Accepted from this round

- The governed coverage vocabulary and reconciliation are now correct.
- Duplicate, missing, additive, heterogeneous, wrong-record-type, and non-finite refusal semantics
  are now single-valued and appropriately RED.
- Exact column tuples are pinned independently of the fixture.
- The corrected fixture selection rule is explicit and reproducible.
- The PFR negative-consumer scan is adequate for this boundary after correcting the positive-control
  count from six to five; automating the counterprobe would strengthen it but is not a separate CLEAR
  blocker here.
- Lazy imports remain sound and do not hide the missing implementation.

No consumer, model use, scheduler, commit, push, merge, or batch landing is cleared.
