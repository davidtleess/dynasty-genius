"""DG-178: grade the ASSEMBLED value C_ij on withheld seasons (review item 8).

Reads both producers' historical per-player predictions with realised labels, grades each
producer alone and both JOINTLY on the seasons they share, per (position, season), under a
stated historical bar proxy (rank by predicted expected points; DG-171 midpoints; +/-5 rank
sensitivity), against each producer's own training-only baseline arm. Writes a run-scoped
report; nothing else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.ranking.grading import (  # noqa: E402
    DEFAULT_BAR_RANKS,
    contributions,
    grade_by_cell,
    grade_multi_season_by_origin,
    historical_reference,
    multi_season_rows_from_single_file,
    rookie_arm_consistency,
    rookie_history_rows,
    veteran_history_rows,
    veteran_multi_season_rows,
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def summarise(cells: dict) -> dict:
    """Pool cell metrics per position across seasons (means), keeping n."""
    out: dict = {}
    by_pos = defaultdict(list)
    for (pos, season), g in cells.items():
        if "skipped" in g:
            continue
        by_pos[pos].append(g)
    for pos, gs in by_pos.items():
        def mean(key):
            vals = [g[key] for g in gs if g.get(key) is not None]
            return (sum(vals) / len(vals)) if vals else None
        out[pos] = {"cells": len(gs), "n_total": sum(g["n"] for g in gs),
                    "spearman_mean": mean("spearman_pred_vs_realised"),
                    "spearman_among_started_mean": mean("spearman_among_started"),
                    "top_k_overlap_mean": mean("top_k_overlap"),
                    "rmse_mean": mean("rmse"),
                    "decision_value_sum": sum(g["decision_value_sum"] for g in gs),
                    "baseline_decision_value_sum": sum(g["baseline_decision_value_sum"] for g in gs)}
    return out


def joint_diagnostics(cand_rows: list[dict], base_rows: list[dict], ranks: dict, n_boot: int = 200) -> dict:
    """On each joint cell: bias of predicted advantage vs realised among retained players by
    producer, with a bootstrap interval and n, and the producer share of the predicted vs
    realised top-k. Residuals are reported with their uncertainty; nothing here explains a
    residual away by the fact that players were selected on their forecast."""
    import numpy as np

    out = {}
    keys = sorted({(r["position"], r["season"]) for r in cand_rows})
    rng = np.random.default_rng(20260906)
    for pos, season in keys:
        rows = [r for r in cand_rows if r["position"] == pos and r["season"] == season]
        brows = [r for r in base_rows if r["position"] == pos and r["season"] == season]
        producers = {r["producer"] for r in rows}
        if len(producers) < 2:
            continue
        try:
            ref = historical_reference(brows, position=pos, season=season, rank=ranks[pos])
        except ValueError:
            continue
        try:
            cs = contributions(rows, reference=ref)  # each arm subtracts its own forecast of him
        except ValueError:
            continue
        k = min({"QB": 12, "RB": 24, "WR": 36, "TE": 12}[pos], len(cs))
        top_pred = sorted(cs, key=lambda c: c.predicted, reverse=True)[:k]
        top_real = sorted(cs, key=lambda c: c.realised_if_started, reverse=True)[:k]
        cell = {"n": len(cs), "k": k, "reference": ref.player_id, "reference_expected": ref.expected_points,
                "reference_realised": ref.realised_points}
        for prod in sorted(producers):
            sub = [c for c in cs if c.producer == prod]
            started = [c for c in sub if c.started]
            biases = np.array([c.predicted - c.realised for c in started])
            ci = None
            if len(biases) >= 3:
                draws = [float(biases[rng.integers(0, len(biases), len(biases))].mean()) for _ in range(n_boot)]
                ci = [float(np.percentile(draws, 5)), float(np.percentile(draws, 95))]
            cell[prod] = {"n": len(sub), "n_retained": len(started),
                          "bias_among_retained": float(biases.mean()) if len(biases) else None,
                          "bias_ci90": ci,
                          "share_of_top_k_predicted": sum(1 for c in top_pred if c.producer == prod) / k,
                          "share_of_top_k_realised": sum(1 for c in top_real if c.producer == prod) / k}
        out[f"{pos}|{season}"] = cell
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--veteran-history", required=True, type=Path)
    ap.add_argument("--veteran-arm", default="recent_production_3col")
    ap.add_argument("--rookie-history", required=True, type=Path)
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    ap.add_argument("--horizons", type=int, default=2,
                    help="how many seasons the veteran history reaches (2 for the annual file, 5 for the basic-horizon file)")
    ap.add_argument("--allow-arm-mismatch", action="store_true",
                    help="grade anyway when the rookie evaluation describes a different arm than the scoring file; recorded")
    ap.add_argument("--veteran-manifest", type=Path, default=None,
                    help="the veteran run's manifest (or corrected manifest); the history file's bytes must match its declared sha256")
    ap.add_argument("--window", choices=["all_reg_weeks", "championship_week17"], default="all_reg_weeks",
                    help="the week window the graded labels must be summed over; both histories' manifests must name it")
    ap.add_argument("--read-mode", choices=["policy", "legacy_arm"], default="policy",
                    help="policy: read the selection policy's policy_* columns only (a fold it never scored is unavailable); "
                         "legacy_arm: read the named raw arm's columns explicitly")
    a = ap.parse_args()
    # The veteran history must be the file its manifest declares: bind the bytes, fail closed.
    vet_man_p = a.veteran_manifest or (a.veteran_history.parent / "manifest.json")
    vet_declared = None
    if vet_man_p.exists():
        vet_declared = ((json.loads(vet_man_p.read_text()).get("outputs_sha256") or {}).get(a.veteran_history.name))
    vet_sha = sha(a.veteran_history)
    if vet_declared is None:
        vet_bind = {"bound": False, "note": f"no manifest at {vet_man_p} declares a sha256 for {a.veteran_history.name}"}
    elif str(vet_declared).lower() != vet_sha:
        vet_bind = {"bound": False, "note": "the manifest's declared sha256 for the history file does not match the bytes read"}
    else:
        vet_bind = {"bound": True, "note": f"history bytes match the sha256 declared in {vet_man_p.name}", "manifest": str(vet_man_p)}
    if not vet_bind["bound"] and not a.allow_arm_mismatch:
        raise SystemExit(f"refusing to grade: {vet_bind['note']} (pass --allow-arm-mismatch to grade it anyway, recorded as UNBOUND)")
    # The rookie history must describe the arm that scores. Refuse otherwise (found 2026-09-06:
    # run 144444Z graded the plain arm while its 2026 scores came from the trend arm).
    # Fail closed: both files must exist and name their arms affirmatively; absence is not agreement.
    man_p, ev_p = a.rookie_history.parent / "manifest.json", a.rookie_history.parent / "evaluation.json"
    if man_p.exists() and ev_p.exists():
        rookie_man = json.loads(man_p.read_text())
        ok, why = rookie_arm_consistency(rookie_man, json.loads(ev_p.read_text()), evaluation_sha256=sha(ev_p))
        # bind the rookie HISTORY bytes too, not only the evaluation file
        declared_hist = (rookie_man.get("outputs_sha256") or {}).get(a.rookie_history.name)
        if ok and declared_hist is None:
            ok, why = False, f"unverified: the rookie manifest declares no sha256 for {a.rookie_history.name}"
        elif ok and str(declared_hist).lower() != sha(a.rookie_history):
            ok, why = False, "the rookie manifest's declared sha256 for the history file does not match the bytes read"
    else:
        ok, why = False, "unverified: manifest.json or evaluation.json missing beside the rookie history"
    arm_check = {"consistent": ok, "note": why, "evidence_status": "verified" if ok else "UNVERIFIED"}
    if not ok and not a.allow_arm_mismatch:
        raise SystemExit(f"refusing to grade: {why} (pass --allow-arm-mismatch to grade it anyway, recorded as UNVERIFIED)")
    # Week-17 queue: the labels graded here must be summed over ONE window on both histories,
    # the requested one, and both files must bind the same outcome artifact when they bind one.
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        _outcome_identity,
        _window,
    )
    vet_man = json.loads(vet_man_p.read_text()) if vet_man_p.exists() else {}
    rookie_man_doc = json.loads(man_p.read_text()) if man_p.exists() else {}
    windows = {"veteran": _window(vet_man), "rookie": _window(rookie_man_doc)}
    outcomes = {"veteran": _outcome_identity(vet_man), "rookie": _outcome_identity(rookie_man_doc)}
    from src.dynasty_genius.ranking.outcome_artifact import bindings_disagree
    window_ok = windows["veteran"] == windows["rookie"] == a.window
    if outcomes["veteran"] is None and outcomes["rookie"] is None:
        outcome_ok, outcome_note = True, "neither history binds an outcome artifact (first producer files)"
    else:
        disagree = bindings_disagree(outcomes["veteran"], outcomes["rookie"])
        outcome_ok = not disagree
        outcome_note = "both histories bind the same outcome artifact on every core field" if outcome_ok else f"core fields differ: {disagree}"
    if not (window_ok and outcome_ok) and not a.allow_arm_mismatch:
        raise SystemExit(f"refusing to grade mixed targets: windows {windows} (requested {a.window}); outcome {outcome_note}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_grading"
    out.mkdir(parents=True)

    report: dict = {"run": stamp, "inputs": {
        "veteran_history": {"path": str(a.veteran_history), "sha256": vet_sha, "arm": a.veteran_arm,
                            "read_mode": a.read_mode, "binding": vet_bind},
        "rookie_history": {"path": str(a.rookie_history), "sha256": sha(a.rookie_history), "arm_check": arm_check}},
        "target_window": {"requested": a.window, "by_producer": windows, "consistent": window_ok},
        "outcome_identity": {"by_producer": outcomes, "consistent": outcome_ok, "note": outcome_note},
        "interval_meaning": ("90% bootstrap over players, conditional on this observed cohort and its reference; the shared "
                             "reference error does not cancel when the arms' actions differ; not model, selection, season "
                             "or forecast uncertainty"),
        "reference_rule": "reference identity and outcome shared by both arms; each arm subtracts its own forecast of him",
        "reference_proxy": {"basis": "rank by the training-only BASELINE arm's predicted season points within (position, season); "
                                     "season-long replace/retain against that player's expected and realised points; "
                                     "a PROXY for the actual available player, not demonstrated waiver availability",
                            "ranks": DEFAULT_BAR_RANKS, "sensitivity_ranks": "+/-5"},
        "grades": {}}
    N_BOOT = 300

    def cells_json(cells):
        return {f"{pos}|{season}": g for (pos, season), g in cells.items()}

    for h in range(1, a.horizons + 1):
        vh = veteran_history_rows(a.veteran_history, arm=a.veteran_arm, horizon=h, mode=a.read_mode)
        vc, vb = vh.candidate, vh.baseline
        rh = rookie_history_rows(a.rookie_history, season_j=h)
        rc, rb = rh.candidate, rh.baseline
        vcells = grade_by_cell(vc, vb, n_boot=N_BOOT)
        rcells = grade_by_cell(rc, rb, n_boot=N_BOOT)
        report["grades"][f"veteran_season{h}"] = {"cells": cells_json(vcells), "summary": summarise(vcells),
                                                  "seasons": sorted({r["season"] for r in vc}), "n": len(vc),
                                                  "unavailable_rows": vh.unavailable, "read_mode": vh.mode,
                                                  "status": ("graded" if vc else
                                                             "not graded: the selected policy scored no fold at this season")}
        report["grades"][f"rookie_season{h}"] = {"cells": cells_json(rcells), "summary": summarise(rcells),
                                                 "seasons": sorted({r["season"] for r in rc}), "n": len(rc),
                                                 "note": "rookie-only cells are skipped when a draft class is smaller than the reference rank"}
        common = sorted({r["season"] for r in vc} & {r["season"] for r in rc})
        jc = [r for r in vc + rc if r["season"] in common]
        jb = [r for r in vb + rb if r["season"] in common]
        joint = grade_by_cell(jc, jb, n_boot=N_BOOT)
        sens = {}
        for delta in (-5, 5):
            ranks = {p: max(1, r + delta) for p, r in DEFAULT_BAR_RANKS.items()}
            sens[f"rank{delta:+d}"] = summarise(grade_by_cell(jc, jb, rank_by_position=ranks))
        report["grades"][f"joint_season{h}"] = {"common_seasons": common, "n": len(jc), "cells": cells_json(joint),
                                                "summary": summarise(joint), "sensitivity": sens,
                                                "diagnostics": joint_diagnostics(jc, jb, DEFAULT_BAR_RANKS)}
    # The k-SEASON SUM from one origin, paired per player, one reference per origin, for
    # every k the veteran history reaches (the annual file pairs h1/h2 rows; the basic-horizon
    # file carries seasons 1..k on its horizon-k row).
    def two_json(cells):
        return {f"{pos}|origin{origin}": {k: v for k, v in g.items() if k != "players"} for (pos, origin), g in cells.items()}

    for k in range(2, a.horizons + 1):
        vk = veteran_multi_season_rows(a.veteran_history, seasons=k, arm=a.veteran_arm, mode=a.read_mode)
        vkc, vkb = vk.candidate, vk.baseline
        rk = multi_season_rows_from_single_file(
            a.rookie_history, seasons=k, id_col="gsis_id", origin_col="forecast_year",
            pred_prefix="e_points_year", base_prefix="baseline_e_points_year", label_prefix="points_", producer="rookie")
        rkc, rkb = rk.candidate, rk.baseline
        vet_cells = grade_multi_season_by_origin(vkc, vkb, seasons=k, n_boot=N_BOOT)
        common_origins = sorted({r["origin"] for r in vkc} & {r["origin"] for r in rkc})
        jkc = [r for r in vkc + rkc if r["origin"] in common_origins]
        jkb = [r for r in vkb + rkb if r["origin"] in common_origins]
        joint_cells = grade_multi_season_by_origin(jkc, jkb, seasons=k, n_boot=N_BOOT)
        report["grades"][f"{k}_season_sum_veteran_by_origin"] = {"origins": sorted({r["origin"] for r in vkc}), "n": len(vkc),
                                                                 "origin_definition": "the FIRST forecast season on every producer",
                                                                 "unavailable_origins": vk.unavailable,
                                                                 "status": ("graded" if vkc else
                                                                            "not graded: no origin has the selected policy's forecast for every season"),
                                                                 "cells": two_json(vet_cells)}
        report["grades"][f"{k}_season_sum_joint_by_origin"] = {"origins": common_origins, "n": len(jkc), "cells": two_json(joint_cells)}

    (out / "report.json").write_text(json.dumps(report, indent=1, default=str))
    lines = [f"# DG-178 assembled-value grading — run {stamp}", "",
             f"veteran history sha {report['inputs']['veteran_history']['sha256'][:12]} arm {a.veteran_arm}; "
             f"rookie history sha {report['inputs']['rookie_history']['sha256'][:12]}",
             f"reference proxy: {report['reference_proxy']['basis']}; ranks {DEFAULT_BAR_RANKS}; sensitivity +/-5",
             f"rookie history arm check: {arm_check}", ""]
    for key, block in report["grades"].items():
        if "_season_sum_" in key:
            lines.append(f"## {key}: n={block['n']} origins={block['origins']} (each fold separately; no pooling)")
            for cell, g in sorted(block["cells"].items()):
                if "skipped" in g:
                    lines.append(f"  {cell}: skipped ({g['skipped']})")
                    continue
                ci = g.get("decision_value_diff_ci90")
                lines.append(f"  {cell}: n={g['n']} spearman={('—' if g['spearman_pred_vs_realised'] is None else f'{g['spearman_pred_vs_realised']:.3f}')} "
                             f"rmse={g['rmse']:.1f} dv={g['decision_value_sum']:.0f} vs baseline {g['baseline_decision_value_sum']:.0f} "
                             f"diff={g['decision_value_diff']:+.0f} ci90={[round(x) for x in ci] if ci else '—'} ref={g['reference']['player_id']}")
            lines.append("")
            continue
        lines.append(f"## {key}: n={block['n']} seasons={block.get('seasons') or block.get('common_seasons')}")
        for pos, s in sorted(block["summary"].items()):
            def fmt(v):
                return "—" if v is None else f"{v:.3f}"
            lines.append(f"  {pos}: cells={s['cells']} n={s['n_total']} spearman={fmt(s['spearman_mean'])} "
                         f"among_started={fmt(s['spearman_among_started_mean'])} top_k_overlap={fmt(s['top_k_overlap_mean'])} "
                         f"rmse={fmt(s['rmse_mean'])} decision_value={s['decision_value_sum']:.0f} vs baseline {s['baseline_decision_value_sum']:.0f}")
        if "sensitivity" in block:
            for lab, sm in block["sensitivity"].items():
                lines.append(f"  sensitivity {lab}: " + "; ".join(
                    f"{pos} spearman={('—' if s['spearman_mean'] is None else f'{s['spearman_mean']:.3f}')} dv={s['decision_value_sum']:.0f}"
                    for pos, s in sorted(sm.items())))
        if block.get("diagnostics"):
            for cell, dg in block["diagnostics"].items():
                parts = []
                for prod in ("veteran", "rookie"):
                    if prod in dg:
                        d = dg[prod]
                        b = d["bias_among_retained"]
                        ci = d["bias_ci90"]
                        parts.append(f"{prod}: n={d['n']} retained={d['n_retained']} bias={('—' if b is None else f'{b:+.1f}')}"
                                     f"{'' if not ci else f' ci90=[{ci[0]:+.0f},{ci[1]:+.0f}]'} "
                                     f"top-k share pred={d['share_of_top_k_predicted']:.2f} real={d['share_of_top_k_realised']:.2f}")
                lines.append(f"  joint {cell}: " + " | ".join(parts))
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {out}/report.json and summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
