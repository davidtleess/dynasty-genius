"""Subpopulation / Axis-of-Edge Study — pre-registered constants + pure stats.

DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.

Characterizes Engine B vs DynastyProcess expert-consensus (`dynastyprocess_ecr_2qb`)
ranking quality against realized PPG across three pre-registered subpopulations
(aging-cliff transition, high model-vs-consensus disagreement, early-career),
for the whole player universe. Model-blind: all market/identity data is read-only
and joined *after* scoring; nothing here feeds Engine A/B training or any decision
surface (`decision_supported` is never True).

Spec: docs/superpowers/specs/2026-05-31-subpopulation-axis-of-edge-study-design.md
(dual-CLEARED, commit 11e3c2d). Plan: docs/superpowers/plans/
2026-05-31-subpopulation-axis-of-edge-study.md (commit cd8f2b8).

The constants below are PRE-REGISTERED: locked before analysis to protect
statistical integrity. They must remain module-level constants, never inline
literals, so a reviewer can confirm no threshold was tuned to a result.

Task 1: module scaffold + pre-registered constants.
Task 2: resolve_draft_year — early-career draft-year dedup, fail-closed.
Task 3: tag_cohorts — three pre-registered axes (aging / disagreement / early-career).
Task 4: compute_slice — orientation-locked Spearman rho_diff + NDCG cross-check.
"""
from __future__ import annotations

import math
import warnings
from collections.abc import Iterable, Mapping

import numpy as np
from scipy import stats as scipy_stats

from src.dynasty_genius.eval.backtest_metrics import compute_ndcg

# Category neutral band on rho_diff: |rho_diff| < NEUTRAL_BAND is reported as
# `statistically_indistinguishable`, independent of the bootstrap CI (spec §4).
NEUTRAL_BAND = 0.05

# Axis 2: |model_rank - consensus_rank| >= this many ranking slots qualifies a
# player as a high model-vs-consensus disagreement case (spec §3, Axis 2).
DISAGREEMENT_MIN_SLOTS = 12

# Axis 3: experience = feature_season - draft_year; early-career = {0, 1, 2}
# seasons (spec §3, Axis 3).
EARLY_CAREER_MAX_EXP = 2

# Minimum slice size to compute Spearman rho; below this the slice reports
# `insufficient_n` (split min-n; NDCG cross-check gated separately at primary_k).
SPEARMAN_MIN_N = 30

# Early-career axis is only emitted when draft_year coverage meets this fraction;
# otherwise the axis surfaces `early_career_axis_unavailable` (fail-closed, no age
# substitution — spec §7).
COVERAGE_GATE = 0.95

# Benjamini-Hochberg target FDR over the aggregate per-(axis, slice, position)
# tests; powered_followup_candidate = (q_value <= FDR_Q) (spec §4/§9.3).
FDR_Q = 0.10

# Aging-cliff transition thresholds on age_at_feature_season — one season ahead of
# the constitution cliffs (RB26/WR28/TE30/QB33) to capture the transition window
# (spec §3, Axis 1).
AGING_THRESHOLDS = {
    "RB": 25,
    "WR": 27,
    "TE": 29,
    "QB": 32,
}


class InvalidDraftYearError(ValueError):
    """Raised when a non-null draft_year cannot be read as an integer year.

    A malformed draft_year is a data-integrity violation, not a missing value:
    "silent substitution forbidden" — we never coerce a bad value to missing
    (spec §7). Distinct from the plain ``ValueError`` raised on a genuine
    conflict between two valid-but-different draft years for one player.
    """


def _coerce_draft_year(raw: object) -> int | None:
    """Return draft_year as int, ``None`` when absent/null, else raise.

    Accepts ``int``, integral ``float``, and base-10 integer strings. Rejects
    ``bool``, non-integral ``float``, and non-integer strings with
    ``InvalidDraftYearError`` (no coercion to missing).
    """
    if raw is None:
        return None
    if isinstance(raw, bool):  # bool is an int subclass; not a valid year
        raise InvalidDraftYearError(f"draft_year is boolean, not a year: {raw!r}")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if raw.is_integer():
            return int(raw)
        raise InvalidDraftYearError(f"draft_year is a non-integer float: {raw!r}")
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError as exc:
            raise InvalidDraftYearError(
                f"draft_year is not an integer string: {raw!r}"
            ) from exc
    raise InvalidDraftYearError(
        f"draft_year has unsupported type {type(raw).__name__}: {raw!r}"
    )


