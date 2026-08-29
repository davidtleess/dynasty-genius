"""Replay-reproducibility harness — DG-050, Master Proposal 3 §6.2.

The guarantee under proof: *replaying a raw snapshot with the same parser
version must reproduce the normalized content the store holds.* Until this
harness existed the guarantee was assumed, never measured — and every captured
week added 2027 training fuel whose vintage-truth was unverified (ticket
DG-050; roadmap L1 "the enabler nearest the edge").

Design rules, in order of precedence:

1. **READ-ONLY, mechanically.** Every SQLite open here is ``mode=ro``; a
   missing store is reported, never created. The store classes' constructors
   run ``CREATE TABLE IF NOT EXISTS`` and are therefore never used here —
   against a trunk-shared symlinked database that would be a write.
2. **The pinned parser IS the replayer.** Normalization and digest code is
   imported from the capture modules, never copied — a copy would drift and
   the harness would then certify the copy, not the parser. Private helpers
   (``_rows_hash`` etc.) are imported deliberately for the same reason; the
   contract test pins parity by replaying a real ``apply_season`` capture.
3. **Same parser version or no verdict.** A snapshot recorded under a
   different schema/parser version is ``parser_version_mismatch`` — §6.2
   promises reproduction under the SAME version, so byte-comparing across
   versions would manufacture false alarms (and false comfort).
4. **Absence is a named status, never silence.** ``no_snapshot`` /
   ``no_matching_raw`` / ``skipped_size_guard`` are results, not omissions —
   a reader must be able to tell "proved" from "could not attempt".

Streams covered, one sampled snapshot each per run:

- nflverse seasonal streams: raw envelope -> ``normalize_rows`` -> the exact
  ``apply_season`` content digest, compared to the ``nflverse_capture`` ledger.
- nflverse snapshot-axis streams (contracts): raw bytes re-hashed against the
  ledger's ``raw_sha256`` (content addressing), then ``normalize_rows`` ->
  ``snapshot_idempotence_digest`` against the ledger's ``content_hash``.
- FantasyCalc forward capture: per-row ``payload_hash`` recomputed from the
  raw sidecar's stored content, and the joinable projection re-derived from
  the raw sidecar and compared row-for-row.
- League snapshot: marker digests re-verified, lineage per-source hashes
  recomputed from the embedded raw sections, and the two derivations that are
  pure functions of stored inputs (coverage, posture) re-run and byte-compared.

The runner writes a dated receipt (embedded UTC timestamp, house pattern):
``app/data/ops/replay_reproducibility_latest.json`` plus an immutable
run-scoped copy under ``app/data/ops/replay_reproducibility/runs/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.dynasty_genius.capture.fc_forward_capture_driver import (
    _content_hash as _fc_content_hash,
)
from src.dynasty_genius.capture.fc_forward_capture_store import (
    _CONTENT_COLUMNS as _FC_CONTENT_COLUMNS,
)
from src.dynasty_genius.nflverse_usage import (
    CONTRACTS,
    DEPTH_CHARTS,
    FF_OPPORTUNITY,
    FTN_CHARTING,
    INJURIES,
    NGS_PASSING,
    NGS_RECEIVING,
    NGS_RUSHING,
    PFR_DEF,
    PFR_PASS,
    PFR_REC,
    PFR_RUSH,
    SNAP_COUNTS,
    IdentityIndex,
    StreamSpec,
    # Imported privates — rule 2 above: the digest recipe must be the store's
    # own, never a copy. Parity is pinned by the DG-050 contract test.
    _coverage_fingerprint,
    _projection_fingerprint,
    _rows_hash,
    normalize_rows,
    snapshot_idempotence_digest,
)
from src.dynasty_genius.nflverse_usage import (
    SCHEMA_VERSION as NFLVERSE_SCHEMA_VERSION,
)
from src.dynasty_genius.sleeper_universe import (
    SCHEMA_VERSION as SLEEPER_SCHEMA_VERSION,
)
from src.dynasty_genius.sleeper_universe import (
    _stable_hash,
    build_coverage_report,
)
from src.dynasty_genius.team_posture import (
    SCHEMA_VERSION as POSTURE_SCHEMA_VERSION,
)
from src.dynasty_genius.team_posture import (
    build_team_posture_artifact,
)

RECEIPT_SCHEMA_VERSION = "replay_reproducibility.v1"

#: The unbound stream specs (loader=None): everything replay needs — columns,
#: grain, eras, digest projection — with no nflreadpy import and no network.
NFLVERSE_SPECS: tuple[StreamSpec, ...] = (
    NGS_PASSING, NGS_RUSHING, NGS_RECEIVING, SNAP_COUNTS, INJURIES,
    PFR_PASS, PFR_RUSH, PFR_REC, PFR_DEF, FF_OPPORTUNITY, FTN_CHARTING,
    DEPTH_CHARTS, CONTRACTS,
)

#: League lineage entries recomputable from the snapshot itself. ``league``,
#: ``sleeper_players`` and ``traded_picks`` hashes cover raw inputs the
#: snapshot stores only projections of — stated, not silently skipped.
_LINEAGE_REPLAYABLE = ("rosters", "users")
_LINEAGE_NOT_REPLAYABLE = ("sleeper_players", "league", "traded_picks")


@dataclass(frozen=True)
class CheckResult:
    """One replay check on one stream. ``evidence`` carries the identifiers
    a reader needs to re-run the claim: paths, hashes, ids, counts."""

    stream: str
    check: str
    status: str  # reproduced | legacy_content_shape | mismatch |
    #              parser_version_mismatch | no_snapshot | no_matching_raw |
    #              skipped_size_guard | error
    evidence: dict[str, Any] = field(default_factory=dict)


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    """mode=ro is the whole read-only contract; a missing file raises here."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _stamp(captured_at: str) -> str:
    """The raw-filename timestamp, exactly as ``write_raw_snapshot`` builds it."""
    return "".join(ch for ch in captured_at if ch.isalnum())


