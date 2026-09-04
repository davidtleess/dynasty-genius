"""DG-154 RED: the season basis cannot change unattended.

`run_daily_chain.py` invokes `run_feature_refresh.py` with NO `--season-end`, so the refresh
derives `season_end = int(player_stats["season"].max())` from the live feed and sets
`inference_season = season_end`. The day nflverse publishes the first 2026 `player_stats`
row — roughly 2026-09-15 — the basis flips 2025 -> 2026 with nobody in the loop, and
`feature_assembly` then drops the COMPLETED 2025 rows in favour of a 2026 partition that is
empty until players reach four games. `ppg_t` silently stops meaning "a full season" and
starts meaning "the four games he has played so far" — on the feature carrying the largest
coefficient at every position.

**This guard decides nothing.** It does not pick 2025, 2026, or a threshold; that is David's
ruling. It only makes the change require one. Today, with the feed's max season equal to the
season already published, it is a no-op and the refresh proceeds exactly as before.

Re-derived here before building (2018-2025, `ff_opportunity` weekly, local, no network,
2,658 player-seasons with >= 8 games): a four-game mean carries 77% of a full season's
variance pooled (23% lost) and 65% at QB (35% lost); as pure sampling precision the loss is
69-73% at EVERY position, so that framing is not a QB finding. Today's inference partition is
exactly 505 rows; after a rebase it refills to about 199 players by week 4, 282 by week 6 and
446 by week 18 (one consistent week window throughout). The like-for-like end state is the
runtime table's own completed seasons, which hold 457-501 rows, mean 480 — so the rebased
board ends the season slightly smaller than today's 505, not dramatically so.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.features.season_basis import (
    SEASON_BASIS_CHANGE_BLOCKED,
    SeasonBasisRefusal,
    authorise_inference_season,
)


def _declaration(season: int, **over):
    base = {
        "declared_inference_season": season,
        "declared_by": "David",
        "declared_at": "2026-09-15T09:00:00-04:00",
        "word_verbatim": "advance the board to 2026",
    }
    base.update(over)
    return base


# ── the no-op case: nothing changes today ────────────────────────────────────────────


def test_an_unchanged_basis_is_authorised_without_any_declaration() -> None:
    """Today's case. The feed's max season equals what is already published, so the guard
    must be invisible: no declaration exists and the refresh proceeds."""
    assert authorise_inference_season(derived=2025, published=2025, declaration=None) == 2025


def test_the_very_first_publish_has_nothing_to_protect_and_proceeds() -> None:
    assert authorise_inference_season(derived=2025, published=None, declaration=None) == 2025


# ── the event this ticket exists for ─────────────────────────────────────────────────


def test_a_new_season_in_the_feed_does_not_silently_change_the_basis() -> None:
    with pytest.raises(SeasonBasisRefusal) as caught:
        authorise_inference_season(derived=2026, published=2025, declaration=None)

    refusal = caught.value
    assert refusal.reason == SEASON_BASIS_CHANGE_BLOCKED
    # The refusal must carry BOTH seasons: an operator reading the alert has to be able to
    # tell what changed without opening the feed.
    assert refusal.derived == 2026
    assert refusal.published == 2025


def test_the_refusal_token_is_distinct_from_a_feed_failure() -> None:
    """DG-136's lesson: a refusal that reads like a break gets triaged as a break. The
    fail-closed window will exit non-zero every morning for a CORRECT reason, so the token
    must name the refusal specifically."""
    assert SEASON_BASIS_CHANGE_BLOCKED == "season_basis_change_blocked"
    assert "unavailable" not in SEASON_BASIS_CHANGE_BLOCKED
    assert "failed" not in SEASON_BASIS_CHANGE_BLOCKED


# ── the release valve, and its governance ────────────────────────────────────────────


def test_a_declaration_naming_the_new_season_authorises_the_change() -> None:
    assert (
        authorise_inference_season(derived=2026, published=2025, declaration=_declaration(2026))
        == 2026
    )


def test_a_declaration_for_a_different_season_does_not_authorise_this_one() -> None:
    """A stale declaration from last year's rollover must not wave through the next one."""
    with pytest.raises(SeasonBasisRefusal) as caught:
        authorise_inference_season(derived=2027, published=2026, declaration=_declaration(2026))
    assert caught.value.reason == SEASON_BASIS_CHANGE_BLOCKED


@pytest.mark.parametrize("missing", ["declared_by", "declared_at", "declared_inference_season"])
def test_a_declaration_missing_its_provenance_authorises_nothing(missing: str) -> None:
    """Same shape as the frozen-prediction declaration: a rule with no author and no date is
    not a governed decision, it is a value someone typed."""
    declaration = _declaration(2026)
    declaration.pop(missing)
    with pytest.raises(SeasonBasisRefusal):
        authorise_inference_season(derived=2026, published=2025, declaration=declaration)


