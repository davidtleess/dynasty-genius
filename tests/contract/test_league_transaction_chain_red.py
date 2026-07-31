"""RED contract for multi-season league transaction ingestion (TW30N-BUILD-01, layer 1).

One season of transactions cannot describe a manager. This contract covers walking
Sleeper's ``previous_league_id`` chain back to the league's first season, and it runs
against a REAL live capture of David's own chain (2026-07-30): four seasons, 932
transactions, the actual rosters and users of each season.

**The regression this file exists for.** The naive extension — one resolver, every season —
type-checks, passes every single-season test, and is wrong. Sleeper reissues ``roster_id``
1..12 in each season of a chain and the slot changes hands between them. On David's own
chain, rosters 2, 3 and 11 have different owners in earlier seasons than they do in 2026,
so a current-season manager map files a departed manager's moves under whoever later took
their slot — silently, with a confident name attached. Live data exposed it; a synthetic
fixture with a stable 12-manager league would have missed it exactly the way a synthetic
fixture missed the four-draft-pick collapse.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.league_transactions import (
    CANONICAL_RESOLVED,
    IdentityResolver,
    LeagueChainLink,
    TransactionCaptureError,
    TransactionStore,
    load_governed_crosswalk,
    normalize_transactions,
    resolve_league_chain,
    run_chain_transaction_capture,
    status_marker_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
CHAIN_FIXTURE = FIXTURES / "sleeper_league_chain_2026_07_30.json"
IDENTITY_FIXTURE = FIXTURES / "sleeper_universe_identity_subset_2026_07_30.json"

ROOT_LEAGUE = "1314363401744416768"
L2025 = "1183088915091423232"
L2024 = "1049152209134424064"
L2023 = "912589367620100096"
CHAIN_ORDER = [ROOT_LEAGUE, L2025, L2024, L2023]

#: Measured from the live chain: roster slots that changed hands. Roster 11 changed before
#: 2025; rosters 2 and 3 changed further back. These are the rows the naive extension
#: attributes to the wrong manager.
REASSIGNED_ROSTERS = {11, 2, 3}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chain_fixture() -> dict[str, Any]:
    return _load(CHAIN_FIXTURE)


@pytest.fixture(scope="module")
def crosswalk() -> dict[str, dict[str, Any]]:
    return load_governed_crosswalk()


@pytest.fixture(scope="module")
def base_resolver(crosswalk) -> IdentityResolver:
    return IdentityResolver.from_snapshot(_load(IDENTITY_FIXTURE), crosswalk_by_sleeper=crosswalk)


@pytest.fixture()
def harness(chain_fixture, base_resolver):
    """Offline replay of the live endpoints, with per-season manager maps."""

    def fetch_league(league_id: str):
        return chain_fixture["leagues"].get(str(league_id))

    def fetch_leg(league_id: str, leg: int):
        return chain_fixture["legs"].get(str(league_id), {}).get(str(leg), [])

    def build_resolver(link: LeagueChainLink) -> IdentityResolver:
        return base_resolver.with_managers(
            rosters=chain_fixture["rosters"].get(link.league_id, []),
            users=chain_fixture["users"].get(link.league_id, []),
        )

    return {
        "fetch_league": fetch_league,
        "fetch_leg": fetch_leg,
        "build_resolver": build_resolver,
    }


def _run(tmp_path: Path, harness, **overrides) -> dict[str, Any]:
    kwargs = {
        "league_id": ROOT_LEAGUE,
        "db_path": tmp_path / "txn.db",
        "raw_root": tmp_path / "runtime",
        **harness,
        **overrides,
    }
    return run_chain_transaction_capture(**kwargs)


# --------------------------------------------------------------------------
# The premise: this is the real chain, not a toy
# --------------------------------------------------------------------------


def test_fixture_is_the_real_live_chain(chain_fixture) -> None:
    """If the fixture is swapped for a synthetic league, this whole contract is void."""
    assert set(chain_fixture["leagues"]) == set(CHAIN_ORDER)
    seasons = [chain_fixture["leagues"][lid]["season"] for lid in CHAIN_ORDER]
    assert seasons == ["2026", "2025", "2024", "2023"]
    # The chain order is a property of the DATA, not of the fixture's key order (the file
    # is written sort_keys=True): each league points at the next one back.
    assert [chain_fixture["leagues"][lid]["previous_league_id"] for lid in CHAIN_ORDER] == [
        L2025,
        L2024,
        L2023,
        None,
    ]
    totals = {
        lid: sum(len(v) for v in chain_fixture["legs"][lid].values()) for lid in CHAIN_ORDER
    }
    assert totals == {ROOT_LEAGUE: 67, L2025: 299, L2024: 323, L2023: 243}
    assert sum(totals.values()) == 932
    # Completed seasons ran 17 legs; the live season has only played leg 1 so far.
    assert sorted(int(k) for k in chain_fixture["legs"][L2024]) == list(range(1, 18))
    assert sorted(int(k) for k in chain_fixture["legs"][ROOT_LEAGUE]) == [1]


def test_the_real_chain_reassigns_roster_slots_between_seasons(chain_fixture) -> None:
    """The measured fact the whole design turns on. If this ever stops being true, the
    per-season resolver is merely correct rather than load-bearing — but it is true."""
    owners = {
        lid: {r["roster_id"]: r["owner_id"] for r in chain_fixture["rosters"][lid]}
        for lid in CHAIN_ORDER
    }
    changed = {
        rid
        for lid in (L2025, L2024, L2023)
        for rid in owners[ROOT_LEAGUE]
        if owners[ROOT_LEAGUE][rid] != owners[lid].get(rid)
    }
    assert changed == REASSIGNED_ROSTERS, (
        "the live chain no longer reassigns roster slots; re-measure before trusting "
        "the attribution tests below"
    )


# --------------------------------------------------------------------------
# Chain traversal
# --------------------------------------------------------------------------


def test_chain_walks_every_prior_season_newest_first(harness) -> None:
    chain = resolve_league_chain(ROOT_LEAGUE, fetch_league=harness["fetch_league"])
    assert [link.league_id for link in chain] == CHAIN_ORDER
    assert [link.season for link in chain] == ["2026", "2025", "2024", "2023"]
    assert chain[-1].previous_league_id is None, "the walk must reach the league's first season"


def test_a_league_that_cannot_be_read_is_a_named_failure_not_a_short_history() -> None:
    """A truncated chain and a complete one must never be indistinguishable."""
    leagues = {
        "A": {"league_id": "A", "season": "2026", "previous_league_id": "B"},
        # "B" is absent: Sleeper answers 200-with-null for an unknown league.
    }
    with pytest.raises(TransactionCaptureError) as exc:
        resolve_league_chain("A", fetch_league=lambda lid: leagues.get(lid))
    assert "league_chain_broken" in str(exc.value)
    assert "B" in str(exc.value)
    assert "A" in str(exc.value), "the failure must name what it had already walked"


def test_a_league_fetch_that_raises_is_a_named_failure() -> None:
    def fetch(league_id: str):
        if league_id == "A":
            return {"league_id": "A", "season": "2026", "previous_league_id": "B"}
        raise RuntimeError("sleeper 503")

    with pytest.raises(TransactionCaptureError) as exc:
        resolve_league_chain("A", fetch_league=fetch)
    assert "league_chain_broken" in str(exc.value)
    assert "sleeper 503" in str(exc.value)


def test_a_cycle_refuses_rather_than_looping_forever() -> None:
    leagues = {
        "A": {"league_id": "A", "season": "2026", "previous_league_id": "B"},
        "B": {"league_id": "B", "season": "2025", "previous_league_id": "A"},
    }
    with pytest.raises(TransactionCaptureError) as exc:
        resolve_league_chain("A", fetch_league=lambda lid: leagues.get(lid))
    assert "league_chain_cycle" in str(exc.value)


def test_an_implausibly_deep_chain_refuses() -> None:
    def fetch(league_id: str):
        n = int(league_id)
        return {"league_id": league_id, "season": str(2026 - n), "previous_league_id": str(n + 1)}

    with pytest.raises(TransactionCaptureError) as exc:
        resolve_league_chain("0", fetch_league=fetch, max_depth=5)
    assert "league_chain_too_deep" in str(exc.value)


def test_a_league_without_a_season_refuses() -> None:
    with pytest.raises(TransactionCaptureError) as exc:
        resolve_league_chain(
            "A", fetch_league=lambda lid: {"league_id": "A", "previous_league_id": None}
        )
    assert "league_chain_missing_season" in str(exc.value)


def test_sleeper_zero_sentinel_terminates_the_chain() -> None:
    chain = resolve_league_chain(
        "A", fetch_league=lambda lid: {"league_id": "A", "season": "2026", "previous_league_id": "0"}
    )
    assert len(chain) == 1
    assert chain[0].previous_league_id is None


# --------------------------------------------------------------------------
# THE REGRESSION — per-season manager attribution
# --------------------------------------------------------------------------


def test_every_season_is_attributed_against_its_own_roster_owner_map(
    tmp_path, harness, chain_fixture
) -> None:
    """Each movement's manager must match the owner of that roster IN THAT SEASON."""
    _run(tmp_path, harness)
    store = TransactionStore(tmp_path / "txn.db")
    owners = {
        lid: {r["roster_id"]: str(r["owner_id"]) for r in chain_fixture["rosters"][lid]}
        for lid in CHAIN_ORDER
    }
    with sqlite3.connect(tmp_path / "txn.db") as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            "SELECT league_id, roster_id, manager_user_id FROM league_transaction_movement"
        )]
    assert rows
    for row in rows:
        expected = owners[row["league_id"]][int(row["roster_id"])]
        assert row["manager_user_id"] == expected, (
            f"league {row['league_id']} roster {row['roster_id']} attributed to "
            f"{row['manager_user_id']}, but that season's owner is {expected}"
        )
    assert store.transaction_count() == 932


