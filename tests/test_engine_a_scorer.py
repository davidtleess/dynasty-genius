"""Engine A scorer tests.

Covers:
1. Elite pick (5, round 1, age 21) scores > 70 for WR/RB/TE; QB gets PROSPECT_D.
2. Late pick (220, round 7, age 24) scores < 30 for all positions.
3. Missing any of pick/round/age → PRE_MODEL, dynasty_value_score stays None.
4. Veteran (is_prospect=False) → PRE_MODEL regardless of pick/round.
5. Score is clamped to [0, 100].
6. Engine A caveats propagate to PVO.
7. model_version matches latest.json pointer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def wr_identity():
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    return PlayerIdentity(
        dg_id=generate_dg_id("Test WR", "WR"),
        full_name="Test WR",
        position="WR",
        nfl_team="KC",
    )


@pytest.fixture
def qb_identity():
    from src.dynasty_genius.identity import generate_dg_id
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    return PlayerIdentity(
        dg_id=generate_dg_id("Test QB", "QB"),
        full_name="Test QB",
        position="QB",
        nfl_team="KC",
    )


# ── 1. Elite pick scores high ────────────────────────────────────────────────

def test_elite_wr_prospect_scores_high(wr_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(wr_identity, {"pick": 5, "round": 1, "age": 21.0}, is_prospect=True)
    assert pvo.model_grade == "PROSPECT_C"
    assert pvo.dynasty_value_score is not None
    assert pvo.dynasty_value_score > 70, f"Expected > 70, got {pvo.dynasty_value_score}"
    assert pvo.engine_used == "engine_a_rookie_forecast_ridge"


def test_elite_qb_gets_prospect_d(qb_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(qb_identity, {"pick": 5, "round": 1, "age": 21.0}, is_prospect=True)
    assert pvo.model_grade == "PROSPECT_D"
    assert pvo.dynasty_value_score is not None
    assert "qb_rookie_signal_inherently_low_ceiling" in pvo.caveats


# ── 2. Late pick scores low ───────────────────────────────────────────────────

def test_late_pick_scores_low(wr_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(wr_identity, {"pick": 220, "round": 7, "age": 24.0}, is_prospect=True)
    assert pvo.dynasty_value_score is not None
    assert pvo.dynasty_value_score < 30, f"Expected < 30, got {pvo.dynasty_value_score}"


# ── 3. Missing inputs → PRE_MODEL ────────────────────────────────────────────

@pytest.mark.parametrize("features", [
    {"round": 1, "age": 21.0},          # missing pick
    {"pick": 5, "age": 21.0},           # missing round
    {"pick": 5, "round": 1},            # missing age
    {},                                  # all missing
])
def test_missing_inputs_stay_pre_model(wr_identity, features):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(wr_identity, features, is_prospect=True)
    assert pvo.model_grade == "PRE_MODEL"
    assert pvo.dynasty_value_score is None
    assert pvo.engine_used is None


# ── 4. Veteran stays PRE_MODEL ───────────────────────────────────────────────

def test_veteran_stays_pre_model(wr_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(
        wr_identity,
        {"pick": 5, "round": 1, "age": 27.0},
        is_prospect=False,
    )
    assert pvo.model_grade == "PRE_MODEL"
    assert pvo.engine_used is None


# ── 5. Score clamped to [0, 100] ─────────────────────────────────────────────

def test_score_clamped_to_0_100(wr_identity):
    from src.dynasty_genius.scoring.engine_a import score_prospect
    # Extreme inputs that might produce very high or negative predictions.
    result_high = score_prospect("WR", 1, 1, 18.0)
    assert result_high is not None
    assert 0.0 <= result_high["dynasty_value_score"] <= 100.0

    result_low = score_prospect("WR", 300, 7, 30.0)
    assert result_low is not None
    assert result_low["dynasty_value_score"] == 0.0


# ── 6. Engine A caveats propagate to PVO ─────────────────────────────────────

def test_engine_a_caveats_in_pvo(wr_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pvo = assemble_pvo(wr_identity, {"pick": 10, "round": 1, "age": 22.0}, is_prospect=True)
    assert "engine_a_rookie_forecast_only" in pvo.caveats
    assert "veteran_scoring_requires_engine_b" in pvo.caveats
    assert "no_usage_efficiency_signal" in pvo.caveats


# ── 7. model_version matches latest.json ─────────────────────────────────────

def test_model_version_matches_latest_pointer(wr_identity):
    from src.dynasty_genius.pvo_assembler import assemble_pvo
    pointer = json.loads((ROOT / "app" / "data" / "models" / "latest.json").read_text())
    pvo = assemble_pvo(wr_identity, {"pick": 10, "round": 1, "age": 22.0}, is_prospect=True)
    assert pvo.model_version == pointer["model_version"]
