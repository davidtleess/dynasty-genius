"""DG-182 — the roster-spot comparison adapter composes the two ACCEPTED inputs the research tabs
already serve (the audit report and the available-player catalog bound to it) into one source-bound
pair of player collections. It fits nothing, infers nothing, rounds nothing; anything it cannot
verify it refuses with the reason (ComparisonSourceError), never a partial or older payload.

Reconstruction rule for David's roster (the report carries margins, not points): a season's points
are the board's full-precision signed expected_margin PLUS that season's reference from the
union_replacement producer's per-position series — the same series research_preview uses. The
top-level report.replacement (a legacy served PPG scenario) and the clipped `advantage` are never used.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

import pytest

from src.dynasty_genius.ranking.roster_comparison import (
    ComparisonSourceError,
    build_comparison,
)

QB_SERIES = [115.32497628242587, 85.90292286152696, 44.487410939143025, 31.467770472882492, 17.583689420821695]
RB_SERIES = [88.2770971070361, 46.1704555773408, 40.0, 30.0, 20.0]
WR_SERIES = [105.58329249503637, 98.21715154207483, 93.22007476857857, 84.97422269775855, 71.05891152992479]
MCCARTHY_MARGINS = [-3.3183004116222747, 12.848557384333802, 48.62145323820008, 60.41020979991474, 70.58621745986794]
SNAPSHOT_SHA = "e" * 64
YEARS = [2026, 2027, 2028, 2029, 2030]


def _union_entry(position, rate, quantity="expected_season_points_same_window"):
    return {"position": position, "policy": "best_available_expected_points", "rate_ppg": rate,
            "rate_quantity": quantity, "player_id": "00-ref", "player_name": {"QB": "Joe Flacco", "RB": "Ref Back", "WR": "Marvin Mims"}[position],
            "pool_complete": True, "horizon_assumption": "same_player_from_snapshot_per_season"}


def _roster_row(sleeper_id, name, position, pid, margins, *, producer="DG-177 veteran annual forecast candidate (report-only):basic_cohort_3col_plus_lags",
                readiness="comparable", reason=None, team="MIN"):
    return {"player_id": pid, "sleeper_id": sleeper_id, "name": name, "position": position, "team": team, "age": 23.0,
            "value": 1.0, "readiness": readiness, "reason": reason, "producer": producer, "estimate_class": "candidate",
            "evidence_verified": True, "reference_player": "Joe Flacco", "reference_expected_points": 115.32497628242587,
            "seasons": [{"season": y, "expected_margin": m, "action": "retain" if m > 0 else "replace", "advantage": max(m, 0.0)}
                        for y, m in zip(YEARS, margins)],
            "rostered_by": 1, "on_davids_roster": True}


def _report():
    roster = [
        _roster_row("11565", "J.J. McCarthy", "QB", "00-0039923", MCCARTHY_MARGINS),
        _roster_row("11576", "Braelon Allen", "RB", "00-0039794", [-53.61265642415228, -3.499953259581865, 1.0, 2.0, 3.0], team="NYJ"),
        _roster_row("13269", "Fernando Mendoza", "QB", "fernando_mendoza_qb", [80.54624873061018, 70.0, 60.0, 50.0, 40.0],
                    producer="dg165_rookie_capital_v3_chain", team="LV"),
        {**_roster_row("9502", "Tank Dell", "WR", "9502", [], readiness="none",
                       reason="not forecast by any annual producer (vet, rookie); a veteran without a 2025 feature row or an undrafted rookie", team="HOU"),
         "reference_player": None, "reference_expected_points": None, "seasons": []},
    ]
    return {
        "run": "20260906T214512Z", "forecast_date": "2026-09-06",
        "board_target": {"scope": "REG", "scoring": "PPR_nflverse_default", "window": "championship_week17", "exposure": "stat_record_weeks_in_window",
                         "event": "appearance", "clock": "per_season", "quantity": "season_points", "labels_through": 2025},
        "outcome_artifact": {"scoring_preset": "nflverse_default_ppr_championship_window_v1", "league_scoring_exact": False},
        "inputs": {"snapshot": {"id": "league-20260906T130052Z", "sha256": SNAPSHOT_SHA}},
        "comparable_views": {"h2": "comparable_board", "h5": "horizon_board"},
        "davids_best_lineup_served_h0": {"total_ppg": 95.4, "excluded_taxi_or_reserve": ["11576", "13269", "9502"],
                                         "scenario": "one week, active roster only, every active player at his served h=0 rate"},
        # the legacy served-rate scenario: a PPG number that must NEVER be added to a season margin
        "replacement": {"QB": {"rate_ppg": 9.4068, "player": "Spencer Rattler"}, "RB": {"rate_ppg": 7.3968}, "WR": {"rate_ppg": 7.3968}},
        "horizon_board": {
            "n_comparable": 3, "horizons_summed": 5,
            "annual_producers": [
                {"model_version": "DG-177 veteran annual forecast candidate (report-only):basic_cohort_3col_plus_lags", "csv": "/x/basic_forecasts.csv",
                 "csv_sha256": "a" * 64, "seasons": 5, "evidence": {"verified": True}},
                {"model_version": "dg165_rookie_capital_v3_chain", "csv": "/x/rookie_scores_2026.csv", "csv_sha256": "b" * 64, "seasons": 6,
                 "evidence": {"verified": True}},
                {"model_version": "union_replacement", "seasons": 5, "positions_without_a_bar": [],
                 "replacement": {"QB": [_union_entry("QB", r) for r in QB_SERIES],
                                 "RB": [_union_entry("RB", r) for r in RB_SERIES],
                                 "WR": [_union_entry("WR", r) for r in WR_SERIES]}},
                {"model_version": "assembled_grading", "assembled_grading": {}},
            ],
            "davids_roster": roster, "league_rostered": [], "top": [], "all_inspectable": [],
        },
    }


def _forecast(points, *, producer="DG-177 veteran annual forecast candidate (report-only):basic_cohort_3col_plus_lags", years=YEARS,
              join_basis="report_gsis", join_id="00-1"):
    return {"producer": producer, "source_csv": "/x/basic_forecasts.csv", "source_csv_sha256": "a" * 64, "join_basis": join_basis, "join_id": join_id,
            "seasons": [{"season": y, "e_points": v, "p_appear": 0.8, "e_points_given_appear": v / 0.8, "e_games": 11.2} for y, v in zip(years, points)]}


def _row(sleeper_id, name, position, *, population="default", availability_class="active", team="KC", status_raw="ACT", forecast=None,
         now=None, future=None, future_reason=None, missing_reason=None, owned_now=False, roster_id=None, recovered=False,
         starting_estimate=False, estimate_classes=None, player_id="00-1", identity_conflict=None):
    return {"sleeper_id": sleeper_id, "player_id": player_id, "name": name, "league_position": position, "fantasy_positions": position,
            "availability_class": availability_class, "population": population, "nfl_team": team, "nfl_status_raw": status_raw,
            "join_basis": "sleeper_id", "identity_conflict": identity_conflict, "now_points": now, "future_points": future,
            "future_years": [2027, 2028, 2029, 2030], "future_reason": future_reason, "missing_reason": missing_reason,
            "impact": {"h2": None, "h5": None}, "readiness": None, "owned_now": owned_now, "roster_id": roster_id, "recovered": recovered,
            "forecast_path": {"status": "complete" if forecast else "none", "years_present": [s["season"] for s in (forecast or {}).get("seasons", [])]},
            "starting_estimate": starting_estimate, "estimate_classes": estimate_classes, "forecast": forecast}


def _catalog_rows():
    starting_classes = {"2026": "cold_start_candidate", **{str(y): "baseline_research_candidate" for y in YEARS[1:]}}
    return [
        _row("200", "Free Wideout", "WR", forecast=_forecast([120.5, 110.0, 100.0, 90.0, 80.0]), now=120.5, future=380.0),
        _row("201", "Practice Guy", "WR", availability_class="practice_squad", status_raw="DEV", player_id=None,
             missing_reason="no forecast from the selected producers; no reason stated"),
        _row("202", "Negative Rookie", "QB", availability_class="injured_reserve", status_raw="RES", player_id=None,
             forecast=_forecast([-0.3, 10.0, 11.0, 9.0, 6.0], producer="DG-165 cold-start research candidate (starting estimate):dg165_cold_start_candidate_v1",
                                join_basis="cold_start_census_nfl_gsis", join_id="00-2"),
             now=-0.3, future=36.0, starting_estimate=True, estimate_classes=starting_classes),
        _row("203", "Cut Passer", "QB", population="cut", availability_class="cut", team="SF", status_raw="CUT",
             forecast=_forecast([50.0, 25.0, 25.0, 25.0, 25.0], join_id="00-3"), now=50.0, future=100.0),
        _row("204", "Recovered Back", "RB", availability_class="practice_squad", status_raw="DEV", player_id=None, recovered=True,
             forecast=_forecast([10.197681979436744, 3.770280866250476, 2.522325552928488, 1.1616111469658732, 1.0910309232898907],
                                join_basis="recovered_census_nfl_gsis", join_id="00-4"),
             now=10.197681979436744, future=8.545248489434728),
        _row("205", "Zero Season", "TE", forecast=_forecast([0.0, 5.0, 5.0, 5.0, 5.0], join_id="00-5"), now=0.0, future=20.0),
        _row("206", "Unknown Tight", "TE", population="unknown", availability_class="unknown", team=None, status_raw=None, player_id=None,
             identity_conflict="nflverse row for gsis 00-0035718 names Sleeper id 6118, not 6618; incompatible source ids",
             missing_reason="no forecast from the selected producers; no reason stated"),
        # owned rows ride along in the catalog as identity/status-only rows; they are never available choices
        _row("11565", "J.J. McCarthy", "QB", population="owned", team="MIN", owned_now=True, roster_id=1, player_id="00-0039923",
             missing_reason="owned in your league; forecasts are shown on the research board"),
        _row("11576", "Braelon Allen", "RB", population="owned", team="NYJ", owned_now=True, roster_id=1, player_id="00-0039794",
             missing_reason="owned in your league; forecasts are shown on the research board"),
        _row("13269", "Fernando Mendoza", "QB", population="owned", team="LV", availability_class="injured_reserve", status_raw="RES",
             owned_now=True, roster_id=1, player_id="fernando_mendoza_qb", missing_reason="owned in your league; forecasts are shown on the research board"),
        _row("9502", "Tank Dell", "WR", population="owned", team="HOU", owned_now=True, roster_id=1, player_id=None,
             missing_reason="owned in your league; forecasts are shown on the research board"),
        _row("96", "Aaron Rodgers", "QB", population="owned", team="PIT", owned_now=True, roster_id=4, player_id="00-0023459",
             missing_reason="owned in your league; forecasts are shown on the research board"),
    ]


def _catalog(report_sha, *, run="20260907T013635Z", report_run="20260906T214512Z", rows=None):
    return {"run": run, "source_report_run": report_run, "census_run_id": "20260906T202057Z",
            "populations": {"default": {"total": 6}, "cut": {"total": 1}, "unknown": {"total": 1}, "owned": {"total": 5}},
            "ownership_as_of": "2026-09-06T13:00:52.635970+00:00", "nfl_status_as_of": "Sun, 06 Sep 2026 11:28:11 GMT",
            "sources": {"report_sha256": report_sha, "report_run": report_run, "snapshot_sha256": SNAPSHOT_SHA, "producers": {}},
            "forecast_note": "values are the producers' own expected season points (nflverse default PPR, championship window) …",
            "forecast_years": list(YEARS), "future_years": YEARS[1:], "rows": 12, "rows_detail": rows if rows is not None else _catalog_rows()}


def _inputs(report=None, mutate_catalog=None, **catalog_kwargs):
    report = report if report is not None else _report()
    report_bytes = json.dumps(report).encode("utf-8")
    catalog = _catalog(hashlib.sha256(report_bytes).hexdigest(), **catalog_kwargs)
    if mutate_catalog:
        mutate_catalog(catalog)
    return report_bytes, catalog


def _build(report_bytes, catalog, **kw):
    kw.setdefault("report_run", "20260906T214512Z")
    kw.setdefault("catalog_run", catalog["run"])
    return build_comparison(report_bytes, catalog, **kw)


# --- the happy path -----------------------------------------------------------------------------


def test_the_payload_binds_both_sources_and_names_the_window_and_the_scoring() -> None:
    report_bytes, catalog = _inputs()
    out = _build(report_bytes, catalog)
    assert out["source"]["report_run"] == "20260906T214512Z" and out["source"]["catalog_run"] == "20260907T013635Z"
    assert out["source"]["report_sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert set(out["source"]) == {"report_run", "catalog_run", "report_sha256", "ownership_as_of", "nfl_status_as_of"}
    assert out["source"]["ownership_as_of"] == "2026-09-06T13:00:52.635970+00:00"
    assert out["source"]["nfl_status_as_of"] == "Sun, 06 Sep 2026 11:28:11 GMT"
    assert out["forecast_years"] == YEARS and out["future_years"] == [2027, 2028, 2029, 2030]
    note = out["scoring_note"]
    assert "PPR" in note and "week 17" in note and "not your league's exact scoring" in note
    assert set(out) == {"source", "forecast_years", "future_years", "scoring_note", "available", "roster"}


def test_available_rows_come_from_the_catalog_with_owned_rows_excluded_and_five_aligned_seasons() -> None:
    out = _build(*_inputs())
    by = {r["sleeper_id"]: r for r in out["available"]}
    assert set(by) == {"200", "201", "202", "203", "204", "205", "206"}     # no owned row, whatever its roster
    fw = by["200"]
    assert fw["name"] == "Free Wideout" and fw["position"] == "WR" and fw["team"] == "KC"
    assert fw["population"] == "default" and fw["status"] == "active" and fw["starting_estimate"] is False
    assert fw["now_points"] == 120.5 and fw["future_points"] == 380.0 and fw["missing_reason"] is None
    assert [s["season"] for s in fw["seasons"]] == YEARS
    assert [s["points"] for s in fw["seasons"]] == [120.5, 110.0, 100.0, 90.0, 80.0]
    assert all(s["estimate_class"] is None for s in fw["seasons"])
    assert by["203"]["population"] == "cut" and by["203"]["status"] == "cut" and by["203"]["now_points"] == 50.0
    assert by["206"]["population"] == "unknown" and by["206"]["status"] == "unknown" and by["206"]["team"] is None
    assert by["204"]["now_points"] == 10.197681979436744 and by["204"]["future_points"] == 8.545248489434728
    assert "recovered" in by["204"]["evidence_note"]
    # the expected keys, exactly, on every player
    keys = {"sleeper_id", "name", "position", "team", "population", "status", "now_points", "future_points", "seasons",
            "starting_estimate", "missing_reason", "evidence_note", "taxi_or_reserve"}
    assert all(r["taxi_or_reserve"] is None for r in out["available"])
    assert all(set(r) == keys for r in out["available"] + out["roster"])
    assert all(set(s) == {"season", "points", "estimate_class"} for r in out["available"] + out["roster"] for s in r["seasons"])


def test_roster_rows_reconstruct_from_the_signed_margin_plus_that_seasons_reference_at_full_precision() -> None:
    out = _build(*_inputs())
    by = {r["sleeper_id"]: r for r in out["roster"]}
    assert set(by) == {"11565", "11576", "13269", "9502"}
    jj = by["11565"]
    expected = [m + r for m, r in zip(MCCARTHY_MARGINS, QB_SERIES)]
    assert [s["points"] for s in jj["seasons"]] == expected                 # exact, no rounding
    assert jj["seasons"][0]["points"] == 112.00667587080359
    assert jj["now_points"] == expected[0] and jj["future_points"] == sum(expected[1:])
    assert jj["population"] == "owned" and jj["status"] == "active" and jj["team"] == "MIN" and jj["position"] == "QB"
    assert jj["starting_estimate"] is False and jj["missing_reason"] is None
    assert all(s["estimate_class"] is None for s in jj["seasons"])
    assert "Joe Flacco" in jj["evidence_note"] and "signed margin" in jj["evidence_note"]
    # a below-reference season is a NEGATIVE margin plus the reference: the clipped advantage (0.0) is never used
    ba = by["11576"]
    assert ba["seasons"][0]["points"] == 88.2770971070361 - 53.61265642415228
    assert ba["seasons"][1]["points"] == 46.1704555773408 - 3.499953259581865
    # a rookie-producer row reconstructs the same way, by index against its position's series
    fm = by["13269"]
    assert fm["seasons"][0]["points"] == 80.54624873061018 + 115.32497628242587
    assert fm["status"] == "injured_reserve"                                 # status joins from the catalog by Sleeper id


def test_a_negative_starting_estimate_and_a_known_zero_survive_and_missing_stays_null() -> None:
    out = _build(*_inputs())
    by = {r["sleeper_id"]: r for r in out["available"]}
    neg = by["202"]
    assert neg["starting_estimate"] is True and neg["now_points"] == -0.3 and neg["future_points"] == 36.0
    assert [s["estimate_class"] for s in neg["seasons"]] == ["cold_start_candidate"] + ["baseline_research_candidate"] * 4
    assert "draft-capital" in neg["evidence_note"] and "historical baseline" in neg["evidence_note"]
    assert "not a breakout probability" in neg["evidence_note"] and "2027" in neg["evidence_note"]
    zero = by["205"]
    assert zero["now_points"] == 0.0 and zero["now_points"] is not None and zero["seasons"][0]["points"] == 0.0
    miss = by["201"]
    assert miss["now_points"] is None and miss["future_points"] is None
    assert [s["points"] for s in miss["seasons"]] == [None] * 5 and [s["season"] for s in miss["seasons"]] == YEARS
    assert miss["missing_reason"] == "no forecast from the selected producers; no reason stated"
    assert miss["evidence_note"].startswith("No accepted forecast")


def test_an_incomplete_future_is_null_with_the_reason_and_an_unsupported_year_is_labelled() -> None:
    def mutate(c):
        r = next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")
        r["forecast"]["seasons"] = [s for s in r["forecast"]["seasons"] if s["season"] != 2030]
        r["future_points"] = None
        r["future_reason"] = "2030 unsupported by the producer: future total undefined, not zero"
        r["forecast_path"] = {"status": "incomplete", "years_present": [2026, 2027, 2028, 2029]}
    out = _build(*_inputs(mutate_catalog=mutate))
    fw = next(r for r in out["available"] if r["sleeper_id"] == "200")
    assert fw["now_points"] == 120.5 and fw["future_points"] is None
    assert fw["missing_reason"] == "2030 unsupported by the producer: future total undefined, not zero"
    assert [s["points"] for s in fw["seasons"]] == [120.5, 110.0, 100.0, 90.0, None]
    assert [s["estimate_class"] for s in fw["seasons"]] == [None, None, None, None, "unsupported"]


def test_a_roster_row_without_seasons_is_null_with_a_plain_reason_not_zero() -> None:
    out = _build(*_inputs())
    dell = next(r for r in out["roster"] if r["sleeper_id"] == "9502")
    assert dell["now_points"] is None and dell["future_points"] is None
    assert [s["points"] for s in dell["seasons"]] == [None] * 5 and [s["season"] for s in dell["seasons"]] == YEARS
    assert dell["missing_reason"].startswith("No forecast from the selected producers")
    assert "not a zero" in dell["missing_reason"] and "annual producer" not in dell["missing_reason"]
    assert "not forecast by any annual producer" in dell["evidence_note"]     # the raw reason rides in the evidence


# --- refusals: binding, window, values, identity ------------------------------------------------


def _refuses(report_bytes, catalog, *needles, **kw):
    with pytest.raises(ComparisonSourceError) as e:
        _build(report_bytes, catalog, **kw)
    for n in needles:
        assert n in str(e.value), (n, str(e.value))


def test_a_catalog_that_does_not_bind_the_report_bytes_or_names_another_run_is_refused() -> None:
    rb, cat = _inputs()
    _refuses(rb, dict(cat, sources={**cat["sources"], "report_sha256": "19e0" + "0" * 60}), "report_sha256")
    _refuses(rb + b" ", cat, "report_sha256")                                  # the bytes served are not the bytes bound
    _refuses(rb, dict(cat, source_report_run="20260906T203007Z"), "20260906T203007Z", "source_report_run")
    _refuses(rb, cat, "run", report_run="20260906T203007Z")
    _refuses(rb, cat, "catalog", catalog_run="20260907T000000Z")


def test_a_snapshot_mismatch_or_an_unstated_snapshot_on_either_side_is_refused() -> None:
    rb, cat = _inputs()
    _refuses(rb, dict(cat, sources={**cat["sources"], "snapshot_sha256": "f" * 64}), "snapshot")
    _refuses(rb, dict(cat, sources={k: v for k, v in cat["sources"].items() if k != "snapshot_sha256"}), "snapshot")
    rep = _report()
    rep["inputs"]["snapshot"].pop("sha256")
    _refuses(*_inputs(report=rep), "snapshot")


def test_a_divergent_window_is_refused_on_either_side() -> None:
    rb, cat = _inputs()
    _refuses(rb, dict(cat, future_years=[2027, 2028, 2029]), "future_years")
    _refuses(rb, dict(cat, forecast_years=[2026, 2027, 2028, 2029, 2030, 2031]), "forecast_years")
    rep = _report()
    rep["horizon_board"]["davids_roster"][0]["seasons"].append({"season": 2031, "expected_margin": 1.0, "action": "retain", "advantage": 1.0})
    _refuses(*_inputs(report=rep), "11565", "2031")
    rep = _report()
    rep["horizon_board"]["davids_roster"][0]["seasons"][1]["season"] = 2027.5
    _refuses(*_inputs(report=rep), "11565", "2027.5")
    rep = _report()
    rep["horizon_board"]["davids_roster"][0]["seasons"][1]["season"] = "2027"
    _refuses(*_inputs(report=rep), "11565", "2027")


def test_a_roster_path_missing_a_year_is_missing_not_malformed() -> None:
    """Root, 2026-09-07: an absent player-specific year is MISSING — align the five years with null there
    and a null future total; only duplicate, foreign or non-integral years and non-finite present values
    are malformed."""
    rep = _report()
    rep["horizon_board"]["davids_roster"][0]["seasons"].pop()                 # 2026–2029 present, 2030 absent
    out = _build(*_inputs(report=rep))
    jj = next(r for r in out["roster"] if r["sleeper_id"] == "11565")
    assert [s["season"] for s in jj["seasons"]] == YEARS
    assert [s["points"] for s in jj["seasons"]][:4] == [m + r for m, r in zip(MCCARTHY_MARGINS[:4], QB_SERIES[:4])]
    assert jj["seasons"][4]["points"] is None and jj["seasons"][4]["estimate_class"] is None
    assert jj["now_points"] == MCCARTHY_MARGINS[0] + QB_SERIES[0] and jj["future_points"] is None
    assert "2030" in jj["missing_reason"] and "not zero" in jj["missing_reason"]


def test_the_reference_series_must_be_season_points_and_reach_every_season() -> None:
    rep = _report()
    union = next(m for m in rep["horizon_board"]["annual_producers"] if m["model_version"] == "union_replacement")
    union["replacement"]["QB"] = union["replacement"]["QB"][:4]
    _refuses(*_inputs(report=rep), "QB", "reference")
    rep = _report()
    union = next(m for m in rep["horizon_board"]["annual_producers"] if m["model_version"] == "union_replacement")
    union["replacement"]["QB"][2] = _union_entry("QB", 9.4068, quantity="ppg_rate")
    _refuses(*_inputs(report=rep), "QB", "rate_quantity")
    rep = _report()
    rep["horizon_board"]["annual_producers"] = [m for m in rep["horizon_board"]["annual_producers"] if m["model_version"] != "union_replacement"]
    _refuses(*_inputs(report=rep), "union_replacement")


def test_non_finite_values_duplicate_seasons_and_an_overflowing_future_are_refused_not_zeroed() -> None:
    def nan_points(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["forecast"]["seasons"][1]["e_points"] = float("nan")
    _refuses(*_inputs(mutate_catalog=nan_points), "200", "finite")

    def stored_inf(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["future_points"] = float("inf")
    _refuses(*_inputs(mutate_catalog=stored_inf), "200", "finite")

    def twice(c):
        s = next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["forecast"]["seasons"]
        s[3] = dict(s[3], season=2028)
    _refuses(*_inputs(mutate_catalog=twice), "200", "2028")

    def overflow(c):
        r = next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")
        for s in r["forecast"]["seasons"][1:]:
            s["e_points"] = 1e308
        r["future_points"] = 4e308      # json would already have turned this into Infinity
    _refuses(*_inputs(mutate_catalog=overflow), "200", "finite")

    rep = _report()
    rep["horizon_board"]["davids_roster"][0]["seasons"][2]["expected_margin"] = float("inf")
    _refuses(*_inputs(report=rep), "11565", "finite")
    rep = _report()
    s = rep["horizon_board"]["davids_roster"][0]["seasons"]
    s[1]["season"] = 2028
    _refuses(*_inputs(report=rep), "11565", "2028")


def test_a_catalog_whose_stored_now_or_future_disagrees_with_its_own_seasons_is_refused() -> None:
    def now_off(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["now_points"] = 121.0
    _refuses(*_inputs(mutate_catalog=now_off), "200", "now_points")

    def future_off(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["future_points"] = 381.0
    _refuses(*_inputs(mutate_catalog=future_off), "200", "future_points")

    def future_claimed_without_every_year(c):
        r = next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")
        r["forecast"]["seasons"].pop()
    _refuses(*_inputs(mutate_catalog=future_claimed_without_every_year), "200", "future_points")


def test_duplicate_or_shared_sleeper_ids_are_refused() -> None:
    def dup(c):
        c["rows_detail"].append(copy.deepcopy(c["rows_detail"][0]))
    _refuses(*_inputs(mutate_catalog=dup), "200", "duplicate")

    def shared(c):
        r = copy.deepcopy(c["rows_detail"][0])
        r["sleeper_id"] = "11565"                                             # McCarthy's id on an unowned row
        c["rows_detail"] = [x for x in c["rows_detail"] if x["sleeper_id"] != "11565"] + [r]
    _refuses(*_inputs(mutate_catalog=shared), "11565")

    rep = _report()
    rep["horizon_board"]["davids_roster"].append(copy.deepcopy(rep["horizon_board"]["davids_roster"][0]))
    _refuses(*_inputs(report=rep), "11565", "duplicate")


def test_roster_and_catalog_must_describe_the_same_owned_players() -> None:
    def missing_owned(c):
        c["rows_detail"] = [x for x in c["rows_detail"] if x["sleeper_id"] != "11576"]
    _refuses(*_inputs(mutate_catalog=missing_owned), "11576")

    def other_roster(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "11576")["roster_id"] = 7
    _refuses(*_inputs(mutate_catalog=other_roster), "11576", "roster")

    def other_position(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "11576")["league_position"] = "WR"
    _refuses(*_inputs(mutate_catalog=other_position), "11576", "position")

    def owned_flag_on_default(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "200")["owned_now"] = True
    _refuses(*_inputs(mutate_catalog=owned_flag_on_default), "200", "owned")

    rep = _report()
    rep["horizon_board"]["davids_roster"][1]["rostered_by"] = 2
    _refuses(*_inputs(report=rep), "11576", "rostered_by")
    rep = _report()
    rep["horizon_board"]["davids_roster"][1]["on_davids_roster"] = False
    _refuses(*_inputs(report=rep), "11576", "on_davids_roster")


def test_names_are_never_used_to_join_the_two_sources() -> None:
    """The accepted sources spell two of David's players differently (Omar Cooper Jr. / Omar Cooper); the
    join is the Sleeper id and the roster keeps the board's spelling."""
    def respell(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "11565")["name"] = "JJ McCarthy"
    out = _build(*_inputs(mutate_catalog=respell))
    assert next(r for r in out["roster"] if r["sleeper_id"] == "11565")["name"] == "J.J. McCarthy"


