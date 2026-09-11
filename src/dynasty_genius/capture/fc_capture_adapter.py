"""Preserve a receipted FantasyCalc capture out of the normalized store (DG-223).

**The original HTTP bytes are gone.** The collector hashes the payload it received and writes that
hash into its success receipt, then normalizes the rows into SQLite — but the response body itself is
never retained, and the receipt file is `fc_forward_capture_latest_report.json`, overwritten every
morning. So for exactly one capture at a time there exists independent evidence of a complete
retrieval, and for every earlier date there does not.

What that evidence can still prove is precise, and this module claims no more than it:

* every stored row re-derives its own `payload_hash` from its stored values, under the DG-050
  content-address convention (`fc_forward_capture_driver.map_fantasycalc_payload_to_entries`);
* the store hash over those rows equals the `store_hash` the collector recorded at capture time;
* the row counts and metadata equal the receipt's.

Together those attest **a complete normalized capture**. They do not attest the HTTP response, and
this module never says they do. A pack built here carries a provenance block stating exactly that,
and its `capture_report` is the collector's own receipt, unaltered.

Three refusals are deliberate and load-bearing:

**A row whose hash does not re-derive refuses the whole capture.** Those are the DG-050
`legacy_content_shape` vintage. Re-hashing them would manufacture the very attestation that is
missing — the digest would verify perfectly and mean nothing.

**A second capture for an identity that already exists, with different content, refuses.** Silently
replacing it would rewrite history; the caller decides what a correction means.

**A receipt that changes while the rows are being read refuses.** The collector rewrites that file
each morning; pairing one capture's receipt with another's rows is the one way these two sources can
disagree without either being corrupt.

Absence is not corruption. No receipt yet, an aborted run, or a receipt naming a date the store has
not got is `waiting` — a normal morning, reported as such. Corruption raises.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

SCHEMA_VERSION = 1
# the nine fields DG-050 fixed as the row's content address, in the types SQLite returns
HASHED_FIELDS = (
    "sleeper_id", "player_name", "position", "value", "overall_rank",
    "position_rank", "trend_30day", "market_volatility", "market_volatility_status",
)
# Every field the stored row carries. `snapshot_date`, `source` and `settings_hash` are here
# because `market_ranks._build` (:266-271) requires each entry to repeat them and match the pack's
# top level — omitting them produced a pack that validated by eye and failed the real consumer.
# This set equals the frozen verified market.json's entry keys exactly.
ENTRY_FIELDS = (
    "snapshot_date", "source", "settings_hash", "player_key", "sleeper_id", "player_name",
    "position", "value", "overall_rank", "position_rank", "trend_30day", "retrieved_at",
    "payload_hash", "market_volatility", "market_volatility_status",
)
RECEIPT_MUST_MATCH_ROW = ("source", "settings_hash", "snapshot_date", "retrieved_at")
# The two named row-hash conventions. `replay_harness._fc_payload_hash_check` (:534-575) fixes the
# second as a bounded vintage: captures from before the driver's storage-faithful normalization
# hashed an integral volatility as an int, which the REAL column returns as a float. A row still
# re-derives DETERMINISTICALLY under that era's projection. Nothing outside these two is accepted,
# and no row is ever rehashed to make it fit.
ROW_HASH_CURRENT = "current"
ROW_HASH_LEGACY = "legacy_integral_volatility"
SHARED_DATA_ROOT = Path("/Users/davidleess/dynasty-genius-product/app/data")
PROVENANCE = (
    "Preserved from the normalized fc_forward_capture store, not from a live response. The "
    "original HTTP bytes are unavailable and remain so: the collector retains the payload's hash "
    "in its success receipt but never the body. The rows in this pack are the collector's own "
    "normalized rows carrying their original per-row content addresses, and the canonical "
    "serialization beside this statement is that store's content, not the original HTTP payload. "
    "Completeness is attested by the receipt's store_hash over these exact rows, nothing more."
)


class CaptureAdapterError(RuntimeError):
    """The capture cannot be preserved honestly."""


class UnsupportedVintageError(CaptureAdapterError):
    """The rows predate the content address entirely — `market_volatility_status` is absent.

    Nothing was hashed that we could re-derive, so there is nothing to disagree with. One such
    capture is unavailable; it does not make the reading a fault.
    """


class CorruptCaptureError(CaptureAdapterError):
    """A row that HAS a content address and does not match it.

    Kept separate from an unsupported vintage because the two are opposite facts. A missing vintage
    is an absence; a hash that will not re-derive from a row that carries one is a disagreement, and
    filing a disagreement among ordinary absences is how tampering hides. This raises on every path,
    so the same fault cannot be an error or a note depending on which argument carried the receipt.
    """


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _read_bytes(path: Path) -> bytes:
    """Indirected so a test can make the receipt shift underfoot."""
    return path.read_bytes()


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, indent=2, default=str).encode()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureAdapterError(message)


def _safe_name(name: str) -> str:
    """An evidence filename, never a path. A stored name is used to build a path on read, so a
    separator or a `..` would reach outside the capture's own directory."""
    _require(
        isinstance(name, str)
        and name not in ("", ".", "..")
        and not name.startswith(".")
        and "/" not in name
        and "\\" not in name
        and "\x00" not in name,
        f"the evidence name {name!r} is not a plain filename",
    )
    return name