def _season_digest(
    spec: StreamSpec, rows: Sequence[Mapping[str, Any]], coverage: Mapping[str, Any]
) -> str:
    """Byte-identical recipe to ``UsageStore.apply_season`` (parity test-pinned)."""
    return hashlib.sha256(
        f"{_rows_hash(rows)}|{_projection_fingerprint(spec)}"
        f"|{_coverage_fingerprint(coverage)}".encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# nflverse — seasonal axis
# ---------------------------------------------------------------------------


def replay_nflverse_seasonal(
    *,
    db_path: Path,
    raw_root: Path,
    specs: Sequence[StreamSpec] | None = None,
    identity: IdentityIndex | None = None,
    streams: set[str] | None = None,
) -> list[CheckResult]:
    """Per seasonal stream: newest ok capture with a surviving raw file,
    replayed through ``normalize_rows`` and compared to the ledger digest."""
    db_path, raw_root = Path(db_path), Path(raw_root)
    specs = tuple(
        s for s in (specs if specs is not None else NFLVERSE_SPECS)
        if s.capture_axis == "seasonal" and (streams is None or s.name in streams)
    )
    if not specs:
        return []
    if not db_path.exists():
        return [
            CheckResult(
                stream="nflverse", check="store_present", status="no_snapshot",
                evidence={"db_path": str(db_path)},
            )
        ]
    results: list[CheckResult] = []
    with _connect_ro(db_path) as conn:
        for spec in specs:
            results.append(
                _replay_one_seasonal(conn, spec, raw_root=raw_root, identity=identity)
            )
    return results


def _replay_one_seasonal(
    conn: sqlite3.Connection,
    spec: StreamSpec,
    *,
    raw_root: Path,
    identity: IdentityIndex | None,
) -> CheckResult:
    stream = f"nflverse:{spec.name}"
    try:
        ledger = conn.execute(
            "SELECT stream_season, season, rows_total, content_hash, ingested_at "
            "FROM nflverse_capture WHERE stream = ? AND status = 'ok' "
            "ORDER BY CAST(season AS INTEGER) DESC",
            (spec.name,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        return CheckResult(
            stream=stream, check="seasonal_digest", status="no_snapshot",
            evidence={"reason": f"ledger unreadable: {exc}"},
        )
    if not ledger:
        return CheckResult(
            stream=stream, check="seasonal_digest", status="no_snapshot",
            evidence={"reason": "no ok capture in nflverse_capture"},
        )

    chosen, raw_path = None, None
    tried: list[str] = []
    for row in ledger:
        candidate = (
            raw_root / "raw"
            / f"{spec.name}_{row['season']}_{_stamp(row['ingested_at'])}.json"
        )
        if candidate.exists():
            chosen, raw_path = row, candidate
            break
        tried.append(str(candidate))
    if chosen is None:
        return CheckResult(
            stream=stream, check="seasonal_digest", status="no_matching_raw",
            evidence={"searched": tried[:3], "ledger_rows": len(ledger)},
        )

    try:
        envelope = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_version = envelope.get("schema_version")
        if raw_version != NFLVERSE_SCHEMA_VERSION:
            return CheckResult(
                stream=stream, check="seasonal_digest",
                status="parser_version_mismatch",
                evidence={
                    "raw_snapshot": str(raw_path),
                    "raw_schema_version": raw_version,
                    "pinned_schema_version": NFLVERSE_SCHEMA_VERSION,
                },
            )
        season = int(chosen["season"])
        if identity is None and spec.identity_applicable:
            identity = IdentityIndex.from_governed_crosswalk()
        rows, coverage = normalize_rows(
            envelope["records"], spec=spec, season=season, identity=identity
        )
        replayed = _season_digest(spec, rows, coverage)
    except Exception as exc:  # a replay crash is a finding, not a crash
        return CheckResult(
            stream=stream, check="seasonal_digest", status="error",
            evidence={"raw_snapshot": str(raw_path), "error": repr(exc)},
        )

    evidence = {
        "stream_season": chosen["stream_season"],
        "raw_snapshot": str(raw_path),
        "raw_captured_at": envelope.get("captured_at"),
        "ledger_content_hash": chosen["content_hash"],
        "replayed_content_hash": replayed,
        "ledger_rows_total": int(chosen["rows_total"]),
        "rows_total": len(rows),
        "schema_version": NFLVERSE_SCHEMA_VERSION,
    }
    reproduced = (
        replayed == chosen["content_hash"]
        and len(rows) == int(chosen["rows_total"])
    )
    return CheckResult(
        stream=stream, check="seasonal_digest",
        status="reproduced" if reproduced else "mismatch", evidence=evidence,
    )


# ---------------------------------------------------------------------------
# nflverse — snapshot axis
# ---------------------------------------------------------------------------


def replay_nflverse_snapshot(
    *,
    db_path: Path,
    specs: Sequence[StreamSpec] | None = None,
    identity: IdentityIndex | None = None,
    raw_root: Path | None = None,
    max_raw_bytes: int | None = None,
    streams: set[str] | None = None,
) -> list[CheckResult]:
    """Per snapshot-axis stream: latest ledger observation — raw bytes
    re-hashed (content addressing), then renormalized and digest-compared."""
    db_path = Path(db_path)
    specs = tuple(
        s for s in (specs if specs is not None else NFLVERSE_SPECS)
        if s.capture_axis == "snapshot" and (streams is None or s.name in streams)
    )
    if not specs:
        return []
    if not db_path.exists():
        return [
            CheckResult(
                stream="nflverse", check="store_present", status="no_snapshot",
                evidence={"db_path": str(db_path)},
            )
        ]
    results: list[CheckResult] = []
    with _connect_ro(db_path) as conn:
        for spec in specs:
            results.extend(
                _replay_one_snapshot(
                    conn, spec, identity=identity, raw_root=raw_root,
                    max_raw_bytes=max_raw_bytes,
                )
            )
    return results


def _replay_one_snapshot(
    conn: sqlite3.Connection,
    spec: StreamSpec,
    *,
    identity: IdentityIndex | None,
    raw_root: Path | None,
    max_raw_bytes: int | None,
) -> list[CheckResult]:
    stream = f"nflverse:{spec.name}"
    try:
        ledger = conn.execute(
            "SELECT snapshot_id, observed_at, rows_total, content_hash, "
            "raw_snapshot, raw_sha256 FROM nflverse_snapshot_capture "
            "WHERE stream = ? ORDER BY ingested_at DESC LIMIT 1",
            (spec.name,),
        ).fetchone()
    except sqlite3.OperationalError as exc:
        return [
            CheckResult(
                stream=stream, check="raw_sha256", status="no_snapshot",
                evidence={"reason": f"ledger unreadable: {exc}"},
            )
        ]
    if ledger is None:
        return [
            CheckResult(
                stream=stream, check="raw_sha256", status="no_snapshot",
                evidence={"reason": "no row in nflverse_snapshot_capture"},
            )
        ]

    # The recorded path is authoritative; a surviving same-named file under
    # the current raw root is the honest fallback for a landed-from-elsewhere
    # capture whose recording predates this tree.
    recorded = Path(ledger["raw_snapshot"])
    raw_path = recorded
    if not raw_path.exists() and raw_root is not None:
        fallback = Path(raw_root) / "raw" / recorded.name
        if fallback.exists():
            raw_path = fallback
    if not raw_path.exists():
        return [
            CheckResult(
                stream=stream, check="raw_sha256", status="no_matching_raw",
                evidence={
                    "snapshot_id": ledger["snapshot_id"],
                    "recorded_raw_snapshot": str(recorded),
                },
            )
        ]
    size = raw_path.stat().st_size
    if max_raw_bytes is not None and size > max_raw_bytes:
        return [
            CheckResult(
                stream=stream, check="raw_sha256", status="skipped_size_guard",
                evidence={
                    "snapshot_id": ledger["snapshot_id"],
                    "raw_snapshot": str(raw_path),
                    "raw_bytes": size, "max_raw_bytes": max_raw_bytes,
                },
            )
        ]

    replayed_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    hash_evidence = {
        "snapshot_id": ledger["snapshot_id"],
        "raw_snapshot": str(raw_path),
        "ledger_raw_sha256": ledger["raw_sha256"],
        "replayed_raw_sha256": replayed_sha,
        "raw_bytes": size,
    }
    if replayed_sha != ledger["raw_sha256"]:
        # Unproven bytes prove nothing downstream: stop this stream here.
        return [
            CheckResult(
                stream=stream, check="raw_sha256", status="mismatch",
                evidence=hash_evidence,
            )
        ]
    results = [
        CheckResult(
            stream=stream, check="raw_sha256", status="reproduced",
            evidence=hash_evidence,
        )
    ]

    try:
        envelope = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_version = envelope.get("schema_version")
        if raw_version != NFLVERSE_SCHEMA_VERSION:
            results.append(
                CheckResult(
                    stream=stream, check="snapshot_digest",
                    status="parser_version_mismatch",
                    evidence={
                        "raw_schema_version": raw_version,
                        "pinned_schema_version": NFLVERSE_SCHEMA_VERSION,
                    },
                )
            )
            return results
        if identity is None and spec.identity_applicable:
            identity = IdentityIndex.from_governed_crosswalk()
        rows, coverage = normalize_rows(
            envelope["records"], spec=spec, season=None, identity=identity
        )
        replayed = snapshot_idempotence_digest(
            spec, rows=rows, coverage=coverage,
            observed_at=ledger["observed_at"], raw_sha256=ledger["raw_sha256"],
        )
    except Exception as exc:
        results.append(
            CheckResult(
                stream=stream, check="snapshot_digest", status="error",
                evidence={"raw_snapshot": str(raw_path), "error": repr(exc)},
            )
        )
        return results

    reproduced = (
        replayed == ledger["content_hash"]
        and len(rows) == int(ledger["rows_total"])
    )
    results.append(
        CheckResult(
            stream=stream, check="snapshot_digest",
            status="reproduced" if reproduced else "mismatch",
            evidence={
                "snapshot_id": ledger["snapshot_id"],
                "observed_at": ledger["observed_at"],
                "ledger_content_hash": ledger["content_hash"],
                "replayed_content_hash": replayed,
                "ledger_rows_total": int(ledger["rows_total"]),
                "rows_total": len(rows),
                "schema_version": NFLVERSE_SCHEMA_VERSION,
            },
        )
    )
    return results


# ---------------------------------------------------------------------------
# FantasyCalc forward capture
# ---------------------------------------------------------------------------


def replay_fc_forward(
    *, db_path: Path, snapshot_date: str | None = None
) -> list[CheckResult]:
    """Latest (or named) fc snapshot_date: per-row content addressing and the
    raw->joinable projection, both re-derived from the raw sidecar alone."""
    db_path = Path(db_path)
    stream = "fc_forward_capture"
    if not db_path.exists():
        return [
            CheckResult(
                stream=stream, check="store_present", status="no_snapshot",
                evidence={"db_path": str(db_path)},
            )
        ]
    with _connect_ro(db_path) as conn:
        try:
            if snapshot_date is None:
                picked = conn.execute(
                    "SELECT snapshot_date FROM fc_forward_capture_raw "
                    "ORDER BY snapshot_date DESC LIMIT 1"
                ).fetchone()
                if picked is None:
                    return [
                        CheckResult(
                            stream=stream, check="payload_hash",
                            status="no_snapshot",
                            evidence={"reason": "fc_forward_capture_raw is empty"},
                        )
                    ]
                snapshot_date = picked["snapshot_date"]
            raw_rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM fc_forward_capture_raw "
                    "WHERE snapshot_date = ? ORDER BY rowid",
                    (snapshot_date,),
                )
            ]
            joinable_rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM fc_forward_capture_joinable "
                    "WHERE snapshot_date = ? ORDER BY rowid",
                    (snapshot_date,),
                )
            ]
        except sqlite3.OperationalError as exc:
            return [
                CheckResult(
                    stream=stream, check="payload_hash", status="no_snapshot",
                    evidence={"reason": f"store unreadable: {exc}"},
                )
            ]

    results = [_fc_payload_hash_check(stream, snapshot_date, raw_rows)]
    results.append(
        _fc_joinable_check(stream, snapshot_date, raw_rows, joinable_rows)
    )
    return results


