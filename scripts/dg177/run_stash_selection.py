#!/usr/bin/env python
"""DG-177 stash-selection evaluation — actual-data runner (report-only; nothing is fitted).

    .venv/bin/python scripts/dg177/run_stash_selection.py \\
      --history  runs/20260906T195728Z/dg177_basic_horizons/historical_predictions.csv \\
      --cohort   runs/20260906T195728Z/dg177_basic_horizons/basic_cohort.csv.gz \\
      --outcomes /Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/outcomes.csv \\
      --outcomes-manifest /Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/manifest.json \\
      --draft    /Users/davidleess/dynasty-genius-product/app/data/backtest/qb_validation/raw/draft_picks/draft_picks_full.parquet \\
      --definitions docs/experiments/stash_selection_definitions_v3.json \\
      --bindings docs/experiments/stash_selection_bindings_v1.json --out-root runs

A production run binds its inputs semantically: captured bytes must match the accepted producers' hashes in
`--bindings`, and the outcome manifest's target identity and last complete season must match. Fixture flags
(`--nonproduction`, `--bars-override`, `--origins`) mark the run nonproduction. Writes a NEW immutable
runs/<ts>/dg177_stash_selection/. Frozen inputs only; no forecast, label or model is touched.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval import stash_selection as ss  # noqa: E402
from src.dynasty_genius.eval.league_scoring_audit import CapturedSource  # noqa: E402
from src.dynasty_genius.eval.run_provenance import launch_provenance  # noqa: E402

OUTPUTS = ("primary_candidates.csv", "cohort_ledger.csv", "summed_future_rows.csv", "summed_future_rows_strict.csv",
           "secondary_2_5_rows.csv", "year1_rows.csv", "bars_primary.csv", "bars_strict.csv", "metrics.json", "season_table.csv",
           "selection.csv", "report.md")
PAIRS = (("rank_future_sum", "rank_origin_points"), ("rank_future_sum", "rank_draft"), ("rank_future_sum", "rank_persistence"),
         ("rank_future_sum", "rank_future_year1"))


def _frame(src: CapturedSource) -> pd.DataFrame:
    name = src.path.name
    if name.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(src.bytes))
    if name.endswith(".gz"):
        return pd.read_csv(io.BytesIO(src.bytes), compression="gzip", low_memory=False)
    return pd.read_csv(io.BytesIO(src.bytes), low_memory=False)


def _check_bindings(bindings: dict, cap: dict, outcomes_manifest: dict | None, last_complete_season: int,
                    outcomes_manifest_sha256: str | None = None) -> None:
    for name, key in (("history", "history_sha256"), ("cohort", "cohort_sha256"), ("outcomes", "outcomes_sha256")):
        if cap[name].sha256 != bindings.get(key):
            raise ss.StashSelectionError(f"binding failed: {name} bytes {cap[name].sha256[:12]}… are not the accepted {str(bindings.get(key))[:12]}…")
    if outcomes_manifest is None:
        raise ss.StashSelectionError("binding failed: a production run needs --outcomes-manifest for the target identity")
    if outcomes_manifest_sha256 != bindings.get("outcomes_manifest_sha256"):
        raise ss.StashSelectionError("binding failed: the captured outcome manifest bytes are not the accepted manifest "
                                     f"({str(outcomes_manifest_sha256)[:12]}… vs {str(bindings.get('outcomes_manifest_sha256'))[:12]}…)")
    if outcomes_manifest.get("target_identity") != bindings.get("target_identity"):
        raise ss.StashSelectionError("binding failed: outcome manifest target_identity is not the accepted target")
    if int(outcomes_manifest.get("last_complete_season", -1)) != int(bindings.get("last_complete_season", -2)) or \
            int(last_complete_season) != int(bindings.get("last_complete_season", -2)):
        raise ss.StashSelectionError("binding failed: incoherent last complete season between the manifest, the bindings and the run")


def _evaluate(rows: pd.DataFrame, budgets, draws: int, seed: int, flag_col: str = "contributor_any") -> dict:
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
    for future, comparator in PAIRS:
        key = f"{future}_minus_{comparator}"
        boots[key] = {"rank": {m: ss.paired_rank_bootstrap(rows, m, comparator, future, draws=draws, seed=seed, flag_col=flag_col)
                               for m in ("spearman", "auc")},
                      "selection": ss.paired_selection_bootstrap(rows, comparator, future, budget=budgets[0], flag_col=flag_col,
                                                                 draws=draws, seed=seed),
                      "selection_by_budget": {str(b): ss.paired_selection_bootstrap(rows, comparator, future, budget=b, flag_col=flag_col,
                                                                                    draws=draws, seed=seed) for b in budgets[1:]}}
    out["bootstrap"] = boots
    return out


def _fmt(v) -> str:
    return "undefined" if v is None or (isinstance(v, float) and v != v) else f"{v:.3f}"


def _render(m: dict, metrics: dict) -> str:
    c = m["counts"]
    p = metrics["primary"]
    lines = [f"# DG-177 stash-selection evaluation — {m['claim']}\n",
             f"Definitions `{m['definitions']['version']}` sha `{m['definitions']['sha256'][:12]}…` · nonproduction={m['nonproduction']} · "
             f"launch git `{m['launch']['git_head'][:8]}` (tracked dirty={m['launch']['tracked_dirty']}) · conditional on {m['uncertainty_conditional_on']}\n",
             "## Cohort (drafted early-career not-yet-contributor screen)\n",
             f"- ledger rows {c['ledger_rows']} over origins {c['origins']}; primary candidates {c['primary_candidates']}; "
             f"ledger exclusions {c['ledger_exclusions']}; draft conflicts {c['draft_conflicting_ids']}, invalid draft ids {c['draft_invalid_ids']}",
             f"- summed t+2/t+3 test rows {p['n_rows']} ({p['n_players']} players; origins {p['origins']}); exclusions {c['exclusions']}; "
             f"repeated players {c['repeated_players']}",
             f"- bars primary {m['bars']['primary']} strict {m['bars']['strict']}; short panels primary {c['short_panels_primary']} strict {c['short_panels_strict']}",
             f"- panel caveat: {m['panel_caveat']}\n",
             "## Primary test: summed t+2/t+3 (pooled over origin × position cells)\n",
             "| ordering | n | Spearman | AUC | hits@2 | misses@2 | busts@2 | points@2 | points/slot@2 |", "|---|---|---|---|---|---|---|---|---|"]
    for col, v in p.get("pooled", {}).items():
        s2 = v["selection"]["2"]
        lines.append(f"| {col} | {v['spearman']['n']} | {_fmt(v['spearman']['value'])} | {_fmt(v['auc']['value'])} | {s2['hits']:.1f} | "
                     f"{s2['misses']:.1f} | {s2['busts']:.1f} | {s2['points_captured']:.0f} | {_fmt(s2['points_per_slot'])} |")
    lines.append("\n### Paired differences, future minus comparator (joint support; 90% player-cluster intervals; draws requested/finite)\n")
    for k, v in p.get("bootstrap", {}).items():
        rk = v["rank"]
        sel = v["selection"]
        lines.append(f"- {k}: Spearman {rk['spearman']['point']:+.3f} [{rk['spearman']['ci90'][0]:+.3f}, {rk['spearman']['ci90'][1]:+.3f}] "
                     f"(joint cells {rk['spearman']['cells_joint']}, excluded {rk['spearman']['cells_excluded']}, draws {rk['spearman']['draws_requested']}/{rk['spearman']['draws_finite']}); "
                     f"AUC {rk['auc']['point']:+.3f} [{rk['auc']['ci90'][0]:+.3f}, {rk['auc']['ci90'][1]:+.3f}]; "
                     f"hits@2 {sel['point']['hits']:+.1f} [{sel['ci90']['hits'][0]:+.1f}, {sel['ci90']['hits'][1]:+.1f}]; "
                     f"points@2 {sel['point']['points']:+.0f} [{sel['ci90']['points'][0]:+.0f}, {sel['ci90']['points'][1]:+.0f}] "
                     f"(draws {sel['draws_requested']}/{sel['draws_finite']}; {sel['estimand']})")
    lines.append("\n### No-record-as-unknown bounds at budget 2 (same fractional weights)\n")
    for col, b in p.get("bounds_no_record_unknown", {}).items():
        lines.append(f"- {col}: hits lower {b['2']['hits_lower']:.1f}, upper {b['2']['hits_upper']:.1f}, boundary ties {b['2']['boundary_ties']}")
    for title, key in (("Strict-bar label sensitivity (cohort fixed)", "primary_strict"), ("Immediate help (year 1) — separate analysis", "year1")):
        lines.append(f"\n## {title}\n")
        for col, v in metrics.get(key, {}).get("pooled", {}).items():
            lines.append(f"- {col}: Spearman {_fmt(v['spearman']['value'])}, AUC {_fmt(v['auc']['value'])}, hits@2 {v['selection']['2']['hits']:.1f}, "
                         f"points/slot@2 {_fmt(v['selection']['2']['points_per_slot'])}")
    sec = metrics.get("secondary_2_5", {})
    lines.append(f"\n## Exploratory secondary: summed years 2–5 — ONE ORIGIN ONLY ({sec.get('origins')}); rows {sec.get('n_rows')}; "
                 f"exclusions {sec.get('exclusions')}\n")
    for col, v in sec.get("pooled", {}).items():
        lines.append(f"- {col}: Spearman {_fmt(v['spearman']['value'])}, AUC {_fmt(v['auc']['value'])}, hits@2 {v['selection']['2']['hits']:.1f}")
    lines.append(f"\n## Claims not made\n- {m['claim']}\n- {m['not_an_untouched_confirmation_meaning']}\n- {m['year5_disclosure']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("--history", "--cohort", "--outcomes", "--draft", "--definitions"):
        ap.add_argument(a, required=True, type=Path)
    ap.add_argument("--outcomes-manifest", type=Path, default=None)
    ap.add_argument("--bindings", type=Path, default=None, help="accepted-producer bindings; required unless --nonproduction")
    ap.add_argument("--nonproduction", action="store_true", help="fixture run: skips bindings, marked in the manifest")
    ap.add_argument("--last-complete-season", type=int, default=2025)
    ap.add_argument("--bars-override", default=None, help="JSON dict; fixtures only, marks the run nonproduction")
    ap.add_argument("--origins", nargs=2, type=int, default=None, help="fixtures only, marks the run nonproduction")
    ap.add_argument("--draws", type=int, default=None)
    ap.add_argument("--out-root", type=Path, default=ROOT / "runs")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)
    launch = launch_provenance(repo_root=ROOT, argv=sys.argv if argv is None else argv)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not ss.valid_run_id(run_id):
        print(f"refusing: run id {run_id!r} is not a bounded timestamp component", file=sys.stderr)
        return 1
    out_dir = args.out_root / run_id / "dg177_stash_selection"
    if out_dir.exists():
        print(f"refusing: {out_dir} exists (runs are immutable)", file=sys.stderr)
        return 1
    nonprod_reasons = [r for r, on in (("--nonproduction", args.nonproduction), ("--bars-override", bool(args.bars_override)),
                                       ("--origins", bool(args.origins)), ("--draws", args.draws is not None)) if on]
    try:
        if not args.definitions.exists():
            raise ss.StashSelectionError(f"frozen definitions file {args.definitions} is missing; refusing to run")
        defs = ss.load_definitions(args.definitions)
        cap = {name: CapturedSource(getattr(args, name)) for name in ("history", "cohort", "outcomes", "draft")}
        sources = {name: src.describe() for name, src in cap.items()}
        outcomes_manifest, outcomes_manifest_sha = None, None
        if args.outcomes_manifest is not None:
            om = CapturedSource(args.outcomes_manifest)
            sources["outcomes_manifest"] = om.describe()
            outcomes_manifest, outcomes_manifest_sha = om.json(), om.sha256
        bindings = None
        if not nonprod_reasons:
            if args.bindings is None:
                raise ss.StashSelectionError("binding failed: a production run needs --bindings (or declare --nonproduction)")
            bsrc = CapturedSource(args.bindings)
            sources["bindings"] = bsrc.describe()
            bindings = bsrc.json()
            _check_bindings(bindings, cap, outcomes_manifest, args.last_complete_season, outcomes_manifest_sha)
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
        vd = ss.validated_draft(draft)
        ledger = pd.concat([ss.primary_cohort_ledger(cohort, outcomes, draft, definitions=defs, bars=bars_primary, origin=o)
                            for o in range(lo, hi + 1)], ignore_index=True)
        cands = ledger[ledger["exclusion_reason"] == ""].reset_index(drop=True)
        lcs = args.last_complete_season
        summed = ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=lcs)
        summed_strict = ss.summed_future_rows(cands, history, outcomes, panel_strict, last_complete_season=lcs)
        rows, rows_strict = ss.v2_orderings(summed), ss.v2_orderings(summed_strict)
        year1 = ss.v2_orderings(ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=lcs, horizons=(1,)))
        sec = ss.v2_orderings(ss.summed_future_rows(cands, history, outcomes, panel_primary, last_complete_season=lcs, horizons=(2, 3, 4, 5)))
        metrics = {"primary": _evaluate(rows, budgets, draws, seed), "primary_strict": _evaluate(rows_strict, budgets, draws, seed),
                   "year1": _evaluate(year1, budgets, draws, seed), "secondary_2_5": _evaluate(sec, budgets, draws, seed)}
        for key, frame in (("primary", summed), ("primary_strict", summed_strict), ("year1", year1), ("secondary_2_5", sec)):
            metrics[key]["exclusions"] = frame.attrs.get("exclusions", {})
        season = ss.season_table(rows, list(ss.V2_ORDERINGS), budget=budgets[0])
        selection = pd.concat([ss.select_at_budget(rows, col, b, "contributor_any") for col in ss.V2_ORDERINGS for b in budgets], ignore_index=True)
        counts = {"origins": [lo, hi], "ledger_rows": int(len(ledger)), "primary_candidates": int(len(cands)),
                  "ledger_exclusions": {k: int(v) for k, v in ledger["exclusion_reason"].value_counts().items() if k},
                  "draft_conflicting_ids": int(len(vd.attrs.get("conflicting_ids", []))), "draft_invalid_ids": int(vd.attrs.get("invalid_ids", 0)),
                  "exclusions": summed.attrs["exclusions"], "repeated_players": int((cands.groupby("player_id").size() > 1).sum()),
                  "short_panels_primary": int(panel_primary["short_panel"].sum()), "short_panels_strict": int(panel_strict["short_panel"].sum())}
        metrics_json = json.dumps(ss.to_jsonable(metrics), indent=2, allow_nan=False)
    except ss.StashSelectionError as err:
        print(f"refusing: {err}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True)
    cands.to_csv(out_dir / "primary_candidates.csv", index=False)
    ledger.to_csv(out_dir / "cohort_ledger.csv", index=False)
    rows.to_csv(out_dir / "summed_future_rows.csv", index=False)
    rows_strict.to_csv(out_dir / "summed_future_rows_strict.csv", index=False)
    sec.to_csv(out_dir / "secondary_2_5_rows.csv", index=False)
    year1.to_csv(out_dir / "year1_rows.csv", index=False)
    panel_primary.to_csv(out_dir / "bars_primary.csv", index=False)
    panel_strict.to_csv(out_dir / "bars_strict.csv", index=False)
    season.to_csv(out_dir / "season_table.csv", index=False)
    selection.to_csv(out_dir / "selection.csv", index=False)
    (out_dir / "metrics.json").write_text(metrics_json + "\n")
    manifest = ss.build_manifest(definitions=defs, sources=sources, launch=launch, counts=counts, outputs={},
                                 bars_override_used=bool(args.bars_override), origins_override=list(args.origins) if args.origins else None)
    manifest.update({"nonproduction": bool(nonprod_reasons), "nonproduction_reasons": nonprod_reasons, "bindings": bindings,
                     "panel_caveat": defs.get("panel_caveat", ""), "bars": {"primary": bars_primary, "strict": bars_strict},
                     "last_complete_season": lcs, "budgets": list(budgets), "draws": draws, "seed": seed})
    (out_dir / "report.md").write_text(_render(manifest, metrics))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in OUTPUTS}
    (out_dir / "manifest.json").write_text(json.dumps(ss.to_jsonable(manifest), indent=2, allow_nan=False, default=str) + "\n")
    print(f"wrote {out_dir}")
    print((out_dir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
