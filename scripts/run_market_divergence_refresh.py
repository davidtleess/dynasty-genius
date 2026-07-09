"""Daily market-divergence refresh runner (Phase 0 — the daily margin recompute).

Turns the already-captured daily market + PVO state into a fresh
``universe_market_divergence`` latest/coverage pair AND a compounding point-in-time
(PIT) history, on a schedule, WITHOUT live network or stale-as-fresh.

Option-C discipline (mirrors ``run_pvo_refresh.py``):
- mutates ONLY the two TRACKED artifacts (``universe_market_divergence_latest.json`` +
  its ``_coverage_latest``) plus the gitignored PIT DB / status marker / report;
- NEVER auto-commits — a dirty tree after a refresh is EXPECTED local state, and
  committing the refreshed baseline is a David-gated action
  (``commit_required_for_repo_baseline=True``);
- backup/restore so a failed publish leaves the tracked pair byte-identical;
- publish honesty: EACH file is written atomically (temp + ``os.replace``), but the
  PAIR is published sequentially (latest, then coverage). This is NOT cross-file
  pair-atomicity — a concurrent reader could observe a fresh latest beside a prior
  coverage for the write window. Eliminating that mixed-pair window (generation
  pointer / combined artifact / dir-swap) is a tracked Phase-0b follow-up;
- fail-closed: unverified runtime PVO, a stale/cold market cache, or a candidate that
  carries a stale-market caveat ABORT before any latest write (stale-as-fresh is an
  active lie, per the 2026-06-23 freshness spec);
- NEVER live-fetches: the market side is read from the already-captured FantasyCalc
  cache only (the daily FC snapshot job owns fetching);
- writes a status marker on EVERY terminal state (silence-is-not-success);
- ``decision_supported=False`` is carried end-to-end (the margin is descriptive, not a
  validated edge).

The PIT history (``market_divergence_history``, gitignored SQLite, PK
``[player_id, capture_date]``, idempotent per-date upsert) is the compounding raw
material for the eventual Gate-4 validation ledger.

The LaunchAgent plist (``ops/launchd/…``) is committable configuration only; installing
it with ``launchctl`` is a separate David-gated machine change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.pvo_source import (  # noqa: E402
    PvoSourceNotReadyError,
    resolve_pvo_source,
)
from src.dynasty_genius.universe_market_divergence import (  # noqa: E402
    build_universe_market_divergence,
)

# ── default tracked artifact + operational paths (overridable via CLI / kwargs) ──
DEFAULT_LATEST_PATH = "app/data/valuation/universe_market_divergence_latest.json"
DEFAULT_COVERAGE_LATEST_PATH = (
    "app/data/valuation/universe_market_divergence_coverage_latest.json"
)
DEFAULT_HISTORY_DB_PATH = "app/data/market_divergence_history.db"
DEFAULT_MARKER_PATH = (
    "app/data/valuation_runtime/market_divergence_refresh_status_latest.json"
)
DEFAULT_REPORT_PATH = (
    "app/data/valuation_runtime/market_divergence_refresh_latest_report.json"
)
DEFAULT_MARKET_CACHE_PATH = "app/cache/fantasycalc/market_values.json"
DEFAULT_PVO_SEED_PATH = "app/data/valuation/universe_pvo_latest.json"
DEFAULT_PVO_COVERAGE_SEED_PATH = "app/data/valuation/universe_pvo_coverage_latest.json"
DEFAULT_PVO_RUNTIME_DIR = "app/data/valuation_runtime"

# Fetch-time is not publish-time: FantasyCalc has no published-at timestamp, so every
# overlay carries this caveat. It is NOT a staleness marker (that is `stale_market_data`).
_FETCH_CAVEAT = "source_timestamp_is_fetch_time_not_publish_time"
# The token the builder stamps on rows when the market snapshot is itself stale. Its
# presence in a candidate means the market side is not trustworthy → refuse to publish.
_STALE_MARKET_TOKEN = "stale_market_data"

_HISTORY_TABLE = "market_divergence_history"

# The owned scheduled market source. `market_values.json` has no scheduled owner — it is
# written only as a side effect of a live fetch — so the scheduled runner reads the FC
# forward-capture PIT store instead. Cache mode survives ONLY as a legacy/manual path.
DEFAULT_FC_SOURCE = "fc_native"
_FC_JOINABLE_TABLE = "fc_forward_capture_joinable"

# Volatility fidelity (Phase-0b §5.6). A pre-migration row has a NULL status: nobody ever
# asked FantasyCalc for that value, so it is neither `captured` nor `source_omitted`.
_STRUCTURALLY_UNAVAILABLE = "structurally_unavailable"
_VOLATILITY_STATUSES = frozenset(
    {"captured", "source_omitted", _STRUCTURALLY_UNAVAILABLE}
)
# The date the volatility schema landed. Rows dated before it can never carry volatility:
# backfilling would mutate an immutable snapshot, which the FC store rejects by design.
VOLATILITY_SCHEMA_EFFECTIVE_DATE = "2026-07-10"


def _season_max_age_hours(now: datetime) -> float:
    """Code-and-season-owned freshness bound. NEVER read from the payload.

    The pre-Phase-0b gate trusted a `ttl_hours` value supplied by the very payload whose
    freshness it was checking — the data decided whether the data was fresh. In-season
    (Aug 16 – Jan 15) the market moves fast enough to demand 6h; off-season, 24h.
    """
    m, d = now.month, now.day
    in_season = (m == 8 and d >= 16) or m in (9, 10, 11, 12) or (m == 1 and d <= 15)
    return 6.0 if in_season else 24.0


class _MarketSourceError(Exception):
    """Carries the fail-closed abort reason for a market-source read."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    """Read a column that may not exist yet.

    The regeneration run (spec §8 step 9) reads rows captured BEFORE the volatility
    schema landed, so the columns are absent from the table entirely — `sqlite3.Row`
    raises `IndexError` rather than returning None. Absent must degrade to a named,
    honest value, not to an unnamed crash.
    """
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def _volatility_status_for_row(row: Any) -> str:
    """Classify a row's volatility fidelity. ABSENT is not the same as INVALID.

    - Column absent (pre-migration table) or NULL (a row the migration back-filled):
      `structurally_unavailable`. It is NOT `source_omitted` — nobody ever asked
      FantasyCalc for that value, and collapsing the two would let a schema gap
      masquerade as a fact about the market.
    - A NON-NULL value outside the enum is CORRUPT and fails closed. Coercing it to
      `structurally_unavailable` would launder corrupt data into an honest-looking
      label — the precise silent-substitution this contract exists to abolish.
    """
    status = _row_get(row, "market_volatility_status")
    if status is None:
        return _STRUCTURALLY_UNAVAILABLE
    if status not in _VOLATILITY_STATUSES:
        raise _MarketSourceError("market_source_volatility_status_invalid")
    return status


def _assert_volatility_consistent(status: str, volatility: Any) -> None:
    """A status must agree with the value it describes, or the row is lying.

    `captured` without a value, or an absent-class status carrying one, is incoherent
    data. Publishing either would put a false fidelity claim into the Gate-4 ledger.
    """
    if status == "captured" and volatility is None:
        raise _MarketSourceError("market_source_volatility_status_invalid")
    if status != "captured" and volatility is not None:
        raise _MarketSourceError("market_source_volatility_status_invalid")


def _read_market_from_fc_pit(
    db_path: Path, *, source: str, settings_hash: str | None, now: datetime
) -> dict[str, Any]:
    """Read the latest owned FC PIT snapshot. Fail closed on ambiguity or a prior date."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise _MarketSourceError("fc_forward_capture_missing")
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        with conn:
            latest = conn.execute(
                f"SELECT MAX(snapshot_date) FROM {_FC_JOINABLE_TABLE} WHERE source = ?",
                (source,),
            ).fetchone()[0]
            if latest is None:
                raise _MarketSourceError("fc_forward_capture_empty")

            hashes = [
                r[0]
                for r in conn.execute(
                    f"SELECT DISTINCT settings_hash FROM {_FC_JOINABLE_TABLE} "
                    "WHERE source = ? AND snapshot_date = ?",
                    (source, latest),
                )
            ]
            if settings_hash is None:
                # Never silently pick a winner: two settings families for one date means we
                # cannot say what "the market" was that day.
                if len(hashes) != 1:
                    raise _MarketSourceError("market_source_ambiguous_settings_hash")
                settings_hash = hashes[0]
            elif settings_hash not in hashes:
                raise _MarketSourceError("fc_forward_capture_settings_hash_absent")

            rows = list(
                conn.execute(
                    f"SELECT * FROM {_FC_JOINABLE_TABLE} "
                    "WHERE source = ? AND snapshot_date = ? AND settings_hash = ? "
                    "ORDER BY overall_rank, player_key",
                    (source, latest, settings_hash),
                )
            )
    except _MarketSourceError:
        raise
    except sqlite3.Error:
        raise _MarketSourceError("fc_forward_capture_unreadable") from None

    if not rows:
        raise _MarketSourceError("fc_forward_capture_empty")
    if str(latest) != now.date().isoformat():
        raise _MarketSourceError("market_source_prior_date")

    fc_response = []
    for r in rows:
        # Raises _MarketSourceError on corrupt fidelity data — before anything is built,
        # published, or written to the compounding history.
        status = _volatility_status_for_row(r)
        volatility = _row_get(r, "market_volatility")
        _assert_volatility_consistent(status, volatility)
        fc_response.append(
            {
                "player": {
                    "sleeperId": r["sleeper_id"],
                    "name": r["player_name"],
                    "position": r["position"],
                },
                "value": r["value"],
                "overallRank": r["overall_rank"],
                "positionRank": r["position_rank"],
                "trend30Day": r["trend_30day"],
                "maybeMovingStandardDeviation": volatility,
                "marketVolatilityStatus": status,
            }
        )
    return {
        "fc_response": fc_response,
        "snapshot_date": str(latest),
        "source_timestamp": rows[0]["retrieved_at"],
        "report": {
            "status": "fresh_fc_forward_capture",
            "snapshot_date": str(latest),
            "retrieved_at": rows[0]["retrieved_at"],
            "settings_hash": settings_hash,
            "db_path": str(db_path),
        },
    }


