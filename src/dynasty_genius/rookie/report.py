"""Human-readable rendering of the evaluation, the scores and the report. Every number in
the markdown is read from the JSON record it sits beside; nothing is computed or typed
here, so the prose can never disagree with the evidence (round-1 review, item 4: the
previous REPORT quoted prevalences that its own JSON contradicted)."""
from __future__ import annotations

__all__ = ["render_evaluation_markdown", "render_report_markdown", "render_scores_markdown"]

ANNUAL_LABELS = {
    "p_qual_year": "P(qualifies in season j)",
    "p_appear_year": "P(appears in season j)",
    "e_points_year": "E[season points] (unconditional; 0 without appearance)",
    "e_games_year": "E[games] (unconditional)",
    "e_points_year_given_appear": "E[season points | appears]",
    "e_games_year_given_appear": "E[games | appears]",
    "e_ppg_year_given_appear": "E[ppg | appears]",
    "e_ppg_given_qual_year": "E[ppg | qualifies] (descriptive)",
}
HORIZON_LABELS = {
    "p_qual_h": "P(any qualifying season in 1..h)",
    "p_appear_by_h": "P(any appearance in 1..h)",
    "e_qual_seasons_h": "E[qualifying seasons in 1..h]",
}


def _f(x, nd=3):
    if x is None:
        return "—"
    try:
        if x != x:
            return "—"
    except TypeError:
        pass
    if isinstance(x, (list, tuple)):
        return "(" + ", ".join(_f(v, nd) for v in x) + ")"
    try:
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _binary_row(name: str, e: dict) -> str:
    years = e.get("forecast_years") or []
    span = f"{years[0]}–{years[-1]}" if years else "—"
    return (f"| {name} | {span} | {e.get('n', 0)} | {_f(e.get('prevalence'), 2)} | {_f(e.get('mean_predicted'), 2)} | "
            f"{_f(e.get('auc'))} {_f(e.get('auc_ci90'))} | {_f(e.get('brier'), 4)} / {_f(e.get('brier_training_baseline'), 4)} | "
            f"{_f(e.get('log_loss'), 4)} / {_f(e.get('log_loss_training_baseline'), 4)} |")


def _level_row(name: str, e: dict) -> str:
    years = e.get("forecast_years") or []
    span = f"{years[0]}–{years[-1]}" if years else "—"
    return (f"| {name} | {span} | {e.get('n', 0)} | {_f(e.get('mean_actual'), 2)} | {_f(e.get('mean_predicted'), 2)} | "
            f"{_f(e.get('rmse'), 2)} / {_f(e.get('rmse_training_baseline'), 2)} | {_f(e.get('bias'), 2)} |")


BINARY_HEADER = ("| quantity | forecast years | n | prevalence | mean predicted | AUC (90% CI) | "
                 "Brier model / training baseline | log loss model / baseline |\n|---|---|---:|---:|---:|---|---|---|")
LEVEL_HEADER = ("| quantity | forecast years | n | mean actual | mean predicted | RMSE model / training baseline | bias |\n"
                "|---|---|---:|---:|---:|---|---:|")


def _slice_tables(e: dict, kind: str) -> list[str]:
    lines = []
    if e.get("by_position"):
        lines += ["", "by position:", ""]
        if kind == "binary":
            lines += ["| position | n | prevalence | mean predicted | AUC | Brier model / baseline |", "|---|---:|---:|---:|---:|---|"]
            for pos, b in e["by_position"].items():
                lines.append(f"| {pos} | {b.get('n', 0)} | {_f(b.get('prevalence'), 2)} | {_f(b.get('mean_predicted'), 2)} | "
                             f"{_f(b.get('auc'))} | {_f(b.get('brier'), 4)} / {_f(b.get('brier_training_baseline'), 4)} |")
        else:
            lines += ["| position | n | mean actual | mean predicted | RMSE model / baseline | bias |", "|---|---:|---:|---:|---|---:|"]
            for pos, b in e["by_position"].items():
                lines.append(f"| {pos} | {b.get('n', 0)} | {_f(b.get('mean_actual'), 2)} | {_f(b.get('mean_predicted'), 2)} | "
                             f"{_f(b.get('rmse'), 2)} / {_f(b.get('rmse_training_baseline'), 2)} | {_f(b.get('bias'), 2)} |")
    if e.get("by_round"):
        lines += ["", "by round:", ""]
        if kind == "binary":
            lines += ["| round | n | actual rate | mean predicted |", "|---|---:|---:|---:|"]
            for rnd, b in sorted(e["by_round"].items(), key=lambda kv: int(kv[0])):
                lines.append(f"| {rnd} | {b.get('n', 0)} | {_f(b.get('prevalence'), 2)} | {_f(b.get('mean_predicted'), 2)} |")
        else:
            lines += ["| round | n | mean actual | mean predicted |", "|---|---:|---:|---:|"]
            for rnd, b in sorted(e["by_round"].items(), key=lambda kv: int(kv[0])):
                lines.append(f"| {rnd} | {b.get('n', 0)} | {_f(b.get('mean_actual'), 2)} | {_f(b.get('mean_predicted'), 2)} |")
    return lines


