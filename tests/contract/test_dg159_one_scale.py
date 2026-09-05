"""DG-159 — one denominator for every position, and the four thresholds that feed it.

David ruled two things on 2026-09-04, both relayed and both built here:

    the anchor is 20.1  —  "the absolute best player in the league, or something
    mathematically achievable because we believe it is a Hall of Fame level Dynasty
    asset", and "not unreachable or extremely reachable"

    take both thresholds  —  the running back and receiver replacement ranks, which
    DG-160's shared-slot budget showed could not both be true in his league

Before this, each position's score was its points per game over ITS OWN ceiling, so a
tight end at 100 produced 9.4 points a game and a quarterback at 100 produced 20.1. The
two numbers were never comparable, which is what "it can't have its own scale" meant.
Now every score is points per game over ONE denominator, and position scarcity lives
entirely in the replacement line — the "calibration to the position" half of his sentence.

**The shape matters more than the values, and two of the guards built for this change
only fire under one of the two obvious shapes.** The wrong shape is to overwrite
ENGINE_B_P90_PPG with 20.1s. It looks identical from the served score's point of view
and it silently disarms two detectors:

  * counter_arguments.position_ceiling is P90 / anchor * 100. Alias the two together and
    it is x/x*100 — identically 100 forever, so the "top fifth" threshold stays at 80 and
    41 players lose the MANDATORY counter-argument with every test still green.
  * the tight-end ceiling stops being sayable. 9.4 / 20.1 * 100 = 46.8 is the honest
    statement that a tight end at the top of his position is worth 46.8 on this scale;
    overwrite the P90 and that number cannot be computed from anything left in the code.

So P90 stays what it is — a measured fact about each position's distribution — and the
denominator is a SEPARATE constant. Tests below pin that separation, because it is the
part a later reader would most plausibly "simplify" away.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from src.dynasty_genius.models.dvs_scale import (
    derive_lambda,
    derive_replacement_dvs,
    derive_sigma,
)
from src.dynasty_genius.models.engine_b_contract import (
    DVS_SCALE_ANCHOR_PPG,
    ENGINE_A_REPLACEMENT_DVS,
    ENGINE_B_P90_PPG,
    ENGINE_B_REPLACEMENT_DVS,
    ENGINE_B_VAR_THRESHOLDS,
    REPLACEMENT_PPG,
    XVAR_ANCHOR_POSITION,
    XVAR_LAMBDA_ENGINE_A,
    XVAR_LAMBDA_ENGINE_B,
)

POSITIONS = ("QB", "RB", "WR", "TE")
ROOT = Path(__file__).resolve().parents[2]


# ── 1. one denominator, and it is not the P90 table wearing a new name ──────
def test_every_position_is_divided_by_the_same_number():
    """The whole ruling in one assertion: one scale, not four."""
    assert len(set(DVS_SCALE_ANCHOR_PPG[pos] for pos in POSITIONS)) == 1


def test_the_denominator_is_the_value_david_chose():
    """20.1 points a game — his ruling, relayed 2026-09-04. He took it knowing every
    cross-positional number on his screen drops about 28% and Kraft goes 100 -> ~47."""
    assert DVS_SCALE_ANCHOR_PPG["QB"] == 20.1


def test_the_anchor_is_a_separate_constant_from_the_position_ceilings():
    """The trap this change is most likely to be 'simplified' into.

    If the anchor is the same object as the P90 table, then P90/anchor is 1 at every
    position, the tight-end ceiling reads 100 again, and counter_arguments' derived
    threshold goes back to a hard 80 that nothing can reach. Green tests, dead guard.
    """
    assert DVS_SCALE_ANCHOR_PPG is not ENGINE_B_P90_PPG
    assert ENGINE_B_P90_PPG == {"QB": 20.1, "RB": 15.7, "WR": 14.5, "TE": 9.4}, (
        "the P90s are a measured fact about each position's distribution, not a scale "
        "choice; the scale choice is DVS_SCALE_ANCHOR_PPG"
    )


def test_a_tight_end_at_the_top_of_his_position_is_worth_less_than_a_quarterback():
    """What one scale MEANS, stated as a number. The best tight end tops out at 46.8
    and the best quarterback at 100, because that is the football: 9.4 points a game
    against 20.1. Nothing here is a downgrade — it is the first time the two numbers
    are in the same unit."""
    from src.dynasty_genius.decision_logic.counter_arguments import position_ceiling

    assert position_ceiling("TE") == pytest.approx(46.8, abs=0.1)
    assert position_ceiling("WR") == pytest.approx(72.1, abs=0.1)
    assert position_ceiling("RB") == pytest.approx(78.1, abs=0.1)
    assert position_ceiling("QB") == pytest.approx(100.0, abs=0.1)


# ── 2. the coupled set, all of it derived from the one anchor ───────────────
@pytest.mark.parametrize("pos", POSITIONS)
def test_every_multiplier_is_one_because_there_is_nothing_left_to_convert(pos: str):
    """The cancellation identity doing its job rather than being switched off: with a
    single denominator there is no position-specific scale left to cancel, so the
    multiplier is 1.000 at every position on both engines."""
    expected = derive_lambda(DVS_SCALE_ANCHOR_PPG[pos], DVS_SCALE_ANCHOR_PPG[XVAR_ANCHOR_POSITION])
    assert XVAR_LAMBDA_ENGINE_B[pos] == expected == 1.000
    assert XVAR_LAMBDA_ENGINE_A[pos] == expected == 1.000


@pytest.mark.parametrize("pos", POSITIONS)
def test_replacement_sits_where_the_one_denominator_puts_it(pos: str):
    expected = derive_replacement_dvs(REPLACEMENT_PPG[pos], DVS_SCALE_ANCHOR_PPG[pos])
    assert ENGINE_B_REPLACEMENT_DVS[pos] == expected


def test_the_two_engines_now_share_one_replacement_table():
    """Replacement level is a fact about the LEAGUE — how many of this position start —
    and does not depend on which model scored the player. Two tables existed only
    because the two engines divided by different ceilings; with one denominator the
    tables collapse. They were 14% apart, so a rookie and a veteran with the same points
    above replacement carried different cross-positional values."""
    assert ENGINE_A_REPLACEMENT_DVS == ENGINE_B_REPLACEMENT_DVS


def test_the_replacement_points_are_a_named_constant_and_not_a_comment():
    """Until now the four numerators lived ONLY in inline comments, and the artifact
    they cite (var_batch_20260516_190328.json) does not contain them — it holds
    13.47 / 8.59 / 8.65 / 9.76. Nothing on disk or in the training data reproduces the
    shipped 12.91 / 7.29 / 8.79 / 8.99 at any rank in any season. A number no
    derivation reaches cannot be checked, which is why it is now derived and pinned."""
    assert set(REPLACEMENT_PPG) == set(POSITIONS)
    for pos in POSITIONS:
        assert isinstance(REPLACEMENT_PPG[pos], float)


# ── 3. the thresholds, and the budget that decides them ────────────────────
def test_the_four_ranks_can_all_be_true_at_once_in_his_league():
    """DG-160's detector, run on the corrected ranks. It is the reason the receiver
    threshold moved at all: the four shipped ranks demanded 48 shared places from a
    league that has 36, and no split of the flex made them jointly true."""
    from src.dynasty_genius.features.replacement_reasoning import (
        DerivationStatus,
        audit_shared_slot_budget,
    )

    audit = audit_shared_slot_budget(
        thresholds=ENGINE_B_VAR_THRESHOLDS,
        roster_positions=["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX"],
        teams=12,
    )
    assert audit["status"] is DerivationStatus.AGREES, audit["explanation"]
    assert audit["demanded"] == audit["available"] == 36, (
        "the shared places are exactly consumed: every flex and superflex seat in the "
        "league is accounted for by exactly one position's rank"
    )


def test_the_receiver_rank_no_longer_assumes_a_third_receiver_slot():
    """The defect in words: WR53 carried a comment deriving it from '12 x 3 = 36',
    a third dedicated receiver slot David's league does not have. It starts two."""
    assert ENGINE_B_VAR_THRESHOLDS["WR"] == 45


