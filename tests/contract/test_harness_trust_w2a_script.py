"""Harness Trust Completion W2a.2 RED: daily FC script uses immutable appends."""

from __future__ import annotations

import pytest

from scripts import snapshot_fantasycalc as snap
from src.dynasty_genius.eval.market_snapshot_store import (
    MarketSnapshotImmutabilityError,
    MarketSnapshotStore,
)


def _fc_row(
    *,
    snapshot_date: str = "2026-05-30",
    sleeper_id: str = "9509",
    value: int = 10500,
    inserted_at: str = "2026-05-30T12:00:00+00:00",
) -> dict:
    return {
        "snapshot_date": snapshot_date,
        "league_settings_hash": snap.LEAGUE_SETTINGS_HASH,
        "sleeper_id": sleeper_id,
        "value": value,
        "overall_rank": 1,
        "position_rank": 1,
        "position": "RB",
        "trend_30day": -50,
        "source": "fc_native",
        "inserted_at": inserted_at,
    }


def test_snapshot_fantasycalc_uses_immutable_append_for_same_day_idempotency(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "snapshots.db"
    monkeypatch.setattr(snap, "_fetch_fc_rows", lambda: [_fc_row()])

    assert snap.snapshot_fantasycalc(db_path=db_path) == 1
    assert snap.snapshot_fantasycalc(db_path=db_path) == 1

    store = MarketSnapshotStore(db_path=db_path)
    rows = store.get_snapshot("2026-05-30")
    assert len(rows) == 1
    assert rows[0]["value"] == 10500


def test_snapshot_fantasycalc_distinct_days_accumulate(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "snapshots.db"
    payloads = iter([
        [_fc_row(snapshot_date="2026-05-30")],
        [_fc_row(snapshot_date="2026-05-31")],
    ])
    monkeypatch.setattr(snap, "_fetch_fc_rows", lambda: next(payloads))

    assert snap.snapshot_fantasycalc(db_path=db_path) == 1
    assert snap.snapshot_fantasycalc(db_path=db_path) == 1

    coverage = MarketSnapshotStore(db_path=db_path).get_coverage()
    assert coverage["n_dates"] == 2
    assert coverage["n_rows"] == 2


def test_snapshot_fantasycalc_changed_same_day_value_raises_immutability_error(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "snapshots.db"
    payloads = iter([
        [_fc_row(value=10500)],
        [_fc_row(value=10600, inserted_at="2026-05-30T12:05:00+00:00")],
    ])
    monkeypatch.setattr(snap, "_fetch_fc_rows", lambda: next(payloads))

    assert snap.snapshot_fantasycalc(db_path=db_path) == 1
    with pytest.raises(MarketSnapshotImmutabilityError):
        snap.snapshot_fantasycalc(db_path=db_path)

    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2026-05-30")
    assert len(rows) == 1
    assert rows[0]["value"] == 10500
