"""DG-177 round 1, item 3 — annual forecast candidates on the appearance event.

For each horizon j after the feature season, on the event A_j = "appeared: >= 1
stat-row game in season t+j" (``annual_outcomes.EVENT``), and with every quantity on
the same rows so a consumer can compose them:

    p_appear_year{j}                 P(A_j | x_t)
    e_points_year{j}_given_appear    E[points_j | A_j, x_t]
    e_games_year{j}_given_appear     E[games_j  | A_j, x_t]
    e_points_year{j}                 = p x E[points | A]   (points are exactly 0 when absent)
    e_games_year{j}                  = p x E[games  | A]

Fitting is the corrected procedure (review item 1 and 4): the probability model has no
hyper-parameter and fits its imputer and scaler on training rows only; the two
conditional ridges choose their penalty with ``select_alpha_leak_free`` at window j
(inner labels closed at the inner validation season, imputer inside each inner fold)
and are then fitted on the whole training window. Censored and unresolved rows train
nothing. Baselines are training-only: the training appearance rate; last season's
points scaled by the training window's aggregate retention ratio; the training mean of
games among those who appeared.

Report-only research. Nothing here is served.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.eval.annual_outcomes import EVENT, EXPOSURE
from src.dynasty_genius.eval.veteran_candidate import (
    RecipeCannotFit,
    paired_cluster_bootstrap,
    score_predictions,
)
from src.dynasty_genius.models.availability import auc, brier
from src.dynasty_genius.models.label_closure import (
    admissible_train_seasons,
    assert_labels_known,
)
from src.dynasty_genius.models.leak_free_tuning import (
    make_imputer,
    select_alpha_leak_free,
)

ALPHA_GRID: tuple[float, ...] = (0.1, 1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0)
PROBABILITY_MODEL = (
    "median_imputer -> StandardScaler -> LogisticRegression(max_iter=2000); "
    "no hyper-parameter; preprocessing fitted on observed training rows only"
)
CALIBRATION_BINS = 10

# ── the selection policy (round 2, item 4) ────────────────────────────────────
#: One explicit space: the training-only baseline, the candidate, or a bounded convex
#: blend of the two. Chosen PER QUANTITY on closed inner folds inside the training
#: window (the candidate refit leak-free inside each inner fold), then applied by the
#: same function final scoring calls. The outer score of the chosen policy is the
#: evidence; per-arm outer scores are exploratory comparisons.
POLICY_SPACE: tuple[str, ...] = ("baseline", "candidate", "blend_0.25", "blend_0.5", "blend_0.75")
POLICY_QUANTITIES: tuple[str, ...] = ("p_appear", "points_given_appear", "games_given_appear")
SELECTION_CRITERION = {"p_appear": "brier", "points_given_appear": "mse", "games_given_appear": "mse"}
FINAL_FIT_PARITY = "fit_policy is the function final scoring calls"
MIN_INNER_ROWS = 10


def QUANTITIES(horizon: int) -> list[str]:  # noqa: N802  (reads as the contract's noun)
    j = int(horizon)
    return [
        f"p_appear_year{j}",
        f"e_points_year{j}_given_appear",
        f"e_games_year{j}_given_appear",
        f"e_points_year{j}",
        f"e_games_year{j}",
    ]


def observed_mask(df: pd.DataFrame, horizon: int) -> pd.Series:
    """Rows whose year-j label is an observation: not censored, identity resolved, label present."""
    j = int(horizon)
    return (
        ~df[f"censored_year{j}"].astype(bool)
        & (df["identity_status"] == "resolved")
        & df[f"appeared_year{j}"].notna()
    )


def _ridge_leak_free(
    rows: pd.DataFrame, features: list[str], target: str, x_test: np.ndarray, *, window: int,
    alphas: Iterable[float],
) -> tuple[np.ndarray, dict[str, Any]]:
    x = rows[list(features)].astype(float).to_numpy()
    y = rows[target].to_numpy(dtype=float)
    try:
        alpha, selection = select_alpha_leak_free(
            x, y, rows["feature_season"].to_numpy(), rows["player_id"].to_numpy(),
            list(alphas), window=window,
        )
    except ValueError as err:
        raise RecipeCannotFit(f"leak_free alpha selection for {target}: {err}") from err
    imputer = make_imputer("median")
    model = Ridge(alpha=alpha).fit(imputer.fit_transform(x), y)
    pred = np.asarray(model.predict(imputer.transform(x_test)), dtype=float)
    meta = {
        "recipe": "leak_free",
        "target": target,
        "alpha": float(alpha),
        "alpha_grid": [float(a) for a in alphas],
        "alpha_selection": {k: v for k, v in selection.items() if k != "fold_indices"},
        "final_fit": "median_imputer_on_training_window -> Ridge(alpha)",
        "n_train": int(len(rows)),
    }
    return pred, meta


def fit_horizon(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    *,
    horizon: int,
    test_season: int | None = None,
    alphas: Iterable[float] = ALPHA_GRID,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Fit the five year-j quantities on ``train`` and score ``test``.

    ``test_season`` (when given) asserts that every training row's year-j label was
    closed at that cutoff; the evaluator always passes it.
    """
    j = int(horizon)
    if test_season is not None:
        assert_labels_known(train, test_season, window=j)
    obs = train[observed_mask(train, j)]
    appeared_col = f"appeared_year{j}"
    app = obs[obs[appeared_col].astype(bool)]
    if len(obs) == 0 or len(app) == 0 or obs[appeared_col].astype(int).nunique() < 2:
        raise RecipeCannotFit(
            f"year-{j} models need observed rows of both outcomes: observed {len(obs)}, appeared {len(app)}"
        )

    x_test = test[list(features)].astype(float).to_numpy()
    classifier = Pipeline([
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000)),
    ]).fit(obs[list(features)].astype(float).to_numpy(), obs[appeared_col].astype(int).to_numpy())
    p = classifier.predict_proba(x_test)[:, 1]

    e_points_raw, points_meta = _ridge_leak_free(app, features, f"points_year{j}", x_test, window=j, alphas=alphas)
    e_games_raw, games_meta = _ridge_leak_free(app, features, f"games_year{j}", x_test, window=j, alphas=alphas)
    max_games = float(app[f"games_year{j}"].max())
    e_points = np.clip(e_points_raw, 0.0, None)
    e_games = np.clip(e_games_raw, 1.0, max_games)

    pred = {
        f"p_appear_year{j}": p,
        f"e_points_year{j}_given_appear": e_points,
        f"e_games_year{j}_given_appear": e_games,
        f"e_points_year{j}": p * e_points,
        f"e_games_year{j}": p * e_games,
    }
    meta = {
        "horizon": j,
        "event": EVENT,
        "exposure": EXPOSURE,
        "features": list(features),
        "n_train_observed": int(len(obs)),
        "n_train_appeared": int(len(app)),
        "train_seasons": sorted(int(s) for s in train["feature_season"].unique()),
        "probability_model": PROBABILITY_MODEL,
        "points_model": points_meta,
        "games_model": games_meta,
        "clipping": {
            "points_given_appear_floor": 0.0,
            "points_clipped": int((e_points_raw < 0).sum()),
            "games_given_appear_range": [1.0, max_games],
            "games_clipped": int(((e_games_raw < 1.0) | (e_games_raw > max_games)).sum()),
        },
    }
    return pred, meta


