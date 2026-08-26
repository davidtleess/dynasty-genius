"""RED — Layer 1 daily source control plane: manifest, preflight, controller.

David's directive (2026-08-07): "we have data sources: determine how to connect, ingest,
and refresh by each source... track which cannot be refreshed and require a manual
download. fill layer 1... assume we need everything refreshed DAILY - we can reduce
frequency after we learn more in layers 2 and 3."

Cockpit alignment 3-of-3 (Claude · Codex · Gemini) on F-A..F-E plus six acceptance
conditions. Repaired under Codex review findings F1-F8; see the notes at each site.

DELIBERATELY OUT OF SCOPE, per the alignment:
  * `contracts` materialization — a measured follow-up, not a proved build
  * installing any LaunchAgent — a David-gated machine change
  * any paid fetch, provider contact, or subscriber-data access
  * provider publication cadence — ABSENT from this gate by design; the local target is
    ours to choose and a vendor's schedule is never consulted

HISTORY OF THIS FILE: it was authored as the RED suite, when the module under test did
not exist and every test exercising it failed. GREEN has since landed, so both of those
statements are now false and the original wording is retained only as history. This is
now a REGRESSION AND CONTRACT suite: it is expected to pass, and a failure here is a
defect in the implementation, not the intended initial state.
"""
from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

MODULE = "src.dynasty_genius.sources.daily_control"

#: The five operational modes. `paid_gated` is NOT here — it is an execution gate on an
#: otherwise-automatic source, never a sixth ontology hiding whether a connection exists.
EXPECTED_MODES = frozenset(
    {"automatic", "manual_download", "static", "blocked", "prohibited"}
)

#: F4 — a refresh target is an ACQUISITION OBLIGATION. Modes that carry one:
MODES_WITH_REFRESH_TARGET = frozenset({"automatic", "manual_download", "blocked"})
#: ...and modes for which a cadence is meaningless and must be absent:
MODES_WITHOUT_REFRESH_TARGET = frozenset({"static", "prohibited"})

#: R1 — the COMPLETE owner+mode mapping. A partition proves every registry key is
#: claimed by SOMEONE; it does not prove it is claimed by the RIGHT owner. All 20
#: registry definitions are pinned to an acquisition family here.
#: family -> (mode, registry_sources it owns)
PINNED_FAMILIES: dict[str, tuple[str, tuple[str, ...]]] = {
    # automatic — real routes that exist and run
    "nflverse_usage_capture": ("automatic", ("nfl_nextgen_stats", "nflreadpy_qb_context")),
    "sleeper":                ("automatic", ("sleeper",)),
    "sleeper_transactions":   ("automatic", ()),   # family outside the registry
    "fantasycalc":            ("automatic", ("fantasycalc",)),
    "cfbd":                   ("automatic", ("cfbd",)),   # + paid gate
    # manual_download — a human fetches the bytes
    "footballguys":           ("manual_download", ("footballguys",)),
    "playerprofiler":         ("manual_download", ("playerprofiler",)),
    "pff":                    ("manual_download", ("pff",)),
    "rotoviz":                ("manual_download", ("rotoviz",)),
    "campus2canton":          ("manual_download", ("campus2canton",)),
    # blocked — no sanctioned acquisition route today
    "nfl_data_py":            ("blocked", ("nfl_data_py",)),  # provenance gap: the
    #     registry names a provider the code does not use (it imports nflreadpy)
    "ras":                    ("blocked", ("ras",)),
    "mfl_rookie_adp":         ("blocked", ("mfl_rookie_adp",)),
    "dynasty_data_lab":       ("blocked", ("dynasty_data_lab",)),
    "dynasty_nerds":          ("blocked", ("dynasty_nerds",)),
    # prohibited — must never be acquired into model inputs
    "ktc":                    ("prohibited", ("ktc",)),
    "sportradar":             ("prohibited", ("sportradar",)),
    "genius_sports":          ("prohibited", ("genius_sports",)),
    "stats_perform":          ("prohibited", ("stats_perform",)),
    "rolling_insights":       ("prohibited", ("rolling_insights",)),
    # static — a pinned study input that must never be auto-refreshed
    "nflreadpy_qb_validation": ("static", ("nflreadpy_qb_validation",)),
}

PINNED_MODES = {k: v[0] for k, v in PINNED_FAMILIES.items()}

#: V1 — exact automatic route TRIPLES: (command entrypoint, destination, success marker).
#: Commands alone let any truthy destination/marker pass. Paths are repo-relative and
#: compared normalized, so a fake string fails.
#: NOTE on fantasycalc: I first recorded this marker as absent. WRONG — withdrawn.
#: The checked-in plist passes `--report-path app/data/capture/fc_forward_capture_latest_report.json`;
#: run_fc_forward_capture.py:93-101 forwards it; fc_forward_capture_driver.py:126-128
#: persists it; `status="ok"` (:215) and `status="aborted"` (:166) both write it (:226, :171).
#: My search looked for `*status_latest*` on disk and grepped module source — it could
#: not find a file named `*_latest_report.json` whose path is configured in PLIST
#: ARGUMENTS. A configured producer path exists whether or not the file is on disk yet.
PINNED_AUTOMATIC_TRIPLES: dict[str, tuple[str, str, str | None]] = {
    "nflverse_usage_capture": (
        "scripts/run_nflverse_usage_capture.py",
        "app/data/nflverse_usage.db",
        "app/data/nflverse_usage/nflverse_usage_status_latest.json",
    ),
    "sleeper_transactions": (
        "scripts/run_league_transaction_capture.py",
        "app/data/league_transactions.db",
        "app/data/league_transactions/transaction_capture_status_latest.json",
    ),
    "sleeper": (
        "scripts/run_league_snapshot_capture.py",
        "app/data/league_runtime",
        "app/data/league_runtime/capture_status_latest.json",
    ),
    "cfbd": (
        "scripts/run_cfbd_foundation_refresh.py",
        "app/data/sources/cfbd_foundation",
        "app/data/sources/cfbd_foundation/status_latest.json",
    ),
    "fantasycalc": (
        "scripts/run_fc_forward_capture.py",
        "app/data/fc_forward_capture.db",
        "app/data/capture/fc_forward_capture_latest_report.json",
    ),
}

PINNED_AUTOMATIC_ROUTES = {k: v[0] for k, v in PINNED_AUTOMATIC_TRIPLES.items()}

#: V3 — a finite connection ontology. "x" must not satisfy it.
CONNECTION_METHODS = frozenset({
    "public_http_api", "public_file_release", "credentialed_http_api",
    "manual_export_download", "vendor_contract_required", "none",
})

#: R2 — expected connection method for EVERY manifest family. Each is evidence-backed
#: from the SOURCE_REGISTRY notes, quoted in the comment. Checking only that a value is
#: a legal enum member answers "is this a word we allow", not "how does this connect" —
#: and HOW EVERY SOURCE CONNECTS is the Layer 1 objective.
PINNED_CONNECTION_METHODS = {
    # --- automatic ---
    "nflverse_usage_capture": "public_file_release",     # nflverse parquet releases
    "sleeper":                "public_http_api",         # public Sleeper API
    "sleeper_transactions":   "public_http_api",         # same public API, transactions
    "fantasycalc":            "public_http_api",         # public FantasyCalc API
    "cfbd":                   "credentialed_http_api",   # API key + billed usage
    # --- manual_download ---
    "footballguys":           "manual_export_download",  # paid Draft Dominator bundle; ToS bars scraping
    "playerprofiler":         "manual_export_download",  # subscriber export button
    "pff":                    "manual_export_download",  # manual export payloads
    "rotoviz":                "manual_export_download",  # "Manual CSV export only. No public API."
    "campus2canton":          "manual_export_download",  # "CSV export from Player Metric Data Table"
    # --- blocked ---
    "nfl_data_py":            "public_file_release",     # parquet_snapshot; blocked on the
    #                                                      provenance gap, not on access
    "ras":                    "none",                    # no production acquisition route
    "mfl_rookie_adp":         "public_http_api",         # "Public documented MFL ADP API"
    "dynasty_data_lab":       "credentialed_http_api",   # "$4 per 1000 requests"
    "dynasty_nerds":          "none",                    # "No clean public API. Deferred."
    # --- prohibited ---
    "ktc":                    "none",                    # "ToS explicitly prohibits scraping"
    "sportradar":             "vendor_contract_required",  # "Enterprise B2B only. ~$7200/year"
    "genius_sports":          "vendor_contract_required",  # "Enterprise pricing."
    "stats_perform":          "vendor_contract_required",  # "enterprise clients"
    "rolling_insights":       "vendor_contract_required",  # "$4200/year post-game"
    # --- static ---
    "nflreadpy_qb_validation": "public_file_release",    # parquet_snapshot study pin
}

#: R3 — PlayerProfiler's five report families arrive through FOUR real import CLIs.
#: One substring importer understates the route.
PINNED_PLAYERPROFILER_IMPORTERS = (
    "scripts/run_playerprofiler_ingest.py",
    "scripts/run_playerprofiler_gamelog_ingest.py",
    "scripts/run_playerprofiler_pbp_ingest.py",
    "scripts/run_playerprofiler_roster_ingest.py",
)

#: R6 — externally-scheduled families name their CHECKED-IN plist, asserted to exist.
PINNED_SCHEDULER_EVIDENCE = {
    "fantasycalc": "ops/launchd/com.davidleess.dynasty-fc-snapshot.plist",
    "sleeper":     "ops/launchd/com.davidleess.dynasty-league-capture.plist",
}

#: R4 — one stable aggregate report path. A random timestamped file cannot be the
#: canonical status contract.
REPORT_FILENAME = "layer1_daily_control_latest.json"

#: F7 — families whose scheduling is owned by an EXISTING checked-in plist, which the
#: controller must not duplicate.
EXTERNALLY_SCHEDULED = {"fantasycalc", "sleeper"}

#: F1 — acquisition families the controller owns because nothing schedules them today.
CONTROLLER_OWNED = {"nflverse_usage_capture", "sleeper_transactions"}


