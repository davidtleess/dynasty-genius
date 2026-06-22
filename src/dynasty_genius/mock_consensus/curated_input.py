"""Curated manual-mock input loader + read-only S3 adapter (Subsystem 1, spec v4 §3/§3b/§4).

Two-stage fail-closed validation of the version-controlled curated-JSON payload:
structural schema gate -> per-row semantic validation. Invalid rows are NEVER
silently dropped: each is recorded as a :class:`DroppedRow` with an explicit reason.

The adapter builds an in-memory :class:`NormalizedCollegeProspectRow` for the S3
identity resolver. It is strictly READ-ONLY: it constructs a typed row and writes
NO registry or bridge state.

Import isolation (spec v4 U2): this module imports only the S3 identity substrate;
it must never import Engine A/B, scoring, or ``backtest_mock_draft``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from src.dynasty_genius.identity.college_prospect_identity import (
    IdProvenance,
    NormalizedCollegeProspectRow,
    normalize_name,
)

# Shared draft-pick maximum (mirrors the S4 value; defined locally because U2 bars
# importing ``backtest_mock_draft`` into ``mock_consensus``).
DRAFT_PICK_MAX = 257

_SCHEMA_VERSION = "s1_curated_mock_consensus_v1"
_MAX_ROUND = 7

# Required non-empty string fields that the adapter / row builder index directly.
# Validated up front so a malformed row is dropped with a reason, never a KeyError.
_REQUIRED_STRING_FIELDS = (
    "source_id",
    "source_snapshot_id",
    "raw_row_hash",
    "prospect_name_raw",
    "position_raw",
    "school_raw",
)

# U3: a curator-canonical analyst string starts with a letter and contains only
# letters, spaces, periods, apostrophes, and hyphens (no underscores/digits).
_CANONICAL_ANALYST_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")


class CuratedInputSchemaError(ValueError):
    """Raised when the curated payload fails the structural schema gate."""


@dataclass(frozen=True)
class CuratedMockRow:
    """A single curated mock-draft row that passed semantic validation."""

    source_id: str
    source_name: str
    analyst: str
    mock_version: str
    published_date: str
    source_snapshot_id: str
    raw_row_hash: str
    parse_status: str
    source_type: str
    prospect_name_raw: str
    position_raw: str
    school_raw: str
    draft_class: int
    projected_pick: int | None
    projected_round: int | None
    nfl_team: str | None
    projection_status: str
    source_rank: int | None


@dataclass(frozen=True)
class DroppedRow:
    """A curated row that failed validation, with an explicit drop reason."""

    raw_row_hash: str
    reason: str


@dataclass(frozen=True)
class CuratedInputResult:
    """Outcome of loading a curated payload: kept rows + dropped rows w/ reasons."""

    rows: list[CuratedMockRow] = field(default_factory=list)
    dropped_rows: list[DroppedRow] = field(default_factory=list)


def _semantic_reason(raw: dict) -> str | None:
    """Return a drop reason for ``raw`` or ``None`` if the row is valid."""
    for required in _REQUIRED_STRING_FIELDS:
        value = raw.get(required)
        if not isinstance(value, str) or not value.strip():
            return f"missing or blank required field {required!r}"

    draft_class = raw.get("draft_class")
    if not isinstance(draft_class, int) or isinstance(draft_class, bool):
        return f"missing or non-integer draft_class (got {draft_class!r})"

    analyst = raw.get("analyst")
    if not isinstance(analyst, str) or not analyst.strip():
        return "blank analyst (U3: curator-canonical analyst string required)"
    if not _CANONICAL_ANALYST_RE.match(analyst.strip()):
        return f"malformed analyst (U3: non-canonical analyst string {analyst!r})"

    source_type = raw.get("source_type")
    if source_type == "big_board":
        return "big_board rows excluded (talent ranking, not a landing-spot mock)"
    if source_type != "mock":
        return f"source_type {source_type!r} excluded (not 'mock')"

    status = raw.get("projection_status")
    pick = raw.get("projected_pick")
    rnd = raw.get("projected_round")
    if status == "exact_pick":
        if not isinstance(pick, int) or isinstance(pick, bool) or not (
            1 <= pick <= DRAFT_PICK_MAX
        ):
            return (
                f"exact_pick requires projected_pick in [1, {DRAFT_PICK_MAX}], "
                f"got {pick!r}"
            )
    elif status == "round_only":
        if not isinstance(rnd, int) or isinstance(rnd, bool) or not (
            1 <= rnd <= _MAX_ROUND
        ):
            return (
                f"round_only requires projected_round in [1, {_MAX_ROUND}], "
                f"got {rnd!r}"
            )
    elif status == "udfa":
        if pick is not None:
            return f"udfa must not carry a projected_pick (got {pick!r})"
    else:
        return f"invalid projection_status {status!r}"

    published_date = raw.get("published_date")
    try:
        date.fromisoformat(published_date)
    except (ValueError, TypeError):
        return (
            f"malformed published_date {published_date!r} "
            "(expected ISO YYYY-MM-DD)"
        )

    return None


def _build_curated_row(raw: dict) -> CuratedMockRow:
    return CuratedMockRow(
        source_id=raw["source_id"],
        source_name=raw.get("source_name", ""),
        analyst=raw["analyst"],
        mock_version=raw.get("mock_version", ""),
        published_date=raw["published_date"],
        source_snapshot_id=raw["source_snapshot_id"],
        raw_row_hash=raw["raw_row_hash"],
        parse_status=raw.get("parse_status", ""),
        source_type=raw["source_type"],
        prospect_name_raw=raw["prospect_name_raw"],
        position_raw=raw["position_raw"],
        school_raw=raw["school_raw"],
        draft_class=raw["draft_class"],
        projected_pick=raw.get("projected_pick"),
        projected_round=raw.get("projected_round"),
        nfl_team=raw.get("nfl_team"),
        projection_status=raw["projection_status"],
        source_rank=raw.get("source_rank"),
    )


def load_curated_json_payload(payload: object) -> CuratedInputResult:
    """Validate a curated payload through the structural + semantic gates.

    Raises :class:`CuratedInputSchemaError` for structural failures (whole-payload
    fail-closed). Per-row semantic failures are recorded as dropped rows, never
    silently discarded.
    """
    if not isinstance(payload, dict):
        raise CuratedInputSchemaError("payload must be a JSON object (dict)")
    if "schema_version" not in payload:
        raise CuratedInputSchemaError("missing 'schema_version'")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise CuratedInputSchemaError("'rows' must be a list")

    seen_hashes: set[str] = set()
    kept: list[CuratedMockRow] = []
    dropped: list[DroppedRow] = []

    for raw in rows:
        if not isinstance(raw, dict):
            dropped.append(
                DroppedRow(raw_row_hash="", reason="malformed row (not an object)")
            )
            continue
        raw_row_hash = raw.get("raw_row_hash", "")
        reason = _semantic_reason(raw)
        if reason is not None:
            dropped.append(DroppedRow(raw_row_hash=raw_row_hash, reason=reason))
            continue
        if raw_row_hash in seen_hashes:
            dropped.append(
                DroppedRow(
                    raw_row_hash=raw_row_hash, reason="duplicate raw_row_hash"
                )
            )
            continue
        seen_hashes.add(raw_row_hash)
        kept.append(_build_curated_row(raw))

    return CuratedInputResult(rows=kept, dropped_rows=dropped)


def adapt_curated_row_to_s3(curated: CuratedMockRow) -> NormalizedCollegeProspectRow:
    """Build a read-only :class:`NormalizedCollegeProspectRow` from a curated row.

    Strictly read-only: constructs an in-memory typed row and writes no registry
    or bridge state. Synthesizes S3 provenance from the curated source fields.
    """
    return NormalizedCollegeProspectRow(
        raw_name=curated.prospect_name_raw,
        normalized_name=normalize_name(curated.prospect_name_raw),
        full_name=curated.prospect_name_raw,
        position=curated.position_raw,
        position_group=curated.position_raw,
        draft_class=curated.draft_class,
        current_school=curated.school_raw,
        source=f"s1_mock_consensus:{curated.source_id}",
        source_record_id=f"{curated.source_id}:{curated.raw_row_hash}",
        source_snapshot_id=curated.source_snapshot_id,
        id_provenance=IdProvenance(),
    )
