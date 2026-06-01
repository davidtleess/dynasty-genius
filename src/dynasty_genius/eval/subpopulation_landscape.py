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
Task 5: aggregate_folds — median rho_diff + folds_covered, no pseudo-replication.
Task 6: apply_fdr — aggregate-only Benjamini-Hochberg family + candidate flag.
Task 7: build_slice_ledger — balanced bins + coverage gate + provenance + posture.
Aggregate-p: aggregate_signflip_p — exact fold-level sign-flip permutation p (§4).
"""
from __future__ import annotations

import copy
import itertools
import math
import statistics
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


def aggregate_folds(slice_folds: Iterable[Mapping[str, object]]) -> dict:
    """Aggregate per-fold compute_slice results over EVALUABLE folds (spec §4).

    No pseudo-replication: the primary aggregate is the MEDIAN ``rho_diff`` across
    folds whose ``rho_diff`` is numeric (not None); ``insufficient_n`` folds are
    excluded from both the median and ``folds_covered``. Every fold row is
    preserved in ``fold_rows`` for auditability and downstream distribution
    mapping — raw rankings are NEVER pooled across folds for the primary
    aggregate (no ``pooled_rho_diff``). Fail-closed: empty input or zero evaluable
    folds -> ``median_rho_diff`` None, ``folds_covered`` 0 (no fabricated 0.0).
    """
    fold_rows = list(slice_folds)
    evaluable = [
        row["rho_diff"] for row in fold_rows if row.get("rho_diff") is not None
    ]
    median_rho_diff = float(np.median(evaluable)) if evaluable else None
    return {
        "median_rho_diff": median_rho_diff,
        "folds_covered": len(evaluable),
        "fold_rows": fold_rows,
    }


def apply_fdr(aggregate_tests: Iterable[Mapping[str, object]]) -> list[dict]:
    """Benjamini-Hochberg FDR over the AGGREGATE per-(axis, slice, position) tests.

    One GLOBAL BH family across all aggregate slice tests with a non-None
    ``boot_p_value`` (spec §4/§6/§9.3). Returns NEW records (deep-copied so the
    inputs and their ``fold_rows`` are never mutated); fold-level rows are left
    untouched and carry no ``q_value`` / ``powered_followup_candidate``. Each
    returned aggregate gains:

    - ``q_value``: BH-adjusted q (step-up monotone, clamped to <= 1.0); ``None``
      for a record whose ``boot_p_value`` is None (excluded from the family);
    - ``powered_followup_candidate``: ``q_value is not None and q_value <= FDR_Q``;
    - ``powered_followup_label``: always ``"hypothesis_generating"`` — a candidate
      is a descriptive flag for a powered confirmatory follow-up, NEVER a
      decision-grade or buy/sell signal.

    Fail-closed: empty input -> ``[]``; all-None p-values -> every q ``None`` and
    no candidates (no crash, no fabricated q).
    """
    records = [copy.deepcopy(dict(rec)) for rec in aggregate_tests]

    valid = [
        (i, rec["boot_p_value"])
        for i, rec in enumerate(records)
        if rec.get("boot_p_value") is not None
    ]
    m = len(valid)
    q_by_index: dict[int, float] = {}
    if m > 0:
        order = sorted(valid, key=lambda t: t[1])  # ascending p, stable
        raw = [(idx, p * m / rank) for rank, (idx, p) in enumerate(order, start=1)]
        q_sorted = [0.0] * m
        running = float("inf")
        for k in range(m - 1, -1, -1):  # BH step-up from largest rank down
            running = min(running, raw[k][1])
            q_sorted[k] = min(running, 1.0)
        for k, (idx, _p) in enumerate(order):
            q_by_index[idx] = q_sorted[k]

    for i, rec in enumerate(records):
        q = q_by_index.get(i)
        rec["q_value"] = q
        rec["powered_followup_candidate"] = q is not None and q <= FDR_Q
        rec["powered_followup_label"] = "hypothesis_generating"
    return records


# Structural constants for the slice ledger (NOT pre-registered thresholds).
_LEDGER_AXES = ("aging_cliff_transition", "high_disagreement", "early_career")
_CATEGORY_BINS = (
    "model_leads_point_estimate",
    "consensus_leads_point_estimate",
    "statistically_indistinguishable",
    "insufficient_n",
)
# The ONE sanctioned use of the word "edge": the descriptive/diagnostic report
# header. The §8 banned-language guard applies to category/slice/recommendation
# labels, never to this header.
_REPORT_HEADER = "DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim."


def _early_career_axis_available(
    early_career_coverage: Mapping[str, object] | None,
    invalid_draft_year_error: object,
) -> bool:
    """Fail-closed early-career coverage gate (spec §7).

    Unavailable when: an InvalidDraftYearError was raised, coverage is missing,
    overall draft_year coverage < COVERAGE_GATE, or ANY per-position-fold coverage
    < COVERAGE_GATE. No age substitution is ever used as a fallback.
    """
    if invalid_draft_year_error is not None:
        return False
    if not early_career_coverage:
        return False
    overall = early_career_coverage.get("overall") or {}
    denom = overall.get("denominator") or 0
    covered = overall.get("covered") or 0
    if denom <= 0 or (covered / denom) < COVERAGE_GATE:
        return False
    for pf in early_career_coverage.get("per_position_fold", []) or []:
        d = pf.get("denominator") or 0
        c = pf.get("covered") or 0
        if d <= 0 or (c / d) < COVERAGE_GATE:
            return False
    return True


def _balanced_axis_rows(aggregates_for_axis: list) -> list[dict]:
    """One row per category bin (all four always present — balanced reporting).

    Empty bins are emitted with n=0, folds_covered=0 so the table can never
    cherry-pick the model-favorable direction. n / folds_covered are summed over
    the aggregates that fell into each category for this axis.
    """
    rows = []
    for category in _CATEGORY_BINS:
        members = [a for a in aggregates_for_axis if a.get("category") == category]
        rows.append(
            {
                "category": category,
                "n": sum(int(a.get("n") or 0) for a in members),
                "folds_covered": sum(int(a.get("folds_covered") or 0) for a in members),
            }
        )
    return rows


def build_slice_ledger(
    aggregate_tests: Iterable[Mapping[str, object]],
    *,
    draft_year_provenance: Mapping[str, object],
    early_career_coverage: Mapping[str, object] | None,
    invalid_draft_year_error: object = None,
) -> dict:
    """Assemble the descriptive slice ledger (spec §4/§7/§8).

    Returns exactly ``{"header", "axis_tables", "provenance"}``:

    - ``header``: the verbatim DESCRIPTIVE/DIAGNOSTIC posture header (the one
      sanctioned use of "edge");
    - ``axis_tables``: one table per pre-registered axis. Available axes carry
      ONLY the controlled balanced category bins (all four, empty bins
      zero-filled); raw per-(slice, position) aggregate dicts are deliberately
      NOT echoed, so a dirty upstream aggregate cannot leak posture fields into
      the ledger (the per-slice median/q/candidate detail is the apply_fdr output,
      carried and posture-checked by the Task 8 CLI artifact). The early-career
      axis fails closed to ``{status: early_career_axis_unavailable,
      coverage_counts, rows: []}`` when the §7 coverage gate is not met (no age
      substitution);
    - ``provenance``: the draft-year provenance block + ``early_career_coverage``
      (+ ``invalid_draft_year_error`` string when one was raised upstream).

    Posture: ``decision_supported`` is never True anywhere, no banned David-facing
    language appears, and "edge" appears only in the header.
    """
    by_axis: dict[str, list] = {axis: [] for axis in _LEDGER_AXES}
    for agg in aggregate_tests:
        axis = agg.get("axis")
        if axis in by_axis:
            by_axis[axis].append(agg)

    axis_tables: dict[str, dict] = {}
    for axis in _LEDGER_AXES:
        if axis == "early_career" and not _early_career_axis_available(
            early_career_coverage, invalid_draft_year_error
        ):
            axis_tables[axis] = {
                "status": "early_career_axis_unavailable",
                "coverage_counts": early_career_coverage,
                "rows": [],
            }
            continue
        # Emit ONLY the controlled balanced bins — never echo raw input aggregate
        # dicts, which could carry dirty posture fields (decision_supported=True,
        # recommendation/banned labels) and defeat the §8 guard. Per-(slice,
        # position) median/q/candidate detail is the apply_fdr output, carried and
        # posture-checked by the Task 8 CLI artifact, not echoed here.
        axis_tables[axis] = {
            "status": "available",
            "rows": _balanced_axis_rows(by_axis[axis]),
        }

    provenance = {**dict(draft_year_provenance), "early_career_coverage": early_career_coverage}
    if invalid_draft_year_error is not None:
        provenance["invalid_draft_year_error"] = str(invalid_draft_year_error)

    return {
        "header": _REPORT_HEADER,
        "axis_tables": axis_tables,
        "provenance": provenance,
    }


def aggregate_signflip_p(fold_rho_diffs: Iterable[float]) -> float | None:
    """Exact fold-level sign-flip permutation p-value for an aggregate (spec §4).

    Tests whether the per-fold ``rho_diff`` effects are consistently signed, with
    the FOLD as the unit of inference (no row-level pooling / pseudo-replication).
    Deterministic and exact — enumerates all ``2^K`` sign flips, no RNG.

    K = number of evaluable folds (zeros are INCLUDED: a zero's flipped sign is
    still zero, but it stays in the observed median and in the enumeration).
    statistic = ``abs(median(fold_rho_diffs))``; two-sided p = fraction of the
    ``2^K`` sign-flip medians whose ``abs`` is ``>= observed``. ``K == 0 -> None``;
    all-zero effects -> ``1.0`` (every flip's median is 0 >= 0).

    With this study's <= 4 annual folds the minimum two-sided p is 0.25, so a
    downstream ``powered_followup_candidate`` (q <= FDR_Q) is structurally
    unreachable — disclosed as a fold-count power limit, not "no signal".
    """
    diffs = [float(d) for d in fold_rho_diffs]
    k = len(diffs)
    if k == 0:
        return None
    observed = abs(statistics.median(diffs))
    hits = 0
    total = 0
    for signs in itertools.product((1.0, -1.0), repeat=k):
        total += 1
        flipped = [s * d for s, d in zip(signs, diffs)]
        if abs(statistics.median(flipped)) >= observed - 1e-12:
            hits += 1
    return hits / total
