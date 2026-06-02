"""S3 Task 10A 2025 prospect fixture-builder contract tests."""

from __future__ import annotations

import importlib

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    NormalizedCollegeProspectRow,
)

SNAPSHOT_ID = {
    "retrieval_timestamp": "2026-06-01T23:45:00Z",
    "endpoint": "/roster?year=2025",
    "api_version": "v2",
    "sha256": "cfbdhash",
    "row_count": 8,
}
SNAPSHOT_ID_STR = "cfbd_roster_2025:2026-06-01T23:45:00Z:/roster?year=2025:v2:cfbdhash:8"


def _builder_module():
    return importlib.import_module("src.dynasty_genius.identity.build_2025_prospect_fixture")


def _cfbd_row(
    athlete_id: int,
    first: str,
    last: str,
    *,
    team: str,
    position: str,
    year=3,
) -> dict:
    return {
        "id": athlete_id,
        "firstName": first,
        "lastName": last,
        "team": team,
        "position": position,
        "year": year,
    }


def _draft_row(
    name: str,
    *,
    position: str,
    college: str,
    college_athlete_id: int | None = None,
    pfr_player_id: str | None = None,
    pick: int = 40,
) -> dict:
    row = {
        "season": 2025,
        "pfr_player_name": name,
        "position": position,
        "college": college,
        "round": 2,
        "pick": pick,
        "team": "TEN",
        "gsis_id": f"00-{pick}",
        "pfr_player_id": pfr_player_id or f"Pick{pick:03d}",
        "cfb_player_id": f"drafted-test-{pick}",
    }
    if college_athlete_id is not None:
        row["collegeAthleteId"] = college_athlete_id
    return row


def _frozen_inputs(*, cfbd_rows, draft_rows, udfa_sources=None, manifest=None):
    return {
        "cfbd_roster": cfbd_rows,
        "nflverse_draft_picks": {"rows": draft_rows},
        "ff_playerids": {"rows": []},
        "udfa_sources": {"sources": udfa_sources or []},
        "manifest": manifest
        or {
            "cfbd_roster": {
                "source_snapshot_id": SNAPSHOT_ID,
                "source_snapshot_id_str": SNAPSHOT_ID_STR,
            }
        },
    }


def _by_source_record(review_queue: list[dict]) -> dict[str, dict]:
    return {row["source_record_id"]: row for row in review_queue}


def test_iterates_drafted_skill_picks_and_silently_excludes_non_cohort_cfbd_rows():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(101, "Alias", "Receiver", team="Ole Miss", position="WR"),
            _cfbd_row(102, "Clean", "Runner", team="Test State", position="RB"),
            _cfbd_row(900, "Undrafted", "Runner", team="Nowhere", position="RB"),
            _cfbd_row(901, "Roster", "Lineman", team="Nowhere", position="OL"),
        ],
        draft_rows=[
            _draft_row(
                "Alias Receiver",
                position="WR",
                college="Mississippi",
                pfr_player_id="AliasRe00",
                pick=11,
            ),
            _draft_row(
                "Clean Runner",
                position="RB",
                college="Test State",
                pfr_player_id="CleanRu00",
                pick=12,
            ),
            _draft_row(
                "Drafted Lineman",
                position="OL",
                college="Nowhere",
                pfr_player_id="LineDr00",
                pick=13,
            ),
        ],
    )

    rows, review_queue = module.build_2025_prospect_fixture(
        frozen_inputs,
        school_aliases={"ole miss": "mississippi"},
    )

    assert review_queue == []
    assert len(rows) == 2
    validated = [NormalizedCollegeProspectRow.model_validate(row) for row in rows]
    by_name = {row.full_name: row for row in validated}
    alias = by_name["Alias Receiver"]

    assert alias.raw_name == "Alias Receiver"
    assert alias.normalized_name == "alias receiver"
    assert alias.position == "WR"
    assert alias.position_group == "WR"
    assert alias.draft_class == 2025
    assert alias.class_year == "3"
    assert alias.current_school == "Ole Miss"
    assert alias.prior_schools == []
    assert alias.cfbd_athlete_id == "101"
    assert alias.source == "cfbd_roster_2025"
    assert alias.source_record_id == "101"
    assert alias.source_snapshot_id == SNAPSHOT_ID_STR
    assert alias.gsis_id is None
    assert alias.pfr_id is None
    assert alias.sleeper_id is None
    assert alias.id_provenance.cfbd_athlete_id == {
        "source": "CFBD /roster v2",
        "source_record_id": "101",
    }
    assert alias.id_provenance.gsis_id is None
    assert alias.id_provenance.pfr_id is None
    assert alias.id_provenance.sleeper_id is None
    dumped_keys = set(alias.model_dump())
    assert {
        "adp",
        "player_adp",
        "draft_grade",
        "market_value",
        "mock_slot",
        "rank",
        "ranking",
    }.isdisjoint(dumped_keys)
    assert {row.cfbd_athlete_id for row in validated} == {"101", "102"}


