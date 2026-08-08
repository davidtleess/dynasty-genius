"""Layer 1 PFF intake and indexer — payload-grain, lossless, manual-download honest.

WHAT THIS IS FOR
    PFF is a `manual_download` source: a human exports files from a subscriber account and drops
    them somewhere. Acquisition and inventory already existed (149 distinct payloads by SHA-256,
    deduped from 307 downloads, with a governed schema catalog and coverage table). What did not
    exist was a repeatable intake path, a queryable metadata ledger, and an honest freshness clock.
    This module is those three things and nothing more.

THE ONE RULE THAT SHAPES EVERYTHING: LAYER 1 LOSES NOTHING.
    Scope-basis selection, duplicate-winner selection, and filtering to `accepted` are SELECTION
    decisions and belong to a later layer, where an analytical question is actually posed. Each was
    proposed during design and each was measured to destroy real data:
      * choosing REGPO as a single basis drops a player present only in REG (measured: 1 player in
        ncaa/receiving_summary/2017);
      * duplicate payloads at the same grain are NOT semantically identical (measured: they differ
        on 1-2 rows), so picking a winner discards observations;
      * 32 of 149 payloads carry a non-`accepted` status, and those statuses are evidence labels,
        not permission to discard.
    So: every payload is retained, every offering is recorded, every status is preserved.

TWO IDENTITIES, BECAUSE THE DATA REQUIRES IT
    307 offerings map to 149 payloads. A single identity cannot express that.
      * PAYLOAD identity  = SHA-256 of the bytes. Immutable.
      * OFFERING identity = (batch_id, offering_id) from the sidecar. An offering is one act of
        handing us a file.

PROVENANCE IS DECLARED, NEVER INFERRED
    league/report/scope/season come from an explicit batch manifest. Filenames, row counts, and
    retrieval order are not provenance. Every wrong claim made about this dataset during design came
    from inferring structure instead of reading it.

THE FRESHNESS CLOCK IS THE SOURCE CLOCK
    `daily_control._COMPLETION_KEYS` ranks `finished_at`/`completed_at` ABOVE `retrieved_at`. A
    marker carrying a generic run-completion time therefore shadows the real acquisition time: a
    three-month-old download would report `current` with age 0.033 days. So the status marker
    deliberately does NOT emit those keys. Execution time is recorded as `indexed_at`, which
    daily_control does not consume, and the consumed clock is the maximum DECLARED offering
    `retrieved_at` across the committed ledger. Age since we built an index is not freshness.

DELIBERATELY NOT HERE
    No network of any kind (this is a manual source). No provider contact. No scope or version
    selection. No normalized/player-row analytical store. No PFF grade promotion to a model surface.
    No rewriting of the governed inventory/coverage artifacts — they remain preserved evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

__all__ = [
    "PFFIntakeError",
    "PFFIdentityConflict",
    "IntakeResult",
    "BackfillResult",
    "intake",
    "backfill",
    "list_payloads",
    "list_offerings",
]

# --------------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------------

#: Transport axis — durability only. `ok` means every offering was preserved AND the metadata
#: transaction committed. It is NOT an opinion about data quality.
STATUS_OK = "ok"
STATUS_FAILED = "failed"

#: Evidence axis — orthogonal to transport. A quarantined-but-indexed payload is a real
#: acquisition; conflating the two would make daily_control report a genuine manual download as
#: never having happened.
REVIEW_CLEAR = "clear"
REVIEW_REQUIRED = "review_required"

#: The six labels already present in the governed inventory, preserved verbatim.
LEGACY_STATUSES = (
    "accepted",
    "accepted_extra_history",
    "accepted_with_export_drift",
    "partial_vendor_coverage",
    "scope_mismatch_retained",
    "superseded_basis_retained",
)
DEFAULT_NEW_STATUS = "pending_review"

#: Nothing outside this set may enter the canonical ledger.
ALLOWED_STATUSES = frozenset(LEGACY_STATUSES) | {DEFAULT_NEW_STATUS, REVIEW_REQUIRED}

#: Provenance fields that become path components, and so must be declared and safe.
PROVENANCE_FIELDS = ("league", "report", "scope", "season")
REQUIRED_OFFERING_FIELDS = ("offering_id", "source_path", *PROVENANCE_FIELDS, "retrieved_at")

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_]+$")
_SEASON = re.compile(r"^\d{4}$")


class PFFIntakeError(RuntimeError):
    """A batch could not be accepted as offered."""


class PFFIdentityConflict(PFFIntakeError):
    """An identity was reused with different facts. Never silently remapped."""


class _StrandedCopies(Exception):
    """Internal: a phase-2 copy failed after earlier copies landed.

    Carries the already-created objects so `intake` can report them instead of leaving the machine
    holding files it never mentions.
    """

    def __init__(self, created: list[str], cause: BaseException) -> None:
        super().__init__(str(cause))
        self.created = list(created)
        self.cause = cause


@dataclass
class IntakeResult:
    status: str
    review_state: str = REVIEW_CLEAR
    review_required_count: int = 0
    payloads_indexed: int = 0
    provenance_added: int = 0
    unindexed_objects: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    source_retrieved_at: Optional[str] = None
    batch_id: Optional[str] = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "review_state": self.review_state,
            "review_required_count": self.review_required_count,
            "payloads_indexed": self.payloads_indexed,
            "provenance_added": self.provenance_added,
            "unindexed_objects": list(self.unindexed_objects),
            "refused": list(self.refused),
            "source_retrieved_at": self.source_retrieved_at,
            "batch_id": self.batch_id,
        }


@dataclass
class BackfillResult:
    status: str = STATUS_OK
    review_state: str = REVIEW_CLEAR
    review_required_count: int = 0
    payloads_indexed: int = 0
    provenance_added: int = 0
    offerings_seen: int = 0
    hash_mismatches: list[str] = field(default_factory=list)
    unresolved_offerings: list[str] = field(default_factory=list)
    source_retrieved_at: Optional[str] = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "review_state": self.review_state,
            "review_required_count": self.review_required_count,
            "payloads_indexed": self.payloads_indexed,
            "provenance_added": self.provenance_added,
            "offerings_seen": self.offerings_seen,
            "hash_mismatches": list(self.hash_mismatches),
            "unresolved_offerings": list(self.unresolved_offerings),
            "source_retrieved_at": self.source_retrieved_at,
        }


# --------------------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------------------

_SCHEMA = (
    """create table if not exists batch(
           batch_id text primary key,
           manifest_sha text not null,
           indexed_at text not null)""",
    """create table if not exists payload(
           sha256 text primary key,
           schema_sha256 text,
           league text, report text, scope text, season text,
           status text not null,
           canonical_path text not null,
           row_count integer, column_count integer, byte_count integer,
           first_retrieved_at text)""",
    """create table if not exists offering(
           offering_id text not null,
           batch_id text not null,
           sha256 text not null,
           league text, report text, scope text, season text,
           retrieved_at text,
           source_path text,
           primary key (offering_id, batch_id))""",
)


def _connect(ledger_path: Path) -> sqlite3.Connection:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ledger_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    for stmt in _SCHEMA:
        conn.execute(stmt)
    conn.commit()


def _rows(ledger_path: Path, table: str) -> list[dict[str, Any]]:
    path = Path(ledger_path)
    if not path.exists():
        return []
    conn = _connect(path)
    try:
        try:
            cur = conn.execute(f"select * from {table}")  # noqa: S608 - fixed identifiers
        except sqlite3.OperationalError:
            return []
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_payloads(*, ledger_path: Path) -> list[dict[str, Any]]:
    return _rows(Path(ledger_path), "payload")


def list_offerings(*, ledger_path: Path) -> list[dict[str, Any]]:
    return _rows(Path(ledger_path), "offering")


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema_sha256(header: Iterable[str]) -> str:
    """SHA-256 of the NEWLINE-joined header — the governed PFF algorithm.

    Matches `scripts/build_provider_contract_bundle.py` and
    `src/dynasty_genius/adapters/pff_te_export._header_hash`. Any other join separator recognises
    synthetic fixtures while every real governed schema hashes elsewhere and quarantines.
    """
    return hashlib.sha256("\n".join(header).encode("utf-8")).hexdigest()


def _profile_csv(path: Path) -> tuple[list[str], int, int]:
    with path.open("r", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0, 0
        return header, sum(1 for _ in reader), len(header)


def _validate_component(field_name: str, value: str) -> str:
    """Provenance becomes a path component, so `..` and separators are refused, not sanitised."""
    text = str(value)
    if not text:
        raise PFFIntakeError(f"offering provenance field {field_name!r} is empty")
    if field_name == "season":
        if not _SEASON.match(text):
            raise PFFIntakeError(f"offering provenance field {field_name!r} is not a season: {text!r}")
        return text
    if ".." in text or "/" in text or "\\" in text or not _SAFE_COMPONENT.match(text):
        raise PFFIntakeError(
            f"offering provenance field {field_name!r} is unsafe as a path component: {text!r}"
        )
    return text


def _parse_retrieved_at(value: str) -> datetime:
    """A declared retrieval time must be a real, timezone-aware instant.

    It is used two ways, and both were unsafe while it was an unvalidated string:
      1. as a PATH COMPONENT — `retrieved_at='../../../../../../escaped'` sliced to `../../../`
         and wrote outside the declared report/scope/season layout while reporting status=ok;
      2. as the SOURCE FRESHNESS CLOCK — a non-time string is a value daily_control cannot use, so
         the manifest would carry a clock that means nothing.
    Naive timestamps are refused too: an age computed against an instant with no offset is a guess.
    """
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PFFIntakeError(
            f"offering retrieved_at is not an ISO-8601 timestamp: {text!r}"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PFFIntakeError(
            f"offering retrieved_at must be timezone-aware; got naive {text!r}"
        )
    return parsed


def _canonical_relpath(*, quarantined: bool, league: str, report: str, scope: str,
                       season: str, retrieved_at: datetime, sha: str) -> str:
    """raw/{league}/{report}/{scope}/{season}/{date}_{sha12}.csv — the existing convention.

    Quarantine mirrors it under `quarantine/` with the SAME immutable SHA identity, so an
    unrecognised schema never loses its provenance and never lands in a second, private layout.
    """
    # Derived from the PARSED instant, never by slicing the declared string. String slicing is
    # what let a traversal-shaped value become a path component.
    date = retrieved_at.date().isoformat()
    root = "quarantine" if quarantined else "raw"
    return f"{root}/{league.lower()}/{report.lower()}/{scope.upper()}/{season}/{date}_{sha[:12]}.csv"


def _repo_relative(path: Path, repo_root: Path) -> str:
    """A repo-anchored, traversal-free relative path, or an absolute path if genuinely outside."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _max_retrieved_at(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute("select max(retrieved_at) as m from offering").fetchone()
    return row["m"] if row and row["m"] else None


