"""Declared, permanent absences of REQUIRED provenance artifacts.

The capture reads certain artifacts solely to sha256 them, and aborts when one is missing
(`required_provenance_missing`). That refusal is correct and stays: an unreadable model
must be a hard error (David, 2026-08-31).

But an artifact can be gone in a way no retry fixes. On 2026-08-31 a write inside an
already-symlinked directory followed the link into the real tree and destroyed
`te_v3_metadata.json`; it is in no backup, because `backup_manifest.json` named the pickle
and the manifest from that directory but never the metadata. There is nothing to restore
and nothing to verify a reconstruction against — a sha256 proves a file matches, it cannot
produce one.

The answer is not to weaken the check and not to fabricate a witness. It is to replace the
missing witness with a RECORDED STATEMENT OF ITS ABSENCE: a narrow, named, David-ruled
registry that travels into the provenance record itself, so the vintage says "this witness
is absent, and here is why" rather than appearing whole. An artifact that is missing and
NOT declared still aborts, byte-for-byte as before.

Sound only where the bytes were hashed and never parsed. If content is read, a declared
absence would silently change behaviour instead of only changing a hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

DISCONTINUITY_REGISTRY_PATH = Path("app/config/provenance_discontinuities.json")


def load_declared_discontinuities(
    read_artifact: Callable[[Any], bytes],
) -> dict[str, dict]:
    """Declared path -> entry. An absent registry declares NOTHING, which is fail-closed:
    with no registry every missing artifact still aborts."""
    try:
        raw = read_artifact(DISCONTINUITY_REGISTRY_PATH)
    except FileNotFoundError:
        return {}
    payload = json.loads(raw)
    return {entry["path"]: entry for entry in payload.get("artifacts", [])}


def sha_or_declared_absence(
    path: Path,
    *,
    read_artifact: Callable[[Any], bytes],
    declared: dict[str, dict],
) -> tuple[Optional[str], Optional[dict]]:
    """``(sha256, None)`` when the artifact reads.

    ``(None, entry)`` when it is missing AND declared unrecoverable, where ``entry`` is the
    raw registry record. Callers project what they need: the hashed provenance SUBSET takes
    the minimal stable fact via :func:`hashable_absence`, so that re-wording the registry's
    prose can never move ``provenance_hash``; the stored block may carry the full record.

    Re-raises ``FileNotFoundError`` when it is missing and NOT declared. That path is the
    existing behaviour and must stay: this module narrows the refusal to a named list, it
    does not soften it.
    """
    try:
        return hashlib.sha256(read_artifact(path)).hexdigest(), None
    except FileNotFoundError:
        entry = declared.get(str(path))
        if entry is None:
            raise
        return None, entry


def hashable_absence(entry: dict) -> dict:
    """The minimal fact, for the subset that defines ``provenance_hash``.

    Only the identity of the absence — never prose. Editing a ``cause`` or ``serving_impact``
    sentence must not change a vintage hash; losing a different artifact, or losing this one
    on a different date, must.
    """
    return {
        "status": "provenance_unavailable",
        "unrecoverable_since": entry.get("unrecoverable_since"),
    }


def recorded_absence(entry: dict) -> dict:
    """The full record, for the stored provenance block (not hashed)."""
    return {
        "status": "provenance_unavailable",
        "declared_in": str(DISCONTINUITY_REGISTRY_PATH),
        "unrecoverable_since": entry.get("unrecoverable_since"),
        "cause": entry.get("cause"),
        # Carried so a reader of a stored vintage never has to guess whether serving was
        # affected — for this class it is the first question asked.
        "serving_impact": entry.get("serving_impact"),
    }
