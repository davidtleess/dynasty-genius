"""Tests for build_roster_need_signals.py — age cliff aggregation by position."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _card(position: str, years_to_cliff) -> dict:
    ra = None if years_to_cliff is None else {"years_to_cliff": years_to_cliff}
    return {"position": position, "roster_audit": ra}


def _classify(cards, position):
    from scripts.build_roster_need_signals import _classify_position
    return _classify_position(cards, position)


def test_high_when_two_players_past_cliff():
    cards = [_card("WR", -1), _card("WR", 0), _card("WR", 3)]
    assert _classify(cards, "WR") == "HIGH"


def test_medium_when_one_at_cliff():
    cards = [_card("RB", 0), _card("RB", 5)]
    assert _classify(cards, "RB") == "MEDIUM"


def test_medium_when_two_approaching():
    cards = [_card("TE", 1), _card("TE", 1), _card("TE", 3)]
    assert _classify(cards, "TE") == "MEDIUM"


def test_low_when_no_cliff_signals():
    cards = [_card("QB", 5), _card("QB", 8)]
    assert _classify(cards, "QB") == "LOW"


def test_low_when_no_roster_audit():
    cards = [_card("WR", None), _card("WR", None)]
    assert _classify(cards, "WR") == "LOW"


def test_low_when_no_players_at_position():
    cards = [_card("WR", 0)]
    assert _classify(cards, "QB") == "LOW"