def resolve_draft_year(
    rows: Iterable[Mapping[str, object]],
) -> tuple[dict[str, int], int | None]:
    """Resolve ``{gsis_id -> draft_year}`` plus the db_season snapshot.

    Deterministic and fail-closed (spec §6/§7):

    - exactly one distinct non-null draft_year per ``gsis_id`` -> mapped (int);
    - two or more distinct non-null draft_year values for one ``gsis_id`` ->
      ``ValueError`` (a genuine conflict; "latest db_season wins" never silently
      overrides a conflict);
    - null/absent draft_year -> excluded from the map (the caller counts the
      ``gsis_id`` toward the coverage denominator), no raise;
    - non-null non-integer draft_year -> ``InvalidDraftYearError`` (no coercion).

    ``db_season_snapshot`` is the latest (max) ``db_season`` across all rows.
    """
    values_by_id: dict[str, set[int]] = {}
    db_seasons: list[int] = []
    for row in rows:
        db_season = row.get("db_season")
        if db_season is not None:
            db_seasons.append(int(db_season))
        year = _coerce_draft_year(row.get("draft_year"))
        gsis_id = row.get("gsis_id")
        if gsis_id is None:
            continue
        bucket = values_by_id.setdefault(str(gsis_id), set())
        if year is not None:
            bucket.add(year)

    draft_year_map: dict[str, int] = {}
    for gsis_id, years in values_by_id.items():
        if not years:
            # null/absent only -> excluded; caller counts it toward coverage.
            continue
        if len(years) > 1:
            raise ValueError(
                f"conflicting non-null draft_year values for {gsis_id!r}: "
                f"{sorted(years)}"
            )
        draft_year_map[gsis_id] = next(iter(years))

    db_season_snapshot = max(db_seasons) if db_seasons else None
    return draft_year_map, db_season_snapshot


def tag_cohorts(
    rows: Iterable[Mapping[str, object]],
    draft_year_map: Mapping[str, int],
) -> list[dict]:
    """Attach the three pre-registered cohort axes to each row (spec §3).

    Returns NEW row dicts (shallow copies); ranks are never mutated. Each
    returned row gains:

    - ``aging_cliff_transition`` (bool): ``age_at_feature_season >=
      AGING_THRESHOLDS[position]``;
    - ``high_disagreement`` (bool) + ``disagreement_bucket``
      (``model_bullish`` / ``model_bearish`` / ``None``): triggered when
      ``abs(model_rank - consensus_rank) >= DISAGREEMENT_MIN_SLOTS``; on the
      lower-is-better rank convention ``model_rank < consensus_rank`` means the
      model ranks the player better (bullish);
    - ``early_career_eligible`` (bool), ``early_career_experience_year``
      (int | None), ``cohort_exclusion_reasons`` (list[str]): experience =
      ``feature_season - draft_year`` (draft_year from ``draft_year_map`` keyed
      by ``player_id``); eligible when ``0 <= experience <= EARLY_CAREER_MAX_EXP``;
      ``experience < 0`` -> ineligible + ``invalid_negative_experience``; missing
      draft_year -> ineligible, experience ``None``, no exclusion reason (a
      coverage gap, not a data-integrity violation).

    Fail-soft for out-of-universe inputs: an unknown position, or a missing
    age / model_rank / consensus_rank, simply yields an un-flagged axis (False /
    None) rather than raising — the join layer (Task 8) owns input completeness.
    """
    tagged: list[dict] = []
    for row in rows:
        out = dict(row)
        reasons: list[str] = []

        # Axis 1 — aging-cliff transition (per-position threshold).
        position = out.get("position")
        age = out.get("age_at_feature_season")
        threshold = AGING_THRESHOLDS.get(position) if isinstance(position, str) else None
        out["aging_cliff_transition"] = (
            threshold is not None and age is not None and age >= threshold
        )

        # Axis 2 — high model-vs-consensus disagreement (lower-is-better ranks).
        model_rank = out.get("model_rank")
        consensus_rank = out.get("consensus_rank")
        if model_rank is None or consensus_rank is None:
            out["high_disagreement"] = False
            out["disagreement_bucket"] = None
        elif abs(model_rank - consensus_rank) >= DISAGREEMENT_MIN_SLOTS:
            out["high_disagreement"] = True
            out["disagreement_bucket"] = (
                "model_bullish" if model_rank < consensus_rank else "model_bearish"
            )
        else:
            out["high_disagreement"] = False
            out["disagreement_bucket"] = None

        # Axis 3 — early-career window via derived experience.
        player_id = out.get("player_id")
        draft_year = (
            draft_year_map.get(player_id) if isinstance(player_id, str) else None
        )
        feature_season = out.get("feature_season")
        if draft_year is None:
            # True coverage gap: un-bridged row. Counted toward the coverage
            # denominator by the caller; not a data-integrity violation, no reason.
            experience: int | None = None
            eligible = False
        elif feature_season is None:
            # Malformed: a draft year is present but feature_season is missing,
            # so experience is null. Distinct from the coverage gap — flagged
            # rather than silently treated as un-bridged ("silent substitution
            # forbidden"). Reuses the pre-registered invalid_negative_experience
            # token (no new label; §4.5/§9.2 pre-registration integrity).
            experience = None
            eligible = False
            reasons.append("invalid_negative_experience")
        else:
            experience = feature_season - draft_year
            if experience < 0:
                eligible = False
                reasons.append("invalid_negative_experience")
            elif experience <= EARLY_CAREER_MAX_EXP:
                eligible = True
            else:
                eligible = False
        out["early_career_experience_year"] = experience
        out["early_career_eligible"] = eligible
        out["cohort_exclusion_reasons"] = reasons

        tagged.append(out)
    return tagged


