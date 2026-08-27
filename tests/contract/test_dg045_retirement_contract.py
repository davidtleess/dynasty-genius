"""Contract: SR-09 step 7 — the retirement WITHOUT destroying the rollback.

Four plists retire (fc-snapshot, feature-refresh, league-capture,
what-changed-report), byte-identical, into ``ops/launchd/retired/`` next to the
pre-change snapshots and a README that forbids tidying the directory away before
the freeze lifts. The two SR-00 retry plists (market, model-pvo) are EDITED, not
retired — David's b-EXCEPTION ruling ("put it back up") — and their own
scheduler tests pin the surviving 11:30/14:00 entries.

The invariant that matters operationally: NO retired producer may have a plist
in the ACTIVE directory, or a future bootstrap double-runs it against the chain.
"""

from __future__ import annotations

from pathlib import Path

ACTIVE = Path("ops/launchd")
RETIRED = ACTIVE / "retired"

RETIRING = (
    "com.davidleess.dynasty-fc-snapshot.plist",
    "com.davidleess.dynasty-feature-refresh.plist",
    "com.davidleess.dynasty-league-capture.plist",
    "com.davidleess.dynasty-what-changed-report.plist",
)
SURVIVING_AS_RETRY_ONLY = (
    "com.davidleess.dynasty-market-divergence-refresh.plist",
    "com.davidleess.dynasty-model-pvo-refresh.plist",
)


def test_the_four_retired_plists_are_in_retired_and_not_active() -> None:
    for name in RETIRING:
        assert (RETIRED / name).is_file(), f"{name} missing from retired/"
        assert not (ACTIVE / name).exists(), f"{name} still active — would double-run"


def test_the_two_sr00_retry_plists_stay_active() -> None:
    for name in SURVIVING_AS_RETRY_ONLY:
        assert (ACTIVE / name).is_file(), f"{name} must survive (b-EXCEPTION)"
        assert not (RETIRED / name).exists(), f"{name} must NOT be retired"


def test_the_chain_plist_is_active() -> None:
    assert (ACTIVE / "com.davidleess.dynasty-daily-chain.plist").is_file()


def test_the_rollback_evidence_is_present() -> None:
    assert (RETIRED / "PRE-SR09-launchctl.txt").is_file()
    assert (RETIRED / "PRE-SR09-schedules.json").is_file()
    readme = RETIRED / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "freeze" in text.lower()
    assert "rollback" in text.lower()
