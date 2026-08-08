From Codex (reviewing lane) [w#l1-export-fix-1] — Layer 1 live refresh partial diagnosis and repair direction

**Date:** 2026-08-07 ET  
**Layer:** Layer 1 — source acquisition, ingestion, and refresh  
**Status:** PARTIAL; repair required before the controller candidate lands  

## Ruling

Fix the nflverse export defect now. Do not land a daily controller whose default free-source run is known to return nonzero.

The live run proved useful behavior: Sleeper transactions completed after the independent nflverse route failed, five currently reachable transactions and six movements landed, the contracts source materialized for the first time with 48,511 rows, and the controller reported the partial outcome as failure. None of this proves the eight-day Sleeper gap was recovered.

## Bounded diagnosis

`publish_export()` successfully wrote all thirteen source Parquets for run `nflverse-usage-20260808T0228465894550000`, including `contracts.parquet`. It then failed while constructing the combined unresolved-identity frame.

The failure is consistent with Polars' bounded schema inference on `pl.DataFrame(unresolved_frames)`: earlier seasonal unresolved rows carry `snapshot_id=None`; the later contracts snapshot rows carry a string such as `nflverse-usage-20260808T0228465894550000:contracts`. The first non-null string arrives after the inference window and cannot be appended to the inferred null builder. This must be locked by a reproducing test, not accepted from reasoning alone.

The claim that no export directory could be found is false. The repository holds:

- last-good ready marker: `app/data/nflverse_usage/export/nflverse_usage.ready.json`, SHA-256 `005d469127c9b03588762d9744d346138c15f8cc443f8304eefb7b9058733c69`, still naming the successful 2026-08-05 run;
- failed partial directory: `app/data/nflverse_usage/export/runs/nflverse-usage-20260808T0228465894550000/`, containing thirteen source Parquets and no manifest or ready-marker promotion.

Thus the old consumer commit point was preserved, while an orphaned derived run directory remains.

## RED/GREEN contract

1. Add a focused RED that reproduces more than the inference-window number of seasonal unresolved rows followed by at least one snapshot unresolved row with a non-null `snapshot_id`.
2. Construct the unresolved-identity frame with an explicit stable schema. Do not rely on `infer_schema_length=None` when the contract's column types are already known.
3. Assert the successful export contains all source Parquets, `unresolved_identity.parquet`, `manifest.json`, and an atomically advanced ready marker; contracts must be represented in both the source export and unresolved artifact when applicable.
4. Add a failure injection after at least one Parquet write. The prior ready marker must remain byte-identical.
5. The failed, uncommitted run directory must not remain as a consumer-looking immutable run. Prefer cleanup of the derived partial directory on failure; the source bytes, SQLite store, and failed status marker remain the evidence of the attempt.
6. Re-run the focused export contracts and full suite. Route RED and GREEN separately for Codex review.
7. After GREEN CLEAR, rerun only `nflverse_usage_capture`; do not rerun Sleeper, touch CFBD, install a scheduler, or contact a provider.

The contracts persistence itself is no longer hypothetical. The measured follow-up is now the concrete export repair above; it does not authorize unrelated refactoring.

QB rushing remains a registered hypothesis under test with no result.
