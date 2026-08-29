"""Load-time artifact verification — serving that can refuse the wrong
artifact (§8.2, DG-057).

Before this module, serving loaded pickles by pointer with no verification of
any kind (engine_a.py read latest.json and ``pickle.load()``ed whatever the
run directory held — the blindness that let DG-017's validated-scaled /
deployed-unscaled split go unnoticed). This module gives every loader one
verification call with exactly three outcomes:

- **verified** — the artifact carries a spec sidecar
  (``<artifact>.spec.json``), its content sha256 matches the sidecar, the
  sidecar's embedded TrainingSpec re-hashes to its recorded ``spec_hash``,
  and (when the loading pointer pins one) that hash equals the pinned
  ``training_spec_hash``.
- **pre_spec_artifact** — the artifact has no sidecar but its content sha256
  is on the explicit, frozen pre-spec grandfather list
  (``app/config/pre_spec_grandfather.json``): the artifacts already deployed
  when DG-057 landed. They load exactly as before, with this state disclosed.
- **refusal** — everything else raises :class:`ArtifactSpecRefusal` with a
  machine-readable ``reason``. Serving must not catch-and-continue past it.

Grandfathering rules (deliberate, narrow):
- The list is FROZEN. It names the artifacts that predate the spec, by exact
  content sha256, sourced from ``model_registry.json``. Nothing may ever be
  added: every artifact trained after DG-057 is spec-hashed at training time
  via :func:`write_spec_sidecar`.
- A pinned pointer (one that carries ``training_spec_hash``) is never
  satisfied by grandfathering — a pin is a promise only a verified sidecar
  can keep.
- A present sidecar always takes precedence over the grandfather list: an
  explicit claim that fails verification is refused, never waved through.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.dynasty_genius.models.training_spec import TrainingSpec

__all__ = [
    "STATE_PRE_SPEC",
    "STATE_VERIFIED",
    "ArtifactSpecRefusal",
    "SpecVerification",
    "load_pre_spec_grandfather",
    "sidecar_path_for",
    "verify_artifact",
    "write_spec_sidecar",
]

_ROOT = Path(__file__).resolve().parents[3]

GRANDFATHER_CONFIG_PATH = _ROOT / "app" / "config" / "pre_spec_grandfather.json"

SIDECAR_SUFFIX = ".spec.json"
SIDECAR_SCHEMA_VERSION = 1

STATE_VERIFIED = "verified"
STATE_PRE_SPEC = "pre_spec_artifact"


class ArtifactSpecRefusal(RuntimeError):
    """Serving refused an artifact. ``reason`` is machine-readable:

    - ``spec_hash_mismatch`` — sidecar's spec hash is not the pinned one.
    - ``content_hash_mismatch`` — artifact bytes are not the bytes the
      sidecar was written for (moved, overwritten, or tampered).
    - ``sidecar_invalid`` — sidecar unreadable, wrong schema, or its embedded
      TrainingSpec does not re-hash to its recorded spec_hash.
    - ``unverifiable_artifact`` — no sidecar and not grandfathered, or no
      sidecar under a pinned pointer.
    """

    def __init__(self, reason: str, message: str, artifact_path: Path) -> None:
        super().__init__(f"{reason}: {message} [{artifact_path}]")
        self.reason = reason
        self.artifact_path = artifact_path


@dataclass(frozen=True)
class SpecVerification:
    """The disclosed outcome of a successful verification."""

    state: str  # STATE_VERIFIED | STATE_PRE_SPEC
    artifact_sha256: str
    spec_hash: Optional[str]  # None for pre-spec artifacts — disclosed, not hidden


def sidecar_path_for(artifact_path: Path) -> Path:
    """``X.pkl`` → ``X.pkl.spec.json`` (suffix appended, never substituted)."""
    return artifact_path.parent / f"{artifact_path.name}{SIDECAR_SUFFIX}"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Training-time API ────────────────────────────────────────────────────────

def write_spec_sidecar(artifact_path: Path, spec: TrainingSpec) -> Path:
    """Stamp an artifact with the hash of the spec that trained it.

    Called at training time, immediately after the artifact is written. The
    sidecar records the artifact's content sha256, the spec hash, and the
    full spec for inspectability.
    """
    artifact_path = Path(artifact_path)
    if not artifact_path.exists():
        raise FileNotFoundError(f"cannot stamp missing artifact: {artifact_path}")
    payload = {
        "sidecar_schema_version": SIDECAR_SCHEMA_VERSION,
        "artifact_sha256": _sha256_file(artifact_path),
        "spec_hash": spec.spec_hash(),
        "training_spec": spec.to_dict(),
    }
    sidecar = sidecar_path_for(artifact_path)
    sidecar.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return sidecar


# ── Grandfather list ─────────────────────────────────────────────────────────

def load_pre_spec_grandfather(
    config_path: Path = GRANDFATHER_CONFIG_PATH,
) -> frozenset[str]:
    """The frozen set of pre-spec content sha256s. Missing config = empty set
    is WRONG on the deployed tree — the config ships with this module — but
    the loader stays strict: a malformed config raises rather than silently
    grandfathering nothing (which would refuse the deployed artifacts)."""
    payload = json.loads(Path(config_path).read_text())
    if payload.get("grandfather_schema_version") != 1:
        raise ValueError(
            f"unsupported grandfather schema in {config_path}: "
            f"{payload.get('grandfather_schema_version')!r}"
        )
    return frozenset(entry["sha256"] for entry in payload["artifacts"])


# ── Load-time API ────────────────────────────────────────────────────────────

def verify_artifact(
    artifact_path: Path,
    *,
    expected_spec_hash: Optional[str],
    grandfathered_sha256s: frozenset[str],
) -> SpecVerification:
    """Verify one artifact at load time. Returns a :class:`SpecVerification`
    on the two pass states; raises :class:`ArtifactSpecRefusal` otherwise.

    ``expected_spec_hash`` is the pointer's pin (``training_spec_hash`` in
    latest.json) or None for a pre-spec pointer. Pinned pointers are never
    satisfied by grandfathering.
    """
    artifact_path = Path(artifact_path)
    actual_sha = _sha256_file(artifact_path)
    sidecar = sidecar_path_for(artifact_path)

    if not sidecar.exists():
        if expected_spec_hash is None and actual_sha in grandfathered_sha256s:
            return SpecVerification(
                state=STATE_PRE_SPEC,
                artifact_sha256=actual_sha,
                spec_hash=None,
            )
        raise ArtifactSpecRefusal(
            "unverifiable_artifact",
            "no spec sidecar and not on the pre-spec grandfather list"
            if expected_spec_hash is None
            else "pointer pins a spec hash but the artifact has no spec sidecar",
            artifact_path,
        )

    # A sidecar exists: it must verify. Grandfathering never rescues a
    # failing explicit claim.
    try:
        payload = json.loads(sidecar.read_text())
        schema = payload["sidecar_schema_version"]
        recorded_artifact_sha = payload["artifact_sha256"]
        recorded_spec_hash = payload["spec_hash"]
        spec_dict = payload["training_spec"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ArtifactSpecRefusal(
            "sidecar_invalid", f"unreadable sidecar: {e}", artifact_path
        ) from e
    if schema != SIDECAR_SCHEMA_VERSION:
        raise ArtifactSpecRefusal(
            "sidecar_invalid", f"unsupported sidecar schema {schema!r}", artifact_path
        )

    try:
        rehash = TrainingSpec.from_dict(spec_dict).spec_hash()
    except (ValueError, TypeError) as e:
        raise ArtifactSpecRefusal(
            "sidecar_invalid", f"embedded TrainingSpec invalid: {e}", artifact_path
        ) from e
    if rehash != recorded_spec_hash:
        raise ArtifactSpecRefusal(
            "sidecar_invalid",
            "embedded TrainingSpec does not re-hash to the recorded spec_hash",
            artifact_path,
        )

    if actual_sha != recorded_artifact_sha:
        raise ArtifactSpecRefusal(
            "content_hash_mismatch",
            f"artifact bytes {actual_sha[:12]}… are not the stamped "
            f"{recorded_artifact_sha[:12]}…",
            artifact_path,
        )

    if expected_spec_hash is not None and recorded_spec_hash != expected_spec_hash:
        raise ArtifactSpecRefusal(
            "spec_hash_mismatch",
            f"artifact was trained under spec {recorded_spec_hash[:12]}… but the "
            f"pointer pins {expected_spec_hash[:12]}…",
            artifact_path,
        )

    return SpecVerification(
        state=STATE_VERIFIED,
        artifact_sha256=actual_sha,
        spec_hash=recorded_spec_hash,
    )
