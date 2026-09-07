"""DG-178 round 2, item 5: the eligible universe and the replacement-pool denominator, proven.

Reads the served artifact (all positions) and the dated league snapshot, builds the eligible
universe (fantasy-relevant skill rows + every league-rostered player), marks which producer
forecasts each row, and writes a run-scoped CSV plus a census. Read-only on inputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.ranking.universe import eligible_universe  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True, type=Path)
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--producer-csv", type=Path, action="append", default=[],
                    help="a producer file with player_id (gsis) or gsis_id; repeatable, name:path")
    ap.add_argument("--reconciliation", type=Path, action="append", default=[],
                    help="a producer's per-row reconciliation CSV (sleeper_id,status,...); name:path; repeatable")
    ap.add_argument("--eligibility", type=Path, default=None,
                    help="lane 24974's sleeper_eligibility.csv: fantasy_positions is the placement authority")
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    a = ap.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_universe"
    out.mkdir(parents=True)
    art = json.loads(a.artifact.read_bytes())
    snap = json.loads(a.snapshot.read_bytes())
    # The SNAPSHOT's player list carries `cohort`; the served artifact enriches gsis/pick/class.
    from src.dynasty_genius.ranking.served_rows import read_fantasy_eligibility
    elig = read_fantasy_eligibility(a.eligibility) if a.eligibility else None
    u = eligible_universe(snap["players"], snap, artifact_rows=art["players"], eligibility=elig)
    producers = {}
    for spec in a.reconciliation:
        name, _, path = str(spec).partition(":")
        u.apply_reconciliation(Path(path), producer=name)
        producers[f"{name}:reconciliation"] = {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    for spec in a.producer_csv:
        name, _, path = str(spec).partition(":")
        p = Path(path)
        ids, picks = set(), set()
        with p.open(newline="") as fh:
            for rec in csv.DictReader(fh):
                g = rec.get("gsis_id") or rec.get("player_id")
                if g:
                    ids.add(str(g))
                if rec.get("pick") and rec.get("draft_season") and rec.get("position"):
                    picks.add((rec["position"].upper(), int(rec["draft_season"]), int(rec["pick"])))
        u.mark_forecast(ids, producer=name, picks=picks)
        producers[name] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "ids": len(ids)}
        # producer ids the universe does not hold: identity gaps or non-eligible rows
        known = {r.gsis_id for r in u.rows if r.gsis_id}
        producers[name]["ids_not_in_universe"] = sorted(ids - known)
    for r in u.rows:
        if r.forecast_by is None and r.forecast_reason is None:
            r.forecast_reason = ("not forecast by any producer; " + ("no 2025 feature row and not a 2026 draftee" if r.eligibility != "rostered_non_skill_position" else r.multi_position_note))
    csv_path = u.write_csv(out / "eligible_universe.csv")
    census = u.census()
    rostered_unforecast = [{"sleeper_id": r.sleeper_id, "gsis_id": r.gsis_id, "name": r.name, "position": r.position,
                            "roster_id": r.roster_id, "eligibility": r.eligibility, "reason": r.forecast_reason}
                           for r in u.rows if r.rostered and not r.forecast_by]
    pool = {}
    for pos in ("QB", "RB", "WR", "TE"):
        rows = [r for r in u.rows if r.position == pos and not r.rostered]
        pool[pos] = {"eligible_unrostered": len(rows), "forecast": sum(1 for r in rows if r.forecast_by),
                     "unforecast": sum(1 for r in rows if not r.forecast_by)}
    report = {"run": stamp, "artifact": {"path": str(a.artifact), "sha256": hashlib.sha256(a.artifact.read_bytes()).hexdigest(),
                                         "captured_at": art.get("captured_at")},
              "snapshot": {"path": str(a.snapshot), "id": a.snapshot.parent.name},
              "producers": producers, "census": census, "replacement_pool_denominator": pool,
              "rostered_unforecast": rostered_unforecast, "note": u.note, "csv": str(csv_path)}
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: report[k] for k in ("census", "replacement_pool_denominator", "producers")}, indent=1, default=str)[:3000])
    print("rostered, not forecast:", json.dumps(rostered_unforecast, default=str)[:1500])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