def _mod():
    """Import the module under test, FAILING (never skipping) when it is absent.

    A RED that SKIPS is worse than no RED: it passes vacuously, so a GREEN could be
    declared without a line of implementation. The first draft used
    `pytest.importorskip` and produced 18 skips / 0 failures — caught before review.
    A module-level import would raise a COLLECTION ERROR, which the standing repo
    invariant forbids, so the import is deferred here and converted to a failure.
    """
    try:
        return importlib.import_module(MODULE)
    except ImportError as exc:  # pragma: no cover - the RED state
        pytest.fail(f"{MODULE} is not implemented yet: {exc}", pytrace=False)


def _by_source(m):
    return {e.source: e for e in m.build_manifest()}


# ---------------------------------------------------------------- manifest coverage


def test_every_registry_key_is_covered_exactly_once_across_acquisition_families():
    """F1 — a registry DEFINITION is not an acquisition FAMILY.

    One canonical route (the nflverse capture) legitimately serves several registry
    definitions. Requiring each registry key to be its own `entry.source` would invent
    duplicate jobs for one route. Coverage is therefore proved by FLATTENING each
    entry's `registry_sources`, which must partition the registry exactly.
    """
    from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

    m = _mod()
    manifest = m.build_manifest()

    registry_names = set(
        SOURCE_REGISTRY.keys() if hasattr(SOURCE_REGISTRY, "keys")
        else (d.name for d in SOURCE_REGISTRY)
    )

    flat: list[str] = []
    for e in manifest:
        flat.extend(e.registry_sources)

    missing = registry_names - set(flat)
    assert not missing, f"registry definitions covered by no family: {sorted(missing)}"

    unknown = set(flat) - registry_names
    assert not unknown, f"registry_sources naming non-registry keys: {sorted(unknown)}"

    dupes = {n for n in flat if flat.count(n) > 1}
    assert not dupes, f"registry definitions claimed by more than one family: {sorted(dupes)}"


def test_acquisition_families_outside_the_registry_are_first_class_entries():
    """No prose-only orphan route. These are real acquisition families the registry
    does not enumerate as definitions of their own."""
    m = _mod()
    names = set(_by_source(m))
    for required in ("sleeper_transactions", "nflverse_usage_capture"):
        assert required in names, f"acquisition family missing from manifest: {required}"


def test_family_names_are_unique():
    m = _mod()
    names = [e.source for e in m.build_manifest()]
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"duplicate acquisition families: {sorted(dupes)}"


# -------------------------------------------------------------------- mode ontology


def test_modes_are_exactly_the_five_and_paid_gated_is_not_a_mode():
    m = _mod()
    assert set(m.MODES) == set(EXPECTED_MODES)
    assert "paid_gated" not in set(m.MODES), (
        "paid_gated is an EXECUTION GATE on an automatic source, not a sixth mode"
    )
    for e in m.build_manifest():
        assert e.mode in EXPECTED_MODES, f"{e.source}: illegal mode {e.mode!r}"


def test_complete_owner_and_mode_mapping_is_pinned():
    """R1 — a partition proves every registry key is claimed by SOMEONE; it does not
    prove it is claimed by the RIGHT owner. All 20 definitions are pinned here."""
    m = _mod()
    entries = _by_source(m)
    for family, (expected_mode, owned) in PINNED_FAMILIES.items():
        assert family in entries, f"pinned family absent from manifest: {family}"
        e = entries[family]
        assert e.mode == expected_mode, (
            f"{family}: expected mode {expected_mode!r}, got {e.mode!r}"
        )
        assert set(e.registry_sources) == set(owned), (
            f"{family}: expected to own {sorted(owned)}, got {sorted(e.registry_sources)}"
        )


def test_pinned_families_account_for_every_registry_definition():
    """R1 — the pinned map itself must be complete, or the pin proves less than it looks."""
    from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

    registry_names = set(
        SOURCE_REGISTRY.keys() if hasattr(SOURCE_REGISTRY, "keys")
        else (d.name for d in SOURCE_REGISTRY)
    )
    pinned = {r for _, owned in PINNED_FAMILIES.values() for r in owned}
    assert pinned == registry_names, (
        f"pinned map incomplete; missing {sorted(registry_names - pinned)}, "
        f"unknown {sorted(pinned - registry_names)}"
    )


def test_cfbd_is_automatic_with_a_paid_gate_not_a_separate_mode():
    m = _mod()
    cfbd = _by_source(m)["cfbd"]
    assert cfbd.mode == "automatic", "cost is a gate; it must not disguise the mode"
    assert cfbd.paid_gated is True, "cfbd bills per run"


# ------------------------------------------------------------- entry completeness


def test_automatic_entries_name_command_destination_and_success_marker():
    m = _mod()
    for e in m.build_manifest():
        if e.mode != "automatic":
            continue
        assert e.command, f"{e.source}: automatic entry with no command"
        assert e.destination, f"{e.source}: automatic entry with no destination"
        assert e.success_marker, f"{e.source}: automatic entry with no success marker"


def test_manual_entries_either_name_their_route_or_name_the_missing_piece():
    """F3 — requiring an importer for every manual source would force GREEN to INVENT
    routes that do not exist. A missing piece is a legitimate, reportable state; what is
    forbidden is silence about which piece is missing."""
    m = _mod()
    manual = [e for e in m.build_manifest() if e.mode == "manual_download"]
    assert manual, "PlayerProfiler and PFF are manual — the manifest must say so"

    for e in manual:
        status = m.entry_status(e)
        if not e.drop_location:
            assert "missing_drop_location" in status.missing, (
                f"{e.source}: absent drop location must be named precisely"
            )
        if not e.importer:
            assert "missing_importer" in status.missing, (
                f"{e.source}: absent importer must be named precisely"
            )


def test_status_names_the_exact_missing_piece_for_an_incomplete_automatic_entry():
    m = _mod()
    broken = m.ManifestEntry(
        source="synthetic_incomplete",
        mode="automatic",
        registry_sources=(),
        refresh_target="daily",
        command=None,
        destination="app/data/nowhere.db",
        success_marker="app/data/ops/nowhere.json",
    )
    status = m.entry_status(broken)
    assert status.ok is False
    assert "missing_command" in status.missing, (
        f"status must name the missing piece; got {status.missing!r}"
    )


# ---------------------------------------------------------------- refresh targets


def test_refresh_target_matches_what_the_source_can_actually_change():
    """F4, UPDATED 2026-08-08 after David's follow-up ruling.

    The original form required `daily` for EVERY obligation-bearing mode, from his directive
    "assume we need everything refreshed DAILY - we can reduce frequency after we learn more in
    layers 2 and 3". That was correct as a placeholder when we knew nothing about these sources.

    We have now learned, and he asked directly: "why are my manual ones due? look at the data - what
    could possibly have changed?" Measured answer: PFF and PlayerProfiler hold season-complete data
    through 2025, no in-scope 2026 regular-season event has occurred, and our own importer returned
    `unchanged` for all six gamelog and all six pbp seasons. A daily clock on a seasonal source
    manufactures an obligation no vendor data can satisfy.

    So `manual_download` now carries `windowed`, with the real per-stream cadence declared in
    `sources/feed_cadence.py`. `automatic` and `blocked` keep `daily` — the placeholder still
    stands where we have not measured otherwise. A `static` pin or a `prohibited` source still has
    no cadence at all, and asserting one is fiction.
    """
    m = _mod()
    for e in m.build_manifest():
        if e.mode == "manual_download":
            # F3 — a source with NO inventory and no marker cannot assert a determined window.
            # RotoViz and Campus2Canton hold nothing, so `windowed` there would be fiction.
            expected = "windowed" if e.source in {"pff", "playerprofiler"} else "undetermined"
            assert e.refresh_target == expected, (
                f"{e.source}: expected {expected!r}; a manual seasonal source is windowed and an "
                "uninventoried one is undetermined — neither is daily"
            )
        elif e.mode in MODES_WITH_REFRESH_TARGET:
            assert e.refresh_target == "daily", (
                f"{e.source} ({e.mode}): David's assume-daily still applies to this obligation"
            )
        elif e.mode in MODES_WITHOUT_REFRESH_TARGET:
            assert e.refresh_target is None, (
                f"{e.source} ({e.mode}): a refresh cadence here is fictional"
            )


def test_paid_gated_source_still_carries_the_daily_target():
    """F-E: daily TARGET honours the directive; the gate protects the wallet."""
    m = _mod()
    assert _by_source(m)["cfbd"].refresh_target == "daily"


# ------------------------------------------------------------------------ preflight


def test_preflight_makes_no_network_call(monkeypatch):
    m = _mod()
    import socket

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("preflight attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", _boom, raising=False)
    monkeypatch.setattr(socket, "create_connection", _boom, raising=False)
    m.preflight(manifest=m.build_manifest())


def test_preflight_spawns_no_subprocess(monkeypatch):
    """F6 — a socket guard alone is porous: a route could shell out and fetch."""
    m = _mod()
    import subprocess

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("preflight spawned a subprocess")

    monkeypatch.setattr(subprocess, "run", _boom, raising=False)
    monkeypatch.setattr(subprocess, "Popen", _boom, raising=False)
    monkeypatch.setattr(subprocess, "check_output", _boom, raising=False)
    m.preflight(manifest=m.build_manifest())


def test_preflight_writes_nothing(tmp_path):
    m = _mod()
    probe = tmp_path / "probe"
    probe.mkdir()
    before = sorted(p.name for p in probe.iterdir())
    m.preflight(manifest=m.build_manifest(), report_root=probe)
    assert sorted(p.name for p in probe.iterdir()) == before, "preflight wrote files"


def test_preflight_reports_the_paid_gate_without_executing_it():
    m = _mod()
    report = m.preflight(manifest=m.build_manifest())
    assert "cfbd" in {g.source for g in report.gated}


# ---------------------------------------------------------------- execution semantics


