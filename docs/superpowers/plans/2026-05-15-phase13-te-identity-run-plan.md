---
document: Phase 13 TE Identity Coverage Run Plan
task: 13.3 (gates Task 13.3.1)
status: READY_FOR_EXECUTION
date: 2026-05-15
owner: David
prepared_by: Claude Code
governance:
  - docs/governance/02-agent-operating-loop.md
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - docs/identity/identity_contract.md
  - docs/validation/phase13-pff-feasibility-memo.md
  - docs/superpowers/specs/2026-05-15-phase13-final-spec.md
---

# Phase 13 TE Identity Coverage Run Plan

## Purpose

Establish that Dynasty Genius can deterministically resolve every TE drafted between 2018 and 2025 to a canonical `player_id` before any PFF/college rows enter feature materialization.

This run plan gates Task 13.3.1. No rubric labeling, PFF field materialization, or TE archetype work may begin until the 2018–2025 drafted TE cohort passes the ≥98% resolved coverage threshold described below.

This document is a run plan and gap report, not an implementation spec. No code changes, no Engine A/B changes, no model promotion.

---

## 1. Denominator Definition

The denominator is **all TEs drafted in the NFL Draft, classes 2018 through 2025, in any round**.

### Rules

- Include every player listed as `TE` at time of draft regardless of position they later play or whether they ever saw a snap.
- Include players who retired before their rookie season, washed out immediately, or are classified as blocking-only in any source.
- Do **not** filter on fantasy relevance, snap count, or target share before running the gate. A secondary fantasy-relevance denominator may be reported as context, but the primary gate uses the full draft cohort.
- Undrafted free agents are out of scope for this drafted-TE denominator. If a UDFA appears in PFF or other source data later, report it in the gap/failure report rather than adding it to this gate.

### Estimated Cohort Size

Historical NFL drafts select roughly 18–28 TEs per class across all rounds. The 2018–2025 window spans 8 draft classes. Expected denominator: approximately 150–220 players. The exact count must be established from the authoritative source during cohort assembly (Step 2 below).

---

## 2. Required Inputs

All inputs must be version-stamped and cited in the run artifacts. If an input is unavailable or stale, the run must not proceed.

| Input | Source | Notes |
|---|---|---|
| 2018–2025 drafted TE cohort roster | nflverse draft data or nflfastR draft table; cross-check Sleeper historical player list | Primary denominator. Must include all rounds. |
| `ff_playerids` crosswalk | `nflreadr::load_ff_playerids()` | gsis_id → sleeper_id, pff_id, pfr_id, espn_id, yahoo_id, etc. Pull fresh at run time; record the pull timestamp. |
| Sleeper `/v1/players/nfl` passthrough | Sleeper API at run time | Needed for 2022–2025 rookies who have a sleeper_id but may lack a gsis_id in the crosswalk. |
| Existing `prospect_alias_bridge.json` | `app/data/prospect_alias_bridge.json` | Covers known rookie aliases. Check for TE entries; extend if gaps found. |
| Identity override registry | `app/data/identity/identity_override_registry.json` (create if absent) | Approved manual overrides with author, timestamp, reason, confidence, evidence, and status fields. |
| PFF CSV identity fields | Manual export — `pff_id`, `player_name`, `college`, `draft_year` | Optional at first run; include if the CSV sample from Task 13.3.0 blockers is resolved. Treat `pff_id` as an additional evidence column only; do not use it as the resolution key. |
| Source timestamps | Recorded at pull time | Required in every artifact; not optional. |

---

## 3. Cohort Assembly: Building IdentityAuditRow Records

The cohort fixture is a JSON file consumed by `scripts/run_identity_audit.py`. The file format is:

```json
{
  "entries": [
    {
      "cohort":       "historical_te",
      "name":         "Travis Kelce",
      "position":     "TE",
      "draft_year":   2013,
      "college":      "Cincinnati",
      "date_of_birth": "1989-10-05",
      "player_id":    null,
      "sleeper_id":   "3164",
      "gsis_id":      "00-0029630",
      "pff_id":       "6702",
      "pfr_id":       "KelcTr00",
      "espn_id":      null,
      "yahoo_id":     null,
      "sportradar_id": null,
      "fantasypros_id": null,
      "rotowire_id":  null,
      "fantasy_data_id": null
    }
  ]
}
```

### Assembly Steps

