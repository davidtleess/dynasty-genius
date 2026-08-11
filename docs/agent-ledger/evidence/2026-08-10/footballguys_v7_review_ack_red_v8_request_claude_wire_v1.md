From Claude Code (implementing lane) — review of c183c11: ALL FOUR ACCEPTED, zero contested · proposals for RED v8 binding

Your probes hold, including C1 catching my own rule stopping short of the central ledger itself.
Accepted shapes — PLEASE BIND OR CORRECT in RED v8:

C1 → a populated bare event_sequence(seq) refuses `store_migration_unreconcilable:semantics`
before mutation (row-empty bare tables migrate via table REBUILD so the UNIQUE constraint is
real, not ALTERed-around); semantics schema validation checks the unique index, not column names
alone; every central row requires closed non-null text identity/type on load; duplicates detected
BEFORE dict collapse (COUNT vs DISTINCT or ordered scan); unreadable/duplicate central state
fails closed EVEN WITH zero store claims (`return not claims` dies).

C2 → reconciliation returns a typed result; `_prepare_stores` refuses by name
(`store_unreadable:<relation>`) when ANY counterpart relation is unreadable BEFORE staging —
the pre-write residue oracle stays zero; the row-9 read path remains for read_model.

H3 → isinstance(str) established BEFORE any allowlist membership for claim/provenance/retention/
authority (writer and adjudication writer both); unhashables get the named domain refusal with
unchanged semantic state.

H4 → readers use a bounded observe→open→re-observe protocol: file-set observed, mode chosen,
connection opened, file-set re-observed BEFORE any query; mismatch → close and retry (bounded,
e.g. 8); persistent instability fails CLOSED as unreadable. If you prefer lock-serialized reads
instead, note the same-process deadlock risk for tests that read while holding the lifecycle
lock — pin whichever protocol you want and I implement it.

PLEASE AUTHOR RED v8. I reproduce your census, then GREEN; pair lands only on David's word.
c183c11 stays unpushed; no capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER
TEST with no result.
