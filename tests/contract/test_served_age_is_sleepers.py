"""DG-139 — the served age is Sleeper's current age, not the model's.

A PVO carries ``age`` from the FEATURE season the model scored (2025), so every
modeled player was served a year young once the new season began — and the roster
audit's age-cliff lane, which already reads the live Sleeper row, disagreed with the
age printed beside it on the same row. Two seams pin the rule:

* the universe batch builder — Sleeper's snapshot age wins whenever it has one; the
  PVO age fills only a snapshot row with no age (unknown, not "no age now");
* the roster audit — the same rule with the live Sleeper roster row as the authority,
  so the served age and the cliff distance come from the same number.

No valuation, band or projection field is touched; the feature table's age is the
model's and stays.
"""
from __future__ import annotations

from app.services.roster_auditor import CLIFF_AGES, _pvo_from_universe_row, audit_player
from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch, served_age
from tests.contract.test_roster_audit_pvo import _universe_row_for_rookie
from tests.contract.test_served_team_is_sleepers import (
    _engine_b_pvo,
    _served,
    _snapshot,
    _snapshot_player,
)

CAPTURED_AT = "2026-09-02T13:00:44+00:00"


# ── the rule itself ─────────────────────────────────────────────────────────
def test_served_age_prefers_sleepers_and_falls_back_only_when_sleeper_has_none():
    assert served_age({"age": 26}, 25.0) == 26
    assert served_age({"age": None}, 25.0) == 25.0
    assert served_age({}, 25.0) == 25.0
    assert served_age({}, None) is None


# ── universe batch builder ──────────────────────────────────────────────────
def _pvo_aged(sleeper_id: str, age: float) -> dict:
    return {**_engine_b_pvo(sleeper_id, nfl_team="NYJ"), "age": age}


def test_batch_serves_sleepers_age_when_the_model_is_a_season_behind():
    """Garrett Wilson: the 2025 feature row says 25.0, Sleeper says 26 today."""
    snapshot = _snapshot(
        _snapshot_player(
            "8146",
            {"full_name": "Garrett Wilson", "position": "WR", "team": "NYJ", "age": 26, "sleeper_status": "Active"},
        )
    )
    batch = build_universe_pvo_batch(snapshot, active_pvos=[_pvo_aged("8146", 25.0)], captured_at=CAPTURED_AT)
    row = _served(batch, "8146")
    assert row["player"]["age"] == 26
    assert row["valuation"]["engine_path"] == "ENGINE_B"
    assert row["valuation"]["dynasty_value_score"] == 72.0  # the value did not move


def test_batch_falls_back_to_the_model_age_when_sleeper_has_none():
    snapshot = _snapshot(
        _snapshot_player(
            "8147", {"full_name": "Active One", "position": "WR", "team": "NYJ", "age": None, "sleeper_status": "Active"}
        )
    )
    batch = build_universe_pvo_batch(snapshot, active_pvos=[_pvo_aged("8147", 25.0)], captured_at=CAPTURED_AT)
    assert _served(batch, "8147")["player"]["age"] == 25.0


def test_batch_falls_back_to_the_model_age_when_the_snapshot_never_spoke():
    snapshot = _snapshot(
        _snapshot_player("8148", {"full_name": "Active One", "position": "WR", "team": "NYJ", "sleeper_status": "Active"})
    )
    batch = build_universe_pvo_batch(snapshot, active_pvos=[_pvo_aged("8148", 25.0)], captured_at=CAPTURED_AT)
    assert _served(batch, "8148")["player"]["age"] == 25.0


def test_batch_keeps_sleepers_age_for_a_player_without_a_pvo():
    """PRE_MODEL players never had a PVO age; nothing changes for them."""
    snapshot = _snapshot(
        _snapshot_player(
            "9502", {"full_name": "Tank Dell", "position": "WR", "team": "HOU", "age": 26, "sleeper_status": "Inactive"}
        )
    )
    batch = build_universe_pvo_batch(snapshot, captured_at=CAPTURED_AT)
    row = _served(batch, "9502")
    assert row["player"]["age"] == 26
    assert row["valuation"]["engine_path"] == "PRE_MODEL"


# ── roster audit ────────────────────────────────────────────────────────────
def test_roster_audit_prefers_the_live_sleeper_age_over_the_artifacts():
    row = _universe_row_for_rookie()  # artifact says 24.0
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 25, "team": "SF"}
    assert _pvo_from_universe_row(row, live_player, provenance=None).age == 25


def test_roster_audit_falls_back_to_the_artifacts_age_only_when_live_has_none():
    row = _universe_row_for_rookie()  # artifact says 24.0
    live_player = {"full_name": "Kaelon Black", "position": "RB", "team": "SF"}
    assert _pvo_from_universe_row(row, live_player, provenance=None).age == 24.0


def test_roster_row_age_and_cliff_distance_come_from_the_same_number():
    """Wilson's row read "age 25" beside "2 years to the 28 cliff" — the cliff lane
    already used the live age. After DG-139 the printed age is the one the cliff
    lane used, so the row can no longer contradict itself."""
    row = _universe_row_for_rookie()
    row["player"]["position"] = "WR"
    row["player"]["age"] = 25.0
    live_player = {"full_name": "Garrett Wilson", "position": "WR", "age": 26, "team": "NYJ"}
    served = _pvo_from_universe_row(row, live_player, provenance=None).age
    audited = audit_player(live_player)
    assert served == 26
    assert audited is not None
    assert audited["years_to_cliff"] == CLIFF_AGES["WR"] - served
