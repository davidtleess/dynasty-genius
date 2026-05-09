"""Generate a league-wide fragility lens using internal valuations.

This intentionally emits signals and caveats, not trade instructions. It is a
pre-model opponent context artifact until live rosters, pick inventory, and
valuation gates are verified.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.roster_auditor import roster_biological_debt

# Mock internal values (0-10000 scale)
PLAYER_VALUES = {
    'tyreek_hill_wr_1994': 8500,
    'davante_adams_wr_1992': 7800,
    'travis_kelce_te_1989': 7200,
    'jeremiah_smith_wr_2005': 9200,
    'arch_manning_qb_2005': 9500,
}

def _opportunity_type(status: str) -> str:
    if status == "FRAGILE":
        return "aging_asset_liquidity_pressure"
    if status == "DEBT_HEAVY":
        return "aging_asset_concentration"
    return "no_fragility_signal"


def _why_flagged(debt_ratio: float | None, has_liquidity: bool) -> list[str]:
    flags: list[str] = []
    if debt_ratio is not None and debt_ratio > 0.40:
        flags.append("biological_debt_ratio_above_40pct")
    if not has_liquidity:
        flags.append("limited_first_round_pick_liquidity")
    if not flags:
        flags.append("no_current_fragility_signal")
    return flags


def generate_report():
    roster_path = ROOT / 'resources' / 'mock_league_rosters.json'
    
    with open(roster_path, 'r') as f:
        rosters = json.load(f)
        
    report = []
    for team in rosters:
        players = []
        for pid in team['players']:
            # Parse year and pos from ID
            parts = pid.split('_')
            pos = parts[2].upper()
            birth_year = int(parts[3])
            age = 2026 - birth_year
            
            players.append({
                'full_name': pid,
                'position': pos,
                'age': age,
                'internal_value': PLAYER_VALUES.get(pid, 500) # Default low value
            })
            
        debt = roster_biological_debt(players)
        
        # Liquidity Check
        has_liquidity = team.get('has_2026_1st', True) or team.get('has_2027_1st', True)
        
        status = "HEALTHY"
        if debt['biological_debt_ratio'] > 0.40 and not has_liquidity:
            status = "FRAGILE"
        elif debt['biological_debt_ratio'] > 0.40:
            status = "DEBT_HEAVY"
            
        report.append({
            'owner': team['display_name'],
            'debt_ratio': debt['biological_debt_ratio'],
            'total_value': debt['total_internal_roster_value'],
            'liquidity': 'HIGH' if has_liquidity else 'NONE',
            'fragility_status': status,
            'opportunity_type': _opportunity_type(status),
            'why_flagged': _why_flagged(debt['biological_debt_ratio'], has_liquidity),
            'decision_supported': False,
            'required_before_action': [
                'replace_mock_rosters_with_live_sleeper_snapshot',
                'verify_opponent_pick_inventory',
                'review_counter_argument',
                'confirm_market_overlay_remains_post_model_only',
            ],
        })
        
    output_path = ROOT / 'resources' / 'league_fragility_report.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    generate_report()
