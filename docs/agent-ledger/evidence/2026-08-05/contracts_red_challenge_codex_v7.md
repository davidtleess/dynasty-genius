# Contracts fourth RED challenge — Codex v7

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **NOT CLEAR for GREEN — two narrow failure-semantics corrections**

## Independent execution

- Focused RED: 58 collected, 55 failed, 3 passed, zero collection errors.
- Ruff on the test and generator: pass.
- The revised source reconciliation, digest allow-list, exact row key, emitted/empty typing,
  forced seasonal-unresolved row, mixed-run content comparison, return-boundary timestamp and named
  durable fields are adequate.

This pass has converged. Only two blockers remain, and both bake a new or incorrect failure semantic
into the RED.

## U1 — export failure now requires an unauthorized database rollback

`tests/contract/test_contracts_ingestion_red.py:948-953` asserts that after an export-stage failure
the database contains exactly the **first prior-run** snapshot and not the snapshot captured in the
failed run.

That is not the cleared contract. Design v2 states that failure semantics are unchanged: the prior
**ready marker and file set** stand and the run marker names the stage. The existing publisher's
documented ordering is that database writes have committed before export begins
(`test_pfr_advstats_ingestion_red.py:755-759`). Design v3 requires honest failure and recovery but
never authorizes cross-resource rollback or deletion of a successfully captured observation because
publication failed.

The current assertion would force GREEN to invent a database/export distributed rollback mechanism,
discard real captured data, or reorder established capture semantics. That is a scope expansion, not
a falsifier.

Required correction:

- record the exact durable snapshot-ID/hash set **after** the induced export failure without
  prescribing that the failed-run observation vanished;
- require the prior ready marker and all prior published files to remain byte-identical;
- on recovery, require every observation that was durable after failure plus the recovery
  observation to remain byte-identical and appear in the new export;
- do not delete or demand deletion of a durable capture merely because publication failed.

## U2 — `captured_before_failure` is current-run state, not historical-store state

`test_a_snapshot_failure_records_partition_context_and_prior_capture` at lines 1072-1102 performs a
complete successful run, then starts a **new** run whose only fetch fails immediately. It expects the
second run's `captured_before_failure` to contain the snapshot from the earlier run.

The existing orchestration constructs `captured_before_failure` from the current run's `results`
list. On an immediate first-fetch failure, the honest list is empty. Prior durable history is not
"captured before failure" in this run. Forcing historical entries into the field would blur run
status with store inventory and change existing semantics.

Required correction: exercise a mixed run in which the snapshot stream succeeds first and a later
seasonal stream fails. Then `captured_before_failure` is genuinely non-empty in the same run and its
snapshot entry can be required to carry exact `capture_axis`, `snapshot_id`, and `observed_at`.

## Scope judgment

Do **not** remove contracts from the batch or redesign the stream. The scope is implementable, the
RED has materially converged, and the remaining defects are two test-shape corrections—not evidence
that the ingestion design is beyond the lane's ability.

No further broadening is requested. After U1/U2 are corrected without introducing a new semantic,
the RED should be ready to open GREEN. This disposition does not itself authorize GREEN, commit,
live landing or push.
