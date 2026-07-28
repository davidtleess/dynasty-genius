# TW28-IDENTITY-1 — Codex re-review of Claude identity board v2

**Reviewer:** Codex (independent technical reviewer)  
**Date:** 2026-07-28  
**Artifact reviewed:** `identity_board_claude_v2.md`  
**Reviewed SHA-256:** `905e5723d4cbce32de505e4b61fd5f53c1e0b8947966b199d755f304b3a6119b`  
**Disposition:** **NOT CLEAR — one narrow factual correction remains.**

No code, production artifact, source board, Compliance Audit surface, or DG2-S0-01
surface was changed or run.

## Enumerated re-review

1. **Missing-crosswalk blast radius — addressed.** Section 2 now says zero Engine B
   values and 80 surviving Engine A values, and it distinguishes the nonblocking
   What-Changed review signal from fail-closed publication.

2. **PRE_MODEL arithmetic — addressed.** Section 2 says 9,478 of 9,480 rows lack
   Engine B features, leaving Kallerup and Williams in the feature-present identity-miss
   class.

3. **Bridge vocabulary — addressed.** Section 1 separates the absent canonical DG-id
   bridge from shipped Sleeper-id continuity in universe assembly and forward capture.

4. **Sleeper `"0"` sentinel — addressed, and Claude's addition (c) is confirmed.**
   `sleeper_universe.py:90-107` admits the truthy string `"0"` into roster context.
   `capture/model_forward_capture_store.py:88-103` explicitly refuses `"0"` as a
   Sleeper key. These layers implement contradictory population boundaries; filtering
   the sentinel before human identity triage is the correct framing.

5. **False player-detail reason — addressed and strengthened correctly.**
   `app/api/routes/players.py:285-291` emits the category explanation and
   `frontend/src/player/PlayerDetailCard.tsx:37-39` renders the degradation message on
   the player card. This is a David-visible honesty defect, not merely an API null.

6. **I-1 scope — addressed.** I-1a and I-1b are cheap fail-closed/reporting units;
   deterministic row attachment is separately classified as I-5 bridge work. The board
   does not smuggle name matching back into production.

7. **Normalizer work — addressed.** It is classified as semantic migration and
   sequenced behind the canonical-key decision.

8. **Realized-outcome join — addressed.** I-7 is point-in-time Sleeper→GSIS input,
   independent of the slug/GSIS canonical-key problem.

9. **Tower's three measurements — independently reproduced in this round.** The local
   file is 3,768,182 bytes with 2026-05-15 23:28 EDT mtime; `.gitignore` excludes
   `app/data/identity/_runs/`; commit `a73ab02` added exactly the three named manifest
   entries, and the current manifest has no identity-run path.

10. **Stale-language sweep — clean.** Searches for the v1 phrases found only explicit
    quotations that immediately correct them; no active claim retains the old
    zero-model, 9,480-without-features, no-bridge, copy-paste, or blank-caveat framing.

11. **Addition (d) — narrowed, not accepted as written.** The metadata claim is true:
    the recorded provenance is only source, pull timestamp, and count, with no upstream
    commit SHA. Therefore the upstream commit/retrieval provenance cannot be reconstructed
    from the snapshot metadata. But v2 lines 175-177 incorrectly conclude that the exact
    operational input "cannot be re-pinned even in principle." The exact production
    snapshot still exists locally and hashes to
    `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`;
    it can be preserved now as a committed or backed-up immutable payload. A hash alone
    would not restore lost bytes, and a future public re-pull would not reproduce this
    vintage, but neither fact makes the extant bytes impossible to pin.

## Required v3 correction

Replace the I-4 causal sentence with the precise distinction:

- **Unrecoverable provenance:** no upstream commit SHA is recorded, so the upstream
  source revision cannot be reconstructed from current metadata.
- **Still-preservable bytes:** the exact local operational snapshot exists and can be
  hashed plus committed or backed up now.
- **Loss condition:** if the payload is lost before preservation, a re-pull from mutable
  `master` cannot be assumed to reproduce the historical vintage.

No other v2 correction is requested. After that sentence is repaired and the document is
swept for equivalent wording, the board is eligible for an enumerated CLEAR; David's word
remains outstanding on all three identity asks.
