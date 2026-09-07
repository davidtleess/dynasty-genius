"""The current-player census (Codex, Week-17 queue, 2026-09-06): who is a current NFL player
today, joined to the full Sleeper eligibility snapshot. Sleeper's active/team flags never
define membership (retired Roethlisberger carries Active+PIT); a dated nflverse roster does,
plus every player David's league owns regardless of flags. Joins are explicit, never guessed."""
from __future__ import annotations

from src.dynasty_genius.ranking.nfl_census import (
    DENOMINATOR_DEFINITION,
    build_census,
    classify_nfl_status,
)


def _sleeper(sid, name, pos, fps, status="Active", team="", gsis=""):
    return {"sleeper_id": sid, "full_name": name, "position": pos, "fantasy_positions": fps, "active": "True",
            "status": status, "team": team, "injury_status": "", "years_exp": "3.0", "gsis_id": gsis}


def _nfl(name, team, pos, status, sleeper_id="", gsis=""):
    return {"season": "2026", "week": "1", "team": team, "position": pos, "status": status, "full_name": name,
            "sleeper_id": sleeper_id, "gsis_id": gsis}


SLEEPER = [
    _sleeper("138", "Ben Roethlisberger", "QB", "QB", "Active", "PIT", "00-0022924"),   # retired; Sleeper still Active+PIT
    _sleeper("9502", "Tank Dell", "WR", "WR", "Inactive", "HOU", ""),                    # league-owned, IR, no Sleeper gsis
    _sleeper("12530", "Travis Hunter", "DB", "DB|WR", "Active", "JAX", ""),
    _sleeper("13516", "Max Bredeson", "RB", "RB", "Active", "MIN", "00-0041081"),        # nflverse row lacks his Sleeper id
    _sleeper("4046", "Patrick Mahomes", "QB", "QB", "Active", "KC", "00-0033873"),
    _sleeper("777", "Practice Guy", "WR", "WR", "Active", "DAL", ""),
    _sleeper("888", "Conflict Guy", "RB", "RB", "Active", "NYJ", "00-0099999"),          # Sleeper gsis disagrees with nflverse
    _sleeper("999", "Owned Ghost", "TE", "TE", "Inactive", "", ""),                       # owned, nowhere in nflverse
    _sleeper("555", "A Kicker", "K", "K", "Active", "DAL", "00-0055555"),                 # not a skill position: outside
]
NFL = [
    _nfl("Tank Dell", "HOU", "WR", "RES", "9502", "00-0038977"),
    _nfl("Travis Hunter", "JAX", "WR", "ACT", "12530", "00-0040718"),
    _nfl("Max Bredeson", "MIN", "RB", "ACT", "", "00-0041081"),
    _nfl("Patrick Mahomes", "KC", "QB", "ACT", "4046", "00-0033873"),
    _nfl("Practice Guy", "DAL", "WR", "DEV", "777", "00-0077777"),
    _nfl("Conflict Guy", "NYJ", "RB", "ACT", "888", "00-0088888"),
    _nfl("Cut Guy", "SEA", "WR", "CUT", "", "00-0066666"),
]
OWNED = {"9502": 1, "999": 4, "4046": 2}


def test_nflverse_statuses_map_onto_named_availability_classes_and_unknown_strings_stay_visible() -> None:
    assert classify_nfl_status("ACT") == "active"
    assert classify_nfl_status("RES") == "injured_reserve"
    assert classify_nfl_status("PUP") == "pup"
    assert classify_nfl_status("NON") == "nfi"
    assert classify_nfl_status("DEV") == "practice_squad"
    assert classify_nfl_status("EXE") == "exempt"
    assert classify_nfl_status("SUS") == "suspended"
    assert classify_nfl_status("CUT") == "cut"
    assert classify_nfl_status("RET") == "retired"
    assert classify_nfl_status("ZZZ") == "other:ZZZ"


