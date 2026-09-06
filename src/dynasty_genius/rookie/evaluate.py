"""Historical evaluation: ONE fit per forecast year, the same procedure final scoring uses,
and every exported quantity graded against its own label.

For forecast year T (pre-season, after the draft):

* the training frame is every class c < T labelled with ``last_completed_season = T − 1``
  — each family inside the model then selects its own observable, at-risk rows exactly as
  the final fit at T = forecast_year does (``fit_at_forecast_year`` is that one procedure);
* the test frame is class T labelled with everything completed TODAY; each quantity is
  graded only on rows whose own label is observable, so an ungradable (T, j) pair is absent
  and listed, never manufactured.

Comparators are TRAINING baselines: for a probability, the training prevalence of that
label at T; for a level, the training mean of that quantity at T (by position for the
conditional rates). They are carried per row into the predictions frame and pooled from
there — never from pooled test prevalence (round-1 review, item 4).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.dynasty_genius.rookie.labels import SeasonKey, horizon_labels
from src.dynasty_genius.rookie.model import RookieCapitalModel

__all__ = ["MENU", "POLICIES", "evaluate_forecast_years", "fit_at_forecast_year", "policy_experiment", "training_frame_at"]

MIN_TRAIN_ROWS = 100
# The bounded menu the inner-window policy chooses from, simplest first (ties go to the
# simpler variant). Inner validation uses the most recent classes whose season-1 labels
# were complete at the cutoff; three classes is the smallest window that can tell a trend
# from one odd class; nothing later than T-1 is ever read.
MENU: tuple[str, ...] = ("plain", "trend", "trend_qb_r1")
POLICIES: tuple[str, ...] = MENU + ("inner_menu",)
INNER_VALIDATION_CLASSES = 3

# (exported column pattern, label column pattern, kind, conditioning label or None)
ANNUAL_QUANTITIES = (
    ("p_qual_year{j}", "qy_{j}", "binary", None),
    ("p_appear_year{j}", "appear_{j}", "binary", None),
    ("e_points_year{j}", "points_{j}", "level", None),
    ("e_games_year{j}", "games_{j}", "level", None),
    ("e_points_year{j}_given_appear", "points_{j}", "level", "appear_{j}"),
    ("e_games_year{j}_given_appear", "games_{j}", "level", "appear_{j}"),
    ("e_ppg_year{j}_given_appear", "ppg_{j}", "level", "appear_{j}"),
    ("e_ppg_given_qual_year{j}", "ppg_{j}", "level", "qy_{j}"),
)
HORIZON_QUANTITIES = (
    ("p_qual_h{h}", "q_{h}", "binary", None),
    ("p_appear_by_h{h}", "appear_by_{h}", "binary", None),
    ("e_qual_seasons_h{h}", "n_{h}", "level", None),
)


def _short(pattern: str) -> str:
    """'e_points_year{j}_given_appear' -> 'e_points_year_given_appear'; 'p_qual_h{h}' -> 'p_qual_h'."""
    return pattern.replace("{j}", "").replace("{h}", "").rstrip("_")


def training_frame_at(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: Iterable[int],
    forecast_year: int,
    unresolved_as_zero: bool = False,
) -> pd.DataFrame:
    """Classes before T, labelled with only the seasons that had completed at T."""
    earlier = cohort.loc[cohort["draft_season"] < forecast_year]
    return horizon_labels(
        earlier, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
        last_completed_season=forecast_year - 1, unresolved_as_zero=unresolved_as_zero,
    )


def _inner_selection(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: tuple[int, ...],
    forecast_year: int,
    unresolved_as_zero: bool,
) -> dict:
    """Choose a variant from MENU INSIDE the training window at T.

    Inner cutoff T' = T − K: fit every variant on classes < T' with labels through T' − 1,
    validate on classes T' .. T − 1 with labels through T − 1 (season 1 of each is complete
    at T). Nothing at or after T is read, so the selection is a decision a forecaster at T
    could have made. Rule, stated before any outer result is seen: a variant replaces
    "plain" only if it beats plain on at least two of the three season-1 validation scores;
    among such variants the one with more wins, ties to the lower log loss of P(qualifies),
    then to the simpler variant.
    """
    K = INNER_VALIDATION_CLASSES
    inner_T = forecast_year - K
    inner_train = training_frame_at(cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                                    forecast_year=inner_T, unresolved_as_zero=unresolved_as_zero)
    validation = horizon_labels(
        cohort.loc[cohort["draft_season"].between(inner_T, forecast_year - 1)], qualifying=qualifying,
        season_stats=season_stats, horizons=horizons, last_completed_season=forecast_year - 1,
        unresolved_as_zero=unresolved_as_zero,
    )
    validation = validation.loc[validation["appear_1"].notna() & validation["qy_1"].notna()]
    scores: dict[str, dict[str, float]] = {}
    for variant in MENU:
        model = RookieCapitalModel(horizons=horizons, variant=variant).fit(inner_train)
        pred = model.predict(validation)
        yq, ya = validation["qy_1"].to_numpy(dtype=int), validation["appear_1"].to_numpy(dtype=int)
        pq = np.clip(pred["p_qual_year1"].to_numpy(), 1e-6, 1 - 1e-6)
        pa = np.clip(pred["p_appear_year1"].to_numpy(), 1e-6, 1 - 1e-6)
        yp, ep = validation["points_1"].to_numpy(dtype=float), pred["e_points_year1"].to_numpy()
        scores[variant] = {
            "log_loss_p_qual_year1": float(log_loss(yq, pq, labels=[0, 1])),
            "log_loss_p_appear_year1": float(log_loss(ya, pa, labels=[0, 1])),
            "rmse_e_points_year1": float(np.sqrt(np.mean((yp - ep) ** 2))),
            "n_validation": int(len(validation)),
        }
    keys = ("log_loss_p_qual_year1", "log_loss_p_appear_year1", "rmse_e_points_year1")
    wins = {v: sum(scores[v][k] < scores["plain"][k] for k in keys) for v in MENU if v != "plain"}
    candidates = [v for v in MENU if v != "plain" and wins[v] >= 2]
    if candidates:
        chosen = min(candidates, key=lambda v: (-wins[v], scores[v]["log_loss_p_qual_year1"], MENU.index(v)))
    else:
        chosen = "plain"
    return {
        "chosen": chosen,
        "rule": "a variant replaces plain only if it beats plain on >= 2 of the 3 season-1 validation scores; "
                "more wins, then lower log loss of P(qualifies), then the simpler variant",
        "menu": list(MENU),
        "wins_vs_plain": wins,
        "inner_cutoff": inner_T,
        "validation_classes": sorted(int(c) for c in validation["draft_season"].unique()),
        "scores": scores,
    }


def fit_at_forecast_year(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: Iterable[int],
    forecast_year: int,
    unresolved_as_zero: bool = False,
    policy: str = "plain",
) -> RookieCapitalModel:
    """THE procedure: historical evaluation and final scoring both call this.

    ``policy`` is a fixed variant name from MENU, or "inner_menu": the variant is chosen
    inside the training window by ``_inner_selection`` and the choice is recorded on the
    model. The policy is declared before the outer loop runs and never changed by it.
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}; choose from {POLICIES}")
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    train = training_frame_at(
        cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
        forecast_year=forecast_year, unresolved_as_zero=unresolved_as_zero,
    )
    selection = None
    if policy == "inner_menu":
        selection = _inner_selection(cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                                     forecast_year=forecast_year, unresolved_as_zero=unresolved_as_zero)
        variant = selection["chosen"]
    else:
        variant = policy
    model = RookieCapitalModel(horizons=horizons, variant=variant, policy=policy).fit(train)
    model.policy_selection = selection
    return model


