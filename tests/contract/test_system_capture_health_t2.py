"""T2 RED: pure capture-health timeline/density/staleness analyzer.

No disk, no SQLite, no route. These tests construct T1 config models plus
reader-normalized date observations and call the pure analyzer. Most date map
values are plain row counts; T2-only seeds that need pre-reader metadata use
``{"row_count": ..., ...}`` payloads so settings-hash and unclassified-caveat
logic can be pinned before the T3 SQLite reader exists.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def _models():
    import app.api.routes.system_capture_health_models as models

    return models


def _ny(
    year: int,
    month: int,
    day: int,
    hour: int = 13,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))


def _utc(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("UTC"))


def _dates(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    out: list[str] = []
    while current <= stop:
        out.append(current.isoformat())
        current += timedelta(days=1)
    return out


def _counts(
    dates: list[str],
    *,
    count: int = 462,
) -> dict[str, int]:
    return {day: count for day in dates}


def _store(**overrides):
    models = _models()
    body = {
        "store_id": "fc_forward_capture",
        "db_path": "app/data/fc_forward_capture.db",
        "table": "fc_forward_capture_raw",
        "date_column": "snapshot_date",
        "source_filter": "fc_native",
        "expected_settings_hash": "e27351d720e9fcf0",
        "capture_start_date": "2026-06-24",
        "expected_cadence": "daily",
        "scheduled_time_local": "09:00",
        "grace_hours": 3,
        "density_floor_pct": 50,
        "density_baseline_window": 14,
        "warn_consecutive_missing": {"in_season": 1, "off_season": 3},
        "window_risk_contiguous_days": 7,
        "companion_tables": [],
    }
    body.update(overrides)
    return models.CadenceStoreConfig.model_validate(body)


def _season_windows():
    return _models().SeasonWindows.model_validate({"in_season_months": [9, 10, 11, 12, 1]})


def _analyze(
    *,
    store_config,
    date_row_counts,
    now: datetime,
    companion_date_sets: dict[str, set[str]] | None = None,
    timezone: str = "America/New_York",
):
    return _models().analyze_store_health(
        store_config=store_config,
        date_row_counts=date_row_counts,
        companion_date_sets=companion_date_sets or {},
        now=now,
        timezone=timezone,
        season_windows=_season_windows(),
    )


def test_healthy_contiguous_store_reports_ok_and_current_streak() -> None:
    result = _analyze(
        store_config=_store(),
        date_row_counts=_counts(_dates("2026-06-24", "2026-07-02")),
        now=_ny(2026, 7, 2, 13),
    )

    assert result.store_status == "ok"
    assert result.timeline.expected_days == 9
    assert result.timeline.present_days == 9
    assert result.timeline.missing_dates_count == 0
    assert result.timeline.missing_ranges == []
    assert result.timeline.missing_ranges_total == 0
    assert result.timeline.max_contiguous_gap_days == 0
    assert result.timeline.consecutive_days_current == 9
    assert result.staleness.stale is False
    assert result.density.baseline_median_rows == 462
    assert result.decision_supported is False


def test_offseason_missing_facts_degrade_but_warning_waits_for_threshold() -> None:
    rows = _counts(
        [day for day in _dates("2026-06-24", "2026-07-02") if day != "2026-06-27"]
    )

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 2, 13))

    assert result.store_status == "degraded"
    assert result.timeline.missing_dates_count == 1
    assert [gap.model_dump(by_alias=True) for gap in result.timeline.missing_ranges] == [
        {"from": "2026-06-27", "to": "2026-06-27", "days": 1}
    ]
    assert result.timeline.max_contiguous_gap_days == 1
    assert result.flags.warn_missing is False
    assert result.flags.warn_basis == "off_season>=3 consecutive"


def test_three_day_offseason_gap_warns_and_uses_contiguous_gap_not_sum() -> None:
    missing = {"2026-06-27", "2026-06-28", "2026-06-29"}
    rows = _counts([day for day in _dates("2026-06-24", "2026-07-02") if day not in missing])

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 2, 13))

    assert result.timeline.missing_dates_count == 3
    assert result.timeline.missing_ranges_total == 1
    assert result.timeline.max_contiguous_gap_days == 3
    assert result.flags.warn_missing is True


def test_one_day_inseason_gap_warns_with_season_basis_disclosed() -> None:
    rows = _counts(
        [day for day in _dates("2026-09-01", "2026-09-10") if day != "2026-09-05"]
    )

    result = _analyze(
        store_config=_store(capture_start_date="2026-09-01"),
        date_row_counts=rows,
        now=_ny(2026, 9, 10, 13),
    )

    assert result.store_status == "degraded"
    assert result.timeline.missing_dates_count == 1
    assert result.flags.warn_missing is True
    assert result.flags.warn_basis == "in_season>=1 consecutive"


def test_window_risk_and_multiple_ranges_use_full_series_totals() -> None:
    missing = {
        "2026-06-26",
        "2026-06-28",
        "2026-06-29",
        "2026-06-30",
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
        "2026-07-04",
    }
    rows = _counts([day for day in _dates("2026-06-24", "2026-07-07") if day not in missing])

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 7, 13))

    assert result.timeline.missing_dates_count == 8
    assert result.timeline.missing_ranges_total == 2
    assert result.timeline.max_contiguous_gap_days == 7
    assert result.flags.window_risk is True
    assert result.flags.window_risk_basis == ">=7 contiguous missing days"


def test_staleness_grace_boundary_and_utc_local_midnight_are_timezone_aware() -> None:
    rows_through_yesterday = _counts(_dates("2026-06-24", "2026-07-01"))

    before_deadline = _analyze(
        store_config=_store(),
        date_row_counts=rows_through_yesterday,
        now=_ny(2026, 7, 2, 11, 59, 59),
    )
    at_deadline = _analyze(
        store_config=_store(),
        date_row_counts=rows_through_yesterday,
        now=_ny(2026, 7, 2, 12, 0, 0),
    )
    utc_midnight_straddle = _analyze(
        store_config=_store(),
        date_row_counts=_counts(_dates("2026-06-24", "2026-07-02")),
        now=_utc(2026, 7, 3, 2),
    )

    assert before_deadline.timeline.expected_days == 8
    assert before_deadline.staleness.stale is False
    assert at_deadline.timeline.expected_days == 9
    assert at_deadline.staleness.stale is True
    assert utc_midnight_straddle.timeline.expected_days == 9
    assert utc_midnight_straddle.staleness.stale is False


def test_empty_shell_counts_as_missing_using_prior_eligible_baseline_only() -> None:
    rows = {
        "2026-06-24": 462,
        "2026-06-25": 462,
        "2026-06-26": 462,
        "2026-06-27": 2,
        "2026-06-28": 462,
    }

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 6, 28, 13))

    assert result.store_status == "degraded"
    assert result.timeline.missing_dates_count == 1
    assert result.timeline.max_contiguous_gap_days == 1
    assert result.density.baseline_median_rows == 462
    assert result.density.sub_floor_dates == ["2026-06-27"]
    assert [gap.model_dump(by_alias=True) for gap in result.timeline.missing_ranges] == [
        {"from": "2026-06-27", "to": "2026-06-27", "days": 1}
    ]


def test_baseline_insufficient_is_class_a_and_coexists_with_ok() -> None:
    result = _analyze(
        store_config=_store(),
        date_row_counts={"2026-06-24": 2, "2026-06-25": 2},
        now=_ny(2026, 6, 25, 13),
    )

    assert result.store_status == "ok"
    assert result.timeline.missing_dates_count == 0
    assert result.density.sub_floor_dates == []
    assert result.caveats == ["density_baseline_insufficient"]


def test_future_and_malformed_dates_are_excluded_and_degrade_with_caveats() -> None:
    rows = _counts(_dates("2026-06-24", "2026-07-02"))
    rows["2026-07-03"] = 462
    rows["not-a-date"] = 462

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 2, 13))

    assert result.store_status == "degraded"
    assert result.timeline.last_date == "2026-07-02"
    assert result.staleness.last_capture_date == "2026-07-02"
    assert "future_dates_detected" in result.caveats
    assert "invalid_dates_detected" in result.caveats


def test_duplicate_date_counts_as_one_present_day_with_summed_density() -> None:
    result = _analyze(
        store_config=_store(capture_start_date="2026-06-24"),
        date_row_counts={"2026-06-24": 924},
        now=_ny(2026, 6, 24, 13),
    )

    assert result.timeline.expected_days == 1
    assert result.timeline.present_days == 1
    assert result.timeline.missing_dates_count == 0
    assert result.density.sub_floor_dates == []


def test_future_capture_start_is_class_a_pre_capture_window_ok() -> None:
    result = _analyze(
        store_config=_store(capture_start_date="2026-07-10"),
        date_row_counts={},
        now=_ny(2026, 7, 2, 13),
    )

    assert result.store_status == "ok"
    assert result.timeline.expected_days == 0
    assert result.timeline.missing_dates_count == 0
    assert result.caveats == ["pre_capture_window"]


def test_companion_coverage_uses_per_companion_start_date() -> None:
    store = _store(
        companion_tables=[
            {
                "table": "model_forward_prediction_snapshot",
                "date_column": "capture_date",
                "capture_start_date": "2026-06-28",
            }
        ]
    )
    raw_rows = _counts(_dates("2026-06-24", "2026-07-02"))
    real_shape_companions = {
        "model_forward_prediction_snapshot": set(_dates("2026-06-28", "2026-07-02"))
    }
    missing_post_start_companion = {
        "model_forward_prediction_snapshot": {
            day for day in _dates("2026-06-28", "2026-07-02") if day != "2026-06-30"
        }
    }

    real_shape = _analyze(
        store_config=store,
        date_row_counts=raw_rows,
        companion_date_sets=real_shape_companions,
        now=_ny(2026, 7, 2, 13),
    )
    broken_shape = _analyze(
        store_config=store,
        date_row_counts=raw_rows,
        companion_date_sets=missing_post_start_companion,
        now=_ny(2026, 7, 2, 13),
    )

    assert real_shape.store_status == "ok"
    assert "companion_rows_missing" not in real_shape.caveats
    assert broken_shape.store_status == "degraded"
    assert "companion_rows_missing" in broken_shape.caveats


def test_unexpected_settings_hash_metadata_degrades_even_when_counts_are_present() -> None:
    rows = _counts(_dates("2026-06-24", "2026-07-02"))
    rows["2026-06-28"] = {
        "row_count": 462,
        "unexpected_settings_hashes": ["other_hash"],
    }

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 2, 13))

    assert result.timeline.missing_dates_count == 0
    assert result.store_status == "degraded"
    assert "unexpected_settings_hash_detected" in result.caveats


def test_unclassified_caveat_defaults_to_degraded_fail_closed() -> None:
    rows = _counts(_dates("2026-06-24", "2026-07-02"))
    rows["2026-06-28"] = {"row_count": 462, "caveats": ["new_unclassified_caveat"]}

    result = _analyze(store_config=_store(), date_row_counts=rows, now=_ny(2026, 7, 2, 13))

    assert result.store_status == "degraded"
    assert "new_unclassified_caveat" in result.caveats


def test_missing_ranges_are_display_capped_but_totals_remain_full_series() -> None:
    all_days = _dates("2026-01-01", "2026-02-28")
    missing = set(all_days[1::2])
    rows = _counts([day for day in all_days if day not in missing])

    result = _analyze(
        store_config=_store(capture_start_date="2026-01-01"),
        date_row_counts=rows,
        now=_ny(2026, 2, 28, 13),
    )

    assert result.timeline.missing_dates_count == len(missing)
    assert result.timeline.missing_ranges_total == len(missing)
    assert len(result.timeline.missing_ranges) == 20
    assert result.timeline.max_contiguous_gap_days == 1
    assert "missing_ranges_truncated" in result.caveats