def test_the_census_is_nfl_roster_membership_plus_league_ownership_never_sleepers_flags() -> None:
    c = build_census(SLEEPER, NFL, league_owned=OWNED, season=2026)
    by = {r.sleeper_id: r for r in c.rows}
    # retired but Active+PIT on Sleeper: NOT in the census, listed as uncovered with the reason
    assert "138" not in by
    unc = {u.sleeper_id: u for u in c.uncovered}
    assert unc["138"].reason.startswith("no verified join to the captured 2026 roster (Sleeper flags Active/PIT")
    # owned + IR + no Sleeper gsis: in, by Sleeper id, injured_reserve, kept because owned AND on a roster
    assert by["9502"].availability_class == "injured_reserve" and by["9502"].league_owned and by["9502"].roster_id == 1
    assert by["9502"].join_basis == "sleeper_id" and by["9502"].nfl_gsis_id == "00-0038977" and by["9502"].sleeper_gsis_id == ""
    # Hunter: nflverse WR/ACT; league placement WR from fantasy_positions; nflverse position recorded separately
    assert by["12530"].availability_class == "active" and by["12530"].league_position == "WR" and by["12530"].nfl_position == "WR"
    # Bredeson: nflverse row has no Sleeper id -> joined on gsis, stated
    assert by["13516"].join_basis == "gsis_id" and by["13516"].availability_class == "active"
    # practice squad is its own class
    assert by["777"].availability_class == "practice_squad"
    # identity conflict: joined by Sleeper id but the gsis ids disagree -> flagged, class unknown, never guessed
    assert by["888"].identity_conflict == "sleeper gsis 00-0099999 != nflverse gsis 00-0088888 on the sleeper_id join"
    assert by["888"].availability_class == "unknown"
    # owned but nowhere in nflverse: kept (ownership), class not_on_nfl_roster_2026, join none
    assert by["999"].league_owned and by["999"].availability_class == "no_verified_join_to_2026_roster" and by["999"].join_basis == "none"
    # a kicker is outside the skill population and never counted
    assert "555" not in by and "555" not in unc
    # a nflverse row no Sleeper player claims is reported, not silently dropped
    assert c.nfl_rows_unclaimed == [("Cut Guy", "SEA", "WR", "CUT", "00-0066666")]


def test_the_report_states_the_denominator_hashes_coverage_by_class_and_position_and_every_uncovered_id() -> None:
    c = build_census(SLEEPER, NFL, league_owned=OWNED, season=2026,
                     sources={"nflverse_roster": {"sha256": "a" * 64, "captured_at": "t1"},
                              "sleeper_eligibility": {"sha256": "b" * 64, "captured_at": "t0"}})
    rep = c.report()
    assert rep["denominator"] == DENOMINATOR_DEFINITION
    assert rep["sources"]["nflverse_roster"]["sha256"] == "a" * 64
    assert rep["counts"]["by_class"]["active"] == 3 and rep["counts"]["by_class"]["injured_reserve"] == 1
    assert rep["counts"]["by_class_and_position"]["WR"]["active"] == 1
    assert rep["counts"]["by_join_basis"] == {"sleeper_id": 5, "gsis_id": 1, "none": 1}
    assert rep["counts"]["league_owned"] == 3 and rep["counts"]["identity_conflicts"] == 1
    assert [u["sleeper_id"] for u in rep["uncovered"]] == ["138"]   # the FULL list, not a count
    assert list(rep["counts"]["uncovered_by_reason"].values()) == [1]
    assert list(rep["counts"]["uncovered_by_reason"])[0].startswith("no verified join to the captured 2026 roster")
    assert rep["sleeper_flags_are_membership"] is False


def test_a_verified_identity_bridge_joins_a_rookie_whose_nflverse_row_lacks_a_sleeper_id_and_says_so() -> None:
    """Max Bredeson: Sleeper has no gsis for 2026 rookies and nflverse's row has no Sleeper id,
    so neither direct key joins. Lane 24974's verified canonical (Sleeper id -> gsis) map does,
    and the row records that it came through the bridge — it never becomes a forecast."""
    sleeper = [_sleeper("13516", "Max Bredeson", "RB", "RB", "Active", "MIN", ""),
               _sleeper("13999", "Bridge Conflict", "WR", "WR", "Active", "SF", "00-0011111")]
    nfl = [_nfl("Max Bredeson", "MIN", "RB", "ACT", "", "00-0041081"),
           _nfl("Bridge Conflict", "SF", "WR", "ACT", "", "00-0022222")]
    bridge = {"13516": "00-0041081", "13999": "00-0022222"}
    c = build_census(sleeper, nfl, league_owned={}, season=2026, identity_bridge=bridge,
                     sources={"identity_bridge": {"path": "reconciliation.csv", "sha256": "c" * 64}})
    by = {r.sleeper_id: r for r in c.rows}
    assert by["13516"].join_basis == "gsis_id_via_bridge" and by["13516"].availability_class == "active"
    assert by["13516"].nfl_gsis_id == "00-0041081" and by["13516"].sleeper_gsis_id == ""
    # Sleeper's own gsis disagrees with the bridge: an explicit conflict, class unknown
    assert by["13999"].identity_conflict == "sleeper gsis 00-0011111 != bridge gsis 00-0022222"
    assert by["13999"].availability_class == "unknown"
    assert c.report()["counts"]["by_join_basis"] == {"gsis_id_via_bridge": 2}


