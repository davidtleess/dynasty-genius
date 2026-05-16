---
document: Phase 13.3.1 TE Archetype Rubric — Gemini Design Memo
task: 13.3.1
status: DESIGN_MEMO
date: 2026-05-16
prepared_by: Gemini
governance:
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - docs/superpowers/specs/2026-05-15-phase13-final-spec.md
  - docs/validation/phase13-pff-feasibility-memo.md
inputs:
  - app/data/identity/pff_te_export_schema_report_20260516.json
  - app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json
---

# Phase 13.3.1 TE Archetype Rubric — Design Memo (Gemini)

## 1. Executive Recommendation

**Proceed with Step 0 labeling for the 110 resolved players in the 2018–2025 drafted TE cohort.** The 6 missing players should be explicitly excluded from the analytical taxonomy to maintain high data fidelity.

This rubric utilizes **Snap-Alignment percentages** as the primary classifier. While Route-Alignment is theoretically superior, current PFF data availability necessitates the use of snap counts as a high-fidelity proxy for offensive role assignment. This is a **diagnostic artifact only**; it provides context for human review and does not modify the predictive feature set or Ridge coefficients.

---

## 2. Archetype Taxonomy & Labeling Status

To ensure analytical clarity, we separate the human-readable **Archetype** from the operational **Labeling Status**.

### 2.1 Archetype (The Analytical Label)
| Label | Criteria Goal |
|---|---|
| `receiving_leaning` | Capture move-TEs and slot specialists with high receiving ceilings. |
| `blocking_leaning` | Identify attached blockers likely to have low fantasy production. |
| `ambiguous` | Capture hybrid players or those in scheme-dependent roles. |
| `null` | No archetype possible (due to low volume or missing data). |

### 2.2 Labeling Status (The Operational State)
| Status | Definition |
|---|---|
| `labeled` | Successfully assigned an archetype. |
| `low_volume` | Below the 100-snap alignment threshold. |
| `invalid_alignment` | Zero snaps found; data integrity failure. |
| `excluded` | Player missing from PFF export coverage (`NO_PFF_DATA`). |

---

## 3. Exact Objective Thresholds

### 3.1 Prerequisite Derived Calculation
Since a global "total snaps" field is unreliable in manual exports, we define the denominator locally:
`alignment_snap_total = inline_snaps + slot_snaps + wide_snaps`

### 3.2 Mandatory Sample Guard
Before assigning an archetype, the row must pass the alignment floor:
`if alignment_snap_total < 100:`
`  labeling_status = "low_volume", archetype = null`

### 3.3 Archetype Decision Logic
Apply the following rules sequentially to all rows passing the sample guard:

1.  **Receiving Trigger**:
    `Detached_Rate = (slot_snaps + wide_snaps) / alignment_snap_total`
    `if Detached_Rate >= 0.40: archetype = "receiving_leaning"`
2.  **Blocking Trigger**:
    `Inline_Rate = inline_snaps / alignment_snap_total`
    `elif Inline_Rate >= 0.70: archetype = "blocking_leaning"`
3.  **Default**:
    `else: archetype = "ambiguous"`

### 3.4 Context Signals (Secondary Flags)
These signals do not drive the label but are included in the artifact for David's review:
*   **Elite Prior**: `yprr_computed >= 1.80` (Flag as `elite_efficiency_prior`).
*   **Target Concentration**: `targets / routes` (TPRR).

---

## 4. Snap-Alignment Fallback Treatment

All classification in Task 13.3.1 is performed using **Snap-Alignment** fields. This is documented as a `snaps_fallback` due to the absence of Route-Alignment data.
*   **Measurement Error Disclosure**: Every labeled row must contain `threshold_basis: "snap_counts"`.
*   **Constraint**: Snap-alignment capture's a coach's *intent* to use a player in a specific formation, which is a valid but noisier signal than route-level participation.

---

## 5. Handling the 6 Missing PFF Rows

The 6 players missing from PFF coverage (2018: 1, 2020: 2, 2021: 1, 2022: 1, 2023: 1) are treated as **Structural Gaps**.
*   **Policy**: No imputation from public sources.
*   **Artifact Mapping**: `archetype: null`, `labeling_status: "excluded"`, `coverage_status: "pff_alignment_missing"`.
*   **Justification**: These are typically FCS or small-school prospects where PFF tracking was unavailable. Inferring their role from box scores would violate the "Objective Alignment" mandate.

---

## 6. Artifact Schema Recommendation

The committed artifact should be a JSON file keyed by **canonical `player_id`** to ensure 100% joinability with the identity snapshot.

```json
{
  "player_id": "dg_te_12345",
  "labeling_status": "labeled",
  "archetype": "receiving_leaning",
  "metrics": {
    "alignment_snap_total": 342,
    "detached_rate_from_snaps": 0.425,
    "inline_rate_from_snaps": 0.575,
    "yprr_computed": 1.92
  },
  "flags": {
    "elite_efficiency_prior": true
  },
  "metadata": {
    "alignment_source": "snaps_fallback",
    "selected_season": 2023,
    "draft_year": 2024
  }
}
```

---

## 7. Sensitivity-Check Recommendation

The runner script should perform an automated **Threshold Distribution Analysis** comparing the following scenarios:
*   **Aggressive**: Receiving at `>= 0.40`
*   **Conservative**: Receiving at `>= 0.45`
*   **Outcome**: Report the number of players who shift from `receiving_leaning` to `ambiguous` between these two settings. This log will be used to finalize the "Gesicki Threshold" in Step 1 review.

---

## 8. Risks and Failure Modes

*   **Formation Noise**: Spread offenses may line up "blocking" TEs wide or in the slot simply due to personnel packages (11 personnel ubiquity). *Mitigation: 100-snap alignment guard and elite YPRR flag for context.*
*   **Identity Corrsive**: Incorrect mapping of PFF ID to DG ID. *Mitigation: Identity Audit (13.1) and eligibility manifest requirement.*

---

## 9. Acceptance Criteria for Task 13.3.1

1.  **Redacted JSON Artifact**: Exists for all 116 players, keyed by `player_id`.
2.  **Privacy Compliance**: Zero player names or raw PFF IDs appear in the committed artifact.
3.  **Traceability**: Every label is reproducible using the `alignment_snap_total` logic and private CSV inputs.
4.  **No Grades**: Proof that no proprietary PFF grades were used for classification.
5.  **Audit Match**: Row count (116) matches the canonical eligibility manifest.

---

## 10. Differences vs Claude

After reviewing `phase13-3-1-archetype-rubric-claude.md`, the following distinctions exist:

*   **Threshold Math**: Claude proposes a strict **greater than** (`> 0.40`), whereas I propose **greater than or equal to** (`>= 0.40`). I recommend `>=` to align with standard statistical binning conventions.
*   **Minimum Guard**: We both agree on the **100 alignment snap** floor.
*   **Upside Flag**: Claude proposes a relative **p75 cohort threshold** for the `upside_caveat`. I propose a fixed **1.80 YPRR anchor** based on historical elite prospect benchmarks. I believe a fixed anchor is more stable for cross-positional evaluation.
*   **Taxonomy Naming**: Claude uses `NO_PFF_DATA` and `INSUFFICIENT_SAMPLE` as top-level labels. I propose separating these into a `labeling_status` field to keep the `archetype` field purely for analytical classes.
*   **Missing Row Handling**: Claude labels missing rows as `NO_PFF_DATA`. I include a `coverage_status` field to explicitly mark them as `pff_alignment_missing`.
*   **Sensitivity Check**: I explicitly recommend a **comparison log** between 0.40 and 0.45 thresholds to inform the final decision.
