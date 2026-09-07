"""DG-178 — the shared value contract every forecast lane hands the assembler.

The assembler never multiplies one producer's probability by another producer's conditional
mean. So the contract admits only terms that are ALREADY unconditional, on one clock, in one
unit, with the event they were integrated over written down. These tests pin that shape.
"""
from __future__ import annotations

from datetime import date

import pytest


def _term(h: int = 0, ev: float = 3.0, **kw):
    from src.dynasty_genius.ranking.contract import HorizonTerm, annual_target

    return HorizonTerm(h=h, season=2026 + h, ev_above_replacement=ev,
                       conditioning_event="fixture event", spec=annual_target(date(2026, 9, 6)), **kw)


def _producer(estimate_class: str = "candidate"):
    from src.dynasty_genius.ranking.contract import ProducerRef

    return ProducerRef(name="fixture", version="0", estimate_class=estimate_class)


def _replacement(position: str = "WR"):
    from src.dynasty_genius.ranking.contract import ReplacementRef

    return ReplacementRef(position=position, policy="fixture", rate_ppg=9.0,
                          snapshot_id="fixture-snapshot",
                          horizon_assumption="held_constant_from_snapshot")


def test_a_terms_unit_comes_from_its_typed_spec_and_cannot_be_declared_in_prose() -> None:
    """The unit is derived from the typed quantity, never a per-producer string."""
    from src.dynasty_genius.ranking.contract import UNIT, HorizonTerm, annual_target

    t = _term()
    assert t.unit == UNIT == "season_points_above_replacement"
    with pytest.raises(Exception):
        HorizonTerm(h=0, season=2026, ev_above_replacement=1.0, conditioning_event="x",
                    spec=annual_target(date(2026, 9, 6)), unit="season_total_points")


def test_a_negative_expected_value_is_refused_not_clamped() -> None:
    """Unconditional EV above replacement is >= 0 by definition: a season he does not
    contribute counts 0 (the replacement plays), never negative. A negative value means the
    producer subtracted the bar from a conditional mean and skipped the probability."""
    with pytest.raises(ValueError, match="unconditional"):
        _term(ev=-0.5)


def test_horizon_zero_is_the_season_that_starts_after_the_forecast_date() -> None:
    """One clock. h=0 for a 2026-09-06 forecast is the 2026 season; h=1 is 2027."""
    from src.dynasty_genius.ranking.contract import season_for_horizon

    assert season_for_horizon(date(2026, 9, 6), 0) == 2026
    assert season_for_horizon(date(2026, 9, 6), 1) == 2027
    # A forecast made in the spring still points at the season that has not started.
    assert season_for_horizon(date(2027, 3, 1), 0) == 2027


def test_a_term_set_refuses_a_term_whose_season_disagrees_with_its_clock() -> None:
    from src.dynasty_genius.ranking.contract import TermSet

    bad = _term(h=1)  # says 2027
    with pytest.raises(ValueError, match="season"):
        TermSet(player_id="p1", position="WR", forecast_date=date(2026, 9, 6),
                producer=_producer(), replacement_ref=_replacement(),
                terms=[_term(h=0), bad.model_copy(update={"season": 2030})],
                coverage="full")


def test_a_term_set_refuses_duplicate_or_unordered_horizons() -> None:
    from src.dynasty_genius.ranking.contract import TermSet

    with pytest.raises(ValueError, match="horizon"):
        TermSet(player_id="p1", position="WR", forecast_date=date(2026, 9, 6),
                producer=_producer(), replacement_ref=_replacement(),
                terms=[_term(h=0), _term(h=0)], coverage="full")


def test_estimate_class_is_closed_and_served_is_never_a_fixture() -> None:
    """Research estimates stay visibly distinct from served values (ticket: 'keeps research
    estimates visibly distinct from served values'). The class is a closed set."""
    from src.dynasty_genius.ranking.contract import ProducerRef

    for ok in ("served", "candidate", "fixture"):
        assert ProducerRef(name="x", version="1", estimate_class=ok).estimate_class == ok
    with pytest.raises(Exception):
        ProducerRef(name="x", version="1", estimate_class="production")


def test_coverage_none_requires_a_reason_and_carries_no_terms() -> None:
    """A blank must say why. A blank with terms attached is a contradiction."""
    from src.dynasty_genius.ranking.contract import TermSet

    with pytest.raises(ValueError, match="reason"):
        TermSet(player_id="p1", position="QB", forecast_date=date(2026, 9, 6),
                producer=_producer(), replacement_ref=_replacement("QB"),
                terms=[], coverage="none")
    with pytest.raises(ValueError, match="terms"):
        TermSet(player_id="p1", position="QB", forecast_date=date(2026, 9, 6),
                producer=_producer(), replacement_ref=_replacement("QB"),
                terms=[_term()], coverage="none", reason="no NFL season")


