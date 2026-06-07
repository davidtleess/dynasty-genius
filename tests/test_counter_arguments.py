import json
import re
from pathlib import Path

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo

ROOT = Path(__file__).resolve().parents[1]
BANNED_VOCABULARY = json.loads(
    (ROOT / "frontend" / "src" / "shell" / "banned_vocabulary.json").read_text()
)
BANNED_STANDALONE_WORDS = set(BANNED_VOCABULARY["banned_standalone_words"])


def _assert_no_banned_standalone_words(text: str) -> None:
    for word in BANNED_STANDALONE_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is None


def test_counter_argument_age_cliff():
    identity = PlayerIdentity(
        dg_id="test_player_rb",
        full_name="Old RB",
        position="RB",
        nfl_team="FA"
    )
    # RB cliff is 26. Setting age to 27.
    features = {
        "age": 27,
        "snap_share": 0.50
    }
    pvo = assemble_pvo(identity, features)
    
    assert "age_past_position_cliff" in pvo.risk_flags
    assert pvo.counter_argument == (
        "Liquidity Caveat: Production may remain useful, but trade liquidity "
        "often narrows as a player moves past the historical age cliff."
    )

def test_counter_argument_low_snap_share():
    identity = PlayerIdentity(
        dg_id="test_player_wr",
        full_name="Low Snap WR",
        position="WR",
        nfl_team="FA"
    )
    features = {
        "age": 24,
        "snap_share": 0.35
    }
    pvo = assemble_pvo(identity, features)
    
    assert "snap_share_below_40pct" in pvo.risk_flags
    assert pvo.counter_argument == (
        "Usage Caveat: Sub-40% snap share at this stage of the season can "
        "signal limited coaching trust and a fragile path to weekly relevance."
    )

def test_counter_argument_top_asset_qb():
    identity = PlayerIdentity(
        dg_id="test_player_qb",
        full_name="Elite QB",
        position="QB",
        nfl_team="FA"
    )
    features = {
        "age": 25,
        "snap_share": 1.0,
        "dynasty_value_score": 85
    }
    pvo = assemble_pvo(identity, features)
    
    assert pvo.dynasty_value_score == 85
    assert (
        "Premium valuation assumes continued high-level rushing or outlier passing efficiency"
        in pvo.counter_argument
    )
    assert "dip in mobility or supporting cast" in pvo.counter_argument
    _assert_no_banned_standalone_words(pvo.counter_argument)


def test_counter_argument_top_asset_te():
    identity = PlayerIdentity(
        dg_id="test_player_te",
        full_name="Premium TE",
        position="TE",
        nfl_team="FA"
    )
    features = {
        "age": 25,
        "snap_share": 1.0,
        "dynasty_value_score": 85
    }
    pvo = assemble_pvo(identity, features)

    assert pvo.dynasty_value_score == 85
    assert "premium status is difficult to maintain" in pvo.counter_argument
    assert "TD-dependent" in pvo.counter_argument
    assert "target-earning wideouts or changes offensive schemes" in pvo.counter_argument
    _assert_no_banned_standalone_words(pvo.counter_argument)

def test_counter_argument_priority():
    # Age cliff should take priority over high value in my implementation
    identity = PlayerIdentity(
        dg_id="test_player_rb_top",
        full_name="Elite Old RB",
        position="RB",
        nfl_team="FA"
    )
    features = {
        "age": 27, # Past cliff
        "snap_share": 0.8,
        "dynasty_value_score": 90
    }
    pvo = assemble_pvo(identity, features)
    
    # Priority 1: Specific Risk Flags
    assert "age_past_position_cliff" in pvo.risk_flags
    assert "Liquidity Caveat" in pvo.counter_argument