def test_default_execute_skips_paid_gated_without_failing(tmp_path):
    m = _mod()
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    cfbd = result.by_source["cfbd"]
    assert cfbd.state == "skipped_paid_gate"
    assert cfbd.failed is False, "a skipped paid gate is not a failure"


def test_default_execute_never_runs_non_automatic_modes(tmp_path):
    m = _mod()
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    for e in m.build_manifest():
        if e.mode != "automatic":
            assert result.by_source[e.source].state != "executed", (
                f"{e.source} is {e.mode} and must never be executed by default"
            )


def test_one_source_failure_does_not_prevent_other_independent_sources(tmp_path):
    """The CH1 lesson: a missing input must not cap every other stream."""
    m = _mod()

    def _runner(entry):
        if entry.source == "nflverse_usage_capture":
            raise RuntimeError("synthetic failure")
        return m.SourceResult(source=entry.source, state="executed", failed=False)

    result = m.execute(
        manifest=m.build_manifest(), report_root=tmp_path, runner=_runner
    )
    assert result.by_source["nflverse_usage_capture"].failed is True
    assert result.by_source["sleeper_transactions"].state == "executed"


def test_aggregate_exit_is_nonzero_when_any_automatic_source_failed(tmp_path):
    m = _mod()

    def _runner(entry):
        raise RuntimeError("synthetic failure")

    result = m.execute(
        manifest=m.build_manifest(), report_root=tmp_path, runner=_runner
    )
    assert result.exit_code != 0


def test_controller_owns_the_unscheduled_routes_and_not_the_externally_scheduled_ones():
    """F7 — ownership is DECLARED, never derived from mutable host state; and this test
    now names exactly what it checks rather than overstating a count."""
    m = _mod()
    entries = _by_source(m)
    owned = {e.source for e in m.build_manifest() if e.controller_owned}

    for family in CONTROLLER_OWNED:
        assert family in owned, f"{family} has no scheduler; the controller must own it"

    for family in EXTERNALLY_SCHEDULED:
        assert family not in owned, (
            f"{family} already has a checked-in plist; owning it would double-pull"
        )
        assert entries[family].scheduler_evidence, (
            f"{family} is externally scheduled and must name its checked-in plist"
        )


# --------------------------------------------------------- manual due/current semantics


def test_every_manual_entry_is_non_running_non_failing_and_accounted_for(tmp_path):
    """F8 — applies to EVERY manual family, not just PlayerProfiler. A stale manual
    source is an ACQUISITION OBLIGATION, never a job failure."""
    m = _mod()
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)

    manual = [e for e in m.build_manifest() if e.mode == "manual_download"]
    assert manual
    for e in manual:
        r = result.by_source[e.source]
        assert r.failed is False, f"{e.source}: manual staleness is not a job failure"
        assert r.state in ("manual_due", "manual_current", "manual_route_incomplete",
         "manual_undetermined", "manual_not_due")
        if r.state == "manual_route_incomplete":
            assert r.missing, f"{e.source}: must name the missing route component"
        else:
            # The vintage age comes from a marker under a GITIGNORED data directory, so
            # it exists on a machine that has ingested and NOT in CI or a fresh clone.
            # Requiring it unconditionally made this contract assert against local
            # machine state — it passed here and failed in CI, which is the defect CI
            # caught. Assert the INVARIANT that holds everywhere: when the marker is
            # present the age must be reported; when it is absent the state is honestly
            # unknown rather than invented.
            marker = Path(e.success_marker) if e.success_marker else None
            if marker is not None and marker.exists():
                assert r.age_days is not None, (
                    f"{e.source}: marker present, so the vintage age must be reported"
                )
            else:
                # NON-CLAIMS ONLY. `unknown` (no evidence) and `undetermined` (obligation
                # uncomputable) both decline to assert a vintage; `current`, `due` and `not_due`
                # are positive claims and stay forbidden. This branch is CI-ONLY on a developer
                # machine — the marker exists locally, so only the `if` side ever runs here, and
                # the vocabulary change that broke it was invisible to a local full-suite pass.
                assert r.age_days is None, (
                    f"{e.source}: no marker on disk, so age must not be invented"
                )
                assert r.freshness in ("unknown", "undetermined"), (
                    f"{e.source}: no marker on disk, so freshness must be a NON-CLAIM; "
                    f"got {r.freshness!r}"
                )


# -------------------------------------------------------------------- atomic report


def test_report_is_valid_json_and_leaves_no_temp_file(tmp_path):
    m = _mod()
    m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    reports = list(tmp_path.glob("*.json"))
    assert reports, "execute must emit an aggregate report"
    assert "by_source" in json.loads(reports[0].read_text())
    assert not list(tmp_path.glob("*.tmp")), "temp file left behind"


def test_report_write_is_behaviourally_atomic(tmp_path, monkeypatch):
    """F5 — a source grep for `.replace(` is a proxy, not proof. Preseed the final
    report, make the rename fail, and require the original bytes to survive intact."""
    m = _mod()
    import os

    m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    final = sorted(tmp_path.glob("*.json"))[0]
    sentinel = b'{"sentinel": "untouched"}'
    final.write_bytes(sentinel)

    def _boom(*a, **k):
        raise OSError("synthetic rename failure")

    monkeypatch.setattr(os, "replace", _boom, raising=False)
    with pytest.raises(OSError):
        m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)

    assert final.read_bytes() == sentinel, (
        "a failed rename must leave the previous report byte-intact — the write was "
        "not atomic"
    )


def test_report_carries_every_manifest_source(tmp_path):
    m = _mod()
    manifest = m.build_manifest()
    result = m.execute(manifest=manifest, report_root=tmp_path, dry_run=True)
    assert set(result.by_source) == {e.source for e in manifest}, (
        "the report must account for every source, including ones it did not run"
    )


# ---------------------------------------------------------------- cadence discipline


def test_no_provider_publication_cadence_field_exists_on_any_entry():
    """R5/R6 — assert absence of the FIELD, via dataclasses.fields rather than vars so a
    slotted implementation is not accidentally forbidden."""
    import dataclasses

    m = _mod()
    banned = {"source_publish_cadence", "publish_cadence", "provider_cadence",
              "source_publish"}
    for e in m.build_manifest():
        names = {f.name for f in dataclasses.fields(e)}
        present = banned & names
        assert not present, (
            f"{e.source}: provider publication cadence is outside this gate; "
            f"found {sorted(present)}"
        )


def test_no_provider_publication_key_is_serialized_into_the_report(tmp_path):
    """R6 — recurse KEYS only. Scanning the whole JSON blob would also match a value
    that legitimately quotes the phrase, e.g. a note explaining the exclusion."""
    m = _mod()
    m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    payload = json.loads((tmp_path / REPORT_FILENAME).read_text())

    banned = {"source_publish_cadence", "publish_cadence", "provider_cadence",
              "source_publish"}
    seen: list[str] = []

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                seen.append(k)
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(payload)
    hits = banned & set(seen)
    assert not hits, f"provider publication keys serialized into the report: {sorted(hits)}"


def test_externally_scheduled_families_name_a_checked_in_plist_that_exists():
    """R6 — replaces a source grep for 'LaunchAgents', which recreated the very proxy
    defect F5 removed and would have missed launchctl or any other host probe. Pin the
    real checked-in evidence and assert it is on disk."""
    m = _mod()
    entries = _by_source(m)
    for family, plist in PINNED_SCHEDULER_EVIDENCE.items():
        e = entries[family]
        assert e.scheduler_evidence == plist, (
            f"{family}: expected scheduler evidence {plist!r}, got {e.scheduler_evidence!r}"
        )
        assert Path(plist).is_file(), f"{family}: checked-in plist missing at {plist}"


# ============================ R2 — execute must OBEY controller_owned ================


def test_default_execute_calls_exactly_the_controller_owned_routes(tmp_path):
    """R2 — `controller_owned` was metadata the executor was never required to honour.
    A GREEN could mark FantasyCalc external and still call it, double-pulling. Record
    what the runner is actually handed."""
    m = _mod()
    called: list[str] = []

    def _recording_runner(entry):
        called.append(entry.source)
        return m.SourceResult(source=entry.source, state="executed", failed=False)

    m.execute(manifest=m.build_manifest(), report_root=tmp_path, runner=_recording_runner)

    assert set(called) == set(CONTROLLER_OWNED), (
        f"default execute must invoke exactly {sorted(CONTROLLER_OWNED)}; got {sorted(called)}"
    )
    for external in EXTERNALLY_SCHEDULED:
        assert external not in called, f"{external} already has a plist — double pull"
    assert "cfbd" not in called, "paid source must not be invoked by default"


def test_explicit_selection_of_an_owned_route_works(tmp_path):
    """R2 — selection must be possible for tests/operations without widening the default."""
    m = _mod()
    called: list[str] = []

    def _recording_runner(entry):
        called.append(entry.source)
        return m.SourceResult(source=entry.source, state="executed", failed=False)

    m.execute(
        manifest=m.build_manifest(),
        report_root=tmp_path,
        runner=_recording_runner,
        only=("sleeper_transactions",),
    )
    assert called == ["sleeper_transactions"]


def test_explicit_selection_cannot_force_a_non_owned_or_paid_route(tmp_path):
    """R2 — selection is a narrowing tool, never an escape hatch onto a paid or
    externally-scheduled route."""
    m = _mod()
    called: list[str] = []

    def _recording_runner(entry):
        called.append(entry.source)
        return m.SourceResult(source=entry.source, state="executed", failed=False)

    for forbidden in {"cfbd", *EXTERNALLY_SCHEDULED}:
        m.execute(
            manifest=m.build_manifest(),
            report_root=tmp_path,
            runner=_recording_runner,
            only=(forbidden,),
        )
        assert forbidden not in called, (
            f"{forbidden} must not be invocable via selection without an explicit gate"
        )


# ================== R3 — exact routes, real paths, connection method ================