def _read_market_from_cache(cache_path: Path, *, now: datetime) -> dict[str, Any]:
    """Legacy/manual cache path. Same code-owned freshness law as the PIT path."""
    if not cache_path.exists():
        raise _MarketSourceError("market_cache_missing")
    try:
        market_payload = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, ValueError, OSError):
        raise _MarketSourceError("market_cache_unreadable") from None
    if not isinstance(market_payload, dict):  # valid JSON, wrong shape (e.g. a list)
        raise _MarketSourceError("market_cache_unreadable")

    # `ttl_hours` no longer decides freshness — the payload may not declare its own
    # validity. Its SHAPE is still a contract: a non-numeric value means the writer is
    # broken, and malformed data fails closed (robustness boundary). We validate it and
    # then deliberately discard it.
    if "ttl_hours" in market_payload:
        try:
            float(market_payload["ttl_hours"])
        except (TypeError, ValueError):
            raise _MarketSourceError("market_cache_unreadable") from None

    fetched_at = market_payload.get("fetched_at")
    if fetched_at is None:
        raise _MarketSourceError("market_cache_unreadable")
    try:
        fetched_dt = _parse_dt(fetched_at)
    except (ValueError, TypeError):  # unparseable timestamp: cannot prove freshness
        raise _MarketSourceError("market_cache_unreadable") from None

    # Date first: a prior-date snapshot is prior-date no matter what TTL it claims.
    if fetched_dt.date() != now.date():
        raise _MarketSourceError("market_source_prior_date")
    if (now - fetched_dt).total_seconds() / 3600.0 > _season_max_age_hours(now):
        raise _MarketSourceError("market_cache_stale")

    return {
        "fc_response": market_payload.get("data") or [],
        "snapshot_date": fetched_dt.date().isoformat(),
        "source_timestamp": fetched_at,
        "report": {"status": "fresh_cache", "cache_path": str(cache_path)},
    }


