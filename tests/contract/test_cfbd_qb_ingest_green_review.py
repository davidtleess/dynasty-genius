"""Adversarial review checks for the CFBD QB GREEN implementation.

These checks exercise boundary cases that the original G1-G7 RED did not
encode.  They make no live API requests.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

import scripts.build_w2b_cfbd as cfbd_builder
from scripts.build_w2b_cfbd import compute_qb_cfbd_features
from src.dynasty_genius.adapters.cfbd_qb_adapter import (
    CfbdRequestError,
    fetch_qb_college_stats,
    normalize_qb_payloads,
)
from src.dynasty_genius.adapters.cfbd_receiving_adapter import (
    fetch_team_pass_attempts,
)
from src.dynasty_genius.capture.cfbd_foundation_refresh import (
    _validate_curated,
    _validate_json_cache,
)

PATCH_GET = "src.dynasty_genius.adapters.cfbd_qb_adapter.httpx.get"


def _response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _raw_payloads(*, search, passing):
    return {
        "player_search": search,
        "passing": passing,
        "rushing": [],
        "ppa": [],
        "wepa": [],
        "team": [],
    }


def _passing_rows(player_id: str, *, ypa: float = 8.9):
    values = {
        "PCT": 0.652,
        "YPA": ypa,
        "TD": 30,
        "INT": 8,
        "YDS": 3000,
        "ATT": 400,
    }
    return [
        {
            "season": 2020,
            "playerId": player_id,
            "player": "Wrong Quarterback",
            "team": "Clemson",
            "statType": stat_type,
            "stat": value,
        }
        for stat_type, value in values.items()
    ]


def test_g1_unresolved_identity_refuses_even_one_unambiguous_stat_vector():
    raw = _raw_payloads(search=[], passing=_passing_rows("wrong-1"))

    result = normalize_qb_payloads(raw, "Trevor Lawrence", "Clemson")

    assert result["completion_pct"] is None
    assert result["yards_per_attempt"] is None
    assert result["td_int_ratio"] is None
    assert result["pass_attempts"] is None


def test_g1_exact_name_on_the_wrong_team_is_not_a_resolved_identity():
    wrong_team_rows = [
        {**row, "player": "Trevor Lawrence", "team": "Alabama"}
        for row in _passing_rows("wrong-team-1")
    ]
    raw = _raw_payloads(
        search=[
            {
                "id": "wrong-team-1",
                "name": "Trevor Lawrence",
                "team": "Alabama",
                "position": "QB",
            }
        ],
        passing=wrong_team_rows,
    )

    result = normalize_qb_payloads(raw, "Trevor Lawrence", "Clemson")

    assert result["completion_pct"] is None
    assert result["yards_per_attempt"] is None
    assert result["td_int_ratio"] is None
    assert result["pass_attempts"] is None


def test_g1_builder_normalizes_college_alias_before_strict_team_resolution(tmp_path):
    empty_stats = {
        "completion_pct": None,
        "yards_per_attempt": None,
        "td_int_ratio": None,
        "sack_rate": None,
        "pass_attempts": None,
    }
    with patch.object(
        cfbd_builder,
        "fetch_qb_college_stats",
        return_value=empty_stats,
    ) as fetch:
        compute_qb_cfbd_features(
            {
                "season": "2015",
                "pfr_player_name": "Jameis Winston",
                "college": "Florida St.",
            },
            api_key="test-key",
            cache_dir=tmp_path,
        )

    assert fetch.call_args.kwargs["college_team"] == "Florida State"


@patch(PATCH_GET, return_value=_response({"provider": "schema changed"}))
def test_g2_non_list_provider_payload_is_a_schema_failure_not_no_data(_):
    with pytest.raises(CfbdRequestError, match="CFBD.*request|request.*CFBD"):
        fetch_qb_college_stats(
            "Trevor Lawrence",
            2020,
            api_key="test-key",
            college_team="Clemson",
        )


def _qb_row(gsis_id: str, season: str) -> dict[str, str]:
    values = {
        "qb_completion_pct_final": "0.652",
        "qb_yards_per_attempt_final": "8.9",
        "qb_td_int_ratio_final": "3.75",
        "qb_sack_rate_final": "0.04",
    }
    row = {
        "gsis_id": gsis_id,
        "position": "QB",
        "season": season,
        "w2b_cfbd_degraded": "0",
    }
    for field, value in values.items():
        row[field] = value
        row[f"{field}_missing"] = "0"
        row[f"{field}_source"] = "cfbd"
    return row


def _write_curated(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_g3_equal_vectors_in_different_seasons_are_not_a_season_collision(tmp_path):
    curated = tmp_path / "curated.csv"
    _write_curated(curated, [_qb_row("qb-1", "2020"), _qb_row("qb-2", "2021")])

    quality = _validate_curated(curated)

    assert quality["row_count"] == 2


def test_g6_raw_payloads_survive_a_normalization_failure(tmp_path):
    raw = _raw_payloads(
        search=[
            {
                "id": "target-1",
                "name": "Trevor Lawrence",
                "team": "Clemson",
                "position": "QB",
            }
        ],
        passing=_passing_rows("target-1"),
    )
    row = {
        "season": "2021",
        "pfr_player_name": "Trevor Lawrence",
        "college": "Clemson",
    }

    with (
        patch(
            "src.dynasty_genius.adapters.cfbd_qb_adapter._fetch_raw_payloads",
            return_value=raw,
        ),
        patch(
            "src.dynasty_genius.adapters.cfbd_qb_adapter.normalize_qb_payloads",
            side_effect=ValueError("normalization defect"),
        ),
        pytest.raises(ValueError, match="normalization defect"),
    ):
        compute_qb_cfbd_features(row, api_key="test-key", cache_dir=tmp_path)

    snapshots = sorted(tmp_path.glob("qb_raw_*.json"))
    assert snapshots, "the fetched response must be durable before normalization starts"
    assert any(
        _passing_rows("target-1")[0]
        in json.loads(snapshot.read_text(encoding="utf-8"))
        for snapshot in snapshots
    )


def test_g6_refresh_validator_accepts_every_cache_family_the_builder_emits(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(cfbd_builder, "CACHE_DIR", tmp_path)
    cfbd_builder._save_tpa_cache(
        "Clemson",
        2020,
        [{"team": "Clemson", "statName": "passAttempts", "statValue": 430}],
    )
    cfbd_builder._save_games_raw_cache(
        "Clemson", 2020, [{"id": 1, "homeTeam": "Clemson"}]
    )

    count, _ = _validate_json_cache(tmp_path)

    assert count == 2


def test_g6_games_cache_preserves_the_unmodified_provider_response(
    tmp_path, monkeypatch
):
    provider_payload = [
        {"id": 1, "season": 2020, "homeTeam": "Clemson", "awayTeam": "Miami"},
        {"id": 2, "season": 2020, "homeTeam": "Duke", "awayTeam": "Clemson"},
    ]
    monkeypatch.setattr(cfbd_builder, "CACHE_DIR", tmp_path)

    with patch.object(cfbd_builder.httpx, "get", return_value=_response(provider_payload)):
        count = cfbd_builder.load_team_games_count(
            "Clemson", 2020, api_key="test-key", force_fetch=True
        )

    assert count == 2
    snapshot = json.loads(
        (tmp_path / "games_count_clemson_2020.json").read_text(encoding="utf-8")
    )
    assert snapshot == provider_payload


def test_g6_tpa_cache_preserves_the_unmodified_provider_response(
    tmp_path, monkeypatch
):
    provider_payload = [
        {
            "team": "Clemson",
            "year": 2020,
            "statName": "passAttempts",
            "statValue": 430,
        },
        {
            "team": "Clemson",
            "year": 2020,
            "statName": "sacksAllowed",
            "statValue": 18,
        },
    ]
    monkeypatch.setattr(cfbd_builder, "CACHE_DIR", tmp_path)

    cfbd_builder._save_tpa_cache("Clemson", 2020, provider_payload)

    snapshot = json.loads(
        (tmp_path / "tpa_clemson_2020.json").read_text(encoding="utf-8")
    )
    assert snapshot == provider_payload
    hit, value = cfbd_builder._load_tpa_cache("Clemson", 2020)
    assert hit is True
    assert value == 430.0


def test_g2_tpa_transport_failure_is_not_cached_as_no_data():
    raw_sink = []
    with (
        patch(
            "src.dynasty_genius.adapters.cfbd_receiving_adapter.httpx.get",
            side_effect=httpx.TimeoutException("timed out"),
        ),
        pytest.raises(RuntimeError),
    ):
        fetch_team_pass_attempts(
            "Clemson", 2020, api_key="test-key", raw_sink=raw_sink
        )

    assert raw_sink == []


def test_g2_games_transport_failure_is_not_persisted_as_an_empty_response(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(cfbd_builder, "CACHE_DIR", tmp_path)

    with (
        patch.object(
            cfbd_builder.httpx,
            "get",
            side_effect=httpx.TimeoutException("timed out"),
        ),
        pytest.raises(RuntimeError),
    ):
        cfbd_builder.load_team_games_count(
            "Clemson", 2020, api_key="test-key", force_fetch=True
        )

    assert not (tmp_path / "games_count_clemson_2020.json").exists()