def test_the_quarterback_and_tight_end_ranks_were_already_right():
    """Both were derivable with no assumption at all — the superflex is a quarterback
    seat and the tight end has no shared demand — and neither moves. A correction that
    moved all four would have been fitting, not deriving."""
    assert ENGINE_B_VAR_THRESHOLDS["QB"] == 25
    assert ENGINE_B_VAR_THRESHOLDS["TE"] == 13


# ── 4. the band is the same football in the new unit ───────────────────────
@pytest.mark.parametrize("pos", POSITIONS)
def test_the_band_is_the_served_model_s_own_error_over_the_one_denominator(pos: str):
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_B, ENGINE_B_SIGMA_RUN

    report = json.loads(
        (
            ROOT / "app/data/models/engine_b/runs" / ENGINE_B_SIGMA_RUN
            / f"validation_report_{pos.lower()}.json"
        ).read_text()
    )
    assert DVS_SIGMA_B[pos] == derive_sigma(
        report["metrics_v2"]["rmse"], DVS_SCALE_ANCHOR_PPG[pos]
    )


@pytest.mark.parametrize("pos", POSITIONS)
def test_the_prior_s_band_is_engine_a_s_own_error_over_the_same_denominator(pos: str):
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_A, ENGINE_A_SIGMA_RUN

    metadata = json.loads(
        (ROOT / "app/data/models/runs" / ENGINE_A_SIGMA_RUN / f"{pos}_metadata.json").read_text()
    )
    assert DVS_SIGMA_A[pos] == derive_sigma(
        metadata["metrics"]["rmse"], DVS_SCALE_ANCHOR_PPG[pos]
    )


