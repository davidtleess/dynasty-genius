"""Tests for Phase 19 W5 Engine A v3 scorer — TE Head A Ridge integration.

TDD RED: All tests in groups 1–4 fail until score_prospect_v3 is implemented
in src/dynasty_genius/scoring/engine_a.py.

Covers:
1. Non-TE positions return None (no v3 contract for WR/RB/QB)
2. TE with any CFBD feature missing returns None
3. Returns None when v3_manifest.json does not exist
4. Returns correct result shape with synthetic Pipeline pkl
5. engine_used == "engine_a_v3_head_a_ridge"
6. "head_a_v3_college_features_used" in caveats
7. model_grade == "PROSPECT_C" for TE
8. pvo_assembler falls back to v2 when TE lacks CFBD features
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]

_TE_V3_FEATURE_ORDER = [
    "nfl_pick",
    "nfl_round",
    "final_college_age",
    "te_ryptpa_final",
    "te_yards_per_reception_career",
]

_FULL_TE_FEATURES = {
    "nfl_pick": 5.0,
    "nfl_round": 1.0,
    "final_college_age": 21.0,
    "te_ryptpa_final": 0.35,
    "te_yards_per_reception_career": 14.5,
}


def _build_te_v3_pipeline(path: Path) -> None:
    """Fit a minimal synthetic TE v3 Pipeline and serialize it to path."""
    pipe = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=50.0))])
    X = np.array([
        [5.0, 1.0, 21.0, 0.35, 14.5],
        [32.0, 2.0, 22.0, 0.28, 12.0],
        [65.0, 3.0, 22.5, 0.20, 10.5],
        [15.0, 1.0, 20.5, 0.40, 16.0],
        [48.0, 2.0, 23.0, 0.18, 9.5],
    ])
    y = np.array([8.5, 6.0, 4.5, 9.2, 3.8])
    pipe.fit(X, y)
    with open(path, "wb") as f:
        pickle.dump(pipe, f)


@pytest.fixture
def te_v3_manifest(tmp_path):
    """Provide a synthetic v3_manifest.json pointing to a valid te_v3.pkl."""
    pkl_path = tmp_path / "te_v3.pkl"
    _build_te_v3_pipeline(pkl_path)
    manifest = {"TE": str(pkl_path)}
    manifest_path = tmp_path / "v3_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


@pytest.fixture
def reset_v3_scorer():
    """Reset the EngineAV3Scorer singleton cache before and after each test."""
    from src.dynasty_genius.scoring import engine_a
    engine_a._v3_scorer._loaded = False
    engine_a._v3_scorer._models.clear()
    yield
    engine_a._v3_scorer._loaded = False
    engine_a._v3_scorer._models.clear()


# ── 1. Non-TE positions return None ──────────────────────────────────────────

@pytest.mark.parametrize("position", ["WR", "RB", "QB"])
def test_non_te_positions_return_none(position):
    """WR/RB/QB have no v3 contract — score_prospect_v3 must return None."""
    from src.dynasty_genius.scoring.engine_a import score_prospect_v3
    result = score_prospect_v3(position, _FULL_TE_FEATURES)
    assert result is None, (
        f"Expected None for {position} (no v3 contract), got {result}"
    )


# ── 2. TE with missing CFBD features returns None ────────────────────────────

@pytest.mark.parametrize("features,label", [
    (
        {"nfl_pick": 5.0, "nfl_round": 1.0, "final_college_age": 21.0},
        "missing both CFBD features",
    ),
    (
        {"nfl_pick": 5.0, "nfl_round": 1.0, "final_college_age": 21.0,
         "te_ryptpa_final": 0.35},
        "missing te_yards_per_reception_career",
    ),
    (
        {"nfl_pick": 5.0, "nfl_round": 1.0, "final_college_age": 21.0,
         "te_yards_per_reception_career": 14.5},
        "missing te_ryptpa_final",
    ),
    (
        {"nfl_pick": 5.0, "nfl_round": 1.0},
        "missing final_college_age and both CFBD features",
    ),
    (
        {},
        "empty features dict",
    ),
])
def test_te_missing_cfbd_returns_none(features, label):
    """TE v3 must return None when any required college feature is absent."""
    from src.dynasty_genius.scoring.engine_a import score_prospect_v3
    result = score_prospect_v3("TE", features)
    assert result is None, f"Expected None when {label}, got {result}"


# ── 3. Returns None when v3_manifest.json does not exist ─────────────────────

def test_returns_none_when_manifest_missing(monkeypatch, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    nonexistent = Path("/tmp/_no_such_v3_manifest_for_tests.json")
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", nonexistent)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is None, (
        "Expected None when v3_manifest.json does not exist"
    )


# ── 4. Returns correct result shape with synthetic Pipeline model ─────────────

def test_te_v3_returns_result_dict(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None, "Expected a result dict for TE with full features"
    assert "dynasty_value_score" in result
    assert isinstance(result["dynasty_value_score"], float)
    assert 0.0 <= result["dynasty_value_score"] <= 100.0


def test_te_v3_result_has_required_keys(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None
    for key in ("dynasty_value_score", "engine_used", "model_grade", "caveats"):
        assert key in result, f"Missing required key '{key}' in v3 result"


# ── 5. engine_used identifier ────────────────────────────────────────────────

def test_te_v3_engine_used_identifier(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None
    assert result["engine_used"] == "engine_a_v3_head_a_ridge"


# ── 6. head_a_v3_college_features_used in caveats ────────────────────────────

def test_te_v3_college_features_caveat(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None
    assert "head_a_v3_college_features_used" in result["caveats"], (
        f"Expected 'head_a_v3_college_features_used' in caveats, got {result['caveats']}"
    )


# ── 7. model_grade for TE ─────────────────────────────────────────────────────

def test_te_v3_model_grade_is_prospect_c(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None
    assert result["model_grade"] == "PROSPECT_C"


# ── 8. pvo_assembler falls back to v2 when TE lacks CFBD features ────────────

def test_pvo_assembler_te_without_cfbd_falls_back_to_v2():
    """A TE prospect supplied with only pick/round/age must still score via v2.

    This documents the graceful degradation contract: v3 returns None when
    CFBD features are absent; pvo_assembler must then invoke v2 without error.
    The engine_used on the returned PVO must be the v2 identifier.
    """
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    te_identity = PlayerIdentity(
        dg_id=generate_dg_id("Test TE W5", "TE"),
        full_name="Test TE W5",
        position="TE",
        nfl_team="KC",
    )
    pvo = assemble_pvo(
        te_identity,
        {"pick": 15, "round": 1, "age": 22.0},
        is_prospect=True,
    )
    assert pvo.engine_used == "engine_a_rookie_forecast_ridge", (
        f"Expected v2 fallback, got engine_used={pvo.engine_used}"
    )
    assert pvo.dynasty_value_score is not None
    assert pvo.model_grade == "PROSPECT_C"


# ── 9. model_version key present in v3 result (Codex blocker 1) ──────────────

def test_te_v3_result_has_model_version(monkeypatch, te_v3_manifest, reset_v3_scorer):
    from src.dynasty_genius.scoring import engine_a
    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)
    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None
    assert "model_version" in result, "model_version key missing from v3 result"
    assert result["model_version"] == "head_a_te_v3_ridge"


# ── 10. assemble_pvo full TE v3 integration path (Codex blocker 1+2) ─────────

def test_pvo_assembler_te_v3_full_path(monkeypatch, te_v3_manifest, reset_v3_scorer):
    """TE with all 5 v3 features must route through v3 with correct metadata.

    Verifies:
    - engine_used == "engine_a_v3_head_a_ridge"
    - model_version is non-null and correct
    - final_college_age from features (not age) drives scoring
    - decision_supported is False
    """
    from src.dynasty_genius.scoring import engine_a
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)

    te_identity = PlayerIdentity(
        dg_id=generate_dg_id("Test TE V3 Full", "TE"),
        full_name="Test TE V3 Full",
        position="TE",
        nfl_team="KC",
    )
    features = {
        "pick": 15,
        "round": 1,
        "age": 22.0,
        "final_college_age": 21.5,
        "te_ryptpa_final": 0.35,
        "te_yards_per_reception_career": 14.5,
    }
    pvo = assemble_pvo(te_identity, features, is_prospect=True)

    assert pvo.engine_used == "engine_a_v3_head_a_ridge", (
        f"Expected v3 routing, got engine_used={pvo.engine_used}"
    )
    assert pvo.model_version is not None, "model_version must not be None for v3 path"
    assert pvo.model_version == "head_a_te_v3_ridge"
    assert pvo.model_grade == "PROSPECT_C"
    assert pvo.decision_supported is False
    assert pvo.dynasty_value_score is not None
    assert 0.0 <= pvo.dynasty_value_score <= 100.0


# ── 11. Head B dark contract (Codex blocker 3) ───────────────────────────────

def test_head_b_dark_no_active_fields_in_pvo():
    """W4 null result: no Head B residual/market-edge score may appear active.

    PVO must have no head_b_* fields with non-None values, and
    decision_supported must be False on all TE paths.
    """
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    te_identity = PlayerIdentity(
        dg_id=generate_dg_id("Test TE Head B Dark", "TE"),
        full_name="Test TE Head B Dark",
        position="TE",
        nfl_team="KC",
    )
    pvo = assemble_pvo(
        te_identity,
        {"pick": 15, "round": 1, "age": 22.0},
        is_prospect=True,
    )

    assert pvo.decision_supported is False, (
        "decision_supported must remain False — Head B is dark after W4 null result"
    )

    pvo_dict = pvo.model_dump() if hasattr(pvo, "model_dump") else pvo.dict()
    active_head_b_fields = [
        k for k in pvo_dict
        if k.startswith("head_b") and pvo_dict[k] is not None
    ]
    assert not active_head_b_fields, (
        f"Head B dark contract violated — active fields: {active_head_b_fields}"
    )


# ── 12. Relative manifest path resolves against ROOT (Codex blocker 2) ────────

def test_relative_manifest_path_resolved_against_root(monkeypatch, tmp_path, reset_v3_scorer):
    """Relative pkl paths in v3_manifest.json must resolve against ROOT, not cwd.

    Regression: before the fix, Path(relative_str).exists() checked against process
    cwd — failing whenever the service was launched from a directory other than ROOT.
    """
    from src.dynasty_genius.scoring import engine_a

    # Build synthetic pkl under tmp_path — this is our "ROOT" for this test.
    pkl_path = tmp_path / "te_v3.pkl"
    _build_te_v3_pipeline(pkl_path)

    # Manifest entry is relative (just the filename, relative to our fake ROOT).
    manifest_path = tmp_path / "v3_manifest.json"
    manifest_path.write_text(json.dumps({"TE": "te_v3.pkl"}))

    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", manifest_path)
    monkeypatch.setattr(engine_a, "ROOT", tmp_path)

    result = engine_a.score_prospect_v3("TE", _FULL_TE_FEATURES)
    assert result is not None, (
        "Relative manifest pkl path must resolve against ROOT — got None "
        "(scorer failed to load the model)"
    )
    assert result["engine_used"] == "engine_a_v3_head_a_ridge"


# ── 13. Route: POST /api/rookies/score — TE v3 full path ─────────────────────

def test_route_te_v3_full_path_returns_v3_engine(monkeypatch, te_v3_manifest, reset_v3_scorer):
    """POST /api/rookies/score with full TE v3 fields must route through v3 scorer."""
    from fastapi.testclient import TestClient
    from app.main import app
    from src.dynasty_genius.scoring import engine_a

    monkeypatch.setattr(engine_a, "V3_MANIFEST_POINTER", te_v3_manifest)

    client = TestClient(app)
    payload = {
        "name": "Test TE Prospect",
        "position": "TE",
        "pick": 15,
        "round": 1,
        "age": 22.0,
        "final_college_age": 21.5,
        "te_ryptpa_final": 0.35,
        "te_yards_per_reception_career": 14.5,
    }
    response = client.post("/api/rookies/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["engine_used"] == "engine_a_v3_head_a_ridge", (
        f"Expected v3 route, got engine_used={data['engine_used']!r}"
    )
    assert data["model_version"] == "head_a_te_v3_ridge", (
        f"Expected model_version=head_a_te_v3_ridge, got {data['model_version']!r}"
    )
    assert data["decision_supported"] is False


# ── 14. Route: POST /api/rookies/score — TE without v3 fields falls back to v2

def test_route_te_without_cfbd_falls_back_to_v2_route():
    """POST /api/rookies/score with only pick/round/age must use v2 for TE."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {
        "name": "Test TE Prospect v2",
        "position": "TE",
        "pick": 15,
        "round": 1,
        "age": 22.0,
    }
    response = client.post("/api/rookies/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["engine_used"] == "engine_a_rookie_forecast_ridge", (
        f"Expected v2 fallback, got engine_used={data['engine_used']!r}"
    )
    assert data["decision_supported"] is False
