"""Artifact Freshness T2 RED: 17.5 roster-cut handoff wiring."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest

from src.dynasty_genius.roster_cut_engine import RosterCutCandidate, RosterCutResult


def _candidate(pid: str = "cut-1") -> RosterCutCandidate:
    return RosterCutCandidate(
        sleeper_player_id=pid,
        full_name="Cut Candidate",
        position="WR",
        age=25.0,
        years_exp=2,
        ir_compliance_status="NOT_ON_IR",
        taxi_eligibility="INELIGIBLE_VET",
        scoring_tier="A",
        xvar_pct=20.0,
        dvs=40.0,
        cut_priority=1,
        age_cliff_warning=False,
        cut_rationale=["waiver_status_from_sleeper_snapshot"],
        exempt=False,
        exempt_reason=None,
    )


def _cut_result() -> RosterCutResult:
    return RosterCutResult(
        roster_id=1,
        total_players=22,
        active_slots=20,
        total_capacity=26,
        cuts_required=1,
        reserve_unrestricted=True,
        cut_candidates=[_candidate()],
        exempt_players=[],
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _team(roster_id: int) -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "roster_id": roster_id,
        "owner": {"team_name": f"Team {roster_id}"},
        "positional_summary": {
            pos: {"z_score": 0.0, "surplus_label": "neutral", "n_rostered": 2}
            for pos in ("QB", "RB", "WR", "TE")
        },
        "team_value_views": {"starter_weighted_xvar": 100.0, "lineup_xvar": 100.0},
        "posture": {"label": "UNCLASSIFIED", "score": None},
        "future_picks": {"owned": [], "outgoing": []},
        "players": [],
        "decision_supported": False,
    }


def _waiver_player() -> dict:
    return {
        "sleeper_player_id": "waiver-1",
        "dg_player_id": "dg_waiver_1",
        "player": {"full_name": "Waiver Player", "position": "WR"},
        "league_context": {
            "rostered": False,
            "roster_id": None,
            "on_taxi": False,
            "on_ir": False,
        },
        "valuation": {"engine_path": "ENGINE_B", "xvar": 10.0},
        "market_overlay": {"market_value": 1000.0},
        "divergence": {
            "signal": "MODEL_HIGH_MARKET_LOW",
            "signal_status": "gates_passed",
            "model_minus_market_delta": 0.25,
            "model_percentile": 0.75,
            "market_percentile": 0.50,
            "decision_supported": False,
        },
    }


def _team_matrix() -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-06-23T12:00:00+00:00",
        "teams": [_team(1), _team(2)],
    }


def _market_divergence() -> dict:
    return {
        "schema_version": "market_divergence.v1",
        "league_id": "league",
        "players": [_waiver_player()],
    }


def test_roster_cut_report_latest_unwraps_inner_result(tmp_path: Path) -> None:
    script = import_module("scripts.build_league_opportunity_map")
    report = tmp_path / "roster_cut_report_latest.json"
    _write_json(
        report,
        {
            "run_id": "phase21-20260623T120000Z",
            "captured_at": "2026-06-23T12:00:00Z",
            "roster_cut_report": _cut_result().model_dump(mode="json"),
        },
    )

    result = script._load_roster_cut_result(report)

    assert isinstance(result, RosterCutResult)
    assert result.cut_candidates[0].sleeper_player_id == "cut-1"


@pytest.mark.parametrize(
    "payload",
    [
        {"run_id": "missing-inner"},
        {"roster_cut_report": {"roster_id": 1}},
    ],
)
def test_roster_cut_report_missing_or_malformed_inner_fails_closed(
    tmp_path: Path,
    payload: dict,
) -> None:
    script = import_module("scripts.build_league_opportunity_map")
    report = tmp_path / "roster_cut_report_latest.json"
    _write_json(report, payload)

    with pytest.raises(ValueError, match="roster_cut_report"):
        script._load_roster_cut_result(report)


def test_league_opportunity_script_passes_unwrapped_roster_cut_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = import_module("scripts.build_league_opportunity_map")
    team_matrix = tmp_path / "team_value_matrix_latest.json"
    market = tmp_path / "universe_market_divergence_latest.json"
    posture = tmp_path / "team_posture_latest.json"
    cut_report = tmp_path / "roster_cut_report_latest.json"
    output_dir = tmp_path / "out"
    _write_json(team_matrix, {"schema_version": "team_value_matrix.v1", "teams": []})
    _write_json(market, {"schema_version": "market_divergence.v1", "players": []})
    _write_json(posture, {"schema_version": "team_posture.v1", "teams": []})
    _write_json(
        cut_report,
        {
            "run_id": "phase21-20260623T120000Z",
            "captured_at": "2026-06-23T12:00:00Z",
            "roster_cut_report": _cut_result().model_dump(mode="json"),
        },
    )

    captured: dict[str, object] = {}

    def fake_build(*_args: object, **kwargs: object) -> dict:
        captured.update(kwargs)
        return {"schema_version": "league_opportunity.v1", "cards": []}

    def fake_write(payload: dict, *, output_dir: Path, run_id: str) -> dict:
        return {"batch": output_dir / f"{run_id}.json", "markdown": output_dir / f"{run_id}.md"}

    monkeypatch.setattr(script, "TEAM_MATRIX_PATH", team_matrix)
    monkeypatch.setattr(script, "MARKET_DIVERGENCE_PATH", market)
    monkeypatch.setattr(script, "TEAM_POSTURE_PATH", posture)
    monkeypatch.setattr(script, "ROSTER_CUT_REPORT_PATH", cut_report, raising=False)
    monkeypatch.setattr(script, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(script, "build_league_opportunity_map", fake_build)
    monkeypatch.setattr(script, "write_league_opportunity_artifacts", fake_write)

    script.main()

    assert isinstance(captured["roster_cut_result"], RosterCutResult)
    assert captured["roster_cut_result"].cut_candidates[0].sleeper_player_id == "cut-1"


def test_script_wiring_adds_recommended_drop_to_waiver_cards(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = import_module("scripts.build_league_opportunity_map")
    team_matrix = tmp_path / "team_value_matrix_latest.json"
    market = tmp_path / "universe_market_divergence_latest.json"
    posture = tmp_path / "team_posture_latest.json"
    cut_report = tmp_path / "roster_cut_report_latest.json"
    output_dir = tmp_path / "out"
    _write_json(team_matrix, _team_matrix())
    _write_json(market, _market_divergence())
    _write_json(posture, {"schema_version": "team_posture.v1", "teams": []})
    _write_json(
        cut_report,
        {
            "run_id": "phase21-20260623T120000Z",
            "captured_at": "2026-06-23T12:00:00Z",
            "roster_cut_report": _cut_result().model_dump(mode="json"),
        },
    )

    written: dict[str, object] = {}

    def fake_write(payload: dict, *, output_dir: Path, run_id: str) -> dict:
        written["payload"] = payload
        return {"batch": output_dir / f"{run_id}.json", "markdown": output_dir / f"{run_id}.md"}

    monkeypatch.setattr(script, "TEAM_MATRIX_PATH", team_matrix)
    monkeypatch.setattr(script, "MARKET_DIVERGENCE_PATH", market)
    monkeypatch.setattr(script, "TEAM_POSTURE_PATH", posture)
    monkeypatch.setattr(script, "ROSTER_CUT_REPORT_PATH", cut_report, raising=False)
    monkeypatch.setattr(script, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(script, "write_league_opportunity_artifacts", fake_write)

    script.main()

    waiver_cards = [
        card
        for card in written["payload"]["cards"]
        if card["card_type"] == "WAIVER_CANDIDATE"
    ]
    assert waiver_cards
    assert waiver_cards[0]["recommended_drop"]["sleeper_player_id"] == "cut-1"