def _missing_volatility_fidelity(batch: dict[str, Any]) -> bool:
    """True if any market-bearing row cannot say what its volatility field means."""
    for row in batch.get("players") or []:
        overlay = row.get("market_overlay")
        if not overlay:
            continue  # no market data at all — nothing to describe
        if overlay.get("market_volatility_status") not in _VOLATILITY_STATUSES:
            return True
        if not row.get("volatility_schema_effective_date"):
            return True
    return False


# ───────────────────────────── small io helpers ─────────────────────────────
def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, tolerating a trailing ``Z`` (UTC)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(f"{path}.tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _default_publish_latest_pair(
    *,
    latest_path: Path,
    coverage_latest_path: Path,
    latest_text: str,
    coverage_text: str,
    **_: Any,
) -> None:
    """Publish the tracked pair, latest first (so a mid-publish failure is detectable)."""
    _atomic_write_text(Path(latest_path), latest_text)
    _atomic_write_text(Path(coverage_latest_path), coverage_text)


def _default_resolver(*, seed_paths: dict, runtime_dir: Path | str):
    """Production default: the fail-closed verified-runtime-or-seed resolver."""
    return resolve_pvo_source(seed_paths=seed_paths, runtime_dir=runtime_dir)


def _has_stale_market(batch: dict[str, Any]) -> bool:
    """True if any candidate row carries a stale-market signal/caveat/note."""
    for row in batch.get("players") or []:
        div = row.get("divergence") or {}
        if div.get("signal") == "SUPPRESSED_STALE_MARKET":
            return True
        if div.get("signal_status") == "gates_blocked":
            return True
        overlay = row.get("market_overlay") or {}
        pools = (
            div.get("notes") or [],
            div.get("failed_gates") or [],
            overlay.get("caveats") or [],
        )
        if any(_STALE_MARKET_TOKEN in pool for pool in pools):
            return True
    return False


