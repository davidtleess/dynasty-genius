"""DG-134 RED: the capture's derived training cutoff reads the season column the table has.

The forward capture records, in the provenance subset that feeds ``provenance_hash``, the
last season the Engine B model was trained through — derived from the feature table as
the max ``feature_season`` among ``training_eligible`` rows. Until DG-134 the derivation
read a ``season`` column the live runtime table (``engine_b_features_runtime.csv``, 44
columns) has never had; the ``KeyError`` was swallowed and the capture wrote
``{"value": null, "status": "derived"}`` every morning — a blank labelled as a finding.
The driver-test fixture carried BOTH spellings, which is why no test ever noticed.

These tests pin:
  * a table with ``feature_season`` and eligible rows derives the cutoff — the max over
    ELIGIBLE rows only (an ineligible 2025 inference row does not move it);
  * the column names come from the shared partition module, and the eligibility flag is
    read through its normaliser (a ``1``/``0``-typed writer must not read as "no rows");
  * a table with no ``feature_season`` column, no ``training_eligible`` column, or an
    eligible row whose season cannot be read is REFUSED with the bare token
    ``capture_training_cutoff_underivable`` — never ``None`` under a "derived" label;
  * the old ``season`` spelling is refused too (one column name, the assembler's — a
    fallback spelling is exactly the leniency that hid this for months);
  * a table whose eligibility column is present but carries no eligible row still
    derives ``None`` — there is nothing to derive from, so the null is honest;
  * the driver turns the refusal into its own aborted report before anything is
    appended; the legacy in-place refresh aborts with the token at its pre-refresh hash
    site, and at the post-refresh site restores a pair it had already mutated on disk.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.capture import model_forward_capture_driver as driver
from src.dynasty_genius.capture.model_forward_capture_driver import (
    TRAINING_CUTOFF_UNDERIVABLE,
    TrainingCutoffUnderivable,
    capture_model_pvo_snapshot,
)
from src.dynasty_genius.features import inference_partition as ip
from tests.contract import test_pvo_refresh_runner as refresh_fixtures
from tests.contract.test_model_forward_capture_driver import (
    COVERAGE_PATH,
    ENGINE_B_FEATURE_CSV_PATH,
    PVO_PATH,
    _artifact_bytes,
    _fixture_feature_source,
    _now,
    _reader,
)

_HEADER = b"player_id,feature_season,position,training_eligible,snap_share\n"
# An eligible window that ends in 2023 plus the 2025 inference row: the cutoff is 2023.
_LIVE_SHAPE = (
    _HEADER
    + b"00-A,2022,RB,True,0.50\n"
    + b"00-B,2023,RB,True,0.60\n"
    + b"00-C,2025,RB,False,0.71\n"
)


# ── the derivation itself ────────────────────────────────────────────────────────────


def test_the_cutoff_is_the_max_feature_season_over_eligible_rows_only() -> None:
    assert driver._derived_training_cutoff(_LIVE_SHAPE) == 2023


def test_the_column_names_are_the_partition_modules_not_bare_literals() -> None:
    source = Path(driver.__file__).read_text()
    derivation = source[source.index("def _derived_training_cutoff") :]
    derivation = derivation[: derivation.index("\ndef ")]
    assert '"season"' not in derivation
    assert '"feature_season"' not in derivation
    assert '"training_eligible"' not in derivation
    assert "SEASON_COLUMN" in derivation and "ELIGIBLE_COLUMN" in derivation
    assert ip.SEASON_COLUMN == "feature_season"


@pytest.mark.parametrize("spelling", ["1", "1.0", "TRUE", "True"])
def test_the_eligibility_flag_is_read_through_the_shared_normaliser(
    spelling: str,
) -> None:
    table = (
        _HEADER + f"00-A,2021,RB,{spelling},0.5\n".encode() + b"00-C,2025,RB,0,0.7\n"
    )
    assert driver._derived_training_cutoff(table) == 2021


@pytest.mark.parametrize(
    "table",
    [
        pytest.param(
            b"player_id,position,training_eligible\n00-A,RB,True\n",
            id="no_feature_season_column",
        ),
        pytest.param(
            b"player_id,season,position,training_eligible\n00-A,2023,RB,True\n",
            id="old_season_spelling_is_refused_not_tolerated",
        ),
        pytest.param(
            b"player_id,feature_season,position\n00-A,2023,RB\n",
            id="no_training_eligible_column",
        ),
        pytest.param(
            _HEADER + b"00-A,,RB,True,0.5\n00-B,2023,RB,True,0.6\n",
            id="an_eligible_row_with_a_blank_season",
        ),
        pytest.param(
            _HEADER + b"00-A,2023.5,RB,True,0.5\n",
            id="an_eligible_row_with_a_non_integer_season",
        ),
    ],
)
def test_an_underivable_cutoff_is_refused_with_the_bare_token(table: bytes) -> None:
    with pytest.raises(TrainingCutoffUnderivable) as excinfo:
        driver._derived_training_cutoff(table)
    assert str(excinfo.value) == TRAINING_CUTOFF_UNDERIVABLE
    assert TRAINING_CUTOFF_UNDERIVABLE == "capture_training_cutoff_underivable"


def test_a_table_with_no_eligible_row_derives_none_because_there_is_nothing_to_derive() -> (
    None
):
    inference_only = _HEADER + b"00-C,2025,RB,False,0.71\n"
    assert driver._derived_training_cutoff(inference_only) is None


def test_an_empty_table_derives_none() -> None:
    assert driver._derived_training_cutoff(b"") is None


# ── the driver: refusal → its own aborted report, nothing appended ────────────────────


def _capture(tmp_path: Path, feature_csv: bytes) -> tuple[dict, Path]:
    db_path = tmp_path / "model_forward.db"
    report = capture_model_pvo_snapshot(
        db_path=db_path,
        report_path=tmp_path / "latest_report.json",
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(
            _artifact_bytes({ENGINE_B_FEATURE_CSV_PATH: feature_csv})
        ),
        now_fn=_now(),
        git_sha_fn=lambda: "docs-only-sha",
        feature_source=_fixture_feature_source(),
    )
    return report, db_path


def test_the_driver_records_the_real_cutoff_in_both_provenance_places(
    tmp_path: Path,
) -> None:
    # The fixture table has ONLY the live spelling — no `season` column to fall back on.
    report, _ = _capture(tmp_path, _LIVE_SHAPE)

    assert report["status"] == "ok"
    assert report["provenance"]["engine_b_derived_training_cutoff"] == {
        "value": 2023,
        "status": "derived",
    }
    assert report["provenance"]["feature_csv"]["max_training_season"] == 2023


def test_the_hashed_subset_carries_the_real_cutoff_so_null_and_2023_never_collide(
    tmp_path: Path,
) -> None:
    pvo = _reader(_artifact_bytes())(PVO_PATH)
    subset = driver.resolve_provenance_subset(
        json.loads(pvo),
        read_artifact=_reader(
            _artifact_bytes({ENGINE_B_FEATURE_CSV_PATH: _LIVE_SHAPE})
        ),
        feature_source=_fixture_feature_source(),
    )
    assert subset["engine_b"]["derived_training_cutoff"] == {
        "value": 2023,
        "status": "derived",
    }


def test_the_driver_aborts_with_the_token_and_appends_nothing(tmp_path: Path) -> None:
    season_less = b"player_id,position,training_eligible,snap_share\n00-A,RB,True,0.5\n"
    report, db_path = _capture(tmp_path, season_less)

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == TRAINING_CUTOFF_UNDERIVABLE
    assert report["decision_supported"] is False
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            ]
            for table in tables:
                assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


# ── the legacy in-place refresh: refusal → restore + abort ─────────────────────────────


def test_the_legacy_refresh_aborts_with_the_token_at_the_pre_refresh_hash_site(
    tmp_path: Path,
) -> None:
    runner = importlib.import_module("scripts.run_pvo_refresh")
    pvo, coverage = refresh_fixtures._write_pair(tmp_path)
    original_pvo, original_coverage = pvo.read_bytes(), coverage.read_bytes()
    lineage = refresh_fixtures._lineage_bytes()
    lineage[refresh_fixtures.ENGINE_B_FEATURE_CSV_PATH] = (
        b"player_id,position,training_eligible\n00-A,RB,True\n"
    )

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized == pvo:
            return pvo.read_bytes()
        if normalized == coverage:
            return coverage.read_bytes()
        if normalized in lineage:
            return lineage[normalized]
        raise FileNotFoundError(str(normalized))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_fn,
        capture_fn=None,
        read_artifact=read_artifact,
        feature_source=refresh_fixtures._fixture_feature_source(),
    )

    assert report["status"] == "aborted"
    assert report["aborted_reason"] == TRAINING_CUTOFF_UNDERIVABLE
    assert report["restored_from_backup"] is True
    # The refusal lands BEFORE refresh_fn runs, so the pair was never dirtied: this
    # pins "nothing was touched", not the restore itself. The restore is measured by
    # the post-refresh test below (and, for non-DG-134 failures, by
    # test_pvo_refresh_runner's test_refresh_failure_restores_both_artifacts_*).
    assert pvo.read_bytes() == original_pvo
    assert coverage.read_bytes() == original_coverage


def test_the_legacy_refresh_restores_a_dirtied_pair_when_the_cutoff_dies_after_the_refresh(
    tmp_path: Path,
) -> None:
    """The POST-refresh hash site: the pair IS on disk, mutated, when the refusal lands.

    This is the site where a restore actually has something to undo — a refresh that
    republishes a feature table the cutoff cannot be derived from. The pre-refresh test
    above cannot reach it, and before DG-134 nothing in the repo exercised it.
    """
    runner = importlib.import_module("scripts.run_pvo_refresh")
    pvo, coverage = refresh_fixtures._write_pair(tmp_path)
    original_pvo, original_coverage = pvo.read_bytes(), coverage.read_bytes()
    lineage = refresh_fixtures._lineage_bytes()
    good_table = lineage[refresh_fixtures.ENGINE_B_FEATURE_CSV_PATH]
    season_less = b"player_id,position,training_eligible\n00-A,RB,True\n"
    refreshed = False

    def refresh_fn(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
        """Publish a new pair AND swap in a feature table with no season column."""
        nonlocal refreshed
        pvo_artifact_path.write_text(
            pvo_artifact_path.read_text().replace("98.5", "99.1")
        )
        coverage_artifact_path.write_text(
            coverage_artifact_path.read_text().replace("98.5", "99.1")
        )
        refreshed = True

    def read_artifact(path: Path | str) -> bytes:
        normalized = Path(path)
        if normalized == pvo:
            return pvo.read_bytes()
        if normalized == coverage:
            return coverage.read_bytes()
        if normalized == refresh_fixtures.ENGINE_B_FEATURE_CSV_PATH:
            return season_less if refreshed else good_table
        if normalized in lineage:
            return lineage[normalized]
        raise FileNotFoundError(str(normalized))

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_fn,
        capture_fn=None,
        read_artifact=read_artifact,
        feature_source=refresh_fixtures._fixture_feature_source(),
    )

    assert refreshed is True, "the refresh must have run for this to test a restore"
    assert report["status"] == "aborted"
    assert report["aborted_reason"] == TRAINING_CUTOFF_UNDERIVABLE
    assert report["restored_from_backup"] is True
    # The pair really was mutated on disk and really was put back.
    assert pvo.read_bytes() == original_pvo
    assert coverage.read_bytes() == original_coverage
    assert b"99.1" not in pvo.read_bytes()
    assert b"99.1" not in coverage.read_bytes()