def test_nothing_is_rounded_anywhere() -> None:
    out = _build(*_inputs())
    jj = next(r for r in out["roster"] if r["sleeper_id"] == "11565")
    assert math.fsum([]) == 0.0
    assert repr(jj["seasons"][0]["points"]) == "112.00667587080359"
    rb = next(r for r in out["available"] if r["sleeper_id"] == "204")
    assert repr(rb["future_points"]) == "8.545248489434728"


def test_the_taxi_or_reserve_label_comes_from_the_saved_lineup_exclusions_and_is_unknown_when_unstated() -> None:
    """Root F4 (2026-09-07): a factual label about the saved roster, never an inferred storage type or a
    freed active spot; absent source → null, not false; a listed id off the roster is refused."""
    out = _build(*_inputs())
    by = {r["sleeper_id"]: r for r in out["roster"]}
    assert by["11576"]["taxi_or_reserve"] is True and by["13269"]["taxi_or_reserve"] is True and by["9502"]["taxi_or_reserve"] is True
    assert by["11565"]["taxi_or_reserve"] is False
    rep = _report()
    rep.pop("davids_best_lineup_served_h0")
    out = _build(*_inputs(report=rep))
    assert all(r["taxi_or_reserve"] is None for r in out["roster"])
    rep = _report()
    rep["davids_best_lineup_served_h0"]["excluded_taxi_or_reserve"].append("4984")     # Josh Allen is not David's
    _refuses(*_inputs(report=rep), "4984", "excluded_taxi_or_reserve")


