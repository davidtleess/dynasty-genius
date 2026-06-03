from __future__ import annotations

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
