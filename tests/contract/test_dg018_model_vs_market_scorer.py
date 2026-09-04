"""DG-018 RED: the standing model-versus-market grade, on the frozen prediction set.

DG-018 asks whether the model beats free consensus pricing. The realized-outcome loop
cannot answer it — ``realized_outcome_scorer`` says in its own docstring that "market data
never enters", and its precision@k is model-only with no difference interval. This scorer
is the missing half: it ranks the SAME players by the model and by the market, grades both
against the SAME realized outcomes, and reports the paired difference with its interval.

Rulings this file pins, so they cannot be quietly dropped later:
  * **The denominator ships on the face of the card.** A paired difference computed on the
    players both sides price, presented without the players only one side prices, is the
    exact trap this project has been burned by. Measured on the declared frozen set
    (2026-08-05): 501 model predictions, 474 market rows, 304 paired — so 197 the model
    prices and the market does not, and 170 the reverse. Those counts are required output,
    never a footnote.
  * **A null is a result.** If the interval straddles zero the scorer reports it straddling
    zero. Nothing here may suppress, tune, or re-roll a measurement toward a signal.
  * **Skill, not agreement.** The scorer never scores the model against the market; both are
    scored against realized outcomes, so agreeing with consensus earns nothing by itself.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.outcome_loop.model_vs_market_scorer import (
    POWER_FLOOR_MIN_COHORT,
    score_model_vs_market,
)


def _players(n: int, *, position: str = "WR", start: int = 0):
    return [f"{position}-{i}" for i in range(start, start + n)]


def _run(model, market, outcomes, **kw):
    return score_model_vs_market(
        model_predictions=model, market_snapshot=market, outcomes=outcomes, **kw
    )


# ── the paired comparison itself ─────────────────────────────────────────────────────


def test_a_model_that_orders_players_correctly_beats_a_market_that_inverts_them() -> None:
    ids = _players(14)
    # realized points descend with index; the model agrees, the market is exactly inverted.
    outcomes = {p: {"ppg": 20.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": 20.0 - i} for i, p in enumerate(ids)]
    market = [{"sleeper_id": p, "position": "WR", "value": float(i)} for i, p in enumerate(ids)]

    card = _run(model, market, outcomes)
    wr = card["positions"]["WR"]

    assert wr["status"] == "scored"
    assert wr["paired_n"] == 14
    assert wr["ndcg_diff"] > 0
    assert wr["model"]["spearman"] > wr["market"]["spearman"]
    assert card["decision_supported"] is False


def test_a_market_that_orders_players_correctly_beats_an_inverted_model() -> None:
    ids = _players(14)
    outcomes = {p: {"ppg": 20.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": float(i)} for i, p in enumerate(ids)]
    market = [{"sleeper_id": p, "position": "WR", "value": 20.0 - i} for i, p in enumerate(ids)]

    wr = _run(model, market, outcomes)["positions"]["WR"]

    assert wr["ndcg_diff"] < 0
    assert wr["model"]["spearman"] < wr["market"]["spearman"]


def test_the_difference_carries_an_interval_and_a_null_is_reported_as_a_null() -> None:
    """Model and market order identically: the honest answer is no difference, reported."""
    ids = _players(14)
    outcomes = {p: {"ppg": 20.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    same = [{"sleeper_id": p, "position": "WR", "projection_2y": 20.0 - i} for i, p in enumerate(ids)]
    market = [{"sleeper_id": p, "position": "WR", "value": 20.0 - i} for i, p in enumerate(ids)]

    wr = _run(same, market, outcomes)["positions"]["WR"]

    assert wr["ndcg_diff"] == pytest.approx(0.0, abs=1e-9)
    low, high = wr["ndcg_diff_ci95"]
    assert low <= 0.0 <= high, "a no-difference result must report an interval containing zero"
    assert wr["beats_market"] is None, "an interval containing zero is not a win"


# ── the denominator, on the face ─────────────────────────────────────────────────────


def test_players_only_one_side_prices_are_counted_on_the_face_never_dropped() -> None:
    paired = _players(12)
    model_only = _players(5, start=100)
    market_only = _players(3, start=200)
    outcomes = {p: {"ppg": 12.0 - i, "games_played": 6} for i, p in enumerate(paired + model_only + market_only)}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": 12.0 - i} for i, p in enumerate(paired + model_only)]
    market = [{"sleeper_id": p, "position": "WR", "value": 12.0 - i} for i, p in enumerate(paired + market_only)]

    card = _run(model, market, outcomes)
    wr = card["positions"]["WR"]

    assert wr["paired_n"] == 12
    assert wr["model_only_n"] == 5
    assert wr["market_only_n"] == 3
    # the paired metric is computed on the 12 alone, and says so
    assert wr["scored_on"] == "paired_only"
    assert card["coverage"]["model_only_n"] == 5
    assert card["coverage"]["market_only_n"] == 3
    assert card["coverage"]["paired_n"] == 12


def test_a_player_with_no_realized_outcome_cannot_enter_the_paired_metric() -> None:
    ids = _players(13)
    outcomes = {p: {"ppg": 13.0 - i, "games_played": 6} for i, p in enumerate(ids[:11])}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": 13.0 - i} for i, p in enumerate(ids)]
    market = [{"sleeper_id": p, "position": "WR", "value": 13.0 - i} for i, p in enumerate(ids)]

    wr = _run(model, market, outcomes)["positions"]["WR"]

    assert wr["paired_n"] == 11
    assert wr["no_outcome_n"] == 2


# ── honesty guards ───────────────────────────────────────────────────────────────────


def test_a_cohort_below_the_power_floor_surfaces_no_numbers() -> None:
    ids = _players(POWER_FLOOR_MIN_COHORT - 1)
    outcomes = {p: {"ppg": 9.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": 9.0 - i} for i, p in enumerate(ids)]
    market = [{"sleeper_id": p, "position": "WR", "value": 9.0 - i} for i, p in enumerate(ids)]

    wr = _run(model, market, outcomes)["positions"]["WR"]

    assert wr["status"] == "power_floor_not_met"
    assert wr["ndcg_diff"] is None
    assert wr["ndcg_diff_ci95"] is None
    assert wr["paired_n"] == POWER_FLOOR_MIN_COHORT - 1


def test_positions_are_scored_separately_and_never_pooled() -> None:
    wr_ids, rb_ids = _players(12), _players(11, position="RB")
    outcomes = {p: {"ppg": 15.0 - i, "games_played": 6} for i, p in enumerate(wr_ids + rb_ids)}
    model = ([{"sleeper_id": p, "position": "WR", "projection_2y": 15.0 - i} for i, p in enumerate(wr_ids)]
             + [{"sleeper_id": p, "position": "RB", "projection_2y": 15.0 - i} for i, p in enumerate(rb_ids)])
    market = ([{"sleeper_id": p, "position": "WR", "value": 15.0 - i} for i, p in enumerate(wr_ids)]
              + [{"sleeper_id": p, "position": "RB", "value": 15.0 - i} for i, p in enumerate(rb_ids)])

    card = _run(model, market, outcomes)

    assert set(card["positions"]) == {"WR", "RB"}
    assert card["positions"]["WR"]["paired_n"] == 12
    assert card["positions"]["RB"]["paired_n"] == 11
    assert "pooled" not in card


def test_the_scorer_never_scores_the_model_against_the_market() -> None:
    """Both sides are graded against realized outcomes. Agreeing with consensus earns nothing:
    a model identical to the market scores a difference of zero, not a win."""
    ids = _players(12)
    outcomes = {p: {"ppg": 12.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    market = [{"sleeper_id": p, "position": "WR", "value": 12.0 - i} for i, p in enumerate(ids)]
    twin = [{"sleeper_id": p, "position": "WR", "projection_2y": 12.0 - i} for i, p in enumerate(ids)]

    wr = _run(twin, market, outcomes)["positions"]["WR"]

    assert wr["ndcg_diff"] == pytest.approx(0.0, abs=1e-9)
    assert wr["beats_market"] is None


def test_a_non_finite_prediction_is_excluded_and_counted_not_silently_ranked() -> None:
    ids = _players(13)
    outcomes = {p: {"ppg": 13.0 - i, "games_played": 6} for i, p in enumerate(ids)}
    model = [{"sleeper_id": p, "position": "WR", "projection_2y": 13.0 - i} for i, p in enumerate(ids)]
    model[0]["projection_2y"] = float("nan")
    market = [{"sleeper_id": p, "position": "WR", "value": 13.0 - i} for i, p in enumerate(ids)]

    wr = _run(model, market, outcomes)["positions"]["WR"]

    assert wr["paired_n"] == 12
    assert wr["excluded"]["nonfinite_prediction"] == 1


# ── the runner: it must fire, store an honest artifact, and refuse loudly ────────────


def _runner():
    import importlib

    return importlib.import_module("scripts.run_model_vs_market_scoring")


def _frozen_rows(n=12, position="WR"):
    return [
        {"sleeper_id": f"{position}-{i}", "position": position, "projection_2y": 12.0 - i}
        for i in range(n)
    ]


def _market_rows(n=12, position="WR"):
    return [
        {"sleeper_id": f"{position}-{i}", "position": position, "value": 12.0 - i}
        for i in range(n)
    ]


def _outcome_rows(n=12, position="WR"):
    return {f"{position}-{i}": {"ppg": 12.0 - i, "games_played": 6} for i in range(n)}


def test_the_runner_writes_a_scorecard_carrying_the_declared_frozen_date(tmp_path) -> None:
    runner = _runner()
    report = tmp_path / "card.json"

    result = runner.run(
        season=2026,
        week=6,
        report_path=report,
        prediction_loader=lambda season: {
            "rows": _frozen_rows(),
            "frozen_capture_date": "2026-08-05",
            "declared_by": "David",
        },
        market_loader=lambda date: _market_rows(),
        outcome_loader=lambda season, week, predictions: {"outcomes": _outcome_rows(), "finalized_weeks": [1, 2, 3, 4, 5, 6]},
        week_finalized=lambda season, week: True,
    )

    import json

    assert result["status"] == "ok"
    assert result["frozen_capture_date"] == "2026-08-05"
    assert result["declared_by"] == "David"
    assert result["finalized_weeks"] == [1, 2, 3, 4, 5, 6]
    assert result["decision_supported"] is False
    assert json.loads(report.read_text()) == result


def test_the_runner_refuses_rather_than_grading_an_unfinished_week(tmp_path) -> None:
    runner = _runner()
    report = tmp_path / "card.json"

    result = runner.run(
        season=2026,
        week=1,
        report_path=report,
        prediction_loader=lambda season: {"rows": _frozen_rows(), "frozen_capture_date": "2026-08-05", "declared_by": "David"},
        market_loader=lambda date: _market_rows(),
        outcome_loader=lambda season, week, predictions: {"outcomes": {}, "finalized_weeks": []},
        week_finalized=lambda season, week: False,
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "week_not_finalized"
    assert not report.exists(), "a no-op must not leave a scorecard that looks like a grade"


def test_a_market_snapshot_missing_for_the_frozen_date_fails_loud(tmp_path) -> None:
    """Silently grading the model against nothing would report a win by construction."""
    runner = _runner()

    result = runner.run(
        season=2026,
        week=6,
        report_path=tmp_path / "card.json",
        prediction_loader=lambda season: {"rows": _frozen_rows(), "frozen_capture_date": "2026-08-05", "declared_by": "David"},
        market_loader=lambda date: [],
        outcome_loader=lambda season, week, predictions: {"outcomes": _outcome_rows(), "finalized_weeks": [1]},
        week_finalized=lambda season, week: True,
    )

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no_market_snapshot_for_frozen_date"


def test_finalized_weeks_with_no_outcomes_fails_loud_instead_of_reading_as_preseason(
    tmp_path,
) -> None:
    """The failure this test exists for: the identity bridge resolves sleeper ids FORWARD to
    gsis and has no reverse lookup. A runner that hedged the reverse direction would return
    zero outcomes for ever and report a healthy no-op every week of the season. Weeks have
    finalised and nothing resolved is a BREAKAGE, not an off-season."""
    runner = _runner()
    report = tmp_path / "card.json"

    result = runner.run(
        season=2026,
        week=6,
        report_path=report,
        prediction_loader=lambda season: {"rows": _frozen_rows(), "frozen_capture_date": "2026-08-05", "declared_by": "David"},
        market_loader=lambda date: _market_rows(),
        outcome_loader=lambda season, week, predictions: {"outcomes": {}, "finalized_weeks": [1, 2, 3, 4, 5, 6]},
        week_finalized=lambda season, week: True,
    )

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no_outcomes_for_finalized_weeks"
    assert not report.exists()


def test_no_finalized_weeks_is_a_quiet_preseason_noop(tmp_path) -> None:
    runner = _runner()

    result = runner.run(
        season=2026,
        week=6,
        report_path=tmp_path / "card.json",
        prediction_loader=lambda season: {"rows": _frozen_rows(), "frozen_capture_date": "2026-08-05", "declared_by": "David"},
        market_loader=lambda date: _market_rows(),
        outcome_loader=lambda season, week, predictions: {"outcomes": {}, "finalized_weeks": []},
        week_finalized=lambda season, week: True,
    )

    assert result["status"] == "noop"
    assert result["noop_reason"] == "no_finalized_weeks"
