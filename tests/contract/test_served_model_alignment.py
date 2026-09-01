"""DG-132 — the trust surface must describe the model that is actually answering.

On 2026-09-01 it described four models replaced the day before and no guard fired,
because both existing guards were structurally incapable of firing: one compared a
version string that reads "engine_b_v2" for every bundle ever built, the other compared
a value to a copy of itself. These pin the content check that replaces them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.dynasty_genius.eval.served_model_alignment import check_served_alignment


def _bundle(tmp_path: Path, name: str, payload: bytes) -> tuple[Path, str]:
    p = tmp_path / name
    p.write_bytes(payload)
    return p, hashlib.sha256(payload).hexdigest()


def _manifest(tmp_path: Path, mapping: dict) -> Path:
    m = tmp_path / "v2_manifest.json"
    m.write_text(json.dumps(mapping), encoding="utf-8")
    return m


def test_matching_hash_is_aligned(tmp_path: Path) -> None:
    bundle, digest = _bundle(tmp_path, "qb_v2.pkl", b"served model bytes")
    manifest = _manifest(tmp_path, {"QB": str(bundle)})

    r = check_served_alignment("QB", digest, manifest_path=manifest, root=tmp_path)

    assert r.aligned is True
    assert r.served_hash == digest


def test_replaced_model_is_detected(tmp_path: Path) -> None:
    """The real defect: the file on disk changed, the published hash did not."""
    bundle, digest = _bundle(tmp_path, "qb_v2.pkl", b"the RETRAINED model")
    manifest = _manifest(tmp_path, {"QB": str(bundle)})

    r = check_served_alignment(
        "QB", "a" * 64, manifest_path=manifest, root=tmp_path
    )

    assert r.aligned is False
    assert r.served_hash == digest
    assert "replaced" in r.reason


def test_unreadable_manifest_fails_closed(tmp_path: Path) -> None:
    r = check_served_alignment(
        "QB", "a" * 64, manifest_path=tmp_path / "absent.json", root=tmp_path
    )
    assert r.aligned is False, "a check that cannot see must never report aligned"


def test_missing_bundle_fails_closed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {"QB": str(tmp_path / "never_written.pkl")})
    r = check_served_alignment(
        "QB", "a" * 64, manifest_path=manifest, root=tmp_path
    )
    assert r.aligned is False


def test_position_mapped_to_null_fails_closed(tmp_path: Path) -> None:
    """A null mapping is a deliberate not-promoted statement — and still means the
    published figures describe nothing that is serving."""
    manifest = _manifest(tmp_path, {"QB": None})
    r = check_served_alignment(
        "QB", "a" * 64, manifest_path=manifest, root=tmp_path
    )
    assert r.aligned is False


def test_absent_published_hash_fails_closed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {"QB": "whatever"})
    r = check_served_alignment("QB", None, manifest_path=manifest, root=tmp_path)
    assert r.aligned is False


def test_a_version_string_could_not_have_caught_this(tmp_path: Path) -> None:
    """Why the old guard failed, pinned so nobody reintroduces it.

    Two DIFFERENT model files both declaring model_version "engine_b_v2" — which every
    Engine B bundle ever built does — are indistinguishable by version string and
    distinguishable by content. That gap is the entire defect.
    """
    old, old_hash = _bundle(tmp_path, "old.pkl", b"May model")
    new, new_hash = _bundle(tmp_path, "new.pkl", b"August model")
    assert old_hash != new_hash, "content differs"

    manifest = _manifest(tmp_path, {"QB": str(new)})
    r = check_served_alignment("QB", old_hash, manifest_path=manifest, root=tmp_path)
    assert r.aligned is False


def test_live_artifacts_are_currently_misaligned_for_all_four_positions() -> None:
    """The measured state on 2026-09-01, and the reason this ticket exists.

    If this ever fails it means the backtest was re-run against the served bundles —
    which is the desired end state. Update it then, deliberately, with the new run id.
    """
    runs = Path("app/data/backtest/trust_surface/latest")
    if not runs.is_dir():
        import pytest

        pytest.skip("published trust surface absent in this tree")

    for pos in ("QB", "RB", "WR", "TE"):
        art = runs / f"backtest_result_{pos}.json"
        if not art.is_file():
            continue
        published = json.loads(art.read_text(encoding="utf-8")).get(
            "model_artifact_hash"
        )
        r = check_served_alignment(pos, published)
        assert r.aligned is False, (
            f"{pos} now reports aligned — if the backtest was re-run against the served "
            "bundles this assertion should be updated deliberately, not deleted"
        )
