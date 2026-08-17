# QB-1 execution framing v5 — independent round-5 CLEAR (Codex v5)

Date: 2026-08-14  
Work item: `TW14-QB1-1`  
Reviewed artifact: `qb1_execution_framing_claude_v5.md`  
Reviewed SHA-256: `1efa8760a467899f8a0ec6251439191dde15af24d4f18135bdae64a0e5a999e4`  
Verdict: **CLEAR — framing phase closes**

This CLEAR authorizes no provider call or study execution. QB rushing
production (H2) remains **UNDER TEST** with no result.

## Enumerated checks

1. Reproduced the v5 artifact SHA-256 exactly.
2. Verified R4-B1 is resolved with one deterministic external operation:
   **seven current nflreadpy provider calls**. The six-call/local-reuse branch
   is explicitly rejected rather than deferred to RED.
3. Verified the seven datasets match shipped `VALIDATION_DATASETS` in spec
   order: weekly, season summary, players, rosters, ff-playerids, draft picks,
   and play-by-play.
4. Checked each table row against the installed nflreadpy signatures and the
   shipped adapter:
   - weekly: 2015–2025 weekly all-position frame;
   - season summary: 2015–2025 REG summary frame;
   - players: full frame;
   - rosters: full returned frames for 2015–2025;
   - ff-playerids: current full frame;
   - draft picks: full returned frame;
   - play-by-play: full returned frames for 2015–2025.
5. Verified fetch and parse are no longer conflated: raw frames are snapshotted
   before in-repo REG/coverage filtering; roster REG use and draft-pick
   1980–2025 admission are correctly described as downstream.
6. Verified `players` is correctly described as both a model-feature source
   (`birth_date` → H4 `age_at_season_start`) and a §10 draft cross-check source.
7. Verified the two crosswalk roles are non-aliased: the pinned 2026-05-16 file
   remains the H5 §9.3 static-join instrument; the fresh provider frame is the
   separately captured D1 identity dataset. No local file is re-enveloped or
   discarded.
8. Verified the decision packet discloses the dominant 2015–2025 play-by-play
   transfer estimate (~2–6 GB), the aggregate small-table estimate, the 0/7 D1
   state, the exact snapshot root, and same-change backup-manifest coverage.
9. Verified the pre-result honesty language remains intact: H5 likely
   `unsupported_power` is advisory until execution; F32 is not tuned; model
   contrasts 1–10 are only F32-unaffected, with their own fold/n power still
   unmeasured and unpromised.
10. Verified standing boundaries: registration unchanged,
    `decision_supported=False`, no fetch before David's explicit word, no push,
    and H2 remains UNDER TEST until execution plus David's ruling.
11. Verified the semantic-round/structured-round undercount is explicitly
    disclosed; this CLEAR is semantic round 5 and no open BLOCKER remains.

## Disposition

Framing is CLEAR. Both lanes now hold at the external-data gate. David's
explicit seven-fetch word is required before any provider access or raw-store
population. RED authorship remains Codex's and opens only after that gate under
the agreed sequencing.

