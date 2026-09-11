"""DG-224 — the forward market tracker: decide WHEN to enrol and WHEN a grade is due.

This module orchestrates. It computes no score, declares no policy and re-implements no rule that
already exists, because a second implementation of an existing rule is a second opinion about it.
Everything it stands on is called through a seam:

  * `build_evaluation_inputs` builds and validates the enrollment.
  * `save_record` appends it — content-addressed, so a duplicate save is already impossible.
  * `select_endpoint` chooses the graded capture, before results and deterministically.
  * the existing grade CLI does the grading.

**The states are the product here.** Three absences look alike from a distance and must never be
merged:

  * `awaiting_capture` — no fresh reading yet. A normal morning while the baseline builds.
  * `awaiting` / `missing` — registered, and the window has not opened or has opened with no endpoint
    to grade. A wait, and retryable.
  * an entry in `errors` — the bytes are wrong. A fault.

If any two of those merge, an ordinary morning pages and a real fault hides among the noise. That is
why every stage reports separately and why a failure in one never erases the valid work of another.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .track_record_inputs import MARKET_START_MAX_AGE, build_evaluation_inputs
from .track_record_store import list_records, save_record
from .workspace_snapshot_store import list_snapshots, save_snapshot

SCHEMA_VERSION = 1

#: Every key root's config must carry. Named individually so a refusal says which one is missing.
REQUIRED_KEYS = (
    "schema_version", "template_archive_root", "template_snapshot_id", "archive_root",
    "evaluation_root", "runs_root", "market_plan_path", "expected_market_plan_sha256",
    "expected_report_sha256", "source_db", "latest_receipt", "capture_root",
)

#: Optional and carried through to the adapter untouched. Absent means no historical receipts were
#: extracted yet; it is never inferred and never defaulted to a directory scan.
OPTIONAL_KEYS = ("historical_receipts",)

#: The declared market horizons. Read from the existing evaluator rather than restated here.
HORIZONS = (30, 90)

#: How long an open window stays retryable before a missing endpoint is recorded once and closed.
WINDOW_DAYS = 3


class TrackerConfigError(ValueError):
    """The configuration is wrong. Nothing is written when this is raised."""


class TrackerError(RuntimeError):
    """A stage failed on real inputs. Distinct from a stage that is merely waiting."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise TrackerConfigError(message)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: Any, what: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TrackerError(f"{what} has no timezone")
        return value
    if not isinstance(value, str) or not value:
        raise TrackerError(f"{what} is not an instant")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # noqa: TRY003 - the message names the field
        raise TrackerError(f"{what} is not an instant: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrackerError(f"{what} has no timezone")
    return parsed


def _within(root: Path, other: Path) -> bool:
    """True when `other` is `root` or sits inside it, following symlinks on both sides."""
    a = root.resolve()
    b = other.resolve()
    return a == b or a in b.parents


def validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Check the configuration completely before anything is written.

    Output roots are refused if they overlap an input root: mutable output inside an immutable
    template is how a run corrupts the thing it was reading. Paths are resolved first, so a symlink
    into the shared tree cannot slip past a string comparison.
    """
    _require(isinstance(config, Mapping), "the config must be a mapping")
    missing = [k for k in REQUIRED_KEYS if k not in config]
    _require(not missing, f"the config is missing {', '.join(missing)}")
    _require(
        config["schema_version"] == SCHEMA_VERSION,
        f"the config schema_version is {config['schema_version']!r}, not {SCHEMA_VERSION}",
    )

    plan_path = Path(str(config["market_plan_path"]))
    _require(plan_path.is_file(), f"the market plan {plan_path} does not exist")
    plan_bytes = plan_path.read_bytes()
    actual = hashlib.sha256(plan_bytes).hexdigest()
    _require(
        actual == str(config["expected_market_plan_sha256"]),
        f"the market plan hashes to {actual}, not the {config['expected_market_plan_sha256']} "
        "the config expects",
    )

    # capture_root is written to by the adapter, so it is an OUTPUT and must satisfy the output
    # rules rather than merely not colliding with them.
    input_keys = ("template_archive_root", "source_db", "latest_receipt", "market_plan_path")
    snapshot_id = str(config["template_snapshot_id"])
    _require(len(snapshot_id) == 64 and all(c in "0123456789abcdef" for c in snapshot_id),
             "template_snapshot_id must be a sha256 identity")
    history_paths = [Path(str(p)) for p in config.get("historical_receipts", [])]
    for source in history_paths:
        _require(source.is_absolute() and not any(p.is_symlink() for p in (source, *source.parents)),
                 "Historical receipt paths must be absolute without symlinks")
    output_keys = ("evaluation_root", "runs_root", "archive_root", "capture_root")

    for key in output_keys + input_keys:
        candidate = Path(str(config[key]))
        _require(candidate.is_absolute(), f"{key} {candidate} must be an absolute path")
        # A symlinked ANCESTOR is enough to land output in the shared tree, so every parent is
        # checked, not just the leaf. Resolving the leaf alone would miss /private/link/runs.
        for parent in [candidate, *candidate.parents]:
            _require(
                not parent.is_symlink(),
                f"{key} {candidate} passes through the symlink {parent}; output must sit on a real "
                "private path",
            )

    for out_key in output_keys:
        out = Path(str(config[out_key]))
        shared = Path("/Users/davidleess/dynasty-genius-product/app/data")
        _require(not _within(shared, out), f"{out_key} must not write shared app/data")
        for source in history_paths:
            _require(not (_within(source, out) or _within(out, source)),
                     "Output overlaps a historical receipt")
        for in_key in input_keys:
            source = Path(str(config[in_key]))
            _require(
                not (_within(source, out) or _within(out, source)),
                f"{out_key} {out} overlaps the input {in_key} {source}; output and source must be "
                "separate",
            )
        for other_key in output_keys:
            if other_key == out_key:
                continue
            other = Path(str(config[other_key]))
            _require(
                not _within(other, out),
                f"{out_key} {out} sits inside {other_key} {other}; each output root is its own",
            )

    report_sha = str(config["expected_report_sha256"])
    _require(
        len(report_sha) == 64 and all(c in "0123456789abcdef" for c in report_sha),
        f"expected_report_sha256 {report_sha!r} is not a sha256 digest",
    )
    # The template's OWN report bytes are verified here, before any lock is taken or any run
    # directory exists. Checking only the digest's shape would let a wrong template through and the
    # refusal would arrive after output had already been created.
    template_report = Path(str(config["template_archive_root"])) / str(
        config["template_snapshot_id"]
    ) / "report.json"
    _require(template_report.is_file(), "The template report is missing")
    if template_report.is_file():
        actual_report = hashlib.sha256(template_report.read_bytes()).hexdigest()
        _require(
            actual_report == report_sha,
            f"the template report hashes to {actual_report}, not the {report_sha} the config "
            "expects; this is not the forecast the tracker was configured for",
        )
    return {"plan_bytes": plan_bytes, "plan_path": plan_path, "expected_report_sha256": report_sha}


def count_records(evaluation_root: Path | str) -> int:
    """Every record in the private store. Used by tests to prove a cycle wrote nothing."""
    root = Path(evaluation_root)
    if not root.is_dir():
        return 0
    return sum(
        1
        for shard in root.iterdir()
        if shard.is_dir() and len(shard.name) == 2
        for directory in shard.iterdir()
        if directory.is_dir()
    )


def _all_enrollments(
    evaluation_root: Path, archive_root: Path,
    list_archived: Callable[[Path], Sequence[Mapping[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Every enrollment in the private store, found through the private ARCHIVE's own snapshots.

    The forward reading is a NEW snapshot with its own id, so looking records up by the TEMPLATE's id
    finds nothing — a bug a fixture that shared the two ids hid completely. `list_records` requires a
    snapshot_id, so the ids come from `list_snapshots` on the runner's own archive rather than from
    parsing the filesystem, which would read whatever happened to be there.
    """
    found: list[dict[str, Any]] = []
    for receipt in (list_archived or list_snapshots)(archive_root):
        snapshot_id = receipt.get("snapshot_id")
        if not snapshot_id:
            continue
        try:
            found.extend(
                record
                for record in list_records(evaluation_root, snapshot_id=snapshot_id)
                if record.get("kind") == "enrollment"
            )
        except FileNotFoundError:
            continue
    return found


def select_capture(captures: Sequence[Mapping[str, Any]], *, now: datetime) -> dict[str, Any]:
    """The freshest complete capture that could legitimately be a start price at `now`.

    Chosen by its own stated retrieval time, never by the momentum it would produce. A capture
    stamped after `now` did not exist yet; one older than the declared start-price age is a reading
    from a different day and registering it would date the enrollment wrongly.
    """
    if not captures:
        return {"state": "awaiting_capture", "reason": "no capture has been collected yet",
                "capture_id": None}

    eligible: list[tuple[datetime, str, Mapping[str, Any]]] = []
    for capture in captures:
        if not isinstance(capture, Mapping):
            raise TrackerError("a capture is not an object")
        payload = capture.get("market_bytes")
        if not isinstance(payload, (bytes, bytearray)):
            raise TrackerError(
                f"capture {capture.get('capture_id')!r} carries no bytes, so its prices are unbound"
            )
        if capture.get("complete") is not True:
            continue
        as_of = _parse(capture.get("as_of"), f"capture {capture.get('capture_id')!r} as_of")
        known = _parse(capture.get("known_at"), "capture known_at")
        observed = _parse(capture.get("observed_at"), "capture observed_at")
        if as_of > now or known > now or observed > now:
            continue  # not possessed at this instant; a future timestamp cannot enroll today
        if observed < known or known != as_of:
            raise TrackerError("Capture retrieval and preservation chronology disagree")
        if now - as_of > MARKET_START_MAX_AGE:
            continue
        eligible.append((as_of, str(capture.get("capture_id") or ""), capture))

    if not eligible:
        hours = int(MARKET_START_MAX_AGE.total_seconds() // 3600)
        return {
            "state": "awaiting_capture",
            "reason": (
                f"no complete capture was retrieved within {hours} hours of this cycle, so no start "
                "price can be registered yet"
            ),
            "capture_id": None,
        }
    eligible.sort(key=lambda item: (item[0], item[1]))
    chosen = eligible[-1][2]
    return {
        "state": "selected",
        "reason": "",
        "capture_id": chosen.get("capture_id"),
        "as_of": chosen.get("as_of"),
        "capture": chosen,
    }


def _eligible_registration(record: Mapping[str, Any]) -> bool:
    market = (record.get("document") or {}).get("market") or {}
    return market.get("state") == "awaiting_capture" and market.get("provenance_class") == "contemporaneous"


def _identity_and_policy(document: Mapping[str, Any]) -> tuple:
    """Forecast identity plus both policy hashes. The forward market DATE is deliberately excluded —
    a later capture of the same forecast is the same measurement, not a new one."""
    return (
        document.get("forecast_identity"),
        (document.get("production") or {}).get("plan_sha256"),
        (document.get("market") or {}).get("plan_sha256"),
    )


def _forecast_identity_of_template(
    config: Mapping[str, Any], checked: Mapping[str, Any], now: datetime
) -> tuple | None:
    """This forecast's identity + policy, computed from the ORIGINAL verified template.

    Built through the same pure builder the enrollment uses, on the template rather than on the
    forward reading, so the answer does not move when a later market capture arrives. `None` means
    the template could not be read — the caller then declines to match rather than matching anything,
    because "match any" would treat a different forecast's enrollment as this one's.
    """
    try:
        from scripts.capture_track_record_inputs import read_archived_artifacts

        from .workspace_snapshot_store import read_snapshot

        archive = Path(str(config["template_archive_root"]))
        snapshot_id = str(config["template_snapshot_id"])
        artifacts = read_archived_artifacts(archive, snapshot_id)
        snapshot = read_snapshot(archive, snapshot_id)
        built = build_evaluation_inputs(
            snapshot=snapshot, artifacts=artifacts,
            baseline_source=None, schedule_source=None, market_history_source=None,
            market_plan=json.loads(bytes(checked["plan_bytes"]).decode("utf-8")),
            captured_at=now,
        )
        return _identity_and_policy(built["document"])
    except Exception as exc:
        raise TrackerConfigError(f"Cannot verify original forecast identity: {exc}") from exc


def _code_sha() -> str:
    """The COMMIT the running code came from, or `unknown`.

    The store refuses anything else, and it is right to: a file digest is not a commit, and claiming
    a commit that does not contain the running code is worse than admitting ignorance. A dirty tree
    is therefore `unknown` rather than a HEAD that does not describe what actually ran.
    """
    import subprocess

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[3],
            capture_output=True, text=True, timeout=5, check=False,
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=Path(__file__).resolve().parents[3],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except Exception:  # noqa: BLE001 - no git is not a fault, it is ignorance
        return "unknown"
    commit = head.stdout.strip()
    if head.returncode != 0 or len(commit) != 40 or dirty.stdout.strip():
        return "unknown"
    return commit


def _forecast_identity(document: Mapping[str, Any]) -> tuple:
    """What makes two enrollments the same measurement. Enrolment time is deliberately excluded."""
    return (
        document.get("snapshot_id"),
        document.get("forecast_identity"),
        (document.get("production") or {}).get("plan_sha256"),
        (document.get("market") or {}).get("plan_sha256"),
    )


def _due_at(t0: datetime, horizon: int) -> datetime:
    return t0 + timedelta(days=horizon)


def plan_evaluations(
    enrollment: Mapping[str, Any], *, now: datetime, graded: Mapping[tuple, Mapping[str, Any]],
    endpoints: Callable[[int], Mapping[str, Any] | None],
) -> list[dict[str, Any]]:
    """One entry per horizon, in exactly one state.

    `awaiting` before the window opens is the state that stops a fifteen-minute cadence from writing
    a grade record every tick. `missing` while the window is open stays retryable, because the
    endpoint may still arrive; once the window has passed it is recorded once and closed.
    """
    document = enrollment.get("document") or {}
    market = document.get("market") or {}
    t0 = _parse(market.get("t0"), "the enrollment t0")
    out: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        opens = _due_at(t0, horizon)
        closes = opens + timedelta(days=WINDOW_DAYS)
        key = (enrollment.get("record_id"), horizon)
        entry: dict[str, Any] = {
            "enrollment_id": enrollment.get("record_id"),
            "claim": "market",
            "horizon_days": horizon,
            "due_at": _stamp(opens),
            "retryable": False,
        }
        if key in graded:
            entry.update(state="skipped", reason="a terminal grade already exists for this endpoint")
        elif now < opens:
            entry.update(state="awaiting", reason="the window has not opened")
        else:
            endpoint = endpoints(horizon)
            if endpoint is not None:
                entry.update(state="due", reason="", endpoint=dict(endpoint))
            elif now <= closes:
                entry.update(
                    state="missing", retryable=True,
                    reason="the window is open and no compatible endpoint capture exists yet",
                )
            else:
                entry.update(
                    state="expired",
                    reason="the window closed with no compatible endpoint capture",
                )
        out.append(entry)
    return out


def run_track_record_cycle(
    *,
    config: Mapping[str, Any],
    captures: Sequence[Mapping[str, Any]],
    now: datetime,
    market_history: Mapping[str, Any] | None = None,
    build_history: Callable[..., Any] | None = None,
    select_endpoint_for: Callable[..., Any] | None = None,
    prepare_outcome: Callable[..., Any] | None = None,
    grade: Callable[..., Any] | None = None,
    outcomes_root: Path | None = None,
    load_template: Callable[..., Any] | None = None,
    build_reading: Callable[..., Any] | None = None,
    save_bundle: Callable[..., Any] | None = None,
    list_archived: Callable[..., Any] | None = None,
    endpoints: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """One cycle: maybe enrol, then report what is due. Writes only under the configured roots.

    `load_template` and `build_reading` are seams for root's forward-reading factory, so this runner
    can be driven and tested before that module lands, and so it never sees the original archive's
    market bytes — the swap it must not perform is therefore unexpressible rather than forbidden.
    """
    checked = validate_config(config)  # raises before any write
    evaluation_root = Path(str(config["evaluation_root"]))
    errors: list[dict[str, Any]] = []

    # ---- capture -------------------------------------------------------------------------------
    try:
        capture_result = select_capture(captures, now=now)
    except TrackerError as exc:
        capture_result = {"state": "error", "reason": str(exc), "capture_id": None}
        errors.append({"stage": "capture", "detail": str(exc)})

    # Root's builder prepares the trailing envelope from the same captures, without backdating the
    # preparation itself. Supplied history wins so a caller can pin one explicitly.
    history_failed = False
    archive_root = Path(str(config["archive_root"]))
    existing = _all_enrollments(evaluation_root, archive_root, list_archived)
    wanted = _forecast_identity_of_template(config, checked, now)
    matching = [r for r in existing if _eligible_registration(r)
                and _identity_and_policy(r.get("document") or {}) == wanted]
    _needs_enrollment = not matching
    if market_history is None and capture_result.get("state") == "selected" and _needs_enrollment:
        try:
            from .forward_market_outcomes import build_market_history

            maker = build_history or build_market_history
            market_history = maker(list(captures), now=now)
        except Exception as exc:  # noqa: BLE001
            # A corrupted baseline must not be silently frozen into a new enrollment as a permanent
            # descriptive association. Refuse to enrol; existing valid enrollments still evaluate.
            errors.append({"stage": "history", "detail": str(exc)})
            history_failed = True

    # ---- enrollment ----------------------------------------------------------------------------
    enrollment: dict[str, Any] = {
        "created": False, "record_id": None, "primary": False, "reason": "", "readiness": {},
    }
    if len(matching) > 1:
        raise TrackerError("Multiple enrollments already exist for this forecast and policy")
    if matching:
        # One automatic enrollment per forecast identity AND policy pair. Taking simply the first
        # record would treat any enrollment as this one's, which is wrong the moment a second
        # forecast is tracked.
        first = matching[0]
        enrollment.update(
            record_id=first["record_id"], primary=True,
            reason="this forecast identity is already enrolled; a later capture does not re-enrol it",
            readiness=_readiness(first["document"]),
        )
    elif history_failed:
        enrollment["reason"] = (
            "the trailing history could not be prepared, so no new enrollment was created; a "
            "corrupted baseline must not be frozen into the record"
        )
    elif capture_result.get("state") == "selected":
        try:
            enrollment = _enrol(
                config=config, checked=checked, capture=capture_result["capture"], now=now,
                load_template=load_template, build_reading=build_reading,
                save_bundle=save_bundle, market_history=market_history,
            )
        except TrackerConfigError:
            raise
        except Exception as exc:  # noqa: BLE001 - classified, never swallowed
            errors.append({"stage": "enrollment", "detail": str(exc)})
            enrollment["reason"] = str(exc)
    else:
        enrollment["reason"] = capture_result.get("reason", "")

    # ---- due evaluations ------------------------------------------------------------------------
    evaluations: list[dict[str, Any]] = []
    for record in _all_enrollments(evaluation_root, archive_root, list_archived):
        if not _eligible_registration(record):
            continue
        try:
            graded = _terminal_grades(evaluation_root, str(record.get("snapshot_id") or ""))
            if endpoints is not None:
                picker = lambda h, r=record: endpoints(r, h)  # noqa: E731 - test seam
            else:
                from .forward_market_outcomes import select_market_endpoint

                chooser = select_endpoint_for or select_market_endpoint

                def picker(h, r=record):  # type: ignore[misc]
                    # The helper returns {chosen, reason, considered, rejected}. The SELECTION is
                    # always an object even when nothing was chosen, so returning it whole would
                    # make every horizon look due. Only `chosen` answers the question.
                    #
                    # And a raise here is a FAULT, not an absence. Catching everything and
                    # returning None would report a malformed capture as "no endpoint yet" — the
                    # failure path returning the success signal, which is the shape this project
                    # has paid for most.
                    return chooser(
                        enrollment=r, captures=list(captures), now=now, horizon_days=h
                    ).get("chosen")
            evaluations.extend(
                plan_evaluations(record, now=now, graded=graded, endpoints=picker)
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {"stage": "evaluation", "enrollment_id": record.get("record_id"), "detail": str(exc)}
            )

    # Only DUE or EXPIRED work reaches preparation and the grader. An open window with no endpoint
    # stays retryable and writes nothing, so a fifteen-minute cadence cannot spam the store.
    if outcomes_root is not None:
        for entry in evaluations:
            if entry["state"] not in ("due", "expired"):
                continue
            try:
                from .forward_market_outcomes import prepare_market_outcome

                preparer = prepare_outcome or prepare_market_outcome
                record = next(
                    r for r in _all_enrollments(evaluation_root, archive_root, list_archived)
                    if r.get("record_id") == entry["enrollment_id"]
                )
                prepared = preparer(
                    enrollment=record, captures=list(captures), now=now,
                    horizon_days=entry["horizon_days"],
                    output_root=Path(outcomes_root)
                    / f"{entry['enrollment_id']}-{entry['horizon_days']}",
                )
                entry["prepared"] = {k: str(v) for k, v in dict(prepared).items()}
                if grade is not None:
                    exit_code = grade(prepared, entry)
                    entry["grade_exit"] = exit_code
                    if exit_code:
                        errors.append({
                            "stage": "grade", "enrollment_id": entry["enrollment_id"],
                            "detail": f"the grade CLI exited {exit_code} for horizon "
                                      f"{entry['horizon_days']}",
                        })
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {"stage": "evaluation", "enrollment_id": entry["enrollment_id"],
                     "detail": str(exc)}
                )

    # The selected capture object carries the raw market bytes and its evidence. Serializing it
    # every cycle would write ~500KB per tick — about 4GB over a 90-day window — restating bytes the
    # immutable capture store already holds. Keep the identity, drop the payload.
    reported_capture = {
        k: v for k, v in capture_result.items() if k != "capture"
    }
    chosen = capture_result.get("capture")
    if isinstance(chosen, Mapping):
        reported_capture["known_at"] = chosen.get("known_at")
        reported_capture["observed_at"] = chosen.get("observed_at")
        reported_capture["market_sha256"] = hashlib.sha256(
            bytes(chosen.get("market_bytes") or b"")
        ).hexdigest()

    future = [e["due_at"] for e in evaluations if e["state"] == "awaiting"]
    return {
        "capture": reported_capture,
        "enrollment": enrollment,
        "evaluations": evaluations,
        "errors": errors,
        "next_due": min(future) if future else None,
    }


def _readiness(document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        stream: {
            "state": (document.get(stream) or {}).get("state"),
            "reason": (document.get(stream) or {}).get("reason"),
            "provenance_class": (document.get(stream) or {}).get("provenance_class"),
            "rows": len((document.get(stream) or {}).get("rows") or []),
        }
        for stream in ("production", "market")
    }


def _terminal_grades(evaluation_root: Path, snapshot_id: str) -> dict[tuple, dict[str, Any]]:
    """Grades already written, keyed by (enrollment_id, horizon). A terminal grade is never rewritten."""
    out: dict[tuple, dict[str, Any]] = {}
    try:
        records = list_records(evaluation_root, snapshot_id=snapshot_id)
    except FileNotFoundError:
        return out
    for record in records:
        if record.get("kind") != "grade":
            continue
        document = record.get("document") or {}
        key = (document.get("enrollment_id"), document.get("horizon_days"))
        out[key] = record
    return out


def _enrol(
    *, config: Mapping[str, Any], checked: Mapping[str, Any], capture: Mapping[str, Any],
    now: datetime, load_template: Callable[..., Any] | None,
    build_reading: Callable[..., Any] | None,
    save_bundle: Callable[..., Any] | None = None,
    market_history: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one enrollment from the forward reading and append it."""
    if load_template is None or build_reading is None:
        from .forward_market_reading import (  # type: ignore[attr-defined]
            build_forward_reading,
            load_forward_template,
        )

        load_template = load_template or load_forward_template
        build_reading = build_reading or build_forward_reading

    template = load_template(
        Path(str(config["template_archive_root"])), str(config["template_snapshot_id"])
    )
    # Root's frozen signature exactly — no invented parameter, no introspection of the callable.
    # NOTE for integration: `build_evaluation_inputs` measures start-price freshness against the
    # BUNDLE's `market_as_of`, not against the capture this runner selected. The factory must
    # therefore publish the new capture's retrieval time in the new bundle; if it leaves the
    # template's older date in place, a perfectly fresh capture enrols as `input_unavailable`.
    # Reported to root rather than worked around here.
    bundle = build_reading(
        template,
        bytes(capture["market_bytes"]),
        capture_artifacts={k: bytes(v) for k, v in dict(capture.get("evidence") or {}).items()},
    )

    # ARCHIVE FIRST. The forward reading is a new snapshot with its own id; saving it here is what
    # makes it findable later through `list_snapshots`, and an enrollment whose snapshot cannot be
    # re-read is a record standing on bytes nobody kept.
    archive = save_bundle or save_snapshot
    archived = None
    if not isinstance(bundle, Mapping):
        archived = archive(
            Path(str(config["archive_root"])), bundle, captured_at=now, code_sha=_code_sha(),
        )

    plan = json.loads(bytes(checked["plan_bytes"]).decode("utf-8"))
    if archived is not None:
        from scripts.capture_track_record_inputs import read_archived_artifacts

        from .workspace_snapshot_store import read_snapshot
        archive_root = Path(str(config["archive_root"]))
        archived_id = archived["snapshot"]["snapshot_id"]
        snapshot_source = read_snapshot(archive_root, archived_id)
        enrol_artifacts = read_archived_artifacts(archive_root, archived_id)
    else:
        snapshot_source = bundle["snapshot"]
        enrol_artifacts = bundle["artifacts"]
    built = build_evaluation_inputs(
        snapshot=snapshot_source,
        artifacts=enrol_artifacts,
        baseline_source=None,   # market-only enrollment: production reports its own unavailability
        schedule_source=None,
        # The trailing inventory the adapter imported, if any. Absent leaves the comparator
        # unavailable and the association descriptive — it does NOT make the market stream
        # input_unavailable, which is reserved for a stale start price.
        market_history_source=dict(market_history) if market_history else None,
        market_plan=plan,
        captured_at=now,
    )
    if not _eligible_registration({"document": built["document"]}):
        return {"created": False, "record_id": None, "primary": False,
                "reason": (built["document"].get("market") or {}).get("reason"),
                "readiness": _readiness(built["document"])}
    saved = save_record(
        Path(str(config["evaluation_root"])),
        kind="enrollment",
        document=built["document"],
        artifacts=built["artifacts"],
        recorded_at=now,
    )
    return {
        "created": bool(saved["created"]),
        "record_id": saved["record"]["record_id"],
        "primary": True,
        "reason": "" if saved["created"] else "an identical enrollment already existed",
        "readiness": _readiness(saved["record"]["document"]),
    }
