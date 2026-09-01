"""A retrain must declare itself, so a scorer cannot read the model set mid-swap.

Publishing a retrain replaces four pickles and a manifest as FIVE separate writes.
`com.davidleess.dynasty-model-pvo-refresh` fires at 11:30 and 14:00 and takes no lock, so a
run landing inside those five writes scores the universe from a half-swapped model set and
publishes the result as live serving state — with a green receipt, because from its side
nothing failed.

`model_publish_lock` (DG-126) is the consumer half and it is already landed. It is INERT
until a producer declares itself: it can only refuse when something has written the
sentinel. These tests are the producer half.

The atomic manifest write landed earlier closes a different window — a reader seeing a
truncated manifest. It does not make five separate writes safe together. Both are needed.

Note what is NOT asserted here: that this is a lock. It is advisory. It stops the scheduled
scorer, which is the observed hazard; it does not stop a human running the scorer by hand,
and it does not make the five writes atomic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.model_publish_lock import sentinel_path


def test_the_sentinel_is_written_before_the_first_bundle_and_cleared_after_the_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordering is the whole point: a sentinel written after the pickles guards nothing."""
    from scripts import train_engine_b

    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)
    observed: list[str] = []
    real_write = train_engine_b.write_manifest

    def spy_write_manifest(path: Path, manifest: dict) -> None:
        observed.append("sentinel_present" if sentinel_path(tmp_path).exists() else "sentinel_absent")
        real_write(path, manifest)

    monkeypatch.setattr(train_engine_b, "write_manifest", spy_write_manifest)

    train_engine_b.publish_model_set(
        tmp_path / "manifest.json",
        {"QB": "runs/X/qb_v2.pkl"},
        run_id="20260901T000000Z",
    )

    assert observed == ["sentinel_present"], (
        "the manifest write must happen while the publish is declared; a sentinel that is "
        "not in place during the writes it guards protects nothing"
    )
    assert not sentinel_path(tmp_path).exists(), (
        "the sentinel must be cleared after the last write, or the next scheduled scorer "
        "defers against a publish that already finished"
    )


def test_a_failed_publish_still_clears_the_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale lock that silently stops the daily chain is worse than the race it prevents."""
    from scripts import train_engine_b

    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)

    def explode(*_a: object, **_k: object) -> None:
        raise RuntimeError("disk full while writing the manifest")

    monkeypatch.setattr(train_engine_b, "write_manifest", explode)

    with pytest.raises(RuntimeError):
        train_engine_b.publish_model_set(
            tmp_path / "manifest.json", {"QB": "runs/X/qb_v2.pkl"}, run_id="20260901T000000Z"
        )

    assert not sentinel_path(tmp_path).exists(), (
        "a crashed retrain must not leave a sentinel wedging the chain — the module has two "
        "staleness escapes, but relying on them for the ordinary failure path is sloppy"
    )


def test_the_sentinel_carries_a_timezone_aware_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A naive stamp is treated as stale by the consumer, which silently disables the guard."""
    from scripts import train_engine_b

    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)
    captured: dict = {}

    real_write = train_engine_b.write_manifest

    def capture(path: Path, manifest: dict) -> None:
        captured.update(json.loads(sentinel_path(tmp_path).read_text()))
        real_write(path, manifest)

    monkeypatch.setattr(train_engine_b, "write_manifest", capture)
    train_engine_b.publish_model_set(
        tmp_path / "manifest.json", {"QB": "runs/X/qb_v2.pkl"}, run_id="20260901T000000Z"
    )

    from datetime import datetime

    stamp = datetime.fromisoformat(captured["started_at"])
    assert stamp.tzinfo is not None, (
        "blocking_publish compares started_at to an aware now(); a naive stamp is read as "
        "stale and the guard quietly stops guarding"
    )
    assert captured["run_id"] == "20260901T000000Z"
    assert isinstance(captured["pid"], int)


def test_the_sentinel_covers_the_PICKLE_writes_not_only_the_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window being guarded opens at the FIRST bundle write, not the last.

    `train_v2_stratified` writes four pickles inside its position loop and the manifest
    afterwards. A scorer landing between pickle two and pickle three reads a half-swapped
    model set — which is the actual hazard. A sentinel that only wraps the manifest write
    leaves the entire pickle sequence unguarded and would be security theatre: present,
    green, and covering the wrong interval.
    """
    from scripts import train_engine_b

    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)
    seen: list[bool] = []

    def fake_train_position(pos, _df, run_dir, *_a, **_k):
        # the real _train_position creates run_dir before writing its bundle; the stub
        # must too, or the failure is the fixture's rather than the code's
        run_dir.mkdir(parents=True, exist_ok=True)
        seen.append(sentinel_path(tmp_path).exists())
        return {"skipped": True, "reason": "stubbed", "position": pos}

    monkeypatch.setattr(train_engine_b, "_train_position", fake_train_position)
    monkeypatch.setattr(train_engine_b, "_load_v1_0_metrics_by_position", lambda _df: {})
    monkeypatch.setattr(train_engine_b, "MODELS_DIR", tmp_path)

    import pandas as pd

    df = pd.DataFrame([{"training_eligible": True, "position": "QB", "feature_season": 2020}])
    train_engine_b.train_v2_stratified(df, tmp_path / "run")

    assert seen and all(seen), (
        "the sentinel must already be in place for EVERY position's bundle write; "
        f"observed presence per position: {seen}"
    )
    assert not sentinel_path(tmp_path).exists(), "and cleared once the publish completes"
