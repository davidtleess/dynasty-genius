"""R16 real-surface probe: the SHARED placeholder classifier at the MATRIX
defensive weekly-record seam, against the REAL admitted store.

Proves, on the actual admitted pool (D1 admission, hash-before-parse), the
round-16 required facts and NOTHING past them:

1. **Exact classification** — mirroring `build_study_matrix`'s defensive path
   byte-for-byte (copy -> shape gate -> manifest-column gate -> `_records` ->
   `exclude_provider_placeholder_rows`), the classifier excludes the measured
   provider placeholder rows and leaves ZERO residual missing-identity rows,
   reported with the REG / non-REG split so 192 REG is checked exactly.
2. **The R15 wall itself** — `_validated_weekly_row` (the guard whose
   `stat_value_invalid` refusal at weekly row 1026 was blocker
   R15-G1-MATRIX-PLACEHOLDER-ADMISSION) replays over every kept defensive
   record. This exercises matrix stage (4) ONLY: no season-coverage gate, no
   fold, no ridge lane, no inference, no report — the round-16 boundary bars
   a second composition run, and none occurs here.
3. **All-position team-rushing totals unchanged** — the S27 `(team, season)`
   rushing-TD sums computed over raw REG records WITH the placeholder rows
   equal the sums the matrix will compute over validated kept REG rows,
   compared zero-default over the union of keys (an excluded row is validated
   zero in every consumed column, so no aggregate can change; this measures
   that claim on the real store instead of trusting it).
4. **Input/frame digests unchanged** — the admitted weekly frame hashes
   identically before and after every operation above; the classifier copies,
   never mutates.

Wall-census discipline (R15-G2 mandated wording): closing this wall proves
this wall. Later composition stages are NOT exercised and NO claim is made
that no wall exists beyond it. No registered metric, statistic, status, or
readout is computed, printed, or persisted.
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
from src.dynasty_genius.eval.qb_validation.qb_ppg_labels import (  # noqa: E402
    PLACEHOLDER_D2_COLUMNS,
    _stat_decimal,
    exclude_provider_placeholder_rows,
)
from src.dynasty_genius.eval.qb_validation.study_matrix import (  # noqa: E402
    _records,
    _usable_text,
    _valid_label_season,
    _validated_weekly_row,
)


def _frame_digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def _missing_id(value: object) -> bool:
    return value is None or (isinstance(value, float) and value != value)


def main() -> int:
    load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=pd.read_parquet
    )

    admitted = pool["weekly"]["frame"]
    digest_before = _frame_digest(admitted)

    # ── Mirror of build_study_matrix's defensive weekly path, exactly ──────
    frame = admitted.copy()
    renames = VALIDATION_PARSED_RENAMES.get("weekly", {})
    pinned = tuple(
        renames.get(column, column)
        for column in VALIDATION_DATASET_COLUMNS["weekly"]
    )
    validate_dataset_shape(frame, dataset="weekly")
    validate_manifest_columns(frame, pinned, dataset="weekly")
    records = _records(frame)

    kept = exclude_provider_placeholder_rows(records)
    excluded_rows = [
        row
        for row in records
        if _missing_id(row.get("player_id"))
        and _missing_id(row.get("position"))
        and all(
            column in row
            and (v := _stat_decimal(column, row[column])) is not None
            and v == 0
            for column in PLACEHOLDER_D2_COLUMNS
        )
    ]
    excluded = len(records) - len(kept)
    reg_excluded = sum(
        1
        for row in excluded_rows
        if _usable_text(row.get("season_type")) == "REG"
    )
    print(f"defensive weekly records: {len(records)}")
    print(f"excluded at matrix seam: {excluded}")
    print(f"  of which REG (must be 192): {reg_excluded}")
    print(f"  of which non-REG: {excluded - reg_excluded}")
    residual_missing = sum(1 for row in kept if _missing_id(row.get("player_id")))
    print(f"kept rows with missing player_id (must be 0): {residual_missing}")

    # ── The R15 wall: matrix stage-(4) validation-law replay, kept rows ────
    reg_validated: list[dict[str, object]] = []
    try:
        for index, raw in enumerate(kept):
            row = _validated_weekly_row(raw, index)
            if row["season_type"] == "REG":
                reg_validated.append(row)
    except qb.QBValidationFailure as failure:
        print(f"matrix weekly validation REFUSED: reason={failure.reason}")
        print(f"detail: {failure.detail}")
        return 1
    print(
        "matrix weekly validation (_validated_weekly_row) passed over all "
        f"{len(kept)} kept records; REG validated rows: {len(reg_validated)}"
    )

    # ── S27 all-position team-rushing totals, with vs without placeholders ─
    before: dict[tuple[str, int], int] = {}
    unparseable = 0
    for row in records:  # WITH placeholder rows, raw REG slice
        if _usable_text(row.get("season_type")) != "REG":
            continue
        season = _valid_label_season(row.get("season"))
        team = _usable_text(row.get("team")) or ""
        value = _stat_decimal("rushing_tds", row.get("rushing_tds"))
        if season is None or value is None:
            unparseable += 1
            continue
        key = (team, season)
        before[key] = before.get(key, 0) + int(value)
    after: dict[tuple[str, int], int] = {}
    for row in reg_validated:  # WITHOUT placeholder rows, validated (matrix law)
        key = (row["team"], row["season"])
        after[key] = after.get(key, 0) + row["rushing_tds"]
    print(f"raw REG rows unparseable for team totals (expect 0): {unparseable}")
    mismatches = [
        key
        for key in set(before) | set(after)
        if before.get(key, 0) != after.get(key, 0)
    ]
    print(f"team-rushing (team, season) keys compared: {len(set(before) | set(after))}")
    print(f"team-rushing total mismatches (must be 0): {len(mismatches)}")
    if mismatches:
        for key in sorted(mismatches)[:5]:
            print(
                f"  MISMATCH {key}: with={before.get(key, 0)} "
                f"without={after.get(key, 0)}"
            )
        return 1

    digest_after = _frame_digest(pool["weekly"]["frame"])
    print(f"admitted weekly frame digest unchanged: {digest_before == digest_after}")
    ok = (
        reg_excluded == 192
        and residual_missing == 0
        and not mismatches
        and unparseable == 0
        and digest_before == digest_after
    )
    print(f"PROBE VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
