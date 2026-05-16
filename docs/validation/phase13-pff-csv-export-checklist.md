# PFF Collegiate TE CSV Export Checklist (Task 13.3.0)
*Phase 13.3 · Step 0 Feasibility · Manual Export Protocol*

## 1. Required PFF Export Columns (2018–2025 Drafted TEs)
These columns are **mandatory** for objective archetype segmentation.

| Required Field | Preferred PFF Label | Accepted Fallback | Role |
| :--- | :--- | :--- | :--- |
| **Source ID** | `player_id` | `pff_id`, `id` | Source-native ID (Requires mapping to canonical `player_id`) |
| **Full Name** | `player` | `name`, `player_name` | Review Evidence Only |
| **College** | `team_name` | `school`, `college` | Resolution Context |
| **Draft Year** | *(DG Metadata)* | N/A | Required context (Joins to 2018-2025 drafted TE cohort) |
| **Season** | `season` | `year` | Temporal Selection |
| **Position** | `position` | `pos` | Filter Confirmation (TE Only) |
| **Routes Run** | `routes` | `routes_run` | Denominator for Rates |
| **Slot Alignment** | `slot_routes` | `slot_snaps` | Archetype Trigger (Receiving) |
| **Wide Alignment** | `wide_routes` | `wide_snaps` | Archetype Trigger (Receiving) |
| **Inline Alignment**| `inline_routes` | `inline_snaps` | Archetype Trigger (Blocking) |
| **Targets** | `targets` | `tgt` | Sample Sanity Check |
| **Receptions** | `receptions` | `rec` | Sample Sanity Check |
| **Yards** | `yards` | `yds` | Efficiency Input (YPRR) |

## 2. Fields Allowed for Step 0 Review ONLY
These fields may be exported and stored in Step 0/rubric artifacts as `context_signal`. **They must not enter Engine A/B training** unless a later, explicit specification changes their source registry status.
*   `targets_per_route_run` / `TPRR`
*   `YAC_per_reception`
*   `contested_catch_rate`
*   `drop_rate`

## 3. PROHIBITED Fields (Machine Learning Hard Ban)
The following proprietary PFF *grades* are **strictly prohibited from Engine A/B feature matrices and promotion evidence.** They are diagnostic only and must not be used as model inputs:
*   ❌ `overall_grade` / `pff_grade`
*   ❌ `receiving_grade`
*   ❌ `run_block_grade` / `pass_block_grade`
*   ❌ `pff_route_grade`

## 4. Required Provenance/Metadata (Sidecar Manifest)
Since PFF UI exports do not allow appending custom columns, every manual CSV export must be accompanied by a companion manifest (e.g., `pff_export_manifest.json`) containing:
*   `export_author`: (e.g., "David")
*   `export_timestamp`: ISO 8601 format.
*   `pff_data_version`: The specific version/date of the PFF database at the time of export.
*   `export_notes`: Any specific filters applied (e.g., "Filtered to 2018-2025 drafted TEs").

## 5. Synthetic Fixture & Redaction Rules
To maintain repository hygiene and respect PFF license terms:
1.  **Redaction:** Real `player_id` (PFF-specific) and `player_name` combinations must not be committed. 
2.  **Synthetic Mapping:** For parser tests, use scrambled names (e.g., "TE_Prospect_A") and high-offset IDs.
3.  **Prohibited Commitment:** Raw `.csv` files from the PFF consumer dashboard are **gitignored** and must live only in local ignored paths or governed bronze storage.

## 6. Minimal Synthetic Fixture Shape (Parser Tests)

**`synthetic_pff_te.csv`**
```csv
player_id,player_name,team_name,draft_year,season,position,routes,slot_routes,wide_routes,inline_routes,targets,receptions,yards
999901,TE_Alpha,Iowa,2024,2023,TE,150,15,5,130,25,18,180
999902,TE_Beta,Georgia,2024,2023,TE,320,180,40,100,85,62,920
```

**`synthetic_pff_manifest.json`**
```json
{
  "export_author": "Gemini",
  "export_timestamp": "2026-05-15T19:00:00Z",
  "pff_data_version": "2026.1-collegiate",
  "export_notes": "Synthetic fixture representing expected export shape."
}
```

## 7. Recorded Export Decisions

1. **Export Source:** Use the PFF **Premium Stats** dashboard as the primary source. The Draft Guide is a fallback only if Premium Stats does not expose the needed collegiate TE route/alignment fields.
2. **Snapshot Timing:** Use **final collegiate season only** as the primary export window. Career totals may be retained as optional context, but they are not the primary archetype signal.
3. **Participation vs. Routes:** Prefer route-based fields: `slot_routes`, `wide_routes`, `inline_routes`, and `routes`. Snap-based fields are acceptable only when route-alignment fields are unavailable.
