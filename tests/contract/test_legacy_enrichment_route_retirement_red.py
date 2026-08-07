"""RED: retire the legacy mixed CFBD/PlayerProfiler enrichment route.

The governed PlayerProfiler adapter consumes David's manual subscriber exports.
The governed CFBD acquisition route is ``run_cfbd_foundation_refresh.py``.  The
legacy ``enrich_training_data.py`` script bypasses both boundaries: it contains a
second PlayerProfiler HTTP client and a direct CFBD client, then writes the
historical ``prospects_with_outcomes_v2.csv`` artifact.

These tests pin retirement rather than a partial class deletion.  The leakage
guard survives in a neutral, network-free module; historical review prose may
continue to name the retired script, but executable tests must stop instructing
users to run it.

RED owner: Codex, independent reviewing lane.  Claude owns GREEN.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGACY_SCRIPT = ROOT / "scripts" / "enrich_training_data.py"
LEAKAGE_MODULE = ROOT / "src" / "dynasty_genius" / "models" / "leakage.py"
CFBD_ENTRYPOINT = ROOT / "scripts" / "run_cfbd_foundation_refresh.py"
PLAYERPROFILER_ENTRYPOINT = ROOT / "scripts" / "run_playerprofiler_ingest.py"
THIS_TEST = Path(__file__).resolve()

LEGACY_REFERENCE = "scripts/" + "enrich_training_data.py"
PLAYERPROFILER_HOST = "playerprofiler.com"
PLAYERPROFILER_AJAX_PATH = "wp-admin/admin-ajax.php"
NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "httpx",
    "playwright",
    "requests",
    "selenium",
    "urllib",
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _string_constants(path: Path) -> list[str]:
    return [
        node.value
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _load_leakage_module():
    assert LEAKAGE_MODULE.exists(), (
        "Move check_leakage out of the retired acquisition script into "
        "src/dynasty_genius/models/leakage.py"
    )
    spec = importlib.util.spec_from_file_location("dg_governed_leakage", LEAKAGE_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_red_legacy_mixed_acquisition_entrypoint_is_retired() -> None:
    """A fail-closed shim is insufficient: it preserves a bypassable second adapter."""
    assert not LEGACY_SCRIPT.exists(), (
        "Retire scripts/enrich_training_data.py after extracting check_leakage. "
        "Do not leave a second PlayerProfiler/CFBD acquisition entrypoint."
    )


def test_red_no_executable_script_contains_playerprofiler_http_route() -> None:
    """Historical prose may retain the URL; executable scripts may not."""
    offenders: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        strings = _string_constants(path)
        if any(
            PLAYERPROFILER_HOST in value or PLAYERPROFILER_AJAX_PATH in value
            for value in strings
        ):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == [], (
        "Executable PlayerProfiler HTTP acquisition remains; the governed route "
        f"is manual subscriber export ingestion. offenders={offenders}"
    )


def test_red_leakage_guard_moves_to_network_free_governed_module() -> None:
    """Importing the leakage guard must not import provider/network machinery."""
    assert LEAKAGE_MODULE.exists(), (
        "Create src/dynasty_genius/models/leakage.py before retiring the legacy script"
    )
    forbidden = sorted(_import_roots(LEAKAGE_MODULE) & NETWORK_IMPORT_ROOTS)
    assert forbidden == [], f"leakage guard imports network clients: {forbidden}"

    strings = _string_constants(LEAKAGE_MODULE)
    route_strings = sorted(
        value
        for value in strings
        if PLAYERPROFILER_HOST in value or PLAYERPROFILER_AJAX_PATH in value
    )
    assert route_strings == [], "leakage guard must carry no provider route"


def test_red_extracted_leakage_guard_preserves_fail_closed_behavior(tmp_path: Path) -> None:
    """Extraction must preserve the guard and make its report destination explicit."""
    module = _load_leakage_module()
    check_leakage = module.check_leakage

    clean_report = tmp_path / "clean.json"
    check_leakage(
        pd.DataFrame({"gsis_id": ["1"], "dominator_rating": [0.3]}),
        report_path=clean_report,
    )
    assert not clean_report.exists()

    violation_report = tmp_path / "violation.json"
    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        check_leakage(
            pd.DataFrame({"gsis_id": ["1"], "ktc_value": [1000]}),
            report_path=violation_report,
        )
    assert violation_report.exists(), "a refusal must leave a durable diagnostic"


def test_red_tests_no_longer_instruct_or_import_legacy_entrypoint() -> None:
    """A retired command cannot remain the documented way to satisfy a test gate."""
    offenders: list[str] = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        if path.resolve() == THIS_TEST:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if LEGACY_REFERENCE in line or "scripts.enrich_training_data" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert offenders == [], (
        "Tests still import or tell users to run the retired acquisition script; "
        f"offenders={offenders}"
    )


def test_red_no_script_combines_playerprofiler_http_with_v2_publication() -> None:
    """A removal must not degrade into a false v2 producer with hidden live reads."""
    offenders: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        has_playerprofiler_network = (
            PLAYERPROFILER_HOST in text or PLAYERPROFILER_AJAX_PATH in text
        )
        if has_playerprofiler_network and "prospects_with_outcomes_v2.csv" in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == [], (
        "No script may combine an unsanctioned PlayerProfiler HTTP route with "
        f"v2 artifact publication. offenders={offenders}"
    )


def test_positive_governed_source_entrypoints_remain_present() -> None:
    """Retirement must preserve both current governed source boundaries."""
    assert CFBD_ENTRYPOINT.exists()
    assert PLAYERPROFILER_ENTRYPOINT.exists()

    cfbd_text = CFBD_ENTRYPOINT.read_text(encoding="utf-8")
    assert "src.dynasty_genius.capture.cfbd_foundation_refresh" in cfbd_text
    assert "DEFAULT_SOURCE_ROOT" in cfbd_text
    assert '"cfbd_foundation"' in cfbd_text

    assert not (_import_roots(PLAYERPROFILER_ENTRYPOINT) & NETWORK_IMPORT_ROOTS)