def _categorize_rho_diff(rho_diff: float) -> str:
    """Category by sign + NEUTRAL_BAND, independent of the bootstrap CI (spec §4).

    rho_diff >= +NEUTRAL_BAND -> model leads (point estimate); <= -NEUTRAL_BAND ->
    consensus leads; otherwise statistically_indistinguishable. Band edges
    (exactly +/-NEUTRAL_BAND) resolve to the leading category (>= / <=).
    """
    if rho_diff >= NEUTRAL_BAND:
        return "model_leads_point_estimate"
    if rho_diff <= -NEUTRAL_BAND:
        return "consensus_leads_point_estimate"
    return "statistically_indistinguishable"


def _bootstrap_rho_diff(
    model_ranks: list,
    consensus_ranks: list,
    realized_ranks: list,
    *,
    n_bootstrap: int,
    rng_seed: int,
) -> dict:
    """Paired BCa bootstrap of the Spearman rho difference (model - consensus).

    Lower-is-better on both sides: a perfectly aligned ranker yields rho = +1, so
    rho_diff = rho_model - rho_consensus > 0 means the model aligns better.
    Returns rho_model / rho_consensus / rho_diff point estimates, the paired BCa
    95% CI on rho_diff (bca_ci95), ci_includes_zero, and a two-sided percentile
    bootstrap p-value (boot_p_value) for H0: rho_diff == 0. Deterministic for a
    fixed rng_seed. Mirrors the compute_ndcg_diff_bootstrap degenerate-collapse
    pattern: a zero-variance statistic (e.g. perfect separation) collapses the CI
    to the point estimate rather than raising.
    """
    model = np.asarray(model_ranks, dtype=float)
    consensus = np.asarray(consensus_ranks, dtype=float)
    realized = np.asarray(realized_ranks, dtype=float)

    rho_model = float(scipy_stats.spearmanr(model, realized).statistic)
    rho_consensus = float(scipy_stats.spearmanr(consensus, realized).statistic)
    rho_diff = rho_model - rho_consensus

    def _diff(m, c, r):
        return (
            scipy_stats.spearmanr(m, r).statistic
            - scipy_stats.spearmanr(c, r).statistic
        )

    lo = hi = rho_diff
    boot_p_value = 0.0 if rho_diff != 0.0 else 1.0
    try:
        with warnings.catch_warnings():
            # Perfect-separation / zero-variance is an EXPECTED degenerate case we
            # handle by collapsing the CI — don't surface scipy's warning.
            warnings.simplefilter("ignore")
            result = scipy_stats.bootstrap(
                (model, consensus, realized),
                _diff,
                n_resamples=n_bootstrap,
                random_state=rng_seed,
                method="BCa",
                paired=True,
                confidence_level=0.95,
            )
        ci_lo = float(result.confidence_interval.low)
        ci_hi = float(result.confidence_interval.high)
        if math.isfinite(ci_lo) and math.isfinite(ci_hi):
            lo = max(-2.0, ci_lo)
            hi = min(2.0, ci_hi)
        dist = np.asarray(result.bootstrap_distribution, dtype=float)
        dist = dist[np.isfinite(dist)]
        if dist.size:
            frac_le = float(np.mean(dist <= 0.0))
            frac_ge = float(np.mean(dist >= 0.0))
            boot_p_value = min(1.0, 2.0 * min(frac_le, frac_ge))
    except Exception:
        # Degenerate distribution — CI collapses to the point estimate.
        lo = hi = rho_diff
        boot_p_value = 0.0 if rho_diff != 0.0 else 1.0

    return {
        "rho_model": rho_model,
        "rho_consensus": rho_consensus,
        "rho_diff": rho_diff,
        "bca_ci95": (lo, hi),
        "ci_includes_zero": lo <= 0.0 <= hi,
        "boot_p_value": boot_p_value,
    }


