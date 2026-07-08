from __future__ import annotations

from types import SimpleNamespace

import scripts.validate_governance as validate_governance


def test_governance_validator_requires_gemini_role_contract() -> None:
    """Gemini CLI must have a project-level role constraint in the governance gate."""
    assert "GEMINI.md" in validate_governance.REQUIRED_FILES
    assert "GEMINI.md" in validate_governance.BOOTSTRAP_FILES
    required_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["GEMINI.md"]
    assert "Product Vision owner and Product Manager" in required_phrases
    assert "shell is prompt-gated" in required_phrases
    assert "native file writes are prohibited by mandate" in required_phrases
    assert "Bootstrap is read-only" in required_phrases
    assert "must not run shell commands" not in required_phrases
    assert "must not modify tracked files" not in required_phrases


def test_governance_validator_requires_design_foundation_bootstrap_and_audit_contracts() -> None:
    assert "PRODUCT.md" in validate_governance.REQUIRED_FILES
    assert "DESIGN.md" in validate_governance.REQUIRED_FILES
    assert "docs/design-audits/README.md" in validate_governance.REQUIRED_FILES
    assert "docs/governance/04-strategic-execution-charter.md" in (
        validate_governance.REQUIRED_FILES
    )

    for target in [
        "docs/governance/00-product-constitution.md",
        "docs/governance/01-north-star-architecture.md",
        "docs/governance/02-agent-operating-loop.md",
        "docs/governance/03-code-hygiene-policy.md",
        "PRODUCT.md",
        "DESIGN.md",
        "AGENT_SYNC.md",
    ]:
        assert target in validate_governance.REQUIRED_BOOTSTRAP_TARGETS

    operating_loop_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES[
        "docs/governance/02-agent-operating-loop.md"
    ]
    assert "Contract-green is never a visual GREEN" in operating_loop_phrases
    assert "fresh-agent visual audit" in operating_loop_phrases
    assert "keep harness-local enablement local" in operating_loop_phrases

    product_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["PRODUCT.md"]
    assert "The scaffolding-hide law." in product_phrases
    assert "No system-nominated single-player hero" in product_phrases
    assert "Shape before code:" in product_phrases

    design_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["DESIGN.md"]
    assert "Shape before code (pre-build)." in design_phrases
    assert "The unanchored scored audit" in design_phrases
    assert "mid-scroll captures" in design_phrases


def test_governance_validator_rejects_tracked_local_hook_enablement(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        target = cmd[-1]
        return SimpleNamespace(returncode=0 if target == ".codex/hooks.json" else 1)

    monkeypatch.setattr(validate_governance.subprocess, "run", fake_run)

    failures: list[str] = []
    validate_governance.validate_local_only_paths(failures)

    assert len(failures) == 1
    assert ".codex/hooks.json" in failures[0]
    assert "local enablement" in failures[0]
