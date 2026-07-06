from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DELTA = (
    REPO_ROOT / "docs" / "strategies" / "2026-07-05-daily-open-benchmark-delta.md"
)


def _read_required(path: Path) -> str:
    assert path.exists(), f"Missing required Task 5 evidence artifact: {path}"
    return path.read_text(encoding="utf-8")


def test_task5_commits_benchmark_delta_for_daily_open_visual_clear() -> None:
    text = _read_required(BENCHMARK_DELTA)

    required_sections = [
        "# H2 Task 5 Daily Open Benchmark Delta",
        "Dynasty Nerds reference",
        "DG evidence bundle",
        "Primitive-library usage",
        "Census-zero blast radius",
        "Benchmark parity",
        "Visual audit",
        "David preview gate",
    ]
    for section in required_sections:
        assert section in text


def test_task5_benchmark_delta_names_the_required_screenshot_evidence() -> None:
    text = _read_required(BENCHMARK_DELTA)

    for artifact in [
        "frontend/artifacts/visual/daily-open-desktop.png",
        "frontend/artifacts/visual/daily-open-mobile.png",
        "frontend/artifacts/visual/daily-open-focus-capture.png",
        "frontend/artifacts/visual/axe-report.json",
    ]:
        assert artifact in text

    assert "Dynasty Nerds" in text
    assert "rankings" in text.lower() or "analyzer" in text.lower()
    assert "benchmark screenshot" in text.lower()


def test_task5_benchmark_delta_records_named_defect_audit_and_preview_blocker() -> None:
    text = _read_required(BENCHMARK_DELTA)

    assert "Named defects remaining: None" in text
    assert "David preview status:" in text
    assert "commit blocked until david preview" in text.lower()
    assert "No fake PIT lines" in text
    assert "I2a code copied selectively, never merged wholesale" in text


def test_task5_benchmark_delta_tracks_the_daily_open_parity_rows() -> None:
    text = _read_required(BENCHMARK_DELTA)

    for parity_row in [
        "one title",
        "desk-header tape",
        "two-column desktop grid",
        "single-column mobile",
        "PlayerIdentity rows",
        "MetricCell signed deltas",
        "SeriesSlot pending",
        "right rail",
        "updated stamps",
        "zero-mover prose",
        "exact-zero neutral dash",
        "experimental grade declared plainly",
    ]:
        assert parity_row in text
