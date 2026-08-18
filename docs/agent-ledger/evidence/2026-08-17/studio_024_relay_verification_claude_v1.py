"""Verify Studio relay 024 claims R1/R3 against the shipped artifact. Read-only."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ART = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "app/data/valuation/universe_market_divergence_latest.json"
)
P90 = {"QB": 20.1, "RB": 15.7, "WR": 14.5, "TE": 9.4}


def main() -> None:
    rows = json.loads(ART.read_text())["players"]
    print(f"rows: {len(rows)}")
    at_ceiling: dict[str, list] = defaultdict(list)
    totals: dict[str, int] = defaultdict(int)
    ratios: dict[str, list[float]] = defaultdict(list)
    clamped_flagged: dict[str, int] = defaultdict(int)
    dvs_present = 0

    for r in rows:
        pos = (r.get("player") or {}).get("position")
        val = r.get("valuation") or {}
        dvs = val.get("dynasty_value_score")
        if dvs is not None and val.get("dvs_clamped"):
            clamped_flagged[pos] += 1
        p2 = r.get("projection_2y")
        if pos not in P90:
            continue
        totals[pos] += 1
        if dvs is not None:
            dvs_present += 1
            if float(dvs) >= 100.0:
                at_ceiling[pos].append(
                    ((r.get("player") or {}).get("full_name"), p2)
                )
            if p2:
                ratios[pos].append(float(dvs) / float(p2))

    print(f"rows carrying a dynasty_value_score: {dvs_present}")
    for pos in ("QB", "RB", "WR", "TE"):
        hits = at_ceiling[pos]
        span = ""
        vals = [p for _, p in hits if p is not None]
        if vals:
            span = f" projection_2y span {max(vals) - min(vals):.2f} PPG (min {min(vals):.2f}, max {max(vals):.2f})"
        print(
            f"{pos}: {len(hits)}/{totals[pos]} at DVS 100.0"
            f" | dvs_clamped=true on {clamped_flagged[pos]}.{span}"
        )
        for name, p2 in sorted(hits, key=lambda t: -(t[1] or 0))[:6]:
            print(f"    {name}: projection_2y {p2}")
        if ratios[pos]:
            rr = ratios[pos]
            mean = sum(rr) / len(rr)
            sd = (sum((x - mean) ** 2 for x in rr) / len(rr)) ** 0.5
            print(
                f"    DVS/projection_2y mean {mean:.4f} sd {sd:.4f} "
                f"| 100/P90 = {100 / P90[pos]:.4f}"
            )


if __name__ == "__main__":
    main()
