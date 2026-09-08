"""Explicit local archive of the exact sources shown in the workspace. No implicit captures."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr

from app.api.routes.research_available import _catalog_for, _runs_root, _served_report
from src.dynasty_genius.capture.workspace_snapshot_sources import (
    WorkspaceSnapshotSourceError,
    load_workspace_snapshot,
)
from src.dynasty_genius.capture.workspace_snapshot_store import (
    WorkspaceSnapshotError,
    list_snapshots,
    read_snapshot,
    save_snapshot,
)

router = APIRouter(prefix="/research/snapshots")
SOURCE_KEYS = (
    "report_run",
    "report_sha256",
    "market_sha256",
    "league_sha256",
    "catalog_run",
    "catalog_content_sha256",
)
_save_lock = (
    Lock()
)  # Serializes the source-tuple check in this local single-process API.


class ExpectedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_run: StrictStr
    report_sha256: StrictStr
    market_sha256: StrictStr
    league_sha256: StrictStr
    catalog_run: StrictStr
    catalog_content_sha256: StrictStr


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected: ExpectedSource


def _root() -> Path | None:
    value = os.environ.get("DG_WORKSPACE_ARCHIVE_ROOT")
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        raise WorkspaceSnapshotError("An absolute archive path is required")
    return path


def _current_paths():
    manifest = os.environ.get("DG_MARKET_RANKS_MANIFEST")
    if not manifest or not Path(manifest).is_absolute():
        raise WorkspaceSnapshotSourceError("Ranking source is not configured")
    report_run, report_path, _ = _served_report(None)
    catalog_run, _ = _catalog_for(report_run, report_path, None)
    directory = _runs_root() / catalog_run / "dg178_available_catalog"
    return Path(manifest), directory / "catalog.json", directory / "report.json"


def _source(bundle):
    source = {**bundle.ranks["source"], **bundle.comparison["source"]}
    return {key: source[key] for key in SOURCE_KEYS}


def _now():
    return datetime.now(timezone.utc)


def _code_sha():
    root = Path(__file__).resolve().parents[3]
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=root,
            text=True,
        )
        if status.strip():
            return "unknown"
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except OSError, subprocess.SubprocessError:
        return "unknown"


def _unavailable():
    return HTTPException(
        status_code=503,
        detail="Saved snapshots are unavailable because their sources or archive could not be verified. No older snapshot was substituted.",
    )


@router.get("")
def snapshots():
    try:
        root = _root()
        return (
            {"status": "not_configured"}
            if root is None
            else {"status": "available", "snapshots": list_snapshots(root)}
        )
    except OSError, ValueError:
        raise _unavailable() from None


@router.post("")
def capture(request: SaveRequest):
    try:
        root = _root()
        if root is None:
            raise HTTPException(
                status_code=503,
                detail="Saving snapshots is not enabled in this workspace.",
            )
        with _save_lock:
            try:
                bundle = load_workspace_snapshot(*_current_paths())
            except HTTPException:
                raise _unavailable() from None
            if _source(bundle) != request.expected.model_dump():
                raise HTTPException(
                    status_code=409,
                    detail="The sources have changed since this screen loaded. Reload before saving.",
                )
            # First save fixes the reading AND evaluation plan for these forecast sources.
            # A prose or plan edit must not silently fork an independent observation.
            existing = [
                s for s in list_snapshots(root) if s["source"] == _source(bundle)
            ]
            if existing:
                first = min(
                    existing, key=lambda s: datetime.fromisoformat(s["saved_at"])
                )
                return {"status": "saved", "created": False, "snapshot": first}
            return {
                "status": "saved",
                **save_snapshot(root, bundle, captured_at=_now(), code_sha=_code_sha()),
            }
    except OSError, ValueError, KeyError, TypeError:
        raise _unavailable() from None


@router.get("/{snapshot_id}")
def snapshot(snapshot_id: str):
    try:
        root = _root()
        if root is None:
            raise HTTPException(
                status_code=503,
                detail="Saved snapshots are not enabled in this workspace.",
            )
        return read_snapshot(root, snapshot_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="This saved snapshot was not found."
        ) from None
    except OSError, ValueError:
        raise _unavailable() from None
