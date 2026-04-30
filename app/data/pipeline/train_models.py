import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parents[3]
CSV_PATH = BASE_DIR / "app" / "data" / "training" / "prospects_with_outcomes.csv"
MODELS_DIR = BASE_DIR / "app" / "data" / "models"

POSITIONS = ["WR", "RB", "TE", "QB"]
FEATURES = ["pick", "round", "age"]
TARGET = "y24_ppg"


def train_position(pos: str, df: pd.DataFrame) -> dict:
    pos_df = df[df["position"] == pos].dropna(subset=FEATURES + [TARGET]).copy()

    X = pos_df[FEATURES].values
    y = pos_df[TARGET].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = Ridge(alpha=10)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n--- {pos} ---")
    print(f"  Train rows: {len(X_train)}  |  Test rows: {len(X_test)}")
    print(f"  RMSE: {rmse:.3f}  |  R²: {r2:.3f}")
    print("  Coefficients:")
    for name, coef in zip(FEATURES, model.coef_):
        print(f"    {name:<8} {coef:+.4f}")
    print(f"  Intercept: {model.intercept_:+.4f}")

    model_path = MODELS_DIR / f"{pos}_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"  Saved → {model_path}")

    return {
        "position":   pos,
        "train_rows": len(X_train),
        "test_rows":  len(X_test),
        "rmse":       round(rmse, 3),
        "r2":         round(r2, 3),
    }


def run() -> None:
    df = pd.read_csv(CSV_PATH)
    df = df[df["is_training"] == 1]
    print(f"Loaded {len(df)} training rows from {CSV_PATH.name}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for pos in POSITIONS:
        results.append(train_position(pos, df))

    print("\n=== Summary ===")
    print(f"{'Position':<10} {'Train':>8} {'Test':>6} {'RMSE':>8} {'R²':>8}")
    print("-" * 44)
    for r in results:
        print(f"{r['position']:<10} {r['train_rows']:>8} {r['test_rows']:>6} {r['rmse']:>8.3f} {r['r2']:>8.3f}")


if __name__ == "__main__":
    run()
