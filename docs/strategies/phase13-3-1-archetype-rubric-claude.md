---
document: Phase 13.3.1 TE Archetype Rubric — Claude Design Memo
task: 13.3.1
status: DESIGN_MEMO
date: 2026-05-16
prepared_by: Claude Code
governance:
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - docs/superpowers/specs/2026-05-15-phase13-final-spec.md
  - docs/validation/phase13-pff-feasibility-memo.md
inputs:
  - app/data/identity/pff_te_export_schema_report_20260516.json
  - src/dynasty_genius/adapters/pff_te_export.py
  - app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json
---

# Phase 13.3.1 TE Archetype Rubric — Design Memo (Claude)

## 1. Executive Recommendation

**Proceed with rubric labeling using 110 of 116 drafted TEs.** The 6 missing rows are excluded from label assignment with explicit `NO_PFF_DATA` status. Do not impute, interpolate from public sources, or use fuzzy-fill for missing rows.

The rubric should use **snap-alignment percentages** as the primary classifier, derived from `inline_snaps`, `slot_snaps`, and `wide_snaps`. `YPRR` — computable as `yards / routes` — should function as an upside caveat flag only, never as a label trigger.

This is a **Step 0 artifact**, not a model input. The output is a labeled sample for human review and decision-making, not a training feature. Every inference should be flagged explicitly. No label assignment should carry more weight than its input data warrants.

The critical caveat that distinguishes this memo's position: **snap alignment and route alignment are different things.** Every threshold in this rubric is calibrated against snap counts. If route-alignment data becomes available later, the thresholds should be re-evaluated before any label is promoted to model use.

---

## 2. Proposed Archetype Taxonomy

Three labels for Step 0 (unchanged from Phase 13 final spec):

| Label | Meaning |
|---|---|
| `receiving_leaning` | TE lines up detached (slot or wide) for a majority of snaps; typical move-TE or pass-catching specialist profile |
| `blocking_leaning` | TE lines up inline for a majority of snaps; blocking-first profile, receiving is secondary |
| `ambiguous` | Neither threshold fires clearly; mixed-role or scheme-dependent usage |

Two non-label statuses for Step 0 processing:

| Status | Meaning |
|---|---|
| `NO_PFF_DATA` | No PFF export row found for this player; excluded from archetype assignment |
| `INSUFFICIENT_SAMPLE` | Player has PFF data but snap count below minimum sample threshold; label withheld |

`NO_PFF_DATA` and `INSUFFICIENT_SAMPLE` players must appear in the labeled sample output but with null archetype labels. They must not be silently omitted.

---

## 3. Exact Objective Thresholds

### 3.1 Derived Fields

From the parser output (`pff_te_export.py`), each row contains:

```
inline_snaps    — alignment snaps as inline TE
slot_snaps      — alignment snaps from slot
wide_snaps      — alignment snaps split wide
routes          — total routes run (separate from alignment snaps)
targets         — target count
receptions      — reception count
yards           — receiving yards
context_signals — optional dict (may contain: yprr, contested_catch_rate, drop_rate, yac_per_reception)
```

Compute these derived fields before applying any threshold:

```
total_alignment_snaps  = inline_snaps + slot_snaps + wide_snaps
slot_wide_snap_pct     = (slot_snaps + wide_snaps) / total_alignment_snaps
inline_snap_pct        = inline_snaps / total_alignment_snaps
yprr_computed          = yards / routes   (only when routes is not null and routes > 0)
catch_rate             = receptions / targets   (only when targets > 0)
```

### 3.2 Minimum Sample Guard

Apply before any archetype label:

```
if total_alignment_snaps < 100:
    label = INSUFFICIENT_SAMPLE
    stop — do not compute percentages or apply thresholds
```

The 100-snap floor is a Step 0 candidate threshold, not production law. It should be checked against the actual cohort distribution — if many labeled TEs cluster near 100 snaps, this floor may need adjustment. Flag any player with 80–120 snaps as `near_threshold = True` in the output.

### 3.3 Label Assignment

Apply in this exact order after the sample guard passes:

```
if slot_wide_snap_pct > 0.40:
    label = receiving_leaning

elif inline_snap_pct > 0.60:
    label = blocking_leaning

else:
    label = ambiguous
```

