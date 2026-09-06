"""DG-177 round 1, item 3 — annual outcomes on explicit seasonal events.

The served target is a two-season average on the event "posted a qualifying season
in t+1 OR t+2". The ranking lane needs one season at a time, on one event, with
exposure carried alongside: for season j after the feature season, did the player
APPEAR (>= 1 regular-season stat-row week), how many such games, how many PPR points.
Zero-appearance seasons are observations (0 games, 0 points, appeared = False), an
unfinished season is CENSORED (NaN, flagged), and an identity the source never saw is
unresolved (NaN, flagged) — never zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.annual_outcomes import (
    SCORING_COLUMN,
    annual_targets,
    season_outcomes,
)

WEEKLY_COLUMNS = ["player_id", "season", "week", "season_type", "position", SCORING_COLUMN]


def _weekly(rows):
    return pd.DataFrame(rows, columns=WEEKLY_COLUMNS)


#: A unit-test statement that the (tiny, hand-built) source was validated; the guard
#: itself is tested below with real defects.
VALIDATED = {"validated": True, "seasons": {}, "duplicate_rows": 0, "missing_points": 0, "missing_player_id": 0}


def test_scoring_column_is_nflverse_weekly_ppr():
    assert SCORING_COLUMN == "fantasy_points_ppr"


def test_season_outcomes_count_regular_season_stat_row_weeks_and_sum_ppr_points():
    weekly = _weekly([
        ("A", 2022, 1, "REG", "WR", 10.0),
        ("A", 2022, 2, "REG", "WR", 0.0),      # a stat row with zero points is still a game
        ("A", 2022, 19, "POST", "WR", 30.0),   # postseason is out of scope for the REG target
        ("B", 2022, 1, "REG", "RB", 5.5),
    ])
    out = season_outcomes(weekly, scope="REG", validation=VALIDATED).set_index(["player_id", "season"])
    assert out.loc[("A", 2022), "games"] == 2
    assert out.loc[("A", 2022), "points"] == pytest.approx(10.0)
    assert out.loc[("B", 2022), "games"] == 1
    assert out.loc[("B", 2022), "points"] == pytest.approx(5.5)
    assert out.attrs["scope"] == "REG"


def test_season_outcomes_all_games_scope_includes_postseason():
    weekly = _weekly([("A", 2022, 1, "REG", "WR", 10.0), ("A", 2022, 19, "POST", "WR", 30.0)])
    out = season_outcomes(weekly, scope="ALL", validation=VALIDATED).set_index(["player_id", "season"])
    assert out.loc[("A", 2022), "games"] == 2
    assert out.loc[("A", 2022), "points"] == pytest.approx(40.0)


def test_season_outcomes_refuses_an_unknown_scope():
    with pytest.raises(ValueError):
        season_outcomes(_weekly([]), scope="PLAYOFFS", validation=VALIDATED)


def _training():
    return pd.DataFrame({
        "player_id": ["A", "B", "C", "D"],
        "position": ["WR", "RB", "TE", "QB"],
        "feature_season": [2022, 2022, 2023, 2024],
    })


def _outcomes():
    # Outcomes span every pulled season, feature seasons included, so a feature player is
    # resolved by construction. A appears in 2023 and 2024; B in 2023 only; C never again
    # after 2023; D's future seasons are unplayed.
    out = pd.DataFrame({
        "player_id": ["A", "A", "B", "C", "D"],
        "season": [2023, 2024, 2023, 2023, 2024],
        "games": [15, 12, 3, 16, 10],
        "points": [200.0, 150.0, 20.0, 100.0, 50.0],
    })
    out.attrs["source_validation"] = dict(VALIDATED)
    out.attrs["scope"] = "REG"
    return out


def test_annual_targets_one_row_per_training_row_with_events_exposure_and_points():
    out = annual_targets(_training(), _outcomes(), horizons=(1, 2), last_complete_season=2024)
    assert len(out) == 4 and list(out["player_id"]) == ["A", "B", "C", "D"]
    a = out.set_index("player_id").loc["A"]
    assert a["season_year1"] == 2023 and a["season_year2"] == 2024
    assert a["appeared_year1"] == True and a["games_year1"] == 15 and a["points_year1"] == 200.0  # noqa: E712
    assert a["ppg_year1"] == pytest.approx(200.0 / 15)
    assert a["appeared_year2"] == True and a["games_year2"] == 12  # noqa: E712
    assert a["censored_year1"] == False and a["censored_year2"] == False  # noqa: E712


def test_a_zero_appearance_season_is_an_observation_not_a_missing_row():
    out = annual_targets(_training(), _outcomes(), horizons=(1, 2), last_complete_season=2024)
    b = out.set_index("player_id").loc["B"]           # 3 games in 2023, nothing in 2024
    assert b["appeared_year1"] == True and b["games_year1"] == 3  # noqa: E712  (3 games still appeared)
    assert b["appeared_year2"] == False and b["games_year2"] == 0 and b["points_year2"] == 0.0  # noqa: E712
    assert np.isnan(b["ppg_year2"])                   # a rate over zero games is undefined, not zero
    assert b["censored_year2"] == False  # noqa: E712


def test_an_unfinished_season_is_censored_not_zero():
    out = annual_targets(_training(), _outcomes(), horizons=(1, 2), last_complete_season=2024)
    c = out.set_index("player_id").loc["C"]           # feature 2023: year1 = 2024 known, year2 = 2025 unplayed
    assert c["appeared_year1"] == False and c["games_year1"] == 0  # noqa: E712
    assert c["censored_year2"] == True  # noqa: E712
    assert pd.isna(c["appeared_year2"]) and np.isnan(c["games_year2"]) and np.isnan(c["points_year2"])
    d = out.set_index("player_id").loc["D"]           # feature 2024: both horizons unplayed
    assert d["censored_year1"] == True and d["censored_year2"] == True  # noqa: E712


def test_an_identity_the_source_never_saw_is_unresolved_not_zero():
    training = pd.DataFrame({"player_id": ["Z"], "position": ["WR"], "feature_season": [2022]})
    out = annual_targets(training, _outcomes(), horizons=(1,), last_complete_season=2024).iloc[0]
    assert out["identity_status"] == "unresolved_in_source"
    assert pd.isna(out["appeared_year1"]) and np.isnan(out["games_year1"])
    assert out["censored_year1"] == False  # noqa: E712
    resolved = annual_targets(_training(), _outcomes(), horizons=(1,), last_complete_season=2024)
    assert set(resolved["identity_status"]) == {"resolved"}


def test_targets_carry_their_definition():
    out = annual_targets(_training(), _outcomes(), horizons=(1,), last_complete_season=2024)
    assert out.attrs["event"] == "appeared: >= 1 stat-row game in the season"
    assert out.attrs["label_window_seasons"] == {"year1": 1}
    assert out.attrs["last_complete_season"] == 2024


# ── round 2, item 3: missing source coverage must never become a known zero ──

from src.dynasty_genius.eval.annual_outcomes import (  # noqa: E402
    SourceIncompleteError,
    validate_weekly_source,
)


def _full_weekly(seasons=(2022, 2023), players=("A", "B", "C"), reg_weeks=None):
    rows = []
    for s in seasons:
        n = reg_weeks or (18 if s >= 2021 else 17)
        for p in players:
            for w in range(1, n + 1):
                rows.append((p, s, w, "REG", "WR", 5.0))
            rows.append((p, s, n + 1, "POST", "WR", 5.0))
    return _weekly(rows)


def test_a_complete_source_passes_and_reports_facts():
    facts = validate_weekly_source(_full_weekly(), seasons=[2022, 2023], min_players_per_season=3)
    assert facts["seasons"]["2022"]["reg_weeks"] == 18 and facts["seasons"]["2023"]["players"] == 3
    assert facts["duplicate_rows"] == 0 and facts["missing_points"] == 0 and facts["missing_player_id"] == 0
    assert facts["validated"] is True


def test_a_missing_scoring_value_is_refused_not_zeroed():
    weekly = _full_weekly()
    weekly.loc[3, SCORING_COLUMN] = np.nan
    with pytest.raises(SourceIncompleteError, match="missing"):
        validate_weekly_source(weekly, seasons=[2022, 2023], min_players_per_season=3)


def test_a_season_absent_from_the_source_is_refused():
    with pytest.raises(SourceIncompleteError, match="2024"):
        validate_weekly_source(_full_weekly(), seasons=[2022, 2023, 2024], min_players_per_season=3)


def test_a_short_season_is_refused():
    with pytest.raises(SourceIncompleteError, match="weeks"):
        validate_weekly_source(_full_weekly(reg_weeks=12), seasons=[2022, 2023], min_players_per_season=3)


def test_duplicate_player_weeks_are_refused():
    weekly = _full_weekly()
    weekly = pd.concat([weekly, weekly.iloc[[0]]], ignore_index=True)
    with pytest.raises(SourceIncompleteError, match="duplicate"):
        validate_weekly_source(weekly, seasons=[2022, 2023], min_players_per_season=3)


def test_too_few_players_is_refused():
    with pytest.raises(SourceIncompleteError, match="players"):
        validate_weekly_source(_full_weekly(), seasons=[2022, 2023], min_players_per_season=50)


def test_outcomes_and_targets_refuse_an_unvalidated_source():
    weekly = _full_weekly()
    with pytest.raises(SourceIncompleteError, match="validated"):
        season_outcomes(weekly, scope="REG")                     # no validation facts attached
    facts = validate_weekly_source(weekly, seasons=[2022, 2023], min_players_per_season=3)
    out = season_outcomes(weekly, scope="REG", validation=facts)
    assert out.attrs["source_validation"]["validated"] is True
    training = pd.DataFrame({"player_id": ["A"], "position": ["WR"], "feature_season": [2022]})
    targets = annual_targets(training, out, horizons=(1,), last_complete_season=2023)
    assert targets.attrs["source_validation"]["validated"] is True
    unvalidated = out.copy()
    unvalidated.attrs = {}
    with pytest.raises(SourceIncompleteError, match="validated"):
        annual_targets(training, unvalidated, horizons=(1,), last_complete_season=2023)


def test_unattributed_zero_rows_are_dropped_and_counted_but_an_unattributed_stat_line_is_refused():
    from src.dynasty_genius.eval.annual_outcomes import drop_unattributed_zero_rows

    weekly = _full_weekly()
    filler = pd.DataFrame([(None, 2022, w, "REG", None, 0.0) for w in range(1, 19)], columns=WEEKLY_COLUMNS)
    kept, facts = drop_unattributed_zero_rows(pd.concat([weekly, filler], ignore_index=True))
    assert len(kept) == len(weekly) and facts["unattributed_zero_rows_dropped"] == 18
    validated = validate_weekly_source(kept, seasons=[2022, 2023], min_players_per_season=3)
    assert validated["validated"] is True
    with_points = pd.concat([weekly, pd.DataFrame([(None, 2022, 1, "REG", "WR", 12.0)], columns=WEEKLY_COLUMNS)],
                            ignore_index=True)
    with pytest.raises(SourceIncompleteError, match="unattributed"):
        drop_unattributed_zero_rows(with_points)


def test_an_unattributed_stat_line_within_the_stated_tolerance_is_dropped_and_listed_above_it_refused():
    from src.dynasty_genius.eval.annual_outcomes import drop_unattributed_zero_rows

    weekly = _full_weekly()
    stray = pd.DataFrame([(None, 2022, 6, "REG", None, 3.1)], columns=WEEKLY_COLUMNS)
    kept, facts = drop_unattributed_zero_rows(pd.concat([weekly, stray], ignore_index=True), tolerated_points_per_season=10.0)
    assert len(kept) == len(weekly)
    assert facts["unattributed_stat_lines_dropped"] == [
        {"season": 2022, "week": 6, "season_type": "REG", "position": None, "points": 3.1}
    ]
    assert facts["unattributed_points_dropped_by_season"] == {"2022": 3.1}
    big = pd.DataFrame([(None, 2022, 6, "REG", None, 30.0)], columns=WEEKLY_COLUMNS)
    with pytest.raises(SourceIncompleteError, match="tolerance"):
        drop_unattributed_zero_rows(pd.concat([weekly, big], ignore_index=True), tolerated_points_per_season=10.0)
