"""DEBT-6 Slice 1 — model-provenance models, loader, classifier, and disk layer.

T1: Pydantic v2 schema (all ``extra="forbid"`` so verdict-fields fail closed),
the checked-in-registry loader (fail-closed on missing/malformed/schema-invalid),
and runtime-environment resolution. T2: the pure ``classify_artifact`` engine.
T3: the disk-truth layer — governing-pointer health (``pointer_status``),
``latest_run_dir`` resolution, streamed sha256 hashing, and the scoped
unregistered-local reverse scan. Route wiring and OpenAPI generation are T4.

Spec: docs/superpowers/specs/2026-07-01-debt6-model-provenance-slice1-design.md
Plan: docs/superpowers/plans/2026-07-01-debt6-model-provenance-slice1-plan.md
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

# --- shared enums ------------------------------------------------------------

PathResolution = Literal["literal", "latest_run_dir"]
ArtifactKind = Literal["tracked_seed", "local_operational"]
PromotionStatus = Literal["active", "candidate", "parked"]
ObservedStatus = Literal[
    "ok",
    "local_override",
    "unregistered_local",
    "hash_mismatch",
    "missing_required",
    "local_artifact_missing_ci",
    "expected_hash_missing",
]
PointerStatus = Literal[
    "referenced",
    "pointer_missing",
    "pointer_malformed",
    "pointer_mismatch",
    "not_applicable",
]
Severity = Literal["info", "caveat", "integrity"]
LoadVerificationStatus = Literal["not_verified", "verified"]
OverallStatus = Literal["ok", "degraded", "blocked"]
RuntimeEnvironment = Literal["development", "ci", "serving", "production"]

_VALID_ENVIRONMENTS: frozenset[str] = frozenset(
    ("development", "ci", "serving", "production")
)


class _Strict(BaseModel):
    """Base model: reject unknown fields so verdict-language cannot leak in."""

    model_config = ConfigDict(extra="forbid")


# --- registry (checked-in expected state) ------------------------------------


class RegistryArtifact(_Strict):
    """One declared model artifact in ``app/config/model_registry.json``.

    ``sha256`` is nullable: a ``null`` expected hash means "declared but not yet
    seeded" (T5 promotion assertion), which the classifier treats as
    ``expected_hash_missing`` — never ``ok``. ``path_resolution: latest_run_dir``
    means ``path`` is a filename resolved against ``governing_pointer``'s run dir.
    """

    artifact_id: str
    path: str
    path_resolution: PathResolution = "literal"
    governing_pointer: str | None = None
    sha256: str | None = None
    kind: ArtifactKind
    promotion_status: PromotionStatus
    required_by_env: list[str]
    allow_local_override: bool = False
    approved_by: str
    approved_date: str
    updated_by_commit: str


class ModelRegistry(_Strict):
    registry_version: int
    artifacts: list[RegistryArtifact]


# --- response (computed provenance) ------------------------------------------


class ArtifactProvenance(_Strict):
    artifact_id: str
    path: str
    expected_kind: ArtifactKind
    promotion_status: PromotionStatus
    observed_status: ObservedStatus
    pointer_status: PointerStatus
    severity: Severity
    load_verification_status: LoadVerificationStatus
    serving_allowed: bool
    decision_supported: Literal[False]


class ModelProvenanceResponse(_Strict):
    overall_status: OverallStatus
    environment: RuntimeEnvironment
    registry_version: int
    artifacts: list[ArtifactProvenance]
    decision_supported: Literal[False]


class ModelProvenanceErrorResponse(_Strict):
    error: str
    message: str
    decision_supported: Literal[False]


# --- loader (fail-closed) ----------------------------------------------------


class ProvenanceConfigError(Exception):
    """Base for provenance configuration failures (registry + runtime env).

    One family so the route (T4) can map any of them to a fail-closed 503: a
    provenance endpoint whose own configuration is broken must not report health.
    """


class ModelRegistryLoadError(ProvenanceConfigError):
    """Raised when the checked-in registry is missing, malformed, or invalid.

    The route maps this to a 503: a provenance endpoint with no source of truth
    must not report health (spec §3.6).
    """


class RuntimeEnvironmentError(ProvenanceConfigError):
    """Raised when ``DG_RUNTIME_ENV`` is set to a value outside the valid set.

    An explicitly-set-but-invalid runtime env is configuration corruption, not
    "unset": it must fail closed rather than silently demote a misconfigured
    serving host to ``development`` (spec §3.1, Codex T1 R7).
    """


def load_model_registry(*, registry_path: Path) -> ModelRegistry:
    """Load and validate the checked-in model registry.

    Fail-closed: an absent, malformed, or schema-invalid registry raises
    :class:`ModelRegistryLoadError` rather than returning a partial/empty
    registry. The path is injectable so tests never touch ``app/config``.
    """

    if not registry_path.exists():
        raise ModelRegistryLoadError(
            f"model registry missing at {registry_path}"
        )

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelRegistryLoadError(
            f"model registry malformed JSON at {registry_path}: {exc}"
        ) from exc

    try:
        registry = ModelRegistry.model_validate(raw)
    except ValidationError as exc:
        raise ModelRegistryLoadError(
            f"model registry schema invalid at {registry_path}: {exc}"
        ) from exc

    # A schema-valid registry can still be unusable as a source of truth: zero
    # declared artifacts is a vacuous all-clear (T4 cockpit-converged → 503),
    # and duplicate ids would silently last-win.
    if not registry.artifacts:
        raise ModelRegistryLoadError(
            f"model registry declares no artifacts at {registry_path}"
        )
    seen_ids: set[str] = set()
    for entry in registry.artifacts:
        if entry.artifact_id in seen_ids:
            raise ModelRegistryLoadError(
                f"model registry has duplicate artifact_id {entry.artifact_id!r} "
                f"at {registry_path}"
            )
        seen_ids.add(entry.artifact_id)
    return registry


# --- environment resolution --------------------------------------------------


def resolve_runtime_environment(*, environ: Mapping[str, str]) -> str:
    """Resolve the runtime environment (spec §3.1).

    Precedence: an explicit, recognized ``DG_RUNTIME_ENV`` wins; otherwise the
    mere PRESENCE of a ``CI`` variable (any value) resolves to ``ci`` — a
    fail-closed-safe default, since treating an ambiguous env as CI marks
    ``local_operational`` artifacts as expected-absent rather than
    unexpectedly-missing; otherwise ``development``.
    """

    if "DG_RUNTIME_ENV" in environ:
        explicit = environ["DG_RUNTIME_ENV"]
        if explicit not in _VALID_ENVIRONMENTS:
            raise RuntimeEnvironmentError(
                "DG_RUNTIME_ENV is set to an invalid value "
                f"{explicit!r}; expected one of {sorted(_VALID_ENVIRONMENTS)}"
            )
        return explicit
    if "CI" in environ:
        return "ci"
    return "development"


# --- classifier (pure; spec §3.2–§3.4) ---------------------------------------

_SEVERITY_ORDER: dict[str, int] = {"info": 0, "caveat": 1, "integrity": 2}
_SERVING_ENVS: frozenset[str] = frozenset(("serving", "production"))
_BROKEN_POINTER: frozenset[str] = frozenset(
    ("pointer_missing", "pointer_malformed", "pointer_mismatch")
)


def _max_severity(a: str, b: str) -> str:
    return a if _SEVERITY_ORDER[a] >= _SEVERITY_ORDER[b] else b


def _serving_active_required(entry: RegistryArtifact, environment: str) -> bool:
    """True when this artifact is the ACTIVE, required model in a serving env.

    The only context where a deviation must hard-block: a mismatched/absent/
    unverifiable/pointer-broken *active* model that a serving host is required to
    load is unapproved serving reality, not a caveat.
    """

    return (
        entry.promotion_status == "active"
        and environment in _SERVING_ENVS
        and environment in entry.required_by_env
    )


def _observed_severity(
    entry: RegistryArtifact, observed_status: str, environment: str
) -> tuple[str, bool]:
    """Map an observed_status to (severity, serving_allowed) — the env's judgment."""

    if observed_status == "ok":
        return "info", True
    if observed_status == "hash_mismatch":
        # Tracked bytes differ from the approved hash: block even in dev, unless
        # an explicit dev-only override is set (the only tracked escape).
        if entry.allow_local_override and environment == "development":
            return "caveat", True
        return "integrity", False
    if observed_status == "missing_required":
        return "integrity", False
    if observed_status == "local_artifact_missing_ci":
        return "caveat", True
    if observed_status == "local_override":
        # Local bytes differ from last-promoted expected. Info in dev; unapproved
        # serving reality (integrity) only for an active+required serving model.
        if environment == "development":
            return "info", True
        if _serving_active_required(entry, environment):
            return "integrity", False
        return "caveat", True
    if observed_status == "expected_hash_missing":
        # No approved hash to verify against: never ok. Blocks an active+required
        # serving model; a caveat elsewhere (candidate/parked, ci/dev absence).
        if _serving_active_required(entry, environment):
            return "integrity", False
        return "caveat", True
    # Defensive: an unmapped status must fail closed, not silently pass.
    return "integrity", False