def _capture_date(batch: dict[str, Any], *, fallback_iso: str) -> str:
    """The PIT key is the MARKET SNAPSHOT DATE, not the day the runner happened to run.

    Keying the compounding Gate-4 series by the runner's wall clock made the join axis
    wrong: a late run, a UTC-midnight crossing, or a regeneration of an older snapshot all
    filed the row under the wrong day. `captured_at` (build time) is only a fallback for
    callers that supply no market vintage.
    """
    market_snapshot_date = batch.get("market_snapshot_date")
    if market_snapshot_date:
        return str(market_snapshot_date)[:10]
    captured = str(batch.get("captured_at") or fallback_iso)
    return captured[:10]


def _upsert_history(history_db_path: Path, batch: dict[str, Any]) -> int:
    """Idempotently upsert one row per (player_id, capture_date) into the PIT store.

    Re-running the same capture_date updates the payload rather than duplicating —
    the primary key is ``(player_id, capture_date)``. ``decision_supported`` is
    persisted as 0/1 and is always 0 (the margin is descriptive)."""
    history_db_path = Path(history_db_path)
    history_db_path.parent.mkdir(parents=True, exist_ok=True)
    capture_date = _capture_date(batch, fallback_iso=datetime.now(UTC).isoformat())
    upserted = 0
    with sqlite3.connect(str(history_db_path)) as conn:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_HISTORY_TABLE} ("
            "player_id TEXT NOT NULL, "
            "capture_date TEXT NOT NULL, "
            "decision_supported INTEGER NOT NULL, "
            "payload_json TEXT NOT NULL, "
            "PRIMARY KEY (player_id, capture_date))"
        )
        for row in batch.get("players") or []:
            player_id = row.get("sleeper_player_id")
            if player_id is None:
                continue
            div = row.get("divergence") or {}
            decision_supported = 1 if div.get("decision_supported") else 0
            conn.execute(
                f"INSERT INTO {_HISTORY_TABLE} "
                "(player_id, capture_date, decision_supported, payload_json) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(player_id, capture_date) DO UPDATE SET "
                "decision_supported=excluded.decision_supported, "
                "payload_json=excluded.payload_json",
                (
                    str(player_id),
                    capture_date,
                    decision_supported,
                    json.dumps(row, sort_keys=True),
                ),
            )
            upserted += 1
        conn.commit()
    return upserted


def _write_marker(marker_path: Path, marker: dict[str, Any]) -> None:
    _atomic_write_text(Path(marker_path), json.dumps(marker, indent=2, sort_keys=True) + "\n")


def _persist_report(report_path: Optional[Path], report: dict[str, Any]) -> dict[str, Any]:
    if report_path is not None:
        _atomic_write_text(
            Path(report_path), json.dumps(report, indent=2, sort_keys=True)
        )
    return report


