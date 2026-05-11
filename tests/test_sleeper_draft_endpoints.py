"""Tests for Sleeper draft API endpoints added in Task 1."""
import asyncio
from unittest.mock import AsyncMock, patch


def test_get_league_drafts_returns_list():
    from app.data.sleeper import get_league_drafts
    mock_data = [{"draft_id": "abc123", "status": "drafting", "created": 1715000000}]
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=mock_data)):
        result = asyncio.run(get_league_drafts("league_999"))
    assert result == mock_data


def test_get_league_drafts_raises_on_none():
    import pytest
    from app.data.sleeper import get_league_drafts
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=None)):
        try:
            asyncio.run(get_league_drafts("league_999"))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No drafts found" in str(e)


def test_get_draft_picks_returns_list():
    from app.data.sleeper import get_draft_picks
    mock_data = [{"pick_no": 1, "player_id": "5849", "picked_by": "user1"}]
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=mock_data)):
        result = asyncio.run(get_draft_picks("draft_abc"))
    assert result == mock_data


def test_get_draft_picks_returns_empty_list_on_none():
    from app.data.sleeper import get_draft_picks
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=None)):
        result = asyncio.run(get_draft_picks("draft_abc"))
    assert result == []