def render_evaluation_markdown(evaluation: dict) -> str:
    annual = evaluation.get("annual", {})
    horizon = evaluation.get("horizon", {})
    lines = [
        "# DG-165 rookie draft-capital candidate — historical evaluation with information cutoffs",
        "",
        "One fit per forecast year T on labels completed by T−1 (the same procedure as final scoring); class T",
        "graded against what happened afterwards, each quantity only where its own label is complete today.",
        "\"Training baseline\" = the prevalence / mean of that label in the training set at T, carried per row.",
        "",
        "## Per-season quantities (season j = 1 is the rookie season)",
    ]
    for j in sorted(annual, key=int):
        block = annual[j]
        lines += ["", f"### season {j}", "", "Probabilities:", "", BINARY_HEADER]
        for key in ("p_qual_year", "p_appear_year"):
            if key in block:
                lines.append(_binary_row(ANNUAL_LABELS[key], block[key]))
        lines += ["", "Levels:", "", LEVEL_HEADER]
        for key in ("e_points_year", "e_games_year", "e_points_year_given_appear", "e_games_year_given_appear",
                    "e_ppg_year_given_appear", "e_ppg_given_qual_year"):
            if key in block:
                lines.append(_level_row(ANNUAL_LABELS[key], block[key]))
        if "p_qual_year" in block and block["p_qual_year"].get("calibration"):
            lines += ["", f"Calibration of P(qualifies in season {j}):", "", "| predicted bin | n | mean predicted | actual |", "|---|---:|---:|---:|"]
            for row in block["p_qual_year"]["calibration"]:
                lines.append(f"| {row['bin']} | {row['n']} | {_f(row['predicted'])} | {_f(row['actual'])} |")
        for key in ("p_qual_year", "e_points_year"):
            if key in block:
                lines += ["", f"{ANNUAL_LABELS[key]} — slices:"]
                lines += _slice_tables(block[key], "binary" if key.startswith("p_") else "level")
        if "p_qual_year" in block and block["p_qual_year"].get("baseline_by_forecast_year"):
            b = block["p_qual_year"]["baseline_by_forecast_year"]
            lines += ["", "Training baseline for P(qualifies) by forecast year: " + ", ".join(f"{t}: {_f(v, 3)}" for t, v in b.items())]
    lines += ["", "## Cumulative quantities (window seasons 1..h)"]
    for h in sorted(horizon, key=int):
        block = horizon[h]
        lines += ["", f"### h = {h}", "", BINARY_HEADER]
        for key in ("p_qual_h", "p_appear_by_h"):
            if key in block:
                lines.append(_binary_row(HORIZON_LABELS[key], block[key]))
        lines += ["", LEVEL_HEADER]
        if "e_qual_seasons_h" in block:
            lines.append(_level_row(HORIZON_LABELS["e_qual_seasons_h"], block["e_qual_seasons_h"]))
        if "p_qual_h" in block and block["p_qual_h"].get("calibration"):
            lines += ["", f"Calibration of P(any qualifying season in 1..{h}):", "", "| predicted bin | n | mean predicted | actual |", "|---|---:|---:|---:|"]
            for row in block["p_qual_h"]["calibration"]:
                lines.append(f"| {row['bin']} | {row['n']} | {_f(row['predicted'])} | {_f(row['actual'])} |")
    lines += ["", "## Not gradable, and why", ""]
    absent = evaluation.get("absent", [])
    if not absent:
        lines.append("None.")
    for a in absent:
        where = ", ".join(f"{k} = {v}" for k, v in a.items() if k != "reason")
        lines.append(f"- {where}: {a['reason']}")
    skipped = evaluation.get("skipped_forecast_years", [])
    if skipped:
        lines += ["", "Forecast years skipped:", ""] + [f"- T = {s['forecast_year']}: {s['reason']}" for s in skipped]
    lines += ["", "## Per forecast year", "", "| T | train classes | train rows | test rows | families on a constant fallback |", "|---|---|---:|---:|---|"]
    for y in evaluation.get("per_forecast_year", []):
        const = ", ".join(sorted(y.get("constant_fits", {}))) or "none"
        lines.append(f"| {y['forecast_year']} | {y['train_classes'][0]}–{y['train_classes'][1]} | {y['n_train_rows']} | {y['n_test']} | {const} |")
    return "\n".join(lines) + "\n"


