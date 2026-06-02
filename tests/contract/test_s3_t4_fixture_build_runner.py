"""S3 Task 10A T4 fixture-build runner contract tests.

The T4 runner consumes the committed T3 frozen payloads and writes only the
provisional fixture + review queue that David inspects before any registry ingest.
It must not re-freeze sources, call live APIs, or mint registry/bridge records.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

RUNNER_PATH = Path("scripts/build_2025_fixture_from_frozen.py")


def _runner_module():
    assert RUNNER_PATH.exists(), "T4 fixture-build runner is not implemented yet"
    spec = importlib.util.spec_from_file_location("build_2025_fixture_from_frozen", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_frozen_stack(root: Path) -> None:
    frozen_dir = root / "_frozen_2025"
    frozen_dir.mkdir(parents=True)
    (frozen_dir / "cfbd_roster_2024.json").write_text(
        json.dumps(
            [
                {
                    "id": "101",
                    "firstName": "Alias",
                    "lastName": "Receiver",
                    "position": "WR",
                    "team": "Ole Miss",
                    "year": 3,
                }
            ]
        )
    )
    (frozen_dir / "nflverse_draft_picks_2025_pin.json").write_text(
        json.dumps(
            {
                "release_tag": "test-release",
                "rows": [
                    {
                        "season": 2025,
                        "pfr_player_id": "AliasRe00",
                        "pfr_player_name": "Alias Receiver",
                        "position": "WR",
                        "college": "Mississippi",
                        "pick": 42,
                    }
                ],
            }
        )
    )
    (frozen_dir / "ff_playerids_pin.json").write_text(
        json.dumps({"snapshot_date": "test-snapshot", "rows": []})
    )
    (frozen_dir / "udfa_sources_manifest.json").write_text(
        json.dumps({"sources": [{"name": "Test UDFA source", "url": "https://example.test"}]})
    )
    (frozen_dir / "manifest.json").write_text(
        json.dumps(
            {
                "cfbd_roster": {
                    "source_snapshot_id": {
                        "retrieval_timestamp": "2026-06-02T20:14:35Z",
                        "endpoint": "/roster?year=2024",
                        "api_version": "v2",
                        "sha256": "cfbdhash",
                        "row_count": 1,
                    },
                    "source_snapshot_id_str": (
                        "cfbd_roster_2024:2026-06-02T20:14:35Z:"
                        "/roster?year=2024:v2:cfbdhash:1"
                    ),
                }
            }
        )
    )


def _fake_builder(calls: list[dict]):
    def build_2025_prospect_fixture(frozen_inputs, *, school_aliases=None):
        calls.append(
            {
                "frozen_inputs": frozen_inputs,
                "school_aliases": dict(school_aliases or {}),
            }
        )
        return (
            [
                {
                    "raw_name": "Alias Receiver",
                    "cfbd_athlete_id": "101",
                    "source_snapshot_id": (
                        "cfbd_roster_2024:2026-06-02T20:14:35Z:"
                        "/roster?year=2024:v2:cfbdhash:1"
                    ),
                }
            ],
            [
                {
                    "source_record_id": "MissPr00",
                    "reason": "draft_truth_match_missing",
                    "action": "manual_review_required",
                },
                {
                    "source_record_id": "AthUn00",
                    "reason": "unresolved_draft_pick_position",
                    "action": "manual_review_required",
                },
            ],
        )

    return build_2025_prospect_fixture


def test_build_runner_loads_frozen_stack_invokes_builder_and_writes_only_fixture_outputs(
    tmp_path: Path,
):
    module = _runner_module()
    _write_frozen_stack(tmp_path)
    calls: list[dict] = []

    summary = module.build_2025_fixture_from_frozen(
        output_root=tmp_path,
        builder=_fake_builder(calls),
        print_summary=False,
    )

    assert len(calls) == 1
    frozen_inputs = calls[0]["frozen_inputs"]
    assert set(frozen_inputs) == {
        "cfbd_roster",
        "nflverse_draft_picks",
        "ff_playerids",
        "udfa_sources",
        "manifest",
    }
    assert frozen_inputs["cfbd_roster"][0]["team"] == "Ole Miss"
    assert frozen_inputs["nflverse_draft_picks"]["rows"][0]["college"] == "Mississippi"
    assert frozen_inputs["ff_playerids"]["rows"] == []
    assert frozen_inputs["udfa_sources"]["sources"][0]["name"] == "Test UDFA source"
    assert frozen_inputs["manifest"]["cfbd_roster"]["source_snapshot_id"]["row_count"] == 1
    assert calls[0]["school_aliases"]["ole miss"] == "mississippi"
    assert {
        "boise st.": "boise state",
        "montana st.": "montana state",
        "north dakota st.": "north dakota state",
        "utah st.": "utah state",
        "central florida": "ucf",
    }.items() <= calls[0]["school_aliases"].items()

    fixture_path = tmp_path / "2025_fantasy_prospects.json"
    review_path = tmp_path / "2025_review_queue.json"
    assert json.loads(fixture_path.read_text()) == [
        {
            "raw_name": "Alias Receiver",
            "cfbd_athlete_id": "101",
            "source_snapshot_id": (
                "cfbd_roster_2024:2026-06-02T20:14:35Z:"
                "/roster?year=2024:v2:cfbdhash:1"
            ),
        }
    ]
    assert json.loads(review_path.read_text()) == [
        {
            "source_record_id": "MissPr00",
            "reason": "draft_truth_match_missing",
            "action": "manual_review_required",
        },
        {
            "source_record_id": "AthUn00",
            "reason": "unresolved_draft_pick_position",
            "action": "manual_review_required",
        },
    ]
    assert {path.name for path in tmp_path.iterdir()} == {
        "_frozen_2025",
        "2025_fantasy_prospects.json",
        "2025_review_queue.json",
    }
    assert not (tmp_path / "college_prospect_registry.json").exists()
    assert not (tmp_path / "college_prospect_bridge.json").exists()
    assert summary == {
        "emitted_rows": 1,
        "review_queue_rows": 2,
        "review_reasons": {
            "draft_truth_match_missing": 1,
            "unresolved_draft_pick_position": 1,
        },
    }


def test_build_runner_prints_bounded_summary(tmp_path: Path, capsys):
    module = _runner_module()
    _write_frozen_stack(tmp_path)

    module.build_2025_fixture_from_frozen(
        output_root=tmp_path,
        builder=_fake_builder([]),
        print_summary=True,
    )

    out = capsys.readouterr().out
    assert "T4 fixture build complete" in out
    assert "emitted_rows=1" in out
    assert "review_queue_rows=2" in out
    assert "draft_truth_match_missing=1" in out
    assert "unresolved_draft_pick_position=1" in out
    assert "Authorization" not in out
    assert "CFBD_API_KEY" not in out


def test_build_runner_fails_closed_when_required_frozen_file_is_missing(tmp_path: Path):
    module = _runner_module()
    _write_frozen_stack(tmp_path)
    (tmp_path / "_frozen_2025" / "manifest.json").unlink()

    with pytest.raises(FileNotFoundError, match="manifest.json"):
        module.build_2025_fixture_from_frozen(
            output_root=tmp_path,
            builder=_fake_builder([]),
            print_summary=False,
        )

    assert not (tmp_path / "2025_fantasy_prospects.json").exists()
    assert not (tmp_path / "2025_review_queue.json").exists()
