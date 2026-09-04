"""DG-137 — the served NFL team is Sleeper's current team, not the model's.

A PVO carries ``nfl_team`` from the FEATURE season the model scored (2025), so a
player cut, traded or signed since then was served with a stale team; and a player
Sleeper now lists with no team was served the team he last played for. Three seams
pin the rule:

* the universe batch builder — Sleeper's snapshot team wins whenever it spoke
  (``None`` included); the PVO team is only a fallback when the snapshot row has
  no ``team`` key at all;
* the roster audit — the same rule, with the live Sleeper roster row as the
  authority over the artifact's team;
* the player-detail route — a player Sleeper lists as active with no NFL team is
  served ``"FA"`` (the roster audit's convention) instead of a blank; an inactive
  player with no team keeps the blank, because "free agent" is not a claim the
  data makes about him.

No valuation, band or projection field is touched.
"""
from __future__ import annotations

from app.services.roster_auditor import _pvo_from_universe_row
from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch
from tests.contract.test_roster_audit_pvo import _universe_row_for_rookie
from tests.contract.test_surface3_player_detail_endpoint import (
    _client,
    _divergence,
    _pvo,
    _pvo_row,
)


# ── universe batch builder ──────────────────────────────────────────────────
def _snapshot(*players: dict) -> dict:
    return {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-09-01T13:00:43+00:00",
        "players": list(players),
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }


def _snapshot_player(sleeper_id: str, player: dict) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "cohort": "FANTASY_RELEVANT",
        "identity_status": "sleeper_resolved",
        "player": player,
        "league_context": {"rostered": False, "roster_id": None},
    }


def _engine_b_pvo(sleeper_id: str, *, nfl_team: str) -> dict:
    return {
        "sleeper_id": sleeper_id,
        "player_id": f"00-000{sleeper_id}",
        "full_name": "Active One",
        "position": "WR",
        "nfl_team": nfl_team,
        "model_grade": "ACTIVE_B",
        "dynasty_value_score": 72.0,
        "xvar": 8.5,
        "dvs_engine": "B",
        "decision_supported": False,
        "market_overlay": None,
    }


def _served(batch: dict, sleeper_id: str) -> dict:
    return next(row for row in batch["players"] if row["sleeper_player_id"] == sleeper_id)


def test_batch_serves_sleepers_team_when_it_disagrees_with_the_model():
    """Traded since the feature season: Sleeper says JAX, the 2025 PVO says WAS."""
    snapshot = _snapshot(
        _snapshot_player(
            "202",
            {"full_name": "Active One", "position": "WR", "team": "JAX", "sleeper_status": "Active"},
        )
    )
    batch = build_universe_pvo_batch(
        snapshot, active_pvos=[_engine_b_pvo("202", nfl_team="WAS")], captured_at="2026-09-01T13:00:44+00:00"
    )
    row = _served(batch, "202")
    assert row["player"]["team"] == "JAX"
    assert row["valuation"]["engine_path"] == "ENGINE_B"
    assert row["valuation"]["dynasty_value_score"] == 72.0


def test_batch_serves_no_team_when_sleeper_says_no_team():
    """Cut since the feature season: Sleeper carries the team key with ``None``; the
    2025 PVO still says ARI. ``None`` is Sleeper speaking — do not fall back."""
    snapshot = _snapshot(
        _snapshot_player(
            "303",
            {"full_name": "Active One", "position": "WR", "team": None, "sleeper_status": "Active"},
        )
    )
    batch = build_universe_pvo_batch(
        snapshot, active_pvos=[_engine_b_pvo("303", nfl_team="ARI")], captured_at="2026-09-01T13:00:44+00:00"
    )
    assert _served(batch, "303")["player"]["team"] is None


def test_batch_falls_back_to_the_model_team_only_when_the_snapshot_never_spoke():
    """A snapshot row with no ``team`` key at all is the only case the PVO team fills."""
    snapshot = _snapshot(
        _snapshot_player("404", {"full_name": "Active One", "position": "WR", "sleeper_status": "Active"})
    )
    batch = build_universe_pvo_batch(
        snapshot, active_pvos=[_engine_b_pvo("404", nfl_team="ARI")], captured_at="2026-09-01T13:00:44+00:00"
    )
    assert _served(batch, "404")["player"]["team"] == "ARI"