# ────────────────────────────── the runner ──────────────────────────────
def run_market_divergence_refresh(
    *,
    latest_path: Path,
    coverage_latest_path: Path,
    history_db_path: Path,
    marker_path: Path,
    report_path: Optional[Path] = None,
    market_cache_path: Path = Path(DEFAULT_MARKET_CACHE_PATH),
    fc_forward_capture_db_path: Optional[Path] = None,
    fc_source: str = DEFAULT_FC_SOURCE,
    fc_settings_hash: Optional[str] = None,
    pvo_seed_path: Optional[Path] = None,
    pvo_coverage_seed_path: Optional[Path] = None,
    pvo_runtime_dir: Optional[Path] = None,
    resolve_pvo_source_fn: Optional[Callable[..., Any]] = None,
    build_fn: Optional[Callable[..., dict[str, Any]]] = None,
    publish_latest_pair_fn: Optional[Callable[..., None]] = None,
    now_fn: Optional[Callable[[], datetime]] = None,
    allow_seed: bool = False,
) -> dict[str, Any]:
    """Recompute the tracked divergence pair from captured state and upsert PIT history.

    Fail-closed and stage-ordered: pvo_source → market_source → build → validation →
    publish → history. Every terminal state writes a status marker and (if given) a
    report. The tracked pair is restored byte-identical on any publish failure; the
    PIT DB is touched only after a successful publish."""
    latest_path = Path(latest_path)
    coverage_latest_path = Path(coverage_latest_path)
    history_db_path = Path(history_db_path)
    marker_path = Path(marker_path)
    market_cache_path = Path(market_cache_path)
    resolve_pvo_source_fn = resolve_pvo_source_fn or _default_resolver
    build_fn = build_fn or build_universe_market_divergence
    publish_latest_pair_fn = publish_latest_pair_fn or _default_publish_latest_pair
    now_fn = now_fn or (lambda: datetime.now(UTC))
    now = now_fn()

    def _degraded(reason: str) -> None:
        _write_marker(
            marker_path,
            {
                "status": "degraded",
                "reason": reason,
                "decision_supported": False,
                "finished_at": now.isoformat(),
            },
        )

    def _abort(stage: str, reason: str, **extra: Any) -> dict[str, Any]:
        _degraded(reason)
        report = {
            "status": "aborted",
            "aborted_stage": stage,
            "aborted_reason": reason,
            "decision_supported": False,
            "commit_required_for_repo_baseline": False,
            "dirty_paths": [],
            "forbidden_commands_attempted": [],
            **extra,
        }
        return _persist_report(report_path, report)

    # Backstop: ANY unhandled exception below is still a terminal state and MUST leave a
    # degraded marker (silence-is-not-success). The staged _abort() returns give precise
    # reasons for the known failures; this guard guarantees no future/edge path dies silent.
    try:
        # 1. Resolve the model side (verified runtime, else seed) — fail closed. ─────────
        seed_paths = {
            "pvo": str(pvo_seed_path or DEFAULT_PVO_SEED_PATH),
            "coverage": str(pvo_coverage_seed_path or DEFAULT_PVO_COVERAGE_SEED_PATH),
        }
        try:
            resolved = resolve_pvo_source_fn(
                seed_paths=seed_paths,
                runtime_dir=pvo_runtime_dir or DEFAULT_PVO_RUNTIME_DIR,
            )
        except PvoSourceNotReadyError as exc:
            return _abort("pvo_source", f"pvo_source_not_ready:{exc}")
        except Exception as exc:  # any resolver failure is terminal, never silent
            return _abort("pvo_source", f"pvo_source_error:{type(exc).__name__}")

        source_kind = getattr(resolved, "source_kind", "seed")
        if source_kind == "seed" and not allow_seed:
            return _abort(
                "pvo_source",
                "runtime_pvo_absent_seed_disallowed",
                pvo_source_kind="seed",
            )

        # 2. Read the already-captured market snapshot — NO live network. ────────────────
        #    The owned scheduled source is the FC forward-capture PIT store. The cache path
        #    survives only as a legacy/manual compatibility mode, under the same freshness law.
        try:
            if fc_forward_capture_db_path is not None:
                market = _read_market_from_fc_pit(
                    Path(fc_forward_capture_db_path),
                    source=fc_source,
                    settings_hash=fc_settings_hash,
                    now=now,
                )
            else:
                market = _read_market_from_cache(market_cache_path, now=now)
        except _MarketSourceError as exc:
            return _abort("market_source", exc.reason)

        # 3. Build the candidate divergence from the resolved PVO + fresh market. ─────────
        try:
            pvo_batch = json.loads(Path(resolved.pvo_path).read_text())
            captured_at = now.isoformat()
            candidate = build_fn(
                pvo_batch,
                market["fc_response"],
                fetch_caveats=[_FETCH_CAVEAT],
                captured_at=captured_at,
                market_snapshot_date=market["snapshot_date"],
                market_source_timestamp=market["source_timestamp"],
                volatility_schema_effective_date=VOLATILITY_SCHEMA_EFFECTIVE_DATE,
            )
        except Exception as exc:  # malformed PVO / builder failure is terminal, never silent
            return _abort("build", f"build_failed:{type(exc).__name__}")

        # 4. Refuse to publish a candidate that itself carries a stale-market caveat. ─────
        if _has_stale_market(candidate):
            return _abort("validation", "stale_market_data_in_candidate")

        # 4b. Refuse to publish — or to write PIT history — when a market-bearing row cannot
        #     say what its volatility field means. A silently-degraded compounding row is
        #     worse than no row: it reads as equivalent to a fully-captured one forever.
        if _missing_volatility_fidelity(candidate):
            return _abort("validation", "market_volatility_fidelity_missing")

        # 5. Publish the tracked pair (each file atomic; the pair is latest-then-coverage,
        #    NOT cross-file atomic — see module docstring). Restore byte-identical on fail.
        try:
            backup_latest = latest_path.read_bytes()
            backup_coverage = coverage_latest_path.read_bytes()
        except OSError as exc:  # tracked pair unreadable → cannot safely publish
            return _abort("publish", f"tracked_pair_unreadable:{type(exc).__name__}")
        latest_text = json.dumps(candidate, indent=2, sort_keys=True) + "\n"
        coverage_text = (
            json.dumps(candidate.get("coverage", {}), indent=2, sort_keys=True) + "\n"
        )
        try:
            publish_latest_pair_fn(
                latest_path=latest_path,
                coverage_latest_path=coverage_latest_path,
                latest_text=latest_text,
                coverage_text=coverage_text,
            )
        except Exception as exc:  # partial/failed publish → restore both, no history write
            latest_path.write_bytes(backup_latest)
            coverage_latest_path.write_bytes(backup_coverage)
            return _abort("publish", str(exc), restored_from_backup=True)

        dirty_paths: list[str] = []
        if latest_path.read_bytes() != backup_latest:
            dirty_paths.append(str(latest_path))
        if coverage_latest_path.read_bytes() != backup_coverage:
            dirty_paths.append(str(coverage_latest_path))

        # 6. Append to the compounding PIT history (only after a successful publish). ─────
        # The publish already succeeded (the tracked pair is fresh), so a history failure
        # does NOT restore the pair — it records a degraded terminal state (never silent).
        try:
            history_upserted_rows = _upsert_history(history_db_path, candidate)
        except Exception as exc:
            return _abort(
                "history",
                f"history_write_failed:{type(exc).__name__}",
                restored_from_backup=False,
                dirty_paths=sorted(dirty_paths),
                commit_required_for_repo_baseline=True,
            )

        # 7. Success marker + report (silence-is-not-success). ───────────────────────────
        is_runtime = source_kind == "runtime"
        _write_marker(
            marker_path,
            {
                "status": "ok",
                "decision_supported": False,
                "latest_sha256": _sha(latest_path),
                "coverage_sha256": _sha(coverage_latest_path),
                "finished_at": now.isoformat(),
            },
        )
        report = {
            "status": "ok",
            "decision_supported": False,
            "pvo_source_kind": source_kind,
            "pvo_runtime_verified": is_runtime,
            "freshness_claimed": is_runtime,
            # Both halves of the basis are derived, never asserted: a report that says
            # "fresh_market_cache" while reading the FC PIT store is itself false provenance.
            "freshness_basis": (
                f"{'runtime_verified_pvo' if is_runtime else 'seed_pvo_baseline'}"
                f"_and_{market['report']['status']}"
            ),
            "market_source": market["report"],
            "commit_required_for_repo_baseline": True,
            "dirty_paths": sorted(dirty_paths),
            "history_db_path": str(history_db_path),
            "history_upserted_rows": history_upserted_rows,
            "forbidden_commands_attempted": [],
            "aborted_reason": None,
        }
        return _persist_report(report_path, report)
    except Exception as exc:  # backstop: never let a terminal state be silent
        return _abort("unexpected", f"unexpected_error:{type(exc).__name__}")


