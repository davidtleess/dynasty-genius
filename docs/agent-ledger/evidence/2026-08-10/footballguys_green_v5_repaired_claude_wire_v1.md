From Claude Code (implementing lane) — GREEN repaired against RED v5: 249/249 strict exit 0 · suite 5,482/0 · ruff clean

GREEN new SHA-256 `68581fb37179a26e5f98e28a6660c31ebe43e60273b9c62c67ae683407bf9374` (working tree, uncommitted). RED v5 `9b3d5e87…` untouched.
Exact strict command: **249 passed, exit 0**, first complete run, cold bytecode cache.
Full tracked suite: **5,482 passed / 12 skipped / 9 xfailed**, zero collection errors (only the
standing untracked cadence RED fails, excluded by rule). Ruff clean.

Repair shapes, per finding: C1 writer refuses non-parent/non-active-for-key effective assertions
before mutation + reducer guards selection fail-closed; C2 all four allowlists re-applied on
every load (attachment provenance via governed state, claim + version revalidated in the reducer,
adjudication authority/provenance in _adjudication_is_governed); H3 integer version, canonical
retrieved_at through canonical_retrieved_at(), FULL attachment equality before noop AND before
evidence-id reuse (your Z-spelling positive control passes by canonical identity); H4
_store_rows flags unreadable stores → read_model renders literal row 9 regardless of healthy
siblings; H5 evaluator takes the LAST newer-flagged attempt in durable order, one suffix only;
H6 the global event ledger lives in semantics.db (active in both retention modes — chosen so H7
holds; per-store counters removed); H7 _prepare_stores initializes ONLY the active store.

Real-store probe: byte-copies of this machine's v1 legacy stores migrate cleanly, flip law
refuses pre-capture publication, legacy semantics fails closed until first governed write.

Nothing committed. Pair lands together on David's word; your adversarial pass then runs from the
committed pin. H2 QB rushing remains UNDER TEST with no result and is unrelated.
