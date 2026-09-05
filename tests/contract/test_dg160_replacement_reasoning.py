"""DG-160: the replacement level explains itself, from the LIVE lineup, so a wrong derivation shows.

The unbuilt second half of David's 2026-08-31 ranking ruling 5, in his words:

    "REPLACEMENT LEVEL — let the derived number stand and show the reasoning. Compute it as an
     order statistic from the real lineup structure. 'Replacement TE = the 12th-best TE,
     because your league starts 12.'"

The order-statistic half is in the code as ENGINE_B_VAR_THRESHOLDS. The reasoning half was
never built, and its absence cost a real constant: the receiver threshold's own comment
derives 53 from "12 x 3 slots = 36", a third receiver slot his league does not have. His
league starts two. On screen in August he would have caught it in a sentence.

⛔ THE TEST THIS MODULE HAS TO PASS TO BE WORTH ANYTHING: if the derivation were completely
wrong, would this look any different? A caption reading "replacement = 8.79 points a game"
fails — a wrong rank is invisible in it. So what is built here carries the slot arithmetic and
compares the shipped rank against the one his lineup implies, and says when they disagree.
That comparison is computed, never hard-coded: nothing here knows in advance that receiver is
the broken one.

⚠ It also has to be honest about what is NOT derivable. The dedicated slots are unambiguous.
The flex places are shared, and how they split between positions is behavioural rather than
structural — and it cannot be measured honestly today, because 52 daily snapshots are the same
lineups re-observed with two edits between them: one observation of 21 filled slots, not 1,091.
Pooling them would be pseudo-replication. That uncertainty goes on screen rather than behind a
round number.

This changes no constant and no number David already sees.
"""

from __future__ import annotations

from src.dynasty_genius.features.replacement_reasoning import (
    DerivationStatus,
    audit_shared_slot_budget,
    explain_replacement,
    starting_slots,
)

# His league, as the snapshot reads it.
HIS_LEAGUE = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX"] + ["BN"] * 11
TEAMS = 12


# ── reading the lineup, not the comment ──────────────────────────────────────────────


def test_the_starting_slots_come_from_the_roster_structure() -> None:
    slots = starting_slots(HIS_LEAGUE, teams=TEAMS)
    assert slots.dedicated == {"QB": 12, "RB": 24, "WR": 24, "TE": 12}
    assert slots.flex_pool == 24
    assert slots.superflex_pool == 12
    assert "BN" not in slots.dedicated


def test_bench_and_reserve_slots_are_not_starters() -> None:
    slots = starting_slots(["QB", "TE", "BN", "BN", "IR", "TAXI"], teams=10)
    assert slots.dedicated == {"QB": 10, "TE": 10}
    assert slots.flex_pool == 0


# ── the sentence David asked for ─────────────────────────────────────────────────────


def test_tight_end_reads_exactly_the_way_he_phrased_it() -> None:
    """His own example: 'Replacement TE = the 12th-best TE, because your league starts 12.'"""
    out = explain_replacement(
        position="TE", shipped_rank=13, roster_positions=HIS_LEAGUE, teams=TEAMS,
        replacement_ppg=8.99,
    )
    assert out["rank"] == 13
    assert out["points_per_game"] == 8.99
    assert "12" in out["reason"] and "tight end" in out["reason"].lower()
    assert out["shared_places_demanded"] == 0, "his TE rank assumes nothing about the flex"


def test_the_explanation_names_the_rank_the_reason_and_the_points() -> None:
    out = explain_replacement(
        position="QB", shipped_rank=25, roster_positions=HIS_LEAGUE, teams=TEAMS,
        replacement_ppg=12.91,
    )
    assert out["rank"] == 25 and out["points_per_game"] == 12.91
    assert out["reason"], "the reason is the whole point of the ruling"
    assert "superflex" in out["reason"].lower(), "a superflex league starts two QBs a team"


# ── the detector: a budget, needing no behavioural assumption ────────────────────────

SHIPPED_THRESHOLDS = {"QB": 25, "RB": 33, "WR": 53, "TE": 13}


