import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parents[3]
CSV_PATH = BASE_DIR / "app" / "data" / "training" / "prospects_with_outcomes.csv"
MODELS_DIR = BASE_DIR / "app" / "data" / "models"
RUNS_DIR = MODELS_DIR / "runs"
LATEST_POINTER = MODELS_DIR / "latest.json"

POSITIONS = ["WR", "RB", "TE", "QB"]
FEATURES = ["pick", "round", "age"]
TARGET = "y24_ppg"
MODEL_FAMILY = "rookie_forecast_ridge"
POSITION_CEILINGS = {
    "WR": 0.50,
    "RB": 0.50,
    "TE": 0.30,
    "QB": 0.20,
}
POSITION_ALWAYS_CAVEATS = {
    "QB": ["qb_rookie_signal_inherently_low_ceiling"],
    "TE": ["te_population_per_class_small"],
    "RB": ["rb_career_arc_capped_by_aging_cliff"],
}
LOW_SAMPLE_CAVEAT = "low_sample_holdout"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _mature_seasons(df: pd.DataFrame) -> set[int]:
    """A draft season is mature when at least one player has observed Y4 output."""
    y4_signal = (df["y4_games"].fillna(0) > 0) | (df["y4_points"].fillna(0) > 0)
    return set(df.loc[y4_signal, "season"].astype(int).unique())


def build_temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    mature_seasons = sorted(_mature_seasons(df))
    if not mature_seasons:
        raise ValueError("No mature draft seasons found. Cannot build temporal holdout.")

    mature_df = df[df["season"].isin(mature_seasons)].copy()
    mature_df["season"] = mature_df["season"].astype(int)

    strategy = "is_training_temporal_holdout"
    if "is_training" in mature_df.columns:
        train_df = mature_df[mature_df["is_training"] == 1].copy()
        holdout_df = mature_df[mature_df["is_training"] == 0].copy()
    else:
        train_df = pd.DataFrame()
        holdout_df = pd.DataFrame()

    # Current generated data may mark all mature rows as training. In that case,
    # use the latest mature draft class as a true forward-looking holdout.
    if train_df.empty or holdout_df.empty:
        holdout_season = max(mature_seasons)
        train_df = mature_df[mature_df["season"] < holdout_season].copy()
        holdout_df = mature_df[mature_df["season"] == holdout_season].copy()
        strategy = "latest_mature_season_temporal_holdout"

    if train_df.empty or holdout_df.empty:
        raise ValueError("Temporal split produced empty train or holdout data.")

    split_info = {
        "strategy": strategy,
        "training_seasons": sorted(train_df["season"].astype(int).unique().tolist()),
        "holdout_seasons": sorted(holdout_df["season"].astype(int).unique().tolist()),
        "excluded_unmatured_seasons": sorted(
            set(df["season"].astype(int).unique()) - set(mature_seasons)
        ),
    }
    return train_df, holdout_df, split_info


def _fit_model(df: pd.DataFrame) -> Ridge:
    X = df[FEATURES].values
    y = df[TARGET].values

    model = Ridge(alpha=10)
    model.fit(X, y)
    return model