def test_a_single_current_season_resolver_would_misattribute_and_this_one_does_not(
    tmp_path, harness, chain_fixture, base_resolver
) -> None:
    """The defect, reproduced side by side.

    Builds the same 2023 season twice — once with 2023's manager map, once with 2026's —
    and asserts the two disagree on real movements. The disagreement is the bug the naive
    extension ships; this contract locks the correct side of it.
    """
    legs_2023 = chain_fixture["legs"][L2023]
    right = normalize_transactions(
        legs_2023,
        league_id=L2023,
        season="2023",
        resolver=base_resolver.with_managers(
            rosters=chain_fixture["rosters"][L2023], users=chain_fixture["users"][L2023]
        ),
    )
    wrong = normalize_transactions(
        legs_2023,
        league_id=L2023,
        season="2023",
        resolver=base_resolver.with_managers(
            rosters=chain_fixture["rosters"][ROOT_LEAGUE], users=chain_fixture["users"][ROOT_LEAGUE]
        ),
    )

    by_key_right = {m["movement_key"]: m for m in right.movements}
    misattributed = [
        key
        for key, mv in {m["movement_key"]: m for m in wrong.movements}.items()
        if by_key_right[key]["manager_user_id"] != mv["manager_user_id"]
    ]
    assert misattributed, (
        "the current-season map produced identical attribution — re-measure "
        "REASSIGNED_ROSTERS before trusting this contract"
    )
    # And the wrong version is wrong in the way that hurts: it still names a manager.
    wrong_rows = {m["movement_key"]: m for m in wrong.movements}
    assert all(wrong_rows[key]["manager_display_name"] for key in misattributed), (
        "the defect is silent by construction — a confident wrong name, not a blank"
    )

    owners_2023 = {r["roster_id"]: str(r["owner_id"]) for r in chain_fixture["rosters"][L2023]}
    for mv in right.movements:
        assert mv["manager_user_id"] == owners_2023[int(mv["roster_id"])]


