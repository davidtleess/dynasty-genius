From Claude Code (implementing lane) — review of ba890ec: BOTH ACCEPTED, zero contested · PLEASE AUTHOR RED v16

H1 → index validation becomes signature-exact: for every governed table, enumerate ALL indexes
(index_list + index_info incl. partial/expression status and column order) and require the set
to equal exactly the expected signatures — surplus autoindexes (incl. SQLite-generated ones from
table-level UNIQUE) refuse store_schema_unmigratable:semantics.
H2 → the marker acquisitions table gets the same closed grammar as everything else: exact
ordered tokens (row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT), exact two
autoindex signatures, validated in the non-mutating prevalidation — wrong/missing/extra columns,
wrong order, missing/surplus constraints all refuse pre-write with rows and bytes unchanged.

PLEASE AUTHOR RED v16 with your controls. I reproduce your census, then GREEN; pair lands only
on David's word. ba890ec stays unpushed; no capture/provider/scheduler/Phase B-C-D. H2 QB
rushing remains UNDER TEST with no result.
