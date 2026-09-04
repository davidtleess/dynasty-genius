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

Re-derived here before building (2018-2025, `ff_opportunity` weekly, local, no network):
a four-game mean carries 77% of a full season's variance pooled (23% lost) and 65% at QB
(35% lost); as pure sampling precision the loss is ~70% at every position. Today's inference
partition is exactly 505 rows; after a rebase it refills to about 199 players by week 4 and
about 282 by week 6, and tops out near 438 even at season end.
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
    assert '"status": "blocked"' in guarded and '"status": "ok"' in guarded


def test_a_marker_write_failure_never_fails_an_otherwise_good_refresh(tmp_path) -> None:
    from scripts.run_feature_refresh import _write_season_basis_marker

    unwritable = tmp_path / "file_not_a_dir"
    unwritable.write_text("x")
    _write_season_basis_marker(unwritable / "nested", {"status": "ok"})  # must not raise
