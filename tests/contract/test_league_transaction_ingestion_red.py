"""RED contract for league transaction ingestion (layer 1).

Every assertion runs against REAL Sleeper data captured 2026-07-30 from David's league and
the REAL governed ff_playerids crosswalk — not synthetic fixtures. The fixture's own shape
drives the contract: `adds`/`drops` arrive as ``null``, a fifth transaction type
(``commissioner``) exists, and failed waiver claims sit alongside completed ones.

Sections marked TW30E-CODEREVIEW-10 lock a specific review finding. Each replaces an
assertion that was too weak to catch it — most notably a row-count check that called
overwrite-with-orphans "idempotent".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.league_transactions import (
    CANONICAL_RESOLVED,
    SLEEPER_ONLY,
    UNKNOWN,
    IdentityResolver,
    NormalizedCapture,
    TransactionCaptureError,
    TransactionStore,
    completed_movements,
    load_governed_crosswalk,
    normalize_leg,
    normalize_transactions,
    run_transaction_capture,
    status_marker_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
TXN_FIXTURE = FIXTURES / "sleeper_league_transactions_2026_07_30.json"
IDENTITY_FIXTURE = FIXTURES / "sleeper_universe_identity_subset_2026_07_30.json"

# Named in the review: present in Sleeper's player map, absent from the governed crosswalk.
NO_CANONICAL_MAPPING = {"13324", "13400"}  # Matt Hibner, Justin Joly


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_legs() -> dict[str, list[dict[str, Any]]]:
    return _load(TXN_FIXTURE)["legs"]


@pytest.fixture(scope="module")
def crosswalk() -> dict[str, dict[str, Any]]:
    return load_governed_crosswalk()


@pytest.fixture(scope="module")
def resolver(crosswalk) -> IdentityResolver:
    return IdentityResolver.from_snapshot(_load(IDENTITY_FIXTURE), crosswalk_by_sleeper=crosswalk)


@pytest.fixture(scope="module")
def normalized(raw_legs, resolver):
    return normalize_transactions(
        raw_legs, league_id="1314363401744416768", season="2026", resolver=resolver
    )


# --------------------------------------------------------------------------
# Shape of the real payload
# --------------------------------------------------------------------------


def test_fixture_is_the_real_capture(raw_legs) -> None:
    """Guards the premise: if the fixture is swapped for a toy, this contract is void."""
    total = sum(len(v) for v in raw_legs.values())
    assert total == 67
    types = {t["type"] for legs in raw_legs.values() for t in legs}
    assert types == {"free_agent", "waiver", "trade", "commissioner"}
    assert any(t.get("adds") is None for legs in raw_legs.values() for t in legs)
    assert any(t.get("drops") is None for legs in raw_legs.values() for t in legs)


def test_every_transaction_is_ingested_none_dropped(normalized, raw_legs) -> None:
    assert len(normalized.transactions) == sum(len(v) for v in raw_legs.values())


def test_commissioner_type_is_preserved_not_discarded(normalized) -> None:
    kinds = {t["type"] for t in normalized.transactions}
    assert "commissioner" in kinds, "a real roster-changing type must not be dropped as unknown"


def test_dates_are_iso_utc_not_epoch_millis(normalized) -> None:
    for row in normalized.transactions:
        assert isinstance(row["created_at"], str)
        assert row["created_at"].endswith("+00:00"), row["created_at"]


def test_created_at_matches_the_source_epoch(normalized, raw_legs) -> None:
    from datetime import datetime, timezone

    by_id = {t["transaction_id"]: t for legs in raw_legs.values() for t in legs}
    row = normalized.transactions[0]
    source_ms = by_id[row["transaction_id"]]["created"]
    assert row["created_at"] == datetime.fromtimestamp(source_ms / 1000, tz=timezone.utc).isoformat()


# --------------------------------------------------------------------------
# TW30E-CODEREVIEW-10 BLOCKING 1 — canonical identity, honestly counted
# --------------------------------------------------------------------------


def test_canonical_dg_player_id_is_actually_stored(normalized) -> None:
    """The prior contract asserted a Sleeper id as 'our identity'. It is not."""
    canonical = [
        m
        for m in normalized.movements
        if m["asset_type"] == "player" and m["identity_status"] == CANONICAL_RESOLVED
    ]
    assert canonical, "no player resolved to a Dynasty Genius canonical id"
    for mv in canonical:
        assert mv["dg_player_id"], f"canonical_resolved without a dg_player_id: {mv}"
        assert mv["dg_player_id"] != mv["sleeper_player_id"]


def test_sleeper_presence_alone_is_not_canonical_resolution(normalized) -> None:
    """The exact defect: these two are in Sleeper's map and have no canonical mapping."""
    by_id = {
        m["sleeper_player_id"]: m for m in normalized.movements if m["asset_type"] == "player"
    }
    for sleeper_id in NO_CANONICAL_MAPPING:
        assert sleeper_id in by_id, f"{sleeper_id} missing from the fixture"
        mv = by_id[sleeper_id]
        assert mv["identity_status"] == SLEEPER_ONLY, mv
        assert mv["dg_player_id"] is None
        # Still attributable, still counted, never dropped.
        assert mv["player_name"]


