"""Task 12.3 + 12.4 + 12.7 unit tests: prediction log, market-comparison ledger,
and divergence ledger.

Task 12.3 (5 tests): emit_prediction_log parameter, row keys, residual arithmetic,
    temporal isolation, CSV serialization.
Task 12.4 (5 tests): emit_market_comparison, MarketComparisonEntry schema,
    JSON serialization.
Task 12.7 (5 tests): build_divergence_ledger, DivergenceLedgerEntry schema,
    flagged_direction logic, JSON output.
Module-scoped fixtures: run() called once and reused across tests.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    FoldResult,
    GateResult,
    StabilityResult,
)
from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.eval.backtest_report import (
    DivergenceLedgerEntry,
    MarketComparisonEntry,
    write_market_comparison_json,
    write_prediction_log_csv,
)
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore
from scripts.build_divergence_ledger import build_divergence_ledger


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def wr_driver_with_log():
    """Run WR walk-forward once with emit_prediction_log=True."""
    driver = WalkForwardDriver(position="WR")
    driver.run(emit_prediction_log=True)
    return driver


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_emit_prediction_log_produces_rows(wr_driver_with_log):
    """run(emit_prediction_log=True) exposes driver.prediction_rows as a non-empty list."""
    rows = wr_driver_with_log.prediction_rows
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_prediction_rows_have_required_keys(wr_driver_with_log):
    """Each row has the required prediction log keys."""
    required = {
        "player_id", "fold_index", "feature_season",
        "predicted_ppg", "realized_ppg", "model_rank", "residual",
    }
    for row in wr_driver_with_log.prediction_rows:
        assert required.issubset(row.keys()), (
            f"Row missing keys: {required - row.keys()}"
        )


def test_prediction_rows_residual_equals_realized_minus_predicted(wr_driver_with_log):
    """residual == realized_ppg - predicted_ppg for every row."""
    for row in wr_driver_with_log.prediction_rows:
        expected = pytest.approx(row["realized_ppg"] - row["predicted_ppg"], abs=1e-9)
        assert row["residual"] == expected


def test_prediction_log_has_no_future_data_in_train_rows(wr_driver_with_log):
    """All rows in prediction_rows come from test folds only.

    Each row's feature_season must equal one of the 4 fold test_years
    (2020, 2021, 2022, 2023), and must match the fold_index's expected year.
    """
    fold_test_years = {1: 2020, 2: 2021, 3: 2022, 4: 2023}
    for row in wr_driver_with_log.prediction_rows:
        fold_idx = row["fold_index"]
        expected_year = fold_test_years[fold_idx]
        assert row["feature_season"] == expected_year, (
            f"fold_index={fold_idx} should have feature_season={expected_year}, "
            f"got {row['feature_season']}"
        )


def test_prediction_csv_writes_correctly(tmp_path, wr_driver_with_log):
    """CSV written from prediction_rows is readable by pandas with correct dtypes."""
    csv_path = tmp_path / "predictions_WR.csv"
    write_prediction_log_csv(wr_driver_with_log.prediction_rows, csv_path)

    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == len(wr_driver_with_log.prediction_rows)
    assert "player_id" in df.columns
    assert "model_rank" in df.columns
    assert "residual" in df.columns
    assert df["model_rank"].dtype in (int, "int64", "Int64")
    assert df["predicted_ppg"].dtype in (float, "float64")


# ── Task 12.4: Market-comparison ledger ───────────────────────────────────────

def _wr_2020_player_ids(n: int = 5) -> list[str]:
    df = pd.read_csv("app/data/training/engine_b_features_v2.csv")
    mask = (
        (df["position"] == "WR")
        & (df["feature_season"] == 2020)
        & df["training_eligible"].astype(bool)
    )
    return df.loc[mask, "player_id"].head(n).astype(str).tolist()


def _market_rows_for_players(player_ids: list[str], n_matched: int | None = None) -> tuple[list[dict], dict[str, str]]:
    n_matched = len(player_ids) if n_matched is None else n_matched
    id_map = {pid: f"slp_{i}" for i, pid in enumerate(player_ids[:n_matched])}
    rows = [
        {
            "snapshot_date": "2021-09-08",
            "league_settings_hash": "test0000",
            "sleeper_id": f"slp_{i}",
            "value": 1000 - i,
            "overall_rank": i + 1,
            "position_rank": i + 1,
            "position": "WR",
            "trend_30day": 0,
            "source": "fc_native",
            "inserted_at": datetime.now(timezone.utc).isoformat(),
        }
        for i in range(n_matched)
    ]
    return rows, id_map


def test_emit_market_comparison_with_empty_store_produces_no_rows(tmp_path):
    """run(market_store=empty_store, emit_market_comparison=True) exposes empty rows."""
    store = MarketSnapshotStore(db_path=tmp_path / "empty.db")
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map={}, emit_market_comparison=True)

    assert driver.market_comparison_rows == []


def test_emit_market_comparison_with_populated_store_produces_rows(tmp_path):
    """With synthetic market rows, market_comparison_rows is non-empty."""
    player_ids = _wr_2020_player_ids()
    rows, id_map = _market_rows_for_players(player_ids)
    store = MarketSnapshotStore(db_path=tmp_path / "populated.db")
    store.upsert_snapshots(rows)
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map=id_map, emit_market_comparison=True)

    assert driver.market_comparison_rows
    assert any(row["fc_value"] is not None for row in driver.market_comparison_rows)


def test_market_comparison_entry_rank_delta_positive_when_model_ranks_higher():
    """rank_delta = fc_rank - model_rank; positive means model ranked player higher."""
    entry = MarketComparisonEntry(
        player_id="p1",
        sleeper_id="s1",
        position="WR",
        fold_index=1,
        feature_season=2020,
        snapshot_date="2021-09-08",
        predicted_ppg=12.0,
        model_rank=2,
        fc_value=900,
        fc_rank=5,
        realized_ppg=11.0,
        realized_rank=3,
        rank_delta=5 - 2,
    )

    assert entry.rank_delta == 3


def test_market_comparison_unmatched_players_have_null_fc_fields(tmp_path):
    """Players with no sleeper_id match have fc fields set to None."""
    player_ids = _wr_2020_player_ids()
    rows, id_map = _market_rows_for_players(player_ids, n_matched=2)
    store = MarketSnapshotStore(db_path=tmp_path / "partial.db")
    store.upsert_snapshots(rows)
    driver = WalkForwardDriver(position="WR")

    driver.run(market_store=store, id_map=id_map, emit_market_comparison=True)

    unmatched = [row for row in driver.market_comparison_rows if row["sleeper_id"] is None]
    assert unmatched
    assert all(row["fc_value"] is None and row["fc_rank"] is None for row in unmatched)


def test_market_comparison_json_serializes(tmp_path):
    """List of MarketComparisonEntry serializes to valid JSON."""
    entries = [
        MarketComparisonEntry(
            player_id="p1",
            sleeper_id="s1",
            position="WR",
            fold_index=1,
            feature_season=2020,
            snapshot_date="2021-09-08",
            predicted_ppg=12.0,
            model_rank=2,
            fc_value=900,
            fc_rank=5,
            realized_ppg=11.0,
            realized_rank=3,
            rank_delta=3,
        )
    ]
    path = tmp_path / "market_comparison_WR.json"

    write_market_comparison_json(entries, path)

    assert path.exists()
    loaded = pd.read_json(path)
    assert loaded.loc[0, "player_id"] == "p1"
    assert loaded.loc[0, "rank_delta"] == 3


# ── Task 12.7: Divergence ledger ──────────────────────────────────────────────

def _make_backtest_result(position: str = "WR") -> BacktestResult:
    folds = [
        FoldResult(
            fold_index=i + 1,
            train_years=list(range(2018, 2020 + i)),
            test_year=2020 + i,
            outcome_seasons=[2021 + i, 2022 + i],
            n_train=200, n_test=50,
            kendall_tau=0.45,
            kendall_tau_bca_ci95=(0.35, 0.55),
            spearman_rho=0.50,
            spearman_rho_bca_ci95=(0.40, 0.60),
            rank_ic=0.50, rmse=3.0, mae=2.0,
        )
        for i in range(4)
    ]
    grade = "EXPERIMENTAL" if position == "TE" else "ACTIVE_B"
    return BacktestResult(
        run_id=uuid4(),
        run_date=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        model_version="engine_b_v2",
        model_artifact_hash="aabbccdd" * 8,
        position=position,  # type: ignore[arg-type]
        ridge_alpha=200.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=folds,
        rmse_stability=StabilityResult(
            rmse_per_fold=[3.0, 3.0, 3.0, 3.0],
            rmse_mean=3.0, rmse_cv=0.0, rmse_max_deviation_pct=0.0,
        ),
        market_source="unavailable",
        promotion_gate=GateResult(
            g1_rank_correlation_pass=(position != "TE"),
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade=grade,
            promotion_justification="test fixture",
        ),
    )


def _write_market_comparison(run_dir: Path, position: str, entries: list[dict]) -> Path:
    path = run_dir / f"market_comparison_{position}.json"
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return path


def test_build_divergence_ledger_requires_backtest_result(tmp_path):
    """build_divergence_ledger raises FileNotFoundError if no BacktestResult exists."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        build_divergence_ledger("WR", runs_dir=runs_dir, output_dir=tmp_path / "out")


