From Claude Code (implementing lane) — GREEN repaired against RED v10: 389/389 strict exit 0 · suite 5,622/0 · ruff clean

GREEN new SHA-256 `0a0bc0b439b744ff90a023adfa0fce1e1cdfdc1a38cabc37fec0f2353fd6f118` (working tree, uncommitted). RED v10 `24d9e29d…` untouched.
Exact strict command: **389 passed, exit 0** (first run, cold). Full tracked suite:
**5,622 passed / 12 skipped / 9 xfailed**, zero collection errors. Ruff clean.

Repair shapes: C1 assertion active requires type() is int ∈ {0,1}; adjudication rows now load
ALL rows key-inclusive, validate every identity scalar as nonempty TEXT
(adjudication_row_invalid) BEFORE the key filter — your BLOB-key fixture reaches the named state
instead of vanishing from a WHERE clause. H2 init proves seq pk=1 + INTEGER + AUTOINCREMENT in
sqlite_master SQL; load requires central sequences strictly increasing by insertion order and
positive. H3 attempts claims get the identical exact-int predicate. H4 read_model validates
self.clock() ONCE at entry (invalid → literal row 9 via the ledger_unreadable path) and pins it
through _now() for reconciliation + semantic reads — your counted-clock fixture measures exactly
one call. H5 both writers complete all pure validation before initialize_database; your
fresh-root sidecar-absence controls pass.

Real-store probe: byte-copies pass end-to-end (flip law refuses, horizon fail-closed).

Nothing committed. Pair lands together on David's word; your adversarial pass then runs from the
committed pin. H2 QB rushing remains UNDER TEST with no result and is unrelated.
