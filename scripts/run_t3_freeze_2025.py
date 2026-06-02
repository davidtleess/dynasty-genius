"""S3 Task 10A — T3 live-freeze runner (replaces the discarded run_2025_curation.py).

Wires a live CFBD client + nflreadpy loaders into the cleared, pure freeze core
(`scripts/freeze_2025_prospect_sources.py`, committed `91de04a`) and writes ONLY
`<output_root>/_frozen_2025/`.

**T3 FREEZE ONLY.** This runner does NOT build the 2025 prospect fixture or any review
queue (that is T4, kept separate and gated for David's inspection of the frozen pull).

Year decoupling (spec §2): `roster_year` (= `draft_year - 1` = 2024 for the 2025 class)
drives the CFBD `/roster` pull; `draft_year` (2025) drives `load_draft_picks`/UDFA + the
`_frozen_{draft_year}/` dir. Probe-confirmed API shape (read-only `scripts/probe_cfbd_api.py`,
2026-06-02): live `/roster?year=` returns ALL teams in one call (incl. FCS) — so the freeze
core's primary all-team path is used and the per-team fallback does not trigger. The
fallback's team list uses `/teams` (all divisions, incl. FCS), NOT `/teams/fbs`.

Usage (key from gitignored env, never echoed):
    set -a; . ./.env; set +a; .venv/bin/python3.14 scripts/run_t3_freeze_2025.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

BASE_URL = "https://api.collegefootballdata.com"

# Named UDFA-tracker source manifest (spec §2 L3 — identity membership only; no values).
UDFA_SOURCES: list[dict] = [
    {"name": "NFL.com 2025 UDFA tracker", "url": "https://www.nfl.com/news/2025-undrafted-free-agent-tracker"},
    {"name": "PFF 2025 UDFA tracker", "url": "https://www.pff.com/news/nfl-2025-undrafted-free-agent-tracker"},
    {"name": "Spotrac 2025 undrafted database", "url": "https://www.spotrac.com/nfl/undrafted/_/year/2025"},
]


class CFBDClient:
    """Live CFBD client conforming to the freeze core's injected interface.

    ``http_client`` must expose ``get(url, *, params, headers, timeout)`` returning a
    response with ``.raise_for_status()`` and ``.json()`` (e.g. ``httpx.Client``).
    """

    def __init__(self, api_key: str, http_client: Any):
        self.api_key = api_key.strip()
        self.http_client = http_client

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_roster(self, *, year: int, team: str | None = None) -> list:
        params: dict = {"year": year}
        if team is not None:
            params["team"] = team
        resp = self.http_client.get(
            f"{BASE_URL}/roster", params=params, headers=self._headers(), timeout=30.0
        )
        resp.raise_for_status()
        return resp.json() or []

    def list_teams(self, *, year: int) -> list[str]:
        # /teams (ALL divisions incl. FCS), NOT /teams/fbs. Only used by the freeze
        # core's empty-all-team fallback, which the probe shows does not trigger.
        resp = self.http_client.get(
            f"{BASE_URL}/teams", params={"year": year}, headers=self._headers(), timeout=30.0
        )
        resp.raise_for_status()
        return [t["school"] for t in resp.json() if "school" in t]


def _load_freeze_core() -> Any:
    path = Path(__file__).resolve().parent / "freeze_2025_prospect_sources.py"
    spec = importlib.util.spec_from_file_location("freeze_2025_prospect_sources", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_t3_freeze_2025(
    *,
    output_root: Path,
    roster_year: int,
    draft_year: int,
    retrieval_timestamp: str,
    http_client: Any,
    nflreadpy_module: Any,
    api_key: str | None = None,
    print_summary: bool = True,
) -> dict:
    """Freeze the live source stack into ``_frozen_{draft_year}/``; return the manifest.

    Spec §2 year decoupling: ``roster_year`` (= ``draft_year - 1``) drives the CFBD
    ``/roster`` pull + ``cfbd_roster_{roster_year}`` artifact; ``draft_year`` drives
    ``load_draft_picks`` + the registry class + the frozen dir. Fail-closed: raises
    ``RuntimeError`` if no ``api_key`` arg and no ``CFBD_API_KEY`` env. T3 only — never
    builds the T4 fixture/review queue.
    """
    key = api_key or os.getenv("CFBD_API_KEY")
    if not key:
        raise RuntimeError(
            "CFBD_API_KEY not available (no api_key argument and CFBD_API_KEY env unset)"
        )
    cfbd_client = CFBDClient(api_key=key, http_client=http_client)

    def draft_picks_loader(yr: int) -> dict:
        frame = nflreadpy_module.load_draft_picks(seasons=[yr])
        return {"release_tag": "live_nflverse_release", "rows": frame.to_dicts()}

    def ff_playerids_loader() -> dict:
        frame = nflreadpy_module.load_ff_playerids()
        return {"snapshot_date": "live_nflreadpy_snapshot", "rows": frame.to_dicts()}

    freeze = _load_freeze_core()
    manifest = freeze.freeze_2025_prospect_sources(
        output_root=Path(output_root),
        roster_year=roster_year,
        draft_year=draft_year,
        retrieval_timestamp=retrieval_timestamp,
        cfbd_client=cfbd_client,
        draft_picks_loader=draft_picks_loader,
        ff_playerids_loader=ff_playerids_loader,
        udfa_sources=UDFA_SOURCES,
    )

    if print_summary:
        # Bounded summary for David's inspection — counts/hashes/endpoints, NEVER the key.
        print(f"T3 freeze complete -> {Path(output_root) / f'_frozen_{draft_year}'}")
        for source, entry in manifest.items():
            sid = entry["source_snapshot_id"]
            print(
                f"  {source}: rows={sid['row_count']} "
                f"sha256={sid['sha256'][:12]}… endpoint={sid['endpoint']}"
            )
    return manifest


def main(argv: list[str] | None = None) -> int:
    import datetime

    import httpx
    import nflreadpy

    retrieval_timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_root = Path("resources/prospect_fixtures")
    with httpx.Client() as client:
        run_t3_freeze_2025(
            output_root=output_root,
            roster_year=2024,
            draft_year=2025,
            retrieval_timestamp=retrieval_timestamp,
            http_client=client,
            nflreadpy_module=nflreadpy,
            print_summary=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
