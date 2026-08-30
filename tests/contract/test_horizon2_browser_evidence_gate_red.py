"""The land-time contract on the browser evidence gate.

WHY THIS FILE MATTERS MORE THAN IT LOOKS. ``dg-land.sh``'s entire gate is
``pytest -q`` at the repo root. Vitest and Playwright do not run there. So this
file is the ONLY automatic check on ``frontend/e2e/visual-smoke.spec.ts`` that
stands between a weakened browser gate and ``main``, and its pins have to be the
load-bearing ones rather than incidental string matches.

DG-118 rewrote that spec from three visited URLs to every view of every
destination, and these pins were rewritten with it. The four that broke were all
literals the H2 gate happened to spell one way — ``daily-open-desktop.png``
before screenshot paths were composed from parts, ``.include("main")`` before
axe was widened from ``<main>`` to the whole page, and a blanket ``"readFile"
not in spec`` that was reaching for "must not read product data off disk" and
caught ``readFileSync`` of the frontend's own frozen fixtures instead. Each is
re-expressed below as the property it was actually protecting, so a real
weakening still fails and a legitimate widening does not.

The rule for editing this file: pin BEHAVIOUR the gate must keep, never the
spelling of a filename. If a pin here fails, first ask whether coverage went UP.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
PLAYWRIGHT_CONFIG = FRONTEND_ROOT / "playwright.config.ts"
VISUAL_SMOKE_SPEC = FRONTEND_ROOT / "e2e" / "visual-smoke.spec.ts"
DESTINATIONS = FRONTEND_ROOT / "src" / "shell" / "destinations.ts"
COVERAGE_LOCK = FRONTEND_ROOT / "src" / "styles" / "visualSmokeContract.test.js"
FIXTURE_DIR = FRONTEND_ROOT / "src" / "lib" / "__fixtures__"
FIXTURE_SCHEMAS = FIXTURE_DIR / "liveFixtureSchemas.ts"


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

    # DG-118: the gate must grade a bundle it built itself. Reusing whatever
    # happens to be listening on 4173 means the receipt names a bundle nobody
    # can identify.
    assert "reuseExistingServer: false" in config_without_comments


def test_h2_visual_smoke_captures_daily_open_evidence_without_goldens() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)
    spec_without_comments = _without_line_comments(spec)

    assert "page.route(" in spec, "Task 1 evidence must use route mocks"
    assert "/api/league/what-changed" in spec
    assert "/api/system/capture-health" in spec
    assert "/api/system/model-provenance" in spec

    # The original pin here was `"readFile" not in spec`, which was reaching for
    # "the gate must not read the product's data off disk" and is now expressed
    # as exactly that. Reading the frontend's own frozen fixtures IS the design.
    assert "app/data" not in spec
    assert "__fixtures__" in spec_without_comments

    assert "toHaveScreenshot" not in spec_without_comments
    assert "toMatchSnapshot" not in spec_without_comments

    assert "width: 1440" in spec
    assert "height: 960" in spec
    assert "width: 390" in spec
    assert "height: 844" in spec
    assert "page.screenshot" in spec

    # Screenshot paths are composed from `${artifacts}-${label}`, so the parts
    # are pinned rather than the assembled filenames the H2 spec spelled out.
    assert 'artifacts: "daily-open"' in spec_without_comments
    assert "-mid-scroll.png" in spec
    assert "fullPage: true" in spec_without_comments


def test_h2_visual_smoke_captures_asset_primitive_page_in_same_contract() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)
    spec_without_comments = _without_line_comments(spec)

    assert "asset-primitive-capture" in spec
    assert "Asset primitive capture" in spec
    assert 'artifacts: "asset-primitive-capture"' in spec_without_comments
    assert 'artifact: "asset-primitive-capture-focus"' in spec_without_comments
    assert "app/data/assets" not in spec
    assert "headshot_manifest.json" not in spec
    assert "toHaveScreenshot" not in spec_without_comments
    assert "toMatchSnapshot" not in spec_without_comments


def test_h2_visual_smoke_records_focus_capture_and_axe_page_wide() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)
    spec_without_comments = _without_line_comments(spec)

    assert "@axe-core/playwright" in spec
    assert "AxeBuilder" in spec
    assert "results.violations" in spec_without_comments

    # COVERAGE MAY GO UP, NEVER BACK DOWN. The H2 gate scanned `.include("main")`
    # and left the rail, the header and the phone's bottom tab bar outside axe
    # entirely. DG-118 scans the whole page; narrowing it again — by any of
    # axe's three scoping or rule-selection APIs — fails here.
    assert "new AxeBuilder({ page }).analyze()" in spec_without_comments
    assert ".include(" not in spec_without_comments
    assert not re.search(r"disableRules\(|withRules\(|\.exclude\(", spec_without_comments)
    assert 'exercisedRules.has("color-contrast")' in spec_without_comments

    assert "daily-open-primitive-focus-capture" in spec
    assert 'getByRole("button", { name: /provenance for/i })' in spec
    assert "toBeFocused()" in spec


def test_h2_every_gated_surface_asserts_axe_zero_and_writes_a_receipt() -> None:
    spec = _read(VISUAL_SMOKE_SPEC)
    spec_without_comments = _without_line_comments(spec)

    # One axe run per surface per width per motion path, each writing its own
    # receipt, each asserting an empty violation list.
    assert "-axe.json" in spec
    assert "-axe-default-motion.json" in spec
    assert "writeFileSync(" in spec_without_comments
    assert "violation_count" in spec
    assert "contrast_readings" in spec
    assert "incomplete_by_reason" in spec, (
        "zero violations with an unexplained pile of undecided nodes is a "
        "receipt with a hole in it; the counts must be recorded"
    )
    assert "runAxe(page, spec" in spec_without_comments


def test_h2_visual_smoke_gates_every_nav_destination() -> None:
    """The coverage lock, run in the suite that actually gates a land.

    The jsdom twin in `visualSmokeContract.test.js` says the same thing in three
    seconds during development. This one is what stops an ungated destination
    reaching main, because vitest does not run in `dg-land.sh`.
    """
    spec_without_comments = _without_line_comments(_read(VISUAL_SMOKE_SPEC))
    destinations_without_comments = _without_line_comments(_read(DESTINATIONS))

    # Five destinations, eight views. The floor is a guard against the regex
    # silently matching nothing after a refactor, which would make everything
    # below pass vacuously — the false receipt, one level up.
    surfaces = re.findall(r'surface:\s*"([^"]+)"', destinations_without_comments)
    assert len(surfaces) >= 8, (
        "found almost no destinations — this check would pass vacuously: "
        f"{surfaces}"
    )

    ungated = [
        surface
        for surface in sorted(set(surfaces))
        if f'surface: "{surface}"' not in spec_without_comments
    ]
    assert ungated == [], (
        "these nav destinations are reachable by David and the browser gate "
        f"never visits them: {ungated}"
    )

    # The jsdom lock is the fast half of the same pair; it may not be deleted.
    coverage_lock = _read(COVERAGE_LOCK)
    assert "DESTINATIONS" in coverage_lock
    assert "gates every view of every nav destination" in coverage_lock


def test_h2_every_live_fixture_is_pinned_to_a_generated_schema() -> None:
    """The fixture-rot lock.

    A frozen fixture that falls out of the generated schema does NOT reliably
    fail the browser gate: on a secondary read (capture-health on the front
    page) the parse failure rewrites one sentence, renders no error card, drops
    no rows and pushes main's text length UP, so every assertion stays green
    while the product says something different. That is why the guard lives at
    the fixture. Zod cannot run here, but "a fixture nobody pinned" can, and
    that is the way the hole reopens.
    """
    schema_map = _read(FIXTURE_SCHEMAS)
    fixtures = sorted(path.name for path in FIXTURE_DIR.glob("*.live.json"))

    assert len(fixtures) >= 12, f"fixtures went missing: {fixtures}"
    unpinned = [name for name in fixtures if f'"{name}"' not in schema_map]
    assert unpinned == [], (
        "these captured fixtures are pinned to no schema and can rot silently: "
        f"{unpinned}"
    )

    spec_without_comments = _without_line_comments(_read(VISUAL_SMOKE_SPEC))
    assert "parseLiveFixture" in spec_without_comments, (
        "the browser gate must parse its fixtures against the generated schemas "
        "at module load"
    )
