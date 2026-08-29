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

Usage (pass ``--repo-root`` explicitly when run from a ticket worktree — the
gitignored live artifacts exist only in the trunk checkout)::

    .venv/bin/python scripts/check_model_no_mutation.py \
        --repo-root /Users/davidleess/dynasty-genius-product

Beyond per-artifact hashing, the guard verifies the SERVING BINDINGS
(pre-land review blockers, 2026-08-28): every path a governing manifest
serves must itself be a registered artifact (a hijacked manifest key serving
an unregistered pickle is SERVED-UNREGISTERED), and the engine_b v1 fallback
scan (``_load_v1_bundle``: last sorted ``runs/*/engine_b_v1.pkl``) must
resolve to a registered path — a newer drop-in pickle is flagged, not
silently served.

Exit codes: 0 — every registry-named artifact matches its recorded hash and
every serving binding resolves to a registered artifact; 1 — at least one
deviates (MUTATED / MISSING / POINTER-BROKEN / UNVERIFIABLE /
SERVED-UNREGISTERED / MANIFEST-UNREADABLE); 2 — the registry itself is
missing or malformed (fail-closed: a guard with no source of truth must not
report cleanliness).

Read-only by construction: the guard opens artifacts for hashing and never
writes anywhere.
"""

from __future__ import annotations

import argparse
import json
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
    rows.extend(_serving_binding_rows(repo_root=repo_root, registry=registry))
    rows.extend(_v1_fallback_rows(repo_root=repo_root, registry=registry))
    return NoMutationReport(rows=tuple(rows))


def _serving_binding_rows(*, repo_root: Path, registry) -> list[ArtifactRow]:
    """Every path a governing MANIFEST serves must be a registered artifact.

    Serving loads what the manifest values say (engine_b `_load_v2_bundles`,
    head_a v3) — the registry row's own hash stays clean when a DIFFERENT
    manifest key is repointed at poison, which is exactly the hijack the
    pre-land review proved exits 0. An unreadable manifest fails closed."""

    registered = {entry.path for entry in registry.artifacts}
    manifests = sorted(
        {
            entry.governing_pointer
            for entry in registry.artifacts
            if entry.path_resolution == "literal" and entry.governing_pointer
        }
    )
    rows: list[ArtifactRow] = []
    for rel in manifests:
        try:
            payload = json.loads((repo_root / rel).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("manifest is not a JSON object")
        except Exception:
            rows.append(
                ArtifactRow(
                    artifact_id=f"manifest:{rel}",
                    path=rel,
                    label="MANIFEST-UNREADABLE",
                    observed_status="manifest_unreadable",
                    pointer_status="unreadable",
                    expected_sha256=None,
                    observed_sha256=None,
                )
            )
            continue
        for key, served in payload.items():
            if served is None:
                continue
            if not isinstance(served, str) or served not in registered:
                rows.append(
                    ArtifactRow(
                        artifact_id=f"manifest:{rel}:{key}",
                        path=str(served),
                        label="SERVED-UNREGISTERED",
                        observed_status="served_path_not_registered",
                        pointer_status="hijacked",
                        expected_sha256=None,
                        observed_sha256=None,
                    )
                )
    return rows


def _v1_fallback_rows(*, repo_root: Path, registry) -> list[ArtifactRow]:
    """Mirror serving's v1 fallback scan and require its pick be registered.

    `engine_b_service._load_v1_bundle` loads the LAST sorted
    ``runs/*/engine_b_v1.pkl`` — a newer drop-in silently becomes what
    serving loads while the registered pickle still hashes clean."""

    registered = {entry.path for entry in registry.artifacts}
    runs = repo_root / "app" / "data" / "models" / "engine_b" / "runs"
    if not runs.is_dir():
        return []
    candidates = sorted(
        d for d in runs.iterdir() if d.is_dir() and (d / "engine_b_v1.pkl").is_file()
    )
    if not candidates:
        return []
    served_rel = (candidates[-1] / "engine_b_v1.pkl").relative_to(repo_root).as_posix()
    if served_rel in registered:
        return []
    return [
        ArtifactRow(
            artifact_id="engine_b:v1_fallback(scan)",
            path=served_rel,
            label="SERVED-UNREGISTERED",
            observed_status="served_path_not_registered",
            pointer_status="scan_resolved",
            expected_sha256=None,
            observed_sha256=None,
        )
    ]


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
