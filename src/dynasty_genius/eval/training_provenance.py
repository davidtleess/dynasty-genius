"""Single source of truth for what the deployed model was fitted on.

DG-015. Two statements about the same artifact disagreed, and nothing could notice:

  * ``scripts/train_engine_b.py`` withheld ``HOLDOUT_SEASONS = [2022, 2023]`` from the
    fit — a literal defined in that file and nowhere else.
  * ``scripts/generate_model_cards.py`` published ``training_window`` rendered from the
    union of the walk-forward folds' ``train_years``. That is a true statement about the
    EVALUATION, published under a name every reader takes to mean the deployed fit.

The result shipped in all four model cards as ``"2018–2022 (expanding; 4 folds)"`` while
the deployed fit had actually seen 2018-2021 and 2025 — claiming a season that was held
out, omitting one that was used, and asserting a contiguous span that does not exist.

This module holds the holdout constant that both sides import, and renders season sets
in a form that cannot imply continuity it does not have.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

# The seasons withheld from the deployed fit and reserved for evaluation.
# Both the trainer and the card generator MUST read this constant rather than
# restating it; a second copy is how the two drifted apart in the first place.
HOLDOUT_SEASONS: tuple[int, ...] = (2022, 2023)

DEFAULT_TRAINING_DATA = Path("app/data/training/engine_b_features_v2.csv")
OUTCOME_COLUMN = "avg_ppg_t1_t2"
ELIGIBILITY_COLUMN = "training_eligible"

# A dash is only honest across three or more unbroken seasons. Across two it saves
# nothing and invites a range reading of what is really an enumeration.
_MIN_RUN_TO_COMPRESS = 3


def _normalise(seasons: Iterable[int]) -> list[int]:
    return sorted({int(s) for s in seasons})


def describe_seasons(seasons: Iterable[int]) -> str:
    """Render a season set without ever implying a season it does not contain.

    ``[2018, 2019, 2020, 2021, 2025]`` becomes ``"2018–2021, 2025"`` — never
    ``"2018–2025"``, which would silently assert 2022, 2023 and 2024.
    """
    ordered = _normalise(seasons)
    if not ordered:
        return "none"

    runs: list[list[int]] = [[ordered[0]]]
    for season in ordered[1:]:
        if season == runs[-1][-1] + 1:
            runs[-1].append(season)
        else:
            runs.append([season])

    parts: list[str] = []
    for run in runs:
        if len(run) >= _MIN_RUN_TO_COMPRESS:
            parts.append(f"{run[0]}–{run[-1]}")
        else:
            parts.extend(str(season) for season in run)
    return ", ".join(parts)


def deployed_fit_seasons(trainable_seasons: Iterable[int]) -> list[int]:
    """The seasons the served artifact was actually fitted on.

    Takes TRAINABLE seasons — rows that carry an outcome. A season present in the
    feature matrix with no outcome yet (2025, whose t+1/t+2 result has not happened)
    cannot contribute to a fit no matter what the holdout says, and claiming it is the
    same overstatement this module exists to prevent.
    """
    holdout = set(HOLDOUT_SEASONS)
    return [s for s in _normalise(trainable_seasons) if s not in holdout]


def training_window_statement(
    trainable_seasons: Iterable[int],
    ungradable_seasons: Iterable[int] = (),
) -> str:
    """What the deployed model saw, and what was withheld from it.

    Names the excluded seasons rather than omitting them: a reader must be able to see
    what was held back without opening the training script. Carries no fold count —
    folds describe the evaluation, and conflating the two is the defect this repairs.
    """
    trainable = _normalise(trainable_seasons)
    fit = deployed_fit_seasons(trainable)
    held = [s for s in trainable if s in set(HOLDOUT_SEASONS)]
    ungradable = _normalise(ungradable_seasons)

    clauses = ["deployed fit"]
    if held:
        clauses.append(f"{describe_seasons(held)} held out for evaluation")
    if ungradable:
        clauses.append(
            f"{describe_seasons(ungradable)} present but not yet gradable, so not fitted"
        )
    if not held and not ungradable:
        clauses.append("no seasons withheld")
    return f"{describe_seasons(fit)} ({'; '.join(clauses)})"


def evaluation_window(fold_train_years: Iterable[Iterable[int]]) -> str:
    """What the walk-forward evaluation trained across, labelled as such.

    This is the statement the old ``training_window`` was actually making. It is true
    and worth publishing — it simply is not the deployed fit, and must say so.
    """
    folds = [list(years) for years in fold_train_years]
    if not folds:
        return "none"
    union = {year for years in folds for year in years}
    return f"{describe_seasons(union)} (walk-forward evaluation; {len(folds)} folds)"


def _blank(value: str | None) -> bool:
    return (value or "").strip().lower() in {"", "nan", "none", "null"}


def seasons_from_training_data(
    path: Path | str = DEFAULT_TRAINING_DATA,
    column: str = "feature_season",
) -> tuple[list[int], list[int]]:
    """Split the feature matrix into (trainable, ungradable) seasons, by measurement.

    A season is trainable when at least one of its rows carries an outcome. Measured
    2026-08-19: 2018-2023 carry outcomes for every row; 2025 carries **none** and its
    `training_eligible` flag is 0 throughout, because the t+1/t+2 result it would be
    graded against has not happened yet.

    Returns empty lists when the file is absent, so a caller can say "unknown" rather
    than publish a plausible-looking guess.
    """
    import csv

    p = Path(path)
    if not p.exists():
        return ([], [])
    with_outcome: set[int] = set()
    without_outcome: set[int] = set()
    with p.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw = (row.get(column) or "").strip()
            if not raw:
                continue
            try:
                season = int(float(raw))
            except ValueError:
                continue
            if _blank(row.get(OUTCOME_COLUMN)):
                without_outcome.add(season)
            else:
                with_outcome.add(season)
    return (sorted(with_outcome), sorted(without_outcome - with_outcome))