def test_automatic_routes_pin_exact_command_destination_and_marker_triples():
    """V1 — commands alone left destination and marker satisfiable by any truthy string."""
    import os

    m = _mod()
    entries = _by_source(m)

    def _norm(v):
        return os.path.normpath(str(v)).lstrip("./")

    for family, (cmd, dest, marker) in PINNED_AUTOMATIC_TRIPLES.items():
        e = entries[family]
        assert cmd in " ".join(e.command), (
            f"{family}: expected command to invoke {cmd}; got {e.command!r}"
        )
        assert Path(cmd).is_file(), f"{family}: entrypoint missing at {cmd}"
        assert _norm(e.destination) == _norm(dest), (
            f"{family}: expected destination {dest!r}, got {e.destination!r}"
        )
        assert _norm(e.success_marker) == _norm(marker), (
            f"{family}: expected marker {marker!r}, got {e.success_marker!r}"
        )


def test_connection_method_is_pinned_for_every_manifest_family():
    """R2 — a 7-of-20 map proved almost nothing: the rest only had to be *some* legal
    enum value. HOW EVERY SOURCE CONNECTS is the Layer 1 objective, so the pin must be
    total and the test must prove totality rather than assume it."""
    m = _mod()
    entries = _by_source(m)

    assert set(PINNED_CONNECTION_METHODS) == set(entries), (
        "the connection-method pin must cover exactly the manifest families; missing "
        f"{sorted(set(entries) - set(PINNED_CONNECTION_METHODS))}, unknown "
        f"{sorted(set(PINNED_CONNECTION_METHODS) - set(entries))}"
    )

    for e in m.build_manifest():
        assert e.connection_method in CONNECTION_METHODS, (
            f"{e.source}: illegal connection method {e.connection_method!r}"
        )
    for family, expected in PINNED_CONNECTION_METHODS.items():
        assert entries[family].connection_method == expected, (
            f"{family}: expected {expected!r}, got {entries[family].connection_method!r}"
        )


def test_playerprofiler_importers_are_an_explicit_collection_of_the_four_clis():
    """V3 — an explicit collection, not a singular substring match."""
    m = _mod()
    pp = _by_source(m)["playerprofiler"]
    assert isinstance(pp.importer, (list, tuple)), (
        f"playerprofiler serves five report families through four CLIs; importer must be "
        f"a collection, got {type(pp.importer).__name__}"
    )
    declared = {str(x) for x in pp.importer}
    assert declared == set(PINNED_PLAYERPROFILER_IMPORTERS), (
        f"expected exactly the four CLIs; got {sorted(declared)}"
    )
    for cli in PINNED_PLAYERPROFILER_IMPORTERS:
        assert Path(cli).is_file(), f"importer entrypoint missing at {cli}"


def test_pff_declares_a_REAL_importer_that_exists_on_disk():
    """V3 — the anti-fiction contract, updated to the measured fact.

    This test previously required PFF to declare NO importer, because none existed and inventing
    one would have been a fiction the manifest then carried as fact. That premise is now false:
    `scripts/run_pff_intake.py` exists, runs, and has indexed the real archive. The intent is
    unchanged — a declared importer must never be a fiction — so the assertion inverts from
    "declare nothing" to "declare exactly the truth", the same shape as the PlayerProfiler test
    above.

    Exact tuple equality is deliberate. A bare string satisfies `in` by SUBSTRING membership and
    is iterated CHARACTER BY CHARACTER by entry_status, which produced 23 phantom
    `importer_not_found:<char>` errors while a substring assertion passed happily.
    """
    m = _mod()
    pff = _by_source(m)["pff"]
    assert pff.importer == ("scripts/run_pff_intake.py",), (
        f"the pff importer must be exactly that one-tuple; got {pff.importer!r}"
    )
    for cli in pff.importer:
        assert Path(cli).is_file(), f"declared importer entrypoint missing at {cli}"
    status = m.entry_status(pff)
    assert status.ok is True, f"the pff route must be complete; missing={status.missing!r}"
    assert status.blocking is False, "a manual route is never blocking"
    assert not any("importer" in x for x in status.missing), (
        f"no importer component may be reported missing; got {status.missing!r}"
    )


# ==================== R4 — stable report path + honest freshness ====================


def test_aggregate_report_is_written_to_one_stable_pinned_path(tmp_path):
    """R4 — a random timestamped filename cannot be the canonical status contract."""
    m = _mod()
    m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    final = tmp_path / REPORT_FILENAME
    assert final.is_file(), (
        f"aggregate report must land at the stable path {REPORT_FILENAME}; "
        f"found {[p.name for p in tmp_path.iterdir()]}"
    )


def test_every_source_result_carries_checked_at_and_nullable_last_success(tmp_path):
    """R4 — freshness must be answerable per source, and honestly unknown when unknown."""
    m = _mod()
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    for source, r in result.by_source.items():
        assert r.checked_at, f"{source}: no checked_at"
        assert hasattr(r, "last_success_at"), f"{source}: no last_success_at field"
        assert r.freshness in ("current", "due", "unknown", "undetermined", "not_due"), (
            f"{source}: freshness must be current|due|unknown, got {r.freshness!r}"
        )
        if r.last_success_at is None:
            # NON-CLAIMS only. `unknown` and `undetermined` both decline to assert a vintage —
            # unknown means we have no evidence, undetermined means the obligation is uncomputable.
            # `current`, `due` and `not_due` are all positive claims and remain forbidden here,
            # so this guard keeps its teeth while admitting the second vocabulary.
            assert r.freshness in ("unknown", "undetermined"), (
                f"{source}: no known success but freshness CLAIMS {r.freshness!r}"
            )


# ============ R5 — preflight must not write ANYWHERE, not just report_root ==========


def test_preflight_cannot_reach_the_module_writer(monkeypatch):
    """R5 — snapshotting report_root only proved preflight did not write THERE."""
    m = _mod()

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("preflight invoked the writer")

    assert hasattr(m, "write_report"), (
        "the module must expose a single named writer so preflight's read-only "
        "property is provable rather than assumed"
    )
    monkeypatch.setattr(m, "write_report", _boom)
    m.preflight(manifest=m.build_manifest())


def test_preflight_uses_no_filesystem_mutation_path_at_all(monkeypatch):
    """V4 — the named-writer guard is bypassable: a GREEN could call Path.write_text
    directly and still satisfy it. Close every mutation route."""
    m = _mod()
    import os

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("preflight mutated the filesystem")

    for attr in ("write_text", "write_bytes", "touch", "mkdir", "unlink", "replace",
                 "rename"):
        monkeypatch.setattr(Path, attr, _boom, raising=False)
    monkeypatch.setattr(os, "replace", _boom, raising=False)
    monkeypatch.setattr(os, "rename", _boom, raising=False)
    monkeypatch.setattr(os, "remove", _boom, raising=False)

    m.preflight(manifest=m.build_manifest())


# ============ V2 — the DEFAULT runner must actually launch something ================


def _patch_subprocess(monkeypatch, m, returncode=0, recorder=None):
    """Mock the module's subprocess boundary and record the call."""
    import subprocess

    class _Completed:
        def __init__(self, args, returncode):
            self.args = args
            self.returncode = returncode
            self.stdout = b""
            self.stderr = b""

    def _fake_run(args, **kwargs):
        if recorder is not None:
            recorder.append((args, kwargs))
        return _Completed(args, returncode)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr(m, "subprocess", subprocess, raising=False)
    return recorder


def test_default_runner_actually_invokes_the_pinned_entrypoint(tmp_path, monkeypatch):
    """V2 — every prior execution test injected a runner or used dry_run, so a GREEN
    could return state='executed' having launched nothing at all."""
    m = _mod()
    calls: list = []
    _patch_subprocess(monkeypatch, m, returncode=0, recorder=calls)

    m.execute(manifest=m.build_manifest(), report_root=tmp_path)

    assert calls, "the default runner launched no subprocess"
    launched = " ".join(" ".join(map(str, a)) for a, _ in calls)
    for family in CONTROLLER_OWNED:
        script = PINNED_AUTOMATIC_TRIPLES[family][0]
        assert script in launched, f"{family}: default runner never invoked {script}"


def test_default_runner_uses_argv_without_a_shell_and_bounds_the_call(tmp_path, monkeypatch):
    """V2 — argv form (no shell) and a bounded timeout; an unbounded daily job can hang
    forever and silently stop refreshing everything behind it."""
    m = _mod()
    calls: list = []
    _patch_subprocess(monkeypatch, m, returncode=0, recorder=calls)
    m.execute(manifest=m.build_manifest(), report_root=tmp_path)

    for args, kwargs in calls:
        assert isinstance(args, (list, tuple)), f"argv must be a sequence, got {args!r}"
        assert kwargs.get("shell", False) is False, "must never run through a shell"
        assert kwargs.get("timeout"), "each source call must be time-bounded"


def test_nonzero_exit_marks_that_source_failed_and_fails_the_aggregate(tmp_path, monkeypatch):
    m = _mod()
    _patch_subprocess(monkeypatch, m, returncode=3, recorder=[])
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path)

    for family in CONTROLLER_OWNED:
        assert result.by_source[family].failed is True, (
            f"{family}: nonzero exit must mark the source failed"
        )
    assert result.exit_code != 0, "aggregate must fail when an owned source failed"


def test_zero_exit_marks_success(tmp_path, monkeypatch):
    m = _mod()
    _patch_subprocess(monkeypatch, m, returncode=0, recorder=[])
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path)
    for family in CONTROLLER_OWNED:
        r = result.by_source[family]
        assert r.failed is False and r.state == "executed"
    assert result.exit_code == 0


def test_default_runner_isolation_one_failure_still_runs_the_other_owned_route(
    tmp_path, monkeypatch
):
    """V2 — isolation must hold through the REAL runner, not only an injected one."""
    m = _mod()
    import subprocess

    seen: list[str] = []

    class _Completed:
        def __init__(self, args, returncode):
            self.args, self.returncode = args, returncode
            self.stdout = self.stderr = b""

    def _fake_run(args, **kwargs):
        joined = " ".join(map(str, args))
        seen.append(joined)
        if PINNED_AUTOMATIC_TRIPLES["nflverse_usage_capture"][0] in joined:
            raise subprocess.SubprocessError("synthetic launch failure")
        return _Completed(args, 0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path)

    other = PINNED_AUTOMATIC_TRIPLES["sleeper_transactions"][0]
    assert any(other in s for s in seen), (
        "the second owned route must still be attempted after the first fails"
    )
    assert result.by_source["nflverse_usage_capture"].failed is True
    assert result.by_source["sleeper_transactions"].failed is False


