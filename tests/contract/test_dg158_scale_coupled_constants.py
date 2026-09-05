"""DG-158 — the four constants written in SCORE UNITS, and the scale moving under them.

DG-159 replaced the per-position denominators with a single anchor, so every displayed
score moved by that position's factor (Engine B: QB 1.0000, RB 0.7811, WR 0.7214,
TE 0.4677; Engine A separately: 0.8308, 0.7264, 0.6318, 0.4527). Four things elsewhere
are expressed in score points and did not move with it. Each was silently coupled to a
scale nobody thought of them as depending on, and each is pinned here so the NEXT
rescale needs no hand-edit.

Measured before building, on the served artifact:
  * the counter-argument population goes 57 -> 9, all quarterbacks, because clearing
    80 would require 102.4 / 110.9 / 171.0 at RB / WR / TE and scores clamp at 100;
  * 80 prospect cards move and the refresh exits 1, so the boards do not rebuild;
  * the model movers list is uncapped — 387 live, 582 on rebase morning, all fallers;
  * the TE band becomes 1.01x the whole TE scale.

**Two of the five were wired to ENGINE_B_P90_PPG, which DG-159 deliberately does not
move** — the P90s stay a measured fact about each position so that a position's ceiling
on the shared scale is still sayable. Repointed at DVS_SCALE_ANCHOR_PPG in DG-159; the
tests below are what a wrong wiring shows up in, and the ones that read the anchor now
say so.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.decision_logic.counter_arguments import (
    TOP_ASSET_SCALE_SHARE,
    counter_argument_for,
    top_asset_threshold,
)
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG

POSITIONS = ("QB", "RB", "WR", "TE")


# ── 1. the counter-argument threshold rides the scale ───────────────────────
def test_the_threshold_is_eighty_percent_of_whatever_the_ceiling_is():
    """When DG-158 landed, all four ceilings were 100 and this asserted a flat 80 —
    behaviour-preserving, nobody gaining or losing an argument on landing day. DG-159
    moved the ceilings, and the whole point of a derived threshold is that this
    assertion follows them instead of pinning a number that stopped being reachable."""
    from src.dynasty_genius.decision_logic.counter_arguments import position_ceiling

    for pos in POSITIONS:
        assert top_asset_threshold(pos) == pytest.approx(0.80 * position_ceiling(pos))
    assert top_asset_threshold("QB") == pytest.approx(80.0, abs=0.1)
    assert top_asset_threshold("TE") == pytest.approx(37.4, abs=0.1)


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
    from src.dynasty_genius.models.engine_b_contract import (
        DVS_SCALE_ANCHOR_PPG,
        ENGINE_B_P90_PPG,
    )

    before = dict(ENGINE_B_P90_PPG)
    # What the band was before the anchor moved: each position's own ceiling was 100,
    # and sigma was its error over that ceiling.
    per_position, _ = _sigma_from_artifacts(dict(ENGINE_B_P90_PPG))
    for pos in POSITIONS:
        ceiling_now = ENGINE_B_P90_PPG[pos] / DVS_SCALE_ANCHOR_PPG[pos] * 100.0
        share_before = per_position[pos] / 100.0
        share_now = DVS_SIGMA_B[pos] / ceiling_now
        assert share_now == pytest.approx(share_before, abs=0.01), (
            f"{pos}: the band changed size relative to its own scale "
            f"({share_before:.3f} -> {share_now:.3f})"
        )
    assert before == dict(ENGINE_B_P90_PPG), "the test must not mutate the contract"


def test_the_two_engines_sigmas_are_computed_apart_even_where_they_coincide():
    """Engine A and Engine B both store 23.6 for tight end and they mean
    different football: 2.2223 ppg against B's ceiling, 2.1520 against A's.
    Recomputed against one anchor they SEPARATE (11.1 and 10.7). The identical
    stored values invite fixing one and copying it across, which would get Engine
    A wrong with nothing anywhere to reveal it — a silent failure hiding inside a
    coincidence."""
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_A, DVS_SIGMA_B
    from src.dynasty_genius.models.engine_b_contract import DVS_SCALE_ANCHOR_PPG

    b, a = _sigma_from_artifacts(DVS_SCALE_ANCHOR_PPG)
    assert (DVS_SIGMA_B["TE"], DVS_SIGMA_A["TE"]) == (b["TE"], a["TE"])
    assert DVS_SIGMA_B["TE"] != DVS_SIGMA_A["TE"], (
        "against one denominator the two engines' TE errors must differ (2.2223 ppg "
        "against 2.1520); equal values mean one was copied from the other"
    )


def test_the_band_reads_the_same_denominator_the_score_divides_by():
    """The one path where piece 4 could go quiet: a NEW anchor constant added BESIDE
    the old one, so the score uses the new denominator while the band's provenance
    test still passes against the old.

    DG-159 did add exactly such a constant, which is what this guards. It is checked
    by DIVIDING rather than by comparing imports: `pvo_assembler.X is X` was true
    whether or not the assembler used X, so it could not have caught the thing it
    names. Here the assembler scores a player of known points a game and the band's
    denominator is read back out of the score itself.
    """
    from src.dynasty_genius.models.dvs_band import DVS_SIGMA_B, ENGINE_B_SIGMA_RUN
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    ppg = 12.0
    pvo = assemble_pvo(
        PlayerIdentity(
            dg_id="denominator-probe",
            full_name="Denominator Probe",
            position="TE",
            is_prospect=False,
            verification_status="VERIFIED_NFL_DRAFT",
        ),
        {
            "engine_b_score": {"predicted_avg_ppg_t1_t2": ppg, "engine": "test_v2"},
            "games_t": 10,
            "feature_season": 2024,
        },
    )
    scoring_denominator = ppg / pvo.dynasty_value_score * 100.0

    report = json.loads(
        (
            Path(__file__).resolve().parents[2] / "app/data/models/engine_b/runs"
            / ENGINE_B_SIGMA_RUN / "validation_report_te.json"
        ).read_text()
    )
    band_denominator = report["metrics_v2"]["rmse"] / DVS_SIGMA_B["TE"] * 100.0

    assert scoring_denominator == pytest.approx(band_denominator, rel=0.005), (
        f"the score divides by {scoring_denominator:.2f} points a game and the band by "
        f"{band_denominator:.2f}; the band would describe a scale nothing is on"
    )


# ── 5. a change of units is not a fall, and must not render as one ──────────
def _rows(scores: dict[str, tuple[str, float]]) -> list[dict]:
    return [
        {"player_key": k, "sleeper_id": k, "position": pos, "dynasty_value_score": v}
        for k, (pos, v) in scores.items()
    ]


def test_a_uniform_per_position_factor_is_recognised_as_a_change_of_units():
    """On rescale morning every compared player in a position moves by exactly
    the same factor. Real football never does that: 130 tight ends do not all
    move 53% in one night. The signature is in the data, so nothing new has to be
    recorded for the product to notice."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior = _rows({f"te{i}": ("TE", 40.0 + i) for i in range(12)})
    latest = _rows({f"te{i}": ("TE", (40.0 + i) * 0.4677) for i in range(12)})
    factors = detect_uniform_position_factor(prior, latest)
    assert factors is not None
    assert factors["TE"] == pytest.approx(0.4677, abs=0.001)