# ── Codex's census review (2026-09-06 evening): real counterexamples, RED first ────────────
def test_one_nfl_record_claimed_by_two_sleeper_rows_quarantines_both_and_never_makes_either_active() -> None:
    """Tyler Conklin (Sleeper 5133, Sleeper gsis 00-0034439) joins nflverse's Conklin row
    (gsis 00-0034270) by Sleeper id — a gsis conflict. Ryan Izzo (Sleeper 5094) carries Sleeper
    gsis 00-0034270 and, through the gsis fallback, claimed the SAME nflverse record and came
    out ACTIVE/DET. Neither source is presumed right: both claimants are quarantined as unknown
    with the multiple-claim note, and the record counts once as contested."""
    sleeper = [_sleeper("5133", "Tyler Conklin", "TE", "TE", "Active", "DET", "00-0034439"),
               _sleeper("5094", "Ryan Izzo", "TE", "TE", "Active", "", "00-0034270")]
    nfl = [_nfl("Tyler Conklin", "DET", "TE", "ACT", "5133", "00-0034270")]
    c = build_census(sleeper, nfl, league_owned={"5133": 3}, season=2026)
    by = {r.sleeper_id: r for r in c.rows}
    assert by["5133"].availability_class == "unknown" and by["5133"].league_owned  # owned Conklin kept, unknown
    assert by["5094"].availability_class == "unknown" and by["5094"].nfl_team is None
    assert "claimed by 2 Sleeper rows" in by["5094"].identity_conflict and "5133" in by["5094"].identity_conflict
    assert "claimed by 2 Sleeper rows" in by["5133"].identity_conflict
    assert c.report()["counts"]["by_class"].get("active", 0) == 0
    assert c.report()["counts"]["contested_nfl_records"] == 1
    assert c.report()["contested_nfl_records"][0]["nfl_gsis_id"] == "00-0034270"
    assert sorted(c.report()["contested_nfl_records"][0]["claimants"]) == ["5094", "5133"]


def test_duplicate_source_keys_are_refused_never_overwritten() -> None:
    import pytest

    nfl_dup_sid = [_nfl("A", "KC", "QB", "ACT", "4046", "00-1"), _nfl("B", "DEN", "QB", "ACT", "4046", "00-2")]
    with pytest.raises(ValueError, match="sleeper_id"):
        build_census([_sleeper("4046", "A", "QB", "QB")], nfl_dup_sid, league_owned={}, season=2026)
    nfl_dup_gsis = [_nfl("A", "KC", "QB", "ACT", "", "00-1"), _nfl("B", "DEN", "QB", "ACT", "", "00-1")]
    with pytest.raises(ValueError, match="gsis_id"):
        build_census([_sleeper("4046", "A", "QB", "QB", gsis="00-1")], nfl_dup_gsis, league_owned={}, season=2026)
    with pytest.raises(ValueError, match="sleeper_id"):
        build_census([_sleeper("1", "A", "QB", "QB"), _sleeper("1", "A", "QB", "QB")], [], league_owned={}, season=2026)


def test_an_owned_id_absent_from_the_sleeper_capture_is_retained_as_an_explicit_unknown_row() -> None:
    c = build_census([], [], league_owned={"owned": 1}, season=2026)
    assert len(c.rows) == 1
    r = c.rows[0]
    assert r.sleeper_id == "owned" and r.league_owned and r.roster_id == 1
    assert r.availability_class == "unknown" and r.join_basis == "none" and r.league_position == "?"
    assert r.identity_conflict == "owned Sleeper id absent from the Sleeper eligibility capture; identity and eligibility unknown"
    assert c.report()["counts"]["owned_absent_from_sleeper_capture"] == 1


def test_a_failed_join_is_worded_as_unverified_not_as_proof_of_absence_and_unclaimed_rows_keep_their_statuses() -> None:
    c = build_census(SLEEPER, NFL, league_owned=OWNED, season=2026)
    unc = {u.sleeper_id: u for u in c.uncovered}
    assert unc["138"].reason == ("no verified join to the captured 2026 roster (Sleeper flags Active/PIT are not membership); "
                                 "absence from the NFL is not proven")
    by = {r.sleeper_id: r for r in c.rows}
    assert by["999"].availability_class == "no_verified_join_to_2026_roster"
    rep = c.report()
    assert rep["counts"]["nfl_rows_unclaimed_by_status"] == {"CUT": 1}
    assert rep["counts"]["active_nfl"] == 3 and rep["counts"]["listed_or_owned"] == rep["counts"]["members"]
    assert "NOT a count of active NFL players" in rep["denominator_note"]


