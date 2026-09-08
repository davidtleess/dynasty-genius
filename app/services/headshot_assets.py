"""Read-only headshot serving from a configured collection or the existing local cache."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


class HeadshotCacheConfigurationError(ValueError):
    """An explicitly selected photo collection is not available."""


def mount_headshots(app: FastAPI, *, repo_root: Path) -> None:
    """Mount before the frontend assets. No download, cache creation or fallback writes."""
    configured = os.environ.get("DG_HEADSHOT_CACHE_ROOT")
    if configured:
        root = Path(configured)
        if not root.is_absolute() or not root.is_dir():
            raise HeadshotCacheConfigurationError(
                "DG_HEADSHOT_CACHE_ROOT must name an existing absolute headshot directory"
            )
    else:
        root = repo_root / "app/data/assets/headshots"
        if not root.is_dir():
            return
    app.mount(
        "/assets/headshots",
        StaticFiles(directory=root, follow_symlink=False),
        name="headshot-assets",
    )
