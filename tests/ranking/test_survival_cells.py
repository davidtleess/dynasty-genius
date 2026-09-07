"""DG-178 — reading the DG-164 retention cells without changing what they mean.

The canonical file says three things in its own definition block: R is unconditional,
a margin below 1.0 is not worth zero, and a cell is suppressed rather than borrowed. The
loader enforces the first by refusing any file that does not carry that warning — nine cell
files with three semantics existed at once, and the wrong one was picked once already.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "retention_cells_fixture.json"


def _cells():
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    return RetentionCells.load(FIXTURE)


def test_loader_refuses_a_cell_file_without_the_unconditional_warning(tmp_path) -> None:
    """A superseded file with different semantics must not load by accident."""
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    raw = json.loads(FIXTURE.read_text())
    del raw["definition"]["WARNING_double_count"]
    bad = tmp_path / "cells.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="unconditional"):
        RetentionCells.load(bad)


def test_loader_records_provenance_of_what_it_read() -> None:
    c = _cells()
    assert c.source_path == FIXTURE
    assert len(c.source_sha256) == 64
    assert c.horizons == 5
    assert c.bar_ranks == {"QB": 37, "RB": 45, "WR": 71, "TE": 21}


def test_age_bands_match_the_cell_file() -> None:
    from src.dynasty_genius.ranking.survival_cells import age_band

    assert age_band(21) == "<=23"
    assert age_band(23) == "<=23"
    assert age_band(24) == "24-25"
    assert age_band(27) == "26-27"
    assert age_band(29) == "28-29"
    assert age_band(31) == "30-31"
    assert age_band(32) == "32+"
    assert age_band(38) == "32+"


def test_a_populated_cell_returns_its_ratios_in_horizon_order() -> None:
    hit = _cells().lookup("WR", age=25, margin=1.55)
    assert hit.status == "cell"
    assert hit.ratios == (0.9, 0.8, 0.7, 0.6, 0.5)
    assert hit.key == ("WR", "24-25", "m2 (d5)")
    assert hit.n == 40


def test_a_suppressed_cell_returns_the_files_own_reason_and_no_ratios() -> None:
    """DG-176's shape: a young quarterback lands on a thin bin. The answer is the reason the
    file gives, never a neighbour's numbers."""
    hit = _cells().lookup("QB", age=22, margin=1.3)
    assert hit.status == "suppressed"
    assert hit.ratios is None
    assert "n=10 < 12" in hit.reason


def test_a_margin_with_no_cell_at_all_is_a_stated_absence() -> None:
    """The fixture has no WR 32+ cell; the real file has bins the panel never populated."""
    hit = _cells().lookup("WR", age=33, margin=1.55)
    assert hit.status == "absent"
    assert hit.ratios is None
    assert "no cell" in hit.reason


def test_an_unknown_age_cannot_be_binned() -> None:
    hit = _cells().lookup("WR", age=None, margin=1.55)
    assert hit.status == "absent"
    assert "age" in hit.reason


def test_edges_form_a_complete_partition_so_every_margin_lands_once() -> None:
    c = _cells()
    for m in (0.0, 0.5, 1.2, 1.5, 1.66, 2.4, 10.0):
        hit = c.lookup("WR", age=25, margin=m)
        assert hit.status in ("cell", "absent", "suppressed")
    # Half-open bins: the upper edge belongs to the next bin.
    assert c.lookup("WR", age=25, margin=1.66).key != ("WR", "24-25", "m2 (d5)")
    assert c.lookup("WR", age=25, margin=1.5).key == ("WR", "24-25", "m2 (d5)")


def test_fractional_ages_follow_the_cells_right_inclusive_cut() -> None:
    """The cells were fitted on exact age at September 1 with
    pd.cut(age, [19, 23, 25, 27, 29, 31, 45]) — RIGHT-inclusive, so 23.5 is '24-25' and 31.5
    is '32+' (preserved rebuild_fixed.py:52). Before this fix every fractional age between
    bands fell through to '32+'. Ages outside (19, 45] were excluded from the panel and
    cannot be binned."""
    from src.dynasty_genius.ranking.survival_cells import age_band

    assert age_band(23.0) == "<=23"
    assert age_band(23.5) == "24-25"
    assert age_band(25.0) == "24-25"
    assert age_band(25.5) == "26-27"
    assert age_band(27.5) == "28-29"
    assert age_band(29.5) == "30-31"
    assert age_band(31.0) == "30-31"
    assert age_band(31.5) == "32+"
    assert age_band(19.2) == "<=23"
    assert age_band(19.0) is None
    assert age_band(45.5) is None


def test_a_non_finite_age_cannot_be_binned() -> None:
    from src.dynasty_genius.ranking.survival_cells import age_band

    assert age_band(float("nan")) is None
    assert age_band(float("inf")) is None