def _resolve_store_root(store_root: Path) -> Path:
    """Somewhere private this process may write. Never the shared store, never through a symlink."""
    _require(store_root.is_absolute(), f"the store root {str(store_root)!r} is not an absolute path")
    # every existing ancestor, not just the leaf: a symlinked parent redirects the write just as
    # completely, and is harder to notice
    for candidate in (store_root, *store_root.parents):
        if candidate.is_symlink():
            raise CaptureAdapterError(
                f"the store root {str(store_root)!r} passes through the symlink "
                f"{str(candidate)!r}; a write through it lands somewhere this call cannot see"
            )
    resolved = store_root.resolve()
    for parent in (resolved, *resolved.parents):
        if parent == SHARED_DATA_ROOT:
            raise CaptureAdapterError(
                f"the store root {str(resolved)!r} is inside the shared data tree; this store must "
                "be private"
            )
    return resolved


def _settings_from_endpoint(endpoint: Any) -> dict[str, Any]:
    """The capture settings, read off the endpoint the collector actually called.

    Sourced rather than assumed: these four values are what produced the settings_hash in the same
    receipt, so a pack built from them describes the request that happened.
    """
    _require(isinstance(endpoint, str) and endpoint, "the receipt states no endpoint")
    query = parse_qs(urlparse(endpoint).query)
    out: dict[str, Any] = {}
    for key, caster in (("isDynasty", None), ("numQbs", int), ("numTeams", int), ("ppr", int)):
        values = query.get(key)
        _require(bool(values), f"the receipt's endpoint states no {key}")
        raw = values[0]
        if caster is None:
            _require(raw in ("true", "false"), f"the endpoint's {key} is {raw!r}")
            out[key] = raw == "true"
        else:
            try:
                out[key] = caster(raw)
            except ValueError as bad:
                raise CaptureAdapterError(f"the endpoint's {key} is {raw!r}") from bad
    return out


