# Gemini Layer 1 Cadence Telemetry Audit Response

**From:** Gemini (Operations & Telemetry)  
**Date:** 2026-08-06 ET  
**Observed:** 2026-08-06 06:48 EDT  

---

## 1. Cadence Telemetry Table

For each Layer 1 dataset/stream, the four operational dimensions are itemized below:

| Ingestion Stream / Store | 1. Declared Cadence (plist/config) | 2. Installed & Loaded? (launchctl list) | 3. Last Observed Fire / Exit State & Timestamp | 4. Refreshed by Job? |
| :--- | :--- | :--- | :--- | :--- |
| **`nflverse_usage.db` (13-spec capture)** | `none found` (no plist or freshness config) | `none found` (not loaded in launchctl) | `none found` (no execution logs) | **No** (Database is updated manually only) |
| **Feature Refresh direct reads** | Plist: Daily @ 09:15; Config: Weekly (`dormant_ok: true`) | **Yes** (`com.davidleess.dynasty-feature-refresh`) | Success: `2026-08-05` @ `09:20 EDT` (exit status: `noop` in [feature_refresh.out.log](file:///Users/davidleess/dynasty-genius-product/app/data/logs/feature_refresh.out.log)) | **No** (Streams are read in-memory; no raw snapshots written) |
| **`fc_forward_capture.db`** | Plist: Daily @ 09:00; Config: `none found` | **Yes** (`com.davidleess.dynasty-fc-snapshot`) | Success: `2026-08-05` @ `13:00:00 UTC` (status: `ok` in [fc_forward_capture.out.log](file:///Users/davidleess/dynasty-genius-product/app/data/logs/fc_forward_capture.out.log)) | **Yes** (Appends daily rows to [fc_forward_capture.db](file:///Users/davidleess/dynasty-genius-product/app/data/fc_forward_capture.db)) |
| **`fc_snapshots.db` (legacy archive)** | `none found` | `none found` | `none found` (no execution logs) | **No** (Frozen archive, last modified `2026-05-30`) |
| **`league_transactions.db` (capture script)** | `none found` | `none found` | `none found` (no execution logs) | **No** (Run manually by user only) |
| **`app/data/league_runtime` (capture script)** | Plist: Daily @ 09:20; Config: Daily @ 09:20 | **Yes** (`com.davidleess.dynasty-league-capture`) | Success: `2026-08-05` @ `13:20:08 UTC` (status: `ok` in [capture_status_latest.json](file:///Users/davidleess/dynasty-genius-product/app/data/league_runtime/capture_status_latest.json)) | **Yes** (Writes daily league state JSONs to [league_runtime/](file:///Users/davidleess/dynasty-genius-product/app/data/league_runtime/)) |
| **PlayerProfiler stores/markers** | `none found` | `none found` | `none found` | **No** (Updated by manual file copy only) |
| **PFF manual export inventory** | `none found` | `none found` | `none found` | **No** (Manual directory reconciliation only) |
| **CFBD foundation promoted store** | `none found` | `none found` | `none found` | **No** (Updated manually by script only) |
| **`nflreadpy_qb_context` (roster audit read)** | `none found` (Roster audit plist declares Weekly @ 10:00 Tuesdays) | **Yes** (`com.davidleess.dynasty-roster-capacity`) | Success: `2026-08-04` @ `10:00 EDT` (exit status: `ok` in [roster_capacity_latest.json](file:///Users/davidleess/dynasty-genius-product/app/data/roster_capacity/roster_capacity_latest.json)) | **No** (Reads live PBP in-memory; does not cache or snapshot) |
| **QB validation raw path** | `none found` | `none found` | `none found` | **No** (Hypothesis is under test; study has not run) |

---

## 2. Catalog Reconciliation Findings

*   **suspected error 1 (daily 09:20 job target)**: Confirmed. The LaunchAgent `com.davidleess.dynasty-league-capture` executes `run_league_snapshot_capture.py`. This script writes roster, user, and league-state JSON files to [app/data/league_runtime/](file:///Users/davidleess/dynasty-genius-product/app/data/league_runtime/) and updates `capture_status_latest.json`. It does **not** update [app/data/league_transactions.db](file:///Users/davidleess/dynasty-genius-product/app/data/league_transactions.db). The transactions store is a separate ingestion stream.
*   **suspected error 2 (canonical nflverse scheduled capture)**: Confirmed. The canonical SQLite database [app/data/nflverse_usage.db](file:///Users/davidleess/dynasty-genius-product/app/data/nflverse_usage.db) contains the 13 ingested streams, but has **no scheduled LaunchAgent or cron job** to capture/refresh them. Feature Refresh executes daily at 09:15, but it bypasses this database and queries `nflreadpy` live into memory without updating the local database.

---

## 3. Fresh Telemetry Update: Active Recovery Backup

*   **Marker Path**: [app/data/ops/backup_status_latest.json](file:///Users/davidleess/dynasty-genius-product/app/data/ops/backup_status_latest.json)
*   **Observation**: The manual recovery backup run (PID `33937` in the previous session) successfully completed on **`2026-08-06T04:52:33.690114+00:00`** (run ID: `20260806T024853Z`).
*   **Status**: `completed` with `sha256_verified: true` and zero failures.
*   **Consequence**: The backup failure status has been cleared, and the 26-hour staleness threshold is fully satisfied.