def test_the_v3_tight_end_head_carries_its_own_out_of_fold_error():
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_A_V3

    script = (ROOT / "scripts/promote_head_a_te_v3.py").read_text()
    oof = float(re.search(r"^\s*oof_rmse = ([0-9.]+)", script, re.M).group(1))
    assert DVS_SIGMA_A_V3 == {"TE": derive_sigma(oof, DVS_SCALE_ANCHOR_PPG["TE"])}


def test_the_two_engines_tight_end_bands_stop_coinciding():
    """They both stored 23.6 and meant different football — 2.2223 points a game
    against Engine B's old ceiling, 2.1520 against Engine A's. One denominator
    separates them, which is the coincidence gone rather than a value changed."""
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_A, DVS_SIGMA_B

    assert DVS_SIGMA_B["TE"] != DVS_SIGMA_A["TE"]


# ── 5. the cancellation identity, restated for one denominator ─────────────
@pytest.mark.parametrize("pos", POSITIONS)
def test_cross_positional_value_is_points_above_replacement_in_one_unit(pos: str):
    """The identity that makes the number mean anything: whatever the denominator, an
    unclamped cross-positional value is (this player's points - replacement's points)
    expressed against the anchor. Under four denominators the position ceiling cancelled;
    under one there is nothing to cancel and the arithmetic is the same."""
    anchor = DVS_SCALE_ANCHOR_PPG[pos]
    ppg = 12.0
    dvs = ppg / anchor * 100.0
    xvar = (dvs - ENGINE_B_REPLACEMENT_DVS[pos]) * XVAR_LAMBDA_ENGINE_B[pos]
    assert xvar == pytest.approx((ppg - REPLACEMENT_PPG[pos]) * 100.0 / anchor, abs=0.06)


# ── 6. the guards DG-158 built for this morning, verified against the real move ──
#
# Three of the five were wired to a constant this change does not move, and a dormant
# guard and a broken guard look identical until the morning they are needed. Each is
# checked here against the SHAPE the rescale actually has rather than an idealised one.


def test_the_top_asset_threshold_falls_with_the_ceiling_it_is_a_share_of():
    """Wired to ENGINE_B_P90_PPG this reads P90/P90*100 — identically 100, so the
    threshold stays at a hard 80 that RB, WR and TE can never reach, and 41 players
    lose the MANDATORY counter-argument (Constitution Rule 4) with nothing on screen
    to say so."""
    from src.dynasty_genius.decision_logic.counter_arguments import (
        SCALE_ANCHOR_PPG,
        counter_argument_for,
        top_asset_threshold,
    )

    assert SCALE_ANCHOR_PPG is not ENGINE_B_P90_PPG
    assert top_asset_threshold("TE") == pytest.approx(37.4, abs=0.1)
    assert top_asset_threshold("QB") == pytest.approx(80.0, abs=0.1)
    # Tucker Kraft, measured: 100.0 before, 46.8 after. He keeps his argument.
    assert counter_argument_for(risk_flags=[], dynasty_value_score=46.8, position="TE") is not None


