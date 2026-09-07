"""Plan T3 (available players): GET /api/research/available serves the newest immutable catalog
built from the SAME accepted report the preview serves (pinned or ?run=); a catalog from another
report is refused with the reason, never silently mixed."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient


def _catalog(report_run="20260906T214512Z", run="20260906T230000Z"):
    row = {"sleeper_id": "200", "player_id": "00-3", "name": "Free Wideout", "league_position": "WR", "fantasy_positions": "WR",
           "availability_class": "active", "population": "default", "nfl_team": "KC", "nfl_status_raw": "ACT",
           "join_basis": "sleeper_id", "identity_conflict": None, "readiness": "comparable",
           "now_points": 120.5, "future_points": 380.0, "future_years": [2027, 2028, 2029, 2030], "future_reason": None,
           "missing_reason": None, "impact": {"h2": 0.0, "h5": 0.0},
           "forecast": {"producer": "vet", "source_csv": "x.csv", "source_csv_sha256": "a" * 64, "join_basis": "report_gsis",
                        "seasons": [{"season": 2026 + i, "e_points": v, "p_appear": 0.8, "e_points_given_appear": v / 0.8, "e_games": 11.2}
                                    for i, v in enumerate([120.5, 110, 100, 90, 80])]}}
    missing = dict(row, sleeper_id="201", player_id=None, name="Practice Guy", availability_class="practice_squad", nfl_status_raw="DEV",
                   readiness=None, now_points=None, future_points=None, forecast=None,
                   missing_reason="no forecast from the selected producers; no reason stated", impact={"h2": None, "h5": None})
    cut = dict(row, sleeper_id="203", name="Cut Passer", league_position="QB", availability_class="cut", population="cut", nfl_status_raw="CUT",
               now_points=50.0, future_points=100.0)
    return {"run": run, "source_report_run": report_run, "census_run_id": "20260906T202057Z",
            "populations": {"default": {"total": 2, "with_forecast": 1, "without_forecast": 1, "by_class": {"active": 1, "practice_squad": 1},
                                        "by_position": {"WR": {"with_forecast": 1, "without_forecast": 1}}},
                            "cut": {"total": 1, "with_forecast": 1, "without_forecast": 0, "by_class": {"cut": 1}, "by_position": {"QB": {"with_forecast": 1, "without_forecast": 0}}}},
            "populations_note": "default = …", "disclosures": {"uncovered_sleeper_ids": 3373, "unmatched_nfl_records": 141, "contested_nfl_records": 1,
                                                                 "archive_unforecast_by_position": {"QB": 368}, "note": "counts only"},
            "ownership_as_of": "2026-09-06T13:00:52+00:00", "nfl_status_as_of": "Sun, 06 Sep 2026 11:28:11 GMT",
            "sources": {"report_sha256": "19e0" + "0" * 60, "census_csv_sha256": "c" * 64, "producers": {}},
            "forecast_note": "values are the producers' own expected season points …", "forecast_years": [2026, 2027, 2028, 2029, 2030],
            "future_years": [2027, 2028, 2029, 2030], "rows": 3, "provenance": {"git_head": "abc", "git_dirty": False},
            "rows_detail": [row, missing, cut]}


def _write(tmp_path, catalogs, audit_runs=("20260906T214512Z",), *, bind=True, companion=True):
    """Write audit reports and catalogs the way the immutable builder does: the catalog records the
    sha256 of the report it read; the companion report.json records the catalog's own bytes."""
    report_sha = {}
    for ar in audit_runs:
        d = tmp_path / "runs" / ar / "dg178_audit"
        d.mkdir(parents=True)
        (d / "report.json").write_text(json.dumps({"run": ar, "comparable_board": {"annual_producers": [], "readiness": {}, "davids_roster": [],
                                                                                    "league_rostered": [], "top": [], "all_inspectable": []},
                                                    "board_target": {}, "inputs": {"snapshot": {"sha256": "e" * 64}}}))
        report_sha[ar] = hashlib.sha256((d / "report.json").read_bytes()).hexdigest()
    for c in catalogs:
        if bind:
            c["sources"]["report_sha256"] = report_sha[c["source_report_run"]]
            c["sources"]["snapshot_sha256"] = "e" * 64
        d = tmp_path / "runs" / c["run"] / "dg178_available_catalog"
        d.mkdir(parents=True)
        (d / "catalog.json").write_text(json.dumps(c))
        if companion:
            (d / "report.json").write_text(json.dumps({"run": c["run"], "source_report_run": c["source_report_run"],
                                                       "outputs_sha256": {"catalog.json": hashlib.sha256((d / "catalog.json").read_bytes()).hexdigest()}}))


@pytest.fixture
def client(tmp_path, monkeypatch):
    _write(tmp_path, [_catalog()])
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("DG178_PREVIEW_RUN", "20260906T214512Z")
    from app.main import app

    return TestClient(app)


