from pathlib import Path

from src.dynasty_genius.models.league_context import LeagueContext, DraftPick
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
        "ppg_t": 15.0,
        "games_t": 16,
        "snap_share": 0.62,
        "aging_curve_value": 1.0,
        "ppg_t_minus_1": 14.0,
        "ppg_t_minus_2": 13.0,
        "snap_share_t_minus_1": 0.65,
        "ppg_t_minus_1_available": True,
        "ppg_t_minus_2_available": True,
        "snap_share_t_minus_1_available": True,
    }

    # Liquidity risk: MEDIUM_LIMITED_ESCAPE_HATCH (has 2027 2nd, missing 2026 2nd)
    league_context = LeagueContext(
        league_id="1", league_name="N", season="2026",
        david_user_id="u", david_display_name="D", david_roster_id=1,
        my_future_picks=[DraftPick(year=2027, round=2)]
    )

    pvo = assemble_pvo(
        identity,
        features,
        league_context=league_context,
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
    # Liquidity risk: HIGH (missing both)
    league_context = LeagueContext(
        league_id="1", league_name="N", season="2026",
        david_user_id="u", david_display_name="D", david_roster_id=1,
        my_future_picks=[]
    )

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
        league_context=league_context,
    )

    assert len(cards) == 18
    assert all(card["model_grade"] == "PRE_MODEL" for card in cards)
    assert all(card["market_overlay"] is None for card in cards)

    cmc = next(card for card in cards if card["player_id"] == "christian_mccaffrey_rb_1996")
    assert cmc["roster_audit"]["liquidity_risk"] == "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"
    assert cmc["roster_audit"]["biological_debt_score"] is not None
    assert "identity_snapshot_date" in cmc["source_versions"]


def test_mock_prospect_pick_round_inputs_are_flagged():
    cards = assemble_roster_audit(ROOT / "resources/mock_prospect_identities_2026_2027.json")

    scored_cards = [card for card in cards if card["dynasty_value_score"] is not None]

    assert scored_cards
    assert all("mock_draft_capital_unverified" in card["risk_flags"] for card in scored_cards)


# ── Task 2: PVO identity field tests ──────────────────────────────────────────
import json
import tempfile


def _make_prospect_fixture(extra=None) -> dict:
    return {
        "source": "test",
        "snapshot_date": "2026-05-09",
        "players": [{
            "full_name": "Test Receiver",
            "position": "WR",
            "birth_date": "2003-01-01",
            "nfl_team": "DAL",
            "is_prospect": True,
            "draft_class": 2026,
            "pick": 15,
            "round": 1,
            "sleeper_id": "99999",
            "verification_status": "VERIFIED_NFL_DRAFT",
            "identity_verified": True,
            "age_verified": True,
            **(extra or {}),
        }]
    }


def _cards_from_fixture(fixture: dict) -> list[dict]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fixture, f)
        tmp = Path(f.name)
    try:
        return assemble_roster_audit(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def test_pvo_has_sleeper_id():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert cards[0]["sleeper_id"] == "99999"


def test_pvo_has_draft_class():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert cards[0]["draft_class"] == 2026


def test_pvo_has_nfl_draft_pick():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert cards[0]["nfl_draft_pick"] == 15


def test_pvo_has_nfl_draft_round():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert cards[0]["nfl_draft_round"] == 1


def test_pvo_decision_supported_is_false():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert cards[0]["decision_supported"] is False


def test_verified_prospect_no_unverified_flag():
    cards = _cards_from_fixture(_make_prospect_fixture())
    assert "mock_draft_capital_unverified" not in cards[0]["risk_flags"]


def test_unverified_prospect_carries_unverified_flag():
    fixture = _make_prospect_fixture({"verification_status": "PENDING", "identity_verified": False, "age_verified": False})
    cards = _cards_from_fixture(fixture)
    assert "mock_draft_capital_unverified" in cards[0]["risk_flags"]
