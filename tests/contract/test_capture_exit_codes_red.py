"""RED contract for SR-07: the two season-critical producers must be able to report failure.

`scripts/run_league_transaction_capture.py:175` and `scripts/run_nflverse_usage_capture.py:81`
are both a bare `return 0`, reached regardless of what `status` holds. These are the two jobs
installed 2026-08-20 to cover live waivers and weekly usage, and neither can tell launchd it
failed. Every other producer gates its exit — `run_market_divergence_refresh.py:737` and
`run_fc_forward_capture.py:108` are both `return 0 if report.get("status") == "ok" else 1`.

**The house pattern alone is NOT sufficient here, and that is the finding.** Measured live
2026-08-22 against a league that does not exist:

    run_league_transaction_capture.py --current-season-only --league-id 0
      -> status: "ok"   managers_total: 0   transactions_total: 0
         legs_with_activity: []   (all 18 legs empty)      EXIT 0

The capture's own self-assessment says "ok" after reaching nothing at all. So
`return 0 if status == "ok" else 1` would STILL exit 0 and SR-07's own verification block
(which requires that exact command to go non-zero) would still fail. The rule has to say what
"actually worked" means — SR-07 step 3, "put the rule in the code, not a comment".

**The discriminator is managers, not transactions.** A real league always has managers even in
a week with zero moves; David's shows 12/12/12/11 across the four chain seasons. Keying on
transaction count would fire falsely every year in the quiet stretch before anyone makes a move
— exactly the 2026-08-05..08-21 window this store just sat through legitimately.

Isolation is in scope on David's word (2026-08-22). `--db-path` redirects the DATABASE only;
`raw_root` — which carries BOTH the status marker and the raw snapshots — is never passed by
the runner, so it always resolves to production. Running SR-07's own verification command
overwrote the real morning marker with a league-0 result and left two junk raw files in
`app/data/league_transactions/raw/`. Any agent following the ticket verbatim does the same.
A redirected database must take its paperwork with it.
"""

from __future__ import annotations

from pathlib import Path

from scripts import run_league_transaction_capture as txn
from scripts import run_nflverse_usage_capture as nfl

# --------------------------------------------------------------------------
# Fixtures shaped from the REAL markers measured 2026-08-22, not invented
# --------------------------------------------------------------------------

HEALTHY_CHAIN = {
    "mode": "chain",
    "status": "ok",
    "chain_complete": True,
    "seasons_in_chain": 4,
    "transactions_stored": 938,
    "chain_coverage": {
        "by_season": {
            "2023": {"league_id": "912589367620100096", "managers_total": 12},
            "2024": {"league_id": "1049152209134424064", "managers_total": 12},
            "2025": {"league_id": "1183088915091423232", "managers_total": 12},
            "2026": {"league_id": "1314363401744416768", "managers_total": 11},
        }
    },
}

#: The exact shape `--league-id 0` produced. Every field measured, none invented.
LEAGUE_THAT_DOES_NOT_EXIST = {
    "status": "ok",
    "league_id": "0",
    "season": "2026",
    "managers_total": 0,
    "players_total": 0,
    "transactions_total": 0,
    "transactions_stored": 0,
    "movements_total": 0,
    "legs_with_activity": [],
    "legs_empty": list(range(1, 19)),
}

HEALTHY_SINGLE = {
    "status": "ok",
    "league_id": "1314363401744416768",
    "season": "2026",
    "managers_total": 11,
    "transactions_total": 73,
    "legs_with_activity": [1],
}


# --------------------------------------------------------------------------
# The transaction capture — what "actually worked" means
# --------------------------------------------------------------------------


def test_a_healthy_chain_capture_is_healthy() -> None:
    assert txn.capture_is_healthy(HEALTHY_CHAIN) is True


def test_a_league_that_does_not_exist_is_NOT_healthy() -> None:
    """SR-07's own verification case. Today this returns exit 0."""
    assert txn.capture_is_healthy(LEAGUE_THAT_DOES_NOT_EXIST) is False


def test_a_healthy_single_season_capture_is_healthy() -> None:
    assert txn.capture_is_healthy(HEALTHY_SINGLE) is True


