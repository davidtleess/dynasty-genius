"""Realized-Outcome Loop T2 — point-in-time identity bridge.

Resolves a captured prediction's ``sleeper_id`` to the ``gsis_id`` (and ``dg_player_id`` /
``pfr_id``) that was valid **at the capture date**, so the realized-outcome scorer (T4) can
join captured predictions (sleeper/dg-keyed) to realized NFL outcomes (gsis-keyed) without
inventing ad-hoc identity logic in the scorer (north-star §Identity).

Source of record: the governed immutable identity snapshots produced by
``audit/identity_snapshot_generator.py``. Each snapshot is a point-in-time mapping state
stamped with a ``timestamp``; a chronological sequence of snapshots yields validity windows
per ``sleeper_id``:

- A mapping that is unchanged across consecutive snapshots **coalesces** into one open window
  (``valid_to=None``) — the common daily-snapshot case must NOT read as a duplicate/overlap
  conflict.
- When a sleeper's mapping **changes** (or disappears), the prior window closes at the date of
  the change and a new window opens.

``resolve`` is fail-closed: an unresolved id → ``unresolved`` (the caller excludes it with a
count); a sleeper that maps to two different gsis in the same window (or duplicate/overlapping
bridge rows) → ``conflict`` (quarantine — never silently pick one). The bridge does no I/O:
callers load the governed snapshots and pass the dicts in.

Design spec: docs/superpowers/specs/2026-06-27-realized-outcome-loop-design.md (§4.2).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
CONFLICT = "conflict"


@dataclass(frozen=True)
class BridgeRow:
    """One sleeper→identity mapping valid over a point-in-time window ``[valid_from, valid_to)``.

    ``valid_to=None`` is an open (still-current) window. ``source_hash`` is the provenance of
    the governed snapshot that opened the window.
    """

    sleeper_id: str
    gsis_id: Optional[str]
    dg_player_id: Optional[str]
    pfr_id: Optional[str]
    season: int
    valid_from: str
    valid_to: Optional[str]
    source_hash: str


@dataclass(frozen=True)
class BridgeResolution:
    """The result of resolving one ``(sleeper_id, capture_date)`` lookup."""

    gsis_id: Optional[str]
    dg_player_id: Optional[str]
    pfr_id: Optional[str]
    resolution_status: str  # resolved | unresolved | conflict


def _date_group_source_hash(snapshots: list[dict[str, Any]]) -> str:
    """Deterministic provenance hash of all governed snapshot envelopes for one date."""
    return hashlib.sha256(
        json.dumps(snapshots, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


class OutcomeIdentityBridge:
    """Point-in-time sleeper→gsis/dg/pfr resolver over governed identity-snapshot windows."""

    def __init__(self, rows: list[BridgeRow]) -> None:
        self.rows: list[BridgeRow] = list(rows)

    # ── construction ──
    @classmethod
    def from_identity_snapshots(
        cls, snapshots: list[dict[str, Any]]
    ) -> "OutcomeIdentityBridge":
        """Build validity windows from a sequence of governed identity snapshots.

        Each snapshot is the ``as_dict()`` of an ``IdentitySnapshot``: it carries a
        ``timestamp`` and ``mappings = {player_id: {sleeper_id, gsis_id, pfr_id, ...}}``.
        Identical consecutive mappings coalesce into one open window; a changed/absent mapping
        closes the prior window at the new date and opens a fresh one.

        Snapshots are grouped by **date** (the window grain — ``valid_from``/``valid_to`` are
        dates), and same-date snapshots are merged into one point-in-time state. So two
        contradictory same-date mappings for a sleeper produce two OVERLAPPING open windows and
        ``resolve`` flags ``conflict`` — never a silent input-order supersession (an intra-day
        contradiction cannot be represented in a date-grained window, so it fails closed).
        """
        ordered = sorted(snapshots, key=lambda snap: str(snap.get("timestamp", "")))
        snapshots_by_date: dict[str, list[dict[str, Any]]] = {}
        for snapshot in ordered:
            date = str(snapshot.get("timestamp", ""))[:10]
            snapshots_by_date.setdefault(date, []).append(snapshot)

        # Each "window key" = (sleeper_id, gsis_id, dg_player_id, pfr_id): a distinct mapping.
        open_windows: dict[tuple, dict[str, Any]] = {}
        completed: list[BridgeRow] = []

        for snapshot_date in sorted(snapshots_by_date):
            date_snapshots = snapshots_by_date[snapshot_date]
            season = int(snapshot_date[:4])
            source_hash = _date_group_source_hash(date_snapshots)

            # Merge all mappings present on this date into one point-in-time state.
            present: dict[tuple, dict[str, Any]] = {}
            for snapshot in date_snapshots:
                for player_id, mapping in (snapshot.get("mappings") or {}).items():
                    sleeper_id = (mapping or {}).get("sleeper_id")
                    if _is_blank(sleeper_id):
                        continue  # rows without a sleeper id cannot anchor a window
                    key = (
                        str(sleeper_id),
                        mapping.get("gsis_id"),
                        player_id,
                        mapping.get("pfr_id"),
                    )
                    present[key] = {
                        "sleeper_id": str(sleeper_id),
                        "gsis_id": mapping.get("gsis_id"),
                        "dg_player_id": player_id,
                        "pfr_id": mapping.get("pfr_id"),
                        "season": season,
                        "source_hash": source_hash,
                    }

            # Close any open window whose mapping is no longer present on this date.
            for key in list(open_windows):
                if key not in present:
                    completed.append(_close_window(open_windows.pop(key), snapshot_date))

            # Open a window for each newly-appearing mapping (coalesce if already open).
            for key, meta in present.items():
                if key not in open_windows:
                    open_windows[key] = {**meta, "valid_from": snapshot_date}

        # Remaining open windows are still current → valid_to=None.
        for window in open_windows.values():
            completed.append(_close_window(window, None))

        completed.sort(
            key=lambda row: (row.sleeper_id, row.valid_from, row.gsis_id or "")
        )
        return cls(completed)

    # ── resolution ──
    def resolve(
        self, sleeper_id: Optional[str], capture_date: str
    ) -> BridgeResolution:
        """Resolve a sleeper id to the mapping valid at ``capture_date`` (fail-closed)."""
        if _is_blank(sleeper_id):
            return BridgeResolution(None, None, None, UNRESOLVED)

        sid = str(sleeper_id)
        as_of = str(capture_date)[:10]
        matches = [
            row
            for row in self.rows
            if row.sleeper_id == sid and _in_window(row, as_of)
        ]
        if not matches:
            return BridgeResolution(None, None, None, UNRESOLVED)
        if len(matches) > 1:
            # Two distinct mappings in the window, OR duplicate/overlapping rows: never guess.
            return BridgeResolution(None, None, None, CONFLICT)
        row = matches[0]
        return BridgeResolution(row.gsis_id, row.dg_player_id, row.pfr_id, RESOLVED)


def _close_window(window: dict[str, Any], valid_to: Optional[str]) -> BridgeRow:
    return BridgeRow(
        sleeper_id=window["sleeper_id"],
        gsis_id=window["gsis_id"],
        dg_player_id=window["dg_player_id"],
        pfr_id=window["pfr_id"],
        season=window["season"],
        valid_from=window["valid_from"],
        valid_to=valid_to,
        source_hash=window["source_hash"],
    )


def _in_window(row: BridgeRow, as_of: str) -> bool:
    """Half-open membership: ``valid_from <= as_of < valid_to`` (open end when valid_to None)."""
    if as_of < row.valid_from:
        return False
    if row.valid_to is not None and as_of >= row.valid_to:
        return False
    return True
