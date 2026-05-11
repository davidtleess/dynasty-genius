import re
import json
import os
from pathlib import Path
import pandas as pd
import sys
from dotenv import load_dotenv
import asyncio
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.dynasty_genius.models.engine_a_contract import PROHIBITED_COLUMNS, LEAKAGE_REGEX

CFBD_CACHE_PATH = ROOT / "app" / "data" / "cache" / "cfbd_cache.json"
CFBD_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

def check_leakage(df: pd.DataFrame):
    prohibited_regex = re.compile(LEAKAGE_REGEX, re.IGNORECASE)
    offending = [
        c for c in df.columns
        if c.lower() in [p.lower() for p in PROHIBITED_COLUMNS]
        or prohibited_regex.match(c.lower())
    ]
    if offending:
        report = {
            "status": "FAILURE",
            "reason": "LEAKAGE DETECTED",
            "offending_columns": offending,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        (ROOT / "leakage_violation_report.json").write_text(json.dumps(report, indent=2))
        raise ValueError(f"LEAKAGE DETECTED: {offending}")

class CFBDAsyncClient:
    def __init__(self):
        self.api_key = os.getenv("CFBD_API_KEY")
        if not self.api_key:
            raise ValueError("CFBD_API_KEY not found in .env. Task 2 requires a valid CFBD API key.")
        self.base_url = "https://api.collegefootballdata.com"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.cache = {}
        if CFBD_CACHE_PATH.exists():
            try:
                self.cache = json.loads(CFBD_CACHE_PATH.read_text())
            except Exception:
                self.cache = {}
        self.semaphore = asyncio.Semaphore(3)

    def save_cache(self):
        CFBD_CACHE_PATH.write_text(json.dumps(self.cache, indent=2))

    async def get_data(self, client, endpoint, params):
        cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        async with self.semaphore:
            for attempt in range(3):
                try:
                    resp = await client.get(f"{self.base_url}{endpoint}", params=params, headers=self.headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        self.cache[cache_key] = data
                        return data
                    elif resp.status_code == 404:
                        return None
                    elif resp.status_code == 429:
                        wait = (attempt + 1) * 10
                        await asyncio.sleep(wait)
                    else:
                        return None
                except Exception:
                    await asyncio.sleep(1)
            return None

def _map_team_name(pfr_team: str) -> str:
    name = pfr_team.replace(" St.", " State")
    name = name.replace(" Col.", " College")

    mapping = {
        "Miami (FL)": "Miami",
        "Florida St.": "Florida State",
        "Central Florida": "UCF",
        "Mississippi": "Ole Miss",
        "NC State": "NC State",
        "Ala-Birmingham": "UAB",
        "Pittsburgh": "Pitt",
        "Middle Tenn. St.": "Middle Tennessee",
        "La-Monroe": "Louisiana Monroe",
        "La-Lafayette": "Louisiana",
        "Southern Miss": "Southern Mississippi",
        "Bowling Green": "Bowling Green State",
        "Appalachian St.": "Appalachian State",
        "James Madison": "James Madison",
        "Boston Col.": "Boston College",
        "Youngstown St.": "Youngstown State",
        "UT Martin": "UT Martin",
        "Coastal Carolina": "Coastal Carolina",
    }
    return mapping.get(pfr_team, name)

async def process_group(http_client, client, draft_year, pfr_team, group):
    target_year = int(draft_year) - 1
    cfbd_team = _map_team_name(pfr_team)

    team_task = client.get_data(http_client, "/stats/season", {"year": target_year, "team": cfbd_team})
    rec_task = client.get_data(http_client, "/stats/player/season", {"year": target_year, "team": cfbd_team, "category": "receiving"})
    rush_task = client.get_data(http_client, "/stats/player/season", {"year": target_year, "team": cfbd_team, "category": "rushing"})

    team_data, rec_stats, rush_stats = await asyncio.gather(team_task, rec_task, rush_task)

    team_rec_yds = sum(float(s.get('statValue', 0)) for s in team_data if s.get('statName') == 'netPassingYards') if team_data else 0
    team_rec_tds = sum(float(s.get('statValue', 0)) for s in team_data if s.get('statName') == 'passingTDs') if team_data else 0
    team_rush_yds = sum(float(s.get('statValue', 0)) for s in team_data if s.get('statName') == 'rushingYards') if team_data else 0
    team_rush_tds = sum(float(s.get('statValue', 0)) for s in team_data if s.get('statName') == 'rushingTDs') if team_data else 0

    group_results = []
    for _, row in group.iterrows():
        player_dict = row.to_dict()
        player_dict.update({
            'dominator_rating': None, 'receiving_yards_share': None,
            'source_dominator_rating': None, 'source_receiving_yards_share': None
        })

        pos = player_dict['position']
        player_name = player_dict['pfr_player_name']

        p_rec_rows = [s for s in (rec_stats or []) if s.get('player', '').lower() == player_name.lower()]
        p_rush_rows = [s for s in (rush_stats or []) if s.get('player', '').lower() == player_name.lower()]

        if p_rec_rows or p_rush_rows:
            p_rec_yds = sum(float(s.get('stat', 0)) for s in p_rec_rows if s.get('statType') == 'YDS')
            p_rec_tds = sum(float(s.get('stat', 0)) for s in p_rec_rows if s.get('statType') == 'TD')
            p_rush_yds = sum(float(s.get('stat', 0)) for s in p_rush_rows if s.get('statType') == 'YDS')
            p_rush_tds = sum(float(s.get('stat', 0)) for s in p_rush_rows if s.get('statType') == 'TD')

            if pos in ["WR", "TE"] and team_rec_yds > 0:
                yds_share = p_rec_yds / team_rec_yds
                td_share = p_rec_tds / team_rec_tds if team_rec_tds > 0 else 0
                player_dict['receiving_yards_share'] = yds_share
                player_dict['source_receiving_yards_share'] = 'cfbd'
                player_dict['dominator_rating'] = (yds_share + td_share) / 2
                player_dict['source_dominator_rating'] = 'cfbd'
            elif pos == "RB" and team_rush_yds > 0:
                rush_yds_share = p_rush_yds / team_rush_yds
                rush_td_share = p_rush_tds / team_rush_tds if team_rush_tds > 0 else 0
                player_dict['dominator_rating'] = (rush_yds_share + rush_td_share) / 2
                player_dict['source_dominator_rating'] = 'cfbd'

        group_results.append(player_dict)
    return group_results

async def enrich_with_cfbd(df: pd.DataFrame, client: CFBDAsyncClient) -> pd.DataFrame:
    print("Starting CFBD enrichment...")
    results = []
    groups = list(df.groupby(['season', 'college']))
    total_groups = len(groups)

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        for i, ((draft_year, pfr_team), group) in enumerate(groups):
            group_res = await process_group(http_client, client, draft_year, pfr_team, group)
            results.extend(group_res)

            if (i + 1) % 20 == 0:
                print(f"[{i+1}/{total_groups}] Processing...")
                client.save_cache()

    client.save_cache()
    return pd.DataFrame(results)

async def main():
    training_csv = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
    output_csv = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_cfbd_partial.csv"

    baseline_df = pd.read_csv(training_csv)
    baseline_rows = len(baseline_df)
    check_leakage(baseline_df)

    client = CFBDAsyncClient()
    enriched_df = await enrich_with_cfbd(baseline_df, client)

    if not enriched_df.empty:
        new_cols = ['dominator_rating', 'receiving_yards_share', 'source_dominator_rating', 'source_receiving_yards_share']
        merge_df = enriched_df[['gsis_id'] + new_cols].copy()
        merge_df = merge_df.drop_duplicates(subset='gsis_id')
        final_df = baseline_df.merge(merge_df, on='gsis_id', how='left')
    else:
        final_df = baseline_df.copy()

    # Final contract assertions
    print(f"Verifying final row count parity: {baseline_rows}")
    if len(final_df) != baseline_rows:
        raise ValueError(f"CRITICAL: Row count changed! Baseline: {baseline_rows}, Result: {len(final_df)}")

    check_leakage(final_df)
    final_df.to_csv(output_csv, index=False)
    print(f"Partial Enriched CSV (CFBD only) written to {output_csv.name}")

if __name__ == "__main__":
    asyncio.run(main())
