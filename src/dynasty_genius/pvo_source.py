"""F-seed-split T1 — fail-closed resolver for the PVO seed/runtime pair.

`resolve_pvo_source` returns the PVO + coverage artifact pair a CONSUMER should read, with
three explicit outcomes (absent ≠ unverified):
  - runtime ABSENT (no ready marker AND no runtime artifact files) → serve the committed SEED
    pair, stamped ``source_kind="seed"``.
  - runtime present AND verified (ready marker status ``ok`` + BOTH file shas match the marker)
    → serve the RUNTIME pair.
  - runtime present BUT unverified (marker missing/not-ok, either sha mismatch, or only one of
    the pair present) → RAISE ``PvoSourceNotReadyError``. A present-but-unverified runtime
    signals corruption (post-write tampering / half-write) and must NEVER silently fall back to
    the seed — the seed fallback is for *absence*, not *corruption*.

The PVO and coverage artifacts are an inseparable atomic pair; the ready marker carries BOTH
hashes. The pre-computed ``seed_staleness`` block is read O(1) from the VERIFIED marker and
passed through opaquely — the resolver never parses or diffs the (large) PVO artifact JSON,
which is the hot path for the API routes. This module derives nothing from the market and
trains no model; ``decision_supported`` is always False.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Runtime artifact + marker names under the gitignored runtime dir (F-seed-split §3.2).
_RUNTIME_PVO_NAME = "universe_pvo_runtime.json"
_RUNTIME_COVERAGE_NAME = "universe_pvo_coverage_runtime.json"
_READY_MARKER_NAME = "universe_pvo_runtime.ready.json"


class PvoSourceNotReadyError(RuntimeError):
    """A runtime PVO pair is present but not verifiably ready — refuse to serve unverified."""


@dataclass(frozen=True)
class ResolvedPvoSource:
    """The PVO + coverage pair a consumer should read, with provenance/freshness metadata."""

    source_kind: str  # "runtime" | "seed"
    pvo_path: Path
    coverage_path: Path
    pvo_sha256: str
    coverage_sha256: str
    source_as_of: Optional[str]
    ready: bool
    seed_staleness: Optional[dict]

    def metadata(self) -> dict:
        """Provenance/freshness stamp — safe to embed in artifacts and league surfaces."""
        return {
            "pvo_source_kind": self.source_kind,
            "pvo_sha256": self.pvo_sha256,
            "pvo_path": str(self.pvo_path),
            "coverage_sha256": self.coverage_sha256,
            "coverage_path": str(self.coverage_path),
            "source_as_of": self.source_as_of,
            "seed_staleness": self.seed_staleness,
            "decision_supported": False,
        }


def _sha256(path: Path) -> str:
    # hashlib over raw bytes — never json.loads the artifact (keeps the resolver off the
    # PVO-parse hot path; the perf guard asserts json is only used on the ready marker).
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_pvo_source(
    *,
    seed_paths: dict,
    runtime_dir: Path | str,
) -> ResolvedPvoSource:
    """Resolve the PVO+coverage pair: a verified runtime if published, else the committed seed.

    Fail-closed: a present-but-unverified runtime raises ``PvoSourceNotReadyError`` rather than
    silently serving the seed over possible corruption. Seed fallback is for ABSENCE only.
    """
    runtime_dir = Path(runtime_dir)
    runtime_pvo = runtime_dir / _RUNTIME_PVO_NAME
    runtime_coverage = runtime_dir / _RUNTIME_COVERAGE_NAME
    marker_path = runtime_dir / _READY_MARKER_NAME

    # "Present" = any runtime trace exists (marker OR either artifact). A bare seed dir with
    # no runtime trace is ABSENT → seed; any partial runtime (e.g. files but no marker) is
    # PRESENT → it must verify fully or fail closed (never seed-fallback over a half-write).
    runtime_present = (
        marker_path.exists() or runtime_pvo.exists() or runtime_coverage.exists()
    )

    if not runtime_present:
        seed_pvo = Path(seed_paths["pvo"])
        seed_coverage = Path(seed_paths["coverage"])
        return ResolvedPvoSource(
            source_kind="seed",
            pvo_path=seed_pvo,
            coverage_path=seed_coverage,
            pvo_sha256=_sha256(seed_pvo),
            coverage_sha256=_sha256(seed_coverage),
            source_as_of=None,
            ready=True,
            seed_staleness=None,
        )

    # Runtime present → verify fully; any gap fails closed.
    if not marker_path.exists():
        raise PvoSourceNotReadyError(
            f"runtime PVO artifacts present under {runtime_dir} but the ready marker "
            f"{_READY_MARKER_NAME} is missing; refusing to serve an unverified runtime"
        )
    try:
        marker = json.loads(marker_path.read_text())
    except (ValueError, OSError) as exc:
        raise PvoSourceNotReadyError(
            f"runtime ready marker at {marker_path} is unreadable/unparseable: {exc}"
        ) from exc
    if not isinstance(marker, dict) or marker.get("status") != "ok":
        raise PvoSourceNotReadyError(
            f"runtime ready marker at {marker_path} is not status=ok; refusing to serve"
        )
    if not runtime_pvo.exists() or not runtime_coverage.exists():
        raise PvoSourceNotReadyError(
            f"runtime ready marker present but the PVO/coverage pair is incomplete under "
            f"{runtime_dir}; refusing to serve a half-written runtime"
        )
    pvo_sha = _sha256(runtime_pvo)
    coverage_sha = _sha256(runtime_coverage)
    if marker.get("pvo_sha256") != pvo_sha or marker.get("coverage_sha256") != coverage_sha:
        raise PvoSourceNotReadyError(
            f"runtime PVO/coverage hashes do not match the ready marker at {marker_path}; "
            f"refusing to serve a tampered/corrupt runtime"
        )
    return ResolvedPvoSource(
        source_kind="runtime",
        pvo_path=runtime_pvo,
        coverage_path=runtime_coverage,
        pvo_sha256=pvo_sha,
        coverage_sha256=coverage_sha,
        source_as_of=marker.get("source_as_of"),
        ready=True,
        seed_staleness=marker.get("seed_staleness"),
    )
