"""Capture one track-record enrollment from explicit source paths.

Root's API calls :func:`capture_from_paths` directly so the baseline decoding lives in exactly one
place, and the command line is a thin wrapper over the same function. Importing this module parses no
arguments and touches no store.

Two rules are load-bearing:

**The clock is the actual clock.** There is no flag and no parameter that can assert an earlier
capture time, because the whole value of an enrollment is that it was registered before the outcome
was known. Tests inject a clock; nothing else can.

**The archive's own bytes are stored, never a re-serialisation of them.** A hash over a document this
process re-encoded proves only that this process is self-consistent. An earlier version of this file
re-serialised the receipt's ``evaluation_plan`` while its comment claimed original bytes, which would
have changed the archived policy hash. Every artifact is now read raw from the snapshot directory and
verified against the hash the archive itself recorded in ``snapshot.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.dynasty_genius.capture.track_record_inputs import (
    TrackRecordInputError,
    build_evaluation_inputs,
)
from src.dynasty_genius.capture.track_record_store import list_records, save_record
from src.dynasty_genius.capture.workspace_snapshot_store import read_snapshot

PRODUCTION_PLAN_ARTIFACT = "evaluation-plan.json"
MARKET_PLAN_ARTIFACT = "market-plan.json"
ARCHIVE_MANIFEST = "snapshot.json"


def read_archived_artifacts(archive_root: Path | str, snapshot_id: str) -> dict[str, bytes]:
    """Every archived artifact, raw, each re-verified against the hash the archive recorded.

    ``read_snapshot`` returns the two DERIVED documents the surface read; it does not hand back the
    raw sources. A policy hash has to be computable from the archive by someone else, so the bytes
    that go into the record are the archive's own — never anything this process re-encoded, and never
    a path taken from a mutable source manifest.
    """
    directory = Path(archive_root) / snapshot_id
    manifest_path = directory / ARCHIVE_MANIFEST
    if not manifest_path.is_file():
        raise TrackRecordInputError(f"the archived snapshot {snapshot_id} has no {ARCHIVE_MANIFEST}")
    manifest = json.loads(manifest_path.read_text())
    declared = manifest.get("files")
    if not isinstance(declared, dict) or not declared:
        raise TrackRecordInputError(f"the archived {ARCHIVE_MANIFEST} records no file hashes")

    artifacts: dict[str, bytes] = {}
    for name, expected in sorted(declared.items()):
        payload = (directory / name).read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise TrackRecordInputError(
                f"the archived {name} hashes to {actual}, not the {expected} the archive recorded"
            )
        artifacts[name] = payload
    return artifacts


def _read_bytes(path: Path | str, what: str) -> bytes:
    candidate = Path(path)
    if not candidate.is_file():
        raise TrackRecordInputError(f"the {what} source file is missing: {candidate}")
    return candidate.read_bytes()


def _read_json(path: Path | str, what: str) -> dict[str, Any]:
    payload = _read_bytes(path, what)
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as bad:
        raise TrackRecordInputError(f"the {what} source is not readable JSON: {bad}") from bad
    if not isinstance(document, dict):
        raise TrackRecordInputError(f"the {what} source is not a JSON object")
    return document


def _load_source_artifacts(entries: Any, role: str) -> list[dict[str, Any]]:
    """Read each declared artifact's own bytes from its private path, once.

    The receipt names where each prepared file lives; this reads those exact paths into buffers so the
    validator can check the hash and length it was given, and the enrollment can keep the same bytes.
    """
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise TrackRecordInputError(f"the {role} source_artifacts are not a list")
    loaded: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise TrackRecordInputError(f"a {role} source_artifacts entry is not an object")
        path = entry.get("path")
        if not path:
            raise TrackRecordInputError(
                f"the {role} source artifact {entry.get('name')!r} names no path"
            )
        loaded.append(dict(entry) | {"raw_bytes": _read_bytes(path, f"{role} artifact {entry.get('name')}")})
    return loaded


def _load_captures(entries: Any) -> list[dict[str, Any]]:
    """Each capture's own bytes, read from the explicit path its inventory names.

    An ordinary JSON inventory cannot carry raw buffers, so the file names a path per capture and this
    reads it. The bytes are what the selector then parses prices, configuration and as-of from; the
    inventory's sibling keys never stand in for the file.
    """
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise TrackRecordInputError("the market history captures are not a list")
    loaded: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise TrackRecordInputError("a market history capture entry is not an object")
        path = entry.get("path")
        if not path:
            raise TrackRecordInputError(
                f"the history capture {entry.get('capture_id')!r} names no path to its bytes"
            )
        payload = _read_bytes(path, f"history capture {entry.get('capture_id')}")
        declared_length = entry.get("bytes")
        if declared_length is not None and int(declared_length) != len(payload):
            raise TrackRecordInputError(
                f"the history capture {entry.get('capture_id')!r} is {len(payload)} bytes, not the "
                f"{declared_length} its inventory declares"
            )
        loaded.append(dict(entry) | {"raw_bytes": payload})
    return loaded


def _parse(value: Any, what: str) -> datetime:
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError) as bad:
        raise TrackRecordInputError(f"{what} is not a timestamp: {value!r}") from bad
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _refuse_future_sources(envelopes: Mapping[str, Mapping[str, Any] | None], now: datetime) -> None:
    """A source cannot have been read after the moment we are reading it."""
    for name, envelope in envelopes.items():
        if envelope is None:
            continue
        captured = envelope.get("captured_at")
        if captured is None:
            continue
        if _parse(captured, f"the {name} captured_at") > now:
            raise TrackRecordInputError(
                f"the {name} source declares captured_at {captured}, which is in the future "
                f"relative to this capture at {now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )


def capture_from_paths(
    *,
    archive_root: Path | str,
    snapshot_id: str,
    evaluation_root: Path | str,
    baseline_manifest: Path | str,
    baseline_csv: Path | str,
    baseline_receipt: Path | str,
    schedule: Path | str,
    market_plan: Path | str,
    market_history: Path | str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Load the named sources, build one enrollment and append it. Returns the save result.

    The archive is opened read-only. Nothing is written anywhere but the evaluation store, and a
    refusal writes nothing at all.
    """
    now = (clock or (lambda: datetime.now(timezone.utc)))()

    # Validate the archive through its own reader first, then take the raw bytes it stands on.
    snapshot = read_snapshot(archive_root, snapshot_id)
    archived = read_archived_artifacts(archive_root, snapshot_id)

    baseline = dict(_read_json(baseline_receipt, "baseline receipt"))
    baseline["raw_bytes"] = _read_bytes(baseline_receipt, "baseline receipt")
    baseline["manifest_bytes"] = _read_bytes(baseline_manifest, "baseline manifest")
    baseline["csv_bytes"] = _read_bytes(baseline_csv, "baseline csv")
    baseline["source_artifacts"] = _load_source_artifacts(baseline.get("source_artifacts"),
                                                          "baseline")

    schedule_document = dict(_read_json(schedule, "schedule"))
    schedule_document["raw_bytes"] = _read_bytes(schedule, "schedule")
    schedule_document["source_artifacts"] = _load_source_artifacts(
        schedule_document.get("source_artifacts"), "schedule"
    )
    market_plan_bytes = _read_bytes(market_plan, "market plan")
    market_plan_document = json.loads(market_plan_bytes.decode("utf-8"))
    history_document = None
    if market_history:
        history_document = dict(_read_json(market_history, "market history"))
        history_document["raw_bytes"] = _read_bytes(market_history, "market history")
        history_document["source_artifacts"] = _load_source_artifacts(
            history_document.get("source_artifacts"), "market history"
        )
        history_document["captures"] = _load_captures(history_document.get("captures"))

    _refuse_future_sources(
        {"baseline": baseline, "schedule": schedule_document, "market history": history_document},
        now,
    )

    if PRODUCTION_PLAN_ARTIFACT not in archived:
        raise TrackRecordInputError(
            f"the archived snapshot carries no {PRODUCTION_PLAN_ARTIFACT}, so the production policy "
            "hash cannot be bound to the archive"
        )
    # The archive's own bytes, plus the market plan's own bytes. Nothing here is re-encoded.
    artifacts = dict(archived)
    artifacts[MARKET_PLAN_ARTIFACT] = market_plan_bytes

    built = build_evaluation_inputs(
        snapshot=snapshot,
        artifacts=artifacts,
        baseline_source=baseline,
        schedule_source=schedule_document,
        market_history_source=history_document,
        market_plan=market_plan_document,
        captured_at=now,
    )
    # A deliberate re-capture of UNCHANGED frozen inputs is the same registration, so it returns the
    # first one with its original T0. Only genuinely new inputs start a new registration. Without
    # this, every button press would mint a fresh enrolment whose only difference was its clock.
    document = built["document"]
    existing = _matching_enrollment(evaluation_root, document)
    if existing is not None:
        return _result(False, existing)

    saved = save_record(
        evaluation_root, kind="enrollment", document=document,
        artifacts=built["artifacts"], recorded_at=now,
    )
    return _result(saved["created"], saved["record"])


