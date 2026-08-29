"""Dual Daily PIT Capture T2 — FantasyCalc capture driver (script/driver layer).

Drives the T1 store (`fc_forward_capture_store`): fetch FantasyCalc current values
(injectable HTTP), map to T1 entries, append (idempotent/immutable), and emit a
machine-readable, aggregate-only capture report. Fail-loud: any retry exhaustion,
fatal HTTP, malformed/empty payload, or store conflict aborts with an `aborted`
report and NO store write — the archive is never left half-written.

Network / sleep / jitter / time are injected so tests never touch the real
endpoint; the scheduled live run (T3) wires the real client.

Design spec: docs/superpowers/specs/2026-06-24-dual-daily-pit-capture-fc-first-brick-design.md
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from src.dynasty_genius.capture.fc_forward_capture_store import (
    FCForwardCaptureConflictError,
    FCForwardCaptureStore,
    FCForwardCaptureValidationError,
)

_SETTINGS_QUERY = "isDynasty=true&numQbs=2&numTeams=12&ppr=1"
FC_ENDPOINT = f"https://api.fantasycalc.com/values/current?{_SETTINGS_QUERY}"
SETTINGS_HASH = hashlib.sha256(_SETTINGS_QUERY.encode()).hexdigest()[:16]
SOURCE = "fc_native"
MAX_ATTEMPTS = 3
_TRANSIENT_STATUS = frozenset({429})  # plus any 5xx (checked by range)


def _content_hash(payload_fields: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload_fields, sort_keys=True, default=str).encode()
    ).hexdigest()


def _storage_faithful_int(value: Any) -> Any:
    """A float-integral value in an INTEGER-affinity column comes back an int.

    Lossless (`float.is_integer()` gates it); anything else passes through
    untouched so a genuinely fractional or non-numeric value still fails loud
    downstream rather than being coerced here.
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def map_fantasycalc_payload_to_entries(
    payload: list[dict], *, retrieved_at: datetime
) -> list[dict[str, Any]]:
    """Map FantasyCalc rows to T1 store entries (stable player_key + per-row hash).

    DG-050 (measured live, 2026-08-28): `payload_hash` is the row's content
    address and must be re-derivable from the STORED row, so every hashed value
    is normalized here to the exact shape SQLite will return. FantasyCalc sends
    integral volatilities as ints; hashed as `2` but read back from the REAL
    column as `2.0`, the address failed replay on 172 of 474 live rows. Floats
    are hashed for volatility (REAL column), ints for the INTEGER columns —
    both losslessly. Rows captured before this normalization are the
    `legacy_content_shape` vintage the DG-050 replay harness names.
    """
    snapshot_date = retrieved_at.date().isoformat()
    retrieved_iso = retrieved_at.isoformat()
    entries: list[dict[str, Any]] = []
    for row in payload:
        player = row["player"]
        sleeper_id = player.get("sleeperId")
        player_key = f"sleeper:{sleeper_id}" if sleeper_id else f"fc:{player['id']}"
        # Phase-0b: volatility is captured forward. A missing value means FantasyCalc
        # published none (`source_omitted`) — never a bare NULL, which would be
        # indistinguishable from a row predating the schema.
        market_volatility = row.get("maybeMovingStandardDeviation")
        market_volatility_status = (
            "captured" if market_volatility is not None else "source_omitted"
        )
        if isinstance(market_volatility, int) and not isinstance(
            market_volatility, bool
        ):
            # REAL column: an int would round-trip to a float and break the
            # content address (the DG-050 live finding). Lossless widening.
            market_volatility = float(market_volatility)
        value = _storage_faithful_int(row.get("value"))
        overall_rank = _storage_faithful_int(row.get("overallRank"))
        position_rank = _storage_faithful_int(row.get("positionRank"))
        trend_30day = _storage_faithful_int(row.get("trend30Day"))
        content = {
            "sleeper_id": sleeper_id,
            "player_name": player.get("name"),
            "position": player.get("position"),
            "value": value,
            "overall_rank": overall_rank,
            "position_rank": position_rank,
            "trend_30day": trend_30day,
            "market_volatility": market_volatility,
            "market_volatility_status": market_volatility_status,
        }
        entries.append(
            {
                "snapshot_date": snapshot_date,
                "source": SOURCE,
                "settings_hash": SETTINGS_HASH,
                "player_key": player_key,
                "sleeper_id": sleeper_id,
                "player_name": player.get("name"),
                "position": player.get("position"),
                "value": value,
                "overall_rank": overall_rank,
                "position_rank": position_rank,
                "trend_30day": trend_30day,
                "retrieved_at": retrieved_iso,
                "payload_hash": _content_hash(content),
                "market_volatility": market_volatility,
                "market_volatility_status": market_volatility_status,
            }
        )
    return entries


