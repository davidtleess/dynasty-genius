"""Task 13.1.3 tests: block unresolved PFF/college rows from materialization."""
from __future__ import annotations

import pytest

from src.dynasty_genius.audit.identity_materialization_gate import (
    IdentityMaterializationRow,
    UnresolvedIdentityGateError,
    assert_identity_materialization_allowed,
)


def test_pff_rows_with_player_id_pass_gate():
    rows = [
        IdentityMaterializationRow(
            row_id="pff_export_2025_te.csv:42",
            source="pff",
            player_id="mason_taylor_te_2025",
            identity_status="RESOLVED_DETERMINISTIC",
        )
    ]

    assert_identity_materialization_allowed(rows)


def test_unresolved_pff_rows_are_blocked_from_training_materialization():
    rows = [
        IdentityMaterializationRow(
            row_id="pff_export_2025_te.csv:42",
            source="pff",
            player_id=None,
            identity_status="PENDING",
        )
    ]

    with pytest.raises(UnresolvedIdentityGateError) as excinfo:
        assert_identity_materialization_allowed(rows)

    assert "pff_export_2025_te.csv:42" in str(excinfo.value)
    assert "PENDING" in str(excinfo.value)


def test_unresolved_college_rows_are_blocked_from_training_materialization():
    rows = [
        IdentityMaterializationRow(
            row_id="cfbd_export.csv:7",
            source="cfbd",
            player_id=None,
            identity_status="INSUFFICIENT_DATA",
        )
    ]

    with pytest.raises(UnresolvedIdentityGateError, match="cfbd_export.csv:7"):
        assert_identity_materialization_allowed(rows)


def test_review_only_fuzzy_candidate_is_not_training_eligible():
    rows = [
        IdentityMaterializationRow(
            row_id="pff_export_2025_te.csv:99",
            source="pff",
            player_id="possible_te_2025",
            identity_status="FUZZY_REVIEW_CANDIDATE",
        )
    ]

    with pytest.raises(UnresolvedIdentityGateError, match="FUZZY_REVIEW_CANDIDATE"):
        assert_identity_materialization_allowed(rows)


def test_unresolved_non_college_context_row_does_not_block_training_gate():
    rows = [
        IdentityMaterializationRow(
            row_id="sleeper_context.csv:1",
            source="sleeper",
            player_id=None,
            identity_status="PENDING",
        )
    ]

    assert_identity_materialization_allowed(rows)
