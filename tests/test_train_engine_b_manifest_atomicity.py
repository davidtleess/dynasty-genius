"""The manifest the live product reads must never be observed truncated.

Why this file exists: `train_engine_b.py` published `v2_manifest.json` with a plain
`open(path, "w")`, which truncates the file the instant it opens. Between that truncate
and the `json.dump` completing there is a real window in which the manifest on disk is
empty or half-written.

That window is not cosmetic, because of what reads the file. `EngineBService` resolves a
bundle with `self._v2_bundles.get(position) or self._v1_bundle`
(app/services/engine_b_service.py:136) — a silent fail-open. A reader landing inside the
window finds no v2 bundles and serves the superseded **v1** model for every position,
with no error and no caveat. A retrain is exactly when that window opens, and a retrain
happens while the product is live.

The repository already answers this elsewhere: `_atomic_write_json` in
`league_transactions.py:73` and `nflverse_usage.py:104` both write to a temp file in the
same directory and `os.replace` it into place, which is atomic on POSIX. This test pins
the same guarantee for the manifest.

The test asserts BEHAVIOUR, not implementation: it makes serialisation fail partway and
then requires that the previously-published manifest is still intact and still parses. A
truncating write cannot satisfy that; any atomic publish can.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_a_failed_manifest_write_leaves_the_previous_manifest_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If publishing dies mid-write, the live product must still resolve v2 bundles."""
    from scripts import train_engine_b

    manifest_path = tmp_path / "v2_manifest.json"
    good = {"QB": "runs/A/qb_v2.pkl", "RB": "runs/A/rb_v2.pkl"}
    manifest_path.write_text(json.dumps(good, indent=2))

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full midway through serialisation")

    monkeypatch.setattr(train_engine_b.json, "dumps", _explode)
    monkeypatch.setattr(train_engine_b.json, "dump", _explode)

    with pytest.raises(RuntimeError):
        train_engine_b.write_manifest(manifest_path, {"QB": "runs/B/qb_v2.pkl"})

    surviving = manifest_path.read_text()
    assert surviving.strip(), (
        "the manifest was truncated by a failed write; EngineBService would find no v2 "
        "bundles and silently serve the superseded v1 model for every position"
    )
    assert json.loads(surviving) == good, (
        "a failed publish must leave the previously-published manifest exactly intact"
    )


def test_a_successful_manifest_write_publishes_the_new_content(tmp_path: Path) -> None:
    """The atomic path must still actually publish — a guard that never writes is useless."""
    from scripts import train_engine_b

    manifest_path = tmp_path / "v2_manifest.json"
    manifest_path.write_text(json.dumps({"QB": "runs/A/qb_v2.pkl"}, indent=2))

    new = {"QB": "runs/B/qb_v2.pkl", "TE": "runs/B/te_v3.pkl"}
    train_engine_b.write_manifest(manifest_path, new)

    assert json.loads(manifest_path.read_text()) == new


def test_no_temp_files_are_left_behind_by_a_failed_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retrain loop that leaks a .tmp per failure fills the models directory."""
    from scripts import train_engine_b

    manifest_path = tmp_path / "v2_manifest.json"
    manifest_path.write_text(json.dumps({"QB": "runs/A/qb_v2.pkl"}, indent=2))

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("serialisation failed")

    monkeypatch.setattr(train_engine_b.json, "dumps", _explode)
    monkeypatch.setattr(train_engine_b.json, "dump", _explode)

    with pytest.raises(RuntimeError):
        train_engine_b.write_manifest(manifest_path, {"QB": "runs/B/qb_v2.pkl"})

    assert list(tmp_path.glob("*.tmp")) == [], "a failed publish must clean up its temp file"
