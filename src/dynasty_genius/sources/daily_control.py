"""Layer 1 daily source control plane: manifest, preflight, controller.

David's directive (2026-08-07): determine how to connect, ingest and refresh EVERY
source; track which cannot be refreshed and require a manual download; assume DAILY for
everything and reduce only once Layers 2-3 teach us otherwise.

Three parts, deliberately separable:

* ``build_manifest()`` — the single answer to "what are our sources, how do we connect,
  and can we automate it". Every registry definition is owned by exactly one acquisition
  family. A family is NOT a registry key: one canonical route legitimately serves
  several definitions, and pretending otherwise would invent duplicate jobs.
* ``preflight()`` — read-only. It verifies routes and credentials EXIST. It performs no
  network call, spawns no process, and writes nothing anywhere.
* ``execute()`` — runs only the routes this controller owns, isolating each so one
  failure cannot cap the others, and writes one atomic aggregate report.

WHAT THIS DELIBERATELY DOES NOT DO
  * It never consults a provider's publication schedule. Two providers publish none, and
    chasing that answer produced nothing usable. The refresh target is OURS to choose.
  * It never executes a paid source without an explicit enablement, so a daily job cannot
    quietly spend money.
  * It never runs a route another scheduler already owns, so nothing double-pulls.
  * It never treats a stale manual source as a failure. A human has not downloaded
    something yet; that is an obligation, not a fault.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: The five operational modes. Cost is NOT among them: a paid source is `automatic` with
#: a gate, because collapsing the two would hide whether a connection exists at all.
MODES: tuple[str, ...] = (
    "automatic",
    "manual_download",
    "static",
    "blocked",
    "prohibited",
)

#: Modes that carry an acquisition obligation, and therefore a refresh target.
_MODES_WITH_TARGET = frozenset({"automatic", "manual_download", "blocked"})

#: How a source is reached. `none` means no route exists, which is a real answer.
CONNECTION_METHODS: tuple[str, ...] = (
    "public_http_api",
    "public_file_release",
    "credentialed_http_api",
    "manual_export_download",
    "vendor_contract_required",
    "none",
)

REPORT_FILENAME = "layer1_daily_control_latest.json"

#: G3 — the canonical report root, so the status contract exists without bespoke code.
DEFAULT_REPORT_ROOT = _REPO_ROOT / "app" / "data" / "ops"

#: G2 — statuses a marker may declare that mean the run actually succeeded. Anything
#: else — failed, aborted, running, or absent — is NOT a success, however recently the
#: file was touched.
SUCCESS_STATUSES = frozenset({"ok", "completed", "success"})

#: G2 — marker keys that carry a SEMANTIC completion time, preferred over file mtime.
_COMPLETION_KEYS = (
    "finished_at", "completed_at", "captured_at", "retrieved_at", "ingested_at",
)

#: G1 — credentials a route needs, checked by inspection only.
REQUIRED_CREDENTIALS = {"cfbd": "CFBD_API_KEY"}

#: A daily job that cannot time out can hang forever and silently stop every source
#: behind it from refreshing.
DEFAULT_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class ManifestEntry:
    source: str
    mode: str
    registry_sources: tuple[str, ...] = ()
    refresh_target: Optional[str] = None
    connection_method: str = "none"
    command: Optional[tuple[str, ...]] = None
    destination: Optional[str] = None
    success_marker: Optional[str] = None
    drop_location: Optional[str] = None
    importer: Optional[tuple[str, ...]] = None
    paid_gated: bool = False
    controller_owned: bool = False
    scheduler_evidence: Optional[str] = None
    #: An EXPLICITLY named prior-success marker (e.g. an export ready marker). Declared,
    #: never discovered: a directory scan finds whatever happens to be lying around, and
    #: a source-name rule breaks the moment a source is renamed.
    last_good_marker: Optional[str] = None
    note: str = ""


@dataclass(frozen=True)
class EntryStatus:
    source: str
    ok: bool
    missing: tuple[str, ...] = ()
    #: R4 — whether an incomplete route BLOCKS. Carried explicitly: inferring it from a
    #: source name would break the moment a source is renamed.
    blocking: bool = False


@dataclass
class SourceResult:
    source: str
    state: str
    failed: bool = False
    checked_at: Optional[str] = None
    last_success_at: Optional[str] = None
    freshness: str = "unknown"
    age_days: Optional[float] = None
    missing: tuple[str, ...] = ()
    detail: str = ""


@dataclass
class GateReport:
    source: str
    reason: str


@dataclass
class CredentialReport:
    source: str
    variable: str
    present: bool


@dataclass
class PreflightReport:
    entries: tuple[EntryStatus, ...] = ()
    gated: tuple[GateReport, ...] = ()
    credentials: tuple[CredentialReport, ...] = ()
    network_used: bool = False


@dataclass
class ExecuteResult:
    by_source: dict[str, SourceResult] = field(default_factory=dict)
    exit_code: int = 0
    report_path: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _age_days(path: Optional[str]) -> Optional[float]:
    if not path:
        return None
    p = _REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not p.exists():
        return None
    delta = datetime.now(timezone.utc).timestamp() - p.stat().st_mtime
    return round(delta / 86400.0, 3)


def _mtime_iso(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = _REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()


def _py() -> str:
    return str(_REPO_ROOT / ".venv" / "bin" / "python3.14")


def build_manifest() -> list[ManifestEntry]:
    """Every source, how it connects, and whether we can automate it.

    Ownership is DECLARED here, never derived from what happens to be installed on a
    machine: host state is mutable and a manifest that reads it would silently change
    meaning between laptops.
    """
    return [
        # ---------------------------------------------------------------- automatic
        ManifestEntry(
            source="nflverse_usage_capture",
            mode="automatic",
            registry_sources=("nfl_nextgen_stats", "nflreadpy_qb_context"),
            refresh_target="daily",
            connection_method="public_file_release",
            command=(_py(), str(_REPO_ROOT / "scripts/run_nflverse_usage_capture.py")),
            destination="app/data/nflverse_usage.db",
            success_marker="app/data/nflverse_usage/nflverse_usage_status_latest.json",
            last_good_marker="app/data/nflverse_usage/export/nflverse_usage.ready.json",
            controller_owned=True,
            note="One runner covering all 13 streams bound by the canonical adapter's "
                 "build_streams(); nothing scheduled it before. The stream names are "
                 "deliberately NOT repeated here: contract tests cordon those symbols "
                 "to the adapter so a stray reference cannot become a consumer.",
        ),
        ManifestEntry(
            source="sleeper_transactions",
            mode="automatic",
            refresh_target="daily",
            connection_method="public_http_api",
            command=(_py(), str(_REPO_ROOT / "scripts/run_league_transaction_capture.py")),
            destination="app/data/league_transactions.db",
            success_marker="app/data/league_transactions/transaction_capture_status_latest.json",
            controller_owned=True,
            note="Event data. A transaction not captured is not recoverable by "
                 "re-reading: the endpoint serves current state, not an archive.",
        ),
        ManifestEntry(
            source="sleeper",
            mode="automatic",
            registry_sources=("sleeper",),
            refresh_target="daily",
            connection_method="public_http_api",
            command=(_py(), str(_REPO_ROOT / "scripts/run_league_snapshot_capture.py")),
            destination="app/data/league_runtime",
            success_marker="app/data/league_runtime/capture_status_latest.json",
            scheduler_evidence="ops/launchd/com.davidleess.dynasty-league-capture.plist",
            note="Already scheduled elsewhere; the controller must not double-pull.",
        ),
        ManifestEntry(
            source="fantasycalc",
            mode="automatic",
            registry_sources=("fantasycalc",),
            refresh_target="daily",
            connection_method="public_http_api",
            command=(_py(), str(_REPO_ROOT / "scripts/run_fc_forward_capture.py")),
            destination="app/data/fc_forward_capture.db",
            success_marker="app/data/capture/fc_forward_capture_latest_report.json",
            scheduler_evidence="ops/launchd/com.davidleess.dynasty-fc-snapshot.plist",
            note="Already scheduled elsewhere.",
        ),
        ManifestEntry(
            source="cfbd",
            mode="automatic",
            registry_sources=("cfbd",),
            refresh_target="daily",
            connection_method="credentialed_http_api",
            command=(_py(), str(_REPO_ROOT / "scripts/run_cfbd_foundation_refresh.py")),
            destination="app/data/sources/cfbd_foundation",
            success_marker="app/data/sources/cfbd_foundation/status_latest.json",
            paid_gated=True,
            note="Daily TARGET honours the directive; the gate protects the wallet. "
                 "Execution needs an explicit cost enablement.",
        ),
        # ----------------------------------------------------------- manual_download
        ManifestEntry(
            source="playerprofiler",
            mode="manual_download",
            registry_sources=("playerprofiler",),
            refresh_target="daily",
            connection_method="manual_export_download",
            destination="app/data/playerprofiler.db",
            success_marker="app/data/playerprofiler/playerprofiler_status_latest.json",
            drop_location="~/Downloads",
            importer=(
                "scripts/run_playerprofiler_ingest.py",
                "scripts/run_playerprofiler_gamelog_ingest.py",
                "scripts/run_playerprofiler_pbp_ingest.py",
                "scripts/run_playerprofiler_roster_ingest.py",
            ),
            note="Five report families through four import CLIs. No API exists.",
        ),
        ManifestEntry(
            source="pff",
            mode="manual_download",
            registry_sources=("pff",),
            refresh_target="daily",
            connection_method="manual_export_download",
            destination="app/data/pff_exports",
            note="No importer CLI exists in this repo. Declaring one would be a fiction "
                 "the manifest then carries as fact.",
        ),
        ManifestEntry(
            source="rotoviz",
            mode="manual_download",
            registry_sources=("rotoviz",),
            refresh_target="daily",
            connection_method="manual_export_download",
            note="Registry: 'Manual CSV export only. No public API.'",
        ),
        ManifestEntry(
            source="campus2canton",
            mode="manual_download",
            registry_sources=("campus2canton",),
            refresh_target="daily",
            connection_method="manual_export_download",
            note="Registry: 'CSV export from Player Metric Data Table.'",
        ),
        # ------------------------------------------------------------------- blocked
        ManifestEntry(
            source="nfl_data_py",
            mode="blocked",
            registry_sources=("nfl_data_py",),
            refresh_target="daily",
            connection_method="public_file_release",
            note="Blocked on a PROVENANCE gap, not on access: the registry names a "
                 "provider the code does not import (it uses nflreadpy).",
        ),
        ManifestEntry(
            source="ras",
            mode="blocked",
            registry_sources=("ras",),
            refresh_target="daily",
            connection_method="none",
            note="No production acquisition route; retention/licensing unresolved.",
        ),
        ManifestEntry(
            source="mfl_rookie_adp",
            mode="blocked",
            registry_sources=("mfl_rookie_adp",),
            refresh_target="daily",
            connection_method="public_http_api",
            note="Registry: 'Public documented MFL ADP API.' Blocked on an adapter "
                 "defect that returns veterans, not on access.",
        ),
        ManifestEntry(
            source="dynasty_data_lab",
            mode="blocked",
            registry_sources=("dynasty_data_lab",),
            refresh_target="daily",
            connection_method="credentialed_http_api",
            note="Registry: '$4 per 1000 requests. Deferred.'",
        ),
        ManifestEntry(
            source="dynasty_nerds",
            mode="blocked",
            registry_sources=("dynasty_nerds",),
            refresh_target="daily",
            connection_method="none",
            note="Registry: 'No clean public API. Deferred.'",
        ),
        # ---------------------------------------------------------------- prohibited
        ManifestEntry(
            source="ktc",
            mode="prohibited",
            registry_sources=("ktc",),
            connection_method="none",
            note="Registry: 'ToS explicitly prohibits scraping rankings.'",
        ),
        ManifestEntry(
            source="sportradar",
            mode="prohibited",
            registry_sources=("sportradar",),
            connection_method="vendor_contract_required",
            note="Registry: 'Enterprise B2B only. ~$7200/year.'",
        ),
        ManifestEntry(
            source="genius_sports",
            mode="prohibited",
            registry_sources=("genius_sports",),
            connection_method="vendor_contract_required",
            note="Registry: 'Enterprise pricing.'",
        ),
        ManifestEntry(
            source="stats_perform",
            mode="prohibited",
            registry_sources=("stats_perform",),
            connection_method="vendor_contract_required",
            note="Registry: 'Enterprise clients.'",
        ),
        ManifestEntry(
            source="rolling_insights",
            mode="prohibited",
            registry_sources=("rolling_insights",),
            connection_method="vendor_contract_required",
            note="Registry: '$4200/year post-game, $7200/year live.'",
        ),
        # -------------------------------------------------------------------- static
        ManifestEntry(
            source="nflreadpy_qb_validation",
            mode="static",
            registry_sources=("nflreadpy_qb_validation",),
            connection_method="public_file_release",
            note="A pre-registered study input. Automation must be physically unable to "
                 "alter a pinned manifest input.",
        ),
    ]


def entry_status(entry: ManifestEntry) -> EntryStatus:
    """Name the EXACT missing piece. 'Invalid' tells a reader nothing actionable."""
    missing: list[str] = []
    if entry.mode == "automatic":
        if not entry.command:
            missing.append("missing_command")
        else:
            # G1: presence of a string is not existence of a route.
            for part in list(entry.command)[:2]:
                candidate = Path(part)
                if not candidate.is_absolute():
                    candidate = _REPO_ROOT / part
                if not candidate.exists():
                    missing.append(f"command_not_found:{part}")
        if not entry.destination:
            missing.append("missing_destination")
        if not entry.success_marker:
            missing.append("missing_success_marker")
    elif entry.mode == "manual_download":
        if not entry.drop_location:
            missing.append("missing_drop_location")
        if not entry.importer:
            missing.append("missing_importer")
        else:
            for imp in entry.importer:
                if not (_REPO_ROOT / imp).exists():
                    missing.append(f"importer_not_found:{imp}")
    # R3: declaring a plist that does not exist is the invented-route class again.
    if entry.scheduler_evidence and not (_REPO_ROOT / entry.scheduler_evidence).exists():
        missing.append(f"scheduler_evidence_not_found:{entry.scheduler_evidence}")

    # R4: an incomplete AUTOMATIC route is a broken pipeline. An incomplete MANUAL route
    # means a human has not supplied something yet — informational, not blocking.
    blocking = bool(missing) and entry.mode == "automatic"
    return EntryStatus(
        source=entry.source, ok=not missing, missing=tuple(missing), blocking=blocking,
    )


def preflight(
    manifest: Optional[Sequence[ManifestEntry]] = None,
    report_root: Optional[Path] = None,  # noqa: ARG001 - accepted, deliberately unused
) -> PreflightReport:
    """Verify routes and credentials EXIST. Read-only, by construction.

    ``report_root`` is accepted so callers may pass one uniformly, and is deliberately
    ignored: preflight writes nothing anywhere, not merely nothing there.
    """
    manifest = list(manifest if manifest is not None else build_manifest())
    statuses = tuple(entry_status(e) for e in manifest)
    gated = tuple(
        GateReport(source=e.source, reason="paid_gated: needs explicit cost enablement")
        for e in manifest
        if e.paid_gated
    )
    creds = tuple(
        CredentialReport(
            source=e.source,
            variable=REQUIRED_CREDENTIALS[e.source],
            present=bool(os.environ.get(REQUIRED_CREDENTIALS[e.source])),
        )
        for e in manifest
        if e.source in REQUIRED_CREDENTIALS
    )
    return PreflightReport(
        entries=statuses, gated=gated, credentials=creds, network_used=False
    )


def _default_runner(entry: ManifestEntry) -> SourceResult:
    """Launch the route. argv form, never a shell, always time-bounded."""
    completed = subprocess.run(  # noqa: S603 - argv form, shell=False, bounded
        list(entry.command or ()),
        shell=False,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        capture_output=True,
        cwd=str(_REPO_ROOT),
    )
    rc = getattr(completed, "returncode", 1)
    return SourceResult(
        source=entry.source,
        state="executed" if rc == 0 else "failed",
        failed=rc != 0,
        detail=f"exit={rc}",
    )


def _manual_result(entry: ManifestEntry, checked_at: str) -> SourceResult:
    """A stale manual source is DUE, never FAILED — different facts entirely."""
    status = entry_status(entry)
    if status.missing:
        return SourceResult(
            source=entry.source,
            state="manual_route_incomplete",
            failed=False,
            checked_at=checked_at,
            freshness="unknown",
            missing=status.missing,
        )
    # R2: reuse the parsed marker semantics. A fresh but FAILED marker previously
    # returned manual_current with an invented last success.
    if entry.success_marker:
        last = marker_last_success(entry)
        age = marker_age_days(entry)
    else:
        last = _mtime_iso(entry.destination)
        age = _age_days(entry.destination)
    if last is None:
        return SourceResult(
            source=entry.source, state="manual_due", failed=False,
            checked_at=checked_at, freshness="unknown", age_days=age,
        )
    due = age is None or age > 1.0
    return SourceResult(
        source=entry.source,
        state="manual_due" if due else "manual_current",
        failed=False,
        checked_at=checked_at,
        last_success_at=last,
        freshness="due" if due else "current",
        age_days=age if age is not None else 0.0,
    )


def write_report(report_root: Path, payload: dict[str, Any]) -> Path:
    """Write the aggregate report ATOMICALLY to one stable path.

    A partial or truncated status file is worse than a stale one: the stale file is at
    least a fact that was once true. Write to a temp file in the same directory, then
    rename — so a crash leaves the previous report byte-intact.
    """
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    final = root / REPORT_FILENAME
    fd, tmp = tempfile.mkstemp(dir=str(root), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, default=str))
        os.replace(tmp, final)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return final


def execute(
    manifest: Optional[Sequence[ManifestEntry]] = None,
    report_root: Optional[Path] = None,
    runner: Optional[Callable[[ManifestEntry], SourceResult]] = None,
    only: Optional[Iterable[str]] = None,
    dry_run: bool = False,
    allow_paid: bool = False,
) -> ExecuteResult:
    """Run the controller-owned routes, isolate failures, emit one atomic report.

    ``only`` NARROWS the default set. It is never an escape hatch: a route this
    controller does not own, or a paid route without ``allow_paid``, stays unrun however
    explicitly it is named.
    """
    manifest = list(manifest if manifest is not None else build_manifest())
    runner = runner or _default_runner
    checked_at = _now()
    results: dict[str, SourceResult] = {}

    selected = set(only) if only is not None else None

    for entry in manifest:
        if entry.mode == "manual_download":
            results[entry.source] = _manual_result(entry, checked_at)
            continue

        if entry.mode != "automatic":
            results[entry.source] = SourceResult(
                source=entry.source, state=f"not_run_{entry.mode}", failed=False,
                checked_at=checked_at, freshness="unknown",
            )
            continue

        # The paid gate is evaluated FIRST and deliberately so. A paid source that is
        # also unowned must report as gated, not as "someone else schedules it": the
        # cost is the consequential fact, and burying it behind an ownership check is
        # how a billed route ends up looking merely delegated.
        if entry.paid_gated and not allow_paid:
            results[entry.source] = SourceResult(
                source=entry.source, state="skipped_paid_gate", failed=False,
                checked_at=checked_at, freshness=_freshness(entry),
                last_success_at=marker_last_success(entry),
                age_days=marker_age_days(entry),
                detail="needs explicit cost enablement",
            )
            continue

        if not entry.controller_owned:
            results[entry.source] = SourceResult(
                source=entry.source,
                state="skipped_external_scheduler" if entry.scheduler_evidence
                else "not_controller_owned",
                failed=False,
                checked_at=checked_at,
                last_success_at=marker_last_success(entry),
                freshness=_freshness(entry),
                age_days=marker_age_days(entry),
                detail=entry.scheduler_evidence or "",
            )
            continue

        if selected is not None and entry.source not in selected:
            results[entry.source] = SourceResult(
                source=entry.source, state="not_selected", failed=False,
                checked_at=checked_at, freshness="unknown",
            )
            continue

        # G1: a route that cannot run is refused with the missing component named,
        # rather than launched and left to fail opaquely.
        pf = entry_status(entry)
        if not pf.ok:
            # A route that CANNOT RUN still has a known last-good vintage. Refusing to
            # launch it says nothing about how old the data is — separate axes again.
            results[entry.source] = SourceResult(
                source=entry.source, state="preflight_failed", failed=True,
                checked_at=checked_at,
                last_success_at=marker_last_success(entry),
                age_days=marker_age_days(entry),
                freshness=_freshness(entry),
                missing=pf.missing,
                detail="refused: route preflight failed",
            )
            continue

        if dry_run:
            results[entry.source] = SourceResult(
                source=entry.source, state="dry_run", failed=False,
                checked_at=checked_at, freshness=_freshness(entry),
                last_success_at=marker_last_success(entry),
                age_days=marker_age_days(entry),
            )
            continue

        # Isolation: one route's failure must never cap another's.
        # G4: isolation catches SOURCE failures, never the operator's Ctrl-C.
        # KeyboardInterrupt and SystemExit must reach the caller.
        try:
            r = runner(entry)
        except Exception as exc:
            r = SourceResult(
                source=entry.source, state="failed", failed=True,
                detail=f"{type(exc).__name__}: {exc}",
            )
        r.checked_at = r.checked_at or checked_at
        if r.last_success_at is None:
            r.last_success_at = marker_last_success(entry)
        r.age_days = r.age_days if r.age_days is not None else marker_age_days(entry)
        # A failed ATTEMPT does not erase what we know about the last GOOD run. These
        # are separate axes: `failed` reports this run, `freshness` reports the data.
        # Hardcoding `unknown` here was the live defect — it discarded a last-good
        # marker that was sitting on disk naming a real prior success.
        r.freshness = _freshness(entry)
        results[entry.source] = r

    # Paid entries the caller narrowed away still belong in the report.
    for entry in manifest:
        results.setdefault(
            entry.source,
            SourceResult(source=entry.source, state="not_run", failed=False,
                         checked_at=checked_at, freshness="unknown"),
        )

    exit_code = 1 if any(r.failed for r in results.values()) else 0
    path = None
    report_root = report_root if report_root is not None else DEFAULT_REPORT_ROOT
    if report_root is not None:
        payload = {
            "generated_at": checked_at,
            "exit_code": exit_code,
            "by_source": {k: vars(v) for k, v in results.items()},
        }
        path = str(write_report(Path(report_root), payload))
    return ExecuteResult(by_source=results, exit_code=exit_code, report_path=path)


def _read_marker(path: Optional[str]) -> Optional[dict[str, Any]]:
    """Return the marker's parsed contents, or None if absent/unreadable/malformed."""
    if not path:
        return None
    p = _REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not p.is_file():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _valid_iso_or_none(value: Optional[str]) -> Optional[str]:
    """Return the value only if it actually parses as a timestamp.

    VALIDATION BELONGS AT THE EVIDENCE BOUNDARY. Failing only the AGE closed while still
    returning the literal let the report serialize `last_success_at: "not-a-timestamp"`
    beside `freshness: unknown` — a field asserting a success that never happened, which
    is the exact defect class this whole repair exists to remove. No success, no age,
    unknown.
    """
    if value is None:
        return None
    return value if _age_from_iso(value) is not None else None


