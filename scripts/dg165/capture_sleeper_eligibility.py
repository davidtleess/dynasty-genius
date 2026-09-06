"""Capture Sleeper's public player list ONCE and reconcile fantasy eligibility (DG-165, Codex 2026-09-06).

    .venv/bin/python scripts/dg165/capture_sleeper_eligibility.py --rookie-run runs/<UTC>/dg165_rookie_capital

Read-only public source (https://docs.sleeper.com/, GET https://api.sleeper.app/v1/players/nfl), no
credentials, no paid provider. Writes ONE immutable run directory runs/<UTC>/eligibility_capture/:
    raw/sleeper_players_nfl.json   the raw payload (gitignored; sha256 in the manifest)
    sleeper_eligibility.csv        compact derivative, every Sleeper player, eligibility fields only
    reconciliation.csv             the rookie file's 80, Dell, Hunter and the candidate pool, keyed by Sleeper id
    RECONCILIATION.md, manifest.json
Nothing under app/data is touched; the accepted rookie forecasts are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.sleeper_eligibility import (  # noqa: E402
    SLEEPER_PLAYERS_URL,
    extract_players,
    reconcile,
)

DG178 = Path.home() / "dg-wt" / "DG-178"
POOL_REPORT = DG178 / "runs/20260906T161634Z/dg178_audit/report.json"
UNIVERSE_CSV = DG178 / "runs/20260906T153607Z/dg178_universe/eligible_universe.csv"
NAMED_EXTRA = {"9502": "Tank Dell", "12530": "Travis Hunter"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rookie-run", type=Path, required=True, help="the accepted rookie run directory (reads cohort.csv)")
    ap.add_argument("--runs-root", type=Path, default=REPO / "runs")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--raw", type=Path, default=None,
                    help="reuse an earlier run's raw payload instead of fetching again (the source is captured ONCE); its sha256 is recorded")
    a = ap.parse_args(argv)

    run_dir = create_run_dir(a.runs_root, name="eligibility_capture")
    (run_dir / "raw").mkdir()
    (run_dir / ".gitignore").write_text("raw/\n")
    captured_at = datetime.now(timezone.utc).isoformat()
    reused_from = None
    try:
        if a.raw is not None:
            body = a.raw.read_bytes()
            status = "reused"
            reused_from = str(a.raw)
            captured_at = json.loads((a.raw.parent.parent / "manifest.json").read_text()).get("captured_at", captured_at)
        else:
            req = urllib.request.Request(SLEEPER_PLAYERS_URL, headers={"User-Agent": "dynasty-genius DG-165 read-only capture"})
            with urllib.request.urlopen(req, timeout=a.timeout) as resp:
                status = resp.status
                body = resp.read()
    except Exception as exc:
        gap = {"source_url": SLEEPER_PLAYERS_URL, "captured_at": captured_at, "status": "FAILED", "error": repr(exc),
               "note": "read-only capture failed; eligibility remains UNKNOWN for every player; nothing inferred"}
        (run_dir / "manifest.json").write_text(json.dumps(gap, indent=1))
        print(f"capture failed, gap recorded: {run_dir / 'manifest.json'}")
        return 2
    raw_path = run_dir / "raw" / "sleeper_players_nfl.json"
    raw_path.write_bytes(body)
    raw_sha = sha256_bytes(body)
    payload = json.loads(body)
    players = extract_players(payload)
    players.to_csv(run_dir / "sleeper_eligibility.csv", index=False)

    cohort = pd.read_csv(a.rookie_run / "cohort.csv")
    rookies = cohort.loc[cohort["draft_season"] == cohort["draft_season"].max()].reset_index(drop=True)
    report = json.loads(POOL_REPORT.read_text())
    pool_ids = {str(i) for v in report["replacement_pool_census"].values() for i in v.get("eligible_ids", [])}
    universe = pd.read_csv(UNIVERSE_CSV)
    rostered_ids = {str(i) for i in universe["sleeper_id"].unique()}
    rec = reconcile(players, rookies=rookies, extra_ids=set(NAMED_EXTRA), pool_ids=pool_ids, rostered_ids=rostered_ids)
    rec.to_csv(run_dir / "reconciliation.csv", index=False)

    rk = rec.loc[rec["source"] == "rookie"]
    summary = {
        "rookies": int(len(rk)),
        "rookies_matched": int(rk["sleeper_id"].notna().sum()),
        "rookies_by_match_basis": rk["match_basis"].value_counts().to_dict(),
        "rookies_eligibility_known": int((rk["league_eligibility"] != "unknown").sum()),
        "rookies_where_sleeper_eligibility_differs_from_draft_position": rk.loc[
            (rk["league_eligibility"] != "unknown") & (rk["league_eligibility"] != rk["draft_position"]),
            ["name", "pick", "draft_position", "position_current_nflverse", "league_eligibility", "availability_class"]].to_dict("records"),
        "rookies_availability": rk["availability_class"].value_counts().to_dict(),
        "named_extra": rec.loc[rec["source"] == "extra", ["sleeper_id", "sleeper_name", "sleeper_position", "league_eligibility",
                                                            "active", "status", "team", "availability_class"]].to_dict("records"),
        "candidate_pool": {"ids": int(len(pool_ids)),
                           "availability": rec.loc[rec["source"] == "candidate_pool", "availability_class"].value_counts().to_dict(),
                           "eligibility_unknown": int((rec.loc[rec["source"] == "candidate_pool", "league_eligibility"] == "unknown").sum()),
                           "eligibility_differs_from_sleeper_position": int((rec.loc[rec["source"] == "candidate_pool"].apply(
                               lambda r: r["league_eligibility"] not in ("unknown", None) and str(r["sleeper_position"]) not in str(r["league_eligibility"]).split("|"), axis=1)).sum())},
        "all_players": {"rows": int(len(players)), "fantasy_positions_missing": int(players["fantasy_positions"].isna().sum()),
                        "active_flag_missing": int(players["active"].isna().sum())},
    }
    lines = ["# Sleeper fantasy eligibility — reconciliation", "",
             f"Captured {captured_at} from `{SLEEPER_PLAYERS_URL}` (HTTP {status}, {len(body):,} bytes, sha256 `{raw_sha[:12]}…`, {len(payload):,} players).", "",
             "`fantasy_positions` is the placement authority. Unknown stays unknown. Flags classify, never suppress.", "",
             "## Rookies (80 from the accepted forecast file)", "",
             f"- matched: {summary['rookies_matched']} of {summary['rookies']} ({summary['rookies_by_match_basis']})",
             f"- eligibility known: {summary['rookies_eligibility_known']}; availability: {summary['rookies_availability']}", "",
             "| player | pick | draft position | nflverse current | Sleeper fantasy_positions | availability |", "|---|---:|---|---|---|---|"]
    for r in summary["rookies_where_sleeper_eligibility_differs_from_draft_position"]:
        lines.append(f"| {r['name']} | {r['pick']} | {r['draft_position']} | {r['position_current_nflverse']} | {r['league_eligibility']} | {r['availability_class']} |")
    lines += ["", "## Named players", "", "| Sleeper id | name | Sleeper position | fantasy_positions | active | status | team | availability |", "|---|---|---|---|---|---|---|---|"]
    for r in summary["named_extra"]:
        lines.append(f"| {r['sleeper_id']} | {r['sleeper_name']} | {r['sleeper_position']} | {r['league_eligibility']} | {r['active']} | {r['status']} | {r['team']} | {r['availability_class']} |")
    cp = summary["candidate_pool"]
    lines += ["", "## Candidate available pool (DG-178 replacement census ids)", "",
              f"- ids: {cp['ids']}; availability: {cp['availability']}; eligibility unknown: {cp['eligibility_unknown']}; "
              f"eligibility differs from Sleeper position: {cp['eligibility_differs_from_sleeper_position']}", "",
              f"All players: {summary['all_players']}"]
    (run_dir / "RECONCILIATION.md").write_text("\n".join(lines) + "\n")
    manifest = {
        "ticket": "DG-165", "purpose": "Sleeper fantasy eligibility capture and reconciliation (read-only public source)",
        "source_url": SLEEPER_PLAYERS_URL, "docs": "https://docs.sleeper.com/", "captured_at": captured_at, "http_status": status,
        "raw_reused_from": reused_from,
        "raw": {"path": "raw/sleeper_players_nfl.json (gitignored)", "bytes": len(body), "sha256": raw_sha, "players": len(payload)},
        "authority": "fantasy_positions is the placement authority; a missing field stays unknown and is never inferred from the NFL position "
                     "or the draft table; active/status classify availability and never suppress; rostered players are always in the universe",
        "inputs": {"rookie_cohort": {"path": str(a.rookie_run / "cohort.csv"), "sha256": sha256_file(a.rookie_run / "cohort.csv")},
                   "dg178_pool_report": {"path": str(POOL_REPORT), "sha256": sha256_file(POOL_REPORT)},
                   "dg178_universe": {"path": str(UNIVERSE_CSV), "sha256": sha256_file(UNIVERSE_CSV)},
                   "named_extra": NAMED_EXTRA},
        "summary": summary,
        "outputs_sha256": {p.name: sha256_file(p) for p in sorted(run_dir.iterdir()) if p.is_file()},
        "rookie_forecasts": "unchanged; this capture joins eligibility beside them and alters no forecast",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    print(f"run dir: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
