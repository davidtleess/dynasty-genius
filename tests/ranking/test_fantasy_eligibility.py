"""Sleeper fantasy eligibility (lane 24974's capture, 2026-09-06 16:41Z) is the placement
authority: a player's league position is the fantasy position Sleeper lets him fill, never
inferred from the NFL or draft position. A missing field stays unknown."""
from __future__ import annotations

from src.dynasty_genius.ranking.served_rows import (
    ServedRow,
    apply_fantasy_eligibility,
    league_placement,
)


def _row(sid, pos, name="X"):
    return ServedRow(player_id=f"dg-{sid}", sleeper_id=sid, full_name=name, position=pos, age=25,
                     dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                     projection_2y=None, captured_at="x")


ELIG = {
    "13516": {"fantasy_positions": "RB", "status": "Active"},          # Bredeson: draft table TE, Sleeper RB
    "13433": {"fantasy_positions": "TE", "status": "Active"},          # Nowakowski: nflverse FB, Sleeper TE
    "12530": {"fantasy_positions": "DB|WR", "status": "Active"},       # Hunter: WR-eligible
    "9502": {"fantasy_positions": "WR", "status": "Inactive"},         # Dell: not on an NFL roster
    "4046": {"fantasy_positions": "QB", "status": "Active"},
    "777": {"fantasy_positions": "", "status": "Active"},              # field missing: unknown, never inferred
}


def test_league_placement_prefers_the_artifact_position_when_eligible_else_the_first_skill_position() -> None:
    assert league_placement("TE", ("RB",)) == "RB"
    assert league_placement("CB", ("DB", "WR")) == "WR"
    assert league_placement("DB", ("DB", "WR")) == "WR"       # DB is a Sleeper fantasy position, not a slot David can start
    assert league_placement("QB", ("QB",)) == "QB"
    assert league_placement("WR", ("WR", "RB")) == "WR"        # eligible at his own position: unchanged
    assert league_placement("TE", ()) == "TE"                   # unknown: unchanged
    assert league_placement("K", ("K",)) == "K"                 # no skill position among them: unchanged


def test_apply_fantasy_eligibility_moves_bredeson_to_rb_keeps_nowakowski_at_te_and_makes_hunter_a_wr() -> None:
    rows = [_row("13516", "TE", "Max Bredeson"), _row("13433", "TE", "Riley Nowakowski"),
            _row("12530", "CB", "Travis Hunter"), _row("9502", "WR", "Tank Dell"), _row("4046", "QB"),
            _row("777", "RB"), _row("999", "WR")]
    out = {r.sleeper_id: r for r in apply_fantasy_eligibility(rows, ELIG)}
    assert out["13516"].position == "RB" and out["13516"].placement_source == "sleeper_fantasy_positions"
    assert out["13433"].position == "TE"
    assert out["12530"].position == "WR" and out["12530"].fantasy_positions == ("DB", "WR")
    assert out["9502"].position == "WR" and out["9502"].nfl_status == "Inactive"
    assert out["4046"].nfl_status == "Active"
    assert out["777"].position == "RB" and out["777"].fantasy_positions is None and out["777"].placement_source is None
    assert out["999"].position == "WR" and out["999"].nfl_status is None  # absent from the capture: unknown


def test_the_universe_places_players_by_fantasy_eligibility_when_supplied() -> None:
    from src.dynasty_genius.ranking.universe import eligible_universe

    players = [
        {"sleeper_player_id": "12530", "cohort": "FANTASY_RELEVANT", "player": {"full_name": "Travis Hunter", "position": "CB", "team": "JAX", "age": 23}},
        {"sleeper_player_id": "13516", "cohort": "FANTASY_RELEVANT", "player": {"full_name": "Max Bredeson", "position": "TE", "team": "MIN", "age": 23}},
    ]
    snapshot = {"david_roster_id": 1, "rosters": [{"roster_id": 2, "players": ["12530"], "taxi": [], "reserve": []}]}
    u = eligible_universe(players, snapshot, eligibility=ELIG)
    by = {r.sleeper_id: r for r in u.rows}
    assert by["12530"].position == "WR" and by["12530"].eligibility == "fantasy_relevant" and by["12530"].nfl_status == "Active"
    assert by["12530"].multi_position_note is None  # he IS a skill-position player in David's league
    assert by["13516"].position == "RB"
    # without the capture the artifact position stands and Hunter is the rostered non-skill row
    u2 = eligible_universe(players, snapshot)
    assert {r.sleeper_id: r.position for r in u2.rows} == {"12530": "CB", "13516": "TE"}


def test_the_replacement_reference_carries_the_bar_players_nfl_status() -> None:
    from pathlib import Path

    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
    )

    fx = Path(__file__).parent / "fixtures"
    c = AnnualCandidate.load(fx / "annual_candidate_fixture.csv", fx / "annual_candidate_manifest.json")
    # fixture WR fa1 (sleeper 201) is the bar; mark him Inactive in the capture
    rows = apply_fantasy_eligibility([_row("201", "WR", "Free Agent One")], {"201": {"fantasy_positions": "WR", "status": "Inactive"}})
    refs = annual_replacement([c], rostered_ids={"101", "102", "401"}, snapshot_id="s", positions=["WR"], served_rows=rows)
    ref = refs["WR"][0]
    assert ref.reference_nfl_status == "Inactive"
    assert "not on an NFL roster" in (ref.pool_note or "")


def test_reading_the_capture_file_keys_by_sleeper_id(tmp_path) -> None:
    from src.dynasty_genius.ranking.served_rows import read_fantasy_eligibility

    p = tmp_path / "sleeper_eligibility.csv"
    p.write_text("sleeper_id,full_name,position,fantasy_positions,active,status,team,injury_status,years_exp,gsis_id\n"
                 "12530,Travis Hunter,DB,DB|WR,True,Active,JAX,,1.0,00-0040000\n")
    e = read_fantasy_eligibility(p)
    assert e["12530"]["fantasy_positions"] == "DB|WR" and e["12530"]["status"] == "Active"


def test_the_artifact_loader_places_rows_before_filtering_so_a_db_wr_joins_the_skill_rows(tmp_path) -> None:
    import json

    from src.dynasty_genius.ranking.served_rows import ServedArtifact

    art = {"captured_at": "x", "players": [
        {"sleeper_player_id": "12530", "dg_player_id": "00-0040718", "player": {"full_name": "Travis Hunter", "position": "CB", "team": "JAX", "age": 23},
         "valuation": {}},
        {"sleeper_player_id": "4046", "dg_player_id": "00-0033873", "player": {"full_name": "Patrick Mahomes", "position": "QB", "team": "KC", "age": 30},
         "valuation": {}},
        {"sleeper_player_id": "1", "dg_player_id": "00-0000001", "player": {"full_name": "A Kicker", "position": "K", "team": "DAL", "age": 30}, "valuation": {}},
    ]}
    p = tmp_path / "art.json"
    p.write_text(json.dumps(art))
    plain = ServedArtifact.load(p)
    assert [r.full_name for r in plain.rows] == ["Patrick Mahomes"] and plain.other_positions["12530"] == "CB"
    placed = ServedArtifact.load(p, eligibility=ELIG)
    by = {r.sleeper_id: r for r in placed.rows}
    assert by["12530"].position == "WR" and by["12530"].placement_source == "sleeper_fantasy_positions"
    assert by["4046"].nfl_status == "Active" and "12530" not in placed.other_positions
    assert placed.other_positions["1"] == "K"
