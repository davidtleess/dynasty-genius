"""S3 Task 10A raw-source freezing contract tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

FIXED_RETRIEVAL_TS = "2026-06-01T23:45:00Z"


def _freeze_module():
    path = Path("scripts/freeze_2025_prospect_sources.py")
    spec = importlib.util.spec_from_file_location("freeze_2025_sources", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_sha256(module, payload) -> str:
    return module.compute_canonical_json_sha256(payload)


class FakeCfbdClient:
    def __init__(self, *, all_team_rows=None, team_rows=None):
        self.all_team_rows = all_team_rows if all_team_rows is not None else []
        self.team_rows = team_rows or {}
        self.roster_calls: list[dict] = []
        self.team_calls: list[int] = []

    def get_roster(self, *, year: int, team: str | None = None):
        self.roster_calls.append({"year": year, "team": team})
        if team is None:
            return list(self.all_team_rows)
        return list(self.team_rows.get(team, []))

    def list_teams(self, *, year: int) -> list[str]:
        self.team_calls.append(year)
        return sorted(self.team_rows)


def _draft_picks_payload():
    return {
        "release_tag": "nflverse-data-test-release",
        "rows": [
            {
                "season": 2025,
                "round": 1,
                "pick": 4,
                "team": "NE",
                "gsis_id": "00-2025",
                "pfr_player_id": "TestDr00",
                "cfb_player_id": "test-drafted-1",
                "pfr_player_name": "Test Drafted",
                "position": "WR",
                "college": "Test State",
            }
        ],
    }


def _ff_playerids_payload():
    return {
        "snapshot_date": "2026-01-10",
        "rows": [
            {
                "mfl_id": "12345",
                "gsis_id": "00-2025",
                "sleeper_id": "99999",
                "cfbref_id": "test-drafted-1",
            }
        ],
    }


def test_freeze_2025_sources_writes_raw_inputs_manifest_and_hashes(tmp_path: Path):
    module = _freeze_module()
    output_root = tmp_path / "resources" / "prospect_fixtures"
    cfbd_rows = [
        {
            "id": 101,
            "firstName": "Test",
            "lastName": "Drafted",
            "team": "Test State",
            "position": "WR",
        },
        {
            "id": 102,
            "firstName": "Test",
            "lastName": "Back",
            "team": "Example",
            "position": "RB",
        },
    ]
    cfbd_client = FakeCfbdClient(all_team_rows=cfbd_rows)
    udfa_sources = [
        {
            "name": "NFL.com 2025 UDFA tracker",
            "url": "https://www.nfl.com/2025-udfa-tracker",
        },
        {
            "name": "Spotrac 2025 undrafted database",
            "url": "https://www.spotrac.com/nfl/undrafted/_/year/2025",
        },
    ]

    manifest = module.freeze_2025_prospect_sources(
        output_root=output_root,
        year=2025,
        retrieval_timestamp=FIXED_RETRIEVAL_TS,
        cfbd_client=cfbd_client,
        draft_picks_loader=lambda year: _draft_picks_payload(),
        ff_playerids_loader=_ff_playerids_payload,
        udfa_sources=udfa_sources,
    )

    frozen_dir = output_root / "_frozen_2025"
    assert frozen_dir.exists()
    assert {
        path.name for path in frozen_dir.iterdir() if path.is_file()
    } == {
        "cfbd_roster_2025.json",
        "nflverse_draft_picks_2025_pin.json",
        "ff_playerids_pin.json",
        "udfa_sources_manifest.json",
        "manifest.json",
    }
    assert all(
        frozen_dir in path.parents
        for path in tmp_path.rglob("*")
        if path.is_file()
    )

    raw_cfbd = json.loads((frozen_dir / "cfbd_roster_2025.json").read_text())
    draft_pin = json.loads(
        (frozen_dir / "nflverse_draft_picks_2025_pin.json").read_text()
    )
    ff_pin = json.loads((frozen_dir / "ff_playerids_pin.json").read_text())
    udfa_manifest = json.loads(
        (frozen_dir / "udfa_sources_manifest.json").read_text()
    )
    manifest_file = json.loads((frozen_dir / "manifest.json").read_text())

    assert raw_cfbd == cfbd_rows
    assert draft_pin == _draft_picks_payload()
    assert ff_pin == _ff_playerids_payload()
    assert udfa_manifest == {"sources": udfa_sources}
    assert manifest == manifest_file

    expected_cfbd_hash = _canonical_sha256(module, cfbd_rows)
    expected_draft_hash = _canonical_sha256(module, _draft_picks_payload())
    expected_ff_hash = _canonical_sha256(module, _ff_playerids_payload())
    expected_udfa_hash = _canonical_sha256(module, {"sources": udfa_sources})

    assert manifest["cfbd_roster"]["source_snapshot_id"] == {
        "retrieval_timestamp": FIXED_RETRIEVAL_TS,
        "endpoint": "/roster?year=2025",
        "api_version": "v2",
        "sha256": expected_cfbd_hash,
        "row_count": 2,
    }
    assert manifest["nflverse_draft_picks"]["source_snapshot_id"] == {
        "retrieval_timestamp": FIXED_RETRIEVAL_TS,
        "endpoint": "nflreadpy.load_draft_picks(2025)",
        "api_version": "nflverse",
        "sha256": expected_draft_hash,
        "row_count": 1,
    }
    assert manifest["ff_playerids"]["source_snapshot_id"] == {
        "retrieval_timestamp": FIXED_RETRIEVAL_TS,
        "endpoint": "nflreadpy.load_ff_playerids()",
        "api_version": "dynastyprocess_crosswalk",
        "sha256": expected_ff_hash,
        "row_count": 1,
    }
    assert manifest["udfa_sources"]["source_snapshot_id"] == {
        "retrieval_timestamp": FIXED_RETRIEVAL_TS,
        "endpoint": "udfa_source_manifest",
        "api_version": "manual_urls",
        "sha256": expected_udfa_hash,
        "row_count": 2,
    }
    assert cfbd_client.roster_calls == [{"year": 2025, "team": None}]


def test_freeze_2025_sources_uses_per_team_fallback_when_all_team_roster_empty(
    tmp_path: Path,
):
    module = _freeze_module()
    output_root = tmp_path / "resources" / "prospect_fixtures"
    cfbd_client = FakeCfbdClient(
        all_team_rows=[],
        team_rows={
            "Ole Miss": [
                {
                    "id": 201,
                    "firstName": "Alias",
                    "lastName": "Receiver",
                    "team": "Ole Miss",
                    "position": "WR",
                }
            ],
            "Miami": [
                {
                    "id": 202,
                    "firstName": "Fallback",
                    "lastName": "Quarterback",
                    "team": "Miami",
                    "position": "QB",
                }
            ],
        },
    )

    manifest = module.freeze_2025_prospect_sources(
        output_root=output_root,
        year=2025,
        retrieval_timestamp=FIXED_RETRIEVAL_TS,
        cfbd_client=cfbd_client,
        draft_picks_loader=lambda year: _draft_picks_payload(),
        ff_playerids_loader=_ff_playerids_payload,
        udfa_sources=[],
    )

    frozen_dir = output_root / "_frozen_2025"
    raw_cfbd = json.loads((frozen_dir / "cfbd_roster_2025.json").read_text())

    assert cfbd_client.team_calls == [2025]
    assert cfbd_client.roster_calls == [
        {"year": 2025, "team": None},
        {"year": 2025, "team": "Miami"},
        {"year": 2025, "team": "Ole Miss"},
    ]
    assert raw_cfbd == [
        {
            "id": 202,
            "firstName": "Fallback",
            "lastName": "Quarterback",
            "team": "Miami",
            "position": "QB",
        },
        {
            "id": 201,
            "firstName": "Alias",
            "lastName": "Receiver",
            "team": "Ole Miss",
            "position": "WR",
        },
    ]
    assert manifest["cfbd_roster"]["source_snapshot_id"]["endpoint"] == (
        "/roster?year=2025&team=*"
    )
    assert manifest["cfbd_roster"]["source_snapshot_id"]["row_count"] == 2