# ================ G1 — preflight must VERIFY routes, not just presence ==============


def test_preflight_rejects_a_route_whose_command_does_not_exist():
    """G1 — presence of a string is not existence of a route. A fabricated path
    previously returned ok=True, so preflight certified a route that cannot run."""
    m = _mod()
    fake = m.ManifestEntry(
        source="synthetic_fake_route",
        mode="automatic",
        refresh_target="daily",
        connection_method="public_http_api",
        command=("/definitely/not/a/real/interpreter", "/definitely/not/a/real/script.py"),
        destination="app/data/nowhere.db",
        success_marker="app/data/ops/nowhere.json",
    )
    status = m.entry_status(fake)
    assert status.ok is False
    assert any("command_not_found" in x for x in status.missing), (
        f"a nonexistent command must be reported; got {status.missing!r}"
    )


def test_preflight_rejects_a_missing_INTERPRETER_even_when_the_script_exists():
    """G1 counter-test — the interpreter is checked INDEPENDENTLY of the script.

    The tests above fabricate commands where BOTH components are absent, so they pass
    whether preflight checks one component or two. While chasing a CI failure I
    weakened this check to the script only; every one of those tests still passed. The
    real defect was a hardcoded gitignored venv path in `_py()`, not the check. This
    case isolates the component the other tests cannot: a REAL, existing script behind
    an interpreter that does not exist must still be refused.
    """
    m = _mod()
    real_script = m._REPO_ROOT / "scripts" / "run_layer1_daily_control.py"
    assert real_script.exists(), "fixture precondition: the script must genuinely exist"
    entry = m.ManifestEntry(
        source="synthetic_missing_interpreter",
        mode="automatic",
        refresh_target="daily",
        connection_method="public_http_api",
        command=("/definitely/not/a/real/interpreter", str(real_script)),
        destination="app/data/nowhere.db",
        success_marker="app/data/ops/nowhere.json",
    )
    status = m.entry_status(entry)
    assert status.ok is False, "a missing interpreter must fail closed"
    missing = status.missing
    assert any(x == "command_not_found:/definitely/not/a/real/interpreter" for x in missing), (
        f"the interpreter must be reported by its own path; got {missing!r}"
    )
    assert not any(str(real_script) in x for x in missing), (
        f"the script EXISTS and must not be reported missing; got {missing!r}"
    )


def _write_plain_file(tmp: Path) -> Path:
    """A real regular file with no execute bit — a valid path that cannot be launched."""
    f = tmp / "not_executable.bin"
    f.write_text("#!/bin/sh\nexit 0\n")
    f.chmod(0o644)
    return f


@pytest.mark.parametrize(
    "label,make_value,expected_code",
    [
        ("empty", lambda tmp: "", "command_interpreter_empty"),
        ("a directory", lambda tmp: str(tmp), "command_interpreter_not_a_file"),
        ("a non-executable file", lambda tmp: str(_write_plain_file(tmp)),
         "command_interpreter_not_executable"),
    ],
)
def test_preflight_fails_closed_on_an_unusable_dynamic_interpreter(
    tmp_path, label, make_value, expected_code
):
    """G1 — `.exists()` is not the contract; a RUNNABLE route is.

    Codex falsified the previous boundary and I reproduced both cases against
    `entry_status` directly:
      * an EMPTY interpreter passed, because `Path("")` resolves to the CWD, which
        always exists;
      * a DIRECTORY passed, because directories exist too.
    Either command certifies a route that cannot launch, which is precisely the class of
    failure preflight exists to catch. A non-executable regular file is the third member
    of the family. All three must fail closed while a valid `sys.executable` still passes.
    """
    m = _mod()
    real = sys.executable
    try:
        sys.executable = make_value(tmp_path)
        entry = next(e for e in m.build_manifest() if e.command)
        status = m.entry_status(entry)
    finally:
        sys.executable = real
    assert status.ok is False, f"an interpreter that is {label} must fail closed"
    assert any(x.startswith(expected_code) for x in status.missing), (
        f"interpreter that is {label} must report {expected_code!r}; got {status.missing!r}"
    )


def test_preflight_still_passes_for_the_real_running_interpreter():
    """The counter-case to the test above: the fail-closed tightening must not make
    every route red. A genuine `sys.executable` is a real, executable file."""
    m = _mod()
    for entry in m.build_manifest():
        if entry.command and entry.mode == "automatic":
            status = m.entry_status(entry)
            assert not any("command_interpreter" in x for x in status.missing), (
                f"{entry.source}: the real interpreter must not be reported unusable; "
                f"got {status.missing!r}"
            )


def test_manifest_interpreter_is_the_running_one_not_a_hardcoded_venv_path():
    """Regression guard for the CI failure of 2026-08-08 (commit c55e645).

    (The commit is dated 2026-08-08T00:48:16-04:00 per `git show -s`. An earlier draft
    of this docstring said 08-07, conflating it with the directive date at the file
    head; the two are different days and only the directive is 08-07.)

    `_py()` returned a hardcoded `.venv/bin/python3.14`. `.venv/` is gitignored, so on
    any tree without this repo's venv — CI, a fresh clone, a differently-located
    environment — every automatic route reported `command_not_found`, nothing executed,
    and three contracts failed. They passed locally because my venv exists, which is
    precisely why the defect reached main.

    The interpreter must be the process's own, and must never be a repo-relative path
    under a gitignored directory.
    """
    m = _mod()
    # A direct `_py() == sys.executable` assertion is VACUOUS on a machine whose
    # running interpreter IS `.venv/bin/python3.14` — the defective and correct values
    # are the same string here, and a mutation restoring the hardcoded path passed.
    # Monkeypatching sys.executable separates them on any machine: the correct
    # implementation FOLLOWS the running interpreter, the hardcoded one ignores it.
    sentinel = "/synthetic/interpreter/for/this/test"
    real = sys.executable
    try:
        sys.executable = sentinel
        observed = m._py()
        commands = [e.command[0] for e in m.build_manifest() if e.command]
    finally:
        sys.executable = real
    assert observed == sentinel, (
        "the runner interpreter must be resolved from sys.executable at call time, so "
        "a child inherits the environment that launched it. A hardcoded repo-relative "
        f"path under the gitignored .venv/ is what broke CI; got {observed!r}"
    )
    assert commands and all(c == sentinel for c in commands), (
        f"every manifest command must launch the running interpreter; got {set(commands)!r}"
    )


def test_preflight_reports_credential_presence_without_network_or_write(monkeypatch):
    """G1 — a paid route's credential is part of 'can this run', and must be checked
    by inspection only."""
    m = _mod()
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    report = m.preflight(manifest=m.build_manifest())
    creds = {c.source: c for c in report.credentials}
    assert "cfbd" in creds
    assert creds["cfbd"].present is False
    assert creds["cfbd"].variable == "CFBD_API_KEY"

    monkeypatch.setenv("CFBD_API_KEY", "synthetic")
    report2 = m.preflight(manifest=m.build_manifest())
    assert {c.source: c for c in report2.credentials}["cfbd"].present is True


def test_owned_execution_refuses_a_route_that_fails_preflight(tmp_path):
    """G1 — a route that cannot run must be refused with the missing component named,
    never launched and left to fail opaquely."""
    m = _mod()
    manifest = [
        m.ManifestEntry(
            source="nflverse_usage_capture",
            mode="automatic",
            refresh_target="daily",
            connection_method="public_file_release",
            command=("/definitely/not/a/real/interpreter", "/nope.py"),
            destination="app/data/nflverse_usage.db",
            success_marker="app/data/nflverse_usage/nflverse_usage_status_latest.json",
            controller_owned=True,
        )
    ]
    launched: list = []

    def _runner(entry):
        launched.append(entry.source)
        return m.SourceResult(source=entry.source, state="executed", failed=False)

    result = m.execute(manifest=manifest, report_root=tmp_path, runner=_runner)
    assert launched == [], "a route failing preflight must not be launched"
    r = result.by_source["nflverse_usage_capture"]
    assert r.failed is True
    assert r.state == "preflight_failed"
    assert any("command_not_found" in x for x in r.missing)


# ============== G2 — a FAILED marker must never read as CURRENT ====================


def test_failed_marker_is_not_current_and_invents_no_last_success(tmp_path):
    """G2 — the sharpest defect in the first GREEN: freshness came from FILE MTIME
    alone, so a marker written seconds ago by a FAILED run reported `current` with a
    last_success_at that never happened. A failure dressed as success is worse than no
    signal at all."""
    m = _mod()
    marker = tmp_path / "marker.json"
    marker.write_text(json.dumps({"status": "failed", "finished_at": "2026-08-07T09:00:00Z"}))

    entry = m.ManifestEntry(
        source="synthetic_failed",
        mode="automatic",
        refresh_target="daily",
        connection_method="public_http_api",
        command=("/bin/true",),
        destination="app/data/nowhere.db",
        success_marker=str(marker),
        controller_owned=False,
    )
    assert m.marker_freshness(entry) == "due" or m.marker_freshness(entry) == "unknown"
    assert m.marker_last_success(entry) is None, (
        "a failed run must not produce a last_success_at"
    )


def test_ok_marker_uses_its_semantic_timestamp_not_file_mtime(tmp_path):
    m = _mod()
    marker = tmp_path / "ok.json"
    marker.write_text(json.dumps({"status": "ok", "finished_at": "2026-08-07T09:00:00+00:00"}))
    entry = m.ManifestEntry(
        source="synthetic_ok", mode="automatic", refresh_target="daily",
        connection_method="public_http_api", command=("/bin/true",),
        destination="d", success_marker=str(marker),
    )
    assert m.marker_last_success(entry) == "2026-08-07T09:00:00+00:00", (
        "the declared completion time is the truth, not when the file was touched"
    )


