"""Root-accepted DG-165 cold-start sidecar (20260907T011503Z): NEW-ONLY consumption into the
available-player catalog. Every guard refuses; nothing is fabricated; the accepted 825 rows and the
four recoveries are untouched; an explicitly unsupported year stays missing and never enters a
partial future sum; the estimate carries its per-year class so the UI can say 'Starting estimate'."""
from __future__ import annotations

import csv
import json

import pytest
from available_fixture import _fixture, _sha

from src.dynasty_genius.ranking.available_catalog import AvailableCatalog
from src.dynasty_genius.ranking.cold_start_consumer import ColdStartSidecar

YEARS = (2026, 2027, 2028, 2029, 2030)
CLASSES = ("cold_start_candidate",) + ("baseline_research_candidate",) * 4
COLS = ["sleeper_id", "gsis_id", "name", "draft_position", "route", "draft_status", "origin_year", "source_binding"] + [
    c for j in range(1, 6) for c in (f"season_year{j}", f"estimate_class_year{j}", f"p_appear_year{j}", f"e_points_year{j}", f"e_games_year{j}",
                                     f"e_points_year{j}_given_appear", f"e_games_year{j}_given_appear")]


def _row(sid="201", gsis="00-5", name="Practice Guy", pos="WR", points=(-0.21, 11.0, 9.5, 8.0, 6.7), p=0.2, classes=CLASSES, origin=2026,
         seasons=YEARS, blank_years=()):
    r = {"sleeper_id": sid, "gsis_id": gsis, "name": name, "draft_position": pos, "route": "never_appeared_drafted",
         "draft_status": "drafted_verified", "origin_year": str(origin),
         "source_binding": json.dumps({"artifact_sha256": "o" * 64, "origin_year": origin})}
    for j in range(1, 6):
        r[f"season_year{j}"] = str(seasons[j - 1])
        r[f"estimate_class_year{j}"] = classes[j - 1]
        if j in blank_years:
            for c in (f"p_appear_year{j}", f"e_points_year{j}", f"e_games_year{j}", f"e_points_year{j}_given_appear", f"e_games_year{j}_given_appear"):
                r[c] = ""
            continue
        e = points[j - 1]
        r.update({f"p_appear_year{j}": p, f"e_points_year{j}": e, f"e_games_year{j}": 2 * p, f"e_points_year{j}_given_appear": e / p,
                  f"e_games_year{j}_given_appear": 2})
    return r


def _sidecar(tmp_path, rows, *, artifact="o" * 64, target="t" * 64, schema="dg165_cold_start_candidate_v1", selected=None):
    d = tmp_path / "20260907T011503Z" / "dg165_cold_start_candidate"
    d.mkdir(parents=True)
    est = d / "cold_start_estimates.csv"
    with est.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    evaluation = {"final_origin_2026": {"selected_per_horizon": selected or {str(j): CLASSES[j - 1] for j in range(1, 6)}},
                  "horizons": {str(j): {"arms": {"b1": {"n": 200 + j, "rmse_points": 28.19, "brier": 0.2474},
                                                 "candidate": {"n": 200 + j, "rmse_points": 24.50, "brier": 0.2293}}} for j in range(1, 6)},
                  "caveats": {"population": "a draft-population prior; not conditioned on remaining on a current roster",
                              "appearance": "P(appear) is appearance, not usefulness"},
                  "selection_rule": "candidate only if both paired 90% intervals are below zero; otherwise B1"}
    (d / "evaluation.json").write_text(json.dumps(evaluation))
    manifest = {"schema_version": schema, "ticket": "DG-165", "run_dir": "runs/20260907T011503Z/dg165_cold_start_candidate",
                "games_bound_declared": [1, 17],
                "inputs": {"outcome_artifact": {"sha256": artifact, "target_identity": target},
                           "coverage_run": {"run_dir": "runs/20260907T010020Z/dg165_cold_start_coverage", "ledger_sha256": "l" * 64},
                           "partition": {"candidates": len(rows), "recovered_existing_forecast": 4, "unresolved": 73, "ledger_rows": 84}},
                "selection_rule": evaluation["selection_rule"], "caveats": evaluation["caveats"],
                "outputs_sha256": {"cold_start_estimates.csv": _sha(est), "evaluation.json": _sha(d / "evaluation.json")}}
    (d / "manifest.json").write_text(json.dumps(manifest))
    return d, _sha(d / "manifest.json"), _sha(est)


