#!/usr/bin/env python3
"""Build a redacted Phase 13 PFF TE export coverage report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.pff_te_export import (  # noqa: E402
    PFFExportManifestEntry,
    summarize_pff_te_exports,
)


def _load_manifest(path: Path) -> list[PFFExportManifestEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    exports = data.get("exports", [])
    entries: list[PFFExportManifestEntry] = []
    for item in exports:
        entries.append(
            PFFExportManifestEntry(
                path=Path(item["path"]),
                season=int(item["season"]),
                label=str(item["label"]),
                source=item.get("source", "pff_premium_stats"),
                pff_data_version=item.get("pff_data_version"),
                export_timestamp=item.get("export_timestamp"),
                notes=item.get("notes"),
            )
        )
    return entries


def _load_eligible_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("eligible")
    if not isinstance(rows, list):
        raise ValueError(f"eligible manifest must contain an 'eligible' list: {path}")
    return rows


def _load_cohort_draft_years(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    return {
        str(row["pff_id"]): int(row["draft_year"])
        for row in entries
        if row.get("pff_id") and row.get("draft_year")
    }


def _merge_cohort_draft_years(
    eligible_rows: list[dict[str, Any]],
    cohort_path: Path | None,
) -> list[dict[str, Any]]:
    if cohort_path is None:
        return eligible_rows

    draft_year_by_pff_id = _load_cohort_draft_years(cohort_path)
    merged: list[dict[str, Any]] = []
    for row in eligible_rows:
        copy = dict(row)
        pff_id = str(copy.get("pff_id") or "")
        if copy.get("draft_year") is None and pff_id in draft_year_by_pff_id:
            copy["draft_year"] = draft_year_by_pff_id[pff_id]
        merged.append(copy)
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    eligible_rows = _merge_cohort_draft_years(
        _load_eligible_rows(args.eligible_manifest),
        args.cohort,
    )
    report = summarize_pff_te_exports(
        _load_manifest(args.manifest),
        eligible_rows=eligible_rows,
        generated_at=args.generated_at,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(
        "PFF TE export report written: "
        f"{args.out} "
        f"matched={summary['unique_matched_drafted_te_ids']}/{summary['eligible_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