def test_a_failed_status_is_not_healthy() -> None:
    assert txn.capture_is_healthy({**HEALTHY_CHAIN, "status": "failed"}) is False


def test_a_running_status_is_not_healthy() -> None:
    """A marker still reading `running` means the run died without a terminal write."""
    assert txn.capture_is_healthy({**HEALTHY_CHAIN, "status": "running"}) is False


def test_an_INCOMPLETE_chain_is_not_healthy() -> None:
    """SR-07 step 3: a partial must not exit 0 silently."""
    assert txn.capture_is_healthy({**HEALTHY_CHAIN, "chain_complete": False}) is False


def test_one_bad_season_inside_an_otherwise_good_chain_is_not_healthy() -> None:
    """Three seasons landing does not excuse the fourth reaching nobody."""
    broken = {
        **HEALTHY_CHAIN,
        "chain_coverage": {
            "by_season": {
                **HEALTHY_CHAIN["chain_coverage"]["by_season"],
                "2026": {"league_id": "1314363401744416768", "managers_total": 0},
            }
        },
    }
    assert txn.capture_is_healthy(broken) is False


def test_a_quiet_league_with_zero_transactions_is_STILL_healthy() -> None:
    """The false-alarm guard. 2026-08-05..08-21 had zero transactions and was fine.

    Keying health on transaction count would cry wolf every off-season.
    """
    quiet = {**HEALTHY_SINGLE, "transactions_total": 0, "legs_with_activity": []}
    assert txn.capture_is_healthy(quiet) is True


def test_a_chain_carrying_no_seasons_at_all_is_not_healthy() -> None:
    empty = {"mode": "chain", "status": "ok", "chain_complete": True,
             "chain_coverage": {"by_season": {}}}
    assert txn.capture_is_healthy(empty) is False


# --------------------------------------------------------------------------
# The nflverse capture
# --------------------------------------------------------------------------


def test_an_ok_nflverse_status_is_healthy() -> None:
    assert nfl.capture_is_healthy({"status": "ok"}) is True


def test_a_failed_nflverse_status_is_not_healthy() -> None:
    """Live 2026-08-22: contracts refused an upstream shape change; status was `failed`."""
    assert nfl.capture_is_healthy({"status": "failed", "failed_stream": "contracts"}) is False


def test_not_yet_available_skips_do_NOT_make_a_run_unhealthy() -> None:
    """Protects SR-06. Until week 1 most streams have no 2026, every single morning.

    If a recorded skip counted as failure the job would exit non-zero every day until
    2026-09-11, poisoning SR-09's dependency edges and SR-11's alert from the day they land.
    """
    with_skips = {
        "status": "ok",
        "results": [
            {"stream": "ngs_passing", "season": 2026,
             "skipped": "not_yet_available", "source_bound": 2025},
            {"stream": "depth_charts", "season": 2026, "applied": "inserted"},
        ],
    }
    assert nfl.capture_is_healthy(with_skips) is True


# --------------------------------------------------------------------------
# Isolation — a redirected database takes its paperwork with it
# --------------------------------------------------------------------------


def test_the_default_db_path_leaves_the_runtime_root_in_production() -> None:
    """No behaviour change for the 06:30 scheduled run, which passes no flags."""
    assert txn.resolve_raw_root(txn.DEFAULT_DB_PATH, None) == txn.DEFAULT_RAW_ROOT


def test_a_redirected_db_path_takes_the_marker_and_raw_snapshots_with_it(tmp_path) -> None:
    """The defect that corrupted the real marker on 2026-08-22."""
    probe = tmp_path / "probe.db"
    assert txn.resolve_raw_root(probe, None) == tmp_path


def test_an_explicit_runtime_root_wins_over_the_derivation(tmp_path) -> None:
    elsewhere = tmp_path / "somewhere_else"
    assert txn.resolve_raw_root(tmp_path / "probe.db", elsewhere) == elsewhere


def test_the_resolved_root_is_a_path_not_a_string(tmp_path) -> None:
    """status_marker_path() does Path(raw_root) / ... — a str would still work, but the
    contract is a Path and a caller should not have to know which."""
    assert isinstance(txn.resolve_raw_root(tmp_path / "probe.db", None), Path)
