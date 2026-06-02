"""Freeze the raw 2025 prospect source inputs for S3 Task 10A (spec §6).

Read-only capture of the layered source stack into an immutable, content-hashed
snapshot under ``<output_root>/_frozen_2025/`` so every registry row is later
regenerable from a pinned, provenance-cited input set:

- CFBD ``/roster?year={roster_year}`` (= ``draft_year - 1`` = 2024 for the 2025 class;
  college-identity substrate — draftees are on their LAST-college-season roster, not the
  draft-year roster; all-team pull, with a per-team fallback when all-team is empty),
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


def _snapshot_id_str(source: str, snapshot_id: dict) -> str:
    """Canonical pre-composed snapshot string (spec §6, D5 — single source of truth).

    ``f"{source}:{retrieval_timestamp}:{endpoint}:{api_version}:{sha256}:{row_count}"``
    where ``source`` is the **year-qualified artifact name** (the persisted file stem) —
    the CFBD roster stem uses ``roster_year`` (e.g. ``cfbd_roster_{roster_year}`` =
    ``cfbd_roster_2024`` for the 2025 class), the draft/ff/udfa stems use ``draft_year``
    (e.g. ``draft_picks_2025``); NOT the bare manifest dict key. The Task-2 builder reads
    this string verbatim; it is never recomposed downstream.
    """
    return ":".join(
        [
            source,
            snapshot_id["retrieval_timestamp"],
            snapshot_id["endpoint"],
            snapshot_id["api_version"],
            snapshot_id["sha256"],
            str(snapshot_id["row_count"]),
        ]
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def freeze_2025_prospect_sources(
    *,
    output_root: Path,
    roster_year: int,
    draft_year: int,
    retrieval_timestamp: str,
    cfbd_client: Any,
    draft_picks_loader: Callable[[int], Any],
    ff_playerids_loader: Callable[[], Any],
    udfa_sources: list[dict],
) -> dict:
    """Freeze the four raw inputs + a hashed manifest under ``_frozen_{draft_year}/``.

    Spec §2 year decoupling: ``roster_year`` (= ``draft_year - 1``) drives the CFBD
    ``/roster`` pull and the ``cfbd_roster_{roster_year}`` artifact + stem; ``draft_year``
    drives ``load_draft_picks`` + the draft/ff/udfa stems + the ``_frozen_{draft_year}/``
    directory. Returns the manifest (also written to ``manifest.json``). Writes ONLY under
    ``<output_root>/_frozen_{draft_year}/``; performs no live network calls itself.
    """
    # CFBD roster (roster_year): all-team pull, per-team fallback when all-team is empty.
    roster_rows = list(cfbd_client.get_roster(year=roster_year, team=None))
    if roster_rows:
        cfbd_endpoint = f"/roster?year={roster_year}"
    else:
        roster_rows = []
        for team in sorted(cfbd_client.list_teams(year=roster_year)):
            roster_rows.extend(cfbd_client.get_roster(year=roster_year, team=team))
        cfbd_endpoint = f"/roster?year={roster_year}&team=*"

    draft_payload = draft_picks_loader(draft_year)
    ff_payload = ff_playerids_loader()
    udfa_payload = {"sources": list(udfa_sources)}

    frozen = Path(output_root) / f"_frozen_{draft_year}"
    frozen.mkdir(parents=True, exist_ok=True)
    _write_json(frozen / f"cfbd_roster_{roster_year}.json", roster_rows)
    _write_json(frozen / f"nflverse_draft_picks_{draft_year}_pin.json", draft_payload)
    _write_json(frozen / "ff_playerids_pin.json", ff_payload)
    _write_json(frozen / "udfa_sources_manifest.json", udfa_payload)

    cfbd_sid = _snapshot_id(
        retrieval_timestamp=retrieval_timestamp,
        endpoint=cfbd_endpoint,
        api_version="v2",
        payload=roster_rows,
        row_count=len(roster_rows),
    )
    draft_sid = _snapshot_id(
        retrieval_timestamp=retrieval_timestamp,
        endpoint=f"nflreadpy.load_draft_picks({draft_year})",
        api_version="nflverse",
        payload=draft_payload,
        row_count=len(draft_payload["rows"]),
    )
    ff_sid = _snapshot_id(
        retrieval_timestamp=retrieval_timestamp,
        endpoint="nflreadpy.load_ff_playerids()",
        api_version="dynastyprocess_crosswalk",
        payload=ff_payload,
        row_count=len(ff_payload["rows"]),
    )
    udfa_sid = _snapshot_id(
        retrieval_timestamp=retrieval_timestamp,
        endpoint="udfa_source_manifest",
        api_version="manual_urls",
        payload=udfa_payload,
        row_count=len(udfa_sources),
    )

    # Each entry carries the structured snapshot dict AND the canonical pre-composed
    # string (spec §6 D5). ``{source}`` is the year-qualified artifact name (file stem).
    manifest = {
        "cfbd_roster": {
            "source_snapshot_id": cfbd_sid,
            "source_snapshot_id_str": _snapshot_id_str(f"cfbd_roster_{roster_year}", cfbd_sid),
        },
        "nflverse_draft_picks": {
            "source_snapshot_id": draft_sid,
            "source_snapshot_id_str": _snapshot_id_str(f"draft_picks_{draft_year}", draft_sid),
        },
        "ff_playerids": {
            "source_snapshot_id": ff_sid,
            "source_snapshot_id_str": _snapshot_id_str(f"ff_playerids_{draft_year}", ff_sid),
        },
        "udfa_sources": {
            "source_snapshot_id": udfa_sid,
            "source_snapshot_id_str": _snapshot_id_str(f"udfa_sources_{draft_year}", udfa_sid),
        },
    }
    _write_json(frozen / "manifest.json", manifest)
    return manifest
