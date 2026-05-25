"""Task 10.2 unit tests: FantasyCalc snapshot script.

Verifies script behavior using mocked HTTP responses.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import httpx
import pytest

from scripts.snapshot_fantasycalc import snapshot_fantasycalc
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


@pytest.fixture
def mock_fc_response():
    return [
        {
            "player": {"name": "Bijan Robinson", "sleeperId": "9509", "position": "RB"},
            "value": 10500,
            "overallRank": 1,
            "positionRank": 1,
            "trend30Day": -50
        },
        {
            "player": {"name": "No Sleeper ID", "sleeperId": None, "position": "WR"},
            "value": 5000,
            "overallRank": 50,
            "positionRank": 10,
            "trend30Day": 0
        },
        {
            "player": {"name": "CeeDee Lamb", "sleeperId": "6786", "position": "WR"},
            "value": 9000,
            "overallRank": 5,
            "positionRank": 1,
            "trend30Day": 100
        }
    ]


# ── Test 1: Successful API response writes correct number of rows ─────────────

def test_snapshot_success_writes_rows(tmp_path, mock_fc_response):
    db_path = tmp_path / "test.db"
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"players": mock_fc_response}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        count = snapshot_fantasycalc(db_path=db_path)
        
        # Should skip the one with sleeperId: None
        assert count == 2
        
        store = MarketSnapshotStore(db_path=db_path)
        coverage = store.get_coverage()
        assert coverage["n_rows"] == 2
        
        snapshot = store.get_snapshot(coverage["latest_date"])
        assert len(snapshot) == 2


# ── Test 2: sleeper_id is populated from sleeperId ────────────────────────────

def test_snapshot_populates_sleeper_id(tmp_path, mock_fc_response):
    db_path = tmp_path / "test.db"
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_fc_response  # List format
        mock_get.return_value = mock_response

        snapshot_fantasycalc(db_path=db_path)
        
        store = MarketSnapshotStore(db_path=db_path)
        rows = store.get_snapshot(datetime.now().strftime("%Y-%m-%d"))
        ids = {r["sleeper_id"] for r in rows}
        assert ids == {"9509", "6786"}


# ── Test 3: source is fc_native on all rows ───────────────────────────────────

def test_snapshot_sets_source_fc_native(tmp_path, mock_fc_response):
    db_path = tmp_path / "test.db"
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_fc_response
        mock_get.return_value = mock_response

        snapshot_fantasycalc(db_path=db_path)
        
        store = MarketSnapshotStore(db_path=db_path)
        rows = store.get_snapshot(datetime.now().strftime("%Y-%m-%d"))
        for row in rows:
            assert row["source"] == "fc_native"


# ── Test 4: On HTTP error, exits with code 1 and writes zero rows ─────────────

def test_snapshot_handles_http_error(tmp_path):
    db_path = tmp_path / "test.db"
    with patch("httpx.get", side_effect=httpx.HTTPError("API Down")):
        with pytest.raises(SystemExit) as excinfo:
            snapshot_fantasycalc(db_path=db_path)
        assert excinfo.value.code == 1
        
        store = MarketSnapshotStore(db_path=db_path)
        assert store.get_coverage()["n_rows"] == 0


# ── Test 5: Skips rows where sleeperId is None ────────────────────────────────

def test_snapshot_skips_none_sleeper_id(tmp_path, mock_fc_response):
    db_path = tmp_path / "test.db"
    # Ensure our mock has the None entry (fixture does)
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_fc_response
        mock_get.return_value = mock_response

        count = snapshot_fantasycalc(db_path=db_path)
        assert count == 2  # 3 input - 1 none = 2

from datetime import datetime
