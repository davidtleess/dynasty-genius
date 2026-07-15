"""RED contract for Morning Tape Phase 1, beginning with G4-2 identity joining.

The artifact owns the model population; the HTTP surface only reads the completed
artifact.  An unresolved or ambiguous GSIS→Sleeper join is a visible evidence state,
never a reason to drop an Engine B row or make an arbitrary identity selection.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.morning_tape_artifact import build_model_population_artifact


def _score(gsis_id: str, prediction: float, *, experimental: bool = False) -> dict:
    return {
        "player_id": gsis_id,
        "predicted_avg_ppg_t1_t2": prediction,
        "engine": "engine_b_v2",
        "feature_season": 2025,
        "position": "WR",
        "decision_supported": False,
        "experimental": experimental,
        "caveats": ["engine_b_not_decision_grade"],
    }


def _crosswalk(gsis_id: str, sleeper_id: str, name: str = "Player") -> dict:
    return {
        "gsis_id": gsis_id,
        "sleeper_id": sleeper_id,
        "name": name,
        "position": "WR",
    }


def test_model_population_keeps_unresolved_engine_b_rows_with_honest_identity_state() -> None:
    artifact = build_model_population_artifact(
        engine_scores=[
            _score("00-0001", 15.4),
            _score("00-0002", 12.1, experimental=True),
        ],
        crosswalk_entries=[_crosswalk("00-0001", "101", "Resolved Player")],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["schema_version"] == "morning_tape_model_population.v1"
    assert artifact["decision_supported"] is False
    assert artifact["status"] == "ok"
    assert artifact["coverage"] == {
        "engine_score_count": 2,
        "resolved_identity_count": 1,
        "unresolved_identity_count": 1,
        "ambiguous_identity_count": 0,
    }

    resolved, unresolved = artifact["players"]
    assert resolved["identity"] == {
        "gsis_id": "00-0001",
        "sleeper_id": "101",
        "identity_resolved": True,
        "identity_status": "resolved",
        "player_name": "Resolved Player",
        "position": "WR",
    }
    assert unresolved["identity"] == {
        "gsis_id": "00-0002",
        "sleeper_id": None,
        "identity_resolved": False,
        "identity_status": "unresolved_crosswalk",
        "player_name": None,
        "position": "WR",
    }
    assert unresolved["model"]["experimental"] is True
    assert unresolved["model"]["decision_supported"] is False
    assert "unresolved_crosswalk" in unresolved["caveats"]
    assert artifact["receipts"]["crosswalk"] == {
        "as_of": "2026-07-14T12:00:00+00:00",
        "status": "fresh",
        "caveats": [],
    }


def test_model_population_preserves_engine_score_input_order_across_identity_states() -> None:
    """Identity disclosure must not reorder the supplied Engine-B population."""
    artifact = build_model_population_artifact(
        engine_scores=[
            _score("00-0005", 11.0),  # unresolved first on purpose
            _score("00-0006", 16.0),  # resolved second on purpose
            _score("00-0007", 13.0),  # unresolved last on purpose
        ],
        crosswalk_entries=[_crosswalk("00-0006", "106", "Middle Player")],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert [row["identity"]["gsis_id"] for row in artifact["players"]] == [
        "00-0005",
        "00-0006",
        "00-0007",
    ]


def test_model_population_deduplicates_without_arbitrarily_resolving_a_conflicted_crosswalk() -> None:
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0003", 14.0), _score("00-0003", 14.0)],
        crosswalk_entries=[
            _crosswalk("00-0003", "103", "First Candidate"),
            _crosswalk("00-0003", "104", "Conflicting Candidate"),
        ],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["coverage"]["engine_score_count"] == 1
    assert artifact["coverage"]["ambiguous_identity_count"] == 1
    assert len(artifact["players"]) == 1
    row = artifact["players"][0]
    assert row["identity"]["sleeper_id"] is None
    assert row["identity"]["identity_resolved"] is False
    assert row["identity"]["identity_status"] == "ambiguous_crosswalk"
    assert "ambiguous_crosswalk" in row["caveats"]


def test_model_population_preserves_rows_but_degrades_when_the_crosswalk_is_stale() -> None:
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0004", 13.0)],
        crosswalk_entries=[_crosswalk("00-0004", "104")],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-13T11:59:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["status"] == "degraded"
    assert artifact["players"][0]["identity"]["identity_resolved"] is True
    assert artifact["receipts"]["crosswalk"] == {
        "as_of": "2026-07-13T11:59:00+00:00",
        "status": "stale",
        "caveats": ["crosswalk_stale_over_24h"],
    }


def test_morning_tape_endpoint_is_thin_read_only_over_the_prebuilt_artifact(
    tmp_path, monkeypatch
) -> None:
    from app.api.routes import morning_tape

    artifact = {
        "schema_version": "morning_tape_model_population.v1",
        "status": "degraded",
        "decision_supported": False,
        "coverage": {
            "engine_score_count": 1,
            "resolved_identity_count": 0,
            "unresolved_identity_count": 1,
            "ambiguous_identity_count": 0,
        },
        "players": [],
        "receipts": {"crosswalk": {"status": "stale"}},
    }
    path = tmp_path / "morning_tape_latest.json"
    path.write_text(json.dumps(artifact))
    monkeypatch.setattr(morning_tape, "_ARTIFACT_PATH", path)
    monkeypatch.setattr(
        morning_tape,
        "build_model_population_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("request path must never rebuild Morning Tape data"),
        ),
    )

    response = TestClient(app).get("/api/league/morning-tape")

    assert response.status_code == 200
    assert response.json() == artifact
