"""RED hardening for Morning Tape G4-2 — two falsified edges from Codex's audit.

1. Duplicate-IDENTICAL crosswalk rows for one player are not a real conflict: they
   collapse to a single RESOLVED identity, never a false ``ambiguous_crosswalk``
   (which would inflate the ambiguous denominator and fire a spurious UI alert).
   Genuinely distinct sleeper targets for one GSIS still stay ambiguous.
2. The read-only endpoint must fail closed (503) on a persisted artifact that is
   malformed or verdict-bearing (``decision_supported`` not False, at artifact or
   player level), never serve it as 200 — a No-Verdict Line guard at the serve layer.
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
    return {"gsis_id": gsis_id, "sleeper_id": sleeper_id, "name": name, "position": "WR"}


def test_identical_duplicate_crosswalk_rows_collapse_to_resolved_not_ambiguous() -> None:
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0008", 12.0)],
        crosswalk_entries=[
            _crosswalk("00-0008", "108", "Same Player"),
            _crosswalk("00-0008", "108", "Same Player"),  # exact duplicate row
        ],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["coverage"]["resolved_identity_count"] == 1
    assert artifact["coverage"]["ambiguous_identity_count"] == 0
    row = artifact["players"][0]
    assert row["identity"]["identity_resolved"] is True
    assert row["identity"]["identity_status"] == "resolved"
    assert row["identity"]["sleeper_id"] == "108"
    assert "ambiguous_crosswalk" not in row["caveats"]


def test_conflicting_distinct_sleeper_ids_remain_ambiguous() -> None:
    """Guard against over-collapsing: genuinely distinct targets stay ambiguous."""
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0009", 12.0)],
        crosswalk_entries=[
            _crosswalk("00-0009", "109", "Candidate A"),
            _crosswalk("00-0009", "110", "Candidate B"),
        ],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["coverage"]["ambiguous_identity_count"] == 1
    row = artifact["players"][0]
    assert row["identity"]["identity_status"] == "ambiguous_crosswalk"
    assert row["identity"]["sleeper_id"] is None


def test_null_sleeper_bridge_row_classifies_as_unresolved_not_resolved() -> None:
    """A real bridge row with a null sleeper_id is not a resolution."""
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0010", 12.0)],
        crosswalk_entries=[_crosswalk("00-0010", None, "Unmatched Bridge")],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["coverage"]["resolved_identity_count"] == 0
    assert artifact["coverage"]["unresolved_identity_count"] == 1
    row = artifact["players"][0]
    assert row["identity"]["identity_resolved"] is False
    assert row["identity"]["identity_status"] == "unresolved_crosswalk"
    assert row["identity"]["sleeper_id"] is None
    assert "unresolved_crosswalk" in row["caveats"]


def test_null_and_real_target_resolves_to_the_real_one() -> None:
    """Mixed rows (a null bridge + a real target) resolve to the real target."""
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0011", 12.0)],
        crosswalk_entries=[
            _crosswalk("00-0011", None, "Null Bridge"),
            _crosswalk("00-0011", "111", "Real Target"),
        ],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert artifact["coverage"]["resolved_identity_count"] == 1
    row = artifact["players"][0]
    assert row["identity"]["identity_resolved"] is True
    assert row["identity"]["sleeper_id"] == "111"
    assert row["identity"]["player_name"] == "Real Target"


def test_every_player_row_carries_explicit_per_row_decision_supported_false() -> None:
    """Each row independently discloses no-verdict so a single card always shows it."""
    artifact = build_model_population_artifact(
        engine_scores=[_score("00-0012", 15.0), _score("00-0013", 9.0)],
        crosswalk_entries=[_crosswalk("00-0012", "112", "Resolved One")],
        engine_scores_as_of="2026-07-14T12:00:00+00:00",
        crosswalk_as_of="2026-07-14T12:00:00+00:00",
        now="2026-07-14T13:00:00+00:00",
    )

    assert len(artifact["players"]) == 2
    for row in artifact["players"]:
        assert row["decision_supported"] is False


def _persist(tmp_path, monkeypatch, payload: dict):
    from app.api.routes import morning_tape

    path = tmp_path / "morning_tape_latest.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(morning_tape, "_ARTIFACT_PATH", path)
    return morning_tape


def test_endpoint_rejects_artifact_level_verdict_with_503(tmp_path, monkeypatch) -> None:
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            "decision_supported": True,  # verdict-bearing — must never serve
            "coverage": {},
            "players": [],
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503


def test_endpoint_rejects_player_model_level_verdict_with_503(tmp_path, monkeypatch) -> None:
    # Row-level flag correct, but the model bundle leaks a verdict → still fail closed.
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            "decision_supported": False,
            "coverage": {},
            "players": [
                {"identity": {}, "decision_supported": False, "model": {"decision_supported": True}, "caveats": []}
            ],
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503


def test_endpoint_rejects_player_row_missing_decision_supported_with_503(
    tmp_path, monkeypatch
) -> None:
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            "decision_supported": False,
            "coverage": {},
            "players": [{"identity": {}, "model": {}, "caveats": []}],  # no row-level flag
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503


def test_endpoint_rejects_player_row_level_verdict_true_with_503(
    tmp_path, monkeypatch
) -> None:
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            "decision_supported": False,
            "coverage": {},
            "players": [{"identity": {}, "decision_supported": True, "model": {}, "caveats": []}],
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503


def test_endpoint_rejects_player_model_missing_decision_supported_with_503(
    tmp_path, monkeypatch
) -> None:
    # Row-level flag correct, but the nested model omits decision_supported:
    # missing/None/non-bool must fail closed, not only literal True.
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            "decision_supported": False,
            "coverage": {},
            "players": [
                {"identity": {}, "decision_supported": False, "model": {}, "caveats": []}
            ],
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503


def test_endpoint_serves_a_well_formed_no_verdict_artifact_200(tmp_path, monkeypatch) -> None:
    artifact = {
        "schema_version": "morning_tape_model_population.v1",
        "status": "ok",
        "decision_supported": False,
        "coverage": {"engine_score_count": 1},
        "players": [
            {
                "identity": {"gsis_id": "00-0014", "sleeper_id": "114", "identity_resolved": True},
                "decision_supported": False,
                "model": {"decision_supported": False, "experimental": False},
                "caveats": [],
            }
        ],
        "receipts": {"crosswalk": {"status": "fresh"}},
    }
    _persist(tmp_path, monkeypatch, artifact)
    response = TestClient(app).get("/api/league/morning-tape")
    assert response.status_code == 200
    assert response.json() == artifact


def test_endpoint_rejects_artifact_missing_decision_supported_with_503(
    tmp_path, monkeypatch
) -> None:
    _persist(
        tmp_path,
        monkeypatch,
        {
            "schema_version": "morning_tape_model_population.v1",
            "status": "ok",
            # decision_supported absent — not provably no-verdict → malformed
            "coverage": {},
            "players": [],
            "receipts": {},
        },
    )
    assert TestClient(app).get("/api/league/morning-tape").status_code == 503