def test_a_declaration_cannot_authorise_a_season_the_feed_does_not_have() -> None:
    """The declaration says WHICH change is allowed, never invents data. If David declares
    2027 and the feed's newest season is 2026, that is not authorisation for 2026."""
    with pytest.raises(SeasonBasisRefusal):
        authorise_inference_season(derived=2026, published=2025, declaration=_declaration(2027))


# ── the served path actually consults it ─────────────────────────────────────────────


def test_the_refresh_reads_the_published_season_from_the_runtime_marker(tmp_path) -> None:
    import json

    from src.dynasty_genius.features.season_basis import published_inference_season

    marker = tmp_path / "engine_b_features_runtime.ready.json"
    marker.write_text(json.dumps({"status": "ok", "inference_season": 2025}))
    assert published_inference_season(tmp_path) == 2025


def test_a_missing_or_unreadable_marker_reads_as_no_published_season(tmp_path) -> None:
    from src.dynasty_genius.features.season_basis import published_inference_season

    assert published_inference_season(tmp_path) is None
    (tmp_path / "engine_b_features_runtime.ready.json").write_text("{not json")
    assert published_inference_season(tmp_path) is None


def test_the_refresh_script_calls_the_guard_before_it_publishes() -> None:
    """A guard nothing calls is the failure this repo keeps finding. Pin the wiring."""
    from pathlib import Path

    import scripts.run_feature_refresh as refresh

    source = Path(refresh.__file__).read_text()
    assert "authorise_inference_season" in source
    guard_at = source.index("authorise_inference_season")
    publish_at = source.index("def publish_fn")
    assert guard_at < publish_at, "the basis must be settled BEFORE the publisher is built"


# ── the alert must tell a REFUSAL from a BREAK ───────────────────────────────────────


def test_the_refusal_writes_its_own_marker_because_alerting_reads_markers_not_exit_codes(
    tmp_path,
) -> None:
    """`app/config/capture_gap_accepted_exits.json` states the contract in its own purpose
    field: a producer's failure is judged on its MARKER, "never on exit code alone". The
    fail-closed window exits non-zero every morning for a correct reason, so the refusal has
    to leave something an alert can read."""
    import json

    from scripts.run_feature_refresh import (
        SEASON_BASIS_MARKER_NAME,
        _write_season_basis_marker,
    )

    _write_season_basis_marker(
        tmp_path,
        {
            "status": "blocked",
            "reason": SEASON_BASIS_CHANGE_BLOCKED,
            "derived_inference_season": 2026,
            "published_inference_season": 2025,
        },
    )
    written = json.loads((tmp_path / SEASON_BASIS_MARKER_NAME).read_text())

    assert written["status"] == "blocked"
    assert written["reason"] == SEASON_BASIS_CHANGE_BLOCKED
    assert written["derived_inference_season"] == 2026
    assert written["published_inference_season"] == 2025


def test_both_branches_record_the_basis_decision(tmp_path) -> None:
    """A marker written only on refusal cannot be distinguished from a producer that never
    ran. Both outcomes must leave the same file with a different status."""
    from pathlib import Path

    import scripts.run_feature_refresh as refresh

    source = Path(refresh.__file__).read_text()
    guarded = source[source.index("authorise_inference_season(") :]
    guarded = guarded[: guarded.index("def publish_fn")]
    assert guarded.count("_write_season_basis_marker(") == 2, (
        "both the refusal and the proceed path must record the decision"
    )
    assert '"status": "blocked"' in guarded
    # NOT "ok": nothing is published at this point in the run, so a marker claiming success
    # here would read `ok` on a morning the publish later blocked.
    assert '"status": "authorised"' in guarded
    assert '"status": "ok"' not in guarded
    # and the refusal must also reach the artifact the freshness contract reads
    assert "_write_season_basis_refusal_report(" in guarded


def test_a_marker_write_failure_never_fails_an_otherwise_good_refresh(tmp_path) -> None:
    from scripts.run_feature_refresh import _write_season_basis_marker

    unwritable = tmp_path / "file_not_a_dir"
    unwritable.write_text("x")
    _write_season_basis_marker(unwritable / "nested", {"status": "ok"})  # must not raise


# ── review round 1: the refusal must reach the artifact that is actually monitored ───