def test_pick_keyed_review_rows_for_missing_ambiguous_and_unresolved_draft_positions():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(201, "Duplicate", "Receiver", team="Test State", position="WR"),
            _cfbd_row(202, "Duplicate", "Receiver", team="Test State", position="WR"),
            _cfbd_row(203, "Athlete", "Unknown", team="Test State", position="ATH"),
            _cfbd_row(204, "Full", "Back", team="Test State", position="FB"),
        ],
        draft_rows=[
            _draft_row(
                "Missing Prospect",
                position="TE",
                college="Test State",
                pfr_player_id="MissPr00",
                pick=21,
            ),
            _draft_row(
                "Duplicate Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="DupeRe00",
                pick=22,
            ),
            _draft_row(
                "Athlete Unknown",
                position="ATH",
                college="Test State",
                pfr_player_id="AthUn00",
                pick=23,
            ),
            _draft_row(
                "Full Back",
                position="FB",
                college="Test State",
                pfr_player_id="FullBa00",
                pick=24,
            ),
        ],
    )

    rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)

    assert rows == []
    review_by_pick = _by_source_record(review_queue)
    assert set(review_by_pick) == {"MissPr00", "DupeRe00", "AthUn00", "FullBa00"}
    assert review_by_pick["MissPr00"]["reason"] == "draft_truth_match_missing"
    assert review_by_pick["MissPr00"]["raw_name"] == "Missing Prospect"
    assert review_by_pick["MissPr00"]["raw_position"] == "TE"
    assert review_by_pick["DupeRe00"]["reason"] == "draft_truth_match_ambiguous"
    assert review_by_pick["AthUn00"]["reason"] == "unresolved_draft_pick_position"
    assert review_by_pick["FullBa00"]["reason"] == "unresolved_draft_pick_position"
    assert all(row["action"] == "manual_review_required" for row in review_queue)
    assert all("guessed" not in str(row).lower() for row in review_queue)


def test_college_athlete_id_fallback_runs_before_final_missing_classification():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(301, "Fallback", "Receiver", team="CFBD State", position="WR"),
            _cfbd_row(302, "Matched", "Runner", team="Same State", position="RB"),
            _cfbd_row(303, "Uncovered", "Tightend", team="Gap State", position="TE"),
        ],
        draft_rows=[
            _draft_row(
                "Fallback Receiver",
                position="WR",
                college="PFR State",
                college_athlete_id=301,
                pfr_player_id="FallRe00",
                pick=31,
            ),
            _draft_row(
                "Matched Runner",
                position="RB",
                college="Same State",
                pfr_player_id="MatcRu00",
                pick=32,
            ),
            _draft_row(
                "Still Missing",
                position="TE",
                college="Gap State",
                pfr_player_id="StilMi00",
                pick=33,
            ),
        ],
    )

    rows, review_queue = module.build_2025_prospect_fixture(
        frozen_inputs,
        drafted_unmatched_fallback_threshold=0.05,
    )

    by_athlete_id = {row["cfbd_athlete_id"]: row for row in rows}
    review_by_pick = _by_source_record(review_queue)
    assert set(by_athlete_id) == {"301", "302"}
    assert "FallRe00" not in review_by_pick
    assert review_by_pick["StilMi00"]["reason"] == "draft_truth_match_missing"
    assert all(row["gsis_id"] is None for row in rows)
    assert all(row["pfr_id"] is None for row in rows)
    assert all(row["sleeper_id"] is None for row in rows)