def _ndcg_xcheck(
    model_ranks: list,
    consensus_ranks: list,
    realized_ranks: list,
    primary_k: int,
    n: int,
) -> dict:
    """NDCG@primary_k cross-check, gated INDEPENDENTLY at n >= primary_k (spec §4).

    Relevance is derived from the realized rank (gain = 1/realized_rank; best
    realized rank gets the highest gain) because compute_slice's contract takes
    realized ranks, not realized PPG. See compute_slice for the (flagged)
    semantic note. Returns status 'available' with both NDCG values, or
    'insufficient_n' with both None when n < primary_k.
    """
    if n < primary_k:
        return {"status": "insufficient_n", "model_ndcg": None, "consensus_ndcg": None}
    relevance = [1.0 / float(r) for r in realized_ranks]
    return {
        "status": "available",
        "model_ndcg": compute_ndcg(list(model_ranks), relevance, primary_k),
        "consensus_ndcg": compute_ndcg(list(consensus_ranks), relevance, primary_k),
    }


def compute_slice(
    model_ranks: list,
    consensus_ranks: list,
    realized_ranks: list,
    *,
    primary_k: int,
    n_bootstrap: int = 1000,
    rng_seed: int = 42,
) -> dict:
    """One slice-fold: orientation-locked Spearman rho_diff + NDCG cross-check.

    Lower-is-better rank convention on both predicted and realized ranks. The two
    gates are INDEPENDENT and never suppress each other:
    - Spearman rho_diff is computed only at n >= SPEARMAN_MIN_N; below that the
      category is 'insufficient_n' and all rho / CI / p-value fields are None.
    - The NDCG cross-check is computed only at n >= primary_k.
    Category is assigned by sign + NEUTRAL_BAND, INDEPENDENT of the CI;
    ci_includes_zero and boot_p_value are reported as separate descriptive fields.

    Note: the NDCG cross-check uses rank-derived relevance (gain = 1/realized_rank)
    because this contract receives realized ranks. A PPG-graded NDCG would need a
    realized_relevance input — a deliberate later-task contract change, not done
    here.
    """
    n = len(realized_ranks)
    ndcg_xcheck = _ndcg_xcheck(
        model_ranks, consensus_ranks, realized_ranks, primary_k, n
    )

    if n < SPEARMAN_MIN_N:
        return {
            "n": n,
            "rho_model": None,
            "rho_consensus": None,
            "rho_diff": None,
            "bca_ci95": None,
            "ci_includes_zero": None,
            "boot_p_value": None,
            "category": "insufficient_n",
            "ndcg_xcheck": ndcg_xcheck,
        }

    boot = _bootstrap_rho_diff(
        model_ranks,
        consensus_ranks,
        realized_ranks,
        n_bootstrap=n_bootstrap,
        rng_seed=rng_seed,
    )
    return {
        "n": n,
        "rho_model": boot["rho_model"],
        "rho_consensus": boot["rho_consensus"],
        "rho_diff": boot["rho_diff"],
        "bca_ci95": boot["bca_ci95"],
        "ci_includes_zero": boot["ci_includes_zero"],
        "boot_p_value": boot["boot_p_value"],
        "category": _categorize_rho_diff(boot["rho_diff"]),
        "ndcg_xcheck": ndcg_xcheck,
    }
