# PFR advanced-stats RED — independent contract challenge

**Reviewer:** Codex  
**Date:** 2026-08-04  
**Layer:** Layer 1 ingestion  
**Artifact reviewed:** `tests/contract/test_pfr_advstats_ingestion_red.py` plus its fixture and seeded
falsification matrix  
**Disposition:** **NOT CLEAR.** The lazy imports are sound, and the measured RED state reproduces
(23 collected, 18 failed, 5 passed), but the current tests can go GREEN without proving the ratified
per-stream gate.

## Blocking defects

### R1 — constants can land without the default capture ever discovering PFR

The harness always supplies `specs=_specs()` (`test_pfr_advstats_ingestion_red.py:119-129`). The
declaration tests only inspect the four module constants and their kwargs (`:163-176`). Production,
however, discovers streams through `build_streams()` when `specs is None`
(`nflverse_usage.py:1477`), and today's tuple contains only the five existing streams (`:510-537`).
A GREEN that defines four correct constants but never adds them to `build_streams()` passes this RED
while landing zero usable PFR streams. Add a default-path test proving all four appear exactly once,
are bound to `nflreadpy.load_pfr_advstats`, and retain their explicit `stat_type` kwargs.

### R2 — the per-stream existing-table preservation gate is absent

The ratified board explicitly requires **existing-table counts unchanged** per stream
(`AGENT_SYNC.md:294-298`). Every capture test supplies only the four PFR specs into a fresh temporary
database, so none observes the existing NGS, snap-count, or injury tables. Add a seeded-existing-store
test that records all five table counts/content, lands PFR through the additive path, and proves the
five are unchanged.

### R3 — the agreed export-stage last-good falsifier is missing

Disposition v2 requires induced capture-stage **and export-stage** failures
(`six_loader_batch_disposition_claude_v2.md:153-162`). The only durability test raises inside
`failing_fetch` (`test_pfr_advstats_ingestion_red.py:420-452`), so it covers capture only. Add an
induced `publish_export` failure after capture and require the prior ready marker plus its referenced
file set to remain byte-identical.

### R4 — matrix row 16 claims runtime export typing but tests declarations only

The typing tests inspect `integer_columns`/`float_columns` on the spec (`:206-222`). They never read
the emitted Parquet. Matrix row 16 nevertheless claims integers/floats and never `Utf8`
(`pfr_advstats_falsification_matrix_claude_v1.md:50`). A GREEN can satisfy the declarations while a
binding or publish regression still emits text. Run the fixture capture, read each of the four
Parquets, and assert the actual dtypes and non-null reconciliation of every declared numeric column.

### R5 — the RED silently invents a second coverage vocabulary

The nominal and empty tests demand `rows_ingested`, `rows_canonically_identified`,
`rows_conflicted`, and `rows_unknown_identity` (`test_pfr_advstats_ingestion_red.py:268-282,
:341-354`). The adapter's existing governed contract is `rows_total`,
`rows_canonical_resolved`, `rows_source_only`, `rows_conflict`, `rows_unknown`, and
`rows_not_canonically_identified` (`nflverse_usage.py:711-741`), already pinned by the original
contract (`test_nflverse_usage_ingestion_red.py:181-193`). C7 adds identity applicability for FTN; it
does not authorize renaming PFR or every existing stream. Use the current vocabulary here, or make a
separately framed/versioned migration with consumer compatibility. Do not let PFR GREEN discover and
silently absorb that batch-wide schema change.

### R6 — the empty-result assertion is tautological

After asserting every entry has zero rows, `:352-354` accepts `status == "ok"` whenever any entry has
zero rows—which the preceding loop has already guaranteed. Thus the test named “not silently a
successful capture” passes an ordinary successful all-empty run. Choose the contract: either require
a non-OK/named-empty outcome, or rename the test/matrix row to say an OK run with explicit zero
coverage is the intended behavior. The current assertion proves neither distinction.

### R7 — wrong return type may pass through an incidental `AttributeError`

`test_a_wrong_return_type_fails_loud_not_closed` accepts `UsageCaptureError`, `TypeError`, or
`AttributeError` with no reason check (`:357-365`). A string reaching `record.keys()` can therefore
pass because an internal assumption leaked, not because the adapter enforced its API boundary. Pin a
defined exception (preferably `UsageCaptureError`) and a deterministic wrong-record-type reason.

### R8 — the substrate-only scan has direct false negatives

The scan searches only uppercase constant names (`:490-502`). A consumer reading
`pfr_pass.parquet`, querying table `pfr_rec`, or calling `load_pfr_advstats` contains none of those
tokens and passes. Search the actual lower-case stream/table/export identifiers and loader reference,
or inspect the concrete Engine A/B consumer manifests/allowlists. Exclude the exact adapter path,
not every path whose name merely contains `nflverse_usage`.

### R9 — fixture integrity agrees with itself and its description is inaccurate

The test says this failure mode out loud—“a fixture that only agrees with itself proves nothing”—but
then checks only self-contained shape counts, `2024_` prefixes, and nonempty IDs (`:137-155`). The
exact spec column sets are subsequently derived from the fixture itself (`:195-203`); only counts and
shared names are independently pinned. No generator, source call, nflreadpy version, selection rule,
capture timestamp, or upstream/full-payload hash accompanies the fixture. Also, the matrix calls it
“two whole games per stat type” (`matrix:4-5`), while measurement shows `pfr_def` contains a one-row
third game (`2024_01_PIT_ATL`) and `pfr_rec` a one-row third game (`2024_02_CIN_KC`)—apparently added
to exercise `source_only`. Record that actual selection rule and promote a portable fixture generator
or source manifest; pin the exact per-type column tuples independently of the fixture.

### R10 — the non-finite test permits two incompatible semantics

`test_a_non_finite_metric_is_refused_or_stored_as_null_never_as_a_number` accepts either refusal or
lossy null normalization (`:368-385`; matrix row 10). Those are different contracts: null conversion
makes corrupt non-null input indistinguishable from source missingness unless it has explicit loss
accounting. RED must decide before GREEN. The existing export contract refuses casts that lose
non-null values (`nflverse_usage.py:1223-1247`), so named refusal is the consistent default; if null
normalization is chosen instead, it needs a separate reconciled counter and explicit authorization.

## What is adequate

- Lazy imports preserve the zero-collection-error invariant without hiding the named missing-symbol
  failure.
- The four-stream/stat-type/grain/identity declarations, missing/additive/heterogeneous/duplicate
  refusals, corrected zero-conflict fixture expectation, raw-file hash comparison, and deterministic
  normalization assertions are appropriate once the blockers above are closed.
- No predictive-value, consumer, model-use, scheduler, commit, or batch-landing authority is implied.

## Reproduction

```text
.venv/bin/python3.14 -m pytest tests/contract/test_pfr_advstats_ingestion_red.py -q
=> 23 collected; 18 failed; 5 passed

Fixture SHA-256:
cca5407115902f0db573bcc7e72a035803883f791e1c7ed98c160f047e815f7b
```