def test_malformed_marker_is_unknown_not_current(tmp_path):
    m = _mod()
    marker = tmp_path / "bad.json"
    marker.write_text("{not json")
    entry = m.ManifestEntry(
        source="synthetic_bad", mode="automatic", refresh_target="daily",
        connection_method="public_http_api", command=("/bin/true",),
        destination="d", success_marker=str(marker),
    )
    assert m.marker_freshness(entry) == "unknown"
    assert m.marker_last_success(entry) is None


# ==================== G3 — a runnable checked-in entrypoint ========================


def test_controller_cli_exists_and_is_runnable():
    """G3 — a control plane nothing can invoke is not a control plane."""
    cli = Path("scripts/run_layer1_daily_control.py")
    assert cli.is_file(), "the controller needs a checked-in CLI entrypoint"
    text = cli.read_text()
    for flag in ("--preflight", "--dry-run", "--only", "--report-root"):
        assert flag in text, f"CLI missing {flag}"
    assert "--allow-paid" not in text, (
        "this repair must not expose paid execution from the CLI"
    )


def test_execute_has_a_default_canonical_report_root(tmp_path, monkeypatch):
    """G3 — execute previously wrote NOTHING unless a caller supplied a root, so the
    canonical status contract existed only for bespoke import code."""
    m = _mod()
    monkeypatch.setattr(m, "DEFAULT_REPORT_ROOT", tmp_path, raising=False)
    m.execute(manifest=m.build_manifest(), dry_run=True)
    assert (tmp_path / REPORT_FILENAME).is_file(), (
        "execute must write the canonical report without being told where"
    )


# ======================== G4 — Ctrl-C must not be swallowed ========================


def test_keyboard_interrupt_propagates_through_source_isolation(tmp_path):
    """G4 — isolation must catch source failures, not the operator's Ctrl-C."""
    m = _mod()

    def _runner(entry):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        m.execute(manifest=m.build_manifest(), report_root=tmp_path, runner=_runner)


def test_system_exit_propagates_through_source_isolation(tmp_path):
    m = _mod()

    def _runner(entry):
        raise SystemExit(2)

    with pytest.raises(SystemExit):
        m.execute(manifest=m.build_manifest(), report_root=tmp_path, runner=_runner)


# ============ R1-R4 — residuals after the first GREEN repair =======================


def test_freshness_uses_semantic_time_not_file_mtime(tmp_path):
    """R1 — the mtime defect survived one layer down. `last_success` was fixed to read
    the declared time while `freshness` still aged the FILE, so an ok marker declaring
    completion in 2020 but touched a second ago reported `current`."""
    m = _mod()
    marker = tmp_path / "ancient.json"
    marker.write_text(json.dumps({"status": "ok", "finished_at": "2020-01-01T00:00:00+00:00"}))

    entry = m.ManifestEntry(
        source="synthetic_ancient", mode="automatic", refresh_target="daily",
        connection_method="public_http_api", command=("/bin/true",),
        destination="d", success_marker=str(marker),
    )
    assert m.marker_last_success(entry) == "2020-01-01T00:00:00+00:00"
    assert m.marker_freshness(entry) == "due", (
        "a run that completed in 2020 is not current because the file was touched today"
    )


def test_captured_at_is_accepted_as_a_semantic_completion_key(tmp_path):
    """R1 — the real CFBD marker uses `captured_at`."""
    m = _mod()
    marker = tmp_path / "cap.json"
    marker.write_text(json.dumps({"status": "ok", "captured_at": "2026-08-07T09:00:00+00:00"}))
    entry = m.ManifestEntry(
        source="synthetic_cap", mode="automatic", refresh_target="daily",
        connection_method="public_http_api", command=("/bin/true",),
        destination="d", success_marker=str(marker),
    )
    assert m.marker_last_success(entry) == "2026-08-07T09:00:00+00:00"


def test_manual_source_honours_marker_status(tmp_path):
    """R2 — a complete manual entry with a FRESH but FAILED marker previously returned
    manual_current with an invented last success."""
    m = _mod()
    marker = tmp_path / "manual.json"
    marker.write_text(json.dumps({"status": "failed", "finished_at": "2026-08-07T09:00:00+00:00"}))
    importer = "scripts/run_playerprofiler_ingest.py"

    entry = m.ManifestEntry(
        source="playerprofiler", mode="manual_download", refresh_target="daily",
        connection_method="manual_export_download",
        destination="app/data/playerprofiler.db",
        success_marker=str(marker), drop_location="~/Downloads",
        importer=(importer,),
    )
    result = m.execute(manifest=[entry], report_root=tmp_path, dry_run=True)
    r = result.by_source["playerprofiler"]
    assert r.failed is False, "a manual source is still never a job failure"
    assert r.state != "manual_current", "a failed marker must not read as current"
    assert r.last_success_at is None, "a failed run must not invent a last success"


def test_missing_scheduler_evidence_fails_preflight():
    """R3 — declaring a plist that does not exist is exactly the invented-route class."""
    m = _mod()
    entry = m.ManifestEntry(
        source="synthetic_external", mode="automatic", refresh_target="daily",
        connection_method="public_http_api",
        command=(str(Path("scripts/run_layer1_daily_control.py").resolve()),),
        destination="d", success_marker="s",
        scheduler_evidence="ops/launchd/definitely-missing.plist",
    )
    status = m.entry_status(entry)
    assert status.ok is False
    assert any("scheduler_evidence_not_found" in x for x in status.missing)


def test_entry_status_carries_explicit_blocking_flag():
    """R4 — blocking must be carried, never inferred from a source name."""
    m = _mod()
    entries = _by_source(m)

    # A WORKING automatic route is not blocking — there is nothing to block on.
    assert m.entry_status(entries["nflverse_usage_capture"]).blocking is False

    # A BROKEN automatic route blocks: the pipeline cannot run.
    broken_auto = m.ManifestEntry(
        source="synthetic_broken", mode="automatic", refresh_target="daily",
        connection_method="public_http_api",
        command=("/definitely/not/real", "/nope.py"),
        destination="d", success_marker="s", controller_owned=True,
    )
    assert m.entry_status(broken_auto).blocking is True

    # An incomplete MANUAL route is informational: a human has not downloaded yet.
    #
    # This used PFF as its exemplar, which was correct until this program built the PFF importer.
    # A SYNTHETIC entry keeps the invariant covered without pretending a now-complete route is
    # still incomplete — and without the test silently going vacuous the next time a real source
    # becomes complete.
    synthetic_manual = m.ManifestEntry(
        source="synthetic_incomplete_manual",
        mode="manual_download",
        refresh_target="daily",
        connection_method="manual_export_download",
        destination="app/data/nowhere",
    )
    manual = m.entry_status(synthetic_manual)
    assert manual.ok is False, "a manual route with no drop location or importer is incomplete"
    assert manual.blocking is False, (
        "an incomplete MANUAL route is informational, never blocking: a human has not downloaded "
        "something yet, which is an obligation and not a pipeline fault"
    )
    # ...and a real, COMPLETE manual route is genuinely ok, so the assertion above is not vacuous.
    assert m.entry_status(entries["pff"]).ok is True