def test_the_four_shipped_ranks_cannot_all_be_true_in_his_league() -> None:
    """The bug that motivated the ticket, caught without assuming anything about flex usage.

    A first design asked whether each rank was individually defensible and was far too
    permissive — letting every shared place go to one position makes almost any rank arguable.
    The question that bites is whether the four can hold at once, because they compete for one
    pool of shared places. Nothing here is told receiver is the broken one.
    """
    out = audit_shared_slot_budget(
        thresholds=SHIPPED_THRESHOLDS, roster_positions=HIS_LEAGUE, teams=TEAMS
    )
    assert out["available"] == 36, "24 flex + 12 superflex"
    assert out["demanded"] == 48
    assert out["over_subscribed_by"] == 12
    assert out["status"] is DerivationStatus.DISAGREES
    assert out["largest_demand"] == "WR"
    assert out["demands"]["WR"] == 28 and out["demands"]["TE"] == 0


def test_a_coherent_set_of_ranks_passes() -> None:
    """So the detector is not simply always angry."""
    out = audit_shared_slot_budget(
        thresholds={"QB": 25, "RB": 33, "WR": 33, "TE": 13},
        roster_positions=HIS_LEAGUE, teams=TEAMS,
    )
    assert out["status"] is DerivationStatus.AGREES
    assert out["over_subscribed_by"] == 0


def test_the_detector_fires_when_the_LEAGUE_changes_under_fixed_constants() -> None:
    """The failure mode it exists for: the constants stay, the lineup moves, nobody notices."""
    smaller = ["QB", "RB", "WR", "TE", "FLEX"] + ["BN"] * 10
    out = audit_shared_slot_budget(
        thresholds=SHIPPED_THRESHOLDS, roster_positions=smaller, teams=TEAMS
    )
    assert out["status"] is DerivationStatus.DISAGREES


def test_the_explanation_says_the_shortfall_in_plain_words() -> None:
    out = audit_shared_slot_budget(
        thresholds=SHIPPED_THRESHOLDS, roster_positions=HIS_LEAGUE, teams=TEAMS
    )
    assert "48" in out["explanation"] and "36" in out["explanation"]
    assert "receiver" in out["explanation"]


def test_a_position_row_carries_the_shared_places_its_rank_assumes() -> None:
    out = explain_replacement(
        position="WR", shipped_rank=53, roster_positions=HIS_LEAGUE, teams=TEAMS,
        replacement_ppg=8.79, thresholds=SHIPPED_THRESHOLDS,
    )
    assert out["shared_places_demanded"] == 28
    assert out["shared_places_available"] == 36
    assert out["status"] is DerivationStatus.DISAGREES


# ── honesty about what is not derivable ──────────────────────────────────────────────


def test_the_flex_share_is_disclosed_as_an_assumption_not_a_fact() -> None:
    out = explain_replacement(
        position="RB", shipped_rank=33, roster_positions=HIS_LEAGUE, teams=TEAMS,
        replacement_ppg=7.29,
    )
    assert out["flex_is_assumed"] is True
    assert "flex" in out["assumption"].lower()


def test_the_quarterback_rank_also_rests_on_an_assumption_and_says_so() -> None:
    """I expected quarterback to be assumption-free and it is not. Its rank of 25 needs all 12
    superflex places to hold quarterbacks. Measured on his league: 9 of 11 filled superflex
    slots do, and two hold a back and a receiver. So even the position that looks structural
    carries a behavioural premise, and the screen must say so."""
    out = explain_replacement(
        position="QB", shipped_rank=25, roster_positions=HIS_LEAGUE, teams=TEAMS,
        replacement_ppg=12.91,
    )
    assert out["shared_places_demanded"] == 12
    assert out["flex_is_assumed"] is True


def test_the_reason_never_states_a_slot_the_league_does_not_have() -> None:
    """The exact failure being fixed: the shipped comment says '12 x 3' for receivers."""
    for position in ("QB", "RB", "WR", "TE"):
        out = explain_replacement(
            position=position, shipped_rank=25, roster_positions=HIS_LEAGUE, teams=TEAMS,
            replacement_ppg=9.0,
        )
        assert "3 WR" not in out["reason"] and "three receiver" not in out["reason"].lower()
        assert str(out["dedicated"]) in out["reason"]


# ── it reaches the surface, or it is decoration ──────────────────────────────────────