# --------------------------------------------------------------------------- baselines
def _training_baselines(train: pd.DataFrame, horizons: tuple[int, ...]) -> dict[str, object]:
    """Per-quantity training baselines at T: prevalence / mean / position means."""
    base: dict[str, object] = {}
    J = max(horizons)
    for pattern, label, kind, cond in ANNUAL_QUANTITIES:
        for j in range(1, J + 1):
            col = label.format(j=j)
            rows = train
            if cond is not None:
                rows = train.loc[train[cond.format(j=j)] == 1]
            values = rows[col].dropna()
            key = pattern.format(j=j)
            if cond is None:
                base[key] = float(values.mean()) if len(values) else np.nan
            else:
                base[key] = {p: float(g[col].dropna().mean()) for p, g in rows.groupby("position") if g[col].notna().any()}
                base[key]["_all"] = float(values.mean()) if len(values) else np.nan
    for pattern, label, kind, cond in HORIZON_QUANTITIES:
        for h in horizons:
            values = train[label.format(h=h)].dropna()
            base[pattern.format(h=h)] = float(values.mean()) if len(values) else np.nan
    return base


def _baseline_row_values(key: str, base: dict, positions: pd.Series) -> np.ndarray:
    value = base.get(key, np.nan)
    if isinstance(value, dict):
        return positions.map(lambda p: value.get(p, value.get("_all", np.nan))).to_numpy(dtype=float)
    return np.full(len(positions), value, dtype=float)


