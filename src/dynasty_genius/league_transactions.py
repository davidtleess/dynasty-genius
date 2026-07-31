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

**Multi-season (TW30N-BUILD-01).** One season of transactions cannot describe a manager, so
capture follows Sleeper's ``previous_league_id`` chain back to the league's first season
(§resolve_league_chain, §run_chain_transaction_capture). The live chain forced one design
decision that a same-resolver-for-every-season extension would have got silently wrong:
**``roster_id`` -> owner is a per-league-season fact, not a league fact.** Measured on David's
own chain 2026-07-30, three of twelve roster slots changed hands across the four seasons, so
reusing the current season's manager map would have filed a departed manager's moves under the
manager who later took that slot — a wrong answer wearing a confident face. Every season is
therefore normalized against a resolver built from **its own** ``/rosters`` + ``/users``
(§IdentityResolver.with_managers), and identity coverage is reported **per season** so a
season that resolves worse than its neighbours stays visible instead of averaging away.
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

SCHEMA_VERSION = "league_transactions.v3"

#: Legs Sleeper exposes. Off-season activity lands in leg 1; regular season uses 1-18.
DEFAULT_LEGS: tuple[int, ...] = tuple(range(1, 19))

#: A dynasty league that has run 40 seasons predates Sleeper. Hitting this cap means the
#: chain is malformed, not that the league is ancient — so it is a named failure, not a stop.
MAX_CHAIN_DEPTH = 40