def classify_artifact(
    *,
    entry: RegistryArtifact,
    artifact_present: bool,
    observed_hash: str | None,
    pointer_status: str = "referenced",
    environment: str,
) -> ArtifactProvenance:
    """Classify one registered artifact into provenance (pure — no disk I/O).

    Derives ``observed_status`` (the technical fact) from the registry entry and
    the observed file facts, then maps ``severity`` + ``serving_allowed`` (the
    environment's judgment) with the fail-closed overlays of spec §3.4. The
    governing-pointer health (``pointer_status``) is supplied by the T3 readers;
    here it only gates severity: a broken pointer means the bytes may be valid
    but unreachable/misselected, so an active+required serving artifact blocks
    even when ``observed_status == "ok"``. ``load_verification_status`` is always
    ``"not_verified"`` in Slice 1 (pointer provenance, not proven resolver load).
    """

    # Fail closed on a bad caller: an invalid environment must not classify as
    # healthy (T1's resolver guards the HTTP path, but this pure function is
    # public and must guard itself — Codex T2 R8).
    if environment not in _VALID_ENVIRONMENTS:
        raise RuntimeEnvironmentError(
            f"classify_artifact received an invalid environment {environment!r}; "
            f"expected one of {sorted(_VALID_ENVIRONMENTS)}"
        )

    # observed_status — the technical fact
    if entry.sha256 is None:
        observed_status = "expected_hash_missing"
    elif not artifact_present:
        if entry.kind == "tracked_seed" or environment in entry.required_by_env:
            observed_status = "missing_required"
        else:
            observed_status = "local_artifact_missing_ci"
    elif observed_hash == entry.sha256:
        observed_status = "ok"
    elif entry.kind == "tracked_seed":
        observed_status = "hash_mismatch"
    else:
        observed_status = "local_override"

    # severity + serving_allowed — the environment's judgment
    severity, serving_allowed = _observed_severity(entry, observed_status, environment)

    # pointer clean-gate overlay (§3.4): valid bytes behind a broken governing
    # pointer are not clean. Hard-block only for an active+required serving model;
    # elsewhere a broken (typically gitignored, ci/dev-absent) manifest is a caveat.
    if pointer_status in _BROKEN_POINTER:
        if _serving_active_required(entry, environment):
            severity, serving_allowed = "integrity", False
        else:
            severity = _max_severity(severity, "caveat")

    return ArtifactProvenance(
        artifact_id=entry.artifact_id,
        path=entry.path,
        expected_kind=entry.kind,
        promotion_status=entry.promotion_status,
        observed_status=observed_status,  # type: ignore[arg-type]
        pointer_status=pointer_status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        load_verification_status="not_verified",
        serving_allowed=serving_allowed,
        decision_supported=False,
    )


