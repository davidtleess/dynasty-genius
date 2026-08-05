# Contracts RED CLEAR — Codex v8

Date: 2026-08-05  
Layer: 1 ingestion foundation  
Disposition: **RED CLEAR — GREEN may open**

## Independent verification

- Focused RED: 58 collected, 55 failed, 3 passed, zero collection errors.
- Ruff on `tests/contract/test_contracts_ingestion_red.py` and the fixture generator: pass.
- The three passing tests establish fixture/provenance and boundary basis; the 55 named failures
  remain attributable to the intentionally unbuilt contracts/snapshot implementation rather than
  collection or environment failure.

## U1 accepted

The export-stage failure test now preserves the actual cleared guarantee: prior ready marker and
published files remain byte-identical. It inventories the durable snapshot set after failure without
inventing rollback, then requires recovery to preserve every inventoried snapshot byte-for-byte,
add the recovery observation, and publish every durable snapshot.

This is consistent with the established DB-before-export ordering and does not delete captured data.

## U2 accepted

The captured-before-failure test now uses one mixed run. Contracts succeeds first; a later seasonal
stream fails. The failed marker must contain exactly one same-run contracts result with honest
snapshot axis/ID/time and no season, and its snapshot ID must match durable SQLite state.

It no longer conflates prior-run history with current-run `captured_before_failure`.

## Scope and authorization

The RED now provides adequate independent falsification for the cleared snapshot-axis contracts
design under the reduced Layer-1 ingestion gate. **GREEN may open.** This CLEAR does not authorize a
commit, product-store landing, push, scheduler, consumer, model feature, or predictive-value claim.
Those remain subject to their existing gates and David's word.
