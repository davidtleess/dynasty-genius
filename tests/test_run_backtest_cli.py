from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from scripts import run_backtest


class _FakeArtifact:
    def __init__(self, position: str, grade: str = "ACTIVE_B_VALIDATED") -> None:
        self.run_id = uuid4()
        self.position = position
        self.promotion_gate = SimpleNamespace(overall_grade=grade)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"backtest_result_{self.position}.json"
        path.write_text("{}", encoding="utf-8")
        return path


class _FakeDriver:
    calls: list[tuple[str, str]] = []

    def __init__(self, position: str, model_version: str) -> None:
        self.position = position
        self.model_version = model_version
        self.calls.append((position, model_version))

    def run(self, market_store=None):
        return _FakeArtifact(self.position)


def test_cli_runs_single_position_with_model_version(monkeypatch, tmp_path):
    monkeypatch.setattr(run_backtest, "WalkForwardDriver", _FakeDriver)
    _FakeDriver.calls = []

    exit_code = run_backtest.main([
        "--position",
        "WR",
        "--model",
        "engine_b_v2_test",
        "--output-dir",
        str(tmp_path),
    ])

    assert exit_code == 0
    assert _FakeDriver.calls == [("WR", "engine_b_v2_test")]
    assert list(tmp_path.glob("*/backtest_result_WR.json"))


def test_cli_all_runs_qb_rb_wr_with_default_model(monkeypatch, tmp_path):
    monkeypatch.setattr(run_backtest, "WalkForwardDriver", _FakeDriver)
    _FakeDriver.calls = []

    exit_code = run_backtest.main(["--all", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    assert _FakeDriver.calls == [
        ("QB", "engine_b_v2"),
        ("RB", "engine_b_v2"),
        ("WR", "engine_b_v2"),
    ]
    for position in ["QB", "RB", "WR"]:
        assert list(tmp_path.glob(f"*/backtest_result_{position}.json"))