def test_the_prospect_boards_are_told_the_scale_moved_and_still_rebuild():
    """Wired to ENGINE_B_P90_PPG the token does not change across this rescale, all 80
    moved cards classify as undeclared drift, the refresh exits 1 and the rookie and
    pick boards do not rebuild at all on the morning the scale changes."""
    from scripts.refresh_prospect_cards import (
        DEFAULT_DVS_SCALE_TOKEN,
        classify_dvs_movement,
        current_dvs_scale_token,
    )

    token = current_dvs_scale_token()
    assert token != DEFAULT_DVS_SCALE_TOKEN
    assert (
        classify_dvs_movement(
            baseline_dvs=85.1,
            new_dvs=70.7,
            declared_scale=token,
            baseline_scale=DEFAULT_DVS_SCALE_TOKEN,
        )
        == "declared_rescale"
    )
    # and the run after, on the new scale, is held to invariance again
    assert (
        classify_dvs_movement(
            baseline_dvs=70.7, new_dvs=64.0, declared_scale=token, baseline_scale=token
        )
        == "undeclared_drift"
    )


def _rescale_rows(anchor: float = 20.1):
    """The comparison the what-changed report actually sees on rescale morning:
    two engines with different old ceilings, and every score rounded to one decimal."""
    old = {"ENGINE_B": {"QB": 20.1, "RB": 15.7, "WR": 14.5, "TE": 9.4},
           "ENGINE_A": {"QB": 16.7, "RB": 14.6, "WR": 12.7, "TE": 9.1}}
    prior, latest = [], []
    for engine, ceilings in old.items():
        for pos, ceiling in ceilings.items():
            for i in range(12):
                ppg = ceiling * (0.25 + 0.06 * i)
                key = f"{engine}-{pos}-{i}"
                row = {"player_key": key, "sleeper_id": key, "position": pos, "engine_path": engine}
                prior.append({**row, "dynasty_value_score": round(ppg / ceiling * 100.0, 1)})
                latest.append({**row, "dynasty_value_score": round(ppg / anchor * 100.0, 1)})
    return prior, latest


def test_the_units_change_is_recognised_on_the_move_that_actually_happens():
    """DG-158's detector required ONE factor per position within half a percent. The
    real morning has two — Engine A players divided by a different old ceiling than
    Engine B's — and one-decimal rounding scatters the ratio of every low score far
    past that tolerance (a receiver at 0.1 -> 0.1 has a ratio of 1.0). Measured on the
    served artifact, the landed form fired at NONE of the four positions, so the
    product would have listed all 582 scored players as fallers, 263 of them David's:
    the exact failure the guard was built to prevent, looking like it worked."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior, latest = _rescale_rows()
    factors = detect_uniform_position_factor(prior, latest)
    assert factors is not None, "the change of units went unnoticed"
    assert factors["TE/ENGINE_B"] == pytest.approx(9.4 / 20.1, abs=0.005)
    assert factors["TE/ENGINE_A"] == pytest.approx(9.1 / 20.1, abs=0.005)
    assert factors["WR/ENGINE_B"] == pytest.approx(14.5 / 20.1, abs=0.005)


def test_the_quarterbacks_that_did_not_move_are_not_reported_as_having_moved():
    """The anchor IS the Engine B quarterback ceiling, so those scores are identical
    on both sides. A detector that called that a change of units would be describing
    a move that did not happen."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior, latest = _rescale_rows()
    factors = detect_uniform_position_factor(prior, latest)
    assert "QB/ENGINE_B" not in factors


def test_an_ordinary_morning_is_still_not_mistaken_for_a_change_of_units():
    """Replayed over all 70 day-to-day comparisons in the model capture database, the
    detector must stay silent on every one. A guard that fires on a normal Tuesday
    would suppress the report David actually reads."""
    import sqlite3

    db = ROOT / "app/data/model_forward_capture.db"
    if not db.exists():  # a worktree without the captured database
        pytest.skip("model capture database not present in this tree")
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        dates = [r[0] for r in con.execute(
            "select distinct capture_date from model_forward_capture_joinable order by 1")]
        query = (
            "select player_key, position, engine_path, dynasty_value_score "
            "from model_forward_capture_joinable where capture_date = ?"
        )
        def rows(date):
            return [
                {"player_key": k, "position": p, "engine_path": e, "dynasty_value_score": v}
                for k, p, e, v in con.execute(query, (date,))
            ]
        fired = [
            (a, b) for a, b in zip(dates, dates[1:])
            if detect_uniform_position_factor(rows(a), rows(b)) is not None
        ]
    finally:
        con.close()
    assert fired == [], f"claimed a change of units on an ordinary morning: {fired}"
