# CFBD FBS schedules GREEN v2 — independent residual review

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **NOT CLEAR**

## Reviewed pins and checks

- RED v6: `9e3d92f27f254181683012528d3cd9cff25b8ceb05d8f4cb6c06c4a6d2ee5019`
- Module v2: `96ffaeff640c3cf1caffc63e7c04529ae7ebc49c925daab17c2a9508038fbc1d`
- CLI unchanged: `a03bd4ed3a76242c1a94493a27b2a6f9b6a1ac2438eacf3fdc923141478f2f47`
- Manifest unchanged: `22afdf528d90febd2bad7e51f5e0099fe79c96eecdfb3508396be1e82dbda396`
- P0-1 through P1-5 are accepted as repaired. One replay-integrity residual remains.

## Residual finding

### R1 — replay verifies vintage identity metadata but not the vintage's canonical data

`replay()` now correctly verifies check and content bytes plus the vintage's claimed ID, raw SHA, and
byte count. It does not verify `vintage["games"]` or its schema against the parsed retained raw bytes.

Independent probe:

1. perform a valid capture;
2. change only `vintages/<id>.json -> games[0].id` from the retained provider value to `999`;
3. leave `vintage_id`, `raw_sha256`, and `raw_bytes` unchanged;
4. call `replay(check_id)`.

Result: replay **succeeds**. The canonical vintage says game `999`, while replayed raw says game
`401752001`. The current vintage mutant changes `raw_sha256`, so the identity check catches it without
proving canonical payload agreement.

Repair: add a valid-JSON vintage-value substitution mutant that leaves all identity metadata intact.
Replay must compare the vintage's games, row count, schema, and schema hash with a fresh parse of the
verified raw content and fail `content_integrity_mismatch` without mutation. Prefer making the ordinary
canonical vintage read path enforce the same integrity rule, so consumers cannot bypass replay and read a
validly encoded but corrupted vintage.

## Disposition

**NOT CLEAR** on module v2. No paid request yet. Return one revised RED/GREEN pin and non-vacuous
RED-before-GREEN result for this residual.

