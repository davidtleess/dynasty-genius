"""League transaction ingestion — the one adapter for Sleeper's transactions endpoint.

Layer 1. Fetch, store durably, resolve identities. Nothing downstream: no analysis of
manager behaviour, no scoring, no surface. Callable, never self-scheduling — a scheduler is
a separate decision and a separate word.

Design note: ``docs/agent-ledger/evidence/2026-07-30/transaction_ingestion_design_claude_v1.md``.

Shape facts measured from the live endpoint (2026-07-30), each of which the code must survive:
``adds``/``drops`` arrive as ``null`` rather than ``{}``; ``type`` includes ``commissioner``
alongside the three David named; ``status`` includes ``failed``; trades carry ``draft_picks``;
timestamps are epoch milliseconds.

Three review findings (TW30E-CODEREVIEW-10) shaped the current design and are named where
they bite: presence in Sleeper's own player map is NOT identity resolution (§IdentityResolver);
an absent leg is not an empty leg and a failed run must not inherit a prior success
(§run_transaction_capture); and row-count stability is not idempotence (§TransactionStore).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA_VERSION = "league_transactions.v2"

#: Legs Sleeper exposes. Off-season activity lands in leg 1; regular season uses 1-18.
DEFAULT_LEGS: tuple[int, ...] = tuple(range(1, 19))

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _REPO_ROOT / "app" / "data" / "league_transactions.db"
DEFAULT_RAW_ROOT = _REPO_ROOT / "app" / "data" / "league_transactions"

COMPLETE = "complete"

#: Identity outcomes, deliberately three-valued. The middle one is the state the first
#: implementation collapsed into "resolved", which is what let a coverage line read
#: ``players_unresolved: 0`` while two players had no canonical mapping at all.
CANONICAL_RESOLVED = "canonical_resolved"
SLEEPER_ONLY = "sleeper_only"
UNKNOWN = "unknown"


class TransactionCaptureError(RuntimeError):
    """The capture refuses rather than publishing something untrustworthy."""


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a marker atomically: a reader never sees a half-written status."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityResolver:
    """Resolves a Sleeper id to a Dynasty Genius canonical id.

    **Presence in Sleeper's own player map is not identity resolution.** The Sleeper
    universe snapshot supplies display attributes (name, position, team) for a Sleeper id;
    the canonical id comes only from the governed ff_playerids crosswalk, which is the
    product's single sanctioned Sleeper->canonical join (`01` §Identity Resolution: no
    adapter invents its own identity logic). A player present in the snapshot but absent
    from the crosswalk is ``sleeper_only`` — attributable but not canonically identified —
    and is counted separately from a player that is simply ``unknown``.
    """

    sleeper_players: Mapping[str, dict[str, Any]]
    crosswalk_by_sleeper: Mapping[str, dict[str, Any]]
    managers: Mapping[int, dict[str, Any]]

    @classmethod
    def from_snapshot(
        cls,
        payload: Mapping[str, Any],
        *,
        crosswalk_by_sleeper: Mapping[str, dict[str, Any]] | None = None,
    ) -> "IdentityResolver":
        players: dict[str, dict[str, Any]] = {}
        for row in payload.get("players") or []:
            sleeper_id = row.get("sleeper_player_id")
            if sleeper_id is None:
                continue
            players[str(sleeper_id)] = row

        users_by_id = {
            str(u.get("user_id")): u for u in (payload.get("users") or []) if u.get("user_id")
        }
        managers: dict[int, dict[str, Any]] = {}
        for roster in payload.get("rosters") or []:
            roster_id = roster.get("roster_id")
            if roster_id is None:
                continue
            owner_id = roster.get("owner_id")
            user = users_by_id.get(str(owner_id)) or {}
            managers[int(roster_id)] = {
                "owner_user_id": str(owner_id) if owner_id is not None else None,
                "display_name": user.get("display_name"),
            }
        return cls(
            sleeper_players=players,
            crosswalk_by_sleeper=dict(crosswalk_by_sleeper or {}),
            managers=managers,
        )

    def player(self, sleeper_player_id: str) -> dict[str, Any]:
        """Always returns a row. An unidentified player is labelled, never dropped."""
        key = str(sleeper_player_id)
        snapshot_row = self.sleeper_players.get(key)
        crosswalk_row = self.crosswalk_by_sleeper.get(key)

        dg_player_id = None
        if crosswalk_row is not None:
            raw = crosswalk_row.get("gsis_id")
            dg_player_id = str(raw).strip() or None if raw is not None else None

        if dg_player_id is not None:
            identity_status = CANONICAL_RESOLVED
        elif snapshot_row is not None:
            identity_status = SLEEPER_ONLY
        else:
            identity_status = UNKNOWN

        attributes = (snapshot_row or {}).get("player") or {}
        return {
            "sleeper_player_id": key,
            # The source join key, matching `build_model_player_key`'s form so this store
            # can join to the model-output capture. It is NOT the canonical identity.
            "player_key": f"sleeper:{key}",
            "dg_player_id": dg_player_id,
            "player_name": attributes.get("full_name") or (crosswalk_row or {}).get("name"),
            "position": attributes.get("position") or (crosswalk_row or {}).get("position"),
            "team": attributes.get("team"),
            "identity_status": identity_status,
        }

    def manager(self, roster_id: Any) -> dict[str, Any]:
        try:
            key = int(roster_id)
        except (TypeError, ValueError):
            return {"owner_user_id": None, "display_name": None}
        return self.managers.get(key, {"owner_user_id": None, "display_name": None})


def load_governed_crosswalk() -> dict[str, dict[str, Any]]:
    """The governed Sleeper->canonical crosswalk, via the product's hardened loader.

    Imported rather than reimplemented: that loader fails closed on nine named defect
    classes (conflicting mappings, duplicate JSON keys, wrong types) that a second
    hand-rolled reader would silently re-admit.
    """
    from scripts.build_universe_pvo_batch import _load_ff_playerids

    _by_gsis, by_sleeper = _load_ff_playerids()
    return dict(by_sleeper)


def manager_key(movement: Mapping[str, Any]) -> str:
    """A stable manager key. Display names are mutable and can collide."""
    user_id = movement.get("manager_user_id")
    if user_id:
        return f"user:{user_id}"
    return f"roster:{movement.get('roster_id')}"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


@dataclass
class NormalizedCapture:
    transactions: list[dict[str, Any]] = field(default_factory=list)
    movements: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)


def _iso_utc(epoch_ms: Any) -> str | None:
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc).isoformat()


def _movement_key(
    transaction_id: str, action: str, asset_type: str, identifier: str, roster_id: Any
) -> str:
    return f"{transaction_id}:{action}:{asset_type}:{identifier}:{roster_id}"


def normalize_leg(
    transactions: Sequence[Mapping[str, Any]],
    *,
    leg: str,
    league_id: str,
    season: str,
    resolver: IdentityResolver,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize one leg. Null-safe on every optional side of the payload."""
    rows: list[dict[str, Any]] = []
    movements: list[dict[str, Any]] = []

    for txn in transactions:
        transaction_id = str(txn.get("transaction_id"))
        status = str(txn.get("status") or "unknown")
        settings = txn.get("settings") or {}
        created_at = _iso_utc(txn.get("created"))
        txn_type = str(txn.get("type") or "unknown")

        rows.append(
            {
                "transaction_id": transaction_id,
                "league_id": league_id,
                "season": season,
                "leg": str(leg),
                "type": txn_type,
                "status": status,
                "created_at": created_at,
                "status_updated_at": _iso_utc(txn.get("status_updated")),
                "creator_user_id": txn.get("creator"),
                "roster_ids": list(txn.get("roster_ids") or []),
                "waiver_bid": settings.get("waiver_bid"),
                "raw_json": json.dumps(txn, sort_keys=True),
            }
        )

        def _base(action: str, roster_id: Any, identifier: str, asset_type: str) -> dict[str, Any]:
            manager = resolver.manager(roster_id)
            return {
                "movement_key": _movement_key(
                    transaction_id, action, asset_type, identifier, roster_id
                ),
                "transaction_id": transaction_id,
                "transaction_status": status,
                "transaction_type": txn_type,
                "created_at": created_at,
                "asset_type": asset_type,
                "action": action,
                "roster_id": roster_id,
                "manager_user_id": manager["owner_user_id"],
                "manager_display_name": manager["display_name"],
            }

        def _emit_player(sleeper_id: Any, roster_id: Any, action: str) -> None:
            row = _base(action, roster_id, str(sleeper_id), "player")
            row.update(
                {
                    "pick_season": None,
                    "pick_round": None,
                    "pick_original_roster_id": None,
                    "pick_previous_owner_roster_id": None,
                    **resolver.player(str(sleeper_id)),
                }
            )
            movements.append(row)

        for sleeper_id, roster_id in (txn.get("adds") or {}).items():
            _emit_player(sleeper_id, roster_id, "add")
        for sleeper_id, roster_id in (txn.get("drops") or {}).items():
            _emit_player(sleeper_id, roster_id, "drop")

        for pick in txn.get("draft_picks") or []:
            pick_season = str(pick.get("season")) if pick.get("season") is not None else None
            pick_round = pick.get("round")
            previous = pick.get("previous_owner_id")
            # `roster_id` on a Sleeper pick is the pick's ORIGINAL owner, and it is what
            # identifies which pick this is. A real 2026-07-30 trade moved four picks in
            # which (season, round, previous_owner) repeated twice; keying without the
            # original owner silently collapsed two genuine movements.
            original = pick.get("roster_id")
            identifier = f"{pick_season}-r{pick_round}-o{original}-p{previous}"
            pick_fields = {
                "sleeper_player_id": None,
                "player_key": None,
                "dg_player_id": None,
                "player_name": None,
                "position": None,
                "team": None,
                "identity_status": "not_a_player",
                "pick_season": pick_season,
                "pick_round": int(pick_round) if pick_round is not None else None,
                "pick_original_roster_id": original,
                "pick_previous_owner_roster_id": previous,
            }

            # BOTH sides. A pick history that records only acquisitions cannot answer
            # "what did this manager do" for the manager who gave the pick up.
            acquire = _base("pick_acquire", pick.get("owner_id"), identifier, "pick")
            acquire.update(pick_fields)
            movements.append(acquire)

            if previous is not None:
                send = _base("pick_send", previous, identifier, "pick")
                send.update(pick_fields)
                movements.append(send)

    return rows, movements


