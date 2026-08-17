"""R17 real-surface probe: the PRIVATE season_summary aggregate classifier at
matrix stage 1b, against the REAL admitted store.

Proves the round-17 required real-surface facts and NOTHING past them:

1. Mirroring `build_study_matrix`'s defensive season_summary path
   byte-for-byte (copy -> F14 shape gate -> F15 manifest-column gate ->
   `_records` -> `_exclude_provider_season_aggregate_rows`): exactly the 11
   measured league-aggregate rows classify (first excluded defensive index
   1845 — the run's actual refusal point) and ZERO unusable-identity rows
   remain.
2. The FULL stage-1b law (identity refusal + duplicate refusal + CPOE
   null-or-finite validation, `study_matrix.py` stage 1b) replays over every
   kept record — the exact wall the round-16 rerun died on is gone, or the
   next refusal is reported honestly by name. This exercises stage 1b ONLY:
   no composition, no fold, no lane, no inference, no report.
3. The admitted season_summary frame digest is identical before and after —
   the classifier copies, never mutates.

Identity-domain discipline retained: no claim is made that no non-identity
wall remains beyond this stage. Nothing registered is computed, printed, or
persisted.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402
from scripts.run_qb1_study import RAW_ROOT, load_registration  # noqa: E402
from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (  # noqa: E402
    VALIDATION_DATASET_COLUMNS,
    VALIDATION_PARSED_RENAMES,
)
from src.dynasty_genius.eval.qb_validation.guards import (  # noqa: E402
    validate_dataset_shape,
    validate_manifest_columns,
)
from src.dynasty_genius.eval.qb_validation.study_matrix import (  # noqa: E402
    _exclude_provider_season_aggregate_rows,
    _finite_float,
    _is_null,
    _records,
    _refuse,
    _usable_player_id,
    _usable_text,
    _valid_label_season,
)


def _digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def main() -> int:
    load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=pd.read_parquet
    )

    admitted = pool["season_summary"]["frame"]
    digest_before = _digest(admitted)

    # ── Mirror of build_study_matrix's defensive season_summary path ───────
    frame = admitted.copy()
    renames = VALIDATION_PARSED_RENAMES.get("season_summary", {})
    pinned = tuple(
        renames.get(column, column)
        for column in VALIDATION_DATASET_COLUMNS["season_summary"]
    )
    validate_dataset_shape(frame, dataset="season_summary")
    validate_manifest_columns(frame, pinned, dataset="season_summary")
    records = _records(frame)

    kept = _exclude_provider_season_aggregate_rows(records)
    # Exact excluded set, measured by identity of surviving rows:
    kept_ids = {id(row) for row in kept}
    excluded = [(i, row) for i, row in enumerate(records) if id(row) not in kept_ids]
    print(f"defensive season_summary records: {len(records)}")
    print(f"excluded by the R17 classifier (must be 11): {len(excluded)}")
    print(f"first excluded defensive index (must be 1845): "
          f"{excluded[0][0] if excluded else None}")
    for i, row in excluded:
        print(
            f"  [{i}] season={row.get('season')!r} "
            f"name={_usable_text(row.get('player_name'))!r} "
            f"games={row.get('games')!r}"
        )
    residual = [
        (i, row)
        for i, row in enumerate(kept)
        if _usable_player_id(row.get("player_id")) is None
        or _valid_label_season(row.get("season")) is None
    ]
    print(f"kept rows with unusable identity (must be 0): {len(residual)}")

    # ── FULL stage-1b law replay over kept records (identity+dup+CPOE) ─────
    summary: dict[tuple, dict] = {}
    try:
        for index, raw in enumerate(kept):
            pid = _usable_player_id(raw.get("player_id"))
            season = _valid_label_season(raw.get("season"))
            if pid is None or season is None:
                _refuse(
                    "stat_value_invalid",
                    f"season_summary row [{index}] has unusable identity",
                )
            key = (pid, season)
            if key in summary:
                _refuse(
                    "duplicate_player_season",
                    f"season_summary duplicates ({pid}, {season}); the CPOE "
                    "join is one-to-one by contract",
                )
            cpoe = raw.get("passing_cpoe")
            summary[key] = {
                "position": _usable_text(raw.get("position")) or "",
                "passing_cpoe": None
                if _is_null(cpoe)
                else _finite_float(
                    cpoe, "passing_cpoe", f"season_summary row [{index}]"
                ),
            }
    except qb.QBValidationFailure as failure:
        print(f"stage-1b REFUSED: reason={failure.reason}")
        print(f"detail: {failure.detail}")
        return 1
    print(
        f"stage-1b law (identity + duplicate + CPOE) passed over all "
        f"{len(kept)} kept records; distinct (player_id, season) keys: "
        f"{len(summary)}"
    )

    digest_after = _digest(pool["season_summary"]["frame"])
    print(f"admitted season_summary frame digest unchanged: "
          f"{digest_before == digest_after}")
    ok = (
        len(excluded) == 11
        and (excluded[0][0] == 1845 if excluded else False)
        and not residual
        and digest_before == digest_after
    )
    print(f"PROBE VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
