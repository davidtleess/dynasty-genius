#!/usr/bin/env python
"""DG-177 stash-selection evaluation — actual-data runner (report-only; nothing is fitted).

    .venv/bin/python scripts/dg177/run_stash_selection.py \\
      --history  runs/20260906T195728Z/dg177_basic_horizons/historical_predictions.csv \\
      --cohort   runs/20260906T195728Z/dg177_basic_horizons/basic_cohort.csv.gz \\
      --outcomes /Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/outcomes.csv \\
      --draft    /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/draft_picks/draft_picks_full.parquet \\
      --definitions docs/experiments/stash_selection_definitions_v3.json --out-root runs

Writes a NEW runs/<ts>/dg177_stash_selection/ (refuses an existing one). The frozen definitions file is hashed into
the manifest; a run without it refuses. Frozen inputs only; no forecast, label or model is touched.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval import stash_selection as ss  # noqa: E402
from src.dynasty_genius.eval.league_scoring_audit import CapturedSource  # noqa: E402
from src.dynasty_genius.eval.run_provenance import launch_provenance  # noqa: E402

OUTPUTS = ("primary_candidates.csv", "cohort_ledger.csv", "summed_future_rows.csv", "secondary_2_5_rows.csv", "year1_rows.csv",
           "metrics.json", "season_table.csv", "selection.csv", "report.md")
PAIRS = (("rank_future_sum", "rank_origin_points"), ("rank_future_sum", "rank_draft"), ("rank_future_sum", "rank_persistence"),
         ("rank_future_sum", "rank_future_year1"))


def _frame(src: CapturedSource) -> pd.DataFrame:
    name = src.path.name
    if name.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(src.bytes))
    if name.endswith(".gz"):
        return pd.read_csv(io.BytesIO(src.bytes), compression="gzip", low_memory=False)
    return pd.read_csv(io.BytesIO(src.bytes), low_memory=False)


def _evaluate(rows: pd.DataFrame, budgets, draws: int, seed: int, flag_col: str = "contributor_any") -> dict:
    """Pooled metrics, per-position metrics, selection at every budget with bounds, and paired bootstraps."""
    out = {"n_rows": int(len(rows)), "n_players": int(rows["player_id"].nunique()) if len(rows) else 0,
           "origins": sorted(int(o) for o in rows["origin"].unique()) if len(rows) else []}
    if not len(rows):
        return out
    cmp = ss.compare_orderings(rows, list(ss.V2_ORDERINGS), budgets=budgets, flag_col=flag_col)
    out["pooled"] = cmp["pooled"]
    out["by_position"] = {pos: ss.compare_orderings(g, list(ss.V2_ORDERINGS), budgets=budgets, flag_col=flag_col)["pooled"]
                          for pos, g in rows.groupby("position")}
    out["bounds_no_record_unknown"] = {col: {str(b): ss.selection_bounds_no_record_unknown(rows, col, b, flag_col) for b in budgets}
                                       for col in ss.V2_ORDERINGS}
    boots = {}
    for a, b in PAIRS:
        for name, fn in (("spearman", ss.metric_fn("spearman")), ("auc", ss.metric_fn("auc", flag_col=flag_col)),
                         ("hits_at_budget_2", ss.metric_fn("hits_at_budget", budget=2, flag_col=flag_col)),
                         ("points_at_budget_2", ss.metric_fn("points_at_budget", budget=2, flag_col=flag_col))):
            boots[f"{a}_minus_{b}"] = boots.get(f"{a}_minus_{b}", {})
            boots[f"{a}_minus_{b}"][name] = ss.paired_difference_bootstrap(rows, fn, b, a, draws=draws, seed=seed)
    # the dictionary key reads "future minus comparator": metric(future) − metric(comparator)
    out["bootstrap"] = {k: {**v, "draws": v[next(iter(v))]["draws"]} for k, v in boots.items()}
    return out


def _render(m: dict, metrics: dict) -> str:
    c = m["counts"]
    p = metrics["primary"]
    lines = [f"# DG-177 stash-selection evaluation — {m['claim']}\n",
             f"Definitions `{m['definitions']['version']}` sha `{m['definitions']['sha256'][:12]}…` · launch git `{m['launch']['git_head'][:8]}` "
             f"(tracked dirty={m['launch']['tracked_dirty']}) · conditional on {m['uncertainty_conditional_on']}\n",
             "## Cohort (drafted early-career not-yet-contributor screen)\n",
             f"- cohort ledger rows {c['ledger_rows']} over origins {c['origins']}; primary candidates {c['primary_candidates']}; "
             f"exclusions {c['ledger_exclusions']}",
             f"- summed t+2/t+3 test rows {p['n_rows']} ({p['n_players']} players; origins {p['origins']}); exclusions {c['exclusions']}",
             f"- panel caveat: {m['panel_caveat']}\n",
             "## Primary test: summed t+2/t+3 (pooled over origin × position cells; Spearman vs realized points, AUC for contributor)\n",
             "| ordering | n | Spearman | AUC | hits@2 | misses@2 | busts@2 | points@2 |", "|---|---|---|---|---|---|---|---|"]
    for col, v in p.get("pooled", {}).items():
        s2 = v["selection"]["2"]
        lines.append(f"| {col} | {v['spearman']['n']} | {v['spearman']['value']:.3f} | {v['auc']['value']:.3f} | {s2['hits']:.1f} | "
                     f"{s2['misses']:.1f} | {s2['busts']:.1f} | {s2['points_captured']:.0f} |")
    lines.append("\n### Paired player-cluster bootstrap differences, future minus comparator (90% intervals)\n")
    for k, v in p.get("bootstrap", {}).items():
        parts = [f"{name}: {r['point']:+.3f} [{r['ci90'][0]:+.3f}, {r['ci90'][1]:+.3f}]" for name, r in v.items() if isinstance(r, dict)]
        lines.append(f"- {k}: " + "; ".join(parts))
    lines.append("\n### No-record-as-unknown bounds at budget 2 (same fractional weights)\n")
    for col, b in p.get("bounds_no_record_unknown", {}).items():
        lines.append(f"- {col}: hits lower {b['2']['hits_lower']:.1f}, upper {b['2']['hits_upper']:.1f}, boundary ties {b['2']['boundary_ties']}")
    lines.append("\n## Strict-bar label sensitivity (cohort fixed)\n")
    for col, v in metrics.get("primary_strict", {}).get("pooled", {}).items():
        lines.append(f"- {col}: Spearman {v['spearman']['value']:.3f}, AUC {v['auc']['value']:.3f}, hits@2 {v['selection']['2']['hits']:.1f}")
    lines.append("\n## Immediate help (year 1) — separate analysis\n")
    for col, v in metrics.get("year1", {}).get("pooled", {}).items():
        lines.append(f"- {col}: Spearman {v['spearman']['value']:.3f}, AUC {v['auc']['value']:.3f}, hits@2 {v['selection']['2']['hits']:.1f}")
    sec = metrics.get("secondary_2_5", {})
    lines.append(f"\n## Exploratory secondary: summed years 2–5 — ONE ORIGIN ONLY ({sec.get('origins')}); rows {sec.get('n_rows')}\n")
    for col, v in sec.get("pooled", {}).items():
        lines.append(f"- {col}: Spearman {v['spearman']['value']:.3f}, AUC {v['auc']['value']:.3f}, hits@2 {v['selection']['2']['hits']:.1f}")
    lines.append(f"\n## Claims not made\n- {m['claim']}\n- {m['not_an_untouched_confirmation_meaning']}\n- {m['year5_disclosure']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("--history", "--cohort", "--outcomes", "--draft", "--definitions"):
        ap.add_argument(a, required=True, type=Path)
    ap.add_argument("--last-complete-season", type=int, default=2025)
    ap.add_argument("--bars-override", default=None, help="JSON dict; fixtures only, disclosed in the manifest")
    ap.add_argument("--origins", nargs=2, type=int, default=None, help="fixtures only, disclosed in the manifest")
    ap.add_argument("--draws", type=int, default=None)
    ap.add_argument("--out-root", type=Path, default=ROOT / "runs")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)
    launch = launch_provenance(repo_root=ROOT, argv=sys.argv if argv is None else argv)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_root / run_id / "dg177_stash_selection"
    if out_dir.exists():
        print(f"refusing: {out_dir} exists (runs are immutable)", file=sys.stderr)
        return 1
    try:
        if not args.definitions.exists():
            raise ss.StashSelectionError(f"frozen definitions file {args.definitions} is missing; refusing to run")
        defs = ss.load_definitions(args.definitions)
        cap = {name: CapturedSource(getattr(args, name)) for name in ("history", "cohort", "outcomes", "draft")}
        sources = {name: src.describe() for name, src in cap.items()}
        history, cohort, outcomes, draft = (_frame(cap[k]) for k in ("history", "cohort", "outcomes", "draft"))
        bars_primary = json.loads(args.bars_override) if args.bars_override else defs["contribution_bars"]["primary"]
        bars_strict = defs["contribution_bars"]["strict_sensitivity"] if not args.bars_override else {k: max(1, v - 1) for k, v in bars_primary.items()}
        lo, hi = args.origins if args.origins else defs["origins"]["feature_seasons"]
        budgets = (defs["budgets"]["primary_per_position_per_origin"], *defs["budgets"]["sensitivity"])
        draws = args.draws or defs["uncertainty"]["draws"]
        seed = defs["uncertainty"]["seed"]
        cohort = cohort[cohort["position"].isin(bars_primary)]
        panel_primary = ss.contribution_bars(cohort, outcomes, bars=bars_primary)
        panel_strict = ss.contribution_bars(cohort, outcomes, bars=bars_strict)
        ledgers = [ss.primary_cohort_ledger(cohort, outcomes, draft, definitions=defs, bars=bars_primary, origin=o) for o in range(lo, hi + 1)]
        ledger = pd.concat(ledgers, ignore_index=True)
        cands = ledger[ledger["exclusion_reason"] == ""].reset_index(drop=True)
        summed = ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=args.last_complete_season)
        summed_strict = ss.summed_future_rows(cands, history, outcomes, panel_strict, last_complete_season=args.last_complete_season)
        rows = ss.v2_orderings(summed)
        rows_strict = ss.v2_orderings(summed_strict)
        year1 = ss.v2_orderings(ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=args.last_complete_season, horizons=(1,)))
        sec = ss.v2_orderings(ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=args.last_complete_season, horizons=(2, 3, 4, 5)))
        metrics = {"primary": _evaluate(rows, budgets, draws, seed), "primary_strict": _evaluate(rows_strict, budgets, draws, seed),
                   "year1": _evaluate(year1, budgets, draws, seed), "secondary_2_5": _evaluate(sec, budgets, draws, seed)}
        metrics["primary"]["exclusions"] = summed.attrs["exclusions"]
        metrics["year1"]["exclusions"] = year1.attrs["exclusions"]
        metrics["secondary_2_5"]["exclusions"] = sec.attrs["exclusions"]
        season = ss.season_table(rows, list(ss.V2_ORDERINGS), budget=budgets[0])
        selection = pd.concat([ss.select_at_budget(rows, col, b, "contributor_any") for col in ss.V2_ORDERINGS for b in budgets], ignore_index=True)
        counts = {"origins": [lo, hi], "ledger_rows": int(len(ledger)), "primary_candidates": int(len(cands)),
                  "ledger_exclusions": {k: int(v) for k, v in ledger["exclusion_reason"].value_counts().items() if k},
                  "exclusions": summed.attrs["exclusions"], "repeated_players": int((cands.groupby("player_id").size() > 1).sum()),
                  "short_panels_primary": int(panel_primary["short_panel"].sum()), "short_panels_strict": int(panel_strict["short_panel"].sum())}
    except ss.StashSelectionError as err:
        print(f"refusing: {err}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True)
    cands.to_csv(out_dir / "primary_candidates.csv", index=False)
    ledger.to_csv(out_dir / "cohort_ledger.csv", index=False)
    rows.to_csv(out_dir / "summed_future_rows.csv", index=False)
    sec.to_csv(out_dir / "secondary_2_5_rows.csv", index=False)
    year1.to_csv(out_dir / "year1_rows.csv", index=False)
    season.to_csv(out_dir / "season_table.csv", index=False)
    selection.to_csv(out_dir / "selection.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=lambda v: None if isinstance(v, float) and np.isnan(v) else str(v)) + "\n")
    manifest = ss.build_manifest(definitions=defs, sources=sources, launch=launch, counts=counts, outputs={},
                                 bars_override_used=bool(args.bars_override), origins_override=list(args.origins) if args.origins else None)
    manifest["panel_caveat"] = defs.get("panel_caveat", "")
    manifest["bars"] = {"primary": bars_primary, "strict": bars_strict}
    (out_dir / "report.md").write_text(_render(manifest, metrics))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in OUTPUTS}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(f"wrote {out_dir}")
    print((out_dir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
