"""Contract tests for the pre-model opponent fragility lens."""

from __future__ import annotations

import json
import re
import sys
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
