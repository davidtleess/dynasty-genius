"""Build live Roster Audit cards from David's real Sleeper roster.

Fetches the live roster, assembles a PVO per player (with real age data so
biological debt and cliff signals are non-null), writes the cards JSON, and
re-injects it into the Roster Audit dashboard HTML.

Usage:
    python3 scripts/build_live_roster.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.services.roster_auditor import get_my_roster, RosterConfigError
from src.dynasty_genius.identity import generate_dg_id
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo

DASHBOARD_HTML = ROOT / "src" / "dynasty_genius" / "dashboard" / "roster_audit.html"
CARDS_OUTPUT   = ROOT / "resources" / "live_roster_cards.json"


def _build_cards(players: list[dict]) -> list[dict]:
    cards = []
    for p in players:
        identity = PlayerIdentity(
            dg_id=generate_dg_id(p["full_name"], p["position"]),
            full_name=p["full_name"],
            position=p["position"],
            nfl_team=p.get("team"),
            age=None,
        )
        features = {"age": float(p["age"]) if p.get("age") is not None else None}
        pvo = assemble_pvo(identity, features, is_prospect=False)
        cards.append(pvo.model_dump())
    return cards


def _inject_into_dashboard(cards: list[dict]) -> None:
    html = DASHBOARD_HTML.read_text()
    new_line = "const CARDS = " + json.dumps(cards, separators=(",", ":")) + ";"
    html = re.sub(r"const CARDS = \[.*?\];", lambda _: new_line, html, flags=re.DOTALL)
    DASHBOARD_HTML.write_text(html)


async def main() -> None:
    print("Fetching roster from Sleeper…")
    try:
        players = await get_my_roster()
    except RosterConfigError as e:
        print(f"Config error: {e}")
        sys.exit(1)

    print(f"Fetched {len(players)} players. Assembling PVOs…")
    cards = _build_cards(players)

    CARDS_OUTPUT.write_text(json.dumps(cards, indent=2))
    print(f"Wrote {len(cards)} cards → {CARDS_OUTPUT.relative_to(ROOT)}")

    _inject_into_dashboard(cards)
    print(f"Injected into dashboard → {DASHBOARD_HTML.relative_to(ROOT)}")

    print(f"\n{'Player':<28} {'Pos':<4} {'Age':>4}  {'Cliff Status':<18}  Completeness")
    print("-" * 72)
    for c in sorted(cards, key=lambda x: x.get("roster_audit", {}).get("years_to_cliff", 99) or 99):
        ra = c.get("roster_audit") or {}
        cliff = ra.get("signal", "—").replace("_", " ")
        age_str = str(int(c["age"])) if c.get("age") is not None else "—"
        print(
            f"{c['full_name']:<28} {c['position']:<4} {age_str:>4}  "
            f"{cliff:<18}  {c['signal_completeness']:.0%}"
        )


if __name__ == "__main__":
    asyncio.run(main())
