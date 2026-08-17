"""Revision-110 diagnostic: ONE read-only F34 draft-join TRIAGE replay over
the frozen admitted study-QB surface (David's word via Codex's staged
continuation; open receipt
`qb1_f34_triage_diagnostic_continuation_open_receipt_codex_v1.md`).

Shipped semantics only, runner-identical call shapes: D1 admission
(`admit_and_load_validation_pool`, counted loader — one load per path proven)
→ D2 labels (`build_label_table` on the REG-filtered, classifier-excluded
weekly records, exactly `run_qb1_study.py:992-997`) → D2a matrix
(`build_study_matrix(pool, registration=…, expected_registration_hash=…)`,
exactly `:1004-1008`) → the ridge lane's OWN label-lookup validator
(`ridge_lane._validate_label_table`). THE MATRIX/F34 STAGE IS THE CEILING:
no folds, no ridge fit, no inference, no comparison, no report, no runner.

The H4 gate ordering is mirrored from `ridge_lane.py` phase 3 verbatim over
cohort-admitted matrix rows (fold membership does not change any gate input,
so per-row gate outcomes are fold-invariant): target/no-target → label
presence cross-check → feature presence/validity → >50% missingness drop →
the draft-capital null refusal. Affected keys are re-resolved through the
SHIPPED `resolve_draft_join` with the exact study rows and draft records the
matrix itself constructs; both-route match multiplicity is measured with the
shipped `identity._usable_key` / `identity.normalize_name` helpers. Nothing
is mutated (per-frame canonical digests before/after prove it) and nothing
registered is computed past the matrix stage; label PPG values are used only
as an existence set, never printed.

Boundary: this diagnoses the F34/H4 seam ONLY and makes NO claim that no
other wall remains. H2 QB rushing remains UNDER TEST with no result.
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
    _usable_key,
    normalize_name,
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


def _digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def _safe(value: object) -> str:
    return repr(value)


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
    print(
        "ONE-PASS PROOF: admit_and_load_validation_pool invoked once; "
        f"{len(load_counts)} paths, each loaded exactly once: {not multi}"
    )
    digests_before = {name: _digest(pool[name]["frame"]) for name in pool}

    # ── shipped D2 labels + the lane's own lookup (existence only) ─────────
    weekly_records = filter_reg_weekly_records(pool["weekly"]["frame"])
    label_out = qb.build_label_table(
        exclude_provider_placeholder_rows(weekly_records),
        registration["scoring"]["components"],
        expected_settings_hash=registration["scoring"]["settings_hash"],
    )
    labels = label_out["labels"]
    label_lookup = _validate_label_table(labels)
    print(f"label lookup keys (existence set only): {len(label_lookup)}")

    # ── shipped D2a matrix (runner-identical call) — THE CEILING ───────────
    matrix_out = qb.build_study_matrix(
        pool,
        registration=dict(registration),
        expected_registration_hash=qb.REGISTRATION_PIN,
    )
    rows = matrix_out["matrix"]
    print(f"matrix rows: {len(rows)}")

    h4_features = tuple(name for name, _ in H4_MANIFEST)

    # ── H4 phase-3 gate mirror (ridge_lane.py:167-203), fold-invariant ─────
    admitted = [r for r in rows if r.get("eligibility") == "cohort_admitted"]
    print(f"cohort_admitted rows: {len(admitted)}")
    mismatches = []
    skipped_no_target = 0
    dropped_missingness: list[tuple[str, int]] = []
    survivors = []
    for row in admitted:
        key = (row["player_id"], row["target_season"])
        present = key in label_lookup
        if row["target"] == "target_evaluable" and not present:
            mismatches.append(("evaluable_without_label", key))
            continue
        if row["target"] == "no_target_season":
            if present:
                mismatches.append(("no_target_with_label", key))
            skipped_no_target += 1
            continue
        bad_value = False
        for name in h4_features:
            if name not in row:
                mismatches.append(("manifest_feature_missing", key, name))
                bad_value = True
                break
            value = row.get(name)
            if value is not None and not _exact_number(value):
                mismatches.append(("imputer_value_invalid", key, name))
                bad_value = True
                break
        if bad_value:
            continue
        missing = sum(1 for name in h4_features if row.get(name) is None)
        if missing / len(h4_features) > _ROW_DROP_FRACTION:
            dropped_missingness.append(key)
            continue
        survivors.append(row)
    print(f"no_target_season rows skipped pre-capital: {skipped_no_target}")
    print(f">50%-missingness drops pre-capital: {len(dropped_missingness)} "
          f"{sorted(dropped_missingness)}")
    print(f"cross-check mismatches (must be 0): {len(mismatches)} {mismatches[:5]}")
    print(f"rows surviving the pre-draft-capital H4 gates: {len(survivors)}")

    affected = [
        row
        for row in survivors
        if any(row.get(name) is None for name in _DRAFT_CAPITAL_FEATURES)
    ]
    affected_keys = sorted(
        {(row["player_id"], row["target_season"]) for row in affected}
    )
    affected_players = sorted({pid for pid, _ in affected_keys})
    print(f"\nH4 NULL-CAPITAL rows (the refusal set): {len(affected)}")
    print(f"distinct (player_id, target_season) keys: {len(affected_keys)}")
    print(f"distinct players: {len(affected_players)} {affected_players}")

    # ── mirror the matrix's own study rows + draft records for F34 replay ──
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

    # ── (1)+(2)+(3): per-affected-player full F34 audit + multiplicity ─────
    print("\n=== PER-PLAYER F34 REPLAY (exact shipped resolver) ===")
    triage_reasons: dict[str, int] = {}
    for pid in affected_players:
        player_row = players_by_id.get(pid)
        study = dict(player_row) if player_row else {"gsis_id": pid}
        record = resolve_draft_join(study, draft_rows)
        gsis = _usable_key(study.get("gsis_id"))
        gsis_matches = [
            r for r in draft_rows if _usable_key(r.get("gsis_id")) == gsis
        ] if gsis is not None else []
        sname = normalize_name(
            study.get("display_name") or study.get("player_name") or ""
        )
        name_matches = (
            [
                r
                for r in draft_rows
                if normalize_name(
                    r.get("pfr_player_name") or r.get("player_name") or ""
                )
                == sname
            ]
            if sname
            else []
        )
        print(f"\nplayer {pid}:")
        print(f"  players-row present: {player_row is not None}")
        print(
            "  identity fields: "
            f"display_name={_safe(study.get('display_name'))} "
            f"player_name={_safe(study.get('player_name'))} "
            f"birth_date={_safe(study.get('birth_date'))} "
            f"college={_safe(study.get('college_name'))}"
        )
        print(
            f"  resolution={record.get('resolution')} "
            f"reason={record.get('reason')} matched_by={record.get('matched_by')}"
        )
        print(
            f"  audit: draft_row_id={_safe(record.get('draft_row_id'))} "
            f"norm_study_name={_safe(record.get('normalized_study_name'))} "
            f"norm_draft_name={_safe(record.get('normalized_draft_name'))}"
        )
        print(f"  age_check={record.get('age_check')}")
        print(f"  college_check={record.get('college_check')}")
        print(
            f"  multiplicity: usable-GSIS candidates={len(gsis_matches)} "
            f"normalized-name candidates={len(name_matches)}"
        )
        for label_, cands in (("gsis", gsis_matches), ("name", name_matches)):
            for r in cands[:5]:
                print(
                    f"    considered[{label_}]: season={_safe(r.get('season'))} "
                    f"round={_safe(r.get('round'))} pick={_safe(r.get('pick'))} "
                    f"name={_safe(r.get('pfr_player_name') or r.get('player_name'))} "
                    f"gsis={_safe(r.get('gsis_id'))}"
                )
        if record.get("resolution") == "TRIAGE":
            reason = record.get("reason") or "unspecified"
            triage_reasons[reason] = triage_reasons.get(reason, 0) + 1

    # ── (4): bidirectional reconciliation over ALL matrix players ──────────
    print("\n=== RECONCILIATION (both directions) ===")
    all_matrix_players = sorted({row["player_id"] for row in rows})
    triage_players = []
    for pid in all_matrix_players:
        player_row = players_by_id.get(pid)
        study = dict(player_row) if player_row else {"gsis_id": pid}
        record = resolve_draft_join(study, draft_rows)
        if record.get("resolution") == "TRIAGE":
            triage_players.append((pid, record.get("reason")))
    print(f"matrix distinct players: {len(all_matrix_players)}")
    print(f"F34 TRIAGE players among them: {len(triage_players)} "
          f"{triage_players}")
    triage_ids = {pid for pid, _ in triage_players}
    null_rows_all = [
        row
        for row in rows
        if any(row.get(name) is None for name in _DRAFT_CAPITAL_FEATURES)
    ]
    null_ids = {row["player_id"] for row in null_rows_all}
    print(f"matrix rows carrying any null capital (all rows): {len(null_rows_all)}; "
          f"distinct players: {sorted(null_ids)}")
    print(f"TRIAGE players with NO null-capital matrix row: "
          f"{sorted(triage_ids - null_ids)}")
    print(f"null-capital players with NO TRIAGE resolution: "
          f"{sorted(null_ids - triage_ids)}")
    reach = {
        pid: {
            "matrix_rows": sum(1 for r in rows if r["player_id"] == pid),
            "gate_surviving_rows": sum(
                1 for r in survivors if r["player_id"] == pid
            ),
            "h4_null_refusal_rows": sum(
                1 for r in affected if r["player_id"] == pid
            ),
        }
        for pid in sorted(triage_ids | null_ids)
    }
    for pid, counts in reach.items():
        print(f"  {pid}: {counts}")
    triage_never_reaching = [
        pid
        for pid in sorted(triage_ids)
        if reach.get(pid, {}).get("h4_null_refusal_rows", 0) == 0
    ]
    print(f"TRIAGE identities never reaching an H4 refusal row: "
          f"{triage_never_reaching}")

    # ── (6): grouped counts ────────────────────────────────────────────────
    print("\n=== GROUPED COUNTS ===")
    print(f"affected H4-refusal rows by target season: "
          f"{ {s: sum(1 for r in affected if r['target_season'] == s) for s in sorted({r['target_season'] for r in affected}) } }")
    print(f"affected players' TRIAGE reasons: {triage_reasons}")

    # ── (5): digest proof ──────────────────────────────────────────────────
    print("\n=== DIGEST PROOF ===")
    ok = True
    for name in sorted(pool):
        same = digests_before[name] == _digest(pool[name]["frame"])
        ok = ok and same
        print(f"  {name}: unchanged={same}")
    print(f"ALL FRAMES UNMUTATED: {ok}")
    print(
        "\nBOUNDARY: this diagnostic covers the F34/H4 seam only; no claim is "
        "made that no other wall remains. No fold, ridge fit, inference, "
        "comparison, or report was computed; label values served as an "
        "existence set only."
    )
    return 0 if ok and not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
