# CFBD published refresh — independent artifact measurement

Date: 2026-08-01  
Reviewer: Codex  
Run: `20260802T024342156864Z`  
Layer: 1 (source ingestion)  

## Verdict

**REFRESH ARTIFACT CLEAR.** The published status, manifest, raw snapshot, and
curated CSV reconcile internally, and the requested QB measurements independently
match Claude's report. This is an artifact verdict; the final post-edit full-suite
and tollgate census remains a separate pending report.

## Integrity and identity

- Status is `ok`; status and manifest both name run
  `20260802T024342156864Z`.
- Curated SHA-256 independently recomputes to
  `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`.
- Active-input SHA-256 independently recomputes to
  `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`,
  exactly the manifest's `input_sha256`; the active training CSV was not mutated.
- Curated output has 874 rows, 874 nonblank `gsis_id` values, 874 unique IDs,
  zero degraded rows, and the same GSIS order as the active input. QB count is
  126 in both.
- Raw inventory has 1,202 provider payloads plus the run-local `manifest.json`,
  hence 1,203 JSON directory entries. Excluding that metadata file, the count is
  exactly the manifest's 1,202 and the recomputed content hash is exactly
  `6270c8bc13dcce90358d6a2d79f1895c6c6afd5279c2249edfcc78ffee571679`.
  All 1,202 provider files decode as arrays of objects. The apparent 1,203/1,202
  difference is intentional accounting, not divergence.

## QB values, re-derived over 126 rows

| Field | Active populated | Published populated | Coverage | Published distinct | Distinct/populated | Published range |
|---|---:|---:|---:|---:|---:|---:|
| completion pct | 32 | 108 | 85.71% | 78 | 72.22% | 0.532–0.774 |
| yards/attempt | 32 | 108 | 85.71% | 42 | 38.89% | 5.6–11.7 |
| TD:INT ratio | 32 | 108 | 85.71% | 81 | 75.00% | 0.636364–15.0 |
| sack rate | 0 | 87 | 69.05% | 86 | 98.85% | 0.009634–0.120092 |

The three formerly populated active fields each have four distinct values over 32
rows (12.5%). Active completion percentage ranges from 0.0 to 0.00594. Every
published coverage fraction exactly matches the manifest; each missing flag and
CFBD source count complements the populated count (18 missing for the first three,
39 for sack rate).

## Collision and change checks

- Complete four-feature QB rows: 87.
- Season-scoped complete-vector groups: 87.
- Largest distinct-player group: 1; groups larger than one: 0.
- The 42-value YPA cardinality is therefore not collision evidence. Its one-decimal
  source precision is consistent with repeated scalar values, while the full
  season-scoped vectors remain injective across the complete cohort.
- QB identity sets are identical between active and curated files. 111/126 QB rows
  change at least one of the four values; 419 value cells change.

No active consumer reads the isolated curated path: repository consumers found by
path search still point at `app/data/training/prospects_with_outcomes_v3.csv`.
This review does not authorize or perform promotion.

## Reviewer actions

Read-only local artifact analysis only. No live request, refresh interaction,
production/test edit, active CSV mutation, promotion, model run, commit, or push.