def _fc_payload_hash_check(
    stream: str, snapshot_date: str, raw_rows: list[dict]
) -> CheckResult:
    """Recompute each row's payload_hash from its stored content fields, with
    the driver's own ``_content_hash`` — the content-address must re-derive."""
    mismatched: list[str] = []
    legacy = 0
    pre_schema = 0
    for row in raw_rows:
        if row.get("market_volatility_status") is None:
            # Pre-Phase-0b row: its hash was computed under an earlier content
            # shape that can never be rebuilt (store docstring). Same-version
            # replay does not apply; counted, never compared.
            pre_schema += 1
            continue
        content = {
            "sleeper_id": row["sleeper_id"],
            "player_name": row["player_name"],
            "position": row["position"],
            "value": row["value"],
            "overall_rank": row["overall_rank"],
            "position_rank": row["position_rank"],
            "trend_30day": row["trend_30day"],
            "market_volatility": row["market_volatility"],
            "market_volatility_status": row["market_volatility_status"],
        }
        if _fc_content_hash(content) == row["payload_hash"]:
            continue
        # The DG-050 live finding (2026-08-28, 172/474 rows): captures from
        # before the driver's storage-faithful normalization hashed integral
        # volatilities as ints, which the REAL column returns as floats. Such
        # a row's hash still re-derives DETERMINISTICALLY under that era's
        # projection — a named, bounded vintage, never a silent pass.
        mv = row["market_volatility"]
        if isinstance(mv, float) and mv.is_integer():
            if _fc_content_hash({**content, "market_volatility": int(mv)}) == (
                row["payload_hash"]
            ):
                legacy += 1
                continue
        mismatched.append(row["player_key"])
    evidence = {
        "snapshot_date": snapshot_date,
        "rows_total": len(raw_rows),
        "rows_pre_schema_skipped": pre_schema,
        "rows_legacy_integral_volatility": legacy,
        "rows_mismatched": len(mismatched),
        "mismatched_player_keys": sorted(mismatched)[:5],
    }
    if len(raw_rows) == 0 or pre_schema == len(raw_rows):
        status = "parser_version_mismatch" if pre_schema else "no_snapshot"
    elif mismatched:
        status = "mismatch"
    elif legacy:
        status = "legacy_content_shape"
    else:
        status = "reproduced"
    return CheckResult(
        stream=stream, check="payload_hash", status=status, evidence=evidence
    )


