"""Building the enrollment: what we registered, what we could not, and why — never a filled-in blank.

Every test here is a way the record could quietly become untrue:

  a median taken over survivors instead of the whole prior population flatters the baseline
  an absent row read as a zero invents a bad season the player never had
  a baseline built today claiming to be contemporaneous rewrites what was knowable at the cutoff
  a target that differs in one measurement field makes two numbers look comparable when they are not
  a source whose bytes do not match its declared hash is a different source
  a missing schedule read as "preseason, probably" fabricates freeze eligibility
  a half-ready market stream deleting the production inputs loses the half that WAS ready

No actual 2026 outcome is touched anywhere in this file. The seasons are synthetic and closed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.dynasty_genius.capture.track_record_inputs import (
    TrackRecordInputError,
    build_evaluation_inputs,
)

CAPTURED_AT = datetime(2026, 9, 9, 9, 40, tzinfo=timezone.utc)

TARGET = {
    "scope": "REG", "scoring": "PPR_nflverse_default", "window": "championship_week17",
    "exposure": "per_season", "event": "points", "clock": "per_season",
    "quantity": "season_points", "labels_through": 2025,
}
SIX = {
    "report_run": "20260906T214512Z", "report_sha256": "1" * 64, "market_sha256": "2" * 64,
    "league_sha256": "3" * 64, "catalog_run": "20260907T013635Z", "catalog_content_sha256": "4" * 64,
}


def positions_parquet(mapping: dict[str, str]) -> bytes:
    """A real parquet in the shape the runtime check reads, so the fixture cannot dodge that check."""
    import io as _io

    import pandas as pd

    rows = [{"player_id": player, "position": position, "season": 2025, "week": 1,
             "season_type": "REG"} for player, position in mapping.items()]
    buffer = _io.BytesIO()
    pd.DataFrame(rows).to_parquet(buffer, index=False)
    return buffer.getvalue()


def gsis(short: str) -> str:
    """The outcome table keys on GSIS ids, so the fixtures use real-shaped ones."""
    return f"00-{int(short):07d}"


def prior_csv(rows: list[tuple[str, int, float, int, int]]) -> bytes:
    body = "player_id,season,points,games,appeared\n"
    for player, season, points, games, appeared in rows:
        identity = player if player.startswith("00-") else gsis(player)
        body += f"{identity},{season},{points},{games},{appeared}\n"
    return body.encode("utf-8")


def artifacts(players: list[dict]) -> dict[str, bytes]:
    """Report and catalog bytes in the SHAPE THE REAL ARCHIVE USES.

    An earlier version of this fixture invented a flat shape of its own. It passed, and it was
    testing nothing: the real board carries signed margins under `horizon_board.all_inspectable`
    with a `union_replacement` reference series, and the real catalog carries `rows_detail`.
    """
    board_rows, catalog_rows = [], []
    for p in players:
        margin = p.get("forecast")
        identity = p.get("gsis") or (gsis(p["id"]) if p["id"].isdigit() else None)
        board_rows.append({
            "player_id": identity, "sleeper_id": p["id"],
            "name": p["name"], "position": p["position"], "producer": p.get("producer", "producer-a"),
            "readiness": p.get("readiness", "comparable"),
            "evidence_verified": p.get("evidence_verified", True),
            "reference_player": "Reference Person", "reference_expected_points": 10.0,
            "seasons": [{"season": 2026,
                         "expected_margin": None if margin is None else margin - 10.0,
                         "action": "hold", "advantage": 0.0}],
        })
        catalog_rows.append({
            "sleeper_id": p["id"], "player_id": identity,
            "name": p["name"], "league_position": p["position"],
            "join_basis": "census_nfl_gsis", "population": p.get("population", "default"),
            "recovered": p.get("recovered", False),
            "starting_estimate": p.get("starting_estimate", False),
            "missing_reason": None, "roster_id": None, "owned_now": False,
            "forecast": {"join_id": identity,
                         "seasons": [{"season": 2026, "e_points": margin}]},
        })
    report = {
        "board_target": dict(TARGET),
        "horizon_board": {
            "all_inspectable": board_rows,
            "annual_producers": [{
                "model_version": "union_replacement",
                "replacement": {position: [{"rate_quantity": "expected_season_points_same_window",
                                            "rate_ppg": 10.0}]
                                for position in {p["position"] for p in players}},
            }],
        },
    }
    catalog = {"rows_detail": catalog_rows, "forecast_years": [2026], "future_years": []}
    return {
        "report.json": json.dumps(report).encode(),
        "catalog.json": json.dumps(catalog).encode(),
        "evaluation-plan.json": json.dumps({"schema_version": "workspace_evaluation_plan.v1",
                                            "plan_id": "workspace-production-2026-v1"}).encode(),
        "market.json": json.dumps({"source": "fc_native", "settings_hash": "abc123",
                                   "settings": {"isDynasty": True, "numQbs": 2, "numTeams": 12,
                                                "ppr": 1}, "entries": []}).encode(),
        "league.json": json.dumps({
            "rosters": [{"roster_id": i} for i in range(1, 13)],
            "league": {"roster_positions": ["QB", "SUPER_FLEX"],
                       "scoring_settings": {"rec": 1.0, "bonus_rec_te": 0.0}},
        }).encode(),
    }


def snapshot(players: list[dict]) -> dict:
    """Only the receipt and the derived ranks matter here; the population comes from the artifacts."""
    return {
        "snapshot": {
            "snapshot_id": "a" * 64, "saved_at": "2026-09-08T12:00:00Z",
            "source": dict(SIX), "forecast_date": "2026-09-06",
            "market_as_of": "2026-09-08T12:00:00Z", "ownership_as_of": "2026-09-06T13:00:52Z",
            "evaluation_plan": {"plan": "workspace-production-2026-v1"},
        },
        "ranks": {"status": "available", "source": dict(SIX), "rows": [
            {"sleeper_id": p["id"], "name": p["name"], "position": p["position"],
             "our_rank": p.get("our_rank"), "market_rank": p.get("market_rank"),
             "market_value": p.get("market_value"), "missing_reason": None}
            for p in players]},
        "comparison": {"source": dict(SIX), "roster": [], "available": []},
    }


def baseline_source(csv_bytes: bytes, **over) -> dict:
    # A real-shaped manifest: it must account for the exact CSV bytes and declare its own windows,
    # coverage and scoring, because those claims are now checked rather than taken from the receipt.
    manifest_bytes = json.dumps({
        "schema_version": "dg179_league_season_outcomes_v1",
        "scoring_preset": "nflverse_default_ppr_championship_window_v1",
        "coverage_status": "qualified_research_game_complete_identified_rows",
        "league_scoring_exact": False,
        "last_complete_season": 2025,
        "season_windows": {"2025": {"included_reg_weeks": list(range(1, 18))}},
        "outputs": {"outcomes.csv": {"bytes": len(csv_bytes),
                                     "sha256": hashlib.sha256(csv_bytes).hexdigest()}},
    }, sort_keys=True).encode()
    declared_positions = over.get("positions") or {gsis(n): "QB" for n in ("1", "2", "3", "9")}
    evidence_bytes = positions_parquet(declared_positions)
    envelope = {
        "role": "prior_season_outcomes", "kind": "dg179_league_season_outcomes_v1",
        "manifest_bytes": manifest_bytes, "csv_bytes": csv_bytes,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "target": dict(TARGET), "prior_season": 2025, "admitted_seasons": [2025],
        # The median must span every verified prior participant, including players who are no longer
        # forecast, so their positions cannot come from the current board. The prior-season source
        # supplies them; without it the position median is unavailable rather than guessed.
        "positions": dict(declared_positions),
        "coverage_status": "qualified_research_game_complete_identified_rows",
        "league_scoring_exact": False,
        "captured_at": "2026-09-09T09:40:00Z", "source_as_of": "2026-01-10T00:00:00Z",
        "source_available_at": None, "source_revision": "nflverse-2026-01-10",
        "source_artifacts": [{
            "name": "prior-positions.parquet", "raw_bytes": evidence_bytes,
            "sha256": hashlib.sha256(evidence_bytes).hexdigest(), "bytes": len(evidence_bytes),
            "original_path": "stats_player_week_2025.parquet",
        }],
        "raw_bytes": b"the baseline receipt file's own bytes",
    }
    envelope.update(over)
    return envelope


def schedule_source(**over) -> dict:
    envelope = {
        "role": "schedule", "season": 2026, "source_sha256": "5" * 64,
        "raw_bytes": b"the schedule file's own bytes",
        "timezone": "America/New_York",  # checked against the bound dictionary, never trusted
        "captured_at": "2026-09-09T09:40:00Z", "source_as_of": "2026-09-01T00:00:00Z",
        "source_available_at": "2026-09-01T00:00:00Z", "source_revision": "sched-1",
        # the declaration is weeks 1 to 17, so evidence about it has to cover them
        "games": [
            {"game_id": f"2026_{week:02d}_A_B", "reg": True, "week": week,
             "kickoff_at": f"2026-09-{9 + week:02d}T00:20:00+00:00", "finalized": False}
            for week in range(1, 18)
        ],
    }
    envelope.update(over)
    header = "game_id,season,game_type,week,gameday,gametime\n"
    zone = ZoneInfo(str(envelope.get("timezone") or "UTC"))
    lines = []
    for game in envelope["games"]:
        if not game.get("reg"):
            continue
        moment = (datetime.fromisoformat(str(game["kickoff_at"]).replace("Z", "+00:00"))
                  .astimezone(zone) if game.get("kickoff_at")
                  else datetime.fromisoformat(f"{game['gameday']}T{game['gametime']}"))
        lines.append(f"{game['game_id']},{envelope.get('season', 2026)},REG,{game['week']},"
                     f"{moment.date()},{moment.strftime('%H:%M')}\n")
    raw_csv = (header + "".join(lines)).encode()
    envelope.setdefault("source_artifacts", [])
    # the dictionary is the evidence for the zone; the prepared claim is checked against it
    dictionary = (b'gameday,character, The date on which the game occurred.\n'
                  b'gametime,character,"The kickoff time of the game. This is represented in '
                  b'24-hour time and the Eastern time zone, regardless of what time zone the game '
                  b'was being played in."\n')
    keep = [a for a in envelope["source_artifacts"]
            if a.get("name") not in {"schedule-raw.csv", "dictionary_schedules.csv"}]
    envelope["source_artifacts"] = keep + [
        {"name": "schedule-raw.csv", "raw_bytes": raw_csv,
         "sha256": hashlib.sha256(raw_csv).hexdigest(), "bytes": len(raw_csv)},
        {"name": "dictionary_schedules.csv", "raw_bytes": dictionary,
         "sha256": hashlib.sha256(dictionary).hexdigest(), "bytes": len(dictionary)},
    ]
    return envelope


MARKET_PLAN = {"plan": "workspace-market-movement-90d-v1", "horizon_days": 90,
               "configuration": {"league": "12-team superflex", "scoring": "full PPR"}}


def build(players=None, *, baseline=..., schedule=..., history=None, captured_at=CAPTURED_AT):
    players = players if players is not None else [
        {"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0},
    ]
    if baseline is ...:
        baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]))
    if schedule is ...:
        schedule = schedule_source()
    return build_evaluation_inputs(
        snapshot=snapshot(players), artifacts=artifacts(players),
        baseline_source=baseline, schedule_source=schedule,
        market_history_source=history, market_plan=MARKET_PLAN, captured_at=captured_at,
    )


def rows_by_id(document: dict, stream: str = "production") -> dict:
    return {r["sleeper_id"]: r for r in document[stream]["rows"]}


# ── the named cases ─────────────────────────────────────────────────────────────

def test_prior_median_uses_full_prior_population():
    """Three players scored 0, 10 and 100 last season; only the 100 is still forecast.

    The median baseline for the position is 10.0 — the middle of everyone who actually played — not
    100.0, which is what taking the median over the survivors would give.
    """
    csv = prior_csv([("1", 2025, 0.0, 17, 1), ("2", 2025, 10.0, 17, 1), ("3", 2025, 100.0, 17, 1)])
    built = build(
        [{"id": "3", "name": "Cy Three", "position": "QB", "forecast": 120.0}],
        baseline=baseline_source(csv),
    )
    row = rows_by_id(built["document"])["3"]
    assert row["baselines"]["position_median"] == 10.0
    assert row["baselines"]["prior_season"] == 100.0


def test_absent_row_is_missing_not_zero():
    csv = prior_csv([("1", 2025, 10.0, 17, 1)])
    built = build(
        [{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0},
         {"id": "9", "name": "Newt Nine", "position": "QB", "forecast": 50.0}],
        baseline=baseline_source(csv),
    )
    absent = rows_by_id(built["document"])["9"]
    assert absent["baselines"]["prior_season"] is None
    assert absent["missing_reasons"]["prior_season"]
    assert "0" not in str(absent["baselines"]["prior_season"])


def test_a_verified_non_participant_may_be_zero():
    """Absence from the table cannot be zero; a verified zero season can."""
    csv = prior_csv([("1", 2025, 0.0, 0, 0), ("2", 2025, 10.0, 17, 1)])
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}],
                  baseline=baseline_source(csv))
    assert rows_by_id(built["document"])["1"]["baselines"]["prior_season"] == 0.0


def test_reconstructed_baseline_keeps_actual_capture_time():
    """A baseline built today is reconstructed even though its 2025 facts predate the save."""
    document = build()["document"]
    production = document["production"]
    assert production["provenance_class"] == "reconstructed"
    source = next(s for s in production["sources"] if s["role"] == "prior_season_outcomes")
    assert source["captured_at"] == "2026-09-09T09:40:00Z"
    assert source["source_available_at"] is None
    assert source["source_as_of"] == "2026-01-10T00:00:00Z"


def test_a_baseline_built_now_is_reconstructed_even_with_a_proven_earlier_source():
    """The facts can predate the save; the BASELINE does not. There is no contemporaneous branch."""
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]),
                               source_available_at="2026-09-07T00:00:00Z")
    assert build(baseline=baseline)["document"]["production"]["provenance_class"] == "reconstructed"


def test_a_source_that_claims_it_was_available_in_the_future_refuses():
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]),
                               source_available_at="2099-01-01T00:00:00Z")
    with pytest.raises(TrackRecordInputError, match="future"):
        build(baseline=baseline)


def test_a_manifest_that_is_not_json_refuses():
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]))
    baseline["manifest_bytes"] = b"not json at all"
    baseline["manifest_sha256"] = hashlib.sha256(baseline["manifest_bytes"]).hexdigest()
    with pytest.raises(TrackRecordInputError, match="manifest"):
        build(baseline=baseline)


def test_a_labels_through_after_the_target_season_refuses():
    """A vintage later than the season being forecast would be future knowledge."""
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]),
                               target=dict(TARGET) | {"labels_through": 2099})
    with pytest.raises(TrackRecordInputError, match="labels_through"):
        build(baseline=baseline)


def test_the_appeared_column_may_be_true_false_strings():
    """The real CSV writes booleans as text; int('true') would raise, and a coerced 0 would lie."""
    csv = prior_csv([("1", 2025, 10.0, 17, "true"), ("2", 2025, 0.0, 0, "false"),
                     ("3", 2025, 30.0, 17, "true")])
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}],
                  baseline=baseline_source(csv))
    row = rows_by_id(built["document"])["1"]
    assert row["baselines"]["prior_season"] == 10.0
    # the non-participant is excluded from the median, so it is the median of 10 and 30
    assert row["baselines"]["position_median"] == 20.0


def test_a_non_participant_is_excluded_from_the_position_median_but_keeps_its_own_zero():
    csv = prior_csv([("1", 2025, 0.0, 0, "false"), ("2", 2025, 10.0, 17, "true"),
                     ("3", 2025, 30.0, 17, "true")])
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}],
                  baseline=baseline_source(csv))
    row = rows_by_id(built["document"])["1"]
    assert row["baselines"]["prior_season"] == 0.0, "a verified zero season was lost"
    assert row["baselines"]["position_median"] == 20.0, "an appeared=false row entered the median"


def test_only_the_four_graded_positions_form_a_median():
    """Raw FB and CB are excluded by the frozen convention, and never remapped to a fantasy slot."""
    csv = prior_csv([("1", 2025, 10.0, 17, "true"), ("2", 2025, 30.0, 17, "true"),
                     ("4", 2025, 999.0, 17, "true")])
    baseline = baseline_source(csv, positions={gsis("1"): "QB", gsis("2"): "QB", gsis("4"): "FB"})
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}],
                  baseline=baseline)
    assert rows_by_id(built["document"])["1"]["baselines"]["position_median"] == 20.0


def test_a_schedule_missing_the_declared_weeks_refuses_to_prove_a_freeze():
    """A week-18-only schedule is not evidence about weeks 1 to 17."""
    late = schedule_source(games=[{"game_id": "2026_18_A_B", "reg": True, "week": 18,
                                   "kickoff_at": "2027-01-10T00:20:00+00:00", "finalized": False}])
    document = build(schedule=late)["document"]
    assert document["production"]["state"] == "input_unavailable"
    assert "week" in document["production"]["reason"].lower()


def test_an_eastern_schedule_is_normalised_with_daylight_saving():
    """The saved CSV carries Eastern wall-clock time; September is EDT, so 20:20 is 00:20Z next day."""
    eastern = schedule_source(games=[
        {"game_id": f"2026_{w:02d}_NE_SEA", "reg": True, "week": w,
         "gameday": "2026-09-09", "gametime": "20:20", "finalized": None}
        for w in range(1, 18)
    ])
    document = build(schedule=eastern)["document"]
    assert document["production"]["target_start_at"] == "2026-09-10T00:20:00Z"


def test_target_mismatch_refuses():
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]),
                               target=dict(TARGET) | {"window": "all_reg_weeks"})
    with pytest.raises(TrackRecordInputError, match="window"):
        build(baseline=baseline)


def test_a_different_labels_through_does_not_refuse():
    """labels_through is checked against the cutoff and target season, never required to match."""
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]),
                               target=dict(TARGET) | {"labels_through": 2024})
    assert build(baseline=baseline)["document"]["production"]["rows"]


def test_hash_mismatch_refuses():
    baseline = baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)]), csv_sha256="0" * 64)
    with pytest.raises(TrackRecordInputError, match="csv_sha256"):
        build(baseline=baseline)


def test_cutoff_evidence_required():
    """No schedule means no freeze evidence. It never means 'preseason, probably'."""
    document = build(schedule=None)["document"]
    assert document["production"]["state"] == "input_unavailable"
    assert "schedule" in document["production"]["reason"].lower()
    assert document["production"]["provenance_class"] == "unavailable"


def test_a_target_game_before_the_freeze_is_cutoff_ineligible():
    early = schedule_source(games=[
        {"game_id": f"2026_{week:02d}_A_B", "reg": True, "week": week,
         "kickoff_at": f"2026-09-0{week}T00:20:00+00:00" if week < 8 else f"2026-09-{9 + week:02d}T00:20:00+00:00",
         "finalized": False}
        for week in range(1, 18)])
    document = build(schedule=early)["document"]
    assert document["production"]["state"] == "cutoff_ineligible"


def test_partial_market_readiness_does_not_erase_production_inputs():
    """A stale market capture makes the market stream unavailable and leaves production intact."""
    stale = snapshot([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}])
    stale["snapshot"]["market_as_of"] = "2026-08-01T13:00:00Z"  # far more than 24h before T0
    built = build_evaluation_inputs(
        snapshot=stale, artifacts=artifacts([{"id": "1", "name": "Ada One", "position": "QB",
                                              "forecast": 100.0}]),
        baseline_source=baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)])),
        schedule_source=schedule_source(), market_history_source=None,
        market_plan=MARKET_PLAN, captured_at=CAPTURED_AT,
    )
    document = built["document"]
    assert document["market"]["state"] == "input_unavailable"
    assert document["production"]["state"] != "input_unavailable"
    assert document["production"]["rows"], "production rows were erased by an unready market stream"


def test_archive_bytes_unchanged():
    """Building an enrollment must not mutate the snapshot it was handed."""
    import copy
    given = snapshot([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0}])
    before = copy.deepcopy(given)
    build_evaluation_inputs(
        snapshot=given, artifacts=artifacts([{"id": "1", "name": "Ada One", "position": "QB",
                                              "forecast": 100.0}]),
        baseline_source=baseline_source(prior_csv([("1", 2025, 10.0, 17, 1)])),
        schedule_source=schedule_source(), market_history_source=None,
        market_plan=MARKET_PLAN, captured_at=CAPTURED_AT,
    )
    assert given == before


# ── the envelope DG-207 consumes ────────────────────────────────────────────────

def test_the_enrollment_carries_every_required_key():
    document = build()["document"]
    assert document["schema_version"] == "track_record.enrollment.v1"
    for key in ("snapshot_id", "forecast_identity", "enrolled_at", "source", "snapshot", "input_hashes",
                "production", "market"):
        assert key in document, key
    assert set(document["source"]) == set(SIX)
    for stream in ("production", "market"):
        for key in ("state", "reason", "plan", "plan_sha256", "window", "provenance_class", "rows",
                    "sources"):
            assert key in document[stream], f"{stream}.{key}"
        assert document[stream]["state"] in {
            "not_registered", "awaiting_horizon", "awaiting_capture", "input_unavailable",
            "cutoff_ineligible", "insufficient_evidence", "graded",
        }


def test_the_market_rows_keep_ties_and_published_zeros():
    players = [
        {"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0,
         "our_rank": {"start": 230, "end": 388, "total": 388},
         "market_rank": {"start": 12, "end": 12, "total": 388}, "market_value": 0.0},
    ]
    document = build(players)["document"]
    row = rows_by_id(document, "market")["1"]
    assert row["our_rank"] == [230, 388], "a tie was flattened"
    assert row["start_price"] == 0.0, "a published zero was dropped"
    assert row["momentum"] is None and row["missing_reasons"]["momentum"]


def test_enrolled_at_is_the_actual_clock_and_not_a_source_date():
    document = build()["document"]
    assert document["enrolled_at"] == "2026-09-09T09:40:00Z"
    assert document["market"]["t0"] == "2026-09-09T09:40:00Z"


def test_the_prior_season_is_joined_by_the_verified_source_id_not_the_sleeper_id():
    """The outcome table keys on GSIS. Joining it by Sleeper id would find nothing, or worse,
    the wrong player. An unresolved identity is unknown, never a zero."""
    csv = prior_csv([("00-0031234", 2025, 42.0, 17, 1), ("00-0031299", 2025, 8.0, 17, 1)])
    baseline = baseline_source(csv, positions={"00-0031234": "QB", "00-0031299": "QB"})
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0,
                    "gsis": "00-0031234"}], baseline=baseline)
    row = rows_by_id(built["document"])["1"]
    assert row["baselines"]["prior_season"] == 42.0
    assert row["baselines"]["position_median"] == 25.0


def test_a_player_with_no_verified_source_id_is_unknown_not_zero():
    csv = prior_csv([("00-0031234", 2025, 42.0, 17, 1)])
    baseline = baseline_source(csv, positions={"00-0031234": "QB"})
    built = build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0,
                    "gsis": "not-a-gsis-id"}], baseline=baseline)
    row = rows_by_id(built["document"])["1"]
    assert row["baselines"]["prior_season"] is None
    assert "source id" in row["missing_reasons"]["prior_season"]


def test_the_expected_game_membership_is_frozen_with_the_enrollment():
    """A grader must match observed outcomes against this, or one self-declared game could pass
    for a season."""
    production = build()["document"]["production"]
    assert production["weeks_expected"] == list(range(1, 18))
    assert len(production["expected_game_ids"]) == 17
    assert production["expected_game_ids"] == sorted(production["expected_game_ids"])


def test_a_schedule_for_another_season_refuses():
    with pytest.raises(TrackRecordInputError, match="season"):
        build(schedule=schedule_source(season=2025))


def test_a_duplicated_game_refuses():
    games = schedule_source()["games"]
    with pytest.raises(TrackRecordInputError, match="twice"):
        build(schedule=schedule_source(games=games + [games[0]]))


def test_a_naive_kickoff_without_an_offset_refuses():
    naive = schedule_source(games=[{"game_id": f"2026_{w:02d}_A_B", "reg": True, "week": w,
                                    "kickoff_at": "2026-09-10T00:20:00", "finalized": None}
                                   for w in range(1, 18)])
    with pytest.raises(TrackRecordInputError, match="timezone offset"):
        build(schedule=naive)


def test_a_non_boolean_finalized_refuses():
    games = [{"game_id": f"2026_{w:02d}_A_B", "reg": True, "week": w,
              "kickoff_at": f"2026-09-{9 + w:02d}T00:20:00+00:00", "finalized": "false"}
             for w in range(1, 18)]
    with pytest.raises(TrackRecordInputError, match="finalized"):
        build(schedule=schedule_source(games=games))


# ── the frozen trailing comparator ──────────────────────────────────────────────

def capture(as_of: str, *, prices: dict, known_at: str | None = None, complete: bool = True,
            configuration: dict | None = None, bind: bool = True) -> dict:
    content = {
        "as_of": as_of, "complete": complete, "prices": prices,
        "configuration": configuration if configuration is not None else {
            "source": "fc_native", "settings_hash": "abc123",
            "isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1,
        },
    }
    payload = json.dumps(content, sort_keys=True).encode()
    entry = {"capture_id": f"cap-{as_of}", "as_of": as_of, "known_at": known_at or as_of,
             "raw_bytes": payload, "sha256": hashlib.sha256(payload).hexdigest()}
    if not bind:
        entry.pop("known_at")
        entry.pop("sha256")
    return entry


def market_history(*captures: dict) -> dict:
    return {"role": "market_history", "kind": "fantasycalc_capture_inventory",
            "captures": list(captures), "raw_bytes": b"the history file's own bytes",
            "source_artifacts": [], "captured_at": "2026-09-09T09:40:00Z",
            "source_as_of": "2026-08-10T00:00:00Z", "source_available_at": "2026-08-10T00:00:00Z",
            "source_revision": "history-1", "source_sha256": "6" * 64}


PLAYER = [{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0,
           "our_rank": {"start": 10, "end": 10, "total": 388},
           "market_rank": {"start": 40, "end": 40, "total": 388}, "market_value": 120.0}]


def market_row(document):
    return rows_by_id(document, "market")["1"]


def test_the_comparator_takes_the_latest_capture_inside_the_declared_window():
    """T0 is 2026-09-09, so the window is as-of in [Aug 7, Aug 10]. The Aug 10 capture wins."""
    built = build(PLAYER, history=market_history(
        capture("2026-08-08T00:00:00Z", prices={"1": 60.0}),
        capture("2026-08-10T00:00:00Z", prices={"1": 100.0}),
    ))
    assert built["document"]["market"]["comparator_capture"]["as_of"] == "2026-08-10T00:00:00Z"
    assert market_row(built["document"])["momentum"] == pytest.approx(0.2)  # 120/100 - 1


def test_a_capture_outside_the_window_is_never_a_near_enough_fallback():
    built = build(PLAYER, history=market_history(capture("2026-07-01T00:00:00Z", prices={"1": 100.0})))
    assert built["document"]["market"]["comparator_capture"] is None
    assert "no complete compatible capture" in built["document"]["market"]["comparator_reason"]
    assert market_row(built["document"])["momentum"] is None


def test_a_capture_not_yet_known_at_enrollment_is_hindsight_and_excluded():
    built = build(PLAYER, history=market_history(
        capture("2026-08-10T00:00:00Z", prices={"1": 100.0}, known_at="2026-09-20T00:00:00Z")))
    assert built["document"]["market"]["comparator_capture"] is None


def test_an_incompatible_or_incomplete_capture_is_excluded():
    for bad in (capture("2026-08-10T00:00:00Z", prices={"1": 100.0}, complete=False),
                capture("2026-08-10T00:00:00Z", prices={"1": 100.0},
                        configuration={"source": "somewhere else"})):
        built = build(PLAYER, history=market_history(bad))
        assert built["document"]["market"]["comparator_capture"] is None


def test_momentum_needs_a_positive_price_at_both_points():
    built = build(PLAYER, history=market_history(capture("2026-08-10T00:00:00Z", prices={"1": 0.0})))
    row = market_row(built["document"])
    assert row["momentum"] is None
    assert row["missing_reasons"]["momentum"]


def test_the_capture_configuration_comes_from_the_archived_market_bytes():
    configuration = build(PLAYER)["document"]["market"]["capture_configuration"]
    assert configuration["source"] == "fc_native"
    assert configuration["numTeams"] == 12
    assert configuration != {}


# ── the three runtime guards the reviewer found missing ─────────────────────────

def test_a_tampered_position_value_refuses_even_though_the_source_bytes_are_untouched():
    """A green receipt does not authorise an arbitrary map. Flipping one QB to WR moves two medians,
    and the raw parquet has not changed a byte, so only a runtime re-derivation can see it."""
    csv = prior_csv([("1", 2025, 10.0, 17, 1), ("2", 2025, 30.0, 17, 1)])
    honest = {gsis("1"): "QB", gsis("2"): "QB"}
    baseline = baseline_source(csv, positions=honest)
    baseline["positions"] = {gsis("1"): "WR", gsis("2"): "QB"}  # bytes untouched, claim changed
    with pytest.raises(TrackRecordInputError, match="disagrees with the raw position source"):
        build([{"id": "1", "name": "Ada One", "position": "QB", "forecast": 100.0,
                "gsis": gsis("1")}], baseline=baseline)


def test_a_prepared_schedule_that_drops_a_game_refuses():
    """Every declared week is still present and every proof still hashes; only the universe shrank."""
    full = schedule_source()
    trimmed = dict(full)
    trimmed["games"] = [g for g in full["games"] if g["game_id"] != full["games"][0]["game_id"]]
    trimmed["source_artifacts"] = full["source_artifacts"]  # the raw proof is unchanged
    with pytest.raises(TrackRecordInputError, match="drops 1 game"):
        build(schedule=trimmed)


def test_a_prepared_kickoff_that_disagrees_with_the_raw_source_refuses():
    full = schedule_source()
    moved = dict(full)
    games = [dict(g) for g in full["games"]]
    games[0]["kickoff_at"] = "2026-09-11T00:20:00+00:00"
    moved["games"] = games
    moved["source_artifacts"] = full["source_artifacts"]
    with pytest.raises(TrackRecordInputError, match="kicks off at"):
        build(schedule=moved)


def test_a_history_capture_without_availability_or_a_digest_refuses():
    """No default may invent when a capture became knowable, or what was in it."""
    with pytest.raises(TrackRecordInputError, match="known_at"):
        build(PLAYER, history=market_history(
            capture("2026-08-10T00:00:00Z", prices={"1": 100.0}, bind=False)))


def test_a_history_capture_whose_bytes_were_tampered_with_refuses():
    entry = capture("2026-08-10T00:00:00Z", prices={"1": 100.0})
    entry["raw_bytes"] = entry["raw_bytes"].replace(b"100.0", b"999.0")
    with pytest.raises(TrackRecordInputError, match="hashes to"):
        build(PLAYER, history=market_history(entry))


def test_a_capture_whose_declared_as_of_contradicts_its_bytes_refuses():
    entry = capture("2026-08-10T00:00:00Z", prices={"1": 100.0})
    entry["as_of"] = "2026-08-09T00:00:00Z"  # the sibling key now lies about the bound content
    with pytest.raises(TrackRecordInputError, match="as-of its own bytes"):
        build(PLAYER, history=market_history(entry))


def test_relabelling_the_prepared_timezone_refuses():
    """Calling Eastern gametimes Pacific would move every kickoff three hours while every hash and
    every declared week stayed valid. The bound dictionary is the evidence, not the label."""
    with pytest.raises(TrackRecordInputError, match="dictionary"):
        build(schedule=schedule_source(timezone="America/Los_Angeles"))


def test_a_schedule_without_its_dictionary_cannot_prove_a_timezone():
    envelope = schedule_source()
    envelope["source_artifacts"] = [a for a in envelope["source_artifacts"]
                                    if a["name"] != "dictionary_schedules.csv"]
    with pytest.raises(TrackRecordInputError, match="no evidence"):
        build(schedule=envelope)


def test_a_dictionary_that_does_not_say_eastern_refuses():
    envelope = schedule_source()
    other = b'gametime,character,"The kickoff time, in local stadium time."\n'
    envelope["source_artifacts"] = [a for a in envelope["source_artifacts"]
                                    if a["name"] != "dictionary_schedules.csv"] + [{
        "name": "dictionary_schedules.csv", "raw_bytes": other,
        "sha256": hashlib.sha256(other).hexdigest(), "bytes": len(other)}]
    with pytest.raises(TrackRecordInputError, match="Eastern"):
        build(schedule=envelope)
