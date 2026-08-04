"""CFBD DATA promotion — a fail-closed state machine for one pinned promotion.

Layer 1 -> Layer 2. This module MOVES BYTES. It does not validate, train, score,
refresh, or claim anything about predictive value.

**What this is.** The corrected CFBD QB college features exist in an isolated curated
table; the active Engine A training input still carries May-cache-derived values. This
module replaces the active file with the candidate under a pinned, independently
recomputed contract, leaving a durable preimage and an honest receipt.

**What this is NOT, stated because a promotion mechanism is exactly where an unearned
claim would hide.** It runs no bakeoff, writes no model, performs no network or paid
refresh, and its receipt records *what bytes moved and when* -- never that the new
values are better. ``decision_supported`` is ``False`` everywhere and the receipt
carries ``promotion_decision="not_applicable_data_movement"``. Nothing here is evidence
about QB rushing (H2), which remains a registered hypothesis UNDER TEST; none of the
promoted fields is a rushing field.

**Two independent signals, deliberately.** The full-file SHA answers *byte provenance*;
the keyed projection digest answers *CFBD retention*. They are not interchangeable: a
legitimate unrelated rewrite changes the file SHA while every promoted field survives,
and reporting that as "CFBD reverted" would be a false alarm that trains readers to
ignore the real one.

**Read-only is literal.** A run without ``confirm`` creates no file and no directory --
not even a lock. Every mutating entrypoint takes the lock only when it is actually
going to write.

Spec of record: ``cfbd_qb_projection.v1`` (see ``PROJECTION_FIELDS``), converged
cross-lane against a golden vector before it was allowed to be load-bearing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Canonical projection contract — cfbd_qb_projection.v1 ────────────────────

PROJECTION_DIGEST_VERSION = "cfbd_qb_projection.v1"

#: Ordered, grouped per metric (value, source, missing). Order is part of the
#: contract: changing it changes the digest and requires a new version + golden vector.
PROJECTION_FIELDS: tuple[str, ...] = (
    "gsis_id",
    "qb_completion_pct_final",
    "qb_completion_pct_final_source",
    "qb_completion_pct_final_missing",
    "qb_yards_per_attempt_final",
    "qb_yards_per_attempt_final_source",
    "qb_yards_per_attempt_final_missing",
    "qb_td_int_ratio_final",
    "qb_td_int_ratio_final_source",
    "qb_td_int_ratio_final_missing",
    "qb_sack_rate_final",
    "qb_sack_rate_final_source",
    "qb_sack_rate_final_missing",
)

#: The 12 promoted columns — everything in the projection except the identity key.
PROMOTED_COLUMNS = frozenset(PROJECTION_FIELDS[1:])

MANIFEST_SCHEMA_VERSION = "cfbd_foundation.v1"

#: A receipt missing any of these is not a receipt. A parseable mapping is not
#: evidence of anything; these are the fields every consumer reads.
REQUIRED_RECEIPT_KEYS = frozenset(
    {
        "status",
        "before_sha256",
        "after_sha256",
        "before_projection_sha256",
        "after_projection_sha256",
        "active_path",
        "candidate_path",
        "preimage_path",
        # The honesty block is REQUIRED, not checked-if-present. An optional honesty
        # field is not an honesty field: omitting it was indistinguishable from
        # asserting it, and omission was the cheaper way to get a receipt accepted.
        "decision_supported",
        "model_changed",
        "bakeoff_run",
        "predictive_validation_run",
        "promotion_decision",
    }
)

PROMOTION_DECISION = "not_applicable_data_movement"

# The authorized one-time promotion. These are NOT eternal schema constants: a
# regenerated candidate starts a NEW reviewed specification with new pins.
_REAL_ACTIVE_SHA256 = "b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38"
_REAL_CANDIDATE_SHA256 = "15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0"
_REAL_ACTIVE_PROJECTION = "683384b89c860f67bf963d2e03022c9fc119572b52b3afc95c26b919d347f3b3"
_REAL_CANDIDATE_PROJECTION = "f2239463bf8da3a48d114b613cb75782d3bccc797cef059c071c1d08795c1dd0"


class CfbdPromotionError(RuntimeError):
    """A fail-closed refusal. ``reason`` is the machine-readable cause."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


def _fail(reason: str, message: str = "") -> None:
    raise CfbdPromotionError(reason, message)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ── Projection digest ────────────────────────────────────────────────────────


