"""S3 Task 10A T3 live-freeze runner contract tests.

These tests lock the live runner wiring without live CFBD/nflreadpy calls. The
runner is T3-freeze only: it may freeze raw inputs under ``_frozen_2025/`` but
must not build the 2025 prospect fixture.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

RUNNER_PATH = Path("scripts/run_t3_freeze_2025.py")
FIXED_TS = "2026-06-02T20:00:00Z"


def _runner_module():
    assert RUNNER_PATH.exists(), "T3 live-freeze runner is not implemented yet"
    spec = importlib.util.spec_from_file_location("run_t3_freeze_2025", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self):
        self.calls: list[dict] = []
        self.payloads = {
            ("/roster", (("year", 2025),)): [
                {
                    "id": "184812",
                    "firstName": "Fcs",
                    "lastName": "Receiver",
                    "position": "WR",
                    "team": "Cal Poly",
                }
            ],
            ("/roster", (("team", "Cal Poly"), ("year", 2025))): [
                {
                    "id": "184812",
                    "firstName": "Fcs",
                    "lastName": "Receiver",
                    "position": "WR",
                    "team": "Cal Poly",
                }
            ],
            ("/teams", (("year", 2025),)): [
                {"school": "Cal Poly", "classification": "fcs"},
                {"school": "Georgia", "classification": "fbs"},
            ],
        }

    def get(self, url: str, *, params=None, headers=None, timeout=None):
        path = url.removeprefix("https://api.collegefootballdata.com")
        normalized_params = tuple(sorted((params or {}).items()))
        self.calls.append(
            {
                "path": path,
                "params": dict(params or {}),
                "headers": dict(headers or {}),
                "timeout": timeout,
            }
        )
        return FakeResponse(self.payloads[(path, normalized_params)])


class FakeFrame:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def to_dicts(self) -> list[dict]:
        return list(self._rows)


def _fake_nflreadpy(calls: list[tuple[str, object]]):
    def load_draft_picks(*, seasons):
        calls.append(("load_draft_picks", seasons))
        return FakeFrame(
            [
                {
                    "season": 2025,
                    "round": 5,
                    "pick": 150,
                    "pfr_player_id": "FcsRe00",
                    "pfr_player_name": "Fcs Receiver",
                    "position": "WR",
                    "college": "Cal Poly",
                }
            ]
        )

    def load_ff_playerids():
        calls.append(("load_ff_playerids", None))
        return FakeFrame(
            [
                {
                    "gsis_id": "00-2025",
                    "pfr_id": "FcsRe00",
                    "sleeper_id": "123456",
                }
            ]
        )

    return SimpleNamespace(
        load_draft_picks=load_draft_picks,
        load_ff_playerids=load_ff_playerids,
    )


def test_cfbd_client_uses_bearer_auth_year_roster_and_full_teams_endpoint():
    module = _runner_module()
    http_client = FakeHttpClient()
    client = module.CFBDClient(api_key="test-key", http_client=http_client)

    roster = client.get_roster(year=2025)
    team_roster = client.get_roster(year=2025, team="Cal Poly")
    teams = client.list_teams(year=2025)

    assert roster[0]["team"] == "Cal Poly"
    assert team_roster[0]["id"] == "184812"
    assert teams == ["Cal Poly", "Georgia"]
    assert [call["path"] for call in http_client.calls] == [
        "/roster",
        "/roster",
        "/teams",
    ]
    assert http_client.calls[0]["params"] == {"year": 2025}
    assert http_client.calls[1]["params"] == {"year": 2025, "team": "Cal Poly"}
    assert http_client.calls[2]["params"] == {"year": 2025}
    assert "/teams/fbs" not in {call["path"] for call in http_client.calls}
    assert all(
        call["headers"]["Authorization"] == "Bearer test-key"
        for call in http_client.calls
    )


def test_run_t3_freeze_wires_live_sources_and_writes_only_frozen_inputs(tmp_path: Path):
    module = _runner_module()
    http_client = FakeHttpClient()
    nflreadpy_calls: list[tuple[str, object]] = []

    manifest = module.run_t3_freeze_2025(
        output_root=tmp_path,
        year=2025,
        api_key="test-key",
        retrieval_timestamp=FIXED_TS,
        http_client=http_client,
        nflreadpy_module=_fake_nflreadpy(nflreadpy_calls),
        print_summary=False,
    )

    frozen_dir = tmp_path / "_frozen_2025"
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
    assert not (tmp_path / "2025_fantasy_prospects.json").exists()
    assert not (tmp_path / "2025_review_queue.json").exists()

    raw_roster = json.loads((frozen_dir / "cfbd_roster_2025.json").read_text())
    draft_pin = json.loads(
        (frozen_dir / "nflverse_draft_picks_2025_pin.json").read_text()
    )
    ff_pin = json.loads((frozen_dir / "ff_playerids_pin.json").read_text())
    udfa_manifest = json.loads((frozen_dir / "udfa_sources_manifest.json").read_text())

    assert raw_roster[0]["team"] == "Cal Poly"
    assert draft_pin["rows"][0]["pfr_player_name"] == "Fcs Receiver"
    assert ff_pin["rows"][0]["sleeper_id"] == "123456"
    assert {source["name"] for source in udfa_manifest["sources"]} == {
        "NFL.com 2025 UDFA tracker",
        "PFF 2025 UDFA tracker",
        "Spotrac 2025 undrafted database",
    }
    assert manifest["cfbd_roster"]["source_snapshot_id"]["endpoint"] == (
        "/roster?year=2025"
    )
    assert manifest["cfbd_roster"]["source_snapshot_id"]["row_count"] == 1
    assert manifest["cfbd_roster"]["source_snapshot_id_str"].startswith(
        f"cfbd_roster_2025:{FIXED_TS}:/roster?year=2025:v2:"
    )
    assert nflreadpy_calls == [
        ("load_draft_picks", [2025]),
        ("load_ff_playerids", None),
    ]
    assert [call["path"] for call in http_client.calls] == ["/roster"]


def test_run_t3_freeze_requires_cfbd_api_key(tmp_path: Path, monkeypatch):
    module = _runner_module()
    monkeypatch.delenv("CFBD_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CFBD_API_KEY"):
        module.run_t3_freeze_2025(
            output_root=tmp_path,
            year=2025,
            retrieval_timestamp=FIXED_TS,
            http_client=FakeHttpClient(),
            nflreadpy_module=_fake_nflreadpy([]),
            print_summary=False,
        )