def persistence_baselines(train: pd.DataFrame, test: pd.DataFrame, *, horizon: int) -> dict[str, np.ndarray]:
    """Training-only comparators: the appearance base rate; last season's points scaled
    by the training window's aggregate retention; the training mean of games among
    those who appeared."""
    j = int(horizon)
    obs = train[observed_mask(train, j)]
    app = obs[obs[f"appeared_year{j}"].astype(bool)]
    rate = float(obs[f"appeared_year{j}"].astype(float).mean())
    denominator = float(app["total_points_t"].sum())
    retention = float(app[f"points_year{j}"].sum() / denominator) if denominator > 0 else float("nan")
    games_mean = float(app[f"games_year{j}"].mean())
    n = len(test)
    e_points = test["total_points_t"].to_numpy(dtype=float) * retention
    e_games = np.full(n, games_mean)
    return {
        f"p_appear_year{j}": np.full(n, rate),
        f"e_points_year{j}_given_appear": e_points,
        f"e_games_year{j}_given_appear": e_games,
        f"e_points_year{j}": rate * e_points,
        f"e_games_year{j}": rate * e_games,
        "_definition": {
            "p": "training appearance rate",
            "points_given_appear": f"total_points_t x training retention ratio ({retention:.4f})",
            "games_given_appear": f"training mean games among appeared ({games_mean:.3f})",
        },
    }