def _build(tmp_path, rows=None, **kw):
    rp, run, snap, csvs = _fixture(tmp_path)
    d, msha, esha = _sidecar(tmp_path, rows if rows is not None else [_row()], **kw)
    side = ColdStartSidecar.load(d, manifest_sha256=msha, estimates_sha256=esha)
    return AvailableCatalog.build(rp, run, csvs, snapshot_path=snap, cold_start=side), (rp, run, snap, csvs, d, msha, esha)


def test_a_starting_estimate_joins_a_default_pool_member_without_a_forecast_by_verified_identity_only(tmp_path) -> None:
    cat, _ = _build(tmp_path)
    pg = next(r for r in cat.rows if r.sleeper_id == "201")
    assert pg.forecast is not None and pg.starting_estimate is True
    assert pg.forecast.producer == "DG-165 cold-start research candidate (starting estimate):dg165_cold_start_candidate_v1"
    assert pg.forecast.join_basis == "cold_start_census_nfl_gsis" and pg.forecast.join_id == "00-5"
    assert pg.now_points == -0.21                                   # a negative starting estimate stays negative
    assert pg.future_points == pytest.approx(11.0 + 9.5 + 8.0 + 6.7)
    assert pg.estimate_classes == {2026: "cold_start_candidate", 2027: "baseline_research_candidate", 2028: "baseline_research_candidate",
                                   2029: "baseline_research_candidate", 2030: "baseline_research_candidate"}
    assert pg.impact == {"h2": None, "h5": None} and pg.missing_reason is None and pg.recovered is False
    assert pg.forecast_path == {"status": "complete", "years_present": list(YEARS)}
    rep = cat.report()
    d = rep["populations"]["default"]
    assert (d["total"], d["with_forecast"], d["without_forecast"], d["starting_estimates"]) == (4, 4, 0, 1)
    se = rep["starting_estimates"]
    assert se["count"] == 1 and se["rows"] == [{"sleeper_id": "201", "gsis": "00-5", "classes": pg.estimate_classes}]
    assert se["source"]["schema_version"] == "dg165_cold_start_candidate_v1" and len(se["source"]["manifest_sha256"]) == 64
    assert se["source"]["partition"] == {"candidates": 1, "recovered_existing_forecast": 4, "unresolved": 73, "ledger_rows": 84}
    assert se["evidence"]["horizons"]["1"]["candidate"]["rmse_points"] == 24.50 and se["evidence"]["selected_per_horizon"]["2"] == "baseline_research_candidate"
    assert "not conditioned on remaining on a current roster" in se["evidence"]["caveats"]["population"]
    # the other rows are exactly as without the sidecar
    assert next(r for r in cat.rows if r.sleeper_id == "200").now_points == 120.5 and next(r for r in cat.rows if r.sleeper_id == "200").starting_estimate is False


def test_exact_source_hashes_and_immutable_paths_are_required(tmp_path) -> None:
    rp, run, snap, csvs = _fixture(tmp_path)
    d, msha, esha = _sidecar(tmp_path, [_row()])
    with pytest.raises(ValueError, match="manifest"):
        ColdStartSidecar.load(d, manifest_sha256="0" * 64, estimates_sha256=esha)
    with pytest.raises(ValueError, match="estimates"):
        ColdStartSidecar.load(d, manifest_sha256=msha, estimates_sha256="0" * 64)
    # bytes edited after the manifest recorded them
    est = d / "cold_start_estimates.csv"
    est.write_text(est.read_text().replace("-0.21", "-0.22"))
    with pytest.raises(ValueError, match="estimates"):
        ColdStartSidecar.load(d, manifest_sha256=msha, estimates_sha256=_sha(est))
    latest = tmp_path / "latest"
    latest.symlink_to(d)
    with pytest.raises(ValueError, match="latest"):
        ColdStartSidecar.load(latest, manifest_sha256=msha, estimates_sha256=esha)


