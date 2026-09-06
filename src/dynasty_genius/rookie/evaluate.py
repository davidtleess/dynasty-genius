"""Walk-forward evaluation with an information cutoff at every forecast year.

For forecast year T (pre-season, after the draft):

* training rows are classes c < T whose label window ended by T-1, i.e. c <= T - h for
  horizon h, labelled with ``last_completed_season = T - 1`` — nothing later exists yet;
* test rows are class T, labelled with everything completed TODAY, so a forecast made at
  T is graded against what actually happened afterwards;
* a (T, h) pair is produced only when class T's window is complete today and the training
  set has both classes; otherwise it is absent, and the report says which pairs are
  absent and why, rather than manufacturing a validation.

Metrics are computed per (T, h) and pooled over T per h, with a player-resampled bootstrap
for the pooled numbers. The comparator is the training prevalence applied to the test
class ("no model"), the honest zero-skill baseline for Brier and log loss.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.dynasty_genius.rookie.labels import SeasonKey, horizon_labels
from src.dynasty_genius.rookie.model import RookieCapitalModel

__all__ = ["Split", "evaluate_walk_forward", "walk_forward_splits"]

MIN_TRAIN_ROWS = 100


@dataclass(frozen=True)
class Split:
    forecast_year: int
    horizon: int
    train: pd.DataFrame
    test: pd.DataFrame


def walk_forward_splits(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    played: set[SeasonKey],
    horizons: Iterable[int],
    forecast_years: Iterable[int],
    last_completed_season_today: int,
    min_train_rows: int = MIN_TRAIN_ROWS,
    season_ppg: Mapping[SeasonKey, float] | None = None,
) -> list[Split]:
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    splits: list[Split] = []
    for T in sorted(set(int(t) for t in forecast_years)):
        earlier = cohort.loc[cohort["draft_season"] < T]
        current = cohort.loc[cohort["draft_season"] == T]
        if earlier.empty or current.empty:
            continue
        train_all = horizon_labels(
            earlier, qualifying=qualifying, played=played, horizons=horizons,
            last_completed_season=T - 1, season_ppg=season_ppg,
        )
        test_all = horizon_labels(
            current, qualifying=qualifying, played=played, horizons=horizons,
            last_completed_season=last_completed_season_today, season_ppg=season_ppg,
        )
        for h in horizons:
            train = train_all.loc[train_all[f"q_{h}"].notna()]
            test = test_all.loc[test_all[f"q_{h}"].notna()]
            if test.empty or len(train) < min_train_rows:
                continue
            # Arithmetic guarantee, asserted rather than trusted: no training class may
            # need a season at or after T.
            assert int(train["draft_season"].max()) <= T - h, (T, h, train["draft_season"].max())
            splits.append(Split(forecast_year=T, horizon=h, train=train, test=test))
    return splits


# --------------------------------------------------------------------------- metrics
def _binary_metrics(y: np.ndarray, p: np.ndarray, base_rate: float) -> dict[str, float]:
    out: dict[str, float] = {
        "n": int(len(y)),
        "prevalence": float(np.mean(y)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1])),
        "brier_base_rate": float(brier_score_loss(y, np.full(len(y), base_rate))),
        "log_loss_base_rate": float(log_loss(y, np.full(len(y), np.clip(base_rate, 1e-6, 1 - 1e-6)), labels=[0, 1])),
    }
    out["auc"] = float(roc_auc_score(y, p)) if len(set(y.tolist())) == 2 else float("nan")
    return out


def _count_metrics(y: np.ndarray, e: np.ndarray, base_mean: float) -> dict[str, float]:
    return {
        "n": int(len(y)),
        "mean_actual": float(np.mean(y)),
        "mean_predicted": float(np.mean(e)),
        "rmse": float(np.sqrt(np.mean((y - e) ** 2))),
        "rmse_base_rate": float(np.sqrt(np.mean((y - base_mean) ** 2))),
        "bias": float(np.mean(e - y)),
    }


def _calibration(y: np.ndarray, p: np.ndarray, edges: list[float]) -> list[dict[str, float]]:
    bins = pd.cut(p, edges, labels=False, include_lowest=True)
    rows = []
    for b in range(len(edges) - 1):
        mask = bins == b
        if not mask.any():
            continue
        rows.append(
            {
                "bin": f"{edges[b]:.2f}-{edges[b + 1]:.2f}",
                "n": int(mask.sum()),
                "predicted": float(np.mean(p[mask])),
                "actual": float(np.mean(y[mask])),
            }
        )
    return rows


def _bootstrap_ci(y: np.ndarray, p: np.ndarray, stat, n_boot: int, rng: np.random.Generator) -> list[float]:
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


def evaluate_walk_forward(
    splits: list[Split],
    *,
    n_boot: int = 1000,
    seed: int = 20260906,
) -> tuple[dict, pd.DataFrame]:
    """Fit a model per split, score its test class, pool per horizon.

    Returns ``(report, predictions)``: the report is JSON-serialisable; predictions carry
    every out-of-time test row with its labels and forecasts for anyone re-slicing it.
    """
    rng = np.random.default_rng(seed)
    frames = []
    per_split = []
    for s in splits:
        model = RookieCapitalModel(horizons=(s.horizon,)).fit(s.train)
        pred = model.predict(s.test)
        h = s.horizon
        merged = s.test[["gsis_id", "draft_season", "position", "pick", "round", "age_at_draft",
                         f"q_{h}", f"n_{h}", f"played_{h}"]].copy()
        merged["forecast_year"] = s.forecast_year
        merged["horizon"] = h
        merged["p_qual"] = pred[f"p_qual_h{h}"].to_numpy()
        merged["p_played"] = pred[f"p_played_h{h}"].to_numpy()
        merged["e_qual_seasons"] = pred[f"e_qual_seasons_h{h}"].to_numpy()
        merged = merged.rename(columns={f"q_{h}": "q", f"n_{h}": "n_qual", f"played_{h}": "played"})
        # The level, graded on the season j = h: only rows that qualified in that season
        # carry a truth, and the comparator is the training qualifiers' mean rate by position.
        has_level = f"ppg_year_{h}" in s.test.columns and f"e_ppg_given_qual_year{h}" in pred.columns
        if has_level:
            qualified_in_h = s.test[f"qy_{h}"].to_numpy() == 1
            merged["ppg_year"] = np.where(qualified_in_h, s.test[f"ppg_year_{h}"].to_numpy(), np.nan)
            merged["e_ppg_given_qual"] = np.where(qualified_in_h, pred[f"e_ppg_given_qual_year{h}"].to_numpy(), np.nan)
            train_q = s.train.loc[s.train[f"qy_{h}"] == 1]
            pos_mean = train_q.groupby("position")[f"ppg_year_{h}"].mean()
            merged["ppg_position_mean"] = np.where(qualified_in_h, s.test["position"].map(pos_mean).to_numpy(dtype=float), np.nan)
        else:
            merged["ppg_year"] = np.nan
            merged["e_ppg_given_qual"] = np.nan
            merged["ppg_position_mean"] = np.nan
        frames.append(merged)
        base_q = float(s.train[f"q_{h}"].mean())
        per_split.append(
            {
                "forecast_year": s.forecast_year,
                "horizon": h,
                "n_train": int(len(s.train)),
                "train_classes": [int(s.train["draft_season"].min()), int(s.train["draft_season"].max())],
                "n_test": int(len(s.test)),
                "qual": _binary_metrics(merged["q"].to_numpy(), merged["p_qual"].to_numpy(), base_q),
                "played": _binary_metrics(merged["played"].to_numpy(), merged["p_played"].to_numpy(),
                                          float(s.train[f"played_{h}"].mean())),
                "seasons": _count_metrics(merged["n_qual"].to_numpy(), merged["e_qual_seasons"].to_numpy(),
                                          float(s.train[f"n_{h}"].mean())),
            }
        )
    predictions = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    pooled = {}
    edges = [0.0, 0.1, 0.2, 0.35, 0.5, 0.7, 1.0]
    for h, g in predictions.groupby("horizon") if len(predictions) else []:
        y, p = g["q"].to_numpy(), g["p_qual"].to_numpy()
        yp, pp = g["played"].to_numpy(), g["p_played"].to_numpy()
        yn, en = g["n_qual"].to_numpy(), g["e_qual_seasons"].to_numpy()
        # Pooled base rate = pooled test prevalence. Per split, the no-model comparator is
        # the TRAINING prevalence (what a manager could have forecast at T); those are in
        # per_split. Pooled over many T the two are within rounding of each other.
        entry = {
            "forecast_years": sorted(int(t) for t in g["forecast_year"].unique()),
            "n": int(len(g)),
            "qual": _binary_metrics(y, p, float(np.mean(y))),
            "qual_auc_ci90": _bootstrap_ci(y, p, roc_auc_score, n_boot, rng),
            "qual_brier_ci90": _bootstrap_ci(y, p, brier_score_loss, n_boot, rng),
            "played": _binary_metrics(yp, pp, float(np.mean(yp))),
            "seasons": _count_metrics(yn, en, float(np.mean(yn))),
            "calibration_qual": _calibration(y, p, edges),
            "by_position": {},
            "by_round": {},
        }
        for pos, gp in g.groupby("position"):
            entry["by_position"][pos] = _binary_metrics(gp["q"].to_numpy(), gp["p_qual"].to_numpy(), float(gp["q"].mean()))
            entry["by_position"][pos]["seasons"] = _count_metrics(gp["n_qual"].to_numpy(), gp["e_qual_seasons"].to_numpy(), float(gp["n_qual"].mean()))
        for rnd, gr in g.groupby("round"):
            entry["by_round"][int(rnd)] = {
                "n": int(len(gr)),
                "actual_qual_rate": float(gr["q"].mean()),
                "predicted_qual_rate": float(gr["p_qual"].mean()),
                "actual_seasons": float(gr["n_qual"].mean()),
                "predicted_seasons": float(gr["e_qual_seasons"].mean()),
            }
        pooled[int(h)] = entry

    level_by_year = {}
    for h, g in predictions.groupby("horizon") if len(predictions) else []:
        q = g.loc[g["ppg_year"].notna() & g["e_ppg_given_qual"].notna()]
        if q.empty:
            continue
        y, e, base = q["ppg_year"].to_numpy(), q["e_ppg_given_qual"].to_numpy(), q["ppg_position_mean"].to_numpy()
        entry = {
            "season": int(h),
            "n": int(len(q)),
            "mean_actual": float(np.mean(y)),
            "mean_predicted": float(np.mean(e)),
            "rmse": float(np.sqrt(np.mean((y - e) ** 2))),
            "rmse_position_mean": float(np.sqrt(np.mean((y - base) ** 2))),
            "bias": float(np.mean(e - y)),
            "by_position": {},
            "by_round": {},
        }
        for pos, gp in q.groupby("position"):
            yy, ee, bb = gp["ppg_year"].to_numpy(), gp["e_ppg_given_qual"].to_numpy(), gp["ppg_position_mean"].to_numpy()
            entry["by_position"][pos] = {"n": int(len(gp)), "mean_actual": float(np.mean(yy)), "mean_predicted": float(np.mean(ee)),
                                         "rmse": float(np.sqrt(np.mean((yy - ee) ** 2))), "rmse_position_mean": float(np.sqrt(np.mean((yy - bb) ** 2)))}
        for rnd, gr in q.groupby("round"):
            entry["by_round"][int(rnd)] = {"n": int(len(gr)), "mean_actual": float(gr["ppg_year"].mean()), "mean_predicted": float(gr["e_ppg_given_qual"].mean())}
        level_by_year[int(h)] = entry

    report = {"per_split": per_split, "pooled_by_horizon": pooled, "level_by_year": level_by_year,
              "n_boot": n_boot, "seed": seed}
    return report, predictions
