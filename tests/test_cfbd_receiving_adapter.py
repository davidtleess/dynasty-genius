"""Tests for Phase 16.2 CFBD receiving adapter."""
from unittest.mock import patch, MagicMock
import pytest
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
    normalize_college_name,
)


def _mock_response(data: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = data
    return mock


def test_fetch_returns_pass_attempts(monkeypatch):
    stat_rows = [
        {"statName": "passAttempts", "statValue": "450"},
        {"statName": "rushingYards", "statValue": "1800"},
    ]
    with patch("httpx.get", return_value=_mock_response(stat_rows)):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result == pytest.approx(450.0)


def test_fetch_returns_none_when_stat_missing(monkeypatch):
    stat_rows = [{"statName": "rushingYards", "statValue": "1800"}]
    with patch("httpx.get", return_value=_mock_response(stat_rows)):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_fetch_returns_none_on_empty_response():
    with patch("httpx.get", return_value=_mock_response([])):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_fetch_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    result = fetch_team_pass_attempts("Alabama", 2022, api_key="")
    assert result is None


def test_fetch_returns_none_on_http_error():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("HTTP 401")
    with patch("httpx.get", return_value=mock):
        result = fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    assert result is None


def test_normalize_college_name_common_cases():
    assert normalize_college_name("Florida St.") == "Florida State"
    assert normalize_college_name("Ohio St.") == "Ohio State"
    assert normalize_college_name("Michigan St.") == "Michigan State"
    assert normalize_college_name("S JOSE ST") == "San Jose State"
    assert normalize_college_name("FAU") == "Florida Atlantic"
    assert normalize_college_name("LSU") == "LSU"


def test_normalize_college_name_passthrough():
    assert normalize_college_name("Alabama") == "Alabama"
    assert normalize_college_name("Oregon") == "Oregon"


def test_fetch_hits_correct_endpoint():
    stat_rows = [{"statName": "passAttempts", "statValue": "400"}]
    with patch("httpx.get", return_value=_mock_response(stat_rows)) as mock_get:
        fetch_team_pass_attempts("Alabama", 2022, api_key="test-key")
    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/stats/season"), (
        f"Expected URL ending in /stats/season, got: {called_url}"
    )
