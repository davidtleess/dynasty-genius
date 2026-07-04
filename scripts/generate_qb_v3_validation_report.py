"""BUILD-4 T3 producer — run the qb_v3 pre-registered validation matrix.

Frame-injectable (committed tests never touch the network or gitignored
artifacts): ``build_qb_v3_validation_report_from_frames`` composes the T1
label regeneration, the T2 candidate matrix + abstention mask, and the T3
classification walk-forward into the validation report. ``main`` wires real
already-ingested nflreadpy source data and writes the report JSON for the T5
promotion decision record. The report is descriptive diagnostics only —
``decision_supported=false`` recursively, no verdict fields.

Run: .venv/bin/python3.14 scripts/generate_qb_v3_validation_report.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_qb_role_occupancy_labels import (
    FEATURE_STORE_PATH,
    HORIZONS,
    INFERENCE_SEASON,
    SOURCE_SEASONS,
    _load_source_frames,
    build_qb_role_occupancy_labels_from_frames,
)
from src.dynasty_genius.eval.qb_v3_walk_forward import (
    run_qb_v3_walk_forward_validation,
)
from src.dynasty_genius.features.qb_v3_candidate_matrix import (
    ENGINE_B_FEATURES_QB_V3_CANDIDATE,
    build_qb_v3_candidate_matrix,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "app" / "data" / "validation" / "qb_v3_validation_report_v1.json"


def build_qb_v3_validation_report_from_frames(
    *,
    player_stats: pd.DataFrame,
    snap_counts: pd.DataFrame,
    feature_rows: pd.DataFrame,
    draft_prior_rows: pd.DataFrame,
    horizons: tuple[int, ...] = HORIZONS,
    n_bootstrap: int = 500,
    random_state: int = 20260703,
) -> dict[str, Any]:
    """Compose T1 labels + T2 matrix/mask + T3 walk-forward from raw frames."""
    label_result = build_qb_role_occupancy_labels_from_frames(
        player_stats=player_stats,
        snap_counts=snap_counts,
        feature_rows=feature_rows,
        horizons=horizons,
        available_label_seasons=SOURCE_SEASONS,
        inference_season=INFERENCE_SEASON,
    )
    matrix_result = build_qb_v3_candidate_matrix(
        feature_rows=feature_rows,
        draft_prior_rows=draft_prior_rows,
        labels=label_result.labels,
        candidate_head="qb_v3_candidate",
    )
    report = run_qb_v3_walk_forward_validation(
        candidate_matrix=matrix_result.candidate_matrix,
        labels=label_result.labels,
        eligibility_mask=matrix_result.eligibility_mask,
        feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
        horizons=horizons,
        n_bootstrap=n_bootstrap,
        random_state=random_state,
    )
    report["label_diagnostics"] = {
        **label_result.diagnostics,
        "decision_supported": False,
    }
    report["abstention_diagnostics"] = {
        **matrix_result.diagnostics,
        "decision_supported": False,
    }
    return report


def _load_draft_prior_rows() -> pd.DataFrame:
    """Pre-NFL draft capital from the already-ingested rosters source."""
    import nflreadpy  # local import: committed tests must never require it

    rosters = nflreadpy.load_rosters(list(SOURCE_SEASONS)).to_pandas()
    qb = rosters[rosters["position"] == "QB"]
    draft = (
        qb[["gsis_id", "entry_year", "draft_number"]]
        .dropna(subset=["gsis_id", "entry_year"])
        .sort_values("entry_year")
        .drop_duplicates(subset=["gsis_id"], keep="first")
        .rename(columns={"gsis_id": "player_id"})
    )
    draft["round"] = pd.NA
    draft["pick"] = pd.NA
    draft["draft_year"] = draft["entry_year"]
    draft["college"] = pd.NA
    return draft.reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    feature_store = pd.read_csv(FEATURE_STORE_PATH)
    feature_rows = feature_store[feature_store["position"] == "QB"]
    player_stats, snap_counts = _load_source_frames()
    draft_prior_rows = _load_draft_prior_rows()

    report = build_qb_v3_validation_report_from_frames(
        player_stats=player_stats,
        snap_counts=snap_counts,
        feature_rows=feature_rows,
        draft_prior_rows=draft_prior_rows,
    )

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2, default=str))
    for horizon, entry in report["horizon_summary"].items():
        print(
            f"H{horizon}: eligible={entry['promotion_eligible']} "
            f"evaluable={entry['evaluable_fold_count']}/{entry['structural_fold_count']} "
            f"reason={entry['non_promotion_reason']} "
            f"avg_brier_delta={entry.get('avg_brier_delta')}"
        )
    print(f"report -> {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
