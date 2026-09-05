"""DG-143 — a player who missed most of a season still gets the model's estimate.

David's ruling 2026-09-03, option A of a written either/or: drop the season-games
gate from 8 to 4. His reason, verbatim: "the model is always making its genuine
estimate". 114 players were refused a 0-100 value while the pipeline had already
produced a two-year projection for every one of them.

The absence was never unpriced — the served value is P(plays) x E[points | plays],
and on the live 2025 population the 4-7 game cohort averages P(plays) 0.488
against 0.847 for 8+ game players. The gate withheld the number, not the discount.

Attached language ruling, David 2026-09-03 verbatim: "no 'partial season' lang".
The number ships bare. These tests must never grow an assertion about explanatory
copy for this cohort.
"""
from __future__ import annotations

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_MIN_GAMES_T,
    DVS_SCALE_ANCHOR_PPG,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import apply_availability, assemble_pvo


def _identity(position: str) -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="00-0037740",
        full_name="Short Season",
        position=position,
        verification_status="VERIFIED_NFL_DRAFT",
    )


def test_the_gate_is_four_because_david_ruled_it():
    """A guard on the ruling itself: 8 refused 114 players the model had scored."""
    assert ENGINE_B_MIN_GAMES_T == 4


def test_a_seven_game_receiver_is_served_a_number():
    """Garrett Wilson's shape. At the old gate of 8 this row served None."""
    pvo = assemble_pvo(
        _identity("WR"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 11.233, "engine": "test_v2"},
            "games_t": 7,
            "availability_p": 0.885,
            "feature_season": 2025,
        },
    )
    assert pvo.dynasty_value_score is not None
    assert pvo.dvs_engine == "B", "the pure Engine B lane, not the blend"
    expected = round(
        min(100.0, max(0.0, apply_availability(11.233, 0.885) / DVS_SCALE_ANCHOR_PPG["WR"] * 100.0)),
        1,
    )
    assert pvo.dynasty_value_score == expected


def test_the_availability_discount_is_still_applied_to_him():
    """The number must be the DISCOUNTED one — ungating must not smuggle in a raw score."""
    common = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": 11.233, "engine": "test_v2"},
        "games_t": 7,
        "feature_season": 2025,
    }
    discounted = assemble_pvo(_identity("WR"), {**common, "availability_p": 0.885})
    undiscounted = assemble_pvo(_identity("WR"), {**common, "availability_p": 1.0})
    assert discounted.dynasty_value_score < undiscounted.dynasty_value_score


def test_a_four_game_player_is_at_the_boundary_and_is_served():
    """4 is IN. Braelon Allen's shape — a backup who was also hurt."""
    pvo = assemble_pvo(
        _identity("RB"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 4.893, "engine": "test_v2"},
            "games_t": ENGINE_B_MIN_GAMES_T,
            "availability_p": 0.657,
            "feature_season": 2025,
        },
    )
    assert pvo.dynasty_value_score is not None
    assert pvo.dvs_engine == "B"


def test_below_the_gate_is_still_refused_without_an_engine_a_prior():
    """The dead window did not disappear; it moved. Three games and no prior -> no number.

    This is the branch Tank Dell-shaped players and true rookies-without-priors fall
    into, and it must keep refusing rather than inventing a value from one game.
    """
    pvo = assemble_pvo(
        _identity("WR"),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": 12.0, "engine": "test_v2"},
            "games_t": ENGINE_B_MIN_GAMES_T - 1,
            "feature_season": 2025,
        },
    )
    assert pvo.dynasty_value_score is None
    assert pvo.dvs_engine is None
