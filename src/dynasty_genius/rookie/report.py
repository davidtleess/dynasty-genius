"""Human-readable rendering of the evaluation and the manifest. Numbers come from the JSON;
nothing is computed here, so the markdown can never disagree with the machine-readable
record it sits beside."""
from __future__ import annotations

__all__ = ["render_evaluation_markdown", "render_scores_markdown"]


def _f(x, nd=3):
    if x is None:
        return "—"
    try:
        if x != x:  # NaN
            return "—"
    except TypeError:
        pass
    return f"{x:.{nd}f}"


def render_evaluation_markdown(evaluation: dict) -> str:
    pooled = evaluation.get("pooled_by_horizon", {})
    lines = [
        "# DG-165 rookie draft-capital candidate — walk-forward evaluation",
        "",
        "Every forecast year T is scored with a model fitted only on labels observable at T",
        "(seasons <= T-1). Test rows are class T graded against what happened afterwards.",
        "\"Base rate\" is the training prevalence applied to the test class: the no-model forecast.",
        "",
        "## Pooled out-of-time results by horizon",
        "",
        "| horizon | forecast years | n | prevalence | AUC (90% CI) | Brier (model / base) | log loss (model / base) | E[N_h] RMSE (model / base) | bias |",
        "|---|---|---:|---:|---|---|---|---|---:|",
    ]
    for h in sorted(pooled, key=int):
        e = pooled[h]
        q = e["qual"]
        years = e["forecast_years"]
        span = f"{years[0]}–{years[-1]}" if years else "—"
        ci = e.get("qual_auc_ci90", [None, None])
        s = e["seasons"]
        lines.append(
            f"| h = {h} | {span} | {e['n']} | {_f(q['prevalence'], 2)} | "
            f"{_f(q['auc'])} ({_f(ci[0])}, {_f(ci[1])}) | {_f(q['brier'], 4)} / {_f(q['brier_base_rate'], 4)} | "
            f"{_f(q['log_loss'], 4)} / {_f(q['log_loss_base_rate'], 4)} | "
            f"{_f(s['rmse'])} / {_f(s['rmse_base_rate'])} | {_f(s['bias'], 3)} |"
        )
    lines += ["", "## P(played by h) — the availability event, reported separately", "",
              "| horizon | n | prevalence | AUC | Brier (model / base) |", "|---|---:|---:|---:|---|"]
    for h in sorted(pooled, key=int):
        p = pooled[h]["played"]
        lines.append(f"| h = {h} | {p['n']} | {_f(p['prevalence'], 2)} | {_f(p['auc'])} | {_f(p['brier'], 4)} / {_f(p['brier_base_rate'], 4)} |")

    for h in sorted(pooled, key=int):
        e = pooled[h]
        lines += ["", f"## h = {h}: calibration of P(Q_{h}), out-of-time", "",
                  "| predicted bin | n | mean predicted | actual |", "|---|---:|---:|---:|"]
        for row in e["calibration_qual"]:
            lines.append(f"| {row['bin']} | {row['n']} | {_f(row['predicted'])} | {_f(row['actual'])} |")
        lines += ["", f"### h = {h}: by position", "",
                  "| position | n | prevalence | AUC | Brier (model / base) | E[N] actual / predicted | RMSE (model / base) |",
                  "|---|---:|---:|---:|---|---|---|"]
        for pos, b in e["by_position"].items():
            s = b["seasons"]
            lines.append(
                f"| {pos} | {b['n']} | {_f(b['prevalence'], 2)} | {_f(b['auc'])} | {_f(b['brier'], 4)} / {_f(b['brier_base_rate'], 4)} | "
                f"{_f(s['mean_actual'], 2)} / {_f(s['mean_predicted'], 2)} | {_f(s['rmse'])} / {_f(s['rmse_base_rate'])} |"
            )
        lines += ["", f"### h = {h}: by round (out-of-time, actual vs predicted)", "",
                  "| round | n | P(Q) actual | P(Q) predicted | E[N] actual | E[N] predicted |", "|---|---:|---:|---:|---:|---:|"]
        for rnd, b in sorted(e["by_round"].items(), key=lambda kv: int(kv[0])):
            lines.append(f"| {rnd} | {b['n']} | {_f(b['actual_qual_rate'], 2)} | {_f(b['predicted_qual_rate'], 2)} | "
                         f"{_f(b['actual_seasons'], 2)} | {_f(b['predicted_seasons'], 2)} |")

    level = evaluation.get("level_by_year", {})
    if level:
        lines += ["", "## The LEVEL: E[ppg | qualifies in season j], out-of-time, graded on qualifiers only", "",
                  "ppg = regular-season PPR points / games with a weekly stat row. Comparator = the training qualifiers' mean rate at the position.", "",
                  "| season j | n qualifiers | mean actual | mean predicted | RMSE (model / position mean) | bias |",
                  "|---|---:|---:|---:|---|---:|"]
        for j in sorted(level, key=int):
            e = level[j]
            lines.append(f"| {j} | {e['n']} | {_f(e['mean_actual'], 2)} | {_f(e['mean_predicted'], 2)} | "
                         f"{_f(e['rmse'], 2)} / {_f(e['rmse_position_mean'], 2)} | {_f(e['bias'], 2)} |")
        for j in sorted(level, key=int):
            e = level[j]
            lines += ["", f"### season {j}: level by position", "",
                      "| position | n | mean actual | mean predicted | RMSE (model / position mean) |", "|---|---:|---:|---:|---|"]
            for pos, b in e["by_position"].items():
                lines.append(f"| {pos} | {b['n']} | {_f(b['mean_actual'], 2)} | {_f(b['mean_predicted'], 2)} | {_f(b['rmse'], 2)} / {_f(b['rmse_position_mean'], 2)} |")
            lines += ["", f"### season {j}: level by round (qualifiers only)", "",
                      "| round | n | mean actual | mean predicted |", "|---|---:|---:|---:|"]
            for rnd, b in sorted(e["by_round"].items(), key=lambda kv: int(kv[0])):
                lines.append(f"| {rnd} | {b['n']} | {_f(b['mean_actual'], 2)} | {_f(b['mean_predicted'], 2)} |")

    absent = evaluation.get("absent_pairs", [])
    lines += ["", "## Forecast-year / horizon pairs NOT evaluated, and why", ""]
    if not absent:
        lines.append("None.")
    for a in absent:
        lines.append(f"- T = {a['forecast_year']}, h = {a['horizon']}: {a['reason']}")
    lines += ["", "## Per-split detail", "",
              "| T | h | train classes | n_train | n_test | AUC | Brier (model / base) |", "|---|---|---|---:|---:|---:|---|"]
    for s in evaluation.get("per_split", []):
        q = s["qual"]
        lines.append(f"| {s['forecast_year']} | {s['horizon']} | {s['train_classes'][0]}–{s['train_classes'][1]} | "
                     f"{s['n_train']} | {s['n_test']} | {_f(q['auc'])} | {_f(q['brier'], 4)} / {_f(q['brier_base_rate'], 4)} |")
    return "\n".join(lines) + "\n"


