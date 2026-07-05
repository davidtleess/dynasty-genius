from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
PLAYWRIGHT_CONFIG = FRONTEND_ROOT / "playwright.config.ts"
VISUAL_SMOKE_SPEC = FRONTEND_ROOT / "e2e" / "visual-smoke.spec.ts"


def _read(path: Path) -> str:
    assert path.exists(), f"Missing required H2 browser-evidence file: {path}"
    return path.read_text(encoding="utf-8")


def _without_line_comments(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )


def test_h2_browser_gate_has_exact_pins_and_visual_smoke_script() -> None:
    package_json = json.loads((FRONTEND_ROOT / "package.json").read_text(encoding="utf-8"))

    dev_dependencies = package_json["devDependencies"]
    scripts = package_json["scripts"]

    assert dev_dependencies.get("@playwright/test") == "1.61.1"
    assert dev_dependencies.get("@axe-core/playwright") == "4.12.1"
    assert (
        scripts.get("visual:smoke")
        == "playwright test --config playwright.config.ts"
    )


def test_h2_browser_gate_config_stays_local_and_non_golden() -> None:
    config = _read(PLAYWRIGHT_CONFIG)
    config_without_comments = _without_line_comments(config)

    assert "visual-smoke.spec.ts" in config
    assert "webServer" in config
    assert "npm run build" in config
    assert "npm run preview" in config
    assert "testDir" in config
    assert "snapshotPathTemplate" not in config_without_comments
    assert "toHaveScreenshot" not in config_without_comments
    assert ".github" not in config, "Task 1 must not add a CI hard gate"


def test_h2_visual_smoke_captures_daily_open_evidence_without_goldens() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)
    spec_without_comments = _without_line_comments(spec)

    assert "page.route(" in spec, "Task 1 evidence must use route mocks"
    assert "/api/league/what-changed" in spec
    assert "/api/system/capture-health" in spec
    assert "/api/system/model-provenance" in spec
    assert "readFile" not in spec
    assert "existsSync" not in spec
    assert "toHaveScreenshot" not in spec_without_comments
    assert "toMatchSnapshot" not in spec_without_comments

    assert 'width: 1440' in spec
    assert 'height: 960' in spec
    assert 'daily-open-desktop.png' in spec
    assert 'width: 390' in spec
    assert 'height: 844' in spec
    assert 'daily-open-mobile.png' in spec
    assert "page.screenshot" in spec


def test_h2_visual_smoke_records_focus_capture_and_axe_main_smoke() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)

    assert "@axe-core/playwright" in spec
    assert "AxeBuilder" in spec
    assert '.include("main")' in spec or ".include('main')" in spec
    assert "violations" in spec
    assert "focus-capture" in spec
    assert "keyboard" in spec.lower() or "Tab" in spec
    assert "not a pass gate" in spec.lower() or "capture only" in spec.lower()
