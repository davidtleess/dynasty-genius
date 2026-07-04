"""BUILD-4 T1 producer — regenerate QB startable-role-occupancy labels.

Frame-injectable by design (the committed contract tests never touch the
network or gitignored artifacts): ``build_qb_role_occupancy_labels_from_frames``
takes source-shaped weekly frames plus the feature store and returns the label
result. The ``main`` entrypoint wires real nflreadpy source data (already an
ingested project source — no new external source) and writes the label table +
diagnostics for the T1 audit.

Run: .venv/bin/python3.14 scripts/generate_qb_role_occupancy_labels.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.features.qb_role_occupancy_labels import (
    QbRoleOccupancyLabelResult,
    aggregate_qb_role_source,
    build_qb_role_occupancy_labels,
    compute_qb_role_occupancy_class_balance,
    compute_structural_label_coverage,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE_STORE_PATH = REPO_ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
OUTPUT_DIR = REPO_ROOT / "app" / "data" / "training"
LABELS_PATH = OUTPUT_DIR / "qb_role_occupancy_labels_v1.csv"
DIAGNOSTICS_PATH = OUTPUT_DIR / "qb_role_occupancy_labels_v1_diagnostics.json"

SOURCE_SEASONS = tuple(range(2018, 2026))
HORIZONS = (1, 2, 3)
INFERENCE_SEASON = 2025
MAX_GAMES_ONLY_SHARE = 0.05


def build_qb_role_occupancy_labels_from_frames(
    *,
    player_stats: pd.DataFrame,
    snap_counts: pd.DataFrame,
    feature_rows: pd.DataFrame,
    horizons: tuple[int, ...] = HORIZONS,
    available_label_seasons: tuple[int, ...] = SOURCE_SEASONS,
    max_games_only_share: float = MAX_GAMES_ONLY_SHARE,
    inference_season: int | None = INFERENCE_SEASON,
) -> QbRoleOccupancyLabelResult:
    """Aggregate weekly source frames and build the per-horizon label table."""
    role_rows = aggregate_qb_role_source(
        player_stats=player_stats, snap_counts=snap_counts
    )
    return build_qb_role_occupancy_labels(
        feature_rows=feature_rows,
        role_rows=role_rows,
        horizons=horizons,
        available_label_seasons=available_label_seasons,
        max_games_only_share=max_games_only_share,
        inference_season=inference_season,
    )


def _load_source_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load real weekly QB source frames from nflreadpy (network/cache).

    Snap counts carry pfr ids while player stats and the feature store carry
    gsis ids — bridged via the SEASON-AWARE rosters crosswalk, mirroring
    ``feature_assembly.py`` exactly (a seasonless crosswalk fans out stale
    pfr-id pairings; a within-season 1:N collision fails loudly, never
    silently merging two players' snaps).
    """
    import nflreadpy  # local import: committed tests must never require it

    stats = nflreadpy.load_player_stats(list(SOURCE_SEASONS)).to_pandas()
    stats = stats[stats["position"] == "QB"]
    player_stats = stats[["player_id", "season", "position", "week", "season_type"]]

    snaps = nflreadpy.load_snap_counts(list(SOURCE_SEASONS)).to_pandas()
    snaps = snaps[snaps["position"] == "QB"]

    rosters = nflreadpy.load_rosters(list(SOURCE_SEASONS)).to_pandas()
    crosswalk = (
        rosters[["gsis_id", "pfr_id", "season"]]
        .dropna()
        .drop_duplicates()
        .rename(columns={"pfr_id": "pfr_player_id"})
    )
    # Guard only collisions that intersect the QB snap rows being joined — a
    # league-wide upstream quirk on players we never touch (e.g. the two 2023
    # Byron Youngs, DL/LB, sharing pfr YounBy01) must not block the producer,
    # but a collision on an actual QB snap id fails loudly (assembler precedent:
    # never merge or fan out snap rows across players).
    relevant = crosswalk[
        crosswalk["pfr_player_id"].isin(set(snaps["pfr_player_id"].dropna()))
    ]
    collisions = relevant.duplicated(["gsis_id", "season"]) | relevant.duplicated(
        ["pfr_player_id", "season"]
    )
    if collisions.any():
        raise ValueError(
            f"rosters crosswalk has {int(collisions.sum())} within-season id collision(s) "
            "on QB snap ids: refusing to merge or fan out snap rows across players."
        )

    snap_counts = (
        snaps.merge(crosswalk, on=["pfr_player_id", "season"], how="inner")
        .rename(columns={"gsis_id": "player_id", "offense_pct": "snap_share"})[
            ["player_id", "season", "position", "week", "snap_share"]
        ]
    )
    return player_stats, snap_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-out", type=Path, default=LABELS_PATH)
    parser.add_argument("--diagnostics-out", type=Path, default=DIAGNOSTICS_PATH)
    args = parser.parse_args()

    feature_store = pd.read_csv(FEATURE_STORE_PATH)
    feature_rows = feature_store[feature_store["position"] == "QB"]

    player_stats, snap_counts = _load_source_frames()
    result = build_qb_role_occupancy_labels_from_frames(
        player_stats=player_stats,
        snap_counts=snap_counts,
        feature_rows=feature_rows,
    )

    balance = compute_qb_role_occupancy_class_balance(result.labels)
    coverage = compute_structural_label_coverage(
        feature_seasons=feature_rows["feature_season"].unique(),
        available_label_seasons=SOURCE_SEASONS,
        horizons=HORIZONS,
        inference_season=INFERENCE_SEASON,
    )
    diagnostics: dict[str, Any] = {
        **result.diagnostics,
        "class_balance": balance.to_dict("records"),
        "structural_coverage": coverage,
        "predicate": {"games_threshold": 8, "snap_share_threshold": 0.50},
    }

    args.labels_out.parent.mkdir(parents=True, exist_ok=True)
    result.labels.to_csv(args.labels_out, index=False)
    args.diagnostics_out.write_text(json.dumps(diagnostics, indent=2, default=str))
    print(
        f"labels={len(result.labels)} rows -> {args.labels_out}\n"
        f"balance={balance.to_dict('records')}\n"
        f"quarantined={len(result.diagnostics['quarantined_player_ids'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