def _read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_projection_rows(path: Path) -> list[dict[str, str]]:
    """Rows plus a HEADER check. A file whose header lacks the projection columns has
    no projection at all -- without this, a zero-row unrelated CSV hashed cleanly over
    an empty list and read as drift instead of as unreadable."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or ())
        missing = [field for field in PROJECTION_FIELDS if field not in header]
        if missing:
            _fail("projection_missing_cell", f"header lacks required fields: {missing}")
        return list(reader)


def _projection_rows(rows: Iterable[Mapping[str, Any]]) -> list[list[str]]:
    ordered: list[list[str]] = []
    seen: set[str] = set()
    for row in rows:
        # csv.DictReader files surplus cells under the restkey (None). A ragged row
        # is malformed input, and letting it share a digest with a well-formed row
        # would make the digest answer a question it cannot actually answer.
        if None in row:
            _fail("projection_extra_cell", "row carries cells beyond the header")
        values: list[str] = []
        for field in PROJECTION_FIELDS:
            value = row.get(field)
            if value is None:
                _fail("projection_missing_cell", f"row is missing required cell {field!r}")
            values.append(value)
        key = values[0]
        if key == "":
            _fail("blank_identity", "gsis_id is blank")
        if key in seen:
            _fail("duplicate_identity", f"gsis_id {key!r} appears more than once")
        seen.add(key)
        ordered.append(values)
    # Sort by the UTF-8 BYTE sequence, not str ordering. This deliberately makes the
    # digest insensitive to file-row reordering; the separate row-order gate governs
    # that event, so a reorder cannot masquerade as CFBD value loss.
    ordered.sort(key=lambda values: values[0].encode("utf-8"))
    return ordered


def projection_digest(path: Path) -> str:
    """SHA-256 of the canonical keyed projection under ``cfbd_qb_projection.v1``.

    Strings are preserved exactly -- no trimming, numeric coercion, Unicode
    normalization, or null folding. ``""`` is a real value and is distinct from a
    missing cell, which is fatal; so is a surplus cell.
    """
    ordered = _projection_rows(_read_projection_rows(path))
    payload = [PROJECTION_DIGEST_VERSION, list(PROJECTION_FIELDS), ordered]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ── The pinned specification ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PromotionSpec:
    """One authorized promotion. Every pin is independently recomputed and fatal."""

    active_path: Path
    candidate_path: Path
    manifest_path: Path
    preimage_path: Path
    receipt_path: Path
    rollback_receipt_path: Path
    lock_path: Path
    expected_active_sha256: str
    expected_candidate_sha256: str
    expected_active_projection_sha256: str
    expected_candidate_projection_sha256: str
    expected_row_count: int
    expected_column_count: int
    expected_changed_row_count: int
    expected_changed_cell_count: int
    allowed_changed_columns: frozenset[str]
    identity_columns: tuple[str, ...]


def default_promotion_spec(root: Path | None = None) -> PromotionSpec:
    """The authorized 2026-08-03 promotion. Pins are literals; nothing is read here."""
    base = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    training = base / "app" / "data" / "training"
    foundation = base / "app" / "data" / "sources" / "cfbd_foundation"
    history = training / "cfbd_promotion_history"
    return PromotionSpec(
        active_path=training / "prospects_with_outcomes_v3.csv",
        candidate_path=foundation / "curated" / "prospects_with_outcomes_v3.csv",
        manifest_path=foundation / "manifest_latest.json",
        preimage_path=history / "preimages" / f"{_REAL_ACTIVE_SHA256}.csv",
        receipt_path=history / "receipts" / f"{_REAL_CANDIDATE_SHA256}.json",
        rollback_receipt_path=history / "receipts" / f"rollback-{_REAL_CANDIDATE_SHA256}.json",
        lock_path=history / "promotion.lock",
        expected_active_sha256=_REAL_ACTIVE_SHA256,
        expected_candidate_sha256=_REAL_CANDIDATE_SHA256,
        expected_active_projection_sha256=_REAL_ACTIVE_PROJECTION,
        expected_candidate_projection_sha256=_REAL_CANDIDATE_PROJECTION,
        expected_row_count=874,
        expected_column_count=173,
        expected_changed_row_count=117,
        expected_changed_cell_count=1123,
        allowed_changed_columns=PROMOTED_COLUMNS,
        identity_columns=("gsis_id", "pfr_player_name"),
    )


# ── Validation — read-only, every gate independently recomputed ──────────────


def _same_file(first: Path, second: Path) -> bool:
    """Path IDENTITY, not spelling. The single comparison rule for this module.

    A symlink and a ``..`` detour are different strings for the same bytes. Lexical
    equality let both slip past jurisdiction, so the guard stood down while the writer
    reached the promoted file through another spelling. Every path comparison here --
    role distinctness AND guard jurisdiction -- goes through this one function, so a
    future fix cannot close it in one place and leave it open in the other.
    """
    first, second = Path(first), Path(second)
    if first == second:
        return True
    try:
        if first.resolve(strict=False) == second.resolve(strict=False):
            return True
        if first.exists() and second.exists() and first.samefile(second):
            return True
    except OSError as exc:
        # UNKNOWN IS A THIRD STATE, NOT False. This previously returned False, and the
        # two callers read that word differently: role distinctness heard "assume
        # distinct", but guard jurisdiction heard "unrelated file" and PERMITTED THE
        # WRITE. An OS/stat failure proves neither sameness nor difference, and at a
        # fail-closed admission boundary uncertainty must never become permission.
        # Raising makes both callers fail closed on the same fact.
        _fail("path_identity_unreadable", f"cannot establish identity of {first} vs {second}: {exc}")
    return False


_ARTIFACT_ROLES = (
    "active_path",
    "candidate_path",
    # The manifest is a GOVERNED artifact, not merely an input. Omitting it let a
    # lock alias onto it: validation read it, the lock declared it stale, unlinked it,
    # and the promotion "succeeded" having deleted the provenance it depended on.
    "manifest_path",
    "preimage_path",
    "receipt_path",
    "rollback_receipt_path",
    "lock_path",
)


def _assert_distinct_paths(spec: PromotionSpec) -> None:
    """Every artifact role must be its own file. Checked BEFORE anything is opened.

    These are not interchangeable slots. A lock aliased onto a data file gets
    ``unlink``ed as "stale"; a receipt aliased onto the preimage replaces the only
    copy of the old bytes with JSON. Each collapse destroys a different guarantee, so
    the whole role set is checked pairwise -- by path, by resolved path, and by inode.
    """
    paths = {role: Path(getattr(spec, role)) for role in _ARTIFACT_ROLES}

    for index, left in enumerate(_ARTIFACT_ROLES):
        for right in _ARTIFACT_ROLES[index + 1 :]:
            if _same_file(paths[left], paths[right]):
                _fail("path_alias", f"{left} and {right} are the same file")


def _check_identity_validity(rows: Sequence[Mapping[str, str]], columns: Sequence[str]) -> None:
    for column in columns:
        seen: set[str] = set()
        for row in rows:
            value = row.get(column)
            if value is None:
                _fail("projection_missing_cell", f"missing identity column {column!r}")
            if value == "":
                _fail("blank_identity", f"{column} is blank")
            if value in seen:
                _fail("duplicate_identity", f"{column} {value!r} appears more than once")
            seen.add(value)


def _raw_files(raw_root: Path) -> list[Path]:
    """Raw snapshot payloads. ``manifest.json`` is excluded by construction: it
    *contains* the digest of these files, so including it is self-referential."""
    return [p for p in sorted(Path(raw_root).glob("*.json")) if p.name != "manifest.json"]


def _raw_content_sha256(raw_root: Path) -> str:
    combined = hashlib.sha256()
    for path in _raw_files(raw_root):
        combined.update(path.name.encode("utf-8"))
        combined.update(_file_sha256(path).encode("ascii"))
    return combined.hexdigest()


def _validate_manifest_chain(spec: PromotionSpec) -> Mapping[str, Any]:
    manifest = json.loads(Path(spec.manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        _fail("manifest_schema_mismatch", "manifest schema_version is not the governed version")
    if manifest.get("input_sha256") != spec.expected_active_sha256:
        _fail("manifest_input_mismatch", "manifest input_sha256 does not match the pinned active")
    if manifest.get("curated_sha256") != spec.expected_candidate_sha256:
        _fail("manifest_candidate_mismatch", "manifest curated_sha256 does not match the pin")

    raw_root = Path(manifest["raw_root"]).resolve()
    governed_root = (Path(spec.manifest_path).parent / "raw").resolve()
    # A manifest is an untrusted document. Left ungoverned, `raw_root` is an
    # arbitrary-path read that would let evidence live outside the governed tree.
    if governed_root != raw_root and governed_root not in raw_root.parents:
        _fail("raw_root_outside_governed_root", f"raw_root {raw_root} escapes {governed_root}")

    raw_manifest_path = raw_root / "manifest.json"
    if not raw_manifest_path.exists():
        _fail("raw_manifest_mismatch", "immutable run manifest is absent")
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    chain_fields = (
        "schema_version",
        "run_id",
        "input_sha256",
        "curated_sha256",
        "raw_content_sha256",
        "raw_file_count",
    )
    for field in chain_fields:
        if manifest.get(field) != raw_manifest.get(field):
            _fail("raw_manifest_mismatch", f"latest and immutable manifests disagree on {field!r}")

    # Recomputed from bytes on disk. Two agreeing manifests are not evidence about
    # the files they describe -- they are evidence about each other.
    if _raw_content_sha256(raw_root) != manifest.get("raw_content_sha256"):
        _fail("raw_content_mismatch", "raw snapshot bytes do not match the manifest chain")
    actual_count = len(_raw_files(raw_root))
    # raw_file_count is REQUIRED, not optional. Chain equality between the two
    # manifests is checked above; presence and recomputed equality are checked here.
    # All three are mandatory: a coordinated deletion plus a rewritten digest is
    # internally consistent, and only an independently recomputed count catches it --
    # while an ABSENT count would have made the whole check silently conditional,
    # which is the same hole wearing a different hat.
    claimed = manifest.get("raw_file_count")
    if claimed is None:
        _fail("raw_file_count_mismatch", "manifest does not declare raw_file_count")
    if claimed != actual_count:
        # NOTE: the message reads `claimed`, never manifest['raw_file_count']. An
        # earlier version interpolated the key while proving it absent and raised
        # KeyError -- a fail-closed path that crashed instead of naming its reason.
        _fail("raw_file_count_mismatch", f"{actual_count} raw files present, manifest claims {claimed}")
    return {**manifest, "raw_file_count_actual": actual_count}


def validate_promotion(spec: PromotionSpec) -> dict[str, Any]:
    """Recompute every gate. Returns a descriptive report; raises on any violation."""
    _assert_distinct_paths(spec)

    if _file_sha256(spec.active_path) != spec.expected_active_sha256:
        _fail("active_sha_mismatch", "active file is not the pinned pre-promotion bytes")
    if _file_sha256(spec.candidate_path) != spec.expected_candidate_sha256:
        _fail("candidate_sha_mismatch", "candidate file is not the pinned bytes")
    if projection_digest(spec.active_path) != spec.expected_active_projection_sha256:
        _fail("active_projection_mismatch", "active projection is not the pinned digest")
    if projection_digest(spec.candidate_path) != spec.expected_candidate_projection_sha256:
        _fail("candidate_projection_mismatch", "candidate projection is not the pinned digest")

    manifest = _validate_manifest_chain(spec)

    active_rows = _read_rows(spec.active_path)
    candidate_rows = _read_rows(spec.candidate_path)

    if len(active_rows) != spec.expected_row_count or len(candidate_rows) != spec.expected_row_count:
        _fail("row_count_mismatch", "row count is not the pinned count")

    active_header = list(active_rows[0]) if active_rows else []
    candidate_header = list(candidate_rows[0]) if candidate_rows else []
    if active_header != candidate_header or len(candidate_header) != spec.expected_column_count:
        _fail("header_mismatch", "header set or order is not identical to the pinned header")

    _check_identity_validity(candidate_rows, spec.identity_columns)

    # PRIMARY identity governs row ORDER; secondary identity is an association check.
    # Conflating them misnames a swapped display name as a reordering.
    primary = spec.identity_columns[0]
    active_primary = [row[primary] for row in active_rows]
    candidate_primary = [row[primary] for row in candidate_rows]
    if active_primary != candidate_primary:
        if sorted(active_primary) == sorted(candidate_primary):
            _fail("row_order_mismatch", f"{primary} sequence differs; rows were reordered")
        _fail("identity_mismatch", f"{primary} values changed between active and candidate")
    for column in spec.identity_columns[1:]:
        if [row[column] for row in active_rows] != [row[column] for row in candidate_rows]:
            _fail("identity_mismatch", f"{column} associations changed at fixed {primary} order")

    delta = _compute_delta(active_rows, candidate_rows, candidate_header)

    non_qb = {pos: n for pos, n in delta["changed_positions"].items() if pos != "QB"}
    if non_qb:
        _fail("non_qb_change", f"non-QB rows changed: {sorted(non_qb)}")
    disallowed = set(delta["changed_columns"]) - set(spec.allowed_changed_columns)
    if disallowed:
        _fail("changed_column_not_allowed", f"columns outside the allowlist changed: {sorted(disallowed)}")
    if delta["changed_row_count"] != spec.expected_changed_row_count:
        _fail("changed_row_count_mismatch", f"{delta['changed_row_count']} rows changed, expected {spec.expected_changed_row_count}")
    if delta["changed_cell_count"] != spec.expected_changed_cell_count:
        _fail("changed_cell_count_mismatch", f"{delta['changed_cell_count']} cells changed, expected {spec.expected_changed_cell_count}")

    return {
        "status": "valid",
        "row_count": len(candidate_rows),
        "column_count": len(candidate_header),
        **delta,
        "manifest_run_id": manifest.get("run_id"),
        "source_manifest_sha256": _file_sha256(spec.manifest_path),
        "raw_content_sha256": manifest.get("raw_content_sha256"),
        "raw_file_count": manifest["raw_file_count_actual"],
        "decision_supported": False,
    }


def _compute_delta(
    before: Sequence[Mapping[str, str]],
    after: Sequence[Mapping[str, str]],
    header: Sequence[str],
) -> dict[str, Any]:
    changed_cells = 0
    changed_columns: set[str] = set()
    changed_positions: dict[str, int] = {}
    for before_row, after_row in zip(before, after, strict=True):
        row_changed = False
        for column in header:
            if before_row.get(column) != after_row.get(column):
                changed_cells += 1
                changed_columns.add(column)
                row_changed = True
        if row_changed:
            position = after_row.get("position", "")
            changed_positions[position] = changed_positions.get(position, 0) + 1
    return {
        "changed_row_count": sum(changed_positions.values()),
        "changed_cell_count": changed_cells,
        "changed_columns": sorted(changed_columns),
        "changed_positions": changed_positions,
    }


# ── Durable primitives ───────────────────────────────────────────────────────


def _fsync_path(path: Path) -> None:
    handle = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def _atomic_write_bytes(target: Path, payload: bytes) -> None:
    """Sibling temp -> fsync file -> replace -> fsync parent directory.

    The temp MUST be a sibling: a cross-filesystem temp makes ``os.replace``
    non-atomic, which is the whole property being bought here. The temp path is
    deterministic, so it is also a predictable target -- an existing entry there is
    refused rather than opened, because a symlink planted at that name would make
    ``open("wb")`` write straight through to whatever it points at.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    if temporary.is_symlink() or temporary.exists():
        _fail("temporary_path_collision", f"{temporary} already exists; refusing to write through it")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        _fsync_path(target.parent)
    except CfbdPromotionError:
        raise
    except FileExistsError as exc:
        _fail("temporary_path_collision", f"{temporary} appeared concurrently: {exc}")
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise CfbdPromotionError("durability_failure", f"durable write failed: {exc}") from exc


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _lock_is_stale(lock_path: Path) -> bool:
    try:
        text = lock_path.read_text(encoding="utf-8")
    except OSError:
        return True
    marker = "pid="
    if marker not in text:
        return True
    raw = text.split(marker, 1)[1].split()[0].strip()
    try:
        return not _pid_is_alive(int(raw))
    except ValueError:
        return True