def test_the_sidecar_must_bind_the_same_outcome_target_years_and_schema_as_the_accepted_report(tmp_path) -> None:
    with pytest.raises(ValueError, match="outcome"):
        _build(tmp_path / "a", artifact="x" * 64)
    with pytest.raises(ValueError, match="target"):
        _build(tmp_path / "b", target="x" * 64)
    with pytest.raises(ValueError, match="schema"):
        _build(tmp_path / "c", schema="dg165_cold_start_candidate_v0")
    with pytest.raises(ValueError, match="origin"):
        _build(tmp_path / "d", rows=[_row(origin=2025)])
    with pytest.raises(ValueError, match="season"):
        _build(tmp_path / "e", rows=[_row(seasons=(2026, 2028, 2028, 2029, 2030))])


def test_new_only_and_verified_identity_every_overlap_or_mismatch_is_refused(tmp_path) -> None:
    with pytest.raises(ValueError, match="already"):                     # 200 has an accepted forecast
        _build(tmp_path / "a", rows=[_row(sid="200", gsis="00-3", name="Free Wideout")])
    with pytest.raises(ValueError, match="owned"):                       # 100 is owned
        _build(tmp_path / "b", rows=[_row(sid="100", gsis="00-1", name="Owned One", pos="QB")])
    with pytest.raises(ValueError, match="census"):                      # not a census member
        _build(tmp_path / "c", rows=[_row(sid="999", gsis="00-999", name="Nobody")])
    with pytest.raises(ValueError, match="identity"):                    # gsis differs from the census's verified gsis
        _build(tmp_path / "d", rows=[_row(gsis="00-55")])
    with pytest.raises(ValueError, match="position"):
        _build(tmp_path / "e", rows=[_row(pos="TE")])
    with pytest.raises(ValueError, match="duplicate"):
        _build(tmp_path / "f", rows=[_row(), _row()])
    with pytest.raises(ValueError, match="default pool"):                # cut player is not in the default pool
        _build(tmp_path / "g", rows=[_row(sid="203", gsis="00-7", name="Cut Passer", pos="QB")])
    with pytest.raises(ValueError, match="already"):                     # the recovered rows are forecasts too
        rp, run, snap, csvs = _fixture(tmp_path / "h")
        vet = csvs[0]
        rows = list(csv.DictReader(vet.open(newline="")))
        extra = dict(rows[0])
        extra["player_id"], extra["position"] = "00-5", "WR"
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
        d, msha, esha = _sidecar(tmp_path / "h", [_row()])
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap, cold_start=ColdStartSidecar.load(d, manifest_sha256=msha, estimates_sha256=esha))