def test_the_refusal_writes_the_report_the_freshness_contract_reads(tmp_path) -> None:
    """The first cut wrote a NEW sidecar and claimed that made a refusal distinguishable
    from a break. Nothing read it. `app/config/report_freshness.json` registers
    `feature_refresh_latest_report.json` for this producer with `status_field: status`,
    `success_status: [ok, noop]` and `failure_reason_field: blocked_reason` — that is the
    file an operator's alert consults, so the refusal has to land there."""
    import json

    from scripts.run_feature_refresh import _write_season_basis_refusal_report
    from src.dynasty_genius.features.season_basis import SEASON_BASIS_CHANGE_BLOCKED

    _write_season_basis_refusal_report(
        tmp_path,
        reason=SEASON_BASIS_CHANGE_BLOCKED,
        derived=2026,
        published=2025,
        detail="No declaration exists.",
        source_hash="abc123",
    )
    report = json.loads((tmp_path / "feature_refresh_latest_report.json").read_text())

    assert report["status"] == "blocked"
    assert report["blocked_reason"] == SEASON_BASIS_CHANGE_BLOCKED
    assert report["generated_at"]
    assert report["derived_inference_season"] == 2026
    assert report["published_inference_season"] == 2025
    assert report["decision_supported"] is False
    assert report["publish_performed"] is False


def test_the_blocked_report_cannot_make_the_next_morning_noop_itself_quiet() -> None:
    """`feature_refresh_runner` refuses to no-op from a prior `blocked` state (its own
    "noop poisoning" guard). Writing status `blocked` therefore keeps the refusal firing
    every morning until it is resolved, instead of going quiet after one day."""
    from pathlib import Path

    import src.dynasty_genius.features.feature_refresh_runner as runner

    source = Path(runner.__file__).read_text()
    assert 'last_status != "blocked"' in source


# ── review round 1: the guard must not fail OPEN on a missing marker ─────────────────


def test_a_published_runtime_with_an_unreadable_marker_refuses_rather_than_proceeds(
    tmp_path,
) -> None:
    """The first cut treated "no readable marker" as "nothing to protect". But a runtime CSV
    can be present with a marker that is missing or corrupt, and proceeding there authorises
    exactly the rebase this guard exists to stop."""
    with pytest.raises(SeasonBasisRefusal):
        authorise_inference_season(
            derived=2026, published=None, declaration=None, runtime_present=True
        )


def test_a_truly_first_publish_still_proceeds(tmp_path) -> None:
    assert (
        authorise_inference_season(
            derived=2026, published=None, declaration=None, runtime_present=False
        )
        == 2026
    )


def test_the_basis_reader_reports_whether_a_runtime_exists_at_all(tmp_path) -> None:
    import json

    from src.dynasty_genius.features.season_basis import published_basis

    empty = published_basis(tmp_path)
    assert empty["season"] is None and empty["runtime_present"] is False

    (tmp_path / "engine_b_features_runtime.csv").write_text("player_id\n")
    corrupt = published_basis(tmp_path)
    assert corrupt["season"] is None and corrupt["runtime_present"] is True

    (tmp_path / "engine_b_features_runtime.ready.json").write_text(
        json.dumps({"inference_season": 2025})
    )
    good = published_basis(tmp_path)
    assert good["season"] == 2025 and good["runtime_present"] is True


# ── review round 1: prove it end to end, not by grepping the source ──────────────────


def test_the_rollover_is_refused_end_to_end_through_main(tmp_path, monkeypatch) -> None:
    """The wiring tests above are source greps. This one drives the real entry point across
    the real event: a published 2025 basis, a feed offering 2026, no declaration."""
    import json

    import scripts.run_feature_refresh as refresh

    runtime = tmp_path / "features_runtime"
    runtime.mkdir()
    (runtime / "engine_b_features_runtime.csv").write_text("player_id,feature_season\nx,2025\n")
    (runtime / "engine_b_features_runtime.ready.json").write_text(
        json.dumps({"status": "ok", "inference_season": 2025})
    )
    before = (runtime / "engine_b_features_runtime.csv").read_text()

    import pandas as pd

    feed = pd.DataFrame(
        {"season": [2025, 2026], "player_id": ["a", "b"], "week": [1, 1]}
    )
    monkeypatch.setattr(refresh, "_load_source", lambda seasons: {"player_stats": feed})

    exit_code = refresh.main(["--runtime-dir", str(runtime)])

    assert exit_code == 1, "the rollover must not publish"
    report = json.loads((runtime / "feature_refresh_latest_report.json").read_text())
    assert report["status"] == "blocked"
    assert report["blocked_reason"] == SEASON_BASIS_CHANGE_BLOCKED
    assert (runtime / "engine_b_features_runtime.csv").read_text() == before, (
        "the live board must keep serving the season it was built on"
    )