def test_the_roster_capture_is_validated_against_its_manifest_season_and_columns(tmp_path) -> None:
    import hashlib
    import json

    import pytest

    from src.dynasty_genius.ranking.nfl_census import load_nfl_roster

    good = ("season,team,position,status,full_name,gsis_id,sleeper_id,week\n"
            "2026,KC,QB,ACT,Patrick Mahomes,00-0033873,4046,1\n").encode()
    p = tmp_path / "roster_2026.csv"
    p.write_bytes(good)
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"sha256": hashlib.sha256(good).hexdigest(), "rows": 1, "season": 2026}))
    rows = load_nfl_roster(p, man, season=2026)
    assert rows[0]["sleeper_id"] == "4046"
    with pytest.raises(ValueError, match="manifest"):
        load_nfl_roster(p, tmp_path / "missing.json", season=2026)
    man.write_text(json.dumps({"sha256": "0" * 64, "rows": 1, "season": 2026}))
    with pytest.raises(ValueError, match="sha256"):
        load_nfl_roster(p, man, season=2026)
    bad = good.replace(b"2026,KC", b"2025,KC")
    p.write_bytes(bad)
    man.write_text(json.dumps({"sha256": hashlib.sha256(bad).hexdigest(), "rows": 1, "season": 2026}))
    with pytest.raises(ValueError, match="season"):
        load_nfl_roster(p, man, season=2026)
    nocol = b"season,team,full_name\n2026,KC,X\n"
    p.write_bytes(nocol)
    man.write_text(json.dumps({"sha256": hashlib.sha256(nocol).hexdigest(), "rows": 1, "season": 2026}))
    with pytest.raises(ValueError, match="columns"):
        load_nfl_roster(p, man, season=2026)


def test_identity_bridges_refuse_conflicting_mappings_instead_of_first_file_wins() -> None:
    import pytest

    from src.dynasty_genius.ranking.nfl_census import merge_identity_bridges

    a = [{"sleeper_id": "1", "my_gsis_id": "00-1"}, {"sleeper_id": "2", "gsis_id": "00-2"}]
    b = [{"sleeper_id": "3", "gsis_id": "00-3"}, {"sleeper_id": "1", "gsis_id": "00-1"}]  # agrees on 1
    assert merge_identity_bridges([("a", a), ("b", b)]) == {"1": "00-1", "2": "00-2", "3": "00-3"}
    c = [{"sleeper_id": "1", "gsis_id": "00-9"}]  # disagrees on 1
    with pytest.raises(ValueError, match="conflict"):
        merge_identity_bridges([("a", a), ("c", c)])
    with pytest.raises(ValueError, match="duplicate"):
        merge_identity_bridges([("d", [{"sleeper_id": "5", "gsis_id": "00-5"}, {"sleeper_id": "5", "gsis_id": "00-6"}])])


def test_a_single_reverse_id_mismatch_on_the_gsis_or_bridge_fallback_is_quarantined_not_made_active() -> None:
    """Codex's last census guard: replay ONLY Ryan Izzo's Sleeper row (5094, Sleeper gsis
    00-0034270) against ONLY Conklin's NFL row (sleeper_id 5133, gsis 00-0034270). With one
    claimant the multiple-claim rule is silent, and the gsis fallback made Izzo active/DET.
    An NFL row that names a DIFFERENT non-empty Sleeper id than the candidate is incompatible
    on the gsis and bridge fallbacks alike: quarantined as unknown, never active."""
    izzo = [_sleeper("5094", "Ryan Izzo", "TE", "TE", "Active", "", "00-0034270")]
    conklin_nfl = [_nfl("Tyler Conklin", "DET", "TE", "ACT", "5133", "00-0034270")]
    c = build_census(izzo, conklin_nfl, league_owned={}, season=2026)
    r = c.rows[0]
    assert r.availability_class == "unknown" and r.nfl_team is None and r.join_basis == "gsis_id"
    assert r.identity_conflict == ("nflverse row for gsis 00-0034270 names Sleeper id 5133, not 5094, on the gsis_id join; "
                                   "incompatible source ids")
    assert c.report()["counts"]["by_class"].get("active", 0) == 0
    # the same rule on the bridge fallback
    bridged = [_sleeper("5094", "Ryan Izzo", "TE", "TE", "Active", "", "")]
    c2 = build_census(bridged, conklin_nfl, league_owned={}, season=2026, identity_bridge={"5094": "00-0034270"})
    assert c2.rows[0].availability_class == "unknown" and "names Sleeper id 5133, not 5094" in c2.rows[0].identity_conflict
    # a fallback to an NFL row with NO Sleeper id stays a clean join (Bredeson)
    c3 = build_census([_sleeper("13516", "Max Bredeson", "RB", "RB", "Active", "MIN", "00-0041081")],
                      [_nfl("Max Bredeson", "MIN", "RB", "ACT", "", "00-0041081")], league_owned={}, season=2026)
    assert c3.rows[0].availability_class == "active" and c3.rows[0].identity_conflict is None
