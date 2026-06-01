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
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

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
