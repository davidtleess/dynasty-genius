"""Does the published trust surface describe the model that is actually SERVING?

The trust surface publishes accuracy figures for a model. Nothing verified that the
model it describes is the one answering David's questions — so on 2026-09-01 every
figure on screen belonged to four models replaced on 2026-08-31, and no guard fired.

Two guards existed and neither could catch it:

* ``publish_trust_surface.py`` compares ``card.model_version`` to
  ``artifact.model_version``. Both are the literal string ``"engine_b_v2"`` for every
  bundle ever built, so the check passes by construction while the artifacts differ.
* ``validate_trust_publication.py`` compares the published card's
  ``model_artifact_hash`` to the artifact's — but the publisher COPIED that value from
  the artifact moments earlier. It compares a value to a copy of itself.

Neither ever consults the serving manifest. This module does, by CONTENT: it hashes the
bundle that is actually deployed and compares it to the hash the trust artifact recorded.

Fails closed. An unreadable manifest, a missing bundle, or an absent recorded hash all
return NOT aligned. A staleness check that assumes freshness when it cannot see is worse
than no check, because it manufactures confidence instead of withholding it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENGINE_B_MANIFEST_PATH = Path("app/data/models/engine_b/v2_manifest.json")


@dataclass(frozen=True)
class ServedModelAlignment:
    """Whether the published figures describe the deployed model."""

    position: str
    aligned: bool
    reason: str
    published_hash: Optional[str] = None
    served_hash: Optional[str] = None
    served_path: Optional[str] = None


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_served_alignment(
    position: str,
    published_hash: Optional[str],
    *,
    manifest_path: Path = ENGINE_B_MANIFEST_PATH,
    root: Path | None = None,
) -> ServedModelAlignment:
    """Compare the trust artifact's recorded model hash to the deployed bundle's bytes.

    ``root`` resolves manifest-relative bundle paths; defaults to the process cwd, which
    is how every other reader in this repo resolves ``app/data`` paths.
    """
    pos = position.upper()
    base = root or Path.cwd()

    if not published_hash:
        return ServedModelAlignment(
            position=pos,
            aligned=False,
            reason="the published figures carry no model identity to check",
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ServedModelAlignment(
            position=pos,
            aligned=False,
            reason="the serving manifest could not be read",
            published_hash=published_hash,
        )

    entry = manifest.get(pos)
    if not entry:
        # A position mapped to null is a deliberate not-promoted statement, not an error
        # — but it still means the published figures describe nothing that is serving.
        return ServedModelAlignment(
            position=pos,
            aligned=False,
            reason="no model is currently deployed for this position",
            published_hash=published_hash,
        )

    bundle = Path(entry)
    if not bundle.is_absolute():
        bundle = base / bundle
    try:
        served_hash = _sha256_file(bundle)
    except OSError:
        return ServedModelAlignment(
            position=pos,
            aligned=False,
            reason="the deployed model file could not be read",
            published_hash=published_hash,
            served_path=str(entry),
        )

    aligned = served_hash == published_hash
    return ServedModelAlignment(
        position=pos,
        aligned=aligned,
        reason=(
            "the published figures describe the deployed model"
            if aligned
            else "the deployed model has been replaced since these figures were measured"
        ),
        published_hash=published_hash,
        served_hash=served_hash,
        served_path=str(entry),
    )
