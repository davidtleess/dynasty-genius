from __future__ import annotations

from types import SimpleNamespace

import scripts.validate_governance as validate_governance


def test_governance_validator_requires_gemini_role_contract() -> None:
    """Gemini CLI must have a project-level role constraint in the governance gate."""
    assert "GEMINI.md" in validate_governance.REQUIRED_FILES
    assert "GEMINI.md" in validate_governance.BOOTSTRAP_FILES
    required_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["GEMINI.md"]
    # Re-role amendment E3 (David-ratified 2026-07-16): the pinned identity is the
    # Operations & Telemetry charter, not the retired Product-Manager mandate.
    assert "Operations & Telemetry agent" in required_phrases
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
        "docs/governance/05-layer-doctrine.md",
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
    assert "material visual-direction change" in operating_loop_phrases

    product_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["PRODUCT.md"]
    assert "The scaffolding-hide law." in product_phrases
    assert "No system-nominated single-player hero" in product_phrases
    assert "Shape before code:" in product_phrases

    design_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES["DESIGN.md"]
    assert "Shape before code (pre-build)." in design_phrases
    assert "The unanchored scored audit" in design_phrases
    assert "mid-scroll captures" in design_phrases


def test_governance_validator_enforces_layer_doctrine() -> None:
    """Every bootstrap file must point at 05 and carry its pending boundary.

    The every-session read requirement is agent-authored and PENDING David's
    ratification; this test pins the pointer and the boundary, NOT the read as law.

    Regression guard for the 2026-07-28 gap: the validator PASSED while no bootstrap
    file mentioned 05 at all. A passing gate that does not know a required file
    exists is adverse evidence, not assurance.
    """
    assert "docs/governance/05-layer-doctrine.md" in validate_governance.REQUIRED_FILES
    assert (
        "docs/governance/05-layer-doctrine.md"
        in validate_governance.REQUIRED_BOOTSTRAP_TARGETS
    )

    doctrine_phrases = validate_governance.REQUIRED_GOVERNANCE_PHRASES[
        "docs/governance/05-layer-doctrine.md"
    ]
    # David's verbatim ruling — the load-bearing sentence of the doctrine.
    assert "if we don't have this our app WILL NOT WORK" in doctrine_phrases
    # The attribution split. v1.0.0 attributed the whole file to David, which was false;
    # pinning it makes that regression mechanical rather than a matter of reviewer memory.
    assert "§2 onward is agent-authored codification" in doctrine_phrases
    # The central pending-activation markers.
    assert "authority_section_2_onward: PENDING" in doctrine_phrases
    assert (
        "pending_activation:"
        in validate_governance.REQUIRED_GOVERNANCE_PHRASES[
            "docs/governance/02-agent-operating-loop.md"
        ]
    )


def test_bootstrap_files_must_mark_the_pending_ritual_pending() -> None:
    """First-contact surfaces must not command unratified rules as law.

    Regression guard for the 2026-07-28 authority-leak family, which recurred five
    times. The central 05/02 pins CANNOT catch this: strip the activation status from
    a bootstrap pointer and it still names the 05 path, so the target check passes
    while an agent reads an agent-authored ritual as binding on first contact.

    05 §1 is David's words and stands on his authority. The every-session READ
    requirement and the ritual obligations are both agent-authored and stay pending
    until he ratifies them.
    """
    assert "PENDING DAVID'S RATIFICATION" in validate_governance.REQUIRED_BOOTSTRAP_PHRASES
    assert "NOT YET BINDING" in validate_governance.REQUIRED_BOOTSTRAP_PHRASES

    for file_name in validate_governance.BOOTSTRAP_FILES:
        path = validate_governance.ROOT / file_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in validate_governance.REQUIRED_BOOTSTRAP_PHRASES:
            assert phrase in text, f"{file_name} is missing the pending marker {phrase!r}"



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