**Priority rule**: `receiving_leaning` takes precedence when both thresholds could theoretically fire. Mathematically the two can coexist only at the boundary (slot_wide_pct exactly 0.40, inline_pct exactly 0.60). The strict `>` for both thresholds means neither fires at the exact boundary, which correctly yields `ambiguous`. Do not use `>=` for both — pick one.

**Recommendation**: Use `> 0.40` for receiving trigger, `> 0.60` for blocking trigger, exact-boundary cases yield `ambiguous`. This is the cleanest and most defensible form.

### 3.4 Upside Caveat Flag

A separate boolean flag `upside_caveat`, not a label modifier:

```
if label in (blocking_leaning, ambiguous):
    if yprr_computed is not None:
        if yprr_computed >= cohort_yprr_p75:
            upside_caveat = True
```

Where `cohort_yprr_p75` is the 75th percentile of `yprr_computed` across all players in the labeled sample who have a non-null `yprr_computed`. This is a within-cohort relative threshold, not an absolute number, because we do not have established YPRR benchmarks for collegiate snap-based data.

`upside_caveat` is never applied to `NO_PFF_DATA` or `INSUFFICIENT_SAMPLE` players.

`upside_caveat` is never applied to `receiving_leaning` players — the flag exists to surface receiving upside for players whose snap alignment undersells their pass-catching role. A player already labeled `receiving_leaning` does not need the caveat.

---

## 4. Snap-Alignment Fallback vs. Route-Alignment Ideal

This is the most important caveat in the rubric. All 9 PFF export files are classified `snaps_fallback` in the parser — meaning the alignment columns (`inline`, `slot`, `wide`) are snap counts, not route counts.

**What snap alignment tells us:** Where the TE lined up at the snap of the ball. This is the standard "formation alignment" measure. It captures how the offense schematically deployed the TE.

**What route alignment would tell us:** From which formation position the TE actually ran routes. A TE who lines up inline but frequently motions to slot before the snap would register as inline-heavy in snap alignment but slot-heavy in route alignment.

**Implication for thresholds:** The 0.40 / 0.60 thresholds in the Phase 13 final spec and feasibility memo were described in terms of `slot_wide_route_pct` and `inline_blocking_rate`. These were route-based concepts. We are applying them to snap-based data. This is directionally valid but introduces measurement error.

**Required disclosure in every labeled output row:**
```
alignment_source: "snaps_fallback"
threshold_basis: "snap_counts"
threshold_caveat: "Thresholds calibrated for snap-based denominator. Route-alignment data unavailable in current PFF export set."
```

**Recommendation for David**: If a future PFF export set provides route-alignment fields (`inline_routes`, `slot_routes`, `wide_routes`), the labeled sample should be regenerated against those fields before any label is used for anything beyond Step 0 review.

---

## 5. Season Selection — Final College Season Only

Each drafted TE may appear in multiple season files. Select exactly one season per player:

1. **Primary**: Use the season with `season = draft_year - 1` (final college season before draft).
2. **Fallback**: If no data for `draft_year - 1`, use `draft_year - 2`.
3. **No further fallback**: If neither season has data, label as `INSUFFICIENT_SAMPLE` (not `NO_PFF_DATA`).
4. Record `selected_season` in the output for every labeled player.

**Do not aggregate across seasons.** Aggregating yards/routes/snaps across multiple years conflates different scheme contexts and different physical development stages. A player's final college season best represents them as evaluated at draft time — which is what PFF collegiate data is used for here.

**Early-entry players**: Some 2025 draftees played their final season in 2024. Their data appears in the 2024 season export (file 16, 16 matched). The season selection logic handles this correctly without special-casing if `draft_year - 1` is applied consistently.

---

## 6. Handling the 6 Missing PFF Rows

The 6 missing rows break down by draft year:

| Draft year | Missing count | Likely reason |
|---|---|---|
| 2018 | 1 | FCS/small-school — no PFF collegiate coverage |
| 2020 | 2 | FCS/small-school or early departure from tracked program |
| 2021 | 1 | FCS/small-school |
| 2022 | 1 | FCS/small-school |
| 2023 | 1 | FCS/small-school |

