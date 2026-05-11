"""Engine A v2 CFBD-only backtest.

Compares Model A (draft capital + age baseline) against Model B
(+ CFBD dominator_rating + receiving_yards_share) on the held-out
validation set. Reports RMSE, R², and Spearman rank correlation
overall and by position.

No PP fields are used. This backtest is deliberately CFBD-only
because the PlayerProfiler decision gate (Task 3) has not resolved.

Usage:
    .venv/bin/python scripts/backtest_engine_a_cfbd_only.py

Output:
    docs/validation/engine_a_v2_cfbd_backtest_report.md
    stdout summary (10 lines)

Promotion criterion (both conditions required):
    Improvement on >=2 of: RMSE reduction >=5%, R² gain >=0.02, Spearman gain >=0.03
    ...on the held-out set for >=2 positions.

If promotion is not warranted, the report documents why.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASELINE_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
PARTIAL_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_cfbd_partial.csv"
REPORT_PATH = ROOT / "docs" / "validation" / "engine_a_v2_cfbd_backtest_report.md"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

MODEL_A_FEATURES = ["pick", "round", "age"]
CFBD_FEATURES = ["dominator_rating", "receiving_yards_share"]
MODEL_B_FEATURES = MODEL_A_FEATURES + CFBD_FEATURES
OUTCOME = "y24_ppg"
POSITIONS = ["WR", "RB", "TE"]

RMSE_THRESHOLD = 0.05    # 5% reduction
R2_THRESHOLD = 0.02
SPEARMAN_THRESHOLD = 0.03
MIN_POSITIONS_FOR_PROMOTION = 2
MIN_HELD_OUT_N = 50


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 4:
        return float("nan")
    return float(stats.spearmanr(y_true, y_pred).statistic)


def fit_predict(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
) -> np.ndarray:
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    return model.predict(X_test)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "rmse": rmse(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else float("nan"),
        "spearman": spearman(y_true, y_pred),
        "n": len(y_true),
    }


def run_model_pair(df_train: pd.DataFrame, df_test: pd.DataFrame, features: list[str]) -> dict:
    """Fit on train, evaluate on test. Imputes nulls with training-set position-group medians."""
    # Impute using training set statistics only
    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(df_train[features])
    X_test = imputer.transform(df_test[features])
    y_train = df_train[OUTCOME].values
    y_test = df_test[OUTCOME].values

    y_pred = fit_predict(X_train, y_train, X_test)
    return evaluate(y_test, y_pred)


def compute_coverage(df: pd.DataFrame, col: str, positions: list[str]) -> dict[str, float]:
    result = {}
    for pos in positions:
        sub = df[df["position"] == pos]
        if len(sub) == 0:
            result[pos.lower()] = 0.0
            continue
        present = sub[col].notna().sum()
        result[pos.lower()] = float(present / len(sub))
    return result


def check_promotion(position_improvements: list[dict]) -> tuple[bool, str]:
    """Return (promoted, reason) based on per-position metric deltas."""
    promoted_positions = []
    for p in position_improvements:
        wins = 0
        if p["delta_rmse_pct"] >= RMSE_THRESHOLD:
            wins += 1
        if p["delta_r2"] >= R2_THRESHOLD:
            wins += 1
        if p["delta_spearman"] >= SPEARMAN_THRESHOLD:
            wins += 1
        if wins >= 2:
            promoted_positions.append(p["position"])

    if len(promoted_positions) >= MIN_POSITIONS_FOR_PROMOTION:
        return True, (
            f"CFBD features improve >=2 of 3 metrics for positions: {promoted_positions}. "
            "Promotion warranted — proceed to add dominator_rating and receiving_yards_share "
            "to the Engine A model feature set."
        )
    else:
        return False, (
            f"CFBD features meet promotion criterion for only {len(promoted_positions)} position(s) "
            f"({promoted_positions}); need >={MIN_POSITIONS_FOR_PROMOTION}. "
            "Features remain in the pipeline but grade promotion is not warranted yet. "
            "Consider: collecting more CFBD coverage (currently 85.6%), adding RAS risk flags "
            "(Task 5), or re-evaluating after a full season of new data."
        )


def write_report(
    combined_a: dict,
    combined_b: dict,
    by_position: list[dict],
    cfbd_coverage: dict[str, float],
    promotion: bool,
    promotion_reason: str,
    held_out_n: int,
    imputed_n: int,
) -> None:
    delta_rmse = combined_a["rmse"] - combined_b["rmse"]
    delta_rmse_pct = delta_rmse / combined_a["rmse"] if combined_a["rmse"] > 0 else 0.0
    delta_r2 = combined_b["r2"] - combined_a["r2"]
    delta_spearman = combined_b["spearman"] - combined_a["spearman"]

    # YAML frontmatter (machine-readable for tests)
    fm_lines = [
        "---",
        f"baseline_model: pick + round + age",
        f"enriched_model: pick + round + age + dominator_rating + receiving_yards_share",
        f"held_out_n: {held_out_n}",
        f"imputed_n_cfbd: {imputed_n}",
        f"metric_delta_rmse_combined: {delta_rmse:.4f}",
        f"metric_delta_rmse_pct_combined: {delta_rmse_pct:.4f}",
        f"metric_delta_r2_combined: {delta_r2:.4f}",
        f"metric_delta_spearman_combined: {delta_spearman:.4f}",
        f"cfbd_coverage_pct_wr: {cfbd_coverage.get('wr', 0):.4f}",
        f"cfbd_coverage_pct_rb: {cfbd_coverage.get('rb', 0):.4f}",
        f"cfbd_coverage_pct_te: {cfbd_coverage.get('te', 0):.4f}",
        f"promotion_warranted: {'true' if promotion else 'false'}",
        "---",
    ]

    pos_rows = []
    for p in by_position:
        pos_rows.append(
            f"| {p['position']} | {p['n_test']} | "
            f"{p['rmse_a']:.3f} | {p['rmse_b']:.3f} | "
            f"{p['r2_a']:.3f} | {p['r2_b']:.3f} | "
            f"{p['spearman_a']:.3f} | {p['spearman_b']:.3f} |"
        )

    body = textwrap.dedent(f"""
        # Engine A v2 CFBD-only Backtest Report

        **Branch:** engine-a/v2-enrichment-pipeline
        **Generated by:** scripts/backtest_engine_a_cfbd_only.py

        ## Summary

        | Metric | Baseline (A) | CFBD-enriched (B) | Delta |
        |--------|-------------|-------------------|-------|
        | RMSE (combined) | {combined_a['rmse']:.4f} | {combined_b['rmse']:.4f} | {delta_rmse:+.4f} ({delta_rmse_pct:+.1%}) |
        | R² (combined) | {combined_a['r2']:.4f} | {combined_b['r2']:.4f} | {delta_r2:+.4f} |
        | Spearman ρ (combined) | {combined_a['spearman']:.4f} | {combined_b['spearman']:.4f} | {delta_spearman:+.4f} |

        Held-out rows: {held_out_n} | CFBD-imputed rows (dominator_rating=null): {imputed_n}

        ## By Position

        | Position | N | RMSE A | RMSE B | R² A | R² B | Spearman A | Spearman B |
        |----------|---|--------|--------|------|------|------------|------------|
        {chr(10).join(pos_rows)}

        ## CFBD Coverage on Held-Out Set

        | Position | dominator_rating coverage |
        |----------|--------------------------|
        | WR | {cfbd_coverage.get('wr', 0):.1%} |
        | RB | {cfbd_coverage.get('rb', 0):.1%} |
        | TE | {cfbd_coverage.get('te', 0):.1%} |

        ## Promotion Decision

        **Promotion warranted:** {'YES' if promotion else 'NO'}

        {promotion_reason}

        ## What Was NOT in This Backtest

        PlayerProfiler fields (`target_share`, `breakout_age`, `speed_score`) are NOT
        included in Model B features. The PP decision gate (Task 3) has not resolved.
        Those fields will only enter the model if the probe confirms >=80% real coverage.
        Imputed-median PP fields are never used as model evidence.

        ## Promotion Criterion

        Model B must improve on >=2 of: RMSE reduction >={RMSE_THRESHOLD:.0%},
        R² gain >={R2_THRESHOLD}, Spearman gain >={SPEARMAN_THRESHOLD} —
        on the held-out set for >={MIN_POSITIONS_FOR_PROMOTION} positions.
    """).strip()

    full = "\n".join(fm_lines) + "\n\n" + body + "\n"
    REPORT_PATH.write_text(full)


def main() -> None:
    # Load and validate inputs
    for path, name in [(BASELINE_CSV, "baseline"), (PARTIAL_CSV, "CFBD partial")]:
        if not path.exists():
            print(f"ERROR: {name} CSV not found: {path}", file=sys.stderr)
            sys.exit(1)

    baseline = pd.read_csv(BASELINE_CSV)
    partial = pd.read_csv(PARTIAL_CSV)

    # Left-join partial enrichment onto baseline (partial already has all baseline cols + CFBD cols)
    df = partial.copy()

    # Require outcome and is_training columns
    for col in [OUTCOME, "is_training", "position"]:
        if col not in df.columns:
            print(f"ERROR: Column '{col}' not in training data.", file=sys.stderr)
            sys.exit(1)

    # Drop rows with no outcome (can't evaluate without a label)
    df = df.dropna(subset=[OUTCOME])

    train_df = df[df["is_training"] == True].copy()
    test_df = df[df["is_training"] == False].copy()

    # Abort if held-out set is too small to be meaningful
    if len(test_df) < MIN_HELD_OUT_N:
        print(
            f"ERROR: Held-out set has only {len(test_df)} rows — need >={MIN_HELD_OUT_N}. "
            "Aborting rather than reporting on an insufficient sample.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Count how many CFBD rows needed imputation
    imputed_n = test_df["dominator_rating"].isna().sum()

    # CFBD coverage by position on held-out set (WR/RB/TE skill positions)
    coverage = compute_coverage(test_df, "dominator_rating", POSITIONS)

    # Combined evaluation
    combined_a = run_model_pair(train_df, test_df, MODEL_A_FEATURES)
    combined_b = run_model_pair(train_df, test_df, MODEL_B_FEATURES)

    # Per-position evaluation
    by_position = []
    position_improvements = []
    for pos in POSITIONS:
        pos_train = train_df[train_df["position"] == pos]
        pos_test = test_df[test_df["position"] == pos]
        if len(pos_test) < 10:
            print(f"  Skipping {pos}: only {len(pos_test)} held-out rows.")
            continue

        metrics_a = run_model_pair(pos_train, pos_test, MODEL_A_FEATURES)
        metrics_b = run_model_pair(pos_train, pos_test, MODEL_B_FEATURES)

        delta_rmse = metrics_a["rmse"] - metrics_b["rmse"]
        delta_rmse_pct = delta_rmse / metrics_a["rmse"] if metrics_a["rmse"] > 0 else 0.0
        delta_r2 = metrics_b["r2"] - metrics_a["r2"]
        delta_spearman = metrics_b["spearman"] - metrics_a["spearman"]

        by_position.append({
            "position": pos,
            "n_test": len(pos_test),
            "rmse_a": metrics_a["rmse"],
            "rmse_b": metrics_b["rmse"],
            "r2_a": metrics_a["r2"],
            "r2_b": metrics_b["r2"],
            "spearman_a": metrics_a["spearman"],
            "spearman_b": metrics_b["spearman"],
        })
        position_improvements.append({
            "position": pos,
            "delta_rmse_pct": delta_rmse_pct,
            "delta_r2": delta_r2,
            "delta_spearman": delta_spearman,
        })

    promotion, promotion_reason = check_promotion(position_improvements)

    write_report(
        combined_a=combined_a,
        combined_b=combined_b,
        by_position=by_position,
        cfbd_coverage=coverage,
        promotion=promotion,
        promotion_reason=promotion_reason,
        held_out_n=len(test_df),
        imputed_n=int(imputed_n),
    )

    # 10-line stdout summary
    delta_rmse = combined_a["rmse"] - combined_b["rmse"]
    delta_rmse_pct = delta_rmse / combined_a["rmse"] if combined_a["rmse"] > 0 else 0.0
    print()
    print("=" * 60)
    print("ENGINE A v2 CFBD-ONLY BACKTEST SUMMARY")
    print("=" * 60)
    print(f"  Held-out rows: {len(test_df)}")
    print(f"  RMSE A={combined_a['rmse']:.4f}  B={combined_b['rmse']:.4f}  delta={delta_rmse:+.4f} ({delta_rmse_pct:+.1%})")
    print(f"  R²   A={combined_a['r2']:.4f}  B={combined_b['r2']:.4f}  delta={combined_b['r2']-combined_a['r2']:+.4f}")
    print(f"  Spearman A={combined_a['spearman']:.4f}  B={combined_b['spearman']:.4f}  delta={combined_b['spearman']-combined_a['spearman']:+.4f}")
    for p in by_position:
        print(f"  {p['position']}: RMSE {p['rmse_a']:.3f}→{p['rmse_b']:.3f}  R² {p['r2_a']:.3f}→{p['r2_b']:.3f}  ρ {p['spearman_a']:.3f}→{p['spearman_b']:.3f}")
    print(f"  Promotion: {'YES' if promotion else 'NO'}")
    print(f"  Report: {REPORT_PATH.relative_to(ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
