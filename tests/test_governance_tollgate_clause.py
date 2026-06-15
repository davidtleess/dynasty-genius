from pathlib import Path

DOC = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "governance"
    / "02-agent-operating-loop.md"
)


def test_tollgate_clause_present_and_references_verifier():
    text = DOC.read_text(encoding="utf-8")

    assert "Sprint-closeout tollgate" in text
    assert "scripts/verify_sprint_closeout.py" in text
    assert "ENFORCE" in text
    assert "full suite" in text


def test_tollgate_clause_scopes_state_documentation_exemption():
    text = DOC.read_text(encoding="utf-8")

    assert (
        "This tollgate applies before declaring any build/phase complete and before "
        "pushing any code, test, configuration, or model-artifact change."
    ) in text
    assert (
        "Routine state-documentation pushes that alter neither execution surfaces "
        "nor governance/spec/plan contracts"
    ) in text
    assert "AGENT_SYNC.md state updates" in text
    assert "daily-ledger appends" in text
    assert "are exempt" in text
