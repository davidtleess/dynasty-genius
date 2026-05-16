# Identity Contract

**Document:** Dynasty Genius Identity Contract
**Version:** 1.0.0
**Last Updated:** 2026-05-15
**Status:** DRAFT (Task 13.1.0)
**Authority:** Architectural (North Star alignment)

## 1. Overview
The Identity Contract governs the deterministic mapping of players across disparate data sources (Sleeper, nflverse, PFF, CFBD, PFR). It ensures that valuation engines ingest clean, uncorrupted data by enforcing a strict resolution cascade and prohibiting silent fuzzy joins in production pipelines.

## 2. Canonical Identity Model
Dynasty Genius distinguishes between the **Application Canonical Key** and the **External Crosswalk Anchor**.

### 2.1 The Canonical `player_id`
- **Owner:** Dynasty Genius (Internal).
- **Definition:** The `player_id` is the immutable, system-wide primary key for a single human athlete.
- **Persistence:** Generated during the first ingestion of an athlete and persisted in the `player_identity` table (Silver layer).
- **Scope:** Covers prospects, active players, and historical/retired cohorts.

### 2.2 The Crosswalk Anchor: `gsis_id`
- **Definition:** The NFL's Global Service Information System identifier (e.g., `00-00XXXXX`).
- **Role:** The primary join key used to bridge the **nflverse** (`ff_playerids`), **Sleeper**, and **PFF**.
- **Governance:** `gsis_id` is a required attribute for all active and historical NFL players. Prospects lacking a `gsis_id` are bridged via the `prospect_alias_bridge`.

## 3. Source-ID Field Ownership
Data source adapters are responsible for emitting **source-native IDs**. They are strictly prohibited from generating or resolving canonical `player_id` or `gsis_id` independently.

| Source | Primary ID Field | Format |
| :--- | :--- | :--- |
| **Sleeper** | `sleeper_id` | Numeric string (~4-5 digits) |
| **nflverse** | `gsis_id` | `00-00XXXXX` |
| **PFF** | `pff_id` | Numeric string (3-6 digits) |
| **CFBD** | `cfbd_id` | Source-specific integer/UUID |
| **PFR** | `pfr_id` | `Last4Fi00` format |

## 4. Deterministic Resolution Cascade
Every row must be resolved through this fixed sequence. If a step fails, the system proceeds to the next. **No silent fuzzy matching is permitted.**

1.  **Identity Registry Join:** Direct lookup in the Silver `player_identity` table using a known source ID (e.g., `sleeper_id` → `player_id`).
2.  **Deterministic Crosswalk (`ff_playerids`):** Join via `gsis_id` using the community-maintained nflverse mapping.
3.  **Sleeper Metadata Pass-through:** Extract `gsis_id` or `sportradar_id` from the Sleeper `/v1/players/nfl` payload.
4.  **Prospect Alias Bridge:** Lookup in `app/data/prospect_alias_bridge.json` (specifically for pre-NFL or unresolved rookies).
5.  **Composite Deterministic Key (High-Confidence):** Join on `Normalized Name` + `DOB` + `Position` + `Draft Year`.
6.  **Composite Prospect Key:** Join on `Normalized Name` + `College` + `Position` + `Draft Year`.
7.  **Review Queue:** If steps 1-6 fail, the row is rejected from the production pipeline and sent to the **Manual Review Queue**.

## 5. Explicit Prohibitions
- **Silent Fuzzy Joins:** Probabilistic string matching (Levenshtein, Jaro-Winkler) is strictly banned from automated production paths.
- **Adapter-Local Identity:** No adapter (e.g., `pff_adapter.py`) may contain hardcoded identity mapping logic.
- **Unresolved Data Ingestion:** Rows failing deterministic resolution must be excluded from training/feature materialization to prevent data corruption.

## 6. Review States & Overrides
Players in the **Manual Review Queue** may exist in the following states:
- `PENDING`: Awaiting human review.
- `RESOLVED_MANUAL`: A manual override has linked the source row to a canonical `player_id`.
- `REJECTED_COLLISION`: Explicitly blocked to prevent incorrect joins (e.g., two players with identical names/positions in the same class).
- `INSUFFICIENT_DATA`: Cannot be resolved with available evidence.

Manual overrides are persisted in the **Identity Override Registry** and are versioned in source control.

## 7. Identity Snapshot Immutability
To ensure backtest reproducibility, the identity layer produces an **Identity Snapshot** for every evaluation run.
- **Rule:** A snapshot is a point-in-time capture of the ID map.
- **Persistence:** Saved alongside backtest artifacts.
- **Governance:** Once a backtest run commences, its identity snapshot is **immutable**. Subsequent manual overrides or bridge updates will not retroactively change the historical identity mappings of that run.