def test_batch_reads_an_empty_sleeper_team_as_no_team():
    snapshot = _snapshot(
        _snapshot_player(
            "606", {"full_name": "Active One", "position": "WR", "team": "", "sleeper_status": "Active"}
        )
    )
    batch = build_universe_pvo_batch(
        snapshot, active_pvos=[_engine_b_pvo("606", nfl_team="ARI")], captured_at="2026-09-01T13:00:44+00:00"
    )
    assert _served(batch, "606")["player"]["team"] is None


def test_batch_keeps_sleepers_team_for_a_player_without_a_pvo():
    """PRE_MODEL players never had a PVO team; nothing changes for them."""
    snapshot = _snapshot(
        _snapshot_player(
            "505", {"full_name": "Rookie One", "position": "TE", "team": "DAL", "sleeper_status": "Active"}
        )
    )
    batch = build_universe_pvo_batch(snapshot, captured_at="2026-09-01T13:00:44+00:00")
    row = _served(batch, "505")
    assert row["player"]["team"] == "DAL"
    assert row["valuation"]["engine_path"] == "PRE_MODEL"


# ── roster audit ────────────────────────────────────────────────────────────
def test_roster_audit_prefers_the_live_sleeper_team_over_the_artifacts():
    row = _universe_row_for_rookie()  # artifact says "SFO"
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 24, "team": "KC"}
    assert _pvo_from_universe_row(row, live_player, provenance=None).nfl_team == "KC"


def test_roster_audit_serves_fa_from_the_live_roster_row_not_the_artifacts_team():
    row = _universe_row_for_rookie()  # artifact says "SFO"
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 24, "team": "FA"}
    assert _pvo_from_universe_row(row, live_player, provenance=None).nfl_team == "FA"


def test_roster_audit_serves_no_team_when_the_live_row_says_no_team():
    """A raw Sleeper row with ``team: None`` is Sleeper speaking — never the artifact's."""
    row = _universe_row_for_rookie()  # artifact says "SFO"
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 24, "team": None}
    assert _pvo_from_universe_row(row, live_player, provenance=None).nfl_team is None


def test_roster_audit_falls_back_to_the_artifacts_team_only_when_live_never_spoke():
    row = _universe_row_for_rookie()
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 24}
    assert _pvo_from_universe_row(row, live_player, provenance=None).nfl_team == "SFO"


# ── player-detail route ─────────────────────────────────────────────────────
def test_player_detail_serves_the_fact_for_an_active_player_with_no_team(monkeypatch):
    """DG-149 (David 2026-09-04 07:35 ET: the FA tag on every player with no NFL
    team): the route serves Sleeper's fact — no team — for Active and Inactive
    alike; the word "FA" is the frontend's, minted once. This used to serve "FA"
    for Active only (DG-137's call, overruled)."""
    row = _pvo_row()
    row["player"]["team"] = None
    assert row["player"]["sleeper_status"] == "Active"
    client = _client(monkeypatch, pvo=_pvo(row), divergence=_divergence())

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    assert response.json()["identity"]["team"] is None


def test_player_detail_keeps_the_blank_for_an_inactive_player_with_no_team(monkeypatch):
    row = _pvo_row(engine_path="INACTIVE")
    row["player"]["team"] = None
    row["player"]["sleeper_status"] = "Inactive"
    client = _client(monkeypatch, pvo=_pvo(row), divergence=_divergence())

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    assert response.json()["identity"]["team"] is None


def test_player_detail_serves_the_artifacts_team_when_it_has_one(monkeypatch):
    client = _client(monkeypatch, pvo=_pvo(_pvo_row()), divergence=_divergence())

    response = client.get("/api/players/13269")

    assert response.status_code == 200
    assert response.json()["identity"]["team"] == "LVR"