# --------------------------------------------------------------------------- metrics
def _binary_block(y: np.ndarray, p: np.ndarray, b: np.ndarray) -> dict[str, float]:
    ok = ~np.isnan(y) & ~np.isnan(p)
    y, p, b = y[ok].astype(int), np.clip(p[ok], 1e-6, 1 - 1e-6), np.clip(b[ok], 1e-6, 1 - 1e-6)
    out = {"n": int(len(y)), "prevalence": float(np.mean(y)) if len(y) else np.nan}
    if len(y) == 0:
        return out
    out["brier"] = float(brier_score_loss(y, p))
    out["brier_training_baseline"] = float(brier_score_loss(y, b))
    out["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    out["log_loss_training_baseline"] = float(log_loss(y, b, labels=[0, 1]))
    out["auc"] = float(roc_auc_score(y, p)) if len(set(y.tolist())) == 2 else np.nan
    out["mean_predicted"] = float(np.mean(p))
    return out


def _level_block(y: np.ndarray, e: np.ndarray, b: np.ndarray) -> dict[str, float]:
    ok = ~np.isnan(y) & ~np.isnan(e) & ~np.isnan(b)
    y, e, b = y[ok], e[ok], b[ok]
    out = {"n": int(len(y))}
    if len(y) == 0:
        return out
    out.update(
        mean_actual=float(np.mean(y)), mean_predicted=float(np.mean(e)),
        rmse=float(np.sqrt(np.mean((y - e) ** 2))), rmse_training_baseline=float(np.sqrt(np.mean((y - b) ** 2))),
        bias=float(np.mean(e - y)),
    )
    return out


def _calibration(y: np.ndarray, p: np.ndarray, edges=(0.0, 0.1, 0.2, 0.35, 0.5, 0.7, 1.0)) -> list[dict]:
    ok = ~np.isnan(y) & ~np.isnan(p)
    y, p = y[ok], p[ok]
    bins = pd.cut(p, list(edges), labels=False, include_lowest=True)
    rows = []
    for b in range(len(edges) - 1):
        mask = bins == b
        if mask.any():
            rows.append({"bin": f"{edges[b]:.2f}-{edges[b + 1]:.2f}", "n": int(mask.sum()),
                         "predicted": float(np.mean(p[mask])), "actual": float(np.mean(y[mask]))})
    return rows


def _bootstrap_ci(y: np.ndarray, p: np.ndarray, stat, n_boot: int, rng: np.random.Generator) -> list[float]:
    ok = ~np.isnan(y) & ~np.isnan(p)
    y, p = y[ok].astype(int), p[ok]
    values = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i].tolist())) < 2:
            continue
        values.append(stat(y[i], p[i]))
    if not values:
        return [float("nan"), float("nan")]
    lo, hi = np.percentile(values, [5, 95])
    return [float(lo), float(hi)]


