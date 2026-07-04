"""BUILD-4 T3 — qb_v3 classification walk-forward validation.

Implements the ratified BUILD-4 spec §6 (docs/superpowers/specs/
2026-07-03-build4-superflex-qb-design.md). This is a NEW classification
driver: it reuses the expanding-window fold definitions and the
temporal-isolation PATTERN from the Ridge ``WalkForwardDriver`` (train =
feature_season < test_year; preprocessors fit on train folds only) but is
NOT that driver — per-horizon binary survival labels are graded on
calibration/discrimination, never R².

Honesty mechanics (all spec-pinned):
- Baseline = TRAIN-fold per-horizon prevalence applied as a constant to the
  test fold; a test-fold-prevalence baseline is a leakage defect and is
  rejected outright.
- Small-n fold-horizons emit ``low_sample_qb_holdout`` — excluded from metric
  averaging but COUNTING against promotion eligibility, judged against the
  per-horizon STRUCTURAL fold counts (H1=4/H2=4/H3=3, all-but-one evaluable).
  Per-horizon non-promotion is a supported honest outcome, never an error.
- Training uses the T2 post-abstention eligible cohort only.
- The report is descriptive diagnostics: ``decision_supported=False``
  recursively and NO promote/recommend/verdict fields — promotion is David's
  decision on the T5 record, never a field this module emits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from src.dynasty_genius.features.qb_role_occupancy_labels import (
    validate_qb_role_occupancy_label_table,
)
from src.dynasty_genius.features.qb_v3_candidate_matrix import (
    validate_qb_v3_candidate_feature_contract,
)

QB_V3_MODEL_FAMILY = "regularized_logistic_regression"
QB_V3_TOP_K = 12
QB_V3_TEST_YEARS = (2020, 2021, 2022, 2023)
# Per-horizon STRUCTURAL fold counts (spec §6, Claude F1 / Codex F5):
# eligibility is judged against these, never a hardcoded "of 4".
QB_V3_STRUCTURAL_FOLD_COUNTS = {1: 4, 2: 4, 3: 3}
MIN_EVALUABLE_ROWS = 30
MIN_MINORITY_ROWS = 10
DEFAULT_N_BOOTSTRAP = 500


@dataclass(frozen=True)
class QbV3FoldData:
    """One temporal fold: standardized train features, imputed test features.

    ``train_features`` are imputed+standardized with statistics fit on the
    train fold ONLY. ``test_features`` are imputed with the train medians but
    returned UNSCALED (the honest raw view); ``scale`` applies the train-fit
    standardization at predict time so no test statistic ever leaks into the
    preprocessing.
    """

    train_features: pd.DataFrame
    test_features: pd.DataFrame
    train_labels: pd.Series
    test_labels: pd.Series
    train_metadata: pd.DataFrame
    test_metadata: pd.DataFrame
    feature_means: pd.Series
    feature_stds: pd.Series

    def scale(self, features: pd.DataFrame) -> pd.DataFrame:
        return (features - self.feature_means) / self.feature_stds


def validate_qb_v3_training_labels(labels: pd.DataFrame) -> None:
    """Training labels must satisfy the T1 label-table contract (fail-closed)."""
    validate_qb_role_occupancy_label_table(labels)


def compute_train_fold_prevalence_baseline(
    *,
    y_train: pd.Series,
    y_test: pd.Series,
    strategy: str = "train_fold_prevalence",
) -> float:
    """The pre-registered baseline; a test-fold-prevalence baseline is leakage."""
    if strategy != "train_fold_prevalence":
        raise ValueError(
            "baseline must be train-fold prevalence; a test-fold-prevalence "
            f"baseline leaks test labels (got strategy={strategy!r})"
        )
    del y_test  # accepted only so misuse is visible at the call site
    return float(y_train.astype(bool).mean())


def build_qb_v3_classification_fold_data(
    *,
    candidate_matrix: pd.DataFrame,
    labels: pd.DataFrame,
    eligibility_mask: pd.DataFrame,
    feature_cols: list[str],
    test_year: int,
    horizon: int,
) -> QbV3FoldData:
    """Assemble one strictly-temporal fold from the post-abstention cohort."""
    validate_qb_v3_candidate_feature_contract(feature_cols)
    validate_qb_v3_training_labels(labels)

    eligible = eligibility_mask[eligibility_mask["eligible_for_qb_v3_candidate"]]
    eligible_keys = set(
        zip(eligible["player_id"], eligible["feature_season"].astype(int), strict=True)
    )
    horizon_labels = labels[labels["horizon"] == horizon][
        ["player_id", "feature_season", "startable_role_occupancy"]
    ]
    frame = candidate_matrix.merge(
        horizon_labels, on=["player_id", "feature_season"], how="inner"
    )
    frame = frame[
        [
            (player_id, int(season)) in eligible_keys
            for player_id, season in zip(
                frame["player_id"], frame["feature_season"], strict=True
            )
        ]
    ]

    train = frame[frame["feature_season"] < test_year]
    test = frame[frame["feature_season"] == test_year]

    train_raw = train[feature_cols].astype(float)
    test_raw = test[feature_cols].astype(float)
    # A column with ZERO train-window signal (e.g. ppg_t_minus_2 in the
    # earliest fold — the source window starts 2018, so no T-2 exists) has a
    # NaN median; impute 0.0 — the availability flags carry the missingness
    # signal, and a constant column is inert after standardization.
    medians = train_raw.median().fillna(0.0)
    train_imputed = train_raw.fillna(medians)
    test_imputed = test_raw.fillna(medians)
    means = train_imputed.mean()
    stds = train_imputed.std(ddof=0).replace(0.0, 1.0).fillna(1.0)

    return QbV3FoldData(
        train_features=(train_imputed - means) / stds,
        test_features=test_imputed,
        train_labels=train["startable_role_occupancy"].astype(bool).reset_index(drop=True),
        test_labels=test["startable_role_occupancy"].astype(bool).reset_index(drop=True),
        train_metadata=train[["player_id", "feature_season"]].reset_index(drop=True),
        test_metadata=test[["player_id", "feature_season"]].reset_index(drop=True),
        feature_means=means,
        feature_stds=stds,
    )


def compute_qb_v3_fold_metrics(
    *,
    fold_index: int,
    test_year: int,
    horizon: int,
    y_true: pd.Series,
    probabilities: pd.Series,
    baseline_probability: float,
    top_k: int = QB_V3_TOP_K,
    rng_seed: int,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
) -> dict[str, Any]:
    """Per-fold calibration/discrimination metrics with BCa CI gate inputs."""
    y = y_true.astype(bool).to_numpy()
    p = probabilities.astype(float).to_numpy()
    baseline = np.full_like(p, float(baseline_probability))

    model_sq = (p - y) ** 2
    baseline_sq = (baseline - y) ** 2
    brier = float(model_sq.mean())
    baseline_brier = float(baseline_sq.mean())

    roc_auc = 0.5 if len(set(y)) < 2 else float(roc_auc_score(y, p))

    k = min(int(top_k), len(p))
    top_idx = np.argsort(-p, kind="stable")[:k]
    top_k_precision = float(y[top_idx].mean()) if k else 0.0

    per_sample_delta = baseline_sq - model_sq
    ci = _bca_interval(per_sample_delta, rng_seed=rng_seed, n_bootstrap=n_bootstrap)
    auc_ci = _bca_auc_delta_interval(
        y=y, p=p, rng_seed=rng_seed + 1, n_bootstrap=n_bootstrap
    )

    return {
        "fold_index": int(fold_index),
        "test_year": int(test_year),
        "horizon": int(horizon),
        "model_family": QB_V3_MODEL_FAMILY,
        "n_test_rows": int(len(p)),
        "brier_score": brier,
        "baseline_brier_score": baseline_brier,
        "brier_delta": float(per_sample_delta.mean()),
        "roc_auc": roc_auc,
        "auc_delta": float(roc_auc - 0.5),
        "top_k": int(top_k),
        "top_k_precision": top_k_precision,
        "brier_delta_bca_ci": ci,
        "auc_delta_bca_ci": auc_ci,
        "decision_supported": False,
    }


def _bca_auc_delta_interval(
    *, y: np.ndarray, p: np.ndarray, rng_seed: int, n_bootstrap: int
) -> dict[str, Any]:
    """BCa interval on (AUC - 0.5) via bootstrap resampling of (y, p) pairs.

    Spec §6 gates the promotion case on BOTH the Brier and AUC CI lower
    bounds clearing zero (Codex T3 review blocker). Single-class resamples
    contribute a 0.0 delta (no discrimination evidence, never an error).
    """
    if len(set(y)) < 2:
        return {"lower": 0.0, "upper": 0.0, "method": "BCa"}
    observed = float(roc_auc_score(y, p) - 0.5)
    n = len(y)
    rng = np.random.default_rng(rng_seed)

    def _delta(indices: np.ndarray) -> float:
        y_b, p_b = y[indices], p[indices]
        if len(set(y_b)) < 2:
            return 0.0
        return float(roc_auc_score(y_b, p_b) - 0.5)

    boot = np.array(
        [_delta(rng.integers(0, n, size=n)) for _ in range(int(n_bootstrap))]
    )
    if np.allclose(boot, boot[0]):
        return {"lower": observed, "upper": observed, "method": "BCa"}

    proportion = float((boot < observed).mean())
    proportion = min(max(proportion, 1.0 / (n_bootstrap + 1)), n_bootstrap / (n_bootstrap + 1))
    z0 = float(norm.ppf(proportion))
    jackknife = np.array(
        [_delta(np.delete(np.arange(n), i)) for i in range(n)]
    )
    diffs = jackknife.mean() - jackknife
    denom = float((diffs**2).sum() ** 1.5)
    acceleration = float((diffs**3).sum() / (6.0 * denom)) if denom > 0 else 0.0

    def _adjusted_percentile(q: float) -> float:
        z = float(norm.ppf(q))
        adjusted = z0 + (z0 + z) / (1.0 - acceleration * (z0 + z))
        return float(norm.cdf(adjusted))

    return {
        "lower": float(np.quantile(boot, _adjusted_percentile(0.025))),
        "upper": float(np.quantile(boot, _adjusted_percentile(0.975))),
        "method": "BCa",
    }


def _bca_interval(
    per_sample_delta: np.ndarray, *, rng_seed: int, n_bootstrap: int, alpha: float = 0.05
) -> dict[str, Any]:
    """BCa bootstrap interval on the mean per-sample Brier delta."""
    observed = float(per_sample_delta.mean())
    n = len(per_sample_delta)
    rng = np.random.default_rng(rng_seed)
    boot = np.array(
        [
            per_sample_delta[rng.integers(0, n, size=n)].mean()
            for _ in range(int(n_bootstrap))
        ]
    )
    if np.allclose(boot, boot[0]):
        return {"lower": observed, "upper": observed, "method": "BCa"}

    proportion = float((boot < observed).mean())
    proportion = min(max(proportion, 1.0 / (n_bootstrap + 1)), n_bootstrap / (n_bootstrap + 1))
    z0 = float(norm.ppf(proportion))

    jackknife = np.array(
        [np.delete(per_sample_delta, i).mean() for i in range(n)]
    )
    diffs = jackknife.mean() - jackknife
    denom = float((diffs**2).sum() ** 1.5)
    acceleration = float((diffs**3).sum() / (6.0 * denom)) if denom > 0 else 0.0

    def _adjusted_percentile(q: float) -> float:
        z = float(norm.ppf(q))
        adjusted = z0 + (z0 + z) / (1.0 - acceleration * (z0 + z))
        return float(norm.cdf(adjusted))

    lower = float(np.quantile(boot, _adjusted_percentile(alpha / 2)))
    upper = float(np.quantile(boot, _adjusted_percentile(1 - alpha / 2)))
    return {"lower": lower, "upper": upper, "method": "BCa"}


def summarize_qb_v3_horizon_gates(
    *,
    fold_metrics: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
    horizons: tuple[int, ...],
) -> dict[int, dict[str, Any]]:
    """Per-horizon promotion-eligibility rollup — no survivorship shortcuts."""
    summary: dict[int, dict[str, Any]] = {}
    for horizon in horizons:
        structural = QB_V3_STRUCTURAL_FOLD_COUNTS[int(horizon)]
        minimum = structural - 1  # all-but-one of the STRUCTURAL folds
        metrics = [m for m in fold_metrics if int(m["horizon"]) == int(horizon)]
        evaluable = len(metrics)

        eligible = evaluable >= minimum
        reason: str | None = None
        if not eligible:
            reason = "insufficient_evaluable_structural_folds"
        else:
            # Spec §6: the promotion case requires BOTH the Brier AND the AUC
            # delta CI lower bounds strictly above zero on every evaluable
            # fold (Codex T3 blocker: Brier-only gating let a negative-AUC
            # fold promote).
            brier_lowers = [
                m.get("brier_delta_bca_ci", {}).get("lower") for m in metrics
            ]
            auc_lowers = [
                m.get("auc_delta_bca_ci", {}).get("lower") for m in metrics
            ]
            if any(lower is None for lower in [*brier_lowers, *auc_lowers]):
                eligible, reason = False, "missing_bca_ci_gate_inputs"
            elif not all(lower > 0.0 for lower in [*brier_lowers, *auc_lowers]):
                eligible, reason = False, "bca_ci_lower_not_above_zero"

        entry: dict[str, Any] = {
            "structural_fold_count": structural,
            "minimum_evaluable_folds": minimum,
            "evaluable_fold_count": evaluable,
            "metric_average_fold_count": evaluable,
            "excluded_fold_count": len(
                [e for e in exclusions if int(e["horizon"]) == int(horizon)]
            ),
            "promotion_eligible": eligible,
            "non_promotion_reason": reason,
            "decision_supported": False,
        }
        if evaluable:
            entry["avg_brier_delta"] = float(
                np.mean([m["brier_delta"] for m in metrics if "brier_delta" in m])
            )
        summary[int(horizon)] = entry
    return summary


def run_qb_v3_walk_forward_validation(
    *,
    candidate_matrix: pd.DataFrame,
    labels: pd.DataFrame,
    eligibility_mask: pd.DataFrame,
    feature_cols: list[str],
    horizons: tuple[int, ...] = (1, 2, 3),
    test_years: tuple[int, ...] = QB_V3_TEST_YEARS,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    random_state: int = 20260703,
) -> dict[str, Any]:
    """The full pre-registered validation matrix over all fold-horizons."""
    validate_qb_v3_candidate_feature_contract(feature_cols)
    validate_qb_v3_training_labels(labels)

    fold_horizon_metrics: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for horizon in horizons:
        for fold_index, test_year in enumerate(test_years, start=1):
            has_fold_labels = bool(
                (
                    (labels["horizon"] == horizon)
                    & (labels["feature_season"] == test_year)
                ).any()
            )
            if not has_fold_labels:
                # Structurally unlabelable fold (outcome window not observable)
                # — reflected in QB_V3_STRUCTURAL_FOLD_COUNTS, not an exclusion.
                continue

            fold = build_qb_v3_classification_fold_data(
                candidate_matrix=candidate_matrix,
                labels=labels,
                eligibility_mask=eligibility_mask,
                feature_cols=feature_cols,
                test_year=test_year,
                horizon=horizon,
            )
            if fold.train_labels.empty or fold.test_labels.empty:
                exclusions.append(
                    {
                        "fold_index": fold_index,
                        "test_year": int(test_year),
                        "horizon": int(horizon),
                        "reason": "empty_eligible_cohort",
                    }
                )
                continue
            minority = int(
                min(fold.test_labels.sum(), (~fold.test_labels).sum())
            )
            if len(fold.test_labels) < MIN_EVALUABLE_ROWS or minority < MIN_MINORITY_ROWS:
                exclusions.append(
                    {
                        "fold_index": fold_index,
                        "test_year": int(test_year),
                        "horizon": int(horizon),
                        "reason": "low_sample_qb_holdout",
                    }
                )
                continue

            model = LogisticRegression(
                penalty="l2", C=1.0, max_iter=5000, random_state=random_state
            )
            model.fit(fold.train_features, fold.train_labels)
            probabilities = pd.Series(
                model.predict_proba(fold.scale(fold.test_features))[:, 1]
            )
            baseline = compute_train_fold_prevalence_baseline(
                y_train=fold.train_labels, y_test=fold.test_labels
            )
            fold_horizon_metrics.append(
                compute_qb_v3_fold_metrics(
                    fold_index=fold_index,
                    test_year=test_year,
                    horizon=horizon,
                    y_true=fold.test_labels,
                    probabilities=probabilities,
                    baseline_probability=baseline,
                    top_k=QB_V3_TOP_K,
                    rng_seed=random_state + horizon * 100 + fold_index,
                    n_bootstrap=n_bootstrap,
                )
            )

    horizon_summary = summarize_qb_v3_horizon_gates(
        fold_metrics=fold_horizon_metrics,
        exclusions=exclusions,
        horizons=horizons,
    )
    return {
        "candidate_head": "qb_v3_candidate",
        "model_family": QB_V3_MODEL_FAMILY,
        "top_k": QB_V3_TOP_K,
        "test_years": [int(year) for year in test_years],
        "n_bootstrap": int(n_bootstrap),
        "random_state": int(random_state),
        "fold_horizon_metrics": fold_horizon_metrics,
        "exclusions": exclusions,
        "horizon_summary": horizon_summary,
        "decision_supported": False,
    }
