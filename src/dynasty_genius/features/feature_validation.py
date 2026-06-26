"""F-feature-refresh T2 — fail-closed validation gate for the feature candidate.

`validate_feature_candidate` runs a set of INDEPENDENT, fail-closed integrity gates over a
freshly assembled engine_b feature candidate and returns a structured result. Each gate
appends its own failure string, so a candidate that trips several gates reports all of them.
Drift versus the prior runtime is computed REPORT-ONLY — it never blocks a publish.

`decision_supported` is always False: this validates DATA INTEGRITY, it does not certify any
model output or decision. This module derives nothing from the market and trains no model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_PROHIBITED_FEATURES,
    OUTCOME_COLUMN,
    validate_no_temporal_leakage,
)

# Columns whose values are bounded shares/rates in [0, 1] (range-sanity gate).
_BOUNDED_UNIT_COLUMNS = (
    "snap_share",
    "snap_share_t_minus_1",
    "route_participation",
    "target_share_nfl",
)

# air_yards_share is NOT a [0,1] unit share — it legitimately goes slightly negative (negative
# air yards on screens). T4: gated separately with a football-plausibility + finiteness bound.
_AIR_YARDS_SHARE_BOUNDS = (-0.5, 2.0)

# Columns that are not model features (excluded from the temporal-leakage column scan; the
# outcome column legitimately encodes T+1/T+2 and would otherwise trip the leakage pattern).
_NON_FEATURE_COLUMNS = frozenset({OUTCOME_COLUMN, "training_eligible"})


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of `validate_feature_candidate`. `drift` is report-only context."""

    ok: bool
    failures: list[str]
    drift: dict
    decision_supported: bool = False
    null_rates: dict = field(default_factory=dict)
    null_thresholds: dict = field(default_factory=dict)


def _engine_b_output_columns() -> tuple[str, ...]:
    # Lazy import: scripts.assemble_engine_b_dataset pulls nflreadpy at module load, so keep
    # importing this validator cheap and standalone-safe.
    from scripts.assemble_engine_b_dataset import ENGINE_B_OUTPUT_COLUMNS

    return tuple(ENGINE_B_OUTPUT_COLUMNS)


def _compute_drift(df: pd.DataFrame, prior_runtime: Optional[pd.DataFrame]) -> dict:
    """Report-only drift context: row counts and per-column numeric mean deltas."""
    drift: dict = {
        "row_count": {
            "candidate": int(len(df)),
            "prior_runtime": (None if prior_runtime is None else int(len(prior_runtime))),
        },
        "numeric_mean_delta": {},
    }
    if prior_runtime is None:
        return drift
    for col in df.columns:
        if col not in prior_runtime.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if not pd.api.types.is_numeric_dtype(prior_runtime[col]):
            continue
        delta = float(df[col].mean() - prior_runtime[col].mean())
        # Keep the report standard-JSON clean: non-finite deltas become None.
        drift["numeric_mean_delta"][col] = delta if pd.notna(delta) else None
    return drift


