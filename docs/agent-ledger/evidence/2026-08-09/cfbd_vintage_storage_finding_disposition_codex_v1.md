# CFBD vintage storage finding — accepted, deferred implementation

Date: 2026-08-09  
Owner: Codex  
Layer: Layer 1 source retention

## Disposition

Claude's post-push divergence audits of `a08247d` and `4701257` are acknowledged **CLEAR**. Their
audit loops are closed.

The CFBD storage finding is **accepted as valid and non-blocking**: the stored `games` array is a
redundant parsed copy. `load_vintage()` already reads and hashes the retained raw JSON, parses it,
recomputes schema evidence and refuses unless the stored array equals the fresh parse. A future
metadata-only vintage can return the freshly parsed rows without changing accepted behavior.

Implementation is **not opened in this closeout**. It is a separate CFBD RED/GREEN and committed-data
migration requiring David's explicit word; it does not displace the directed next-session
Footballguys pilot.

## Measurement correction

The submitted table's component sizes use different JSON serializations and therefore are not
additive. A representation-consistent measurement using the store's current `indent=2,
sort_keys=True` encoding is:

- stored vintage: 908,769 bytes;
- metadata-only vintage under the same writer: 3,214 bytes;
- duplicate storage removed: 905,555 bytes (99.65% of the vintage file);
- separately retained raw provider JSON: 655,068 bytes;
- 888 derived game rows.

This correction strengthens rather than weakens the finding. The raw provider JSON must remain
losslessly reconstructable and hash-verifiable; “use Parquet” is not permission to discard the
source-authentic wire bytes. Any future raw compression/representation change is a separate source
retention contract.

## Required future ticket

- RED proves the persisted vintage contains metadata only and `load_vintage()` derives `games` from
  retained raw bytes.
- Preserve byte-count, full-SHA, vintage identity, row-count, ordered schema and schema-hash checks.
- Prove the existing 888 rows are identical before and after migration.
- Prove replay remains idempotent and no accounting/vintage identity is minted by a read.
- Strip the one committed vintage only after losslessness is measured, with backup and exact-SHA CI
  evidence.

No code, data, config or scheduler was changed for this disposition.
