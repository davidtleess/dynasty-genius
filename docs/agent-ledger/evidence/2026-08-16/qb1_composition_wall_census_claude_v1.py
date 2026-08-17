"""R15 real-surface proof + the David-authorized read-only wall census.

Two instruments in one pass over the REAL admitted store, repairing nothing:

1. PER-DATASET GATE CENSUS — for each of the seven datasets, the matrix's own
   pinned-column expectation (VALIDATION_DATASET_COLUMNS mapped through
   VALIDATION_PARSED_RENAMES) is checked against the frame the composition
   will actually receive (post-seam: pbp parsed, everything else raw). Every
   missing pinned column is a named wall, enumerated here without running the
   pipeline — so walls of this class are discovered ALL AT ONCE.
2. COMPOSITION PROBE — the full composition runs once; its first named
   refusal (if any) is recorded. If it completes, the result is DISCARDED
   UNREAD: no registered metric, statistic, status, or readout is printed or
   persisted; the fresh rerun (Codex CLEAR gate) stays the only path to a
   report.
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
from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (  # noqa: E402
    VALIDATION_DATASET_COLUMNS,
    VALIDATION_PARSED_RENAMES,
)


def main() -> int:
    registration = load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
    crosswalk_entries, observed_at = load_crosswalk(REPO_ROOT)
    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=pd.read_parquet
    )

    print("== per-dataset pinned-column census (post-seam frames)")
    wall_count = 0
    for name, columns in VALIDATION_DATASET_COLUMNS.items():
        frame = pool[name]["frame"]
        renames = VALIDATION_PARSED_RENAMES.get(name, {})
        pinned = [renames.get(column, column) for column in columns]
        missing = [column for column in pinned if column not in frame.columns]
        status = "OK" if not missing else f"WALL missing={missing}"
        if missing:
            wall_count += 1
        print(f"  {name}: rows={len(frame)} {status}")
    print(f"column-gate walls: {wall_count}")

    print("== composition probe (result discarded unread if it completes)")
    dp_snapshots = qb.load_h5_snapshots(
        REPO_ROOT / DP_VALUES_ROOT, registration=registration
    )
    dp_rows_by_season = {
        snapshot["season"]: load_dp_snapshot_rows(snapshot)
        for snapshot in dp_snapshots
    }
    try:
        result = compose_study(
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
        print(f"composition WALL: reason={failure.reason}")
        print(f"detail: {failure.detail}")
        return 1
    del result
    print("composition COMPLETED (result discarded unread)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