def render_scores_markdown(scores, horizons, forecast_year: int, top: int = 80) -> str:
    """A readable table of the scored class; the CSV is the record, this is the glance."""
    hmax = max(horizons)
    cols = ["pick", "round", "name", "position", "team", "age_at_draft", "identity_status", "coverage_status"]
    head = (["P(A y1)", "E[pts y1]", "E[games y1]", "P(Q y1)", "E[ppg|Q y1]", "P(A y3)", "E[pts y3]", "P(Q y3)",
             f"P(A by {hmax})", f"P(Q_{hmax})", f"E[N_{hmax}]", f"E[N_{hmax}] 90% fit"])
    lines = [f"# {forecast_year} draft class — draft-capital candidate (research output, not served)", "",
             "P(A yj) = appears in season j (a weekly stat row); E[pts yj] = expected REG PPR season total, unconditional "
             "(zero without an appearance); P(Q yj) = qualifies by season total at the availability bar; "
             "E[ppg|Q] = descriptive conditional rate. Intervals are fit uncertainty, not outcome spread.", "",
             "| " + " | ".join(cols + head) + " |", "|" + "---|" * (len(cols) + len(head))]
    for _, r in scores.head(top).iterrows():
        cells = [str(r.get(c, "")) if c != "age_at_draft" else _f(r.get(c), 0) for c in cols]
        cells += [_f(r.get("p_appear_year1"), 2), _f(r.get("e_points_year1"), 0), _f(r.get("e_games_year1"), 1),
                  _f(r.get("p_qual_year1"), 2), _f(r.get("e_ppg_given_qual_year1"), 1),
                  _f(r.get("p_appear_year3"), 2), _f(r.get("e_points_year3"), 0), _f(r.get("p_qual_year3"), 2),
                  _f(r.get(f"p_appear_by_h{hmax}"), 2), _f(r.get(f"p_qual_h{hmax}"), 2), _f(r.get(f"e_qual_seasons_h{hmax}"), 2),
                  f"{_f(r.get(f'e_qual_seasons_h{hmax}_lo90'), 2)}–{_f(r.get(f'e_qual_seasons_h{hmax}_hi90'), 2)}"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def render_report_markdown(manifest: dict, evaluation: dict, sensitivity: dict | None, scores, trend: dict | None = None,
                           assessment: dict | None = None) -> str:
    """REPORT.md: the numeric record rendered from JSON, with number-free framing prose."""
    lines = [
        "# DG-165 — draft-capital rookie candidate: the record",
        "",
        f"Run `{manifest['run_dir']}` · git `{manifest['git_sha'][:8]}` · model `{manifest['model_version']}` · policy `{manifest.get('model_policy')}` · arm `{manifest.get('scoring_arm_id')}` · {manifest['status']}",
        "",
        "Every number below is rendered from `evaluation.json`, `manifest.json` and `rookie_scores_*.csv`; the prose",
        "in `NOTES.md` interprets and carries no statistics of its own.",
        "",
        "## Definitions",
        "",
    ]
    for k, v in manifest.get("definitions", {}).items():
        lines.append(f"- **{k}**: {v}")
    for k, v in manifest.get("units", {}).items():
        lines.append(f"- **{k}**: {v}")
    fd = manifest.get("forecast_date", {})
    lines += ["", f"- **forecast cutoff**: {fd.get('forecast_cutoff')} · **label window**: {fd.get('label_window')}", ""]
    cov = manifest.get("cohort", {}).get("coverage", {})
    lines += ["## Cohort", "", "| item | value |", "|---|---:|"]
    for k, v in cov.items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Headline out-of-time results", "", "Per season (see `EVALUATION.md` for every quantity, slice and calibration table):", "", BINARY_HEADER]
    for j in sorted(evaluation.get("annual", {}), key=int):
        b = evaluation["annual"][j]
        if "p_qual_year" in b:
            lines.append(_binary_row(f"season {j}: P(qualifies)", b["p_qual_year"]))
        if "p_appear_year" in b:
            lines.append(_binary_row(f"season {j}: P(appears)", b["p_appear_year"]))
    lines += ["", LEVEL_HEADER]
    for j in sorted(evaluation.get("annual", {}), key=int):
        b = evaluation["annual"][j]
        for key in ("e_points_year", "e_games_year", "e_ppg_given_qual_year"):
            if key in b:
                lines.append(_level_row(f"season {j}: {ANNUAL_LABELS[key]}", b[key]))
    lines += ["", "Cumulative:", "", BINARY_HEADER]
    for h in sorted(evaluation.get("horizon", {}), key=int):
        b = evaluation["horizon"][h]
        for key in ("p_qual_h", "p_appear_by_h"):
            if key in b:
                lines.append(_binary_row(f"h = {h}: {HORIZON_LABELS[key]}", b[key]))
    lines += ["", LEVEL_HEADER]
    for h in sorted(evaluation.get("horizon", {}), key=int):
        b = evaluation["horizon"][h]
        if "e_qual_seasons_h" in b:
            lines.append(_level_row(f"h = {h}: {HORIZON_LABELS['e_qual_seasons_h']}", b["e_qual_seasons_h"]))
    if sensitivity:
        lines += ["", "## Sensitivity: unresolved identities labelled zero instead of unknown", "",
                  "| quantity | default (unknown excluded) | sensitivity arm (zero) | difference |", "|---|---:|---:|---:|"]
        for row in sensitivity.get("evaluation_deltas", []):
            lines.append(f"| {row['quantity']} | {_f(row['default'], 4)} | {_f(row['arm'], 4)} | {_f(row['delta'], 4)} |")
        lines += ["", "Largest absolute change in a 2026 score under the sensitivity arm:", "", "| column | max abs change | player |", "|---|---:|---|"]
        for row in sensitivity.get("score_deltas", []):
            lines.append(f"| {row['column']} | {_f(row['max_abs_delta'], 4)} | {row['player']} |")
    if trend:
        lines += ["", "## Model policy and exploratory comparison", "",
                  f"Declared policy: **{trend['policy']}** — evidence status: {trend['evidence_status'].get(trend['policy'], '')}", ""]
        for name, status in trend["evidence_status"].items():
            if name != trend["policy"]:
                lines.append(f"- `{name}`: {status}")
        lines += ["", "Paired bootstrap of the difference (exploratory − policy), same test rows resampled once per replicate:", "",
                  "| exploratory arm | quantity | metric | policy | exploratory | difference (90% CI) | reading |", "|---|---|---|---:|---:|---|---|"]
        for name, table in trend["comparison"].items():
            for label, metrics in table.items():
                for metric, c in metrics.items():
                    lines.append(f"| {name} | {label} | {metric} | {_f(c['policy'], 4)} | {_f(c['exploratory'], 4)} | "
                                 f"{_f(c['difference'], 4)} ({_f(c['difference_ci90'][0], 4)}, {_f(c['difference_ci90'][1], 4)}) | {c['reading']} |")
        chosen = [(y["forecast_year"], (y.get("policy_selection") or {}).get("chosen", y.get("variant")))
                  for y in evaluation.get("per_forecast_year", [])]
        lines += ["", "Variant chosen inside each training window by the policy: " + ", ".join(f"{t}: {v}" for t, v in chosen)]
    if assessment:
        lines += ["", "## Recent-era QB / first-round calibration assessment (no correction applied)", "",
                  "| position | band | era | season | n | appearance bias (90%) | conditional points bias among appearers (90%) | unconditional points bias (90%) |",
                  "|---|---|---|---|---:|---|---|---|"]
        for pos in ("QB", "RB", "WR", "TE"):
            for band in ("R1", "all"):
                for era, js in assessment["cells"].get(pos, {}).get(band, {}).items():
                    for j, c in js.items():
                        lines.append(f"| {pos} | {band} | {era} | {j} | {c['n']} | {_f(c['appearance_bias'], 3)} ({_f(c['appearance_bias_ci90'][0], 3)}, {_f(c['appearance_bias_ci90'][1], 3)}) | "
                                     f"{_f(c['conditional_points_bias'], 1)} ({_f(c['conditional_points_bias_ci90'][0], 1)}, {_f(c['conditional_points_bias_ci90'][1], 1)}) | "
                                     f"{_f(c['unconditional_points_bias'], 1)} ({_f(c['unconditional_points_bias_ci90'][0], 1)}, {_f(c['unconditional_points_bias_ci90'][1], 1)}) |")
    if scores is not None and len(scores):
        lines += ["", "## Scored class, first rows (see `ROOKIES_*.md`)", ""]
        lines += render_scores_markdown(scores, manifest["model"]["horizons"], manifest["forecast_date"]["forecast_year"], top=12).split("\n")[4:]
    return "\n".join(lines) + "\n"
