"""Static guardrails for SQL decision-surface wording."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SQL_SURFACES = [
    ROOT / "resources" / "gold_roster_valuation.sql",
    ROOT / "resources" / "opponent_fragility_lens.sql",
    ROOT / "resources" / "leaguemate_fragility_index.sql",
    ROOT / "resources" / "model_accuracy_dashboard.sql",
    ROOT / "resources" / "alpha_divergence_weekly_report.sql",
]

BANNED_SQL_TERMS = re.compile(
    r"\b("
    r"SELL_HIGH|SHOP_FOR|BUY_OR_HOLD|HOLD_MONITOR|HIGH_LIQUIDATE|"
    r"LIQUIDATION_TARGET|great_liquidation|liquidation_action|"
    r"acquisition_action|ACQUIRE_|NO_ACTION|NO_TARGET_PICK|"
    r"DO_NOT_OVERPAY|REQUIRE_KICKER|PRIORITY_SHORT"
    r")\b",
    re.IGNORECASE,
)


def test_sql_surfaces_use_neutral_signal_language():
    hits: list[str] = []
    for path in SQL_SURFACES:
        text = path.read_text()
        for match in BANNED_SQL_TERMS.finditer(text):
            hits.append(f"{path.relative_to(ROOT)}:{match.group(0)}")

    assert not hits