def _last_good_success(entry: ManifestEntry) -> Optional[str]:
    """The prior success time from an explicitly named last-good marker, or None.

    IDENTITY REQUIREMENT: a nonempty `run_id` AND a `captured_at`. Without both, the file
    is not the consumer commit point — an arbitrary JSON that happens to carry a
    timestamp must not license a freshness claim.
    """
    payload = _read_marker(entry.last_good_marker)
    if payload is None:
        return None
    run_id = str(payload.get("run_id") or "").strip()
    captured_at = str(payload.get("captured_at") or "").strip()
    if not run_id or not captured_at:
        return None
    return _valid_iso_or_none(captured_at)


def marker_last_success(entry: ManifestEntry) -> Optional[str]:
    """The declared completion time of a SUCCESSFUL run, or None.

    G2: file mtime is not evidence of success. A marker written seconds ago by a run
    that FAILED previously produced `current` plus a last_success_at that never
    happened — a failure wearing success's clothes, which is worse than no signal.
    """
    payload = _read_marker(entry.success_marker)
    if payload is not None and str(payload.get("status", "")).lower() in SUCCESS_STATUSES:
        # A CURRENT primary success is the better evidence and must win over an older
        # last-good marker.
        for key in _COMPLETION_KEYS:
            value = payload.get(key)
            if value:
                # A declared-but-unparseable time is NOT evidence. Fall through to the
                # last-good marker rather than serializing a lie, and note that an
                # ABSENT key is different: absence legitimately falls back to mtime.
                validated = _valid_iso_or_none(str(value))
                if validated is not None:
                    return validated
                return _last_good_success(entry)
        return _mtime_iso(entry.success_marker)

    # The attempt failed or is unreadable — but that is a different axis from what we
    # know about the last GOOD run. Reporting `unknown` while the answer sits in an
    # explicitly configured marker throws away real information, and leaves a reader
    # unable to tell "failed once over fresh data" from "never succeeded at all".
    return _last_good_success(entry)


def _age_from_iso(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return round(
        (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0, 3
    )


def marker_age_days(entry: ManifestEntry) -> Optional[float]:
    """Age of the last DECLARED success.

    R1: file mtime is not when a run completed. A marker declaring completion in 2020,
    touched a second ago by anything at all, is not fresh. Semantic time wins; mtime is
    the fallback only when no completion key is present.
    """
    # marker_last_success now validates at the boundary, so anything it returns parses.
    return _age_from_iso(marker_last_success(entry))


def marker_freshness(entry: ManifestEntry) -> str:
    """Freshness of the last DECLARED success, primary first then last-good fallback."""
    if marker_last_success(entry) is None:
        return "unknown"
    age = marker_age_days(entry)
    if age is None:
        return "unknown"
    return "current" if age <= 1.0 else "due"


def _freshness(entry: ManifestEntry) -> str:
    return marker_freshness(entry)