def _fc_joinable_check(
    stream: str,
    snapshot_date: str,
    raw_rows: list[dict],
    joinable_rows: list[dict],
) -> CheckResult:
    """Re-derive the joinable projection from the raw sidecar (the parser step
    the store performs at append time) and compare content-for-content."""

    def content_key(row: dict) -> tuple:
        return tuple(row.get(c) for c in _FC_CONTENT_COLUMNS)

    derived = sorted(
        content_key(r) for r in raw_rows if r.get("sleeper_id") is not None
    )
    stored = sorted(content_key(r) for r in joinable_rows)
    missing = [t for t in derived if t not in stored]
    extra = [t for t in stored if t not in derived]
    evidence = {
        "snapshot_date": snapshot_date,
        "raw_rows": len(raw_rows),
        "joinable_rows": len(joinable_rows),
        "derived_joinable_rows": len(derived),
        "rows_missing_from_store": len(missing),
        "rows_unexplained_in_store": len(extra),
    }
    status = "reproduced" if derived == stored else "mismatch"
    if not raw_rows and not joinable_rows:
        status = "no_snapshot"
    return CheckResult(
        stream=stream, check="joinable_projection", status=status,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# League snapshot
# ---------------------------------------------------------------------------


def replay_league_snapshot(*, runtime_root: Path) -> list[CheckResult]:
    """The marker-pinned run: artifact digests, lineage hashes, and the two
    stored derivations that are pure functions of stored inputs."""
    runtime_root = Path(runtime_root)
    stream = "league_snapshot"
    marker_path = runtime_root / "ready_latest.json"
    if not marker_path.is_file():
        return [
            CheckResult(
                stream=stream, check="artifact_digests", status="no_snapshot",
                evidence={"marker": str(marker_path)},
            )
        ]
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        run_dir = runtime_root / "runs" / marker["run_id"]
        digests: dict[str, str] = marker["sha256"]
    except Exception as exc:
        return [
            CheckResult(
                stream=stream, check="artifact_digests", status="error",
                evidence={"marker": str(marker_path), "error": repr(exc)},
            )
        ]

    results: list[CheckResult] = []
    mismatched_files = []
    for name, expected in sorted(digests.items()):
        path = run_dir / name
        actual = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file() else "absent"
        )
        if actual != expected:
            mismatched_files.append(name)
    results.append(
        CheckResult(
            stream=stream, check="artifact_digests",
            status="reproduced" if not mismatched_files else "mismatch",
            evidence={
                "run_id": marker["run_id"], "run_dir": str(run_dir),
                "artifacts": len(digests),
                "mismatched_artifacts": mismatched_files,
            },
        )
    )
    if mismatched_files:
        # Unproven stored bytes prove nothing about the parser: stop here.
        return results

    try:
        snapshot = json.loads(
            (run_dir / "snapshot.json").read_text(encoding="utf-8")
        )
    except Exception as exc:
        results.append(
            CheckResult(
                stream=stream, check="lineage_hashes", status="error",
                evidence={"run_dir": str(run_dir), "error": repr(exc)},
            )
        )
        return results

    if snapshot.get("schema_version") != SLEEPER_SCHEMA_VERSION:
        results.append(
            CheckResult(
                stream=stream, check="lineage_hashes",
                status="parser_version_mismatch",
                evidence={
                    "snapshot_schema_version": snapshot.get("schema_version"),
                    "pinned_schema_version": SLEEPER_SCHEMA_VERSION,
                },
            )
        )
        return results

    lineage = snapshot.get("lineage") or {}
    lineage_mismatch = []
    for source in _LINEAGE_REPLAYABLE:
        if _stable_hash(snapshot.get(source)) != lineage.get(f"{source}_hash"):
            lineage_mismatch.append(source)
    results.append(
        CheckResult(
            stream=stream, check="lineage_hashes",
            status="reproduced" if not lineage_mismatch else "mismatch",
            evidence={
                "run_id": marker["run_id"],
                "replayed_sources": list(_LINEAGE_REPLAYABLE),
                "mismatched_sources": lineage_mismatch,
                # Stated, not silent: these hash raw inputs the snapshot keeps
                # only projections of, so same-version replay cannot reach them.
                "not_replayable_from_snapshot": list(_LINEAGE_NOT_REPLAYABLE),
            },
        )
    )

    results.append(
        _league_rederive_check(
            stream, "coverage_rederive", run_dir / "coverage.json",
            lambda: build_coverage_report(snapshot), marker["run_id"],
        )
    )

    def _posture() -> dict:
        matrix = json.loads(
            (run_dir / "team_value_matrix.json").read_text(encoding="utf-8")
        )
        stored = json.loads(
            (run_dir / "team_posture.json").read_text(encoding="utf-8")
        )
        if stored.get("schema_version") != POSTURE_SCHEMA_VERSION:
            raise _ParserVersionMismatch(
                stored.get("schema_version"), POSTURE_SCHEMA_VERSION
            )
        return build_team_posture_artifact(
            matrix, captured_at=stored.get("captured_at")
        )

    results.append(
        _league_rederive_check(
            stream, "posture_rederive", run_dir / "team_posture.json",
            _posture, marker["run_id"],
        )
    )
    return results


