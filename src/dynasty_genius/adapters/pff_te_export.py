"""Phase 13 PFF collegiate TE export parser.

This module is intentionally Step 0 only. It normalizes private PFF manual
exports into redacted coverage reports and context-signal rows; it does not
create model features or training materialization.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "pff_id": ("player_id", "pff_id", "id"),
    "player_name": ("player", "name", "player_name"),
    "college": ("team_name", "school", "college"),
    "position": ("position", "pos"),
    "routes": ("routes", "routes_run"),
    "inline": ("inline_routes", "inline_snaps"),
    "slot": ("slot_routes", "slot_snaps"),
    "wide": ("wide_routes", "wide_snaps"),
    "targets": ("targets", "tgt"),
    "receptions": ("receptions", "rec"),
    "yards": ("yards", "yds"),
}

OPTIONAL_CONTEXT_ALIASES: dict[str, tuple[str, ...]] = {
    "yprr": ("yprr",),
    "contested_catch_rate": ("contested_catch_rate",),
    "drop_rate": ("drop_rate",),
    "yards_after_catch_per_reception": (
        "yards_after_catch_per_reception",
        "yac_per_reception",
    ),
}

PROHIBITED_COLUMN_PATTERNS = (
    "grade",
    "pff_grade",
    "receiving_grade",
    "run_block_grade",
    "pass_block_grade",
    "route_grade",
)


@dataclass(frozen=True)
class PFFExportManifestEntry:
    """A local manual export plus its external season provenance."""

    path: Path
    season: int
    label: str
    source: str = "pff_premium_stats"
    pff_data_version: str | None = None
    export_timestamp: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class PFFExportSchemaReport:
    """Schema decision for one PFF export."""

    required_present: dict[str, str]
    required_missing: list[str]
    optional_present: dict[str, str]
    prohibited_columns: list[str]
    alignment_source: str


@dataclass(frozen=True)
class ParsedPFFTEExport:
    """Safe parsed rows and redacted file-level metadata."""

    rows: list[dict[str, Any]]
    schema_report: PFFExportSchemaReport
    file_summary: dict[str, Any]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_column(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")


def _norm_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _present_aliases(headers: list[str], aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    normalized = {_norm_column(header): header for header in headers}
    present: dict[str, str] = {}
    for field, options in aliases.items():
        for option in options:
            if _norm_column(option) in normalized:
                present[field] = normalized[_norm_column(option)]
                break
    return present


def _prohibited_columns(headers: list[str]) -> list[str]:
    prohibited: list[str] = []
    for header in headers:
        normalized = _norm_column(header)
        if any(pattern in normalized for pattern in PROHIBITED_COLUMN_PATTERNS):
            prohibited.append(header)
    return sorted(prohibited)


def _alignment_source(present: dict[str, str]) -> str:
    alignment_columns = [present.get("inline"), present.get("slot"), present.get("wide")]
    if all(column and column.endswith("_routes") for column in alignment_columns):
        return "routes"
    if all(column and column.endswith("_snaps") for column in alignment_columns):
        return "snaps_fallback"
    return "mixed_or_unknown"


def _schema_report(headers: list[str]) -> PFFExportSchemaReport:
    required_present = _present_aliases(headers, REQUIRED_COLUMN_ALIASES)
    optional_present = _present_aliases(headers, OPTIONAL_CONTEXT_ALIASES)
    missing = [
        field
        for field in REQUIRED_COLUMN_ALIASES
        if field not in required_present
    ]
    return PFFExportSchemaReport(
        required_present=required_present,
        required_missing=missing,
        optional_present=optional_present,
        prohibited_columns=_prohibited_columns(headers),
        alignment_source=_alignment_source(required_present),
    )


def _sha256_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _header_hash(headers: list[str]) -> str:
    return hashlib.sha256("\n".join(headers).encode("utf-8")).hexdigest()[:12]


def _read_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _eligible_by_pff_id(eligible_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    for row in eligible_rows:
        pff_id = _norm_id(row.get("pff_id"))
        player_id = row.get("player_id")
        if not pff_id:
            continue
        if not player_id:
            unresolved.append(pff_id)
            continue
        indexed[pff_id] = row
    if unresolved:
        raise ValueError(
            "PFF TE export summary requires canonical player_id for every eligible row; "
            f"unresolved pff_ids={sorted(unresolved)}"
        )
    return indexed


def parse_pff_te_export(
    csv_path: str | Path,
    *,
    season: int,
    eligible_by_pff_id: dict[str, dict[str, Any]],
    source_label: str,
) -> ParsedPFFTEExport:
    """Parse one PFF receiving-summary export into safe Step 0 TE rows."""

    path = Path(csv_path)
    headers, raw_rows = _read_rows(path)
    schema_report = _schema_report(headers)
    present = schema_report.required_present

    matched_rows: list[dict[str, Any]] = []
    te_ids: set[str] = set()
    matched_ids: set[str] = set()

    for raw in raw_rows:
        position_col = present.get("position")
        if position_col and (raw.get(position_col) or "").strip() != "TE":
            continue

        pff_col = present.get("pff_id")
        pff_id = _norm_id(raw.get(pff_col)) if pff_col else None
        if pff_id:
            te_ids.add(pff_id)
        eligible = eligible_by_pff_id.get(pff_id or "")
        if not pff_id or not eligible:
            continue

        context_signals = {
            field: _to_float(raw.get(column))
            for field, column in schema_report.optional_present.items()
            if _to_float(raw.get(column)) is not None
        }
        matched_rows.append(
            {
                "player_id": eligible["player_id"],
                "pff_id": pff_id,
                "draft_year": eligible.get("draft_year"),
                "season": season,
                "source": "pff",
                "source_label": source_label,
                "college": raw.get(present["college"]),
                "routes": _to_float(raw.get(present["routes"])),
                "inline_snaps": _to_float(raw.get(present["inline"])),
                "slot_snaps": _to_float(raw.get(present["slot"])),
                "wide_snaps": _to_float(raw.get(present["wide"])),
                "targets": _to_float(raw.get(present["targets"])),
                "receptions": _to_float(raw.get(present["receptions"])),
                "yards": _to_float(raw.get(present["yards"])),
                "alignment_source": schema_report.alignment_source,
                "context_signals": context_signals,
            }
        )
        matched_ids.add(pff_id)

    file_summary = {
        "file_name": path.name,
        "source_label": source_label,
        "season": season,
        "row_count": len(raw_rows),
        "te_rows": sum(
            1 for raw in raw_rows
            if present.get("position") and (raw.get(present["position"]) or "").strip() == "TE"
        ),
        "unique_te_ids": len(te_ids),
        "matched_drafted_te_ids": len(matched_ids),
        "unmatched_te_ids": len(te_ids - matched_ids),
        "header_hash": _header_hash(headers),
        "content_hash": _sha256_short(path),
        "alignment_source": schema_report.alignment_source,
        "prohibited_columns": schema_report.prohibited_columns,
        "required_missing": schema_report.required_missing,
    }
    return ParsedPFFTEExport(
        rows=matched_rows,
        schema_report=schema_report,
        file_summary=file_summary,
    )


def summarize_pff_te_exports(
    manifest_entries: list[PFFExportManifestEntry],
    *,
    eligible_rows: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Summarize local PFF TE exports without player names or raw local paths."""

    generated_at = generated_at or _utc_timestamp()
    eligible = _eligible_by_pff_id(eligible_rows)
    parsed = [
        parse_pff_te_export(
            entry.path,
            season=entry.season,
            eligible_by_pff_id=eligible,
            source_label=entry.label,
        )
        for entry in manifest_entries
    ]

    matched_ids = {
        row["pff_id"]
        for export in parsed
        for row in export.rows
    }
    eligible_ids = set(eligible)
    missing_ids = eligible_ids - matched_ids

    missing_by_draft_year: dict[str, int] = {}
    for pff_id in missing_ids:
        draft_year = str(eligible[pff_id].get("draft_year"))
        missing_by_draft_year[draft_year] = missing_by_draft_year.get(draft_year, 0) + 1

    file_summaries = [export.file_summary for export in parsed]
    content_groups: dict[str, list[str]] = {}
    for file_summary in file_summaries:
        content_groups.setdefault(file_summary["content_hash"], []).append(file_summary["source_label"])

    return {
        "generated_at": generated_at,
        "source": "pff_premium_stats_manual_csv",
        "scope": "Phase 13.3 Step 0 schema and drafted-TE coverage report",
        "summary": {
            "eligible_count": len(eligible_ids),
            "file_count": len(file_summaries),
            "unique_matched_drafted_te_ids": len(matched_ids),
            "missing_drafted_te_ids": len(missing_ids),
            "raw_rows_materialized": 0,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
        },
        "coverage_caveat": {
            "status": "partial_pff_coverage" if missing_ids else "complete_pff_coverage",
            "matched_drafted_te_ids": len(matched_ids),
            "eligible_count": len(eligible_ids),
            "missing_drafted_te_ids": len(missing_ids),
            "likely_missing_reason": "PFF collegiate coverage limitation, commonly FCS or small-school gaps.",
            "archetype_labeling_policy": (
                "Missing PFF alignment rows are excluded from archetype assignment; "
                "do not impute or fuzzy-fill."
            ),
            "model_materialization_policy": (
                "PFF fields remain context_signal only and cannot enter Engine A/B "
                "training materialization in Phase 13."
            ),
        },
        "files": file_summaries,
        "content_groups": content_groups,
        "missing_by_draft_year": dict(sorted(missing_by_draft_year.items())),
        "notes": [
            "Raw PFF CSV rows remain private and uncommitted.",
            "Report intentionally excludes player names and local absolute paths.",
            "PFF fields remain context_signal only; no Engine A/B training materialization.",
        ],
    }