def test_cli_preflight_exit_is_nonzero_for_a_broken_automatic_route(monkeypatch, tmp_path):
    """R4 — preflight returned 0 regardless, so a broken owned route looked fine."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_l1cli", Path("scripts/run_layer1_daily_control.py")
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    m = _mod()
    broken = [
        m.ManifestEntry(
            source="nflverse_usage_capture", mode="automatic", refresh_target="daily",
            connection_method="public_file_release",
            command=("/definitely/not/real", "/nope.py"),
            destination="d", success_marker="s", controller_owned=True,
        )
    ]
    monkeypatch.setattr(cli, "build_manifest", lambda: broken)
    assert cli.main(["--preflight"]) != 0


def test_cli_preflight_exit_is_zero_when_only_manual_routes_are_incomplete(monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_l1cli2", Path("scripts/run_layer1_daily_control.py")
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    m = _mod()
    manual_only = [
        m.ManifestEntry(
            source="pff", mode="manual_download", refresh_target="daily",
            connection_method="manual_export_download", destination="app/data/pff_exports",
        )
    ]
    monkeypatch.setattr(cli, "build_manifest", lambda: manual_only)
    # DG-048 (David 2026-08-26: "retire daily control"): the RUNNER refuses in
    # every mode now — its control-plane role is superseded by DG-044/DG-049.
    # The manual-route semantics this test originally pinned live on in the
    # MODULE and are still bound by the module tests above; the CLI-level pin
    # flips to the retirement contract (see test_dg048_daily_control_retired).
    assert cli.main(["--preflight"]) != 0, (
        "the retired runner must refuse even preflight"
    )


# ============ MANUAL CADENCE — CONTROLLER BOUNDARY (added after review w#c11gan7a-1) ==========
#
# These exist because three controller-boundary defects were REPAIRED WITH NO TEST, so the focused
# count stayed at 119 and nothing pinned the repair. A fix without a test is a claim, not a contract.


#: The three facts that are COMPETITION-SCOPED. Overrides naming one of these are routed into the
#: competition block; everything else stays at the top level, where league-year events live.
_SCOPED_KEYS = ("week1_kickoff", "final_game", "game_week_completions")


def _cal(competition="nfl", **over):
    """A competition-scoped calendar.

    These fixtures were flat, which is the shape the engine read globally — one league's facts
    governing every league's streams. Overrides keep working unchanged at the call sites; they are
    simply routed to the right level now.
    """
    block = {
        "week1_kickoff": "2026-09-10T20:20:00-04:00",
        "final_game": "2027-01-04T20:20:00-05:00",
        "game_week_completions": [],
    }
    base = {
        "season": 2026,
        "prior_final_game": "2026-01-05T20:20:00-05:00",
        "league_year_open": "2026-03-11T16:00:00-04:00",
        "draft_complete": "2026-04-25T19:00:00-04:00",
    }
    for key, value in over.items():
        if key in _SCOPED_KEYS:
            block[key] = value
        else:
            base[key] = value
    base["competitions"] = {competition: block}
    return base


@pytest.mark.parametrize(
    "label,payload,expect_status",
    [
        ("malformed", "{not json", "invalid"),
        ("wrong shape (list)", "[1, 2, 3]", "invalid"),
        ("partial: no calendar", '{"unexpected": true}', "invalid"),
        ("calendar not an object", '{"calendar": 7}', "invalid"),
        ("calendar missing keys", '{"calendar": {"season": 2026}}', "invalid"),
    ],
)
def test_governed_inputs_reject_every_broken_shape(tmp_path, label, payload, expect_status):
    """Absent and INVALID must never collapse into one state: a corrupted governed artifact that
    reads as 'we simply have no calendar yet' can sit there indefinitely unnoticed."""
    m = _mod()
    f = tmp_path / "inputs.json"
    f.write_text(payload)
    status, loaded, detail = m._load_cadence_inputs(f)
    assert status == expect_status, f"{label}: expected {expect_status}, got {status}"
    assert loaded is None
    assert detail, f"{label}: an invalid artifact must say WHY"


def test_absent_governed_inputs_are_distinguishable_from_invalid(tmp_path):
    m = _mod()
    assert m._load_cadence_inputs(tmp_path / "nope.json")[0] == "absent"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert m._load_cadence_inputs(bad)[0] == "invalid"


@pytest.mark.parametrize(
    "label,calendar",
    [
        ("unparseable", _cal(week1_kickoff="not-a-timestamp")),
        ("naive (no offset)", _cal(week1_kickoff="2026-09-10T20:20:00")),
        ("bad completion entry", _cal(game_week_completions=["not-a-timestamp"])),
        ("naive completion entry", _cal(game_week_completions=["2026-09-14T23:30:00"])),
    ],
)
def test_calendar_TIMESTAMPS_are_validated_not_merely_present(label, calendar):
    """KEY PRESENCE IS NOT VALIDITY. An unparseable time previously passed and then either blew up
    mid-evaluation or — worse — did NOT, because the failure only surfaced when a stream happened to
    carry held data. A guard whose effect depends on incidental data presence is not a guard."""
    m = _mod()
    status, loaded, detail = m._validate_inputs({"calendar": calendar})
    assert status == "invalid", f"{label}: accepted a bad timestamp"
    assert loaded is None and detail


def test_invalid_governed_config_FAILS_CLOSED_and_still_enumerates_streams(tmp_path):
    """Invalid configuration is a DEFECT, not an honest gap. Failing open produced a green
    controller run over a corrupted artifact, forever."""
    m = _mod()
    pff = _by_source(m)["pff"]
    r = m._manual_result(pff, "2026-08-08T00:00:00+00:00", inputs={"unexpected": True})
    assert r.state == "manual_inputs_invalid"
    assert r.failed is True, "invalid governed config must fail CLOSED"
    assert r.coverage == "unknown"
    assert r.streams, "an error fallback must still enumerate declared streams"


def test_ABSENT_inputs_do_not_fail_only_report_undetermined(monkeypatch):
    """Counter-test: absence is an honest gap and must NOT be a failure, or the two are conflated
    in the other direction.

    HERMETIC. An earlier version passed `inputs=None`, which read the REAL production path — so it
    passed only because that artifact does not exist TODAY, and the next slice is explicitly meant
    to create it. A test whose verdict depends on the developer's filesystem is not a contract.
    """
    m = _mod()
    monkeypatch.setattr(m, "_load_cadence_inputs", lambda path=None: ("absent", None, "no artifact"))
    pff = _by_source(m)["pff"]
    r = m._manual_result(pff, "2026-08-08T00:00:00+00:00", inputs=None)
    assert r.failed is False, "no governed artifact yet is not a defect"
    assert r.freshness == "undetermined"
    assert r.streams, "declared streams are enumerated even with no inputs"


def test_manual_evaluation_uses_the_REPORT_INSTANT_not_a_fresh_clock_read(monkeypatch):
    """BEHAVIOURAL proof, across an event boundary, with a deliberately conflicting wall clock.

    The previous version grepped `inspect.getsource()` for two strings. That is the source-proxy
    class already rejected twice in this program: it passes while a HELPER re-reads the clock, or
    while the implementation computes at the wrong instant by any other route. It tests the text,
    not the behaviour.

    Here the wall clock is pinned FAR PAST an event that the report instant precedes. If evaluation
    honours `checked_at`, the stream is not yet due; if it re-reads the clock anywhere in the call
    graph, the event has passed and the state flips. The two answers are genuinely different, so the
    test cannot pass by accident.
    """
    m = _mod()
    from src.dynasty_genius.sources import feed_cadence

    calendar = _cal(game_week_completions=["2026-09-14T23:30:00-04:00"])
    held = {"gamelog": {"newest_season": 2025, "covered_seasons": [2025],
                        "ingested_at": "2026-09-01T00:00:00+00:00"}}
    offer = {"gamelog": {"newest_season": 2026, "covered_seasons": [2025, 2026],
                         "observed_at": "2026-09-01T00:00:00+00:00",
                         "provenance": "vendor_export_manifest"}}
    inputs = {"calendar": calendar, "held": {"playerprofiler": held},
              "offer": {"playerprofiler": offer}}

    class _FarFutureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            # Long AFTER the 2026-09-14 completion. Any clock re-read lands here.
            return datetime(2026, 12, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(feed_cadence, "datetime", _FarFutureClock)
    pp = _by_source(m)["playerprofiler"]

    # Report instant is BEFORE the completion, so nothing is due at the time of record.
    before = m._manual_result(pp, "2026-09-12T00:00:00+00:00", inputs=inputs)
    assert before.streams["gamelog"]["cadence"] != "due", (
        "at 2026-09-12 the week-1 completion has not happened; a `due` here means the "
        f"implementation used the wall clock, not the report instant. got "
        f"{before.streams['gamelog']['cadence']!r}"
    )

    # Same inputs, report instant AFTER the completion -> genuinely due. This proves the first
    # assertion is not passing merely because nothing is ever due.
    after = m._manual_result(pp, "2026-09-16T00:00:00+00:00", inputs=inputs)
    assert after.streams["gamelog"]["cadence"] == "due", (
        "at 2026-09-16 the completion HAS happened and the stream must be due; "
        f"got {after.streams['gamelog']['cadence']!r}"
    )


def test_a_broken_manual_config_does_not_stop_later_independent_routes(tmp_path, monkeypatch):
    """One malformed config file previously raised KeyError from OUTSIDE the per-source isolation
    and took down every route in the controller."""
    m = _mod()
    monkeypatch.setattr(m, "_load_cadence_inputs",
                        lambda path=None: ("ok", {"unexpected": True}, ""))
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    every = {e.source for e in m.build_manifest()}
    assert set(result.by_source) == every, "every source must still be reported"
    assert result.by_source["nflverse_usage_capture"].state != "failed", (
        "an unrelated automatic route must be unaffected by a manual config defect"
    )


def test_every_manual_result_serializes_BOTH_axes_and_all_declared_streams(tmp_path):
    """The report surface previously emitted coverage: null and streams: null for all four manual
    sources, so a gap was invisible in the artifact David actually reads."""
    m = _mod()
    from src.dynasty_genius.sources import feed_cadence
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    for e in m.build_manifest():
        if e.mode != "manual_download":
            continue
        r = result.by_source[e.source]
        assert r.coverage in feed_cadence.COVERAGE_STATES, f"{e.source}: coverage {r.coverage!r}"
        assert r.streams is not None, f"{e.source}: streams must not be null"
        assert set(r.streams) == set(feed_cadence.streams_for(e.source)), (
            f"{e.source}: every declared stream must serialize"
        )
        for name, s in r.streams.items():
            assert s["cadence"] in feed_cadence.CADENCE_STATES
            assert s["coverage"] in feed_cadence.COVERAGE_STATES


def test_governed_inputs_are_loaded_ONCE_per_run_as_one_immutable_snapshot(tmp_path, monkeypatch):
    """W2 — one aggregate report must describe ONE control-plane vintage.

    Each `_manual_result` previously called the loader independently, so a two-source run read the
    file twice; direct instrumentation returned load-1 for PlayerProfiler and load-2 for PFF. A
    mid-run edit could therefore combine different vintages inside a single report, and nothing in
    the artifact would reveal it.
    """
    m = _mod()
    calls: list[int] = []
    real = m._load_cadence_inputs

    def counting(path=None):
        calls.append(len(calls) + 1)
        return real(path)

    monkeypatch.setattr(m, "_load_cadence_inputs", counting)
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)

    manual = [e.source for e in m.build_manifest() if e.mode == "manual_download"]
    assert len(manual) > 1, "fixture precondition: more than one manual source, or this is vacuous"
    assert len(calls) == 1, (
        f"the governed artifact must be read ONCE per run; it was read {len(calls)} times for "
        f"{len(manual)} manual sources"
    )
    # ...and every manual source that REACHES the snapshot must have used the same one. Sources
    # with an incomplete route return earlier with their route diagnostics and never consult it —
    # that is correct behaviour, so comparing all four details was my error, not the code's.
    consulted = [s for s in manual
                 if result.by_source[s].state != "manual_route_incomplete"]
    assert consulted, "fixture precondition: at least one manual route must be complete"
    detail = {result.by_source[s].detail for s in consulted}
    assert len(detail) == 1, f"sources disagree about the snapshot they used: {detail}"


def test_a_snapshot_is_passed_through_rather_than_reloaded_per_source(tmp_path, monkeypatch):
    """Counter-test for the above: prove the pass-through path is what is exercised, by making a
    RELOAD return something different and showing no source picks it up."""
    m = _mod()
    seen: list[str] = []

    def drifting(path=None):
        seen.append("x")
        # First read is valid; any LATER read returns a different (invalid) vintage. If the
        # controller reloaded per source, later sources would report the drifted state.
        if len(seen) == 1:
            return ("absent", None, "snapshot-A")
        return ("invalid", None, "snapshot-B-DRIFTED")

    monkeypatch.setattr(m, "_load_cadence_inputs", drifting)
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)
    manual = [e.source for e in m.build_manifest() if e.mode == "manual_download"]
    consulted = [s for s in manual
                 if result.by_source[s].state != "manual_route_incomplete"]
    assert consulted, "fixture precondition: at least one manual route must be complete"
    for source in consulted:
        assert result.by_source[source].detail == "snapshot-A", (
            f"{source} used a drifted vintage: {result.by_source[source].detail!r}"
        )
        assert result.by_source[source].failed is False, (
            f"{source} inherited the drifted INVALID state instead of the snapshot's ABSENT state"
        )


#: Competition-scoped, with no flat fallback. The three game-calendar facts are scoped together.
_VCAL = {"season": 2026, "competitions": {"nfl": {
    "week1_kickoff": "2026-09-10T20:20:00-04:00",
    "final_game": "2027-01-04T20:20:00-05:00",
    "game_week_completions": []}}}
_VHELD = {"ingested_at": "2026-08-01T00:00:00+00:00", "newest_season": 2025,
          "covered_seasons": [2025]}
_VOFFER = {"observed_at": "2026-08-01T00:00:00+00:00", "provenance": "vendor_export_manifest",
           "newest_season": 2025, "covered_seasons": [2025]}


@pytest.mark.parametrize("label,payload", [
    ("season not an integer", {"calendar": {**_VCAL, "season": "not-an-int"}}),
    ("covered_seasons are strings",
     {"calendar": _VCAL, "held": {"pff": {"nfl_passing_summary": {**_VHELD, "covered_seasons": ["2025"]}}}}),
    ("newest_season is a string",
     {"calendar": _VCAL, "held": {"pff": {"nfl_passing_summary": {**_VHELD, "newest_season": "2025"}}}}),
    ("offer without provenance",
     {"calendar": _VCAL, "offer": {"pff": {"nfl_passing_summary": {"observed_at": "2026-08-01T00:00:00+00:00"}}}}),
    ("held record with NO covered_seasons",
     {"calendar": _VCAL,
      "held": {"pff": {"nfl_passing_summary": {"ingested_at": "2026-08-01T00:00:00+00:00",
                                  "newest_season": 2025}}}}),
    ("offer record with NO covered_seasons",
     {"calendar": _VCAL,
      "offer": {"pff": {"nfl_passing_summary": {"observed_at": "2026-08-01T00:00:00+00:00",
                                   "provenance": "vendor_export_manifest",
                                   "newest_season": 2025}}}}),
    ("covered_seasons is null",
     {"calendar": _VCAL, "held": {"pff": {"nfl_passing_summary": {**_VHELD, "covered_seasons": None}}}}),
    ("covered_seasons is not a list",
     {"calendar": _VCAL, "held": {"pff": {"nfl_passing_summary": {**_VHELD, "covered_seasons": 7}}}}),
    # These now assert the FLAT-KEY refusal. A stray flat game-calendar key is a leftover from the
    # deleted shape, and ignoring it would silently drop whatever the operator put there while the
    # artifact still loaded — a worse failure than rejecting it.
    ("flat game_week_completions is refused outright",
     {"calendar": {**_VCAL, "game_week_completions": 7}}),
    ("flat game_week_completions as a bare string is refused outright",
     {"calendar": {**_VCAL, "game_week_completions": "2026-09-14T23:30:00-04:00"}}),
    ("scoped game_week_completions is not a list",
     {"calendar": {"season": 2026, "competitions": {"nfl": {
         "week1_kickoff": "2026-09-10T20:20:00-04:00",
         "final_game": "2027-01-04T20:20:00-05:00",
         "game_week_completions": 7}}}}),
    ("TYPOED stream key", {"calendar": _VCAL, "held": {"pff": {"gamelogg": _VHELD}}}),
    ("unknown source key", {"calendar": _VCAL, "held": {"pffx": {"nfl_passing_summary": _VHELD}}}),
    ("unknown availability window",
     {"calendar": _VCAL, "availability": {"xfl": {"available_at": "2026-09-15T12:00:00-04:00"}}}),
])
def test_semantic_and_key_validation_rejects_each_malformed_class(label, payload):
    """Shape and timestamp checks are not enough.

    ASSERTING ONLY THE STATUS IS NOT ENOUGH EITHER. `_validate_inputs` wraps everything in a
    catch-all that converts an unexpected exception into INVALID — so removing an explicit type
    guard STILL returns "invalid", just via a crash instead of a decision. Mutation testing proved
    every type guard here was unpinned for exactly that reason. Each case therefore also requires a
    SPECIFIC diagnostic, not the generic containment message.

    A TYPOED STREAM KEY is the most insidious of these: it is silently ignored, so an operator
    believes the data was supplied while that stream reports `undetermined` forever. A string season
    sorts and compares wrongly and would mis-derive every coverage gap. An offer with no stated
    provenance is the bare oracle the cadence contract exists to refuse.
    """
    m = _mod()
    status, loaded, detail = m._validate_inputs(payload)
    assert status == "invalid", f"{label}: accepted"
    assert loaded is None and detail, f"{label}: must say why"
    assert not detail.startswith("governed inputs failed validation:"), (
        f"{label}: rejected by the catch-all rather than by an explicit guard — the diagnostic is "
        f"generic ({detail!r}), so the specific validation is missing"
    )


@pytest.mark.parametrize("label,payload", [
    ("minimal", {"calendar": _VCAL}),
    ("full artifact", {"calendar": _VCAL, "held": {"pff": {"nfl_passing_summary": _VHELD}},
                       "offer": {"pff": {"nfl_passing_summary": _VOFFER}},
                       "availability": {"nfl": {"available_at": "2026-09-15T12:00:00-04:00"}}}),
    ("RETAINED SEASON SUPERSET",
     {"calendar": _VCAL,
      "held": {"pff": {"nfl_passing_summary": {**_VHELD, "covered_seasons": [2015, 2016, 2025]}}},
      "offer": {"pff": {"nfl_passing_summary": _VOFFER}}}),
])
def test_valid_artifacts_are_ACCEPTED_so_the_validator_is_not_merely_refusing_everything(
    label, payload
):
    """Counter-tests. Without these the whole validation suite passes trivially if the validator
    rejects every input — and the retained-superset case matters because holding MORE seasons than
    the vendor offers must never be read as a defect."""
    m = _mod()
    status, loaded, detail = m._validate_inputs(payload)
    assert status == "ok", f"{label}: wrongly rejected — {detail}"
    assert loaded is not None


def test_a_malformed_artifact_fails_closed_AT_THE_CONTROLLER_and_preserves_isolation(
    tmp_path, monkeypatch
):
    """Pin at least one malformed case at the FULL CONTROLLER SURFACE, not only at the validator.

    A boundary function that returns the right verdict proves nothing if the controller ignores it.
    """
    m = _mod()
    bad = {"calendar": _VCAL, "held": {"pff": {"gamelogg": _VHELD}}}   # typoed stream key
    monkeypatch.setattr(m, "_load_cadence_inputs",
                        lambda path=None: m._validate_inputs(bad))
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)

    complete_manual = [e.source for e in m.build_manifest()
                       if e.mode == "manual_download"
                       and result.by_source[e.source].state != "manual_route_incomplete"]
    assert complete_manual, "fixture precondition: at least one complete manual route"
    for source in complete_manual:
        r = result.by_source[source]
        assert r.state == "manual_inputs_invalid", f"{source}: {r.state}"
        assert r.failed is True, f"{source}: a malformed artifact must fail CLOSED"
        assert r.streams, f"{source}: the error path must still enumerate declared streams"
    assert result.exit_code != 0, "a malformed governed artifact must make the run nonzero"
    # ...and isolation holds: unrelated automatic routes are untouched.
    assert result.by_source["nflverse_usage_capture"].state != "failed"
    assert set(result.by_source) == {e.source for e in m.build_manifest()}


def test_a_validator_exception_becomes_INVALID_and_never_escapes(monkeypatch):
    """A malformed artifact must never propagate as an exception.

    `game_week_completions: 7` previously raised TypeError from iterating an int — OUT of the
    validator and past source isolation, so one bad config file crashed the whole controller. Any
    unanticipated error is INVALID EVIDENCE, which is exactly what it is.
    """
    m = _mod()

    def boom(payload):
        raise RuntimeError("synthetic validator explosion")

    monkeypatch.setattr(m, "_validate_inputs_inner", boom)
    status, loaded, detail = m._validate_inputs({"calendar": _VCAL})
    assert status == "invalid"
    assert loaded is None
    assert "RuntimeError" in detail, f"the failure class must be named; got {detail!r}"


def test_a_container_type_defect_fails_closed_AT_THE_CONTROLLER(tmp_path, monkeypatch):
    """Pinned at the full controller surface, not only at the validator: the point of the fix is
    that the RUN survives and reports, rather than crashing."""
    m = _mod()
    bad = {"calendar": {**_VCAL, "game_week_completions": 7}}
    monkeypatch.setattr(m, "_load_cadence_inputs", lambda path=None: m._validate_inputs(bad))
    result = m.execute(manifest=m.build_manifest(), report_root=tmp_path, dry_run=True)

    assert set(result.by_source) == {e.source for e in m.build_manifest()}, (
        "the run must complete and report every source"
    )
    complete = [e.source for e in m.build_manifest()
                if e.mode == "manual_download"
                and result.by_source[e.source].state != "manual_route_incomplete"]
    assert complete, "fixture precondition: at least one complete manual route"
    for source in complete:
        assert result.by_source[source].state == "manual_inputs_invalid"
        assert result.by_source[source].failed is True
        assert result.by_source[source].streams, "the error path still enumerates streams"
    assert result.exit_code != 0
    assert result.by_source["nflverse_usage_capture"].state != "failed", (
        "isolation holds: an unrelated automatic route is untouched"
    )