def _rankdata(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average").to_numpy()


def _safe_spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return 0.0
    true_ranks = _rankdata(y_true)
    pred_ranks = _rankdata(y_pred)
    corr = np.corrcoef(true_ranks, pred_ranks)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(corr)


def _top_k_hit_rate(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    if len(y_true) == 0:
        return 0.0
    k = max(1, min(k, len(y_true)))
    pred_top_idx = set(np.argsort(y_pred)[-k:])
    actual_top_idx = set(np.argsort(y_true)[-k:])
    return float(len(pred_top_idx.intersection(actual_top_idx)) / k)


def _bottom_quartile_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    q = max(1, len(y_true) // 4)
    pred_bottom_idx = set(np.argsort(y_pred)[:q])
    actual_bottom_idx = set(np.argsort(y_true)[:q])
    return float(len(pred_bottom_idx.intersection(actual_bottom_idx)) / q)


def _model_grade(
    *,
    position: str,
    r2: float,
    spearman: float,
    top_12_hit_rate: float,
    holdout_rows: int,
) -> str:
    ceiling = POSITION_CEILINGS[position]
    if (
        r2 >= (ceiling * 0.7)
        and spearman >= 0.60
        and top_12_hit_rate >= 0.50
        and holdout_rows >= 80
    ):
        return "A"
    if r2 >= (ceiling * 0.5) and spearman >= 0.45 and holdout_rows >= 30:
        return "B"
    if r2 < 0 or spearman < 0:
        return "D"
    if r2 >= 0 and spearman >= 0:
        return "C"
    return "unvalidated"


def _position_caveats(position: str, holdout_rows: int) -> list[str]:
    caveats = list(POSITION_ALWAYS_CAVEATS.get(position, []))
    if holdout_rows < 30:
        caveats.append(LOW_SAMPLE_CAVEAT)
    return caveats


def train_position(
    pos: str,
    train_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    run_dir: Path,
    run_metadata: dict,
) -> dict:
    pos_train = train_df[train_df["position"] == pos].dropna(subset=FEATURES + [TARGET]).copy()
    pos_holdout = holdout_df[holdout_df["position"] == pos].dropna(subset=FEATURES + [TARGET]).copy()

    if pos_train.empty or pos_holdout.empty:
        raise ValueError(f"{pos} split has no training or holdout rows.")

    model = _fit_model(pos_train)

    X_holdout = pos_holdout[FEATURES].values
    y_holdout = pos_holdout[TARGET].values
    y_pred = model.predict(X_holdout)
    rmse = np.sqrt(mean_squared_error(y_holdout, y_pred))
    r2 = r2_score(y_holdout, y_pred)
    spearman = _safe_spearman(y_holdout, y_pred)
    top_12_hit_rate = _top_k_hit_rate(y_holdout, y_pred, k=12)
    bust_avoidance_rate = _bottom_quartile_rate(y_holdout, y_pred)
    holdout_rows = len(pos_holdout)
    position_ceiling = POSITION_CEILINGS[pos]
    model_grade = _model_grade(
        position=pos,
        r2=float(r2),
        spearman=float(spearman),
        top_12_hit_rate=float(top_12_hit_rate),
        holdout_rows=holdout_rows,
    )
    caveats = _position_caveats(pos, holdout_rows)

    metrics = {
        "rmse": round(float(rmse), 3),
        "r2": round(float(r2), 3),
        "spearman_rank_correlation": round(float(spearman), 3),
        "top_12_hit_rate": round(float(top_12_hit_rate), 3),
        "bust_avoidance_rate": round(float(bust_avoidance_rate), 3),
    }

    print(f"\n--- {pos} ---")
    print(f"  Train rows: {len(pos_train)}  |  Holdout rows: {len(pos_holdout)}")
    print(f"  Holdout RMSE: {rmse:.3f}  |  Holdout R²: {r2:.3f}")
    print(f"  Spearman: {spearman:.3f}  |  Top-12 hit rate: {top_12_hit_rate:.3f}")
    print(f"  Bust avoidance rate: {bust_avoidance_rate:.3f}  |  Grade: {model_grade}")
    print("  Coefficients:")
    for name, coef in zip(FEATURES, model.coef_):
        print(f"    {name:<8} {coef:+.4f}")
    print(f"  Intercept: {model.intercept_:+.4f}")

    model_path = run_dir / f"{pos}_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"  Saved -> {model_path}")

    position_metadata = {
        **run_metadata,
        "position": pos,
        "artifact_path": str(model_path.relative_to(BASE_DIR)),
        "train_rows": len(pos_train),
        "holdout_rows": holdout_rows,
        "metrics": metrics,
        "coefficients": {
            name: round(float(coef), 6) for name, coef in zip(FEATURES, model.coef_)
        },
        "feature_means": {
            name: round(float(pos_train[name].mean()), 6) for name in FEATURES
        },
        "intercept": round(float(model.intercept_), 6),
    }

    metadata_path = run_dir / f"{pos}_metadata.json"
    metadata_path.write_text(json.dumps(position_metadata, indent=2, default=_json_default) + "\n")

    return {
        "train_rows": len(pos_train),
        "holdout_rows": holdout_rows,
        **metrics,
        "position_ceiling": position_ceiling,
        "coverage_80": None,
        "model_grade": model_grade,
        "caveats": caveats,
    }


def run() -> None:
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows from {CSV_PATH.name}")

    train_df, holdout_df, split_info = build_temporal_split(df)
    print(f"Split strategy: {split_info['strategy']}")
    print(f"Training seasons: {split_info['training_seasons']}")
    print(f"Holdout seasons: {split_info['holdout_seasons']}")
    print(f"Excluded unmatured seasons: {split_info['excluded_unmatured_seasons']}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    run_metadata = {
        "model_version": run_id,
        "model_family": MODEL_FAMILY,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "target": TARGET,
        "data_path": str(CSV_PATH.relative_to(BASE_DIR)),
        "data_sha256": _file_sha256(CSV_PATH),
        "split": split_info,
    }

    results = {}
    for pos in POSITIONS:
        results[pos] = train_position(pos, train_df, holdout_df, run_dir, run_metadata)

    all_positions_validated = all(
        results.get(pos, {}).get("model_grade") != "unvalidated"
        for pos in POSITIONS
    )
    te_non_negative_r2 = results.get("TE", {}).get("r2", -1.0) >= 0.0

    validation_report = {
        **run_metadata,
        "per_position": results,
        "gates": {
            "te_non_negative_r2": te_non_negative_r2,
            "all_positions_validated": all_positions_validated,
        },
    }
    (run_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2, default=_json_default) + "\n"
    )
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_POINTER.write_text(
        json.dumps(
            {
                "model_version": run_id,
                "run_dir": str(run_dir.relative_to(BASE_DIR)),
                "validation_report": str((run_dir / "validation_report.json").relative_to(BASE_DIR)),
            },
            indent=2,
        )
        + "\n"
    )

    print("\n=== Summary ===")
    print(
        f"{'Position':<10} {'Train':>8} {'Holdout':>8} {'RMSE':>8} "
        f"{'R²':>8} {'ρ':>8} {'Top12':>8} {'Grade':>8}"
    )
    print("-" * 76)
    for pos in POSITIONS:
        r = results[pos]
        print(
            f"{pos:<10} {r['train_rows']:>8} {r['holdout_rows']:>8} {r['rmse']:>8.3f} "
            f"{r['r2']:>8.3f} {r['spearman_rank_correlation']:>8.3f} "
            f"{r['top_12_hit_rate']:>8.3f} {r['model_grade']:>8}"
        )
    print(f"\nLatest pointer -> {LATEST_POINTER}")


if __name__ == "__main__":
    run()
