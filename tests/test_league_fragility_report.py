"""Contract tests for the pre-model opponent fragility lens."""

from __future__ import annotations

import json
import re
import sys
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "resources" / "league_fragility_report.json"

BANNED_DIRECTIVE_WORDS = re.compile(
    r"\b(recommendation|target for liquidation|forced seller|forced sellers|sell_high|"
    r"sell high|liquidate|liquidation action|acquisition_action|monitor)\b",
    re.IGNORECASE,
)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def test_league_fragility_report_uses_signal_contract():
    report = json.loads(REPORT_PATH.read_text())

    assert report
    for team in report:
        assert "recommendation" not in team
        assert "fragility_status" in team
        assert "opportunity_type" in team
        assert "why_flagged" in team
        assert team["decision_supported"] is False
        assert team["required_before_action"]


def test_league_fragility_report_has_no_directive_language():
    report = json.loads(REPORT_PATH.read_text())
    hits = [text for text in _walk_strings(report) if BANNED_DIRECTIVE_WORDS.search(text)]
    assert not hits


def test_live_roster_fetch_uses_explicit_future_first_inventory(monkeypatch):
    import app.data.sleeper as sleeper
    from scripts import generate_league_audit

    monkeypatch.setenv("DYNASTY_SLEEPER_LEAGUE_ID", "league-1")
    monkeypatch.setenv("DYNASTY_SEASON", "2026")

    async def fake_rosters(league_id: str) -> list[dict]:
        assert league_id == "league-1"
        return [{"roster_id": 1, "owner_id": "u1", "players": ["p1"]}]

    async def fake_users(league_id: str) -> list[dict]:
        return [{"user_id": "u1", "display_name": "Owner One"}]

    async def fake_players() -> dict[str, dict]:
        return {
            "p1": {
                "first_name": "Roster",
                "last_name": "Player",
                "position": "WR",
                "age": 24,
            }
        }

    async def fake_traded_picks(league_id: str) -> list[dict]:
        return [
            {"season": "2027", "round": 1, "roster_id": 1, "owner_id": 99},
        ]

    monkeypatch.setattr(sleeper, "get_rosters", fake_rosters)
    monkeypatch.setattr(sleeper, "get_users", fake_users)
    monkeypatch.setattr(sleeper, "get_all_players", fake_players)
    monkeypatch.setattr(sleeper, "get_traded_picks", fake_traded_picks)

    teams = asyncio.run(generate_league_audit._fetch_live_rosters())

    assert teams[0]["future_first_round_picks"] == ["2028"]
    assert teams[0]["has_future_1st_liquidity"] is True
    assert "has_2026_1st" not in teams[0]
    assert "has_2027_1st" not in teams[0]
