#!/usr/bin/env python3
"""DG-224 — run one forward market tracking cycle.

`--config` is the only argument. There is deliberately **no `--now`**: a tracker that can be told
what time it is can be told to backdate an enrollment, and the whole point of a prospective record is
that its T0 is the moment it actually happened.

Exit codes are the operational contract:
  0  healthy — enrolled, idempotent, waiting for a capture, or waiting for a window to open
  0  another cycle already holds the lock; this one did no work, which is not a fault
  1  a real error — corrupt bytes, a refused configuration, a stage that raised
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.capture.forward_market_tracker import (  # noqa: E402
    run_track_record_cycle,
    validate_config,
)


class CliRefusal(RuntimeError):
    """Something the operator must fix. Reported by name, never as a traceback."""


def _run_directory(runs_root: Path, started: datetime) -> Path:
    """A NEW directory per invocation. An existing report is never overwritten."""
    stamp = started.strftime("%Y%m%dT%H%M%S%fZ")
    directory = runs_root / f"{stamp}-forward-market-tracker"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _lock(path: Path):
    """Advisory, non-blocking, on a persistent inode. Never unlinked.

    Held for the life of the process. A second cycle that cannot take it does no work and says so —
    that is a healthy outcome, not a failure, because the first cycle is already doing the work.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    handle = os.fdopen(fd, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        # ONLY contention means "someone else is doing the work". Catching every OSError would
        # report an EIO or ENOLCK as a healthy skipped cycle, so the tracker would look fine while
        # never running again — the failure path returning the success signal.
        if exc.errno in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
            return None
        raise CliRefusal(f"the tracker lock at {path} could not be taken: {exc}") from exc
    return handle


def _summary(result: dict[str, Any]) -> str:
    capture = result.get("capture") or {}
    enrollment = result.get("enrollment") or {}
    counts: dict[str, int] = {}
    for entry in result.get("evaluations") or []:
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    parts = [f"capture: {capture.get('state')}"]
    parts.append(
        "enrollment: created" if enrollment.get("created") else
        f"enrollment: {enrollment.get('reason') or 'none'}"
    )
    if counts:
        parts.append("evaluations: " + ", ".join(f"{n} {state}" for state, n in sorted(counts.items())))
    if result.get("next_due"):
        parts.append(f"next due: {result['next_due']}")
    if result.get("errors"):
        parts.append(f"ERRORS: {len(result['errors'])}")
    return " · ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    directory = None
    config_bytes = None
    held = None
    old_mask = os.umask(0o077)
    stage = "configuration"
    result: dict[str, Any] = {"errors": [], "status": "ok"}
    try:
        config_bytes = args.config.read_bytes()
        config = json.loads(config_bytes)
        if not isinstance(config, dict):
            raise CliRefusal("the configuration is not an object")
        # The installed runtime names its immutable config by these exact bytes.
        name = args.config.stem
        if len(name) == 64 and all(c in "0123456789abcdef" for c in name) \
                and hashlib.sha256(config_bytes).hexdigest() != name:
            raise CliRefusal("the versioned configuration no longer matches its filename")
        validate_config(config)
        # Verify the pinned original report before creating even a lock file.
        from src.dynasty_genius.capture.forward_market_reading import (
            load_forward_template,
        )
        template = load_forward_template(Path(config["template_archive_root"]), config["template_snapshot_id"])
        if hashlib.sha256(template.artifacts["report.json"]).hexdigest() != config["expected_report_sha256"]:
            raise CliRefusal("the archived forecast differs from the configured report identity")
        runs_root = Path(config["runs_root"])
        directory = _run_directory(runs_root, started)
        stage = "lock"
        held = _lock(runs_root / ".forward-market-tracker.lock")
        if held is None:
            result.update(status="already_running", reason="another tracker cycle holds the lock")
        else:
            from src.dynasty_genius.capture.fc_capture_adapter import (
                capture_market_inventory,
            )
            stage = "capture"
            inventory = capture_market_inventory(
                source_db=Path(config["source_db"]), latest_receipt=Path(config["latest_receipt"]),
                store_root=Path(config["capture_root"]), observed_at=started,
                historical_receipts=[Path(p) for p in config.get("historical_receipts", [])],
            )
            def grade(prepared, entry):
                from scripts.grade_workspace_track_record import main as grade_main
                identity = f"{entry['enrollment_id']}-{entry['horizon_days']}"
                output = directory / "grades" / identity
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = grade_main([
                        "--evaluation-root", config["evaluation_root"],
                        "--enrollment-id", entry["enrollment_id"], "--claim", "market",
                        "--outcome-manifest", str(prepared["manifest_path"]),
                        "--capture-inventory", str(prepared["inventory_path"]),
                        "--horizon-days", str(entry["horizon_days"]),
                        "--evaluated-at", started.isoformat(), "--output-root", str(output),
                    ])
                output.mkdir(parents=True, exist_ok=True)
                for name, value in (("stdout.txt", stdout.getvalue()), ("stderr.txt", stderr.getvalue())):
                    with (output/name).open("x", encoding="utf-8") as stream:
                        stream.write(value)
                return code
            stage = "tracking"
            cycle = run_track_record_cycle(config=config, captures=inventory["captures"], now=started,
                                           grade=grade, outcomes_root=directory/"outcomes")
            result.update(cycle)
            result["capture_inventory"] = {k: v for k, v in inventory.items() if k != "captures"}
            result["capture_inventory"]["preserved_captures"] = len(inventory["captures"])
            if result.get("errors"):
                result["status"] = "error"
    except Exception as exc:
        result.update(status="error", errors=[{"stage": stage, "detail": str(exc), "type": type(exc).__name__}])
    finally:
        if held is not None:
            held.close()
        try:
            result.update(started_at=started.isoformat(), finished_at=datetime.now(timezone.utc).isoformat(),
                          runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
            if config_bytes is not None:
                result["configuration_sha256"] = hashlib.sha256(config_bytes).hexdigest()
            if directory is not None:
                receipt = directory / "cycle.json"
                with receipt.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
                print(_summary(result))
                print(f"receipt: {receipt}")
            else:
                print("refused: " + "; ".join(e["detail"] for e in result["errors"]), file=sys.stderr)
        finally:
            os.umask(old_mask)
    return 1 if result["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