1. Pull the nflverse draft table for years 2018–2025. Filter to `position == "TE"`. This is the primary denominator.
2. For each player, fill every source-ID field available from `ff_playerids` (keyed on `gsis_id`).
3. For players missing `gsis_id` (typically 2023–2025 rookies with limited nflverse coverage), pull Sleeper `/v1/players/nfl` and populate `sleeper_id` and any Sleeper-native ID fields.
4. Check `prospect_alias_bridge.json` for alias entries covering the TE cohort; merge `sleeper_id` where the bridge has a match.
5. Set `cohort` to `"historical_te"` for all rows.
6. Set `player_id` to null unless Dynasty Genius already has a canonical ID for the player in its Silver layer. Do not generate new `player_id` values during cohort assembly.
7. Include `date_of_birth` where available — it powers Stage 5 (composite deterministic key).
8. Null fields are acceptable. Never fabricate an ID value; prefer null to a guess.
9. Write the assembled fixture to a path that is **not committed to the repo** (e.g., `app/data/identity/_runs/te_cohort_2018_2025.json`). This path is in `.gitignore`. Check-in a synthetic/redacted sample only if needed for test coverage.

---

## 4. Audit Command

Using the existing CLI (`scripts/run_identity_audit.py`):

```bash
.venv/bin/python3.14 scripts/run_identity_audit.py \
  --cohort app/data/identity/_runs/te_cohort_2018_2025.json \
  --ff-playerids app/data/identity/_runs/ff_playerids_<date>.json \
  --alias-bridge app/data/prospect_alias_bridge.json \
  --out-dir app/data/identity/_runs \
  --run-id te_2018_2025_<YYYYMMDD>
```

The script writes two artifacts:

- `app/data/identity/_runs/identity_coverage_matrix_{run_id}.json`
- `app/data/identity/_runs/identity_review_queue_{run_id}.jsonl`

These paths are untracked (add `app/data/identity/_runs/` to `.gitignore` if not already present). A passing run's snapshot must then be manually promoted to the governed artifact path (see Section 6).

### Limitation: CLI does not expose all lookup tables

The current `run_identity_audit.py` CLI accepts `--ff-playerids` and `--alias-bridge` but does not expose `--composite-registry` or `--prospect-registry` flags. The Python API (`run_audit()`) supports these tables via keyword arguments. For the first run, Stages 5 and 6 of the cascade will not fire unless the script is extended or the audit is invoked directly in Python. This is a known gap (see Section 9).

---

## 5. Required Artifacts

The run is not considered complete until all of the following exist:

| Artifact | Path (governed) | Description |
|---|---|---|
| `identity_coverage_matrix_{run_id}.json` | `app/data/identity/` | Coverage matrix including cohort summary, row count, duplicate conflicts, and run metadata. |
| `identity_review_queue_{run_id}.jsonl` | `app/data/identity/` | One JSONL line per unresolved row. Must include name, position, cohort, draft_year, all source IDs that were tried, resolution stage reached, and notes. |
| `identity_failure_report_{run_id}.md` | `app/data/identity/` | Human-readable summary of unresolved rows grouped by failure mode (no gsis_id, alias not found, composite key missing DOB, etc.). See Section 7 for structure. |
| `identity_snapshot_{run_id}.json` | `app/data/identity/` | Immutable point-in-time ID map for the passing run. All resolved rows. One entry per player. Once written and committed, the snapshot content must not be altered retroactively. |
| PFF materialization eligibility manifest | `app/data/identity/pff_te_eligible_{run_id}.json` | List of canonical player_ids eligible for PFF/college row join: rows where `r.resolved is True` (deterministic, Stages 1–6) plus override registry entries with `review_status == "APPROVED"` (manual). Only produced after the gate passes. |

The `_runs/` directory is untracked working storage. The governed `app/data/identity/` directory holds promoted artifacts from passing runs only. Because these artifacts may contain DOBs and source-native IDs, promote only sanitized summaries by default; commit raw identity snapshots or source-ID-heavy artifacts only after David explicitly approves the exposure.

---

## 6. Pass / Fail Criteria

The gate passes if **all** of the following are true:

