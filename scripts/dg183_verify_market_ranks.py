"""Independent raw-source acceptance oracle; no application/adapter imports.

Usage: python scripts/dg183_verify_market_ranks.py MANIFEST --url http://127.0.0.1:8789
"""

import argparse
import hashlib
import json
import math
import urllib.request
from pathlib import Path


def verify(manifest_path, payload):
    manifest = json.loads(Path(manifest_path).read_bytes())
    sources = {}
    for key, spec in manifest["files"].items():
        raw = Path(spec["path"]).read_bytes()
        assert (
            hashlib.sha256(raw).hexdigest()
            == spec["sha256"]
            == payload["source"][key + "_sha256"]
        )
        sources[key] = json.loads(raw)
    report, market, snapshot = [sources[key] for key in ("report", "market", "league")]
    models = {
        r["sleeper_id"]: r
        for r in report[report["comparable_views"]["h5"]]["all_inspectable"]
    }
    prices = {
        r["sleeper_id"]: r
        for r in market["entries"]
        if r["position"] in {"QB", "RB", "WR", "TE"}
    }
    common = set(models) & set(prices)
    roster = next(
        r for r in snapshot["rosters"] if r["roster_id"] == snapshot["david_roster_id"]
    )
    owned, taxi = set(roster["players"]), set(roster["taxi"]) | set(roster["reserve"])
    assert len(payload["rows"]) == len({r["sleeper_id"] for r in payload["rows"]})
    assert {r["sleeper_id"] for r in payload["rows"]} == set(models) | set(prices)

    def interval(value, values):
        return dict(
            start=1 + sum(v > value for v in values),
            end=sum(v >= value for v in values),
            total=len(values),
        )

    for row in payload["rows"]:
        sid = row["sleeper_id"]
        m, p = models.get(sid), prices.get(sid)
        assert row["on_roster"] == (sid in owned)
        assert row["taxi_or_reserve"] == ((sid in taxi) if sid in owned else None)
        assert row["model_value"] == (m["value"] if m else None)
        assert row["market_value"] == (p["value"] if p else None)
        assert row["market_rank_published"] == (p["overall_rank"] if p else None)
        if m:
            assert row["model_rank_all"] == interval(
                m["value"], [r["value"] for r in models.values()]
            )
            assert row["seasons"] == [
                dict(season=s["season"], advantage=max(0, s["expected_margin"]))
                for s in m["seasons"]
            ]
            assert math.isclose(
                sum(s["advantage"] for s in row["seasons"]),
                row["model_value"],
                abs_tol=1e-9,
            )
        if sid in common:
            ours = interval(m["value"], [models[s]["value"] for s in common])
            theirs = interval(p["value"], [prices[s]["value"] for s in common])
            assert row["our_rank"] == ours and row["market_rank"] == theirs
            lo, hi = theirs["start"] - ours["end"], theirs["end"] - ours["start"]
            direction = (
                "higher"
                if lo > 0
                else "lower"
                if hi < 0
                else "same"
                if lo == hi == 0
                else "overlap"
            )
            assert row["comparison"] == dict(
                direction=direction, gap_min=lo, gap_max=hi
            )
        else:
            assert row["our_rank"] is None and row["market_rank"] is None
            assert row["comparison"] == dict(
                direction="unavailable", gap_min=None, gap_max=None
            )
    assert payload["coverage"] == dict(
        model_players=len(models),
        market_players=len(prices),
        market_picks=len(market["entries"]) - len(prices),
        common_players=len(common),
        total_players=len(set(models) | set(prices)),
        roster_players=len(owned),
        roster_common_players=len(owned & common),
    )
    return {
        "status": "passed",
        "verified_players": len(payload["rows"]),
        "coverage": payload["coverage"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    with urllib.request.urlopen(
        args.url.rstrip("/") + "/api/research/market-ranks"
    ) as response:
        payload = json.load(response)
    print(json.dumps(verify(args.manifest, payload), indent=2))
