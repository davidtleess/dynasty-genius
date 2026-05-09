from pathlib import Path

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo, assemble_roster_audit


ROOT = Path(__file__).resolve().parents[1]


def test_assemble_pvo_includes_local_roster_audit_without_market_overlay():
    identity = PlayerIdentity(
        dg_id="christian_mccaffrey_rb_1996",
        full_name="Christian McCaffrey",
        position="RB",
        nfl_team="SF",
        verification_status="VERIFIED",
    )
    features = {
        "age": 29,
        "internal_value": 72.5,
        "ktc_market_value": 9999,
        "snap_share": 0.62,
        "target_share": 0.14,
        "breakaway_run_pct": 0.08,
        "run_blocking_grade": 71.0,
    }

    pvo = assemble_pvo(
        identity,
        features,
        roster_context={"has_2026_2nd": False, "has_2027_2nd": True},
    )
    card = pvo.model_dump()

    assert card["model_grade"] == "PRE_MODEL"
    assert card["dynasty_value_score"] is None
    assert card["market_overlay"] is None
    assert card["signal_completeness"] == 1.0
    assert card["roster_audit"]["age_cliff_risk"] == 1.0
    assert card["roster_audit"]["biological_debt_score"] == 72.5
    assert card["roster_audit"]["liquidity_risk"] == "MEDIUM_LIMITED_ESCAPE_HATCH"
    assert "ktc_market_value" not in str(card["roster_audit"])


def test_assemble_roster_audit_mock_cards_are_pre_model_and_caveated():
    cards = assemble_roster_audit(
        ROOT / "resources/mock_playerprofiler_identity.json",
        features_by_dg_id={
            "christian_mccaffrey_rb_1996": {
                "internal_value": 72.5,
                "snap_share": 0.62,
                "target_share": 0.14,
                "breakaway_run_pct": 0.08,
                "run_blocking_grade": 71.0,
            }
        },
        roster_context={"has_2026_2nd": False, "has_2027_2nd": False},
    )

    assert len(cards) == 18
    assert all(card["model_grade"] == "PRE_MODEL" for card in cards)
    assert all(card["market_overlay"] is None for card in cards)

    cmc = next(card for card in cards if card["player_id"] == "christian_mccaffrey_rb_1996")
    assert cmc["roster_audit"]["liquidity_risk"] == "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"
    assert cmc["roster_audit"]["biological_debt_score"] is not None
    assert "identity_snapshot_date" in cmc["source_versions"]