| Criterion | Threshold | Notes |
|---|---|---|
| TE cohort resolved percentage | ≥ 98% | `CohortCoverage.resolved / total` for the `historical_te` cohort. |
| All drafted TEs in denominator | 100% | Every player from the nflverse draft table appears as an input row. No silent omissions. |
| Row count preserved | `total_input_rows == total_output_rows` | The `CoverageMatrix.row_count_preserved` property must be True. |
| No duplicate non-null IDs | 0 duplicate conflicts | `matrix.duplicate_conflicts` must be empty. Any shared player_id, sleeper_id, or gsis_id across distinct players is a hard failure. |
| Unresolved rows fully documented | All review_queue rows written | Every unresolved row must appear in `identity_review_queue_{run_id}.jsonl`. No row may be silently dropped. |
| Fuzzy candidates review-only | Not auto-resolved | No fuzzy match may produce a Stage 1–6 resolution. Fuzzy candidates appear only as review queue notes. |
| Override registry integrity | All manual overrides include required fields | author, timestamp, reason, confidence, evidence, status. |
| Identity snapshot generated | File exists and is non-empty | Generated only after all other criteria pass. |

To check the 98% gate programmatically using the existing utility:

```python
from src.dynasty_genius.audit.identity_coverage_matrix import CohortCoverage

# After run_audit():
te_cov = next(c for c in matrix.cohort_summary if c.cohort == "historical_te")
gate_passes = te_cov.passes_gate(max_loss_rate=0.02)  # 2% loss rate = 98% threshold
```

---

## 7. Failure Remediation Flow

When the gate fails, work through this sequence before re-running:

### Step 1 — Triage the review queue by failure mode

Open `identity_review_queue_{run_id}.jsonl`. Group rows by the `stage` field:

| Stage reached | Interpretation | Remediation |
|---|---|---|
| `ff_playerids_crosswalk` not reached | No gsis_id and not in alias bridge or composite registries | Check if the player has a gsis_id in nflverse that was missing from the cohort fixture; add it and re-run. |
| `sleeper_passthrough` not reached | sleeper_id absent or not in passthrough | Pull Sleeper `/v1/players/nfl` and check for the player; if found, add sleeper_id to the cohort fixture. |
| `prospect_alias_bridge` not reached | Name/position/draft_year key not in bridge | Add an entry to `prospect_alias_bridge.json` with a sleeper_id, or write an override registry entry. |
| `composite_name_dob` not reached | DOB missing from cohort fixture | Add DOB from a licensed reference source; re-run. |
| `composite_name_college` not reached | College missing or mismatched | Correct the college field; re-run. |
| `review_queue` (terminal) | All 6 deterministic stages exhausted | Player requires a manual override with full evidence. Write the override registry entry; re-run. |

### Step 2 — Write override registry entries for manual resolutions

Each entry in `app/data/identity/identity_override_registry.json`:

```json
{
  "overrides": [
    {
      "canonical_player_id": "canonical_pid_here",
      "assertions": {
        "sleeper_id": "12345",
        "gsis_id": "00-00XXXXX",
        "pff_id": "99999"
      },
      "evidence": {
        "source_row": "te_cohort_2018_2025.json:Player Name",
        "note": "Verified via Sleeper player page and PFF profile match; same DOB, college, and draft class."
      },
      "metadata": {
        "author": "David",
        "timestamp": "2026-05-15T00:00:00Z",
        "reason": "Player lacks gsis_id in nflverse draft table; sleeper_id confirmed via API response.",
        "confidence": "HIGH",
        "review_status": "APPROVED"
      }
    }
  ]
}
```

Fuzzy match candidates may be noted as review evidence but must not be committed as resolutions without human sign-off.

### Step 3 — Re-run the audit

After updating cohort fixture, alias bridge, or override registry, re-run the audit with the same `--run-id` prefix plus an iteration suffix (e.g., `te_2018_2025_20260515_r2`). Do not overwrite a prior run's artifacts.

### Step 4 — Promote to governed path

When the gate passes:

1. Copy the four required artifacts from `_runs/` to `app/data/identity/`.
2. Write the PFF materialization eligibility manifest.
3. Mark the snapshot as immutable — do not modify it after commit.
4. Record the passing run ID in `AGENT_SYNC.md` and the daily ledger.

---

## 8. What Must Be True Before Task 13.3.1

Task 13.3.1 (TE archetype rubric labeling and PFF field materialization) may not begin until:

