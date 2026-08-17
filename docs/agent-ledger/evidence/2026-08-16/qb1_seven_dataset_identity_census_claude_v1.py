"""Revision-103 diagnostic: ONE read-only identity census across ALL SEVEN
admitted QB-1 datasets (David's word via Codex's staged continuation; open
receipt `qb1_identity_census_continuation_open_receipt_codex_v1.md`).

Exactly one admission/load pass (`admit_and_load_validation_pool`, invoked
once; the frame loader is wrapped with a counter to PROVE one load per
dataset). Frames are censused in memory only. Every identity judgment uses the
SHIPPED consumer's own imported helpers — `_usable_player_id`,
`_valid_label_season`, `_usable_text`, `_stat_decimal`,
`exclude_provider_placeholder_rows`, `identity._usable_key` — never a
reimplementation, and never a universal predicate where the consumer law skips
rather than refuses. Per-dataset frame digests are taken before and after all
censusing to prove no mutation.

NOT run: the runner, the composition, any fold/lane/inference/report stage.
No repair, no input mutation, no registered value. Census facts are the
authorized output; nothing registered is computed, printed, or persisted.
H2 QB rushing remains UNDER TEST with no result.
"""

from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402
from scripts.run_qb1_study import RAW_ROOT, load_registration  # noqa: E402
from src.dynasty_genius.eval.qb_validation.identity import (  # noqa: E402
    _usable_key,
)
from src.dynasty_genius.eval.qb_validation.qb_ppg_labels import (  # noqa: E402
    PLACEHOLDER_D2_COLUMNS,
    _stat_decimal,
    _usable_player_id,
    _usable_text,
    _valid_label_season,
    exclude_provider_placeholder_rows,
)
from src.dynasty_genius.eval.qb_validation.sources import (  # noqa: E402
    VALIDATION_DATASETS,
)


def _digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()


def _is_null(value: object) -> bool:
    return value is None or (isinstance(value, float) and value != value)


def _pick(row: dict, *names: str) -> dict[str, object]:
    return {n: row.get(n) for n in names if n in row}


def _numeric_content(row: dict, numeric_cols: list[str]) -> tuple[bool, list]:
    """(all numeric cells zero-or-null, the nonzero cells if any)."""
    nonzero = []
    for c in numeric_cols:
        v = row.get(c)
        if _is_null(v):
            continue
        try:
            if float(v) != 0.0:
                nonzero.append((c, v))
        except (TypeError, ValueError):
            nonzero.append((c, v))
    return (not nonzero, nonzero)


def _shape_census(
    rows: list[tuple[int, dict]],
    numeric_cols: list[str],
    name_fields: tuple[str, ...],
) -> None:
    groups: dict[tuple, dict] = {}
    for index, row in rows:
        allzero, nonzero = _numeric_content(row, numeric_cols)
        key = tuple(
            f"{f}={_usable_text(row.get(f))!r}" for f in name_fields if f in row
        ) + (f"all_numeric_zero_or_null={allzero}",)
        g = groups.setdefault(
            key,
            {"n": 0, "seasons": set(), "first_index": index, "nonzero_ex": None},
        )
        g["n"] += 1
        g["seasons"].add(row.get("season"))
        if nonzero and g["nonzero_ex"] is None:
            g["nonzero_ex"] = (index, nonzero[:6])
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["n"]):
        seasons = sorted(s for s in g["seasons"] if s is not None)
        srange = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
        print(
            f"    shape {key}: n={g['n']} seasons={srange} "
            f"first_index={g['first_index']}"
        )
        if g["nonzero_ex"]:
            print(f"      NONZERO content example: {g['nonzero_ex']}")


