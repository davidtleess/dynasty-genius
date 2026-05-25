"""Task 13.1.1 tests — identity coverage matrix audit runner.

Verifies:
  - Unresolved rows are counted in review_queue, never silently dropped.
  - Duplicate non-null ID values are detected and reported.
  - Row count is preserved (total_input_rows == total_output_rows).
  - Each resolution stage fires correctly with the right fixture data.
  - Cohort coverage is aggregated per segment.
  - Coverage matrix serializes to a JSON-compatible dict.
  - Coverage gate helper works correctly.
"""
from __future__ import annotations

import json

from src.dynasty_genius.audit.identity_coverage_matrix import (
    CohortCoverage,
    IdentityAuditRow,
    ResolutionStage,
    run_audit,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _row(name: str, position: str = "WR", cohort: str = "active_starter", **kwargs) -> IdentityAuditRow:
    return IdentityAuditRow(cohort=cohort, name=name, position=position, **kwargs)


_FF_PLAYERIDS = {
    "00-0034857": {
        "gsis_id": "00-0034857",
        "player_id": "josh_allen_qb_1996",
        "sleeper_id": "4984",
        "pff_id": "16358",
    },
    "00-0036442": {
        "gsis_id": "00-0036442",
        "player_id": "justin_jefferson_wr_2000",
        "sleeper_id": "6794",
        "pff_id": "18296",
    },
}

_SLEEPER_PASSTHROUGH = {
    "4984": {"sleeper_id": "4984", "gsis_id": "00-0034857"},
    "9999": {"sleeper_id": "9999", "gsis_id": None},  # 2022+ rookie, gsis_id absent
}

_ALIAS_BRIDGE = {
    ("travis hunter", "WR", 2025): "99001",
    ("mason taylor", "TE", 2025): "99002",
}

_COMPOSITE_REGISTRY = {
    ("christian mccaffrey", "1996-06-07", "RB", 2017): "cmc_rb_1996",
}

_PROSPECT_REGISTRY = {
    ("tetairoa mcmillan", "arizona", "WR", 2025): "tetairoa_wr_2003",
}


# ---------------------------------------------------------------------------
# Core invariant: unresolved rows are counted, not dropped
# ---------------------------------------------------------------------------

def test_unresolved_rows_are_counted_not_dropped():
    rows = [
        _row("Josh Allen", "QB", gsis_id="00-0034857"),       # resolves
        _row("Mystery Player A", "WR"),                        # unresolvable
        _row("Mystery Player B", "TE"),                        # unresolvable
    ]
    results, matrix = run_audit(rows, ff_playerids=_FF_PLAYERIDS)

    assert matrix.total_input_rows == 3
    assert matrix.total_output_rows == 3
    assert matrix.row_count_preserved

    unresolved = [r for r in results if not r.resolved]
    assert len(unresolved) == 2
    for r in unresolved:
        assert r.stage == ResolutionStage.REVIEW_QUEUE


def test_all_unresolved_cohort_shows_zero_resolved():
    rows = [_row(f"Ghost {i}", cohort="historical_te") for i in range(5)]
    _, matrix = run_audit(rows)

    assert len(matrix.cohort_summary) == 1
    cov = matrix.cohort_summary[0]
    assert cov.cohort == "historical_te"
    assert cov.total == 5
    assert cov.resolved == 0
    assert cov.review_queue == 5
    assert cov.loss_rate == 1.0


# ---------------------------------------------------------------------------
# Row count preservation
# ---------------------------------------------------------------------------

def test_row_count_preserved_with_mixed_resolution():
    rows = [
        _row("Josh Allen", "QB", gsis_id="00-0034857"),
        _row("Justin Jefferson", "WR", gsis_id="00-0036442"),
        _row("No ID Player", "RB"),
        _row("Also No ID", "TE"),
        _row("Known Player", "QB", player_id="existing_pid"),
    ]
    results, matrix = run_audit(rows, ff_playerids=_FF_PLAYERIDS)

    assert matrix.total_input_rows == len(rows)
    assert matrix.total_output_rows == len(rows)
    assert matrix.row_count_preserved
    assert len(results) == len(rows)


# ---------------------------------------------------------------------------
# Duplicate non-null ID detection
# ---------------------------------------------------------------------------

def test_duplicate_gsis_id_is_detected():
    rows = [
        _row("Player A", gsis_id="00-0099999", player_id="pid_a"),
        _row("Player B", gsis_id="00-0099999", player_id="pid_b"),
    ]
    _, matrix = run_audit(rows)

    gsis_conflicts = [d for d in matrix.duplicate_conflicts if d.field == "gsis_id"]
    assert gsis_conflicts, "Expected gsis_id duplicate to be flagged"
    conflict = gsis_conflicts[0]
    assert conflict.value == "00-0099999"
    assert "Player A" in conflict.player_names
    assert "Player B" in conflict.player_names


def test_duplicate_sleeper_id_is_detected():
    rows = [
        _row("Alpha", sleeper_id="9000", player_id="alpha_pid"),
        _row("Beta", sleeper_id="9000", player_id="beta_pid"),
    ]
    _, matrix = run_audit(rows)

    sleeper_conflicts = [d for d in matrix.duplicate_conflicts if d.field == "sleeper_id"]
    assert sleeper_conflicts
    assert sleeper_conflicts[0].value == "9000"


def test_duplicate_player_id_with_different_names_is_detected():
    rows = [
        _row("Veteran Name", player_id="shared_pid"),
        _row("College Export Name", player_id="shared_pid"),
    ]
    _, matrix = run_audit(rows)

    player_id_conflicts = [
        d for d in matrix.duplicate_conflicts if d.field == "player_id"
    ]
    assert player_id_conflicts
    assert player_id_conflicts[0].value == "shared_pid"
    assert set(player_id_conflicts[0].player_names) == {
        "Veteran Name",
        "College Export Name",
    }


def test_no_false_positive_duplicates_for_null_ids():
    """Null IDs must not be flagged as duplicates across rows."""
    rows = [
        _row("X", gsis_id=None, player_id="pid_x"),
        _row("Y", gsis_id=None, player_id="pid_y"),
    ]
    _, matrix = run_audit(rows)

    gsis_conflicts = [d for d in matrix.duplicate_conflicts if d.field == "gsis_id"]
    assert not gsis_conflicts


# ---------------------------------------------------------------------------
# Resolution stage coverage
# ---------------------------------------------------------------------------

def test_stage1_direct_id():
    rows = [_row("Known Player", player_id="known_pid")]
    results, _ = run_audit(rows)
    assert results[0].stage == ResolutionStage.DIRECT_ID
    assert results[0].resolved
    assert results[0].resolved_player_id == "known_pid"


def test_stage2_ff_playerids_crosswalk():
    rows = [_row("Josh Allen", "QB", gsis_id="00-0034857")]
    results, _ = run_audit(rows, ff_playerids=_FF_PLAYERIDS)
    assert results[0].stage == ResolutionStage.FF_PLAYERIDS
    assert results[0].resolved
    assert results[0].resolved_player_id == "josh_allen_qb_1996"
    assert results[0].resolved_sleeper_id == "4984"


def test_stage3_sleeper_passthrough_with_gsis():
    rows = [_row("Josh Allen", "QB", sleeper_id="4984")]
    results, _ = run_audit(
        rows,
        ff_playerids=_FF_PLAYERIDS,
        sleeper_passthrough=_SLEEPER_PASSTHROUGH,
    )
    assert results[0].stage == ResolutionStage.SLEEPER_PASSTHROUGH
    assert results[0].resolved
    assert results[0].resolved_gsis_id == "00-0034857"


def test_stage3_sleeper_passthrough_no_gsis_still_resolves():
    """2022+ rookies: sleeper_id present but gsis_id absent — still counts as resolved."""
    rows = [_row("New Rookie", "WR", sleeper_id="9999")]
    results, _ = run_audit(
        rows,
        ff_playerids=_FF_PLAYERIDS,
        sleeper_passthrough=_SLEEPER_PASSTHROUGH,
    )
    result = results[0]
    assert result.stage == ResolutionStage.SLEEPER_PASSTHROUGH
    assert result.resolved
    assert result.resolved_gsis_id is None
    assert "propagation lag" in result.notes


def test_stage4_alias_bridge():
    rows = [_row("Travis Hunter", "WR", draft_year=2025)]
    results, _ = run_audit(rows, alias_bridge=_ALIAS_BRIDGE)
    assert results[0].stage == ResolutionStage.ALIAS_BRIDGE
    assert results[0].resolved
    assert results[0].resolved_sleeper_id == "99001"


def test_stage5_composite_name_dob():
    rows = [
        _row(
            "Christian McCaffrey", "RB",
            date_of_birth="1996-06-07",
            draft_year=2017,
        )
    ]
    results, _ = run_audit(rows, composite_registry=_COMPOSITE_REGISTRY)
    assert results[0].stage == ResolutionStage.COMPOSITE_KEY
    assert results[0].resolved
    assert results[0].resolved_player_id == "cmc_rb_1996"


def test_stage6_composite_prospect():
    rows = [
        _row("Tetairoa McMillan", "WR", college="Arizona", draft_year=2025)
    ]
    results, _ = run_audit(rows, prospect_registry=_PROSPECT_REGISTRY)
    assert results[0].stage == ResolutionStage.COMPOSITE_PROSPECT
    assert results[0].resolved
    assert results[0].resolved_player_id == "tetairoa_wr_2003"


def test_stage7_review_queue_when_no_data():
    rows = [_row("Total Mystery", "TE")]
    results, _ = run_audit(rows)
    assert results[0].stage == ResolutionStage.REVIEW_QUEUE
    assert not results[0].resolved
    assert results[0].resolved_player_id is None
    assert results[0].resolved_sleeper_id is None


# ---------------------------------------------------------------------------
# Cascade priority: earlier stage wins
# ---------------------------------------------------------------------------

def test_direct_id_wins_over_crosswalk():
    """Stage 1 fires even when gsis_id would also resolve via stage 2."""
    rows = [_row("Josh Allen", "QB", player_id="direct_pid", gsis_id="00-0034857")]
    results, _ = run_audit(rows, ff_playerids=_FF_PLAYERIDS)
    assert results[0].stage == ResolutionStage.DIRECT_ID
    assert results[0].resolved_player_id == "direct_pid"


# ---------------------------------------------------------------------------
# Cohort coverage and gates
# ---------------------------------------------------------------------------

def test_cohort_coverage_aggregates_by_segment():
    rows = [
        _row("A", cohort="active_starter", player_id="pid_a"),
        _row("B", cohort="active_starter", player_id="pid_b"),
        _row("C", cohort="active_starter"),                     # unresolved
        _row("D", cohort="historical_te", player_id="pid_d"),
        _row("E", cohort="historical_te"),                      # unresolved
    ]
    _, matrix = run_audit(rows)

    by_cohort = {c.cohort: c for c in matrix.cohort_summary}
    assert set(by_cohort) == {"active_starter", "historical_te"}

    starters = by_cohort["active_starter"]
    assert starters.total == 3
    assert starters.resolved == 2
    assert starters.review_queue == 1
    assert abs(starters.loss_rate - 1 / 3) < 1e-4

    tes = by_cohort["historical_te"]
    assert tes.total == 2
    assert tes.resolved == 1
    assert tes.loss_rate == 0.5


def test_cohort_coverage_gate_helper():
    cov = CohortCoverage(cohort="historical_te", total=100, resolved=99, review_queue=1)
    assert cov.loss_rate == 0.01
    assert cov.passes_gate(max_loss_rate=0.02)     # 13.1 spec gate
    assert not cov.passes_gate(max_loss_rate=0.005)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def test_coverage_matrix_serializes_to_json():
    rows = [
        _row("A", player_id="pid_a"),
        _row("B"),
    ]
    _, matrix = run_audit(rows, run_id="test_run_001")
    d = matrix.as_dict()
    # Must round-trip through json without error
    serialized = json.dumps(d)
    restored = json.loads(serialized)

    assert restored["run_id"] == "test_run_001"
    assert restored["timestamp"] == restored["run_timestamp"]
    assert restored["total_input_rows"] == 2
    assert restored["total_output_rows"] == 2
    assert restored["row_count_preserved"] is True
    assert len(restored["cohort_summary"]) == 1
    assert restored["cohort_summary"][0]["resolved"] == 1
    assert restored["cohort_summary"][0]["review_queue"] == 1


def test_audit_result_serializes_to_dict():
    rows = [_row("Test Player", gsis_id="00-0034857")]
    results, _ = run_audit(rows, ff_playerids=_FF_PLAYERIDS)
    d = results[0].as_dict()
    assert d["name"] == "Test Player"
    assert d["resolved"] is True
    assert d["stage"] == ResolutionStage.FF_PLAYERIDS.value


# ---------------------------------------------------------------------------
# Empty cohort
# ---------------------------------------------------------------------------

def test_empty_cohort_produces_empty_matrix():
    results, matrix = run_audit([])
    assert matrix.total_input_rows == 0
    assert matrix.total_output_rows == 0
    assert matrix.row_count_preserved
    assert matrix.cohort_summary == []
    assert matrix.duplicate_conflicts == []
    assert results == []
