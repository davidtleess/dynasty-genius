import json
from pathlib import Path

PLAN = Path("resources/project_plan.json")
EXEC = Path("docs/agent-execution-plan.md")
STATUS = {"planned", "in_progress", "done", "blocked", "deferred"}

# Complete v1 macro set (F5): these macro phases MUST be present so the
# authoritative ledger can never ship partial. (Finer granularity is a later
# JSON content update, not a code change.)
REQUIRED_PHASE_IDS = {
    "phase-foundation",
    "phase-engine-a",
    "phase-engine-b",
    "phase-pvo",
    "phase-decision-surfaces",
    "phase-market-overlay",
}


def test_seed_conforms_to_schema_v1():
    data = json.loads(PLAN.read_text(encoding="utf-8"))
    assert data["schema_version"] == "project_plan.v1"
    assert isinstance(data["updated_at"], str) and data["updated_at"]
    assert isinstance(data["phases"], list) and data["phases"]
    phase_ids = set()
    for p in data["phases"]:
        assert {"id", "title", "status", "tasks"} <= p.keys()
        assert p["status"] in STATUS
        assert p["id"] not in phase_ids  # unique phase ids
        phase_ids.add(p["id"])
        task_ids = set()  # F3: task ids unique WITHIN each phase (not global)
        for t in p["tasks"]:
            assert {"id", "title", "status"} <= t.keys()
            assert t["status"] in STATUS
            assert t["id"] not in task_ids
            task_ids.add(t["id"])
    assert REQUIRED_PHASE_IDS <= phase_ids  # F5: no partial macro ledger


def test_execution_plan_retained_with_banner():
    text = EXEC.read_text(encoding="utf-8")
    assert len(text.splitlines()) > 100  # NOT retired/stubbed - full doc retained
    head = "\n".join(text.splitlines()[:8]).lower()
    assert "resources/project_plan.json" in head  # banner points to the JSON
    assert "deprecat" in head or "live status" in head
