"""DG-178 round 1 — the audit's denominators are every roster id, and nothing is overwritten.

Before this: identities missing from the artifact were recorded but excluded from the
coverage counts, and dictionaries keyed by Sleeper id silently kept the last duplicate.
"""
from __future__ import annotations

import pytest


def _row(sid, pos="WR", dvs=40.0, proj=8.0, clamped=False, engine="B"):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=sid, sleeper_id=sid, full_name=sid, position=pos, age=25,
                     dynasty_value_score=dvs, dvs_p90_ref=20.1, dvs_clamped=clamped, dvs_engine=engine,
                     projection_2y=proj, captured_at="x")


def test_reconciliation_counts_every_roster_id_including_those_absent_from_the_artifact() -> None:
    from src.dynasty_genius.ranking.audit_support import reconcile_roster

    rec = reconcile_roster(["a", "b", "ghost"], [_row("a"), _row("b"), _row("c")])
    assert rec.present_ids == ["a", "b"]
    assert rec.absent_ids == ["ghost"]
    assert rec.denominator == 3


def test_duplicate_sleeper_ids_in_the_artifact_are_refused_not_overwritten() -> None:
    from src.dynasty_genius.ranking.audit_support import reconcile_roster

    with pytest.raises(ValueError, match="duplicate"):
        reconcile_roster(["a"], [_row("a"), _row("a", pos="RB")])


def test_duplicate_ids_on_a_roster_are_refused() -> None:
    from src.dynasty_genius.ranking.audit_support import reconcile_roster

    with pytest.raises(ValueError, match="duplicate"):
        reconcile_roster(["a", "a"], [_row("a")])


def test_replacement_pool_census_shows_who_could_and_could_not_set_the_bar() -> None:
    """Best SCORED available is not best OBTAINABLE available: the unscored unrostered
    players are outside the pool by construction, and the census says how many."""
    from src.dynasty_genius.ranking.audit_support import replacement_pool_census

    rows = [_row("r1"), _row("f_ok"), _row("f_clamped", clamped=True), _row("f_noproj", proj=None, engine="A"),
            _row("f_unscored", dvs=None, proj=None, engine=None), _row("f_ok2", dvs=30.0)]
    c = replacement_pool_census(rows, rostered_ids={"r1"})["WR"]
    assert c["unrostered"] == 5
    assert c["scored"] == 4
    assert c["eligible"] == 2
    assert c["excluded_clamped"] == 1
    assert c["excluded_no_projection"] == 1
    assert c["excluded_unscored"] == 1
    assert c["eligible_ids"] == ["f_ok", "f_ok2"]


def test_a_roster_id_whose_artifact_row_is_outside_the_skill_population_is_labelled_not_lost() -> None:
    """Travis Hunter is rostered and the artifact lists him as DB, so he is outside the
    QB/RB/WR/TE population — a stated position fact, not a lost identity."""
    from src.dynasty_genius.ranking.audit_support import reconcile_roster

    rec = reconcile_roster(["a", "hunter", "ghost"], [_row("a")], other_positions={"hunter": "DB"})
    assert rec.present_ids == ["a"]
    assert rec.outside_population == {"hunter": "DB"}
    assert rec.absent_ids == ["ghost"]
    assert rec.denominator == 3
