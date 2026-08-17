"""R18 mandatory final-pin real-surface replay: the registered F34 college
normalization against the REAL admitted store — NO composition.

Verifies, at the final Round-18 pins, every expectation Codex's transition
mandates: (1) the 49 previously-affected players resolve authoritative
DRAFTED capital with the ORIGINAL draft-row round/pick, and every one of
their matrix rows (which include all 143 previously-refusing H4 rows) carries
non-null capital; (2) all 67 representation-only TRIAGE players resolve
DRAFTED; (3) the residual TRIAGE set is EXACTLY {00-0029857, 00-0037175},
both `cross_check_conflict` (the two pinned true negative controls);
(4) ZERO H4 gate-surviving rows retain null draft capital (the phase-3 gate
mirror re-run at final pins); (5) before/after resolution counts reconcile in
both directions against the pinned v2 diagnostic evidence (69 = 67 flipped +
2 residual; after-TRIAGE ⊆ before-TRIAGE; monotonicity: the law can only
flip conflict→pass, never pass→conflict, and the replay confirms no new
TRIAGE); (6) one admission/load pass and all seven admitted frame digests
unchanged. Ceiling: labels + matrix + resolver replay only — no folds, ridge
fit, inference, comparison, report, or runner. H2 QB rushing remains UNDER
TEST with no result.
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
    RAW_ROOT,
    exclude_provider_placeholder_rows,
    filter_reg_weekly_records,
    load_registration,
)
from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (  # noqa: E402
    VALIDATION_DATASET_COLUMNS,
    VALIDATION_PARSED_RENAMES,
)
from src.dynasty_genius.eval.qb_validation.folds import (  # noqa: E402
    _DRAFT_CAPITAL_FEATURES,
)
from src.dynasty_genius.eval.qb_validation.guards import (  # noqa: E402
    validate_dataset_shape,
    validate_manifest_columns,
)
from src.dynasty_genius.eval.qb_validation.identity import (  # noqa: E402
    _parse_int,
    _usable_key,
    resolve_draft_join,
)
from src.dynasty_genius.eval.qb_validation.ridge_lane import (  # noqa: E402
    _ROW_DROP_FRACTION,
    _exact_number,
    _validate_label_table,
)
from src.dynasty_genius.eval.qb_validation.study_matrix import (  # noqa: E402
    H4_MANIFEST,
    _records,
    _usable_player_id,
)

# Pinned BEFORE state — the v2 diagnostic's 69 TRIAGE players (output
# `qb1_f34_triage_diagnostic_claude_v2_output.txt`, all cross_check_conflict).
BEFORE_TRIAGE = {
    "00-0007091", "00-0021206", "00-0022924", "00-0022942", "00-0023459",
    "00-0023645", "00-0024279", "00-0025430", "00-0026143", "00-0026158",
    "00-0026993", "00-0027796", "00-0027939", "00-0028012", "00-0029263",
    "00-0029531", "00-0029567", "00-0029604", "00-0029677", "00-0029682",
    "00-0029857", "00-0030520", "00-0030526", "00-0031064", "00-0031076",
    "00-0031266", "00-0031280", "00-0031395", "00-0031407", "00-0031503",
    "00-0032245", "00-0032431", "00-0032436", "00-0032893", "00-0032950",
    "00-0033077", "00-0033098", "00-0033119", "00-0033958", "00-0034401",
    "00-0034412", "00-0034771", "00-0034855", "00-0034857", "00-0035146",
    "00-0035228", "00-0035232", "00-0035251", "00-0035264", "00-0035282",
    "00-0035289", "00-0035652", "00-0036264", "00-0036312", "00-0036389",
    "00-0036442", "00-0036945", "00-0037012", "00-0037175", "00-0037327",
    "00-0037834", "00-0038108", "00-0038128", "00-0038998", "00-0039152",
    "00-0039376", "00-0039398", "00-0039917", "00-0039918",
}
# The 49 that previously reached the H4 refusal (143 rows), from the same
# pinned evidence.
BEFORE_AFFECTED_49 = {
    "00-0021206", "00-0022924", "00-0022942", "00-0023459", "00-0023645",
    "00-0025430", "00-0026143", "00-0026158", "00-0027939", "00-0028012",
    "00-0029263", "00-0029567", "00-0029604", "00-0029682", "00-0030520",
    "00-0030526", "00-0031076", "00-0031280", "00-0031395", "00-0031407",
    "00-0031503", "00-0032245", "00-0032436", "00-0032950", "00-0033077",
    "00-0033119", "00-0033958", "00-0034401", "00-0034771", "00-0034855",
    "00-0034857", "00-0035228", "00-0035232", "00-0035264", "00-0035289",
    "00-0035652", "00-0036264", "00-0036389", "00-0036442", "00-0036945",
    "00-0037012", "00-0037834", "00-0038108", "00-0038128", "00-0039152",
    "00-0039376", "00-0039398", "00-0039917", "00-0039918",
}
EXPECTED_RESIDUAL = {"00-0029857", "00-0037175"}


def _digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def main() -> int:
    registration = load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)
    load_counts: dict[str, int] = {}

    def counted_loader(path, *args, **kwargs):
        load_counts[str(path)] = load_counts.get(str(path), 0) + 1
        return pd.read_parquet(path, *args, **kwargs)

    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=counted_loader
    )
    multi = {p: n for p, n in load_counts.items() if n != 1}
    print(f"ONE-PASS PROOF: {len(load_counts)} paths, each once: {not multi}")
    digests_before = {name: _digest(pool[name]["frame"]) for name in pool}

    weekly_records = filter_reg_weekly_records(pool["weekly"]["frame"])
    label_out = qb.build_label_table(
        exclude_provider_placeholder_rows(weekly_records),
        registration["scoring"]["components"],
        expected_settings_hash=registration["scoring"]["settings_hash"],
    )
    label_lookup = _validate_label_table(label_out["labels"])
    matrix_out = qb.build_study_matrix(
        pool,
        registration=dict(registration),
        expected_registration_hash=qb.REGISTRATION_PIN,
    )
    rows = matrix_out["matrix"]
    print(f"matrix rows: {len(rows)}")

    # ── (4) H4 phase-3 gate mirror at FINAL pins ───────────────────────────
    h4_features = tuple(name for name, _ in H4_MANIFEST)
    survivors = []
    for row in rows:
        if row.get("eligibility") != "cohort_admitted":
            continue
        key = (row["player_id"], row["target_season"])
        present = key in label_lookup
        if row["target"] == "target_evaluable" and not present:
            print(f"UNEXPECTED evaluable-without-label {key}")
            return 1
        if row["target"] == "no_target_season":
            continue
        if any(
            name not in row
            or (row.get(name) is not None and not _exact_number(row.get(name)))
            for name in h4_features
        ):
            print(f"UNEXPECTED feature presence/validity failure {key}")
            return 1
        missing = sum(1 for name in h4_features if row.get(name) is None)
        if missing / len(h4_features) > _ROW_DROP_FRACTION:
            continue
        survivors.append(row)
    null_survivors = [
        (r["player_id"], r["target_season"])
        for r in survivors
        if any(r.get(n) is None for n in _DRAFT_CAPITAL_FEATURES)
    ]
    print(f"H4 gate-surviving rows: {len(survivors)}")
    print(f"H4 gate-surviving rows with null capital (MUST be 0): "
          f"{len(null_survivors)} {null_survivors[:5]}")

    # ── mirror study rows + draft records for the resolver replay ──────────
    players_frame = pool["players"]["frame"].copy()
    validate_dataset_shape(players_frame, dataset="players")
    validate_manifest_columns(
        players_frame,
        tuple(
            VALIDATION_PARSED_RENAMES.get("players", {}).get(c, c)
            for c in VALIDATION_DATASET_COLUMNS["players"]
        ),
        dataset="players",
    )
    players_by_id = {
        _usable_player_id(row.get("gsis_id")): row
        for row in _records(players_frame)
        if _usable_player_id(row.get("gsis_id")) is not None
    }
    draft_frame = pool["draft_picks"]["frame"].copy()
    validate_dataset_shape(draft_frame, dataset="draft_picks")
    validate_manifest_columns(
        draft_frame,
        tuple(
            VALIDATION_PARSED_RENAMES.get("draft_picks", {}).get(c, c)
            for c in VALIDATION_DATASET_COLUMNS["draft_picks"]
        ),
        dataset="draft_picks",
    )
    draft_rows = _records(draft_frame)

    # ── (1)(2)(3)(5): full 179-player replay + reconciliation ──────────────
    all_players = sorted({row["player_id"] for row in rows})
    after_triage: dict[str, str] = {}
    drafted: dict[str, dict] = {}
    other: dict[str, str] = {}
    for pid in all_players:
        player_row = players_by_id.get(pid)
        study = dict(player_row) if player_row else {"gsis_id": pid}
        record = resolve_draft_join(study, draft_rows)
        resolution = record.get("resolution")
        if resolution == "TRIAGE":
            after_triage[pid] = record.get("reason")
        elif resolution == "DRAFTED":
            drafted[pid] = record
        else:
            other[pid] = resolution
    print(f"\nmatrix distinct players: {len(all_players)}")
    print(f"after: TRIAGE={len(after_triage)} DRAFTED={len(drafted)} "
          f"other(UDFA)={len(other)}")
    print(f"residual TRIAGE set == {{00-0029857, 00-0037175}}: "
          f"{set(after_triage) == EXPECTED_RESIDUAL} ({after_triage})")
    print(f"residual reasons both cross_check_conflict: "
          f"{all(r == 'cross_check_conflict' for r in after_triage.values())}")
    new_triage = set(after_triage) - BEFORE_TRIAGE
    print(f"after-TRIAGE within before-TRIAGE (no new TRIAGE, monotone): "
          f"{not new_triage} (new={sorted(new_triage)})")
    flipped = BEFORE_TRIAGE - set(after_triage)
    print(f"flipped players: {len(flipped)} (must be 67: {len(flipped) == 67})")
    flipped_drafted = [p for p in flipped if p in drafted]
    print(f"all 67 flipped resolve DRAFTED: "
          f"{len(flipped_drafted) == len(flipped)} "
          f"(non-DRAFTED flipped: {sorted(set(flipped) - set(flipped_drafted))})")
    print(f"49 previously-H4-affected all flipped+DRAFTED: "
          f"{BEFORE_AFFECTED_49 <= set(flipped_drafted)}")

    # ── (1) original-capital verification for the 49 ───────────────────────
    capital_ok = True
    checked_rows = 0
    for pid in sorted(BEFORE_AFFECTED_49):
        record = drafted.get(pid)
        gsis_candidates = [
            r for r in draft_rows if _usable_key(r.get("gsis_id")) == pid
        ]
        if record is None or len(gsis_candidates) != 1:
            print(f"  CAPITAL CHECK FAIL {pid}: record={record is not None} "
                  f"candidates={len(gsis_candidates)}")
            capital_ok = False
            continue
        original_round = _parse_int(gsis_candidates[0].get("round"))
        original_pick = _parse_int(gsis_candidates[0].get("pick"))
        if (
            record.get("draft_round") != original_round
            or record.get("draft_overall") != original_pick
            or record.get("is_udfa") != 0
        ):
            print(f"  CAPITAL MISMATCH {pid}: resolver="
                  f"{record.get('draft_round')}/{record.get('draft_overall')} "
                  f"original={original_round}/{original_pick}")
            capital_ok = False
        matrix_rows_pid = [r for r in rows if r["player_id"] == pid]
        for r in matrix_rows_pid:
            checked_rows += 1
            if (
                r.get("draft_round") != original_round
                or r.get("draft_overall") != original_pick
                or r.get("is_udfa") != 0
            ):
                print(f"  MATRIX CAPITAL MISMATCH {pid} "
                      f"season={r['target_season']}")
                capital_ok = False
    print(f"49-player ORIGINAL round/pick verification across "
          f"{checked_rows} matrix rows: {'PASS' if capital_ok else 'FAIL'}")

    # ── (6) digest proof ───────────────────────────────────────────────────
    ok = True
    for name in sorted(pool):
        same = digests_before[name] == _digest(pool[name]["frame"])
        ok = ok and same
    print(f"ALL FRAMES UNMUTATED: {ok}")

    verdict = (
        not multi
        and not null_survivors
        and set(after_triage) == EXPECTED_RESIDUAL
        and all(r == "cross_check_conflict" for r in after_triage.values())
        and not new_triage
        and len(flipped) == 67
        and len(flipped_drafted) == len(flipped)
        and BEFORE_AFFECTED_49 <= set(flipped_drafted)
        and capital_ok
        and ok
    )
    print(f"\nPROBE VERDICT: {'PASS' if verdict else 'FAIL'}")
    print("BOUNDARY: labels+matrix+resolver replay only; no composition; "
          "F34/H4 seam only — no last-wall claim.")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
