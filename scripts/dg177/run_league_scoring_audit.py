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

OUTPUTS = ("components.csv", "event_ledger.csv", "reconciliation.csv", "unresolved.csv", "quarantine_reaudit.csv", "report.md")


def _sha(path: Path) -> dict:
    b = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def _read(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


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
             f"- {c['population_note']}\n",
             f"## Exact-league qualification: {m['league_scoring_exact']}\n", *[f"- {r}" for r in m["qualification_reasons"]], "",
             "## Differences vs research PPR (attributed) and unresolved rows (ids, never names)\n"]
    show = rec[rec.status.isin(["attributed_difference", "unresolved"])]
    lines.append(show[["week", "sleeper_id", "gsis_id", "sleeper_points", "research_ppr", "league_points", "diff_vs_research",
                       "diff_vs_league", "unresolved_reason", "reconciliation_reason", "status"]].to_string(index=False) if len(show) else "none")
    lines.append("\n## Championship-window population deltas (all weekly rows, weeks 1–17; league − research)\n")
    w = comps[comps.championship_window]
    delta = lsa.league_points(w, m["scoring_settings"]) - lsa.research_ppr_from_components(w)
    lines.append(f"- player-weeks with a nonzero delta: {int((delta.abs() > lsa.TOL).sum())} of {len(w)}; sum {round(float(delta.sum()), 2)}; "
                 f"min {round(float(delta.min()), 2)} max {round(float(delta.max()), 2)}" if len(w) else "- no championship-window rows")
    lines.append(f"- weekly rows unresolved in the window: {int((w.attribution_status == 'unresolved').sum())}")
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
        sources = {"weekly": _sha(args.weekly), "quarantine": _sha(args.quarantine), "pbp": _sha(args.pbp),
                   "league_snapshot": _sha(args.league_snapshot), "idmap": _sha(args.idmap),
                   "sleeper_matchups": {p.name: _sha(p) for p in sorted(args.sleeper_season_dir.glob("matchups_week_*.json"))},
                   "sleeper_league": _sha(args.sleeper_season_dir / "league.json")}
        settings = json.loads(args.league_snapshot.read_bytes())["league"]["scoring_settings"]
        lsa.assert_settings_match(settings, lsa.load_sleeper_settings(args.sleeper_season_dir))
        classification = lsa.classify_scoring_keys(settings)
        weekly = _read(args.weekly)
        weekly = weekly[pd.to_numeric(weekly["season"], errors="coerce") == args.season]
        pbp = _read(args.pbp)
        if "season" in pbp:
            pbp = pbp[pd.to_numeric(pbp["season"], errors="coerce") == args.season]
        if "season_type" in pbp:
            pbp = pbp[pbp["season_type"] == "REG"]
        events = lsa.extract_fumble_events(pbp)
        comps = lsa.player_week_components(weekly, events)
        sleeper = lsa.load_sleeper_week_points(args.sleeper_season_dir)
        identity = lsa.map_sleeper_ids(sleeper["sleeper_id"], _read(args.idmap)[["sleeper_id", "gsis_id"]])
        rec = lsa.reconcile(comps, sleeper, identity, settings)
        quar = _read(args.quarantine)
        if "season" in quar:
            quar = quar[pd.to_numeric(quar["season"], errors="coerce") == args.season]
        quar_audit = lsa.audit_quarantine(quar, settings)
        counts = lsa.coverage_counts(comps, rec, sleeper, identity)
        kickers = bool(weekly["position"].isin(["K", "P"]).any()) if "position" in weekly else False
        qual = lsa.exact_qualification(classification, counts, kicker_rows_present=kickers)
    except lsa.ScoringAuditError as err:
        print(f"refusing: {err}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True)
    comps.to_csv(out_dir / "components.csv", index=False)
    events.to_csv(out_dir / "event_ledger.csv", index=False)
    rec.to_csv(out_dir / "reconciliation.csv", index=False)
    pd.concat([rec[rec.status == "unresolved"].assign(source="reconciliation"),
               comps[comps.attribution_status == "unresolved"].assign(source="components")],
              ignore_index=True).to_csv(out_dir / "unresolved.csv", index=False)
    quar_audit.to_csv(out_dir / "quarantine_reaudit.csv", index=False)
    manifest = lsa.build_audit_manifest(sources=sources, settings=settings, classification=classification, counts=counts,
                                        qualification=qual, launch=launch, outputs={})
    manifest["season"] = args.season
    manifest["quarantine_reaudit"] = {"rows": int(len(quar_audit)),
                                      "nonzero_under_league_keys": int(quar_audit["nonzero_under_league_keys"].sum())}
    (out_dir / "report.md").write_text(_render(manifest, rec, comps))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in OUTPUTS}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(f"wrote {out_dir}")
    print((out_dir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