def normalize_transactions(
    legs: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    league_id: str,
    season: str,
    resolver: IdentityResolver,
) -> NormalizedCapture:
    """Normalize every leg, disclose identity coverage honestly, and refuse a total break."""
    capture = NormalizedCapture()
    for leg in sorted(legs, key=lambda value: int(value) if str(value).isdigit() else value):
        rows, movements = normalize_leg(
            legs[leg], leg=str(leg), league_id=league_id, season=season, resolver=resolver
        )
        capture.transactions.extend(rows)
        capture.movements.extend(movements)

    players = [m for m in capture.movements if m["asset_type"] == "player"]
    canonical = [m for m in players if m["identity_status"] == CANONICAL_RESOLVED]
    sleeper_only = [m for m in players if m["identity_status"] == SLEEPER_ONLY]
    unknown = [m for m in players if m["identity_status"] == UNKNOWN]
    managers_unresolved = [m for m in capture.movements if not m["manager_display_name"]]

    capture.coverage = {
        "schema_version": SCHEMA_VERSION,
        "transactions_total": len(capture.transactions),
        "movements_total": len(capture.movements),
        "players_total": len(players),
        # Three counts, never one. "Not canonically identified" is the sum of the last two
        # and is reported explicitly so no reader can infer it from a single zero.
        "players_canonical_resolved": len(canonical),
        "players_sleeper_only": len(sleeper_only),
        "players_unknown": len(unknown),
        "players_not_canonically_identified": len(sleeper_only) + len(unknown),
        "sleeper_only_ids": sorted({m["sleeper_player_id"] for m in sleeper_only}),
        "unknown_ids": sorted({m["sleeper_player_id"] for m in unknown}),
        "managers_unresolved": len(managers_unresolved),
    }

    if players and not canonical:
        raise TransactionCaptureError(
            "identity resolution produced zero canonically resolved players across "
            f"{len(players)} player movements — refusing to publish a transaction "
            "history whose players cannot be identified"
        )

    return capture


