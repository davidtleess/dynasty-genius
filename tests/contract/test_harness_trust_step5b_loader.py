"""Step-5b.1 RED: DynastyProcess archive loader into the backfill adapter."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


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


def _init_repo(tmp_path: Path, name: str = "dp-data") -> Path:
    repo = tmp_path / name
    (repo / "files").mkdir(parents=True)
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "LICENSE").write_text("GPL-3.0\n")
    return repo


def _write_ids(repo: Path) -> None:
    (repo / "files" / "db_playerids.csv").write_text(
        "mfl_id,fantasypros_id,sleeper_id,position\n"
        ",1001,sleeper_qb_old,QB\n"
        ",1002,sleeper_wr_active,WR\n"
        ",2001,sleeper_pick,PICK\n"
    )


def _write_values(repo: Path, *, scrape_date: str, qb_value: int, wr_value: int) -> None:
    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value_2qb,scrape_date,fp_id\n"
        f"Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,{qb_value},"
        f"{scrape_date},1001\n"
        f"Active Wideout,WR,CIN,24,2020,40,40,WR14,3200,{wr_value},"
        f"{scrape_date},1002\n"
        f"Future Pick,PICK,,0,2022,999,999,PICK,2000,2000,{scrape_date},2001\n"
        f"Unmapped Runner,RB,SEA,24,2020,60,60,RB24,2500,2500,"
        f"{scrape_date},9999\n"
    )


def _fixture_repo_with_before_and_after(tmp_path: Path) -> dict[str, object]:
    repo = _init_repo(tmp_path)
    _write_ids(repo)
    _write_values(repo, scrape_date="2021-09-06", qb_value=4100, wr_value=3200)
    before_sha = _commit(repo, when="2021-09-06", message="values before target")
    _write_values(repo, scrape_date="2021-09-09", qb_value=4200, wr_value=3300)
    after_sha = _commit(repo, when="2021-09-09", message="values after target")
    return {"repo": repo, "before_sha": before_sha, "after_sha": after_sha}


def test_loader_maps_real_schema_player_rows_into_backfill_adapter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.load_dynastyprocess_archive as loader

    fixture = _fixture_repo_with_before_and_after(tmp_path)
    captured: dict[str, object] = {}

    def fake_backfill_market_archive(archive, *, db_path, snapshot_dates):
        captured["archive"] = archive
        captured["db_path"] = db_path
        captured["snapshot_dates"] = snapshot_dates
        return {"rows_written": len(archive), "rows_skipped": 0}

    monkeypatch.setattr(loader, "backfill_market_archive", fake_backfill_market_archive)

    stats = loader.load_dynastyprocess_archive(
        repo_path=fixture["repo"],
        target_dates=["2021-09-08"],
        db_path=tmp_path / "snapshots.db",
    )

    assert stats["targets"]["2021-09-08"]["status"] == "loaded"
    assert stats["targets"]["2021-09-08"]["selected_commit"]["sha"] == fixture[
        "before_sha"
    ]
    assert stats["targets"]["2021-09-08"]["selected_commit"]["delta_days"] == -2
    assert stats["targets"]["2021-09-08"]["adapter_rows_emitted"] == 2
    assert stats["targets"]["2021-09-08"]["pick_rows_excluded"] == 1
    assert stats["targets"]["2021-09-08"]["unmapped_rows_skipped"] == 1

    assert captured["snapshot_dates"] == ["2021-09-08"]
    assert captured["archive"] == [
        {
            "sleeper_id": "sleeper_qb_old",
            "value": 4100,
            "position": "QB",
            "archive_publish_date": "2021-09-06",
            "source": "dp_archive",
            "updated_at": "2021-09-06",
            "overall_rank": None,
            "position_rank": None,
        },
        {
            "sleeper_id": "sleeper_wr_active",
            "value": 3200,
            "position": "WR",
            "archive_publish_date": "2021-09-06",
            "source": "dp_archive",
            "updated_at": "2021-09-06",
            "overall_rank": None,
            "position_rank": None,
        },
    ]


def test_loader_is_idempotent_when_re_run_against_snapshot_store(tmp_path: Path) -> None:
    from scripts.load_dynastyprocess_archive import load_dynastyprocess_archive

    fixture = _fixture_repo_with_before_and_after(tmp_path)
    db_path = tmp_path / "snapshots.db"

    first = load_dynastyprocess_archive(
        repo_path=fixture["repo"],
        target_dates=["2021-09-08"],
        db_path=db_path,
    )
    second = load_dynastyprocess_archive(
        repo_path=fixture["repo"],
        target_dates=["2021-09-08"],
        db_path=db_path,
    )

    assert first["targets"]["2021-09-08"]["rows_written"] == 2
    assert second["targets"]["2021-09-08"]["rows_written"] == 2
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08")
    assert len(rows) == 2
    assert {r["sleeper_id"] for r in rows} == {"sleeper_qb_old", "sleeper_wr_active"}
    assert {r["source"] for r in rows} == {"dp_archive"}
    assert {r["value"] for r in rows} == {4100, 3200}


def test_loader_refuses_after_target_only_commit_without_explicit_approval(
    tmp_path: Path,
) -> None:
    from scripts.load_dynastyprocess_archive import load_dynastyprocess_archive

    repo = _init_repo(tmp_path, "after-only")
    _write_ids(repo)
    _write_values(repo, scrape_date="2021-09-09", qb_value=4200, wr_value=3300)
    _commit(repo, when="2021-09-09", message="only after target")

    stats = load_dynastyprocess_archive(
        repo_path=repo,
        target_dates=["2021-09-08"],
        db_path=tmp_path / "snapshots.db",
    )

    target = stats["targets"]["2021-09-08"]
    assert target["status"] == "unavailable"
    assert target["rows_written"] == 0
    assert "after_target_commit_disallowed" in target["findings"]
    assert MarketSnapshotStore(db_path=tmp_path / "snapshots.db").get_snapshot(
        "2021-09-08"
    ) == []


def test_loader_skips_missing_clean_commit_without_snapshot_store_write(
    tmp_path: Path,
) -> None:
    from scripts.load_dynastyprocess_archive import load_dynastyprocess_archive

    repo = _init_repo(tmp_path, "out-of-window")
    _write_ids(repo)
    _write_values(repo, scrape_date="2021-08-01", qb_value=4100, wr_value=3200)
    _commit(repo, when="2021-08-01", message="outside window")

    stats = load_dynastyprocess_archive(
        repo_path=repo,
        target_dates=["2021-09-08"],
        db_path=tmp_path / "snapshots.db",
    )

    target = stats["targets"]["2021-09-08"]
    assert target["status"] == "unavailable"
    assert target["rows_written"] == 0
    assert "no_on_or_before_commit_in_window" in target["findings"]
    assert MarketSnapshotStore(db_path=tmp_path / "snapshots.db").get_snapshot(
        "2021-09-08"
    ) == []


def test_loader_skips_malformed_non_int_value_without_crashing(tmp_path: Path) -> None:
    # Codex F1: malformed external value_2qb must skip (fail closed), not crash the
    # loader before the adapter's int gate — same data-corruption boundary as W1.4.
    from scripts.load_dynastyprocess_archive import load_dynastyprocess_archive

    repo = _init_repo(tmp_path, "malformed-value")
    _write_ids(repo)
    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "value_2qb,scrape_date,fp_id\n"
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,not-int,2021-09-06,1001\n"
        "Active Wideout,WR,CIN,24,2020,40,40,WR14,3200,3300,2021-09-06,1002\n"
    )
    _commit(repo, when="2021-09-06", message="malformed qb value")
    db_path = tmp_path / "snapshots.db"

    stats = load_dynastyprocess_archive(
        repo_path=repo,
        target_dates=["2021-09-08"],
        db_path=db_path,
    )

    target = stats["targets"]["2021-09-08"]
    assert target["status"] == "loaded"
    assert target["malformed_rows_skipped"] == 1
    assert target["adapter_rows_emitted"] == 1  # only the valid WR
    assert target["rows_written"] == 1
    rows = MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08")
    assert {r["sleeper_id"] for r in rows} == {"sleeper_wr_active"}
    assert {r["value"] for r in rows} == {3300}


def test_loader_fails_closed_when_value_2qb_column_missing(tmp_path: Path) -> None:
    # Codex F2: if the required value_2qb column is absent globally (schema drift),
    # the loader must fail closed for that target — unavailable, no partial write —
    # not crash on KeyError. Step-5b is the write boundary consuming external content.
    from scripts.load_dynastyprocess_archive import load_dynastyprocess_archive

    repo = _init_repo(tmp_path, "missing-value-col")
    _write_ids(repo)
    (repo / "files" / "values.csv").write_text(
        "player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,"
        "scrape_date,fp_id\n"  # value_2qb column absent
        "Old Quarterback,QB,PIT,39,2004,80,75,QB28,2500,2021-09-06,1001\n"
    )
    _commit(repo, when="2021-09-06", message="missing value_2qb column")
    db_path = tmp_path / "snapshots.db"

    stats = load_dynastyprocess_archive(
        repo_path=repo,
        target_dates=["2021-09-08"],
        db_path=db_path,
    )

    target = stats["targets"]["2021-09-08"]
    assert target["status"] == "unavailable"
    assert "value_2qb_missing" in target["findings"]
    assert target["rows_written"] == 0
    assert MarketSnapshotStore(db_path=db_path).get_snapshot("2021-09-08") == []