def test_replacement_ref_declares_the_future_as_a_scenario_not_a_fact() -> None:
    """Today's free agent held constant years forward is an explicit assumption."""
    from src.dynasty_genius.ranking.contract import ReplacementRef

    r = _replacement()
    assert r.horizon_assumption == "held_constant_from_snapshot"
    with pytest.raises(Exception):
        ReplacementRef(position="WR", policy="fixture", rate_ppg=9.0,
                       snapshot_id="s", horizon_assumption="known_future")


def test_a_non_finite_expected_value_is_refused() -> None:
    """NaN compares false against zero and slipped through the >= 0 check."""
    with pytest.raises(ValueError, match="finite"):
        _term(ev=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        _term(ev=float("inf"))


# ── Week-17 window (Codex, 2026-09-06 evening; David: the championship ends NFL Week 17) ──
def test_the_target_carries_its_week_window_and_a_producer_on_another_window_is_a_mismatch_never_mixed() -> None:
    """DG-179's shared outcome is nflverse-default PPR over David's window: REG weeks 1-16
    through 2020, 1-17 since 2021, equal weekly weighting. A producer still on the full
    regular season (all 17/18 weeks) is a DIFFERENT target: refused by mismatch, never
    rescaled or mixed."""
    from datetime import date

    from src.dynasty_genius.ranking.contract import TargetSpec, annual_target

    old = annual_target(date(2026, 9, 6))
    new = annual_target(date(2026, 9, 6), window="championship_week17")
    assert old.window == "all_reg_weeks" and new.window == "championship_week17"
    assert new.scoring == "PPR_nflverse_default" and old.scoring == "PPR_nflverse_weekly"
    assert set(new.mismatches(old)) == {"window", "scoring", "exposure"}
    assert new.exposure == "stat_record_weeks_in_window"  # DG-179: unique stat_record weeks within the outcome window
    # the window is a closed set: no free text
    import pytest

    with pytest.raises(Exception):
        TargetSpec(scope="REG", scoring="PPR_nflverse_default", exposure="stat_row_games", event="appearance",
                   clock="per_season", quantity="season_points", labels_through=2025, window="weeks 1-17 or so")
    # what the window means, in words the surface can quote
    assert new.window_description.startswith("points through the championship week (NFL Week 17) since 2021")
    assert "Week 16" in new.window_description and "equal weekly weighting" in new.window_description
    assert "not David's exact league scoring" in new.scoring_caveat


def test_a_manifest_that_names_the_window_types_onto_it_and_one_that_does_not_stays_on_the_full_season(tmp_path) -> None:

    from src.dynasty_genius.ranking.adapters.annual_candidate import _spec_from_manifest

    base = {"scoring_scope": "regular season", "scoring": "fantasy_points_ppr", "exposure_definition": "stat_row_games",
            "event": "appearance", "labels_through": 2025}
    assert _spec_from_manifest(base).window == "all_reg_weeks"
    win = dict(base, scoring="nflverse_default_ppr",
               window={"id": "championship_week17", "regular_weeks_through_2020": [1, 16], "regular_weeks_since_2021": [1, 17]})
    spec = _spec_from_manifest(win)
    assert spec.window == "championship_week17" and spec.scoring == "PPR_nflverse_default"
    # a window string the closed table does not know is refused, never guessed
    import pytest

    with pytest.raises(ValueError, match="window"):
        _spec_from_manifest(dict(base, window="weeks 1-18"))


def test_the_week17_research_preset_is_named_explicitly_and_its_scoring_caveat_names_the_unattributed_components() -> None:
    """CHAMPIONSHIP-WINDOW-2026-09-06.md: the target is `nflverse_default_ppr_championship_window_v1`,
    not David's exact scoring; saved PPR does not establish equivalence for all-unit fumble
    losses, recovery touchdowns and individual special-teams forced-fumble/recovery bonuses;
    research mode names its preset, exact-league mode refuses incomplete attribution."""
    from datetime import date

    from src.dynasty_genius.ranking.contract import annual_target

    new = annual_target(date(2026, 9, 6), window="championship_week17")
    assert new.target_id == "nflverse_default_ppr_championship_window_v1"
    assert annual_target(date(2026, 9, 6)).target_id == "nflverse_weekly_ppr_all_reg_weeks_v0"
    cav = new.scoring_caveat
    for phrase in ("fumble losses", "recovery touchdowns", "special-teams forced-fumble", "not David's exact league scoring",
                   "research preset", "no exact-match claim"):
        assert phrase in cav, phrase


def test_a_manifest_naming_the_preset_id_types_onto_the_week17_target(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import _spec_from_manifest

    m = {"scoring_scope": "regular season", "scoring": "nflverse_default_ppr_championship_window_v1",
         "exposure_definition": "stat_row_games", "event": "appearance", "labels_through": 2025,
         "window": "championship_week17"}
    spec = _spec_from_manifest(m)
    assert spec.scoring == "PPR_nflverse_default" and spec.window == "championship_week17"
    assert spec.target_id == "nflverse_default_ppr_championship_window_v1"
