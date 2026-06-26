"""F-feature-refresh T4 RED: automated no-commit scheduler + ops docs."""

from __future__ import annotations

import importlib
import plistlib
import re
from pathlib import Path

PLIST = Path("ops/launchd/com.davidleess.dynasty-feature-refresh.plist")
ARTIFACTS = Path("docs/ARTIFACTS.md")
QUICK_REFERENCE = Path("docs/development/quick-reference.md")
ROOT = Path("/Users/davidleess/dynasty-genius-product")


def test_feature_refresh_launchd_plist_runs_refresh_cli_before_pvo_window() -> None:
    data = plistlib.loads(PLIST.read_bytes())
    args = data["ProgramArguments"]

    assert data["Label"] == "com.davidleess.dynasty-feature-refresh"
    assert args == [
        str(ROOT / ".venv" / "bin" / "python3.14"),
        str(ROOT / "scripts" / "run_feature_refresh.py"),
    ]
    assert data["WorkingDirectory"] == str(ROOT)
    assert data["StartCalendarInterval"] == {"Hour": 9, "Minute": 15}
    assert data["RunAtLoad"] is False
    assert data["StandardOutPath"] == str(
        ROOT / "app" / "data" / "logs" / "feature_refresh.out.log"
    )
    assert data["StandardErrorPath"] == str(
        ROOT / "app" / "data" / "logs" / "feature_refresh.err.log"
    )

    forbidden_args = {
        "git",
        "scripts/train_engine_b.py",
        "scripts/assemble_engine_b_dataset.py",
        "app/data/models",
    }
    assert not forbidden_args.intersection(args)


def test_feature_refresh_launchd_plist_is_parseable_without_macos_plutil() -> None:
    data = plistlib.loads(PLIST.read_bytes())

    assert isinstance(data, dict)
    assert "ProgramArguments" in data
    assert "StartCalendarInterval" in data


def test_feature_refresh_cli_real_run_uses_atomic_publish_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A scheduled CLI run must publish the validated runtime, not stop at candidate."""
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,position,training_eligible\n")
    captured: dict = {}

    monkeypatch.setattr(cli, "_load_source", lambda _seasons: {"frames": object()})
    monkeypatch.setattr(cli, "compute_source_hash", lambda **_kwargs: "source-hash")

    def fake_run_feature_refresh(**kwargs):
        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(cli, "run_feature_refresh", fake_run_feature_refresh)

    rc = cli.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--seed-path",
            str(seed_path),
            "--season-start",
            "2023",
            "--season-end",
            "2025",
        ]
    )

    assert rc == 0
    assert callable(captured["publish_fn"])
    assert captured["runtime_dir"] == str(runtime_dir)
    assert captured["seed_path"] == str(seed_path)


def test_feature_refresh_cli_refuses_existing_lock_before_loading_sources(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir()
    (runtime_dir / "feature_refresh.lock").write_text("already running")
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,position,training_eligible\n")

    def fail_load(_seasons):
        raise AssertionError("locked scheduler must not load nflreadpy sources")

    monkeypatch.setattr(cli, "_load_source", fail_load)

    rc = cli.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--seed-path",
            str(seed_path),
            "--season-start",
            "2023",
            "--season-end",
            "2025",
        ]
    )

    out = capsys.readouterr().out.lower()
    assert rc == 1
    assert "locked" in out
    assert not (runtime_dir / "engine_b_features_candidate.csv").exists()


def test_feature_refresh_cli_exits_nonzero_when_publish_blocks(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,position,training_eligible\n")

    monkeypatch.setattr(cli, "_load_source", lambda _seasons: {"frames": object()})
    monkeypatch.setattr(cli, "compute_source_hash", lambda **_kwargs: "source-hash")
    monkeypatch.setattr(
        cli,
        "run_feature_refresh",
        lambda **_kwargs: {"status": "blocked", "blocked_reason": "validation failed"},
    )

    rc = cli.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--seed-path",
            str(seed_path),
            "--season-start",
            "2023",
            "--season-end",
            "2025",
        ]
    )

    assert rc == 1
    assert "blocked" in capsys.readouterr().out


def test_feature_refresh_scheduler_log_directory_placeholder_exists() -> None:
    assert Path("app/data/logs/.gitkeep").is_file()


def test_feature_refresh_active_docs_record_scheduler_and_go_live_boundary() -> None:
    artifacts_text = ARTIFACTS.read_text(encoding="utf-8")
    quick_reference_text = QUICK_REFERENCE.read_text(encoding="utf-8")
    combined = f"{artifacts_text}\n{quick_reference_text}"

    required_fragments = [
        "scripts/run_feature_refresh.py",
        "ops/launchd/com.davidleess.dynasty-feature-refresh.plist",
        "app/data/features_runtime/engine_b_features_runtime.csv",
        "app/data/features_runtime/engine_b_features_runtime.ready.json",
        "feature_refresh.lock",
        "09:15",
        "RunAtLoad=false",
        "decision_supported=false",
    ]
    for fragment in required_fragments:
        assert fragment in combined

    artifacts_section = artifacts_text.split(
        "## F-Feature-Refresh Operational Scheduler", 1
    )[1]
    artifacts_section = artifacts_section.split("\n## ", 1)[0].lower()
    assert "seed-split" in artifacts_section
    assert "no auto-commit" in artifacts_section
    assert "source-hash" in artifacts_section
    assert "noop" in artifacts_section
    assert "launchctl" in artifacts_section and "david" in artifacts_section

    banned_patterns = [
        r"\bbuy\b",
        r"\bsell\b",
        r"\bwin\b",
        r"\bloss\b",
        r"\btiering\b",
        r"tradeable edge",
    ]
    for pattern in banned_patterns:
        assert re.search(pattern, artifacts_section) is None