@contextmanager
def promotion_lock(spec: PromotionSpec):
    """Exclusive promotion lock. A lock owned by a dead PID is stolen, not deadlocked.

    Acquired ONLY on a path that is going to write: taking it during a read-only run
    would leave a directory and a file behind and make "read-only" false.
    """
    lock_path = Path(spec.lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if not _lock_is_stale(lock_path):
            _fail("promotion_locked", f"another promotion holds {lock_path}")
        lock_path.unlink(missing_ok=True)
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, f"cfbd_data_promotion pid={os.getpid()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


# ── Receipts — records of byte movement, never of validation ─────────────────


def _receipt_payload(
    spec: PromotionSpec,
    report: Mapping[str, Any],
    status: str,
    *,
    recovered_from_split: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": "cfbd_data_promotion.v1",
        "projection_digest_version": PROJECTION_DIGEST_VERSION,
        "recorded_at": _utc_now_iso(),
        "active_path": str(spec.active_path),
        "candidate_path": str(spec.candidate_path),
        "preimage_path": str(spec.preimage_path),
        "before_sha256": spec.expected_active_sha256,
        "after_sha256": spec.expected_candidate_sha256,
        "before_projection_sha256": spec.expected_active_projection_sha256,
        "after_projection_sha256": spec.expected_candidate_projection_sha256,
        "manifest_run_id": report.get("manifest_run_id"),
        "source_manifest_sha256": report.get("source_manifest_sha256"),
        "raw_content_sha256": report.get("raw_content_sha256"),
        "raw_file_count": report.get("raw_file_count"),
        "changed_row_count": report.get("changed_row_count"),
        "changed_cell_count": report.get("changed_cell_count"),
        "changed_columns": report.get("changed_columns"),
        "recovered_from_split": recovered_from_split,
        # The honesty block. This is data movement; nothing here was validated.
        "decision_supported": False,
        "model_changed": False,
        "bakeoff_run": False,
        "predictive_validation_run": False,
        "promotion_decision": PROMOTION_DECISION,
    }


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write_bytes(Path(path), text.encode("utf-8"))


def _parse_receipt(path: Path, *, corrupt_reason: str, invalid_reason: str) -> Mapping[str, Any] | None:
    """Absent -> None. Unparseable -> ``corrupt_reason``. Parseable but not a receipt
    -> ``invalid_reason``. A parseable mapping is not evidence of anything."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        _fail(corrupt_reason, "receipt is not valid JSON")
    if not isinstance(payload, Mapping):
        _fail(invalid_reason, "receipt is not a JSON object")
    missing = REQUIRED_RECEIPT_KEYS - set(payload)
    if missing:
        _fail(invalid_reason, f"receipt is missing required fields: {sorted(missing)}")
    return payload


def _assert_receipt_matches_spec(spec: PromotionSpec, receipt: Mapping[str, Any]) -> None:
    """A receipt must be THIS transaction's receipt, and must carry the honesty block.

    Key presence proved only that a JSON object existed. A ``rolled_back`` status, a
    ``decision_supported: true``, a foreign projection digest, or a rewritten
    ``preimage_path`` naming the candidate all satisfied presence while describing a
    different event entirely.
    """
    governed = {
        "status": "promoted",
        "before_sha256": spec.expected_active_sha256,
        "after_sha256": spec.expected_candidate_sha256,
        "before_projection_sha256": spec.expected_active_projection_sha256,
        "after_projection_sha256": spec.expected_candidate_projection_sha256,
    }
    for field, expected in governed.items():
        if receipt.get(field) != expected:
            _fail("receipt_invalid", f"receipt {field}={receipt.get(field)!r} is not {expected!r}")
    for field, expected_path in (
        ("active_path", spec.active_path),
        ("candidate_path", spec.candidate_path),
        ("preimage_path", spec.preimage_path),
    ):
        if Path(receipt.get(field, "")) != Path(expected_path):
            _fail("receipt_invalid", f"receipt {field} is not this transaction's")
    # The honesty block is part of the contract, not decoration: a receipt asserting
    # decision support would be the exact overclaim this module exists to prevent.
    for field in ("decision_supported", "model_changed", "bakeoff_run", "predictive_validation_run"):
        if receipt.get(field) is not False:
            _fail("receipt_invalid", f"receipt {field} must be false, got {receipt.get(field)!r}")
    if receipt.get("promotion_decision") != PROMOTION_DECISION:
        _fail("receipt_invalid", f"receipt promotion_decision must be {PROMOTION_DECISION!r}")


def _verify_named_preimage(spec: PromotionSpec, receipt: Mapping[str, Any]) -> None:
    named = Path(receipt.get("preimage_path", spec.preimage_path))
    if not named.exists():
        _fail("evidence_incomplete", f"receipt names a preimage that does not exist: {named}")
    if _file_sha256(named) != receipt.get("before_sha256"):
        _fail("evidence_incomplete", "named preimage does not hash to the receipt's before_sha256")


# ── The promotion transaction ────────────────────────────────────────────────


def _noop_hook(_stage: str) -> None:
    return None


def promote_cfbd_data(
    spec: PromotionSpec,
    *,
    confirm: bool = False,
    fault_hook: Callable[[str], None] = _noop_hook,
) -> dict[str, Any]:
    """Validate, then (only with ``confirm``) atomically replace the active file.

    Without ``confirm`` this creates nothing at all -- no lock, no directory, no file.
    """
    _assert_distinct_paths(spec)
    active_sha = _file_sha256(spec.active_path) if Path(spec.active_path).exists() else ""

    # An unreadable receipt is an OCCUPIED EVIDENCE PATH here, not a recovery signal;
    # `recover` is where corruption means `receipt_corrupt`.
    receipt = _parse_receipt(
        spec.receipt_path, corrupt_reason="evidence_collision", invalid_reason="receipt_invalid"
    )
    if receipt is not None:
        if receipt.get("after_sha256") != spec.expected_candidate_sha256:
            _fail("evidence_collision", "a different receipt already occupies this path")
        _assert_receipt_matches_spec(spec, receipt)
        _verify_named_preimage(spec, receipt)
        if active_sha != spec.expected_candidate_sha256:
            _fail("evidence_collision", "a receipt exists but active is not the promoted bytes")
        return {
            "status": "already_promoted",
            "decision_supported": False,
            "model_changed": False,
            "bakeoff_run": False,
        }

    if Path(spec.preimage_path).exists() and _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
        _fail("evidence_collision", "unrelated bytes already occupy the preimage path")

    report = validate_promotion(spec)

    if not confirm:
        return {
            "status": "dry_run",
            "would_promote": True,
            "validation": report,
            "decision_supported": False,
            "model_changed": False,
            "bakeoff_run": False,
        }

    with promotion_lock(spec):
        # Everything above ran UNLOCKED, so it describes a state that may already be
        # gone. Re-establish it before the first byte is written, not after.
        if _file_sha256(spec.active_path) != spec.expected_active_sha256:
            _fail("active_changed_during_promotion", "active changed before the lock was held")
        if _file_sha256(spec.candidate_path) != spec.expected_candidate_sha256:
            _fail("candidate_changed_during_promotion", "candidate changed before the lock was held")
        # Data CAS is not enough: the EVIDENCE paths were also checked unlocked, and a
        # concurrent writer can occupy them in between. Overwriting someone else's
        # durable evidence is exactly as destructive as overwriting their data.
        if Path(spec.receipt_path).exists():
            _fail("evidence_collision", "receipt path was occupied before the lock was held")
        if Path(spec.preimage_path).exists() and _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
            _fail("evidence_collision", "preimage path was occupied before the lock was held")

        # Re-run the WHOLE validation under the lock, not another hand-picked subset.
        # The pre-lock report also covered the manifest and raw-snapshot chain, and
        # those can move too -- promoting on a stale provenance read and then
        # receipting it would record a lineage that was already false when written.
        # Choosing "the complete check" over "the checks I thought mattered" is the
        # correction here: every earlier gap in this module came from a short set.
        report = validate_promotion(spec)

        original = Path(spec.active_path).read_bytes()
        candidate_bytes = Path(spec.candidate_path).read_bytes()

        # Durable preimage FIRST. If this cannot be made durable, nothing moves.
        _atomic_write_bytes(Path(spec.preimage_path), original)
        if _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
            _fail("durability_failure", "preimage did not read back as the pinned active bytes")

        fault_hook("before_active_replace")

        # TOCTOU: validation proved a state that may no longer hold.
        if _file_sha256(spec.candidate_path) != spec.expected_candidate_sha256:
            _fail("candidate_changed_during_promotion", "candidate changed after validation")
        if _file_sha256(spec.active_path) != spec.expected_active_sha256:
            _fail("active_changed_during_promotion", "active changed after validation")

        _atomic_write_bytes(Path(spec.active_path), candidate_bytes)

        fault_hook("after_active_replace")

        if _file_sha256(spec.active_path) != spec.expected_candidate_sha256 or (
            projection_digest(spec.active_path) != spec.expected_candidate_projection_sha256
        ):
            _fail("post_replace_verification_failed", "active did not read back as the candidate")

        _write_json_atomic(spec.receipt_path, _receipt_payload(spec, report, "promoted"))
        return {
            "status": "promoted",
            "before_sha256": spec.expected_active_sha256,
            "after_sha256": spec.expected_candidate_sha256,
            "decision_supported": False,
            "model_changed": False,
            "bakeoff_run": False,
        }


def recover_cfbd_promotion(spec: PromotionSpec, *, confirm: bool = False) -> dict[str, Any]:
    """Classify an interrupted promotion. Never invents a success.

    ``confirm=False`` classifies and writes nothing. Only the post-replace split state
    has a repair to perform, and only with ``confirm``.
    """
    # The role gate guards every lock-taking entrypoint, not just promotion. Recovery
    # omitted it, so a lock aliased onto the manifest was unlinked as "stale",
    # replaced with lock text, and then read back as provenance -- the exact G16
    # failure, surviving in the one entrypoint the G16 fix did not reach.
    _assert_distinct_paths(spec)
    receipt = _parse_receipt(
        spec.receipt_path, corrupt_reason="receipt_corrupt", invalid_reason="receipt_invalid"
    )
    active_sha = _file_sha256(spec.active_path) if Path(spec.active_path).exists() else ""

    if active_sha == spec.expected_active_sha256:
        if receipt is None:
            return {"status": "clean_pre_promotion", "decision_supported": False}
        _fail("receipt_active_mismatch", "a promotion receipt exists but active is the old bytes")

    if active_sha == spec.expected_candidate_sha256:
        if receipt is not None:
            _assert_receipt_matches_spec(spec, receipt)
            _verify_named_preimage(spec, receipt)
            return {"status": "complete", "decision_supported": False}
        if not Path(spec.preimage_path).exists():
            _fail("evidence_incomplete", "active is promoted but no preimage exists")
        if _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
            _fail("evidence_incomplete", "preimage is not the pinned pre-promotion bytes")

        if not confirm:
            return {"status": "would_recover_post_replace", "decision_supported": False}

        with promotion_lock(spec):
            # Classification happened unlocked; a concurrent writer may have moved
            # active since. Recheck before receipting a state that no longer exists.
            if _file_sha256(spec.active_path) != spec.expected_candidate_sha256:
                _fail("active_changed_during_recovery", "active changed before the lock was held")
            if Path(spec.receipt_path).exists():
                _fail("evidence_collision", "receipt path was occupied before the lock was held")
            if not Path(spec.preimage_path).exists():
                _fail("evidence_incomplete", "preimage disappeared before the lock was held")
            if _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
                _fail("evidence_incomplete", "preimage was replaced before the lock was held")
            # The delta is RECOMPUTED from the preimage and the live active file. An
            # earlier version wrote the whole allowlist here, which fabricated a
            # 12-column change into a durable record when only 3 columns had moved.
            before_rows = _read_rows(spec.preimage_path)
            after_rows = _read_rows(spec.active_path)
            header = list(after_rows[0]) if after_rows else []
            delta = _compute_delta(before_rows, after_rows, header)
            manifest = _validate_manifest_chain(spec)
            report = {
                **delta,
                "manifest_run_id": manifest.get("run_id"),
                "source_manifest_sha256": _file_sha256(spec.manifest_path),
                "raw_content_sha256": manifest.get("raw_content_sha256"),
                "raw_file_count": manifest["raw_file_count_actual"],
            }
            _write_json_atomic(
                spec.receipt_path,
                _receipt_payload(spec, report, "promoted", recovered_from_split=True),
            )
        return {"status": "recovered_post_replace", "decision_supported": False}

    _fail("unknown_active_state", "active is neither the pinned pre- nor post-promotion bytes")
    raise AssertionError("unreachable")  # pragma: no cover


def rollback_cfbd_promotion(spec: PromotionSpec, *, confirm: bool = False) -> dict[str, Any]:
    """Restore the preimage, CAS-guarded. Refuses to erase bytes it did not write."""
    _assert_distinct_paths(spec)
    if not Path(spec.preimage_path).exists():
        _fail("evidence_incomplete", "no preimage exists to roll back to")
    if _file_sha256(spec.active_path) != spec.expected_candidate_sha256:
        _fail("rollback_cas_mismatch", "active is not the promoted bytes; refusing to overwrite")
    if _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
        _fail("evidence_incomplete", "preimage is not the pinned pre-promotion bytes")

    if not confirm:
        return {"status": "would_roll_back", "decision_supported": False}

    with promotion_lock(spec):
        # Recheck the CAS under the lock: the classification above was unlocked, and
        # rolling back over a concurrent writer's bytes would destroy them silently.
        if _file_sha256(spec.active_path) != spec.expected_candidate_sha256:
            _fail("rollback_cas_mismatch", "active changed before the lock was held")
        # Refuse an occupied rollback receipt BEFORE active moves, not after: the
        # alternative leaves the data rolled back and the evidence overwritten.
        if Path(spec.rollback_receipt_path).exists():
            _fail("evidence_collision", "unrelated bytes already occupy the rollback receipt path")
        # Re-pin the preimage under the lock. Copying a concurrently replaced preimage
        # over active destroys the promoted bytes and only THEN fails verification --
        # a refusal that arrives after the damage is not a refusal.
        if not Path(spec.preimage_path).exists():
            _fail("evidence_incomplete", "preimage disappeared before the lock was held")
        if _file_sha256(spec.preimage_path) != spec.expected_active_sha256:
            _fail("evidence_incomplete", "preimage was replaced before the lock was held")

        _atomic_write_bytes(Path(spec.active_path), Path(spec.preimage_path).read_bytes())
        if _file_sha256(spec.active_path) != spec.expected_active_sha256:
            _fail("post_replace_verification_failed", "rollback did not read back as the preimage")

        # The promotion receipt is NOT deleted: it is the record that the promotion
        # happened. The rollback gets its own receipt alongside it.
        payload = {
            "status": "rolled_back",
            "schema_version": "cfbd_data_promotion.v1",
            "recorded_at": _utc_now_iso(),
            "restored_sha256": spec.expected_active_sha256,
            "rolled_back_from_sha256": spec.expected_candidate_sha256,
            "decision_supported": False,
            "model_changed": False,
            "bakeoff_run": False,
            "predictive_validation_run": False,
            "promotion_decision": "not_applicable_data_movement",
        }
        _write_json_atomic(spec.rollback_receipt_path, payload)
    return {"status": "rolled_back", "decision_supported": False}


# ── Destructive-writer guard ─────────────────────────────────────────────────


def guard_destructive_cfbd_write(
    *,
    active_path: Path,
    receipt_path: Path,
    writer_name: str,
    governed_active_path: Path | None = None,
) -> None:
    """Refuse a destructive rewrite while CFBD promotion evidence exists.

    A promotion is not durable by construction: producers that reconstruct or
    recompute the training CSV will silently revert it, and nothing downstream would
    say so. This is the admission boundary that turns that silent regression into a
    loud refusal.

    **No receipt is the normal case and is silent. Everything else fails closed.** An
    unreadable receipt, a missing active file, an unreadable projection, or a
    projection that has already drifted are all states where this function cannot
    prove the write is safe -- and a guard that cannot prove safety must not grant it.
    """
    receipt_path = Path(receipt_path)
    active_path = Path(active_path)

    # ── JURISDICTION FIRST, from TRUSTED CALLER CONFIGURATION ────────────────
    # `governed_active_path` is supplied by the caller's own configuration, never
    # read from the artifact under judgment. Defaults to `active_path`, i.e. IN
    # jurisdiction, so an omission fails closed rather than open.
    #
    # Two corrections are encoded here, both from review:
    #  1. My first repair took jurisdiction from `receipt.active_path` -- letting the
    #     RECEIPT DECIDE ITS OWN JURISDICTION. Editing that one field to a decoy left a
    #     structurally complete, honest-looking receipt that silently disarmed the guard
    #     on the real promoted file. The artifact being judged could opt itself out.
    #  2. Jurisdiction is settled BEFORE the receipt is read at all. Validating a
    #     malformed real receipt first would preserve exactly the cross-world coupling
    #     that broke four tests: a fixture target must not be judged by another world's
    #     evidence, however broken that evidence is.
    governed = Path(governed_active_path) if governed_active_path is not None else active_path
    if not _same_file(active_path, governed):
        return

    if not receipt_path.exists():
        return

    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        _fail("promotion_receipt_invalid", f"{receipt_path} exists but is not readable JSON")
    if not isinstance(payload, Mapping):
        _fail("promotion_receipt_invalid", f"{receipt_path} is not a JSON object")
    # A lone after_projection_sha256 is not a receipt. The guard has no spec to check
    # values against, so it enforces STRUCTURE: the full governed key set plus the
    # honesty block. Partial occupied evidence means the state is unknown, and unknown
    # is not permission.
    missing = REQUIRED_RECEIPT_KEYS - set(payload)
    if missing:
        _fail("promotion_receipt_invalid", f"{receipt_path} is missing {sorted(missing)}")
    for field in ("decision_supported", "model_changed", "bakeoff_run", "predictive_validation_run"):
        if payload.get(field) is not False:
            _fail("promotion_receipt_invalid", f"{receipt_path} {field} must be false")
    if payload.get("promotion_decision") != PROMOTION_DECISION:
        _fail("promotion_receipt_invalid", f"{receipt_path} promotion_decision is not governed")

    # Inside jurisdiction the receipt MUST describe the GOVERNED file -- compared
    # against trusted configuration, never against the caller's spelling, which may be
    # an alias. A mismatch is a corrupt or foreign receipt on the governed path.
    if not _same_file(Path(payload.get("active_path", "")), governed):
        _fail("promotion_receipt_invalid", f"{receipt_path} does not describe {governed}")

    expected = payload.get("after_projection_sha256")
    if not expected:
        _fail("promotion_receipt_invalid", f"{receipt_path} carries no after_projection_sha256")

    if not active_path.exists():
        _fail("promotion_state_invalid", f"{active_path} is absent while promotion evidence exists")
    try:
        current = projection_digest(active_path)
    except CfbdPromotionError as exc:
        _fail("promotion_state_invalid", f"cannot read the promoted projection: {exc.reason}")

    if current == expected:
        _fail(
            "promoted_projection_write_refused",
            f"{writer_name} would destroy the promoted CFBD projection in {active_path}; "
            "roll back the promotion first or repoint this producer",
        )
    _fail(
        "promoted_projection_drift",
        f"{writer_name} refused: promotion evidence exists but {active_path} no longer carries "
        "the promoted projection. Something already changed it -- reconcile before writing again.",
    )
