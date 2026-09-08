"""DG-190 — the workspace snapshot archive: an exact, verifiable copy of what David was looking at.

The forecasts on screen today and the market price they were compared against are both gone tomorrow. This store
keeps them, byte for byte, so a later evaluation can say what was known and when. It grades nothing and claims
nothing: every receipt carries ``evaluation_status: "ungraded"``, and saving September 6 forecasts on September 8 is
recorded as exactly that.

Three properties carry the weight, and each has its own tests below:

* **Identity is content.** The snapshot id is a hash of the schema version and every archived byte, and excludes the
  save time and the capture code. Saving the same sources twice converges on one archive with its ORIGINAL saved
  time, rather than minting a second observation that a later count would double.
* **The archive verifies itself.** Every file's hash is recorded beside it, and list, read and re-save all check the
  bytes against that record. A corrupted archive fails loudly instead of quietly returning a plausible receipt.
* **A count is derived, never asserted.** Populations are counted from the rows themselves and cross-checked against
  the coverage block that summarises them. Zero is a count; missing is not; a boolean is not a number.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dynasty_genius.capture.workspace_snapshot_store import (
    ARTIFACT_NAMES,
    SnapshotBundle,
    WorkspaceSnapshotError,
    list_snapshots,
    read_snapshot,
    save_snapshot,
)

SAVED_AT = datetime(2026, 9, 8, 1, 30, 0, tzinfo=timezone.utc)
CODE_SHA = "a85f726f23cad759d17877ce2762f93b30d9294f"
YEARS = [2026, 2027, 2028, 2029, 2030]
REPORT_RUN = "20260906T214512Z"
CATALOG_RUN = "20260907T013635Z"
REPORT_SHA = "19e032a4067dff1759199a84720c0f879bb61f792fd3b2703808b55485a7af37"
MARKET_SHA = "05bce6dd9d76198ecca2a2f0f1493b4e99f02da1f4dd9a5c1b5b85ec8e01a339"
LEAGUE_SHA = "ece82e24a66d50882345733971a8e1c66d1c0bae020496c2f48a8ff8a8ad8a35"
# Root supplies this file; the store archives it unchanged. Declaring baselines and populations BEFORE any outcome
# is read is the whole point of keeping it beside the forecast.
EVALUATION_PLAN = {
    "schema_version": "workspace_evaluation_plan.v1",
    "target": "championship-window points, nflverse default PPR",
    "eligible_population": "every player in the verified report and catalog",
    "baselines": ["market rank on the same day", "no opinion"],
    "horizon_policy": "each season graded when it completes",
}


def canonical(doc: dict) -> bytes:
    return json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


# --- fixtures shaped like the real payloads --------------------------------------------------------


def ranks_payload(*, model=6, market_only=2, paired=4, roster=3) -> dict:
    """Rows shaped like the real market-ranks payload, so the counts can actually be derived from them.

    The union is model rows plus market-only rows. Within the model rows, the first ``paired`` also carry a market
    price and both ranks, and the first ``roster`` are David's. The coverage block below is what the store must
    CHECK against these rows, never copy.
    """
    rows = []
    for index in range(model):
        row = {
            "sleeper_id": f"p{index}",
            "name": f"Player {index}",
            "position": "QB",
            "on_roster": index < roster,
            "model_value": 100.0 - index,
            "market_value": None,
            "our_rank": None,
            "market_rank": None,
        }
        if index < paired:
            row["market_value"] = 5000 - index
            row["our_rank"] = {"start": index + 1, "end": index + 1, "total": paired}
            row["market_rank"] = {"start": index + 1, "end": index + 1, "total": paired}
        rows.append(row)
    for index in range(market_only):
        rows.append(
            {
                "sleeper_id": f"m{index}",
                "name": f"Priced {index}",
                "position": "WR",
                "on_roster": False,
                "model_value": None,
                "market_value": 400 - index,
                "our_rank": None,
                "market_rank": None,
            }
        )
    return {
        "status": "available",
        "source": {
            "report_run": REPORT_RUN,
            "report_sha256": REPORT_SHA,
            "market_sha256": MARKET_SHA,
            "league_sha256": LEAGUE_SHA,
            "forecast_date": "2026-09-06",
            "market_as_of": "2026-09-06T13:00:02.542329+00:00",
            "ownership_as_of": "2026-09-06T13:00:52.635970+00:00",
        },
        "basis": {
            "years": list(YEARS),
            "season_weights": [1, 1, 1, 1, 1],
            "summary": "Five seasons added with equal weight.",
            "market_proxy_note": "A proxy for the wider market.",
            "scoring_note": "Not your league's exact scoring.",
        },
        "coverage": {
            "model_players": model,
            "market_players": paired + market_only,
            "market_picks": 24,
            "common_players": paired,
            "total_players": model + market_only,
            "roster_players": roster,
            "roster_common_players": min(roster, paired),
        },
        "rows": rows,
    }


def comparison_payload(
    *, roster=3, available=5, with_forecasts=4, starting=1, other=2, catalog_content_sha=None
) -> dict:
    def player(index: int, *, population: str, priced: bool, estimate: bool) -> dict:
        return {
            "sleeper_id": f"a{index}",
            "name": f"Compared {index}",
            "position": "WR",
            "team": "KC",
            "population": population,
            "status": "active",
            "now_points": 120.5 if priced else None,
            "future_points": 380.25 if priced else None,
            "seasons": [{"season": year, "points": 1.0, "estimate_class": None} for year in YEARS],
            "starting_estimate": estimate,
            "missing_reason": None if priced else "no forecast from the selected producers",
            "evidence_note": "note",
        }

    default_rows = [
        player(index, population="default", priced=index < with_forecasts, estimate=index < starting)
        for index in range(available)
    ]
    # a separate population that must never be counted as available
    other_rows = [player(900 + index, population="cut", priced=True, estimate=False) for index in range(other)]
    source = {
        "report_run": REPORT_RUN,
        "catalog_run": CATALOG_RUN,
        "report_sha256": REPORT_SHA,
        "ownership_as_of": "2026-09-06T13:00:52.635970+00:00",
        "nfl_status_as_of": "Sun, 06 Sep 2026 11:28:11 GMT",
    }
    if catalog_content_sha is not None:
        source["catalog_content_sha256"] = catalog_content_sha
    roster_rows = [
        {**player(index, population="owned", priced=True, estimate=False), "sleeper_id": f"p{index}"}
        for index in range(roster)
    ]
    return {
        "source": source,
        "forecast_years": list(YEARS),
        "future_years": YEARS[1:],
        "scoring_note": "Not your league's exact scoring.",
        "available": default_rows + other_rows,
        "roster": roster_rows,
    }


def artifacts(**over) -> dict[str, bytes]:
    base = {
        "source-manifest.json": canonical({"schema_version": 1, "report_run": REPORT_RUN}),
        "report.json": canonical({"run": REPORT_RUN, "forecast_date": "2026-09-06"}),
        "market.json": canonical({"snapshot_date": "2026-09-06", "entries": [{"sleeper_id": f"pick-{i}", "position": "PICK"} for i in range(24)]}),
        "league.json": canonical({"captured_at": "2026-09-06T13:00:52.635970+00:00"}),
        "catalog.json": canonical({"run": CATALOG_RUN, "source_report_run": REPORT_RUN, "rows_detail": []}),
        "catalog-companion.json": canonical({"run": CATALOG_RUN, "outputs_sha256": {"catalog.json": "f" * 64}}),
        "evaluation-plan.json": canonical(EVALUATION_PLAN),
    }
    base.update(over)
    return base


def catalog_content_hash(art: dict[str, bytes]) -> str:
    return hashlib.sha256(canonical(json.loads(art["catalog.json"]))).hexdigest()


def bundle(**over) -> SnapshotBundle:
    art = over.pop("artifacts", None) or artifacts()
    ranks = over.pop("ranks", None) or ranks_payload()
    comparison = over.pop("comparison", None) or comparison_payload()
    assert not over, over
    return SnapshotBundle(artifacts=art, ranks=ranks, comparison=comparison)


def save(root: Path, subject: SnapshotBundle | None = None, *, at=SAVED_AT, code=CODE_SHA) -> dict:
    return save_snapshot(root, subject or bundle(), captured_at=at, code_sha=code)


def refuses(*needles, root: Path, **kwargs):
    with pytest.raises(WorkspaceSnapshotError) as error:
        save(root, **kwargs)
    for needle in needles:
        assert needle in str(error.value), (needle, str(error.value))


# --- identity is content ----------------------------------------------------------------------------


def test_the_snapshot_is_identified_by_its_content_and_saving_it_twice_converges(tmp_path) -> None:
    first = save(tmp_path)
    assert first["created"] is True
    identifier = first["snapshot"]["snapshot_id"]
    assert len(identifier) == 64 and identifier == identifier.lower()
    assert set(identifier) <= set("0123456789abcdef")

    later = save(tmp_path, at=SAVED_AT + timedelta(days=1), code="b" * 40)
    assert later["created"] is False
    assert later["snapshot"]["snapshot_id"] == identifier
    # the archive keeps when it was FIRST saved; a second look is not a second observation
    assert later["snapshot"]["saved_at"] == first["snapshot"]["saved_at"]
    assert later["snapshot"]["capture_code_sha"] == CODE_SHA
    assert [entry["snapshot_id"] for entry in list_snapshots(tmp_path)] == [identifier]


def test_the_identity_ignores_when_it_was_saved_and_which_code_saved_it(tmp_path) -> None:
    one = save(tmp_path)["snapshot"]["snapshot_id"]
    two = save(tmp_path / "other", at=SAVED_AT + timedelta(days=30), code="unknown")["snapshot"]["snapshot_id"]
    assert one == two


@pytest.mark.parametrize("artifact", sorted(ARTIFACT_NAMES))
def test_changing_any_archived_byte_changes_the_identity(tmp_path, artifact) -> None:
    baseline = save(tmp_path)["snapshot"]["snapshot_id"]
    changed = artifacts(**{artifact: canonical({**json.loads(artifacts()[artifact]), "changed": artifact})})
    other = save(tmp_path, bundle(artifacts=changed))["snapshot"]["snapshot_id"]
    assert other != baseline
    assert {entry["snapshot_id"] for entry in list_snapshots(tmp_path)} == {baseline, other}


def test_two_different_snapshots_coexist_and_list_newest_first(tmp_path) -> None:
    first = save(tmp_path)["snapshot"]
    second = save(
        tmp_path,
        bundle(ranks=ranks_payload(model=7)),
        at=SAVED_AT + timedelta(hours=1),
    )["snapshot"]
    listed = list_snapshots(tmp_path)
    assert [entry["snapshot_id"] for entry in listed] == [second["snapshot_id"], first["snapshot_id"]]
    assert all(set(entry) == set(first) for entry in listed)          # receipts only, no payloads


# --- the receipt --------------------------------------------------------------------------------------


def test_the_receipt_is_exactly_the_agreed_shape(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    assert set(receipt) == {
        "snapshot_id", "saved_at", "forecast_date", "report_generated_at", "catalog_generated_at",
        "market_as_of", "ownership_as_of", "years", "source", "counts", "evaluation_plan",
        "capture_code_sha", "evaluation_status",
    }
    assert receipt["saved_at"] == "2026-09-08T01:30:00+00:00"
    assert receipt["forecast_date"] == "2026-09-06"
    assert receipt["years"] == YEARS and all(isinstance(year, int) for year in receipt["years"])
    assert receipt["evaluation_status"] == "ungraded"
    assert receipt["capture_code_sha"] == CODE_SHA
    assert set(receipt["source"]) == {
        "report_run", "report_sha256", "market_sha256", "league_sha256", "catalog_run", "catalog_content_sha256",
    }
    assert all(isinstance(value, str) for value in receipt["source"].values())
    assert receipt["source"]["catalog_run"] == CATALOG_RUN
    assert set(receipt["counts"]) == {
        "model", "market", "market_picks", "paired", "roster", "available", "available_total",
        "available_with_forecasts", "available_without_forecasts", "starting_estimates",
    }
    assert receipt["evaluation_plan"] == EVALUATION_PLAN
    assert all(isinstance(value, int) and not isinstance(value, bool) for value in receipt["counts"].values())


def test_the_counts_are_derived_from_the_rows_for_todays_frozen_populations(tmp_path) -> None:
    """The shape David is looking at now: 825 forecast, 399 priced, 388 in both, his 27, and 433 available of which
    360 carry numbers, 73 do not and 7 are starting estimates."""
    subject = bundle(
        ranks=ranks_payload(model=825, market_only=11, paired=388, roster=27),
        comparison=comparison_payload(roster=27, available=433, with_forecasts=360, starting=7, other=77),
    )
    counts = save(tmp_path, subject)["snapshot"]["counts"]
    assert counts == {
        "model": 825, "market": 399, "market_picks": 24, "paired": 388, "roster": 27,
        "available": 433, "available_total": 510,
        "available_with_forecasts": 360, "available_without_forecasts": 73, "starting_estimates": 7,
    }
    # the whole catalog is 510 rows; the relevant pool is 433. One must never be read as the other.
    assert counts["available_total"] != counts["available"]
    assert counts["market_picks"] == 24 and counts["market"] == 399      # picks are not players


def test_the_counts_are_not_wired_to_todays_numbers(tmp_path) -> None:
    subject = bundle(
        ranks=ranks_payload(model=11, market_only=4, paired=5, roster=2),
        comparison=comparison_payload(roster=2, available=6, with_forecasts=6, starting=0),
    )
    counts = save(tmp_path, subject)["snapshot"]["counts"]
    assert counts == {
        "model": 11, "market": 9, "market_picks": 24, "paired": 5, "roster": 2,
        "available": 6, "available_total": 8,
        "available_with_forecasts": 6, "available_without_forecasts": 0, "starting_estimates": 0,
    }
    # zero is a count that was measured, not a value that went missing
    assert counts["starting_estimates"] == 0 and counts["available_without_forecasts"] == 0


def test_only_the_default_population_is_counted_as_available(tmp_path) -> None:
    """The comparison carries cut and retired players too. They are archived, and they are not availability."""
    receipt = save(tmp_path)["snapshot"]
    assert receipt["counts"]["available"] == 5           # the two 'cut' rows are excluded
    archived = read_snapshot(tmp_path, receipt["snapshot_id"])
    assert len(archived["comparison"]["available"]) == 7  # but nothing was dropped from the archive


def test_the_catalog_content_hash_is_derived_from_the_archived_catalog(tmp_path) -> None:
    art = artifacts()
    receipt = save(tmp_path, bundle(artifacts=art))["snapshot"]
    assert receipt["source"]["catalog_content_sha256"] == catalog_content_hash(art)


def test_a_comparison_that_disagrees_about_the_catalog_content_is_refused(tmp_path) -> None:
    art = artifacts()
    agreeing = comparison_payload(catalog_content_sha=catalog_content_hash(art))
    assert save(tmp_path, bundle(artifacts=art, comparison=agreeing))["created"] is True
    refuses(
        "catalog_content_sha256", root=tmp_path / "other",
        subject=bundle(artifacts=art, comparison=comparison_payload(catalog_content_sha="0" * 64)),
    )


# --- refusals ------------------------------------------------------------------------------------------


def test_the_six_raw_artifacts_must_all_be_present_as_bytes(tmp_path) -> None:
    missing = artifacts()
    del missing["market.json"]
    refuses("market.json", root=tmp_path, subject=bundle(artifacts=missing))
    extra = artifacts()
    extra["notes.txt"] = b"hello"
    refuses("notes.txt", root=tmp_path, subject=bundle(artifacts=extra))
    refuses("report.json", "bytes", root=tmp_path, subject=bundle(artifacts=artifacts(**{"report.json": "text"})))
    refuses("league.json", root=tmp_path, subject=bundle(artifacts=artifacts(**{"league.json": b""})))


def test_an_archived_artifact_must_be_readable_json(tmp_path) -> None:
    refuses("catalog.json", "JSON", root=tmp_path, subject=bundle(artifacts=artifacts(**{"catalog.json": b"{not json"})))


def test_a_non_finite_number_is_refused_rather_than_archived(tmp_path) -> None:
    broken = comparison_payload()
    broken["available"][0]["now_points"] = float("inf")
    refuses("finite", root=tmp_path, subject=bundle(comparison=broken))
    broken_ranks = ranks_payload()
    broken_ranks["rows"][0]["our_rank"]["start"] = float("nan")
    refuses("finite", root=tmp_path, subject=bundle(ranks=broken_ranks))


@pytest.mark.parametrize(
    "field,value",
    [("report_run", "20260101T000000Z"), ("report_sha256", "0" * 64), ("ownership_as_of", "2026-01-01T00:00:00+00:00")],
)
def test_the_two_payloads_must_describe_the_same_sources(tmp_path, field, value) -> None:
    other = comparison_payload()
    other["source"][field] = value
    refuses(field, root=tmp_path, subject=bundle(comparison=other))


def test_the_two_payloads_must_describe_the_same_five_years(tmp_path) -> None:
    other = comparison_payload()
    other["forecast_years"] = [2025, 2026, 2027, 2028, 2029]
    refuses("years", root=tmp_path, subject=bundle(comparison=other))


def test_a_coverage_count_that_disagrees_with_its_own_rows_is_refused(tmp_path) -> None:
    inflated = ranks_payload()
    inflated["coverage"]["total_players"] = 99
    refuses("total_players", root=tmp_path, subject=bundle(ranks=inflated))
    mismatched = ranks_payload()
    mismatched["coverage"]["roster_players"] = 9
    refuses("roster", root=tmp_path, subject=bundle(ranks=mismatched))


def test_a_duplicate_player_is_refused_in_every_collection(tmp_path) -> None:
    duplicated_rows = ranks_payload()
    duplicated_rows["rows"].append(copy.deepcopy(duplicated_rows["rows"][0]))
    duplicated_rows["coverage"]["model_players"] = len(duplicated_rows["rows"])
    duplicated_rows["coverage"]["total_players"] = len(duplicated_rows["rows"])
    refuses("duplicate", root=tmp_path, subject=bundle(ranks=duplicated_rows))

    duplicated_available = comparison_payload()
    duplicated_available["available"].append(copy.deepcopy(duplicated_available["available"][0]))
    refuses("duplicate", root=tmp_path, subject=bundle(comparison=duplicated_available))

    duplicated_roster = comparison_payload()
    duplicated_roster["roster"].append(copy.deepcopy(duplicated_roster["roster"][0]))
    refuses("duplicate", root=tmp_path, subject=bundle(comparison=duplicated_roster))


def test_a_count_that_is_a_boolean_is_not_a_number(tmp_path) -> None:
    lying = ranks_payload()
    lying["coverage"]["market_players"] = True
    refuses("market_players", root=tmp_path, subject=bundle(ranks=lying))


def test_a_source_cannot_be_dated_after_the_moment_it_was_saved(tmp_path) -> None:
    refuses("saved", root=tmp_path, at=datetime(2026, 9, 5, tzinfo=timezone.utc))
    late = ranks_payload()
    late["source"]["market_as_of"] = "2026-09-09T13:00:00+00:00"
    refuses("saved", root=tmp_path, subject=bundle(ranks=late))


def test_a_malformed_date_is_refused_rather_than_guessed(tmp_path) -> None:
    broken = ranks_payload()
    broken["source"]["forecast_date"] = "the sixth"
    refuses("forecast_date", root=tmp_path, subject=bundle(ranks=broken))


def test_the_save_time_must_be_an_explicit_utc_instant(tmp_path) -> None:
    with pytest.raises(WorkspaceSnapshotError, match="captured_at"):
        save_snapshot(tmp_path, bundle(), captured_at=datetime(2026, 9, 8, 1, 30), code_sha=CODE_SHA)


def test_the_capture_code_is_a_commit_or_literally_unknown(tmp_path) -> None:
    assert save(tmp_path, code="unknown")["snapshot"]["capture_code_sha"] == "unknown"
    with pytest.raises(WorkspaceSnapshotError, match="code_sha"):
        save(tmp_path / "a", code="engine_b_v2_qb")            # never a model version
    with pytest.raises(WorkspaceSnapshotError, match="code_sha"):
        save(tmp_path / "b", code="")


# --- the archive on disk ---------------------------------------------------------------------------------


def test_an_absent_archive_lists_nothing_and_is_not_created_by_looking(tmp_path) -> None:
    absent = tmp_path / "never-made"
    assert list_snapshots(absent) == []
    assert not absent.exists()


def test_reading_returns_the_validated_payloads_and_the_receipt(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    archived = read_snapshot(tmp_path, receipt["snapshot_id"])
    assert set(archived) == {"snapshot", "ranks", "comparison"}
    assert archived["snapshot"] == receipt
    assert archived["ranks"] == ranks_payload()
    assert archived["comparison"] == comparison_payload()


def test_an_unknown_snapshot_is_absent_and_a_malformed_id_is_refused(tmp_path) -> None:
    save(tmp_path)
    with pytest.raises(FileNotFoundError):
        read_snapshot(tmp_path, "a" * 64)
    for unsafe in ("../escape", "not-hex", "A" * 64, "", "abc"):
        with pytest.raises(WorkspaceSnapshotError):
            read_snapshot(tmp_path, unsafe)


def test_a_corrupted_archive_fails_loudly_on_read_list_and_resave(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    archived_file = tmp_path / receipt["snapshot_id"] / "report.json"
    archived_file.write_bytes(canonical({"run": "tampered"}))
    with pytest.raises(WorkspaceSnapshotError, match="report.json"):
        read_snapshot(tmp_path, receipt["snapshot_id"])
    with pytest.raises(WorkspaceSnapshotError):
        list_snapshots(tmp_path)
    with pytest.raises(WorkspaceSnapshotError):
        save(tmp_path)                                   # the duplicate path must verify, not assume


def test_a_snapshot_whose_own_manifest_was_edited_is_refused(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    manifest_path = tmp_path / receipt["snapshot_id"] / "snapshot.json"
    doc = json.loads(manifest_path.read_text())
    doc["receipt"]["counts"]["available"] = 999
    manifest_path.write_text(json.dumps(doc))
    with pytest.raises(WorkspaceSnapshotError):
        read_snapshot(tmp_path, receipt["snapshot_id"])


def test_a_successful_save_leaves_no_working_directory_behind(tmp_path) -> None:
    save(tmp_path)
    save(tmp_path)
    assert [entry.name for entry in tmp_path.iterdir() if entry.name.startswith(".tmp")] == []


def test_a_failure_while_publishing_cleans_up_after_itself(tmp_path, monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", explode, raising=False)
    monkeypatch.setattr(os, "rename", explode)
    with pytest.raises(OSError):
        save(tmp_path)
    assert [entry.name for entry in tmp_path.iterdir() if entry.name.startswith(".tmp")] == []


# --- the archive must be a private, real place -------------------------------------------------------------


def test_a_symlinked_archive_root_is_refused(tmp_path) -> None:
    """Exactly how app/cache silently became the shared trunk cache: a link where a directory was expected."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        save(link)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        list_snapshots(link)


