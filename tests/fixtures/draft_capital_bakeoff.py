"""Fixture data for Phase 13.2 draft-capital bake-off tests.

Each function returns a list of DraftClassEvaluationRow objects covering one
named scenario. Codex's Task 13.2.2 tests should import these factories and
assert behavioral properties of the LOOCV harness against them.

Predicted-score conventions per candidate:
  current_engine_a_baseline : linear  max(0, 100 - pick)  — no cliff encoding
  log_decay                 : smooth  100 / ln(pick + 1)
  position_bucketed         : step    hard tier boundaries from manifest priors
  position_isotonic_step    : step    same tier structure, slightly smoothed
                                      within each tier (simulates learned PAVA output)

Realized-value convention: career PPG-equivalent over the dynasty window
  (units are arbitrary; only the within-class *rank* is what the LOOCV tests).
"""
from __future__ import annotations

import math
from typing import NamedTuple

from src.dynasty_genius.eval.draft_class_loocv import DraftClassEvaluationRow

# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------


def _baseline_score(pick: int) -> float:
    return max(0.0, 100.0 - pick)


def _log_decay_score(pick: int) -> float:
    return 100.0 / math.log(pick + 1)


def _qb_bucketed_score(pick: int) -> float:
    if pick <= 15:
        return 90.0
    if pick <= 32:
        return 52.0
    if pick <= 64:
        return 22.0
    return 6.0


def _rb_bucketed_score(pick: int) -> float:
    if pick <= 32:
        return 88.0
    if pick <= 64:
        return 54.0
    if pick <= 105:
        return 18.0
    return 5.0


def _wr_bucketed_score(pick: int) -> float:
    if pick <= 32:
        return 85.0
    if pick <= 75:    # viability extends to pick 75
        return 58.0
    if pick <= 105:
        return 22.0
    return 6.0


def _te_bucketed_score(pick: int) -> float:
    if pick <= 32:
        return 80.0
    return 20.0   # only one meaningful breakpoint for TE


def _isotonic_score(bucketed: float, pick: int) -> float:
    """Simulate PAVA output: same tier structure as bucketed with pick-level nudge."""
    return bucketed - (pick % 10) * 0.1   # tiny monotone within-tier decay


# ---------------------------------------------------------------------------
# Scenario 1: QB top-15 cliff
#
# Three draft classes. Within each class the realized value exhibits a hard
# cliff at pick 15/16. Both bucketed and isotonic candidates should rank
# first-tier QBs above second-tier QBs; log_decay smooths over the cliff.
# ---------------------------------------------------------------------------

_QB_CLIFF_PICKS = [1, 6, 12, 15, 16, 28, 42, 64, 120]

_QB_CLIFF_REALIZED = {
    1: 22.4,
    6: 19.1,
    12: 17.5,
    15: 16.0,   # last pick in top-15 tier — still high
    16: 7.8,    # first pick outside top-15 — cliff lands here
    28: 9.2,
    42: 4.1,
    64: 2.8,
    120: 0.6,
}

_QB_CLIFF_YEARS = (2019, 2020, 2021)