def test_the_catalog_is_served_for_the_pinned_preview_run_with_populations_rows_and_freshness(client) -> None:
    body = client.get("/api/research/available").json()
    assert body["source"]["catalog_run"] == "20260906T230000Z" and body["source"]["report_run"] == "20260906T214512Z"
    assert body["source"]["pinned"] is True
    assert body["populations"]["default"]["total"] == 2 and body["populations"]["cut"]["total"] == 1
    assert body["freshness"]["ownership_as_of"] == "2026-09-06T13:00:52+00:00"
    assert body["freshness"]["nfl_status_as_of"] == "Sun, 06 Sep 2026 11:28:11 GMT"
    assert "as of" in body["freshness"]["caveat"] and "may have changed" in body["freshness"]["caveat"]
    rows = {r["sleeper_id"]: r for r in body["rows"]}
    assert rows["200"]["now_points"] == 120.5 and rows["200"]["future_points"] == 380.0 and rows["200"]["future_years"] == [2027, 2028, 2029, 2030]
    assert rows["200"]["forecast"]["seasons"][0]["p_appear"] == 0.8
    assert rows["201"]["now_points"] is None and rows["201"]["missing_reason"].startswith("no forecast")
    assert rows["203"]["population"] == "cut"
    assert body["disclosures"]["unmatched_nfl_records"] == 141
    assert body["notes"]["ownership"].startswith("Ownership filters availability only")
    assert "not weekly start advice" in body["notes"]["now"] and "2027–2030" in body["notes"]["future"]
    assert "P(appears)" in body["notes"]["appearance"] and "not" in body["notes"]["appearance"]
    assert body["starting_estimates"] == {"count": 0, "rows": [], "source": None, "evidence": None}   # none in this catalog
    assert "not a breakout probability" in body["notes"]["starting_estimate"]


def test_a_catalog_from_another_report_is_refused_not_mixed(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(report_run="20260906T203007Z", run="20260906T230100Z")], audit_runs=("20260906T203007Z", "20260906T214512Z"))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("DG178_PREVIEW_RUN", "20260906T214512Z")
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/research/available")
    assert r.status_code == 404 and "20260906T214512Z" in r.json()["detail"] and "no available-player catalog" in r.json()["detail"]
    # explicitly asking for the other report's run serves its catalog
    ok = c.get("/api/research/available", params={"run": "20260906T203007Z"}).json()
    assert ok["source"]["report_run"] == "20260906T203007Z" and ok["source"]["pinned"] is False


def test_the_newest_catalog_for_the_served_report_wins_and_older_ones_stay_addressable(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(run="20260906T230000Z"), _catalog(run="20260906T231500Z")])
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("DG178_PREVIEW_RUN", "20260906T214512Z")
    from app.main import app

    c = TestClient(app)
    assert c.get("/api/research/available").json()["source"]["catalog_run"] == "20260906T231500Z"
    assert c.get("/api/research/available", params={"catalog": "20260906T230000Z"}).json()["source"]["catalog_run"] == "20260906T230000Z"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("DG178_PREVIEW_RUN", "20260906T214512Z")
    from app.main import app

    return TestClient(app)


def test_a_catalog_that_does_not_bind_the_served_report_bytes_is_refused_not_served(tmp_path, monkeypatch) -> None:
    """Root: the same run NAME is not a binding. The route re-hashes the report it actually serves and
    the catalog bytes against the companion record; a mismatch is an explicit fail-closed error."""
    _write(tmp_path, [_catalog()], bind=False)          # sources.report_sha256 stays '19e0000…', not the served bytes
    r = _client(tmp_path, monkeypatch).get("/api/research/available")
    assert r.status_code == 500
    assert "20260906T230000Z" in r.json()["detail"] and "report_sha256" in r.json()["detail"] and "refus" in r.json()["detail"]


def test_catalog_bytes_that_differ_from_the_companion_record_are_refused_and_never_fall_back(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(run="20260906T230000Z"), _catalog(run="20260906T231500Z")])
    newest = tmp_path / "runs" / "20260906T231500Z" / "dg178_available_catalog" / "catalog.json"
    doc = json.loads(newest.read_text())
    doc["rows_detail"][0]["now_points"] = 999.0                          # tampered after the companion record was written
    newest.write_text(json.dumps(doc))
    c = _client(tmp_path, monkeypatch)
    r = c.get("/api/research/available")
    assert r.status_code == 500 and "20260906T231500Z" in r.json()["detail"] and "catalog.json" in r.json()["detail"]
    # the older, intact catalog is NOT silently served in its place; it stays addressable by name
    assert c.get("/api/research/available", params={"catalog": "20260906T230000Z"}).json()["source"]["catalog_run"] == "20260906T230000Z"


def test_a_malformed_or_companionless_newest_catalog_is_an_explicit_error(tmp_path, monkeypatch) -> None:
    _write(tmp_path, [_catalog(run="20260906T230000Z")])
    broken = tmp_path / "runs" / "20260906T232000Z" / "dg178_available_catalog"
    broken.mkdir(parents=True)
    (broken / "catalog.json").write_text("{not json")
    c = _client(tmp_path, monkeypatch)
    r = c.get("/api/research/available")
    assert r.status_code == 500 and "20260906T232000Z" in r.json()["detail"]
    (broken / "catalog.json").write_text(json.dumps(_catalog(run="20260906T232000Z")))    # valid JSON, no companion record
    r = c.get("/api/research/available")
    assert r.status_code == 500 and "20260906T232000Z" in r.json()["detail"] and "companion" in r.json()["detail"]
