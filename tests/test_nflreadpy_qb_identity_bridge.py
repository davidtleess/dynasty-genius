from __future__ import annotations

import json

import pandas as pd


def test_build_bridge_resolves_qbs_and_marks_unresolved() -> None:
    from scripts.build_nflreadpy_qb_identity_bridge import build_bridge

    canonical_qbs = [
        {"player_id": "josh_allen_qb_1996", "pfr_player_name": "Josh Allen", "position": "QB", "season": 2024},
        {"player_id": "missing_qb", "pfr_player_name": "Missing QB", "position": "QB", "season": 2024},
        {"player_id": "not_a_qb", "pfr_player_name": "Wide Receiver", "position": "WR", "season": 2024},
    ]
    rosters = pd.DataFrame(
        [
            {
                "player_name": "Josh Allen",
                "position": "QB",
                "gsis_id": "00-0034857",
                "season": 2024,
            }
        ]
    )

    bridge = build_bridge(canonical_qbs, rosters, coverage_threshold=0.5)

    assert set(bridge["players"]) == {"josh_allen_qb_1996", "missing_qb"}
    assert bridge["players"]["josh_allen_qb_1996"]["gsis_id"] == "00-0034857"
    assert bridge["players"]["josh_allen_qb_1996"]["coverage"] == "FULL"
    assert bridge["players"]["missing_qb"]["coverage"] == "NONE"
    assert bridge["players"]["missing_qb"]["unresolved_reason"] == "no_nflreadpy_roster_match"
    assert bridge["coverage"]["resolved"] == 1
    assert bridge["coverage"]["unresolved"] == 1
    assert bridge["coverage"]["coverage_pct"] == 0.5
    assert bridge["coverage"]["threshold_met"] is True


def test_build_bridge_is_deterministic() -> None:
    from scripts.build_nflreadpy_qb_identity_bridge import build_bridge

    canonical_qbs = [
        {"player_id": "b_qb", "pfr_player_name": "Beta QB", "position": "QB", "season": 2025},
        {"player_id": "a_qb", "pfr_player_name": "Alpha QB", "position": "QB", "season": 2025},
    ]
    rosters = pd.DataFrame(
        [
            {"player_name": "Alpha QB", "position": "QB", "gsis_id": "00-0000001", "season": 2025},
            {"player_name": "Beta QB", "position": "QB", "gsis_id": "00-0000002", "season": 2025},
        ]
    )

    first = build_bridge(canonical_qbs, rosters)
    second = build_bridge(list(reversed(canonical_qbs)), rosters.sample(frac=1, random_state=7))

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert list(first["players"]) == ["a_qb", "b_qb"]


def test_write_bridge_artifact_round_trips_json(tmp_path) -> None:
    from scripts.build_nflreadpy_qb_identity_bridge import write_bridge_artifact

    bridge = {
        "metadata": {"source": "test"},
        "coverage": {"total": 1, "resolved": 1, "unresolved": 0, "coverage_pct": 1.0, "threshold_met": True},
        "players": {
            "josh_allen_qb_1996": {
                "pfr_player_name": "Josh Allen",
                "normalized_name": "josh_allen",
                "gsis_id": "00-0034857",
                "season": 2024,
                "coverage": "FULL",
                "unresolved_reason": None,
            }
        },
    }

    output_path = tmp_path / "bridge.json"
    write_bridge_artifact(bridge, output_path)

    assert json.loads(output_path.read_text()) == bridge