def test_every_movement_carries_the_league_season_it_belongs_to(tmp_path, harness) -> None:
    """`roster_id` is meaningless without it, so it is stored, not inferred."""
    _run(tmp_path, harness)
    with sqlite3.connect(tmp_path / "txn.db") as conn:
        conn.row_factory = sqlite3.Row
        pairs = {
            (r["league_id"], r["season"])
            for r in conn.execute("SELECT league_id, season FROM league_transaction_movement")
        }
    assert pairs == {
        (ROOT_LEAGUE, "2026"),
        (L2025, "2025"),
        (L2024, "2024"),
        (L2023, "2023"),
    }


def test_manager_history_spans_seasons_and_can_be_scoped_to_one(tmp_path, harness) -> None:
    """Years of behaviour under one key is the entire point of walking the chain."""
    _run(tmp_path, harness)
    store = TransactionStore(tmp_path / "txn.db")
    everything = store.manager_activity()
    assert everything

    multi_season = [
        key
        for key, bucket in everything.items()
        if len({m["season"] for m in bucket["movements"]}) > 1
    ]
    assert multi_season, "no manager accumulated history across more than one season"

    scoped = store.manager_activity(season="2023")
    assert scoped
    assert all(
        m["season"] == "2023" for bucket in scoped.values() for m in bucket["movements"]
    )
    assert sum(len(b["movements"]) for b in scoped.values()) < sum(
        len(b["movements"]) for b in everything.values()
    )