def test_coverage_cannot_report_a_single_reassuring_zero(normalized) -> None:
    """`players_unresolved: 0` was true of Sleeper presence and false of identity."""
    coverage = normalized.coverage
    assert "players_unresolved" not in coverage, "the ambiguous single count must not return"
    assert coverage["players_sleeper_only"] == len(NO_CANONICAL_MAPPING)
    assert set(coverage["sleeper_only_ids"]) == NO_CANONICAL_MAPPING
    assert coverage["players_not_canonically_identified"] == (
        coverage["players_sleeper_only"] + coverage["players_unknown"]
    )
    assert (
        coverage["players_canonical_resolved"]
        + coverage["players_not_canonically_identified"]
        == coverage["players_total"]
    )


def test_crosswalk_coverage_of_the_real_fixture_is_66_of_68(normalized, raw_legs) -> None:
    referenced = {
        str(pid)
        for legs in raw_legs.values()
        for t in legs
        for side in ("adds", "drops")
        for pid in (t.get(side) or {})
    }
    assert len(referenced) == 68
    resolved_ids = {
        m["sleeper_player_id"]
        for m in normalized.movements
        if m["identity_status"] == CANONICAL_RESOLVED
    }
    assert len(resolved_ids) == 66


def test_unknown_player_is_labelled_distinctly_from_sleeper_only(crosswalk) -> None:
    """A player in neither source is `unknown`, not silently merged with `sleeper_only`."""
    resolver = IdentityResolver.from_snapshot({"players": [], "users": [], "rosters": []},
                                              crosswalk_by_sleeper=crosswalk)
    row = resolver.player("999999999")
    assert row["identity_status"] == UNKNOWN
    assert row["dg_player_id"] is None


def test_zero_canonical_resolution_refuses(raw_legs) -> None:
    snapshot = _load(IDENTITY_FIXTURE)
    resolver = IdentityResolver.from_snapshot(snapshot, crosswalk_by_sleeper={})
    with pytest.raises(TransactionCaptureError) as exc:
        normalize_transactions(raw_legs, league_id="L", season="2026", resolver=resolver)
    assert "zero canonically resolved" in str(exc.value)


# --------------------------------------------------------------------------
# TW30E-CODEREVIEW-10 BLOCKING 2 — completeness evidenced, failure loud
# --------------------------------------------------------------------------


def _capture_kwargs(tmp_path, resolver, fetch_leg, legs):
    return {
        "league_id": "L",
        "season": "2026",
        "fetch_leg": fetch_leg,
        "resolver": resolver,
        "legs": legs,
        "db_path": tmp_path / "txn.db",
        "raw_root": tmp_path / "runtime",
    }


