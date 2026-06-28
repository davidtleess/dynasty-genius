"""Realized-Outcome Loop T2 RED: point-in-time identity bridge.

The bridge must use governed identity snapshots as its PIT source of record. T1 capture
rows may prove useful downstream, but this resolver should not invent ad-hoc identity
logic from captured predictions or current-state IdentityResolver.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.audit.identity_snapshot_generator import (
    IdentitySnapshotRow,
    generate_identity_snapshot,
)
from src.dynasty_genius.identity.outcome_identity_bridge import (
    BridgeRow,
    OutcomeIdentityBridge,
)


def _snapshot(*, timestamp: str, rows: list[IdentitySnapshotRow]) -> dict:
    return generate_identity_snapshot(
        rows,
        run_id=timestamp[:10],
        created_at=timestamp,
        mapping_version="test.v1",
    ).as_dict()


def _resolved_tuple(resolution) -> tuple:
    return (
        resolution.gsis_id,
        resolution.dg_player_id,
        resolution.pfr_id,
        resolution.resolution_status,
    )


def test_resolves_sleeper_to_gsis_valid_at_capture_date_from_identity_snapshot() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_bijan",
                        sleeper_id="9509",
                        gsis_id="00-TEST-RB",
                        pfr_id="RobiBi00",
                    )
                ],
            )
        ]
    )

    resolution = bridge.resolve("9509", "2026-06-24")

    assert _resolved_tuple(resolution) == (
        "00-TEST-RB",
        "dg_bijan",
        "RobiBi00",
        "resolved",
    )
    assert bridge.rows[0].season == 2026
    assert bridge.rows[0].valid_from == "2026-06-01"
    assert bridge.rows[0].valid_to is None
    assert bridge.rows[0].source_hash


def test_resolve_uses_mapping_valid_at_capture_date_not_latest_snapshot() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_player_old",
                        sleeper_id="7777",
                        gsis_id="00-OLD",
                        pfr_id="Oldxx00",
                    )
                ],
            ),
            _snapshot(
                timestamp="2026-07-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_player_new",
                        sleeper_id="7777",
                        gsis_id="00-NEW",
                        pfr_id="Newxx00",
                    )
                ],
            ),
        ]
    )

    before_change = bridge.resolve("7777", "2026-06-24")
    after_change = bridge.resolve("7777", "2026-07-15")

    assert _resolved_tuple(before_change) == (
        "00-OLD",
        "dg_player_old",
        "Oldxx00",
        "resolved",
    )
    assert _resolved_tuple(after_change) == (
        "00-NEW",
        "dg_player_new",
        "Newxx00",
        "resolved",
    )


def test_stable_mapping_across_daily_snapshots_coalesces_to_one_open_window() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_stable",
                        sleeper_id="5555",
                        gsis_id="00-STABLE",
                        pfr_id="Stabxx00",
                    )
                ],
            ),
            _snapshot(
                timestamp="2026-06-02T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_stable",
                        sleeper_id="5555",
                        gsis_id="00-STABLE",
                        pfr_id="Stabxx00",
                    )
                ],
            ),
            _snapshot(
                timestamp="2026-06-03T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_stable",
                        sleeper_id="5555",
                        gsis_id="00-STABLE",
                        pfr_id="Stabxx00",
                    )
                ],
            ),
        ]
    )

    resolution = bridge.resolve("5555", "2026-06-24")
    rows_for_sleeper = [row for row in bridge.rows if row.sleeper_id == "5555"]

    assert _resolved_tuple(resolution) == (
        "00-STABLE",
        "dg_stable",
        "Stabxx00",
        "resolved",
    )
    assert len(rows_for_sleeper) == 1
    assert rows_for_sleeper[0].valid_from == "2026-06-01"
    assert rows_for_sleeper[0].valid_to is None


def test_same_timestamp_distinct_mappings_for_sleeper_return_conflict() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_old",
                        sleeper_id="1234",
                        gsis_id="00-OLD",
                        pfr_id="Oldxx00",
                    )
                ],
            ),
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_new",
                        sleeper_id="1234",
                        gsis_id="00-NEW",
                        pfr_id="Newxx00",
                    )
                ],
            ),
        ]
    )

    resolution = bridge.resolve("1234", "2026-06-01")

    assert _resolved_tuple(resolution) == (None, None, None, "conflict")


def test_same_timestamp_identical_mapping_for_sleeper_coalesces_without_conflict() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_same",
                        sleeper_id="1234",
                        gsis_id="00-SAME",
                        pfr_id="Samexx00",
                    )
                ],
            ),
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_same",
                        sleeper_id="1234",
                        gsis_id="00-SAME",
                        pfr_id="Samexx00",
                    )
                ],
            ),
        ]
    )

    resolution = bridge.resolve("1234", "2026-06-01")
    rows_for_sleeper = [row for row in bridge.rows if row.sleeper_id == "1234"]

    assert _resolved_tuple(resolution) == (
        "00-SAME",
        "dg_same",
        "Samexx00",
        "resolved",
    )
    assert len(rows_for_sleeper) == 1
    assert rows_for_sleeper[0].valid_from == "2026-06-01"
    assert rows_for_sleeper[0].valid_to is None


@pytest.mark.parametrize("sleeper_id", [None, "", "unknown"])
def test_null_blank_or_unknown_sleeper_id_resolves_unresolved(sleeper_id) -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_bijan",
                        sleeper_id="9509",
                        gsis_id="00-TEST-RB",
                        pfr_id="RobiBi00",
                    )
                ],
            )
        ]
    )

    resolution = bridge.resolve(sleeper_id, "2026-06-24")

    assert _resolved_tuple(resolution) == (None, None, None, "unresolved")


def test_one_sleeper_to_two_gsis_in_same_window_returns_conflict() -> None:
    bridge = OutcomeIdentityBridge.from_identity_snapshots(
        [
            _snapshot(
                timestamp="2026-06-01T00:00:00Z",
                rows=[
                    IdentitySnapshotRow(
                        player_id="dg_left",
                        sleeper_id="1234",
                        gsis_id="00-LEFT",
                        pfr_id="Leftxx00",
                    ),
                    IdentitySnapshotRow(
                        player_id="dg_right",
                        sleeper_id="1234",
                        gsis_id="00-RIGHT",
                        pfr_id="Rightx00",
                    ),
                ],
            )
        ]
    )

    resolution = bridge.resolve("1234", "2026-06-24")

    assert _resolved_tuple(resolution) == (None, None, None, "conflict")


def test_duplicate_bridge_rows_for_same_sleeper_window_return_conflict() -> None:
    bridge = OutcomeIdentityBridge(
        rows=[
            BridgeRow(
                sleeper_id="1234",
                gsis_id="00-SAME",
                dg_player_id="dg_player",
                pfr_id="Samexx00",
                season=2026,
                valid_from="2026-06-01",
                valid_to=None,
                source_hash="source-a",
            ),
            BridgeRow(
                sleeper_id="1234",
                gsis_id="00-SAME",
                dg_player_id="dg_player",
                pfr_id="Samexx00",
                season=2026,
                valid_from="2026-06-01",
                valid_to=None,
                source_hash="source-a",
            ),
        ]
    )

    resolution = bridge.resolve("1234", "2026-06-24")

    assert _resolved_tuple(resolution) == (None, None, None, "conflict")


def test_overlapping_validity_windows_for_sleeper_return_conflict() -> None:
    bridge = OutcomeIdentityBridge(
        rows=[
            BridgeRow(
                sleeper_id="1234",
                gsis_id="00-OLD",
                dg_player_id="dg_old",
                pfr_id="Oldxx00",
                season=2026,
                valid_from="2026-06-01",
                valid_to="2026-07-10",
                source_hash="source-old",
            ),
            BridgeRow(
                sleeper_id="1234",
                gsis_id="00-NEW",
                dg_player_id="dg_new",
                pfr_id="Newxx00",
                season=2026,
                valid_from="2026-07-01",
                valid_to=None,
                source_hash="source-new",
            ),
        ]
    )

    resolution = bridge.resolve("1234", "2026-07-05")

    assert _resolved_tuple(resolution) == (None, None, None, "conflict")
