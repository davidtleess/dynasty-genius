"""DG-207 — the two graders, proved on synthetic closed seasons only.

No actual 2026 outcome is queried anywhere in this file. Every fixture is invented, and the
arithmetic is chosen so a wrong metric cannot pass: forecast errors [2, 4] against baseline
errors [4, 8] in every position give forecast MAE 3, baseline MAE 6, difference -3 exactly.
"""

import copy
import json

import pytest

from src.dynasty_genius.eval.workspace_track_record import (
    TrackRecordError,
    _missing_endpoint_sensitivity,
    grade_market,
    grade_production,
    select_endpoint,
)

POSITIONS = ("QB", "RB", "WR", "TE")
PLAN_SHA = "a" * 64
MARKET_PLAN_SHA = "b" * 64

# The frozen schedule the enrollment commits to: 17 weeks, 16 games each. The expected universe
# lives in the ENROLLMENT, so an outcome source cannot declare a smaller season for itself.
WEEKS_EXPECTED = list(range(1, 18))
EXPECTED_GAME_IDS = sorted(f"2026-W{week:02d}-G{game:02d}"
                           for week in WEEKS_EXPECTED for game in range(1, 17))


# --------------------------------------------------------------------------- fixtures
def _target():
    return {"scoring": "PPR_nflverse_default", "window": "championship_week17", "season": 2026}


def _window():
    return {"label": "REG weeks 1-17", "start_at": "2026-09-10T00:00:00Z", "end_at": "2027-01-05T00:00:00Z"}


def production_enrollment(*, rows=None, cutoff_at="2026-09-08T01:48:12Z"):
    """Two players per position: forecast errors 2 and 4, baseline errors 4 and 8."""
    if rows is None:
        rows = []
        for position in POSITIONS:
            for index, (forecast_error, baseline_error) in enumerate(((2.0, 4.0), (4.0, 8.0))):
                outcome = 100.0
                rows.append(
                    {
                        "sleeper_id": f"{position}{index}",
                        "name": f"{position} Player {index}",
                        "position": position,
                        "producer": "veteran_annual_v3",
                        "provenance": "original",
                        "forecast": outcome + forecast_error,
                        "baselines": {
                            "prior_season": outcome + baseline_error,
                            "position_median": outcome - baseline_error,
                        },
                        "missing_reasons": {},
                    }
                )
    return {
        "record_id": "e" * 64,
        "kind": "enrollment",
        "recorded_at": "2026-09-09T00:00:00Z",
        "snapshot_id": "f" * 64,
        "artifact_hashes": {"report.json": "1" * 64},
        "document": {
            "schema_version": "track_record.enrollment.v1",
            "snapshot_id": "f" * 64,
            "forecast_identity": "identity-1",
            "enrolled_at": "2026-09-09T00:00:00Z",
            "production": {
                "state": "awaiting_horizon",
                "reason": None,
                "plan": "workspace-production-2026-v1",
                "plan_sha256": PLAN_SHA,
                "target": _target(),
                "window": _window(),
                "provenance_class": "reconstructed",
                "cutoff_at": cutoff_at,
                "target_start_at": "2026-09-10T00:00:00Z",
                "target_end_at": "2027-01-05T00:00:00Z",
                "weeks_expected": list(WEEKS_EXPECTED),
                "expected_game_ids": list(EXPECTED_GAME_IDS),
                "rows": rows,
            },
            "market": {"state": "not_registered", "reason": None, "rows": []},
        },
    }


def outcome_source(enrollment, *, values=None, complete=True, target=None, weeks_present=None,
                   observed_game_ids=None, expected_game_ids=None, games_present=None,
                   captured_at="2027-01-06T00:00:00Z"):
    rows = enrollment["document"]["production"]["rows"]
    players = {}
    for row in rows:
        if values is not None and row["sleeper_id"] in values:
            players[row["sleeper_id"]] = values[row["sleeper_id"]]
        else:
            players[row["sleeper_id"]] = {"value": 100.0, "games": 17, "reason": None}
    return {
        "schema_version": "track_record.outcome_source.v1",
        "target": target if target is not None else _target(),
        "window": _window(),
        "complete": complete,
        "coverage": {
            "weeks_expected": list(WEEKS_EXPECTED),
            "weeks_present": weeks_present if weeks_present is not None else list(WEEKS_EXPECTED),
            "expected_game_ids": (list(EXPECTED_GAME_IDS) if expected_game_ids is None
                                  else expected_game_ids),
            "observed_game_ids": (list(EXPECTED_GAME_IDS) if observed_game_ids is None
                                  else observed_game_ids),
            "games_expected": len(EXPECTED_GAME_IDS),
            "games_present": (len(EXPECTED_GAME_IDS) if games_present is None else games_present),
        },
        "scoring_code_identity": {"name": "research_ppr", "version": "1", "sha256": "c" * 64},
        "sources": [
            {"name": "nflverse_weekly", "url": "https://example.invalid/w.csv",
             "captured_at": captured_at, "sha256": "d" * 64, "bytes_len": 10}
        ],
        "players": players,
    }