def test_values_are_validated_and_an_unsupported_year_stays_missing_never_a_partial_sum(tmp_path) -> None:
    with pytest.raises(ValueError, match="probability"):
        _build(tmp_path / "a", rows=[_row(p=1.2)])
    with pytest.raises(ValueError, match="estimate_class"):
        _build(tmp_path / "b", rows=[_row(classes=("cold_start_candidate", "made_up", "baseline_research_candidate", "baseline_research_candidate", "baseline_research_candidate"))])
    with pytest.raises(ValueError, match="incomplete"):                  # a supported class with no value
        _build(tmp_path / "c", rows=[_row(blank_years=(3,))])
    with pytest.raises(ValueError, match="unsupported"):                 # an unsupported class WITH a value is incoherent
        _build(tmp_path / "d", rows=[_row(classes=("cold_start_candidate", "baseline_research_candidate", "unsupported", "baseline_research_candidate", "baseline_research_candidate"))])
    with pytest.raises(ValueError, match="selected"):                    # the row's class must be the evaluation's selection for that horizon
        _build(tmp_path / "e", rows=[_row(classes=("baseline_research_candidate",) * 5)])
    cat, _ = _build(tmp_path / "f", rows=[_row(classes=("cold_start_candidate", "baseline_research_candidate", "unsupported", "baseline_research_candidate", "baseline_research_candidate"), blank_years=(3,))],
                    selected={"1": "cold_start_candidate", "2": "baseline_research_candidate", "3": "unsupported", "4": "baseline_research_candidate", "5": "baseline_research_candidate"})
    pg = next(r for r in cat.rows if r.sleeper_id == "201")
    assert [s.season for s in pg.forecast.seasons] == [2026, 2027, 2029, 2030]
    assert pg.now_points == -0.21 and pg.future_points is None
    assert pg.future_reason == "2028 unsupported by the producer: future total undefined, not zero"
    assert pg.forecast_path == {"status": "incomplete", "years_present": [2026, 2027, 2029, 2030]}
    assert pg.estimate_classes[2028] == "unsupported"


def test_a_supported_year_needs_all_five_finite_terms_games_within_the_declared_bound_and_exact_year_labels(tmp_path) -> None:
    """Root's boundary review: a supported cold-start year must carry P(appear), expected points,
    expected games and both conditional terms (the accepted producers' contract); expected games
    cannot be negative and conditional games must sit inside the manifest's declared bound;
    origin and season labels must be exact integral years, never truncated."""
    def blank_games(r):
        r["e_games_year2"] = ""
        return r
    with pytest.raises(ValueError, match="incomplete"):
        _build(tmp_path / "a", rows=[blank_games(_row())])

    def blank_conditional(r):
        r["e_points_year3_given_appear"] = ""
        return r
    with pytest.raises(ValueError, match="incomplete"):
        _build(tmp_path / "b", rows=[blank_conditional(_row())])

    def negative_games(r):                      # coherent (p × conditional) but negative
        r["e_games_year1_given_appear"] = -2.5
        r["e_games_year1"] = 0.2 * -2.5
        return r
    with pytest.raises(ValueError, match="games"):
        _build(tmp_path / "c", rows=[negative_games(_row())])

    def out_of_bound(r):                        # coherent but 20 conditional games > declared 17
        r["e_games_year1_given_appear"] = 20
        r["e_games_year1"] = 0.2 * 20
        return r
    with pytest.raises(ValueError, match="bound"):
        _build(tmp_path / "d", rows=[out_of_bound(_row())])
    with pytest.raises(ValueError, match="origin"):
        _build(tmp_path / "e", rows=[_row(origin="2026.5")])
    with pytest.raises(ValueError, match="season"):
        _build(tmp_path / "f", rows=[_row(seasons=(2026, "2027.5", 2028, 2029, 2030))])
    with pytest.raises(ValueError, match="season"):
        _build(tmp_path / "g", rows=[_row(seasons=(2026, "2027.0", 2028, 2029, 2030))])
    # a manifest that declares no games bound cannot be checked, refused
    rp, run, snap, csvs = _fixture(tmp_path / "h")
    d, msha, esha = _sidecar(tmp_path / "h", [_row()])
    m = json.loads((d / "manifest.json").read_text())
    del m["games_bound_declared"]
    (d / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="games_bound_declared"):
        AvailableCatalog.build(rp, run, csvs, snapshot_path=snap, cold_start=ColdStartSidecar.load(d, manifest_sha256=_sha(d / "manifest.json"), estimates_sha256=esha))
    # the legitimate signed year-1 points (Rourke-like −0.21) still pass
    cat, _ = _build(tmp_path / "i")
    assert next(r for r in cat.rows if r.sleeper_id == "201").now_points == -0.21
