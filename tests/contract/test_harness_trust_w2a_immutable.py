"""Harness Trust Completion W2a.1 RED: immutable market snapshot appends."""

from __future__ import annotations

import pytest

from src.dynasty_genius.eval import market_snapshot_store as store_mod
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


def _row(
    *,
    snapshot_date: str = "2024-09-08",
    sleeper_id: str = "player_1",
    value: int = 5000,
    league_settings_hash: str = "sf_ppr_12",
) -> dict:
    return {
        "snapshot_date": snapshot_date,
        "league_settings_hash": league_settings_hash,
        "sleeper_id": sleeper_id,
        "value": value,
        "overall_rank": 1,
        "position_rank": 1,
        "position": "QB",
        "trend_30day": 0,
        "source": "fc_native",
        "inserted_at": "2026-05-30T00:00:00+00:00",
    }


def test_append_snapshots_identical_reappend_is_idempotent_noop(tmp_path) -> None:
    store = MarketSnapshotStore(db_path=tmp_path / "snapshots.db")
    row = _row()

    assert store.append_snapshots([row]) == 1
    assert store.append_snapshots([row]) == 1

    rows = store.get_snapshot("2024-09-08")
    assert len(rows) == 1
    assert rows[0]["value"] == 5000


def test_append_snapshots_changed_value_on_same_pk_raises_and_preserves_original(
    tmp_path,
) -> None:
    store = MarketSnapshotStore(db_path=tmp_path / "snapshots.db")
    original = _row(value=5000)
    changed = _row(value=5100)
    store.append_snapshots([original])

    with pytest.raises(store_mod.MarketSnapshotImmutabilityError):
        store.append_snapshots([changed])

    rows = store.get_snapshot("2024-09-08")
    assert len(rows) == 1
    assert rows[0]["value"] == 5000


def test_append_snapshots_distinct_dates_accumulate(tmp_path) -> None:
    store = MarketSnapshotStore(db_path=tmp_path / "snapshots.db")

    assert store.append_snapshots([_row(snapshot_date="2024-09-08")]) == 1
    assert store.append_snapshots([_row(snapshot_date="2024-09-09")]) == 1

    coverage = store.get_coverage()
    assert coverage["n_dates"] == 2
    assert coverage["n_rows"] == 2


def test_append_snapshots_conflict_mid_batch_leaves_no_partial_write(tmp_path) -> None:
    store = MarketSnapshotStore(db_path=tmp_path / "snapshots.db")
    original = _row(sleeper_id="player_1", value=5000)
    new_row_before_conflict = _row(sleeper_id="player_2", value=4500)
    conflicting_existing_row = _row(sleeper_id="player_1", value=5100)
    store.append_snapshots([original])

    with pytest.raises(store_mod.MarketSnapshotImmutabilityError):
        store.append_snapshots([new_row_before_conflict, conflicting_existing_row])

    rows = store.get_snapshot("2024-09-08")
    assert len(rows) == 1
    assert rows[0]["sleeper_id"] == "player_1"
    assert rows[0]["value"] == 5000
