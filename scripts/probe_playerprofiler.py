"""PlayerProfiler coverage probe — one-time diagnostic.

Probes the PlayerProfiler shadow API for each player in the Engine A training
set (2015-2025 draft classes) to determine whether real, non-null enrichment
coverage meets the 80% threshold required for model_input promotion.

Usage:
    .venv/bin/python scripts/probe_playerprofiler.py

Output:
    app/data/cache/pp_probe_results.json  — per-player probe results
    stdout summary                        — coverage numbers for the ledger

This script is DIAGNOSTIC ONLY. It does not write to any training CSV.
It does not modify the source registry. It does not start Task 4.

After running, execute:
    .venv/bin/python -m pytest tests/test_playerprofiler_decision_gate.py -v -s

to evaluate the gate. Record the result in the daily ledger.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRAINING_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
PROBE_RESULTS_PATH = ROOT / "app" / "data" / "cache" / "pp_probe_results.json"
PROBE_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

PP_AJAX_URL = "https://www.playerprofiler.com/wp-admin/admin-ajax.php"
RECENT_SEASONS = set(range(2015, 2026))

# Rate limiting: max 5 concurrent, 1s sleep between batches
SEMAPHORE_LIMIT = 5
BATCH_SLEEP_SEC = 1.0


def _derive_slug(name: str) -> str:
    """Convert PFR player name to a PlayerProfiler-style slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def _extract_field(payload: dict, *keys: str) -> str | None:
    """Walk nested keys tolerantly, return string value or None."""
    val = payload
    for k in keys:
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    if val is None:
        return None
    return str(val).strip() or None


async def probe_player(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    row: dict,
) -> dict:
    name = row.get("pfr_player_name", "")
    position = row.get("position", "")
    season = row.get("season")
    slug = _derive_slug(name)

    result = {
        "pfr_player_name": name,
        "position": position,
        "season": season,
        "pp_slug": slug,
        "target_share_raw": None,
        "breakout_age_raw": None,
        "speed_score_raw": None,
        "status": "not_attempted",
    }

    payload = {
        "action": "playerprofiler_api",
        "endpoint": f"/player/{slug}",
    }

    async with sem:
        try:
            resp = await client.post(
                PP_AJAX_URL,
                data=payload,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15.0,
            )

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if not data or data == 0 or data == "0":
                        result["status"] = "not_found"
                    else:
                        result["status"] = "found"
                        result["target_share_raw"] = _extract_field(data, "target_share")
                        result["breakout_age_raw"] = _extract_field(data, "breakout_age")
                        result["speed_score_raw"] = _extract_field(data, "speed_score")
                        # Nested path fallbacks
                        if result["target_share_raw"] is None:
                            result["target_share_raw"] = _extract_field(data, "college_target_share")
                        if result["breakout_age_raw"] is None:
                            result["breakout_age_raw"] = _extract_field(data, "college_breakout_age")
                except (ValueError, KeyError):
                    result["status"] = "parse_error"
            elif resp.status_code == 404:
                result["status"] = "not_found"
            else:
                result["status"] = f"http_{resp.status_code}"

        except httpx.TimeoutException:
            result["status"] = "timeout"
        except Exception as e:
            result["status"] = f"error_{type(e).__name__}"

    return result


async def run_probe(rows: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Process in batches to respect rate limiting
        batch_size = SEMAPHORE_LIMIT
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[probe_player(client, sem, row) for row in batch]
            )
            results.extend(batch_results)

            processed = min(i + batch_size, len(rows))
            if processed % 50 == 0 or processed == len(rows):
                found = sum(1 for r in results if r["status"] == "found")
                ts_present = sum(
                    1 for r in results
                    if r["target_share_raw"] not in (None, "", "nan")
                )
                print(
                    f"[{processed}/{len(rows)}] found={found} "
                    f"target_share_coverage={ts_present/max(processed,1):.0%}"
                )

            if i + batch_size < len(rows):
                await asyncio.sleep(BATCH_SLEEP_SEC)

    return results


def print_summary(results: list[dict]) -> None:
    total = len(results)
    found = sum(1 for r in results if r["status"] == "found")
    not_found = sum(1 for r in results if r["status"] == "not_found")
    parse_error = sum(1 for r in results if r["status"] == "parse_error")
    other = total - found - not_found - parse_error

    ts_present = sum(1 for r in results if r["target_share_raw"] not in (None, "", "nan"))
    ba_present = sum(1 for r in results if r["breakout_age_raw"] not in (None, "", "nan"))
    ss_present = sum(1 for r in results if r["speed_score_raw"] not in (None, "", "nan"))

    print("\n" + "=" * 60)
    print("PLAYERPROFILER PROBE SUMMARY")
    print("=" * 60)
    print(f"  Total probed:      {total}")
    print(f"  found:             {found} ({found/total:.0%})")
    print(f"  not_found:         {not_found} ({not_found/total:.0%})")
    print(f"  parse_error:       {parse_error}")
    print(f"  other:             {other}")
    print()
    print(f"  target_share:      {ts_present}/{total} = {ts_present/total:.0%}")
    print(f"  breakout_age:      {ba_present}/{total} = {ba_present/total:.0%}")
    print(f"  speed_score:       {ss_present}/{total} = {ss_present/total:.0%}")
    print()

    gate = ts_present / total >= 0.80 and ba_present / total >= 0.80
    if gate:
        print("  GATE RESULT: PASS — PP coverage meets 80% threshold")
        print("  Next step: run pytest tests/test_playerprofiler_decision_gate.py -v")
        print("  If pass: update source_registry.py PP role to model_input, implement adapter")
    else:
        print("  GATE RESULT: FAIL — PP coverage below 80% threshold")
        print("  Path B applies:")
        print("    - PP stays context_signal in source_registry.py")
        print("    - Remove target_share, breakout_age, speed_score from ALLOWED_ENRICHMENT_COLUMNS")
        print("    - Do NOT impute these fields — fabricated values are not model evidence")
        print("    - Log decision in docs/agent-ledger/YYYY-MM-DD.md")
        print("    - Then proceed to Task 4 (CFBD-only backtest) without PP fields")
    print("=" * 60)


def main() -> None:
    if not TRAINING_CSV.exists():
        print(f"ERROR: Training CSV not found at {TRAINING_CSV}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(TRAINING_CSV)
    # Filter to seasons most likely to have PP pages
    df_recent = df[df["season"].isin(RECENT_SEASONS)].copy()

    print(f"Probing {len(df_recent)} players from 2015-2025 draft classes...")
    print(f"(Full training set: {len(df)} players — only recent seasons probed for gate)")
    print()

    rows = df_recent[["pfr_player_name", "position", "season"]].to_dict("records")

    start = time.time()
    results = asyncio.run(run_probe(rows))
    elapsed = time.time() - start

    print(f"\nProbe complete in {elapsed:.0f}s")
    PROBE_RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Results written to: {PROBE_RESULTS_PATH.name}")

    print_summary(results)


if __name__ == "__main__":
    main()
