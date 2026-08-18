"""RED — the DVS ceiling must be disclosed on the surface it ships to.

`00-product-constitution.md` §No-Verdict Line: "Surface the arithmetic honestly,
unclamped... Tightening, clamping, banding, or editorializing a number into a
recommendation is the failure mode this line prevents."

`PlayerValueObject` already defines the two disclosure fields
(`dvs_clamped`, `dvs_p90_ref`) and `pvo_assembler` already computes them, but the
universe batch serializer drops both — so a player whose raw DVS exceeded 100
ships as a bare 100.0 with nothing saying it was truncated. Measured 2026-08-18 on
the served artifact: 23 players sit at exactly 100.0 (RB 6, WR 6, TE 11) and zero
rows carry `dvs_clamped`; McCaffrey's raw DVS is 120.1.

These contracts pin the disclosure, not the valuation design. The ceiling itself is
a separate, David-gated question.
"""
from __future__ import annotations

from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch

CLAMPED_PVO = {
    "sleeper_id": "202",
    "player_id": "00-0000202",
    "full_name": "Active One",
    "position": "RB",
    "model_grade": "ACTIVE_B",
    "dynasty_value_score": 100.0,
    "dvs_clamped": True,
    "dvs_p90_ref": 15.7,
    "xvar": 8.5,
    "dvs_pct": 99.0,
    "dvs_engine": "B",
    "decision_supported": False,
    "market_overlay": None,
}

UNCLAMPED_PVO = {
    "sleeper_id": "101",
    "player_id": "rookie_one_wr_2004",
    "full_name": "Rookie One",
    "position": "WR",
    "model_grade": "PROSPECT_C",
    "dynasty_value_score": 88.0,
    "dvs_clamped": False,
    "dvs_p90_ref": 14.5,
    "xvar": 12.5,
    "dvs_engine": "A",
    "decision_supported": False,
    "market_overlay": None,
}


def _snapshot() -> dict:
    return {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-08-18T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "101",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Rookie One", "position": "WR", "team": "NYG"},
                "league_context": {"rostered": True, "roster_id": 1},
            },
            {
                "sleeper_player_id": "202",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Active One", "position": "RB", "team": "KC"},
                "league_context": {"rostered": True, "roster_id": 2},
            },
            {
                "sleeper_player_id": "303",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Unknown One", "position": "TE", "team": "FA"},
                "league_context": {"rostered": True, "roster_id": 3},
            },
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }


def _batch() -> dict[str, dict]:
    batch = build_universe_pvo_batch(
        _snapshot(),
        prospect_pvos=[dict(UNCLAMPED_PVO)],
        active_pvos=[dict(CLAMPED_PVO)],
        captured_at="2026-08-18T00:00:01+00:00",
    )
    return {row["sleeper_player_id"]: row for row in batch["players"]}


def test_clamped_player_discloses_dvs_clamped_true() -> None:
    """A player whose raw DVS exceeded the ceiling must say so on the surface."""
    assert _batch()["202"]["valuation"]["dvs_clamped"] is True


def test_clamped_player_discloses_the_p90_reference_that_produced_the_score() -> None:
    """The denominator is what makes 100.0 interpretable; ship it with the score."""
    assert _batch()["202"]["valuation"]["dvs_p90_ref"] == 15.7


def test_unclamped_player_discloses_dvs_clamped_false_not_missing() -> None:
    """False and absent are different claims: absent hides whether the check ran."""
    valuation = _batch()["101"]["valuation"]
    assert "dvs_clamped" in valuation
    assert valuation["dvs_clamped"] is False


def test_unscored_player_carries_the_disclosure_keys_as_null() -> None:
    """Schema stability: every row exposes the keys, unscored rows carry null."""
    valuation = _batch()["303"]["valuation"]
    assert valuation["dvs_clamped"] is None
    assert valuation["dvs_p90_ref"] is None


def test_disclosure_never_alters_the_shipped_score_or_decision_flag() -> None:
    """This is a disclosure change only — the valuation itself must not move."""
    rows = _batch()
    assert rows["202"]["valuation"]["dynasty_value_score"] == 100.0
    assert rows["101"]["valuation"]["dynasty_value_score"] == 88.0
    assert all(
        row["valuation"]["decision_supported"] is False for row in rows.values()
    )