class _ParserVersionMismatch(Exception):
    def __init__(self, found: Any, pinned: str) -> None:
        super().__init__(f"stored {found!r} vs pinned {pinned!r}")
        self.found, self.pinned = found, pinned


def _league_rederive_check(
    stream: str, check: str, stored_path: Path, rederive, run_id: str
) -> CheckResult:
    """Byte-compare a stored derived artifact against its re-derivation,
    serialized exactly as ``league_capture.run_capture`` serializes."""
    try:
        stored_bytes = stored_path.read_bytes()
        replayed_bytes = json.dumps(rederive(), sort_keys=True).encode("utf-8")
    except _ParserVersionMismatch as exc:
        return CheckResult(
            stream=stream, check=check, status="parser_version_mismatch",
            evidence={
                "run_id": run_id, "stored_schema_version": exc.found,
                "pinned_schema_version": exc.pinned,
            },
        )
    except Exception as exc:
        return CheckResult(
            stream=stream, check=check, status="error",
            evidence={"artifact": str(stored_path), "error": repr(exc)},
        )
    evidence = {
        "run_id": run_id,
        "artifact": stored_path.name,
        "stored_sha256": hashlib.sha256(stored_bytes).hexdigest(),
        "replayed_sha256": hashlib.sha256(replayed_bytes).hexdigest(),
    }
    return CheckResult(
        stream=stream, check=check,
        status="reproduced" if stored_bytes == replayed_bytes else "mismatch",
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# runner + receipt
# ---------------------------------------------------------------------------


def run_replay(
    *,
    repo_root: Path,
    streams: set[str] | None = None,
    max_raw_bytes: int | None = None,
    league_root: Path | None = None,
    nflverse_db: Path | None = None,
    nflverse_raw_root: Path | None = None,
    fc_db: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """One full replay pass -> the receipt payload (not yet written)."""
    repo_root = Path(repo_root)
    data = repo_root / "app" / "data"
    nflverse_db = Path(nflverse_db or data / "nflverse_usage.db")
    nflverse_raw_root = Path(nflverse_raw_root or data / "nflverse_usage")
    fc_db = Path(fc_db or data / "fc_forward_capture.db")
    league_root = Path(league_root or data / "league_runtime")
    started = now or datetime.now(timezone.utc)

    checks: list[CheckResult] = []
    if streams is None or streams - {"fc_forward_capture", "league_snapshot"}:
        nfl_streams = (
            None if streams is None
            else {s for s in streams if s not in
                  ("fc_forward_capture", "league_snapshot")}
        )
        checks.extend(
            replay_nflverse_seasonal(
                db_path=nflverse_db, raw_root=nflverse_raw_root,
                streams=nfl_streams,
            )
        )
        checks.extend(
            replay_nflverse_snapshot(
                db_path=nflverse_db, raw_root=nflverse_raw_root,
                max_raw_bytes=max_raw_bytes, streams=nfl_streams,
            )
        )
    if streams is None or "fc_forward_capture" in streams:
        checks.extend(replay_fc_forward(db_path=fc_db))
    if streams is None or "league_snapshot" in streams:
        checks.extend(replay_league_snapshot(runtime_root=league_root))

    totals: dict[str, int] = {}
    for check in checks:
        totals[check.status] = totals.get(check.status, 0) + 1
    if totals.get("mismatch") or totals.get("error"):
        verdict = "not_reproduced"
    elif totals.get("reproduced") or totals.get("legacy_content_shape"):
        # legacy_content_shape is reproduced-class: every such row's hash
        # re-derives deterministically under its documented capture-era
        # serialization (the receipt still names the count per stream).
        verdict = "reproduced"
    else:
        verdict = "nothing_replayed"

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "run_id": started.strftime("replay-%Y%m%dT%H%M%SZ"),
        "generated_at": started.isoformat(),
        "repo_root": str(repo_root),
        "parser_versions": {
            "nflverse_usage": NFLVERSE_SCHEMA_VERSION,
            "sleeper_universe": SLEEPER_SCHEMA_VERSION,
            "team_posture": POSTURE_SCHEMA_VERSION,
        },
        "checks": [asdict(check) for check in checks],
        "totals": totals,
        "verdict": verdict,
    }


def write_receipt(
    receipt: Mapping[str, Any], *, ops_root: Path
) -> tuple[Path, Path]:
    """Atomic ``*_latest.json`` plus an immutable run-scoped copy.

    The dated copy REFUSES to overwrite an existing run — the rule the
    2026-08-17 overwritten run record is the origin of.
    """
    ops_root = Path(ops_root)
    body = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    dated = ops_root / "replay_reproducibility" / "runs" / (
        f"{receipt['run_id']}.json"
    )
    if dated.exists():
        raise FileExistsError(
            f"run receipt already exists, refusing to overwrite: {dated}"
        )
    dated.parent.mkdir(parents=True, exist_ok=True)
    dated.write_text(body, encoding="utf-8")

    latest = ops_root / "replay_reproducibility_latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(latest.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.replace(tmp, latest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return latest, dated
