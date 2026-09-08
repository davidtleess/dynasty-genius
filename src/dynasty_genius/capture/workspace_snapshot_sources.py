"""Read and validate one complete workspace snapshot, hashing the exact buffers archived."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.dynasty_genius.ranking.market_ranks import SourceError, build_market_ranks
from src.dynasty_genius.ranking.roster_comparison import (
    ComparisonSourceError,
    build_comparison,
)

if TYPE_CHECKING:
    from src.dynasty_genius.capture.workspace_snapshot_store import SnapshotBundle


class WorkspaceSnapshotSourceError(ValueError):
    """The selected sources cannot establish a coherent saved workspace."""


def _require(condition, message):
    if not condition:
        raise WorkspaceSnapshotSourceError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise WorkspaceSnapshotSourceError("Non-finite JSON number")


def _parse(raw):
    return json.loads(raw, object_pairs_hook=_object, parse_constant=_invalid_constant)


def load_workspace_snapshot(
    manifest_path: Path, catalog_path: Path, companion_path: Path
) -> SnapshotBundle:
    """Read each source once. Never execute a model, rewrite inputs, or use fallback scores."""
    try:
        artifacts = {"source-manifest.json": Path(manifest_path).read_bytes()}
        plan_path = (
            Path(__file__).resolve().parents[3]
            / "app/config/workspace_evaluation_plan.json"
        )
        artifacts["evaluation-plan.json"] = plan_path.read_bytes()
        evaluation_plan = _parse(artifacts["evaluation-plan.json"])
        _require(
            isinstance(evaluation_plan, dict)
            and type(evaluation_plan.get("schema_version")) is int
            and evaluation_plan.get("schema_version") == 1
            and bool(evaluation_plan.get("plan_id")),
            "Evaluation declaration missing or invalid",
        )
        manifest = _parse(artifacts["source-manifest.json"])
        _require(
            type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
            "Unsupported source manifest",
        )
        docs, hashes = {}, {}
        for key in ("report", "market", "league"):
            spec = manifest["files"][key]
            path = Path(spec["path"])
            _require(path.is_absolute(), "Source path must be absolute")
            raw = path.read_bytes()
            _require(
                isinstance(spec["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]),
                "Invalid declared source hash",
            )
            _require(_sha(raw) == spec["sha256"], f"{key} source bytes differ")
            artifacts[key + ".json"] = raw
            docs[key], hashes[key] = _parse(raw), _sha(raw)
        report_run = manifest["report_run"]
        _require(isinstance(report_run, str) and bool(report_run), "Report run missing")
        _require(docs["report"]["run"] == report_run, "Report run differs")
        _require(
            docs["report"]["inputs"]["snapshot"]["sha256"] == hashes["league"],
            "Report-bound league differs",
        )
        artifacts["catalog.json"] = Path(catalog_path).read_bytes()
        artifacts["catalog-companion.json"] = Path(companion_path).read_bytes()
        catalog = _parse(artifacts["catalog.json"])
        companion = _parse(artifacts["catalog-companion.json"])
        catalog_run = catalog["run"]
        _require(
            isinstance(catalog_run, str) and bool(catalog_run), "Catalog run missing"
        )
        _require(companion["run"] == catalog_run, "Catalog run differs from companion")
        _require(
            companion["source_report_run"]
            == catalog["source_report_run"]
            == report_run,
            "Catalog report binding differs",
        )
        _require(
            companion["outputs_sha256"]["catalog.json"]
            == _sha(artifacts["catalog.json"]),
            "Catalog bytes differ from companion",
        )
        ranks = build_market_ranks(docs["report"], docs["market"], docs["league"])
        ranks["source"].update(
            {f"{key}_sha256": value for key, value in hashes.items()}
        )
        comparison = build_comparison(
            artifacts["report.json"],
            catalog,
            report_run=report_run,
            catalog_run=catalog_run,
        )
        _require(
            comparison["source"]["ownership_as_of"]
            == ranks["source"]["ownership_as_of"],
            "Ownership dates differ",
        )
        _require(
            comparison["forecast_years"] == ranks["basis"]["years"]
            and comparison["future_years"] == ranks["basis"]["years"][1:],
            "Forecast years differ",
        )
        rank_rows = {row["sleeper_id"]: row for row in ranks["rows"]}
        _require(
            {row["sleeper_id"] for row in comparison["roster"]}
            == {sid for sid, row in rank_rows.items() if row["on_roster"]},
            "Roster membership differs",
        )
        for row in comparison["roster"] + comparison["available"]:
            other = rank_rows.get(row["sleeper_id"])
            _require(
                other is None or row["position"] == other["position"],
                "Player positions differ",
            )
        from src.dynasty_genius.capture.workspace_snapshot_store import SnapshotBundle

        return SnapshotBundle(artifacts=artifacts, ranks=ranks, comparison=comparison)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        if isinstance(exc, WorkspaceSnapshotSourceError):
            raise
        if isinstance(exc, (SourceError, ComparisonSourceError)):
            raise WorkspaceSnapshotSourceError(str(exc)) from exc
        raise WorkspaceSnapshotSourceError(
            "Workspace source files are incomplete or invalid"
        ) from exc
