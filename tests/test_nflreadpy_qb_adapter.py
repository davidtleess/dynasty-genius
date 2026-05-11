from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.dynasty_genius.models.engine_a_contract import QB_CONTEXT_COLUMNS


def test_fetch_qb_nfl_stats_returns_stable_none_shape_without_source_data():
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import fetch_qb_nfl_stats

    with patch("src.dynasty_genius.adapters.nflreadpy_qb_adapter.load_pbp") as load_pbp:
        load_pbp.return_value = None
        result = fetch_qb_nfl_stats("00-0031234", [2024])

    assert set(result) == QB_CONTEXT_COLUMNS
    assert all(value is None for value in result.values())


def test_fetch_qb_nfl_stats_aggregates_dropback_telemetry():
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import fetch_qb_nfl_stats

    pbp = pd.DataFrame(
        [
            {
                "passer_player_id": "00-0031234",
                "qb_dropback": 1,
                "pass_attempt": 1,
                "epa": 0.40,
                "cpoe": 4.0,
            },
            {
                "passer_player_id": "00-0031234",
                "qb_dropback": 1,
                "pass_attempt": 0,
                "epa": -0.10,
                "cpoe": None,
            },
            {
                "passer_player_id": "00-0099999",
                "qb_dropback": 1,
                "pass_attempt": 1,
                "epa": 10.0,
                "cpoe": 50.0,
            },
        ]
    )

    with patch("src.dynasty_genius.adapters.nflreadpy_qb_adapter.load_pbp") as load_pbp:
        load_pbp.return_value = pbp
        result = fetch_qb_nfl_stats("00-0031234", [2024])

    assert result["dropback_count"] == 2
    assert result["pass_attempts"] == 1
    assert result["epa_per_dropback"] == pytest.approx(0.15)
    assert result["cpoe"] == pytest.approx(4.0)
    assert result["dakota"] == pytest.approx(0.117)


def test_fetch_qb_nfl_stats_returns_none_without_matching_dropbacks():
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import fetch_qb_nfl_stats

    pbp = pd.DataFrame(
        [{"passer_player_id": "00-0031234", "qb_dropback": 0, "pass_attempt": 0, "epa": 1.0, "cpoe": 9.0}]
    )

    with patch("src.dynasty_genius.adapters.nflreadpy_qb_adapter.load_pbp") as load_pbp:
        load_pbp.return_value = pbp
        result = fetch_qb_nfl_stats("00-0031234", [2024])

    assert result["dropback_count"] == 0
    assert result["pass_attempts"] == 0
    assert result["epa_per_dropback"] is None
    assert result["cpoe"] is None
    assert result["dakota"] is None


def test_fetch_qb_nfl_stats_uses_only_qb_context_fields():
    from src.dynasty_genius.adapters.nflreadpy_qb_adapter import fetch_qb_nfl_stats

    pbp = pd.DataFrame(
        [{"passer_player_id": "00-0031234", "qb_dropback": 1, "pass_attempt": 1, "epa": 0.2, "cpoe": 2.0}]
    )

    with patch("src.dynasty_genius.adapters.nflreadpy_qb_adapter.load_pbp") as load_pbp:
        load_pbp.return_value = pbp
        result = fetch_qb_nfl_stats("00-0031234", [2024, 2025])

    assert set(result) == QB_CONTEXT_COLUMNS
    assert "completion_pct" not in result
    assert "yards_per_attempt" not in result
    load_pbp.assert_called_once_with([2024, 2025])
