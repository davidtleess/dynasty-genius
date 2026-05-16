# Identity Artifact Schemas (Proposed)

This document defines the proposed JSON schemas for the Identity Audit Family of artifacts, as mandated by the Phase 13 Final Spec.

## 1. Coverage Matrix
**File Pattern:** `identity_coverage_matrix_{run_id}.json`

```json
{
  "run_id": "uuid-v4",
  "timestamp": "2026-05-15T12:00:00Z",
  "cohorts": [
    {
      "name": "2018-2025 Drafted TEs",
      "denominator": 342,
      "metrics": {
        "deterministic_coverage_pct": 0.982,
        "review_queue_pct": 0.015,
        "unmatched_pct": 0.003
      },
      "source_coverage": {
        "gsis_id": 338,
        "sleeper_id": 340,
        "pff_id": 335
      }
    },
    {
      "name": "Historical Backtest (10-Year)",
      "denominator": 1450,
      "metrics": {
        "deterministic_coverage_pct": 0.965,
        "review_queue_pct": 0.025,
        "unmatched_pct": 0.010
      }
    }
  ],
  "gates": {
    "te_98_percent_gate": "PASSED",
    "historical_95_percent_gate": "PASSED"
  }
}
```

## 2. Review Queue
**File Pattern:** `identity_review_queue_{run_id}.jsonl`

```json
{"candidate_id": "temp_001", "name": "John Doe", "position": "TE", "college": "Iowa", "draft_year": 2024, "fuzzy_candidates": [{"player_id": "dg_123", "score": 0.92, "reason": "Name + College match"}], "status": "PENDING"}
{"candidate_id": "temp_002", "name": "Jim Smith", "position": "RB", "college": "Georgia", "draft_year": 2023, "fuzzy_candidates": [], "status": "INSUFFICIENT_DATA"}
```

## 3. Override Registry
**File Pattern:** `app/data/identity_override_registry.json`

```json
{
  "overrides": [
    {
      "canonical_player_id": "dg_12345",
      "assertions": {
        "sleeper_id": "9876",
        "gsis_id": "00-0012345",
        "pff_id": "123"
      },
      "evidence": {
        "source_row": "PFF_Export_2024_TE.csv:Row_42",
        "note": "Verified manual mapping for prospect name collision."
      },
      "metadata": {
        "author": "Gemini",
        "timestamp": "2026-05-15T18:45:00Z",
        "reason": "Resolving collision with retired veteran of same name.",
        "confidence": "HIGH"
      }
    }
  ]
}
```

## 4. Identity Snapshot
**File Pattern:** `identity_snapshot_{run_id}.json`
*Note: This is an immutable capture of the current ID mapping state used for a specific backtest run.*

```json
{
  "run_id": "uuid-v4",
  "immutable": true,
  "mapping_version": "1.0.0",
  "mappings": {
    "dg_12345": {
      "gsis_id": "00-0012345",
      "sleeper_id": "9876",
      "pff_id": "123",
      "pfr_id": "DoeJo00"
    }
  }
}
```