def _slices(frame: pd.DataFrame, y_col: str, p_col: str, b_col: str, kind: str) -> dict:
    block = _binary_block if kind == "binary" else _level_block
    out = {"by_position": {}, "by_round": {}}
    for pos, g in frame.groupby("position"):
        out["by_position"][pos] = block(g[y_col].to_numpy(dtype=float), g[p_col].to_numpy(dtype=float), g[b_col].to_numpy(dtype=float))
    for rnd, g in frame.groupby("round"):
        out["by_round"][int(rnd)] = block(g[y_col].to_numpy(dtype=float), g[p_col].to_numpy(dtype=float), g[b_col].to_numpy(dtype=float))
    return out


# --------------------------------------------------------------------------- the loop
def evaluate_forecast_years(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: Iterable[int],
    forecast_years: Iterable[int],
    last_completed_season_today: int,
    n_boot: int = 1000,
    seed: int = 20260906,
    min_train_rows: int = MIN_TRAIN_ROWS,
    unresolved_as_zero: bool = False,
    policy: str = "plain",
) -> tuple[dict, pd.DataFrame]:
    """Returns ``(report, predictions)``. The report is JSON-serialisable; ``predictions``
    holds one row per (forecast year, test prospect) with every exported quantity, its
    label, and the training baseline that applies to that row."""
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    J = max(horizons)
    rng = np.random.default_rng(seed)
    frames, per_year, skipped = [], [], []
    for T in sorted(set(int(t) for t in forecast_years)):
        train = training_frame_at(cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                                  forecast_year=T, unresolved_as_zero=unresolved_as_zero)
        current = cohort.loc[cohort["draft_season"] == T]
        if current.empty or int(train["appear_1"].notna().sum()) < min_train_rows:
            skipped.append({"forecast_year": T, "reason": "no test class" if current.empty else "training set below the minimum size"})
            continue
        model = fit_at_forecast_year(cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                                     forecast_year=T, unresolved_as_zero=unresolved_as_zero, policy=policy)
        test = horizon_labels(current, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                              last_completed_season=last_completed_season_today, unresolved_as_zero=unresolved_as_zero)
        pred = model.predict(test)
        base = _training_baselines(train, horizons)
        extra = {"forecast_year": np.full(len(test), T)}
        for col in pred.columns:
            if col != "gsis_id":
                extra[col] = pred[col].to_numpy()
        for pattern, label, kind, cond in ANNUAL_QUANTITIES:
            for j in range(1, J + 1):
                key = pattern.format(j=j)
                extra[f"baseline_{key}"] = _baseline_row_values(key, base, test["position"])
        for pattern, label, kind, cond in HORIZON_QUANTITIES:
            for h in horizons:
                key = pattern.format(h=h)
                extra[f"baseline_{key}"] = _baseline_row_values(key, base, test["position"])
        merged = pd.concat([test.reset_index(drop=True), pd.DataFrame(extra)], axis=1)
        frames.append(merged)
        per_year.append({"forecast_year": T, "n_train_rows": int(len(train)), "n_test": int(len(test)),
                         "train_classes": [int(train["draft_season"].min()), int(train["draft_season"].max())],
                         "n_train_by_family": dict(model.n_train), "constant_fits": dict(model.constant_fits),
                         "variant": model.variant, "arm_id": model.arm_id, "policy_selection": model.policy_selection,
                         "training_baselines": {k: v for k, v in base.items() if not isinstance(v, dict)}})
    predictions = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    annual: dict[int, dict] = {}
    absent: list[dict] = []
    for j in range(1, J + 1):
        annual[j] = {}
        for pattern, label, kind, cond in ANNUAL_QUANTITIES:
            key = pattern.format(j=j)
            ycol = label.format(j=j)
            if predictions.empty:
                continue
            rows = predictions
            if cond is not None:
                rows = rows.loc[rows[cond.format(j=j)] == 1]
            rows = rows.loc[rows[ycol].notna()]
            if rows.empty:
                absent.append({"season": j, "quantity": key, "reason": "no gradable rows"})
                continue
            y, p, b = rows[ycol].to_numpy(dtype=float), rows[key].to_numpy(dtype=float), rows[f"baseline_{key}"].to_numpy(dtype=float)
            entry = _binary_block(y, p, b) if kind == "binary" else _level_block(y, p, b)
            entry["forecast_years"] = sorted(int(t) for t in rows["forecast_year"].unique())
            entry["baseline_by_forecast_year"] = {str(int(t)): float(g[f"baseline_{key}"].mean()) for t, g in rows.groupby("forecast_year")}
            if kind == "binary":
                entry["auc_ci90"] = _bootstrap_ci(y, p, roc_auc_score, n_boot, rng)
                entry["brier_ci90"] = _bootstrap_ci(y, p, brier_score_loss, n_boot, rng)
                entry["calibration"] = _calibration(y, p)
            entry.update(_slices(rows, ycol, key, f"baseline_{key}", kind))
            annual[j][_short(pattern)] = entry
    horizon: dict[int, dict] = {}
    for h in horizons:
        horizon[h] = {}
        for pattern, label, kind, cond in HORIZON_QUANTITIES:
            key = pattern.format(h=h)
            ycol = label.format(h=h)
            if predictions.empty:
                continue
            rows = predictions.loc[predictions[ycol].notna()]
            if rows.empty:
                absent.append({"horizon": h, "quantity": key, "reason": "no gradable rows"})
                continue
            y, p, b = rows[ycol].to_numpy(dtype=float), rows[key].to_numpy(dtype=float), rows[f"baseline_{key}"].to_numpy(dtype=float)
            entry = _binary_block(y, p, b) if kind == "binary" else _level_block(y, p, b)
            entry["forecast_years"] = sorted(int(t) for t in rows["forecast_year"].unique())
            if kind == "binary":
                entry["auc_ci90"] = _bootstrap_ci(y, p, roc_auc_score, n_boot, rng)
                entry["calibration"] = _calibration(y, p)
            entry.update(_slices(rows, ycol, key, f"baseline_{key}", kind))
            horizon[h][_short(pattern)] = entry
    # Which (forecast year, season) pairs are not gradable today, and why.
    for T in sorted(set(int(t) for t in forecast_years)):
        for j in range(1, J + 1):
            if T + j - 1 > last_completed_season_today:
                absent.append({"forecast_year": T, "season": j,
                               "reason": f"NFL season {T + j - 1} not complete by {last_completed_season_today}; cannot be graded yet"})
    report = {"policy_id": policy, "arm_ids": sorted({y["arm_id"] for y in per_year}),
              "annual": annual, "horizon": horizon, "per_forecast_year": per_year, "skipped_forecast_years": skipped,
              "absent": absent, "n_boot": n_boot, "seed": seed, "unresolved_as_zero": unresolved_as_zero}
    return report, predictions


