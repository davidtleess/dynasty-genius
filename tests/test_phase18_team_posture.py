from __future__ import annotations

import copy
import json


def _team(
    roster_id: int,
    *,
    starter_weighted_xvar: float,
    value_weighted_age: float | None,
    owned_picks: list[dict] | None = None,
    outgoing_picks: list[dict] | None = None,
    taxi_xvar: float = 0.0,
) -> dict:
    return {
        "roster_id": roster_id,
        "owner": {"team_name": f"Team {roster_id}", "display_name": f"Owner {roster_id}"},
        "team_value_views": {
            "starter_weighted_xvar": starter_weighted_xvar,
            "lineup_xvar": starter_weighted_xvar,
            "depth_credit_xvar": 0.0,
        },
        "age_profile": {
            "value_weighted_age": value_weighted_age,
            "pct_value_over_28": 0.10 if value_weighted_age and value_weighted_age < 27 else 0.55,
        },
        "future_picks": {
            "owned": owned_picks or [],
            "outgoing": outgoing_picks or [],
        },
        "players": [
            {
                "sleeper_player_id": f"taxi-{roster_id}",
                "position": "RB",
                "raw_xvar": taxi_xvar,
                "lineup_role": "taxi",
            }
        ],
        "posture": {"label": "UNCLASSIFIED", "score": None},
        "decision_supported": False,
    }


def _matrix() -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-05-22T20:00:00+00:00",
        "teams": [
            _team(1, starter_weighted_xvar=130.0, value_weighted_age=28.5),
            _team(
                2,
                starter_weighted_xvar=70.0,
                value_weighted_age=24.0,
                owned_picks=[
                    {"season": 2027, "round": 1, "pick_value_status": "deferred"},
                    {"season": 2027, "round": 2, "pick_value_status": "deferred"},
                ],
                taxi_xvar=12.0,
            ),
            _team(
                3,
                starter_weighted_xvar=100.0,
                value_weighted_age=24.5,
                owned_picks=[{"season": 2027, "round": 1, "pick_value_status": "deferred"}],
                taxi_xvar=10.0,
            ),
            _team(
                4,
                starter_weighted_xvar=95.0,
                value_weighted_age=29.0,
                outgoing_picks=[{"season": 2027, "round": 1, "pick_value_status": "deferred"}],
            ),
        ],
    }


def test_team_posture_classifier_emits_governed_non_decision_labels():
    from src.dynasty_genius.team_posture import build_team_posture_artifact

    posture = build_team_posture_artifact(_matrix(), captured_at="2026-05-22T20:05:00+00:00")
    labels = {team["roster_id"]: team["posture"]["label"] for team in posture["teams"]}

    assert posture["schema_version"] == "team_posture.v1"
    assert posture["decision_supported"] is False
    assert posture["coverage"]["decision_supported_true_count"] == 0
    assert posture["coverage"]["market_fields_absent"] is True
    assert labels[1] == "CONTENDER"
    assert labels[2] == "REBUILDING"
    assert labels[3] == "ASCENDING"
    assert labels[4] == "TRANSITIONAL"
    for row in posture["teams"]:
        assert row["posture"]["manual_override_allowed"] is True
        assert row["posture"]["classification_basis"] == "internal_team_matrix_v1"
        assert row["posture"]["decision_supported"] is False


def test_team_posture_does_not_mutate_team_matrix():
    from src.dynasty_genius.team_posture import build_team_posture_artifact

    matrix = _matrix()
    original = copy.deepcopy(matrix)
    build_team_posture_artifact(matrix)

    assert matrix == original


def test_apply_team_postures_replaces_unclassified_labels_without_mutating_inputs():
    from src.dynasty_genius.team_posture import (
        apply_team_postures,
        build_team_posture_artifact,
    )

    matrix = _matrix()
    posture = build_team_posture_artifact(matrix)
    updated = apply_team_postures(matrix, posture)

    assert {team["posture"]["label"] for team in matrix["teams"]} == {"UNCLASSIFIED"}
    assert {team["posture"]["label"] for team in updated["teams"]} >= {"CONTENDER", "REBUILDING", "ASCENDING"}
    assert updated["teams"][0]["posture"]["source_artifact_schema_version"] == "team_posture.v1"


def test_team_posture_writer_outputs_json_and_latest(tmp_path):
    from src.dynasty_genius.team_posture import (
        build_team_posture_artifact,
        write_team_posture_artifacts,
    )

    posture = build_team_posture_artifact(_matrix())
    paths = write_team_posture_artifacts(posture, output_dir=tmp_path, run_id="phase18-3-test")

    assert paths["posture"].exists()
    assert paths["posture_latest"].exists()
    payload = json.loads(paths["posture_latest"].read_text())
    assert payload["schema_version"] == "team_posture.v1"
