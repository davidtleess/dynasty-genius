"""DG-133 — the inference partition is a SEASON, not the complement of a flag.

Why this file exists: the 09:00 PVO refresh failed every morning on
``engine_b_prediction_conflict``. Four consumers selected the inference partition as
``frame[frame["training_eligible"] == False]``. That flag means "can train the
production regression"; since the attrition fix a complete-window washout row is kept
with a null outcome and is therefore ALSO ``training_eligible == False``. On the live
table the mask returned 1,143 rows across 2018..2023 and 2025 with 29 duplicated
player_ids, where the partition is the 505 rows of feature_season 2025.

These tests pin the shared selector (``inference_partition``), its pure-Python twin,
the fail-closed paths by their bare machine tokens, each of the four readers by
BEHAVIOUR on the washout shape (a source scan alone cannot hold a reader — it is kept
as a best-effort tripwire and self-tested for reach), and the serving path's answer
when the partition is refused.
"""
from __future__ import annotations

import asyncio
import csv
import importlib
import io
import re
import tokenize
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge

from src.dynasty_genius.features import inference_partition as ip
from src.dynasty_genius.features.feature_assembly import (
    OUTCOME_COLUMN,
    inference_season_rule,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The four readers named in DG-133, by import path.
_READER_MODULES = (
    "scripts.build_universe_pvo_batch",
    "app.services.engine_b_service",
    "src.dynasty_genius.capture.model_forward_capture_driver",
    "app.services.roster_auditor",
)


def _row(player_id: str, season: int, *, eligible: bool, washout: bool = False) -> dict:
    """One feature row in the assembler's shape.

    ``washout`` is the attrition-fix shape: a complete-window row kept with
    outcome_returned=False and a null outcome — hence training_eligible=False.
    """
    return {
        "player_id": player_id,
        "feature_season": season,
        "position": "WR",
        "age": 24 + (season - 2018),
        "ppg_t": 10.0,
        "weighted_opportunity": 0.5,
        "games_t": 17,
        OUTCOME_COLUMN: np.nan if (washout or not eligible) else 12.0,
        "outcome_returned": (False if washout else (True if eligible else pd.NA)),
        "training_eligible": eligible,
    }


def _live_shape_frame() -> pd.DataFrame:
    """The exact shape that fired the guard: one player with a 2018 washout row AND a
    2025 inference row, beside ordinary training rows and a second inference player."""
    return pd.DataFrame(
        [
            _row("00-WASHOUT", 2018, eligible=False, washout=True),
            _row("00-TRAINED", 2018, eligible=True),
            _row("00-TRAINED", 2019, eligible=True),
            _row("00-WASHOUT", 2025, eligible=False),
            _row("00-TRAINED", 2025, eligible=False),
        ]
    )


def _old_mask(frame: pd.DataFrame) -> pd.DataFrame:
    """The selection every reader used before DG-133 — kept here only as the foil."""
    return frame[frame["training_eligible"] == False]  # noqa: E712


# ── 1. the live shape ──────────────────────────────────────────────────────────────


def test_a_washout_row_from_an_earlier_season_is_not_a_second_inference_row() -> None:
    frame = _live_shape_frame()

    old = _old_mask(frame)
    assert len(old) == 3, (
        "the old mask admits the washout row alongside the inference rows"
    )
    assert int(old["player_id"].duplicated().sum()) == 1, (
        "the old mask hands the producer the same player twice — that is the conflict"
    )

    partition = ip.select_inference_partition(frame)
    assert set(partition["feature_season"]) == {2025}
    assert sorted(partition["player_id"]) == ["00-TRAINED", "00-WASHOUT"]
    assert not partition["player_id"].duplicated().any()
    assert not partition["training_eligible"].any()
    assert list(partition.index) == [0, 1], (
        "the partition is a fresh frame, index reset"
    )


def test_the_partition_season_is_the_assembler_rule_not_a_literal() -> None:
    assert ip.inference_season_of([2018, 2025, 2021]) == inference_season_rule(
        [2018, 2025, 2021]
    )
    later = pd.concat(
        [_live_shape_frame(), pd.DataFrame([_row("00-NEW", 2026, eligible=False)])],
        ignore_index=True,
    )
    assert set(ip.select_inference_partition(later)["feature_season"]) == {2026}


# ── 2. every fail-closed path, by its token ────────────────────────────────────────


def test_every_refusal_is_a_typed_error_carrying_only_its_token() -> None:
    """The runner writes ``str(exc)`` into ``aborted_reason`` and the routes map the
    class to a 503, so the class must be a ValueError and the message must be bare."""
    assert issubclass(ip.InferencePartitionError, ValueError)
    with pytest.raises(ip.InferencePartitionError) as caught:
        ip.select_inference_partition(_live_shape_frame().iloc[0:0])
    assert str(caught.value) == ip.EMPTY
    with pytest.raises(ip.InferencePartitionError, match=f"^{ip.EMPTY}$"):
        ip.inference_season_of([])


def test_no_season_column_fails_closed() -> None:
    frame = _live_shape_frame().drop(columns=["feature_season"])
    with pytest.raises(ValueError, match=f"^{ip.NO_SEASON_COLUMN}$"):
        ip.select_inference_partition(frame)


def test_an_unreadable_season_cell_fails_closed_rather_than_skipping_the_row() -> None:
    frame = _live_shape_frame()
    frame.loc[3, "feature_season"] = np.nan
    with pytest.raises(ValueError, match=f"^{ip.NO_SEASON_COLUMN}$"):
        ip.select_inference_partition(frame)
    for unreadable in ("", "nan", "x", "2025.5", True, 2025.5):
        with pytest.raises(ValueError, match=f"^{ip.NO_SEASON_COLUMN}$"):
            ip.season_of(unreadable)


def test_empty_table_fails_closed() -> None:
    frame = _live_shape_frame().iloc[0:0]
    with pytest.raises(ValueError, match=f"^{ip.EMPTY}$"):
        ip.select_inference_partition(frame)


def test_a_training_row_in_the_latest_season_fails_closed() -> None:
    frame = _live_shape_frame()
    frame.loc[frame["player_id"] == "00-TRAINED", "training_eligible"] = True
    with pytest.raises(ValueError, match=f"^{ip.CONTAINS_TRAINING_ROWS}$"):
        ip.select_inference_partition(frame)


def test_a_duplicated_player_in_the_latest_season_fails_closed() -> None:
    frame = pd.concat(
        [_live_shape_frame(), pd.DataFrame([_row("00-TRAINED", 2025, eligible=False)])],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match=f"^{ip.DUPLICATE_PLAYER}$"):
        ip.select_inference_partition(frame)


def test_null_player_ids_are_left_for_the_caller_not_counted_as_duplicates() -> None:
    frame = pd.concat(
        [
            _live_shape_frame(),
            pd.DataFrame(
                [_row(None, 2025, eligible=False), _row(None, 2025, eligible=False)]
            ),
        ],
        ignore_index=True,
    )
    partition = ip.select_inference_partition(frame)
    assert len(partition) == 4
    assert int(partition["player_id"].isna().sum()) == 2
    assert [ip.player_key(v) for v in (None, np.nan, pd.NA, "", "  ")] == [None] * 5
    assert ip.player_key(" 00-0012345 ") == "00-0012345"


def test_missing_player_or_eligibility_columns_fail_closed() -> None:
    with pytest.raises(ValueError, match=f"^{ip.NO_PLAYER_COLUMN}$"):
        ip.select_inference_partition(_live_shape_frame().drop(columns=["player_id"]))
    with pytest.raises(ValueError, match=f"^{ip.NO_ELIGIBILITY_COLUMN}$"):
        ip.select_inference_partition(
            _live_shape_frame().drop(columns=["training_eligible"])
        )


def test_an_unreadable_eligibility_cell_is_not_reported_as_a_missing_column() -> None:
    """``aborted_reason`` must tell a schema problem from a data problem."""
    frame = _live_shape_frame().astype({"training_eligible": object})
    frame.loc[3, "training_eligible"] = "yes"
    with pytest.raises(ValueError, match=f"^{ip.UNREADABLE_ELIGIBILITY}$"):
        ip.select_inference_partition(frame)
    assert ip.UNREADABLE_ELIGIBILITY != ip.NO_ELIGIBILITY_COLUMN


def test_records_twin_raises_the_same_tokens() -> None:
    rows = _live_shape_frame().to_dict("records")

    with pytest.raises(ValueError, match=f"^{ip.EMPTY}$"):
        ip.select_inference_records([])
    with pytest.raises(ValueError, match=f"^{ip.NO_SEASON_COLUMN}$"):
        ip.select_inference_records(
            [{k: v for k, v in r.items() if k != "feature_season"} for r in rows]
        )
    with pytest.raises(ValueError, match=f"^{ip.NO_SEASON_COLUMN}$"):
        ip.select_inference_records([{**r, "feature_season": ""} for r in rows])
    with pytest.raises(ValueError, match=f"^{ip.CONTAINS_TRAINING_ROWS}$"):
        ip.select_inference_records(
            [
                {**r, "training_eligible": "True"} if r["feature_season"] == 2025 else r
                for r in rows
            ]
        )
    with pytest.raises(ValueError, match=f"^{ip.DUPLICATE_PLAYER}$"):
        ip.select_inference_records(rows + [rows[-1]])
    with pytest.raises(ValueError, match=f"^{ip.UNREADABLE_ELIGIBILITY}$"):
        ip.select_inference_records(
            [{**r, "training_eligible": "T"} if r["feature_season"] == 2025 else r
             for r in rows]
        )


# ── 3. the records twin agrees with the frame variant ──────────────────────────────

# How each writer this repo could plausibly meet spells the two columns the selector
# reads. "words"/"int_bool" is the assembler (bool column → "True"/"False", int
# season); the float spellings are what pandas writes once either column has been
# through a float dtype — "2025.0", "1.0"/"0.0" — which pandas reads back as numbers
# but the csv module hands over as strings. The twins must agree on all of them.
_WRITERS = ("words", "digits", "float_season", "float_eligibility", "nullable_boolean")


def _csv_bytes(frame: pd.DataFrame, *, writer: str) -> bytes:
    out = frame.copy()
    if writer == "words":
        out["training_eligible"] = out["training_eligible"].map(
            {True: "True", False: "False"}
        )
    elif writer == "digits":
        out["training_eligible"] = out["training_eligible"].map({True: "1", False: "0"})
    elif writer == "float_season":
        out["feature_season"] = out["feature_season"].astype("float64")
    elif writer == "float_eligibility":
        out["training_eligible"] = out["training_eligible"].astype("float64")
    elif writer == "nullable_boolean":
        out["training_eligible"] = out["training_eligible"].astype("boolean")
        out.loc[0, "training_eligible"] = pd.NA  # a null flag on the washout row
    else:  # pragma: no cover - guard against a typo in the parametrisation
        raise AssertionError(writer)
    return out.to_csv(index=False).encode()


@pytest.mark.parametrize("writer", _WRITERS)
def test_records_twin_agrees_with_the_frame_variant_on_every_writer_spelling(
    writer: str,
) -> None:
    frame = _live_shape_frame()
    raw = _csv_bytes(frame, writer=writer)

    from_frame = ip.select_inference_partition(pd.read_csv(io.BytesIO(raw)))
    from_records = ip.select_inference_records(
        csv.DictReader(io.StringIO(raw.decode()))
    )

    assert [r["player_id"] for r in from_records] == list(from_frame["player_id"])
    assert sorted(from_frame["player_id"]) == ["00-TRAINED", "00-WASHOUT"]
    assert {ip.season_of(r["feature_season"]) for r in from_records} == {2025}
    assert {ip.season_of(v) for v in from_frame["feature_season"]} == {2025}
    assert not any(
        ip.is_training_eligible(r["training_eligible"]) for r in from_records
    )


@pytest.mark.parametrize("writer", _WRITERS)
def test_records_twin_refuses_what_the_frame_variant_refuses_on_every_spelling(
    writer: str,
) -> None:
    """Agreement must hold on the refusals too: the same bytes, the same token."""
    frame = pd.concat(
        [_live_shape_frame(), pd.DataFrame([_row("00-TRAINED", 2025, eligible=True)])],
        ignore_index=True,
    )
    raw = _csv_bytes(frame, writer=writer)
    with pytest.raises(ValueError) as from_frame:
        ip.select_inference_partition(pd.read_csv(io.BytesIO(raw)))
    with pytest.raises(ValueError) as from_records:
        ip.select_inference_records(csv.DictReader(io.StringIO(raw.decode())))
    assert str(from_frame.value) == str(from_records.value) == ip.CONTAINS_TRAINING_ROWS


def test_the_shared_boolean_reader_covers_every_dtype_a_csv_can_deliver() -> None:
    truthies = (
        True, np.True_, 1, np.int64(1), 1.0, np.float64(1.0),
        "True", "true", " TRUE ", "1", "1.0", " 1.0 ",
    )
    for truthy in truthies:
        assert ip.is_training_eligible(truthy) is True, truthy
    falsies = (
        False, np.False_, 0, np.int64(0), 0.0, np.float64(0.0),
        "False", "false", "0", "0.0", "", None, np.nan, pd.NA, "nan",
    )
    for falsy in falsies:
        assert ip.is_training_eligible(falsy) is False, falsy
    for unreadable in ("yes", "T", "F", 2, "2", 2.0, -1, "0.5", object()):
        with pytest.raises(ValueError, match=f"^{ip.UNREADABLE_ELIGIBILITY}$"):
            ip.is_training_eligible(unreadable)


def test_the_shared_season_reader_gives_one_answer_per_spelling() -> None:
    for spelling in (2025, np.int64(2025), 2025.0, np.float64(2025.0), "2025", "2025.0", " 2025 "):
        assert ip.season_of(spelling) == 2025, spelling


# ── 4. no reader still carries the private mask (a best-effort tripwire) ───────────
#
# This scan is a tripwire, not the guarantee — sections 6-8 hold each reader by
# behaviour. It reads CODE tokens only (comments and docstrings are dropped, a
# black-wrapped expression is rejoined), so prose may say "training_eligible == False"
# freely, and it is self-tested below on the spellings it must catch and must not.

_FLAG = r"""(["']training_eligible["']|\.\s*training_eligible\b)"""
# Applied to one logical line of code at a time.
_SAME_EXPRESSION_MASKS = (
    # the flag compared with a falsehood inside one expression, in any spelling
    re.compile(
        _FLAG
        + r".{0,60}?(==\s*(False|0|np\s*\.\s*False_)\b|!=\s*(True|1)\b|is\s+False\b"
        + r"""|[!=]=\s*(?i:["']false["']))"""
    ),
    # the pandas method spellings of the same comparison
    re.compile(
        _FLAG
        + r".{0,60}?\.\s*(eq\s*\(\s*(False|0)\b|ne\s*\(\s*(True|1)\b"
        + r"|isin\s*\(\s*[\[(]\s*(False|0)\b)"
    ),
    # negation applied to the column — ~frame["training_eligible"],
    # ~frame.training_eligible, not row["training_eligible"], with or without an
    # .astype(bool) hung off it — unless the column is then REDUCED to a scalar
    # (.any()/.all()/...), which is an assertion, not a row selection.
    re.compile(
        r"(~|\bnot\b)\s*\w+\s*(\[\s*" + _FLAG + r"\s*\]|\.\s*training_eligible\b)"
        r"(?!\s*\.\s*(any|all|sum|mean|count)\s*\()"
    ),
)
# Applied to a logical line joined with the one after it: the skip-loop spelling
# `if <flag> == "true":` / `continue` keeps exactly the non-training rows. The driver's
# training-cutoff derivation uses the same comparison followed by a `try:` block and
# must stay allowed, so the `continue` is required.
_SKIP_LOOP_MASK = re.compile(
    _FLAG + r""".{0,80}?[!=]=\s*(?i:["']true["'])\s*:\s*continue\b"""
)


def _code_lines(source: str) -> list[str]:
    """Logical lines of code, space-joined from tokens: comments gone, docstrings gone,
    wrapped expressions on one line."""
    lines: list[str] = []
    current: list[tokenize.TokenInfo] = []
    skipped = {
        tokenize.COMMENT, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING,
    }
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in skipped:
            continue
        if tok.type in (tokenize.NEWLINE, tokenize.ENDMARKER):
            is_docstring = len(current) == 1 and current[0].type == tokenize.STRING
            if current and not is_docstring:
                lines.append(" ".join(t.string for t in current))
            current = []
            continue
        current.append(tok)
    return lines


def _private_mask_hits(source: str) -> list[str]:
    lines = _code_lines(source)
    hits: list[str] = []
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if any(pattern.search(line) for pattern in _SAME_EXPRESSION_MASKS):
            hits.append(line)
        elif _SKIP_LOOP_MASK.search(f"{line}\n{following}"):
            hits.append(line)
    return hits


_MUST_CATCH = (
    'inference = frame[frame["training_eligible"] == False].copy()',
    'if str(record.get("training_eligible", "")).strip().lower() != "false":\n    continue',
    'inference = frame[frame["training_eligible"] == "False"]',
    'inference = frame[frame["training_eligible"] != True]',
    'inference = frame[frame["training_eligible"] == 0]',
    'inference = frame[frame["training_eligible"] != 1]',
    'inference = frame[~frame["training_eligible"]]',
    'inference = frame[~frame["training_eligible"].astype(bool)]',
    "inference = frame[~frame.training_eligible]",
    'inference = frame[frame["training_eligible"].eq(False)]',
    'inference = frame[frame["training_eligible"].isin([False])]',
    'inference = frame[frame["training_eligible"].isin([0, False])]',
    'if row["training_eligible"] is False:\n    keep(row)',
    'if not row["training_eligible"]:\n    keep(row)',
    'inference = frame[frame["training_eligible"] == np.False_]',
    'inference = frame[frame["training_eligible"].astype(bool) == False]',
    'inference = frame[\n    frame["training_eligible"]\n    == False\n]',
    'if str(record.get("training_eligible", "")).strip().lower() == "true":\n    continue',
    'if record.get("training_eligible") != "False":\n    continue',
    "inference = frame[frame.training_eligible == False]",
)

_MUST_IGNORE = (
    '# the old mask was frame[frame["training_eligible"] == False]',
    '"""The old mask was frame[frame["training_eligible"] == False]."""\nx = 1',
    'def f():\n    """frame[~frame["training_eligible"]] was the bug."""\n    return 1',
    # the driver's training-cutoff derivation until DG-134: == "true" then a try block
    'if record.get("training_eligible", "").lower() == "true":\n    try:\n        pass\n    except KeyError:\n        pass',
    # the assembler's own assignment of the flag
    'merged["training_eligible"] = window_complete & merged[OUTCOME_COLUMN].notna()',
    'assert not partition["training_eligible"].any()',
    'eligible = ip.is_training_eligible(row["training_eligible"])',
)


@pytest.mark.parametrize("snippet", _MUST_CATCH)
def test_the_source_scan_catches_each_known_reintroduction_spelling(snippet: str) -> None:
    assert _private_mask_hits(snippet), f"scan misses: {snippet!r}"


@pytest.mark.parametrize("snippet", _MUST_IGNORE)
def test_the_source_scan_ignores_prose_and_the_legitimate_uses(snippet: str) -> None:
    assert _private_mask_hits(snippet) == [], f"scan false-positive: {snippet!r}"


@pytest.mark.parametrize("module_name", _READER_MODULES)
def test_no_reader_selects_the_partition_by_the_flag_any_more(module_name: str) -> None:
    source = Path(importlib.import_module(module_name).__file__).read_text()
    hits = _private_mask_hits(source)
    assert hits == [], f"{module_name} still selects on the flag: {hits}"


# Each reader must not only import the shared module but CALL it where the partition
# is taken — an import alone would satisfy a substring check.
_READER_CALL_SITES = {
    "scripts.build_universe_pvo_batch": ("select_inference_partition(frame)", 1),
    "app.services.engine_b_service": ("select_inference_partition(df)", 1),
    "src.dynasty_genius.capture.model_forward_capture_driver": (
        "select_inference_records(reader)", 1
    ),
    "app.services.roster_auditor": (
        "_index_predictions_by_player(score_inference_partition())", 2
    ),
}


@pytest.mark.parametrize("module_name", _READER_MODULES)
def test_every_reader_takes_its_partition_from_the_shared_module(module_name: str) -> None:
    source = Path(importlib.import_module(module_name).__file__).read_text()
    assert "from src.dynasty_genius.features.inference_partition import" in source, (
        f"{module_name} must take its partition from the shared module"
    )
    call, count = _READER_CALL_SITES[module_name]
    assert source.count(call) == count, (
        f"{module_name}: expected {count} call site(s) of {call!r}"
    )


# ── 5. the live artifact: the bug is real on this machine's data ───────────────────

_DATA = _REPO_ROOT / "app" / "data"
_LIVE_TABLES = {
    "runtime": _DATA / "features_runtime" / "engine_b_features_runtime.csv",
    "seed": _DATA / "training" / "engine_b_features_v2.csv",
}


@pytest.mark.parametrize("label", sorted(_LIVE_TABLES))
def test_on_the_real_table_the_flag_mask_over_selects_and_the_season_does_not(
    label: str,
) -> None:
    path = _LIVE_TABLES[label]
    if not path.exists():
        pytest.skip(f"{label} feature table not present at {path}")
    raw = path.read_bytes()
    frame = pd.read_csv(io.BytesIO(raw))

    old = _old_mask(frame)
    partition = ip.select_inference_partition(frame)

    assert partition["feature_season"].nunique() == 1
    assert int(partition["player_id"].dropna().duplicated().sum()) == 0
    assert len(partition) < len(old), (
        f"{label}: the old mask returns {len(old)} rows across seasons "
        f"{sorted(old['feature_season'].unique())}; the partition is "
        f"{len(partition)} — if these are equal the table no longer carries "
        "complete-window washout rows"
    )
    assert int(old["player_id"].duplicated().sum()) > 0, (
        f"{label}: the old mask should carry duplicated player_ids on this table"
    )

    # The capture driver reads these same bytes through the csv module.
    from_records = ip.select_inference_records(csv.DictReader(io.StringIO(raw.decode())))
    assert [r["player_id"] for r in from_records] == list(partition["player_id"])


# ── 6. roster_auditor refuses a repeated prediction instead of last-wins ───────────


def test_roster_audit_refuses_two_predictions_for_one_player() -> None:
    from tests.contract.test_roster_audit_pvo import (
        _RB_ENGINE_B_SCORE,
        _RB_PLAYER,
        _run,
    )

    conflicting = {**_RB_ENGINE_B_SCORE, "predicted_avg_ppg_t1_t2": 3.1}
    with pytest.raises(ValueError, match="^engine_b_prediction_duplicate_player$"):
        _run(roster=[_RB_PLAYER], scores=[_RB_ENGINE_B_SCORE, conflicting])


def test_run_audit_refuses_two_predictions_for_one_player_too() -> None:
    """The legacy ``run_audit`` shares the index helper; pin its call site as well."""
    from app.services.roster_auditor import run_audit
    from tests.contract.test_roster_audit_pvo import _RB_ENGINE_B_SCORE

    roster = [
        {"player_id": "rb1", "full_name": "Veteran RB", "position": "RB", "team": "FA",
         "age": 27, "gsis_id": _RB_ENGINE_B_SCORE["player_id"]},
    ]
    conflicting = {**_RB_ENGINE_B_SCORE, "predicted_avg_ppg_t1_t2": 3.1}
    with (
        patch("app.services.roster_auditor.get_my_roster", new_callable=AsyncMock,
              return_value=roster),
        patch("app.services.roster_auditor.score_inference_partition",
              return_value=[_RB_ENGINE_B_SCORE, conflicting]),
        patch("app.services.roster_auditor.load_qb_identity_bridge",
              return_value={"players": {}}),
    ):
        with pytest.raises(ValueError, match="^engine_b_prediction_duplicate_player$"):
            asyncio.run(run_audit())


def test_roster_audit_index_helper_keys_by_the_partition_player_column() -> None:
    from app.services.roster_auditor import _index_predictions_by_player

    indexed = _index_predictions_by_player(
        [{"player_id": "a", "x": 1}, {"player_id": "b", "x": 2}]
    )
    assert indexed == {"a": {"player_id": "a", "x": 1}, "b": {"player_id": "b", "x": 2}}
    with pytest.raises(ip.InferencePartitionError,
                       match="^engine_b_prediction_duplicate_player$"):
        _index_predictions_by_player([{"player_id": "a"}, {"player_id": "a"}])


def test_two_unkeyed_predictions_are_not_the_same_player_twice() -> None:
    """A null ``player_id`` is a missing id, not a repeated one: the index skips it
    and the audit proceeds, exactly as the old comprehension let it (which collapsed
    them under one NaN key) — it must not abort under the duplicate token."""
    from app.services.roster_auditor import _index_predictions_by_player
    from tests.contract.test_roster_audit_pvo import (
        _RB_ENGINE_B_SCORE,
        _RB_PLAYER,
        _run,
    )

    unkeyed = [
        {**_RB_ENGINE_B_SCORE, "player_id": np.nan},
        {**_RB_ENGINE_B_SCORE, "player_id": None},
        {**_RB_ENGINE_B_SCORE, "player_id": ""},
        {k: v for k, v in _RB_ENGINE_B_SCORE.items() if k != "player_id"},
    ]
    indexed = _index_predictions_by_player([*unkeyed, _RB_ENGINE_B_SCORE])
    assert list(indexed) == [_RB_ENGINE_B_SCORE["player_id"]]

    result = _run(roster=[_RB_PLAYER], scores=[*unkeyed, _RB_ENGINE_B_SCORE])
    assert len(result["players"]) == 1


# ── 7. the service scores only the inference season ────────────────────────────────


def _bundle(features: list[str]) -> dict:
    """A tiny fitted bundle in the service's shape (as tests/test_engine_b_service)."""
    X = np.array([[20, 5.0, 0.1], [21, 10.0, 0.2], [22, 15.0, 0.3], [23, 20.0, 0.4]])
    y = np.array([5.0, 10.0, 15.0, 20.0])
    model = Ridge().fit(X, y)
    imputer = SimpleImputer(strategy="mean").fit(X)
    return {
        "model": model,
        "imputer": imputer,
        "features": features,
        "version": "engine_b_v2_wr",
    }


def _service_over(frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    from app.services import engine_b_service

    monkeypatch.setattr(engine_b_service.pd, "read_csv", lambda *_a, **_k: frame)
    svc = engine_b_service.EngineBService.__new__(engine_b_service.EngineBService)
    svc._loaded = True
    svc._v2_bundles = {"WR": _bundle(["age", "ppg_t", "weighted_opportunity"])}
    svc._v1_bundle = {}

    class _Source:
        path = Path("unused-by-the-monkeypatched-reader.csv")

    return lambda: svc.score_inference_partition(feature_source=_Source())


def test_service_scores_only_the_inference_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictions = _service_over(_live_shape_frame(), monkeypatch)()

    assert sorted(p["player_id"] for p in predictions) == ["00-TRAINED", "00-WASHOUT"]
    assert {p["feature_season"] for p in predictions} == {2025}
    assert len({p["player_id"] for p in predictions}) == len(predictions)


def test_service_skips_an_unkeyed_row_rather_than_emitting_a_nan_player(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two inference-season rows with no ``player_id`` must not reach the roster index
    as two predictions sharing one NaN key (which would read as a duplicate player)."""
    frame = pd.concat(
        [
            _live_shape_frame(),
            pd.DataFrame(
                [_row(None, 2025, eligible=False), _row(None, 2025, eligible=False)]
            ),
        ],
        ignore_index=True,
    )
    # Through real CSV bytes, as production reads it: a blank cell becomes NaN.
    frame = pd.read_csv(io.BytesIO(frame.to_csv(index=False).encode()))
    predictions = _service_over(frame, monkeypatch)()

    assert sorted(p["player_id"] for p in predictions) == ["00-TRAINED", "00-WASHOUT"]
    from app.services.roster_auditor import _index_predictions_by_player

    assert set(_index_predictions_by_player(predictions)) == {"00-TRAINED", "00-WASHOUT"}


def test_service_fails_closed_on_a_present_but_unusable_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ip.InferencePartitionError, match=f"^{ip.EMPTY}$"):
        _service_over(_live_shape_frame().iloc[0:0], monkeypatch)()


# ── 8. readers 1 and 3 by behaviour: the washout row comes AFTER the 2025 row ──────
#
# On the live table file order happens to put a player's 2025 row last, so a
# last-wins dict was right by luck. These fixtures put the washout row after the 2025
# row, where last-wins is wrong, so the readers are held by what they return and not
# by the source scan.

_WASHOUT_AFTER_INFERENCE_CSV = (
    b"player_id,season,feature_season,position,training_eligible,snap_share,"
    b"route_participation,target_share_nfl,air_yards_share,weighted_opportunity,yprr,tprr\n"
    b"00-Y,2025,2025,WR,False,0.40,0.50,0.10,0.10,0.30,1.50,0.15\n"
    b"00-X,2025,2025,RB,False,0.90,0.64,0.18,0.08,0.79,2.19,0.22\n"
    b"00-X,2019,2019,RB,False,0.05,0.10,0.02,0.01,0.05,0.50,0.05\n"
    b"00-Z,2019,2019,RB,True,0.70,0.60,0.15,0.07,0.70,2.00,0.20\n"
)


def test_producer_row_loader_keeps_the_inference_row_when_the_washout_row_comes_later(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import build_universe_pvo_batch as producer
    from src.dynasty_genius.models import availability

    # The loader attaches P(plays) from the availability model; that is a separate
    # contract, stubbed here so this test holds only the partition.
    monkeypatch.setattr(availability, "score_rows", lambda rows, **_: {"00-X": 0.5})
    path = tmp_path / "features.csv"
    path.write_bytes(_WASHOUT_AFTER_INFERENCE_CSV)

    rows = producer._load_engine_b_feature_rows(path)

    assert set(rows) == {"00-X", "00-Y"}
    assert rows["00-X"]["feature_season"] == 2025
    assert rows["00-X"]["snap_share"] == pytest.approx(0.90)
    assert rows["00-X"]["availability_p"] == 0.5
    assert "availability_p" not in rows["00-Y"]


def test_capture_driver_utilization_map_keeps_the_inference_row_when_the_washout_row_comes_later() -> None:
    from src.dynasty_genius.capture.model_forward_capture_driver import (
        _load_prediction_time_utilization,
    )

    by_player, present = _load_prediction_time_utilization(
        {"feature_csv": {"path": "x.csv"}}, lambda _p: _WASHOUT_AFTER_INFERENCE_CSV
    )

    assert set(by_player) == {"00-X", "00-Y"}
    assert by_player["00-X"]["feature_season"] == "2025"
    assert by_player["00-X"]["snap_share"] == "0.90"
    assert "snap_share" in present


@pytest.mark.parametrize(
    ("feature_csv", "token"),
    [
        (
            b"player_id,season,feature_season,position,training_eligible,snap_share\n",
            ip.EMPTY,
        ),
        (
            b"player_id,season,feature_season,position,training_eligible,snap_share\n"
            b"00-TEST-RB,2025,2025,RB,false,0.71\n"
            b"00-TEST-RB,2025,2025,RB,false,0.72\n",
            ip.DUPLICATE_PLAYER,
        ),
        (
            b"player_id,season,feature_season,position,training_eligible,snap_share\n"
            b"00-OLD,2025,2025,QB,true,0.10\n"
            b"00-TEST-RB,2025,2025,RB,false,0.71\n",
            ip.CONTAINS_TRAINING_ROWS,
        ),
    ],
)
def test_capture_driver_reports_a_refused_partition_through_its_own_abort(
    tmp_path: Path, feature_csv: bytes, token: str
) -> None:
    """Every other refusal in the driver is a persisted ``aborted`` report; a
    partition the selector refuses must be reported the same way, not as a traceback
    on the standalone CLI, and nothing may be appended to the store."""
    from src.dynasty_genius.capture.model_forward_capture_driver import (
        capture_model_pvo_snapshot,
    )
    from src.dynasty_genius.capture.model_forward_capture_store import (
        MODEL_PVO_SOURCE,
        ModelForwardCaptureStore,
    )
    from tests.contract.test_model_forward_capture_driver import (
        COVERAGE_PATH,
        ENGINE_B_FEATURE_CSV_PATH,
        PVO_PATH,
        _artifact_bytes,
        _fixture_feature_source,
        _now,
        _reader,
    )

    report_path = tmp_path / "model_capture" / "latest_report.json"
    db_path = tmp_path / "model_forward.db"
    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=report_path,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(_artifact_bytes({ENGINE_B_FEATURE_CSV_PATH: feature_csv})),
        now_fn=_now(),
        git_sha_fn=lambda: "git-sha",
        feature_source=_fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == token
    assert report["decision_supported"] is False
    assert report_path.exists(), "the abort must be persisted like every other abort"
    assert ModelForwardCaptureStore(db_path).get_raw_entries(
        "2026-06-24", MODEL_PVO_SOURCE, "anything", "anything"
    ) == []


# ── 9. the serving path answers a governed 503, not a bare 500 ─────────────────────


def test_roster_audit_route_answers_a_governed_503_when_the_partition_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app.api.routes import roster as route
    from app.main import app

    async def refuse() -> dict:
        raise ip.InferencePartitionError(ip.EMPTY)

    monkeypatch.setattr(route, "run_audit_pvo", refuse)
    response = TestClient(app).get("/api/roster/audit")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error": "roster_dependency_unavailable",
        "message": ip.EMPTY,
    }


def test_engine_b_scores_route_answers_a_governed_503_when_the_partition_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app.api.routes import engine_b as route
    from app.main import app

    def refuse() -> list:
        raise ip.InferencePartitionError(ip.DUPLICATE_PLAYER)

    monkeypatch.setattr(route, "score_inference_partition", refuse)
    response = TestClient(app).get("/api/engine-b/scores")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error": "engine_b_dependency_unavailable",
        "message": ip.DUPLICATE_PLAYER,
    }
