"""DG-128 (2026-09-01): the band and its basis marker reach every scored surface.

PVO → universe row valuation → roster-audit index/rebuild → API models. A blended
veteran (BLEND_AB) is the row the old surfaces would have dropped or relabelled as
an Engine A rookie; these tests use him as the probe because "the gate looks fixed
while David's three blanks stay blank" is exactly the failure mode.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.api.routes.players import PlayerModelLane
from app.api.routes.roster_audit_models import RosterAuditPlayer, map_player
from app.services.roster_auditor import (
    _load_rostered_universe_pvos,
    _pvo_from_universe_row,
)
from src.dynasty_genius.universe_pvo_batch import (
    _empty_valuation,
    _route_from_pvo,
    _valuation_from_pvo,
)
from tests.contract.test_surface3_player_detail_endpoint import (
    _client,
    _divergence,
    _pvo,
    _pvo_row,
)

# ── universe row ──────────────────────────────────────────────────────────────────


def test_the_valuation_block_carries_the_band() -> None:
    pvo = {"dynasty_value_score": 63.8, "dvs_band_low": 30.1, "dvs_band_high": 97.5}
    valuation = _valuation_from_pvo("BLEND_AB", pvo)
    band = (valuation["dvs_band_low"], valuation["dvs_band_high"])
    assert band == (30.1, 97.5)


def test_an_unscored_row_carries_the_band_keys_as_null() -> None:
    valuation = _empty_valuation("PRE_MODEL")
    assert valuation["dvs_band_low"] is None and valuation["dvs_band_high"] is None


def test_engine_path_is_the_lane_and_dvs_engine_is_the_basis() -> None:
    # Two axes, not one. engine_path names the LANE the player is in (rookie draft
    # row vs active-player row) and the roster index keys eligibility on it; the
    # band's BASIS — what produced the score — rides on dvs_engine. A veteran served
    # a prior stays an active-player row (phase 17 pins his dead-window case); only
    # the blend earns its own path because both engines contributed to the number.
    veteran_lane = {"engine_used": "engine_b", "model_grade": "ACTIVE_B"}
    assert _route_from_pvo({**veteran_lane, "dvs_engine": "blend"}) == "BLEND_AB"
    assert _route_from_pvo({**veteran_lane, "dvs_engine": "B"}) == "ENGINE_B"
    assert _route_from_pvo({**veteran_lane, "dvs_engine": "A"}) == "ENGINE_B"
    assert _route_from_pvo({**veteran_lane, "dvs_engine": None}) == "ENGINE_B"
    prospect_lane = {"dvs_engine": "A", "model_grade": "PROSPECT_C"}
    assert _route_from_pvo(prospect_lane) == "ENGINE_A"


# ── roster audit ──────────────────────────────────────────────────────────────────


def _blend_row() -> dict:
    return {
        "sleeper_player_id": "8146",
        "dg_player_id": "00-0037740",
        "identity_ids": {"sleeper_id": "8146"},
        "player": {
            "full_name": "Garrett Wilson",
            "position": "WR",
            "team": "NYJ",
            "age": 26.0,
        },
        "league_context": {"rostered": True, "roster_id": 1, "in_current_draft": False},
        "dvs_engine": "blend",
        "projection_2y": 12.0,
        "valuation": {
            "engine_path": "BLEND_AB",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 63.8,
            "dvs_band_low": 30.1,
            "dvs_band_high": 97.5,
            "xvar": 4.2,
            "model_version": "engine_b_v2",
            "model_grade": "ACTIVE_B",
            "feature_completeness": 1.0,
            "decision_supported": False,
        },
        "lineage": {"sleeper_snapshot_hash": "sha256:test"},
    }


def _live_wilson() -> dict:
    return {
        "player_id": "8146",
        "full_name": "Garrett Wilson",
        "position": "WR",
        "age": 26,
    }


def test_the_roster_index_admits_a_blended_veteran(tmp_path: Path) -> None:
    universe = tmp_path / "universe_pvo_batch.json"
    universe.write_text(json.dumps({"players": [_blend_row()]}))
    indexed, _provenance = _load_rostered_universe_pvos(universe)
    assert "8146" in indexed


def test_a_blended_veteran_is_rebuilt_as_a_veteran_with_his_band() -> None:
    pvo = _pvo_from_universe_row(_blend_row(), _live_wilson())
    assert pvo.is_prospect is False
    assert pvo.engine_used == "engine_b"
    assert pvo.dvs_engine == "blend"
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == (30.1, 97.5)
    assert pvo.projection_2y == 12.0
    assert "current_draft_rookie_engine_a_value_preserved" not in pvo.caveats


def test_a_measured_veteran_is_rebuilt_with_his_band_too() -> None:
    row = _blend_row()
    row["dvs_engine"] = "B"
    row["valuation"].update(
        {"engine_path": "ENGINE_B", "dvs_band_low": 43.8, "dvs_band_high": 83.8}
    )
    pvo = _pvo_from_universe_row(row, _live_wilson())
    assert pvo.dvs_engine == "B"
    assert (pvo.dvs_band_low, pvo.dvs_band_high) == (43.8, 83.8)


# ── API models ────────────────────────────────────────────────────────────────────


def test_the_roster_audit_player_carries_the_band_through_its_allowlist() -> None:
    raw = {
        "player_id": "8146",
        "full_name": "Garrett Wilson",
        "position": "WR",
        "model_grade": "ACTIVE_B",
        "dvs_engine": "blend",
        "dynasty_value_score": 63.8,
        "dvs_band_low": 30.1,
        "dvs_band_high": 97.5,
        "engine_used": "engine_b",
    }
    player = map_player(raw)
    assert isinstance(player, RosterAuditPlayer)
    assert (player.dvs_band_low, player.dvs_band_high) == (30.1, 97.5)


def test_the_player_model_lane_has_the_band() -> None:
    lane = PlayerModelLane(
        engine_path="BLEND_AB",
        dvs_engine="blend",
        model_grade="ACTIVE_B",
        model_version="engine_b_v2",
        dynasty_value_score=63.8,
        dvs_band_low=30.1,
        dvs_band_high=97.5,
        xvar=4.2,
        xvar_percentile_position=55.0,
        projection_1y=None,
        projection_2y=12.0,
        projection_3y=None,
    )
    assert (lane.dvs_band_low, lane.dvs_band_high) == (30.1, 97.5)
    assert lane.dvs_engine == "blend"


def test_the_player_detail_endpoint_serves_the_band(monkeypatch) -> None:
    row = _pvo_row(engine_path="BLEND_AB")
    row["dvs_engine"] = "blend"
    row["valuation"].update({"dvs_band_low": 30.1, "dvs_band_high": 97.5})
    client = _client(monkeypatch, pvo=_pvo(row), divergence=_divergence())

    data = client.get("/api/players/13269").json()

    assert data["model"]["engine_path"] == "BLEND_AB"
    assert data["model"]["dvs_engine"] == "blend"
    band = (data["model"]["dvs_band_low"], data["model"]["dvs_band_high"])
    assert band == (30.1, 97.5)