def test_an_archive_root_inside_the_shared_data_stores_is_refused(tmp_path) -> None:
    shared = tmp_path / "app" / "data" / "archive"
    shared.mkdir(parents=True)
    with pytest.raises(WorkspaceSnapshotError, match="shared"):
        save(shared)
    cache = tmp_path / "app" / "cache" / "archive"
    cache.mkdir(parents=True)
    with pytest.raises(WorkspaceSnapshotError, match="shared"):
        save(cache)


# --- root's 2026-09-08 amendments -----------------------------------------------------------------------


def test_the_evaluation_plan_is_archived_beside_the_forecast_and_summarised_in_the_receipt(tmp_path) -> None:
    """Declaring the target, the eligible population and the baselines BEFORE any outcome is read is what stops a
    later evaluation from choosing the comparison that flatters the result."""
    receipt = save(tmp_path)["snapshot"]
    assert receipt["evaluation_plan"] == EVALUATION_PLAN
    archived = read_snapshot(tmp_path, receipt["snapshot_id"])
    assert json.loads((tmp_path / receipt["snapshot_id"] / "evaluation-plan.json").read_bytes()) == EVALUATION_PLAN
    assert archived["snapshot"]["evaluation_plan"]["baselines"] == ["market rank on the same day", "no opinion"]


