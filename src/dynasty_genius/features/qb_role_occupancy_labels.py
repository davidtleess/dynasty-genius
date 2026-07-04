"""BUILD-4 T1 — QB startable-role-occupancy label regeneration.

Implements the ratified BUILD-4 spec §3 (docs/superpowers/specs/
2026-07-03-build4-superflex-qb-design.md): per-horizon binary labels
``startable_role_occupancy@H`` regenerated from source-shaped weekly frames,
NOT from the committed feature store (which only carries the combined 2-year
magnitude label).

Label rule (spec-pinned): positive iff the season-T+H QB row shows
games >= 8 AND mean snap share >= 0.50 — the predicate is the FRACTION
``>= 0.50``; a percent-scale ``>= 50`` misread yields zero positives in every
season (Codex F4). Snap-share-missing rows fall back to games-only with a
disclosed ``label_basis``; an absent T+H row labels negative (disclosed
conflation of "<4 games" with "out of the league"). The label conflates
availability with job retention (injury annex, Codex F7/Claude F3).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

GAMES_THRESHOLD = 8
SNAP_SHARE_THRESHOLD = 0.50  # FRACTION scale (0-1), never percent.

LABEL_COLUMN = "startable_role_occupancy"
LABEL_TABLE_COLUMNS = [
    "player_id",
    "feature_season",
    "target_season",
    "horizon",
    LABEL_COLUMN,
    "label_basis",
]
_SEASON_COLUMNS = ("feature_season", "target_season", "horizon")

# Walk-forward test years — mirrors WalkForwardDriver.FOLD_DEFINITIONS in
# src/dynasty_genius/eval/backtest_harness.py (kept local so this pure-pandas
# module never imports the sklearn-backed driver; the T1 RED pins the counts).
WALK_FORWARD_TEST_YEARS = (2020, 2021, 2022, 2023)

_ROLE_ROW_COLUMNS = ["player_id", "season", "position", "games", "snap_share"]


@dataclass(frozen=True)
class QbRoleOccupancyLabelResult:
    """Regenerated label table plus honesty diagnostics."""

    labels: pd.DataFrame
    diagnostics: dict[str, Any]


def aggregate_qb_role_source(
    *, player_stats: pd.DataFrame, snap_counts: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate weekly source frames to per-(player, season) role rows.

    Games = nunique weeks with a stat line INCLUDING postseason weeks (the
    existing ``games_t`` construction the spec cites); snap share = the mean of
    weekly snap shares on the 0-1 fraction scale. Duplicate weekly source rows
    are a deterministic rejection, never a silent winner.
    """
    for name, frame in (("player_stats", player_stats), ("snap_counts", snap_counts)):
        if frame.duplicated(subset=["player_id", "season", "week"]).any():
            raise ValueError(f"duplicate source rows in {name} for (player_id, season, week)")

    games = (
        player_stats.groupby(["player_id", "season"], as_index=False)
        .agg(position=("position", "first"), games=("week", "nunique"))
    )
    snaps = (
        snap_counts.groupby(["player_id", "season"], as_index=False)
        .agg(snap_share=("snap_share", "mean"))
    )
    role_rows = games.merge(snaps, on=["player_id", "season"], how="left")
    return role_rows[_ROLE_ROW_COLUMNS].reset_index(drop=True)