#: Sleeper terminates a chain with ``null``; ``"0"`` is its sentinel for "no id" in adjacent
#: league/draft fields. Both are treated as the end of the chain, and nothing else is.
_CHAIN_TERMINATORS = {None, "", "0"}

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

    @staticmethod
    def build_managers(
        rosters: Iterable[Mapping[str, Any]], users: Iterable[Mapping[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        """``roster_id`` -> manager, **for one league-season and no other.**

        Sleeper reissues ``roster_id`` 1..12 in every season of a chain, and the slot can
        change hands between them. On David's own chain (measured 2026-07-30) rosters 2, 3
        and 11 each have a different ``owner_id`` in an earlier season than they do in 2026.
        A map built from one season is therefore **wrong** for another, and wrong silently:
        every movement still gets a confident manager name, just the wrong manager's.
        """
        users_by_id = {str(u.get("user_id")): u for u in users if u.get("user_id")}
        managers: dict[int, dict[str, Any]] = {}
        for roster in rosters:
            roster_id = roster.get("roster_id")
            if roster_id is None:
                continue
            owner_id = roster.get("owner_id")
            user = users_by_id.get(str(owner_id)) or {}
            managers[int(roster_id)] = {
                "owner_user_id": str(owner_id) if owner_id is not None else None,
                "display_name": user.get("display_name"),
            }
        return managers

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

        return cls(
            sleeper_players=players,
            crosswalk_by_sleeper=dict(crosswalk_by_sleeper or {}),
            managers=cls.build_managers(payload.get("rosters") or [], payload.get("users") or []),
        )

    def with_managers(
        self,
        *,
        rosters: Iterable[Mapping[str, Any]],
        users: Iterable[Mapping[str, Any]],
    ) -> "IdentityResolver":
        """This resolver's player universe, re-pointed at another season's manager map.

        The player universe and the crosswalk are season-independent and large; the manager
        map is twelve rows and season-specific. Sharing the former by reference and replacing
        only the latter is what makes per-season attribution cheap enough to be unconditional.
        """
        return IdentityResolver(
            sleeper_players=self.sleeper_players,
            crosswalk_by_sleeper=self.crosswalk_by_sleeper,
            managers=self.build_managers(rosters, users),
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
    """A stable manager key. Display names are mutable and can collide.

    The ``user:`` form is the one that carries a manager across seasons — that continuity is
    the whole point of walking the chain. The ``roster:`` fallback is scoped by league,
    because ``roster_id`` 1..12 is reissued every season and an unscoped fallback would fuse
    four different managers who happened to hold the same slot in four different years.
    """
    user_id = movement.get("manager_user_id")
    if user_id:
        return f"user:{user_id}"
    return f"roster:{movement.get('league_id')}:{movement.get('roster_id')}"


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
                # A movement is uninterpretable without its league-season: `roster_id` is
                # reissued every season and means a different manager in each one.
                "league_id": league_id,
                "season": season,
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
        # Stamped on the coverage itself so a per-season block can never be read as the
        # chain's, and a chain summary can never hide a season that resolved worse.
        "league_id": league_id,
        "season": season,
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
        # Managers get the same treatment players do: a count alone lets an unnamed manager
        # in one season disappear into a chain total, so the roster slots are NAMED. These
        # are per-league-season roster ids and mean nothing outside `league_id` above.
        "managers_total": len({m["roster_id"] for m in capture.movements}),
        "managers_unresolved_roster_ids": sorted(
            {m["roster_id"] for m in managers_unresolved if m["roster_id"] is not None},
            key=str,
        ),
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
    "league_id",
    "season",
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


#: One row per league-season the store has actually captured. Without it the store cannot
#: answer "which seasons do you hold, and did each of them land completely?" except by
#: trusting a status marker that describes only the most recent run.
_SEASON_COLUMNS = (
    "league_id",
    "season",
    "status",
    "legs_attempted",
    "legs_with_activity",
    "legs_empty",
    "transactions_total",
    "movements_total",
    "coverage_json",
    "failure_reason",
    "content_hash",
    "ingested_at",
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
            conn.execute(
                "CREATE TABLE IF NOT EXISTS league_season_capture ("
                + ", ".join(f"{c} TEXT" for c in _SEASON_COLUMNS)
                + ", PRIMARY KEY (league_id))"
            )
            # `CREATE TABLE IF NOT EXISTS` is a no-op against a table from an earlier
            # schema, so a store built by a prior version would otherwise be discovered
            # only by an OperationalError mid-write. Fail closed, by name, up front.
            self._assert_schema(conn, "league_transaction", _TRANSACTION_COLUMNS)
            self._assert_schema(conn, "league_transaction_movement", _MOVEMENT_COLUMNS)
            self._assert_schema(conn, "league_season_capture", _SEASON_COLUMNS)

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
                    "SELECT content_hash, league_id FROM league_transaction "
                    "WHERE transaction_id = ?",
                    (transaction_id,),
                ).fetchone()

                # `transaction_id` is the primary key, so a collision across two seasons of
                # the chain would silently REPLACE one league-season's history with
                # another's. Measured on David's chain 2026-07-30: 932 transactions across
                # four seasons, zero collisions — so this refuses rather than re-keys, and
                # the day Sleeper's assumption stops holding it says so instead of deleting.
                if existing is not None and str(existing["league_id"]) != str(row["league_id"]):
                    raise TransactionCaptureError(
                        f"league_transaction_id_collision: transaction {transaction_id} is "
                        f"already stored under league {existing['league_id']} and this "
                        f"capture assigns it to league {row['league_id']} — refusing to "
                        "overwrite one league-season's history with another's"
                    )

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

    def record_season(
        self,
        *,
        league_id: str,
        season: str,
        status: str,
        legs_attempted: Sequence[int] = (),
        legs_with_activity: Sequence[int] = (),
        legs_empty: Sequence[int] = (),
        transactions_total: int | None = None,
        movements_total: int | None = None,
        coverage: Mapping[str, Any] | None = None,
        failure_reason: str | None = None,
        ingested_at: str | None = None,
    ) -> str:
        """Record what this league-season's capture actually did. Returns the applied state.

        A season that failed gets a row saying so. That is the difference between a store
        that holds three of four seasons and a store that *looks* like it holds four —
        the same "silence is not success" property the status marker has, but durable in
        the data rather than in a file describing only the latest run.

        Content-addressed like the transaction rows: an unchanged re-capture leaves the row
        byte-identical, including its original ``ingested_at``, so idempotence stays
        provable by content across the whole store.
        """
        payload = {
            "league_id": str(league_id),
            "season": str(season),
            "status": status,
            "legs_attempted": json.dumps([int(v) for v in legs_attempted]),
            "legs_with_activity": json.dumps([int(v) for v in legs_with_activity]),
            "legs_empty": json.dumps([int(v) for v in legs_empty]),
            "transactions_total": transactions_total,
            "movements_total": movements_total,
            "coverage_json": json.dumps(coverage or {}, sort_keys=True, default=str),
            "failure_reason": failure_reason,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT content_hash FROM league_season_capture WHERE league_id = ?",
                (str(league_id),),
            ).fetchone()
            if existing is not None and existing["content_hash"] == digest:
                return "unchanged"
            payload["content_hash"] = digest
            payload["ingested_at"] = ingested_at or datetime.now(timezone.utc).isoformat()
            conn.execute(
                f"INSERT OR REPLACE INTO league_season_capture "
                f"({', '.join(_SEASON_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _SEASON_COLUMNS)})",
                [payload.get(c) for c in _SEASON_COLUMNS],
            )
            return "inserted" if existing is None else "updated"

    def seasons(self) -> list[dict[str, Any]]:
        """Which league-seasons this store holds, newest first, with each one's own status."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM league_season_capture ORDER BY season DESC, league_id DESC"
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            for key in ("legs_attempted", "legs_with_activity", "legs_empty"):
                record[key] = json.loads(record[key]) if record.get(key) else []
            record["coverage"] = json.loads(record.pop("coverage_json") or "{}")
            for key in ("transactions_total", "movements_total"):
                record[key] = int(record[key]) if record.get(key) is not None else None
            out.append(record)
        return out

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
            rows += [
                tuple(r)
                for r in conn.execute(
                    "SELECT * FROM league_season_capture ORDER BY league_id"
                ).fetchall()
            ]
        return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()

    def manager_activity(self, *, season: str | None = None) -> dict[str, dict[str, Any]]:
        """What every manager actually did — completed movements only, newest first.

        Keyed by a stable manager key, never by display name: display names are mutable
        and two managers can share one. With ``season`` omitted this spans every season the
        store holds, which is the point of walking the chain; pass one to scope it.

        ``display_name`` is taken from the manager's **most recent** movement, because a
        display name is a mutable label and the four-season history of one manager should
        not be filed under whatever they called themselves in 2023.
        """
        query = (
            "SELECT * FROM league_transaction_movement WHERE transaction_status = ?"
            + (" AND season = ?" if season is not None else "")
            + " ORDER BY created_at DESC"
        )
        params: tuple[Any, ...] = (COMPLETE,) if season is None else (COMPLETE, str(season))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
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
# The league chain — every prior season of the same league
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeagueChainLink:
    """One league-season in the ``previous_league_id`` chain."""

    league_id: str
    season: str
    previous_league_id: str | None
    name: str | None = None
    status: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "league_id": self.league_id,
            "season": self.season,
            "previous_league_id": self.previous_league_id,
            "name": self.name,
            "status": self.status,
        }


def _chain_terminates(previous_league_id: Any) -> bool:
    if previous_league_id is None:
        return True
    return str(previous_league_id).strip() in _CHAIN_TERMINATORS


def resolve_league_chain(
    league_id: str,
    *,
    fetch_league: Callable[[str], Mapping[str, Any] | None],
    max_depth: int = MAX_CHAIN_DEPTH,
) -> list[LeagueChainLink]:
    """Walk ``previous_league_id`` from ``league_id`` back to the league's first season.

    Returns newest-first, terminating only when Sleeper says the chain ends.

    **A short chain and a broken chain are not the same thing, and this refuses to let
    them look alike.** If a league in the middle of the chain cannot be read, that is a
    named failure — never a quietly truncated history that a later run would report as a
    complete one. Same for a cycle and for an implausible depth: both raise with the
    partial chain named, because a traversal that silently stops is exactly how a manager
    ends up with three seasons of behaviour when they have four.
    """
    links: list[LeagueChainLink] = []
    seen: set[str] = set()
    current: str | None = str(league_id)
    referrer: str | None = None

    while current is not None:
        walked = [link.league_id for link in links]
        if current in seen:
            raise TransactionCaptureError(
                f"league_chain_cycle: league {current} is reachable from itself via "
                f"previous_league_id on {referrer}; walked {walked} — refusing to loop"
            )
        if len(links) >= max_depth:
            raise TransactionCaptureError(
                f"league_chain_too_deep: exceeded {max_depth} seasons at league {current}; "
                f"walked {walked} — the chain is malformed rather than long"
            )
        seen.add(current)

        try:
            payload = fetch_league(current)
        except Exception as exc:
            raise TransactionCaptureError(
                f"league_chain_broken: league {current} could not be read"
                + (f" (referred to by previous_league_id on {referrer})" if referrer else "")
                + f"; walked {walked} — a partial chain is a failure, not a short history: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if not payload:
            raise TransactionCaptureError(
                f"league_chain_broken: league {current} returned no league record"
                + (f" (referred to by previous_league_id on {referrer})" if referrer else "")
                + f"; walked {walked} — a partial chain is a failure, not a short history"
            )

        season = payload.get("season")
        if season is None or str(season).strip() == "":
            raise TransactionCaptureError(
                f"league_chain_missing_season: league {current} has no season; walked "
                f"{walked} — a league-season cannot be stored without knowing which season"
            )

        previous = payload.get("previous_league_id")
        previous_id = None if _chain_terminates(previous) else str(previous).strip()
        links.append(
            LeagueChainLink(
                league_id=str(payload.get("league_id") or current),
                season=str(season),
                previous_league_id=previous_id,
                name=payload.get("name"),
                status=payload.get("status"),
            )
        )
        referrer = current
        current = previous_id

    return links


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
    # The league-season is in the FILENAME: one chain run writes one snapshot per season at
    # the same `captured_at`, and a timestamp-only name would have them overwrite each other.
    # The stamp is reduced to [0-9A-Za-z] so an ISO offset's `+` and the fractional second's
    # `.` never reach a shell glob or a path-splitting consumer.
    stamp = "".join(ch for ch in captured_at if ch.isalnum())
    path = raw_dir / f"transactions_{season}_{league_id}_{stamp}.json"
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


class _StageFailure(Exception):
    """Internal: carries WHICH stage broke, so a marker can name it rather than guess."""

    def __init__(self, stage: str, cause: BaseException, *, leg: int | None = None) -> None:
        super().__init__(str(cause))
        self.stage = stage
        self.cause = cause
        self.leg = leg

    @property
    def reason(self) -> str:
        return f"{type(self.cause).__name__}: {self.cause}"


def _capture_league_season(
    *,
    league_id: str,
    season: str,
    fetch_leg: Callable[[int], Sequence[Mapping[str, Any]]],
    resolver: IdentityResolver,
    legs_attempted: Sequence[int],
    store: TransactionStore,
    raw_root: Path,
    captured_at: str,
) -> dict[str, Any]:
    """Fetch -> raw snapshot -> normalize -> store, for exactly one league-season.

    The shared primitive behind both the single-season and the chain entry points, so the
    two cannot drift apart in what they store or in how honestly they fail. Raises
    ``_StageFailure`` naming the stage (and leg) so the caller writes a specific marker.
    """
    fetched: dict[str, list[dict[str, Any]]] = {}
    legs_empty: list[int] = []
    leg: int | None = None
    try:
        for leg in legs_attempted:
            payload = fetch_leg(leg) or []
            if payload:
                fetched[str(leg)] = [dict(item) for item in payload]
            else:
                legs_empty.append(leg)
    except Exception as exc:
        raise _StageFailure("fetch", exc, leg=leg) from exc

    try:
        raw_path = write_raw_snapshot(
            fetched,
            league_id=league_id,
            season=season,
            captured_at=captured_at,
            legs_attempted=legs_attempted,
            legs_empty=legs_empty,
            raw_root=raw_root,
        )
    except Exception as exc:
        raise _StageFailure("raw_snapshot", exc) from exc

    try:
        capture = normalize_transactions(
            fetched, league_id=league_id, season=season, resolver=resolver
        )
    except Exception as exc:
        raise _StageFailure("normalize", exc) from exc

    try:
        applied = store.upsert(capture, ingested_at=captured_at)
    except Exception as exc:
        raise _StageFailure("store", exc) from exc

    legs_with_activity = sorted(int(value) for value in fetched)
    store.record_season(
        league_id=league_id,
        season=season,
        status="ok",
        legs_attempted=legs_attempted,
        legs_with_activity=legs_with_activity,
        legs_empty=legs_empty,
        transactions_total=len(capture.transactions),
        movements_total=len(capture.movements),
        coverage=capture.coverage,
        ingested_at=captured_at,
    )
    return {
        "league_id": league_id,
        "season": season,
        "legs_attempted": list(legs_attempted),
        "legs_with_activity": legs_with_activity,
        "legs_empty": legs_empty,
        "raw_snapshot": str(raw_path),
        "applied": applied,
        "coverage": capture.coverage,
    }


def _record_season_failure(
    store: TransactionStore | None,
    *,
    league_id: str,
    season: str,
    reason: str,
    legs_attempted: Sequence[int],
    captured_at: str,
) -> None:
    """Best-effort: the store should say a season failed, not omit it into ambiguity.

    Swallows its own errors deliberately. This runs on an already-failing path and its job
    is to add information; it must never replace the real failure with a bookkeeping one.
    """
    if store is None:
        return
    try:
        store.record_season(
            league_id=league_id,
            season=season,
            status="failed",
            legs_attempted=legs_attempted,
            failure_reason=reason,
            ingested_at=captured_at,
        )
    except Exception:  # noqa: BLE001 - never mask the originating failure
        pass


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

    One league-season. For every prior season of the same league, see
    ``run_chain_transaction_capture``.

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

    store: TransactionStore | None = None
    try:
        try:
            store = TransactionStore(db_path)
        except Exception as exc:
            raise _StageFailure("store_open", exc) from exc
        result = _capture_league_season(
            league_id=league_id,
            season=season,
            fetch_leg=fetch_leg,
            resolver=resolver,
            legs_attempted=legs_attempted,
            store=store,
            raw_root=raw_root,
            captured_at=started_at,
        )
    except _StageFailure as failure:
        _record_season_failure(
            store,
            league_id=league_id,
            season=season,
            reason=failure.reason,
            legs_attempted=legs_attempted,
            captured_at=started_at,
        )
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_stage": failure.stage,
                **({"failed_leg": failure.leg} if failure.leg is not None else {}),
                "reason": failure.reason,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if failure.stage == "fetch":
            raise TransactionCaptureError(
                f"leg {failure.leg} fetch failed: {failure.cause}"
            ) from failure.cause
        raise failure.cause from None

    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "legs_with_activity": result["legs_with_activity"],
        "legs_empty": result["legs_empty"],
        "raw_snapshot": result["raw_snapshot"],
        "db_path": str(db_path),
        "applied": result["applied"],
        "transactions_stored": store.transaction_count(),
        "movements_stored": store.movement_count(),
        **result["coverage"],
    }
    _atomic_write_json(marker, status)
    return status


def run_chain_transaction_capture(
    *,
    league_id: str,
    fetch_league: Callable[[str], Mapping[str, Any] | None],
    fetch_leg: Callable[[str, int], Sequence[Mapping[str, Any]]],
    build_resolver: Callable[[LeagueChainLink], IdentityResolver],
    legs: Sequence[int] = DEFAULT_LEGS,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    max_depth: int = MAX_CHAIN_DEPTH,
) -> dict[str, Any]:
    """Capture EVERY season of the league, walking ``previous_league_id`` back to the first.

    ``build_resolver`` is supplied per link rather than once, because the manager map is a
    per-league-season fact (§IdentityResolver.build_managers). Passing one resolver for the
    whole chain is the defect this signature exists to make impossible to write by accident.

    Failure semantics, in order of how badly each was wanted:

    - The marker is written ``running`` **before chain discovery**, so a run that dies at any
      point never leaves the previous run's ``ok`` standing.
    - A chain that cannot be fully walked fails at discovery, **before anything is fetched**.
      A partial history is never published as a whole one.
    - A season that fails mid-chain writes ``status=failed`` naming the league, the season,
      the stage and (for a fetch) the leg — and names ``seasons_captured``, so what did land
      is a stated fact rather than an inference. Earlier seasons keep their real data; the
      store's own ``league_season_capture`` table records which seasons are ok and which are
      not, so the DB stays honest without reference to this marker.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"chain-{league_id}-{started_at.replace(':', '').replace('-', '')}"
    marker = status_marker_path(raw_root)
    legs_attempted = [int(leg) for leg in legs]

    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "mode": "chain",
        "root_league_id": str(league_id),
        "legs_attempted": legs_attempted,
    }
    _atomic_write_json(marker, {**base, "status": "running", "phase": "chain_discovery"})

    try:
        chain = resolve_league_chain(
            league_id, fetch_league=fetch_league, max_depth=max_depth
        )
    except Exception as exc:
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_stage": "chain_discovery",
                "chain_complete": False,
                "seasons_captured": [],
                "reason": f"{type(exc).__name__}: {exc}",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise

    chain_rows = [link.as_dict() for link in chain]
    _atomic_write_json(
        marker,
        {
            **base,
            "status": "running",
            "phase": "capture",
            "chain": chain_rows,
            "seasons_in_chain": len(chain),
        },
    )

    store: TransactionStore | None = None
    captured: list[dict[str, Any]] = []
    try:
        try:
            store = TransactionStore(db_path)
        except Exception as exc:
            raise _StageFailure("store_open", exc) from exc

        for link in chain:
            try:
                resolver = build_resolver(link)
            except Exception as exc:
                raise _StageFailure("resolver", exc) from exc
            result = _capture_league_season(
                league_id=link.league_id,
                season=link.season,
                fetch_leg=lambda leg, _lid=link.league_id: fetch_leg(_lid, leg),
                resolver=resolver,
                legs_attempted=legs_attempted,
                store=store,
                raw_root=raw_root,
                captured_at=started_at,
            )
            captured.append(result)
    except _StageFailure as failure:
        # `store_open` fails before any season is attempted, so it belongs to no link.
        # Naming chain[0] there would blame a season the run never reached.
        failed_link = (
            chain[len(captured)]
            if failure.stage != "store_open" and len(captured) < len(chain)
            else None
        )
        if failed_link is not None:
            _record_season_failure(
                store,
                league_id=failed_link.league_id,
                season=failed_link.season,
                reason=failure.reason,
                legs_attempted=legs_attempted,
                captured_at=started_at,
            )
        _atomic_write_json(
            marker,
            {
                **base,
                "status": "failed",
                "failed_stage": failure.stage,
                "failed_league_id": failed_link.league_id if failed_link else None,
                "failed_season": failed_link.season if failed_link else None,
                **({"failed_leg": failure.leg} if failure.leg is not None else {}),
                "reason": failure.reason,
                "chain": chain_rows,
                "chain_complete": True,
                "seasons_in_chain": len(chain),
                "seasons_captured": [
                    {"league_id": r["league_id"], "season": r["season"]} for r in captured
                ],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise failure.cause from None

    stored_leagues = {str(row["league_id"]) for row in store.seasons()}
    status = {
        **base,
        "status": "ok",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "chain": chain_rows,
        # True by construction: `resolve_league_chain` raises rather than returning a
        # partial walk. Stated anyway so a reader of the marker never has to know that.
        "chain_complete": True,
        "seasons_in_chain": len(chain),
        "seasons": [
            {
                "league_id": r["league_id"],
                "season": r["season"],
                "legs_with_activity": r["legs_with_activity"],
                "applied": r["applied"],
                "coverage": r["coverage"],
            }
            for r in captured
        ],
        # A season the store holds that THIS run did not touch. Not an error — a league can
        # legitimately be re-pointed — but it is the kind of thing that should never be
        # discovered by surprise later.
        "seasons_in_store_not_in_this_run": sorted(
            stored_leagues - {link.league_id for link in chain}
        ),
        "db_path": str(db_path),
        "transactions_stored": store.transaction_count(),
        "movements_stored": store.movement_count(),
        "chain_coverage": _chain_coverage(captured),
    }
    _atomic_write_json(marker, status)
    return status


def _chain_coverage(captured: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Chain totals that cannot hide a season.

    The three-valued identity outcome survives aggregation: totals are reported alongside
    a per-season breakdown and an explicit list of the seasons that carry an unresolved
    player or an unnamed manager. A single chain-level number is exactly how "97 of 99
    resolved" becomes "resolved", which is the failure the three-valued outcome exists to
    prevent — so the summary names the seasons rather than smoothing them.
    """
    seasons = [dict(row["coverage"]) for row in captured]
    totals = {
        key: sum(int(block.get(key) or 0) for block in seasons)
        for key in (
            "transactions_total",
            "movements_total",
            "players_total",
            "players_canonical_resolved",
            "players_sleeper_only",
            "players_unknown",
            "players_not_canonically_identified",
        )
    }
    return {
        **totals,
        "seasons_captured": len(seasons),
        "sleeper_only_ids": sorted(
            {pid for block in seasons for pid in (block.get("sleeper_only_ids") or [])}
        ),
        "unknown_ids": sorted(
            {pid for block in seasons for pid in (block.get("unknown_ids") or [])}
        ),
        "seasons_with_unresolved_players": sorted(
            block["season"]
            for block in seasons
            if int(block.get("players_not_canonically_identified") or 0) > 0
        ),
        "seasons_with_unresolved_managers": sorted(
            block["season"] for block in seasons if int(block.get("managers_unresolved") or 0) > 0
        ),
        "by_season": {block["season"]: block for block in seasons},
    }
