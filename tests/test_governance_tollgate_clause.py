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