# --- T3: disk-truth layer (pointer health, hashing, scoped scan; §3.5) --------

_HASH_CHUNK_BYTES = 1024 * 1024
_MODEL_ROOT_PARTS = ("app", "data", "models")

HashFile = Callable[[Path], str]
LoadJson = Callable[[Path], Any]


def hash_file_sha256(path: Path, *, chunk_size: int = _HASH_CHUNK_BYTES) -> str:
    """Stream a file's sha256 in bounded chunks (never one full-file read)."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _model_root(repo_root: Path) -> Path:
    return repo_root.joinpath(*_MODEL_ROOT_PARTS)


def _within_model_root(path: Path, repo_root: Path) -> bool:
    """Traversal guard: resolution never escapes the served model root."""

    try:
        return path.resolve().is_relative_to(_model_root(repo_root).resolve())
    except OSError:
        return False


def _valid_run_dir(run_dir: object, repo_root: Path) -> bool:
    if not isinstance(run_dir, str) or not run_dir:
        return False
    return _within_model_root(repo_root / run_dir, repo_root)


def _read_pointer(
    entry: RegistryArtifact, repo_root: Path, load_json: LoadJson
) -> tuple[str, dict[str, Any] | None]:
    """Read an entry's governing pointer → (pointer_status, parsed body).

    Exception-driven so an injected loader controls the outcome: absent →
    ``pointer_missing``; unreadable (permissions), undecodable, non-object, or
    an unusable ``run_dir`` (missing/empty/escaping the model root) →
    ``pointer_malformed``; parseable but not referencing this entry →
    ``pointer_mismatch``. Manifest reference comparison is a strict
    case-sensitive string match — a case-drifted path that happens to resolve
    on macOS must still surface before it breaks on a case-sensitive host.
    """

    if entry.governing_pointer is None:
        return "not_applicable", None
    pointer_path = repo_root / entry.governing_pointer
    try:
        if not pointer_path.resolve().is_relative_to(repo_root.resolve()):
            return "pointer_malformed", None
    except OSError:
        return "pointer_malformed", None
    try:
        body = load_json(pointer_path)
    except FileNotFoundError:
        return "pointer_missing", None
    except (OSError, ValueError, UnicodeDecodeError):
        return "pointer_malformed", None
    if not isinstance(body, dict):
        return "pointer_malformed", None
    if entry.path_resolution == "latest_run_dir":
        if not _valid_run_dir(body.get("run_dir"), repo_root):
            return "pointer_malformed", None
        return "referenced", body
    values = [value for value in body.values() if isinstance(value, str)]
    if entry.path in values:
        return "referenced", body
    return "pointer_mismatch", body


def derive_pointer_status(
    *,
    entry: RegistryArtifact,
    repo_root: Path,
    load_json: LoadJson | None = None,
) -> str:
    """Governing-pointer health for one registry entry (spec §3.5, Codex R6)."""

    status, _body = _read_pointer(entry, repo_root, load_json or _load_json_file)
    return status


def _resolve_artifact_path(
    entry: RegistryArtifact,
    repo_root: Path,
    pointer_status: str,
    pointer_body: dict[str, Any] | None,
) -> tuple[str, Path | None]:
    """Resolve (repo-relative display path, absolute path or None).

    ``latest_run_dir`` entries resolve only through a healthy pointer — with the
    pointer broken the run dir is unknown, so the artifact is unresolvable
    (reported by its raw filename) rather than guessed. The FINAL resolved path
    must stay under the model root in BOTH resolution modes (Codex T3 R9): a
    registry ``path`` that normalizes outside it (`../` in a filename, or a
    literal like ``app/data/models/../x.pkl``) is unresolvable (fail-closed),
    never hashed — otherwise escaped bytes could hash-match and report ``ok``.
    """

    if entry.path_resolution == "latest_run_dir":
        if pointer_status == "referenced" and pointer_body is not None:
            run_dir = pointer_body["run_dir"]
            absolute = repo_root / run_dir / entry.path
            if not _within_model_root(absolute, repo_root):
                return entry.path, None
            display = f"{run_dir.rstrip('/')}/{entry.path}"
            return display, absolute
        return entry.path, None
    absolute = repo_root / entry.path
    if not _within_model_root(absolute, repo_root):
        return entry.path, None
    return entry.path, absolute


def inspect_registered_artifact(
    *,
    entry: RegistryArtifact,
    repo_root: Path,
    environment: str,
    hash_file: HashFile | None = None,
    load_json: LoadJson | None = None,
) -> ArtifactProvenance:
    """Inspect one registered artifact on disk and classify its provenance.

    The T3 disk layer: derives ``pointer_status``, resolves the served path
    (``latest_run_dir`` via the pointer's run dir — Codex R1/R6b), establishes
    presence + streamed observed hash, then delegates the meaning to the pure
    T2 ``classify_artifact``. Disk anomalies fail closed as absence: a
    directory squatting on the artifact path, a dangling symlink, or an
    unreadable file (PermissionError) all classify as missing rather than
    crashing or passing.
    """

    if environment not in _VALID_ENVIRONMENTS:
        raise RuntimeEnvironmentError(
            f"inspect_registered_artifact received an invalid environment "
            f"{environment!r}; expected one of {sorted(_VALID_ENVIRONMENTS)}"
        )
    hasher = hash_file or hash_file_sha256
    loader = load_json or _load_json_file

    pointer_status, pointer_body = _read_pointer(entry, repo_root, loader)
    display_path, absolute_path = _resolve_artifact_path(
        entry, repo_root, pointer_status, pointer_body
    )

    artifact_present = False
    observed_hash: str | None = None
    if absolute_path is not None and absolute_path.is_file():
        try:
            observed_hash = hasher(absolute_path)
            artifact_present = True
        except OSError:
            artifact_present = False
            observed_hash = None

    provenance = classify_artifact(
        entry=entry,
        artifact_present=artifact_present,
        observed_hash=observed_hash,
        pointer_status=pointer_status,
        environment=environment,
    )
    if provenance.path != display_path:
        provenance = provenance.model_copy(update={"path": display_path})
    return provenance


def scan_unregistered_local_artifacts(
    *,
    registry: ModelRegistry,
    repo_root: Path,
    environment: str,
    load_json: LoadJson | None = None,
) -> list[ArtifactProvenance]:
    """Scoped reverse scan for ``.pkl`` bytes the registry does not declare.

    Scan roots (Codex R5 — never a blanket walk, never ``tests/`` fixtures):
    the served model root's top level, plus pointer-referenced run dirs and
    registered artifacts' parent dirs, all confined to the model root.

    Severity keys on pointer-REFERENCED file paths, not directory containment
    (cockpit-converged 2026-07-02 over the real ``te_v2.pkl`` stale sibling): a
    pointer naming bytes the registry does not know is unapproved serving
    reality → ``integrity``/blocked in serving/production (``caveat`` in
    dev/ci — visible, not blocking); an unreferenced sibling or off-path
    leftover is inert to the resolvers → ``info``, never degrading anything.
    """

    if environment not in _VALID_ENVIRONMENTS:
        raise RuntimeEnvironmentError(
            f"scan_unregistered_local_artifacts received an invalid environment "
            f"{environment!r}; expected one of {sorted(_VALID_ENVIRONMENTS)}"
        )
    loader = load_json or _load_json_file

    registered: set[str] = set()
    referenced: set[str] = set()
    scan_dirs: set[Path] = set()
    root = _model_root(repo_root)
    if root.is_dir():
        scan_dirs.add(root)

    for entry in registry.artifacts:
        pointer_status, pointer_body = _read_pointer(entry, repo_root, loader)
        display_path, absolute_path = _resolve_artifact_path(
            entry, repo_root, pointer_status, pointer_body
        )
        registered.add(display_path)
        if absolute_path is not None and _within_model_root(
            absolute_path.parent, repo_root
        ):
            scan_dirs.add(absolute_path.parent)
        if pointer_body is None:
            continue
        if entry.path_resolution == "latest_run_dir":
            if pointer_status == "referenced":
                referenced.add(display_path)
        else:
            for value in pointer_body.values():
                if not isinstance(value, str) or not value.endswith(".pkl"):
                    continue
                referenced.add(value)
                parent = (repo_root / value).parent
                if _within_model_root(parent, repo_root):
                    scan_dirs.add(parent)

    found: set[str] = set()
    for directory in scan_dirs:
        if not directory.is_dir():
            continue
        for candidate in directory.glob("*.pkl"):
            if candidate.is_file():
                found.add(str(candidate.relative_to(repo_root)))

    rows: list[ArtifactProvenance] = []
    for rel_path in sorted(found - registered):
        is_referenced = rel_path in referenced
        if is_referenced and environment in _SERVING_ENVS:
            severity, serving_allowed = "integrity", False
        elif is_referenced:
            severity, serving_allowed = "caveat", True
        else:
            severity, serving_allowed = "info", True
        rows.append(
            ArtifactProvenance(
                artifact_id=f"unregistered:{rel_path}",
                path=rel_path,
                expected_kind="local_operational",
                promotion_status="active" if is_referenced else "parked",
                observed_status="unregistered_local",
                pointer_status="referenced" if is_referenced else "not_applicable",
                severity=severity,  # type: ignore[arg-type]
                load_verification_status="not_verified",
                serving_allowed=serving_allowed,
                decision_supported=False,
            )
        )
    return rows