def test_the_reasoning_reaches_the_roster_audit_response() -> None:
    """A derivation nothing displays is the failure this repo keeps producing: something that
    looks green while doing nothing. Pin that it is actually carried to David."""
    from app.api.routes.roster_audit_models import assemble_response

    out = assemble_response(
        {
            "players": [],
            "league": {"roster_positions": HIS_LEAGUE, "teams": TEAMS},
        }
    )
    assert len(out.replacement_reasoning) == 4
    by_position = {v.position: v for v in out.replacement_reasoning}
    assert set(by_position) == {"QB", "RB", "WR", "TE"}
    assert "tight end" in by_position["TE"].reason.lower()
    assert by_position["TE"].shared_places_assumed == 0
    # DG-159 corrected the receiver rank from 53 to 45, so the demand it makes on the
    # shared places falls from 28 to 20 and the four ranks now fit the 36 his league has.
    assert by_position["WR"].shared_places_assumed == 20
    assert by_position["WR"].points_per_game == 9.05, (
        "the sentence must quote the points a game the score is actually measured "
        "against, not a figure back-derived through a denominator it no longer uses"
    )

    assert out.replacement_budget is not None
    # DG-160 built this detector and it read "disagrees", over-subscribed by 12, with
    # receiver the largest demand. DG-159 corrected the two ranks it caught, so it now
    # reads "agrees" — the detector finding nothing is the fix landing, and this
    # assertion is what would catch a future rank that breaks the budget again.
    assert out.replacement_budget.status == "agrees"
    assert out.replacement_budget.over_subscribed_by == 0
    assert out.replacement_budget.demanded == out.replacement_budget.available == 36


def test_no_lineup_means_no_invented_explanation() -> None:
    """Without the league's own slots there is nothing to derive from, and inventing one is
    precisely the failure mode — a confident sentence resting on a slot structure nobody
    checked."""
    from app.api.routes.roster_audit_models import assemble_response

    out = assemble_response({"players": []})
    assert out.replacement_reasoning == []
    assert out.replacement_budget is None


def test_the_response_carries_no_new_player_number() -> None:
    """Anti-scope: this ticket changes no constant and no number David already sees."""
    from app.api.routes.roster_audit_models import assemble_response

    out = assemble_response(
        {"players": [], "league": {"roster_positions": HIS_LEAGUE, "teams": TEAMS}}
    )
    assert out.players == []
    assert out.decision_supported is False


def test_the_reader_points_at_where_the_daily_chain_actually_writes() -> None:
    """The failure I nearly shipped: the audit payload carries no league block at all, so the
    feature would have been silently empty in production while every unit test passed. The
    reader now falls back to the captured snapshot — so the PATH is the thing to pin, because
    a wrong one degrades to a blank panel rather than an error.

    Path-shape rather than existence: a ticket worktree deliberately has no league_runtime (it
    is per-worktree private, since producers write there), so asserting a snapshot exists would
    fail at the gate for the wrong reason.
    """
    from pathlib import Path

    from src.dynasty_genius.features.replacement_reasoning import LEAGUE_RUNTIME_ROOT

    repo_root = Path(__file__).resolve().parents[2]
    assert LEAGUE_RUNTIME_ROOT == repo_root / "app" / "data" / "league_runtime" / "runs"


def test_the_reader_finds_a_league_in_a_snapshot_shaped_directory(tmp_path) -> None:
    """Behaviour, against the real snapshot shape the chain writes."""
    import json

    from src.dynasty_genius.features.replacement_reasoning import load_league_structure

    run = tmp_path / "league-20260904T130046Z"
    run.mkdir()
    (run / "snapshot.json").write_text(
        json.dumps(
            {
                "captured_at": "2026-09-04T13:00:46Z",
                "league": {"roster_positions": HIS_LEAGUE},
                "rosters": [{"roster_id": i} for i in range(TEAMS)],
            }
        )
    )
    league = load_league_structure(tmp_path)
    assert league is not None
    assert league["teams"] == TEAMS
    assert league["roster_positions"] == HIS_LEAGUE


def test_the_newest_snapshot_wins_and_a_corrupt_one_is_skipped(tmp_path) -> None:
    import json

    from src.dynasty_genius.features.replacement_reasoning import load_league_structure

    old = tmp_path / "league-20260101T000000Z"
    old.mkdir()
    (old / "snapshot.json").write_text(
        json.dumps({"league": {"roster_positions": ["QB"]}, "rosters": [{}, {}]})
    )
    newest = tmp_path / "league-20260904T130046Z"
    newest.mkdir()
    (newest / "snapshot.json").write_text("{not json")

    league = load_league_structure(tmp_path)
    assert league is not None, "a corrupt newest snapshot must not blank the panel"
    assert league["roster_positions"] == ["QB"], "it should fall back to the readable one"


def test_an_unreadable_snapshot_root_shows_nothing_rather_than_guessing(tmp_path) -> None:
    from src.dynasty_genius.features.replacement_reasoning import load_league_structure

    assert load_league_structure(tmp_path) is None
