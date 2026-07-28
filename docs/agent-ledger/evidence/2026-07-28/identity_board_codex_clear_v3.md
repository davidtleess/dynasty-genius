# TW28-IDENTITY-1 — Codex final review of Claude identity board v3

**Reviewer:** Codex (independent technical reviewer)  
**Date:** 2026-07-28  
**Artifact reviewed:** `identity_board_claude_v3.md`  
**Reviewed SHA-256:** `b42dcbae3c796a524208a84604eeaeb1e465ce5cefe30c7dd4ec759a2a3f9ce0`  
**Disposition:** **CLEAR — as a scoped board, not as authorization to implement any item.**

No code, production artifact, Compliance Audit surface, DG2-S0-01 surface, or
canonical-key work was changed or run.

## Enumerated CLEAR

1. **The v3 artifact identity is exact.** I reproduced the SHA-256 above from the
   working-tree file.

2. **The requested v2 correction is the only substantive board change.** A full
   `diff -u` from v2 to v3 contains the review-chain disclosure and the I-4
   provenance-versus-preservable-bytes repair. The eight earlier corrections that I
   had independently confirmed in v2 are otherwise unchanged.

3. **Unrecoverable provenance is now stated narrowly and correctly.** The operational
   snapshot records `source`, `pull_timestamp`, and `count`, but no upstream commit
   SHA. Therefore the exact upstream source revision cannot be reconstructed from the
   snapshot metadata.

4. **Preservable bytes are now stated separately and correctly.** The local file
   `app/data/identity/_runs/ff_playerids_20260516.json` still exists at 3,768,182
   bytes, and I independently reproduced its SHA-256:
   `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
   Those bytes can be committed or backed up now.

5. **The one-way loss condition is correct.** If the extant bytes are lost before
   preservation, a later pull from mutable upstream `master` cannot be assumed to
   recreate the historical vintage; the hash proves identity but cannot restore
   missing bytes.

6. **The correction does not smuggle in a stronger reproducibility claim.** The board
   says preservation pins the operational payload, not the missing upstream revision
   provenance.

7. **The original six-measurement challenge remains resolved.** Across the v1
   challenge and v2 re-review I independently reproduced the 12,203-row status
   distribution; the 501 GSIS-shaped/80 slug-shaped modeled-ID split; the two
   feature-present crosswalk-orphan players and their exhaustiveness; the
   missing-crosswalk fail-open code path; the vintage—not duplicate-key—explanation
   for the 12,201/12,202/12,203 spread; and the absence of production callers for the
   name-similarity matcher. I did not take any of those six measurements on Claude's
   word.

8. **Scope remains honest.** The artifact is a board, not a repair. It keeps I-5,
   name matching, canonical-key selection, the parked Compliance Audit workflow, and
   DG2-S0-01 unit (d) outside the opened work.

This CLEAR closes the mandatory challenge round for the board itself. It does not
clear the separate implementation framing, which has its own disposition.
