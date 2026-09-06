"""DG-177 — an honest historical evaluation path for veteran forecast candidates.

Every arm here is scored the same way: walk forward by feature season, fit every
transform inside the training window, and only ever forecast a test season whose
training labels were fully KNOWN at the cutoff. The label (``avg_ppg_t1_t2``) for a row
with feature season ``t`` is the mean PPG over seasons ``t+1`` and ``t+2``, so it is
final only once season ``t+2`` has been played. A forecast made after season ``s``
may therefore train on rows with ``t + 2 <= s`` and nothing later.

Two rules are named rather than defaulted:

``labels_known_at_cutoff``
    ``t + LABEL_WINDOW_SEASONS <= s``. The honest rule, and the same admissibility the
    deployed trainer encodes as ``no_shared_outcome_season`` (DG-026) for a single test
    season. ``tests/test_dg177_veteran_candidate.py`` asserts the two never drift.
``window_closed_before_test``
    ``t + LABEL_WINDOW_SEASONS < s``. Stricter than needed by one season; it is what
    DG-162's walk-forward used, and is kept so that table can be reproduced exactly.

What this module refuses to do quietly (each is a test):
  * train on a row whose outcome window is still open at the cutoff
    (``FutureLabelError``), even if a caller hands it one;
  * fit any arm whose feature list names a future season or a third-party projection,
    ranking or price (the Engine B contract's gates, applied before any fit);
  * drop a fold that is too thin — it is written as skipped, with its counts;
  * overwrite a run directory.

Uncertainty is the bootstrapped DIFFERENCE between two arms scored on identical rows,
resampling PLAYERS rather than rows because the same player appears in several test
seasons. Separate per-arm intervals would assume an independence that does not hold.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.dynasty_genius.models.engine_b_contract import (
    OUTCOME_COLUMN,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
)
from src.dynasty_genius.models.label_closure import (  # noqa: F401  (re-exported)
    CUTOFF_RULES,
    LABEL_WINDOW_SEASONS,
    FutureLabelError,
    admissible_train_seasons,
    assert_labels_known,
)
from src.dynasty_genius.models.leak_free_tuning import (
    make_imputer,
    select_alpha_leak_free,
)

#: The penalty grid the served Engine B v2 pickles were selected from
#: (scripts/train_engine_b.py ALPHA_CANDIDATES; served alphas 1000/500/200/10 all lie on it).
DEPLOYED_ALPHA_GRID: tuple[float, ...] = (0.1, 1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0)

#: How the served pickles were fitted: a median imputer that keeps an all-missing column
#: (as zeros) rather than dropping it, then RidgeCV over the grid with unshuffled 5-fold
#: selection. Reproduced here so the "deployed" arm is the deployed recipe, not a cousin.
DEPLOYED_RECIPE = "SimpleImputer(median, keep_empty_features) -> RidgeCV(alphas=grid, cv=5)"

CI_PERCENTILES = (5.0, 95.0)


# ── folds ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Fold:
    test_season: int
    train_seasons: list[int]
    n_train: int
    n_test: int
    n_train_players: int
    n_test_players: int
    skipped_reason: str | None


def build_folds(
    df: pd.DataFrame,
    test_seasons: Iterable[int],
    rule: str = "labels_known_at_cutoff",
    min_train_rows: int = 60,
    min_test_rows: int = 10,
) -> list[Fold]:
    """One fold per requested test season. A thin fold is returned skipped, never omitted."""
    seasons = sorted(int(s) for s in df["feature_season"].unique())
    folds: list[Fold] = []
    for s in sorted(int(t) for t in test_seasons):
        train_seasons = admissible_train_seasons(seasons, s, rule=rule)
        train = df[df["feature_season"].isin(train_seasons)]
        test = df[df["feature_season"] == s]
        reason: str | None = None
        if len(train) < min_train_rows:
            reason = f"train rows {len(train)} < minimum {min_train_rows}"
        elif len(test) < min_test_rows:
            reason = f"test rows {len(test)} < minimum {min_test_rows}"
        folds.append(Fold(
            test_season=s,
            train_seasons=train_seasons,
            n_train=int(len(train)),
            n_test=int(len(test)),
            n_train_players=int(train["player_id"].nunique()) if "player_id" in train else 0,
            n_test_players=int(test["player_id"].nunique()) if "player_id" in test else 0,
            skipped_reason=reason,
        ))
    return folds


# ── the feature gate ──────────────────────────────────────────────────────────

def validate_candidate_features(features: list[str]) -> None:
    """Refuse future-season columns and third-party projections/rankings/prices.

    Delegates to the Engine B contract so this path and the trainer cannot disagree
    about what a leak is. DG-173's class patterns are inside
    ``validate_no_prohibited_features``.
    """
    validate_no_temporal_leakage(list(features))
    validate_no_prohibited_features(list(features))


# ── fitting inside the window ─────────────────────────────────────────────────

#: ``leak_free`` is the corrected procedure and the one final scoring fits: the ridge
#: penalty is chosen on expanding-time inner folds clustered on player with every inner
#: training label closed at its validation season and the imputer fitted inside each
#: inner fold; the final model is a median imputer on the whole training window and a
#: Ridge at that penalty. ``deployed_reproduction`` is the served 2026-08-31 recipe —
#: RidgeCV with random, player-leaky 5-fold selection inside the training window —
#: kept as a NAMED reproduction arm, never as a candidate.
RECIPES = ("leak_free", "deployed_reproduction")
LEAK_FREE_FINAL_FIT = "median_imputer_on_training_window -> Ridge(alpha)"
DEPLOYED_REPRODUCTION_FINAL_FIT = "median_imputer_on_training_window -> RidgeCV(alphas, cv=5)"


class RecipeCannotFit(ValueError):
    """The recipe cannot be fitted honestly on this training window (e.g. too few
    closed seasons for an inner selection). A fold is skipped, never degraded."""


def fit_arm(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    *,
    recipe: str = "leak_free",
    alphas: Iterable[float] = DEPLOYED_ALPHA_GRID,
    outcome: str = OUTCOME_COLUMN,
    window: int = LABEL_WINDOW_SEASONS,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit one arm on ``train`` only and forecast ``test``; return predictions and how
    the fit was made. Nothing is fitted on ``test``."""
    if recipe not in RECIPES:
        raise ValueError(f"unknown recipe {recipe!r}; expected one of {RECIPES}")
    alphas = [float(a) for a in alphas]
    x_train_raw = train[list(features)].astype(float).to_numpy()
    x_test_raw = test[list(features)].astype(float).to_numpy()
    y_train = train[outcome].to_numpy(dtype=float)

    if recipe == "leak_free":
        try:
            alpha, selection = select_alpha_leak_free(
                x_train_raw, y_train, train["feature_season"].to_numpy(),
                train["player_id"].to_numpy(), alphas, window=window,
            )
        except ValueError as err:
            raise RecipeCannotFit(f"leak_free alpha selection: {err}") from err
        imputer = make_imputer("median")
        model = Ridge(alpha=alpha).fit(imputer.fit_transform(x_train_raw), y_train)
        meta = {
            "recipe": recipe,
            "alpha": float(alpha),
            "alpha_grid": alphas,
            "alpha_selection": {k: v for k, v in selection.items() if k != "fold_indices"},
            "final_fit": LEAK_FREE_FINAL_FIT,
        }
    else:
        imputer = make_imputer("median")
        model = RidgeCV(alphas=alphas, cv=5).fit(imputer.fit_transform(x_train_raw), y_train)
        meta = {
            "recipe": recipe,
            "alpha": float(model.alpha_),
            "alpha_grid": alphas,
            "alpha_selection": {
                "method": "RidgeCV random unshuffled 5-fold within the training window "
                          "(served 2026-08-31 recipe; the same player can sit on both sides)",
            },
            "final_fit": DEPLOYED_REPRODUCTION_FINAL_FIT,
        }
    pred = np.asarray(model.predict(imputer.transform(x_test_raw)), dtype=float)
    return pred, meta