COMPARED = (("annual", 1, "p_qual_year", "brier"), ("annual", 1, "p_qual_year", "log_loss"), ("annual", 1, "p_qual_year", "auc"),
            ("annual", 1, "p_appear_year", "brier"), ("annual", 1, "e_points_year", "rmse"),
            ("annual", 3, "p_qual_year", "brier"), ("annual", 3, "e_points_year", "rmse"))
LOSS_METRICS = {"brier", "log_loss", "rmse"}


def _metric(rows: pd.DataFrame, ycol: str, pcol: str, metric: str) -> float:
    ok = rows[ycol].notna() & rows[pcol].notna()
    y, p = rows.loc[ok, ycol].to_numpy(dtype=float), rows.loc[ok, pcol].to_numpy(dtype=float)
    if len(y) == 0:
        return float("nan")
    if metric == "brier":
        return float(brier_score_loss(y.astype(int), np.clip(p, 1e-6, 1 - 1e-6)))
    if metric == "log_loss":
        return float(log_loss(y.astype(int), np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1]))
    if metric == "auc":
        return float(roc_auc_score(y.astype(int), p)) if len(set(y.astype(int).tolist())) == 2 else float("nan")
    return float(np.sqrt(np.mean((y - p) ** 2)))


def policy_experiment(cohort: pd.DataFrame, *, policy: str, exploratory: tuple[str, ...] = ("plain",), **kwargs) -> dict:
    """Evaluate the DECLARED policy and, beside it, exploratory alternatives.

    The policy is fixed before the outer loop runs (round-2 review, item 1): its outer
    evaluation is never swapped for an alternative's on the strength of that same outer
    loop. It is a retrospective historical evaluation with forecast cutoffs enforced, not
    untouched independent confirmation: the menu was refined after these years were seen. Alternatives are compared to it by a PAIRED
    bootstrap of the difference (the two arms grade the same test rows, so rows are
    resampled once and both arms re-scored on the same draw); the comparison is
    exploratory and is labelled so. No decision is made here.
    """
    n_boot = int(kwargs.get("n_boot", 1000))
    rng = np.random.default_rng(int(kwargs.get("seed", 20260906)) + 1)
    arms, predictions = {}, {}
    for name in (policy,) + tuple(a for a in exploratory if a != policy):
        report, rows = evaluate_forecast_years(cohort, policy=name, **kwargs)
        arms[name] = report
        predictions[name] = rows
    base = predictions[policy].set_index(["forecast_year", "gsis_id"])
    comparison: dict[str, dict] = {}
    for name in exploratory:
        if name == policy:
            continue
        other = predictions[name].set_index(["forecast_year", "gsis_id"]).loc[base.index]
        comparison[name] = {}
        for block, key, quantity, metric in COMPARED:
            label = f"{quantity}{key}"
            ycol = {"p_qual_year": f"qy_{key}", "p_appear_year": f"appear_{key}", "e_points_year": f"points_{key}"}[quantity]
            pcol = f"{quantity}{key}"
            if ycol not in base.columns or pcol not in base.columns:
                continue  # a season beyond the requested horizons is not compared
            pv, ev = _metric(base, ycol, pcol, metric), _metric(other, ycol, pcol, metric)
            diffs = []
            idx = np.arange(len(base))
            for _ in range(n_boot):
                take = idx[rng.integers(0, len(idx), len(idx))]
                b, o = base.iloc[take], other.iloc[take]
                diffs.append(_metric(o, ycol, pcol, metric) - _metric(b, ycol, pcol, metric))
            diffs = np.array(diffs, dtype=float)
            diffs = diffs[~np.isnan(diffs)]
            ci = [float(v) for v in np.percentile(diffs, [5, 95])] if len(diffs) else [float("nan"), float("nan")]
            comparison[name].setdefault(label, {})[metric] = {
                "policy": pv, "exploratory": ev, "difference": ev - pv, "difference_ci90": ci,
                "reading": ("positive difference favours the policy" if metric in LOSS_METRICS else "negative difference favours the policy"),
            }
    return {
        "policy": policy,
        "arms": arms,
        "predictions": predictions,
        "comparison": comparison,
        # Copy correction (Codex, 2026-09-06): the policy MENU was refined after inspecting
        # these historical years, so the outer evaluation is a retrospective historical
        # evaluation with forecast cutoffs enforced — not untouched independent confirmation.
        "evidence_status": {
            policy: "retrospective historical evaluation with forecast cutoffs enforced; the policy selects, if at all, only inside "
                    "each training window, but the policy menu itself was refined after inspecting these historical years, so this "
                    "is not untouched independent confirmation",
            **{name: "exploratory comparison against the declared policy on the same retrospective evaluation; never used to "
                     "reassign the canonical evidence"
               for name in exploratory if name != policy},
        },
        "paired_bootstrap": {"n_boot": n_boot, "rows": int(len(base)), "resampling": "test rows (forecast year, prospect) drawn once per replicate, both arms re-scored on the same draw"},
    }
