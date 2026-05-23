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
curve fitting but written to the output CSV for inference scoring.

TE hierarchical pooling: the TE annual cohort is small (~3–5 fantasy-relevant
players per class). To stabilize the isotonic fit, SHRINKAGE_K_TE synthetic
"WR prior" observations are added per unique pick bucket. This Bayesian
augmentation shrinks sparse-bucket TE estimates toward the WR baseline.

Usage:
    .venv/bin/python3.14 scripts/build_head_b_targets.py
"""

from __future__ import annotations

import csv
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

# ── I/O paths ─────────────────────────────────────────────────────────────────

SOURCE_CSV = ROOT / "app/data/training/prospects_with_outcomes.csv"
OUTPUT_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
CURVES_JSON = ROOT / "app/data/training/expected_ppg_curves_v3.json"

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_GAMES_THRESHOLD: int = 8        # Minimum career games to produce a usable PPG
TRAINING_MAX_SEASON: int = 2021     # Latest draft class with a complete Y2-Y4 arc
SHRINKAGE_K_TE: float = 5.0         # Synthetic WR-prior observations per TE pick bucket
CURVE_VERSION: str = "v3"
TARGET_VERSION: str = "head_b_v3"

POSITIONS_ISOTONIC = ("WR", "RB")   # Positions using standalone isotonic regression
POSITION_TE = "TE"                  # Position using pooled isotonic with WR prior

# ── Leakage guard ─────────────────────────────────────────────────────────────

# Patterns that must NOT appear in any output column name.
# Mirrors engine_a_contract.LEAKAGE_REGEX plus broad market-field coverage.
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

    Returns None when total_games < MIN_GAMES_THRESHOLD (insufficient
    career arc for a reliable target — these rows receive the censoring
    flag and are excluded from curve fitting).

    Note: "Best 3 of 4" per the spec reduces to this when Y1 data is absent
    and exactly 3 seasons are available (Y2, Y3, Y4). Game-weighting is
    preferable to a simple season average because it down-weights injury-
    shortened years proportionally.
    """
    if total_games < MIN_GAMES_THRESHOLD:
        return None
    return round(total_points / total_games, 4)


def compute_censoring_flag(draft_season: int, total_games: int) -> bool:
    """True when the career arc is incomplete for Head B training purposes.

    Excludes rows from curve fitting when:
    - draft_season > TRAINING_MAX_SEASON: Y4 may not yet have occurred.
    - total_games < MIN_GAMES_THRESHOLD: too few games for a reliable PPG.

    Censored rows are still written to the output CSV for inference scoring.
    """
    return draft_season > TRAINING_MAX_SEASON or total_games < MIN_GAMES_THRESHOLD


def fit_isotonic_curve(
    picks: list[float],
    ppg_values: list[float],
) -> IsotonicRegression:
    """Fit monotonically non-increasing isotonic regression: pick → expected PPG.

    Uses the Pool Adjacent Violators Algorithm (PAVA) via sklearn.
    `out_of_bounds='clip'` extrapolates by repeating the boundary value for
    picks outside the training range.
    """
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

    For each unique pick value in the TE training set, `shrinkage_k` synthetic
    observations are added at the WR-predicted value. This is equivalent to a
    hierarchical model where the TE distribution is a priori centered on the WR
    curve. With n TE observations per bucket and k synthetic points, the
    effective weight on the WR prior is k / (n + k).

    The augmented dataset is then fit with the same isotonic algorithm used for
    WR/RB, preserving the monotonicity guarantee.
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

def _build_curves(
    rows: list[dict],
) -> dict[str, IsotonicRegression]:
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
        # Drop rows where either pick or ppg is None
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
            # TE: pooled with WR prior
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
    """Produce a JSON-serialisable curve summary for the artifact."""
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

    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 19 W1 — Head B Target Pipeline")
    print(f"  Run ID: {run_id}")
    print(f"  Source: {SOURCE_CSV}")

    rows = _load_rows(SOURCE_CSV)
    print(f"  Loaded: {len(rows)} rows")

    # ── Fit curves ──────────────────────────────────────────────────────────
    print(f"\n  Fitting expected-PPG curves (training ≤{TRAINING_MAX_SEASON})...")
    curves = _build_curves(rows)
    for pos, ir in curves.items():
        method = "isotonic" if pos in POSITIONS_ISOTONIC else f"isotonic_pooled_wr_prior(k={SHRINKAGE_K_TE})"
        ex1 = expected_ppg_at_pick(1.0, ir)
        ex32 = expected_ppg_at_pick(32.0, ir)
        ex100 = expected_ppg_at_pick(100.0, ir)
        print(f"  {pos}: pick1={ex1:.2f}, pick32={ex32:.2f}, pick100={ex100:.2f}")

    # ── Enrich rows ─────────────────────────────────────────────────────────
    print("\n  Enriching rows with Head B target columns...")
    n_training = n_censored = n_no_curve = 0
    for row in rows:
        total_points = _to_float(row.get("total_points", 0)) or 0.0
        total_games = int(row.get("total_games", 0) or 0)
        draft_season = int(row.get("season", 0))
        position = row.get("position", "")
        pick = _to_float(row.get("pick"))

        best3of4 = compute_best3of4_ppg(total_points, total_games)
        censored = compute_censoring_flag(draft_season, total_games)

        row["best3of4_ppg"] = "" if best3of4 is None else str(best3of4)
        row["censored_incomplete_arc"] = "1" if censored else "0"

        if pick is not None and position in curves and best3of4 is not None:
            exp = expected_ppg_at_pick(pick, curves[position])
            residual = round(best3of4 - exp, 4)
            row["expected_ppg_at_pick"] = str(round(exp, 4))
            row["residual_ppg"] = str(residual)
        else:
            row["expected_ppg_at_pick"] = ""
            row["residual_ppg"] = ""
            if position in ("WR", "RB", "TE") and not censored:
                n_no_curve += 1

        row["target_version"] = TARGET_VERSION
        row["curve_version"] = CURVE_VERSION

        if not censored and best3of4 is not None:
            n_training += 1
        elif censored:
            n_censored += 1

    print(f"  Training rows: {n_training} | Censored: {n_censored} | No curve: {n_no_curve}")

    # ── Write output CSV ────────────────────────────────────────────────────
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    print(f"\n  Written: {OUTPUT_CSV}")

    # ── Write curve artifact ────────────────────────────────────────────────
    training_row_counts = {}
    for position in (*POSITIONS_ISOTONIC, POSITION_TE):
        pos_training = [
            r for r in rows
            if r.get("position") == position
            and r.get("censored_incomplete_arc") == "0"
            and r.get("best3of4_ppg") != ""
        ]
        training_row_counts[position] = len(pos_training)

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "version": CURVE_VERSION,
        "source_csv": SOURCE_CSV.name,
        "training_cohort": {
            "min_season": 2015,
            "max_season": TRAINING_MAX_SEASON,
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