def test_attempted_legs_are_recorded_so_completeness_is_provable(tmp_path, resolver, raw_legs) -> None:
    """An 18-leg fetch and a 1-leg fetch previously left identical evidence."""
    fetch = lambda leg: raw_legs.get(str(leg), [])  # noqa: E731
    status = run_transaction_capture(**_capture_kwargs(tmp_path, resolver, fetch, list(range(1, 19))))
    assert status["legs_attempted"] == list(range(1, 19))
    assert status["legs_empty"] == [leg for leg in range(2, 19)]
    assert status["legs_with_activity"] == [1]

    raw = json.loads(Path(status["raw_snapshot"]).read_text())
    assert raw["legs_attempted"] == list(range(1, 19))

    narrow = run_transaction_capture(**_capture_kwargs(tmp_path, resolver, fetch, [1]))
    assert narrow["legs_attempted"] == [1]
    assert narrow["legs_attempted"] != status["legs_attempted"], "the two runs must be distinguishable"


def test_a_failed_leg_does_not_leave_the_previous_success_standing(tmp_path, resolver, raw_legs) -> None:
    """The disease of the week: an artifact reporting healthy while carrying nothing new."""
    marker = status_marker_path(tmp_path / "runtime")
    good = lambda leg: raw_legs.get(str(leg), [])  # noqa: E731
    run_transaction_capture(**_capture_kwargs(tmp_path, resolver, good, [1]))
    assert json.loads(marker.read_text())["status"] == "ok"

    def exploding(leg: int):
        if leg == 2:
            raise RuntimeError("sleeper 503")
        return raw_legs.get(str(leg), [])

    with pytest.raises(TransactionCaptureError):
        run_transaction_capture(**_capture_kwargs(tmp_path, resolver, exploding, [1, 2, 3]))

    after = json.loads(marker.read_text())
    assert after["status"] == "failed", "a failed run must not inherit the prior ok"
    assert after["failed_leg"] == 2
    assert "sleeper 503" in after["reason"]


def test_a_start_record_is_written_before_any_fetch(tmp_path, resolver) -> None:
    """Distinguishes a run that died mid-flight from one that never started."""
    marker = status_marker_path(tmp_path / "runtime")
    seen: list[dict[str, Any]] = []

    def observing(leg: int):
        seen.append(json.loads(marker.read_text()))
        return []

    run_transaction_capture(**_capture_kwargs(tmp_path, resolver, observing, [1]))
    assert seen, "fetch was never called"
    assert seen[0]["status"] == "running"
    assert seen[0]["run_id"]
    assert seen[0]["started_at"]


def test_identity_refusal_is_recorded_as_failed_not_left_silent(tmp_path, raw_legs) -> None:
    marker = status_marker_path(tmp_path / "runtime")
    broken = IdentityResolver.from_snapshot(_load(IDENTITY_FIXTURE), crosswalk_by_sleeper={})
    fetch = lambda leg: raw_legs.get(str(leg), [])  # noqa: E731
    with pytest.raises(TransactionCaptureError):
        run_transaction_capture(**_capture_kwargs(tmp_path, broken, fetch, [1]))
    assert json.loads(marker.read_text())["status"] == "failed"


# --------------------------------------------------------------------------
# TW30E-CODEREVIEW-10 BLOCKING 3 — real idempotence, real reconciliation
# --------------------------------------------------------------------------


def test_reingesting_identical_content_mutates_nothing(tmp_path, normalized) -> None:
    """Row counts were stable before; the bytes were not."""
    store = TransactionStore(tmp_path / "txn.db")
    first = store.upsert(normalized, ingested_at="2026-07-30T00:00:00+00:00")
    fingerprint = store.content_fingerprint()
    assert first["inserted"] == len(normalized.transactions)

    second = store.upsert(normalized, ingested_at="2026-07-31T00:00:00+00:00")
    assert second["unchanged"] == len(normalized.transactions)
    assert second["inserted"] == 0 and second["updated"] == 0
    assert store.content_fingerprint() == fingerprint, "a no-op re-ingest rewrote rows"