def test_top_level_shape_fails_loud_but_malformed_source_records_fail_closed():
    module = _builder_module()

    with pytest.raises(KeyError):
        module.build_2025_prospect_fixture({"cfbd_roster": []})

    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            {
                "firstName": "Broken",
                "lastName": "Receiver",
                "team": "Test State",
                "position": "WR",
                "year": 3,
            },
            _cfbd_row(401, "Clean", "Runner", team="Test State", position="RB"),
        ],
        draft_rows=[
            _draft_row(
                "Broken Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="BrokRe00",
                pick=41,
            ),
            _draft_row(
                "Clean Runner",
                position="RB",
                college="Test State",
                pfr_player_id="CleaRu00",
                pick=42,
            ),
        ],
    )

    try:
        rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)
    except KeyError as exc:
        pytest.fail(
            "malformed individual source records must fail closed into a "
            f"malformed_source_record review row, not raise {exc!r}"
        )

    assert [row["cfbd_athlete_id"] for row in rows] == ["401"]
    review_by_reason = {row["reason"]: row for row in review_queue}
    malformed = review_by_reason["malformed_source_record"]
    assert malformed["raw_name"] == "Broken Receiver"
    assert malformed["raw_position"] == "WR"
    assert malformed["source_record_id"] == "cfbd_roster:<missing>"


def test_malformed_draft_pick_structural_record_fails_closed_not_loud():
    module = _builder_module()
    malformed_pick = _draft_row(
        "Draft Broken",
        position="WR",
        college="Test State",
        pfr_player_id="DrafBr00",
        pick=51,
    )
    del malformed_pick["season"]
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(501, "Draft", "Broken", team="Test State", position="WR"),
        ],
        draft_rows=[malformed_pick],
    )

    try:
        rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)
    except KeyError as exc:
        pytest.fail(
            "malformed drafted-pick records must fail closed into a "
            f"malformed_source_record review row, not raise {exc!r}"
        )

    assert rows == []
    assert len(review_queue) == 1
    malformed = review_queue[0]
    assert malformed["reason"] == "malformed_source_record"
    assert malformed["source_record_id"] == "DrafBr00"
    assert malformed["raw_name"] == "Draft Broken"
    assert malformed["raw_position"] == "WR"


def test_duplicate_draft_picks_claiming_one_cfbd_identity_fail_closed_as_ambiguous():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(601, "Collision", "Receiver", team="Test State", position="WR"),
        ],
        draft_rows=[
            _draft_row(
                "Collision Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="CollRe01",
                pick=61,
            ),
            _draft_row(
                "Collision Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="CollRe02",
                pick=62,
            ),
        ],
    )

    rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)

    assert rows == []
    review_by_pick = _by_source_record(review_queue)
    assert set(review_by_pick) == {"CollRe01", "CollRe02"}
    assert review_by_pick["CollRe01"]["reason"] == "draft_truth_match_ambiguous"
    assert review_by_pick["CollRe02"]["reason"] == "draft_truth_match_ambiguous"
    assert len({row.get("source_record_id") for row in rows}) == len(rows)


def test_non_dict_draft_row_element_fails_closed_not_loud():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(701, "Valid", "Receiver", team="Test State", position="WR"),
        ],
        draft_rows=[123],
    )

    try:
        rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)
    except AttributeError as exc:
        pytest.fail(
            "non-dict drafted-pick records must fail closed into a "
            f"malformed_source_record review row, not raise {exc!r}"
        )

    assert rows == []
    assert len(review_queue) == 1
    malformed = review_queue[0]
    assert malformed["reason"] == "malformed_source_record"
    assert malformed["source_record_id"] == "nflverse_draft_picks:<missing>"


def test_non_dict_cfbd_row_element_fails_closed_not_loud():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[123],
        draft_rows=[
            _draft_row(
                "Valid Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="ValiRe00",
                pick=71,
            ),
        ],
    )

    try:
        rows, review_queue = module.build_2025_prospect_fixture(frozen_inputs)
    except AttributeError as exc:
        pytest.fail(
            "non-dict CFBD roster records must fail closed into a "
            f"malformed_source_record review row, not raise {exc!r}"
        )

    assert rows == []
    review_by_reason = {row["reason"]: row for row in review_queue}
    malformed = review_by_reason["malformed_source_record"]
    assert malformed["source_record_id"] == "cfbd_roster:<missing>"


def test_cfbd_rows_container_wrong_type_fails_loud():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows={"not": "a-list"},
        draft_rows=[
            _draft_row(
                "Valid Receiver",
                position="WR",
                college="Test State",
                pfr_player_id="ValiRe10",
                pick=81,
            ),
        ],
    )

    with pytest.raises(TypeError):
        module.build_2025_prospect_fixture(frozen_inputs)


def test_draft_rows_container_wrong_type_fails_loud():
    module = _builder_module()
    frozen_inputs = _frozen_inputs(
        cfbd_rows=[
            _cfbd_row(801, "Valid", "Receiver", team="Test State", position="WR"),
        ],
        draft_rows={"not": "a-list"},
    )

    with pytest.raises(TypeError):
        module.build_2025_prospect_fixture(frozen_inputs)
