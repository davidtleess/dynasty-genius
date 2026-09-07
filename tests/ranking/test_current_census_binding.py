"""T1 of docs/superpowers/plans/2026-09-06-player-comparison-and-current-coverage.md: the reviewed,
dated current-player census is BOUND into an audit — same bytes re-hashed, identities of its own
sources re-verified, season and uniqueness checked, never a mutable 'latest' path — and read as
three separate populations (league-owned, listed unowned by NFL status, unmatched NFL records)
plus an attachment verdict per Sleeper id that is 'unverified' whenever no verified join exists."""
from __future__ import annotations

import csv
import hashlib
import json

import pytest

from src.dynasty_genius.ranking.current_census_binding import CensusBinding

CENSUS_COLS = ["sleeper_id", "name", "league_position", "fantasy_positions", "sleeper_status", "sleeper_team",
               "sleeper_gsis_id", "nfl_team", "nfl_position", "nfl_status_raw", "nfl_gsis_id", "availability_class",
               "join_basis", "identity_conflict", "league_owned", "roster_id", "contested_nfl_gsis_id"]
UNCOVERED_COLS = ["sleeper_id", "name", "league_position", "sleeper_status", "sleeper_team", "sleeper_gsis_id", "reason"]


def _census_row(sid, name, pos, cls, owned, basis="sleeper_id", conflict="", roster="", team="KC"):
    return dict(zip(CENSUS_COLS, [sid, name, pos, pos, "Active", team, "", team if cls != "unknown" else "", pos,
                                  "ACT", "00-1", cls, basis, conflict, str(owned), roster, ""]))


