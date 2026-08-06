# Gemini Layer 1 reports — Codex verification v1

**Date:** 2026-08-06 (America/New_York)  
**Layer:** Layer 1 ingestion / operations evidence  
**Verdict:** useful with corrections; **not safe to carry verbatim**  
**Scope:** read-only evidence verification. No scheduler, capture, store, consumer, commit, push, or
enablement authority is inferred.

The mandatory cockpit hygiene scan and Gemini-attributed ledger scan both pass. Those scans detect
unexpected writes and prohibited role declarations; they do not establish factual correctness.

## Safe to carry

- Gemini independently recommends **Option A** as planning direction, with no operational dissent.
- Feature Refresh directly reads five nflreadpy datasets and retains no replayable five-input bundle.
- `snap_counts` duplicates canonical `player_snap_count` (253,106 rows, 2016–2025).
- The measured 2018–2025 five-stream baseline is 1,101,479 rows / 189.32 MiB, attributed to the
  Codex pressure test Gemini reviewed.
- Canonical `nflverse_usage.db` capture has no scheduled job.
- The Feature Refresh, FantasyCalc forward-capture, and league-runtime jobs are loaded at 09:15,
  09:00, and 09:20; their current LaunchAgent last-exit values are 0.
- The 09:20 job writes `app/data/league_runtime`, not the transaction database.
- Backup run `20260806T024853Z` completed with 508 files, 2,203,676,656 bytes, verified hashes, and
  zero failures.

## Corrections required before reuse

1. **The “37x” sentence mixes operands.** 37.12x compares one eight-season JSON envelope set
   (68,904,107 bytes) with 1,856,232 Parquet bytes. All 129 JSON files total 1,120,520,543 bytes,
   about 603.65x that Parquet baseline.
2. **“Backup still uploading” is stale.** It completed at 2026-08-06T04:52:33Z.
3. **“Excluded to prevent upload timeouts” is unsupported.** The prior failure cause remains
   undiagnosed; the timeout explanation was withdrawn.
4. **“Safely add 189.32 MiB without bloating the daily upload” is false under the current backup
   design.** Every manifest file is uploaded into every immutable run prefix, adding bytes and
   restore-hash work unless backup design changes.
5. **“0% replayability” is too broad.** The exact five-input Feature Refresh bundle cannot be
   reconstructed if upstream bytes change; canonical snap-count raw history does exist.
6. **“Zero impact” overclaims one parity experiment.** The measured substitution produced
   value-identical 2,743 x 39 candidates on that pinned common vintage.
7. **The cadence report conflates bound and captured.** SQLite has 12 stream tables plus the capture
   ledger; contracts is the 13th bound spec but is uncaptured.
8. **`fc_snapshots.db` is not frozen at 2026-05-30.** It contains `fc_native` rows through 2026-06-24
   and has a 2026-06-24 modification time.
9. **The QB-context cadence row is wrong.** No `com.davidleess.dynasty-roster-capacity` service
   exists. Tuesday 10:00 belongs to Realized Outcome. QB context is an on-demand live read through
   Roster Auditor, with no snapshot or cache.
10. **Application outcome and process exit are separate facts.** `noop` is application output;
    LaunchAgent exit code is 0.
11. **The cadence report has machine-bound `file:///Users/...` links.** Replace with repo-relative
    evidence paths before adopting it as durable canonical evidence.

## Planning consequence

Gemini strengthens, but does not independently authorize, Option A. The supported operational
design is exact content-addressed source capture, per-component vintages, an atomic bundle manifest,
last-good publication, and consumer parity before retiring each live route. Storage format and
backup treatment remain design gates; the generic JSON envelope and current full-copy backup shape
must not be copied blindly.
