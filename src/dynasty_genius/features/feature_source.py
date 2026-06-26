"""F-feature-refresh T3 — the single resolved feature-source helper for ALL consumers.

Every engine_b feature consumer (the service, the PVO batch, the model-capture driver)
must read its feature CSV through `resolve_feature_source` rather than reaching for the
committed seed directly. The resolver prefers a PUBLISHED runtime (T2 atomic publish +
ready marker) and falls back to the committed seed when no runtime exists. It is
FAIL-CLOSED: a runtime CSV that is present but not verifiably ready (missing/blocked
marker, or a hash that does not match the file) raises rather than silently serving a
half-written or stale artifact.

The resolved `metadata()` block carries the source kind + hashes + as-of label so consumers
can stamp provenance and the league surfaces can disclose feature freshness. It never
certifies a decision — `decision_supported` is always False.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_CSV_NAME = "engine_b_features_runtime.csv"
_READY_MARKER_NAME = "engine_b_features_runtime.ready.json"


class FeatureSourceNotReadyError(RuntimeError):
    """A runtime feature CSV is present but not verifiably ready (fail-closed)."""


def _sha256(path: Path) -> Optional[str]:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class ResolvedFeatureSource:
    """The feature CSV a consumer should read, with provenance/freshness metadata."""

    path: Path
    source_kind: str  # "runtime" | "seed"
    sha256: Optional[str]
    source_as_of: Optional[str]
    ready: bool
    published_seed_sha256: Optional[str]

    def metadata(self) -> dict:
        """Provenance/freshness stamp — safe to embed in artifacts and league surfaces."""
        return {
            "feature_source_kind": self.source_kind,
            "feature_csv_sha256": self.sha256,
            "feature_csv_path": _relative_to_repo(self.path),
            "source_as_of": self.source_as_of,
            "published_seed_sha256": self.published_seed_sha256,
            "decision_supported": False,
        }


def resolve_feature_source(
    *,
    seed_path: Path | str,
    runtime_dir: Path | str,
) -> ResolvedFeatureSource:
    """Resolve the feature CSV: a verified runtime if published, else the committed seed.

    Fail-closed: if the runtime CSV exists but its ready marker is missing, not ``ok``, or
    its ``runtime_sha256`` does not match the file on disk, raise
    ``FeatureSourceNotReadyError`` instead of serving an unverified artifact.
    """
    seed_path = Path(seed_path)
    runtime_dir = Path(runtime_dir)
    runtime_path = runtime_dir / _RUNTIME_CSV_NAME
    ready_path = runtime_dir / _READY_MARKER_NAME
    seed_sha = _sha256(seed_path)

    if runtime_path.exists():
        runtime_sha = _sha256(runtime_path)
        ready: Optional[dict] = None
        if ready_path.exists():
            try:
                ready = json.loads(ready_path.read_text())
            except (ValueError, OSError):
                ready = None
        if (
            not isinstance(ready, dict)
            or ready.get("status") != "ok"
            or ready.get("runtime_sha256") != runtime_sha
        ):
            raise FeatureSourceNotReadyError(
                f"runtime feature CSV present at {runtime_path} but not verifiably ready "
                f"(marker status/hash mismatch); refusing to serve unverified features"
            )
        return ResolvedFeatureSource(
            path=runtime_path,
            source_kind="runtime",
            sha256=runtime_sha,
            source_as_of=ready.get("source_as_of"),
            ready=True,
            published_seed_sha256=seed_sha,
        )

    # No runtime published — serve the committed seed (the always-available baseline).
    return ResolvedFeatureSource(
        path=seed_path,
        source_kind="seed",
        sha256=seed_sha,
        source_as_of=None,
        ready=True,
        published_seed_sha256=seed_sha,
    )
