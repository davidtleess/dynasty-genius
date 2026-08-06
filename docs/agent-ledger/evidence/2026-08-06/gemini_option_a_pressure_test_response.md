# Gemini Option A Ingestion Pressure Test Response

**From:** Gemini (Operations & Telemetry)  
**Date:** 2026-08-06 ET  
**Observed:** 2026-08-06 00:25 EDT  

## 1. Assessment of Ingestion Lineage & Live Reads

*   **Direct Live Read Necessity**: There is no operational or reliability advantage to keeping any of the five streams (`player_stats`, `rosters`, `snap_counts`, `pbp`, `participation`) as direct live reads. 
*   **Parallel-Route Defect**: A double-route defect currently exists for `snap_counts`. The data is already captured, resolved, and stored canonically as `player_snap_count` (253,106 rows) inside `app/data/nflverse_usage.db`, yet `run_feature_refresh.py` downloads the same data live over the internet. Removing the live read and routing the feature builder through the canonical database/export yields value-identical candidates (`2,743 rows × 39 columns`), eliminating the network dependency with zero impact on derived features.

---

## 2. Operational & Reliability Consequences

*   **Failure Isolation**: Isolating the morning Feature Refresh (09:15) from live external connections prevents network timeouts (such as the `2026-08-02` participation download timeout) from aborting downstream feature derivation. Under Option A, if the capture job fails, Feature Refresh can gracefully execute against the local "last-good" cache while reporting a staleness warning.
*   **Replayability**: Storing the raw provider bytes is a prerequisite for replayability. Currently, yesterday's run is not reproducible (0% replayability) because no input snapshots are stored. Content-addressed Parquet files allow byte-exact historical derivation replays.
*   **Storage footprint**: For the 8-year historical window (2018–2025), the total compressed Parquet payload is **`189.32 MiB`** (1,101,479 rows).
    *   *JSON Envelope Penalty*: Storing these as generic raw JSON snapshots causes a **37× expansion** (129 `snap_counts` JSONs occupy ~1.12 GB vs 1.77 MiB Parquet). Option A must use Parquet storage.
*   **Backup consequences**: Since rebuildable assets are excluded from the offsite backup manifest to prevent upload timeouts (today's backup run PID `33937` is still uploading the 2.2 GiB package), we can safely add the `189.32 MiB` compressed Parquet directory to `app/config/backup_manifest.json`. This preserves replay evidence offsite without bloating the daily upload.

---

## 3. Per-Stream Mixture Coherence

*   **Verdict**: A per-stream mixture (e.g., capturing stats/rosters but leaving play-by-play live) is **operationally incoherent**. It fails to establish uniform replayability, complicates the ingestion schedule, and preserves parallel-route defects for mixed streams. Lineage must be uniform across all five feeds.

---

## 4. Preconditions for Option A Enablement

Before Option A is scheduled and enabled, the following gates must be satisfied:
1.  **Backup Recovery Verification**: Confirm that the background backup recovery run (PID `33937`) has completed successfully.
2.  **Backup Manifest Extension**: Add the Parquet raw storage directory to `app/config/backup_manifest.json` under a strict content-addressed, non-duplicating pattern with a storage ceiling.
3.  **Marker Dependency**: The capture schedule must run before the Feature Refresh, and Feature Refresh must gate its run on the ingestion status marker to verify if a new season frontier has landed.

---

## 5. Dissent & Alignment

*   No operational dissent exists. The telemetry, footprint metrics, and reliability analysis are in complete alignment with Claude/Codex's postures and David's stated preference.

RECOMMENDATION: OPTION A

---

*Editorial note (Claude, committing lane): the `file:///Users/...` markdown links in Gemini's
original were rewritten to repo-relative paths. **Content and meaning unchanged** — machine-bound
absolute paths are not durable evidence and the closeout gate's `ephemeral-locators` check ENFORCEs
against them. No claim of Gemini's was altered.*
