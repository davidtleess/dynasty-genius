"""Phase 16.2 PFF collegiate WR/RB export parser.

Normalizes private PFF manual exports into identity-joined feature rows
for Engine A college signal enrichment. Season year is injected from the
manifest — the CSV files carry no season column.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "pff_id": ("player_id", "pff_id", "id"),
    "player_name": ("player", "name", "player_name"),
    "college": ("team_name", "school", "college"),
    "position": ("position", "pos"),
    "routes": ("routes", "routes_run"),
    "yprr": ("yprr",),
    "yards": ("yards", "yds", "receiving_yards"),
    "targets": ("targets", "tgt"),
    "receptions": ("receptions", "rec"),
}

PROHIBITED_COLUMN_PATTERNS = (
    "grade",
    "pff_grade",
    "receiving_grade",
    "run_block_grade",
    "pass_block_grade",
    "route_grade",
)

_ELIGIBLE_POSITIONS = {"WR", "RB", "HB"}
_POSITION_NORMALIZE = {"HB": "RB"}


class PFFWRExportError(ValueError):
    """Raised when the export violates the Phase 16 parser contract."""


@dataclass(frozen=True)
class ParsedPFFWRSeason:
    """Safe parsed WR/RB rows from one PFF season export."""

    rows: list[dict[str, Any]]
    season: int
    row_count: int
    wr_rb_count: int
    content_hash: str
    prohibited_columns: list[str]
    required_missing: list[str]


def _norm_col(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")


def _find_alias(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    norm = {_norm_col(h): h for h in headers}
    for alias in aliases:
        if _norm_col(alias) in norm:
            return norm[_norm_col(alias)]
    return None


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


def _norm_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _sha256_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _check_prohibited(headers: list[str]) -> list[str]:
    found = []
    for h in headers:
        norm = _norm_col(h)
        if any(pattern in norm for pattern in PROHIBITED_COLUMN_PATTERNS):
            found.append(h)
    return sorted(found)


def parse_pff_wr_season(
    csv_path: str | Path,
    *,
    season: int,
) -> ParsedPFFWRSeason:
    """Parse one PFF receiving-summary export for WR/RB rows.

    Args:
        csv_path: Local path to the PFF CSV. Not committed; used read-only.
        season: College season year (injected from manifest, e.g. 2022).

    Raises:
        PFFWRExportError: If required columns are missing or prohibited grade
            columns are present.
    """
    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        raw_rows = list(reader)

    prohibited = _check_prohibited(headers)

    col_map: dict[str, str] = {}
    missing: list[str] = []
    for field_name, aliases in REQUIRED_COLUMN_ALIASES.items():
        found = _find_alias(headers, aliases)
        if found:
            col_map[field_name] = found
        else:
            missing.append(field_name)

    if missing:
        raise PFFWRExportError(
            f"missing required columns in PFF export: {missing}"
        )

    rows: list[dict[str, Any]] = []
    wr_rb_count = 0

    for raw in raw_rows:
        pos = (raw.get(col_map["position"]) or "").strip().upper()
        if pos not in _ELIGIBLE_POSITIONS:
            continue
        wr_rb_count += 1
        normalized_pos = _POSITION_NORMALIZE.get(pos, pos)

        pff_id = _norm_id(raw.get(col_map["pff_id"]))
        rows.append({
            "pff_id": pff_id,
            "player_name": (raw.get(col_map["player_name"]) or "").strip(),
            "college": (raw.get(col_map["college"]) or "").strip(),
            "position": normalized_pos,
            "season": season,
            "routes": _to_float(raw.get(col_map["routes"])),
            "yprr": _to_float(raw.get(col_map["yprr"])),
            "yards": _to_float(raw.get(col_map["yards"])),
            "targets": _to_float(raw.get(col_map["targets"])),
            "receptions": _to_float(raw.get(col_map["receptions"])),
        })

    return ParsedPFFWRSeason(
        rows=rows,
        season=season,
        row_count=len(raw_rows),
        wr_rb_count=wr_rb_count,
        content_hash=_sha256_short(path),
        prohibited_columns=prohibited,
        required_missing=missing,
    )