def fit_predict_arm(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    *,
    recipe: str = "leak_free",
    alphas: Iterable[float] = DEPLOYED_ALPHA_GRID,
    outcome: str = OUTCOME_COLUMN,
) -> np.ndarray:
    """Predictions only; see ``fit_arm``."""
    pred, _ = fit_arm(train, test, features, recipe=recipe, alphas=alphas, outcome=outcome)
    return pred


# ── metrics ───────────────────────────────────────────────────────────────────

def _topk_overlap(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    k = int(min(k, len(y_true)))
    if k <= 0:
        return float("nan")
    top_true = set(np.argsort(-y_true, kind="stable")[:k])
    top_pred = set(np.argsort(-y_pred, kind="stable")[:k])
    return len(top_true & top_pred) / k


def _spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 3 or np.all(y_pred == y_pred[0]):
        return float("nan")
    return float(scipy_stats.spearmanr(y_true, y_pred).statistic)


TOPK_BY_SEASON = "mean_over_forecast_seasons"
TOPK_SINGLE = "single_forecast_season"


def _topk_by_fold(y_true: np.ndarray, y_pred: np.ndarray, k: int, fold_ids: np.ndarray | None) -> float:
    """Top-k overlap taken WITHIN each forecast season and averaged, never over the
    concatenation of years — a top-k over concatenated seasons is dominated by whichever
    season scored highest, which is not a ranking question anyone asks."""
    if fold_ids is None:
        return _topk_overlap(y_true, y_pred, k)
    fold_ids = np.asarray(fold_ids)
    values = [_topk_overlap(y_true[fold_ids == f], y_pred[fold_ids == f], k) for f in np.unique(fold_ids)]
    values = [v for v in values if np.isfinite(v)]
    return float(np.mean(values)) if values else float("nan")


def score_predictions(
    y_true: np.ndarray, y_pred: np.ndarray, k: int, fold_ids: np.ndarray | None = None
) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "n": int(len(y_true)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else float("nan"),
        "spearman": _spearman(y_true, y_pred),
        "topk_overlap": _topk_by_fold(y_true, y_pred, k, fold_ids),
        "topk_aggregation": TOPK_BY_SEASON if fold_ids is not None else TOPK_SINGLE,
        "k": int(min(k, len(y_true))),
    }


_DELTA_METRICS = ("rmse", "r2", "spearman", "topk_overlap")


def paired_cluster_bootstrap(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    groups: np.ndarray,
    *,
    draws: int,
    seed: int,
    k: int,
    fold_ids: np.ndarray | None = None,
) -> dict[str, Any]:
    """Bootstrap ``metric(b) - metric(a)`` on identical rows, resampling clusters.

    ``groups`` is the player id per row. Clusters are drawn from the union of both arms'
    rows — which is the same set, because a paired comparison scores both arms on the
    same rows — so a player who appears in several test seasons moves as a block.
    """
    y_true = np.asarray(y_true, dtype=float)
    pred_a = np.asarray(pred_a, dtype=float)
    pred_b = np.asarray(pred_b, dtype=float)
    groups = np.asarray(groups)
    fold_ids = None if fold_ids is None else np.asarray(fold_ids)
    if not (len(y_true) == len(pred_a) == len(pred_b) == len(groups)):
        raise ValueError("paired bootstrap needs one y_true, pred_a, pred_b and group per row")

    def deltas(idx: np.ndarray) -> dict[str, float]:
        f = None if fold_ids is None else fold_ids[idx]
        a = score_predictions(y_true[idx], pred_a[idx], k, fold_ids=f)
        b = score_predictions(y_true[idx], pred_b[idx], k, fold_ids=f)
        return {m: b[m] - a[m] for m in _DELTA_METRICS}

    point = deltas(np.arange(len(y_true)))
    members = {g: np.flatnonzero(groups == g) for g in np.unique(groups)}
    keys = np.array(list(members.keys()), dtype=object)
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {m: [] for m in _DELTA_METRICS}
    for _ in range(int(draws)):
        picked = rng.choice(keys, size=len(keys), replace=True)
        idx = np.concatenate([members[g] for g in picked])
        for m, v in deltas(idx).items():
            samples[m].append(v)

    out: dict[str, Any] = {
        "rows": int(len(y_true)),
        "clusters": int(len(keys)),
        "draws": int(draws),
        "seed": int(seed),
        "ci": f"percentile_{CI_PERCENTILES[0]:g}_{CI_PERCENTILES[1]:g}",
        "topk_aggregation": TOPK_BY_SEASON if fold_ids is not None else TOPK_SINGLE,
    }
    for m in _DELTA_METRICS:
        arr = np.asarray(samples[m], dtype=float)
        arr = arr[np.isfinite(arr)]
        lo, hi = (float(v) for v in np.percentile(arr, CI_PERCENTILES)) if arr.size else (float("nan"),) * 2
        out[f"delta_{m}"] = {"point": float(point[m]), "ci90": [lo, hi]}
    return out


# ── the whole evaluation ──────────────────────────────────────────────────────

def run_candidate_evaluation(
    df: pd.DataFrame,
    *,
    arms: dict[str, list[str]],
    test_seasons: Iterable[int],
    reference_arms: list[str],
    k_by_position: dict[str, int],
    rule: str = "labels_known_at_cutoff",
    min_train_rows: int = 60,
    min_test_rows: int = 10,
    draws: int = 2000,
    seed: int = 20260906,
    alphas: Iterable[float] = DEPLOYED_ALPHA_GRID,
    outcome: str = OUTCOME_COLUMN,
    recipe: str = "leak_free",
    arm_recipes: dict[str, str] | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Score every arm on identical walk-forward test rows, per position.

    Returns ``(results, predictions)``: a JSON-ready dict and a row-level frame with one
    row per (test row, arm). Every arm is retained whatever it scores; every requested
    fold appears, skipped or not. Paired differences are reported against EACH arm in
    ``reference_arms`` — the ticket's two questions ("does the deployed set beat recent
    production?" and "does the family earn its place over the deployed set?") need two
    references, and a reference is never compared with itself.
    """
    reference_arms = list(reference_arms)
    unknown = [r for r in reference_arms if r not in arms]
    if unknown or not reference_arms:
        raise ValueError(f"reference arms {unknown or reference_arms!r} are not among {sorted(arms)}")
    recipes_by_arm = {name: (arm_recipes or {}).get(name, recipe) for name in arms}
    for name, r in recipes_by_arm.items():
        if r not in RECIPES:
            raise ValueError(f"arm {name!r} names unknown recipe {r!r}; expected one of {RECIPES}")
    for name, features in arms.items():
        validate_candidate_features(features)
        missing = sorted(set(features) - set(df.columns))
        if missing:
            raise ValueError(f"arm {name!r} names columns the frame does not carry: {missing}")

    eligible = df
    if "training_eligible" in eligible.columns:
        eligible = eligible[eligible["training_eligible"].astype(bool)]
    eligible = eligible[eligible[outcome].notna()]

    alphas = tuple(float(a) for a in alphas)
    test_seasons = sorted(int(s) for s in test_seasons)
    positions: dict[str, Any] = {}
    prediction_rows: list[pd.DataFrame] = []

    for position in sorted(eligible["position"].unique()):
        pos_df = eligible[eligible["position"] == position]
        k = int(k_by_position.get(position, 12))
        folds_out: list[dict[str, Any]] = []
        pooled: dict[str, dict[str, list[np.ndarray]]] = {
            name: {"y_true": [], "y_pred": [], "groups": [], "fold_ids": []} for name in arms
        }
        for fold in build_folds(pos_df, test_seasons, rule=rule,
                                min_train_rows=min_train_rows, min_test_rows=min_test_rows):
            record: dict[str, Any] = {**asdict(fold), "arms": {}, "fit": {}, "deltas": {}}
            if fold.skipped_reason is None:
                train = pos_df[pos_df["feature_season"].isin(fold.train_seasons)]
                test = pos_df[pos_df["feature_season"] == fold.test_season]
                assert_labels_known(train, fold.test_season, rule=rule)
                y_true = test[outcome].to_numpy(dtype=float)
                groups = test["player_id"].to_numpy()
                preds: dict[str, np.ndarray] = {}
                try:
                    for name, features in arms.items():
                        preds[name], record["fit"][name] = fit_arm(
                            train, test, features, recipe=recipes_by_arm[name],
                            alphas=alphas, outcome=outcome,
                        )
                except RecipeCannotFit as err:
                    # Paired comparison needs every arm on identical rows: if one recipe
                    # cannot be fitted honestly here, the whole fold is skipped and says why.
                    record.update({"skipped_reason": str(err), "arms": {}, "fit": {}, "deltas": {}})
                    folds_out.append(record)
                    continue
                for name in arms:
                    record["arms"][name] = score_predictions(y_true, preds[name], k)
                    pooled[name]["y_true"].append(y_true)
                    pooled[name]["y_pred"].append(preds[name])
                    pooled[name]["groups"].append(groups)
                    pooled[name]["fold_ids"].append(np.full(len(y_true), fold.test_season))
                    prediction_rows.append(pd.DataFrame({
                        "player_id": test["player_id"].to_numpy(),
                        "position": position,
                        "feature_season": fold.test_season,
                        "arm": name,
                        "y_true": y_true,
                        "y_pred": preds[name],
                    }))
                for reference in reference_arms:
                    record["deltas"][reference] = {
                        name: paired_cluster_bootstrap(
                            y_true, preds[reference], preds[name], groups,
                            draws=draws, seed=seed, k=k,
                        )
                        for name in arms if name != reference
                    }
            folds_out.append(record)

        evaluated = [f["test_season"] for f in folds_out if f["skipped_reason"] is None]
        pooled_metrics: dict[str, Any] = {}
        pooled_deltas: dict[str, Any] = {}
        if evaluated:
            cat = {name: {key: np.concatenate(v) for key, v in parts.items()}
                   for name, parts in pooled.items()}
            for name in arms:
                pooled_metrics[name] = score_predictions(
                    cat[name]["y_true"], cat[name]["y_pred"], k, fold_ids=cat[name]["fold_ids"]
                )
            for reference in reference_arms:
                ref = cat[reference]
                pooled_deltas[reference] = {
                    name: paired_cluster_bootstrap(
                        ref["y_true"], ref["y_pred"], cat[name]["y_pred"], ref["groups"],
                        draws=draws, seed=seed, k=k, fold_ids=ref["fold_ids"],
                    )
                    for name in arms if name != reference
                }
        positions[position] = {
            "k": k,
            "evaluated_test_seasons": evaluated,
            "folds": folds_out,
            "pooled": pooled_metrics,
            "deltas": pooled_deltas,
        }

    results = {
        "config": {
            "rule": rule,
            "label_window_seasons": LABEL_WINDOW_SEASONS,
            "test_seasons": test_seasons,
            "reference_arms": reference_arms,
            "arms": {name: list(features) for name, features in arms.items()},
            "recipe": recipe,
            "recipes_by_arm": recipes_by_arm,
            "recipe_definitions": {
                "leak_free": "alpha on expanding-time inner folds clustered on player, inner labels "
                             "closed at the validation season, imputer fitted inside each inner fold; "
                             + LEAK_FREE_FINAL_FIT,
                "deployed_reproduction": "the served 2026-08-31 recipe: " + DEPLOYED_RECIPE,
            },
            "alpha_grid": list(alphas),
            "min_train_rows": min_train_rows,
            "min_test_rows": min_test_rows,
            "bootstrap_draws": draws,
            "bootstrap_seed": seed,
            "k_by_position": {p: int(k) for p, k in k_by_position.items()},
            "outcome": outcome,
            "population": "training_eligible rows with an observed outcome "
                          "(E[points | returned]; P(returns) is the availability model's question)",
        },
        "positions": positions,
    }
    predictions = (
        pd.concat(prediction_rows, ignore_index=True)
        if prediction_rows
        else pd.DataFrame(columns=["player_id", "position", "feature_season", "arm", "y_true", "y_pred"])
    )
    return results, predictions


# ── the run-scoped artifact ───────────────────────────────────────────────────

def write_run_artifact(
    out_dir: Path,
    results: dict[str, Any],
    predictions: pd.DataFrame,
    *,
    provenance: dict[str, Any],
    report_md: str,
) -> list[str]:
    """Write results.json, predictions.csv and report.md into a NEW directory only."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise FileExistsError(f"run directory already exists and is never overwritten: {out_dir}")
    out_dir.mkdir(parents=True)
    (out_dir / "results.json").write_text(
        json.dumps({**results, "provenance": provenance}, indent=2, default=_json_default) + "\n"
    )
    predictions.to_csv(out_dir / "predictions.csv", index=False)
    (out_dir / "report.md").write_text(report_md)
    return ["results.json", "predictions.csv", "report.md"]


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")
