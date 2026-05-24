"""TDD tests for the Phase 19 Head A v3 TE Ridge promotion script.

RED suite — all tests must fail before scripts/promote_head_a_te_v3.py exists.
"""
from __future__ import annotations

import csv
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_minimal_v3_csv(path: Path, n_te: int = 20, n_wr: int = 5) -> None:
    """Write a synthetic v3 CSV with TE and WR rows."""
    fields = [
        "pfr_player_name", "position", "season", "censored_incomplete_arc",
        "nfl_pick", "nfl_round", "final_college_age",
        "te_ryptpa_final", "te_ryptpa_final_missing",
        "te_yards_per_reception_career", "te_yards_per_reception_career_missing",
        "best3of4_ppg",
    ]
    rng = np.random.default_rng(42)
    rows = []
    for i in range(n_te):
        rows.append({
            "pfr_player_name": f"TE Player {i}",
            "position": "TE",
            "season": str(2015 + (i % 7)),
            "censored_incomplete_arc": "0",
            "nfl_pick": str(20 + i * 5),
            "nfl_round": str(1 + i % 5),
            "final_college_age": str(round(21.0 + rng.uniform(-0.5, 1.5), 1)),
            "te_ryptpa_final": str(round(float(rng.uniform(0.01, 0.08)), 4)),
            "te_ryptpa_final_missing": "0",
            "te_yards_per_reception_career": str(round(float(rng.uniform(9.0, 15.0)), 2)),
            "te_yards_per_reception_career_missing": "0",
            "best3of4_ppg": str(round(float(rng.uniform(2.0, 14.0)), 2)),
        })
    # Two censored TE rows — must be excluded from training
    for i in range(2):
        rows.append({
            "pfr_player_name": f"TE Censored {i}",
            "position": "TE",
            "season": "2022",
            "censored_incomplete_arc": "1",
            "nfl_pick": "50",
            "nfl_round": "2",
            "final_college_age": "22.0",
            "te_ryptpa_final": "0.04",
            "te_ryptpa_final_missing": "0",
            "te_yards_per_reception_career": "11.5",
            "te_yards_per_reception_career_missing": "0",
            "best3of4_ppg": "5.0",
        })
    # Non-TE rows — must not affect TE model
    for i in range(n_wr):
        rows.append({
            "pfr_player_name": f"WR Player {i}",
            "position": "WR",
            "season": "2018",
            "censored_incomplete_arc": "0",
            "nfl_pick": "30",
            "nfl_round": "2",
            "final_college_age": "21.5",
            "te_ryptpa_final": "",
            "te_ryptpa_final_missing": "1",
            "te_yards_per_reception_career": "",
            "te_yards_per_reception_career_missing": "1",
            "best3of4_ppg": "8.0",
        })
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def promotion_env(tmp_path, monkeypatch):
    """Set up a self-contained promotion environment with a synthetic v3 CSV."""
    v3_csv = tmp_path / "v3.csv"
    _make_minimal_v3_csv(v3_csv)
    head_a_dir = tmp_path / "head_a"
    head_a_dir.mkdir()
    # Monkeypatch module-level constants before import
    import importlib
    if "promote_head_a_te_v3" in sys.modules:
        del sys.modules["promote_head_a_te_v3"]
    # Add scripts/ to path
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import promote_head_a_te_v3 as promo
    monkeypatch.setattr(promo, "V3_CSV", v3_csv)
    monkeypatch.setattr(promo, "HEAD_A_DIR", head_a_dir)
    return promo, head_a_dir


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_promotion_creates_te_pkl_and_manifest(promotion_env):
    """promote() must create te_v3.pkl and v3_manifest.json under HEAD_A_DIR."""
    promo, head_a_dir = promotion_env
    promo.promote()
    pkls = list((head_a_dir / "runs").glob("*/te_v3.pkl"))
    assert pkls, "te_v3.pkl must exist in a timestamped run subdirectory"
    assert (head_a_dir / "v3_manifest.json").exists(), "v3_manifest.json must be created"


def test_serialized_pipeline_predicts_without_error(promotion_env):
    """Loaded te_v3.pkl must be a fitted sklearn Pipeline that accepts 5 features."""
    promo, head_a_dir = promotion_env
    promo.promote()
    pkl_path = next((head_a_dir / "runs").glob("*/te_v3.pkl"))
    with pkl_path.open("rb") as f:
        pipeline = pickle.load(f)
    # 5 features: nfl_pick, nfl_round, final_college_age, te_ryptpa_final, te_yards_per_reception_career
    X_sample = np.array([[50.0, 2.0, 22.5, 0.04, 11.5]])
    pred = pipeline.predict(X_sample)
    assert pred.shape == (1,), "predict must return a (1,) array"
    assert np.isfinite(pred[0]), "prediction must be a finite float"


def test_manifest_has_te_key_pointing_to_pkl(promotion_env):
    """v3_manifest.json must have a 'TE' key pointing to the te_v3.pkl path."""
    promo, head_a_dir = promotion_env
    promo.promote()
    manifest = json.loads((head_a_dir / "v3_manifest.json").read_text())
    assert "TE" in manifest, "manifest must have a 'TE' key"
    assert "te_v3.pkl" in manifest["TE"], "TE path must reference te_v3.pkl"


def test_metadata_records_winning_alpha_and_features(promotion_env):
    """te_v3_metadata.json must record alpha=50.0 and all 5 TE features."""
    promo, head_a_dir = promotion_env
    promo.promote()
    meta_paths = list((head_a_dir / "runs").glob("*/te_v3_metadata.json"))
    assert meta_paths, "te_v3_metadata.json must be created alongside the pkl"
    meta = json.loads(meta_paths[0].read_text())
    assert meta["alpha"] == 50.0, "metadata must record winning alpha=50.0"
    expected_features = [
        "nfl_pick", "nfl_round", "final_college_age",
        "te_ryptpa_final", "te_yards_per_reception_career",
    ]
    assert meta["features"] == expected_features, "metadata must list all 5 TE features in order"


def test_censored_rows_excluded_from_training(promotion_env):
    """Metadata n_train_rows must not count censored TE rows."""
    promo, head_a_dir = promotion_env
    promo.promote()
    meta_paths = list((head_a_dir / "runs").glob("*/te_v3_metadata.json"))
    meta = json.loads(meta_paths[0].read_text())
    # Synthetic CSV has 20 non-censored TE rows (all features populated) + 2 censored
    assert meta["n_train_rows"] == 20, (
        f"expected 20 non-censored training rows, got {meta['n_train_rows']}"
    )


def test_non_te_rows_do_not_affect_te_model(promotion_env):
    """promote() must complete without error even when WR rows lack TE features."""
    promo, head_a_dir = promotion_env
    # Should not raise even though WR rows have empty te_ryptpa_final
    promo.promote()
    assert (head_a_dir / "v3_manifest.json").exists()
