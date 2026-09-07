"""DG-182: GET /api/research/comparison serves David's roster (from the served report's five-year
view) beside the unowned rows of the catalog bound to that report — the same pinned run and the
same catalog binding the available-players route uses; a catalog from another report or with
tampered bytes is an explicit error, never a silently substituted one.

The second half runs against the FROZEN tracked inputs in this checkout (report 20260906T214512Z,
catalog 20260907T013635Z) and proves the reconstruction against the ORIGINAL producer files through
the accepted identity bridge — by Sleeper id → gsis, never by name.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CHECKOUT = Path(__file__).resolve().parents[2]
FROZEN_REPORT_RUN, FROZEN_REPORT_SHA = "20260906T214512Z", "19e032a4067dff1759199a84720c0f879bb61f792fd3b2703808b55485a7af37"
FROZEN_CATALOG_RUN, FROZEN_CATALOG_SHA = "20260907T013635Z", "d08e89087c5038439d81421cfacba186ebedd4619be9d0015a9c42b74938597e"
QB_SERIES = [115.32497628242587, 85.90292286152696, 44.487410939143025, 31.467770472882492, 17.583689420821695]
YEARS = [2026, 2027, 2028, 2029, 2030]


# --- a small runs root, written the way the immutable builder writes -----------------------------


def _report(run="20260906T214512Z"):
    union = {"model_version": "union_replacement", "seasons": 5, "positions_without_a_bar": [],
             "replacement": {"QB": [{"position": "QB", "rate_ppg": r, "rate_quantity": "expected_season_points_same_window",
                                     "player_name": "Joe Flacco", "pool_complete": True} for r in QB_SERIES]}}
    mccarthy = {"player_id": "00-0039923", "sleeper_id": "11565", "name": "J.J. McCarthy", "position": "QB", "team": "MIN", "age": 23.0,
                "value": 192.5, "readiness": "comparable", "reason": None, "producer": "DG-177 veteran annual forecast candidate (report-only):basic_cohort_3col_plus_lags",
                "estimate_class": "candidate", "evidence_verified": True, "reference_player": "Joe Flacco", "reference_expected_points": QB_SERIES[0],
                "seasons": [{"season": y, "expected_margin": m, "action": "retain", "advantage": max(m, 0.0)}
                            for y, m in zip(YEARS, [-3.3183004116222747, 12.848557384333802, 48.62145323820008, 60.41020979991474, 70.58621745986794])],
                "rostered_by": 1, "on_davids_roster": True}
    return {"run": run, "forecast_date": "2026-09-06",
            "board_target": {"scope": "REG", "scoring": "PPR_nflverse_default", "window": "championship_week17", "quantity": "season_points", "clock": "per_season"},
            "outcome_artifact": {"scoring_preset": "nflverse_default_ppr_championship_window_v1", "league_scoring_exact": False},
            "inputs": {"snapshot": {"id": "league-20260906T130052Z", "sha256": "e" * 64}},
            "comparable_views": {"h2": "comparable_board", "h5": "horizon_board"},
            "davids_best_lineup_served_h0": {"excluded_taxi_or_reserve": []},
            "comparable_board": {"annual_producers": [], "readiness": {}, "davids_roster": [], "league_rostered": [], "top": [], "all_inspectable": []},
            "horizon_board": {"n_comparable": 1, "horizons_summed": 5, "annual_producers": [union], "davids_roster": [mccarthy],
                              "league_rostered": [], "top": [], "all_inspectable": []}}


def _row(sleeper_id, name, position, **over):
    base = {"sleeper_id": sleeper_id, "player_id": None, "name": name, "league_position": position, "fantasy_positions": position,
            "availability_class": "active", "population": "default", "nfl_team": "KC", "nfl_status_raw": "ACT", "join_basis": "sleeper_id",
            "identity_conflict": None, "now_points": None, "future_points": None, "future_years": YEARS[1:], "future_reason": None,
            "missing_reason": "no forecast from the selected producers; no reason stated", "impact": {"h2": None, "h5": None}, "readiness": None,
            "owned_now": False, "roster_id": None, "recovered": False, "forecast_path": {"status": "none", "years_present": []},
            "starting_estimate": False, "estimate_classes": None, "forecast": None}
    return {**base, **over}


def _catalog(report_run="20260906T214512Z", run="20260906T230000Z"):
    points = [120.5, 110.0, 100.0, 90.0, 80.0]
    forecast = {"producer": "DG-177 veteran annual forecast candidate (report-only):basic_cohort_3col_plus_lags", "source_csv": "x.csv",
                "source_csv_sha256": "a" * 64, "join_basis": "report_gsis", "join_id": "00-3",
                "seasons": [{"season": y, "e_points": v, "p_appear": 0.8, "e_points_given_appear": v / 0.8, "e_games": 11.2} for y, v in zip(YEARS, points)]}
    rows = [_row("200", "Free Wideout", "WR", player_id="00-3", now_points=120.5, future_points=380.0, missing_reason=None, forecast=forecast,
                 forecast_path={"status": "complete", "years_present": YEARS}),
            _row("201", "Practice Guy", "WR", availability_class="practice_squad", nfl_status_raw="DEV"),
            _row("11565", "J.J. McCarthy", "QB", player_id="00-0039923", population="owned", nfl_team="MIN", owned_now=True, roster_id=1,
                 missing_reason="owned in your league; forecasts are shown on the research board")]
    return {"run": run, "source_report_run": report_run, "census_run_id": "20260906T202057Z",
            "populations": {"default": {"total": 2}, "owned": {"total": 1}}, "populations_note": "default = …",
            "disclosures": {"uncovered_sleeper_ids": 0, "unmatched_nfl_records": 0, "contested_nfl_records": 0, "archive_unforecast_by_position": {}, "note": ""},
            "ownership_as_of": "2026-09-06T13:00:52+00:00", "nfl_status_as_of": "Sun, 06 Sep 2026 11:28:11 GMT",
            "sources": {"report_sha256": "19e0" + "0" * 60, "snapshot_sha256": "e" * 64, "producers": {}},
            "forecast_note": "…", "forecast_years": YEARS, "future_years": YEARS[1:], "rows": 3, "provenance": {"git_head": "abc", "git_dirty": False},
            "rows_detail": rows}


def _write(tmp_path, catalogs, audit_runs=("20260906T214512Z",), *, bind=True):
    report_sha = {}
    for ar in audit_runs:
        d = tmp_path / "runs" / ar / "dg178_audit"
        d.mkdir(parents=True)
        (d / "report.json").write_text(json.dumps(_report(ar)))
        report_sha[ar] = hashlib.sha256((d / "report.json").read_bytes()).hexdigest()
    for c in catalogs:
        if bind:
            c["sources"]["report_sha256"] = report_sha[c["source_report_run"]]
        d = tmp_path / "runs" / c["run"] / "dg178_available_catalog"
        d.mkdir(parents=True)
        (d / "catalog.json").write_text(json.dumps(c))
        (d / "report.json").write_text(json.dumps({"run": c["run"], "source_report_run": c["source_report_run"],
                                                   "outputs_sha256": {"catalog.json": hashlib.sha256((d / "catalog.json").read_bytes()).hexdigest()}}))


def _client(runs_root, monkeypatch, pinned="20260906T214512Z"):
    monkeypatch.setenv("DG178_RUNS_ROOT", str(runs_root))
    monkeypatch.setenv("DG178_PREVIEW_RUN", pinned)
    from app.main import app

    return TestClient(app)


def test_the_comparison_is_served_for_the_pinned_run_and_its_bound_catalog(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog()])
    body = _client(tmp_path / "runs", monkeypatch).get("/api/research/comparison").json()
    assert body["source"]["report_run"] == "20260906T214512Z" and body["source"]["catalog_run"] == "20260906T230000Z"
    assert body["source"]["report_sha256"] == hashlib.sha256((tmp_path / "runs" / "20260906T214512Z" / "dg178_audit" / "report.json").read_bytes()).hexdigest()
    assert body["source"]["ownership_as_of"] == "2026-09-06T13:00:52+00:00" and body["source"]["nfl_status_as_of"] == "Sun, 06 Sep 2026 11:28:11 GMT"
    assert body["forecast_years"] == YEARS and body["future_years"] == YEARS[1:]
    assert "not your league's exact scoring" in body["scoring_note"]
    assert [r["sleeper_id"] for r in body["available"]] == ["200", "201"]                # the owned row is not an available choice
    assert body["available"][0]["now_points"] == 120.5 and body["available"][0]["future_points"] == 380.0
    assert body["available"][1]["now_points"] is None and body["available"][1]["missing_reason"].startswith("no forecast")
    (jj,) = body["roster"]
    assert jj["sleeper_id"] == "11565" and jj["team"] == "MIN" and jj["status"] == "active" and jj["population"] == "owned"
    assert jj["seasons"][0]["points"] == 112.00667587080359 and jj["now_points"] == 112.00667587080359
    assert jj["future_points"] == sum(m + r for m, r in zip([12.848557384333802, 48.62145323820008, 60.41020979991474, 70.58621745986794], QB_SERIES[1:]))
    assert jj["taxi_or_reserve"] is False


def test_a_catalog_from_another_report_is_refused_and_the_other_run_stays_addressable(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(report_run="20260906T203007Z", run="20260906T230100Z")], audit_runs=("20260906T203007Z", "20260906T214512Z"))
    c = _client(tmp_path / "runs", monkeypatch)
    r = c.get("/api/research/comparison")
    assert r.status_code == 404 and "no available-player catalog" in r.json()["detail"]
    ok = c.get("/api/research/comparison", params={"run": "20260906T203007Z"}).json()
    assert ok["source"]["report_run"] == "20260906T203007Z" and ok["source"]["catalog_run"] == "20260906T230100Z"


def test_a_catalog_that_does_not_bind_the_served_bytes_or_was_tampered_is_refused_not_substituted(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(run="20260906T230000Z"), _catalog(run="20260906T231500Z")])
    newest = tmp_path / "runs" / "20260906T231500Z" / "dg178_available_catalog" / "catalog.json"
    doc = json.loads(newest.read_text())
    doc["rows_detail"][0]["now_points"] = 999.0
    newest.write_text(json.dumps(doc))                                                  # bytes no longer match the companion record
    c = _client(tmp_path / "runs", monkeypatch)
    r = c.get("/api/research/comparison")
    assert r.status_code == 500 and "20260906T231500Z" in r.json()["detail"] and "refus" in r.json()["detail"]
    assert c.get("/api/research/comparison", params={"catalog": "20260906T230000Z"}).json()["source"]["catalog_run"] == "20260906T230000Z"
    # a catalog whose recorded report sha is not the served report's bytes
    _write(tmp_path / "other", [_catalog()], bind=False)
    r = _client(tmp_path / "other" / "runs", monkeypatch).get("/api/research/comparison")
    assert r.status_code == 500 and "report_sha256" in r.json()["detail"]


def test_an_internally_inconsistent_catalog_is_refused_with_the_reason_never_served_partially(tmp_path, monkeypatch) -> None:
    """The route's loader proves the bytes; the adapter proves the numbers. A stored total that
    disagrees with its own seasons is a 500 naming the row, not a payload with one bad number."""
    cat = _catalog()
    cat["rows_detail"][0]["future_points"] = 381.0
    _write(tmp_path, [cat])
    r = _client(tmp_path / "runs", monkeypatch).get("/api/research/comparison")
    assert r.status_code == 500
    assert "200" in r.json()["detail"] and "future_points" in r.json()["detail"] and "not serving a partial" in r.json()["detail"]


# --- the frozen accepted inputs tracked in this checkout ------------------------------------------


def _frozen_or_skip():
    report = CHECKOUT / "runs" / FROZEN_REPORT_RUN / "dg178_audit" / "report.json"
    catalog = CHECKOUT / "runs" / FROZEN_CATALOG_RUN / "dg178_available_catalog" / "catalog.json"
    for p in (report, catalog):
        if not p.exists():
            pytest.skip(f"frozen accepted input absent in this checkout: {p}")
    return report, catalog


@pytest.fixture
def frozen(monkeypatch):
    report, catalog = _frozen_or_skip()
    assert hashlib.sha256(report.read_bytes()).hexdigest() == FROZEN_REPORT_SHA, "the tracked report is not the accepted 214512Z bytes"
    assert hashlib.sha256(catalog.read_bytes()).hexdigest() == FROZEN_CATALOG_SHA, "the tracked catalog is not the accepted 013635Z bytes"
    body = _client(CHECKOUT / "runs", monkeypatch, pinned=FROZEN_REPORT_RUN).get("/api/research/comparison")
    assert body.status_code == 200, body.text
    return body.json(), json.loads(report.read_text())


def test_the_frozen_accepted_inputs_serve_davids_27_beside_510_unowned_with_the_accepted_counts(frozen) -> None:
    body, _ = frozen
    assert body["source"] == {"report_run": FROZEN_REPORT_RUN, "catalog_run": FROZEN_CATALOG_RUN, "report_sha256": FROZEN_REPORT_SHA,
                              "ownership_as_of": "2026-09-06T13:00:52.635970+00:00", "nfl_status_as_of": "Sun, 06 Sep 2026 11:28:11 GMT"}
    assert body["forecast_years"] == YEARS and body["future_years"] == YEARS[1:]
    assert len(body["roster"]) == 27 and len(body["available"]) == 510
    default = [r for r in body["available"] if r["population"] == "default"]
    assert len(default) == 433
    assert sum(1 for r in default if r["now_points"] is not None) == 360
    assert sum(1 for r in default if r["starting_estimate"]) == 7
    assert sum(1 for r in default if r["now_points"] is None) == 73
    assert {r["population"] for r in body["available"]} == {"default", "cut", "retired", "unknown"}
    assert all(r["now_points"] is None for r in default if r["now_points"] is None) and all(len(r["seasons"]) == 5 for r in body["available"] + body["roster"])
    assert len({r["sleeper_id"] for r in body["available"]} & {r["sleeper_id"] for r in body["roster"]}) == 0
    # the real edge cases the brief names, from the actual sources
    by = {r["name"]: r for r in body["available"]}
    assert by["Kurtis Rourke"]["starting_estimate"] is True and by["Kurtis Rourke"]["now_points"] < 0          # a negative starting estimate survives
    assert by["Michael Burton"]["now_points"] == 0.0 and "recovered" in by["Michael Burton"]["evidence_note"]    # a known zero, recovered by identity
    parked = {r["sleeper_id"] for r in body["roster"] if r["taxi_or_reserve"] is True}
    assert parked == {"11576", "12486", "13269", "13276", "9484", "9502"}
    assert all(r["taxi_or_reserve"] is None for r in body["available"])


def test_mccarthys_seasons_are_the_boards_margins_plus_flaccos_series_at_full_precision(frozen) -> None:
    """Values independently reconstructed by root's source oracle
    (DG-180/runs/20260907T095100Z/source_oracle/expected.json)."""
    body, _ = frozen
    jj = next(r for r in body["roster"] if r["sleeper_id"] == "11565")
    assert jj["name"] == "J.J. McCarthy" and jj["position"] == "QB" and jj["team"] == "MIN" and jj["status"] == "active"
    assert [s["points"] for s in jj["seasons"]] == [112.00667587080359, 98.75148024586076, 93.10886417734311, 91.87798027279723, 88.16990688068964]
    assert jj["now_points"] == 112.00667587080359 and jj["future_points"] == 371.90823157669075
    assert jj["missing_reason"] is None and "Joe Flacco" in jj["evidence_note"]
    dell = next(r for r in body["roster"] if r["sleeper_id"] == "9502")
    assert dell["name"] == "Tank Dell" and dell["now_points"] is not None and dell["taxi_or_reserve"] is True


def test_every_roster_season_agrees_with_the_original_producer_through_the_identity_bridge(frozen) -> None:
    """Parity with the ORIGINAL producer files the report declares (bytes verified by sha256),
    resolving each of David's players by Sleeper id → gsis through the accepted identity bridge —
    never by name and never by the report's own player_id (five of them are aliases). Tolerance is
    floating-point addition noise only (root oracle: abs 1e-10 / rel 1e-12)."""
    body, report = frozen
    bridge = report["identity_bridge"]
    producers = [p for p in report["horizon_board"]["annual_producers"] if p.get("csv")]
    for path in [bridge["path"]] + [p["csv"] for p in producers]:
        if not Path(path).exists():
            pytest.skip(f"original producer file absent on this machine: {path}")
    bridge_bytes = Path(bridge["path"]).read_bytes()
    assert hashlib.sha256(bridge_bytes).hexdigest() == bridge["sha256"]
    sleeper_to_gsis = {r["sleeper_id"]: r["gsis_id"] for r in csv.DictReader(io.StringIO(bridge_bytes.decode("utf-8"))) if r.get("gsis_id")}
    tables = {}
    for p in producers:
        data = Path(p["csv"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == p["csv_sha256"], p["csv"]
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
        key = "gsis_id" if "gsis_id" in rows[0] else "player_id"
        tables[p["model_version"]] = {r[key]: r for r in rows}
    checked = 0
    worst = 0.0
    for served in body["roster"]:
        src = next(r for r in report["horizon_board"]["davids_roster"] if str(r["sleeper_id"]) == served["sleeper_id"])
        gsis = sleeper_to_gsis[served["sleeper_id"]]
        prow = tables[src["producer"]][gsis]
        for j, season in enumerate(served["seasons"], start=1):
            original = float(prow[f"e_points_year{j}"])
            assert season["season"] == YEARS[j - 1] and season["points"] is not None
            assert math.isclose(season["points"], original, rel_tol=1e-12, abs_tol=1e-10), (served["name"], season, original)
            worst = max(worst, abs(season["points"] - original))
            checked += 1
    assert checked == 27 * 5 and worst < 1e-10