def main() -> int:
    load_registration(REPO_ROOT)
    qb.enforce_consumer_boundary(repo_root=REPO_ROOT)

    load_counts: dict[str, int] = {}

    def counted_loader(path, *args, **kwargs):
        load_counts[str(path)] = load_counts.get(str(path), 0) + 1
        return pd.read_parquet(path, *args, **kwargs)

    pool = qb.admit_and_load_validation_pool(
        REPO_ROOT / RAW_ROOT, repo_root=REPO_ROOT, frame_loader=counted_loader
    )
    print(f"datasets admitted: {sorted(pool.keys())}")
    print(f"VALIDATION_DATASETS: {list(VALIDATION_DATASETS)}")
    multi = {p: n for p, n in load_counts.items() if n != 1}
    print(
        "ONE-PASS PROOF: admit_and_load_validation_pool invoked once; "
        f"loader calls={len(load_counts)} paths, each exactly once: {not multi}"
    )
    if multi:
        print(f"  MULTIPLE LOADS (defect in this probe, not the pool): {multi}")

    digests_before = {name: _digest(pool[name]["frame"]) for name in pool}

    numeric_cols_of = {
        name: [
            c
            for c in pool[name]["frame"].columns
            if pd.api.types.is_numeric_dtype(pool[name]["frame"][c])
            and c not in ("season", "week", "birth_year", "draft_year")
        ]
        for name in pool
    }

    # ── 1. weekly — matrix/label refuse-law after the shared classifier ────
    name = "weekly"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    reg = [r for r in records if _usable_text(r.get("season_type")) == "REG"]
    print(f"\n=== {name}: rows={len(records)} REG={len(reg)} "
          f"non-REG={len(records) - len(reg)}")
    print("  identity law: player_id+season REFUSE at _validated_weekly_row; "
          "shared classifier excludes exact placeholders first")
    missing = [
        (i, r) for i, r in enumerate(records)
        if _usable_player_id(r.get("player_id")) is None
    ]
    kept = exclude_provider_placeholder_rows(records)
    excluded = len(records) - len(kept)
    reg_excluded = len(reg) - len(exclude_provider_placeholder_rows(reg))
    print(f"  missing-player_id rows: {len(missing)}")
    print(f"  shared-17-D2-predicate exclusions: {excluded} "
          f"(REG {reg_excluded} + non-REG {excluded - reg_excluded}) — "
          f"reconciles 236=192+44: "
          f"{excluded == 236 and reg_excluded == 192}")
    residual = [
        (i, r) for i, r in missing
        if any(
            c not in r
            or (v := _stat_decimal(c, r[c])) is None
            or v != 0
            for c in PLACEHOLDER_D2_COLUMNS
        )
        or _usable_text(r.get("position")) is not None
    ]
    print(f"  missing-id rows NOT matching the ruled predicate (must be 0): "
          f"{len(residual)}")
    _shape_census(missing, numeric_cols_of[name],
                  ("player_name", "player_display_name", "position"))

    # ── 2. season_summary — matrix stage-1b REFUSE law ─────────────────────
    name = "season_summary"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    print(f"\n=== {name}: rows={len(records)} "
          "(no registered season-type field: no REG split)")
    print("  identity law: _usable_player_id(player_id)+_valid_label_season("
          "season) REFUSE stat_value_invalid at study_matrix.py:308-315")
    bad = [
        (i, r) for i, r in enumerate(records)
        if _usable_player_id(r.get("player_id")) is None
        or _valid_label_season(r.get("season")) is None
    ]
    print(f"  unusable-identity rows (the refusal class): {len(bad)}")
    if bad:
        print(f"  FIRST refusing index: {bad[0][0]}")
        print("  FULL ENUMERATION (index, season, name/position audit fields, "
              "validated passing_cpoe, all-numeric-zero):")
        for i, r in bad:
            cpoe = r.get("passing_cpoe")
            cpoe_fact = (
                "null" if _is_null(cpoe) else f"value={cpoe!r}"
            )
            allzero, nonzero = _numeric_content(r, numeric_cols_of[name])
            print(
                f"    [{i}] season={r.get('season')!r} "
                f"{_pick(r, 'player_name', 'player_display_name', 'position')} "
                f"passing_cpoe={cpoe_fact} all_numeric_zero_or_null={allzero}"
                + (f" NONZERO={nonzero[:6]}" if nonzero else "")
            )
        _shape_census(bad, numeric_cols_of[name],
                      ("player_name", "player_display_name", "position"))

    # ── 3. players — consumer SKIPS unusable gsis_id (never refuses) ───────
    name = "players"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    print(f"\n=== {name}: rows={len(records)} (no season-type field)")
    print("  identity law: keyed by _usable_player_id(gsis_id); unusable rows "
          "are SKIPPED by the dict build (study_matrix.py:344-348), no refusal")
    bad = [
        (i, r) for i, r in enumerate(records)
        if _usable_player_id(r.get("gsis_id")) is None
    ]
    print(f"  unusable-gsis_id rows (skipped, not refused): {len(bad)}")
    _shape_census(bad, numeric_cols_of[name],
                  ("display_name", "player_name", "position"))

    # ── 4. rosters — consumer SKIPS unusable ids; REG filter by game_type ──
    name = "rosters"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    reg = [r for r in records if _usable_text(r.get("game_type")) == "REG"]
    print(f"\n=== {name}: rows={len(records)} REG={len(reg)} "
          f"non-REG={len(records) - len(reg)} (split by game_type)")
    print("  identity law: pid=_usable_player_id(player_id or gsis_id); "
          "unusable → continue (study_matrix.py:333-337), no refusal")
    bad = [
        (i, r) for i, r in enumerate(records)
        if _usable_player_id(r.get("player_id") or r.get("gsis_id")) is None
    ]
    print(f"  unusable-identity rows (skipped, not refused): {len(bad)}")
    _shape_census(bad, numeric_cols_of[name],
                  ("player_name", "full_name", "position"))

    # ── 5. ff_playerids — D1-admitted identity dataset; matrix non-consumer ─
    name = "ff_playerids"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    print(f"\n=== {name}: rows={len(records)} (no season-type field)")
    print("  consumer disposition: admitted at D1 as the fresh identity "
          "DATASET; the shipped composition consumes the SEPARATE pinned "
          "crosswalk COPY as the H5 join instrument (run_qb1_study.py:54-64); "
          "build_study_matrix does not read this frame — no refusal path")
    bad = [
        (i, r) for i, r in enumerate(records)
        if _usable_player_id(r.get("gsis_id")) is None
    ]
    print(f"  rows with unusable gsis_id (descriptive only): {len(bad)}")
    print(f"  columns: {sorted(frame.columns.tolist())[:12]}…")

    # ── 6. draft_picks — resolve_draft_join law; TRIAGE never refuses ──────
    name = "draft_picks"
    frame = pool[name]["frame"]
    records = [dict(r) for r in frame.to_dict("records")]
    print(f"\n=== {name}: rows={len(records)} (no season-type field)")
    print("  identity law: draft-side keys via identity._usable_key inside "
          "resolve_draft_join (F34); a missing-like gsis never raises and "
          "never equals a real key; TRIAGE never becomes imputed capital "
          "(S30) — no refusal path")
    bad = [
        (i, r) for i, r in enumerate(records)
        if _usable_key(r.get("gsis_id")) is None
    ]
    print(f"  rows with unusable gsis_id (join-inert, not refused): {len(bad)}")
    _shape_census(bad, numeric_cols_of[name],
                  ("pfr_player_name", "player_name", "position"))

    # ── 7. pbp — team/context keyed; NO player-identity field ──────────────
    name = "pbp"
    frame = pool[name]["frame"]
    print(f"\n=== {name}: rows={len(frame)} cols={len(frame.columns)}")
    print("  identity law: the pinned pbp schema is TEAM/CONTEXT keyed and "
          "has NO player-identity field; the matrix consumes (season_type, "
          "offense_team, season, pass_oe) at study_matrix.py:380-391 — "
          "null pass_oe rows are skipped; a non-null NON-FINITE pass_oe "
          "REFUSES stat_value_invalid via _finite_float")
    st = frame["season_type"].map(_usable_text)
    print(f"  season_type census: {st.value_counts(dropna=False).to_dict()} "
          "(post-R15-parse frame is REG-only by construction)")
    seasons_bad = frame["season"].map(_valid_label_season).isna()
    print(f"  rows with invalid season (skipped by the .get guard): "
          f"{int(seasons_bad.sum())}")
    team_missing = frame["offense_team"].map(_usable_text).isna()
    print(f"  rows with missing offense_team (keyed under '' — consumed, "
          f"not refused): {int(team_missing.sum())}")
    oe = frame["pass_oe"]
    oe_nonnull = oe[~oe.isna()]
    nonfinite = oe_nonnull[~oe_nonnull.map(
        lambda v: isinstance(v, (int, float)) and math.isfinite(float(v))
    )]
    print(f"  pass_oe: non-null={len(oe_nonnull)} "
          f"NON-FINITE non-null (the REFUSE class, must be 0 to pass): "
          f"{len(nonfinite)}")
    if len(nonfinite):
        print(f"    first refusing positional index: "
              f"{frame.index.get_loc(nonfinite.index[0])} "
              f"value={nonfinite.iloc[0]!r}")

    # ── digest proof ───────────────────────────────────────────────────────
    print("\n=== DIGEST PROOF (before == after, per dataset):")
    ok = True
    for dname in sorted(pool):
        same = digests_before[dname] == _digest(pool[dname]["frame"])
        ok = ok and same
        print(f"  {dname}: unchanged={same}")
    print(f"ALL FRAMES UNMUTATED: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
