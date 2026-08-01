"""Failing RED contract for the CFBD QB ingest and publication repair.

These tests encode the G1-G7 boundary agreed by the Codex review lane and
Claude source-pipeline lane on 2026-08-01. They make no live API requests.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from scripts.build_w2b_cfbd import compute_qb_cfbd_features
from src.dynasty_genius.adapters.cfbd_qb_adapter import fetch_qb_college_stats
from src.dynasty_genius.capture.cfbd_foundation_refresh import (
    CfbdRefreshError,
    _validate_curated,
    _validate_json_cache,
    run_cfbd_foundation_refresh,
)

PATCH_GET = "src.dynasty_genius.adapters.cfbd_qb_adapter.httpx.get"
NOW = datetime(2026, 8, 1, 20, 0, tzinfo=timezone.utc)


def _response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _player_rows(
    *,
    player_id: str,
    player: str,
    team: str,
    pct: float,
    ypa: float,
    td: int,
    interceptions: int,
    attempts: int,
):
    values = {
        "PCT": pct,
        "YPA": ypa,
        "TD": td,
        "INT": interceptions,
        "YDS": 3000,
        "ATT": attempts,
    }
    return [
        {
            "season": 2020,
            "playerId": player_id,
            "player": player,
            "position": "QB",
            "team": team,
            "category": "passing",
            "statType": stat_type,
            "stat": value,
        }
        for stat_type, value in values.items()
    ]


WRONG_ROWS = _player_rows(
    player_id="wrong-1",
    player="Wrong Quarterback",
    team="Clemson",
    pct=0.401,
    ypa=4.1,
    td=4,
    interceptions=10,
    attempts=200,
)
TARGET_ROWS = _player_rows(
    player_id="target-1",
    player="Trevor Lawrence",
    team="Clemson",
    pct=0.652,
    ypa=8.9,
    td=30,
    interceptions=8,
    attempts=400,
)


def _identity_router(url, **kwargs):
    params = kwargs.get("params", {})
    if "/player/search" in url:
        return _response(
            [
                {
                    "id": "target-1",
                    "name": "Trevor Lawrence",
                    "team": "Clemson",
                    "position": "QB",
                }
            ]
        )
    if "/stats/player/season" in url:
        if params.get("category") == "passing":
            return _response(WRONG_ROWS + TARGET_ROWS)
        return _response([])
    if "/ppa/players/season" in url:
        return _response(
            [
                {
                    "id": "wrong-1",
                    "name": "Wrong Quarterback",
                    "team": "Clemson",
                    "averagePPA": {"all": -0.5},
                },
                {
                    "id": "target-1",
                    "name": "Trevor Lawrence",
                    "team": "Clemson",
                    "averagePPA": {"all": 0.5},
                },
            ]
        )
    if "/wepa/players/passing" in url:
        return _response(
            [
                {
                    "athleteId": "wrong-1",
                    "athleteName": "Wrong Quarterback",
                    "team": "Clemson",
                    "wepa": -10.0,
                },
                {
                    "athleteId": "target-1",
                    "athleteName": "Trevor Lawrence",
                    "team": "Clemson",
                    "wepa": 42.0,
                },
            ]
        )
    if "/stats/team/season" in url:
        return _response(
            [
                {"statName": "passAttempts", "statValue": 430},
                {"statName": "sacksAllowed", "statValue": 18},
                {"statName": "netPassingYards", "statValue": 3200},
            ]
        )
    return _response([])


@patch(PATCH_GET, side_effect=_identity_router)
def test_g1_binds_every_feature_family_to_the_resolved_player(_):
    result = fetch_qb_college_stats(
        "Trevor Lawrence", 2020, api_key="test-key", college_team="Clemson"
    )

    assert result["yards_per_attempt"] == pytest.approx(8.9)
    assert result["td_int_ratio"] == pytest.approx(30 / 8)
    assert result["pass_attempts"] == 400
    assert result["ppa"] == pytest.approx(0.5)
    assert result["wepa"] == pytest.approx(42.0)


@patch(PATCH_GET, side_effect=_identity_router)
def test_g4_provider_fractional_completion_pct_is_not_divided_again(_):
    result = fetch_qb_college_stats(
        "Trevor Lawrence", 2020, api_key="test-key", college_team="Clemson"
    )

    assert result["completion_pct"] == pytest.approx(0.652)


@patch(PATCH_GET, side_effect=_identity_router)
def test_g7_uses_only_provider_supported_query_parameters(mock_get):
    fetch_qb_college_stats(
        "Trevor Lawrence", 2020, api_key="test-key", college_team="Clemson"
    )

    allowed = {
        "/player/search": {"searchTerm", "year", "team", "position"},
        "/stats/player/season": {
            "year",
            "conference",
            "team",
            "startWeek",
            "endWeek",
            "seasonType",
            "category",
        },
        "/ppa/players/season": {
            "year",
            "conference",
            "team",
            "position",
            "playerId",
            "threshold",
            "excludeGarbageTime",
        },
        "/wepa/players/passing": {"year", "team", "conference", "position"},
        "/stats/team/season": {
            "year",
            "team",
            "conference",
            "startWeek",
            "endWeek",
        },
    }
    seen_search = False
    for call in mock_get.call_args_list:
        endpoint = next(
            (path for path in allowed if path in call.args[0]),
            None,
        )
        assert endpoint is not None, f"unexpected CFBD endpoint: {call.args[0]}"
        params = set(call.kwargs.get("params", {}))
        assert params <= allowed[endpoint], (
            f"unsupported params for {endpoint}: {sorted(params - allowed[endpoint])}"
        )
        seen_search = seen_search or endpoint == "/player/search"
    assert seen_search, "player identity must be resolved before stat extraction"


@patch(PATCH_GET, side_effect=httpx.TimeoutException("timed out"))
def test_g2_transport_failure_is_not_collapsed_into_player_not_found(_):
    with pytest.raises(RuntimeError, match="CFBD.*request|request.*CFBD"):
        fetch_qb_college_stats(
            "Trevor Lawrence", 2020, api_key="test-key", college_team="Clemson"
        )


@patch(PATCH_GET, side_effect=_identity_router)
def test_g6_qb_cache_preserves_source_response_before_normalization(_, tmp_path):
    compute_qb_cfbd_features(
        {
            "season": "2021",
            "pfr_player_name": "Trevor Lawrence",
            "college": "Clemson",
        },
        api_key="test-key",
        cache_dir=tmp_path,
    )

    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(tmp_path.glob("*.json"))
    ]
    raw_rows = [
        row
        for payload in payloads
        if isinstance(payload, list)
        for row in payload
        if isinstance(row, dict)
    ]
    assert TARGET_ROWS[0] in raw_rows, (
        "the cache must contain the unmodified player-stat response before "
        "normalization; a normalized feature dict is not a raw snapshot"
    )


def _write_curated(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _qb_row(
    gsis_id: str,
    *,
    completion_pct: str = "0.652",
    ypa: str = "8.9",
    td_int: str = "3.75",
    sack_rate: str = "0.04",
) -> dict[str, str]:
    values = {
        "qb_completion_pct_final": completion_pct,
        "qb_yards_per_attempt_final": ypa,
        "qb_td_int_ratio_final": td_int,
        "qb_sack_rate_final": sack_rate,
    }
    row = {
        "gsis_id": gsis_id,
        "position": "QB",
        "season": "2021",
        "w2b_cfbd_degraded": "0",
    }
    for field, value in values.items():
        row[field] = value
        row[f"{field}_missing"] = "0" if value else "1"
        row[f"{field}_source"] = "cfbd" if value else ""
    return row


def test_g3_identical_complete_qb_vectors_refuse_publication(tmp_path):
    curated = tmp_path / "curated.csv"
    _write_curated(curated, [_qb_row("qb-1"), _qb_row("qb-2")])

    with pytest.raises(CfbdRefreshError, match="collision|identical"):
        _validate_curated(curated)


def test_g4_implausible_qualifying_completion_pct_refuses_publication(tmp_path):
    curated = tmp_path / "curated.csv"
    _write_curated(curated, [_qb_row("qb-1", completion_pct="0.00594")])

    with pytest.raises(CfbdRefreshError, match="completion|range|plausib"):
        _validate_curated(curated)


def test_g5_zero_coverage_declared_qb_family_refuses_publication(tmp_path):
    curated = tmp_path / "curated.csv"
    _write_curated(curated, [_qb_row("qb-1", sack_rate="")])

    with pytest.raises(CfbdRefreshError, match="sack|coverage|0%"):
        _validate_curated(curated)


@pytest.mark.parametrize(
    "name,payload",
    [
        ("qb_stats_example_2020.json", {"completion_pct": 0.652}),
        ("tpa_example_2020.json", 430.0),
    ],
)
def test_g6_normalized_or_scalar_derivatives_do_not_qualify_as_raw(
    tmp_path, name, payload
):
    (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CfbdRefreshError, match="raw|normalized|scalar"):
        _validate_json_cache(tmp_path)


def test_g5_material_feature_coverage_regression_refuses_publication(tmp_path):
    input_path = tmp_path / "input.csv"
    source_root = tmp_path / "source"
    baseline_rows = [
        _qb_row("qb-1", ypa="8.9"),
        _qb_row("qb-2", ypa="8.1"),
        _qb_row("qb-3", ypa="7.4"),
        _qb_row("qb-4", ypa="7.0"),
    ]
    _write_curated(input_path, baseline_rows)

    def baseline_builder(output_path, raw_cache_dir):
        (raw_cache_dir / "player_passing_2020.json").write_text(
            json.dumps(TARGET_ROWS), encoding="utf-8"
        )

    run_cfbd_foundation_refresh(
        source_root=source_root,
        input_path=input_path,
        builder=baseline_builder,
        now_fn=lambda: NOW,
    )

    def regressed_builder(output_path, raw_cache_dir):
        rows = [baseline_rows[0]] + [
            _qb_row(f"qb-{index}", ypa="") for index in range(2, 5)
        ]
        _write_curated(output_path, rows)
        payload = [*TARGET_ROWS, {"capture": "changed"}]
        (raw_cache_dir / "player_passing_2020.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    with pytest.raises(CfbdRefreshError, match="coverage|regress|retention"):
        run_cfbd_foundation_refresh(
            source_root=source_root,
            input_path=input_path,
            builder=regressed_builder,
            now_fn=lambda: datetime(2026, 8, 1, 20, 1, tzinfo=timezone.utc),
        )
