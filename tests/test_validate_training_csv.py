"""Task 2A tests: training CSV market-leakage guard.

Tests the validate_training_csv script that blocks market-overlay column names
from entering Engine A/B training CSVs. Pattern detection is derived from:
  - PROHIBITED_COLUMNS (exact names)
  - LEAKAGE_REGEX (regex patterns)
  - market_overlay source names from SOURCE_REGISTRY (prefix patterns)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_training_csv import _violations_in_header, validate_csv


def test_clean_csv_header_produces_no_violations():
    """Columns with no market signal pass cleanly."""
    clean = ["player_id", "position", "age", "ppg_t", "games_t", "snap_share", "avg_ppg_t1_t2"]
    assert _violations_in_header(clean) == []


def test_prohibited_exact_column_name_fails():
    """Exact PROHIBITED_COLUMNS names are flagged."""
    cols = ["player_id", "ppg_t", "ktc_value", "games_t"]
    violations = _violations_in_header(cols)
    assert any("ktc_value" in v for v in violations), violations


def test_leakage_regex_pattern_fails():
    """Columns matching LEAKAGE_REGEX are flagged."""
    # LEAKAGE_REGEX covers ^ktc_, ^adp, _rank$, ^expert, ^market_, ^consensus
    for col in ("market_value", "consensus_rank", "adp_2024", "expert_ranking"):
        violations = _violations_in_header(["player_id", col])
        assert violations, f"Expected violation for column {col!r}"


def test_market_overlay_source_prefix_fails():
    """Columns with market_overlay source name as prefix are flagged."""
    # fantasycalc, ktc, dynasty_nerds, dynasty_data_lab are market_overlay in registry
    cols = ["player_id", "fantasycalc_value", "dynastynerds_score"]
    violations = _violations_in_header(cols)
    assert any("fantasycalc_value" in v for v in violations), violations


def test_validate_csv_returns_empty_for_clean_file(tmp_path):
    """validate_csv returns [] for a CSV with no market columns."""
    csv_file = tmp_path / "clean.csv"
    csv_file.write_text("player_id,position,age,ppg_t,avg_ppg_t1_t2\n1,QB,25,18.0,15.0\n")
    assert validate_csv(csv_file) == []


def test_validate_csv_returns_violation_for_prohibited_column(tmp_path):
    """validate_csv returns non-empty list when a prohibited column is present."""
    csv_file = tmp_path / "leaky.csv"
    csv_file.write_text("player_id,ktc_value,ppg_t\n1,5000,18.0\n")
    violations = validate_csv(csv_file)
    assert violations
    assert any("ktc_value" in v for v in violations)