# --- root's early review (2026-09-07): four more things the payload must refuse or withhold --------


def test_the_board_target_must_be_the_accepted_target_and_the_forecast_date_must_open_the_window() -> None:
    """The comparison is defined on the accepted research target (REG scope, nflverse default PPR,
    championship window through week 17, season points per season). A report on another target is
    refused, never described as accepted by the scoring note."""
    for key, value in (("scoring", "PPR_league_exact"), ("window", "all_reg_weeks"), ("scope", "ALL"), ("quantity", "ppg_rate"), ("clock", "two_season_window")):
        rep = _report()
        rep["board_target"][key] = value
        _refuses(*_inputs(report=rep), key, value)
    rep = _report()
    rep["board_target"].pop("scoring")
    _refuses(*_inputs(report=rep), "scoring")
    rep = _report()
    rep["forecast_date"] = "2025-09-06"
    _refuses(*_inputs(report=rep), "forecast_date", "2026")
    rep = _report()
    rep.pop("forecast_date")
    _refuses(*_inputs(report=rep), "forecast_date")


def test_the_five_year_view_is_resolved_through_comparable_views_with_one_union_reference_of_exactly_five_seasons() -> None:
    rep = _report()
    rep.pop("comparable_views")
    _refuses(*_inputs(report=rep), "comparable_views")
    rep = _report()
    rep["comparable_views"]["h5"] = "comparable_board"
    rep["comparable_board"] = {"annual_producers": [], "horizons_summed": 2, "davids_roster": []}
    _refuses(*_inputs(report=rep), "horizons_summed")
    rep = _report()
    rep["horizon_board"]["horizons_summed"] = 2
    _refuses(*_inputs(report=rep), "horizons_summed", "2")
    rep = _report()
    union = next(m for m in rep["horizon_board"]["annual_producers"] if m["model_version"] == "union_replacement")
    rep["horizon_board"]["annual_producers"].append(copy.deepcopy(union))
    _refuses(*_inputs(report=rep), "union_replacement", "2")
    rep = _report()
    union = next(m for m in rep["horizon_board"]["annual_producers"] if m["model_version"] == "union_replacement")
    union["replacement"]["QB"].append(_union_entry("QB", 10.0))                 # six seasons for a five-year window
    _refuses(*_inputs(report=rep), "QB", "reference", "6")