def test_changed_transaction_reconciles_removed_movements(tmp_path, resolver) -> None:
    """Reproduces the review's case: player A replaced by player B left BOTH rows."""
    def leg(player_id: str):
        return {
            "1": [
                {
                    "transaction_id": "T1",
                    "type": "free_agent",
                    "status": "complete",
                    "created": 1785367315963,
                    "status_updated": 1785367315963,
                    "adds": {player_id: 1},
                    "drops": None,
                    "roster_ids": [1],
                    "draft_picks": [],
                    "creator": "u1",
                    "settings": None,
                }
            ]
        }

    a, b = "11370", "8180"
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalize_transactions(leg(a), league_id="L", season="2026", resolver=resolver))
    assert {m["sleeper_player_id"] for m in store.movements_for("T1")} == {a}

    applied = store.upsert(
        normalize_transactions(leg(b), league_id="L", season="2026", resolver=resolver)
    )
    assert applied["updated"] == 1
    stored = {m["sleeper_player_id"] for m in store.movements_for("T1")}
    assert stored == {b}, f"a removed movement survived: {stored}"
    assert store.movement_count() == 1


def test_store_persists_and_reads_back(tmp_path, normalized) -> None:
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalized)
    assert store.transaction_count() == len(normalized.transactions)
    assert store.movement_count() == len(normalized.movements)


def test_raw_payload_is_preserved_for_replay(tmp_path, normalized, raw_legs) -> None:
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalized)
    by_id = {t["transaction_id"]: t for legs in raw_legs.values() for t in legs}
    row = store.fetch_transaction(normalized.transactions[0]["transaction_id"])
    assert json.loads(row["raw_json"]) == by_id[row["transaction_id"]]


# --------------------------------------------------------------------------
# TW30E-CODEREVIEW-10 MATERIAL — both sides of a pick, stable manager identity
# --------------------------------------------------------------------------


def test_pick_movement_records_the_send_side_too(normalized) -> None:
    """A history recording only acquisitions cannot say what the sending manager did."""
    trade = [
        m
        for m in normalized.movements
        if m["transaction_id"] == "1365162652438921216" and m["asset_type"] == "pick"
    ]
    acquires = [m for m in trade if m["action"] == "pick_acquire"]
    sends = [m for m in trade if m["action"] == "pick_send"]
    assert len(acquires) == 4
    assert len(sends) == 4
    assert {m["roster_id"] for m in acquires} == {6}
    assert {m["roster_id"] for m in sends} == {4}
    assert len({m["movement_key"] for m in trade}) == 8


def test_pick_movements_are_uniquely_keyed_by_their_original_owner(normalized) -> None:
    """Regression: a real trade moved FOUR picks in which (season, round, previous_owner)
    repeated twice. Keying without the pick's ORIGINAL owner collapsed two movements."""
    keys = [m["movement_key"] for m in normalized.movements]
    assert len(keys) == len(set(keys)), "movement keys must be unique or the store loses rows"
    trade = [
        m
        for m in normalized.movements
        if m["transaction_id"] == "1365162652438921216" and m["action"] == "pick_acquire"
    ]
    assert {m["pick_original_roster_id"] for m in trade} == {10, 4, 6}


def test_manager_activity_is_keyed_by_stable_identity_not_display_name(tmp_path, resolver, raw_legs) -> None:
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalize_transactions(raw_legs, league_id="L", season="2026", resolver=resolver))
    activity = store.manager_activity()
    assert activity
    for key, bucket in activity.items():
        assert key.startswith("user:") or key.startswith("roster:")
        assert bucket["movements"]
        assert all(m["transaction_status"] == "complete" for m in bucket["movements"])


def test_two_managers_sharing_a_display_name_do_not_merge(tmp_path, crosswalk, raw_legs) -> None:
    """Display names are mutable and collide; the prior grouping merged them silently."""
    snapshot = _load(IDENTITY_FIXTURE)
    collided = dict(snapshot)
    collided["users"] = [dict(u, display_name="SameName") for u in snapshot["users"]]
    resolver = IdentityResolver.from_snapshot(collided, crosswalk_by_sleeper=crosswalk)
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalize_transactions(raw_legs, league_id="L", season="2026", resolver=resolver))
    activity = store.manager_activity()
    assert len({b["display_name"] for b in activity.values()}) == 1
    assert len(activity) > 1, "distinct managers collapsed into one display name"


