"""T1 of docs/superpowers/plans/2026-09-06-available-player-discovery.md: the available-player
catalog reads the ACCEPTED report, the SAME census bytes and the producers' frozen CSVs; it
composes nothing. Ownership filters availability only; values are the producers' own; a member
without a verified forecast is retained with a plain reason; future = the named years only when
every year is present; cut / retired / unknown are separate populations; unmatched NFL identities
are never 'available'."""
from __future__ import annotations

import csv
import hashlib
import json

import pytest
from available_fixture import CENSUS_COLS, UNCOVERED_COLS, _fixture, _sha

from src.dynasty_genius.ranking.available_catalog import AvailableCatalog


def test_the_catalog_is_unowned_census_members_with_producer_values_and_separate_populations(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    by = {r.sleeper_id: r for r in cat.rows}
    # owned players are never AVAILABLE: they are identity-only rows in the 'owned' population
    assert by["100"].population == "owned" and by["101"].population == "owned"
    assert {sid for sid, r in by.items() if r.population != "owned"} == {"200", "13516", "201", "202", "203", "204", "205"}
    assert by["200"].population == "default" and by["200"].availability_class == "active"
    assert by["201"].population == "default" and by["202"].population == "default"
    assert by["203"].population == "cut" and by["204"].population == "retired" and by["205"].population == "unknown"
    # producer values, not margins: Free Wideout 2026 = 120.5 from the CSV
    fw = by["200"]
    assert fw.forecast is not None and fw.forecast.producer == "vet"
    assert [s.e_points for s in fw.forecast.seasons] == [120.5, 110.0, 100.0, 90.0, 80.0]
    assert fw.forecast.seasons[0].p_appear == 0.8 and fw.forecast.seasons[0].season == 2026
    assert fw.now_points == 120.5 and fw.future_points == 380.0 and fw.future_years == [2027, 2028, 2029, 2030]
    assert fw.impact == {"h2": 0.0, "h5": 0.0}                     # the accepted impact rides along, unchanged
    # a rookie joins through (draft_season, pick) / gsis and keeps the producer's values
    assert by["13516"].forecast.producer == "dg165_rookie" and by["13516"].now_points == 10.0 and by["13516"].future_points == 190.0
    # a negative forecast is a value, distinct from zero and missing
    assert by["202"].now_points == -1.5 and by["202"].forecast is not None
    # missing forecast retained with a plain reason, never a number
    pg = by["201"]
    assert pg.forecast is None and pg.now_points is None and pg.future_points is None
    assert pg.missing_reason == "no forecast from the selected producers; no reason stated"
    assert by["205"].forecast is None and "unknown" in by["205"].availability_class


def test_future_is_undefined_when_any_named_year_is_missing_never_zero_or_partial(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path, drop_year=True)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    te = next(r for r in cat.rows if r.sleeper_id == "202")
    assert te.now_points == -1.5 and te.future_points is None
    assert te.future_reason == "2030 forecast missing: future total undefined, not zero"
    assert [s.season for s in te.forecast.seasons] == [2026, 2027, 2028, 2029]


def test_a_producer_csv_whose_bytes_differ_from_the_reports_hash_is_refused(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path, break_csv_sha=True)
    with pytest.raises(ValueError, match="sha256"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_the_report_states_denominators_consistent_with_the_rows_and_disclosures_apart(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    rep = cat.report()
    d = rep["populations"]["default"]
    assert (d["total"], d["with_forecast"], d["without_forecast"]) == (4, 3, 1)
    assert d["by_class"] == {"active": 2, "practice_squad": 1, "injured_reserve": 1}
    assert rep["populations"]["cut"]["total"] == 1 and rep["populations"]["retired"]["total"] == 1 and rep["populations"]["unknown"]["total"] == 1
    assert rep["populations"]["default"]["by_position"]["WR"] == {"with_forecast": 1, "without_forecast": 1}
    assert rep["disclosures"]["unmatched_nfl_records"] == 141 and rep["disclosures"]["uncovered_sleeper_ids"] == 1
    assert rep["disclosures"]["archive_unforecast_by_position"] == {"QB": 368}
    assert rep["ownership_as_of"] == "2026-09-06T13:00:52+00:00" and rep["nfl_status_as_of"] == "Sun, 06 Sep 2026 11:28:11 GMT"
    assert rep["sources"]["report_sha256"] == hashlib.sha256(rp.read_bytes()).hexdigest()
    assert rep["sources"]["census_csv_sha256"] == hashlib.sha256((run / "census.csv").read_bytes()).hexdigest()
    assert rep["forecast_note"].startswith("values are the producers' own expected season points")
    assert sum(p["total"] for k, p in rep["populations"].items() if k != "owned") == rep["available_rows"] == 7
    assert rep["rows"] == 9 and rep["populations"]["owned"]["total"] == 2


def test_a_report_row_with_a_sleeper_shaped_id_joins_its_producer_through_the_census_verified_gsis(tmp_path) -> None:
    """Adrian Martinez (Sleeper 11065): the accepted report row's player_id is the artifact's
    Sleeper-shaped id, not a gsis. The producer row is found through the census's VERIFIED
    NFL gsis (the join the audit used via the identity bridge), never by name."""
    rp, run, snap, csvs = _fixture(tmp_path)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for x in rep[sec]["all_inspectable"]:
            if x["sleeper_id"] == "200":
                x["player_id"] = "200"  # Sleeper-shaped, as the artifact sometimes carries
    rp.write_text(json.dumps(rep))
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    fw = next(r for r in cat.rows if r.sleeper_id == "200")
    assert fw.forecast is not None and fw.forecast.join_basis == "census_nfl_gsis" and fw.now_points == 120.5
    # a comparable report row with NO producer row under any verified gsis is an inconsistency, refused
    rep2 = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for x in rep2[sec]["all_inspectable"]:
            if x["sleeper_id"] == "200":
                x["player_id"] = "00-9999"
    rp.write_text(json.dumps(rep2))
    rows = list(csv.DictReader((run / "census.csv").open(newline="")))
    for r in rows:
        if r["sleeper_id"] == "200":
            r["nfl_gsis_id"], r["sleeper_gsis_id"] = "00-9999", "00-9999"
    with (run / "census.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CENSUS_COLS)
        w.writeheader()
        w.writerows(rows)
    rc = json.loads((run / "report.json").read_text())
    rc["census_csv_sha256"] = _sha(run / "census.csv")
    (run / "report.json").write_text(json.dumps(rc))
    rep2["current_census"]["census_csv_sha256"] = rc["census_csv_sha256"]
    rep2["current_census"]["report_sha256"] = _sha(run / "report.json")
    rp.write_text(json.dumps(rep2))
    with pytest.raises(ValueError, match="no producer row"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_owned_members_are_identity_only_rows_so_a_watched_player_who_becomes_owned_is_resolvable(tmp_path) -> None:
    """Root: the watched-only view must retain a watched player who became owned, with truthful
    changed status. Owned census members are therefore in the catalog as identity/status-only
    rows (population 'owned', owned_now, roster) — never in the available populations."""
    rp, run, snap, csvs = _fixture(tmp_path)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    by = {r.sleeper_id: r for r in cat.rows}
    assert by["100"].population == "owned" and by["100"].owned_now is True and by["100"].roster_id == 1
    assert by["100"].forecast is None and by["100"].now_points is None       # identity/status only
    assert by["100"].missing_reason == "owned in your league; forecasts are shown on the research board"
    rep = cat.report()
    assert rep["populations"]["owned"]["total"] == 2
    assert rep["available_rows"] == 7 and rep["rows"] == 9                # available populations exclude owned
    assert all(r.owned_now is False for r in cat.rows if r.population != "owned")


def test_a_frozen_producer_forecast_is_recovered_only_by_verified_census_identity_and_flagged(tmp_path) -> None:
    """Root permits new-only rows for frozen producer forecasts recoverable under a VERIFIED
    census identity (four RBs today), using the exact original values; the 825 accepted rows
    are untouched and the recovered rows say they are not among them."""
    rp, run, snap, csvs = _fixture(tmp_path)
    # Practice Guy (201) has no report row; give the veteran CSV a row under his verified NFL gsis 00-5
    vet = csvs[0]
    rows = list(csv.DictReader(vet.open(newline="")))
    extra = dict(rows[0])
    extra["player_id"], extra["position"] = "00-5", "WR"
    for j in range(1, 6):
        extra[f"e_points_year{j}"] = str(60 - 5 * j)
        extra[f"e_points_year{j}_given_appear"] = str((60 - 5 * j) / 0.8)
    rows.append(extra)
    with vet.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for m in rep[sec]["annual_producers"]:
            if m.get("model_version") == "vet":
                m["csv_sha256"] = _sha(vet)
    rp.write_text(json.dumps(rep))
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    pg = next(r for r in cat.rows if r.sleeper_id == "201")
    assert pg.forecast is not None and pg.recovered is True and pg.forecast.join_basis == "recovered_census_nfl_gsis"
    assert pg.forecast.join_id == "00-5" and pg.to_dict()["forecast"]["join_id"] == "00-5"
    assert pg.now_points == 55.0 and pg.future_points == 50 + 45 + 40 + 35
    assert pg.impact == {"h2": None, "h5": None}                         # not among the accepted 825
    assert pg.missing_reason is None
    assert cat.report()["recovered"] == {"count": 1, "rows": [{"sleeper_id": "201", "gsis": "00-5", "producer": "vet"}],
                                         "note": "frozen producer forecasts joined by verified census identity; not among the accepted 825 rows; exact original values"}
    # a contested/unknown identity is never recovered
    assert next(r for r in cat.rows if r.sleeper_id == "205").forecast is None


# ---- root's independent specification review (2026-09-07): fail-open cases, each refused ----

def _rewrite_vet(rp, vet, mutate):
    """Rewrite the veteran CSV through `mutate(rows) -> rows` and re-sign its sha in the report,
    the way a tampered-but-rehashed copy would look."""
    rows = list(csv.DictReader(vet.open(newline="")))
    rows = mutate(rows)
    with vet.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for m in rep[sec]["annual_producers"]:
            if m.get("model_version") == "vet":
                m["csv_sha256"] = _sha(vet)
    rp.write_text(json.dumps(rep))


def test_a_rehashed_producer_csv_whose_arm_is_not_the_reports_declared_arm_is_refused(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)

    def other_arm(rows):
        for r in rows:
            r["arm"] = "different_unreviewed_arm"
        return rows
    _rewrite_vet(rp, csvs[0], other_arm)
    with pytest.raises(ValueError, match="arm"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # a rookie CSV whose model_version / scoring arm differ from the declaration is refused too
    rp, run, snap, csvs = _fixture(tmp_path / "b")
    rows = list(csv.DictReader(csvs[1].open(newline="")))
    rows[0]["scoring_arm_id"] = "dg165_rookie:inner_menu:plain"
    with csvs[1].open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for m in rep[sec]["annual_producers"]:
            if m.get("model_version") == "dg165_rookie":
                m["csv_sha256"] = _sha(csvs[1])
    rp.write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="arm"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_forecast_year_semantics_are_validated_against_the_requested_path_never_relabelled(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)

    def old_vintage(rows):
        for r in rows:
            r["forecast_cutoff"] = "post-2017-season"
            for j in range(1, 6):
                r[f"forecast_season_year{j}"] = f"{2017 + j}.0"
        return rows
    _rewrite_vet(rp, csvs[0], old_vintage)
    with pytest.raises(ValueError, match="2026"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # cutoff alone disagreeing with year 1 is refused as well
    rp, run, snap, csvs = _fixture(tmp_path / "b")

    def stale_cutoff(rows):
        for r in rows:
            r["forecast_cutoff"] = "post-2024-season"
        return rows
    _rewrite_vet(rp, csvs[0], stale_cutoff)
    with pytest.raises(ValueError, match="cutoff"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # a rookie file whose draft season is not the forecast year cannot be year 1 = 2026
    rp, run, snap, csvs = _fixture(tmp_path / "c")
    rows = list(csv.DictReader(csvs[1].open(newline="")))
    rows[0]["draft_season"] = "2025"
    with csvs[1].open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        for m in rep[sec]["annual_producers"]:
            if m.get("model_version") == "dg165_rookie":
                m["csv_sha256"] = _sha(csvs[1])
    rp.write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="draft_season"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_duplicate_identities_are_refused_never_silently_overwritten(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)

    def dup(rows):
        extra = dict(rows[1])            # 00-3 again with an absurd value
        for j in range(1, 6):
            extra[f"e_points_year{j}"] = "9999"
            extra[f"e_points_year{j}_given_appear"] = str(9999 / 0.8)
        return rows + [extra]
    _rewrite_vet(rp, csvs[0], dup)
    with pytest.raises(ValueError, match="duplicate"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # the same producer supplied twice is a conflicting argument, refused
    rp, run, snap, csvs = _fixture(tmp_path / "b")
    with pytest.raises(ValueError, match="duplicate"):
        AvailableCatalog.build(rp, run, [csvs[0], csvs[0], csvs[1]], snapshot_path=snap)
    # a Sleeper identity listed twice in the accepted report is refused
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        rep[sec]["all_inspectable"].append(dict(rep[sec]["all_inspectable"][1]))
    rp.write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="duplicate"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_conflicting_authoritative_identities_fail_instead_of_serving_another_player(tmp_path) -> None:
    """The report says Free Wideout is 00-7 (Cut Passer's gsis, which HAS a producer row) while the
    census's verified gsis stays 00-3: never serve 00-7's 50.0 under his name."""
    rp, run, snap, csvs = _fixture(tmp_path)
    rep = json.loads(rp.read_text())
    for sec in ("comparable_board", "horizon_board"):
        rep[sec]["all_inspectable"] = [x for x in rep[sec]["all_inspectable"] if x["sleeper_id"] != "203"]
        for x in rep[sec]["all_inspectable"]:
            if x["sleeper_id"] == "200":
                x["player_id"] = "00-7"
    rp.write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="conflict"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)


def test_a_producer_row_with_every_year_blank_is_no_usable_forecast_and_counts_are_per_basis(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)

    def blank(rows):
        for r in rows:
            if r["player_id"] == "00-3":
                for j in range(1, 6):
                    for c in (f"e_points_year{j}", f"e_points_year{j}_given_appear", f"p_appear_year{j}", f"e_games_year{j}",
                              f"e_games_year{j}_given_appear"):
                        r[c] = ""
        return rows
    _rewrite_vet(rp, csvs[0], blank)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    fw = next(r for r in cat.rows if r.sleeper_id == "200")
    assert fw.forecast is None and fw.now_points is None and fw.future_points is None
    assert fw.missing_reason == "producer row found under the verified identity but every season's expected points is blank: no usable forecast"
    assert fw.forecast_path == {"status": "none", "years_present": []}
    d = cat.report()["populations"]["default"]
    assert (d["total"], d["with_forecast"], d["without_forecast"]) == (4, 2, 2)
    assert (d["with_now"], d["with_future_total"], d["incomplete_path"]) == (2, 2, 0)
    # an incomplete path is its own state, counted apart from complete and none
    rp, run, snap, csvs = _fixture(tmp_path / "b", drop_year=True)
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    te = next(r for r in cat.rows if r.sleeper_id == "202")
    assert te.forecast_path == {"status": "incomplete", "years_present": [2026, 2027, 2028, 2029]}
    d = cat.report()["populations"]["default"]
    assert (d["with_forecast"], d["with_now"], d["with_future_total"], d["incomplete_path"]) == (3, 3, 2, 1)


def test_non_finite_aggregates_probability_bounds_and_the_conditional_identity_are_refused(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)

    def huge(rows):
        for r in rows:
            if r["player_id"] == "00-3":
                for j in range(2, 6):
                    r[f"e_points_year{j}"] = "1e308"
                    r[f"e_points_year{j}_given_appear"] = str(1e308 / 0.8)
        return rows
    _rewrite_vet(rp, csvs[0], huge)
    with pytest.raises(ValueError, match="finite"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    rp, run, snap, csvs = _fixture(tmp_path / "b")

    def bad_prob(rows):
        rows[1]["p_appear_year1"] = "1.2"
        rows[1]["e_points_year1_given_appear"] = str(120.5 / 1.2)
        return rows
    _rewrite_vet(rp, csvs[0], bad_prob)
    with pytest.raises(ValueError, match="probability"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    rp, run, snap, csvs = _fixture(tmp_path / "c")

    def broken_identity(rows):
        rows[1]["e_points_year1"] = "200"       # p_appear 0.8 × given 150.625 ≠ 200
        return rows
    _rewrite_vet(rp, csvs[0], broken_identity)
    with pytest.raises(ValueError, match="conditional"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # legitimate negatives are values (Reserve End −1.5 is retained by the base fixture)
    rp, run, snap, csvs = _fixture(tmp_path / "d")
    cat = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    assert next(r for r in cat.rows if r.sleeper_id == "202").now_points == -1.5


def test_metadata_only_census_mutations_are_refused_the_whole_captured_census_must_be_the_bound_one(tmp_path) -> None:
    """Root: the census CSV hash alone is not the binding. A census report.json with a different
    roster date or unmatched count, or a different uncovered.csv, is not the census the accepted
    report bound even when census.csv is byte-identical."""
    rp, run, snap, csvs = _fixture(tmp_path)
    rc = json.loads((run / "report.json").read_text())
    rc["sources"]["nflverse_roster"]["http_last_modified"] = "Fri, 01 Jan 2027 00:00:00 GMT"
    rc["counts"]["nfl_rows_unclaimed"] = 9999
    (run / "report.json").write_text(json.dumps(rc))
    with pytest.raises(ValueError, match="report_sha256"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    rp, run, snap, csvs = _fixture(tmp_path / "b")
    with (run / "uncovered.csv").open("a", newline="") as fh:
        csv.DictWriter(fh, fieldnames=UNCOVERED_COLS).writerow(dict(zip(UNCOVERED_COLS, ["9", "Nobody", "WR", "Active", "", "", "x"])))
    with pytest.raises(ValueError, match="uncovered"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # an accepted report that does not record the census report / uncovered hashes cannot bind, refused
    rp, run, snap, csvs = _fixture(tmp_path / "c")
    rep = json.loads(rp.read_text())
    del rep["current_census"]["report_sha256"]
    rp.write_text(json.dumps(rep))
    with pytest.raises(ValueError, match="report_sha256"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap)
    # the good build carries the full census binding
    rp, run, snap, csvs = _fixture(tmp_path / "d")
    src = AvailableCatalog.build(rp, run, csvs, snapshot_path=snap).report()["sources"]["census"]
    assert src == {"run_id": "20260906T202057Z", "census_csv_sha256": _sha(run / "census.csv"), "report_sha256": _sha(run / "report.json"),
                   "uncovered_csv_sha256": _sha(run / "uncovered.csv")}
