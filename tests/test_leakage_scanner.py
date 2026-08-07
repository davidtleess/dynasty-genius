"""Leakage guard tests — now against the governed, network-free module.

Previously imported from the legacy mixed enrichment script, retired on 2026-08-07
because it combined this guard with two unsanctioned acquisition routes. The retired
path is named in the retirement contract test, not repeated here.
The guard's behaviour is unchanged; only its home and its report destination moved.
"""

import json

import pandas as pd
import pytest

from src.dynasty_genius.models.leakage import check_leakage


def test_check_leakage_clean_df(tmp_path):
    df = pd.DataFrame(
        {"gsis_id": ["1"], "pfr_player_name": ["Player A"], "dominator_rating": [0.3]}
    )
    report_path = tmp_path / "leakage_violation_report.json"
    check_leakage(df, report_path=report_path)
    assert not report_path.exists(), "a passing check must write nothing"


def test_check_leakage_prohibited_columns(tmp_path):
    df = pd.DataFrame(
        {"gsis_id": ["1"], "ktc_value": [1000], "pfr_player_name": ["Player A"]}
    )
    report_path = tmp_path / "leakage_violation_report.json"

    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        check_leakage(df, report_path=report_path)

    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "ktc_value" in report["offending_columns"]


def test_check_leakage_regex_columns(tmp_path):
    df = pd.DataFrame(
        {"gsis_id": ["1"], "adp_sleeper": [10.5], "pfr_player_name": ["Player A"]}
    )
    report_path = tmp_path / "leakage_violation_report.json"

    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        check_leakage(df, report_path=report_path)

    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "adp_sleeper" in report["offending_columns"]


def test_report_path_is_required_and_explicit(tmp_path):
    """The retired script wrote to a fixed repo-root path as a side effect."""
    df = pd.DataFrame({"gsis_id": ["1"], "ktc_value": [1000]})
    with pytest.raises(TypeError):
        check_leakage(df)  # type: ignore[call-arg]