def _write_run(tmp_path, *, rows=None, uncovered=None, season=2026, break_hash=None, dup=False):
    run = tmp_path / "20260906T202057Z" / "dg178_current_census"
    run.mkdir(parents=True)
    rows = rows if rows is not None else [
        _census_row("4046", "Patrick Mahomes", "QB", "active", True, roster="2"),
        _census_row("9502", "Tank Dell", "WR", "injured_reserve", True, roster="1"),
        _census_row("13516", "Max Bredeson", "RB", "active", False, basis="gsis_id_via_bridge"),
        _census_row("777", "Practice Guy", "WR", "practice_squad", False),
        _census_row("5133", "Tyler Conklin", "TE", "unknown", False, conflict="contested"),
    ]
    if dup:
        rows = rows + [rows[0]]
    with (run / "census.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CENSUS_COLS)
        w.writeheader()
        w.writerows(rows)
    uncovered = uncovered if uncovered is not None else [
        dict(zip(UNCOVERED_COLS, ["4098", "Kareem Hunt", "RB", "Active", "", "00-0033923",
                                  "no verified join to the captured 2026 roster (Sleeper flags Active/- are not membership); "
                                  "absence from the NFL is not proven"]))]
    with (run / "uncovered.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=UNCOVERED_COLS)
        w.writeheader()
        w.writerows(uncovered)
    # the census's own sources, re-hashable
    src = tmp_path / "sources"
    src.mkdir(exist_ok=True)
    roster = src / "roster_2026.csv"
    roster.write_bytes(b"season,team\n2026,KC\n")
    sleeper = src / "sleeper_eligibility.csv"
    sleeper.write_bytes(b"sleeper_id\n4046\n")
    snap = src / "snapshot.json"
    snap.write_bytes(b'{"rosters": []}')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    bridge = src / "default_bridge.csv"
    bridge.write_bytes(b"sleeper_id,my_gsis_id\n13516,00-0041081\n")
    report = {
        "season": season, "run": "20260906T202057Z",
        "denominator": "…", "denominator_note": "members = listed-or-owned, NOT active NFL",
        "sources": {"nflverse_roster": {"path": str(roster), "sha256": sha(roster) if break_hash != "roster" else "0" * 64},
                    "sleeper_eligibility": {"path": str(sleeper), "sha256": sha(sleeper)},
                    "league_snapshot": {"path": str(snap), "sha256": sha(snap), "owned_ids": 2},
                    "identity_bridge": [{"path": str(bridge), "sha256": sha(bridge), "rows": 1}]},
        "counts": {"members": len(rows), "nfl_rows_unclaimed": 141, "contested_nfl_records": 1, "uncovered": len(uncovered)},
        "nfl_rows_unclaimed": [["Someone", "KC", "WR", "DEV", "00-9"]],
        "census_csv_sha256": sha(run / "census.csv") if break_hash != "census" else "0" * 64,
    }
    (run / "report.json").write_text(json.dumps(report))
    return run, sha(snap)


def test_a_bound_census_rehashes_its_bytes_and_its_sources_and_refuses_any_mismatch(tmp_path) -> None:
    run, snap_sha = _write_run(tmp_path)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    assert b.run_id == "20260906T202057Z" and b.members == 5 and b.uncovered_count == 1
    assert b.census_csv_sha256 == hashlib.sha256((run / "census.csv").read_bytes()).hexdigest()
    assert b.identity_checks == {"census_csv_sha256": True, "nflverse_roster_sha256": True,
                                 "sleeper_eligibility_sha256": True, "league_snapshot_sha256": True,
                                 "identity_bridge_sha256": True, "season": True, "unique_sleeper_ids": True,
                                 "counts_reconcile": True}
    run2, snap2 = _write_run(tmp_path / "b", break_hash="census")
    with pytest.raises(ValueError, match="census.csv"):
        CensusBinding.load(run2, season=2026, league_snapshot_sha256=snap2)
    run3, snap3 = _write_run(tmp_path / "c", break_hash="roster")
    with pytest.raises(ValueError, match="nflverse_roster"):
        CensusBinding.load(run3, season=2026, league_snapshot_sha256=snap3)
    run4, snap4 = _write_run(tmp_path / "d")
    with pytest.raises(ValueError, match="snapshot"):
        CensusBinding.load(run4, season=2026, league_snapshot_sha256="f" * 64)
    with pytest.raises(ValueError, match="season"):
        CensusBinding.load(run4, season=2027, league_snapshot_sha256=snap4)
    run5, snap5 = _write_run(tmp_path / "e", dup=True)
    with pytest.raises(ValueError, match="duplicate"):
        CensusBinding.load(run5, season=2026, league_snapshot_sha256=snap5)


def test_a_mutable_latest_path_is_refused(tmp_path) -> None:
    run, snap_sha = _write_run(tmp_path)
    latest = tmp_path / "latest"
    latest.symlink_to(run)
    with pytest.raises(ValueError, match="latest"):
        CensusBinding.load(latest, season=2026, league_snapshot_sha256=snap_sha)


def test_attachment_is_unverified_for_uncovered_unknown_or_absent_ids_and_verified_only_for_a_clean_join(tmp_path) -> None:
    run, snap_sha = _write_run(tmp_path)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    hunt = b.attachment("4098")
    assert hunt["status"] == "unverified" and hunt["basis"] == "no verified join"
    assert "absence from the NFL is not proven" in hunt["note"] and "Sleeper" in hunt["note"]
    assert b.attachment("4046") == {"status": "active", "basis": "sleeper_id", "nfl_team": "KC",
                                    "note": "verified join to the captured 2026 roster (ACT)"}
    assert b.attachment("5133")["status"] == "unverified" and "contested" in b.attachment("5133")["note"]
    assert b.attachment("nobody")["status"] == "unverified" and "not in the census" in b.attachment("nobody")["note"]


def test_coverage_keeps_league_owned_listed_unowned_and_unmatched_records_as_separate_populations(tmp_path) -> None:
    run, snap_sha = _write_run(tmp_path)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    board = {"4046": True, "13516": True, "777": False, "9502": False}  # sleeper id -> has a research estimate
    cov = b.coverage(board, owned_ids={"4046", "9502"}, positions=("QB", "RB", "WR", "TE"))
    assert cov["league_owned"]["total"] == 2 and cov["league_owned"]["in_census"] == 2
    assert cov["league_owned"]["by_class"] == {"active": 1, "injured_reserve": 1}
    assert cov["league_owned"]["with_forecast"] == 1 and cov["league_owned"]["without_forecast"] == 1
    lu = cov["listed_unowned"]["by_position"]
    assert lu["RB"] == {"active": {"with_forecast": 1, "without_forecast": 0}}
    assert lu["WR"] == {"practice_squad": {"with_forecast": 0, "without_forecast": 1}}
    assert "TE" not in lu  # Conklin has no verified join: he is not 'listed'
    assert cov["unverified_unowned"]["by_position"]["TE"] == {"with_forecast": 0, "without_forecast": 1}
    assert cov["unmatched_nfl_records"] == {"count": 141, "note": "NFL skill rows no Sleeper row claims; kept separate, never added to a denominator"}
    assert cov["uncovered_sleeper_ids"] == 1
    assert cov["denominator_note"].startswith("members = listed-or-owned")


# ── Root code review (2026-09-06 17:3x ET): one byte buffer per consumed file; blank ids; owned-absent coverage ──
def test_each_consumed_file_is_read_exactly_once_and_hashed_and_parsed_from_the_same_bytes(tmp_path, monkeypatch) -> None:
    """Hash-then-reopen lets a file change between the hash and the parse. Every consumed file
    (census.csv, uncovered.csv, report.json, the three sources) is captured once as bytes, and
    both the hash and the parse come from that buffer. Adversarial regression: a file that
    changes after the first read must not be able to change what was parsed."""
    from pathlib import Path as _P

    run, snap_sha = _write_run(tmp_path)
    reads: dict[str, int] = {}
    real = _P.read_bytes

    def counting(self):
        reads[self.name] = reads.get(self.name, 0) + 1
        data = real(self)
        if self.name == "census.csv":  # mutate on disk right after the first read
            self.write_bytes(data.replace(b"Patrick Mahomes", b"Somebody Else"))
        return data

    monkeypatch.setattr(_P, "read_bytes", counting)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    assert all(n == 1 for n in reads.values()), reads          # every consumed file read exactly once
    assert {"census.csv", "uncovered.csv", "report.json", "roster_2026.csv", "sleeper_eligibility.csv", "snapshot.json", "default_bridge.csv"} <= set(reads)
    assert b.member("4046")["name"] == "Patrick Mahomes"       # parsed from the captured bytes, not the mutated file
    monkeypatch.undo()
    on_disk = hashlib.sha256((run / "census.csv").read_bytes()).hexdigest()
    assert b.census_csv_sha256 != on_disk                       # the disk changed after the single read; the binding did not
    assert b.identity_checks["census_csv_sha256"] is True       # and the hash it checked was the parsed buffer's


def test_blank_ids_and_count_mismatches_are_refused(tmp_path) -> None:
    rows = [_census_row("", "Blank Id", "QB", "active", False)]
    run, snap_sha = _write_run(tmp_path / "blank", rows=rows)
    with pytest.raises(ValueError, match="blank sleeper_id"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    run2, snap2 = _write_run(tmp_path / "count")
    rep = json.loads((run2 / "report.json").read_text())
    rep["counts"]["members"] = 99
    (run2 / "report.json").write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="members"):
        CensusBinding.load(run2, season=2026, league_snapshot_sha256=snap2)


def test_owned_ids_absent_from_the_census_still_count_in_league_owned_coverage(tmp_path) -> None:
    run, snap_sha = _write_run(tmp_path)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    board = {"4046": True, "9502": False, "ghost": True, "ghost2": False}
    cov = b.coverage(board, owned_ids={"4046", "9502", "ghost", "ghost2"}, positions=("QB", "RB", "WR", "TE"))
    lo = cov["league_owned"]
    assert lo["total"] == 4 and lo["in_census"] == 2 and lo["absent_from_census"] == 2
    assert lo["with_forecast"] == 2 and lo["without_forecast"] == 2  # ghosts counted, not dropped
    assert lo["by_class"] == {"active": 1, "injured_reserve": 1, "absent_from_census": 2}
    assert lo["with_forecast"] + lo["without_forecast"] == lo["total"]


def test_list_valued_identity_bridge_sources_are_rehashed_and_kept_as_provenance(tmp_path) -> None:
    """The census report records identity_bridge as a LIST of {path, sha256}; four real joins
    depend on those files. Every bridge input is re-hashed and kept in the binding's sources;
    a missing or tampered bridge file refuses the binding."""
    run, snap_sha = _write_run(tmp_path)
    bridge = tmp_path / "sources" / "reconciliation.csv"
    bridge.write_bytes(b"sleeper_id,my_gsis_id\n13516,00-0041081\n")
    rep = json.loads((run / "report.json").read_text())
    rep["sources"]["identity_bridge"] = [{"path": str(bridge), "sha256": hashlib.sha256(bridge.read_bytes()).hexdigest(), "rows": 1}]
    (run / "report.json").write_text(json.dumps(rep))
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    assert b.identity_checks["identity_bridge_sha256"] is True
    assert b.sources["identity_bridge"][0]["sha256"] == hashlib.sha256(bridge.read_bytes()).hexdigest()
    assert b.to_json()["sources"]["identity_bridge"][0]["path"] == str(bridge)
    bridge.write_bytes(b"sleeper_id,my_gsis_id\n13516,00-0099999\n")  # tampered
    with pytest.raises(ValueError, match="identity_bridge"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    bridge.unlink()  # missing
    with pytest.raises(ValueError, match="identity_bridge"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)


def test_unknown_members_are_reported_apart_from_verified_listed_players(tmp_path) -> None:
    """Conklin / Izzo / Searight are census members with NO verified NFL join. They must not be
    counted as 'listed on a 2026 NFL roster'; they are a separate, visible population with
    their own forecast / no-forecast counts."""
    run, snap_sha = _write_run(tmp_path)
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    cov = b.coverage({"5133": True, "13516": True}, owned_ids=set(), positions=("QB", "RB", "WR", "TE"))
    lu = cov["listed_unowned"]["by_position"]
    assert "unknown" not in lu.get("TE", {})               # not under the verified-listed population
    assert cov["unverified_unowned"]["by_position"]["TE"] == {"with_forecast": 1, "without_forecast": 0}
    assert cov["unverified_unowned"]["note"].startswith("census members with no verified NFL join")
    assert lu["RB"] == {"active": {"with_forecast": 1, "without_forecast": 0}}


def test_every_census_ownership_claim_is_reconciled_against_the_verified_snapshot_rosters(tmp_path) -> None:
    """Root's reviewer flipped Rodgers to league_owned=False / roster 999, updated the census hash,
    kept the original snapshot — and the loader passed. Ownership is the SNAPSHOT's fact: every
    census row's league_owned / roster_id must equal the verified snapshot's rosters, and every
    owned id in the snapshot must appear as owned in the census."""
    run, snap_sha = _write_run(tmp_path)
    snapshot_owned = {"4046": 2, "9502": 1}
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha, snapshot_owned=snapshot_owned)
    assert b.identity_checks["ownership_reconciles"] is True
    # tamper: Mahomes unowned / roster 999 in the census, hash updated, snapshot unchanged
    rows = list(csv.DictReader((run / "census.csv").open(newline="")))
    for r in rows:
        if r["sleeper_id"] == "4046":
            r["league_owned"], r["roster_id"] = "False", "999"
    with (run / "census.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CENSUS_COLS)
        w.writeheader()
        w.writerows(rows)
    rep = json.loads((run / "report.json").read_text())
    rep["census_csv_sha256"] = hashlib.sha256((run / "census.csv").read_bytes()).hexdigest()
    (run / "report.json").write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="ownership"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha, snapshot_owned=snapshot_owned)
    # an owned id the census lacks entirely is a reconciliation failure too, not a silent absence
    run2, snap2 = _write_run(tmp_path / "b")
    with pytest.raises(ValueError, match="ownership"):
        CensusBinding.load(run2, season=2026, league_snapshot_sha256=snap2, snapshot_owned={"4046": 2, "9502": 1, "ghost": 4})


def test_rows_joined_through_a_bridge_require_bridge_provenance_fail_closed(tmp_path) -> None:
    """Root's regression: with sources.identity_bridge removed from the report while four rows
    still say join_basis=gsis_id_via_bridge, the loader passed. Any bridge-joined row requires
    at least one re-hashed bridge source; missing or empty provenance refuses the binding."""
    run, snap_sha = _write_run(tmp_path)   # fixture has Bredeson via the bridge
    rep = json.loads((run / "report.json").read_text())
    del rep["sources"]["identity_bridge"]   # provenance removed, rows still say gsis_id_via_bridge
    (run / "report.json").write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="identity_bridge"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    rep["sources"]["identity_bridge"] = []
    (run / "report.json").write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="identity_bridge"):
        CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    # with a real re-hashed bridge it loads and records the provenance
    bridge = tmp_path / "sources" / "reconciliation.csv"
    bridge.write_bytes(b"sleeper_id,my_gsis_id\n13516,00-0041081\n")
    rep["sources"]["identity_bridge"] = [{"path": str(bridge), "sha256": hashlib.sha256(bridge.read_bytes()).hexdigest()}]
    (run / "report.json").write_text(json.dumps(rep))
    b = CensusBinding.load(run, season=2026, league_snapshot_sha256=snap_sha)
    assert b.identity_checks["identity_bridge_sha256"] is True and b.bridge_joined_rows == 1