# --------------------------------------------------------------------------
# Three-valued identity, per season, never rounded to resolved
# --------------------------------------------------------------------------


def test_identity_coverage_is_reported_per_season_not_only_in_total(tmp_path, harness) -> None:
    status = _run(tmp_path, harness)
    by_season = status["chain_coverage"]["by_season"]
    assert set(by_season) == {"2026", "2025", "2024", "2023"}
    for season, block in by_season.items():
        assert block["season"] == season
        assert (
            block["players_canonical_resolved"]
            + block["players_not_canonically_identified"]
            == block["players_total"]
        ), f"{season} coverage does not reconcile"
        assert "players_unresolved" not in block, "the ambiguous single count must not return"


def test_a_season_that_resolves_worse_than_its_neighbours_stays_visible(
    tmp_path, harness
) -> None:
    """Measured: 2026 carries two players with no canonical mapping (recent additions the
    frozen crosswalk predates); 2023, 2024 and 2025 carry none. A chain total alone would
    read as 930-something-of-932 and lose which season the gap is in."""
    status = _run(tmp_path, harness)
    coverage = status["chain_coverage"]
    assert coverage["seasons_with_unresolved_players"] == ["2026"]
    assert coverage["sleeper_only_ids"] == ["13324", "13400"]
    by_season = coverage["by_season"]
    assert by_season["2026"]["players_sleeper_only"] == 2
    for season in ("2025", "2024", "2023"):
        assert by_season[season]["players_not_canonically_identified"] == 0
        assert by_season[season]["players_canonical_resolved"] > 0


def test_chain_totals_reconcile_with_the_per_season_blocks(tmp_path, harness) -> None:
    status = _run(tmp_path, harness)
    coverage = status["chain_coverage"]
    blocks = coverage["by_season"].values()
    for key in ("players_total", "players_canonical_resolved", "players_sleeper_only"):
        assert coverage[key] == sum(b[key] for b in blocks)
    assert coverage["transactions_total"] == 932
    assert (
        coverage["players_canonical_resolved"] + coverage["players_not_canonically_identified"]
        == coverage["players_total"]
    )


def test_every_manager_in_every_season_is_named(tmp_path, harness) -> None:
    status = _run(tmp_path, harness)
    coverage = status["chain_coverage"]
    assert coverage["seasons_with_unresolved_managers"] == []
    for season, block in coverage["by_season"].items():
        assert block["managers_unresolved"] == 0, season
        assert block["managers_unresolved_roster_ids"] == []


def test_prior_season_players_resolve_canonically(tmp_path, harness) -> None:
    """Guards a plausible-looking wrong answer: a 2023 player resolving as `unknown`
    because the CURRENT universe snapshot no longer lists them. Canonical identity comes
    from the crosswalk, which is season-independent, so it must not degrade with age."""
    _run(tmp_path, harness)
    with sqlite3.connect(tmp_path / "txn.db") as conn:
        conn.row_factory = sqlite3.Row
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT identity_status, dg_player_id FROM league_transaction_movement "
                "WHERE league_id = ? AND asset_type = 'player'",
                (L2023,),
            )
        ]
    assert rows
    assert {r["identity_status"] for r in rows} == {CANONICAL_RESOLVED}
    assert all(r["dg_player_id"] for r in rows)


# --------------------------------------------------------------------------
# Idempotence by content, across the whole chain
# --------------------------------------------------------------------------


def test_recapturing_the_whole_chain_mutates_nothing(tmp_path, harness) -> None:
    """Verified by content, not row count: identical bytes across all three tables."""
    first = _run(tmp_path, harness)
    store = TransactionStore(tmp_path / "txn.db")
    fingerprint = store.content_fingerprint()
    assert sum(s["applied"]["inserted"] for s in first["seasons"]) == 932

    second = _run(tmp_path, harness)
    assert sum(s["applied"]["unchanged"] for s in second["seasons"]) == 932
    assert sum(s["applied"]["inserted"] + s["applied"]["updated"] for s in second["seasons"]) == 0
    assert store.content_fingerprint() == fingerprint, "a no-op re-capture rewrote rows"
    assert store.transaction_count() == 932


