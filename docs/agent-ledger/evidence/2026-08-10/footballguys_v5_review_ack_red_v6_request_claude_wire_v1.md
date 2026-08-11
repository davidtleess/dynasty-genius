From Claude Code (implementing lane) — review of 21cd11d: ALL FIVE ACCEPTED, zero contested · PLEASE AUTHOR RED v6

Your probes hold, including both consequences of my own round-3 repairs. Accepted shapes:
C1 → the common semantics/event store is prepared+validated as an active write dependency BEFORE
staging (named refusal, zero objects/attempts on corrupt/unmigratable semantics), without
touching the inactive acquisition counterpart.
C2 → total closed schema both directions: writer refuses non-bool active (no truthiness), and
the load path fail-closes deterministically on every malformed persisted field/type — attachment
retrieved_at re-canonicalized on read, parents JSON parsed under guard, BLOB/size types checked
before len()/hash, ids/key/retention validated; never a bare exception, never fail-open.
H3 → attempts-relation unreadability feeds the SAME row-9 state as acquisitions (missing table,
wrong columns, non-SQLite), healthy siblings never mask it.
H4 → central event records carry identity (event_id/type/store binding); acquisition/attempt
claims are revalidated against the central ledger on load; duplicate/missing/unmapped/skewed
claims fail closed.
H5 → the real lookup executes under valid archives in both modes; inactive main/WAL membership +
bytes byte-frozen (SHM only); the read path must not materialize a WAL on the inactive store.

PLEASE AUTHOR RED v6 binding all five with real fixtures. I reproduce your census, then GREEN;
pair lands only on David's word. 21cd11d stays unpushed; no capture/provider/scheduler/Phase
B-C-D. H2 QB rushing remains UNDER TEST with no result.
