import re
import json
import os
from pathlib import Path
import pandas as pd
import sys
from dotenv import load_dotenv
import asyncio
import httpx
from typing import Optional, List, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.dynasty_genius.models.engine_a_contract import PROHIBITED_COLUMNS, LEAKAGE_REGEX

CFBD_CACHE_PATH = ROOT / "app" / "data" / "cache" / "cfbd_cache.json"
PP_CACHE_PATH = ROOT / "app" / "data" / "cache" / "pp_id_map.json"
PP_STATS_CACHE_PATH = ROOT / "app" / "data" / "cache" / "pp_stats_cache.json"
ENRICHMENT_REPORT_PATH = ROOT / "app" / "data" / "cache" / "enrichment_report.json"

for p in [CFBD_CACHE_PATH, PP_CACHE_PATH, PP_STATS_CACHE_PATH]:
    p.parent.mkdir(parents=True, exist_ok=True)

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
            raise ValueError("CFBD_API_KEY not found in .env.")
        self.base_url = "https://api.collegefootballdata.com"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.cache = json.loads(CFBD_CACHE_PATH.read_text()) if CFBD_CACHE_PATH.exists() else {}
        self.semaphore = asyncio.Semaphore(3)

    def save_cache(self):
        CFBD_CACHE_PATH.write_text(json.dumps(self.cache, indent=2))

    async def get_data(self, client, endpoint, params):
        cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}"
        if cache_key in self.cache: return self.cache[cache_key]
        async with self.semaphore:
            for attempt in range(3):
                try:
                    resp = await client.get(f"{self.base_url}{endpoint}", params=params, headers=self.headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        self.cache[cache_key] = data
                        return data
                    elif resp.status_code == 404: return None
                    elif resp.status_code == 429: await asyncio.sleep((attempt + 1) * 10)
                    else: return None
                except Exception: await asyncio.sleep(1)
            return None

def _map_team_name(pfr_team: str) -> str:
    name = pfr_team.replace(" St.", " State").replace(" Col.", " College")
    mapping = {
        "Miami (FL)": "Miami", "Florida St.": "Florida State", "Central Florida": "UCF",
        "Ole Miss": "Ole Miss", "Mississippi": "Ole Miss", "NC State": "NC State", "Ala-Birmingham": "UAB",
        "Pittsburgh": "Pitt", "Middle Tenn. St.": "Middle Tennessee", "La-Monroe": "Louisiana Monroe",
        "La-Lafayette": "Louisiana", "Southern Miss": "Southern Mississippi", "Bowling Green": "Bowling Green State",
        "Appalachian St.": "Appalachian State", "James Madison": "James Madison", "Boston Col.": "Boston College",
        "Youngstown St.": "Youngstown State", "UT Martin": "UT Martin", "Coastal Carolina": "Coastal Carolina",
    }
    return mapping.get(pfr_team, name)

async def process_cfbd_group(http_client, client, draft_year, pfr_team, group):
    target_year = int(draft_year) - 1
    cfbd_team = _map_team_name(pfr_team)
    team_data = await client.get_data(http_client, "/stats/season", {"year": target_year, "team": cfbd_team})
    rec_stats = await client.get_data(http_client, "/stats/player/season", {"year": target_year, "team": cfbd_team, "category": "receiving"})
    rush_stats = await client.get_data(http_client, "/stats/player/season", {"year": target_year, "team": cfbd_team, "category": "rushing"})
    
    team_rec_yds = sum(float(s.get('statValue', 0)) for s in (team_data or []) if s.get('statName') == 'netPassingYards')
    team_rec_tds = sum(float(s.get('statValue', 0)) for s in (team_data or []) if s.get('statName') == 'passingTDs')
    team_rush_yds = sum(float(s.get('statValue', 0)) for s in (team_data or []) if s.get('statName') == 'rushingYards')
    team_rush_tds = sum(float(s.get('statValue', 0)) for s in (team_data or []) if s.get('statName') == 'rushingTDs')
    
    res = []
    for _, row in group.iterrows():
        p = row.to_dict()
        p.update({'dominator_rating': None, 'receiving_yards_share': None, 'source_dominator_rating': None, 'source_receiving_yards_share': None})
        pr = [s for s in (rec_stats or []) if s.get('player', '').lower() == p['pfr_player_name'].lower()]
        ps = [s for s in (rush_stats or []) if s.get('player', '').lower() == p['pfr_player_name'].lower()]
        if pr or ps:
            pry = sum(float(s.get('stat', 0)) for s in pr if s.get('statType') == 'YDS')
            prt = sum(float(s.get('stat', 0)) for s in pr if s.get('statType') == 'TD')
            psy = sum(float(s.get('stat', 0)) for s in ps if s.get('statType') == 'YDS')
            pst = sum(float(s.get('stat', 0)) for s in ps if s.get('statType') == 'TD')
            if p['position'] in ["WR", "TE"] and team_rec_yds > 0:
                ys = pry / team_rec_yds
                ts = prt / team_rec_tds if team_rec_tds > 0 else 0
                p.update({'receiving_yards_share': ys, 'source_receiving_yards_share': 'cfbd', 'dominator_rating': (ys + ts) / 2, 'source_dominator_rating': 'cfbd'})
            elif p['position'] == "RB" and team_rush_yds > 0:
                rs = psy / team_rush_yds
                rt = pst / team_rush_tds if team_rush_tds > 0 else 0
                p.update({'dominator_rating': (rs + rt) / 2, 'source_dominator_rating': 'cfbd'})
        res.append(p)
    return res

async def enrich_with_cfbd(df: pd.DataFrame, client: CFBDAsyncClient) -> pd.DataFrame:
    print("Starting CFBD enrichment...")
    results = []
    groups = list(df.groupby(['season', 'college'], dropna=False))
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        for i, ((year, team), group) in enumerate(groups):
            if pd.isna(team):
                results.extend([r.to_dict() for _, r in group.iterrows()])
                continue
            res = await process_cfbd_group(http_client, client, year, team, group)
            results.extend(res)
            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{len(groups)} groups...")
                client.save_cache()
    client.save_cache()
    return pd.DataFrame(results)

class PPClient:
    def __init__(self):
        self.base_url = "https://www.playerprofiler.com/wp-admin/admin-ajax.php"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.id_map = json.loads(PP_CACHE_PATH.read_text()) if PP_CACHE_PATH.exists() else {}
        self.stats_cache = json.loads(PP_STATS_CACHE_PATH.read_text()) if PP_STATS_CACHE_PATH.exists() else {}
        self.semaphore = asyncio.Semaphore(1)

    def save_caches(self):
        PP_CACHE_PATH.write_text(json.dumps(self.id_map, indent=2))
        PP_STATS_CACHE_PATH.write_text(json.dumps(self.stats_cache, indent=2))

    async def initialize_id_map(self, http_client):
        if self.id_map: return
        print("  Initializing PlayerProfiler ID map from /players endpoint...")
        try:
            params = {'action': 'playerprofiler_api', 'endpoint': '/players'}
            resp = await http_client.get(self.base_url, params=params, headers={"User-Agent": self.ua})
            if resp.status_code == 200:
                data = resp.json()
                players = data.get('data', {}).get('Players', [])
                for p in players:
                    name = p.get('Full Name')
                    pid = p.get('Player_ID')
                    if name and pid: self.id_map[name] = pid
                self.save_caches()
                print(f"    Mapped {len(self.id_map)} players.")
        except Exception: pass

    async def get_stats(self, http_client, pp_id: str, season: int) -> Optional[dict]:
        key = f"{pp_id}_{season}"
        if key in self.stats_cache: return self.stats_cache[key]
        async with self.semaphore:
            try:
                params = {'action': 'playerprofiler_api', 'endpoint': f'/player/{pp_id}'}
                resp = await http_client.get(self.base_url, params=params, headers={"User-Agent": self.ua})
                await asyncio.sleep(1.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get('success'):
                        d = data.get('data', {}).get('Player', {})
                        perf = d.get('College Performance', {})
                        metrics = d.get('College Metrics', {})
                        workout = d.get('Workout Metrics', {})
                        target_year = str(season - 1)
                        year_stats = metrics.get(target_year, {})
                        
                        def _pf(v):
                            try:
                                if v is None or v == '-': return None
                                return float(str(v).replace('%','')) / 100 if '%' in str(v) else float(v)
                            except: return None

                        res = {
                            "target_share": _pf(perf.get('College Target Share')) or _pf(year_stats.get('Target Share')),
                            "breakout_age": _pf(perf.get('Breakout Age')),
                            "speed_score": _pf(workout.get('Speed Score')),
                            "yprr": _pf(year_stats.get('Yards Per Team Targets'))
                        }
                        self.stats_cache[key] = res
                        return res
                return None
            except Exception: return None

async def enrich_with_pp(df: pd.DataFrame, client: PPClient) -> pd.DataFrame:
    print("Starting PlayerProfiler enrichment...")
    results = []
    failures = []
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        await client.initialize_id_map(http_client)
        for i, row in df.iterrows():
            p = row.to_dict()
            name, pos, season = p['pfr_player_name'], p['position'], int(p['season'])
            p.update({'target_share': None, 'breakout_age': None, 'speed_score': None, 'yprr': None, 'source_target_share': None, 'source_breakout_age': None, 'source_speed_score': None, 'source_yprr': None, 'imputed_yprr': 0})
            if pos != "QB":
                pp_id = client.id_map.get(name)
                if pp_id:
                    s = await client.get_stats(http_client, pp_id, season)
                    if s and any(v is not None for v in s.values()):
                        p.update({
                            'target_share': s.get('target_share'), 'breakout_age': s.get('breakout_age'),
                            'speed_score': s.get('speed_score'), 'yprr': s.get('yprr'),
                            'source_target_share': 'playerprofiler' if s.get('target_share') is not None else None,
                            'source_breakout_age': 'playerprofiler' if s.get('breakout_age') is not None else None,
                            'source_speed_score': 'playerprofiler' if s.get('speed_score') is not None else None,
                            'source_yprr': 'playerprofiler' if s.get('yprr') is not None else None
                        })
                    else: failures.append({"name": name, "id": pp_id, "reason": "No data in JSON fields"})
                else: failures.append({"name": name, "reason": "ID mapping failed"})
            if pos in ["WR", "TE"] and p['yprr'] is None:
                p.update({'yprr': 1.85, 'source_yprr': 'imputed_median', 'imputed_yprr': 1})
            results.append(p)
            if (i + 1) % 100 == 0:
                print(f"  Processed {i+1}/{len(df)} players...")
                client.save_caches()
    client.save_caches()
    if failures: ENRICHMENT_REPORT_PATH.write_text(json.dumps(failures, indent=2))
    return pd.DataFrame(results)

async def main():
    t_csv, v2_csv = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv", ROOT / "app" / "data" / "training" / "prospects_with_outcomes_v2.csv"
    b_df = pd.read_csv(t_csv)
    c_df = await enrich_with_cfbd(b_df, CFBDAsyncClient())
    p_df = await enrich_with_pp(c_df, PPClient())
    if len(p_df) != len(b_df): raise ValueError("Row count mismatch")
    check_leakage(p_df)
    p_df.to_csv(v2_csv, index=False)
    print(f"Enriched CSV written to {v2_csv.name}")

if __name__ == "__main__":
    asyncio.run(main())
