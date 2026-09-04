"""DG-158 — the four constants written in SCORE UNITS, and the scale moving under them.

Fred's rescale replaces the per-position denominators with a single anchor, so every
displayed score moves by that position's factor (Engine B: QB 1.0000, RB 0.7811,
WR 0.7214, TE 0.4677). Four things elsewhere are expressed in score points and do
not move with it. Each was silently coupled to a scale nobody thought of them as
depending on, and each is pinned here so the NEXT rescale needs no hand-edit.

Measured before building, on the served artifact:
  * the counter-argument population goes 57 -> 9, all quarterbacks, because clearing
    80 would require 102.4 / 110.9 / 171.0 today at RB / WR / TE and scores clamp at 100;
  * 80 prospect cards move and the refresh exits 1, so the boards do not rebuild;
  * the model movers list is uncapped — 387 live, 582 on rebase morning, all fallers;
  * the TE band becomes 1.01x the whole TE scale.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.decision_logic.counter_arguments import (
    TOP_ASSET_SCALE_SHARE,
    counter_argument_for,
    top_asset_threshold,
)
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG

POSITIONS = ("QB", "RB", "WR", "TE")


# ── 1. the counter-argument threshold rides the scale ───────────────────────
def test_today_the_threshold_is_still_eighty():
    """Behaviour-preserving on the scale as it stands: the constant was 80 on a
    0-100 scale, and that is 80% of the ceiling. Nobody gains or loses an
    argument on the day this lands."""
    for pos in POSITIONS:
        assert top_asset_threshold(pos) == pytest.approx(80.0)


def test_the_threshold_follows_a_rescaled_ceiling_instead_of_standing_still(monkeypatch):
    """The whole defect: with a single anchor denominator the TE ceiling falls to
    46.8, so a fixed 80 can never be reached. The threshold has to be a SHARE of
    the scale, not a number of points on it."""
    monkeypatch.setitem(ENGINE_B_P90_PPG, "TE", 9.4)
    anchor = {"QB": 20.1, "RB": 20.1, "WR": 20.1, "TE": 20.1}
    monkeypatch.setattr(
        "src.dynasty_genius.decision_logic.counter_arguments.SCALE_ANCHOR_PPG", anchor
    )
    # TE ceiling becomes 9.4 / 20.1 * 100 = 46.77; 80% of that is 37.4
    assert top_asset_threshold("TE") == pytest.approx(37.4, abs=0.1)
    assert top_asset_threshold("QB") == pytest.approx(80.0)


def test_a_top_tight_end_keeps_his_mandatory_argument_after_the_rescale(monkeypatch):
    """Tucker Kraft, measured: 100.0 today, 46.8 after. Under a fixed 80 he loses
    the mandatory counter-argument silently; under a share of the scale he keeps it."""
    anchor = {"QB": 20.1, "RB": 20.1, "WR": 20.1, "TE": 20.1}
    monkeypatch.setattr(
        "src.dynasty_genius.decision_logic.counter_arguments.SCALE_ANCHOR_PPG", anchor
    )
    argument = counter_argument_for(risk_flags=[], dynasty_value_score=46.8, position="TE")
    assert argument is not None
    assert "TD-dependent" in argument


def test_the_share_is_named_and_is_what_eighty_meant():
    assert TOP_ASSET_SCALE_SHARE == 0.80


def test_an_unknown_position_refuses_rather_than_defaulting_to_a_number():
    with pytest.raises(KeyError):
        top_asset_threshold("K")


def test_a_risk_flag_still_outranks_the_threshold():
    """Priority 1 is unchanged: a flagged player gets the flag's argument
    whatever the scale is doing."""
    argument = counter_argument_for(
        risk_flags=["age_past_position_cliff"], dynasty_value_score=1.0, position="RB"
    )
    assert argument is not None
    assert "Liquidity Caveat" in argument


# ── 2. the prospect boards are TOLD about the move, never left to guess ─────
def test_an_undeclared_drift_still_stops_the_refresh():
    """The gate is a CONTAMINATION detector — enrich_te_prospects_cfbd_2026.py
    exists to set a baseline so the refresh passes it cleanly. A rescale must not
    be an excuse to switch it off; an unexplained score move still stops the run."""
    from scripts.refresh_prospect_cards import classify_dvs_movement

    verdict = classify_dvs_movement(
        baseline_dvs=71.0, new_dvs=70.2, declared_scale="anchor-v1", baseline_scale="anchor-v1"
    )
    assert verdict == "undeclared_drift"


def test_a_declared_rescale_is_expected_movement_not_a_fault():
    """80 of 82 cards move on rescale morning. Under the old gate the boards
    simply did not rebuild (sys.exit(1)); the movement is now declarable."""
    from scripts.refresh_prospect_cards import classify_dvs_movement

    verdict = classify_dvs_movement(
        baseline_dvs=85.1, new_dvs=70.7, declared_scale="anchor-20.1", baseline_scale="anchor-v1"
    )
    assert verdict == "declared_rescale"


def test_no_movement_is_still_the_normal_answer():
    from scripts.refresh_prospect_cards import classify_dvs_movement

    assert (
        classify_dvs_movement(
            baseline_dvs=71.0, new_dvs=71.0, declared_scale="anchor-v1", baseline_scale="anchor-v1"
        )
        == "unchanged"
    )


def test_declaring_a_scale_does_not_excuse_a_second_undeclared_move():
    """Once the run declares a new scale, every card is expected to move — but the
    NEXT run, on the same scale, is held to invariance again."""
    from scripts.refresh_prospect_cards import classify_dvs_movement

    assert (
        classify_dvs_movement(
            baseline_dvs=70.7, new_dvs=64.0, declared_scale="anchor-20.1", baseline_scale="anchor-20.1"
        )
        == "undeclared_drift"
    )


# ── 3. the model movers are capped, and the total is still told ─────────────
def test_the_model_section_caps_its_movers_like_the_market_section_does():
    """Uncapped it emits 387 today and 582 on rescale morning, every one a
    faller, 263 of them David's. The market lane has capped at 25 since it was
    written; the model lane never did."""
    from src.dynasty_genius.what_changed.daily_diff import MODEL_TOP_MOVERS_CAP

    assert MODEL_TOP_MOVERS_CAP == 25


def test_the_capped_list_still_reports_how_many_there_really_were():
    """A capped list that hides its own total is the same silence in a smaller
    box — the market lane reports total_movers_count and so must this one."""
    from src.dynasty_genius.what_changed.daily_diff import cap_model_deltas

    deltas = [{"sleeper_id": str(i), "value_delta": float(-i)} for i in range(1, 101)]
    out = cap_model_deltas(deltas)
    assert len(out["deltas"]) == 25
    assert out["total_movers_count"] == 100
    # biggest movement first, so the cap keeps the ones worth reading
    assert abs(out["deltas"][0]["value_delta"]) >= abs(out["deltas"][-1]["value_delta"])


def test_a_short_list_is_untouched_and_honest():
    from src.dynasty_genius.what_changed.daily_diff import cap_model_deltas

    deltas = [{"sleeper_id": "a", "value_delta": -1.0}]
    out = cap_model_deltas(deltas)
    assert out["deltas"] == deltas
    assert out["total_movers_count"] == 1


# ── 4. the band is the same real quantity in whatever unit the scale uses ───
def _sigma_from_artifacts(anchor: dict[str, float]) -> tuple[dict, dict]:
    """Recompute both engines' sigmas against a given denominator, from each
    engine's OWN published error — the derivation dvs_band.py's docstring states."""
    import json
    from pathlib import Path

    from src.dynasty_genius.models.dvs_band import (
        ENGINE_A_SIGMA_RUN,
        ENGINE_B_SIGMA_RUN,
    )

    root = Path(__file__).resolve().parents[2]
    b, a = {}, {}
    for pos in POSITIONS:
        rep = json.loads(
            (
                root / "app/data/models/engine_b/runs" / ENGINE_B_SIGMA_RUN
                / f"validation_report_{pos.lower()}.json"
            ).read_text()
        )
        b[pos] = round(rep["metrics_v2"]["rmse"] / anchor[pos] * 100.0, 1)
        md = json.loads(
            (root / "app/data/models/runs" / ENGINE_A_SIGMA_RUN / f"{pos}_metadata.json").read_text()
        )
        a[pos] = round(md["metrics"]["rmse"] / anchor[pos] * 100.0, 1)
    return b, a


def test_the_band_keeps_its_size_relative_to_the_scale_when_the_anchor_moves():
    """The defect: sigma is stored in DVS points, so a shrinking scale leaves the
    band standing still and it swallows the position. Measured against a single
    anchor with sigma left behind, the tight-end band becomes 1.57x the
    replacement-to-best range. Recomputed from the same denominator the score
    uses, the band is the SAME real quantity — one holdout RMSE — and its share
    of the scale does not move at all."""
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_B
    from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG

    today = dict(ENGINE_B_P90_PPG)
    anchored = {pos: 20.1 for pos in POSITIONS}
    recomputed, _ = _sigma_from_artifacts(anchored)
    for pos in POSITIONS:
        ceiling_today = 100.0
        ceiling_anchored = ENGINE_B_P90_PPG[pos] / anchored[pos] * 100.0
        share_today = DVS_SIGMA_B[pos] / ceiling_today
        share_anchored = recomputed[pos] / ceiling_anchored
        assert share_anchored == pytest.approx(share_today, abs=0.01), (
            f"{pos}: the band changed size relative to its own scale "
            f"({share_today:.3f} -> {share_anchored:.3f})"
        )
    assert today == dict(ENGINE_B_P90_PPG), "the test must not mutate the contract"


def test_the_two_engines_sigmas_are_computed_apart_even_where_they_coincide():
    """Engine A and Engine B both store 23.6 for tight end and they mean
    different football: 2.2223 ppg against B's ceiling, 2.1520 against A's.
    Recomputed against one anchor they SEPARATE (11.1 and 10.7). The identical
    stored values invite fixing one and copying it across, which would get Engine
    A wrong with nothing anywhere to reveal it — a silent failure hiding inside a
    coincidence."""
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_A, DVS_SIGMA_B

    assert DVS_SIGMA_B["TE"] == DVS_SIGMA_A["TE"], "the coincidence this guards is gone; re-read the test"
    b, a = _sigma_from_artifacts({pos: 20.1 for pos in POSITIONS})
    assert b["TE"] != a["TE"], (
        "recomputed against one anchor the two engines' TE errors must differ; "
        "equal values here mean one was copied from the other"
    )


def test_the_band_reads_the_same_denominator_the_score_divides_by():
    """The one path where piece 4 could go quiet: a NEW anchor constant added
    BESIDE the old one, so the score uses the new denominator while the band's
    provenance test still passes against the old. They must be the same object."""
    from src.dynasty_genius import pvo_assembler
    from src.dynasty_genius.models import (
        dvs_band,  # noqa: F401  (imported for the pin below)
    )
    from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG

    assert pvo_assembler.ENGINE_B_P90_PPG is ENGINE_B_P90_PPG, (
        "the assembler must divide by the same mapping the band is derived from"
    )