def render_scores_markdown(scores, horizons, forecast_year: int, top: int = 80) -> str:
    """A readable table of the scored class; the CSV is the record, this is the glance."""
    cols = ["pick", "round", "name", "position", "team", "age_at_draft", "coverage_status"]
    level_years = [j for j in (1, 3, 5) if f"e_ppg_given_qual_year{j}" in scores.columns]
    lines = [f"# {forecast_year} draft class — draft-capital candidate (research output, not served)", "",
             "P(Q_h) = probability of at least one qualifying season within h NFL seasons; "
             "E[N_h] = expected qualifying seasons within h. E[ppg|Q] yj = expected REG PPR points per stat-row game "
             "IF he qualifies in season j (conditional; multiply on the consumer's side, never here). "
             "90% intervals are fit uncertainty, not outcome spread.", "",
             "| " + " | ".join(cols) + " | " + " | ".join(f"P(Q_{h})" for h in horizons) + " | "
             + " | ".join(f"E[N_{h}]" for h in horizons) + f" | E[N_{max(horizons)}] 90% | "
             + " | ".join(f"E[ppg\|Q] y{j}" for j in level_years) + " |",
             "|" + "---|" * (len(cols) + 2 * len(horizons) + 1 + len(level_years))]
    hmax = max(horizons)
    for _, r in scores.head(top).iterrows():
        cells = [str(r.get(c, "")) if c != "age_at_draft" else _f(r.get(c), 0) for c in cols]
        cells += [_f(r[f"p_qual_h{h}"], 2) for h in horizons]
        cells += [_f(r[f"e_qual_seasons_h{h}"], 2) for h in horizons]
        lo, hi = r.get(f"e_qual_seasons_h{hmax}_lo90"), r.get(f"e_qual_seasons_h{hmax}_hi90")
        cells.append(f"{_f(lo, 2)}–{_f(hi, 2)}")
        cells += [_f(r[f"e_ppg_given_qual_year{j}"], 1) for j in level_years]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
