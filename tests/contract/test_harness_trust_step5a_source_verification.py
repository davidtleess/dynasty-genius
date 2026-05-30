"""Step-5a RED: read-only DynastyProcess source verification report."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def _commit(repo: Path, *, when: str, message: str) -> str:
    env = {
        "GIT_AUTHOR_DATE": f"{when}T12:00:00Z",
        "GIT_COMMITTER_DATE": f"{when}T12:00:00Z",
    }
    _git(repo, "add", "files/values.csv", "files/db_playerids.csv", "LICENSE")
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def dynastyprocess_fixture_repo(tmp_path: Path) -> dict[str, object]:
    repo = tmp_path / "dp-data"
    (repo / "files").mkdir(parents=True)
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "LICENSE").write_text("GPL-3.0\n")
    (repo / "files" / "db_playerids.csv").write_text(
        "mfl_id,fantasypros_id,sleeper_id,position\n"
        ",1001,sleeper_qb_old,QB\n"
        ",1002,sleeper_wr_active,WR\n"
        ",2001,sleeper_pick,PICK\n"
    )

    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value_2qb,scrape_date,fp_id\n"
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,4100,2021-09-06,1001\n"
        "Active Wideout,WR,CIN,24,2020,40,40,WR14,3200,3200,2021-09-06,1002\n"
        "Future Pick,PICK,,0,2022,999,999,PICK,2000,2000,2021-09-06,2001\n"
        "Unmapped Runner,RB,SEA,24,2020,60,60,RB24,2500,2500,2021-09-06,9999\n"
    )
    before_sha = _commit(repo, when="2021-09-06", message="values before kickoff")

    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value_2qb,scrape_date,fp_id\n"
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,4200,2021-09-09,1001\n"
        "Active Wideout,WR,CIN,24,2020,40,40,WR14,3300,3300,2021-09-09,1002\n"
        "Future Pick,PICK,,0,2022,999,999,PICK,2100,2100,2021-09-09,2001\n"
        "Unmapped Runner,RB,SEA,24,2020,60,60,RB24,2600,2600,2021-09-09,9999\n"
    )
    after_sha = _commit(repo, when="2021-09-09", message="values after kickoff")

    return {"repo": repo, "before_sha": before_sha, "after_sha": after_sha}


def test_verify_source_prefers_on_or_before_commit_and_reports_core_metadata(
    dynastyprocess_fixture_repo: dict[str, object],
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    report = verify_source(
        repo_path=dynastyprocess_fixture_repo["repo"],
        target_dates=["2021-09-08"],
        survivorship_sentinels={
            "2021-09-08": [{"fp_id": "1001", "name": "Old Quarterback"}]
        },
    )

    target = report["targets"]["2021-09-08"]
    assert target["status"] == "available"
    assert target["selected_commit"]["sha"] == dynastyprocess_fixture_repo["before_sha"]
    assert target["selected_commit"]["commit_date"] == "2021-09-06"
    assert target["selected_commit"]["delta_days"] == -2
    assert target["source_family"] == "dynastyprocess_ecr_2qb"
    assert target["methodology"] == "fantasypros_ecr_consensus"
    assert target["schema"]["value_2qb_present"] is True
    assert "value_2qb" in target["schema"]["values_header"]
    assert target["license"] == "GPL-3.0"


def test_verify_source_computes_era_crosswalk_coverage_and_position_pools(
    dynastyprocess_fixture_repo: dict[str, object],
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    report = verify_source(
        repo_path=dynastyprocess_fixture_repo["repo"],
        target_dates=["2021-09-08"],
        survivorship_sentinels={},
    )

    target = report["targets"]["2021-09-08"]
    assert target["crosswalk"]["values_rows"] == 4
    assert target["crosswalk"]["mapped_rows"] == 2
    assert target["crosswalk"]["mapped_pick_rows_excluded"] == 1
    assert target["crosswalk"]["unmapped_rows"] == 1
    assert target["crosswalk"]["coverage_pct"] == pytest.approx(66.6667, rel=1e-4)
    assert target["per_position_matched_pool_n"] == {"QB": 1, "WR": 1}
    assert "PICK" not in target["per_position_matched_pool_n"]
    assert target["pool_evaluability"]["QB"]["primary_k"] == 12
    assert target["pool_evaluability"]["QB"]["status"] == "defer_pool_below_k"
    assert target["pool_evaluability"]["WR"]["primary_k"] == 24
    assert target["pool_evaluability"]["WR"]["status"] == "defer_pool_below_k"


def test_verify_source_records_survivorship_sentinel_presence(
    dynastyprocess_fixture_repo: dict[str, object],
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    report = verify_source(
        repo_path=dynastyprocess_fixture_repo["repo"],
        target_dates=["2021-09-08"],
        survivorship_sentinels={
            "2021-09-08": [
                {"fp_id": "1001", "name": "Old Quarterback"},
                {"fp_id": "5555", "name": "Missing Retired Player"},
            ]
        },
    )

    sentinels = report["targets"]["2021-09-08"]["survivorship_sentinels"]
    assert sentinels == [
        {"fp_id": "1001", "name": "Old Quarterback", "present": True},
        {"fp_id": "5555", "name": "Missing Retired Player", "present": False},
    ]


def test_verify_source_fails_closed_on_schema_drift_missing_value_2qb(
    tmp_path: Path,
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    repo = tmp_path / "dp-schema-drift"
    (repo / "files").mkdir(parents=True)
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "LICENSE").write_text("GPL-3.0\n")
    (repo / "files" / "db_playerids.csv").write_text(
        "fantasypros_id,sleeper_id,position\n1001,s1,QB\n"
    )
    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value,scrape_date,fp_id\n"
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,4100,2021-09-06,1001\n"
    )
    _commit(repo, when="2021-09-06", message="missing 2qb schema")

    report = verify_source(
        repo_path=repo,
        target_dates=["2021-09-08"],
        survivorship_sentinels={},
    )

    target = report["targets"]["2021-09-08"]
    assert target["status"] == "unavailable"
    assert "value_2qb_missing" in target["findings"]
    assert target["schema"]["value_2qb_present"] is False
    assert target["crosswalk"] is None


def test_verify_source_fails_closed_when_scrape_date_after_commit_date(
    tmp_path: Path,
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    repo = tmp_path / "dp-revision"
    (repo / "files").mkdir(parents=True)
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "LICENSE").write_text("GPL-3.0\n")
    (repo / "files" / "db_playerids.csv").write_text(
        "fantasypros_id,sleeper_id,position\n1001,s1,QB\n"
    )
    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value_2qb,scrape_date,fp_id\n"
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,4100,2021-09-12,1001\n"
    )
    _commit(repo, when="2021-09-06", message="future scrape date")

    report = verify_source(
        repo_path=repo,
        target_dates=["2021-09-08"],
        survivorship_sentinels={},
    )

    target = report["targets"]["2021-09-08"]
    assert target["status"] == "unavailable"
    assert "scrape_date_after_commit_date" in target["findings"]
    assert target["revision_guard"]["status"] == "fail"


def test_verify_source_has_no_snapshot_store_or_raw_archive_writes(
    dynastyprocess_fixture_repo: dict[str, object],
    tmp_path: Path,
) -> None:
    from scripts.verify_dynastyprocess_source import verify_source

    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    report = verify_source(
        repo_path=dynastyprocess_fixture_repo["repo"],
        target_dates=["2021-09-08"],
        survivorship_sentinels={},
    )
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}

    assert report["writes_performed"] == []
    assert before == after
    assert not list(tmp_path.rglob("*.db"))
