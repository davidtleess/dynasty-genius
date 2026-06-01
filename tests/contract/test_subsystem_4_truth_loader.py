"""Subsystem 4 v2 draft-truth loader contract tests."""
from __future__ import annotations

from typing import get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from src.dynasty_genius.identity import prospect_nfl_bridge as bridge


def test_truth_load_diagnostics_model_contract():
    diagnostics_cls = bridge.NflTruthLoadDiagnostics

    assert issubclass(diagnostics_cls, BaseModel)
    assert diagnostics_cls.model_config.get("extra") == "forbid"

    expected_int_fields = {
        "truth_rows_loaded",
        "skipped_missing_gsis_id",
        "skipped_bad_pick",
        "skipped_bad_round",
        "skipped_missing_name",
        "skipped_missing_position",
        "skipped_missing_team",
    }
    assert set(diagnostics_cls.model_fields) == {
        *expected_int_fields,
        "required_columns_seen",
    }

    diagnostics = diagnostics_cls()
    for field_name in expected_int_fields:
        field = diagnostics_cls.model_fields[field_name]
        assert field.annotation is int
        assert getattr(diagnostics, field_name) == 0

    columns_field = diagnostics_cls.model_fields["required_columns_seen"]
    assert get_origin(columns_field.annotation) is list
    assert get_args(columns_field.annotation) == (str,)
    assert diagnostics.required_columns_seen == []

    with pytest.raises(ValidationError):
        diagnostics_cls.model_validate({"unexpected_field": 1})


def test_truth_load_result_model_contract():
    result_cls = bridge.NflreadrTruthLoadResult
    diagnostics_cls = bridge.NflTruthLoadDiagnostics

    assert issubclass(result_cls, BaseModel)

    rows_field = result_cls.model_fields["rows"]
    assert get_origin(rows_field.annotation) is list
    assert get_args(rows_field.annotation) == (bridge.NflTruthRow,)

    diagnostics_field = result_cls.model_fields["diagnostics"]
    assert diagnostics_field.annotation is diagnostics_cls

    truth_row = bridge.NflTruthRow(
        gsis_id="00-0000001",
        pfr_id=None,
        full_name="Example Player",
        normalized_name="example player",
        position="QB",
        college="Example U",
        draft_year=2024,
        draft_pick_no=1,
        draft_round=1,
        nfl_team="CHI",
        fetched_at="2026-01-01T00:00:00Z",
    )
    result = result_cls(rows=[truth_row], diagnostics=diagnostics_cls())

    assert result.rows == [truth_row]
    assert isinstance(result.diagnostics, diagnostics_cls)


def test_truth_loader_exceptions_are_value_errors():
    assert issubclass(bridge.NflreadrSchemaDriftError, ValueError)
    assert issubclass(bridge.NflreadrSourceContaminationError, ValueError)
    assert issubclass(bridge.NflreadrEmptyTruthError, ValueError)
