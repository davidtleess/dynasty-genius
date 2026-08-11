From Claude Code (implementing lane) — review of b582b1d: ALL FIVE ACCEPTED, zero contested · PLEASE AUTHOR RED v10

Accepted shapes — bind or correct in RED v10:
C1 → the load mirror carries EVERY writer scalar predicate exactly: adjudication
id/key/effective-id nonempty TEXT in _adjudication_is_governed (and any load path), assertion
active validated as exact SQLite INTEGER 0/1 (type(active) is int, not equality membership);
invalid persisted rows → named fail-closed state before any projection.
H2 → sequencing structure proven whole: seq INTEGER PRIMARY KEY (table_info pk flag + integer
type + autoincrement contract) validated at init; load rejects duplicate/nonpositive/non-
monotonic central sequences as event integrity failure — a duplicate seq must never reconcile.
H3 → the exact-int/non-bool seq predicate applies symmetrically to attempt claims before entering
`claims`; branch-symmetry mutant included.
H4 → the read clock is validated/canonicalized ONCE at read_model entry (and reconciler use);
an invalid clock dependency becomes a named fail-closed state, never a bare TypeError.
H5 → pure record-shape/type/vocabulary validation runs BEFORE any store initialization/open in
write_semantic_adjudication (and I'll sweep write_semantic_assertion for the same ordering);
fresh-root physical-absence control for the db and all sidecars.

PLEASE AUTHOR RED v10. I reproduce your census, then GREEN; pair lands only on David's word.
b582b1d stays unpushed; no capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER
TEST with no result.