Treatment:
- Each missing player appears in the labeled sample output with `archetype: null`, `label_status: "NO_PFF_DATA"`.
- `likely_missing_reason` is `"pff_collegiate_coverage_gap_fcs_or_small_school"` — recorded as probable, not confirmed per-player.
- Do not query public sources (cfbfastR, PlayerProfiler, PFR) to fill in missing rows for archetype assignment. Public fallback sources can be mentioned as context in a separate gap report, but they may not substitute for PFF alignment fields as archetype triggers.
- These 6 players are eligible for the identity manifest but excluded from archetype labeling.
- The labeled sample must clearly distinguish `NO_PFF_DATA` (no PFF coverage) from `INSUFFICIENT_SAMPLE` (PFF coverage exists but below snap threshold).

---

## 7. QA Checks and Failure Modes

Required QA checks on the labeled sample output before Task 13.3.1 is considered complete:

| Check | Pass condition | Failure mode |
|---|---|---|
| Row count | Exactly 116 rows (110 labeled/status + 6 NO_PFF_DATA) | Missing rows or duplicates |
| Unique player_ids | All 116 are distinct | Duplicate canonical IDs — investigate identity backfill |
| No null snaps for labeled rows | `inline_snaps`, `slot_snaps`, `wide_snaps` all non-null for all players with `label_status != NO_PFF_DATA` | Parser gap — re-export needed |
| Snap total sanity | `total_alignment_snaps == inline + slot + wide` within 1 (float tolerance) | Rounding/parsing error |
| Percentage sum | `slot_wide_snap_pct + inline_snap_pct == 1.0` within 0.001 | Division error |
| YPRR sanity | `0 <= yprr_computed <= 8.0` for all non-null values | Implausible — investigate raw data |
| Catch rate sanity | `0 <= catch_rate <= 1.0` for all non-null values | Divide by zero or data error |
| Label exhaustiveness | Every row has exactly one of: `receiving_leaning`, `blocking_leaning`, `ambiguous`, `INSUFFICIENT_SAMPLE`, `NO_PFF_DATA` | Missing label logic branch |
| Upside caveat scope | `upside_caveat == True` only on `blocking_leaning` or `ambiguous` rows | Applied incorrectly to receiving or non-label rows |
| Grade columns absent | No `grade`, `grades_*` field in any output row | Parser not stripping grades |
| Player names absent | No raw PFF player name in any committed output artifact | Privacy/redaction failure |
| Alignment source documented | Every labeled row has `alignment_source: "snaps_fallback"` | Missing disclosure |

---

## 8. Acceptance Criteria for Task 13.3.1

Task 13.3.1 is accepted when:

1. Labeled sample file exists for all 116 players (110 with label or status, 6 with `NO_PFF_DATA`).
2. Each labeled player has: `player_id`, `draft_year`, `selected_season`, `archetype`, `label_status`, `inline_snap_pct`, `slot_wide_snap_pct`, `total_alignment_snaps`, `alignment_source`, `yprr_computed` (or null), `upside_caveat`.
3. All QA checks in Section 7 pass.
4. No PFF grade field appears in any committed artifact.
5. No raw player names appear in any committed artifact.
6. `alignment_source` is documented as `"snaps_fallback"` on every labeled row.
7. The 6 missing players appear with `label_status: "NO_PFF_DATA"` — not silently dropped.
8. Rubric version is recorded in the artifact metadata (e.g., `rubric_version: "0.1.0"`).
9. No Engine A or Engine B code is changed.
10. No model training occurs.
11. TE `model_grade` remains `EXPERIMENTAL`.
12. PFF fields remain `context_signal` in the source registry.
13. A brief gap report notes the 6 missing players and their probable reason.

---

## 9. Out-of-Scope Items

The following must not happen during Task 13.3.1:

- Using PFF grade columns (`grades_offense`, `grades_pass_block`, `grades_pass_route`, etc.) for any classification.
- Using public sources (cfbfastR, PlayerProfiler, combine data) as substitutes for missing PFF alignment data.
- Promoting TE out of `EXPERIMENTAL` status.
- Adding any PFF-derived field to Engine A or Engine B training features.
- Inferring archetypes for the 6 players with no PFF data.
- Using KTC, ADP, FantasyCalc, or any market signal.
- Assigning a four-archetype label (receiving specialist, big-slot hybrid, in-line receiving, blocking-first) — that taxonomy is deferred per Phase 13 final spec §8.
- Computing LOOCV or any validation against outcomes — Step 0 is labeling only.
- Writing code that ingests raw PFF CSVs from committed paths.

