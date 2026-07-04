"""BUILD-4 T2 — qb_v3 candidate cohort, feature matrix, and abstention mask.

Implements the ratified BUILD-4 spec §5/§7 (docs/superpowers/specs/
2026-07-03-build4-superflex-qb-design.md): the candidate-specific feature
contract (the frozen qb_v2 contract is untouched and still rejects these
columns), the fork-A draft-capital prior (David-ratified), and the abstention
eligibility mask that exists BEFORE any training because it changes the
population and validation denominators.

Fork-A mechanics (binding): ``draft_capital_prior`` is a derived scalar from
pre-NFL draft capital only, mapped by the FIXED PRE-REGISTERED rule below —
raw pick/round/draft_year/college columns never enter the candidate matrix,
and the ``nfl_year_at_feature`` gate is metadata, never a feature column. The
prior exists only for QB rows in NFL years 1–3 on the candidate head; year 4+
is zero (second-contract window — organizational patience decays).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_QB,
    MARKET_PROHIBITED,
)

CANDIDATE_HEAD = "qb_v3_candidate"

# The candidate contract = the frozen QB contract + the two ratified additions.
# Explicit DETERMINISTIC order (sorted base + pinned additions): the base
# contract is a set, and expanding it directly made matrix column order vary
# with PYTHONHASHSEED — a reproducibility blocker (Codex T2 review probe).
ENGINE_B_FEATURES_QB_V3_CANDIDATE: list[str] = [
    *sorted(ENGINE_B_FEATURES_QB),
    "draft_capital_prior",
    "dual_threat_x_age",
]

# Raw pre-NFL capital columns: inputs to the derived prior, NEVER features.
RAW_DRAFT_COLUMNS = ("pick", "round", "draft_year", "college", "draft_number", "entry_year")

# FIXED PRE-REGISTERED PRIOR RULE (fork-A, David-ratified 2026-07-03).
# Pick-banded organizational-patience scalar, applied only in NFL years 1-3 —
# the bands mirror the constitution's rookie draft-capital weighting (picks
# 1-32 dominate / 33-64 equal / 65+ situation-dependent). Keyed on
# draft_number because the REAL rosters source carries no round column
# (real-shape check 2026-07-03); the mapping is a registered constant —
# never fit on pooled data.
DRAFT_CAPITAL_PRIOR_BANDS: tuple[tuple[int, float], ...] = (
    (32, 1.0),  # picks 1-32
    (64, 0.7),  # picks 33-64
)
DAY3_PRIOR = 0.15  # picks 65+ (typically mask-abstained in year 1 anyway)
UNDRAFTED_PRIOR = 0.05
PRIOR_NFL_YEARS = (1, 2, 3)

# Spec §7: Day-3 rookies (picks 65+) never receive a candidate probability.
DAY3_PICK_THRESHOLD = 65
SMALL_SAMPLE_GAMES_FLOOR = 8

_REQUIRED_FEATURE_COLUMNS = ("player_id", "position", "feature_season", *ENGINE_B_FEATURES_QB)


@dataclass(frozen=True)
class QbV3CandidateMatrixResult:
    """Candidate matrix + the pre-training abstention mask + diagnostics."""

    candidate_matrix: pd.DataFrame
    eligibility_mask: pd.DataFrame
    feature_cols: list[str]
    diagnostics: dict[str, Any]


def validate_qb_v3_candidate_feature_contract(feature_cols: list[str]) -> None:
    """Fail-closed candidate contract: market and raw-draft columns never pass."""
    allowed = set(ENGINE_B_FEATURES_QB_V3_CANDIDATE)
    for column in feature_cols:
        if column in MARKET_PROHIBITED:
            raise ValueError(f"prohibited market-derived column in candidate matrix: {column}")
        if column in RAW_DRAFT_COLUMNS:
            raise ValueError(f"raw draft column prohibited in candidate matrix: {column}")
        if column == "nfl_year_at_feature":
            raise ValueError("nfl_year_at_feature is metadata only, prohibited as a feature")
        if column not in allowed:
            raise ValueError(f"column not in allowed qb_v3 candidate contract: {column}")
    missing = allowed - set(feature_cols)
    if missing:
        raise ValueError(f"candidate contract columns missing: {sorted(missing)}")


def build_qb_v3_candidate_matrix(
    *,
    feature_rows: pd.DataFrame,
    draft_prior_rows: pd.DataFrame,
    labels: pd.DataFrame,
    candidate_head: str,
) -> QbV3CandidateMatrixResult:
    """Build the qb_v3 candidate cohort with abstention applied before scoring."""
    if candidate_head != CANDIDATE_HEAD:
        raise ValueError(f"unknown candidate head: {candidate_head}")
    _validate_feature_rows(feature_rows)
    if draft_prior_rows.duplicated(subset=["player_id"]).any():
        raise ValueError("duplicate draft prior rows for player_id")

    # The label table must satisfy the T1 contract before any cohort use.
    from src.dynasty_genius.features.qb_role_occupancy_labels import (
        validate_qb_role_occupancy_label_table,
    )

    validate_qb_role_occupancy_label_table(labels)

    qb_rows = feature_rows[feature_rows["position"] == "QB"].copy()
    excluded_non_qb_count = int(len(feature_rows) - len(qb_rows))

    draft = draft_prior_rows.set_index("player_id")
    qb_rows["nfl_year_at_feature"] = [
        _nfl_year_at_feature(row.player_id, int(row.feature_season), draft)
        for row in qb_rows.itertuples(index=False)
    ]
    qb_rows["draft_capital_prior"] = [
        _draft_capital_prior(row.player_id, row.nfl_year_at_feature, draft)
        for row in qb_rows.itertuples(index=False)
    ]
    qb_rows["dual_threat_x_age"] = qb_rows["age"].astype(float) * qb_rows[
        "is_dual_threat"
    ].astype(bool).astype(float)

    eligibility_mask = _build_eligibility_mask(qb_rows, draft)

    feature_cols = list(ENGINE_B_FEATURES_QB_V3_CANDIDATE)
    validate_qb_v3_candidate_feature_contract(feature_cols)
    candidate_matrix = qb_rows[["player_id", "feature_season", *feature_cols]].reset_index(
        drop=True
    )

    reasons = eligibility_mask["abstention_reason"].dropna()
    diagnostics: dict[str, Any] = {
        "candidate_head": candidate_head,
        "excluded_non_qb_count": excluded_non_qb_count,
        "draft_capital_prior_basis": "fixed_pre_registered_rule",
        "abstention_counts": reasons.value_counts().to_dict(),
        "label_rows": int(len(labels)),
    }
    return QbV3CandidateMatrixResult(
        candidate_matrix=candidate_matrix,
        eligibility_mask=eligibility_mask,
        feature_cols=feature_cols,
        diagnostics=diagnostics,
    )


def _validate_feature_rows(feature_rows: pd.DataFrame) -> None:
    for column in _REQUIRED_FEATURE_COLUMNS:
        if column not in feature_rows.columns:
            raise ValueError(f"missing required column: {column}")
    if not pd.api.types.is_integer_dtype(feature_rows["feature_season"]):
        raise ValueError("feature_season must be an integer season column")
    if feature_rows.duplicated(subset=["player_id", "feature_season"]).any():
        raise ValueError("duplicate feature rows for (player_id, feature_season)")


def _nfl_year_at_feature(
    player_id: str, feature_season: int, draft: pd.DataFrame
) -> int | None:
    """Metadata-only career-year gate — never a feature column."""
    if player_id not in draft.index:
        return None
    entry_year = draft.loc[player_id, "entry_year"]
    if pd.isna(entry_year):
        return None
    return feature_season - int(entry_year) + 1


def _draft_capital_prior(
    player_id: str, nfl_year: int | None, draft: pd.DataFrame
) -> float:
    """The fixed pre-registered fork-A prior; zero outside NFL years 1-3."""
    if nfl_year is None or nfl_year not in PRIOR_NFL_YEARS:
        return 0.0
    if player_id not in draft.index:
        return UNDRAFTED_PRIOR
    draft_number = draft.loc[player_id, "draft_number"]
    if pd.isna(draft_number):
        return UNDRAFTED_PRIOR
    for band_max, prior in DRAFT_CAPITAL_PRIOR_BANDS:
        if int(draft_number) <= band_max:
            return prior
    return DAY3_PRIOR


def _build_eligibility_mask(qb_rows: pd.DataFrame, draft: pd.DataFrame) -> pd.DataFrame:
    """Abstention runs BEFORE scoring: abstained rows never receive a candidate
    probability (spec §7 ordering) — the mask is the training/scoring gate."""
    prior_season_ok = {
        (row.player_id, int(row.feature_season)): int(row.games_t) >= SMALL_SAMPLE_GAMES_FLOOR
        for row in qb_rows.itertuples(index=False)
    }

    records: list[dict[str, Any]] = []
    for row in qb_rows.itertuples(index=False):
        feature_season = int(row.feature_season)
        reason: str | None = None
        # Missing draft-prior metadata fails CLOSED: without entry_year the
        # year-1-to-3 gating and Day-3 abstention cannot be enforced at all.
        # (pd.isna, not `is None` — the frame column coerces None to NaN.)
        if pd.isna(row.nfl_year_at_feature):
            reason = "draft_prior_missing"
        elif _is_day3_rookie(row.player_id, row.nfl_year_at_feature, draft):
            reason = "day3_rookie"
        # A year-1 UDFA holds LESS capital than a pick-65 rookie — it must not
        # be scorable either (the 0.05 prior stays as a disclosed cohort prior).
        elif _is_undrafted_rookie(row.player_id, row.nfl_year_at_feature, draft):
            reason = "undrafted_rookie"
        elif int(row.games_t) < SMALL_SAMPLE_GAMES_FLOOR and not prior_season_ok.get(
            (row.player_id, feature_season - 1), False
        ):
            reason = "small_sample_qb"
        records.append(
            {
                "player_id": row.player_id,
                "feature_season": feature_season,
                "nfl_year_at_feature": row.nfl_year_at_feature,
                "eligible_for_qb_v3_candidate": reason is None,
                "abstention_reason": reason,
            }
        )
    return pd.DataFrame(records)


def _is_day3_rookie(player_id: str, nfl_year: int | None, draft: pd.DataFrame) -> bool:
    if nfl_year != 1 or player_id not in draft.index:
        return False
    draft_number = draft.loc[player_id, "draft_number"]
    return bool(pd.notna(draft_number) and int(draft_number) >= DAY3_PICK_THRESHOLD)


def _is_undrafted_rookie(player_id: str, nfl_year: int | None, draft: pd.DataFrame) -> bool:
    if nfl_year != 1 or player_id not in draft.index:
        return False
    return bool(pd.isna(draft.loc[player_id, "draft_number"]))
