"""Phase 19 Head A v3 TE Ridge Promotion Script.

Trains the final TE Head A v3 Ridge model on the full LOOCV-eligible population
from prospects_with_outcomes_v3.csv and serializes the trained pipeline to the
Head A v3 model directory.

Winning configuration from W3 bakeoff (artifact 826e5156):
  alpha      = 50.0  (unanimous best_alpha across all 4 walk-forward folds)
  candidate  = Ridge (not GBT — Ridge was the sole passing candidate)
  features   = nfl_pick, nfl_round, final_college_age,
               te_ryptpa_final, te_yards_per_reception_career
  target     = best3of4_ppg
  gate       = 2/3 (RMSE +7.0%, NDCG ✓; Spearman ✗ at fold level)

Storage layout (mirrors engine_b/ pattern):
  app/data/models/head_a/runs/{ts}/te_v3.pkl
  app/data/models/head_a/runs/{ts}/te_v3_metadata.json
  app/data/models/head_a/v3_manifest.json

NOTE: Does NOT update app/data/models/latest.json (Engine A v2 scorer path).
The v2 scorer uses pick/round/age only and cannot accept these 5 features.
W5 (Service Layer) will wire the Head A v3 scorer via v3_manifest.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
HEAD_A_DIR = ROOT / "app/data/models/head_a"

# Winning configuration from W3 bakeoff artifact 826e5156
WINNING_ALPHA = 50.0
TE_FEATURES = [
    "nfl_pick",
    "nfl_round",
    "final_college_age",
    "te_ryptpa_final",
    "te_yards_per_reception_career",
]
TARGET_COL = "best3of4_ppg"
POSITION = "TE"


def _to_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _load_eligible_te_rows(csv_path: Path) -> list[dict]:
    """Load non-censored TE rows with all required features populated."""
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    eligible = []
    for row in rows:
        if row.get("position", "").upper() != POSITION:
            continue
        if row.get("censored_incomplete_arc", "0") == "1":
            continue
        # All features and target must be non-null
        values = {col: _to_float(row.get(col)) for col in TE_FEATURES + [TARGET_COL]}
        if any(v is None for v in values.values()):
            continue
        eligible.append(row)
    return eligible


def _build_Xy(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    X = np.array([
        [float(r[col]) for col in TE_FEATURES]
        for r in rows
    ], dtype=float)
    y = np.array([float(r[TARGET_COL]) for r in rows], dtype=float)
    return X, y


def promote(run_ts: str | None = None) -> Path:
    """Train and serialize the TE Head A v3 Ridge model.

    Returns the path to the created te_v3.pkl artifact.
    """
    if not V3_CSV.exists():
        raise FileNotFoundError(f"v3 CSV not found: {V3_CSV}")

    rows = _load_eligible_te_rows(V3_CSV)
    if len(rows) < 5:
        raise ValueError(
            f"Only {len(rows)} eligible TE rows — cannot train a meaningful model"
        )

    X, y = _build_Xy(rows)
    n_train = len(rows)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=WINNING_ALPHA)),
    ])
    pipeline.fit(X, y)

    # ── Serialize ──────────────────────────────────────────────────────────────
    if run_ts is None:
        run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    run_dir = HEAD_A_DIR / "runs" / run_ts
    run_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = run_dir / "te_v3.pkl"
    with pkl_path.open("wb") as f:
        pickle.dump(pipeline, f)

    # ── Metadata ───────────────────────────────────────────────────────────────
    csv_sha256 = hashlib.sha256(V3_CSV.read_bytes()).hexdigest()[:16]

    scaler: StandardScaler = pipeline.named_steps["scaler"]
    ridge: Ridge = pipeline.named_steps["ridge"]

    oof_rmse = 2.7051   # from bakeoff artifact 826e5156
    baseline_rmse = 2.9094
    rmse_improvement_pct = round((baseline_rmse - oof_rmse) / baseline_rmse * 100, 2)

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)

    metadata = {
        "phase": "Phase 19 W3",
        "bakeoff_artifact": "head_a_bakeoff_20260524T134221Z_826e5156.json",
        "promotion_decision": "TE:ridge PASSES 2/3 gates (RMSE +7.0%, NDCG ✓; Spearman ✗)",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_ts": run_ts,
        "model_family": "head_a_v3_ridge",
        "position": POSITION,
        "alpha": WINNING_ALPHA,
        "features": TE_FEATURES,
        "target": TARGET_COL,
        "n_train_rows": n_train,
        "data_path": _rel(V3_CSV),
        "data_sha256_prefix": csv_sha256,
        "artifact_path": _rel(pkl_path),
        "oof_metrics": {
            "rmse": oof_rmse,
            "rmse_improvement_pct": rmse_improvement_pct,
            "mean_fold_spearman": 0.5934,
            "mean_fold_ndcg_at_10": 0.9662,
            "gates_passed": "2/3 (RMSE, NDCG)",
        },
        "scaler_means": scaler.mean_.tolist(),
        "scaler_scales": scaler.scale_.tolist(),
        "coefficients": dict(zip(TE_FEATURES, ridge.coef_.tolist())),
        "intercept": float(ridge.intercept_),
        "engine_a_v2_scorer_compat": False,
        "w5_integration_note": (
            "Does not update latest.json. "
            "W5 will wire Head A v3 scorer via app/data/models/head_a/v3_manifest.json."
        ),
    }

    meta_path = run_dir / "te_v3_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # ── Manifest ───────────────────────────────────────────────────────────────
    manifest_path = HEAD_A_DIR / "v3_manifest.json"
    existing: dict = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except Exception:
            existing = {}
    existing[POSITION] = _rel(pkl_path)
    manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print(f"\nHead A v3 TE Ridge promotion complete.")
    print(f"  pkl:      {pkl_path}")
    print(f"  metadata: {meta_path}")
    print(f"  manifest: {manifest_path}")
    print(f"  n_train:  {n_train} rows")
    print(f"  alpha:    {WINNING_ALPHA}")
    return pkl_path


if __name__ == "__main__":
    promote()