def build_qb_role_occupancy_labels(
    *,
    feature_rows: pd.DataFrame,
    role_rows: pd.DataFrame,
    horizons: tuple[int, ...],
    available_label_seasons: tuple[int, ...],
    max_games_only_share: float,
    inference_season: int | None = None,
) -> QbRoleOccupancyLabelResult:
    """Build the per-horizon label table under strict PIT discipline.

    Features are as-of season T; labels come strictly from season T+H.
    ``inference_season`` rows are NEVER labeled regardless of the available
    window (an extending window must not quietly convert inference rows into
    training labels); ``None`` means the caller asserts no inference season is
    present in ``feature_rows`` — the real producer always passes it.
    """
    available = set(int(season) for season in available_label_seasons)
    known_ids = set(feature_rows["player_id"])

    quarantined = sorted(set(role_rows["player_id"]) - known_ids)
    quarantine_reasons = {player_id: "unknown_player_id" for player_id in quarantined}
    usable_roles = role_rows[role_rows["player_id"].isin(known_ids)]
    # Duplicate role rows for one (player, season) must fail deterministically —
    # a dict lookup would silently keep the last row (Codex GREEN-review probe).
    if usable_roles.duplicated(subset=["player_id", "season"]).any():
        raise ValueError("duplicate role rows for (player_id, season)")
    role_lookup = {
        (row.player_id, int(row.season)): row
        for row in usable_roles.itertuples(index=False)
    }

    records: list[dict[str, Any]] = []
    for feature in feature_rows.itertuples(index=False):
        feature_season = int(feature.feature_season)
        if inference_season is not None and feature_season == int(inference_season):
            continue
        for horizon in horizons:
            target_season = feature_season + int(horizon)
            if target_season not in available:
                continue
            role = role_lookup.get((feature.player_id, target_season))
            if role is None:
                label, basis = False, "absent_target_row"
            elif pd.isna(role.snap_share):
                label = int(role.games) >= GAMES_THRESHOLD
                basis = "games_only"
            else:
                label = (
                    int(role.games) >= GAMES_THRESHOLD
                    and float(role.snap_share) >= SNAP_SHARE_THRESHOLD
                )
                basis = "games_and_snap"
            records.append(
                {
                    "player_id": feature.player_id,
                    "feature_season": feature_season,
                    "target_season": target_season,
                    "horizon": int(horizon),
                    LABEL_COLUMN: bool(label),
                    "label_basis": basis,
                }
            )

    labels = pd.DataFrame(records, columns=LABEL_TABLE_COLUMNS)
    # Explicit dtypes so a legitimately-empty labelable set still validates
    # (an empty object-dtype frame must not read as a contract violation).
    labels = labels.astype(
        {
            "feature_season": int,
            "target_season": int,
            "horizon": int,
            LABEL_COLUMN: bool,
        }
    )
    labels = labels.sort_values(["horizon", "feature_season", "player_id"]).reset_index(
        drop=True
    )
    validate_qb_role_occupancy_label_table(labels)

    diagnostics: dict[str, Any] = {
        "quarantined_player_ids": quarantined,
        "quarantine_reasons": quarantine_reasons,
        "games_only_share_by_season": _games_only_share_by_season(
            labels, max_games_only_share=max_games_only_share
        ),
    }
    return QbRoleOccupancyLabelResult(labels=labels, diagnostics=diagnostics)


def _games_only_share_by_season(
    labels: pd.DataFrame, *, max_games_only_share: float
) -> dict[int, dict[str, Any]]:
    """Per-target-season games_only share over rows with a present target row.

    A crosswalk regression must never silently make the fallback dominate
    (Codex F6) — beyond the pinned tolerance the season is marked ``fail``.
    """
    present = labels[labels["label_basis"].isin(["games_and_snap", "games_only"])]
    shares: dict[int, dict[str, Any]] = {}
    for season, group in present.groupby("target_season"):
        share = float((group["label_basis"] == "games_only").mean())
        shares[int(season)] = {
            "share": share,
            "status": "fail" if share > max_games_only_share else "ok",
        }
    return shares


def validate_qb_role_occupancy_label_table(labels: pd.DataFrame) -> None:
    """Fail-closed label-table contract (spec §9 seed 11)."""
    for column in LABEL_TABLE_COLUMNS:
        if column not in labels.columns:
            raise ValueError(f"missing required column: {column}")
    if labels[LABEL_COLUMN].dtype != bool:
        raise ValueError(f"{LABEL_COLUMN} must be bool, got {labels[LABEL_COLUMN].dtype}")
    for column in _SEASON_COLUMNS:
        if not pd.api.types.is_integer_dtype(labels[column]):
            raise ValueError(f"{column} must be an integer season/horizon column")
    duplicated = labels.duplicated(subset=["player_id", "feature_season", "horizon"])
    if duplicated.any():
        raise ValueError("duplicate label rows for (player_id, feature_season, horizon)")


def compute_structural_label_coverage(
    *,
    feature_seasons: Iterable[int],
    available_label_seasons: Iterable[int],
    horizons: tuple[int, ...],
    inference_season: int,
) -> dict[int, dict[str, int]]:
    """Per-horizon structural coverage (Claude F1, Codex-verified).

    Eligibility must be computed against these STRUCTURAL fold counts
    (H1=4/H2=4/H3=3 for the current window), never a hardcoded "of 4".
    """
    features = sorted(set(int(season) for season in feature_seasons))
    available = set(int(season) for season in available_label_seasons)
    coverage: dict[int, dict[str, int]] = {}
    for horizon in horizons:
        labelable = [
            season
            for season in features
            if season != inference_season and season + int(horizon) in available
        ]
        evaluable_folds = [
            year for year in WALK_FORWARD_TEST_YEARS if year + int(horizon) in available
        ]
        coverage[int(horizon)] = {
            "max_feature_season": max(labelable),
            "structural_fold_count": len(evaluable_folds),
        }
    return coverage


def compute_qb_role_occupancy_class_balance(labels: pd.DataFrame) -> pd.DataFrame:
    """Recompute class balance from the role-occupancy labels themselves.

    The spec's rejected rank-proxy balance numbers must never be reproduced as
    the new balance — this derives strictly from the regenerated table.
    """
    rows = []
    for horizon, group in labels.groupby("horizon"):
        positive = int(group[LABEL_COLUMN].sum())
        total = int(len(group))
        rows.append(
            {
                "horizon": int(horizon),
                "positive": positive,
                "negative": total - positive,
                "total": total,
                "positive_rate": positive / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows, columns=["horizon", "positive", "negative", "total", "positive_rate"])