def inspect_market_divergence_refresh_status(
    *,
    marker_path: Path,
    now_fn: Callable[[], datetime],
    interval_hours: float,
    grace_hours: float,
) -> dict[str, Any]:
    """Read the status marker; absent or older than interval+grace is degraded.

    Silence-is-not-success: a missing marker or one whose ``finished_at`` is stale is a
    degraded state, not a healthy one."""
    marker_path = Path(marker_path)
    if not marker_path.exists():
        return {"status": "degraded", "reason": "marker_absent", "decision_supported": False}
    marker = json.loads(marker_path.read_text())
    finished_at = marker.get("finished_at")
    if finished_at is None:
        return {"status": "degraded", "reason": "marker_absent", "decision_supported": False}
    age_hours = (now_fn() - _parse_dt(finished_at)).total_seconds() / 3600.0
    if age_hours > interval_hours + grace_hours:
        return {"status": "degraded", "reason": "marker_stale", "decision_supported": False}
    return {"status": "ok", "decision_supported": False}


# ────────────────────────────── CLI ──────────────────────────────
def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompute the tracked market-divergence pair from captured state "
        "(daily margin recompute; never live-fetches, never commits)."
    )
    parser.add_argument("--latest-path", default=DEFAULT_LATEST_PATH)
    parser.add_argument("--coverage-latest-path", default=DEFAULT_COVERAGE_LATEST_PATH)
    parser.add_argument("--history-db-path", default=DEFAULT_HISTORY_DB_PATH)
    parser.add_argument("--marker-path", default=DEFAULT_MARKER_PATH)
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--market-cache-path",
        default=DEFAULT_MARKET_CACHE_PATH,
        help="LEGACY/manual cache path. The scheduled job must pass "
        "--fc-forward-capture-db-path instead: the cache has no scheduled owner.",
    )
    parser.add_argument(
        "--fc-forward-capture-db-path",
        default=None,
        help="The OWNED scheduled market source (FC forward-capture PIT store). "
        "When given, the orphan cache is not read at all.",
    )
    parser.add_argument("--fc-source", default=DEFAULT_FC_SOURCE)
    parser.add_argument(
        "--fc-settings-hash",
        default=None,
        help="Pin the FC settings family. Omitted, the runner aborts if a snapshot date "
        "carries more than one settings_hash rather than silently picking one.",
    )
    parser.add_argument("--pvo-seed-path", default=DEFAULT_PVO_SEED_PATH)
    parser.add_argument("--pvo-coverage-seed-path", default=DEFAULT_PVO_COVERAGE_SEED_PATH)
    parser.add_argument("--pvo-runtime-dir", default=DEFAULT_PVO_RUNTIME_DIR)
    parser.add_argument(
        "--allow-seed",
        action="store_true",
        help="Permit a seed-PVO refresh when no verified runtime is present. The output "
        "is explicitly NOT freshness-claimed (pvo_source_kind=seed).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_market_divergence_refresh(
        latest_path=Path(args.latest_path),
        coverage_latest_path=Path(args.coverage_latest_path),
        history_db_path=Path(args.history_db_path),
        marker_path=Path(args.marker_path),
        report_path=Path(args.report_path),
        market_cache_path=Path(args.market_cache_path),
        fc_forward_capture_db_path=(
            Path(args.fc_forward_capture_db_path)
            if args.fc_forward_capture_db_path
            else None
        ),
        fc_source=args.fc_source,
        fc_settings_hash=args.fc_settings_hash,
        pvo_seed_path=Path(args.pvo_seed_path),
        pvo_coverage_seed_path=Path(args.pvo_coverage_seed_path),
        pvo_runtime_dir=Path(args.pvo_runtime_dir),
        allow_seed=args.allow_seed,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
