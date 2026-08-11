From Claude Code (implementing lane) — GREEN repaired against RED v8: 340/340 strict exit 0 · suite 5,573/0 · ruff clean

GREEN new SHA-256 `241d031dc4e36ee3f54500df8d6e9ad2bcd9fb208bdc5f062d0fc4b6c7ad8f4c` (working tree, uncommitted). RED v8 `8a31fd94…` untouched.
Exact strict command: **340 passed, exit 0** (PYTHONDONTWRITEBYTECODE=1, cold). Full tracked
suite: **5,573 passed / 12 skipped / 9 xfailed**, zero collection errors. Ruff clean.

Repair shapes: C1 _migrate_semantics_store is validate-all-then-mutate — populated bare
allocator refuses store_migration_unreconcilable:semantics BYTE-FROZEN (your fingerprint
assertion drove the two-pass ordering); empty bare rebuilds via DROP+CREATE (real UNIQUE);
full-shape without the unique index refuses unmigratable; the reconciler is typed
(reconciled/unreadable/mismatch) — closed central rows, duplicates before dict collapse,
unreadable central → row 9 with zero claims, mismatch → integrity special; intake gate refuses
event_ledger_unreconciled on non-reconciled. C2 _refuse_unreadable_counterpart probes PRESENT
counterpart relations with the exact production read shapes pre-staging →
store_unreadable:<store>.<relation>; absent attempts stays tolerable (legacy predates it — your
v7 c3 world still intakes). H3 isinstance before membership everywhere; required-field check is
presence-not-truthiness so unhashables reach their own named refusals. H4 module-level
_observe_sqlite_file_set seam + bounded(8) observe→open→re-observe; comparison on the WAL flag
only (SHM = permitted residue); instability → sqlite error → unreadable → row 9.

Real-store probe: byte-copies of this machine's stores — flip law refuses, read model no_record,
horizon unknown/fail-closed.

Nothing committed. Pair lands together on David's word; your adversarial pass then runs from the
committed pin. H2 QB rushing remains UNDER TEST with no result and is unrelated.
