"""DG-028 — the "we changed nothing" check that can actually see.

The old convention proved model-science work left production alone with::

    git diff -- app/config/model_registry.json app/data/models

but ``.gitignore`` covers the live artifacts under ``app/data/models``
(``.gitignore:60-65``: the engine_b run dirs and manifest, ``head_a/``), so
that diff is empty whether or not the bytes moved. Any agent could overwrite
a live model artifact and the check still passed.

This guard hashes the artifacts NAMED in ``app/config/model_registry.json``
and compares them against the recorded hashes, resolving each path exactly
the way serving does — the DEBT-6 provenance layer: literal and
``latest_run_dir`` resolution through governing pointers, streamed sha256,
traversal guards. It fails loudly, one line per deviation, when a live
artifact moves, disappears, loses its governing pointer, or has no recorded
hash to verify against.

Usage::

    .venv/bin/python scripts/check_model_no_mutation.py

Exit codes: 0 — every registry-named artifact matches its recorded hash;
1 — at least one deviates (MUTATED / MISSING / POINTER-BROKEN /
UNVERIFIABLE); 2 — the registry itself is missing or malformed
(fail-closed: a guard with no source of truth must not report cleanliness).

Read-only by construction: the guard opens artifacts for hashing and never
writes anywhere.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.api.routes.system_model_provenance_models import (  # noqa: E402
    ArtifactProvenance,
    ModelRegistryLoadError,
    hash_file_sha256,
    inspect_registered_artifact,
    load_model_registry,
)

# The two pointer states that mean "the governing pointer is healthy".
_HEALTHY_POINTER = frozenset(("referenced", "not_applicable"))

# The guard judges as production on purpose: the question is "did serving
# reality move?", so absence of a serving-required artifact is a failure here
# even where a dev checkout would tolerate it.
_GUARD_ENVIRONMENT = "production"

EXIT_CLEAN = 0
EXIT_MUTATION = 1
EXIT_CONFIG = 2


@dataclass(frozen=True)
class ArtifactRow:
    """One registry-named artifact's verdict — a fact, not a judgment."""

    artifact_id: str
    path: str
    label: str  # "ok" | "MUTATED" | "MISSING" | "POINTER-BROKEN" | "UNVERIFIABLE"
    observed_status: str
    pointer_status: str
    expected_sha256: str | None
    observed_sha256: str | None

    @property
    def clean(self) -> bool:
        return self.label == "ok"

    def line(self) -> str:
        if self.clean:
            return (
                f"ok              {self.artifact_id}  {self.path}  "
                f"sha256={self.observed_sha256}"
            )
        return (
            f"{self.label:<15} {self.artifact_id}  {self.path}  "
            f"observed_status={self.observed_status} "
            f"pointer_status={self.pointer_status} "
            f"expected_sha256={self.expected_sha256} "
            f"observed_sha256={self.observed_sha256}"
        )


@dataclass(frozen=True)
class NoMutationReport:
    rows: tuple[ArtifactRow, ...]

    @property
    def clean(self) -> bool:
        return all(row.clean for row in self.rows)


def _label(provenance: ArtifactProvenance) -> str:
    """Collapse the provenance facts into the guard's verdict for one row.

    Deliberately stricter than the endpoint's env-lenient severity mapping:
    the guard proves "we changed nothing", so ANYTHING other than
    hash-verified bytes behind a healthy pointer is a failure.
    """

    if provenance.observed_status == "expected_hash_missing":
        return "UNVERIFIABLE"
    if provenance.observed_status in ("hash_mismatch", "local_override"):
        return "MUTATED"
    if provenance.observed_status in (
        "missing_required",
        "local_artifact_missing_ci",
    ):
        return "MISSING"
    if provenance.pointer_status not in _HEALTHY_POINTER:
        return "POINTER-BROKEN"
    if provenance.observed_status == "ok":
        return "ok"
    # Fail closed on any status this guard does not know.
    return "MUTATED"


def run_check(
    *, repo_root: Path, registry_path: Path | None = None
) -> NoMutationReport:
    """Hash every artifact the registry names; compare to the recorded hashes.

    Raises :class:`ModelRegistryLoadError` when the registry itself is
    missing/malformed — the caller maps that to :data:`EXIT_CONFIG` rather
    than this function inventing a "clean" answer without a source of truth.
    """

    resolved_registry = (
        registry_path
        if registry_path is not None
        else repo_root / "app" / "config" / "model_registry.json"
    )
    registry = load_model_registry(registry_path=resolved_registry)

    rows: list[ArtifactRow] = []
    for entry in registry.artifacts:
        hashed: list[str] = []

        def recording_hasher(path: Path, _sink: list[str] = hashed) -> str:
            digest = hash_file_sha256(path)
            _sink.append(digest)
            return digest

        provenance = inspect_registered_artifact(
            entry=entry,
            repo_root=repo_root,
            environment=_GUARD_ENVIRONMENT,
            hash_file=recording_hasher,
        )
        rows.append(
            ArtifactRow(
                artifact_id=entry.artifact_id,
                path=provenance.path,
                label=_label(provenance),
                observed_status=provenance.observed_status,
                pointer_status=provenance.pointer_status,
                expected_sha256=entry.sha256,
                observed_sha256=hashed[-1] if hashed else None,
            )
        )
    return NoMutationReport(rows=tuple(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove the registry-named model artifacts are byte-identical to "
            "their recorded hashes (the seeing replacement for the blind "
            "'git diff -- app/config/model_registry.json app/data/models')."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="repository root to guard (default: this script's own repo)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="registry path (default: <repo-root>/app/config/model_registry.json)",
    )
    args = parser.parse_args(argv)

    try:
        report = run_check(
            repo_root=args.repo_root, registry_path=args.registry
        )
    except ModelRegistryLoadError as exc:
        print(f"NO-MUTATION CHECK CANNOT RUN — registry unusable: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    for row in report.rows:
        print(row.line(), file=sys.stdout if row.clean else sys.stderr)

    if report.clean:
        print(
            f"CLEAN — {len(report.rows)} registry-named artifacts match "
            "their recorded hashes"
        )
        return EXIT_CLEAN
    failing = sum(1 for row in report.rows if not row.clean)
    print(
        f"MUTATION DETECTED — {failing} of {len(report.rows)} registry-named "
        "artifacts deviate from their recorded hashes",
        file=sys.stderr,
    )
    return EXIT_MUTATION


if __name__ == "__main__":
    raise SystemExit(main())
