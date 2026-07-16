"""Amendment E REDs for the ratified Gemini operations/telemetry re-role.

These contracts intentionally fail until the corresponding GREEN lands. Historical
ledger attribution remains a supported scanner input; it is not an active role label.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import scripts.validate_governance as validate_governance

ROOT = Path(__file__).resolve().parents[2]
NEW_ATTRIBUTION = "Gemini (Operations & Telemetry)"
HISTORICAL_ATTRIBUTION = "Gemini (Product Manager)"
FIXED_NOW = datetime(2026, 7, 16, 15, 0, tzinfo=ZoneInfo("America/New_York"))
E8_SKILL_PATH = ROOT / ".agents" / "skills" / "cockpit-messaging" / "SKILL.md"


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"amendment_e_{name}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_e1_ledger_writer_emits_new_ops_telemetry_attribution(tmp_path: Path) -> None:
    module = _load_script("gemini_ledger_append")

    written = module.append_gemini_ledger_entry(
        body="- Task: Telemetry report.",
        ledger_dir=tmp_path / "docs" / "agent-ledger",
        now=FIXED_NOW,
    )

    assert written.read_text(encoding="utf-8").startswith(
        f"## 15:00 ET - {NEW_ATTRIBUTION}\n\n"
    )


def test_e1_ledger_writer_has_no_active_product_manager_self_description() -> None:
    text = _read("scripts/gemini_ledger_append.py")

    assert NEW_ATTRIBUTION in text
    assert "Product Manager" not in text
    assert "Gemini (PM)" not in text


def test_e2_tripwire_flags_banned_phrase_under_new_header() -> None:
    module = _load_script("cockpit_hygiene_check")
    ledger = "\n".join(
        [
            "# Agent Ledger - 2026-07-16",
            "",
            f"## 15:00 ET - {NEW_ATTRIBUTION}",
            "- Governance CLEAR should be flagged.",
        ]
    )

    assert module.scan_gemini_ledger_violations(ledger) == [
        (4, "Governance CLEAR", "- Governance CLEAR should be flagged.")
    ]


def test_e2_tripwire_allows_clean_telemetry_under_new_header() -> None:
    module = _load_script("cockpit_hygiene_check")
    ledger = "\n".join(
        [
            "# Agent Ledger - 2026-07-16",
            "",
            f"## 15:00 ET - {NEW_ATTRIBUTION}",
            "- capture_status_latest is failed at app/data/status.json.",
            "- Observed at 2026-07-16T14:59:00-04:00.",
        ]
    )

    assert module.scan_gemini_ledger_violations(ledger) == []


def test_e2_tripwire_still_scans_historical_product_manager_header() -> None:
    module = _load_script("cockpit_hygiene_check")
    ledger = "\n".join(
        [
            "# Agent Ledger - 2026-07-15",
            "",
            f"## 10:00 ET - {HISTORICAL_ATTRIBUTION}",
            "- The loop is closed.",
        ]
    )

    assert module.scan_gemini_ledger_violations(ledger) == [
        (4, "the loop is closed", "- The loop is closed.")
    ]


def test_e2_hygiene_module_retires_source_verification_clear_instruction() -> None:
    text = _read("scripts/cockpit_hygiene_check.py")

    assert "source-verification CLEAR" not in text


def test_e3_validator_pins_ops_telemetry_role_in_operating_loop() -> None:
    required = validate_governance.REQUIRED_GOVERNANCE_PHRASES[
        "docs/governance/02-agent-operating-loop.md"
    ]

    assert any("Operations & Telemetry" in phrase for phrase in required)


def test_e4_connector_has_no_live_product_manager_role_labels() -> None:
    text = _read("scripts/claude_code_connector.py")

    assert NEW_ATTRIBUTION in text
    assert "Gemini - Product Manager" not in text
    assert "Gemini (Product Manager)" not in text
    assert "Strategy oversight" not in text


def test_e5_closeout_reminder_routes_judgment_to_binding_lanes() -> None:
    module = _load_script("verify_sprint_closeout")
    detail = module.remind_checklist().detail

    assert "independent reviewer" in detail
    assert "Gemini" in detail
    assert "awareness" in detail
    assert "Codex + Gemini" not in detail
    assert "both reviewers" not in detail


def test_e6_prospect_checklist_assigns_enforcement_to_binding_lanes() -> None:
    text = _read("docs/governance/prospect_verification_checklist.md")
    live_pm_row = "| **Gemini (PM)** |"

    assert live_pm_row not in text
    assert "binding lane" in text.lower()


def test_e7_live_dg_pm_skills_use_amended_framing_and_routing() -> None:
    synthesize = _read(
        "tools/dg-pm-plugin/dg-pm/skills/synthesize-research/SKILL.md"
    )
    write_spec = _read("tools/dg-pm-plugin/dg-pm/skills/write-spec/SKILL.md")
    roadmap = _read("tools/dg-pm-plugin/dg-pm/skills/roadmap-update/SKILL.md")
    david_update = _read("tools/dg-pm-plugin/dg-pm/skills/david-update/SKILL.md")

    assert "Gemini product-edge lane" not in synthesize
    assert "operations" in synthesize.lower()
    assert "telemetry" in synthesize.lower()

    assert "Gemini advisory" not in write_spec
    assert "Claude authors the framing" in write_spec
    assert "Codex" in write_spec and "challenge" in write_spec.lower()
    assert "written disposition" in write_spec

    assert "Gemini frames" not in roadmap
    assert "binding lanes" in roadmap
    assert "telemetry" in roadmap.lower()

    assert "back to Codex/Gemini" not in david_update
    assert "binding lanes" in david_update
    assert "Gemini" in david_update and "awareness" in david_update.lower()


def test_e7_plugin_wide_live_instructions_have_no_retired_gemini_routing() -> None:
    skills_root = ROOT / "tools" / "dg-pm-plugin" / "dg-pm" / "skills"
    live_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(skills_root.glob("*/SKILL.md"))
    )

    for retired_instruction in (
        "Gemini frames",
        "Gemini advisory",
        "Gemini product-edge lane",
        "back to Codex/Gemini",
    ):
        assert retired_instruction not in live_text


@pytest.mark.skipif(
    not E8_SKILL_PATH.is_file(),
    reason="E8 cockpit-messaging skill is local-by-law and absent in a fresh clone",
)
def test_e8_local_cockpit_skill_encodes_binding_routes_and_awareness_exception() -> None:
    text = _read(".agents/skills/cockpit-messaging/SKILL.md")

    assert "both active cockpit agents" not in text
    assert "binding lanes" in text
    assert "awareness copy" in text.lower()
    assert "no reply requested" in text.lower()

