"""DG-140 — the age verdict on a row must be true of the age printed beside it.

DG-139 made the universe artifact serve Sleeper's current age. The evidence
tokens beside that age (``top_drivers`` / ``risk_flags``) were still the ones
``pvo_assembler`` computed at the FEATURE-season age, so a card could read
"age 26" above "Age is on his side — he is years away from the usual decline"
about a receiver two years from the cliff. Measured on the 2026-09-02 artifact:
583 rows carry an age verdict and 97 of them contradicted the served age.

The roster audit was never affected — it recomputes drivers from the live
Sleeper row (``roster_auditor.py:198,217``) — which is why the card and the
roster row disagreed about Garrett Wilson.
"""
from __future__ import annotations

from src.dynasty_genius.age_cliff import (
    AGE_DRIVER_TOKENS,
    PAST_CLIFF_TOKEN,
    cliff_driver,
    restate_age_verdict,
)
from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch
from tests.contract.test_served_team_is_sleepers import (
    _engine_b_pvo,
    _served,
    _snapshot,
    _snapshot_player,
)

WITHIN_TWO = "age_within_two_years_of_position_cliff"
NOT_NEAR = "age_not_near_position_cliff"
AT_CLIFF = "age_at_position_cliff"


def test_the_rule_is_the_one_the_roster_audit_applies():
    """One rule, one place: the shared module must agree with the live surface.

    ``roster_auditor`` imports its constants from ``age_cliff``; this pins the
    banding itself, so the two surfaces cannot drift apart silently.
    """
    from app.services.roster_auditor import CLIFF_AGES, SIGNAL_DRIVERS, audit_player

    assert CLIFF_AGES["WR"] == 28
    assert set(SIGNAL_DRIVERS.values()) == set(AGE_DRIVER_TOKENS)
    for position, age in (("WR", 26.0), ("WR", 25.0), ("RB", 27.0), ("TE", 30.0), ("QB", 31.0)):
        live = audit_player({"position": position, "age": age, "full_name": "x"})
        assert live["signal_drivers"] == [cliff_driver(position, age)]


def test_a_receiver_who_turned_26_is_no_longer_told_his_age_is_fine():
    """Garrett Wilson's case: the feature age said 25, Sleeper says 26."""
    assert cliff_driver("WR", 25.0) == NOT_NEAR
    assert cliff_driver("WR", 26) == WITHIN_TWO

    drivers, flags = restate_age_verdict([NOT_NEAR, "usage_share_rising"], [], "WR", 26)
    assert drivers == [WITHIN_TWO, "usage_share_rising"], "the verdict is restated in place"
    assert flags == []


def test_a_player_who_crossed_his_cliff_gains_the_risk_flag():
    """33 live rows are past their cliff at the served age and carried no flag."""
    drivers, flags = restate_age_verdict([AT_CLIFF], ["injury_history"], "RB", 27)
    assert drivers == [PAST_CLIFF_TOKEN]
    assert flags == ["injury_history", PAST_CLIFF_TOKEN]


def test_a_player_who_moved_back_off_his_cliff_loses_the_risk_flag():
    """The flag must track the verdict in BOTH directions, or it becomes a ratchet."""
    drivers, flags = restate_age_verdict(
        [PAST_CLIFF_TOKEN], ["injury_history", PAST_CLIFF_TOKEN], "RB", 25
    )
    assert drivers == [WITHIN_TWO]
    assert flags == ["injury_history"]


def test_a_verdict_is_never_invented_for_a_row_that_had_none():
    """A row the model gave no age verdict keeps none — restating is not asserting."""
    assert restate_age_verdict(None, None, "WR", 26) == (None, None)
    assert restate_age_verdict([], [], "WR", 26) == ([], [])
    assert restate_age_verdict(["usage_share_rising"], [], "WR", 26) == (
        ["usage_share_rising"],
        [],
    )


def test_a_stale_verdict_is_dropped_when_none_can_be_derived():
    """Position drift (a WR now served as CB) must not keep asserting the old claim."""
    drivers, flags = restate_age_verdict([NOT_NEAR, "x"], [], "CB", 26)
    assert drivers == ["x"]
    drivers, _ = restate_age_verdict([NOT_NEAR], None, "WR", None)
    assert drivers == []