def validate_feature_candidate(
    df: pd.DataFrame,
    *,
    inference_season: int,
    min_total_rows: int,
    min_position_rows: dict[str, int],
    critical_features: tuple[str, ...],
    max_null_rate_by_column: dict[str, float],
    prior_runtime: Optional[pd.DataFrame] = None,
) -> ValidationResult:
    """Run every integrity gate (fail-closed, independent) over a feature candidate."""
    failures: list[str] = []
    columns = set(df.columns)

    # Gate: prohibited / market-leakage columns (market-out-of-model is constitutional).
    prohibited = sorted(columns & set(ENGINE_B_PROHIBITED_FEATURES))
    if prohibited:
        failures.append(f"prohibited: market/leakage columns present: {prohibited}")

    # Gate: temporal leakage by column name (T+1/T+2/future markers), features only.
    feature_columns = [c for c in df.columns if c not in _NON_FEATURE_COLUMNS]
    try:
        validate_no_temporal_leakage(feature_columns)
    except ValueError as exc:
        failures.append(f"prohibited: temporal leakage detected: {exc}")

    # Gate: schema — every required output column must be present.
    required = _engine_b_output_columns()
    missing = [c for c in required if c not in columns]
    if missing:
        failures.append(f"schema: missing required columns: {missing}")

    # Gate: critical features must be present (nullness handled by the NaN gate below).
    missing_critical = [c for c in critical_features if c not in columns]
    if missing_critical:
        failures.append(f"schema: missing critical feature columns: {missing_critical}")

    # Gate: dtype — feature_season must be integer-valued.
    if "feature_season" in columns:
        fs = df["feature_season"]
        if not pd.api.types.is_integer_dtype(fs):
            coerced = pd.to_numeric(fs, errors="coerce")
            non_integer = coerced.dropna()
            if coerced.isna().any() or not bool((non_integer % 1 == 0).all()):
                failures.append("dtype: feature_season must be integer-valued")

    # Gate: blank player ids.
    if "player_id" in columns:
        ids = df["player_id"].astype("string")
        blank = ids.isna() | (ids.str.strip() == "")
        if bool(blank.any()):
            failures.append(f"blank: {int(blank.sum())} blank player_id value(s)")

    # Gate: duplicate player-season rows.
    if {"player_id", "feature_season"} <= columns:
        dup = df.duplicated(subset=["player_id", "feature_season"])
        if bool(dup.any()):
            failures.append(
                f"duplicate: {int(dup.sum())} duplicate player_id/feature_season row(s)"
            )

    # Gate: inference-season coverage — the season we will score must be present.
    has_inference = "feature_season" in columns and bool(
        (df["feature_season"] == inference_season).any()
    )
    if not has_inference:
        failures.append(f"inference: no rows for inference season {inference_season}")

    # Gate: total-row floor.
    if len(df) < min_total_rows:
        failures.append(
            f"coverage: total rows {len(df)} below min_total_rows {min_total_rows}"
        )

    # Gate: per-position coverage floors over the inference-season rows.
    inference_rows = (
        df[df["feature_season"] == inference_season] if "feature_season" in columns
        else df.iloc[0:0]
    )
    for position, floor in min_position_rows.items():
        count = (
            int((inference_rows["position"] == position).sum())
            if "position" in columns else 0
        )
        if count < floor:
            failures.append(
                f"coverage: position {position} has {count} inference-season row(s) "
                f"(< floor {floor})"
            )

    # Gate: range sanity — bounded share/rate columns must lie in [0, 1].
    for col in _BOUNDED_UNIT_COLUMNS:
        if col in columns:
            series = pd.to_numeric(df[col], errors="coerce")
            out_of_range = ((series < 0) | (series > 1)) & series.notna()
            if bool(out_of_range.any()):
                failures.append(
                    f"range: {col} has {int(out_of_range.sum())} value(s) outside [0, 1]"
                )

    # Gate: air_yards_share plausibility — NOT a [0,1] unit share (negative air yards are
    # legitimate). Football-semantic finite bound; a non-numeric / non-finite value FAILS
    # EXPLICITLY — it must not silently coerce to NaN and bypass the gate.
    if "air_yards_share" in columns:
        raw = df["air_yards_share"]
        numeric = pd.to_numeric(raw, errors="coerce")
        lo, hi = _AIR_YARDS_SHARE_BOUNDS
        # FINITE-required (Codex T4a catch + Gemini ruling): production air_yards_share is
        # ALWAYS present (0 nulls, all positions — non-receivers are 0.0, not null), so a null,
        # a non-numeric value coerced to NaN, or a non-finite ±inf is a data anomaly that must
        # FAIL explicitly — never silently impute. ~np.isfinite catches all three.
        non_finite = ~np.isfinite(numeric)
        out_of_bound = ((numeric < lo) | (numeric > hi)) & numeric.notna()
        n_bad = int((non_finite | out_of_bound).sum())
        if n_bad:
            failures.append(
                f"range: air_yards_share has {n_bad} value(s) outside the plausibility "
                f"bound [{lo}, {hi}] or non-finite/non-numeric/null"
            )

    # Gate: NaN integrity — null rate per configured column. snap_share is INFERENCE-SCOPED:
    # the blocker applies only to the rows actually published/scored (feature_season ==
    # inference_season), so a clean inference season is never masked by historical training
    # nulls; its all-row + non-inference rates are DISCLOSED, never a blocker. Other columns
    # stay whole-candidate.
    null_rates: dict = {}
    null_thresholds: dict = {}
    non_inference_rows = (
        df[df["feature_season"] != inference_season] if "feature_season" in columns
        else df.iloc[0:0]
    )
    for col, max_rate in (max_null_rate_by_column or {}).items():
        if col not in columns:
            failures.append(f"schema: null-rate column {col} is missing")
            continue
        if col == "snap_share":
            inf_rate = (
                float(inference_rows[col].isna().mean()) if len(inference_rows) else 0.0
            )
            null_rates[col] = {
                "inference": inf_rate,
                "all_rows": float(df[col].isna().mean()),
                "non_inference": (
                    float(non_inference_rows[col].isna().mean())
                    if len(non_inference_rows) else 0.0
                ),
            }
            null_thresholds[col] = {"scope": "inference", "max": max_rate}
            if inf_rate > max_rate:
                failures.append(
                    f"nan: {col} inference null rate {inf_rate:.3f} exceeds max {max_rate}"
                )
        else:
            rate = float(df[col].isna().mean())
            if rate > max_rate:
                failures.append(
                    f"nan: {col} null rate {rate:.3f} exceeds max {max_rate}"
                )

    drift = _compute_drift(df, prior_runtime)
    return ValidationResult(
        ok=(len(failures) == 0),
        failures=failures,
        drift=drift,
        decision_supported=False,
        null_rates=null_rates,
        null_thresholds=null_thresholds,
    )
