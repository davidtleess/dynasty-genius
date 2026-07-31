from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

import pytest

from src.dynasty_genius.capture.cfbd_foundation_refresh import (
    CfbdRefreshError,
    run_cfbd_foundation_refresh,
)

NOW = datetime(2026, 7, 31, 3, 0, tzinfo=timezone.utc)


def _input(path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "gsis_id",
                "position",
                "wr_dominator_final",
                "wr_dominator_final_source",
                "w2b_cfbd_degraded",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "gsis_id": "00-0000001",
                "position": "WR",
                "wr_dominator_final": "",
                "wr_dominator_final_source": "",
                "w2b_cfbd_degraded": "0",
            }
        )


def _builder(output_path, raw_cache_dir):
    (raw_cache_dir / "player_receiving_2025.json").write_text(
        json.dumps([{"player": "Example", "stat": 100}]),
        encoding="utf-8",
    )
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["wr_dominator_final"] = "0.31"
    rows[0]["wr_dominator_final_source"] = "cfbd"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_refresh_isolates_raw_and_curated_outputs_from_source_input(tmp_path):
    input_path = tmp_path / "input.csv"
    source_root = tmp_path / "source"
    _input(input_path)
    original = input_path.read_bytes()

    result = run_cfbd_foundation_refresh(
        source_root=source_root,
        input_path=input_path,
        builder=_builder,
        now_fn=lambda: NOW,
    )

    assert result["status"] == "ok"
    assert result["raw_file_count"] == 1
    assert result["identity_coverage"] == 1.0
    assert input_path.read_bytes() == original
    assert (
        source_root / "raw" / result["run_id"] / "player_receiving_2025.json"
    ).exists()
    assert (
        source_root / "curated" / "prospects_with_outcomes_v3.csv"
    ).exists()


def test_identical_refresh_is_noop_and_keeps_one_raw_run(tmp_path):
    input_path = tmp_path / "input.csv"
    source_root = tmp_path / "source"
    _input(input_path)
    first = run_cfbd_foundation_refresh(
        source_root=source_root,
        input_path=input_path,
        builder=_builder,
        now_fn=lambda: NOW,
    )
    second = run_cfbd_foundation_refresh(
        source_root=source_root,
        input_path=input_path,
        builder=_builder,
        now_fn=lambda: datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    assert second["status"] == "noop"
    assert second["last_changed_at"] == first["captured_at"]
    assert len(list((source_root / "raw").iterdir())) == 1


def test_degraded_output_fails_without_mutating_input(tmp_path):
    input_path = tmp_path / "input.csv"
    _input(input_path)
    original = input_path.read_bytes()

    def degraded_builder(output_path, raw_cache_dir):
        _builder(output_path, raw_cache_dir)
        text = output_path.read_text().replace(",0\n", ",1\n")
        output_path.write_text(text)

    with pytest.raises(CfbdRefreshError, match="degraded"):
        run_cfbd_foundation_refresh(
            source_root=tmp_path / "source",
            input_path=input_path,
            builder=degraded_builder,
            now_fn=lambda: NOW,
        )
    assert input_path.read_bytes() == original
    assert not (tmp_path / "source" / "raw").exists()


def test_missing_identity_fails_closed(tmp_path):
    input_path = tmp_path / "input.csv"
    _input(input_path)

    def no_identity_builder(output_path, raw_cache_dir):
        _builder(output_path, raw_cache_dir)
        output_path.write_text(
            output_path.read_text().replace("00-0000001", ""),
            encoding="utf-8",
        )

    with pytest.raises(CfbdRefreshError, match="identity coverage"):
        run_cfbd_foundation_refresh(
            source_root=tmp_path / "source",
            input_path=input_path,
            builder=no_identity_builder,
            now_fn=lambda: NOW,
        )


def test_invalid_raw_json_fails_closed(tmp_path):
    input_path = tmp_path / "input.csv"
    _input(input_path)

    def invalid_raw_builder(output_path, raw_cache_dir):
        _builder(output_path, raw_cache_dir)
        (raw_cache_dir / "player_receiving_2025.json").write_text("{")

    with pytest.raises(CfbdRefreshError, match="invalid raw JSON"):
        run_cfbd_foundation_refresh(
            source_root=tmp_path / "source",
            input_path=input_path,
            builder=invalid_raw_builder,
            now_fn=lambda: NOW,
        )


# --------------------------------------------------------------------------
# Pre-land isolation guards (Codex round-2 condition; Claude, limited handoff)
#
# The wrapper isolates the CFBD builder by monkeypatching two module globals.
# That only works while EVERY path inside `scripts.build_w2b_cfbd` is derived
# from those globals at CALL time. Nothing enforced that, so a future edit of
# the shape `def f(..., cache_dir: Path = CACHE_DIR)` would silently defeat the
# patch and write into `app/data/cfbd_cache/` — the directory held frozen for
# the pre-registered morning run — with every other test still green.
# --------------------------------------------------------------------------


def _default_values(func):
    """Every default value bound to a callable, positional and keyword-only."""
    values = list(func.__defaults__ or ())
    values.extend((func.__kwdefaults__ or {}).values())
    return values


def test_builder_binds_no_protected_path_as_a_default_argument():
    """A default argument is evaluated at DEF time, so a captured CACHE_DIR or
    V3_CSV survives the monkeypatch and writes to the real, protected location."""
    import inspect
    from pathlib import Path

    import scripts.build_w2b_cfbd as builder

    protected = [Path(builder.CACHE_DIR).resolve(), Path(builder.V3_CSV).resolve()]
    offenders = []
    for name, func in vars(builder).items():
        if not inspect.isfunction(func):
            continue
        for value in _default_values(func):
            if not isinstance(value, Path):
                continue
            resolved = value.resolve()
            for guard in protected:
                if resolved == guard or guard in resolved.parents:
                    offenders.append(f"{name}() default -> {resolved}")
    assert offenders == [], (
        "these defaults capture a protected path at import time and defeat the "
        f"wrapper's isolation: {offenders}"
    )


def test_builder_globals_are_restored_when_the_build_raises():
    """The wrapper patches V3_CSV/CACHE_DIR and restores them in `finally`. If a
    raising build left them patched, a LATER in-process caller would write into
    a deleted staging directory — or, worse, wherever the stale value points."""
    from pathlib import Path

    import scripts.build_w2b_cfbd as builder
    from scripts.run_cfbd_foundation_refresh import _builder

    original_csv, original_cache = builder.V3_CSV, builder.CACHE_DIR

    def explode(**_kwargs):
        raise RuntimeError("builder failed mid-run")

    saved_main = builder.main
    builder.main = explode
    try:
        with pytest.raises(RuntimeError, match="builder failed mid-run"):
            _builder(Path("/nonexistent/out.csv"), Path("/nonexistent/cache"))
    finally:
        builder.main = saved_main

    assert builder.V3_CSV == original_csv, "V3_CSV stayed patched after a failed build"
    assert builder.CACHE_DIR == original_cache, "CACHE_DIR stayed patched after a failed build"