1. The identity coverage gate has passed (≥98% resolved, all criteria in Section 6 met).
2. `identity_snapshot_{run_id}.json` exists, is committed, and is marked immutable.
3. `pff_te_eligible_{run_id}.json` exists and lists the materialization-eligible player_ids.
4. The passing run ID is recorded in `AGENT_SYNC.md`.
5. A real PFF collegiate TE CSV sample/schema has been provided and locked (Blocker 1 from the PFF feasibility memo).
6. David has confirmed that PFF CSV export is acceptable for Step 0 (Open Decision 4 from the Phase 13 final spec).

If the PFF CSV sample is not yet available when the identity gate passes, record the gate result and wait. Do not begin rubric labeling with synthetic data.

---

## 9. Gaps in Current Utilities

These gaps must be addressed before or during the run. None require David approval — they are scoped implementation tasks.

| Gap | Severity | Resolution |
|---|---|---|
| CLI does not expose `--composite-registry` or `--prospect-registry` flags | Medium | Extend `run_identity_audit.py` to accept these optional JSON fixture paths. The Python API already supports them. Add loaders following the same pattern as `_load_ff_playerids`. |
| CLI always exits non-zero if any rows are unresolved | Low | The current exit-1-on-any-unresolved behavior is intentionally strict. For Phase 13 the gate is ≥98%, not 100%. Consider adding a `--max-loss-rate` flag; the existing `CohortCoverage.passes_gate()` helper already supports this. |
| CLI does not call the existing `identity_snapshot` generator | Medium | `src/dynasty_genius/audit/identity_snapshot_generator.py` exists and refuses overwrite. The CLI writes coverage matrix and review queue only. Extend the CLI to call the generator after a passing run, or invoke the generator as a separate post-run step. |
| No `identity_failure_report` writer | Medium | Add a Markdown failure report writer grouping unresolved rows by terminal resolution stage. The coverage matrix has the data; the failure report is the human-readable surface. |
| No `pff_te_eligible` manifest writer | Medium | Add a post-gate step that filters results to `r.resolved is True` (deterministic) plus override registry entries with `review_status == "APPROVED"` (manual), then writes the eligibility manifest. |
| Sleeper passthrough is derived from `ff_playerids` file, not a separate source | Low | The current `_load_sleeper_passthrough` in the CLI indexes the same `ff_playerids` JSON by sleeper_id. For 2022–2025 rookies whose records are in Sleeper but not yet in nflverse, a separate Sleeper-native passthrough fixture may be needed. Document the gap in the failure report if it fires. |
| `app/data/identity/_runs/` not in `.gitignore` | Low | Add this path to `.gitignore` before the first run. Raw cohort fixtures may contain PII-adjacent data (DOB) and must not be committed. |
| No composite_registry or prospect_registry population step | Medium | The cascade Stages 5 and 6 require these tables. For the TE run, the composite prospect key `(normalized_name, college, pos, draft_year)` is especially relevant for 2022–2025 rookies with limited nflverse coverage. Populate from `ff_playerids` + nflverse draft data at assembly time. |

---

## 10. Execution Checklist

Before running:
- [ ] nflverse draft table pulled for 2018–2025; TE cohort extracted; row count confirmed.
- [ ] `ff_playerids` crosswalk pulled at run time; pull timestamp recorded.
- [ ] Sleeper `/v1/players/nfl` passthrough pulled for 2022–2025 TE cohort.
- [ ] `prospect_alias_bridge.json` reviewed for TE entries; gaps noted.
- [ ] `identity_override_registry.json` exists (empty is acceptable for first run).
- [ ] `app/data/identity/_runs/` added to `.gitignore`.
- [ ] CLI gaps from Section 9 resolved: at minimum, existing snapshot generator wired into the CLI/post-run flow and `--composite-registry` flag.

After gate passes:
- [ ] Coverage matrix promoted to `app/data/identity/`.
- [ ] Review queue promoted to `app/data/identity/`.
- [ ] Failure report promoted to `app/data/identity/`.
- [ ] Identity snapshot promoted to `app/data/identity/` and marked immutable.
- [ ] PFF materialization eligibility manifest written to `app/data/identity/`.
- [ ] Passing run ID recorded in `AGENT_SYNC.md`.
- [ ] Ledger entry written with: run_id, cohort size, resolved count, loss rate, unresolved count, override count.
- [ ] PFF CSV sample confirmed available (Blocker 1 from feasibility memo) before assigning Task 13.3.1.
