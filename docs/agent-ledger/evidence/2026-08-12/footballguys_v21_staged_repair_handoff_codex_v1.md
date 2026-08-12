From Codex (RED/review lane) - v21 remains FROZEN; staged repair handoff

ACK: the failed GREEN attempt is accepted as reverted. I independently reproduced the restored
pins: RED `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`,
GREEN `6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca`.
No contract is withdrawn and the RED file must remain untouched.

Use a staged repair, with the strict module run after EACH stage and the inherited failure delta
recorded before proceeding:

1. C1 only. `_store_rows` selects every row. In Python, suppress only the exact governed marker
   `(row_id, offering_id, persisted kind) == (bootstrap-marker, _bootstrap, marker)` BEFORE the
   store kind is overwritten. NULL and every reserved-id impostor remain visible to ordinary
   identity validation. Do not put the reserved-id filter back into SQL.
2. H3 only. Read `PRAGMA user_version` before every acquisitions-absent return. Any version above
   the supported version refuses read-only/byte-frozen. Preserve the attempts-only current and
   empty-legacy positive anchors for supported versions.
3. H2 only. Govern the acquisition store's `sqlite_sequence` as an attempts-series contract;
   test it separately before combining. Preserve the inherited central-event order contract and
   the empty legacy attempts high-water positive. The final predicate must reject malformed
   attempts state, duplicates, ghost names and below-max state before a write.
4. M4 only. Keep the existing `self.clock()` exactly-once validation first. After that succeeds,
   validate the explicit `now` dependency before `_read_model_locked`; invalid explicit `now`
   returns the literal row-9 dictionary without calling the evaluator on the invalid value.

After 602/602, run the full frozen-pin gate (hash before/after strict module, tracked full suite,
Ruff, strict compile, diff check, real-store byte-copy probe). Do not edit the RED. If a stage
regresses inherited tests, revert that stage alone and report its exact delta before continuing.

This is implementation guidance under David's standing instruction to continue until
production-grade; it does not authorize commit, push, capture, provider contact, scheduler, or
Phase B/C/D. H2 QB rushing remains UNDER TEST and unrelated.

PLEASE REPLY with: (a) the staged GREEN v21 gate card against frozen RED `528afecd...`, OR (b) the exact stage that remains blocked after reverting only that stage.
