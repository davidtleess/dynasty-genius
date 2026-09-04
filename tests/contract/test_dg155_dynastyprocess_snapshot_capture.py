"""DG-155 RED: capture the annual consensus snapshot from its GPL-3.0 archive.

The only evidence that a free consensus ranking orders players better than Engine B rests on
four files: `app/data/backtest/qb_validation/raw/dp_values/values_{2021..2024}-09-08.csv`.

**Two premises of the filing did not survive verification, and these tests encode what is
actually true.** The four files were extracted from the git history of
`github.com/dynastyprocess/data` (GPL-3.0, read-only clone, David-signed-off per
`scripts/verify_dynastyprocess_source.py`), NOT downloaded on the day:

  * **There is no hard deadline.** Git history is immutable and reaches back to 2019 (361
    commits touching `files/values.csv`), so a 2026-09-08 snapshot captured in October is the
    same bytes as one captured on the day. Verified end to end: extracting the nearest commit
    on-or-before 2024-09-08 (`1f17c551`, committed 2024-09-06) reproduces the stored
    `values_2024-09-08.csv` BYTE FOR BYTE.
  * **2025 is not a permanent gap.** A commit exists at 2025-09-05 — exactly what the
    on-or-before-within-7-days rule selects for a 2025-09-08 target. The series can go from
    four points to five today.

These tests pin the SELECTION RULE (pure, no network) and the file shape against a real
stored snapshot. The rule is the load-bearing part: pick the commit nearest the target within
±7 days, PREFERRING on-or-before, because a commit after the target would leak information the
comparison exists to hold constant.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.dynasty_genius.sources.dynastyprocess_snapshot import (
    SNAPSHOT_COLUMNS,
    SOURCE_LICENSE,
    SOURCE_URL,
    NoCommitInWindow,
    select_snapshot_commit,
    validate_snapshot_columns,
)


def _c(iso: str, sha: str = "x"):
    return {"sha": sha, "committed": date.fromisoformat(iso)}


# ── the selection rule ───────────────────────────────────────────────────────────────


def test_an_exact_hit_on_the_target_date_wins() -> None:
    chosen = select_snapshot_commit(
        [_c("2023-09-01", "early"), _c("2023-09-08", "exact"), _c("2023-09-12", "late")],
        target=date(2023, 9, 8),
    )
    assert chosen["sha"] == "exact"


def test_on_or_before_is_preferred_even_when_a_later_commit_is_nearer() -> None:
    """A commit AFTER the target carries roster news the comparison holds constant. Two days
    late must lose to three days early."""
    chosen = select_snapshot_commit(
        [_c("2024-09-05", "before"), _c("2024-09-10", "after")], target=date(2024, 9, 8)
    )
    assert chosen["sha"] == "before"


def test_among_several_on_or_before_the_closest_wins() -> None:
    chosen = select_snapshot_commit(
        [_c("2024-08-30", "far"), _c("2024-09-06", "near"), _c("2024-09-01", "mid")],
        target=date(2024, 9, 8),
    )
    assert chosen["sha"] == "near"


def test_a_later_commit_is_used_only_when_nothing_precedes_the_target() -> None:
    chosen = select_snapshot_commit([_c("2024-09-11", "after")], target=date(2024, 9, 8))
    assert chosen["sha"] == "after"


def test_nothing_within_the_window_refuses_rather_than_reaching_further() -> None:
    """Widening the window silently is how a snapshot stops being comparable."""
    with pytest.raises(NoCommitInWindow):
        select_snapshot_commit([_c("2024-08-01"), _c("2024-10-01")], target=date(2024, 9, 8))


def test_the_window_is_seven_days_on_each_side() -> None:
    assert select_snapshot_commit([_c("2024-09-01", "edge")], target=date(2024, 9, 8))["sha"] == "edge"
    with pytest.raises(NoCommitInWindow):
        select_snapshot_commit([_c("2024-08-31")], target=date(2024, 9, 8))


# ── the file shape, pinned against a real stored snapshot ────────────────────────────


def test_the_expected_columns_match_the_2024_snapshot_on_disk() -> None:
    """If the upstream schema drifts, the capture must fail rather than write a file that
    silently is not the same object as the other four."""
    from pathlib import Path

    stored = (
        Path(__file__).resolve().parents[2]
        / "app/data/backtest/qb_validation/raw/dp_values/values_2024-09-08.csv"
    )
    header = stored.read_text().splitlines()[0]
    columns = [c.strip('"') for c in header.split(",")]
    assert columns == list(SNAPSHOT_COLUMNS)


def test_a_snapshot_missing_the_load_bearing_column_is_refused() -> None:
    columns = [c for c in SNAPSHOT_COLUMNS if c != "value_2qb"]
    with pytest.raises(ValueError, match="value_2qb"):
        validate_snapshot_columns(columns)


def test_an_upstream_schema_that_gained_a_column_is_still_accepted() -> None:
    """Additive drift is not a reason to refuse: the comparison reads named columns."""
    validate_snapshot_columns([*SNAPSHOT_COLUMNS, "some_new_upstream_column"])


# ── provenance is not optional ───────────────────────────────────────────────────────


def test_the_source_and_licence_are_recorded_in_code_not_folklore() -> None:
    assert SOURCE_URL == "https://github.com/dynastyprocess/data"
    assert SOURCE_LICENSE == "GPL-3.0"


# ── the producer: run-scoped, idempotent, and it never clobbers evidence ─────────────


def _runner():
    import importlib

    return importlib.import_module("scripts.capture_dynastyprocess_snapshot")


def _fake_archive(monkeypatch, runner, *, csv_text: str, sha="abc1234", committed="2025-09-05"):
    monkeypatch.setattr(
        runner, "_commits_touching_values",
        lambda repo: [{"sha": sha, "committed": date.fromisoformat(committed)}],
    )
    monkeypatch.setattr(runner, "_file_at_commit", lambda repo, sha_, path: csv_text)
    monkeypatch.setattr(runner, "_ensure_clone", lambda repo_path, work_dir: "REPO")


_CSV = (
    '"player","pos","team","age","draft_year","ecr_1qb","ecr_2qb","ecr_pos",'
    '"value_1qb","value_2qb","scrape_date","fp_id"\n'
    '"A Player","WR","CIN",24.5,2021,1.7,7.7,2.2,10089,8762,"2025-09-05","19788"\n'
)


def test_the_capture_writes_the_snapshot_and_its_provenance(tmp_path, monkeypatch) -> None:
    import json

    runner = _runner()
    _fake_archive(monkeypatch, runner, csv_text=_CSV)

    result = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    assert result["status"] == "ok"
    snapshot = tmp_path / "values_2025-09-08.csv"
    assert snapshot.read_text() == _CSV
    provenance = json.loads((tmp_path / "values_2025-09-08.provenance.json").read_text())
    assert provenance["source_license"] == "GPL-3.0"
    assert provenance["source_url"] == "https://github.com/dynastyprocess/data"
    assert provenance["commit_sha"] == "abc1234"
    assert provenance["commit_date"] == "2025-09-05"
    assert provenance["days_from_target"] == -3
    assert provenance["sha256"]
    assert provenance["fetched_at"]
    assert provenance["access_method"].startswith("read-only git clone")


def test_re_running_the_capture_is_a_no_op_not_a_rewrite(tmp_path, monkeypatch) -> None:
    runner = _runner()
    _fake_archive(monkeypatch, runner, csv_text=_CSV)

    first = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")
    stamp = (tmp_path / "values_2025-09-08.csv").stat().st_mtime_ns
    second = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    assert first["status"] == "ok"
    assert second["status"] == "noop"
    assert second["noop_reason"] == "already_captured_identical"
    assert (tmp_path / "values_2025-09-08.csv").stat().st_mtime_ns == stamp


def test_a_changed_upstream_file_refuses_rather_than_overwriting_the_archive(
    tmp_path, monkeypatch
) -> None:
    """These files ARE the evidence. If upstream ever revises a historical commit, the capture
    must say so loudly rather than silently replace a snapshot other results were computed on."""
    runner = _runner()
    _fake_archive(monkeypatch, runner, csv_text=_CSV)
    runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    revised = _CSV.replace("8762", "9999")
    _fake_archive(monkeypatch, runner, csv_text=revised)
    result = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    assert result["status"] == "failed"
    assert result["failure_reason"] == "existing_snapshot_differs"
    assert (tmp_path / "values_2025-09-08.csv").read_text() == _CSV, "the archive is untouched"


def test_a_snapshot_whose_schema_lost_a_column_is_refused(tmp_path, monkeypatch) -> None:
    runner = _runner()
    broken = _CSV.replace('"value_2qb",', "").replace(",8762", "")
    _fake_archive(monkeypatch, runner, csv_text=broken)

    result = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    assert result["status"] == "failed"
    assert "value_2qb" in result["failure_reason"]
    assert not (tmp_path / "values_2025-09-08.csv").exists()


def test_no_commit_in_the_window_fails_named_rather_than_reaching_further(
    tmp_path, monkeypatch
) -> None:
    runner = _runner()
    _fake_archive(monkeypatch, runner, csv_text=_CSV, committed="2025-08-01")

    result = runner.capture(year=2025, out_dir=tmp_path, work_dir=tmp_path / "work")

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no_commit_in_window"
