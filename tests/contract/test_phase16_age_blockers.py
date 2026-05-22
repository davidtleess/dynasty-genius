"""Phase 16.1 age-blocker resolution contract tests."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITY_FILE = ROOT / "resources" / "prospect_identity_2026.json"
CARDS_FILE = ROOT / "resources" / "prospect_cards.json"

_BLOCKER_NAMES = {
    "Omar Cooper Jr.",
    "Chris Brazzell II",
    "Mike Washington Jr.",
    "Kevin Coleman Jr.",
    "Emmanuel Henderson Jr.",
    "Jam Miller",
}

_BLOCKER_SLEEPER_IDS = {
    "Omar Cooper Jr.": "13276",
    "Chris Brazzell II": "13353",
    "Mike Washington Jr.": "13305",
    "Kevin Coleman Jr.": "13338",
    "Emmanuel Henderson Jr.": "13313",
    "Jam Miller": "13403",
}

_AGE_RANGE = (20, 26)


def _load_identity_data() -> dict:
    with open(IDENTITY_FILE) as f:
        return json.load(f)


def _load_identity_players() -> list[dict]:
    return _load_identity_data()["players"]


def _load_cards() -> list[dict]:
    with open(CARDS_FILE) as f:
        return json.load(f)


class TestIdentityFile:
    def test_all_six_have_birth_date(self) -> None:
        players = _load_identity_players()
        blockers = {p["full_name"]: p for p in players if p["full_name"] in _BLOCKER_NAMES}
        assert len(blockers) == 6
        for name, player in blockers.items():
            assert player.get("birth_date") is not None, f"{name} still has null birth_date"

    def test_all_six_age_verified_true(self) -> None:
        players = _load_identity_players()
        blockers = {p["full_name"]: p for p in players if p["full_name"] in _BLOCKER_NAMES}
        assert len(blockers) == 6
        for name, player in blockers.items():
            assert player.get("age_verified") is True, f"{name} age_verified is not True"

    def test_washington_conflict_logged(self) -> None:
        players = _load_identity_players()
        player = next(p for p in players if p["full_name"] == "Mike Washington Jr.")
        assert player.get("dob_conflict_source")
        assert "lines.com" in player["dob_conflict_source"].lower()

    def test_coleman_conflict_logged(self) -> None:
        players = _load_identity_players()
        player = next(p for p in players if p["full_name"] == "Kevin Coleman Jr.")
        assert player.get("dob_conflict_source")
        assert "nfldraftbuzz" in player["dob_conflict_source"].lower()

    def test_birth_dates_in_valid_age_range(self) -> None:
        data = _load_identity_data()
        ref = date.fromisoformat(data.get("snapshot_date", "2026-05-09"))
        blockers = [p for p in data["players"] if p["full_name"] in _BLOCKER_NAMES]
        assert len(blockers) == 6
        for player in blockers:
            birth = date.fromisoformat(player["birth_date"])
            age = (ref - birth).days / 365.25
            assert _AGE_RANGE[0] <= age <= _AGE_RANGE[1], (
                f"{player['full_name']}: computed age {age:.2f} outside valid range {_AGE_RANGE}"
            )


class TestProspectCards:
    def test_zero_pre_model_among_blockers(self) -> None:
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6
        for card in blocker_cards:
            assert card.get("model_grade") != "PRE_MODEL", (
                f"{card['full_name']} still PRE_MODEL after refresh"
            )

    def test_all_six_have_dvs(self) -> None:
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6
        for card in blocker_cards:
            assert card.get("dynasty_value_score") is not None, (
                f"{card['full_name']} has null DVS after refresh"
            )

    def test_all_six_have_xvar(self) -> None:
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6
        for card in blocker_cards:
            assert card.get("xvar") is not None, f"{card['full_name']} has null xvar"

    def test_all_six_have_xvar_class_rank(self) -> None:
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6
        for card in blocker_cards:
            assert card.get("xvar_class_rank") is not None, (
                f"{card['full_name']} missing xvar_class_rank"
            )

    def test_fractional_ages_in_valid_range(self) -> None:
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6
        for card in blocker_cards:
            age = card.get("age")
            assert age is not None, f"{card['full_name']} has null age"
            assert _AGE_RANGE[0] <= age <= _AGE_RANGE[1], (
                f"{card['full_name']}: age {age} outside valid range {_AGE_RANGE}"
            )

    def test_sleeper_ids_preserved(self) -> None:
        cards = _load_cards()
        blocker_cards = {c["full_name"]: c for c in cards if c["full_name"] in _BLOCKER_NAMES}
        assert len(blocker_cards) == 6
        for name, expected_id in _BLOCKER_SLEEPER_IDS.items():
            card = blocker_cards.get(name)
            assert card is not None
            assert str(card.get("sleeper_id", "")) == expected_id

    def test_model_grade_prospect_c_for_non_qb(self) -> None:
        cards = _load_cards()
        non_qb_blockers = [
            c
            for c in cards
            if c.get("full_name") in _BLOCKER_NAMES and c.get("position") != "QB"
        ]
        assert len(non_qb_blockers) == 6
        for card in non_qb_blockers:
            assert card.get("model_grade") == "PROSPECT_C", (
                f"{card['full_name']} ({card.get('position')}): "
                f"expected PROSPECT_C, got {card.get('model_grade')}"
            )

    def test_dvs_invariance_existing_scored_players(self) -> None:
        cards = _load_cards()
        scored_non_blocker = [
            c
            for c in cards
            if c.get("dynasty_value_score") is not None
            and c.get("draft_class") == 2026
            and c.get("full_name") not in _BLOCKER_NAMES
        ]
        assert len(scored_non_blocker) == 74
