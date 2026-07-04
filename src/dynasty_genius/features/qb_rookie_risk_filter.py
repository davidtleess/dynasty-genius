"""BUILD-4 T4 — shared rookie-QB risk filter (Engine A-facing, pre-NFL only).

The binary risk-filter BUILD-4 absorbed from the 2026-07-01 rookie fork.
Consumes PRE-NFL inputs ONLY — draft capital and age at NFL entry — with an
EXACT-SET input contract: any NFL-usage column is a leakage defect and fails
loudly (spec §4: no NFL usage leaks into Engine A). The filter's output never
enters Engine B training rows (the fork-A prior is derived separately inside
the candidate matrix builder from raw capital, not from this module).

The base-rate survival priors come SOLELY from the v2 unconditioned prior
table (app/config/rookie_qb_prior_table_v2.json — the recalibration of
2026-07-04, computed from the real 2018-2023 draft classes with never-played
rookies as honest negatives); the v1 folklore scalars are removed, and any
table problem fails closed with no fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

# EXACT-SET input contract: anything else is treated as attempted leakage.
ALLOWED_INPUT_COLUMNS = ("player_id", "position", "draft_number", "age_at_entry")

DAY3_PICK_THRESHOLD = 65

# The v2 unconditioned prior table (recalibration 2026-07-04) is the ONLY
# prior source — the v1 folklore scalars are removed, and a missing or
# invalid table FAILS CLOSED (no silent fallback).
PRIOR_TABLE_CANONICAL_PATH = "app/config/rookie_qb_prior_table_v2.json"
_DEFAULT_PRIOR_TABLE_PATH = (
    Path(__file__).resolve().parents[3] / PRIOR_TABLE_CANONICAL_PATH
)
REQUIRED_CONFIG_VERSION = 2

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


def classify_rookie_qb_risk(
    inputs: pd.DataFrame,
    *,
    prior_table_path: Path | None = None,
) -> RookieQbRiskFilterResult:
    """Classify rookie QBs by pre-NFL capital; never a start/deploy verdict."""
    _validate_inputs(inputs)
    priors_by_band = _load_prior_table(prior_table_path or _DEFAULT_PRIOR_TABLE_PATH)

    records: list[dict[str, Any]] = []
    for row in inputs.itertuples(index=False):
        if pd.isna(row.draft_number):
            classification = "undrafted_insufficient_capital"
            band = "undrafted"
        elif int(row.draft_number) >= DAY3_PICK_THRESHOLD:
            classification = "day3_insufficient_capital"
            band = "day3_picks_65_plus"
        else:
            classification = "capital_qualified"
            band = (
                "round_1_picks_1_32"
                if int(row.draft_number) <= 32
                else "round_2_picks_33_64"
            )
        horizon_priors = priors_by_band[band]
        records.append(
            {
                "player_id": row.player_id,
                "age_at_entry": float(row.age_at_entry),
                "risk_filter_classification": classification,
                "capital_band": band,
                "base_rate_survival_prior": horizon_priors[1],
                "survival_priors_by_horizon": dict(horizon_priors),
                "abstention_badge_text": _BADGE_TEXT[classification],
                # Provenance names the CANONICAL runtime home of the table,
                # regardless of injection (tests inject fixtures; the source
                # of record is the committed config artifact).
                "prior_basis": {
                    "source": PRIOR_TABLE_CANONICAL_PATH,
                    "config_version": REQUIRED_CONFIG_VERSION,
                },
                "decision_supported": False,
            }
        )
    return RookieQbRiskFilterResult(rows=pd.DataFrame(records))


def _load_prior_table(path: Path) -> dict[str, dict[int, float]]:
    """Fail-closed v2 table loader — never a silent fallback to old constants."""
    if not path.exists():
        raise ValueError(f"rookie prior table is missing at {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"rookie prior table is malformed JSON at {path}: {exc}") from exc
    if artifact.get("metadata", {}).get("config_version") != REQUIRED_CONFIG_VERSION:
        raise ValueError(
            "rookie prior table config_version mismatch: expected "
            f"{REQUIRED_CONFIG_VERSION}, got {artifact.get('metadata', {}).get('config_version')!r}"
        )
    # Reuse the producer's table contract (duplicate cells, all-bands H1 n>0,
    # null-not-zero empties) — single source of truth for validity.
    from scripts.compute_rookie_qb_unconditioned_priors import (
        validate_rookie_qb_prior_table,
    )

    validate_rookie_qb_prior_table(artifact)
    priors: dict[str, dict[int, float]] = {}
    for row in artifact["rows"]:
        priors.setdefault(row["capital_band"], {})[int(row["horizon"])] = row["rate"]
    # The filter consumes the FULL grid: every band, every horizon (Codex T3
    # review — a missing cell must be a load-time ValueError, never a KeyError
    # at classification time or a silently thinner horizon dict).
    expected_bands = (
        "round_1_picks_1_32",
        "round_2_picks_33_64",
        "day3_picks_65_plus",
        "undrafted",
    )
    missing = [
        (band, horizon)
        for band in expected_bands
        for horizon in (1, 2, 3)
        if horizon not in priors.get(band, {})
    ]
    if missing:
        raise ValueError(f"rookie prior table is missing required cells: {missing}")
    return priors


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
