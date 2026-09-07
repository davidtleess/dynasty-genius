"""DG-178 round 2 — the eligible universe, proven, not assumed from scored rows.

Every row the audit counts comes from one of: the artifact's fantasy-relevant skill rows,
or a league roster (any position — a rostered player is eligible by the fact of being
rostered). Multi-position eligibility cannot be verified here because the capture keeps
only Sleeper's single `position` string and not `fantasy_positions`; that is stated on the
row, never inferred.
"""
from __future__ import annotations


def _artifact_rows():
    return [
        {"sleeper_player_id": "1", "dg_player_id": "00-0000001", "cohort": "FANTASY_RELEVANT",
         "player": {"full_name": "Skill Guy", "position": "WR", "team": "NYJ", "age": 25}},
        {"sleeper_player_id": "2", "dg_player_id": "00-0000002", "cohort": "INACTIVE",
         "player": {"full_name": "Retired Guy", "position": "RB", "team": None, "age": 34}},
        {"sleeper_player_id": "3", "dg_player_id": "00-0000003", "cohort": "CONTEXT_ONLY",
         "player": {"full_name": "Travis Hunter", "position": "DB", "team": "JAX", "age": 22}},
        {"sleeper_player_id": "4", "dg_player_id": "00-0000004", "cohort": "EXCLUDED",
         "player": {"full_name": "A Kicker", "position": "K", "team": "DAL", "age": 30}},
        {"sleeper_player_id": "5", "dg_player_id": "00-0000005", "cohort": "FANTASY_RELEVANT",
         "player": {"full_name": "Tank Dell", "position": "WR", "team": "HOU", "age": 26}},
    ]


def _snapshot():
    return {"david_roster_id": 1, "rosters": [
        {"roster_id": 1, "players": ["5"], "taxi": [], "reserve": ["5"]},
        {"roster_id": 5, "players": ["3"], "taxi": [], "reserve": []},
    ]}


def test_the_universe_is_fantasy_relevant_rows_plus_every_rostered_player() -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    u = eligible_universe(_artifact_rows(), _snapshot())
    by = {r.sleeper_id: r for r in u.rows}
    assert set(by) == {"1", "3", "5"}
    assert by["1"].eligibility == "fantasy_relevant" and by["1"].rostered is False
    assert by["3"].eligibility == "rostered_non_skill_position" and by["3"].roster_id == 5
    assert by["3"].multi_position_note is not None and "fantasy_positions" in by["3"].multi_position_note
    assert by["5"].rostered is True and by["5"].roster_id == 1 and by["5"].on_reserve is True
    assert u.excluded == {"INACTIVE": 1, "EXCLUDED": 1}


def test_the_universe_carries_gsis_and_can_be_written_as_a_csv(tmp_path) -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    u = eligible_universe(_artifact_rows(), _snapshot())
    p = u.write_csv(tmp_path / "universe.csv")
    text = p.read_text()
    assert "sleeper_id,gsis_id,name,position,eligibility,rostered,roster_id" in text.splitlines()[0]
    assert "00-0000005" in text and "Tank Dell" in text


def test_forecast_coverage_is_marked_per_universe_row_never_by_scored_rows_only() -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    u = eligible_universe(_artifact_rows(), _snapshot())
    u.mark_forecast({"00-0000001"}, producer="vet")
    by = {r.sleeper_id: r for r in u.rows}
    assert by["1"].forecast_by == "vet"
    assert by["5"].forecast_by is None
    assert u.census()["unforecast"] == 2


def test_rookie_forecasts_are_marked_by_draft_pick_when_the_row_has_no_gsis() -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    rows = _artifact_rows() + [{"sleeper_player_id": "9", "dg_player_id": "9", "cohort": "FANTASY_RELEVANT",
                                "nfl_draft_pick": 3, "draft_class": 2026,
                                "player": {"full_name": "Rookie Back", "position": "RB", "team": "ARI", "age": 21}}]
    u = eligible_universe(rows, _snapshot())
    u.mark_forecast(set(), producer="rookie", picks={("RB", 2026, 3)})
    by = {r.sleeper_id: r for r in u.rows}
    assert by["9"].forecast_by == "rookie" and by["9"].nfl_draft_pick == 3 and by["9"].draft_class == 2026


def test_rookie_forecast_marking_joins_on_draft_season_and_pick_alone() -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    rows = _artifact_rows() + [{"sleeper_player_id": "9", "dg_player_id": "9", "cohort": "FANTASY_RELEVANT",
                                "nfl_draft_pick": 159, "draft_class": 2026,
                                "player": {"full_name": "Max Bredeson", "position": "RB", "team": "MIN", "age": 23}}]
    u = eligible_universe(rows, _snapshot())
    u.mark_forecast(set(), producer="rookie", picks={("TE", 2026, 159)})
    assert {r.sleeper_id: r for r in u.rows}["9"].forecast_by == "rookie"


def test_a_producers_reconciliation_statuses_become_the_stated_reason_on_each_row(tmp_path) -> None:
    """Lane 23481 reconciles every universe row with one status (forecast, no_gsis_mapping,
    left_cohort_two_absent_seasons, no_nfl_history, position_outside_modelled_set). The
    universe carries that status as the producer's own statement, keyed by sleeper id."""
    from src.dynasty_genius.ranking.universe import eligible_universe

    p = tmp_path / "recon.csv"
    p.write_text("sleeper_id,name,position,rostered,gsis_id,status,cohort_position,games_2025\n"
                 "5,Tank Dell,WR,True,00-0038977,forecast,WR,0\n"
                 "3,Travis Hunter,DB,True,00-0040718,position_outside_modelled_set,CB,17\n"
                 "1,Skill Guy,WR,False,,no_gsis_mapping,,\n")
    rows = [dict(r, dg_player_id="9502") if r["sleeper_player_id"] == "5" else r for r in _artifact_rows()]
    u = eligible_universe(rows, _snapshot())  # Dell's artifact row carries no gsis, as in the real artifact
    u.apply_reconciliation(p, producer="vet_basic")
    by = {r.sleeper_id: r for r in u.rows}
    assert by["5"].reconciliation == {"vet_basic": "forecast"} and by["5"].gsis_id == "00-0038977"
    assert by["5"].forecast_by == "vet_basic"  # the producer's own "forecast" status marks the row
    assert by["3"].reconciliation == {"vet_basic": "position_outside_modelled_set"}
    assert "CB" in (by["3"].forecast_reason or "")
    assert by["1"].reconciliation == {"vet_basic": "no_gsis_mapping"}
