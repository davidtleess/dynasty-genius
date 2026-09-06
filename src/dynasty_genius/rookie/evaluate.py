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

__all__ = ["evaluate_forecast_years", "fit_at_forecast_year", "training_frame_at", "trend_experiment"]

MIN_TRAIN_ROWS = 100
# Inner validation for the trend option: the most recent classes whose season-1 labels
# were complete at the cutoff. Three classes is the smallest window that can tell a
# trend from one odd class; nothing later than T-1 is ever read.
TREND_VALIDATION_CLASSES = 3

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


def _inner_trend_selection(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: tuple[int, ...],
    forecast_year: int,
    unresolved_as_zero: bool,
) -> dict:
    """Choose plain vs class-year trend INSIDE the training window at T.

    Inner cutoff T' = T − K: fit both variants on classes < T' with labels through T' − 1,
    validate on classes T' .. T − 1 with labels through T − 1 (season 1 of each is complete
    at T). Nothing at or after T is read, so the selection is a decision a forecaster at T
    could have made.
    """
    K = TREND_VALIDATION_CLASSES
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
    for name, flag in (("plain", False), ("trend", True)):
        model = RookieCapitalModel(horizons=horizons, trend=flag).fit(inner_train)
        pred = model.predict(validation)
        yq, ya = validation["qy_1"].to_numpy(dtype=int), validation["appear_1"].to_numpy(dtype=int)
        pq = np.clip(pred["p_qual_year1"].to_numpy(), 1e-6, 1 - 1e-6)
        pa = np.clip(pred["p_appear_year1"].to_numpy(), 1e-6, 1 - 1e-6)
        yp, ep = validation["points_1"].to_numpy(dtype=float), pred["e_points_year1"].to_numpy()
        scores[name] = {
            "log_loss_p_qual_year1": float(log_loss(yq, pq, labels=[0, 1])),
            "log_loss_p_appear_year1": float(log_loss(ya, pa, labels=[0, 1])),
            "rmse_e_points_year1": float(np.sqrt(np.mean((yp - ep) ** 2))),
            "n_validation": int(len(validation)),
        }
    improvements = sum(
        scores["trend"][k] < scores["plain"][k]
        for k in ("log_loss_p_qual_year1", "log_loss_p_appear_year1", "rmse_e_points_year1")
    )
    return {
        "selected": bool(improvements >= 2),
        "rule": "trend wins if it improves at least two of the three season-1 validation scores; otherwise the simpler model",
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
    trend: bool | str = False,
) -> RookieCapitalModel:
    """THE procedure: historical evaluation and final scoring both call this.

    ``trend`` is False (plain), True (class-year term), or "auto" (chosen inside the
    training window by ``_inner_trend_selection``; the choice is recorded on the model).
    """
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    train = training_frame_at(
        cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
        forecast_year=forecast_year, unresolved_as_zero=unresolved_as_zero,
    )
    selection = None
    if trend == "auto":
        selection = _inner_trend_selection(cohort, qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                                           forecast_year=forecast_year, unresolved_as_zero=unresolved_as_zero)
        use_trend = selection["selected"]
    else:
        use_trend = bool(trend)
    model = RookieCapitalModel(horizons=horizons, trend=use_trend).fit(train)
    model.trend_selection = selection
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
    trend: bool | str = False,
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
                                     forecast_year=T, unresolved_as_zero=unresolved_as_zero, trend=trend)
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
                         "trend": bool(model.trend), "trend_selection": model.trend_selection,
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
    report = {"annual": annual, "horizon": horizon, "per_forecast_year": per_year, "skipped_forecast_years": skipped,
              "absent": absent, "n_boot": n_boot, "seed": seed, "unresolved_as_zero": unresolved_as_zero,
              "trend": trend if isinstance(trend, str) else bool(trend)}
    return report, predictions


TREND_COMPARISON = (("annual", 1, "p_qual_year", "brier"), ("annual", 1, "p_qual_year", "log_loss"),
                    ("annual", 1, "p_appear_year", "brier"), ("annual", 1, "e_points_year", "rmse"),
                    ("annual", 3, "p_qual_year", "brier"), ("annual", 3, "e_points_year", "rmse"))


def trend_experiment(cohort: pd.DataFrame, **kwargs) -> dict:
    """The bounded bias experiment: plain vs auto-selected class-year trend, both graded
    out of time with the same procedure. Decision rule: the trend arm replaces the plain
    model only if it improves a majority of the compared out-of-time metrics; otherwise the
    simpler model stays. Both arms are reported whatever the decision."""
    arms = {}
    for name, flag in (("plain", False), ("auto_trend", "auto")):
        report, _ = evaluate_forecast_years(cohort, trend=flag, **kwargs)
        arms[name] = report
    comparison = {}
    wins = 0
    for block, key, quantity, metric in TREND_COMPARISON:
        plain = arms["plain"].get(block, {}).get(key, {}).get(quantity, {}).get(metric, np.nan)
        auto = arms["auto_trend"].get(block, {}).get(key, {}).get(quantity, {}).get(metric, np.nan)
        label = f"{quantity}{key}"
        comparison.setdefault(label, {}).update({
            f"plain_{metric}": plain, f"auto_trend_{metric}": auto,
            f"improvement_{metric}": (plain - auto) if np.isfinite(plain) and np.isfinite(auto) else np.nan,
        })
        if np.isfinite(plain) and np.isfinite(auto) and auto < plain:
            wins += 1
    selections = [y.get("trend_selection", {}).get("selected") for y in arms["auto_trend"]["per_forecast_year"]]
    decision = "auto_trend" if wins > len(TREND_COMPARISON) / 2 else "plain"
    return {"arms": arms, "comparison": comparison, "metrics_compared": len(TREND_COMPARISON), "auto_trend_wins": wins,
            "auto_selected_trend_in_forecast_years": int(sum(1 for s in selections if s)),
            "forecast_years_evaluated": len(selections), "decision": decision,
            "rule": "auto_trend replaces plain only if it improves a majority of the compared out-of-time metrics"}
