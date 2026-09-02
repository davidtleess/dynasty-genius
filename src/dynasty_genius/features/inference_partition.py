"""DG-133 — the one definition of "the inference partition" for every consumer.

Why this file exists: the 09:00 PVO refresh failed every morning on
``ValueError("engine_b_prediction_conflict")`` raised by the producer's value-collision
guard. The guard was right; the rows it was handed were wrong. Four consumers — the
producer's row loader, ``EngineBService.score_inference_partition``, the model-capture
driver's utilization reader and the roster auditor's score index — each defined the
inference partition privately as::

    frame[frame["training_eligible"] == False]

That flag has never meant "score me". It means "this row can train the PRODUCTION
regression" (feature_assembly.py: ``window_complete & OUTCOME.notna()``). Since the
attrition fix, a player who washed out inside a complete window is KEPT with a null
outcome — an observation, not a missing row — and is therefore
``training_eligible == False`` as well. The mask stopped meaning "the latest season"
the day that landed.

Measured on the live runtime table (3,384 rows): the mask returns 1,143 rows spread
across feature seasons 2018..2023 and 2025, carrying 29 player_ids more than once. The
actual inference partition is the 505 rows of feature_season 2025 — one season, zero
duplicates, zero training rows. The service scored every masked ROW, so a player with
a washout row and a 2025 row received two different predictions, and the collision
guard fired.

The assembler already owns the rule: ``inference_season_rule(seasons) -> max(seasons)``,
pinned by tests/contract/test_inference_partition_seasons.py (DG-029) — "inference =
the latest season in the window, kept WITHOUT an outcome and training_eligible=False".
The consumers never called it. This module is the single place they call it from, and
it fails closed on every shape that could make "one prediction per player" untrue:

  * no ``feature_season`` column, or a season cell that does not read as an integer
  * an empty table
  * a row of the inference season that IS training-eligible (the partition rule and
    the flag disagree — the table was not built by the assembler's rule)
  * a ``training_eligible`` cell that reads as neither truth nor falsehood
  * a ``player_id`` appearing twice inside the inference season

Every failure is an ``InferencePartitionError`` whose message is a bare machine token,
because the refresh runner copies ``str(exc)`` into the governed report's
``aborted_reason`` and the API routes map the class to a governed 503. Two variants
share one rule set: a pandas frame selector for the readers that already hold a frame,
and a pure-Python records twin for the capture driver, which deliberately reads bytes
through the ``csv`` module and must stay pandas-free. They are kept rule-identical by
construction — every cell goes through the same normaliser whether it arrives as a
pandas scalar or as the CSV string pandas would have parsed it from (``"2025.0"`` and
``2025.0`` are the same season; ``"0.0"``, ``0.0`` and ``"False"`` are the same flag)
— and a contract test holds them to it across the spellings each writer produces.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.dynasty_genius.features.feature_assembly import inference_season_rule

SEASON_COLUMN = "feature_season"
PLAYER_COLUMN = "player_id"
ELIGIBLE_COLUMN = "training_eligible"

# Bare machine tokens: the refresh runner writes `str(exc)` into `aborted_reason`.
NO_SEASON_COLUMN = "inference_partition_no_season_column"
NO_PLAYER_COLUMN = "inference_partition_no_player_column"
NO_ELIGIBILITY_COLUMN = "inference_partition_no_eligibility_column"
UNREADABLE_ELIGIBILITY = "inference_partition_unreadable_eligibility"
EMPTY = "inference_partition_empty"
CONTAINS_TRAINING_ROWS = "inference_partition_contains_training_rows"
DUPLICATE_PLAYER = "inference_partition_duplicate_player"


class InferencePartitionError(ValueError):
    """A fail-closed refusal from the inference-partition contract.

    ``str(exc)`` is always one of the bare tokens above (or a consumer's own token for
    the same one-row-per-player promise), never prose, so a report or an HTTP detail
    can carry it verbatim. It subclasses ``ValueError`` so every existing
    ``except ValueError`` and ``pytest.raises(ValueError)`` keeps working; the subclass
    exists so a route can map this family to a governed 503 without swallowing every
    ``ValueError`` in the request.
    """


# How a boolean column arrives depends on who wrote it: pandas gives bool, a nullable
# boolean gives True/False/<NA>, a CSV read through the csv module gives the strings
# "True"/"False" (or "1"/"0" from an int-typed writer, "1.0"/"0.0" from a float-typed
# one), and a null cell gives "". Words are matched here; digits fall through to the
# numeric rule shared with the pandas path.
_TRUE_STRINGS = frozenset({"true"})
_FALSE_STRINGS = frozenset({"false", "", "nan"})


def inference_season_of(seasons: Iterable[int]) -> int:
    """The inference season for a set of present seasons: the assembler's rule, reused.

    Delegates to ``feature_assembly.inference_season_rule`` rather than restating it, so
    there is exactly one place the rule can change. No seasons at all is an empty
    partition, reported by its token rather than by ``max()``'s own message.
    """
    present = list(seasons)
    if not present:
        raise InferencePartitionError(EMPTY)
    return inference_season_rule(present)


def _is_missing(value: Any) -> bool:
    if value is None or value is pd.NA:
        return True
    return isinstance(value, float) and math.isnan(value)


def _is_training_eligible(value: Any) -> bool:
    """Read one ``training_eligible`` cell however the source dtype delivered it.

    Shared by both variants so a CSV string and a pandas scalar answer identically: a
    word is matched as a word, and anything else is read as a number that must be
    exactly 0 or 1 (NaN is a null cell, hence not eligible). A cell that is neither —
    ``"yes"``, ``2``, ``"T"`` — is refused; guessing would let a training row through
    on a spelling.
    """
    if _is_missing(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE_STRINGS:
            return True
        if text in _FALSE_STRINGS:
            return False
        try:
            number = float(text)
        except ValueError as exc:
            raise InferencePartitionError(UNREADABLE_ELIGIBILITY) from exc
    else:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise InferencePartitionError(UNREADABLE_ELIGIBILITY) from exc
    if math.isnan(number):
        return False
    if number == 1.0:
        return True
    if number == 0.0:
        return False
    raise InferencePartitionError(UNREADABLE_ELIGIBILITY)


def _season_of(value: Any) -> int:
    """Parse one ``feature_season`` cell to an int, refusing blanks and non-integers.

    A season that cannot be read cannot be placed in the partition, and skipping it
    would silently shrink the table — so it fails the whole selection instead. A CSV
    string takes the same numeric path as a pandas scalar, so ``"2025.0"`` (a
    float-typed writer) and ``2025.0`` (what pandas reads it back as) agree.
    """
    if _is_missing(value):
        raise InferencePartitionError(NO_SEASON_COLUMN)
    if isinstance(value, (bool, np.bool_)):
        raise InferencePartitionError(NO_SEASON_COLUMN)
    try:
        as_float = float(value.strip() if isinstance(value, str) else value)
    except (TypeError, ValueError) as exc:
        raise InferencePartitionError(NO_SEASON_COLUMN) from exc
    if math.isnan(as_float) or not as_float.is_integer():
        raise InferencePartitionError(NO_SEASON_COLUMN)
    return int(as_float)


def player_key(value: Any) -> str | None:
    """The identity a consumer keys on, or None for an absent ``player_id``.

    Every consumer keys its dict by the string form of the gsis id and skips a null
    one (a row with no id can never be joined to a roster, a PVO or a capture entry).
    Duplicates are judged on this same key, so absent ids are never duplicates of each
    other — they are left in the partition for the caller to skip through this helper.
    """
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _assert_one_row_per_player(
    player_ids: Iterable[Any], eligibles: Iterable[Any]
) -> None:
    """The two invariants both variants promise, checked from plain iterables."""
    for eligible in eligibles:
        if _is_training_eligible(eligible):
            raise InferencePartitionError(CONTAINS_TRAINING_ROWS)
    seen: set[str] = set()
    for raw in player_ids:
        key = player_key(raw)
        if key is None:
            continue
        if key in seen:
            raise InferencePartitionError(DUPLICATE_PLAYER)
        seen.add(key)


def select_inference_partition(frame: pd.DataFrame) -> pd.DataFrame:
    """The rows of the inference season, verified one-per-player, as a fresh frame.

    Requires ``feature_season``, ``player_id`` and ``training_eligible``. Returns a copy
    with a reset index so a caller can never write through to the source frame. Cells
    are returned as delivered — the season column keeps the source dtype.
    """
    for column, token in (
        (SEASON_COLUMN, NO_SEASON_COLUMN),
        (PLAYER_COLUMN, NO_PLAYER_COLUMN),
        (ELIGIBLE_COLUMN, NO_ELIGIBILITY_COLUMN),
    ):
        if column not in frame.columns:
            raise InferencePartitionError(token)
    if frame.empty:
        raise InferencePartitionError(EMPTY)

    seasons = pd.Series(
        [_season_of(value) for value in frame[SEASON_COLUMN]], index=frame.index
    )
    season = inference_season_of(seasons)
    partition = frame[seasons == season].copy().reset_index(drop=True)
    if partition.empty:
        raise InferencePartitionError(EMPTY)

    _assert_one_row_per_player(partition[PLAYER_COLUMN], partition[ELIGIBLE_COLUMN])
    return partition


def select_inference_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The pure-Python twin of ``select_inference_partition`` for ``csv.DictReader``.

    Identical rules, identical error tokens, no pandas: materialise, find the
    inference season, keep its rows, assert one-per-player. CSV cells arrive as
    strings — a blank or unparsable ``feature_season`` fails the selection rather
    than being skipped. Records are returned as delivered (string cells intact).
    """
    rows = [dict(record) for record in records]
    if not rows:
        raise InferencePartitionError(EMPTY)
    for row in rows:
        if PLAYER_COLUMN not in row:
            raise InferencePartitionError(NO_PLAYER_COLUMN)
        if ELIGIBLE_COLUMN not in row:
            raise InferencePartitionError(NO_ELIGIBILITY_COLUMN)

    seasons = [_season_of(row.get(SEASON_COLUMN)) for row in rows]
    season = inference_season_of(seasons)
    partition = [row for row, row_season in zip(rows, seasons) if row_season == season]
    if not partition:
        raise InferencePartitionError(EMPTY)

    _assert_one_row_per_player(
        (row.get(PLAYER_COLUMN) for row in partition),
        (row.get(ELIGIBLE_COLUMN) for row in partition),
    )
    return partition