def _report(
    *,
    status: str,
    snapshot_date: str,
    retrieved_iso: str,
    raw_written: int = 0,
    joinable_written: int = 0,
    missing_sleeper: int = 0,
    duplicate: int = 0,
    payload_hash: Optional[str] = None,
    store_hash: Optional[str] = None,
    aborted_reason: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "snapshot_date": snapshot_date,
        "retrieved_at": retrieved_iso,
        "source": SOURCE,
        "settings_hash": SETTINGS_HASH,
        "endpoint": FC_ENDPOINT,
        "raw_entries_written": raw_written,
        "joinable_rows_written": joinable_written,
        "missing_sleeper_count": missing_sleeper,
        "duplicate_count": duplicate,
        "payload_hash": payload_hash,
        "store_hash": store_hash,
        "aborted_reason": aborted_reason,
        "decision_supported": False,
    }


def _persist(report: dict, report_path: Optional[Path]) -> None:
    if report_path is not None:
        Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True))


def _normalize_payload(data: object) -> tuple[Optional[list], Optional[str]]:
    """Return (players, abort_reason). Accepts a raw list or {'players': [...]}."""
    if isinstance(data, list):
        players = data
    elif isinstance(data, dict) and "players" in data:
        players = data["players"]
    else:
        return None, "malformed_payload"
    if not isinstance(players, list):
        return None, "malformed_payload"
    if not players:
        return None, "empty_payload"
    return players, None


def capture_fantasycalc_snapshot(
    *,
    db_path: Path,
    report_path: Optional[Path] = None,
    fetch_json: Callable[[str], object],
    now_fn: Callable[[], datetime],
    sleep_fn: Callable[[float], None],
    jitter_fn: Callable[[], float],
) -> dict[str, Any]:
    """Capture one daily FantasyCalc snapshot into the T1 store + emit a report.

    Fail-loud: transient (429/5xx/timeout) → bounded retry (max_attempts=3,
    exponential backoff + jitter); retry exhaustion / fatal HTTP / malformed /
    empty / store conflict → `aborted` report, NO store write."""
    retrieved_at = now_fn()
    snapshot_date = retrieved_at.date().isoformat()
    retrieved_iso = retrieved_at.isoformat()

    def abort(reason: str) -> dict[str, Any]:
        report = _report(
            status="aborted",
            snapshot_date=snapshot_date,
            retrieved_iso=retrieved_iso,
            aborted_reason=reason,
        )
        _persist(report, report_path)
        return report

    # ── fetch with bounded retry/backoff ──
    data: object = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            data = fetch_json(FC_ENDPOINT)
            break
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            transient = code in _TRANSIENT_STATUS or 500 <= code < 600
            if not transient:
                return abort(f"fatal_http_{code}")
            if attempt >= MAX_ATTEMPTS:
                return abort(f"retry_exhausted_http_{code}")
            sleep_fn(2 ** (attempt - 1) + jitter_fn())
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt >= MAX_ATTEMPTS:
                return abort("retry_exhausted_timeout")
            sleep_fn(2 ** (attempt - 1) + jitter_fn())

    # ── validate + map (row-level malformed content → aborted, no write) ──
    players, reason = _normalize_payload(data)
    if reason is not None:
        return abort(reason)
    try:
        entries = map_fantasycalc_payload_to_entries(players, retrieved_at=retrieved_at)
    except (KeyError, TypeError, AttributeError):
        return abort("malformed_payload_row")

    # ── append to the T1 store (fail-closed → aborted, no overwrite) ──
    store = FCForwardCaptureStore(db_path)
    try:
        counts = store.append_entries(entries)
    except (FCForwardCaptureConflictError, FCForwardCaptureValidationError) as exc:
        return abort(str(exc))

    raw_written = counts["raw_entries_written"]
    joinable_written = counts["joinable_rows_written"]
    store_hash = _content_hash(
        {"sigs": sorted(e["player_key"] + ":" + e["payload_hash"] for e in entries)}
    )
    report = _report(
        status="ok",
        snapshot_date=snapshot_date,
        retrieved_iso=retrieved_iso,
        raw_written=raw_written,
        joinable_written=joinable_written,
        missing_sleeper=raw_written - joinable_written,
        duplicate=len(entries) - raw_written,
        payload_hash=_content_hash({"players": players}),
        store_hash=store_hash,
        aborted_reason=None,
    )
    _persist(report, report_path)
    return report
