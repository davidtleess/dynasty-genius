"""Tests for the Engine A v2 CFBD-only backtest.

Validates that the backtest script produces a well-formed report with
correct structure and sensible values. Does NOT assert that CFBD improves
the model — that is an empirical question answered by reading the report.

These tests skip until the backtest script has been run and the report
exists. Run:
    .venv/bin/python scripts/backtest_engine_a_cfbd_only.py

Then:
    .venv/bin/python -m pytest tests/test_engine_a_backtest.py -v
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "validation" / "engine_a_v2_cfbd_backtest_report.md"
PARTIAL_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_cfbd_partial.csv"


def _skip_if_no_report():
    return pytest.mark.skipif(
        not REPORT_PATH.exists(),
        reason="Backtest report not generated — run scripts/backtest_engine_a_cfbd_only.py first",
    )


def _parse_yaml_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a markdown file (between --- delimiters)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    yaml_lines = lines[1:end]
    result = {}
    for line in yaml_lines:
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


@pytest.mark.skipif(
    not PARTIAL_CSV.exists(),
    reason="CFBD partial CSV not generated — run scripts/enrich_training_data.py first",
)
def test_partial_csv_exists_for_backtest():
    """The CFBD partial artifact must exist before the backtest can run."""
    assert PARTIAL_CSV.exists(), (
        f"CFBD partial CSV not found at {PARTIAL_CSV}. "
        "Run scripts/enrich_training_data.py first."
    )


@_skip_if_no_report()
def test_report_exists_and_is_markdown():
    assert REPORT_PATH.exists()
    text = REPORT_PATH.read_text()
    assert len(text) > 100, "Report appears empty."
    assert "---" in text, "Report must have YAML frontmatter."


@_skip_if_no_report()
def test_report_frontmatter_has_required_fields():
    text = REPORT_PATH.read_text()
    fm = _parse_yaml_frontmatter(text)
    required = {
        "baseline_model",
        "enriched_model",
        "held_out_n",
        "metric_delta_rmse_combined",
        "metric_delta_r2_combined",
        "metric_delta_spearman_combined",
        "promotion_warranted",
        "cfbd_coverage_pct_wr",
        "cfbd_coverage_pct_rb",
        "cfbd_coverage_pct_te",
    }
    missing = required - set(fm.keys())
    assert not missing, f"Report frontmatter missing required fields: {missing}"


@_skip_if_no_report()
def test_held_out_n_is_sufficient():
    text = REPORT_PATH.read_text()
    fm = _parse_yaml_frontmatter(text)
    n = int(fm.get("held_out_n", "0"))
    assert n >= 100, (
        f"Held-out set has only {n} rows — must be >=100 for meaningful evaluation. "
        "Check is_training column in the baseline CSV."
    )


@_skip_if_no_report()
def test_metric_deltas_are_finite():
    text = REPORT_PATH.read_text()
    fm = _parse_yaml_frontmatter(text)
    for field in ("metric_delta_rmse_combined", "metric_delta_r2_combined", "metric_delta_spearman_combined"):
        raw = fm.get(field, "")
        try:
            val = float(raw)
        except ValueError:
            pytest.fail(f"Field '{field}' is not a valid float: '{raw}'")
        assert math.isfinite(val), f"Field '{field}' is not finite: {val}"


@_skip_if_no_report()
def test_promotion_warranted_is_boolean():
    text = REPORT_PATH.read_text()
    fm = _parse_yaml_frontmatter(text)
    val = fm.get("promotion_warranted", "").lower()
    assert val in ("true", "false"), (
        f"promotion_warranted must be 'true' or 'false', got: '{val}'"
    )


@_skip_if_no_report()
def test_cfbd_coverage_percentages_are_in_range():
    text = REPORT_PATH.read_text()
    fm = _parse_yaml_frontmatter(text)
    for field in ("cfbd_coverage_pct_wr", "cfbd_coverage_pct_rb", "cfbd_coverage_pct_te"):
        raw = fm.get(field, "")
        try:
            val = float(raw)
        except ValueError:
            pytest.fail(f"Field '{field}' is not a valid float: '{raw}'")
        assert 0.0 <= val <= 1.0, f"Coverage field '{field}' out of [0,1] range: {val}"


@_skip_if_no_report()
def test_report_body_contains_position_sections():
    text = REPORT_PATH.read_text()
    for pos in ("WR", "RB", "TE"):
        assert pos in text, f"Report body must include position-level results for {pos}."


@_skip_if_no_report()
def test_report_does_not_reference_phantom_pp_fields():
    """Guard that the backtest did not use imputed PP fields as features."""
    text = REPORT_PATH.read_text()
    phantom_markers = ["target_share", "breakout_age", "speed_score", "imputed_median"]
    for marker in phantom_markers:
        if marker in text.lower():
            # Allow in the 'deferred' / notes section but not in the feature list
            feature_section_idx = text.lower().find("features for model b")
            if feature_section_idx != -1:
                feature_text = text[feature_section_idx:feature_section_idx + 500].lower()
                assert marker not in feature_text, (
                    f"Phantom PP field '{marker}' found in Model B feature list. "
                    "Backtest must run CFBD-only. PP fields are deferred pending the gate."
                )