def completed_movements(movements: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Movements that actually happened. A failed waiver claim is behaviour, not an event."""
    return [dict(m) for m in movements if m.get("transaction_status") == COMPLETE]


# ---------------------------------------------------------------------------
# Durable store
# ---------------------------------------------------------------------------

_TRANSACTION_COLUMNS = (
    "transaction_id",
    "league_id",
    "season",
    "leg",
    "type",
    "status",
    "created_at",
    "status_updated_at",
    "creator_user_id",
    "roster_ids",
    "waiver_bid",
    "raw_json",
    "content_hash",
    "ingested_at",
)

_MOVEMENT_COLUMNS = (
    "movement_key",
    "transaction_id",
    "transaction_status",
    "transaction_type",
    "created_at",
    "asset_type",
    "action",
    "roster_id",
    "manager_user_id",
    "manager_display_name",
    "sleeper_player_id",
    "player_key",
    "dg_player_id",
    "player_name",
    "position",
    "team",
    "identity_status",
    "pick_season",
    "pick_round",
    "pick_original_roster_id",
    "pick_previous_owner_roster_id",
)


def _content_hash(row: Mapping[str, Any], movements: Sequence[Mapping[str, Any]]) -> str:
    payload = {
        "transaction": {k: row.get(k) for k in _TRANSACTION_COLUMNS if k not in {"content_hash", "ingested_at"}},
        "movements": sorted(
            ({k: m.get(k) for k in _MOVEMENT_COLUMNS} for m in movements),
            key=lambda m: str(m["movement_key"]),
        ),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


class TransactionStore:
    """Content-addressed, reconciling store.

    Re-ingesting identical content mutates **nothing** — not a timestamp, not a byte —
    and re-ingesting *changed* content replaces that transaction's movement set entirely,
    so a movement removed upstream does not survive as a phantom. Row-count stability was
    the weaker property the first implementation had, and it hid both defects.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS league_transaction ("
                + ", ".join(f"{c} TEXT" for c in _TRANSACTION_COLUMNS)
                + ", PRIMARY KEY (transaction_id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS league_transaction_movement ("
                + ", ".join(f"{c} TEXT" for c in _MOVEMENT_COLUMNS)
                + ", PRIMARY KEY (movement_key))"
            )
            # `CREATE TABLE IF NOT EXISTS` is a no-op against a table from an earlier
            # schema, so a store built by a prior version would otherwise be discovered
            # only by an OperationalError mid-write. Fail closed, by name, up front.
            self._assert_schema(conn, "league_transaction", _TRANSACTION_COLUMNS)
            self._assert_schema(conn, "league_transaction_movement", _MOVEMENT_COLUMNS)

    @staticmethod
    def _assert_schema(
        conn: sqlite3.Connection, table: str, expected: Sequence[str]
    ) -> None:
        actual = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        missing = [column for column in expected if column not in actual]
        if missing:
            raise TransactionCaptureError(
                f"league_transactions_schema_mismatch: {table} is missing "
                f"{missing} — the store predates {SCHEMA_VERSION}; rebuild it from the "
                "raw snapshots rather than writing mixed-schema rows"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert(self, capture: NormalizedCapture, *, ingested_at: str | None = None) -> dict[str, int]:
        """Apply a capture. Returns what actually changed, so a caller can prove it."""
        stamp = ingested_at or datetime.now(timezone.utc).isoformat()
        by_transaction: dict[str, list[dict[str, Any]]] = {}
        for movement in capture.movements:
            by_transaction.setdefault(str(movement["transaction_id"]), []).append(movement)

        inserted = 0
        updated = 0
        unchanged = 0
        with self._connect() as conn:
            for row in capture.transactions:
                transaction_id = str(row["transaction_id"])
                movements = by_transaction.get(transaction_id, [])
                digest = _content_hash(row, movements)
                existing = conn.execute(
                    "SELECT content_hash FROM league_transaction WHERE transaction_id = ?",
                    (transaction_id,),
                ).fetchone()

                if existing is not None and existing["content_hash"] == digest:
                    unchanged += 1
                    continue

                payload = dict(row)
                payload["roster_ids"] = json.dumps(payload.get("roster_ids") or [])
                payload["content_hash"] = digest
                payload["ingested_at"] = stamp
                conn.execute(
                    f"INSERT OR REPLACE INTO league_transaction ({', '.join(_TRANSACTION_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _TRANSACTION_COLUMNS)})",
                    [payload.get(c) for c in _TRANSACTION_COLUMNS],
                )
                # Reconcile: the stored movement set becomes exactly this transaction's
                # current movement set, so an upstream removal cannot survive.
                conn.execute(
                    "DELETE FROM league_transaction_movement WHERE transaction_id = ?",
                    (transaction_id,),
                )
                for movement in movements:
                    conn.execute(
                        f"INSERT OR REPLACE INTO league_transaction_movement "
                        f"({', '.join(_MOVEMENT_COLUMNS)}) "
                        f"VALUES ({', '.join('?' for _ in _MOVEMENT_COLUMNS)})",
                        [movement.get(c) for c in _MOVEMENT_COLUMNS],
                    )
                if existing is None:
                    inserted += 1
                else:
                    updated += 1

        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

    def transaction_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM league_transaction").fetchone()[0])

    def movement_count(self) -> int:
        with self._connect() as conn:
            return int(
                conn.execute("SELECT COUNT(*) FROM league_transaction_movement").fetchone()[0]
            )

    def fetch_transaction(self, transaction_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM league_transaction WHERE transaction_id = ?", (transaction_id,)
            ).fetchone()

    def movements_for(self, transaction_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM league_transaction_movement WHERE transaction_id = ? "
                    "ORDER BY movement_key",
                    (transaction_id,),
                ).fetchall()
            ]

    def content_fingerprint(self) -> str:
        """Hash of every stored row. Two runs with identical content produce identical bytes."""
        with self._connect() as conn:
            rows = [
                tuple(r)
                for r in conn.execute(
                    "SELECT * FROM league_transaction ORDER BY transaction_id"
                ).fetchall()
            ]
            rows += [
                tuple(r)
                for r in conn.execute(
                    "SELECT * FROM league_transaction_movement ORDER BY movement_key"
                ).fetchall()
            ]
        return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()

    def manager_activity(self) -> dict[str, dict[str, Any]]:
        """What every manager actually did — completed movements only, newest first.

        Keyed by a stable manager key, never by display name: display names are mutable
        and two managers can share one.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM league_transaction_movement "
                "WHERE transaction_status = ? ORDER BY created_at DESC",
                (COMPLETE,),
            ).fetchall()
        activity: dict[str, dict[str, Any]] = {}
        for row in rows:
            record = dict(row)
            key = manager_key(record)
            bucket = activity.setdefault(
                key,
                {
                    "manager_key": key,
                    "manager_user_id": record.get("manager_user_id"),
                    "display_name": record.get("manager_display_name"),
                    "movements": [],
                },
            )
            bucket["movements"].append(record)
        return activity


# ---------------------------------------------------------------------------
# Capture orchestration (callable; never self-scheduling)
# ---------------------------------------------------------------------------


def status_marker_path(raw_root: Path = DEFAULT_RAW_ROOT) -> Path:
    return Path(raw_root) / "transaction_capture_status_latest.json"


def write_raw_snapshot(
    legs: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    league_id: str,
    season: str,
    captured_at: str,
    legs_attempted: Sequence[int],
    legs_empty: Sequence[int],
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> Path:
    """Write the raw payload BEFORE parsing (`01` §Source Adapter Rules).

    Records which legs were ATTEMPTED and which came back empty. Without that, an
    18-leg fetch and a 1-leg fetch leave identical evidence and completeness is
    unprovable from the artifact.
    """
    raw_dir = Path(raw_root) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"transactions_{captured_at.replace(':', '').replace('-', '')}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "league_id": league_id,
                "season": season,
                "captured_at": captured_at,
                "legs_attempted": list(legs_attempted),
                "legs_empty": list(legs_empty),
                "legs": legs,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run_transaction_capture(
    *,
    league_id: str,
    season: str,
    fetch_leg: Callable[[int], Sequence[Mapping[str, Any]]],
    resolver: IdentityResolver,
    legs: Sequence[int] = DEFAULT_LEGS,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> dict[str, Any]:
    """Start marker -> fetch -> raw snapshot -> normalize -> store -> terminal marker.

    A start record is written before any fetch, so a run that dies mid-flight leaves
    ``status=running`` rather than the previous run's ``status=ok``. A leg that raises
    writes ``status=failed`` naming the leg, then re-raises. Silence is never success.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"{league_id}-{started_at.replace(':', '').replace('-', '')}"
    marker = status_marker_path(raw_root)
    legs_attempted = [int(leg) for leg in legs]

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "league_id": league_id,
        "season": season,
        "legs_attempted": legs_attempted,
    }
    _atomic_write_json(marker, {**base, "status": "running"})

    fetched: dict[str, list[dict[str, Any]]] = {}
    legs_empty: list[int] = []
    try:
        for leg in legs_attempted:
            payload = fetch_leg(leg) or []
            if payload:
                fetched[str(leg)] = [dict(item) for item in payload]
            else:
                legs_empty.append(leg)
    except Exception as exc:
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_leg": leg,
                "reason": f"{type(exc).__name__}: {exc}",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise TransactionCaptureError(f"leg {leg} fetch failed: {exc}") from exc

    raw_path = write_raw_snapshot(
        fetched,
        league_id=league_id,
        season=season,
        captured_at=started_at,
        legs_attempted=legs_attempted,
        legs_empty=legs_empty,
        raw_root=raw_root,
    )

    try:
        capture = normalize_transactions(
            fetched, league_id=league_id, season=season, resolver=resolver
        )
        store = TransactionStore(db_path)
        applied = store.upsert(capture, ingested_at=started_at)
    except Exception as exc:
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
                "raw_snapshot": str(raw_path),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise

    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "legs_with_activity": sorted(int(leg) for leg in fetched),
        "legs_empty": legs_empty,
        "raw_snapshot": str(raw_path),
        "db_path": str(db_path),
        "applied": applied,
        "transactions_stored": store.transaction_count(),
        "movements_stored": store.movement_count(),
        **capture.coverage,
    }
    _atomic_write_json(marker, status)
    return status
