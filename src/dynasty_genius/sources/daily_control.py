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
  * It never consults a provider's publication cadence. That cadence is outside this
    local-refresh gate and is never used to decide execution; the refresh target is
    OURS to choose.
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
import sys
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
    #: The COVERAGE axis, independent of freshness/cadence. A source can be quiet and incomplete at
    #: the same time; collapsing the two destroys the second fact.
    coverage: Optional[str] = None
    #: Per-stream states for manual sources. Every declared stream serializes, even unheld ones.
    streams: Optional[dict[str, Any]] = None


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
    """The interpreter to launch source runners with.

    `sys.executable`, NOT a hardcoded `.venv/bin/python3.14`. The venv is gitignored, so
    a hardcoded path made every automatic route fail preflight anywhere the venv does not
    exist — CI, a fresh clone, or any machine with a differently-located environment. CI
    caught exactly that. Using the running interpreter is also simply more correct: a
    child process should inherit the environment that launched it.
    """
    return sys.executable


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
            refresh_target="windowed",
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
            refresh_target="windowed",
            connection_method="manual_export_download",
            destination="app/data/pff_exports",
            # The drop location is the human INBOX, not the canonical destination above. The two
            # are different things: a person puts files in the inbox; the importer writes the
            # content-addressed store. Naming the canonical tree here would tell an operator to
            # hand-place files into a machine-managed layout.
            drop_location="app/data/pff_exports/inbox",
            # A TUPLE, matching the declared `Optional[tuple[str, ...]]`. A bare string is
            # iterated CHARACTER BY CHARACTER by entry_status, which reported 23 phantom
            # `importer_not_found:s`, `:c`, `:r`... failures and kept PFF permanently incomplete.
            importer=("scripts/run_pff_intake.py",),
            success_marker="app/data/ops/pff_intake_status_latest.json",
            last_good_marker="app/data/ops/pff_intake.ready.json",
            note="Manual subscriber export. `run_pff_intake.py --batch-manifest <sidecar>` indexes "
                 "a drop; `--backfill-existing` indexes payloads already held. Provenance is "
                 "declared in the sidecar, never inferred from filenames. The reported age is the "
                 "SOURCE download age, not the age of our index.",
        ),
        ManifestEntry(
            source="rotoviz",
            mode="manual_download",
            registry_sources=("rotoviz",),
            refresh_target="undetermined",
            connection_method="manual_export_download",
            note="Registry: 'Manual CSV export only. No public API.'",
        ),
        ManifestEntry(
            source="campus2canton",
            mode="manual_download",
            registry_sources=("campus2canton",),
            refresh_target="undetermined",
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
            # G1: presence of a string is not existence of a RUNNABLE route. BOTH the
            # interpreter and the script are checked, and `.exists()` alone is not the
            # contract at this boundary — it fails OPEN twice over:
            #   * `Path("")` resolves to the CWD, which always exists, so an empty
            #     interpreter certified a command that cannot launch;
            #   * a DIRECTORY exists too, so a path pointing at a folder passed.
            # Both were reproduced against this function. The contract is that each
            # component is a real FILE, and that the interpreter is one we can execute.
            for index, part in enumerate(list(entry.command)[:2]):
                role = "interpreter" if index == 0 else "script"
                if not part:
                    missing.append(f"command_{role}_empty")
                    continue
                candidate = Path(part)
                if not candidate.is_absolute():
                    candidate = _REPO_ROOT / part
                if not candidate.is_file():
                    # A missing path and a non-file path are distinct failures; naming
                    # which one keeps preflight output diagnostic rather than merely red.
                    # `command_not_found:` is preserved VERBATIM for the not-found case
                    # because already-CLEARed contracts assert on that exact token; the
                    # new codes cover only the genuinely new failure modes.
                    if candidate.exists():
                        missing.append(f"command_{role}_not_a_file:{part}")
                    else:
                        missing.append(f"command_not_found:{part}")
                elif role == "interpreter" and not os.access(candidate, os.X_OK):
                    # Executability applies to the interpreter only. Runner scripts are
                    # launched as arguments to it and carry no +x bit in this repo.
                    missing.append(f"command_interpreter_not_executable:{part}")
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


#: Governed inputs for per-stream cadence. Absent by design today: no season calendar and no
#: per-stream inventory exist in this repo yet. Their absence yields `undetermined`/`unknown`, which
#: is the honest answer — it must NEVER fall back to a daily clock.
MANUAL_CADENCE_INPUTS = _REPO_ROOT / "app" / "config" / "manual_feed_cadence_inputs.json"


#: R2 — three distinct load outcomes. Collapsing them was the defect: a MALFORMED artifact became
#: indistinguishable from an ABSENT one, so a corrupted governed input read as "we simply have no
#: calendar yet" and nobody would ever know it was broken.
INPUTS_ABSENT, INPUTS_INVALID, INPUTS_OK = "absent", "invalid", "ok"

#: The minimum a governed inputs artifact must declare to be usable at all.
_REQUIRED_INPUT_KEYS = ("calendar",)
_REQUIRED_CALENDAR_KEYS = ("season", "week1_kickoff", "final_game")
#: EVERY calendar key the engine consumes. `combine_complete` was omitted while
#: `playerprofiler.player_season` consumes it, so a bad value there survived validation and could
#: only fail later, and only if a stream happened to reach that branch.
_CALENDAR_TIME_KEYS = ("week1_kickoff", "final_game", "prior_final_game",
                       "league_year_open", "draft_complete", "combine_complete")
#: Evidence records must carry these, timezone-aware.
_HELD_TIME_KEYS = ("ingested_at",)
_OFFER_TIME_KEYS = ("observed_at",)


def _load_cadence_inputs(
    path: Optional[Path] = None,
) -> tuple[str, Optional[dict[str, Any]], str]:
    """Load governed cadence facts, distinguishing ABSENT from INVALID.

    Returns (status, payload, detail). A schema check happens HERE, at the evidence boundary,
    because a partial-but-valid JSON object previously passed the isinstance test and then raised
    KeyError('calendar') deep inside evaluation — which aborted the entire controller run before any
    later source could be isolated. One malformed config file took down every route.
    """
    target = Path(path) if path is not None else MANUAL_CADENCE_INPUTS
    if not target.is_file():
        return INPUTS_ABSENT, None, "no governed calendar/inventory artifact exists"
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return INPUTS_INVALID, None, f"unreadable governed inputs: {type(exc).__name__}"
    if not isinstance(payload, dict):
        return INPUTS_INVALID, None, "governed inputs must be a JSON object"
    return _validate_inputs(payload)


def _validate_inputs(payload: Any) -> tuple[str, Optional[dict[str, Any]], str]:
    """Public entry point: a malformed artifact can never escape as an exception.

    An unexpected shape previously raised out of the validator (TypeError from iterating an int)
    and crashed the controller BEFORE source isolation — one bad config file taking down every
    route, which is the failure this boundary exists to stop. Any unanticipated error is now
    reported as INVALID evidence, because that is what it is.
    """
    try:
        return _validate_inputs_inner(payload)
    except Exception as exc:  # noqa: BLE001 - a validator must not propagate
        return INPUTS_INVALID, None, f"governed inputs failed validation: {type(exc).__name__}: {exc}"


def _validate_inputs_inner(payload: Any) -> tuple[str, Optional[dict[str, Any]], str]:
    """Schema check applied to EVERY input, however it arrived.

    Validating only the file-loaded path left a hole: a caller passing a partial dict directly
    skipped the check entirely and still raised KeyError('calendar') deep inside evaluation. The
    boundary has to be the DATA, not the door it came through.
    """
    if not isinstance(payload, dict):
        return INPUTS_INVALID, None, "governed inputs must be a JSON object"
    missing = [k for k in _REQUIRED_INPUT_KEYS if k not in payload]
    if missing:
        return INPUTS_INVALID, None, f"governed inputs missing keys: {', '.join(missing)}"
    calendar = payload.get("calendar")
    if not isinstance(calendar, dict):
        return INPUTS_INVALID, None, "governed inputs calendar must be an object"
    missing_cal = [k for k in _REQUIRED_CALENDAR_KEYS if k not in calendar]
    if missing_cal:
        return INPUTS_INVALID, None, f"calendar missing keys: {', '.join(missing_cal)}"
    # KEY PRESENCE IS NOT VALIDITY. An unparseable or naive timestamp previously passed this check
    # and then blew up — or worse, did NOT blow up, because the failure only surfaced when a stream
    # happened to carry held data. A guard whose effect depends on incidental data presence is not
    # a guard.
    for key in _CALENDAR_TIME_KEYS:
        value = calendar.get(key)
        if key not in calendar:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return INPUTS_INVALID, None, f"calendar {key} is not an ISO-8601 timestamp: {value!r}"
        if parsed.tzinfo is None:
            return INPUTS_INVALID, None, f"calendar {key} must be timezone-aware: {value!r}"
    for key in ("game_week_completions",):
        declared = calendar.get(key)
        if declared is not None and not isinstance(declared, list):
            return INPUTS_INVALID, None, (
                f"calendar {key} must be a list, got {type(declared).__name__}"
            )
        for value in declared or []:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return INPUTS_INVALID, None, f"calendar {key} entry is not a timestamp: {value!r}"
            if parsed.tzinfo is None:
                return INPUTS_INVALID, None, f"calendar {key} entry must be tz-aware: {value!r}"

    # NESTED SHAPES. held/offer/availability are traversed as mappings during evaluation. Leaving
    # their container and record shapes unchecked reproduced the exact source-dependent defect this
    # boundary exists to remove: the artifact failed only when incidental data reached a bad branch.
    # SEMANTIC types, not just presence. A season that is a string sorts and compares wrongly and
    # would silently mis-derive every coverage gap.
    season = calendar.get("season")
    if not isinstance(season, int) or isinstance(season, bool):
        return INPUTS_INVALID, None, f"calendar season must be an integer, got {season!r}"

    from . import feed_cadence

    for section, time_keys in (("held", _HELD_TIME_KEYS), ("offer", _OFFER_TIME_KEYS)):
        block = payload.get(section)
        if block is None:
            continue
        if not isinstance(block, dict):
            return INPUTS_INVALID, None, f"{section} must be an object, got {type(block).__name__}"
        for source, streams in block.items():
            if source not in feed_cadence.MANUAL_SOURCES:
                return INPUTS_INVALID, None, (
                    f"{section}.{source} is not a known manual source "
                    f"{sorted(feed_cadence.MANUAL_SOURCES)}"
                )
            if not isinstance(streams, dict):
                return INPUTS_INVALID, None, (
                    f"{section}.{source} must be an object, got {type(streams).__name__}"
                )
            declared = set(feed_cadence.streams_for(source))
            for stream, record in streams.items():
                # A TYPOED KEY IS THE WORST FAILURE HERE: it is silently ignored, so the operator
                # believes the data was supplied while the stream reports undetermined forever.
                if stream not in declared:
                    return INPUTS_INVALID, None, (
                        f"{section}.{source}.{stream} is not a declared stream; "
                        f"expected one of {sorted(declared)}"
                    )
                if record is None:
                    continue
                if not isinstance(record, dict):
                    return INPUTS_INVALID, None, (
                        f"{section}.{source}.{stream} must be an object, "
                        f"got {type(record).__name__}"
                    )
                # Presence: evidence timestamps, plus provenance on an offer (an offer with no
                # stated provenance is a bare oracle, which the cadence contract refuses).
                required = time_keys + (("provenance",) if section == "offer" else ())
                for key in required:
                    if key not in record or not str(record.get(key) or "").strip():
                        return INPUTS_INVALID, None, (
                            f"{section}.{source}.{stream} is missing {key}"
                        )
                # Validity: only the TIME keys are timestamps. An earlier edit of mine orphaned this
                # loop inside the covered_seasons block, where it reused a leaked `key` and checked
                # `newest_season` as an ISO-8601 string — rejecting a perfectly valid artifact.
                for key in time_keys:
                    bad = _bad_timestamp(record[key])
                    if bad:
                        return INPUTS_INVALID, None, (
                            f"{section}.{source}.{stream}.{key} {bad}: {record[key]!r}"
                        )
                # Semantics: seasons are integers. A string season sorts and compares wrongly and
                # would silently mis-derive every coverage gap.
                value = record.get("newest_season")
                if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                    return INPUTS_INVALID, None, (
                        f"{section}.{source}.{stream}.newest_season must be an integer, "
                        f"got {value!r}"
                    )
                # COVERAGE EVIDENCE IS MANDATORY, not optional. Omitting it validated fine and
                # then reported coverage ADEQUATE from an empty set — completeness claimed from
                # nothing at all, which is the false reassurance the two axes exist to prevent.
                if "covered_seasons" not in record:
                    return INPUTS_INVALID, None, (
                        f"{section}.{source}.{stream} is missing covered_seasons; coverage cannot "
                        "be asserted without the evidence for it"
                    )
                # `null` is not evidence. Treating it as "absent and therefore fine" reproduced
                # the same false-adequate defect as omitting the key entirely.
                seasons = record.get("covered_seasons")
                if not isinstance(seasons, list):
                    return INPUTS_INVALID, None, (
                        f"{section}.{source}.{stream}.covered_seasons must be a list, "
                        f"got {type(seasons).__name__}"
                    )
                if True:
                    bad_season = next(
                        (s for s in seasons if not isinstance(s, int) or isinstance(s, bool)), None
                    )
                    if bad_season is not None:
                        return INPUTS_INVALID, None, (
                            f"{section}.{source}.{stream}.covered_seasons must be integers, "
                            f"got {bad_season!r}"
                        )

    availability = payload.get("availability")
    if availability is not None:
        if not isinstance(availability, dict):
            return INPUTS_INVALID, None, (
                f"availability must be an object, got {type(availability).__name__}"
            )
        known_windows = {
            p.window for key in feed_cadence._REGISTRY
            for p in (feed_cadence._REGISTRY[key],) if p.window
        }
        for window, record in availability.items():
            if window not in known_windows:
                return INPUTS_INVALID, None, (
                    f"availability.{window} is not a known window {sorted(known_windows)}"
                )
            if not isinstance(record, dict):
                return INPUTS_INVALID, None, (
                    f"availability.{window} must be an object, got {type(record).__name__}"
                )
            if "available_at" not in record:
                return INPUTS_INVALID, None, f"availability.{window} is missing available_at"
            bad = _bad_timestamp(record["available_at"])
            if bad:
                return INPUTS_INVALID, None, (
                    f"availability.{window}.available_at {bad}: {record['available_at']!r}"
                )
    return INPUTS_OK, payload, ""


def _bad_timestamp(value: Any) -> Optional[str]:
    """Return why a timestamp is unusable, or None when it is fine."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return "is not an ISO-8601 timestamp"
    return "must be timezone-aware" if parsed.tzinfo is None else None


def _undetermined_streams(source: str) -> dict[str, Any]:
    """Every DECLARED stream, serialized as uncomputable.

    R1 — the early-return paths previously emitted `coverage: null` and `streams: null`, so a source
    with no governed inputs, or an incomplete route, showed NOTHING in the report. Omission is
    exactly how a gap becomes invisible; the states exist so an unknown stream can be REPORTED.
    """
    from . import feed_cadence

    return {
        stream: feed_cadence.StreamState(
            source=source, stream=stream,
            cadence=feed_cadence.UNDETERMINED, coverage=feed_cadence.UNKNOWN,
        ).as_dict()
        for stream in feed_cadence.streams_for(source)
    }


def _manual_result(
    entry: ManifestEntry,
    checked_at: str,
    inputs: Optional[dict[str, Any]] = None,
    snapshot: Optional[tuple[str, Optional[dict[str, Any]], str]] = None,
) -> SourceResult:
    """A manual source reports TWO AXES, per stream, and never a one-day clock.

    THE DEFECT THIS REPLACES, in David's words: "why are my manual ones due? look at the data - what
    could possibly have changed?" The old rule was `due = age > 1.0 day` applied to sources holding
    season-complete data whose next possible change is a game that has not been played.

    R3 — evaluation uses the SAME instant the report is stamped with. Re-reading the clock here let
    report time and evaluated state disagree across a window boundary, so a report could claim a
    state that was not true at the moment it says it was taken.
    """
    from . import feed_cadence

    now = _parse_checked_at(checked_at)
    status = entry_status(entry)
    known_source = entry.source in feed_cadence.MANUAL_SOURCES

    if status.missing:
        # Route diagnostics are RETAINED, and the per-stream axes are still enumerated.
        return SourceResult(
            source=entry.source, state="manual_route_incomplete", failed=False,
            checked_at=checked_at, freshness=feed_cadence.UNDETERMINED,
            coverage=feed_cadence.UNKNOWN,
            streams=_undetermined_streams(entry.source) if known_source else {},
            missing=status.missing,
        )

    last = marker_last_success(entry)
    age = marker_age_days(entry)

    if inputs is not None:
        load_status, inputs, detail = _validate_inputs(inputs)
    elif snapshot is not None:
        load_status, inputs, detail = snapshot
    else:
        load_status, inputs, detail = _load_cadence_inputs()

    if load_status != INPUTS_OK or not known_source:
        # ABSENT inputs are an honest gap: nothing is broken, we simply cannot compute yet.
        # INVALID inputs are a DEFECT in governed configuration, and failing open on those means a
        # corrupted artifact produces a green controller run forever. Absent -> not failed;
        # invalid -> FAILED, so the aggregate exit is nonzero and somebody looks at it.
        invalid = load_status == INPUTS_INVALID
        return SourceResult(
            source=entry.source,
            state="manual_inputs_invalid" if invalid else "manual_undetermined",
            failed=invalid,
            checked_at=checked_at, last_success_at=last,
            freshness=feed_cadence.UNDETERMINED, coverage=feed_cadence.UNKNOWN,
            streams=_undetermined_streams(entry.source) if known_source else {},
            age_days=age,
            detail=detail or "per-stream cadence is uncomputable without governed inputs",
        )

    states = feed_cadence.evaluate_source(
        source=entry.source, now=now, calendar=inputs["calendar"],
        held=(inputs.get("held") or {}).get(entry.source),
        offer=(inputs.get("offer") or {}).get(entry.source),
        availability=inputs.get("availability"),
    )
    return SourceResult(
        source=entry.source,
        state=f"manual_{feed_cadence._rollup_cadence(states.values())}",
        failed=False, checked_at=checked_at, last_success_at=last,
        freshness=feed_cadence._rollup_cadence(states.values()),
        coverage=feed_cadence._rollup_coverage(states.values()),
        age_days=age,
        streams={name: s.as_dict() for name, s in states.items()},
    )


def _parse_checked_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
    # ONE IMMUTABLE SNAPSHOT for the whole run. Loading per source meant a two-source run read the
    # file twice, so a mid-run edit could combine different control-plane vintages inside a single
    # aggregate report.
    cadence_snapshot = _load_cadence_inputs()
    results: dict[str, SourceResult] = {}

    selected = set(only) if only is not None else None

    for entry in manifest:
        if entry.mode == "manual_download":
            # Isolation applies here too: a malformed governed input must not stop later routes.
            try:
                results[entry.source] = _manual_result(
                    entry, checked_at, snapshot=cadence_snapshot
                )
            except Exception as exc:
                results[entry.source] = SourceResult(
                    source=entry.source, state="manual_inputs_invalid", failed=True,
                    checked_at=checked_at, freshness="undetermined", coverage="unknown",
                    streams=_undetermined_streams(entry.source),
                    detail=f"{type(exc).__name__}: {exc}",
                )
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
