"""R13 real-surface probe: the team-aggregate exclusion against the REAL pool.

Proves, on the actual admitted store, that (1) exactly the measured 236
provider TEAM sentinels leave the label input and nothing else does, (2) the
admitted weekly frame is byte-identical before and after, and (3) the full
composition now proceeds past the stage the 2026-08-16 first execution failed
on. Publication is NOT attempted, and NO registered metric, statistic, status,
or readout is printed or persisted — the composition result is discarded so
the held rerun (Codex CLEAR gate) stays the only path to a report.
"""

from __future__ import annotations

import hashlib
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
    exclude_provider_team_aggregates,
    filter_reg_weekly_records,
    load_crosswalk,
    load_dp_snapshot_rows,
    load_registration,
)


def _frame_digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def main() -> int:
    registration = load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
    crosswalk_entries, observed_at = load_crosswalk(REPO_ROOT)
    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=pd.read_parquet
    )

    frame = pool["weekly"]["frame"]
    digest_before = _frame_digest(frame)
    reg_records = filter_reg_weekly_records(frame)
    label_records = exclude_provider_team_aggregates(reg_records)
    excluded = len(reg_records) - len(label_records)
    print(f"weekly frame rows: {len(frame)}")
    print(f"REG records: {len(reg_records)}")
    print(f"label records after exclusion: {len(label_records)}")
    print(f"excluded rows: {excluded}")
    residual_bad = [
        row
        for row in label_records
        if row.get("player_id") is None
        or (
            isinstance(row.get("player_id"), float)
            and row["player_id"] != row["player_id"]
        )
    ]
    print(f"kept rows with missing player_id (must be 0): {len(residual_bad)}")
    digest_after = _frame_digest(pool["weekly"]["frame"])
    print(f"weekly frame digest unchanged: {digest_before == digest_after}")

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
        print(f"composition FAILED: reason={failure.reason}")
        print(f"detail: {failure.detail}")
        return 1
    # Deliberately discarded: no metric, status, comparison, or readout is
    # examined or printed. Stage-level truth only.
    del result
    print("composition COMPLETED past the label stage (result discarded unread)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