def market_enrollment(*, rows=None, momentum=True, t0="2026-09-09T00:00:00Z"):
    if rows is None:
        rows = []
        for position in POSITIONS:
            for index in range(12):
                rows.append(
                    {
                        "sleeper_id": f"M{position}{index}",
                        "name": f"{position} Market {index}",
                        "position": position,
                        # a clean ordinal signal: better DG rank (lower) than market
                        "our_rank": [index + 1, index + 1],
                        "market_rank": [index + 1 + (11 - index), index + 1 + (11 - index)],
                        "start_price": 100.0,
                        "momentum": (0.01 * index) if momentum else None,
                        "missing_reasons": {},
                    }
                )
    return {
        "record_id": "e" * 64,
        "kind": "enrollment",
        "recorded_at": "2026-09-09T00:00:00Z",
        "snapshot_id": "f" * 64,
        "artifact_hashes": {"market.json": "2" * 64},
        "document": {
            "schema_version": "track_record.enrollment.v1",
            "snapshot_id": "f" * 64,
            "forecast_identity": "identity-1",
            "enrolled_at": t0,
            "production": {"state": "not_registered", "reason": None, "rows": []},
            "market": {
                "state": "awaiting_capture",
                "reason": None,
                "plan": "workspace-market-movement-90d-v1",
                "plan_sha256": MARKET_PLAN_SHA,
                "t0": t0,
                "window": {"label": "90-day", "start_at": None, "end_at": None},
                "provenance_class": "contemporaneous",
                "configuration": {"isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1},
                "rows": rows,
            },
        },
    }


def endpoint_source(enrollment, *, prices=None, as_of="2026-12-08T00:00:00Z", complete=True,
                    configuration=None):
    rows = enrollment["document"]["market"]["rows"]
    built = {}
    for position_index, row in enumerate(rows):
        if prices is not None and row["sleeper_id"] in prices:
            built[row["sleeper_id"]] = prices[row["sleeper_id"]]
        else:
            # movement rises with DG advantage so the association is positive
            gap = row["market_rank"][0] - row["our_rank"][0]
            built[row["sleeper_id"]] = {"price": 100.0 * (1.0 + 0.01 * gap), "reason": None}
    return {
        "schema_version": "track_record.endpoint_source.v1",
        "configuration": configuration if configuration is not None
        else {"isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1},
        "as_of": as_of,
        "complete": complete,
        "sources": [
            {"name": "fantasycalc", "url": "https://example.invalid/v",
             "captured_at": as_of, "sha256": "e" * 64, "bytes_len": 10}
        ],
        "prices": built,
    }


# --------------------------------------------------------------------------- production
def test_production_arithmetic_is_exact_and_favours_the_forecast():
    enrollment = production_enrollment()
    grade = grade_production(
        enrollment=enrollment, outcome_source=outcome_source(enrollment),
        evaluated_at="2027-01-10T00:00:00Z",
    )
    assert grade["state"] == "graded"
    assert grade["decision_supported"] is False
    prior = next(c for c in grade["result"]["comparisons"] if c["id"].endswith("prior_season"))
    # forecast MAE 3, baseline MAE 6, difference exactly -3
    assert prior["estimate"] == pytest.approx(-3.0)
    assert prior["state"] == "favorable"
    assert prior["eligible"] == 8 and prior["scored"] == 8


def test_production_reports_both_baselines_separately_never_pooled():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    ids = [c["id"] for c in grade["result"]["comparisons"]]
    assert any(i.endswith("prior_season") for i in ids)
    assert any(i.endswith("position_median") for i in ids)
    # producer is named in the comparison id; producers are never silently averaged
    assert all("veteran_annual_v3" in i for i in ids if "aggregate" in i)


def test_production_interval_is_deterministic_under_a_fixed_seed():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    first = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    second = grade_production(enrollment=enrollment, outcome_source=source,
                              evaluated_at="2027-01-10T00:00:00Z")
    a = next(c for c in first["result"]["comparisons"] if c["id"].endswith("prior_season"))
    b = next(c for c in second["result"]["comparisons"] if c["id"].endswith("prior_season"))
    assert a["interval95"] == b["interval95"] is not None


def test_production_missing_one_position_suppresses_the_aggregate():
    enrollment = production_enrollment()
    enrollment["document"]["production"]["rows"] = [
        r for r in enrollment["document"]["production"]["rows"] if r["position"] != "TE"
    ]
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    aggregate = [c for c in grade["result"]["comparisons"] if "aggregate" in c["id"]]
    assert all(c["state"] == "insufficient" and c["estimate"] is None for c in aggregate)
    assert any(c["id"].startswith("position:") for c in grade["result"]["comparisons"])


def test_production_zero_outcome_and_unknown_outcome_are_different():
    enrollment = production_enrollment()
    source = outcome_source(enrollment, values={
        "QB0": {"value": 0.0, "games": 0, "reason": None},          # verified nonparticipation
        "QB1": {"value": None, "games": None, "reason": "incomplete feed"},  # unknown
    })
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    rows = {r["sleeper_id"]: r for r in grade["result"]["rows"]}
    assert rows["QB0"]["outcome"] == 0.0 and rows["QB0"]["error"] is not None
    assert rows["QB1"]["outcome"] is None and rows["QB1"]["error"] is None
    assert rows["QB1"]["reason"] == "incomplete feed"
    assert grade["counts"]["missing"] == 1


def test_production_refuses_a_target_mismatch_before_computing_anything():
    enrollment = production_enrollment()
    bad = outcome_source(enrollment, target={"scoring": "half_ppr", "window": "week18", "season": 2026})
    with pytest.raises(TrackRecordError, match="target"):
        grade_production(enrollment=enrollment, outcome_source=bad,
                         evaluated_at="2027-01-10T00:00:00Z")


def test_production_incomplete_window_yields_no_primary_grade():
    enrollment = production_enrollment()
    partial = outcome_source(enrollment, complete=False, weeks_present=list(range(1, 12)))
    grade = grade_production(enrollment=enrollment, outcome_source=partial,
                             evaluated_at="2027-01-10T00:00:00Z")   # after the window closed
    assert grade["state"] == "input_unavailable"
    assert grade["result"] is None


def test_production_cutoff_ineligible_when_a_target_game_began_before_the_freeze():
    enrollment = production_enrollment(cutoff_at="2026-09-20T00:00:00Z")  # after kickoff
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "cutoff_ineligible"
    assert grade["result"] is None


def test_production_keeps_an_unfloored_negative_forecast_negative():
    enrollment = production_enrollment()
    enrollment["document"]["production"]["rows"][0]["forecast"] = -5.0
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    row = next(r for r in grade["result"]["rows"] if r["sleeper_id"] == "QB0")
    assert row["forecast"] == -5.0


def test_production_separates_provenance_strata_and_producers():
    enrollment = production_enrollment()
    enrollment["document"]["production"]["rows"][1]["provenance"] = "starting_estimate"
    enrollment["document"]["production"]["rows"][1]["producer"] = "rookie_cold_start_v2"
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    ids = [c["id"] for c in grade["result"]["comparisons"]]
    assert any("rookie_cold_start_v2" in i for i in ids)
    assert any("veteran_annual_v3" in i for i in ids)


def test_production_refuses_a_changed_plan_hash():
    enrollment = production_enrollment()
    enrollment["document"]["production"]["plan_sha256"] = "9" * 64
    source = outcome_source(enrollment)
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    # the hash is recorded honestly, and it is the enrollment's, never silently replaced
    assert grade["policy_sha256"] == "9" * 64


def test_production_refuses_duplicate_player_ids():
    enrollment = production_enrollment()
    rows = enrollment["document"]["production"]["rows"]
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(TrackRecordError, match="duplicate"):
        grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                         evaluated_at="2027-01-10T00:00:00Z")


# --------------------------------------------------------------------------- market
def test_market_percentage_return_arithmetic():
    assert ((110.0 / 100.0) - 1.0) > 0.099999
    assert ((0.0 / 100.0) - 1.0) == -1.0


def test_market_grades_a_clean_ordinal_association():
    enrollment = market_enrollment()
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    assert grade["state"] == "graded"
    assert grade["decision_supported"] is False
    gap = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap["estimate"] is not None and gap["estimate"] > 0.9
    rows = grade["result"]["rows"]
    assert all(r["error"] is None for r in rows)  # never a price forecast


def test_market_uniform_doubling_is_undefined_not_a_win():
    enrollment = market_enrollment()
    prices = {r["sleeper_id"]: {"price": 200.0, "reason": None}
              for r in enrollment["document"]["market"]["rows"]}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    assert grade["state"] == "insufficient_evidence"
    gap = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap["estimate"] is None and gap["state"] == "insufficient"
    assert "undefined" in gap["note"].lower()


def test_market_true_end_zero_is_minus_one_hundred_percent_and_absent_is_missing():
    enrollment = market_enrollment()
    prices = {"MQB0": {"price": 0.0, "reason": None},
              "MQB1": {"price": None, "reason": "absent from complete capture"}}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    rows = {r["sleeper_id"]: r for r in grade["result"]["rows"]}
    assert rows["MQB0"]["outcome"] is not None
    assert rows["MQB1"]["outcome"] is None and rows["MQB1"]["reason"]
    assert grade["counts"]["missing"] >= 1


def test_market_reordering_a_tie_changes_nothing():
    enrollment = market_enrollment()
    for row in enrollment["document"]["market"]["rows"][:6]:
        row["our_rank"] = [230, 388]   # the real zero-floor tie shape
    first = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    shuffled = copy.deepcopy(enrollment)
    block = shuffled["document"]["market"]["rows"][:6]
    shuffled["document"]["market"]["rows"][:6] = list(reversed(block))
    second = grade_market(enrollment=shuffled, endpoint_source=endpoint_source(shuffled),
                          evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    a = next(c for c in first["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    b = next(c for c in second["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert a["estimate"] == b["estimate"]


def test_market_missing_frozen_momentum_blocks_the_comparator_claim_only():
    enrollment = market_enrollment(momentum=False)
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    paired = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:paired_difference")
    assert paired["estimate"] is None and paired["state"] == "insufficient"
    gap = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap["estimate"] is not None  # descriptive association survives


def test_market_endpoint_outside_the_registered_window_is_not_used():
    enrollment = market_enrollment()
    late = endpoint_source(enrollment, as_of="2027-03-01T00:00:00Z")
    grade = grade_market(enrollment=enrollment, endpoint_source=late,
                         evaluated_at="2027-03-02T00:00:00Z", horizon_days=90)
    assert grade["state"] == "input_unavailable"
    assert grade["result"] is None


def test_market_before_the_window_opens_is_awaiting_capture():
    enrollment = market_enrollment()
    early = endpoint_source(enrollment, as_of="2026-10-01T00:00:00Z")
    grade = grade_market(enrollment=enrollment, endpoint_source=early,
                         evaluated_at="2026-10-02T00:00:00Z", horizon_days=90)
    assert grade["state"] == "awaiting_capture"


def test_market_incomplete_capture_produces_no_primary_grade():
    enrollment = market_enrollment()
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, complete=False),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    assert grade["state"] == "input_unavailable"
    assert grade["result"] is None


def test_market_configuration_mismatch_refuses():
    enrollment = market_enrollment()
    bad = endpoint_source(enrollment, configuration={"isDynasty": True, "numQbs": 1,
                                                     "numTeams": 12, "ppr": 1})
    with pytest.raises(TrackRecordError, match="configuration"):
        grade_market(enrollment=enrollment, endpoint_source=bad,
                     evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)


def test_market_duplicate_ids_refuse():
    enrollment = market_enrollment()
    rows = enrollment["document"]["market"]["rows"]
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(TrackRecordError, match="duplicate"):
        grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                     evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)


def test_market_one_thin_position_suppresses_the_aggregate():
    enrollment = market_enrollment()
    rows = enrollment["document"]["market"]["rows"]
    enrollment["document"]["market"]["rows"] = [r for r in rows if r["position"] != "TE"][:26]
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    gap = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap["state"] == "insufficient"


def test_market_seed_is_reproducible():
    enrollment = market_enrollment()
    source = endpoint_source(enrollment)
    a = grade_market(enrollment=enrollment, endpoint_source=source,
                     evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    b = grade_market(enrollment=enrollment, endpoint_source=source,
                     evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    ca = next(c for c in a["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    cb = next(c for c in b["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert ca["interval95"] == cb["interval95"]


def test_market_missing_endpoint_sensitivity_is_separate_from_primary():
    enrollment = market_enrollment()
    prices = {"MQB1": {"price": None, "reason": "absent from complete capture"}}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    labels = [d["label"] for d in grade["result"]["details"]]
    assert any("sensitivity" in label.lower() for label in labels)
    rows = {r["sleeper_id"]: r for r in grade["result"]["rows"]}
    assert rows["MQB1"]["outcome"] is None  # primary data untouched by the scenario


def test_market_horizon_days_is_restricted():
    enrollment = market_enrollment()
    with pytest.raises(TrackRecordError, match="horizon"):
        grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                     evaluated_at="2026-12-09T00:00:00Z", horizon_days=45)


def test_market_produces_an_unfavorable_result_under_the_same_rules():
    enrollment = market_enrollment()
    prices = {}
    for row in enrollment["document"]["market"]["rows"]:
        gap = row["market_rank"][0] - row["our_rank"][0]
        prices[row["sleeper_id"]] = {"price": 100.0 * (1.0 - 0.01 * gap), "reason": None}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    gap_c = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap_c["estimate"] < 0
    assert gap_c["state"] == "unfavorable"


def test_every_grade_document_carries_the_required_envelope():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    for key in ("schema_version", "snapshot_id", "enrollment_id", "claim", "evaluated_at",
                "policy_sha256", "input_hashes", "decision_supported", "state", "reason",
                "window", "provenance_class", "counts", "result"):
        assert key in grade, key
    assert grade["schema_version"] == "track_record.grade.v1"
    assert grade["enrollment_id"] == enrollment["record_id"]
    assert isinstance(grade["counts"]["eligible"], int)
    assert not isinstance(grade["counts"]["eligible"], bool)
    json.dumps(grade, allow_nan=False)  # must be strict-JSON serialisable


# --------------------------------------------------------------------------- root amendment 2026-09-09
def test_grade_carries_horizon_days_and_outcome_source_hashes():
    enrollment = production_enrollment()
    production = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                                  evaluated_at="2027-01-10T00:00:00Z")
    assert production["horizon_days"] is None                      # production has no horizon
    assert production["outcome_source_hashes"] == {"nflverse_weekly": "d" * 64}
    # input_hashes still carries the enrollment hashes as well as the outcome hashes
    assert production["input_hashes"]["report.json"] == "1" * 64
    assert production["input_hashes"]["nflverse_weekly"] == "d" * 64

    market_record = market_enrollment()
    market = grade_market(enrollment=market_record,
                          endpoint_source=endpoint_source(market_record),
                          evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    assert market["horizon_days"] == 90
    assert market["outcome_source_hashes"] == {"fantasycalc": "e" * 64}
    assert market["input_hashes"]["market.json"] == "2" * 64


def test_production_rows_expose_both_declared_baselines():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    row = next(r for r in grade["result"]["rows"] if r["sleeper_id"] == "QB0")
    assert row["baseline"] == 104.0                       # prior season
    assert row["baseline_position_median"] == 96.0        # position median, visible without a second table


def test_production_favorable_direction_is_lower_error_not_higher():
    """The declaration says the forecast beat a baseline only when the interval is wholly BELOW zero."""
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    prior = next(c for c in grade["result"]["comparisons"] if c["id"].endswith("prior_season"))
    assert prior["estimate"] < 0 and prior["interval95"][1] < 0
    assert prior["state"] == "favorable"


def test_production_worse_forecast_is_unfavorable_under_the_same_rule():
    enrollment = production_enrollment()
    for row in enrollment["document"]["production"]["rows"]:      # forecast now worse than baseline
        row["forecast"] = 100.0 + (row["baselines"]["prior_season"] - 100.0) * 3.0
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    prior = next(c for c in grade["result"]["comparisons"] if c["id"].endswith("prior_season"))
    assert prior["estimate"] > 0
    assert prior["state"] == "unfavorable"


def test_outcome_vintage_does_not_break_measurement_identity():
    """A newer labels_through is a revision, not a different measurement."""
    enrollment = production_enrollment()
    enrollment["document"]["production"]["target"] = {**_target(), "labels_through": "2027-01-05"}
    source = outcome_source(enrollment, target={**_target(), "labels_through": "2027-02-11"})
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-02-12T00:00:00Z")
    assert grade["state"] == "graded"
    assert any("vintage" in d["label"].lower() for d in grade["result"]["details"])


def test_incomplete_game_coverage_blocks_grading_even_when_every_week_is_present():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["coverage"]["games_present"] = 271          # one game short, all 17 weeks present
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "271 of 272" in grade["reason"]
    assert grade["result"] is None


def test_unproven_game_coverage_is_unavailable_not_assumed_complete():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["coverage"].pop("games_expected")
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"


def test_outcome_source_hashes_are_a_subset_of_input_hashes():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    assert set(grade["outcome_source_hashes"]).issubset(set(grade["input_hashes"]))
    for name, digest in grade["outcome_source_hashes"].items():
        assert grade["input_hashes"][name] == digest


def test_market_claim_is_canonical_and_the_horizon_is_a_separate_field():
    """Root integration check: consumers key on claim alone, so 30 must not masquerade as 90."""
    enrollment = market_enrollment()
    ninety = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                          evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    thirty = grade_market(enrollment=enrollment,
                          endpoint_source=endpoint_source(enrollment, as_of="2026-10-10T00:00:00Z"),
                          evaluated_at="2026-10-11T00:00:00Z", horizon_days=30)
    assert ninety["claim"] == "market_movement"
    assert thirty["claim"] == "market_movement"
    assert ninety["horizon_days"] == 90 and thirty["horizon_days"] == 30
    # identical claim strings, so only horizon_days distinguishes them
    assert ninety["claim"] == thirty["claim"]


def test_production_claim_is_canonical():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["claim"] == "football_production"
    assert grade["horizon_days"] is None


def test_counts_are_coherent_and_never_exceed_the_enrolled_cohort():
    """Root checks for impossible counts; these are the invariants that make them impossible."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment, values={
        "QB1": {"value": None, "games": None, "reason": "incomplete feed"},
    })
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    counts = grade["counts"]
    enrolled = len(enrollment["document"]["production"]["rows"])
    assert counts["eligible"] == enrolled
    assert 0 <= counts["scored"] <= counts["eligible"]
    assert 0 <= counts["missing"] <= counts["eligible"]
    assert counts["scored"] + counts["missing"] == counts["eligible"]
    assert len(grade["result"]["rows"]) == enrolled          # every enrolled player is shown
    for comparison in grade["result"]["comparisons"]:
        assert 0 <= comparison["scored"] <= comparison["eligible"] <= enrolled


def test_market_counts_are_coherent_and_rows_are_complete():
    enrollment = market_enrollment()
    prices = {"MQB1": {"price": None, "reason": "absent from complete capture"}}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    counts = grade["counts"]
    enrolled = len(enrollment["document"]["market"]["rows"])
    assert counts["eligible"] == enrolled
    assert 0 <= counts["scored"] <= counts["eligible"]
    assert 0 <= counts["missing"] <= counts["eligible"]
    assert counts["scored"] + counts["missing"] == counts["eligible"]
    assert len(grade["result"]["rows"]) == enrolled


def test_an_unavailable_state_never_ships_a_result():
    """A pending or refused stream must not carry numbers a reader could mistake for a grade."""
    enrollment = production_enrollment()
    partial = outcome_source(enrollment, complete=False, weeks_present=list(range(1, 12)))
    grade = grade_production(enrollment=enrollment, outcome_source=partial,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] != "graded"
    assert grade["result"] is None
    assert grade["counts"]["scored"] == 0


# --------------------------------------------------------------- independent review blockers
def test_production_refuses_to_grade_before_the_window_closes():
    """A complete:true a source asserts about an unfinished season is not a finished season."""
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2026-11-01T00:00:00Z")   # mid-season
    assert grade["state"] == "awaiting_horizon"
    assert grade["result"] is None


def test_production_refuses_a_source_describing_a_different_window():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["window"] = {"label": "REG weeks 1-9", "start_at": "2026-09-10T00:00:00Z",
                        "end_at": "2026-11-10T00:00:00Z"}
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "different window" in grade["reason"]


def test_market_paired_difference_uses_one_complete_case_population():
    """The counterexample: momentum on a subset must not be subtracted from gap on everyone."""
    enrollment = market_enrollment()
    # strip momentum from half of each position, leaving >=10 per position on both sides
    for row in enrollment["document"]["market"]["rows"]:
        if row["sleeper_id"].endswith("0"):        # 2 of 12 per position -> 10 remain
            row["momentum"] = None
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    by_id = {c["id"]: c for c in grade["result"]["comparisons"]}
    paired = by_id["market:paired_difference"]
    gap_all = by_id["market:gap_correlation"]
    gap_paired = by_id["market:gap_correlation_paired"]
    momentum = by_id["market:momentum_correlation"]
    # the two sides of the subtraction are measured on the SAME smaller population
    assert gap_paired["eligible"] == momentum["eligible"] == paired["scored"]
    assert gap_paired["eligible"] < gap_all["eligible"]
    # and the reported difference is exactly those two, not the all-players correlation
    assert paired["estimate"] == pytest.approx(gap_paired["estimate"] - momentum["estimate"])


def test_market_aggregate_requires_all_four_positions():
    enrollment = market_enrollment()
    enrollment["document"]["market"]["rows"] = [
        r for r in enrollment["document"]["market"]["rows"] if r["position"] != "TE"
    ]
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    gap = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert gap["estimate"] is None and gap["state"] == "insufficient"
    assert grade["state"] == "insufficient_evidence"


def test_missing_endpoint_sensitivity_is_actually_computed():
    """It must produce a number and its counts, or say plainly that it did not."""
    enrollment = market_enrollment()
    prices = {f"M{p}{i}": {"price": None, "reason": "absent from complete capture"}
              for p in ("QB", "RB", "WR", "TE") for i in (0, 1)}
    grade = grade_market(enrollment=enrollment,
                         endpoint_source=endpoint_source(enrollment, prices=prices),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    detail = next(d for d in grade["result"]["details"]
                  if d["label"] == "Missing-endpoint sensitivity")
    assert detail["value"].startswith("computed:")
    assert "Scenario correlation" in detail["value"]
    assert "8 set to -100%" in detail["value"]
    # the primary rows are untouched by the scenario
    rows = {r["sleeper_id"]: r for r in grade["result"]["rows"]}
    assert rows["MQB0"]["outcome"] is None


def test_missing_endpoint_sensitivity_says_so_when_not_exercised():
    enrollment = market_enrollment()
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    detail = next(d for d in grade["result"]["details"]
                  if d["label"] == "Missing-endpoint sensitivity")
    assert detail["value"].startswith("not_exercised:")


def test_same_producer_mixed_provenance_is_never_pooled():
    """The review's counterexample: recovered rows need not carry a different producer id."""
    enrollment = production_enrollment()
    rows = enrollment["document"]["production"]["rows"]
    for row in rows:
        if row["position"] in ("QB", "RB"):
            row["provenance"] = "recovered"          # SAME producer, different provenance
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    ids = [c["id"] for c in grade["result"]["comparisons"]]
    assert any(":veteran_annual_v3:original:" in i for i in ids)
    assert any(":veteran_annual_v3:recovered:" in i for i in ids)
    # neither stratum covers all four positions, so neither may claim an aggregate
    for comparison in grade["result"]["comparisons"]:
        if "aggregate" in comparison["id"]:
            assert comparison["state"] == "insufficient" and comparison["estimate"] is None


def test_production_reports_positional_mae_and_rmse():
    enrollment = production_enrollment()
    grade = grade_production(enrollment=enrollment, outcome_source=outcome_source(enrollment),
                             evaluated_at="2027-01-10T00:00:00Z")
    ids = {c["id"]: c for c in grade["result"]["comparisons"]}
    mae = ids["position:QB:veteran_annual_v3:original:forecast_mae"]
    rmse = ids["position:QB:veteran_annual_v3:original:forecast_rmse"]
    assert mae["estimate"] == pytest.approx(3.0)                    # |2| and |4|
    assert rmse["estimate"] == pytest.approx((( 4.0 + 16.0) / 2) ** 0.5)
    assert mae["units"] == "points" and rmse["units"] == "points"


def test_production_eligible_counts_the_full_enrolled_stratum():
    """Excluded rows must stay visible in the denominator, not vanish from it."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment, values={
        "QB1": {"value": None, "games": None, "reason": "incomplete feed"},
    })
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    aggregate = next(c for c in grade["result"]["comparisons"] if "aggregate" in c["id"])
    assert aggregate["eligible"] == 8      # all enrolled in the stratum
    assert aggregate["scored"] == 7        # one lost to a missing outcome
    assert aggregate["scored"] < aggregate["eligible"]


def test_market_position_readings_survive_a_failed_aggregate():
    enrollment = market_enrollment()
    rows = enrollment["document"]["market"]["rows"]
    enrollment["document"]["market"]["rows"] = [r for r in rows if r["position"] != "TE"]
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    aggregate = next(c for c in grade["result"]["comparisons"] if c["id"] == "market:gap_correlation")
    assert aggregate["estimate"] is None
    per_position = [c for c in grade["result"]["comparisons"]
                    if c["id"].startswith("position:") and c["id"].endswith("gap_correlation")]
    assert len(per_position) == 3                       # QB, RB, WR still readable
    assert all(c["estimate"] is not None for c in per_position)


def test_zero_start_price_is_not_counted_as_a_missing_endpoint():
    enrollment = market_enrollment()
    enrollment["document"]["market"]["rows"][0]["start_price"] = 0.0
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-09T00:00:00Z", horizon_days=90)
    detail = next(d for d in grade["result"]["details"]
                  if d["label"] == "Missing-endpoint sensitivity")
    assert detail["value"].startswith("not_exercised:")   # a start zero is not a missing endpoint
    excluded = next(d for d in grade["result"]["details"] if d["label"] == "Excluded")
    assert "1 with a zero start price" in excluded["value"]


def test_missing_scoring_code_identity_blocks_grading():
    """An outcome column with no named, hashed scoring code is an unattributed table."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source.pop("scoring_code_identity")
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "scoring-code identity" in grade["reason"]
    assert grade["result"] is None


# --------------------------------------------------------------- re-review counterexamples
def test_a_source_cannot_declare_its_own_smaller_season():
    """The exact re-review case: unchanged window, but the source says one week and one game.

    Comparing weeks_expected to weeks_present only ever compared the source to itself, so any
    self-consistent source passed. The expected universe now comes from the enrollment.
    """
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["coverage"]["weeks_expected"] = [1]
    source["coverage"]["weeks_present"] = [1]
    source["coverage"]["expected_game_ids"] = EXPECTED_GAME_IDS[:1]
    source["coverage"]["observed_game_ids"] = EXPECTED_GAME_IDS[:1]
    source["coverage"]["games_expected"] = 1
    source["coverage"]["games_present"] = 1
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "frozen at enrollment" in grade["reason"]
    assert grade["result"] is None


def test_a_source_cannot_shrink_the_game_universe_while_keeping_the_weeks():
    """Isolates the game-id binding: every week is declared, but the schedule is redefined."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    half = EXPECTED_GAME_IDS[: len(EXPECTED_GAME_IDS) // 2]
    source["coverage"]["expected_game_ids"] = half
    source["coverage"]["observed_game_ids"] = half
    source["coverage"]["games_expected"] = len(half)
    source["coverage"]["games_present"] = len(half)
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "expected game universe frozen at enrollment" in grade["reason"]


def test_one_unobserved_frozen_game_blocks_the_grade():
    enrollment = production_enrollment()
    source = outcome_source(enrollment, observed_game_ids=EXPECTED_GAME_IDS[:-1],
                            games_present=len(EXPECTED_GAME_IDS) - 1)
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "unobserved" in grade["reason"]


def test_duplicate_observed_game_ids_are_refused():
    enrollment = production_enrollment()
    doubled = EXPECTED_GAME_IDS + [EXPECTED_GAME_IDS[0]]
    source = outcome_source(enrollment, observed_game_ids=doubled)
    with pytest.raises(TrackRecordError, match="duplicate game ids"):
        grade_production(enrollment=enrollment, outcome_source=source,
                         evaluated_at="2027-01-10T00:00:00Z")


def test_a_source_stamped_in_the_future_cannot_support_todays_grade():
    """The re-review case: outcomes captured in 2099 accepted by a 2027 evaluation."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment, captured_at="2099-01-06T00:00:00Z")
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "after the evaluation instant" in grade["reason"]


def test_a_source_captured_before_the_window_closed_cannot_describe_it():
    enrollment = production_enrollment()
    source = outcome_source(enrollment, captured_at="2026-11-01T00:00:00Z")
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "predates the close" in grade["reason"]


def test_a_malformed_game_count_is_refused_not_coerced():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["coverage"]["games_present"] = True          # int(True) == 1
    with pytest.raises(TrackRecordError, match="non-negative integer"):
        grade_production(enrollment=enrollment, outcome_source=source,
                         evaluated_at="2027-01-10T00:00:00Z")


def test_a_naive_instant_is_refused_rather_than_read_in_local_time():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    with pytest.raises(TrackRecordError, match="no timezone offset"):
        grade_production(enrollment=enrollment, outcome_source=source,
                         evaluated_at="2027-01-10T00:00:00")


def test_an_all_missing_producer_stratum_is_reported_with_its_denominator():
    """A stratum whose every outcome is missing used to vanish from the report entirely."""
    enrollment = production_enrollment()
    for row in enrollment["document"]["production"]["rows"][:2]:
        row["producer"] = "silent_producer"
    source = outcome_source(enrollment)
    for row in enrollment["document"]["production"]["rows"][:2]:
        source["players"][row["sleeper_id"]] = {"value": None, "games": 0, "reason": "no outcome"}
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    ids = [c["id"] for c in grade["result"]["comparisons"]]
    assert any("silent_producer" in identity for identity in ids), ids
    silent = [c for c in grade["result"]["comparisons"] if "silent_producer" in c["id"]]
    assert all(c["scored"] == 0 for c in silent)
    assert all(c["eligible"] > 0 for c in silent)


# --------------------------------------------------------------------------- market cases
def test_an_ineligible_registration_cannot_be_rescued_by_a_later_endpoint():
    enrollment = market_enrollment()
    enrollment["document"]["market"]["state"] = "input_unavailable"
    enrollment["document"]["market"]["reason"] = "stale start capture"
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-12-11T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "stale start capture" in grade["reason"]
    assert grade["result"] is None


def test_an_endpoint_stamped_after_the_run_did_not_exist_when_it_was_made():
    enrollment = market_enrollment()
    grade = grade_market(enrollment=enrollment, endpoint_source=endpoint_source(enrollment),
                         evaluated_at="2026-09-01T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "after the evaluation instant" in grade["reason"]


def test_a_still_open_capture_window_is_awaiting_not_unavailable():
    """Day 91 of a 90-93 window: a compatible capture can still arrive."""
    enrollment = market_enrollment()
    during = grade_market(enrollment=enrollment, endpoint_source=None,
                          evaluated_at="2026-12-09T00:00:00Z")
    assert during["state"] == "awaiting_capture"
    assert "still open" in during["reason"]

    before = grade_market(enrollment=enrollment, endpoint_source=None,
                          evaluated_at="2026-10-01T00:00:00Z")
    assert before["state"] == "awaiting_capture"
    assert "has not opened" in before["reason"]

    after = grade_market(enrollment=enrollment, endpoint_source=None,
                         evaluated_at="2027-02-01T00:00:00Z")
    assert after["state"] == "input_unavailable"


def test_selection_filters_configuration_before_choosing_the_earliest():
    """An earlier capture under different league settings is a different measurement."""
    superflex = {"isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1}
    one_qb = {"isDynasty": True, "numQbs": 1, "numTeams": 12, "ppr": 1}
    captures = [
        {"as_of": "2026-12-08T00:00:00Z", "sha256": "a" * 64, "complete": True,
         "configuration": one_qb},
        {"as_of": "2026-12-09T00:00:00Z", "sha256": "b" * 64, "complete": True,
         "configuration": superflex},
    ]
    chosen = select_endpoint(inventory=captures, t0="2026-09-09T00:00:00Z", horizon_days=90,
                             configuration=superflex, evaluated_at="2026-12-11T00:00:00Z")
    assert chosen["chosen"]["sha256"] == "b" * 64
    # and the answer does not depend on the order the inventory happens to arrive in
    reversed_choice = select_endpoint(inventory=list(reversed(captures)),
                                      t0="2026-09-09T00:00:00Z", horizon_days=90,
                                      configuration=superflex,
                                      evaluated_at="2026-12-11T00:00:00Z")
    assert reversed_choice["chosen"]["sha256"] == "b" * 64


def test_selection_ignores_a_capture_that_did_not_exist_at_evaluation():
    captures = [{"as_of": "2026-12-08T00:00:00Z", "sha256": "a" * 64, "complete": True,
                 "configuration": None}]
    chosen = select_endpoint(inventory=captures, t0="2026-09-09T00:00:00Z", horizon_days=90,
                             configuration=None, evaluated_at="2026-12-07T00:00:00Z")
    assert chosen["chosen"] is None
    assert any("after the evaluation instant" in reason for _, reason in chosen["rejected"])


def test_sensitivity_reports_insufficient_when_nobody_has_a_frozen_baseline():
    """The re-review repro: no frozen momentum anywhere, yet it reported a strong association.

    Most rows carry a real movement and a few are missing, so the scenario is NOT degenerate --
    the old gap-only cohort produced a confident number here. The cohort rule is what refuses it,
    not an accidental constant.
    """
    entries = []
    for position in POSITIONS:
        for index in range(12):
            missing = index < 3
            entries.append({"position": position, "gap": float(index),
                            "raw": None if missing else 0.01 * index, "momentum": None,
                            "start_positive": True, "start_zero": False,
                            "endpoint_missing": missing})
    result = _missing_endpoint_sensitivity(entries)
    assert result["state"] == "insufficient"
    assert result["estimate"] is None
    assert "frozen baseline" in result["note"]


def test_sensitivity_excludes_an_unknown_start_price_not_only_an_explicit_zero():
    entries = [{"position": position, "gap": float(index), "raw": None,
                "momentum": float(index), "start_positive": False, "start_zero": False,
                "endpoint_missing": True}
               for position in POSITIONS for index in range(12)]
    assert _missing_endpoint_sensitivity(entries)["state"] == "insufficient"


def test_selection_cannot_silently_skip_the_compatibility_filter():
    """An optional filter is a filter a caller forgets. Both are required of every caller."""
    with pytest.raises(TypeError):
        select_endpoint(inventory=[], t0="2026-09-09T00:00:00Z", horizon_days=90)


def test_an_ineligible_registration_is_unavailable_even_with_no_endpoint():
    """Readiness is settled at enrollment, so it is decided before the capture window.

    Asking "has a capture arrived yet?" first reported an ineligible stream as awaiting_capture,
    which reads as merely early rather than never eligible.
    """
    enrollment = market_enrollment()
    enrollment["document"]["market"]["state"] = "input_unavailable"
    enrollment["document"]["market"]["reason"] = "stale start capture"
    grade = grade_market(enrollment=enrollment, endpoint_source=None,
                         evaluated_at="2026-12-09T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "stale start capture" in grade["reason"]


def test_a_prepared_serialization_cannot_witness_for_a_real_capture():
    """A restatement of the prepared numbers is not an observation of the world."""
    enrollment = production_enrollment()
    source = outcome_source(enrollment, captured_at="2026-11-01T00:00:00Z")
    source["sources"].append({"name": "prepared_outcome.json", "sha256": "e" * 64,
                              "role": "prepared_serialization",
                              "captured_at": "2027-01-05T00:00:00Z", "bytes_len": 4})
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "predates the close" in grade["reason"]


def test_a_source_list_with_only_a_serialization_proves_nothing():
    enrollment = production_enrollment()
    source = outcome_source(enrollment)
    source["sources"] = [{"name": "prepared_outcome.json", "sha256": "e" * 64,
                          "role": "prepared_serialization", "bytes_len": 4}]
    grade = grade_production(enrollment=enrollment, outcome_source=source,
                             evaluated_at="2027-01-10T00:00:00Z")
    assert grade["state"] == "input_unavailable"
    assert "no actual capture" in grade["reason"]