---

## 10. Open Decisions for David

1. **110/116 coverage acceptance**: Is 94.8% PFF coverage (110 of 116 drafted TEs) sufficient to proceed with Task 13.3.1 labeling, or is there a minimum coverage threshold below which the Step 0 rubric is not meaningful? The 6 missing players are likely FCS/small-school — pursuing them further may not be productive.

2. **Route-alignment upgrade path**: The 0.40/0.60 thresholds were designed for route-alignment data. Do you want to: (a) accept snap-alignment thresholds for Step 0 with explicit disclosure, then revisit with routes if a better PFF export becomes available; or (b) re-export with route-alignment fields before proceeding?

3. **YPRR upside caveat threshold**: Within-cohort 75th percentile (relative) vs. an absolute YPRR number. Since this is Step 0 review, relative is more defensible — but David may have a prior on what "elite" YPRR looks like for collegiate TEs.

4. **INSUFFICIENT_SAMPLE handling**: Should players who fall below 100 alignment snaps in their final college season be allowed a fallback to an older season for labeling? The current design says no — only `draft_year - 2` as a data fallback, but still subject to the 100-snap guard.

5. **Output format**: The labeled sample should be committed as a JSON file per the governance model. Should it be a redacted summary (no player names, just player_ids and labels) or a full Step 0 artifact with all computed fields? The latter is more useful for review; the former is cleaner for the repo.

6. **Gap report destination**: Should the 6 missing-player gap report be a section of the labeled sample output, a separate `identity_failure_report` supplement, or a standalone Step 0 memo?

---

## Appendix: Rubric Decision Tree (Pseudocode)

```python
def assign_archetype(row: dict) -> dict:
    """Apply the Step 0 TE archetype rubric to one parsed PFF row."""

    if row is None or row.get("pff_id") is None:
        return {"archetype": None, "label_status": "NO_PFF_DATA", "upside_caveat": False}

    inline = row.get("inline_snaps")
    slot = row.get("slot_snaps")
    wide = row.get("wide_snaps")

    if any(v is None for v in [inline, slot, wide]):
        return {"archetype": None, "label_status": "MISSING_SNAP_DATA", "upside_caveat": False}

    total = inline + slot + wide
    if total < 100:
        return {"archetype": None, "label_status": "INSUFFICIENT_SAMPLE",
                "total_alignment_snaps": total, "upside_caveat": False}

    slot_wide_pct = (slot + wide) / total
    inline_pct = inline / total

    routes = row.get("routes")
    yards = row.get("yards")
    yprr = (yards / routes) if (routes and routes > 0 and yards is not None) else None

    if slot_wide_pct > 0.40:
        label = "receiving_leaning"
        upside_caveat = False   # not applicable to receiving_leaning
    elif inline_pct > 0.60:
        label = "blocking_leaning"
        upside_caveat = _upside_caveat(yprr, cohort_yprr_p75)
    else:
        label = "ambiguous"
        upside_caveat = _upside_caveat(yprr, cohort_yprr_p75)

    return {
        "archetype": label,
        "label_status": "LABELED",
        "inline_snap_pct": round(inline_pct, 4),
        "slot_wide_snap_pct": round(slot_wide_pct, 4),
        "total_alignment_snaps": int(total),
        "alignment_source": "snaps_fallback",
        "yprr_computed": round(yprr, 3) if yprr is not None else None,
        "upside_caveat": upside_caveat,
        "threshold_caveat": (
            "Thresholds calibrated for snap-based denominator. "
            "Route-alignment data unavailable in current PFF export set."
        ),
    }


def _upside_caveat(yprr: float | None, p75: float | None) -> bool:
    if yprr is None or p75 is None:
        return False
    return yprr >= p75
```

`cohort_yprr_p75` is computed from all labeled rows with non-null `yprr_computed` after the sample pass — it is a cohort-level statistic, not per-player. Compute it in a two-pass approach: first label all rows, then compute the YPRR percentile, then apply the upside caveat flag.