def test_manager_activity_totals_match_completed_movements(tmp_path, resolver, raw_legs) -> None:
    capture = normalize_transactions(raw_legs, league_id="L", season="2026", resolver=resolver)
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(capture)
    activity = store.manager_activity()
    total = sum(len(b["movements"]) for b in activity.values())
    assert total == len(completed_movements(capture.movements))


# --------------------------------------------------------------------------
# Honesty and adapter discipline
# --------------------------------------------------------------------------


def test_failed_transactions_are_stored_with_their_status(normalized) -> None:
    assert "failed" in {t["status"] for t in normalized.transactions}
    for mv in normalized.movements:
        assert mv["transaction_status"] in {"complete", "failed"}


def test_completed_movements_excludes_failed_claims(normalized) -> None:
    done = completed_movements(normalized.movements)
    assert done
    assert all(m["transaction_status"] == "complete" for m in done)
    assert len(done) < len(normalized.movements)


def test_every_movement_names_the_manager_who_made_it(normalized) -> None:
    for mv in normalized.movements:
        assert mv["roster_id"] is not None
        assert mv["manager_display_name"], f"manager unresolved for {mv}"


def test_waiver_bid_is_captured(normalized) -> None:
    waivers = [t for t in normalized.transactions if t["type"] == "waiver"]
    assert waivers
    assert all(t["waiver_bid"] is not None for t in waivers)


def test_normalize_leg_is_null_safe_on_both_sides() -> None:
    txn = {
        "transaction_id": "1",
        "type": "free_agent",
        "status": "complete",
        "created": 1785367315963,
        "status_updated": 1785367315963,
        "adds": None,
        "drops": None,
        "roster_ids": [5],
        "draft_picks": [],
        "creator": "u1",
        "settings": None,
    }
    rows, movements = normalize_leg(
        [txn],
        leg="1",
        league_id="L",
        season="2026",
        resolver=IdentityResolver.from_snapshot({"players": [], "users": [], "rosters": []}),
    )
    assert len(rows) == 1
    assert movements == []


def test_empty_capture_is_not_an_identity_failure(resolver) -> None:
    capture = normalize_transactions({}, league_id="L", season="2026", resolver=resolver)
    assert isinstance(capture, NormalizedCapture)
    assert capture.coverage["players_total"] == 0


def test_store_from_an_earlier_schema_fails_closed_by_name(tmp_path) -> None:
    """`CREATE TABLE IF NOT EXISTS` is a no-op against an older table, so a stale store
    would otherwise surface as an OperationalError mid-write."""
    import sqlite3

    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE league_transaction (transaction_id TEXT PRIMARY KEY)")
    with pytest.raises(TransactionCaptureError) as exc:
        TransactionStore(path)
    assert "schema_mismatch" in str(exc.value)


def test_backup_manifest_coverage_is_deliberately_deferred() -> None:
    """The store is NOT in the backup manifest, and that is a David ruling, not an omission.

    2026-07-30: the manifest is read from DISK at run time, so an entry present only in a
    working tree was already live to the next scheduled backup. That run is David's clean
    baseline, and this store is rebuildable from the public Sleeper API in seconds while the
    baseline is not rebuildable at all — so the entry was reverted and returns when a
    scheduler word lands and the store begins accruing history the API no longer serves.

    This test exists so the absence stays deliberate: it fails the moment someone adds the
    entry without the scheduler decision, and the manifest-coverage law's own anti-rot test
    (`test_backup_manifest_anti_rot_red.py`) independently catches a present-but-uncovered
    store. Neither guard is weakened here.
    """
    manifest = json.loads((REPO_ROOT / "app" / "config" / "backup_manifest.json").read_text())
    covered = {
        entry["path"]
        for section in ("required", "optional")
        for entry in manifest.get(section, [])
        if isinstance(entry, dict)
    }
    assert "app/data/league_transactions.db" not in covered, (
        "the manifest entry returned without a scheduler word — if that is now intended, "
        "update this test and the accompanying note together"
    )