def _calibration(truths: np.ndarray, probs: np.ndarray, bins: int = CALIBRATION_BINS) -> list[dict[str, float]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (probs >= lo) & ((probs < hi) if hi < 1.0 else (probs <= hi))
        if mask.any():
            out.append({"bin_low": float(lo), "bin_high": float(hi), "n": int(mask.sum()),
                        "mean_predicted": float(probs[mask].mean()), "observed_rate": float(truths[mask].mean())})
    return out


def _probability_block(truths: np.ndarray, p: np.ndarray, p_base: np.ndarray) -> dict[str, Any]:
    return {
        "n": int(len(truths)),
        "brier": brier(truths, p),
        "auc": auc(truths, p) if len(np.unique(truths)) > 1 else float("nan"),
        "base_rate": float(truths.mean()),
        "baseline_brier": brier(truths, p_base),
        "mean_predicted": float(p.mean()),
        "calibration": _calibration(truths, p),
    }


def _paired_block(y, base, model, groups, *, k, draws, seed, fold_ids=None) -> dict[str, Any]:
    return {
        "model": score_predictions(y, model, k, fold_ids=fold_ids),
        "baseline": score_predictions(y, base, k, fold_ids=fold_ids),
        "delta_vs_baseline": paired_cluster_bootstrap(y, base, model, groups, draws=draws, seed=seed, k=k,
                                                      fold_ids=fold_ids),
    }


def evaluate_horizon(
    df: pd.DataFrame,
    features: list[str],
    *,
    horizon: int,
    test_seasons: Iterable[int],
    k: int,
    draws: int = 2000,
    seed: int = 20260906,
    min_train_rows: int = 60,
    min_test_rows: int = 10,
    alphas: Iterable[float] = ALPHA_GRID,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Walk forward by feature season; grade every exported quantity against its own label."""
    j = int(horizon)
    seasons = sorted(int(s) for s in df["feature_season"].unique())
    folds: list[dict[str, Any]] = []
    pooled: dict[str, list[np.ndarray]] = {key: [] for key in (
        "truth_app", "p", "p_base", "groups_all", "fold_all", "y_points_all", "e_points", "e_points_base",
        "groups_app", "fold_app", "y_points_app", "e_points_app", "e_points_app_base",
        "y_games_app", "e_games_app", "e_games_app_base",
    )}
    rows_out: list[pd.DataFrame] = []

    for s in sorted(int(t) for t in test_seasons):
        train_seasons = admissible_train_seasons(seasons, s, window=j)
        train = df[df["feature_season"].isin(train_seasons)]
        test_all = df[df["feature_season"] == s]
        test = test_all[observed_mask(test_all, j)].reset_index(drop=True)
        n_train_obs = int(observed_mask(train, j).sum()) if len(train) else 0
        record: dict[str, Any] = {
            "test_season": s, "forecast_season": s + j, "train_seasons": train_seasons,
            "n_train_observed": n_train_obs, "n_test_rows": int(len(test_all)),
            "n_test_observed": int(len(test)), "n_test_appeared": int(test[f"appeared_year{j}"].astype(bool).sum()) if len(test) else 0,
            "skipped_reason": None,
        }
        if n_train_obs < min_train_rows:
            record["skipped_reason"] = f"observed train rows {n_train_obs} < minimum {min_train_rows}"
        elif len(test) < min_test_rows:
            record["skipped_reason"] = f"observed test rows {len(test)} < minimum {min_test_rows}"
        if record["skipped_reason"] is None:
            try:
                pred, meta = fit_horizon(train, test, features, horizon=j, test_season=s, alphas=alphas)
            except RecipeCannotFit as err:
                record["skipped_reason"] = str(err)
        if record["skipped_reason"] is not None:
            folds.append(record)
            continue

        base = persistence_baselines(train, test, horizon=j)
        truth_app = test[f"appeared_year{j}"].astype(int).to_numpy()
        y_points = test[f"points_year{j}"].to_numpy(dtype=float)
        y_games = test[f"games_year{j}"].to_numpy(dtype=float)
        groups = test["player_id"].to_numpy()
        app = truth_app.astype(bool)
        q = QUANTITIES(j)
        record.update({
            "fit": meta,
            "baseline_definition": base["_definition"],
            "probability": _probability_block(truth_app, pred[q[0]], base[q[0]]),
            "points_given_appear": _paired_block(y_points[app], base[q[1]][app], pred[q[1]][app], groups[app],
                                                 k=k, draws=draws, seed=seed),
            "games_given_appear": _paired_block(y_games[app], base[q[2]][app], pred[q[2]][app], groups[app],
                                                k=k, draws=draws, seed=seed),
            "points_unconditional": _paired_block(y_points, base[q[3]], pred[q[3]], groups,
                                                  k=k, draws=draws, seed=seed),
        })
        folds.append(record)

        fold_all = np.full(len(test), s)
        collected = {
            "truth_app": truth_app, "p": pred[q[0]], "p_base": base[q[0]],
            "groups_all": groups, "fold_all": fold_all,
            "y_points_all": y_points, "e_points": pred[q[3]], "e_points_base": base[q[3]],
            "groups_app": groups[app], "fold_app": fold_all[app],
            "y_points_app": y_points[app], "e_points_app": pred[q[1]][app], "e_points_app_base": base[q[1]][app],
            "y_games_app": y_games[app], "e_games_app": pred[q[2]][app], "e_games_app_base": base[q[2]][app],
        }
        for key, value in collected.items():
            pooled[key].append(value)

        frame = test[["player_id", "position", "feature_season"]].copy()
        frame["forecast_season"] = s + j
        for name in q:
            frame[name] = pred[name]
            frame[f"baseline_{name}"] = base[name]
        for col in (f"appeared_year{j}", f"games_year{j}", f"points_year{j}"):
            frame[col] = test[col].to_numpy()
        rows_out.append(frame)

    evaluated = [f["test_season"] for f in folds if f["skipped_reason"] is None]
    pooled_out: dict[str, Any] = {}
    if evaluated:
        c = {key: np.concatenate(v) for key, v in pooled.items()}
        pooled_out = {
            "n_observed": int(len(c["truth_app"])),
            "n_appeared": int(c["truth_app"].sum()),
            "probability": _probability_block(c["truth_app"], c["p"], c["p_base"]),
            "points_given_appear": _paired_block(c["y_points_app"], c["e_points_app_base"], c["e_points_app"], c["groups_app"],
                                                 k=k, draws=draws, seed=seed, fold_ids=c["fold_app"]),
            "games_given_appear": _paired_block(c["y_games_app"], c["e_games_app_base"], c["e_games_app"], c["groups_app"],
                                                k=k, draws=draws, seed=seed, fold_ids=c["fold_app"]),
            "points_unconditional": _paired_block(c["y_points_all"], c["e_points_base"], c["e_points"], c["groups_all"],
                                                  k=k, draws=draws, seed=seed, fold_ids=c["fold_all"]),
        }
    out = {
        "horizon": j,
        "event": EVENT,
        "exposure": EXPOSURE,
        "features": list(features),
        "quantities": QUANTITIES(j),
        "label_window_seasons": j,
        "evaluated_test_seasons": evaluated,
        "folds": folds,
        "pooled": pooled_out,
        "k": int(k),
    }
    predictions = pd.concat(rows_out, ignore_index=True) if rows_out else pd.DataFrame(
        columns=["player_id", "position", "feature_season", "forecast_season", *QUANTITIES(j)]
    )
    return out, predictions


def compose_policy(candidate: np.ndarray, baseline: np.ndarray, policy: str) -> np.ndarray:
    """The named combination: baseline, candidate, or w·candidate + (1−w)·baseline."""
    candidate = np.asarray(candidate, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    if policy == "baseline":
        return baseline.copy()
    if policy == "candidate":
        return candidate.copy()
    if policy.startswith("blend_") and policy in POLICY_SPACE:
        w = float(policy.split("_", 1)[1])
        return w * candidate + (1.0 - w) * baseline
    raise ValueError(f"unknown policy {policy!r}; expected one of {POLICY_SPACE}")


def _quantity_columns(j: int) -> dict[str, str]:
    return {
        "p_appear": f"p_appear_year{j}",
        "points_given_appear": f"e_points_year{j}_given_appear",
        "games_given_appear": f"e_games_year{j}_given_appear",
    }


def _inner_score(quantity: str, truth_rows: pd.DataFrame, values: np.ndarray, j: int) -> float:
    appeared = truth_rows[f"appeared_year{j}"].astype(bool).to_numpy()
    if quantity == "p_appear":
        return brier(appeared.astype(int), np.clip(values, 0.0, 1.0))
    target = f"points_year{j}" if quantity == "points_given_appear" else f"games_year{j}"
    y = truth_rows[target].to_numpy(dtype=float)[appeared]
    return float(np.mean((y - values[appeared]) ** 2)) if appeared.any() else float("nan")


def fit_policy(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    *,
    horizon: int,
    test_season: int | None = None,
    alphas: Iterable[float] = ALPHA_GRID,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Select a policy per quantity on closed inner folds, then apply it to ``test``.

    Inner fold for validation season v: training rows with feature_season + j <= v
    (observed labels), validation rows with feature_season == v. The candidate is
    refit inside each inner fold with ``fit_horizon`` (its own leak-free alpha inside),
    the baseline is recomputed on the inner training rows, and every policy in
    POLICY_SPACE is scored on the validation rows. The mean inner score picks the
    policy. The final fit uses the whole training window through the same functions.
    """
    j = int(horizon)
    if test_season is not None:
        assert_labels_known(train, test_season, window=j)
    cols = _quantity_columns(j)
    seasons = sorted(int(s) for s in train["feature_season"].unique())
    inner_folds: list[dict[str, Any]] = []
    inner_scores: dict[str, dict[str, list[float]]] = {q: {p: [] for p in POLICY_SPACE} for q in POLICY_QUANTITIES}
    for v in seasons:
        inner_train = train[(train["feature_season"].astype(int) + j <= v)]
        inner_train = inner_train[observed_mask(inner_train, j)]
        inner_val = train[train["feature_season"].astype(int) == v]
        inner_val = inner_val[observed_mask(inner_val, j)]
        if len(inner_train) < MIN_INNER_ROWS or len(inner_val) < MIN_INNER_ROWS:
            continue
        try:
            cand, _ = fit_horizon(inner_train, inner_val, features, horizon=j, alphas=alphas)
        except RecipeCannotFit:
            continue
        base = persistence_baselines(inner_train, inner_val, horizon=j)
        fold_scores: dict[str, dict[str, float]] = {}
        for q, col in cols.items():
            fold_scores[q] = {}
            for policy in POLICY_SPACE:
                score = _inner_score(q, inner_val, compose_policy(cand[col], base[col], policy), j)
                inner_scores[q][policy].append(score)
                fold_scores[q][policy] = score
        inner_folds.append({
            "validation_season": int(v),
            "train_seasons": sorted(int(s) for s in inner_train["feature_season"].unique()),
            "n_train": int(len(inner_train)), "n_validation": int(len(inner_val)),
            "scores": fold_scores,
        })
    if not inner_folds:
        raise RecipeCannotFit(
            f"policy selection for year {j}: no inner validation season with closed training rows "
            f"and a fittable candidate (seasons present: {seasons})"
        )
    mean_scores = {q: {p: float(np.nanmean(v)) if len(v) else float("nan") for p, v in per.items()}
                   for q, per in inner_scores.items()}
    policy_by_quantity = {
        q: min(POLICY_SPACE, key=lambda p: (np.isnan(mean_scores[q][p]), mean_scores[q][p]))
        for q in POLICY_QUANTITIES
    }

    cand, cand_meta = fit_horizon(train, test, features, horizon=j, alphas=alphas)
    base = persistence_baselines(train, test, horizon=j)
    p = np.clip(compose_policy(cand[cols["p_appear"]], base[cols["p_appear"]], policy_by_quantity["p_appear"]), 0.0, 1.0)
    e_points = compose_policy(cand[cols["points_given_appear"]], base[cols["points_given_appear"]],
                              policy_by_quantity["points_given_appear"])
    e_games = compose_policy(cand[cols["games_given_appear"]], base[cols["games_given_appear"]],
                             policy_by_quantity["games_given_appear"])
    pred = {
        f"p_appear_year{j}": p,
        f"e_points_year{j}_given_appear": e_points,
        f"e_games_year{j}_given_appear": e_games,
        f"e_points_year{j}": p * e_points,
        f"e_games_year{j}": p * e_games,
    }
    meta = {
        "horizon": j,
        "policy_space": list(POLICY_SPACE),
        "selection_criterion": dict(SELECTION_CRITERION),
        "policy_by_quantity": policy_by_quantity,
        "inner_folds": inner_folds,
        "inner_scores": mean_scores,
        "candidate_fit": cand_meta,
        "baseline_definition": base["_definition"],
        "final_fit_parity": FINAL_FIT_PARITY,
    }
    return pred, meta


def evaluate_horizon_policy(
    df: pd.DataFrame,
    features: list[str],
    *,
    horizon: int,
    test_seasons: Iterable[int],
    k: int,
    draws: int = 2000,
    seed: int = 20260906,
    min_train_rows: int = 60,
    min_test_rows: int = 10,
    alphas: Iterable[float] = ALPHA_GRID,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Walk forward; on each fold the POLICY (selected inside the training window) is the
    evidence, and the plain candidate arm is reported beside it as an exploratory comparison."""
    j = int(horizon)
    seasons = sorted(int(s) for s in df["feature_season"].unique())
    q = QUANTITIES(j)
    folds: list[dict[str, Any]] = []
    keys = ("truth_app", "groups", "fold", "y_points", "y_games")
    pooled: dict[str, list[np.ndarray]] = {key: [] for key in keys}
    for arm in ("policy", "candidate", "baseline"):
        for name in q:
            pooled[f"{arm}:{name}"] = []
    rows_out: list[pd.DataFrame] = []

    for s in sorted(int(t) for t in test_seasons):
        train_seasons = admissible_train_seasons(seasons, s, window=j)
        train = df[df["feature_season"].isin(train_seasons)]
        test_all = df[df["feature_season"] == s]
        test = test_all[observed_mask(test_all, j)].reset_index(drop=True)
        n_train_obs = int(observed_mask(train, j).sum()) if len(train) else 0
        record: dict[str, Any] = {
            "test_season": s, "forecast_season": s + j, "train_seasons": train_seasons,
            "n_train_observed": n_train_obs, "n_test_rows": int(len(test_all)),
            "n_test_observed": int(len(test)),
            "n_test_appeared": int(test[f"appeared_year{j}"].astype(bool).sum()) if len(test) else 0,
            "skipped_reason": None,
        }
        if n_train_obs < min_train_rows:
            record["skipped_reason"] = f"observed train rows {n_train_obs} < minimum {min_train_rows}"
        elif len(test) < min_test_rows:
            record["skipped_reason"] = f"observed test rows {len(test)} < minimum {min_test_rows}"
        if record["skipped_reason"] is None:
            try:
                pol, pol_meta = fit_policy(train, test, features, horizon=j, test_season=s, alphas=alphas)
            except RecipeCannotFit as err:
                record["skipped_reason"] = str(err)
        if record["skipped_reason"] is not None:
            folds.append(record)
            continue
        cand_pred, _ = fit_horizon(train, test, features, horizon=j, alphas=alphas)
        base = persistence_baselines(train, test, horizon=j)
        truth_app = test[f"appeared_year{j}"].astype(int).to_numpy()
        y_points = test[f"points_year{j}"].to_numpy(dtype=float)
        y_games = test[f"games_year{j}"].to_numpy(dtype=float)
        groups = test["player_id"].to_numpy()
        app = truth_app.astype(bool)

        def blocks(pred: dict[str, np.ndarray]) -> dict[str, Any]:
            return {
                "probability": _probability_block(truth_app, pred[q[0]], base[q[0]]),
                "points_given_appear": _paired_block(y_points[app], base[q[1]][app], pred[q[1]][app], groups[app],
                                                     k=k, draws=draws, seed=seed),
                "games_given_appear": _paired_block(y_games[app], base[q[2]][app], pred[q[2]][app], groups[app],
                                                    k=k, draws=draws, seed=seed),
                "points_unconditional": _paired_block(y_points, base[q[3]], pred[q[3]], groups,
                                                      k=k, draws=draws, seed=seed),
            }

        record["policy"] = {**blocks(pol), "policy_by_quantity": pol_meta["policy_by_quantity"],
                            "inner_folds": pol_meta["inner_folds"], "inner_scores": pol_meta["inner_scores"]}
        record["exploratory_candidate"] = blocks(cand_pred)
        record["fit"] = pol_meta["candidate_fit"]
        record["baseline_definition"] = base["_definition"]
        folds.append(record)

        fold_ids = np.full(len(test), s)
        for key, value in (("truth_app", truth_app), ("groups", groups), ("fold", fold_ids),
                           ("y_points", y_points), ("y_games", y_games)):
            pooled[key].append(value)
        for arm, pred in (("policy", pol), ("candidate", cand_pred), ("baseline", base)):
            for name in q:
                pooled[f"{arm}:{name}"].append(np.asarray(pred[name], dtype=float))
        frame = test[["player_id", "position", "feature_season"]].copy()
        frame["forecast_season"] = s + j
        for arm, pred in (("policy", pol), ("candidate", cand_pred), ("baseline", base)):
            for name in q:
                frame[f"{arm}_{name}"] = np.asarray(pred[name], dtype=float)
        for col in (f"appeared_year{j}", f"games_year{j}", f"points_year{j}"):
            frame[col] = test[col].to_numpy()
        rows_out.append(frame)

    evaluated = [f["test_season"] for f in folds if f["skipped_reason"] is None]
    pooled_out: dict[str, Any] = {}
    if evaluated:
        c = {key: np.concatenate(v) for key, v in pooled.items() if v}
        app = c["truth_app"].astype(bool)

        def pooled_blocks(arm: str) -> dict[str, Any]:
            g = lambda name: c[f"{arm}:{name}"]  # noqa: E731
            b = lambda name: c[f"baseline:{name}"]  # noqa: E731
            return {
                "probability": _probability_block(c["truth_app"], g(q[0]), b(q[0])),
                "points_given_appear": _paired_block(c["y_points"][app], b(q[1])[app], g(q[1])[app], c["groups"][app],
                                                     k=k, draws=draws, seed=seed, fold_ids=c["fold"][app]),
                "games_given_appear": _paired_block(c["y_games"][app], b(q[2])[app], g(q[2])[app], c["groups"][app],
                                                    k=k, draws=draws, seed=seed, fold_ids=c["fold"][app]),
                "points_unconditional": _paired_block(c["y_points"], b(q[3]), g(q[3]), c["groups"],
                                                      k=k, draws=draws, seed=seed, fold_ids=c["fold"]),
            }

        pooled_out = {
            "n_observed": int(len(c["truth_app"])), "n_appeared": int(app.sum()),
            "policy": pooled_blocks("policy"),
            "exploratory_candidate": pooled_blocks("candidate"),
            "policies_chosen_by_fold": {str(f["test_season"]): f["policy"]["policy_by_quantity"]
                                        for f in folds if f["skipped_reason"] is None},
        }
    out = {
        "horizon": j, "event": EVENT, "exposure": EXPOSURE, "features": list(features),
        "quantities": q, "label_window_seasons": j, "evaluated_test_seasons": evaluated,
        "evidence": "policy",
        "policy_space": list(POLICY_SPACE), "selection_criterion": dict(SELECTION_CRITERION),
        "folds": folds, "pooled": pooled_out, "k": int(k),
    }
    predictions = pd.concat(rows_out, ignore_index=True) if rows_out else pd.DataFrame(
        columns=["player_id", "position", "feature_season", "forecast_season"]
    )
    return out, predictions
