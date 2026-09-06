#!/usr/bin/env python
"""DG-177 league scoring component audit — actual-data runner.

    .venv/bin/python scripts/dg177/run_league_scoring_audit.py \\
      --weekly     /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/identified_weekly.parquet \\
      --quarantine /Users/davidleess/dg-wt/DG-165/runs/20260906T194454Z/source_preparation/quarantine.parquet \\
      --pbp        /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/pbp/pbp_2025.parquet \\
      --sleeper-season-dir /Users/davidleess/dynasty-genius-product/app/data/research/league_behavior/raw/2026-07-19/season_2025_1183088915091423232 \\
      --league-snapshot /Users/davidleess/dynasty-genius-product/app/data/league_runtime/runs/league-20260906T130052Z/snapshot.json \\
      --idmap      /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/ff_playerids/ff_playerids_full.parquet \\
      --season 2025 --out-root runs

Writes a NEW runs/<ts>/dg177_league_scoring_audit/ (refuses an existing one). Report-only: no forecast,
label or model is touched. Counts come from the weekly source; play-by-play supplies the special-teams /
own-vs-opponent / lost split; the Sleeper comparison covers rostered players only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval import league_scoring_audit as lsa  # noqa: E402
from src.dynasty_genius.eval.run_provenance import launch_provenance  # noqa: E402

OUTPUTS = ("components.csv", "event_ledger.csv", "unattributed_events.csv", "reconciliation.csv", "unresolved.csv",
           "quarantine_reaudit.csv", "report.md")


def _render(m: dict, rec: pd.DataFrame, comps: pd.DataFrame) -> str:
    c = m["coverage"]
    lines = [f"# DG-177 league scoring component audit — season {m['season']}\n",
             f"Settings sha `{m['settings_sha256'][:12]}…` · individual keys credited {m['individual_keys_credited']} · "
             f"team keys never applied {m['team_keys_never_applied_to_individuals']} · launch git `{m['launch']['git_head'][:8]}` "
             f"dirty={m['launch']['git_dirty']}\n",
             "## Coverage (rostered Sleeper player-weeks vs weekly source)\n",
             f"- weekly REG player-weeks {c['weekly_player_weeks_reg']} (championship weeks 1–17: {c['weekly_player_weeks_championship']})",
             f"- Sleeper player-weeks {c['sleeper_player_weeks']} (championship: {c['sleeper_player_weeks_championship']}), players "
             f"{c['sleeper_players']}; identity resolved {c['identity_resolved']} / unmapped {c['identity_unmapped']} / ambiguous "
             f"{c['identity_ambiguous']}; equal duplicate observations collapsed {c['sleeper_duplicate_observations_collapsed']}, "
             f"conflicting {c['sleeper_conflicting_duplicates']}",
             f"- all REG weeks: exact {c['status_exact']} · attributed difference {c['status_attributed_difference']} · absent-zero "
             f"{c['status_absent_zero']} · unresolved {c['status_unresolved']}",
             f"- championship weeks 1–17: exact {c['status_exact_championship']} · attributed difference "
             f"{c['status_attributed_difference_championship']} · absent-zero {c['status_absent_zero_championship']} · unresolved "
             f"{c['status_unresolved_championship']}",
             f"- reconciliation unresolved by reason: {c['reconciliation_unresolved_by_reason']}",
             f"- component weeks unresolved by reason: {c['components_unresolved_by_reason']}",
             f"- {c['population_note']}",
             f"- event ledger: {m['event_coverage']}",
             f"- quarantine re-audit (ALL rows, every season): {m['quarantine_reaudit']}\n",
             f"## Exact-league qualification: {m['league_scoring_exact']}\n", *[f"- {r}" for r in m["qualification_reasons"]], "",
             "## Differences vs research PPR (attributed) and unresolved rows (ids, never names)\n"]
    show = rec[rec.status.isin(["attributed_difference", "unresolved"])]
    lines.append(show[["week", "sleeper_id", "gsis_id", "sleeper_points", "research_ppr", "league_points", "diff_vs_research",
                       "diff_vs_league", "unresolved_reason", "reconciliation_reason", "status"]].to_string(index=False) if len(show) else "none")
    lines.append("\n## Championship-window population deltas (all weekly rows, weeks 1–17; league − research)\n")
    for label, key in (("offensive positions (QB/RB/WR/TE)", "window_delta_offense"), ("other positions", "window_delta_other")):
        b = c[key]
        lines.append(f"- {label}: player-weeks {b['player_weeks']}, nonzero delta {b['nonzero_player_weeks']}, sum {b['sum']}, "
                     f"min {b['min']} max {b['max']}, unresolved {b['unresolved_player_weeks']}")
    lines.append("- recovery touchdowns by defenders would score under the individual key fum_rec_td, but this league starts no "
                 "defender; the offensive line is the league-relevant effect")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("--weekly", "--quarantine", "--pbp", "--sleeper-season-dir", "--league-snapshot", "--idmap"):
        ap.add_argument(a, required=True, type=Path)
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--out-root", type=Path, default=ROOT / "runs")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)
    launch = launch_provenance(repo_root=ROOT, argv=sys.argv if argv is None else argv)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_root / run_id / "dg177_league_scoring_audit"
    if out_dir.exists():
        print(f"refusing: {out_dir} exists (runs are immutable)", file=sys.stderr)
        return 1
    try:
        # every input is read ONCE; the bytes hashed into the manifest are the bytes parsed below
        cap = {name: lsa.CapturedSource(getattr(args, name)) for name in ("weekly", "quarantine", "pbp", "league_snapshot", "idmap")}
        matchups = {p.name: lsa.CapturedSource(p) for p in sorted(args.sleeper_season_dir.glob("matchups_week_*.json"))}
        league_json = lsa.CapturedSource(args.sleeper_season_dir / "league.json")
        sources = {**{name: src.describe() for name, src in cap.items()},
                   "sleeper_matchups": {name: src.describe() for name, src in matchups.items()},
                   "sleeper_league": league_json.describe()}
        settings = cap["league_snapshot"].json()["league"]["scoring_settings"]
        lsa.assert_settings_match(settings, league_json.json()["payload"]["scoring_settings"])
        classification = lsa.classify_scoring_keys(settings)
        weekly = cap["weekly"].frame()
        weekly = weekly[pd.to_numeric(weekly["season"], errors="coerce") == args.season]
        pbp = cap["pbp"].frame()
        if "season" in pbp:
            pbp = pbp[pd.to_numeric(pbp["season"], errors="coerce") == args.season]
        if "season_type" in pbp:
            pbp = pbp[pbp["season_type"] == "REG"]
        events = lsa.extract_fumble_events(pbp)
        comps = lsa.player_week_components(weekly, events)
        sleeper = lsa.sleeper_week_points_from_payloads({int(n[-7:-5]): src.json()["payload"] for n, src in matchups.items()})
        identity = lsa.map_sleeper_ids(sleeper["sleeper_id"], cap["idmap"].frame()[["sleeper_id", "gsis_id"]])
        rec = lsa.reconcile(comps, sleeper, identity, settings)
        quar_audit = lsa.audit_quarantine(cap["quarantine"].frame(), settings, audit_season=args.season)   # ALL rows, every season
        event_cov = lsa.event_coverage(events, comps)
        counts = {**lsa.coverage_counts(comps, rec, sleeper, identity), **lsa.window_delta_summary(comps, settings),
                  "events_total": event_cov["events_total"], "events_unattributed": event_cov["events_missing_player_id"],
                  "events_ambiguous": int((events["status"] == "ambiguous").sum()) if len(events) else 0,
                  "events_nullified": int((events["status"] == "nullified").sum()) if len(events) else 0}
        kickers = bool(weekly["position"].isin(["K", "P"]).any()) if "position" in weekly else False
        qual = lsa.exact_qualification(classification, counts, kicker_rows_present=kickers)
    except lsa.ScoringAuditError as err:
        print(f"refusing: {err}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True)
    comps.to_csv(out_dir / "components.csv", index=False)
    events.to_csv(out_dir / "event_ledger.csv", index=False)
    # events that could not be attributed to a verified player/side never disappear: they are listed here and counted
    lsa.unattributed_events(events, comps).to_csv(out_dir / "unattributed_events.csv", index=False)
    rec.to_csv(out_dir / "reconciliation.csv", index=False)
    pd.concat([rec[rec.status == "unresolved"].assign(source="reconciliation"),
               comps[comps.attribution_status == "unresolved"].assign(source="components")],
              ignore_index=True).to_csv(out_dir / "unresolved.csv", index=False)
    quar_audit.to_csv(out_dir / "quarantine_reaudit.csv", index=False)
    manifest = lsa.build_audit_manifest(sources=sources, settings=settings, classification=classification, counts=counts,
                                        qualification=qual, launch=launch, outputs={})
    manifest["season"] = args.season
    manifest["quarantine_reaudit"] = lsa.quarantine_summary(quar_audit)
    manifest["event_coverage"] = event_cov
    (out_dir / "report.md").write_text(_render(manifest, rec, comps))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in OUTPUTS}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(f"wrote {out_dir}")
    print((out_dir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