def _matching_enrollment(root: Path | str, document: Mapping[str, Any]) -> dict[str, Any] | None:
    """A prior enrollment of the same forecast, policies and inputs, if one exists.

    Sameness is the things that were frozen: the snapshot, the forecast identity, the two policy
    hashes and every input file hash. The enrolment time is deliberately NOT part of it — that is the
    field that would otherwise differ on every press.
    """
    def identity(candidate: Mapping[str, Any]) -> tuple:
        return (
            candidate.get("snapshot_id"), candidate.get("forecast_identity"),
            candidate.get("production", {}).get("plan_sha256"),
            candidate.get("market", {}).get("plan_sha256"),
            tuple(sorted((candidate.get("input_hashes") or {}).items())),
        )

    wanted = identity(document)
    try:
        prior = list_records(root, snapshot_id=str(document.get("snapshot_id")))
    except FileNotFoundError:
        return None
    for record in prior:
        if record["kind"] == "enrollment" and identity(record["document"]) == wanted:
            return record
    return None


def _result(created: bool, record: Mapping[str, Any]) -> dict[str, Any]:
    document = record["document"]
    return {
        "created": created,
        "record": dict(record),
        "readiness": {
            stream: {
                "state": document[stream]["state"],
                "reason": document[stream]["reason"],
                "provenance_class": document[stream]["provenance_class"],
                "rows": len(document[stream]["rows"]),
            }
            for stream in ("production", "market")
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    for flag, help_text in (
        ("--archive-root", "the existing snapshot archive, opened read-only"),
        ("--snapshot-id", "which archived snapshot to enrol"),
        ("--evaluation-root", "the private append-only evaluation store"),
        ("--baseline-manifest", "the prior-season outcome manifest"),
        ("--baseline-csv", "the prior-season outcome rows"),
        ("--baseline-receipt", "the prior-season source receipt and its knowledge times"),
        ("--schedule", "the target season's schedule bytes and receipt"),
        ("--market-plan", "the market registration plan"),
    ):
        parser.add_argument(flag, required=True, help=help_text)
    parser.add_argument(
        "--market-history", default=None,
        help="optional trailing price capture; absent means the momentum comparator is unavailable",
    )
    args = parser.parse_args(argv)

    try:
        result = capture_from_paths(
            archive_root=args.archive_root, snapshot_id=args.snapshot_id,
            evaluation_root=args.evaluation_root, baseline_manifest=args.baseline_manifest,
            baseline_csv=args.baseline_csv, baseline_receipt=args.baseline_receipt,
            schedule=args.schedule, market_plan=args.market_plan,
            market_history=args.market_history,
        )
    except (TrackRecordInputError, ValueError, FileNotFoundError) as refused:
        print(f"REFUSED: {refused}")
        return 2

    record = result["record"]
    print(
        f"{'saved' if result['created'] else 'already saved'} {record['record_id']}\n"
        f"  snapshot   {record['snapshot_id']}\n"
        f"  recorded   {record['recorded_at']}"
    )
    for stream, readiness in result["readiness"].items():
        print(f"  {stream:11} {readiness['state']} ({readiness['provenance_class']}), "
              f"{readiness['rows']} rows — {readiness['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
