"""BUILD-4 T4 — shared rookie-QB risk filter (Engine A-facing, pre-NFL only).

The binary risk-filter BUILD-4 absorbed from the 2026-07-01 rookie fork.
Consumes PRE-NFL inputs ONLY — draft capital and age at NFL entry — with an
EXACT-SET input contract: any NFL-usage column is a leakage defect and fails
loudly (spec §4: no NFL usage leaks into Engine A). The filter's output never
enters Engine B training rows (the fork-A prior is derived separately inside
the candidate matrix builder from raw capital, not from this module).

The base-rate survival priors are REGISTERED constants v1, aligned with the
capital bands of the ratified fork-A rule and the regenerated 2018-2025
role-occupancy label data; recomputing them from the label table as a live
cohort artifact is T5-record work, not silent module drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

# EXACT-SET input contract: anything else is treated as attempted leakage.
ALLOWED_INPUT_COLUMNS = ("player_id", "position", "draft_number", "age_at_entry")

DAY3_PICK_THRESHOLD = 65

# Registered v1 base-rate survival priors by capital band (headline horizon 1).
BASE_RATE_SURVIVAL_PRIOR_V1 = {
    "capital_qualified": 0.63,
    "day3_insufficient_capital": 0.15,
    "undrafted_insufficient_capital": 0.05,
}

_BADGE_TEXT = {
    "capital_qualified": "capital qualified — no abstention",
    "day3_insufficient_capital": "abstained — insufficient draft capital (pick 65+)",
    "undrafted_insufficient_capital": "abstained — insufficient draft capital (undrafted)",
}


@dataclass(frozen=True)
class RookieQbRiskFilterResult:
    """Filter rows plus the standing integration wall disclosures."""

    rows: pd.DataFrame
    engine_b_training_integration: bool = False
    decision_supported: bool = False


def classify_rookie_qb_risk(inputs: pd.DataFrame) -> RookieQbRiskFilterResult:
    """Classify rookie QBs by pre-NFL capital; never a start/deploy verdict."""
    _validate_inputs(inputs)

    records: list[dict[str, Any]] = []
    for row in inputs.itertuples(index=False):
        if pd.isna(row.draft_number):
            classification = "undrafted_insufficient_capital"
        elif int(row.draft_number) >= DAY3_PICK_THRESHOLD:
            classification = "day3_insufficient_capital"
        else:
            classification = "capital_qualified"
        records.append(
            {
                "player_id": row.player_id,
                "age_at_entry": float(row.age_at_entry),
                "risk_filter_classification": classification,
                "base_rate_survival_prior": BASE_RATE_SURVIVAL_PRIOR_V1[classification],
                "abstention_badge_text": _BADGE_TEXT[classification],
                "prior_basis": "registered_capital_band_prior_v1",
                "decision_supported": False,
            }
        )
    return RookieQbRiskFilterResult(rows=pd.DataFrame(records))


def _validate_inputs(inputs: pd.DataFrame) -> None:
    for column in ALLOWED_INPUT_COLUMNS:
        if column not in inputs.columns:
            raise ValueError(f"missing required column: {column}")
    extras = [column for column in inputs.columns if column not in ALLOWED_INPUT_COLUMNS]
    if extras:
        raise ValueError(
            f"NFL usage / non-pre-NFL columns are leakage into the rookie filter: {extras}"
        )
    if not (inputs["position"] == "QB").all():
        raise ValueError("rookie filter accepts position=QB rows only")
    numeric_or_na = inputs["draft_number"].map(
        lambda value: pd.isna(value) or isinstance(value, (int, float))
    )
    if not numeric_or_na.all():
        raise ValueError("draft_number must be a numeric draft slot or NA")
    if inputs.duplicated(subset=["player_id"]).any():
        raise ValueError("duplicate rookie filter rows for player_id")
