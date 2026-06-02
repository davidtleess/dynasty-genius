"""Freeze the raw 2025 prospect source inputs for S3 Task 10A (spec §6).

Read-only capture of the layered source stack into an immutable, content-hashed
snapshot under ``<output_root>/_frozen_2025/`` so every registry row is later
regenerable from a pinned, provenance-cited input set:

- CFBD ``/roster?year=2025`` (college-identity substrate; all-team pull, with a
  per-team fallback when the all-team response is empty),
- ``nflreadpy.load_draft_picks(2025)`` (drafted-cohort truth pin),
- ``load_ff_playerids()`` (DynastyProcess ID-crosswalk pin — IDs only),
- the named UDFA-tracker source manifest.

All external sources are **injected** (``cfbd_client`` / ``draft_picks_loader`` /
``ff_playerids_loader`` / ``udfa_sources``) and the ``retrieval_timestamp`` is
passed in — so the core is deterministic and testable with no live network/key.

The real T3 pull (David-gated, needs ``CFBD_API_KEY``) wires the live ``cfbd``
client + ``nflreadpy`` loaders into ``freeze_2025_prospect_sources`` against the
live CFBD OpenAPI confirmed at pull time (not assumed here).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


def compute_canonical_json_sha256(payload: Any) -> str:
    """SHA-256 over canonicalized JSON (sorted keys, compact separators)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _snapshot_id(
    *, retrieval_timestamp: str, endpoint: str, api_version: str, payload: Any, row_count: int
) -> dict:
    return {
        "retrieval_timestamp": retrieval_timestamp,
        "endpoint": endpoint,
        "api_version": api_version,
        "sha256": compute_canonical_json_sha256(payload),
        "row_count": row_count,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def freeze_2025_prospect_sources(
    *,
    output_root: Path,
    year: int,
    retrieval_timestamp: str,
    cfbd_client: Any,
    draft_picks_loader: Callable[[int], Any],
    ff_playerids_loader: Callable[[], Any],
    udfa_sources: list[dict],
) -> dict:
    """Freeze the four raw inputs + a hashed manifest under ``_frozen_2025/``.

    Returns the manifest (also written to ``manifest.json``). Writes ONLY under
    ``<output_root>/_frozen_2025/``; performs no live network calls itself.
    """
    # CFBD roster: all-team pull, with a per-team fallback when all-team is empty.
    roster_rows = list(cfbd_client.get_roster(year=year, team=None))
    if roster_rows:
        cfbd_endpoint = f"/roster?year={year}"
    else:
        roster_rows = []
        for team in sorted(cfbd_client.list_teams(year=year)):
            roster_rows.extend(cfbd_client.get_roster(year=year, team=team))
        cfbd_endpoint = f"/roster?year={year}&team=*"

    draft_payload = draft_picks_loader(year)
    ff_payload = ff_playerids_loader()
    udfa_payload = {"sources": list(udfa_sources)}

    frozen = Path(output_root) / "_frozen_2025"
    frozen.mkdir(parents=True, exist_ok=True)
    _write_json(frozen / "cfbd_roster_2025.json", roster_rows)
    _write_json(frozen / "nflverse_draft_picks_2025_pin.json", draft_payload)
    _write_json(frozen / "ff_playerids_pin.json", ff_payload)
    _write_json(frozen / "udfa_sources_manifest.json", udfa_payload)

    manifest = {
        "cfbd_roster": {
            "source_snapshot_id": _snapshot_id(
                retrieval_timestamp=retrieval_timestamp,
                endpoint=cfbd_endpoint,
                api_version="v2",
                payload=roster_rows,
                row_count=len(roster_rows),
            )
        },
        "nflverse_draft_picks": {
            "source_snapshot_id": _snapshot_id(
                retrieval_timestamp=retrieval_timestamp,
                endpoint=f"nflreadpy.load_draft_picks({year})",
                api_version="nflverse",
                payload=draft_payload,
                row_count=len(draft_payload["rows"]),
            )
        },
        "ff_playerids": {
            "source_snapshot_id": _snapshot_id(
                retrieval_timestamp=retrieval_timestamp,
                endpoint="nflreadpy.load_ff_playerids()",
                api_version="dynastyprocess_crosswalk",
                payload=ff_payload,
                row_count=len(ff_payload["rows"]),
            )
        },
        "udfa_sources": {
            "source_snapshot_id": _snapshot_id(
                retrieval_timestamp=retrieval_timestamp,
                endpoint="udfa_source_manifest",
                api_version="manual_urls",
                payload=udfa_payload,
                row_count=len(udfa_sources),
            )
        },
    }
    _write_json(frozen / "manifest.json", manifest)
    return manifest
