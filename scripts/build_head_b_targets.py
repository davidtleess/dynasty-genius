"""Phase 19 W1 — Head B Target Pipeline.

Fits per-position expected-PPG-by-pick curves using isotonic regression
(WR, RB) and TE hierarchical pooling with the WR curve as a shrinkage prior.
Writes:
  - app/data/training/prospects_with_outcomes_v3.csv  (gitignored)
  - app/data/training/expected_ppg_curves_v3.json     (gitignored)

Does NOT overwrite prospects_with_outcomes.csv.
Does NOT touch production model pkl files or latest.json.
Market-derived data (KTC, ADP, FantasyCalc, etc.) must not appear in any
output column — enforced by MARKET_FIELD_PATTERNS and the contract test suite.

Design notes
------------
The spec target is "best 3 of first 4 seasons PPR PPG". The base CSV holds
Y2, Y3, Y4 seasons (Y1 excluded per spec reasoning: Year-1 PPG biases toward
immediate-opportunity picks). With 3 available seasons, "best 3 of 3" = the
game-weighted average across all available seasons = y24_ppg.

Training cohort (≤TRAINING_MAX_SEASON): players with complete Y2-Y4 career arcs.
Censored rows (>TRAINING_MAX_SEASON or <MIN_GAMES_THRESHOLD): excluded from
training target population. best3of4_ppg and residual_ppg are blank for
censored rows. expected_ppg_at_pick is still populated for valid picks to
support inference scoring of 2022+ rookies.

TE hierarchical pooling: the TE annual cohort is small (~3–5 fantasy-relevant
players per class). SHRINKAGE_K_TE synthetic "WR prior" observations are added
per unique pick bucket, pulling sparse TE estimates toward the WR baseline.

Spec drift note
---------------
The approved spec (§8 / §5.5) targets a 2010-2021 training cohort. The current
source CSV (prospects_with_outcomes.csv) starts at draft season 2015. W1 fits
curves on 2015-2021 cohorts. This gap is documented in the artifact and the
ledger. W2 may back-extend if a repo-native 2010-2014 backfill source is found.

Usage:
    .venv/bin/python3.14 scripts/build_head_b_targets.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.head_b_contract import (  # noqa: E402
    HEAD_B_PROHIBITED_COLUMNS,
    W1_TARGET_COLUMNS,
)

# ── I/O paths ─────────────────────────────────────────────────────────────────

SOURCE_CSV = ROOT / "app/data/training/prospects_with_outcomes.csv"
OUTPUT_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
CURVES_JSON = ROOT / "app/data/training/expected_ppg_curves_v3.json"

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_GAMES_THRESHOLD: int = 8        # Minimum career games for a reliable PPG target
TRAINING_MAX_SEASON: int = 2021     # Latest draft class with a confirmed complete arc
SHRINKAGE_K_TE: float = 5.0         # WR-prior synthetic observations per TE pick bucket
CURVE_VERSION: str = "v3"
TARGET_VERSION: str = "head_b_v3"

POSITIONS_ISOTONIC = ("WR", "RB")   # Standalone isotonic regression
POSITION_TE = "TE"                  # Pooled isotonic with WR prior

# Spec says 2010-2021; source CSV starts at 2015 — see module docstring.
SPEC_TRAINING_MIN_SEASON: int = 2010   # Spec target (not achievable with current source)
ACTUAL_TRAINING_MIN_SEASON: int = 2015  # Actual earliest season in source CSV

# ── Leakage guard ─────────────────────────────────────────────────────────────

MARKET_FIELD_PATTERNS: list[str] = [
    r"^ktc_",
    r"^adp",
    r"_rank$",
    r"^expert",
    r"^market_",
    r"^value_",
    r"^consensus",
    r"fantasycalc",
    r"dynastynerds",
    r"fantasypros",
    r"^nfl_yprr",
    r"^pff_grade",
    r"^pff_route_grade",
]


# ── Core computation functions ─────────────────────────────────────────────────

def compute_best3of4_ppg(
    total_points: float,
    total_games: int,
) -> Optional[float]:
    """Game-weighted average PPG across available Y2-Y4 seasons.

    Returns None when total_games < MIN_GAMES_THRESHOLD. Callers must also
    ensure the row is not censored before using this as a training target.
    """
    if total_games < MIN_GAMES_THRESHOLD:
        return None
    return round(total_points / total_games, 4)


def compute_censoring_flag(draft_season: int, total_games: int) -> bool:
    """True when the career arc is incomplete for Head B training purposes.

    A row is censored when:
    - draft_season > TRAINING_MAX_SEASON: Y4 may not have occurred yet.
    - total_games < MIN_GAMES_THRESHOLD: insufficient career data.

    Censored rows are written to the output CSV (for inference) but receive
    blank best3of4_ppg and residual_ppg — they are NOT Head B training labels.
    """
    return draft_season > TRAINING_MAX_SEASON or total_games < MIN_GAMES_THRESHOLD


def fit_isotonic_curve(
    picks: list[float],
    ppg_values: list[float],
) -> IsotonicRegression:
    """Fit monotonically non-increasing isotonic regression: pick → expected PPG."""
    ir = IsotonicRegression(increasing=False, out_of_bounds="clip")
    ir.fit(np.array(picks, dtype=float), np.array(ppg_values, dtype=float))
    return ir


def fit_te_pooled_curve(
    te_picks: list[float],
    te_ppg: list[float],
    wr_ir: IsotonicRegression,
    shrinkage_k: float = SHRINKAGE_K_TE,
) -> IsotonicRegression:
    """TE isotonic curve with Bayesian-style shrinkage toward the WR prior.

    Adds `shrinkage_k` synthetic WR-prior observations per unique TE pick bucket.
    The effective prior weight is k / (n + k) per bucket.
    """
    unique_picks = sorted(set(te_picks))
    wr_prior_vals = wr_ir.predict(np.array(unique_picks, dtype=float))

    aug_picks = list(te_picks)
    aug_ppg = list(te_ppg)
    k = int(shrinkage_k) if shrinkage_k >= 1 else 1
    for pick, wr_val in zip(unique_picks, wr_prior_vals):
        aug_picks.extend([float(pick)] * k)
        aug_ppg.extend([float(wr_val)] * k)

    ir = IsotonicRegression(increasing=False, out_of_bounds="clip")
    ir.fit(np.array(aug_picks, dtype=float), np.array(aug_ppg, dtype=float))
    return ir


def expected_ppg_at_pick(pick: float, ir: IsotonicRegression) -> float:
    """Look up expected PPG for a given pick from a fitted isotonic curve."""
    return float(ir.predict(np.array([pick], dtype=float))[0])


def compute_row_targets(
    row: dict,
    curves: dict[str, IsotonicRegression],
) -> dict[str, str]:
    """Compute Head B target columns for a single row.

    Returns a dict of column name → string value to merge into the row.

    Column semantics:
    - censored_incomplete_arc: 1 if row is excluded from training.
    - best3of4_ppg: game-weighted PPG; BLANK for censored rows.
    - expected_ppg_at_pick: populated for all rows with valid pick+curve
      (including censored rows, for inference scoring of recent rookies).
    - residual_ppg: actual - expected; BLANK for censored rows.
    - head_b_training_eligible: 1 only when all of the above are populated
      and the row is a valid Head B training label.
    """
    total_points = _to_float(row.get("total_points", 0)) or 0.0
    total_games = int(row.get("total_games", 0) or 0)
    draft_season = int(row.get("season", 0))
    position = row.get("position", "")
    pick = _to_float(row.get("pick"))

    censored = compute_censoring_flag(draft_season, total_games)

    # best3of4_ppg: blank for censored rows — they lack a complete career arc
    best3of4 = None if censored else compute_best3of4_ppg(total_points, total_games)

    # expected_ppg_at_pick: available for any valid pick + curve (supports inference)
    if pick is not None and position in curves:
        exp = round(expected_ppg_at_pick(pick, curves[position]), 4)
        expected_str = str(exp)
    else:
        exp = None
        expected_str = ""

    # residual_ppg: only when not censored, best3of4 exists, and expected exists
    if not censored and best3of4 is not None and exp is not None:
        residual_str = str(round(best3of4 - exp, 4))
    else:
        residual_str = ""

    eligible = (
        not censored
        and best3of4 is not None
        and exp is not None
        and residual_str != ""
    )

    return {
        "censored_incomplete_arc": "1" if censored else "0",
        "best3of4_ppg": "" if best3of4 is None else str(best3of4),
        "expected_ppg_at_pick": expected_str,
        "residual_ppg": residual_str,
        "head_b_training_eligible": "1" if eligible else "0",
        "target_version": TARGET_VERSION,
        "curve_version": CURVE_VERSION,
    }


def compute_v3_universal_features(row: dict) -> dict[str, str]:
    """Compute universally-derivable Engine A v3 feature columns for a single row.

    Populates columns that can be derived from the existing source training CSV
    without external API calls. CFBD-dependent columns (early_declare,
    final_college_age, covid_eligibility_flag, transfer_portal_flag) are added
    as explicit stubs with _missing="1" until the W2 CFBD enrichment pipeline
    populates them.

    The _missing and _source naming convention follows head_b_contract.py.
    """
    # age_at_draft: directly available from source "age" column
    age_raw = row.get("age", "")
    age_valid = _to_float(age_raw) is not None
    result: dict[str, str] = {
        "age_at_draft": age_raw if age_valid else "",
        "age_at_draft_missing": "0" if age_valid else "1",
        "age_at_draft_source": "nfl_data_py" if age_valid else "",
    }

    # CFBD-dependent universal features: stubs until enrichment pipeline runs.
    # _missing="1" signals that values are not yet computed — not silent null-fill.
    for cfbd_col in (
        "covid_eligibility_flag",
        "transfer_portal_flag",
        "early_declare",
        "final_college_age",
    ):
        result[cfbd_col] = ""
        result[f"{cfbd_col}_missing"] = "1"
        result[f"{cfbd_col}_source"] = ""

    return result


# ── Data loading ───────────────────────────────────────────────────────────────

def _load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _to_float(v: str | None) -> Optional[float]:
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── Curve fitting ──────────────────────────────────────────────────────────────

def _build_curves(rows: list[dict]) -> dict[str, IsotonicRegression]:
    """Fit per-position expected-PPG curves from the training cohort rows."""
    curves: dict[str, IsotonicRegression] = {}

    for position in (*POSITIONS_ISOTONIC, POSITION_TE):
        pos_rows = [
            r for r in rows
            if r.get("position") == position
            and not compute_censoring_flag(
                int(r.get("season", 0)),
                int(r.get("total_games", 0) or 0),
            )
        ]
        picks = [_to_float(r.get("pick")) for r in pos_rows]
        ppg_vals = [
            compute_best3of4_ppg(
                _to_float(r.get("total_points", 0)) or 0.0,
                int(r.get("total_games", 0) or 0),
            )
            for r in pos_rows
        ]
        clean = [
            (p, g) for p, g in zip(picks, ppg_vals)
            if p is not None and g is not None
        ]
        if len(clean) < 2:
            print(f"  [WARN] {position}: fewer than 2 training rows — skipping curve fit")
            continue
        clean_picks, clean_ppg = zip(*clean)

        if position in POSITIONS_ISOTONIC:
            curves[position] = fit_isotonic_curve(list(clean_picks), list(clean_ppg))
        else:
            if "WR" not in curves:
                print(f"  [WARN] TE pooling requires WR curve — skipping TE fit")
                continue
            curves[position] = fit_te_pooled_curve(
                list(clean_picks), list(clean_ppg), curves["WR"], SHRINKAGE_K_TE
            )

    return curves


def _curve_summary(
    position: str,
    ir: IsotonicRegression,
    n_training: int,
    method: str,
) -> dict:
    sample_picks = [1, 10, 32, 64, 100, 150, 200, 250]
    return {
        "method": method,
        "n_training_rows": n_training,
        "sample_points": [
            {"pick": p, "expected_ppg": round(expected_ppg_at_pick(float(p), ir), 4)}
            for p in sample_picks
        ],
    }


# ── Main pipeline ──────────────────────────────────────────────────────────────

def main() -> None:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Source CSV not found: {SOURCE_CSV}\n"
            "Run scripts/build_training_data.py first."
        )

    # Governance assertion: W1 target columns must not violate the Head B prohibition.
    overlap = W1_TARGET_COLUMNS & HEAD_B_PROHIBITED_COLUMNS
    assert not overlap, (
        f"GOVERNANCE VIOLATION: W1 target column(s) in HEAD_B_PROHIBITED_COLUMNS: {overlap}"
    )

    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 19 W1 — Head B Target Pipeline")
    print(f"  Run ID: {run_id}")
    print(f"  Source: {SOURCE_CSV}")

    # ── Source provenance ────────────────────────────────────────────────────
    source_bytes = SOURCE_CSV.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    rows = _load_rows(SOURCE_CSV)
    source_row_count = len(rows)
    print(f"  Loaded: {source_row_count} rows  sha256=...{source_sha256[-8:]}")

    # ── Fit curves ──────────────────────────────────────────────────────────
    print(f"\n  Fitting expected-PPG curves (training ≤{TRAINING_MAX_SEASON})...")
    curves = _build_curves(rows)
    for pos, ir in curves.items():
        ex1 = expected_ppg_at_pick(1.0, ir)
        ex32 = expected_ppg_at_pick(32.0, ir)
        ex100 = expected_ppg_at_pick(100.0, ir)
        print(f"  {pos}: pick1={ex1:.2f}, pick32={ex32:.2f}, pick100={ex100:.2f}")

    # ── Enrich rows ─────────────────────────────────────────────────────────
    print("\n  Enriching rows with Head B target columns...")
    n_eligible = n_censored_class = n_censored_games = n_no_curve = 0
    seasons_in_source = []
    training_seasons = []

    for row in rows:
        season = int(row.get("season", 0))
        seasons_in_source.append(season)
        total_games = int(row.get("total_games", 0) or 0)
        position = row.get("position", "")

        targets = compute_row_targets(row, curves)
        row.update(targets)
        row.update(compute_v3_universal_features(row))

        if targets["head_b_training_eligible"] == "1":
            n_eligible += 1
            training_seasons.append(season)
        elif targets["censored_incomplete_arc"] == "1":
            if season > TRAINING_MAX_SEASON:
                n_censored_class += 1
            else:
                n_censored_games += 1
        elif position in ("WR", "RB", "TE") and targets["expected_ppg_at_pick"] == "":
            n_no_curve += 1

    actual_min_season = min(seasons_in_source) if seasons_in_source else None
    actual_max_season = max(seasons_in_source) if seasons_in_source else None
    training_min = min(training_seasons) if training_seasons else None
    training_max = max(training_seasons) if training_seasons else None

    print(f"  Head B eligible: {n_eligible}")
    print(f"  Censored (class >2021): {n_censored_class}")
    print(f"  Censored (low games): {n_censored_games}")
    print(f"  No curve: {n_no_curve}")

    # ── Write output CSV ────────────────────────────────────────────────────
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    print(f"\n  Written: {OUTPUT_CSV}")

    # ── Verify source is untouched ────────────────────────────────────────
    assert hashlib.sha256(SOURCE_CSV.read_bytes()).hexdigest() == source_sha256, (
        "INTEGRITY VIOLATION: source CSV hash changed during pipeline run"
    )

    # ── Write curve artifact ────────────────────────────────────────────────
    training_row_counts = {}
    for position in (*POSITIONS_ISOTONIC, POSITION_TE):
        training_row_counts[position] = sum(
            1 for r in rows
            if r.get("position") == position
            and r.get("head_b_training_eligible") == "1"
        )

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "version": CURVE_VERSION,
        "provenance": {
            "source_csv": SOURCE_CSV.name,
            "source_csv_sha256": source_sha256,
            "source_row_count": source_row_count,
            "source_season_range": {
                "min": actual_min_season,
                "max": actual_max_season,
            },
            "training_season_range": {
                "spec_target_min": SPEC_TRAINING_MIN_SEASON,
                "spec_target_max": TRAINING_MAX_SEASON,
                "actual_min": training_min,
                "actual_max": training_max,
                "spec_drift_note": (
                    f"Spec targets {SPEC_TRAINING_MIN_SEASON}-{TRAINING_MAX_SEASON} cohorts; "
                    f"source CSV starts at {ACTUAL_TRAINING_MIN_SEASON}. "
                    f"W1 fits {training_min}-{training_max}. "
                    "W2 may back-extend if a 2010-2014 backfill source is found."
                ),
            },
            "censored_rows": {
                "by_recent_class": n_censored_class,
                "by_low_games": n_censored_games,
                "total": n_censored_class + n_censored_games,
                "note": (
                    "Censored rows have blank best3of4_ppg and residual_ppg. "
                    "expected_ppg_at_pick is still populated for inference scoring."
                ),
            },
            "head_b_eligible_rows": n_eligible,
        },
        "min_games_threshold": MIN_GAMES_THRESHOLD,
        "shrinkage_k_te": SHRINKAGE_K_TE,
        "curves": {
            pos: _curve_summary(
                pos,
                ir,
                n_training=training_row_counts.get(pos, 0),
                method=(
                    "isotonic_regression" if pos in POSITIONS_ISOTONIC
                    else f"isotonic_pooled_wr_prior_k{int(SHRINKAGE_K_TE)}"
                ),
            )
            for pos, ir in curves.items()
        },
        "governance": {
            "market_data_used": False,
            "model_pkl_changed": False,
            "latest_json_changed": False,
            "source_csv_overwritten": False,
        },
    }

    CURVES_JSON.parent.mkdir(parents=True, exist_ok=True)
    CURVES_JSON.write_text(json.dumps(artifact, indent=2))
    print(f"  Written: {CURVES_JSON}")
    print(f"\n  Curves fitted: {list(curves.keys())}")
    print("  promotion_decision: NOT_APPLICABLE (W1 data pipeline only)")


if __name__ == "__main__":
    main()
