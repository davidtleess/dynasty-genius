#!/usr/bin/env python3
"""Build the Phase 13.3.1 TE archetype rubric artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_pff_te_export_report import (  # noqa: E402
    _load_eligible_rows,
    _load_manifest,
    _merge_cohort_draft_years,
)
from src.dynasty_genius.adapters.pff_te_export import parse_pff_te_export  # noqa: E402
from src.dynasty_genius.audit.te_archetype_rubric import (  # noqa: E402
    DEFAULT_RECEIVING_THRESHOLD,
    RUBRIC_VERSION,
    SENSITIVITY_RECEIVING_THRESHOLD,
    TEArchetypeInput,
    classify_te_archetype,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_id(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _source_row_hash(pff_id: str | None, season: int | None, content_hash: str | None) -> str | None:
    if not pff_id or season is None or not content_hash:
        return None
    return hashlib.sha256(f"{pff_id}|{season}|{content_hash}".encode("utf-8")).hexdigest()[:12]


def _content_hash_by_source_label(file_summaries: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["source_label"]): str(row["content_hash"])
        for row in file_summaries
        if row.get("source_label") and row.get("content_hash")
    }


def _select_final_season(rows: list[dict[str, Any]], draft_year: int) -> dict[str, Any] | None:
    by_season: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row.get("season") is None:
            continue
        season = int(row["season"])
        if season in by_season:
            player_id = row.get("player_id")
            raise ValueError(f"duplicate PFF TE rows for player_id={player_id} season={season}")
        by_season[season] = row

    for season in (draft_year - 1, draft_year - 2):
        if season in by_season:
            return by_season[season]
    return None


def _excluded_row(player_id: str, draft_year: int | None) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "draft_year": draft_year,
        "selected_season": None,
        "coverage_status": "pff_alignment_missing",
        "labeling_status": "excluded",
        "archetype": None,
        "source_row_hash": None,
        "alignment_snap_total": None,
        "detached_rate_from_snaps": None,
        "inline_rate_from_snaps": None,
        "routes": None,
        "targets": None,
        "receptions": None,
        "yards": None,
        "yprr_computed": None,
        "tprr_computed": None,
        "elite_efficiency_prior": False,
        "near_volume_threshold": False,
        "alignment_source": None,
        "threshold_basis": None,
    }


def _sensitivity_counts(players: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {
        "receiving_leaning": 0,
        "blocking_leaning": 0,
        "ambiguous": 0,
        "low_volume": 0,
        "invalid_alignment": 0,
        "excluded": 0,
    }
    for row in players.values():
        status = row["labeling_status"]
        if status != "labeled":
            counts[status] += 1
        else:
            counts[row["archetype"]] += 1
    return counts


def build_te_archetype_artifact(
    parsed_rows: list[dict[str, Any]],
    *,
    eligible_rows: list[dict[str, Any]],
    file_summaries: list[dict[str, Any]],
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the committed redacted Step 0 artifact from parsed PFF rows."""

    generated_at = generated_at or _utc_timestamp()
    content_hash_by_source = _content_hash_by_source_label(file_summaries)
    by_player: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        by_player.setdefault(str(row["player_id"]), []).append(row)

    players_040: dict[str, dict[str, Any]] = {}
    players_045: dict[str, dict[str, Any]] = {}
    missing_by_draft_year: dict[str, int] = {}

    for eligible in sorted(eligible_rows, key=lambda r: str(r.get("player_id") or "")):
        player_id = str(eligible["player_id"])
        draft_year = int(eligible["draft_year"]) if eligible.get("draft_year") is not None else None
        selected = _select_final_season(by_player.get(player_id, []), draft_year) if draft_year else None
        if selected is None:
            players_040[player_id] = _excluded_row(player_id, draft_year)
            players_045[player_id] = _excluded_row(player_id, draft_year)
            missing_by_draft_year[str(draft_year)] = missing_by_draft_year.get(str(draft_year), 0) + 1
            continue

        source_hash = _source_row_hash(
            _norm_id(selected.get("pff_id")),
            int(selected["season"]),
            content_hash_by_source.get(str(selected.get("source_label"))),
        )
        input_row = TEArchetypeInput(
            player_id=player_id,
            draft_year=draft_year,
            selected_season=int(selected["season"]),
            source_row_hash=source_hash,
            inline_snaps=selected.get("inline_snaps"),
            slot_snaps=selected.get("slot_snaps"),
            wide_snaps=selected.get("wide_snaps"),
            routes=selected.get("routes"),
            targets=selected.get("targets"),
            receptions=selected.get("receptions"),
            yards=selected.get("yards"),
        )
        players_040[player_id] = classify_te_archetype(
            input_row,
            receiving_threshold=DEFAULT_RECEIVING_THRESHOLD,
        )
        players_045[player_id] = classify_te_archetype(
            input_row,
            receiving_threshold=SENSITIVITY_RECEIVING_THRESHOLD,
        )

    moved = sum(
        1
        for player_id, row in players_040.items()
        if row.get("archetype") == "receiving_leaning"
        and players_045[player_id].get("archetype") == "ambiguous"
    )
    yprr_values = sorted(
        row["yprr_computed"]
        for row in players_040.values()
        if row.get("yprr_computed") is not None and row.get("labeling_status") == "labeled"
    )
    yprr_p75 = None
    if yprr_values:
        yprr_p75 = yprr_values[int((len(yprr_values) - 1) * 0.75)]

    coverage_count = sum(
        1 for row in players_040.values() if row["coverage_status"] == "pff_alignment_available"
    )
    return {
        "metadata": {
            "run_id": run_id,
            "rubric_version": RUBRIC_VERSION,
            "generated_at": generated_at,
            "eligible_count": len(eligible_rows),
            "coverage_count": coverage_count,
            "missing_count": len(eligible_rows) - coverage_count,
            "alignment_source": "snaps_fallback",
            "threshold_basis": "snap_counts",
            "cohort_yprr_p75": yprr_p75,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
        },
        "players": players_040,
        "sensitivity": {
            "receiving_threshold_0_40": _sensitivity_counts(players_040),
            "receiving_threshold_0_45": _sensitivity_counts(players_045),
            "moved_from_receiving_to_ambiguous": moved,
        },
        "coverage_gap": {
            "missing_by_draft_year": dict(sorted(missing_by_draft_year.items())),
            "likely_missing_reason": "PFF collegiate coverage limitation, commonly FCS or small-school gaps.",
            "policy": "Missing PFF alignment rows are excluded from archetype assignment; do not impute or fuzzy-fill.",
        },
    }


def _parse_private_exports(
    manifest_path: Path,
    eligible_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = _load_manifest(manifest_path)
    by_pff = {
        str(row["pff_id"]): row
        for row in eligible_rows
        if row.get("pff_id") and row.get("player_id")
    }
    parsed_rows: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    for entry in entries:
        parsed = parse_pff_te_export(
            entry.path,
            season=entry.season,
            eligible_by_pff_id=by_pff,
            source_label=entry.label,
        )
        parsed_rows.extend(parsed.rows)
        file_summaries.append(parsed.file_summary)
    return parsed_rows, file_summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 13.3.1 TE archetype rubric artifact.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_archetype_20260516")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    eligible_rows = _merge_cohort_draft_years(
        _load_eligible_rows(args.eligible_manifest),
        args.cohort,
    )
    parsed_rows, file_summaries = _parse_private_exports(args.manifest, eligible_rows)
    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id=args.run_id,
        generated_at=args.generated_at,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata = artifact["metadata"]
    print(
        f"TE archetype rubric written: {args.out} "
        f"coverage={metadata['coverage_count']}/{metadata['eligible_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