def test_the_store_records_which_seasons_it_holds(tmp_path, harness) -> None:
    """The store answers "what do you contain" without trusting a status marker that
    describes only the most recent run."""
    _run(tmp_path, harness)
    seasons = TransactionStore(tmp_path / "txn.db").seasons()
    assert [s["season"] for s in seasons] == ["2026", "2025", "2024", "2023"]
    assert {s["status"] for s in seasons} == {"ok"}
    assert sum(s["transactions_total"] for s in seasons) == 932
    live = next(s for s in seasons if s["season"] == "2026")
    assert live["legs_attempted"] == list(range(1, 19))
    assert live["legs_with_activity"] == [1]
    assert live["coverage"]["players_sleeper_only"] == 2


# --------------------------------------------------------------------------
# Partial or failed traversal writes a named failure — never inherits success
# --------------------------------------------------------------------------


def test_a_mid_chain_failure_does_not_leave_the_previous_success_standing(
    tmp_path, harness
) -> None:
    marker = status_marker_path(tmp_path / "runtime")
    _run(tmp_path, harness)
    assert json.loads(marker.read_text())["status"] == "ok"

    good_leg = harness["fetch_leg"]

    def exploding(league_id: str, leg: int):
        if league_id == L2024 and leg == 3:
            raise RuntimeError("sleeper 503")
        return good_leg(league_id, leg)

    with pytest.raises(Exception):
        _run(tmp_path, harness, fetch_leg=exploding)

    after = json.loads(marker.read_text())
    assert after["status"] == "failed", "a failed chain run must not inherit the prior ok"
    assert after["failed_stage"] == "fetch"
    assert after["failed_league_id"] == L2024
    assert after["failed_season"] == "2024"
    assert after["failed_leg"] == 3
    assert "sleeper 503" in after["reason"]
    # What DID land is stated, never inferred.
    assert [s["season"] for s in after["seasons_captured"]] == ["2026", "2025"]


def test_a_failed_season_is_recorded_as_failed_in_the_store(tmp_path, harness) -> None:
    def exploding(league_id: str, leg: int):
        if league_id == L2024:
            raise RuntimeError("sleeper 503")
        return harness["fetch_leg"](league_id, leg)

    with pytest.raises(Exception):
        _run(tmp_path, harness, fetch_leg=exploding)

    seasons = {s["season"]: s for s in TransactionStore(tmp_path / "txn.db").seasons()}
    assert seasons["2026"]["status"] == "ok"
    assert seasons["2025"]["status"] == "ok"
    assert seasons["2024"]["status"] == "failed"
    assert "sleeper 503" in seasons["2024"]["failure_reason"]
    assert "2023" not in seasons, "a season the run never reached must not appear as captured"


def test_a_broken_chain_fails_before_anything_is_fetched(tmp_path, harness) -> None:
    """Discovery precedes capture, so a partial history is never published as a whole one."""
    marker = status_marker_path(tmp_path / "runtime")
    fetched: list[str] = []

    def recording_leg(league_id: str, leg: int):
        fetched.append(league_id)
        return harness["fetch_leg"](league_id, leg)

    def broken(league_id: str):
        if league_id == L2024:
            return None
        return harness["fetch_league"](league_id)

    with pytest.raises(TransactionCaptureError):
        _run(tmp_path, harness, fetch_league=broken, fetch_leg=recording_leg)

    assert fetched == [], "legs were fetched despite an unwalkable chain"
    after = json.loads(marker.read_text())
    assert after["status"] == "failed"
    assert after["failed_stage"] == "chain_discovery"
    assert after["chain_complete"] is False
    assert after["seasons_captured"] == []
    assert not (tmp_path / "txn.db").exists(), "a store was created for a chain we cannot walk"


def test_a_start_record_is_written_before_chain_discovery(tmp_path, harness) -> None:
    marker = status_marker_path(tmp_path / "runtime")
    seen: list[dict[str, Any]] = []

    def observing(league_id: str):
        seen.append(json.loads(marker.read_text()))
        return harness["fetch_league"](league_id)

    _run(tmp_path, harness, fetch_league=observing)
    assert seen[0]["status"] == "running"
    assert seen[0]["phase"] == "chain_discovery"
    assert seen[0]["run_id"]