def qb_top15_cliff_rows(candidate: str = "position_bucketed") -> list[DraftClassEvaluationRow]:
    """QB cohort demonstrating a sharp cliff between picks 15 and 16."""
    score_fn = {
        "current_engine_a_baseline": _baseline_score,
        "log_decay": _log_decay_score,
        "position_bucketed": _qb_bucketed_score,
        "position_isotonic_step": lambda p: _isotonic_score(_qb_bucketed_score(p), p),
    }[candidate]

    rows = []
    for year in _QB_CLIFF_YEARS:
        for pick in _QB_CLIFF_PICKS:
            rows.append(
                DraftClassEvaluationRow(
                    candidate_name=candidate,
                    player_id=f"qb_pick{pick}_{year}",
                    position="QB",
                    draft_year=year,
                    predicted_score=score_fn(pick),
                    realized_value=_QB_CLIFF_REALIZED[pick] + (year - 2019) * 0.3,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Scenario 2: WR pick-75 viability
#
# Realized values stay meaningful through pick 75 then drop sharply at 76+.
# The position_bucketed WR bins use [1-32], [33-75], [76-105], [106+].
# Tests should verify that pick-74 and pick-76 end up in different score tiers
# under bucketed/isotonic but NOT under log_decay.
# ---------------------------------------------------------------------------

_WR_VIABILITY_PICKS = [8, 24, 45, 72, 74, 76, 80, 95, 110, 150]

_WR_VIABILITY_REALIZED = {
    8: 18.5,
    24: 15.2,
    45: 12.8,
    72: 10.1,
    74: 9.8,    # last viable pick — realized still solid
    76: 5.2,    # cliff: first pick after the WR tier boundary
    80: 4.9,
    95: 3.1,
    110: 1.8,
    150: 0.4,
}

_WR_VIABILITY_YEARS = (2020, 2021, 2022)


def wr_pick75_viability_rows(candidate: str = "position_bucketed") -> list[DraftClassEvaluationRow]:
    """WR cohort demonstrating viability through pick 75 then a cliff at 76."""
    score_fn = {
        "current_engine_a_baseline": _baseline_score,
        "log_decay": _log_decay_score,
        "position_bucketed": _wr_bucketed_score,
        "position_isotonic_step": lambda p: _isotonic_score(_wr_bucketed_score(p), p),
    }[candidate]

    rows = []
    for year in _WR_VIABILITY_YEARS:
        for pick in _WR_VIABILITY_PICKS:
            rows.append(
                DraftClassEvaluationRow(
                    candidate_name=candidate,
                    player_id=f"wr_pick{pick}_{year}",
                    position="WR",
                    draft_year=year,
                    predicted_score=score_fn(pick),
                    realized_value=_WR_VIABILITY_REALIZED[pick] + (year - 2020) * 0.2,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Scenario 3: RB Day-2 / Day-3 drop
#
# Sharp RB cliff after pick 64. Day-3 (picks 65+) realized values collapse to
# <5 PPG while Day-2 (33-64) hovers at 8-14 PPG. Log_decay underestimates the
# severity of this cliff because it cannot represent a step.
# ---------------------------------------------------------------------------

_RB_DROP_PICKS = [5, 18, 30, 38, 52, 65, 72, 90, 110, 160]

_RB_DROP_REALIZED = {
    5: 21.0,
    18: 17.5,
    30: 14.1,
    38: 11.8,
    52: 9.4,
    65: 4.2,    # Day-3 starts — cliff
    72: 3.8,
    90: 2.6,
    110: 1.4,
    160: 0.3,
}

_RB_DROP_YEARS = (2019, 2020, 2021, 2022)


def rb_day2_day3_drop_rows(candidate: str = "position_bucketed") -> list[DraftClassEvaluationRow]:
    """RB cohort demonstrating the sharp Day-2 / Day-3 drop after pick 64."""
    score_fn = {
        "current_engine_a_baseline": _baseline_score,
        "log_decay": _log_decay_score,
        "position_bucketed": _rb_bucketed_score,
        "position_isotonic_step": lambda p: _isotonic_score(_rb_bucketed_score(p), p),
    }[candidate]

    rows = []
    for year in _RB_DROP_YEARS:
        for pick in _RB_DROP_PICKS:
            rows.append(
                DraftClassEvaluationRow(
                    candidate_name=candidate,
                    player_id=f"rb_pick{pick}_{year}",
                    position="RB",
                    draft_year=year,
                    predicted_score=score_fn(pick),
                    realized_value=_RB_DROP_REALIZED[pick] + (year - 2019) * 0.1,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Scenario 4: TE small-cohort (metrics guarded)
#
# Only 2 draft classes with 3 TEs each → n < 5 per fold → compute_subgroup_metrics
# returns None for all metrics. The LOOCV harness must propagate Nones cleanly.
# ---------------------------------------------------------------------------

_TE_SMALL_PICKS = [12, 45, 78]  # 3 TEs per class — intentionally below n=5 guard


def te_small_cohort_rows(candidate: str = "position_bucketed") -> list[DraftClassEvaluationRow]:
    """TE cohort with 3 players per class — triggers null metric guard (n < 5)."""
    score_fn = {
        "current_engine_a_baseline": _baseline_score,
        "log_decay": _log_decay_score,
        "position_bucketed": _te_bucketed_score,
        "position_isotonic_step": lambda p: _isotonic_score(_te_bucketed_score(p), p),
    }[candidate]

    rows = []
    for year in (2021, 2022):
        for pick in _TE_SMALL_PICKS:
            rows.append(
                DraftClassEvaluationRow(
                    candidate_name=candidate,
                    player_id=f"te_pick{pick}_{year}",
                    position="TE",
                    draft_year=year,
                    predicted_score=score_fn(pick),
                    realized_value=16.0 - pick * 0.1,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Scenario 5: All four candidates — same QB cohort, different predicted scores
#
# Shows how bucketed/isotonic produce a hard score gap between picks 15 and 16
# while log_decay smooths over it. Used to test comparative ranking behavior.
# ---------------------------------------------------------------------------

def all_candidates_qb_rows() -> list[DraftClassEvaluationRow]:
    """All four candidates over the same QB cohort for direct comparison."""
    candidates = [
        "current_engine_a_baseline",
        "log_decay",
        "position_bucketed",
        "position_isotonic_step",
    ]
    rows = []
    for candidate in candidates:
        rows.extend(qb_top15_cliff_rows(candidate=candidate))
    return rows


class CandidateScoreAtPick(NamedTuple):
    """Helper for comparing candidate scores at a specific pick in tests."""
    current_engine_a: float
    log_decay: float
    position_bucketed: float
    position_isotonic_step: float


def candidate_scores_at_pick(pick: int) -> CandidateScoreAtPick:
    """Return the predicted score each QB-candidate assigns to a given pick."""
    return CandidateScoreAtPick(
        current_engine_a=_baseline_score(pick),
        log_decay=_log_decay_score(pick),
        position_bucketed=_qb_bucketed_score(pick),
        position_isotonic_step=_isotonic_score(_qb_bucketed_score(pick), pick),
    )


# ---------------------------------------------------------------------------
# Scenario 6: Market-derived source field — must be rejected
#
# A single row with source_fields containing a prohibited market key.
# build_loocv_folds and _assert_no_market_fields should raise DraftClassLOOCVError.
# ---------------------------------------------------------------------------

_MARKET_CONTAMINATED_SOURCE_FIELDS = (
    ("ktc_value",),
    ("adp",),
    ("fantasycalc_value",),
    ("market_score",),
    ("adp_2024",),
)


def market_contaminated_row(source_fields: tuple[str, ...] = ("ktc_value",)) -> DraftClassEvaluationRow:
    """A single evaluation row carrying a prohibited market-derived source field."""
    return DraftClassEvaluationRow(
        candidate_name="position_bucketed",
        player_id="wr_pick22_2021",
        position="WR",
        draft_year=2021,
        predicted_score=85.0,
        realized_value=14.0,
        source_fields=source_fields,
    )


def market_contaminated_cohort(source_fields: tuple[str, ...] = ("ktc_value",)) -> list[DraftClassEvaluationRow]:
    """A multi-class WR cohort where exactly one row carries a prohibited field."""
    clean = wr_pick75_viability_rows(candidate="position_bucketed")
    dirty = market_contaminated_row(source_fields=source_fields)
    return clean + [dirty]


# ---------------------------------------------------------------------------
# Scenario 7: Insufficient draft classes (single year)
#
# Only one draft year → build_loocv_folds raises DraftClassLOOCVError.
# Tests should confirm the error message references "at least two draft classes".
# ---------------------------------------------------------------------------

def single_class_rows(candidate: str = "position_bucketed") -> list[DraftClassEvaluationRow]:
    """WR rows from a single draft year — insufficient for LOOCV (need ≥ 2 years)."""
    return [
        DraftClassEvaluationRow(
            candidate_name=candidate,
            player_id=f"wr_pick{pick}_2022",
            position="WR",
            draft_year=2022,
            predicted_score=_wr_bucketed_score(pick),
            realized_value=_WR_VIABILITY_REALIZED.get(pick, 5.0),
        )
        for pick in [12, 35, 80]
    ]
