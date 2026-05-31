"""Step-5b.2 G3 trust contracts.

These tests intentionally describe the hardened contract before the GREEN exists:
clean deterministic identity joins, fail-loud id-map behavior, honest
DynastyProcess labeling, diagnostic rank derivation, temporal pairing, and the
anti-confusion invariant that G3 NDCG is computed from values rather than stored
archive ranks.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts import run_backtest
from src.dynasty_genius.eval import backtest_harness
from src.dynasty_genius.eval.backtest_harness import (
    WalkForwardDriver,
    _compute_market_ndcg,
    _load_gsis_to_sleeper_map,
)
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


def _wr_2020_player_ids(n: int) -> list[str]:
    df = pd.read_csv("app/data/training/engine_b_features_v2.csv")
    mask = (
        (df["position"] == "WR")
        & (df["feature_season"] == 2020)
        & df["training_eligible"].astype(bool)
    )
    return df.loc[mask, "player_id"].head(n).astype(str).tolist()


def _market_rows(
    player_ids: list[str],
    *,
    snapshot_date: str = "2021-09-08",
    source: str = "dp_archive",
    ranks_present: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    id_map = {pid: f"slp_{i}" for i, pid in enumerate(player_ids)}
    rows = []
    for i, _pid in enumerate(player_ids):
        rows.append({
            "snapshot_date": snapshot_date,
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": 1000 - (i * 10),
            "overall_rank": i + 1 if ranks_present else None,
            "position_rank": i + 1 if ranks_present else None,
            "position": "WR",
            "trend_30day": 0,
            "source": source,
            "inserted_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows, id_map


def _store_with_rows(tmp_path: Path, rows: list[dict]) -> MarketSnapshotStore:
    store = MarketSnapshotStore(db_path=tmp_path / "snapshots.db")
    store.upsert_snapshots(rows)
    return store


class _FakeArtifact:
    def __init__(self, position: str) -> None:
        self.run_id = "run-id"
        self.position = position
        self.git_sha = None
        self.promotion_gate = SimpleNamespace(overall_grade="ACTIVE_B")

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"backtest_result_{self.position}.json"
        path.write_text("{}", encoding="utf-8")
        return path


class _FakeDriver:
    id_maps: list[dict[str, str] | None] = []

    def __init__(self, position: str, model_version: str) -> None:
        self.position = position
        self.model_version = model_version
        self.prediction_rows = []
        self.market_comparison_rows = []

    def run(
        self,
        market_store=None,
        id_map=None,
        emit_prediction_log: bool = False,
        emit_market_comparison: bool = False,
    ) -> _FakeArtifact:
        self.id_maps.append(id_map)
        return _FakeArtifact(self.position)


def test_market_comparison_derives_fc_rank_from_fc_value_when_archive_ranks_null(tmp_path):
    player_ids = _wr_2020_player_ids(6)
    rows, id_map = _market_rows(player_ids, ranks_present=False)
    store = _store_with_rows(tmp_path, rows)
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map=id_map, emit_market_comparison=True)

    matched = [
        row for row in driver.market_comparison_rows
        if row["sleeper_id"] in {f"slp_{i}" for i in range(6)}
    ]
    assert matched
    by_value_desc = sorted(matched, key=lambda row: row["fc_value"], reverse=True)
    assert [row["fc_rank"] for row in by_value_desc] == [1, 2, 3, 4, 5, 6]
    assert all(row["rank_delta"] is not None for row in matched)


def test_default_nflreadpy_id_loader_normalizes_float_sleeper_ids(monkeypatch):
    fake_ff = pd.DataFrame({
        "gsis_id": ["00-0031234", "00-0039999"],
        "sleeper_id": [13269.0, 4034.0],
    })
    monkeypatch.setitem(
        sys.modules,
        "nflreadpy",
        SimpleNamespace(load_ff_playerids=lambda: fake_ff),
    )

    id_map = _load_gsis_to_sleeper_map()

    assert id_map == {"00-0031234": "13269", "00-0039999": "4034"}
    assert all(not sleeper_id.endswith(".0") for sleeper_id in id_map.values())


def test_id_map_csv_loads_and_normalizes_float_string_sleeper_ids(tmp_path):
    path = tmp_path / "db_playerids.csv"
    path.write_text(
        "gsis_id,sleeper_id,name\n"
        "00-0031234,13269.0,Float String\n"
        "00-0039999,4034,Clean String\n"
        "00-0000000,NA,Missing Sleeper\n",
        encoding="utf-8",
    )

    id_map = run_backtest._load_id_map_csv(path)

    assert id_map == {"00-0031234": "13269", "00-0039999": "4034"}
    assert all(".0" not in sleeper_id for sleeper_id in id_map.values())


@pytest.mark.parametrize("id_map", [{}, {"00-0031234": ""}])
def test_market_data_present_empty_or_all_na_id_map_raises_loudly(tmp_path, id_map):
    player_ids = _wr_2020_player_ids(3)
    rows, _ = _market_rows(player_ids, ranks_present=True)
    store = _store_with_rows(tmp_path, rows)
    expected_error = getattr(backtest_harness, "IdMapUnavailableError", RuntimeError)

    with pytest.raises(expected_error, match="id_map_unavailable"):
        WalkForwardDriver(position="WR").run(market_store=store, id_map=id_map)


def test_market_store_active_default_loader_unavailable_raises_loudly(
    monkeypatch,
    tmp_path,
):
    player_ids = _wr_2020_player_ids(3)
    rows, _ = _market_rows(player_ids, ranks_present=True)
    store = _store_with_rows(tmp_path, rows)
    expected_error = getattr(backtest_harness, "IdMapUnavailableError", RuntimeError)
    monkeypatch.setattr(backtest_harness, "_load_gsis_to_sleeper_map", lambda: {})

    with pytest.raises(expected_error, match="id_map_unavailable"):
        WalkForwardDriver(position="WR").run(market_store=store)


def test_cli_passes_normalized_id_map_csv_to_driver(monkeypatch, tmp_path):
    market_store_path = tmp_path / "snapshots.db"
    MarketSnapshotStore(db_path=market_store_path)
    id_map_path = tmp_path / "db_playerids.csv"
    id_map_path.write_text(
        "gsis_id,sleeper_id\n00-0031234,13269.0\n00-0039999,4034\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(run_backtest, "WalkForwardDriver", _FakeDriver)
    monkeypatch.setattr(run_backtest, "_current_git_sha", lambda: "a" * 40)
    _FakeDriver.id_maps = []

    exit_code = run_backtest.main([
        "--position",
        "WR",
        "--market-store",
        str(market_store_path),
        "--id-map-csv",
        str(id_map_path),
        "--output-dir",
        str(tmp_path / "runs"),
    ])

    assert exit_code == 0
    assert _FakeDriver.id_maps == [{"00-0031234": "13269", "00-0039999": "4034"}]


def test_cli_empty_id_map_csv_fails_loudly_when_market_store_active(tmp_path):
    market_store_path = tmp_path / "snapshots.db"
    player_ids = _wr_2020_player_ids(3)
    rows, _ = _market_rows(player_ids, ranks_present=True)
    store = MarketSnapshotStore(db_path=market_store_path)
    store.upsert_snapshots(rows)
    id_map_path = tmp_path / "db_playerids.csv"
    id_map_path.write_text(
        "gsis_id,sleeper_id\n00-0031234,\n00-0039999,NA\n",
        encoding="utf-8",
    )

    exit_code = run_backtest.main([
        "--position",
        "WR",
        "--market-store",
        str(market_store_path),
        "--id-map-csv",
        str(id_map_path),
        "--output-dir",
        str(tmp_path / "runs"),
    ])

    assert exit_code == 1


def test_feature_season_pairs_to_next_preseason_snapshot_in_result(tmp_path):
    player_ids = _wr_2020_player_ids(3)
    rows, id_map = _market_rows(player_ids, snapshot_date="2021-09-08")
    store = _store_with_rows(tmp_path, rows)

    result = WalkForwardDriver(position="WR").run(market_store=store, id_map=id_map)

    assert result.market_snapshot_dates == {2020: "2021-09-08"}
    assert result.folds[0].test_year == 2020
    assert result.folds[0].outcome_seasons == [2021, 2022]


def test_dp_archive_market_source_gets_dynastyprocess_expert_consensus_label(tmp_path):
    player_ids = _wr_2020_player_ids(30)
    rows, id_map = _market_rows(player_ids, source="dp_archive", ranks_present=True)
    store = _store_with_rows(tmp_path, rows)

    result = WalkForwardDriver(position="WR").run(market_store=store, id_map=id_map)

    assert result.market_source == "dp_archive"
    assert result.market_source_label == "dynastyprocess_ecr_2qb"


def test_market_ndcg_computes_from_values_even_when_stored_ranks_are_null():
    market_rows = [
        {
            "sleeper_id": f"slp_{i}",
            "value": value,
            "overall_rank": None,
            "position_rank": None,
        }
        for i, value in enumerate([300, 100, 200, 50, 400, 150, 250, 75, 350, 125, 275, 25])
    ]
    player_ids = [f"gsis_{i}" for i in range(12)]
    id_map = {f"gsis_{i}": f"slp_{i}" for i in range(12)}
    y_pred = np.array([12, 7, 10, 4, 11, 6, 9, 3, 8, 5, 2, 1], dtype=float)
    y_realized = np.array([9, 5, 8, 2, 12, 4, 7, 1, 10, 3, 6, 0], dtype=float)

    result = _compute_market_ndcg(
        y_pred=y_pred,
        player_ids=player_ids,
        y_realized=y_realized,
        market_rows=market_rows,
        id_map=id_map,
        position="WR",
        n_bootstrap=10,
    )

    assert result["market_pool_n"] == 12
    assert result["ndcg_at_12_market"] is not None
    assert 0.0 <= result["ndcg_at_12_market"] <= 1.0