def test_a_resolver_that_cannot_be_built_is_a_named_failure(tmp_path, harness) -> None:
    marker = status_marker_path(tmp_path / "runtime")

    def broken_resolver(link: LeagueChainLink):
        if link.season == "2025":
            raise RuntimeError("rosters unavailable")
        return harness["build_resolver"](link)

    with pytest.raises(Exception):
        _run(tmp_path, harness, build_resolver=broken_resolver)

    after = json.loads(marker.read_text())
    assert after["status"] == "failed"
    assert after["failed_stage"] == "resolver"
    assert after["failed_season"] == "2025"


# --------------------------------------------------------------------------
# Cross-season collision safety
# --------------------------------------------------------------------------


def test_a_transaction_id_reused_across_leagues_refuses_rather_than_overwriting(
    tmp_path, base_resolver, chain_fixture
) -> None:
    """`transaction_id` is the primary key. Measured on the live chain: 932 transactions,
    zero collisions — so this is a synthetic probe of a real overwrite path. If Sleeper's
    uniqueness ever stops holding, one league-season's history must not silently replace
    another's."""
    leg = {"1": [dict(chain_fixture["legs"][L2023]["1"][0])]}
    resolver = base_resolver.with_managers(
        rosters=chain_fixture["rosters"][L2023], users=chain_fixture["users"][L2023]
    )
    store = TransactionStore(tmp_path / "txn.db")
    store.upsert(normalize_transactions(leg, league_id=L2023, season="2023", resolver=resolver))
    before = store.content_fingerprint()

    with pytest.raises(TransactionCaptureError) as exc:
        store.upsert(
            normalize_transactions(leg, league_id=L2024, season="2024", resolver=resolver)
        )
    assert "league_transaction_id_collision" in str(exc.value)
    assert store.content_fingerprint() == before, "the collision overwrote data before refusing"


def test_a_store_predating_the_multi_season_schema_fails_closed_by_name(tmp_path) -> None:
    """A v2 store has no `league_id` on its movements, so every row in it is ambiguous
    about which season's roster ids it uses. Refuse it by name rather than mixing schemas."""
    path = tmp_path / "v2.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE league_transaction (transaction_id TEXT PRIMARY KEY, league_id TEXT, "
            "season TEXT, leg TEXT, type TEXT, status TEXT, created_at TEXT, "
            "status_updated_at TEXT, creator_user_id TEXT, roster_ids TEXT, waiver_bid TEXT, "
            "raw_json TEXT, content_hash TEXT, ingested_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE league_transaction_movement (movement_key TEXT PRIMARY KEY, "
            "transaction_id TEXT, transaction_status TEXT, action TEXT)"
        )
    with pytest.raises(TransactionCaptureError) as exc:
        TransactionStore(path)
    assert "schema_mismatch" in str(exc.value)
    assert "league_id" in str(exc.value), "the failure must name the missing column"


# --------------------------------------------------------------------------
# Raw snapshots — one per season, replayable
# --------------------------------------------------------------------------


def test_each_season_writes_its_own_raw_snapshot_before_parsing(tmp_path, harness) -> None:
    """A timestamp-only filename would have four seasons overwrite each other at one
    `captured_at`, leaving the chain unreplayable."""
    status = _run(tmp_path, harness)
    paths = [Path(s["league_id"]) for s in status["seasons"]]
    assert len(paths) == 4
    raw_dir = tmp_path / "runtime" / "raw"
    files = sorted(raw_dir.glob("transactions_*.json"))
    assert len(files) == 4, f"expected one snapshot per season, got {[f.name for f in files]}"
    by_season = {}
    for file in files:
        payload = json.loads(file.read_text())
        by_season[payload["season"]] = payload
    assert set(by_season) == {"2026", "2025", "2024", "2023"}
    for season, payload in by_season.items():
        assert payload["legs_attempted"] == list(range(1, 19))
        assert payload["schema_version"].endswith("v3")
        total = sum(len(v) for v in payload["legs"].values())
        assert total > 0, f"{season} snapshot is empty"


def test_the_terminal_marker_states_the_chain_it_walked(tmp_path, harness) -> None:
    status = _run(tmp_path, harness)
    assert status["status"] == "ok"
    assert status["chain_complete"] is True
    assert status["seasons_in_chain"] == 4
    assert [c["season"] for c in status["chain"]] == ["2026", "2025", "2024", "2023"]
    assert status["seasons_in_store_not_in_this_run"] == []
    assert status["transactions_stored"] == 932
    assert status["movements_stored"] > 932
