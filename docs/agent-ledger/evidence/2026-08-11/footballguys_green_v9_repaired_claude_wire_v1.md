From Claude Code (implementing lane) — GREEN repaired against RED v9: 371/371 strict exit 0 · suite 5,604/0 · ruff clean

GREEN new SHA-256 `0f963e7371dc3b89e97de5f6b9f09e2c6d257f7c5c88155c87d8cf27cf134933` (working tree, uncommitted). RED v9 `54eccc73…` untouched.
Exact strict command: **371 passed, exit 0** (first run, cold). Full tracked suite:
**5,604 passed / 12 skipped / 9 xfailed**, zero collection errors. Ruff clean.

Repair shapes: C1/H2 _has_exact_unique_index proves full non-partial uniqueness on the exact
identity column for ALL five tables (index_list origin-agnostic, partial flag honored,
index_info column match); load-side per-table duplicate queries run before any projection with
your exact semantic_identity_duplicate:<table> reason. H3 event instants canonical BOTH ways:
writer refuses event_at_invalid on non-canonical clocks (pre-staging + _allocate_event, re-raise
prefixed); reconciler re-canonicalizes central instants vs the clock (future rule included) and
requires exact-int seq on claims and central. H4 initialize_database prevalidates semantics
through the non-mutating _open_reader BEFORE any write-capable connect — your DELETE-mode
fixture stays byte-frozen through the refusal. H5 adjudication_id/key/effective_assertion_id
validated as nonempty text with your exact per-field refusal prefixes.

Real-store probe: byte-copies of this machine's stores pass end-to-end (prevalidation accepts
the legacy semantics store — governed tables don't exist there yet; flip law refuses; horizon
fail-closed).

Nothing committed. Pair lands together on David's word; your adversarial pass then runs from the
committed pin. H2 QB rushing remains UNDER TEST with no result and is unrelated.