def test_a_snapshot_without_a_declared_plan_is_refused(tmp_path) -> None:
    refuses("evaluation plan", root=tmp_path, subject=bundle(artifacts=artifacts(**{"evaluation-plan.json": canonical({})})))


def test_the_producers_own_creation_times_are_recorded_and_kept_separate_from_the_forecast_date(tmp_path) -> None:
    stamped = artifacts(
        **{
            "report.json": canonical(
                {"run": REPORT_RUN, "provenance": {"generated_at": "2026-09-06T21:45:12+00:00"}}
            ),
            "catalog.json": canonical(
                {"run": CATALOG_RUN, "source_report_run": REPORT_RUN,
                 "provenance": {"generated_at": "2026-09-07T01:36:35+00:00"}},
            ),
        }
    )
    receipt = save(tmp_path, bundle(artifacts=stamped))["snapshot"]
    assert receipt["report_generated_at"] == "2026-09-06T21:45:12+00:00"
    assert receipt["catalog_generated_at"] == "2026-09-07T01:36:35+00:00"
    assert receipt["forecast_date"] == "2026-09-06"        # the day it is FOR, not the day it was made


def test_a_missing_creation_time_stays_missing_rather_than_borrowing_the_forecast_date(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    assert receipt["report_generated_at"] is None and receipt["catalog_generated_at"] is None


def test_a_source_generated_after_the_save_is_refused(tmp_path) -> None:
    impossible = artifacts(
        **{"report.json": canonical({"run": REPORT_RUN, "provenance": {"generated_at": "2026-09-09T00:00:00+00:00"}})}
    )
    refuses("report.json", "saved", root=tmp_path, subject=bundle(artifacts=impossible))


def test_the_same_forecast_saved_under_a_changed_rendering_is_not_a_second_prediction(tmp_path) -> None:
    """The id is the whole saved reading, so a presentation change makes a new archive entry. The SOURCE TUPLE is
    what identifies the forecast underneath, and it is unchanged — two entries here are one forecast, not two."""
    first = save(tmp_path)["snapshot"]
    reworded = ranks_payload()
    reworded["basis"]["summary"] = "Reworded for the screen; the numbers are untouched."
    second = save(tmp_path, bundle(ranks=reworded), at=SAVED_AT + timedelta(minutes=1))["snapshot"]
    assert second["snapshot_id"] != first["snapshot_id"]
    assert second["source"] == first["source"]
    assert len(list_snapshots(tmp_path)) == 2
    assert first["saved_at"] != second["saved_at"]        # and the original rendering is never rewritten


# --- the amended path rule ---------------------------------------------------------------------------------


def test_the_platforms_own_aliases_are_usable_but_a_user_made_link_is_not(tmp_path) -> None:
    """Refusing every symlink would refuse every temporary directory on this machine, because /var and /tmp are
    themselves aliases. Refusing none would let an archive be pointed at somebody else's store."""
    assert list_snapshots(Path("/tmp") / "dg190-archive-that-does-not-exist") == []

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        save(parent_link / "archive")


def test_a_snapshot_directory_replaced_by_a_link_is_refused(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    real = tmp_path / receipt["snapshot_id"]
    moved = tmp_path / "moved"
    real.rename(moved)
    real.symlink_to(moved, target_is_directory=True)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        read_snapshot(tmp_path, receipt["snapshot_id"])


def test_the_alias_exception_is_the_exact_system_path_and_nothing_that_merely_looks_like_it(tmp_path) -> None:
    """Root asked me to confirm this: /tmp and /var are exempt because the platform makes them links, not because
    of their names. A link called 'tmp' anywhere else is an ordinary link and is refused."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    lookalike = tmp_path / "tmp"
    lookalike.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        save(lookalike / "archive")
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        list_snapshots(lookalike)


def test_a_symlink_anywhere_in_the_middle_of_the_path_is_refused(tmp_path) -> None:
    real = tmp_path / "real" / "deep"
    real.mkdir(parents=True)
    middle = tmp_path / "middle"
    middle.symlink_to(tmp_path / "real", target_is_directory=True)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        save(middle / "deep" / "archive")


def test_a_real_path_with_no_links_of_its_own_is_accepted(tmp_path) -> None:
    """The counterpart to the refusals above: an ordinary private directory works, including under the platform's
    own /var alias that every pytest temporary directory sits beneath."""
    nested = tmp_path / "one" / "two" / "archive"
    receipt = save(nested)["snapshot"]
    assert list_snapshots(nested)[0]["snapshot_id"] == receipt["snapshot_id"]


# --- root's independent store review, 2026-09-08: five corrections ------------------------------------


def test_the_population_counts_are_derived_from_the_rows_and_not_copied_from_the_coverage_block(tmp_path) -> None:
    """The defect this replaces: model, market and paired were taken straight from coverage, so the "cross-check"
    could not fail. Each is now counted from the rows, and a coverage block that disagrees is refused by name."""
    for field, value in (("model_players", 99), ("market_players", 99), ("common_players", 99)):
        broken = ranks_payload()
        broken["coverage"][field] = value
        refuses(field, root=tmp_path / field, subject=bundle(ranks=broken))

    # and the derivation follows the rows when the rows change
    counts = save(
        tmp_path / "derived", bundle(ranks=ranks_payload(model=9, market_only=3, paired=4, roster=2),
                                     comparison=comparison_payload(roster=2))
    )["snapshot"]["counts"]
    assert counts["model"] == 9 and counts["market"] == 7 and counts["paired"] == 4 and counts["roster"] == 2


def test_the_two_sources_must_name_the_same_roster(tmp_path) -> None:
    mismatched = comparison_payload(roster=3)
    mismatched["roster"][0]["sleeper_id"] = "somebody-else"
    refuses("roster", root=tmp_path, subject=bundle(comparison=mismatched))


def test_a_player_cannot_be_both_on_the_roster_and_available(tmp_path) -> None:
    overlapping = comparison_payload(roster=3)
    overlapping["available"][0]["sleeper_id"] = "p0"          # already David's
    refuses("p0", root=tmp_path, subject=bundle(comparison=overlapping))


@pytest.mark.parametrize(
    "raw",
    [b'{"value": NaN}', b'{"value": Infinity}', b'{"value": -Infinity}', b'{"value": 1e999}'],
)
def test_a_raw_artifact_carrying_a_non_finite_number_is_refused(tmp_path, raw) -> None:
    """``json.loads`` accepts NaN and Infinity by default, and 1e999 overflows silently to infinity. An archive that
    swallowed one would look complete and hold a number that is not a measurement."""
    refuses("finite", root=tmp_path, subject=bundle(artifacts=artifacts(**{"report.json": raw})))


def test_a_raw_artifact_with_duplicate_keys_is_refused_rather_than_silently_resolved(tmp_path) -> None:
    refuses(
        "duplicate", root=tmp_path,
        subject=bundle(artifacts=artifacts(**{"market.json": b'{"snapshot_date": "2026-09-06", "snapshot_date": "2026-09-07"}'})),
    )


def test_a_raw_artifact_that_is_not_an_object_is_refused(tmp_path) -> None:
    refuses("object", root=tmp_path, subject=bundle(artifacts=artifacts(**{"league.json": b"[1, 2, 3]"})))


def test_a_named_snapshot_that_is_not_a_directory_is_reported_rather_than_skipped(tmp_path) -> None:
    """A snapshot must never quietly disappear from the list because something replaced it."""
    save(tmp_path)
    impostor = tmp_path / ("b" * 64)
    impostor.write_text("not a snapshot")
    with pytest.raises(WorkspaceSnapshotError):
        list_snapshots(tmp_path)
    impostor.unlink()
    broken_link = tmp_path / ("c" * 64)
    broken_link.symlink_to(tmp_path / "nowhere")
    with pytest.raises(WorkspaceSnapshotError):
        list_snapshots(tmp_path)


def test_an_archived_member_file_replaced_by_a_link_is_refused(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    directory = tmp_path / receipt["snapshot_id"]
    outside = tmp_path / "outside.json"
    outside.write_bytes((directory / "report.json").read_bytes())
    (directory / "report.json").unlink()
    (directory / "report.json").symlink_to(outside)
    with pytest.raises(WorkspaceSnapshotError, match="symlink"):
        read_snapshot(tmp_path, receipt["snapshot_id"])


def test_a_manifest_that_is_not_an_object_is_refused_rather_than_crashing(tmp_path) -> None:
    receipt = save(tmp_path)["snapshot"]
    (tmp_path / receipt["snapshot_id"] / "snapshot.json").write_bytes(b"[]")
    with pytest.raises(WorkspaceSnapshotError):
        read_snapshot(tmp_path, receipt["snapshot_id"])


def test_every_stated_timestamp_must_precede_the_save(tmp_path) -> None:
    late_plan = artifacts(
        **{"evaluation-plan.json": canonical({**EVALUATION_PLAN, "declared_at": "2026-09-09T00:00:00+00:00"})}
    )
    refuses("declared_at", "saved", root=tmp_path / "plan", subject=bundle(artifacts=late_plan))

    late_status = comparison_payload()
    late_status["source"]["nfl_status_as_of"] = "2026-09-09T00:00:00+00:00"
    refuses("nfl_status_as_of", "saved", root=tmp_path / "status", subject=bundle(comparison=late_status))

    # a plan that declares its date honestly is accepted and archived
    good_plan = artifacts(
        **{"evaluation-plan.json": canonical({**EVALUATION_PLAN, "declared_at": "2026-09-07T00:00:00+00:00"})}
    )
    saved = save(tmp_path / "good", bundle(artifacts=good_plan))["snapshot"]
    assert saved["evaluation_plan"]["declared_at"] == "2026-09-07T00:00:00+00:00"


def test_market_pick_count_must_match_archived_raw_entries(tmp_path):
    subject = bundle()
    subject.ranks['coverage']['market_picks'] = 23
    with pytest.raises(WorkspaceSnapshotError, match='market_picks'):
        save(tmp_path, subject)