def test_the_batch_restates_the_verdict_with_the_age_it_serves():
    """End to end: the artifact row's verdict is true of the artifact row's age."""
    pvo = {**_engine_b_pvo("8146", nfl_team="NYJ"), "age": 25.0, "position": "WR"}
    pvo["top_drivers"] = [NOT_NEAR]
    pvo["risk_flags"] = []
    snapshot = _snapshot(_snapshot_player("8146", {"age": 26, "team": "NYJ", "position": "WR"}))

    row = _served(build_universe_pvo_batch(snapshot, active_pvos=[pvo]), "8146")

    assert row["player"]["age"] == 26
    assert row["top_drivers"] == [WITHIN_TWO]
    assert cliff_driver(row["player"]["position"], row["player"]["age"]) == row["top_drivers"][0]


def test_the_batch_leaves_the_verdict_alone_when_sleeper_has_no_age():
    """No Sleeper age -> the model's age is served (DG-139), so its verdict still stands."""
    pvo = {**_engine_b_pvo("8146", nfl_team="NYJ"), "age": 25.0, "position": "WR"}
    pvo["top_drivers"] = [NOT_NEAR]
    pvo["risk_flags"] = []
    snapshot = _snapshot(_snapshot_player("8146", {"age": None, "team": "NYJ", "position": "WR"}))

    row = _served(build_universe_pvo_batch(snapshot, active_pvos=[pvo]), "8146")

    assert row["player"]["age"] == 25.0
    assert row["top_drivers"] == [NOT_NEAR], "the served age is the model's, so its verdict is true"


def test_a_restated_flag_takes_its_counter_argument_with_it():
    """The counter-argument is a FUNCTION of risk_flags, so it cannot be left behind.

    ``pvo_assembler`` generates it at assembly time from the feature-season flags
    (``counter_arguments.py:15`` makes ``age_past_position_cliff`` the priority-1
    branch). On the 33 live rows that GAIN that flag, the assembly-time argument
    was computed without it — 16 of them had no counter-argument at all, which
    Product Constitution Rule 4 forbids.
    """
    pvo = {**_engine_b_pvo("8146", nfl_team="NYJ"), "age": 25.0, "position": "RB"}
    pvo["top_drivers"] = [AT_CLIFF]
    pvo["risk_flags"] = []
    pvo["counter_argument"] = None
    snapshot = _snapshot(_snapshot_player("8146", {"age": 27, "team": "NYJ", "position": "RB"}))

    row = _served(build_universe_pvo_batch(snapshot, active_pvos=[pvo]), "8146")

    assert row["risk_flags"] == [PAST_CLIFF_TOKEN]
    assert row["counter_argument"] is not None, "Rule 4: the counter-argument is mandatory"
    assert "age cliff" in row["counter_argument"]


def test_an_untouched_row_keeps_the_producer_s_exact_counter_argument():
    """Regenerate only when the flags actually moved — never restate what did not change."""
    pvo = {**_engine_b_pvo("8146", nfl_team="NYJ"), "age": 26.0, "position": "WR"}
    pvo["top_drivers"] = [WITHIN_TWO]
    pvo["risk_flags"] = []
    pvo["counter_argument"] = "a string only the producer could have written"
    snapshot = _snapshot(_snapshot_player("8146", {"age": 26, "team": "NYJ", "position": "WR"}))

    row = _served(build_universe_pvo_batch(snapshot, active_pvos=[pvo]), "8146")

    assert row["counter_argument"] == "a string only the producer could have written"


def test_one_unusable_age_cannot_take_down_the_whole_artifact_build():
    """This runs inside the single build loop; a bad Sleeper age must degrade one row.

    ``sleeper_universe.py:245`` copies Sleeper's age with no coercion, so the batch
    is the first place arithmetic touches it. Aborting here would leave the morning
    with no artifact at all rather than 12,226 good rows.
    """
    from src.dynasty_genius.age_cliff import cliff_band

    assert cliff_band("WR", "not-an-age") is None
    assert cliff_band("WR", float("nan")) is None
    assert cliff_band("WR", "26") == "approaching_cliff", "a numeric string still works"
    assert cliff_band("WR", 26.9) == "approaching_cliff", "truncation, as audit_player does"


def test_a_past_cliff_verdict_carries_its_flag_onto_a_row_that_had_none():
    """risk_flags=None must not swallow the flag — the flag is what makes Rule 4 fire."""
    drivers, flags = restate_age_verdict([AT_CLIFF], None, "RB", 27)
    assert drivers == [PAST_CLIFF_TOKEN]
    assert flags == [PAST_CLIFF_TOKEN]