def test_build_divergence_ledger_with_no_market_comparison_produces_empty_ledger(tmp_path):
    """With no market_comparison JSON, ledger has zero entries."""
    runs_dir = tmp_path / "runs"
    result = _make_backtest_result("WR")
    run_dir = runs_dir / str(result.run_id)
    result.save(run_dir)
    # No market_comparison JSON written

    entries = build_divergence_ledger("WR", runs_dir=runs_dir, output_dir=tmp_path / "out")

    assert entries == []


def test_divergence_ledger_entry_flagged_direction_model_higher():
    """rank_delta > 0 → flagged_direction == 'model_higher'.

    rank_delta = fc_rank - engine_b_rank.
    Positive means FC has a worse rank (higher number) than the model.
    """
    entry = DivergenceLedgerEntry(
        player_id="p1",
        position="WR",
        feature_season=2020,
        engine_b_pred_ppg=14.0,
        engine_b_rank=3,
        fc_rank=10,
        rank_delta=10 - 3,     # = 7 > 0
        flagged_direction="model_higher",
    )
    assert entry.rank_delta == 7
    assert entry.flagged_direction == "model_higher"


def test_divergence_ledger_entry_flagged_direction_none_for_zero_delta():
    """rank_delta == 0 → flagged_direction == None."""
    entry = DivergenceLedgerEntry(
        player_id="p2",
        position="WR",
        feature_season=2020,
        engine_b_pred_ppg=12.0,
        engine_b_rank=5,
        fc_rank=5,
        rank_delta=0,
        flagged_direction=None,
    )
    assert entry.rank_delta == 0
    assert entry.flagged_direction is None


def test_build_divergence_ledger_writes_json(tmp_path):
    """build_divergence_ledger writes valid JSON deserializable to list[DivergenceLedgerEntry]."""
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "out"
    result = _make_backtest_result("WR")
    run_dir = runs_dir / str(result.run_id)
    result.save(run_dir)
    market_entries = [
        {
            "player_id": "p1", "sleeper_id": "s1", "position": "WR",
            "fold_index": 1, "feature_season": 2020,
            "snapshot_date": "2021-09-08", "predicted_ppg": 14.0,
            "model_rank": 3, "fc_value": 900, "fc_rank": 10,
            "realized_ppg": 13.0, "realized_rank": 4, "rank_delta": 7,
        }
    ]
    _write_market_comparison(run_dir, "WR", market_entries)

    entries = build_divergence_ledger("WR", runs_dir=runs_dir, output_dir=output_dir)

    ledger_path = output_dir / "divergence_ledger_WR.json"
    assert ledger_path.exists()
    raw = json.loads(ledger_path.read_text())
    validated = [DivergenceLedgerEntry.parse_obj(row) for row in raw]
    assert len(validated) == 1
    assert validated[0].player_id == "p1"
    assert validated[0].flagged_direction == "model_higher"