def _load_manifest(batch_manifest: Path) -> tuple[str, list[dict[str, Any]], str]:
    path = Path(batch_manifest)
    if not path.is_file():
        raise PFFIntakeError(f"batch manifest not found: {path}")
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise PFFIntakeError(f"batch manifest is not valid JSON: {exc}") from exc
    batch_id = str(doc.get("batch_id") or "").strip()
    if not batch_id:
        raise PFFIntakeError("batch manifest is missing batch_id")
    offerings = doc.get("offerings")
    if not isinstance(offerings, list):
        raise PFFIntakeError("batch manifest is missing an offerings list")
    manifest_sha = hashlib.sha256(
        json.dumps(doc, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return batch_id, offerings, manifest_sha


def _validated_offering(record: Any) -> dict[str, str]:
    if not isinstance(record, dict):
        raise PFFIntakeError(f"offering record must be an object; got {type(record).__name__}")
    missing = [f for f in REQUIRED_OFFERING_FIELDS if not str(record.get(f) or "").strip()]
    if missing:
        raise PFFIntakeError(
            "offering is missing declared provenance: "
            + ", ".join(missing)
            + " (provenance is declared in the sidecar; filenames are never parsed for it)"
        )
    clean = {f: str(record[f]) for f in REQUIRED_OFFERING_FIELDS}
    for name in PROVENANCE_FIELDS:
        clean[name] = _validate_component(name, clean[name])
    status = record.get("status")
    if status is not None:
        status = str(status)
        if status not in ALLOWED_STATUSES:
            raise PFFIntakeError(
                f"declared status {status!r} is outside the governed ontology "
                f"{sorted(ALLOWED_STATUSES)}"
            )
        clean["status"] = status
    return clean


# --------------------------------------------------------------------------------------
# Intake
# --------------------------------------------------------------------------------------


def intake(
    *,
    batch_manifest: Path,
    store_root: Path,
    ledger_path: Path,
    marker_path: Path,
    ready_marker_path: Path,
    repo_root: Path,
    known_schemas: Iterable[str],
) -> IntakeResult:
    store_root = Path(store_root)
    ledger_path = Path(ledger_path)
    repo_root = Path(repo_root)
    known = {str(s) for s in known_schemas}

    batch_id, raw_offerings, manifest_sha = _load_manifest(Path(batch_manifest))
    offerings = [_validated_offering(rec) for rec in raw_offerings]

    result = IntakeResult(status=STATUS_FAILED, batch_id=batch_id)
    conn = _connect(ledger_path)
    try:
        _ensure_schema(conn)
        _detect_identity_conflicts(conn, batch_id, manifest_sha, offerings)

        # An exact replay of an already-recorded batch is a complete no-op: no payload rows, no
        # provenance rows, and — critically — no marker rewrite, so the freshness clock does not
        # move for an act that acquired nothing.
        existing_batch = conn.execute(
            "select manifest_sha from batch where batch_id = ?", (batch_id,)
        ).fetchone()
        if existing_batch is not None and existing_batch["manifest_sha"] == manifest_sha:
            result.status = STATUS_OK
            result.review_state, result.review_required_count = _review_state(conn)
            result.source_retrieved_at = _max_retrieved_at(conn)
            return result

        try:
            staged, unindexed = _stage_payloads(conn, offerings, store_root, repo_root, known)
        except _StrandedCopies as stranded:
            # Bytes already landed. Report them and write a FAILED latest-attempt marker; the
            # last-good marker is untouched, so a prior good vintage survives.
            result.status = STATUS_FAILED
            result.unindexed_objects = stranded.created
            result.refused.append(str(stranded.cause))
            _write_status_marker(marker_path, result, _max_retrieved_at(conn))
            if isinstance(stranded.cause, PFFIntakeError):
                raise stranded.cause
            if isinstance(stranded.cause, OSError):
                # A durability failure (the canonical root cannot be written) is a TRANSPORT
                # failure, reported as a failed result. Only a batch-validity problem is raised:
                # the caller can act on "your batch is malformed" but not on "the disk refused".
                return result
            raise PFFIntakeError(str(stranded.cause)) from stranded.cause
        result.unindexed_objects = unindexed

        try:
            conn.execute("begin")
            for item in staged:
                if item["is_new_payload"]:
                    conn.execute(
                        "insert into payload(sha256, schema_sha256, league, report, scope, season,"
                        " status, canonical_path, row_count, column_count, byte_count,"
                        " first_retrieved_at) values (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            item["sha256"], item["schema_sha256"], item["league"], item["report"],
                            item["scope"], item["season"], item["status"], item["canonical_path"],
                            item["row_count"], item["column_count"], item["byte_count"],
                            item["retrieved_at"],
                        ),
                    )
                conn.execute(
                    "insert into offering(offering_id, batch_id, sha256, league, report, scope,"
                    " season, retrieved_at, source_path) values (?,?,?,?,?,?,?,?,?)",
                    (
                        item["offering_id"], batch_id, item["sha256"], item["league"],
                        item["report"], item["scope"], item["season"], item["retrieved_at"],
                        item["source_path"],
                    ),
                )
            conn.execute(
                "insert or replace into batch(batch_id, manifest_sha, indexed_at) values (?,?,?)",
                (batch_id, manifest_sha, _now_iso()),
            )
            conn.commit()
        except sqlite3.Error:
            # ONE transaction is the commit point. Anything already copied stays on disk and is
            # REPORTED as an unindexed object so a retry can reconcile it; nothing is deleted.
            conn.rollback()
            result.status = STATUS_FAILED
            result.payloads_indexed = 0
            result.provenance_added = 0
            result.unindexed_objects = sorted(
                {*unindexed, *(i["canonical_path"] for i in staged)}
            )
            _write_status_marker(marker_path, result, _max_retrieved_at(conn))
            return result

        result.status = STATUS_OK
        result.payloads_indexed = sum(1 for i in staged if i["is_new_payload"])
        result.provenance_added = len(staged)
        result.unindexed_objects = []
        result.review_state, result.review_required_count = _review_state(conn)
        result.source_retrieved_at = _max_retrieved_at(conn)
        _write_status_marker(marker_path, result, result.source_retrieved_at)
        _write_ready_marker(ready_marker_path, batch_id, result.source_retrieved_at)
        return result
    except PFFIntakeError:
        raise
    except OSError as exc:
        # A durability failure (e.g. the canonical root cannot be created) is a transport failure.
        result.status = STATUS_FAILED
        result.refused.append(str(exc))
        _write_status_marker(marker_path, result, None)
        return result
    finally:
        conn.close()


def _detect_identity_conflicts(
    conn: sqlite3.Connection, batch_id: str, manifest_sha: str, offerings: list[dict[str, str]]
) -> None:
    """An identity is never silently remapped.

    Offering-level conflicts are checked first so the message names the specific offering; a batch
    whose manifest changed while its offerings still agree is reported at batch level.
    """
    for item in offerings:
        row = conn.execute(
            "select sha256, league, report, scope, season, retrieved_at from offering"
            " where offering_id = ? and batch_id = ?",
            (item["offering_id"], batch_id),
        ).fetchone()
        if row is None:
            continue
        source = Path(item["source_path"])
        if source.is_file():
            sha = _sha256_file(source)
            if sha != row["sha256"]:
                raise PFFIdentityConflict(
                    f"offering identity ({batch_id}, {item['offering_id']}) was already recorded "
                    f"for payload {row['sha256'][:12]} and is now offered with different bytes "
                    f"{sha[:12]}"
                )
        for name in (*PROVENANCE_FIELDS, "retrieved_at"):
            if row[name] != item[name]:
                raise PFFIdentityConflict(
                    f"offering identity ({batch_id}, {item['offering_id']}) was already recorded "
                    f"with {name}={row[name]!r} and is now declared {item[name]!r}"
                )
    existing = conn.execute(
        "select manifest_sha from batch where batch_id = ?", (batch_id,)
    ).fetchone()
    if existing is not None and existing["manifest_sha"] != manifest_sha:
        raise PFFIdentityConflict(
            f"batch_id {batch_id!r} was already recorded with a different manifest; a batch_id "
            "identifies one manifest and is never reused for another"
        )


def _stage_payloads(
    conn: sqlite3.Connection,
    offerings: list[dict[str, str]],
    store_root: Path,
    repo_root: Path,
    known: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Copy raw bytes into the content-addressed tree BEFORE the transaction.

    Copy-then-index is deliberate: if the commit fails, the object is already on disk and can be
    reported as unindexed and reconciled by a retry. The human's original download is only ever
    read.
    """
    # TWO PHASES, deliberately separated.
    #
    # Interleaving validation with copying stranded real bytes: a batch whose SECOND offering had a
    # missing source raised after the FIRST was already copied into the canonical tree, leaving an
    # unindexed object that was never reported and no marker at all. The operator saw "invalid
    # batch" while the machine quietly held a file it did not know about.
    #
    # PHASE 1 validates, hashes and profiles EVERY offering, touching nothing. PHASE 2 copies. A
    # failure in phase 1 therefore cannot strand anything, and a failure in phase 2 enumerates what
    # it already created.
    #
    # SHA identity spans the LEDGER *and* the batch in flight: two byte-identical offerings in one
    # batch are one payload with two mappings. That shape is the norm here, not an edge case —
    # 307 offerings collapse to 149 payloads.
    plans: list[dict[str, Any]] = []
    seen_in_batch: dict[str, dict[str, Any]] = {}

    for item in offerings:  # ---- PHASE 1: pure inspection, no writes ----
        source = Path(item["source_path"])
        if not source.is_file():
            raise PFFIntakeError(f"offering {item['offering_id']!r} source not found: {source}")
        retrieved = _parse_retrieved_at(item["retrieved_at"])
        sha = _sha256_file(source)
        header, row_count, column_count = _profile_csv(source)
        schema_sha = _schema_sha256(header)
        quarantined = schema_sha not in known

        prior = seen_in_batch.get(sha)
        existing = conn.execute(
            "select canonical_path, status from payload where sha256 = ?", (sha,)
        ).fetchone()
        if prior is not None:
            rel, status, needs_copy = prior["canonical_path"], prior["status"], False
        elif existing is not None:
            rel, status, needs_copy = existing["canonical_path"], existing["status"], False
        else:
            store_rel = _canonical_relpath(
                quarantined=quarantined,
                league=item["league"], report=item["report"], scope=item["scope"],
                season=item["season"], retrieved_at=retrieved, sha=sha,
            )
            # Persist the path anchored at the REPO ROOT so the ledger is portable, while the
            # object lives under the canonical store. Computing a path is not a write, so this
            # still belongs in phase 1.
            rel = _repo_relative(store_root / store_rel, repo_root)
            # An unrecognised schema is quarantined for REVIEW. A declared status never blesses it:
            # a sidecar is a provenance declaration, not a schema authority.
            status = REVIEW_REQUIRED if quarantined else item.get("status", DEFAULT_NEW_STATUS)
            needs_copy = True

        plan = {
            **item,
            "sha256": sha,
            "schema_sha256": schema_sha,
            "canonical_path": rel,
            "status": status,
            "row_count": row_count,
            "column_count": column_count,
            "byte_count": source.stat().st_size,
            "is_new_payload": needs_copy,
            "_needs_copy": needs_copy,
            "_source": source,
        }
        if needs_copy:
            seen_in_batch[sha] = plan
        plans.append(plan)

    created: list[str] = []
    try:  # ---- PHASE 2: writes only ----
        for plan in plans:
            if not plan["_needs_copy"]:
                continue
            destination = (repo_root / plan["canonical_path"]).resolve()
            if destination.exists():
                # CANONICAL IMMUTABILITY: a content-addressed object is never overwritten blindly.
                # If the destination already holds these exact bytes, reuse it; if it holds
                # different bytes, the store is inconsistent and that must surface, not be papered
                # over by a write.
                if _sha256_file(destination) != plan["sha256"]:
                    raise PFFIntakeError(
                        f"canonical destination {plan['canonical_path']} already exists with "
                        "different content; refusing to overwrite a content-addressed object"
                    )
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(plan["_source"], destination)
                created.append(plan["canonical_path"])
    except Exception as exc:  # noqa: BLE001 - re-raised with the strand enumerated
        raise _StrandedCopies(created, exc) from exc

    for plan in plans:
        plan.pop("_needs_copy", None)
        plan.pop("_source", None)
    return plans, created


def _review_state(conn: sqlite3.Connection) -> tuple[str, int]:
    """Evidence quality, computed from what is actually in the ledger — never inferred from
    transport success."""
    count = conn.execute(
        "select count(*) as n from payload where status = ?", (REVIEW_REQUIRED,)
    ).fetchone()["n"]
    return (REVIEW_REQUIRED if count else REVIEW_CLEAR), count


def _write_status_marker(path: Path, result: IntakeResult, source_clock: Optional[str]) -> None:
    """The latest-attempt marker.

    It deliberately omits `finished_at`/`completed_at`. Those outrank `retrieved_at` in
    `daily_control._COMPLETION_KEYS`, so emitting either would make an old manual download read as
    freshly acquired. Execution time is recorded as `indexed_at`, which daily_control does not
    consume for freshness.
    """
    payload = {
        "status": result.status,
        "review_state": result.review_state,
        "review_required_count": result.review_required_count,
        "indexed_at": _now_iso(),
        "payloads_indexed": result.payloads_indexed,
        "provenance_added": result.provenance_added,
    }
    if source_clock:
        payload["retrieved_at"] = source_clock
    if result.batch_id:
        payload["run_id"] = result.batch_id
    _atomic_write_json(Path(path), payload)


def _write_ready_marker(path: Path, batch_id: str, source_clock: Optional[str]) -> None:
    """The LAST-GOOD clock, advanced only on transport success.

    `daily_control._last_good_success` requires a nonempty `run_id` AND `captured_at`; without both
    the file is ignored entirely. `captured_at` is the SOURCE retrieval clock, not wall time.
    """
    if not source_clock:
        return
    _atomic_write_json(Path(path), {
        "status": STATUS_OK,
        "run_id": batch_id,
        "captured_at": source_clock,
        "indexed_at": _now_iso(),
    })


# --------------------------------------------------------------------------------------
# Backfill
# --------------------------------------------------------------------------------------


def backfill(
    *,
    inventory_csv: Path,
    download_map_csv: Path,
    ledger_path: Path,
    repo_root: Path,
    store_root: Path,
    marker_path: Optional[Path] = None,
    ready_marker_path: Optional[Path] = None,
) -> BackfillResult:
    """Index the ALREADY-CANONICAL objects in place.

    Backfill is not intake. The existing payloads are already in the content-addressed tree and
    already governed, so they need no sidecar and must not be copied, moved, or rewritten. Recorded
    hashes are verified against the objects; a mismatch is a corruption signal and that payload —
    with every offering referencing it — stays out of the ledger entirely.
    """
    inventory_csv, download_map_csv = Path(inventory_csv), Path(download_map_csv)
    repo_root, store_root = Path(repo_root), Path(store_root)
    result = BackfillResult()

    inv_rows = list(csv.DictReader(inventory_csv.open(newline="")))
    map_rows = list(csv.DictReader(download_map_csv.open(newline="")))
    result.offerings_seen = len(map_rows)

    conn = _connect(Path(ledger_path))
    try:
        _ensure_schema(conn)
        valid: dict[str, dict[str, Any]] = {}
        for row in inv_rows:
            sha = str(row.get("sha256") or "").strip()
            raw_path = Path(str(row.get("canonical_path") or ""))
            # Real inventory rows store ABSOLUTE canonical paths. Persisting them verbatim would
            # make the ledger machine-specific, which is the portability defect this program has
            # already shipped once.
            resolved = raw_path if raw_path.is_absolute() else (repo_root / raw_path)
            if not resolved.is_file():
                result.hash_mismatches.append(f"missing:{sha}")
                continue
            if _sha256_file(resolved) != sha:
                result.hash_mismatches.append(sha)
                continue
            try:
                resolved.resolve().relative_to(store_root.resolve())
            except ValueError:
                result.hash_mismatches.append(f"outside_store_root:{sha}")
                continue
            rel = _repo_relative(resolved, repo_root)
            valid[sha] = {"row": row, "rel": rel}

        for sha, item in valid.items():
            row = item["row"]
            if conn.execute("select 1 from payload where sha256 = ?", (sha,)).fetchone():
                continue
            conn.execute(
                "insert into payload(sha256, schema_sha256, league, report, scope, season, status,"
                " canonical_path, row_count, column_count, byte_count, first_retrieved_at)"
                " values (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    sha, row.get("schema_sha256"), row.get("league"), row.get("report"),
                    row.get("scope"), row.get("season"),
                    row.get("status") or DEFAULT_NEW_STATUS, item["rel"],
                    int(row.get("rows") or 0), int(row.get("columns") or 0),
                    int(row.get("bytes") or 0), row.get("retrieved_at"),
                ),
            )
            result.payloads_indexed += 1

        for index, row in enumerate(map_rows):
            sha = str(row.get("sha256") or "").strip()
            offering_id = str(row.get("original_file") or f"offering-{index}")
            if sha not in valid:
                result.unresolved_offerings.append(offering_id)
                continue
            if conn.execute(
                "select 1 from offering where offering_id = ? and batch_id = ?",
                (offering_id, "backfill"),
            ).fetchone():
                continue
            conn.execute(
                "insert into offering(offering_id, batch_id, sha256, league, report, scope, season,"
                " retrieved_at, source_path) values (?,?,?,?,?,?,?,?,?)",
                (
                    offering_id, "backfill", sha, row.get("league"), row.get("report"),
                    row.get("scope"), row.get("season"), row.get("retrieved_at"),
                    row.get("original_path"),
                ),
            )
            result.provenance_added += 1

        # A corrupt payload is EXCLUDED from the ledger along with every offering that references
        # it — but the independent, valid payloads still index. Rolling everything back would let
        # one bad object hold the whole governed archive hostage; indexing the bad one would be
        # worse. The batch is still reported FAILED, so the exit code is nonzero and the last-good
        # marker does not advance.
        conn.commit()
        result.source_retrieved_at = _max_retrieved_at(conn)
        result.review_state, result.review_required_count = _review_state(conn)
        if result.hash_mismatches or result.unresolved_offerings:
            result.status = STATUS_FAILED

        if marker_path is not None:
            _atomic_write_json(Path(marker_path), {
                "status": result.status,
                "review_state": result.review_state,
                "review_required_count": result.review_required_count,
                "indexed_at": _now_iso(),
                "run_id": "backfill",
                **({"retrieved_at": result.source_retrieved_at} if result.source_retrieved_at else {}),
            })
        if ready_marker_path is not None and result.status == STATUS_OK:
            _write_ready_marker(Path(ready_marker_path), "backfill", result.source_retrieved_at)
        return result
    finally:
        conn.close()