def test_an_ordinary_morning_is_not_mistaken_for_a_change_of_units():
    """The guard that matters: this must fire on the one predictable morning and
    never swallow a real one."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior = _rows({f"wr{i}": ("WR", 50.0 + i) for i in range(20)})
    latest = _rows({f"wr{i}": ("WR", 50.0 + i + (i % 3) - 1) for i in range(20)})
    assert detect_uniform_position_factor(prior, latest) is None


def test_a_quiet_morning_where_nothing_moved_is_not_a_units_change():
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior = _rows({f"rb{i}": ("RB", 30.0 + i) for i in range(15)})
    assert detect_uniform_position_factor(prior, list(prior)) is None


def test_too_few_players_in_a_position_is_not_enough_to_claim_a_pattern():
    """Three players moving alike is a coincidence, not a re-denomination."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    prior = _rows({f"qb{i}": ("QB", 60.0 + i) for i in range(3)})
    latest = _rows({f"qb{i}": ("QB", (60.0 + i) * 0.83) for i in range(3)})
    assert detect_uniform_position_factor(prior, latest) is None


def test_it_fires_once_by_construction_and_not_again_the_next_day():
    """The morning after, both sides are already in the new unit, the factor is
    1.0, and nothing is reported. The trigger cannot stay armed."""
    from src.dynasty_genius.what_changed.daily_diff import (
        detect_uniform_position_factor,
    )

    rescaled = _rows({f"te{i}": ("TE", (40.0 + i) * 0.4677) for i in range(12)})
    assert detect_uniform_position_factor(rescaled, list(rescaled)) is None


def test_the_refusal_names_no_cause_and_emits_no_per_player_fall():
    """Every score is lower, and not one player got worse. The product must not
    list 582 fallers, and must not invent a reason for the move either."""
    from src.dynasty_genius.what_changed.daily_diff import MODEL_UNIFORM_FACTOR_STATUS

    assert MODEL_UNIFORM_FACTOR_STATUS == "model_uniform_factor_per_position"
    for banned in ("rescale", "rebuilt", "model_run", "fell", "dropped"):
        assert banned not in MODEL_UNIFORM_FACTOR_STATUS
