"""DG-057 — Engine A load-time spec verification wiring.

TDD RED: fails until EngineAScorer._load() verifies every artifact through
src/dynasty_genius/models/artifact_verification.py.

Both directions the ticket demands, at the real serving loader:
1. Grandfathered pass-through — the CURRENTLY deployed artifacts (pre-spec,
   no sidecars) keep loading and scoring exactly as today, with a disclosed
   "pre_spec_artifact" state. Not a refusal; serving output unchanged.
2. Wrong-hash refusal — a pointer that pins a spec hash refuses artifacts
   stamped with a different spec; an unknown artifact with no sidecar and no
   grandfather entry refuses as unverifiable.
3. Spec-hashed artifacts (the 2027 path) load as "verified" and score.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]

_POSITIONS = ("WR", "RB", "TE", "QB")


def _make_spec(position: str):
    from src.dynasty_genius.models.training_spec import TrainingSpec

    return TrainingSpec(
        engine="engine_a",
        model_id=f"engine_a:{position}",
        feature_set=("pick", "round", "age"),
        feature_set_version="v2",
        target="y24_ppg",
        label_horizon="second_nfl_season",
        cohort_filter="drafted_prospects_with_outcomes",
        preprocessing={"missing_data": "refuse_incomplete_rows", "scaling": "none"},
        estimator_family="ridge",
        tuning_policy={"alpha": "fixed", "search": "none"},
        time_split={"scheme": "draft_class_holdout", "grouping": "draft_class"},
        evaluation_baselines=("pick_only_linear",),
        calibration_method="empirical_p90_ceiling",
    )


def _fit_synthetic_ridge() -> Ridge:
    X = np.array([[5, 1, 21.0], [40, 2, 22.0], [100, 4, 23.0], [220, 7, 24.0]])
    y = np.array([14.0, 9.0, 5.0, 1.5])
    return Ridge(alpha=1.0).fit(X, y)


@pytest.fixture
def synthetic_run(tmp_path):
    """A fake ROOT holding a run dir with fitted pkls for all four positions.

    Returns (fake_root, run_dir, pointer_path). The pointer is NOT written —
    each test writes its own (pinned or unpinned).
    """
    fake_root = tmp_path
    run_dir = fake_root / "app" / "data" / "models" / "runs" / "19700101T000000Z"
    run_dir.mkdir(parents=True)
    model = _fit_synthetic_ridge()
    for pos in _POSITIONS:
        with open(run_dir / f"{pos}_model.pkl", "wb") as f:
            pickle.dump(model, f)
    pointer_path = fake_root / "app" / "data" / "models" / "latest.json"
    return fake_root, run_dir, pointer_path


def _write_pointer(pointer_path: Path, *, spec_hash: str | None) -> None:
    payload = {
        "model_version": "19700101T000000Z",
        "run_dir": "app/data/models/runs/19700101T000000Z",
    }
    if spec_hash is not None:
        payload["training_spec_hash"] = spec_hash
    pointer_path.write_text(json.dumps(payload))


def _point_engine_a_at(monkeypatch, fake_root: Path, pointer_path: Path) -> None:
    from src.dynasty_genius.scoring import engine_a

    monkeypatch.setattr(engine_a, "ROOT", fake_root)
    monkeypatch.setattr(engine_a, "LATEST_POINTER", pointer_path)


# ── 1. Grandfathered pass-through (the deployed artifacts) ───────────────────

def test_deployed_artifacts_load_and_score_as_pre_spec():
    from src.dynasty_genius.models.artifact_verification import STATE_PRE_SPEC
    from src.dynasty_genius.scoring.engine_a import EngineAScorer

    scorer = EngineAScorer()
    result = scorer.score("WR", pick=5, round_=1, age=21.0)

    # Serving output is unchanged from the pre-DG-057 contract.
    assert result is not None
    assert result["engine_used"] == "engine_a_rookie_forecast_ridge"
    assert result["dynasty_value_score"] is not None
    pointer = json.loads(
        (ROOT / "app" / "data" / "models" / "latest.json").read_text()
    )
    assert result["model_version"] == pointer["model_version"]

    # ...and the pre-spec state is disclosed, per position.
    states = scorer.spec_verification_state()
    assert set(states) == set(_POSITIONS)
    for pos in _POSITIONS:
        assert states[pos] == STATE_PRE_SPEC, pos


# ── 2a. Wrong-hash refusal ───────────────────────────────────────────────────

def test_pinned_pointer_refuses_wrong_spec_artifacts(monkeypatch, synthetic_run):
    from src.dynasty_genius.models.artifact_verification import (
        ArtifactSpecRefusal,
        write_spec_sidecar,
    )
    from src.dynasty_genius.scoring.engine_a import EngineAScorer

    fake_root, run_dir, pointer_path = synthetic_run
    for pos in _POSITIONS:
        write_spec_sidecar(run_dir / f"{pos}_model.pkl", _make_spec(pos))
    # The pointer pins a DIFFERENT spec (QB's) than the first-loaded artifact
    # (WR's) was stamped with.
    _write_pointer(pointer_path, spec_hash=_make_spec("QB").spec_hash())
    _point_engine_a_at(monkeypatch, fake_root, pointer_path)

    scorer = EngineAScorer()
    with pytest.raises(ArtifactSpecRefusal) as exc:
        scorer.score("WR", pick=5, round_=1, age=21.0)
    assert exc.value.reason == "spec_hash_mismatch"


# ── 2b. Unverifiable refusal ─────────────────────────────────────────────────

def test_unknown_sidecarless_artifact_refused(monkeypatch, synthetic_run):
    """A retrained pickle dropped into the run dir with no sidecar is neither
    verified nor grandfathered — serving refuses instead of loading blind."""
    from src.dynasty_genius.models.artifact_verification import ArtifactSpecRefusal
    from src.dynasty_genius.scoring.engine_a import EngineAScorer

    fake_root, _run_dir, pointer_path = synthetic_run
    _write_pointer(pointer_path, spec_hash=None)
    _point_engine_a_at(monkeypatch, fake_root, pointer_path)

    scorer = EngineAScorer()
    with pytest.raises(ArtifactSpecRefusal) as exc:
        scorer.score("WR", pick=5, round_=1, age=21.0)
    assert exc.value.reason == "unverifiable_artifact"


# ── 3. Spec-hashed artifacts load as verified and score ──────────────────────

def test_spec_hashed_artifacts_load_verified_and_score(monkeypatch, synthetic_run):
    from src.dynasty_genius.models.artifact_verification import (
        STATE_VERIFIED,
        write_spec_sidecar,
    )
    from src.dynasty_genius.scoring.engine_a import EngineAScorer

    fake_root, run_dir, pointer_path = synthetic_run
    # One spec governs the run (per-position model_id would produce
    # per-position hashes; a run-level pin means one spec for all four).
    spec = _make_spec("ALL")
    for pos in _POSITIONS:
        write_spec_sidecar(run_dir / f"{pos}_model.pkl", spec)
    _write_pointer(pointer_path, spec_hash=spec.spec_hash())
    _point_engine_a_at(monkeypatch, fake_root, pointer_path)

    scorer = EngineAScorer()
    result = scorer.score("WR", pick=5, round_=1, age=21.0)
    assert result is not None
    assert result["dynasty_value_score"] is not None
    states = scorer.spec_verification_state()
    for pos in _POSITIONS:
        assert states[pos] == STATE_VERIFIED, pos


def test_unpinned_pointer_still_loads_verified_sidecars(monkeypatch, synthetic_run):
    """Sidecar-stamped artifacts under a pre-spec pointer verify internally."""
    from src.dynasty_genius.models.artifact_verification import (
        STATE_VERIFIED,
        write_spec_sidecar,
    )
    from src.dynasty_genius.scoring.engine_a import EngineAScorer

    fake_root, run_dir, pointer_path = synthetic_run
    for pos in _POSITIONS:
        write_spec_sidecar(run_dir / f"{pos}_model.pkl", _make_spec(pos))
    _write_pointer(pointer_path, spec_hash=None)
    _point_engine_a_at(monkeypatch, fake_root, pointer_path)

    scorer = EngineAScorer()
    assert scorer.score("WR", pick=5, round_=1, age=21.0) is not None
    assert set(scorer.spec_verification_state().values()) == {STATE_VERIFIED}
