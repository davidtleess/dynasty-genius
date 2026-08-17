"""Read-only diagnostic for the 2026-08-16 first registered QB-1 execution.

The terminal artifact is metric-free by design (`label_row_invalid`), so this
script reproduces the composition's failing step to surface the refusal's
named detail. It writes NO artifact, publishes nothing, and mutates nothing:
it calls the same admission + composition path main() runs and prints the
QBValidationFailure's reason and detail.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402
from scripts.run_qb1_study import (  # noqa: E402
    CROSSWALK_PATH,
    CROSSWALK_SHA256,
    DP_VALUES_ROOT,
    RAW_ROOT,
    compose_study,
    load_crosswalk,
    load_dp_snapshot_rows,
    load_registration,
)


def main() -> int:
    registration = load_registration(REPO_ROOT)
    try:
        qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
        crosswalk_entries, observed_at = load_crosswalk(REPO_ROOT)
        pool = qb.admit_and_load_validation_pool(
            REPO_ROOT / RAW_ROOT,
            repo_root=REPO_ROOT,
            frame_loader=pd.read_parquet,
        )
        dp_snapshots = qb.load_h5_snapshots(
            REPO_ROOT / DP_VALUES_ROOT, registration=registration
        )
        dp_rows_by_season = {
            snapshot["season"]: load_dp_snapshot_rows(snapshot)
            for snapshot in dp_snapshots
        }
        compose_study(
            registration=registration,
            pool=pool,
            crosswalk_entries=crosswalk_entries,
            crosswalk_observed_at=observed_at,
            dp_snapshots=dp_snapshots,
            dp_rows_by_season=dp_rows_by_season,
            repo_root=REPO_ROOT,
            frozen_inputs={REPO_ROOT / CROSSWALK_PATH: CROSSWALK_SHA256},
        )
    except qb.QBValidationFailure as failure:
        print(f"reason: {failure.reason}")
        print(f"detail: {failure.detail}")
        return 0
    print("composition completed without a QBValidationFailure")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
