From Claude Code (implementing lane) — GREEN repaired against RED v6: 278/278 strict exit 0 · suite 5,511/0 · ruff clean

GREEN new SHA-256 `43fddc5ef59b2c9f1352f99b7fdd6381b34d86f507204c0ba9fd0688541fbf71` (working tree, uncommitted). RED v6 `a5847de0…` untouched.
Exact strict command: **278 passed, exit 0** (PYTHONDONTWRITEBYTECODE=1, cold cache). Full
tracked suite: **5,511 passed / 12 skipped / 9 xfailed**, zero collection errors. Ruff clean.

Repair shapes: C1 _prepare_stores validates the semantics/event store pre-staging with
exact-shape table validation (store_schema_unmigratable:semantics; store_unreadable: for
non-SQLite bytes; both re-raised, zero residue). C2 writer refuses non-bool active/empty ids/
off-vocabulary retention/non-bytes evidence before mutation; load revalidates every scalar
(retrieved_at re-canonicalized via _canonical_instant, active ∈ {0,1}, guarded parents JSON →
ungoverned, BLOB/size isinstance guards) — states, never exceptions. H3 _load_attempts sets the
same unreadable flag → row 9. H4 event_sequence carries event_id/event_type/store_name/
subject_id/event_at/seq; acquisitions claim event_id, attempts claim attempt_id+event_id;
read_model revalidates all claims against central and fails closed as an integrity state on any
mismatch (schema v4 migrations chained v1→v4). H5 classification + row/attempt loads use
immutable=1 with journal mode from the file HEADER (immutable PRAGMA reports the connection, not
the file — measured); a plain ro open materializes a zero-byte -wal, immutable creates nothing;
your four mode×shape fixtures pass with main/WAL byte-frozen.

Real-store probe: byte-copies of this machine's stores — flip law refuses, v1→v4 migration
clean, event ledger identity-bound, horizon fail-closed.

Nothing committed. Pair lands together on David's word; your adversarial pass then runs from the
committed pin. H2 QB rushing remains UNDER TEST with no result and is unrelated.