def test_an_unverified_or_not_comparable_roster_number_is_withheld_with_the_reason_never_shown_as_accepted() -> None:
    rep = _report()
    row = rep["horizon_board"]["davids_roster"][0]
    row["readiness"] = "unverified"
    row["evidence_verified"] = False
    row["reason"] = "unverified: the producer's evidence identity could not be verified (manifest declares no sha256 for the scoring CSV)"
    out = _build(*_inputs(report=rep))
    jj = next(r for r in out["roster"] if r["sleeper_id"] == "11565")
    assert jj["now_points"] is None and jj["future_points"] is None and [s["points"] for s in jj["seasons"]] == [None] * 5
    assert "could not be verified" in jj["missing_reason"] and jj["evidence_note"].startswith("Not an accepted forecast")
    assert "Accepted" not in jj["evidence_note"]
    rep = _report()
    row = rep["horizon_board"]["davids_roster"][0]
    row["evidence_verified"] = False                                            # readiness still says comparable
    out = _build(*_inputs(report=rep))
    jj = next(r for r in out["roster"] if r["sleeper_id"] == "11565")
    assert jj["now_points"] is None and "verified" in jj["missing_reason"] and jj["evidence_note"].startswith("Not an accepted forecast")
    rep = _report()
    row = rep["horizon_board"]["davids_roster"][0]
    row["readiness"] = "research_only"
    row["reason"] = "not comparable with the board target"
    out = _build(*_inputs(report=rep))
    jj = next(r for r in out["roster"] if r["sleeper_id"] == "11565")
    assert jj["now_points"] is None and "not comparable with the board target" in jj["missing_reason"]


def test_davids_full_membership_is_checked_against_the_catalogs_owned_rows_not_only_the_supplied_report_rows() -> None:
    rep = _report()
    rep["horizon_board"]["davids_roster"] = rep["horizon_board"]["davids_roster"][:-1]      # Tank Dell dropped from the board
    _refuses(*_inputs(report=rep), "9502", "roster")
    rep = _report()
    rep["horizon_board"]["davids_roster"] = []
    _refuses(*_inputs(report=rep), "roster")

    def owned_flag_false(c):
        next(x for x in c["rows_detail"] if x["sleeper_id"] == "11565")["owned_now"] = False
    _refuses(*_inputs(mutate_catalog=owned_flag_false), "11565", "owned_now")

    def extra_owned_by_david(c):
        c["rows_detail"].append(_row("777", "Phantom Owned", "RB", population="owned", owned_now=True, roster_id=1,
                                     missing_reason="owned in your league; forecasts are shown on the research board"))
    _refuses(*_inputs(mutate_catalog=extra_owned_by_david), "777", "roster")
