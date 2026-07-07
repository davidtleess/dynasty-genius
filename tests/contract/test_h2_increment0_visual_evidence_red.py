from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMITIVE_DELTA = (
    REPO_ROOT / "docs" / "strategies" / "2026-07-06-h2-increment0-primitive-delta.md"
)


def _read_required(path: Path) -> str:
    assert path.exists(), f"Missing required Increment-0 evidence artifact: {path}"
    return path.read_text(encoding="utf-8")


def test_increment0_primitive_delta_records_evidence_and_visual_audit() -> None:
    text = _read_required(PRIMITIVE_DELTA)

    for section in [
        "# H2 Increment 0 Primitive Capture Delta",
        "DG evidence bundle",
        "Asset pipeline behavior",
        "Primitive extensions",
        "Hue candidate sheet",
        "Visual audit",
        "Axe result",
        "David preview gate",
    ]:
        assert section in text

    for artifact in [
        "frontend/artifacts/visual/asset-primitive-capture-desktop.png",
        "frontend/artifacts/visual/asset-primitive-capture-mobile.png",
        "frontend/artifacts/visual/asset-primitive-capture-focus.png",
        "frontend/artifacts/visual/asset-primitive-capture-axe-report.json",
    ]:
        assert artifact in text

    assert "Named defects remaining: None" in text
    assert "violation_count: 0" in text
    assert "commit blocked until david preview" in text.lower()
