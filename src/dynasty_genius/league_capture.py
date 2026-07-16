"""League snapshot capture + marker-pinned runtime loading (F1 spec of record).

Spec: docs/superpowers/specs/2026-07-15-league-snapshot-scheduled-capture-design.md.

The ready marker is the ONLY acceptance record. A run is servable iff the marker
names it and every named artifact re-hashes to the marker's digest. An invalid or
absent marker falls back to the committed seeds — the loader never scans ``runs/``
to guess a servable run, because a complete-looking run directory without an
acceptance record may be an unaccepted partial.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ARTIFACTS: tuple[str, ...] = (
    "snapshot.json",
    "coverage.json",
    "team_posture.json",
    "team_value_matrix.json",
    "roster_cut_report.json",
    "provenance.json",
)
DERIVED_ARTIFACTS: tuple[str, ...] = ARTIFACTS[1:]
MARKER_NAME = "ready_latest.json"
STATUS_NAME = "capture_status_latest.json"
SEED_FALLBACK_CAVEAT = "league_snapshot_seed_fallback"
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = _REPO_ROOT / "app" / "config" / "league_capture_config.json"

# The four tracked seed artifacts the daily run must never touch (F9) and that
# consumers may no longer read directly (F17).
TRACKED_SEED_PATHS: tuple[str, ...] = (
    "app/data/league_snapshots/sleeper_universe_snapshot_latest.json",
    "app/data/valuation/team_posture_latest.json",
    "app/data/valuation/team_value_matrix_latest.json",
    "app/data/valuation/roster_cut_report_latest.json",
)


class CaptureError(RuntimeError):
    """Named-reason capture failure; the reason string IS the contract."""


_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _run_id_is_safe(run_id: object) -> bool:
    """A run_id is a single path segment: no traversal, no separators, no leading dot."""
    return isinstance(run_id, str) and bool(_RUN_ID_PATTERN.fullmatch(run_id)) and ".." not in run_id


@dataclass(frozen=True)
class LeagueSet:
    """One coherent league artifact set: marker-pinned runtime run or seeds."""

    paths: dict[str, Path]
    run_ids: dict[str, str]
    caveat: str | None


def _write_status(runtime_root: Path, status: str, run_id: str) -> None:
    from datetime import datetime, timezone

    reason = status.split(":", 1)[1] if status.startswith("failed:") else None
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / STATUS_NAME).write_text(
        json.dumps(
            {
                "status": status,
                "reason": reason,
                "run_id": run_id,
                # Execution-state clock, not source vintage (that lives in the marker).
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _fail(runtime_root: Path, run_id: str, reason: str) -> CaptureError:
    _write_status(runtime_root, f"failed:{reason}", run_id)
    return CaptureError(reason)


def _load_threshold_bp(config_path: Path) -> int:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CaptureError("league_capture_config_invalid") from None
    threshold = config.get("unresolved_threshold_bp") if isinstance(config, dict) else None
    if (
        not isinstance(config, dict)
        or not isinstance(config.get("schema_version"), str)
        or not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or threshold < 0
    ):
        raise CaptureError("league_capture_config_invalid")
    return threshold


def _validated_rostered_ids(payload: Any) -> list[str]:
    """Payload validation runs BEFORE any derivation (F8/F11)."""
    if not isinstance(payload, dict):
        raise CaptureError("sleeper_payload_invalid:not_a_mapping")
    rosters = payload.get("rosters")
    if not isinstance(rosters, list) or not rosters:
        raise CaptureError("sleeper_payload_invalid:rosters_missing_or_empty")
    rostered: dict[str, None] = {}
    for roster in rosters:
        if not isinstance(roster, dict) or not isinstance(roster.get("players"), list):
            raise CaptureError("sleeper_payload_invalid:roster_shape")
        for player_id in roster["players"]:
            if not isinstance(player_id, str):
                raise CaptureError("sleeper_payload_invalid:player_id_type")
            rostered[player_id] = None
    if not rostered:
        raise CaptureError("sleeper_payload_invalid:no_rostered_players")
    return list(rostered)


def _count_unresolved(payload: dict, rostered: list[str]) -> int:
    """Both real shapes: the Phase-17 builder emits a LIST of identity rows
    (`sleeper_player_id` + `identity_status`); raw Sleeper payloads carry a
    dict map keyed by player id. An unknown shape counts everything unresolved
    so the floor fails loudly instead of guessing."""
    players = payload.get("players")
    if isinstance(players, dict):
        return sum(1 for pid in rostered if pid not in players)
    if isinstance(players, list):
        rows = {
            str(row["sleeper_player_id"]): row
            for row in players
            if isinstance(row, dict) and row.get("sleeper_player_id") is not None
        }
        return sum(
            1
            for pid in rostered
            if (row := rows.get(pid)) is None
            or row.get("identity_status") == "unresolved"
            or row.get("cohort") == "UNRESOLVED_IDENTITY"
        )
    return len(rostered)


def _check_identity_floor(payload: dict, rostered: list[str], threshold_bp: int) -> int:
    unresolved_count = _count_unresolved(payload, rostered)
    total = len(rostered)
    # Integer cross-multiplication: exactly AT the threshold fails closed (spec F14).
    if total and unresolved_count and unresolved_count * 10_000 >= threshold_bp * total:
        raise CaptureError("sleeper_identity_suspect")
    return unresolved_count


def run_capture(
    *,
    fetch_league_state: Callable[[], Any],
    derive_chain: Callable[[dict], dict],
    runtime_root: Path,
    clock: Callable[[], Any],
    run_id: str,
    config_path: Path | None = None,
    rename: Callable[[Path, Path], Any] | None = None,
) -> LeagueSet:
    runtime_root = Path(runtime_root)
    if not _run_id_is_safe(run_id):
        raise _fail(runtime_root, str(run_id), "run_id_invalid")
    run_dir = runtime_root / "runs" / run_id
    if run_dir.exists():
        raise _fail(runtime_root, run_id, "run_id_conflict")

    # Stamped immediately BEFORE the fetch is issued: the source vintage, never build time.
    source_captured_at = clock()
    if getattr(source_captured_at, "tzinfo", None) is None:
        raise _fail(runtime_root, run_id, "clock_naive_rejected")
    from datetime import timedelta as _td

    if source_captured_at.utcoffset() != _td(0):
        raise _fail(runtime_root, run_id, "clock_non_utc_rejected")

    try:
        payload = fetch_league_state()
        rostered = _validated_rostered_ids(payload)
        threshold_bp = _load_threshold_bp(Path(config_path or DEFAULT_CONFIG_PATH))
        unresolved_count = _check_identity_floor(payload, rostered, threshold_bp)
    except CaptureError as exc:
        raise _fail(runtime_root, run_id, str(exc)) from None

    try:
        derived = derive_chain(payload)
    except Exception:
        _write_status(runtime_root, "failed:derive_chain_error", run_id)
        raise
    if not isinstance(derived, dict) or set(derived) != set(DERIVED_ARTIFACTS):
        raise _fail(runtime_root, run_id, "derive_chain_incomplete_set")

    run_dir.mkdir(parents=True)
    digests: dict[str, str] = {}
    provenance = dict(derived["provenance.json"]) if isinstance(derived["provenance.json"], dict) else {}
    provenance["identity"] = {
        "total_rostered": len(rostered),
        "unresolved_count": unresolved_count,
        "unresolved_threshold_bp": threshold_bp,
    }
    derived = {**derived, "provenance.json": provenance}
    contents = {"snapshot.json": payload, **derived}
    try:
        for name in ARTIFACTS:
            body = json.dumps(contents[name], sort_keys=True).encode("utf-8")
            (run_dir / name).write_bytes(body)
            digests[name] = hashlib.sha256(body).hexdigest()
    except Exception:
        # Partial run stays unaccepted (no marker); the failure is still recorded.
        _write_status(runtime_root, "failed:artifact_write_error", run_id)
        raise

    marker = {
        "run_id": run_id,
        "source_captured_at": source_captured_at.isoformat(),
        "artifacts": list(ARTIFACTS),
        "sha256": digests,
        "unresolved_count": unresolved_count,
    }
    tmp = runtime_root / (MARKER_NAME + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(marker, sort_keys=True))
        f.flush()
        os.fsync(f.fileno())
    try:
        (rename or os.replace)(tmp, runtime_root / MARKER_NAME)
    except Exception:
        # Torn publish: the PRIOR valid marker stays in place and keeps serving.
        _write_status(runtime_root, "failed:publish_rename_error", run_id)
        raise
    _write_status(runtime_root, "ok", run_id)
    return LeagueSet(
        paths={name: run_dir / name for name in ARTIFACTS},
        run_ids={name: run_id for name in ARTIFACTS},
        caveat=None,
    )


def _seed_set(seed_paths: dict[str, Path]) -> LeagueSet:
    return LeagueSet(
        paths=dict(seed_paths),
        run_ids={name: "seed" for name in seed_paths},
        caveat=SEED_FALLBACK_CAVEAT,
    )


def load_league_set(runtime_root: Path, seed_paths: dict[str, Path]) -> LeagueSet:
    """Resolve the marker-pinned run (digest-verified) or fall back to seeds."""
    runtime_root = Path(runtime_root)
    marker_path = runtime_root / MARKER_NAME
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _seed_set(seed_paths)
    if not isinstance(marker, dict) or not _run_id_is_safe(marker.get("run_id")):
        return _seed_set(seed_paths)
    # Exact canonical artifact set: traversal, absolute paths, omissions, and
    # extras all fail this single equality (F16).
    if tuple(marker.get("artifacts") or ()) != ARTIFACTS:
        return _seed_set(seed_paths)
    digests = marker.get("sha256")
    if not isinstance(digests, dict) or set(digests) != set(ARTIFACTS):
        return _seed_set(seed_paths)
    run_dir = runtime_root / "runs" / marker["run_id"]
    paths: dict[str, Path] = {}
    for name in ARTIFACTS:
        path = run_dir / name
        try:
            body = path.read_bytes()
        except OSError:
            return _seed_set(seed_paths)
        if hashlib.sha256(body).hexdigest() != digests[name]:
            return _seed_set(seed_paths)
        paths[name] = path
    return LeagueSet(
        paths=paths,
        run_ids={name: marker["run_id"] for name in ARTIFACTS},
        caveat=None,
    )


# --- Production wiring -----------------------------------------------------------

DEFAULT_RUNTIME_ROOT = _REPO_ROOT / "app" / "data" / "league_runtime"

# The committed seed set. This module is the single sanctioned home for these
# tracked paths (F17 allowlists it); every consumer resolves through
# load_production_league_set instead.
PRODUCTION_SEED_PATHS: dict[str, Path] = {
    "snapshot.json": _REPO_ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json",
    "coverage.json": _REPO_ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_coverage_latest.json",
    "team_posture.json": _REPO_ROOT / "app" / "data" / "valuation" / "team_posture_latest.json",
    "team_value_matrix.json": _REPO_ROOT / "app" / "data" / "valuation" / "team_value_matrix_latest.json",
    "roster_cut_report.json": _REPO_ROOT / "app" / "data" / "valuation" / "roster_cut_report_latest.json",
    "provenance.json": _REPO_ROOT / "app" / "config" / "league_runtime_provenance_seed.json",
}


def load_production_league_set() -> LeagueSet:
    """The one production resolution: marker-pinned runtime run, else seeds."""
    return load_league_set(DEFAULT_RUNTIME_ROOT, PRODUCTION_SEED_PATHS)


SEED_RELATIVES: dict[str, str] = {
    name: str(path.relative_to(_REPO_ROOT)) for name, path in PRODUCTION_SEED_PATHS.items()
}


def load_league_set_for_root(root: Path) -> LeagueSet:
    """Root-relative resolution for scripts whose tests monkeypatch ROOT.

    Resolves the runtime store and the seed set under ``root`` using the same
    relative layout as production, so hermetic tests keep their tmp-root
    isolation while production callers pass the repo root.
    """
    root = Path(root)
    seeds = {name: root / rel for name, rel in SEED_RELATIVES.items()}
    return load_league_set(root / "app" / "data" / "league_runtime", seeds)


# --- F17: the loader-migration anti-rot scan -----------------------------------

# Producer chain (Appendix A): these stay path-aware by design — they build or
# refresh the seed artifacts themselves. Everything else must go through
# load_league_set.
_ALLOWED_PRODUCERS: tuple[str, ...] = (
    "src/dynasty_genius/league_capture.py",
    "scripts/run_league_snapshot_capture.py",
    "scripts/run_league_intelligence_refresh.py",
    "scripts/refresh_league_intelligence.py",
    "scripts/build_team_posture.py",
    "scripts/build_team_value_matrix.py",
    "scripts/build_roster_cut_report.py",
    "scripts/build_sleeper_universe_snapshot.py",
    "src/dynasty_genius/sleeper_universe.py",
    "src/dynasty_genius/team_posture.py",
    "src/dynasty_genius/team_value_matrix.py",
)
_SCAN_ROOTS = ("app", "src", "scripts")
_NEEDLES = tuple(Path(p).name for p in TRACKED_SEED_PATHS)


def assert_no_legacy_direct_readers(*, repo_root: Path) -> None:
    """Fail if any non-producer source file references a tracked seed path."""
    repo_root = Path(repo_root)
    allowed = {repo_root / rel for rel in _ALLOWED_PRODUCERS}
    violations: list[str] = []
    for root in _SCAN_ROOTS:
        for path in sorted((repo_root / root).rglob("*.py")):
            if path in allowed or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in _NEEDLES:
                if needle in text:
                    violations.append(f"{path.relative_to(repo_root)}: {needle}")
    if violations:
        raise AssertionError(
            "legacy direct readers of tracked league seeds (migrate to "
            "load_league_set): " + "; ".join(violations)
        )
    return None