def _rows_for(source_db: Path, receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every stored row of the receipted capture, read in ONE read-only consistent transaction."""
    uri = f"file:{source_db}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    except sqlite3.Error as bad:
        raise CaptureAdapterError(f"the source store cannot be opened read-only: {bad}") from bad
    try:
        conn.row_factory = sqlite3.Row
        # one snapshot for the whole read: a capture landing mid-read must not be half-seen
        conn.execute("BEGIN")
        try:
            found = conn.execute(
                "SELECT * FROM fc_forward_capture_raw "
                "WHERE snapshot_date=? AND source=? AND settings_hash=? ORDER BY player_key",
                (receipt["snapshot_date"], receipt["source"], receipt["settings_hash"]),
            ).fetchall()
        except sqlite3.Error as bad:
            raise CaptureAdapterError(f"the source store cannot be read: {bad}") from bad
        return [dict(row) for row in found]
    finally:
        conn.close()


def _row_conventions(rows: Sequence[Mapping[str, Any]]) -> tuple[str, int, int]:
    """Which named convention re-derives every row: (label, verified_current, verified_legacy).

    Refuses rather than reprojecting. A pre-Phase-0b row carries no `market_volatility_status` at
    all and its content address can never be rebuilt (the store's own docstring, and
    replay_harness:534-575 counts these and never compares them) — such a capture is unsupported,
    not merely unverified.
    """
    pre_schema = [r["player_key"] for r in rows if r.get("market_volatility_status") is None]
    if pre_schema:
        raise UnsupportedVintageError(
            f"{len(pre_schema)} of {len(rows)} rows carry no market_volatility_status: this is the "
            "pre-Phase-0b vintage whose content address can never be rebuilt, so the capture "
            "cannot be attested and is not archived"
        )
    current = legacy = 0
    unverified: list[str] = []
    for row in rows:
        content = {field: row.get(field) for field in HASHED_FIELDS}
        if _digest(content) == row.get("payload_hash"):
            current += 1
            continue
        volatility = row.get("market_volatility")
        if isinstance(volatility, float) and volatility.is_integer():
            era = {**content, "market_volatility": int(volatility)}
            if _digest(era) == row.get("payload_hash"):
                legacy += 1
                continue
        unverified.append(row["player_key"])
    if unverified:
        raise CorruptCaptureError(
            f"{len(unverified)} of {len(rows)} stored rows do not re-derive their own content "
            f"address under either named convention (first: {unverified[:1]}); re-hashing them "
            "would manufacture the attestation that is missing"
        )
    return (ROW_HASH_CURRENT if legacy == 0 else ROW_HASH_LEGACY), current, legacy


def _attest(rows: Sequence[Mapping[str, Any]], receipt: Mapping[str, Any]) -> tuple[str, int, int]:
    """The checks that turn a normalized store into evidence of a complete capture.

    The store hash is computed over the payload hashes AS STORED, so it is independent of which
    content convention produced them: it proves this exact set of rows is the batch the collector
    recorded, unmodified since. The per-row re-derivation is the separate, additional check.
    """
    for field in RECEIPT_MUST_MATCH_ROW:
        stated = receipt.get(field)
        differing = sorted({str(row.get(field)) for row in rows if row.get(field) != stated})
        _require(
            not differing,
            f"the receipt states {field} {stated!r} but stored rows carry {differing}",
        )
    # `rows` are the RAW rows. The joinable view holds only rows with a Sleeper id
    # (fc_forward_capture_store:204-211), so joinable < raw exactly when a row has none, and the
    # collector records that difference as missing_sleeper_count. Requiring both to equal the raw
    # count would refuse a complete capture the moment an unresolved id appears — which the
    # contract explicitly says to retain.
    _require(
        receipt.get("raw_entries_written") == len(rows),
        f"the receipt counts {receipt.get('raw_entries_written')!r} raw entries but "
        f"{len(rows)} rows are stored",
    )
    joinable, missing = receipt.get("joinable_rows_written"), receipt.get("missing_sleeper_count")
    if joinable is not None and missing is not None:
        _require(
            joinable + missing == len(rows),
            f"the receipt's {joinable} joinable rows plus {missing} missing-sleeper rows do not "
            f"account for the {len(rows)} rows stored",
        )
    stored_without_id = sum(1 for row in rows if row.get("sleeper_id") is None)
    if missing is not None:
        _require(
            stored_without_id == missing,
            f"the receipt records {missing} rows without a Sleeper id but {stored_without_id} "
            "stored rows have none",
        )
    computed = _digest(
        {"sigs": sorted(f"{row['player_key']}:{row['payload_hash']}" for row in rows)}
    )
    _require(
        computed == receipt.get("store_hash"),
        f"the rows hash to store_hash {computed} but the receipt recorded "
        f"{receipt.get('store_hash')!r}",
    )
    return _row_conventions(rows)


def _pack(rows: Sequence[Mapping[str, Any]], receipt: Mapping[str, Any],
          conventions: tuple[str, int, int]) -> bytes:
    """The existing schema_version 1 market.json shape, with every row and an honest provenance."""
    entries = [{field: row.get(field) for field in ENTRY_FIELDS} for row in rows]
    return _canonical(
        {
            "schema_version": SCHEMA_VERSION,
            "source": receipt["source"],
            "settings": _settings_from_endpoint(receipt.get("endpoint")),
            "settings_hash": receipt["settings_hash"],
            "snapshot_date": receipt["snapshot_date"],
            "retrieved_at": receipt["retrieved_at"],
            "entries": entries,
            "capture_report": dict(receipt),
            "provenance": {
                "reading": "normalized_store_capture",
                "original_http_bytes": "unavailable",
                "row_hash_convention": conventions[0],
                "rows_verified_current": conventions[1],
                "rows_verified_legacy": conventions[2],
                "statement": PROVENANCE,
            },
        }
    )


def _identity(receipt: Mapping[str, Any]) -> str:
    return f"{receipt['source']}__{receipt['settings_hash']}__{receipt['snapshot_date']}"


def _record_from(directory: Path) -> dict[str, Any]:
    """Read one stored capture back and re-verify it against its own recorded digests."""
    meta_path = directory / "capture.json"
    _require(meta_path.is_file(), f"the stored capture {directory.name!r} has no capture.json")
    try:
        meta = json.loads(meta_path.read_text())
    except json.JSONDecodeError as bad:
        raise CaptureAdapterError(f"the stored capture {directory.name!r} is corrupt: {bad}") from bad
    market_bytes = (directory / "market.json").read_bytes()
    _require(
        hashlib.sha256(market_bytes).hexdigest() == meta.get("market_sha256"),
        f"the stored capture {directory.name!r} is corrupt: its market pack does not match the "
        "digest recorded when it was preserved",
    )
    evidence: dict[str, bytes] = {}
    recomputed_evidence: dict[str, str] = {}
    for name, expected in sorted((meta.get("evidence_sha256") or {}).items()):
        payload = (directory / "evidence" / _safe_name(name)).read_bytes()
        _require(
            hashlib.sha256(payload).hexdigest() == expected,
            f"the stored capture {directory.name!r} is corrupt: evidence {name!r} does not match "
            "its recorded digest",
        )
        evidence[name] = payload
        recomputed_evidence[name] = expected
    # capture.json is not itself hash-protected, so bind its claimed identity to the bytes it
    # describes: a consistent edit of the digests AND the payloads still fails here.
    capture_id = _digest({
        "market": hashlib.sha256(market_bytes).hexdigest(),
        "evidence": recomputed_evidence,
    })
    _require(
        capture_id == meta.get("capture_id"),
        f"the stored capture {directory.name!r} is corrupt: its capture_id does not address the "
        "bytes it records",
    )
    # and it must be sitting in the slot its own identity and content name: a capture moved into
    # another identity's directory would otherwise read back as that identity's evidence
    _require(
        directory.name == f"{meta.get('identity')}__{capture_id[:16]}",
        f"the stored capture {directory.name!r} is corrupt: its directory does not match the "
        f"identity and content it records ({meta.get('identity')}__{capture_id[:16]})",
    )
    return {
        "capture_id": meta["capture_id"],
        "as_of": meta["as_of"],
        "known_at": meta["known_at"],
        "observed_at": meta["observed_at"],
        "complete": meta["complete"],
        "market_bytes": market_bytes,
        "evidence": evidence,
    }


def _stored_captures(store_root: Path) -> list[tuple[str, Path]]:
    """Every PRESERVED capture. Dot-prefixed names are staging debris from an interrupted write
    and are skipped: an abandoned attempt must not make every later reading fail."""
    root = store_root / "captures"
    if not root.is_dir():
        return []
    return sorted(
        (path.name, path)
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def _preserve(root: Path, rows: Sequence[Mapping[str, Any]], receipt: Mapping[str, Any],
              receipt_bytes: bytes, observed_at: datetime) -> tuple[dict[str, Any], int]:
    """Attest one receipted capture and preserve it. Returns (record, imported).

    The rows are passed IN, never re-read. Reading them again here would attest a different set
    from the one the caller's mid-read guard bracketed: a row appended between the two reads would
    surface as a receipt/store count disagreement — an integrity fault — when it is an ordinary
    capture in flight.
    """
    conventions = _attest(rows, receipt)
    market_bytes = _pack(rows, receipt, conventions)
    evidence = {
        "receipt.json": receipt_bytes,
        "normalized_rows.json": _canonical(
            [{field: row.get(field) for field in ENTRY_FIELDS} for row in rows]
        ),
        "provenance.txt": PROVENANCE.encode(),
    }
    content_id = _digest(
        {
            "market": hashlib.sha256(market_bytes).hexdigest(),
            "evidence": {name: hashlib.sha256(blob).hexdigest() for name, blob in evidence.items()},
        }
    )
    identity = _identity(receipt)
    directory = root / "captures" / f"{identity}__{content_id[:16]}"

    for name, path in _stored_captures(root):
        if name.startswith(f"{identity}__") and path != directory:
            raise CaptureAdapterError(
                f"conflict: {identity} is already preserved with different content "
                f"({name}); a correction is never written over the reading it corrects"
            )

    if directory.is_dir():
        return _record_from(directory), 0       # identical poll: the first preservation stands

    meta = {
        "capture_id": content_id,
        "as_of": receipt["retrieved_at"],
        # the collector's own recorded retrieval clock, never this transfer's time
        "known_at": receipt["retrieved_at"],
        "known_at_source": "fc_forward_capture success receipt retrieved_at",
        "observed_at": observed_at.isoformat(),
        "complete": True,
        "identity": identity,
        "row_hash_convention": conventions[0],
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "market_sha256": hashlib.sha256(market_bytes).hexdigest(),
        "evidence_sha256": {
            name: hashlib.sha256(blob).hexdigest() for name, blob in evidence.items()
        },
    }
    # A unique staging dir per attempt, hidden from _stored_captures by its leading dot: a crash
    # leaves an orphan that is ignored rather than one that fails every future read, and two
    # attempts can never mix bytes in a shared directory. (The DG-215 lock-wedge shape.)
    captures_root = directory.parent
    captures_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".partial-", dir=captures_root))
    (staging / "evidence").mkdir(parents=True, exist_ok=True)
    (staging / "market.json").write_bytes(market_bytes)
    for name, blob in evidence.items():
        (staging / "evidence" / _safe_name(name)).write_bytes(blob)
    (staging / "capture.json").write_bytes(_canonical(meta))
    try:
        staging.rename(directory)                # append-only: visible whole or not at all
    except OSError as bad:                       # pragma: no cover - filesystem-level failure
        shutil.rmtree(staging, ignore_errors=True)
        raise CaptureAdapterError(f"the capture could not be preserved atomically: {bad}") from bad
    return _record_from(directory), 1


def _history_reasons(source_db: Path, preserved: set[str], extra: Sequence[str]) -> list[str]:
    """Why every date NOT preserved is unavailable — named, never silently dropped."""
    reasons = list(extra)
    try:
        conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
        try:
            dates = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT snapshot_date FROM fc_forward_capture_raw ORDER BY 1"
                )
            ]
        finally:
            conn.close()
    except sqlite3.Error:
        return reasons + ["the source store's capture dates could not be listed"]
    others = [date for date in dates if date not in preserved]
    if others:
        reasons.append(
            f"{len(others)} capture date(s) {others[0]}..{others[-1]} are present in the store but "
            "are not retained as verified captures here; reasons include missing original success "
            "receipts and the unsupported vintages reported above"
        )
    reasons.append(
        "the original HTTP payload bytes are not retained for any capture date, so no stored "
        "capture can attest the response FantasyCalc served, only the normalized rows it produced"
    )
    return reasons


def capture_market_inventory(
    *,
    source_db: Path,
    latest_receipt: Path,
    store_root: Path,
    observed_at: datetime,
    historical_receipts: Sequence[Path] = (),
) -> dict[str, Any]:
    """Preserve every receipted capture there is evidence for, and name what is not available.

    `historical_receipts` are ORIGINAL collector success receipts extracted byte-for-byte from the
    preserved stdout log — never composed here. Each is attested against the read-only store exactly
    as the current one is. A receipt whose rows no named convention can re-derive makes that one
    capture unavailable with its cause; it does not fail the reading. A receipt that CONTRADICTS the
    store raises, because that is a disagreement rather than a missing vintage.

    Returns `{captures, imported, history_unavailable, source_state}`. `source_state` is
    `"imported"`, `"unchanged"` or `"waiting"`; nothing is written on a refusal.
    """
    root = _resolve_store_root(Path(store_root))
    source_db = Path(source_db)
    latest_receipt = Path(latest_receipt)
    _require(observed_at.tzinfo is not None, "observed_at must be an aware UTC instant")
    _require(source_db.is_file(), f"the source store {str(source_db)!r} does not exist")

    imported = 0
    preserved: set[str] = set()
    notes: list[str] = []

    for path in historical_receipts:
        path = Path(path)
        if not path.is_file():
            notes.append(f"the historical receipt {str(path)!r} is not a readable file")
            continue
        blob = _read_bytes(path)
        try:
            receipt = json.loads(blob)
        except (UnicodeDecodeError, json.JSONDecodeError) as bad:
            raise CaptureAdapterError(
                f"the historical receipt {path.name!r} is not readable JSON: {bad}"
            ) from bad
        _require(isinstance(receipt, dict), f"the historical receipt {path.name!r} is not an object")
        if receipt.get("status") != "ok" or receipt.get("aborted_reason") is not None:
            notes.append(
                f"the historical receipt for {receipt.get('snapshot_date')!r} reports status "
                f"{receipt.get('status')!r}, so it attests no complete capture"
            )
            continue
        for field in ("source", "settings_hash", "snapshot_date", "retrieved_at", "store_hash"):
            _require(receipt.get(field), f"the historical receipt {path.name!r} states no {field}")
        rows = _rows_for(source_db, receipt)
        if not rows:
            notes.append(
                f"capture {receipt['snapshot_date']}: the receipt attests a complete capture but "
                "the store holds no rows for it"
            )
            continue
        try:
            record, added = _preserve(root, rows, receipt, blob, observed_at)
        except UnsupportedVintageError as unsupported:
            # an absence, not a disagreement: this one capture is unavailable and the reading goes on
            notes.append(f"capture {receipt['snapshot_date']}: {unsupported}")
            continue
        imported += added
        preserved.add(receipt["snapshot_date"])

    def finish(state: str) -> dict[str, Any]:
        records = [_record_from(path) for _, path in _stored_captures(root)]
        retained_dates = {json.loads(record["market_bytes"])["snapshot_date"] for record in records}
        return {
            "captures": records,
            "imported": imported,
            "history_unavailable": _history_reasons(source_db, retained_dates, notes),
            "source_state": state if imported else ("unchanged" if state == "imported" else state),
        }

    if not latest_receipt.is_file():
        notes.append("no readable success receipt was present for the current capture")
        return finish("waiting")

    before = _read_bytes(latest_receipt)
    try:
        receipt = json.loads(before)
    except (UnicodeDecodeError, json.JSONDecodeError) as bad:
        raise CaptureAdapterError(f"the success receipt is not readable JSON: {bad}") from bad
    _require(isinstance(receipt, dict), "the success receipt is not a JSON object")

    if receipt.get("status") != "ok" or receipt.get("aborted_reason") is not None:
        notes.append(
            f"the latest capture reports status {receipt.get('status')!r} (aborted_reason "
            f"{receipt.get('aborted_reason')!r}), so no complete current capture is available"
        )
        return finish("waiting")

    for field in ("source", "settings_hash", "snapshot_date", "retrieved_at", "store_hash"):
        _require(receipt.get(field), f"the success receipt states no {field}")

    rows = _rows_for(source_db, receipt)
    after = _read_bytes(latest_receipt)
    _require(
        after == before,
        "the success receipt changed while its rows were being read; pairing one capture's receipt "
        "with another's rows would look complete and be wrong",
    )
    if not rows:
        notes.append(
            f"the receipt names capture {receipt['snapshot_date']} but the store holds no rows for "
            "it yet; this is a capture in flight, not a fault"
        )
        return finish("waiting")

    _, added = _preserve(root, rows, receipt, before, observed_at)
    imported += added
    preserved.add(receipt["snapshot_date"])
    return finish("imported")
