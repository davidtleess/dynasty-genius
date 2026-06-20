import json

from app.services.project_plan_loader import load_project_plan


def _write(tmp_path, obj):
    p = tmp_path / "project_plan.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


VALID = {
    "schema_version": "project_plan.v1",
    "updated_at": "2026-06-19",
    "phases": [
        {
            "id": "p1",
            "title": "Phase 1",
            "status": "done",
            "tasks": [
                {"id": "t1", "title": "Task 1", "status": "done"},
                {
                    "id": "t2",
                    "title": "Task 2",
                    "status": "planned",
                    "note": "n",
                },
            ],
        },
    ],
}


def test_valid_file_ok(tmp_path):
    r = load_project_plan(_write(tmp_path, VALID))
    assert r.status == "ok" and r.warnings == []
    assert r.phases[0].id == "p1" and len(r.phases[0].tasks) == 2
    assert r.phases[0].tasks[1].note == "n"


def test_missing_file_degrades(tmp_path):
    r = load_project_plan(tmp_path / "nope.json")
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_source_missing" in r.warnings


def test_malformed_json_degrades(tmp_path):
    p = tmp_path / "project_plan.json"
    p.write_text("{not json", encoding="utf-8")
    r = load_project_plan(p)
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_malformed_json" in r.warnings


def test_unsupported_schema_version_degrades(tmp_path):
    r = load_project_plan(_write(tmp_path, {**VALID, "schema_version": "project_plan.v2"}))
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_schema_version_unsupported" in r.warnings
    assert r.schema_version is None  # bad actual value not surfaced


def test_missing_root_field_degrades(tmp_path):
    bad = {"schema_version": "project_plan.v1", "phases": []}  # no updated_at
    r = load_project_plan(_write(tmp_path, bad))
    assert r.status == "degraded"
    assert "project_plan_missing_root_field:updated_at" in r.warnings


def test_duplicate_phase_id_degrades(tmp_path):
    dup = {**VALID, "phases": [VALID["phases"][0], {**VALID["phases"][0]}]}
    r = load_project_plan(_write(tmp_path, dup))
    assert r.status == "degraded" and r.phases == []
    assert any(w.startswith("project_plan_duplicate_id:") for w in r.warnings)


def test_invalid_phase_status_drops_phase(tmp_path):
    obj = {
        **VALID,
        "phases": [
            VALID["phases"][0],
            {"id": "pbad", "title": "Bad", "status": "shipping", "tasks": []},
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [p.id for p in r.phases] == ["p1"]  # valid phase kept, bad dropped
    assert "project_plan_phase_invalid:pbad" in r.warnings


def test_invalid_task_drops_task(tmp_path):
    obj = {
        "schema_version": "project_plan.v1",
        "updated_at": "x",
        "phases": [
            {
                "id": "p1",
                "title": "P",
                "status": "done",
                "tasks": [
                    {"id": "t1", "title": "ok", "status": "done"},
                    {"id": "t2", "title": "bad", "status": "nope"},
                ],
            }
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert "project_plan_task_invalid:p1/t2" in r.warnings


def test_duplicate_task_id_degrades(tmp_path):
    obj = {
        "schema_version": "project_plan.v1",
        "updated_at": "x",
        "phases": [
            {
                "id": "p1",
                "title": "P",
                "status": "done",
                "tasks": [
                    {"id": "dup", "title": "a", "status": "done"},
                    {"id": "dup", "title": "b", "status": "done"},
                ],
            }
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_duplicate_id:dup" in r.warnings


def test_missing_root_phases_degrades(tmp_path):
    r = load_project_plan(
        _write(tmp_path, {"schema_version": "project_plan.v1", "updated_at": "x"})
    )
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_missing_root_field:phases" in r.warnings


def test_phase_missing_required_field_drops_phase(tmp_path):
    obj = {
        **VALID,
        "phases": [
            VALID["phases"][0],
            {"id": "p2", "status": "done", "tasks": []},
        ],
    }  # missing title
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [p.id for p in r.phases] == ["p1"]
    assert "project_plan_phase_invalid:p2" in r.warnings


def test_task_missing_required_field_drops_task(tmp_path):
    obj = {
        "schema_version": "project_plan.v1",
        "updated_at": "x",
        "phases": [
            {
                "id": "p1",
                "title": "P",
                "status": "done",
                "tasks": [
                    {"id": "t1", "title": "ok", "status": "done"},
                    {"id": "t2", "status": "done"},
                ],
            }
        ],
    }  # task missing title
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert "project_plan_task_invalid:p1/t2" in r.warnings


def test_two_missing_id_phases_drop_not_whole_degrade(tmp_path):
    # F2 regression guard: missing ids DROP per-record, not duplicate-None degrade.
    obj = {
        **VALID,
        "phases": [
            VALID["phases"][0],
            {"title": "no id A", "status": "done", "tasks": []},
            {"title": "no id B", "status": "done", "tasks": []},
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert [p.id for p in r.phases] == ["p1"]  # valid phase kept
    assert not any(w.startswith("project_plan_duplicate_id") for w in r.warnings)
    assert sum(w.startswith("project_plan_phase_invalid") for w in r.warnings) == 2


def test_empty_phase_id_drops_phase(tmp_path):
    # F-new-2: empty-string id is not valid required text -> drop, not degrade.
    obj = {
        **VALID,
        "phases": [
            VALID["phases"][0],
            {"id": "", "title": "empty id", "status": "done", "tasks": []},
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert [p.id for p in r.phases] == ["p1"]
    assert not any(w.startswith("project_plan_duplicate_id") for w in r.warnings)
    assert any(w.startswith("project_plan_phase_invalid") for w in r.warnings)


def test_empty_task_id_drops_task(tmp_path):
    obj = {
        "schema_version": "project_plan.v1",
        "updated_at": "x",
        "phases": [
            {
                "id": "p1",
                "title": "P",
                "status": "done",
                "tasks": [
                    {"id": "t1", "title": "ok", "status": "done"},
                    {"id": "", "title": "empty id", "status": "done"},
                ],
            }
        ],
    }
    r = load_project_plan(_write(tmp_path, obj))
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert any(w.startswith("project_plan_task_invalid:p1/") for w in r.warnings)
