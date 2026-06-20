# Live Project Tracker v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. In this project the build runs as the cockpit TDD cycle: **Codex authors the RED test → Claude implements GREEN → Codex (technical) + Gemini (governance) dual-CLEAR → David-authorized commit → zero-divergence audit.**

**Goal:** A read-only, single-pane-of-glass Project Tracker surface in the AppShell that renders the macro roadmap (phases → tasks + status) from a structured `resources/project_plan.json`, fail-closed.

**Architecture:** A structured JSON status ledger (`resources/project_plan.json`) is the authoritative source. A pure Python loader validates it through an explicit two-stage pipeline (root/integrity → whole-degrade; per-record → drop+warn) and returns a typed DTO. An internal FastAPI endpoint (`GET /api/internal/project-plan`, `include_in_schema=False`) serves it; a React `ProjectTracker` AppShell surface consumes it via manual `fetch` + local Zod. Internal dev-tooling — NOT a dynasty decision surface.

**Tech Stack:** Python 3.14 + FastAPI + Pydantic + stdlib `json`; Vite + React + TS; Vitest + @testing-library/react; local Zod (no generated client). No new runtime dependencies.

**Revision:** v3 — integrates Codex plan-review findings. v2: F1 (matrix-row RED tests: dup-task-id, missing-root-phases, missing-phase-field, missing-task-field), F2 (dup-id considers only present string ids; missing-id = per-record drop), F3 (task-id uniqueness within-phase across T1/T2/spec), F4 (Zod enforces status enum), F5 (complete v1 macro seed + REQUIRED_PHASE_IDS guard). v3: F-new-1 (remove unused test imports → no F401 at pre-commit), F-new-2 (`_text` helper requires non-empty-string id/title; empty/non-string id or title → per-record DROP, + empty-id drop tests), F-new-3 (DTO `status` typed to `PlanStatus` Literal, matching the Zod enum).

## Global Constraints

- **Internal dev-tooling**, not a dynasty decision surface: NO `decision_supported`, NO Engine/model/market logic, NO dynasty-decision framing. Exempt from decision-surface gates.
- **No new runtime dependencies.** Backend = stdlib `json` + Pydantic. Frontend = AppShell `activeSurface` (NO react-router) + local Zod.
- **`include_in_schema=False`** on the endpoint → must NOT change `frontend/openapi.json`; the OpenAPI drift guard (`tests/contract/test_openapi_drift_contract.py`) stays green untouched.
- **Path B (non-destructive):** `resources/project_plan.json` is authoritative for phase/task STATUS; `docs/agent-execution-plan.md` is RETAINED with a deprecation banner (no migration, no retirement); `AGENT_SYNC.md` stays the micro narrative.
- **Fail-closed:** fixed single allowlisted source path; no request-supplied paths; all failure modes → HTTP 200 `status="degraded"` + warnings (never 5xx, never a misleading empty `"ok"`).
- **Status enum (exact tokens):** `planned | in_progress | done | blocked | deferred`.
- **Schema version:** supported `== "project_plan.v1"` only.
- **Validation matrix (spec §3.2):** malformed JSON / missing-or-unsupported `schema_version` / missing root field / duplicate id → **whole-degrade** (`phases=[]`). Invalid phase (missing field or bad status) → **drop phase**. Invalid task (missing field or bad status) → **drop task**. Valid remainder always renders.

---

### Task 1: Structured substrate — seed JSON + non-destructive banner

**Files:**
- Create: `resources/project_plan.json`
- Modify: `docs/agent-execution-plan.md` (top-of-file deprecation banner only)
- Test: `tests/contract/test_project_plan_substrate.py`

**Interfaces:**
- Produces: `resources/project_plan.json` conforming to `project_plan.v1` (consumed by Task 2/3). Schema: `{schema_version, updated_at, doctrine_version, phases:[{id,title,status,summary?,tasks:[{id,title,status,note?}]}]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/contract/test_project_plan_substrate.py
import json
from pathlib import Path

PLAN = Path("resources/project_plan.json")
EXEC = Path("docs/agent-execution-plan.md")
STATUS = {"planned", "in_progress", "done", "blocked", "deferred"}

# Complete v1 macro set (F5): these macro phases MUST be present so the
# authoritative ledger can never ship partial. (Finer granularity is a later
# JSON content update, not a code change.)
REQUIRED_PHASE_IDS = {
    "phase-foundation", "phase-engine-a", "phase-engine-b", "phase-pvo",
    "phase-decision-surfaces", "phase-market-overlay",
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
    assert len(text.splitlines()) > 100  # NOT retired/stubbed — full doc retained
    head = "\n".join(text.splitlines()[:8]).lower()
    assert "resources/project_plan.json" in head  # banner points to the JSON
    assert "deprecat" in head or "live status" in head
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_project_plan_substrate.py -v`
Expected: FAIL (`resources/project_plan.json` does not exist).

- [ ] **Step 3: Create the seed file + banner**

Create `resources/project_plan.json` — the **complete v1 macro set** below (NOT a starter to extend). It is a curated *macro* roadmap (6 top-level phases covering the product's arc); the fine-grained detail stays in the RETAINED `agent-execution-plan.md` (Path B). The T1 test's `REQUIRED_PHASE_IDS` guards exactly these 6 ids so the ledger can never ship partial. Status is curated from AGENT_SYNC reality; ids are kebab-case + unique; statuses from the enum. (Adding finer phases later is a JSON content update, no code change.) Write the file exactly:

```json
{
  "schema_version": "project_plan.v1",
  "updated_at": "2026-06-19",
  "doctrine_version": "1.0.0",
  "phases": [
    { "id": "phase-foundation", "title": "Foundation, Governance & League Context", "status": "done", "summary": "Safety, governance docs, league context, identity resolution.", "tasks": [
      { "id": "fnd-governance", "title": "Governance doctrine (00-03)", "status": "done" },
      { "id": "fnd-identity", "title": "Identity resolution layer", "status": "done" } ] },
    { "id": "phase-engine-a", "title": "Engine A — Rookie Forecast", "status": "done", "summary": "Bifurcated rookie forecast (v3).", "tasks": [
      { "id": "ea-v3", "title": "Engine A v3 (W1-W5)", "status": "done", "note": "Phase 19" } ] },
    { "id": "phase-engine-b", "title": "Engine B — Active Player Forecast", "status": "done", "summary": "Position-stratified active-player models.", "tasks": [
      { "id": "eb-v2", "title": "Engine B v2 (QB/RB/WR/TE)", "status": "done" } ] },
    { "id": "phase-pvo", "title": "Unified Player Value Object", "status": "done", "summary": "DVS normalization, xVAR, PVO assembly.", "tasks": [
      { "id": "pvo-dvs", "title": "DVS normalization + bridge", "status": "done", "note": "Phase 14" },
      { "id": "pvo-xvar", "title": "xVAR cross-positional valuation", "status": "done", "note": "Phase 15" } ] },
    { "id": "phase-decision-surfaces", "title": "Phase 12 — Decision Surfaces (Frontend)", "status": "in_progress", "summary": "Read-only surfaces over the typed contract.", "tasks": [
      { "id": "ds-rookie-board", "title": "Rookie Board (standalone)", "status": "done" },
      { "id": "ds-trade-lab", "title": "Trade Lab surface", "status": "done", "note": "PR #59" },
      { "id": "ds-trust-console", "title": "Model Trust Console", "status": "done", "note": "PR #61" },
      { "id": "ds-roster-audit-inc1", "title": "Roster Audit Inc1 (backend contract)", "status": "done", "note": "PR #65" },
      { "id": "ds-roster-audit-inc2", "title": "Roster Audit Inc2 (read-only UI)", "status": "done", "note": "PR #66" },
      { "id": "ds-roster-audit-inc3a", "title": "Roster Audit Inc3 Task A (sort/filter/group)", "status": "done", "note": "PR #67" },
      { "id": "ds-roster-audit-inc3b", "title": "Roster Audit Inc3 Task B (decision-framed grouping)", "status": "planned" },
      { "id": "ds-project-tracker", "title": "Project Tracker v1 (internal tooling)", "status": "in_progress" } ] },
    { "id": "phase-market-overlay", "title": "Market Overlay & Backtest Harness", "status": "in_progress", "summary": "Market overlay (overlay-only) + model-vs-market validation harness.", "tasks": [
      { "id": "mo-harness-trust", "title": "Harness Trust Completion (G3/R2)", "status": "done" },
      { "id": "mo-gate4", "title": "Gate-4 forward fc_native accrual", "status": "in_progress", "note": "~2026-12-12" } ] }
  ]
}
```

Add a banner to the TOP of `docs/agent-execution-plan.md` (above the existing first line — do NOT delete any content):

```markdown
> **⚠️ DEPRECATED for live status (2026-06-19).** This file is RETAINED as the historical macro-roadmap playbook (detail + rationale). **Live phase/task status now lives in `resources/project_plan.json`** (rendered by the Project Tracker surface). Update status there; this doc is reference-only.

```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_project_plan_substrate.py -v`
Expected: PASS (2 tests). Also run `.venv/bin/python3.14 -c "import json; json.load(open('resources/project_plan.json'))"` → no error.

- [ ] **Step 5: Commit**

```bash
git add resources/project_plan.json docs/agent-execution-plan.md tests/contract/test_project_plan_substrate.py
git commit -m "feat(tracker): T1 — seed project_plan.json + non-destructive deprecation banner"
```

---

### Task 2: Loader service + DTO + validation pipeline (pure)

**Files:**
- Create: `app/services/project_plan_loader.py`
- Test: `tests/contract/test_project_plan_loader.py`

**Interfaces:**
- Produces: `class PlanTask`, `class PlanPhase`, `class ProjectPlanResponse(BaseModel)` (fields: `source:str`, `schema_version:str|None`, `updated_at:str|None`, `phases:list[PlanPhase]`, `warnings:list[str]`, `parser_version:str`, `status:Literal["ok","degraded"]`); `PROJECT_PLAN_PATH:Path`; `load_project_plan(path: Path = PROJECT_PLAN_PATH) -> ProjectPlanResponse`. Consumed by Task 3.
- Residual note pinned (Codex): on whole-degrade, `schema_version`/`updated_at` are returned as `None` (we do NOT surface a bad actual schema_version value); the warning token names the issue.

- [ ] **Step 1: Write the failing test**

```python
# tests/contract/test_project_plan_loader.py
import json
from app.services.project_plan_loader import load_project_plan

def _write(tmp_path, obj):
    p = tmp_path / "project_plan.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p

VALID = {
    "schema_version": "project_plan.v1", "updated_at": "2026-06-19",
    "phases": [
        {"id": "p1", "title": "Phase 1", "status": "done",
         "tasks": [{"id": "t1", "title": "Task 1", "status": "done"},
                   {"id": "t2", "title": "Task 2", "status": "planned", "note": "n"}]},
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
    p = tmp_path / "project_plan.json"; p.write_text("{not json", encoding="utf-8")
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
    obj = {**VALID, "phases": [VALID["phases"][0],
        {"id": "pbad", "title": "Bad", "status": "shipping", "tasks": []}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [p.id for p in r.phases] == ["p1"]  # valid phase kept, bad dropped
    assert "project_plan_phase_invalid:pbad" in r.warnings

def test_invalid_task_drops_task(tmp_path):
    obj = {"schema_version": "project_plan.v1", "updated_at": "x", "phases": [
        {"id": "p1", "title": "P", "status": "done", "tasks": [
            {"id": "t1", "title": "ok", "status": "done"},
            {"id": "t2", "title": "bad", "status": "nope"}]}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert "project_plan_task_invalid:p1/t2" in r.warnings

def test_duplicate_task_id_degrades(tmp_path):
    obj = {"schema_version": "project_plan.v1", "updated_at": "x", "phases": [
        {"id": "p1", "title": "P", "status": "done", "tasks": [
            {"id": "dup", "title": "a", "status": "done"},
            {"id": "dup", "title": "b", "status": "done"}]}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_duplicate_id:dup" in r.warnings

def test_missing_root_phases_degrades(tmp_path):
    r = load_project_plan(_write(tmp_path, {"schema_version": "project_plan.v1", "updated_at": "x"}))
    assert r.status == "degraded" and r.phases == []
    assert "project_plan_missing_root_field:phases" in r.warnings

def test_phase_missing_required_field_drops_phase(tmp_path):
    obj = {**VALID, "phases": [VALID["phases"][0],
        {"id": "p2", "status": "done", "tasks": []}]}  # missing title
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [p.id for p in r.phases] == ["p1"]
    assert "project_plan_phase_invalid:p2" in r.warnings

def test_task_missing_required_field_drops_task(tmp_path):
    obj = {"schema_version": "project_plan.v1", "updated_at": "x", "phases": [
        {"id": "p1", "title": "P", "status": "done", "tasks": [
            {"id": "t1", "title": "ok", "status": "done"},
            {"id": "t2", "status": "done"}]}]}  # task missing title
    r = load_project_plan(_write(tmp_path, obj))
    assert r.status == "degraded"
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert "project_plan_task_invalid:p1/t2" in r.warnings

def test_two_missing_id_phases_drop_not_whole_degrade(tmp_path):
    # F2 regression guard: two phases missing id DROP per-record, NOT whole-degrade as duplicate-None
    obj = {**VALID, "phases": [VALID["phases"][0],
        {"title": "no id A", "status": "done", "tasks": []},
        {"title": "no id B", "status": "done", "tasks": []}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert [p.id for p in r.phases] == ["p1"]  # valid phase kept
    assert not any(w.startswith("project_plan_duplicate_id") for w in r.warnings)
    assert sum(w.startswith("project_plan_phase_invalid") for w in r.warnings) == 2

def test_empty_phase_id_drops_phase(tmp_path):
    # F-new-2: empty-string id is not a valid required text field -> drop, not whole-degrade
    obj = {**VALID, "phases": [VALID["phases"][0],
        {"id": "", "title": "empty id", "status": "done", "tasks": []}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert [p.id for p in r.phases] == ["p1"]
    assert not any(w.startswith("project_plan_duplicate_id") for w in r.warnings)
    assert any(w.startswith("project_plan_phase_invalid") for w in r.warnings)

def test_empty_task_id_drops_task(tmp_path):
    obj = {"schema_version": "project_plan.v1", "updated_at": "x", "phases": [
        {"id": "p1", "title": "P", "status": "done", "tasks": [
            {"id": "t1", "title": "ok", "status": "done"},
            {"id": "", "title": "empty id", "status": "done"}]}]}
    r = load_project_plan(_write(tmp_path, obj))
    assert [t.id for t in r.phases[0].tasks] == ["t1"]
    assert any(w.startswith("project_plan_task_invalid:p1/") for w in r.warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_project_plan_loader.py -v`
Expected: FAIL (module `app.services.project_plan_loader` does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/project_plan_loader.py
import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel

PROJECT_PLAN_PATH = Path("resources/project_plan.json")
SUPPORTED_SCHEMA_VERSION = "project_plan.v1"
PlanStatus = Literal["planned", "in_progress", "done", "blocked", "deferred"]
_STATUS = {"planned", "in_progress", "done", "blocked", "deferred"}
_PARSER_VERSION = "v1"


class PlanTask(BaseModel):
    id: str
    title: str
    status: PlanStatus
    note: Optional[str] = None


class PlanPhase(BaseModel):
    id: str
    title: str
    status: PlanStatus
    summary: Optional[str] = None
    tasks: list[PlanTask]


class ProjectPlanResponse(BaseModel):
    source: str
    schema_version: Optional[str] = None
    updated_at: Optional[str] = None
    phases: list[PlanPhase]
    warnings: list[str]
    parser_version: str
    status: Literal["ok", "degraded"]


def _first_dup(ids: list[Any]) -> Optional[Any]:
    seen: set[Any] = set()
    for i in ids:
        if i in seen:
            return i
        seen.add(i)
    return None


def _text(d: dict, key: str) -> bool:
    """Required text field present as a non-empty string (F-new-2)."""
    v = d.get(key)
    return isinstance(v, str) and bool(v)


def _degraded(path: Path, warnings: list[str]) -> ProjectPlanResponse:
    return ProjectPlanResponse(
        source=str(path), schema_version=None, updated_at=None, phases=[],
        warnings=warnings, parser_version=_PARSER_VERSION, status="degraded",
    )


def load_project_plan(path: Path = PROJECT_PLAN_PATH) -> ProjectPlanResponse:
    # 1. read
    if not path.is_file():
        return _degraded(path, ["project_plan_source_missing"])
    # 2. parse
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return _degraded(path, ["project_plan_malformed_json"])
    if not isinstance(raw, dict):
        return _degraded(path, ["project_plan_malformed_json"])
    # 3. root validation
    if raw.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        return _degraded(path, ["project_plan_schema_version_unsupported"])
    if not isinstance(raw.get("updated_at"), str) or not raw["updated_at"]:
        return _degraded(path, ["project_plan_missing_root_field:updated_at"])
    phases_raw = raw.get("phases")
    if not isinstance(phases_raw, list):
        return _degraded(path, ["project_plan_missing_root_field:phases"])
    # 4. id-integrity (whole-degrade) — only PRESENT non-empty string ids. A missing
    #    id is a per-record drop (handled below), NOT a duplicate-None whole-degrade (F2).
    dup = _first_dup([
        p["id"] for p in phases_raw
        if isinstance(p, dict) and isinstance(p.get("id"), str) and p["id"]
    ])
    if dup is not None:
        return _degraded(path, [f"project_plan_duplicate_id:{dup}"])
    for p in phases_raw:
        if isinstance(p, dict) and isinstance(p.get("tasks"), list):
            dup_t = _first_dup([
                t["id"] for t in p["tasks"]
                if isinstance(t, dict) and isinstance(t.get("id"), str) and t["id"]
            ])
            if dup_t is not None:
                return _degraded(path, [f"project_plan_duplicate_id:{dup_t}"])
    # 5/6. per-phase + per-task (drop + warn)
    warnings: list[str] = []
    phases: list[PlanPhase] = []
    for idx, p in enumerate(phases_raw):
        pid = p.get("id") if isinstance(p, dict) else None
        label = pid if pid else f"index:{idx}"
        if (not isinstance(p, dict) or not _text(p, "id") or not _text(p, "title")
                or p.get("status") not in _STATUS or not isinstance(p.get("tasks"), list)):
            warnings.append(f"project_plan_phase_invalid:{label}")
            continue
        tasks: list[PlanTask] = []
        for tidx, t in enumerate(p["tasks"]):
            tid = t.get("id") if isinstance(t, dict) else None
            tlabel = tid if tid else f"index:{tidx}"
            if (not isinstance(t, dict) or not _text(t, "id") or not _text(t, "title")
                    or t.get("status") not in _STATUS):
                warnings.append(f"project_plan_task_invalid:{pid}/{tlabel}")
                continue
            tasks.append(PlanTask(id=t["id"], title=t["title"], status=t["status"], note=t.get("note")))
        phases.append(PlanPhase(id=p["id"], title=p["title"], status=p["status"],
                                summary=p.get("summary"), tasks=tasks))
    return ProjectPlanResponse(
        source=str(path), schema_version=raw.get("schema_version"),
        updated_at=raw.get("updated_at"), phases=phases, warnings=warnings,
        parser_version=_PARSER_VERSION, status="degraded" if warnings else "ok",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_project_plan_loader.py -v`
Expected: PASS (15 tests). Then `.venv/bin/ruff check app/services/project_plan_loader.py tests/contract/test_project_plan_loader.py` → clean (both touched files).

- [ ] **Step 5: Commit**

```bash
git add app/services/project_plan_loader.py tests/contract/test_project_plan_loader.py
git commit -m "feat(tracker): T2 — project_plan_loader with two-stage validation pipeline"
```

---

### Task 3: Internal endpoint + router registration

**Files:**
- Create: `app/api/routes/internal_project_plan.py`
- Modify: `app/main.py` (import + `include_router`)
- Test: `tests/contract/test_internal_project_plan_route.py`

**Interfaces:**
- Consumes: `load_project_plan`, `ProjectPlanResponse`, `PROJECT_PLAN_PATH` from Task 2.
- Produces: `router = APIRouter(prefix="/internal")`; `GET /api/internal/project-plan` (`include_in_schema=False`) → `ProjectPlanResponse`.

- [ ] **Step 1: Write the failing test**

```python
# tests/contract/test_internal_project_plan_route.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_route_returns_plan_ok():
    r = client.get("/api/internal/project-plan")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}  # real seed file present -> ok
    assert "phases" in body and "warnings" in body
    assert body["parser_version"] == "v1"

def test_route_excluded_from_openapi():
    schema = client.get("/openapi.json").json()
    assert "/api/internal/project-plan" not in schema.get("paths", {})

def test_route_accepts_no_path_param():
    # fixed source only: a path-style suffix must 404 (SPA fallback excludes api/), not read an arbitrary file
    r = client.get("/api/internal/project-plan/etc/passwd")
    assert r.status_code == 404

def test_route_degrades_when_source_missing(monkeypatch, tmp_path):
    import app.api.routes.internal_project_plan as mod
    monkeypatch.setattr(mod, "PROJECT_PLAN_PATH", tmp_path / "absent.json")
    r = client.get("/api/internal/project-plan")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"
    assert "project_plan_source_missing" in r.json()["warnings"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_internal_project_plan_route.py -v`
Expected: FAIL (route 404 / module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# app/api/routes/internal_project_plan.py
from fastapi import APIRouter

from app.services.project_plan_loader import (
    PROJECT_PLAN_PATH,
    ProjectPlanResponse,
    load_project_plan,
)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get(
    "/project-plan",
    response_model=ProjectPlanResponse,
    include_in_schema=False,  # internal tooling: keep OpenAPI deterministic, no client churn
)
def get_project_plan() -> ProjectPlanResponse:
    # Fixed allowlisted source only; no request-supplied path. Fail-closed/degraded inside.
    return load_project_plan(PROJECT_PLAN_PATH)
```

In `app/main.py`: add `internal_project_plan` to the `from app.api.routes import (...)` block and register it (with the other `/api` routers):

```python
app.include_router(internal_project_plan.router, prefix="/api")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_internal_project_plan_route.py -v`
Expected: PASS (4 tests). Then `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` → unchanged PASS (endpoint excluded). `.venv/bin/ruff check app` → clean.

- [ ] **Step 5: Commit**

```bash
git add app/api/routes/internal_project_plan.py app/main.py tests/contract/test_internal_project_plan_route.py
git commit -m "feat(tracker): T3 — GET /api/internal/project-plan (include_in_schema=False)"
```

---

### Task 4: Frontend ProjectTracker component

**Files:**
- Create: `frontend/src/project/ProjectTracker.tsx`, `frontend/src/project/ProjectTracker.css`, `frontend/src/project/projectPlanSchema.ts`
- Test: `frontend/src/project/ProjectTracker.test.jsx`

**Interfaces:**
- Produces: `ProjectTracker` React component (no props); local Zod schema `zProjectPlan` mirroring the DTO. Consumed by Task 5.

- [ ] **Step 1: Write the failing test**

```jsx
// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectTracker } from "./ProjectTracker";

const OK = {
  source: "resources/project_plan.json", schema_version: "project_plan.v1",
  updated_at: "2026-06-19", parser_version: "v1", status: "ok", warnings: [],
  phases: [
    { id: "p1", title: "Phase 1", status: "in_progress", summary: "s",
      tasks: [{ id: "t1", title: "Task 1", status: "done", note: null }] },
  ],
};
function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({ ok: status === 200, status, json: async () => body });
}
afterEach(() => vi.restoreAllMocks());

describe("ProjectTracker", () => {
  it("renders phases and expands to tasks", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
    fireEvent.click(screen.getByText("Phase 1"));
    await waitFor(() => expect(screen.getByText("Task 1")).toBeTruthy());
  });
  it("renders a status badge from the enum", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getAllByText(/in_progress/i).length).toBeGreaterThan(0));
  });
  it("renders degraded warnings without crashing", async () => {
    mockFetch(200, { ...OK, status: "degraded", phases: [], warnings: ["project_plan_source_missing"] });
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText(/project_plan_source_missing/i)).toBeTruthy());
  });
  it("renders an honest error on parse failure", async () => {
    mockFetch(200, { bogus: true });
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText(/could not load the project plan/i)).toBeTruthy());
  });
  it("refresh re-fetches", async () => {
    mockFetch(200, OK);
    render(<ProjectTracker />);
    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/project/ProjectTracker.test.jsx`
Expected: FAIL (component/module missing).

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/project/projectPlanSchema.ts
import { z } from "zod";

// F4: enforce the status enum so the UI parse catches backend contract drift.
export const zPlanStatus = z.enum(["planned", "in_progress", "done", "blocked", "deferred"]);
export const zPlanTask = z.object({
  id: z.string(), title: z.string(), status: zPlanStatus,
  note: z.string().nullable().optional(),
});
export const zPlanPhase = z.object({
  id: z.string(), title: z.string(), status: zPlanStatus,
  summary: z.string().nullable().optional(), tasks: z.array(zPlanTask),
});
export const zProjectPlan = z.object({
  source: z.string(),
  schema_version: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  phases: z.array(zPlanPhase),
  warnings: z.array(z.string()),
  parser_version: z.string(),
  status: z.enum(["ok", "degraded"]),
});
export type ProjectPlan = z.infer<typeof zProjectPlan>;
```

```tsx
// frontend/src/project/ProjectTracker.tsx
import { useCallback, useEffect, useState } from "react";
import "./ProjectTracker.css";
import { type ProjectPlan, zProjectPlan } from "./projectPlanSchema";

type State =
  | { status: "loading" }
  | { status: "ready"; data: ProjectPlan }
  | { status: "error" };

export function ProjectTracker() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch("/api/internal/project-plan");
      const data = zProjectPlan.parse(await res.json());
      setState({ status: "ready", data });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === "loading") return <p className="dg-tracker__msg">Loading project plan…</p>;
  if (state.status === "error")
    return <p className="dg-tracker__msg">Could not load the project plan.</p>;

  const { data } = state;
  return (
    <div className="dg-tracker">
      <div className="dg-tracker__bar">
        <span>Updated: {data.updated_at ?? "—"}</span>
        <button type="button" onClick={() => void load()}>Refresh</button>
      </div>
      {data.warnings.length > 0 && (
        <ul className="dg-tracker__warnings" role="status">
          {data.warnings.map((w) => <li key={w}>{w}</li>)}
        </ul>
      )}
      {data.phases.length === 0 ? (
        <p className="dg-tracker__msg">No project plan available.</p>
      ) : (
        data.phases.map((p) => (
          <section key={p.id} className="dg-tracker__phase">
            <button
              type="button"
              className="dg-tracker__phase-head"
              aria-expanded={!!open[p.id]}
              onClick={() => setOpen((o) => ({ ...o, [p.id]: !o[p.id] }))}
            >
              <span className="dg-tracker__badge" data-status={p.status}>{p.status}</span>
              {p.title}
            </button>
            {open[p.id] && (
              <ul className="dg-tracker__tasks">
                {p.tasks.map((t) => (
                  <li key={t.id}>
                    <span className="dg-tracker__badge" data-status={t.status}>{t.status}</span>
                    {t.title}
                    {t.note ? <em> — {t.note}</em> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))
      )}
    </div>
  );
}
```

```css
/* frontend/src/project/ProjectTracker.css */
.dg-tracker { display: flex; flex-direction: column; gap: 0.5rem; }
.dg-tracker__bar { display: flex; gap: 1rem; align-items: center; }
.dg-tracker__warnings { color: #d18; font-size: 0.85rem; }
.dg-tracker__phase-head { display: flex; gap: 0.5rem; align-items: center; width: 100%; text-align: left; background: none; border: none; padding: 0.4rem 0; cursor: pointer; }
.dg-tracker__tasks { list-style: none; padding-left: 1.5rem; display: flex; flex-direction: column; gap: 0.25rem; }
.dg-tracker__badge { font-size: 0.7rem; padding: 0.1rem 0.4rem; border: 1px solid currentcolor; border-radius: 0.25rem; opacity: 0.85; }
.dg-tracker__badge[data-status="done"] { opacity: 0.55; }
.dg-tracker__msg { opacity: 0.8; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/project/ProjectTracker.test.jsx`
Expected: PASS (5 tests). Then `npm --prefix frontend run typecheck` + `npm --prefix frontend run lint` → clean (format new files with `node_modules/.bin/biome check --write` from `frontend/` if needed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/project/
git commit -m "feat(tracker): T4 — ProjectTracker component + local Zod schema"
```

---

### Task 5: AppShell wiring (new surface)

**Files:**
- Modify: `frontend/src/shell/AppShell.tsx`
- Test: `frontend/src/shell/AppShell.test.jsx` (append)

**Interfaces:**
- Consumes: `ProjectTracker` from Task 4.

- [ ] **Step 1: Write the failing test**

```jsx
// (append to frontend/src/shell/AppShell.test.jsx)
it("renders the Project Tracker surface when its nav item is selected", async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({
      source: "resources/project_plan.json", schema_version: "project_plan.v1",
      updated_at: "2026-06-19", parser_version: "v1", status: "ok", warnings: [],
      phases: [{ id: "p1", title: "Phase 1", status: "in_progress", summary: null, tasks: [] }],
    }),
  });
  render(<AppShell />);
  fireEvent.click(screen.getByRole("button", { name: "Project Tracker" }));
  await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
});
```

(Ensure `fireEvent`, `waitFor`, `vi` are imported in the test file; add to the existing import if missing.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/shell/AppShell.test.jsx`
Expected: FAIL (no "Project Tracker" nav item / surface).

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/shell/AppShell.tsx`: import the component and add the surface + render branch.

```tsx
import { ProjectTracker } from "../project/ProjectTracker";
```

Add `"Project Tracker"` to the `SURFACES` array (append after `"Research Assistant"`):

```tsx
const SURFACES = [
  "Rookie Board",
  "Roster Audit",
  "Trade Lab",
  "Waiver Radar",
  "League Pulse",
  "Model Trust",
  "Research Assistant",
  "Project Tracker",
] as const;
```

Add the render branch alongside the others (inside the `<main>` non-detail block):

```tsx
{activeSurface === "Project Tracker" && <ProjectTracker />}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/shell/AppShell.test.jsx`
Expected: PASS (existing AppShell tests + the new one). Then `npm --prefix frontend run typecheck` + `lint` → clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shell/AppShell.tsx frontend/src/shell/AppShell.test.jsx
git commit -m "feat(tracker): T5 — wire Project Tracker into AppShell (no router)"
```

---

### Task 6: Closeout verification + state docs

**Files:** Modify `AGENT_SYNC.md`, `docs/agent-ledger/2026-06-19.md` (state docs; separate commit).

- [ ] **Step 1: Full FE gate**

Run: `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run test && npm --prefix frontend run build`
Expected: all green; full FE vitest suite passes (incl. project + shell).

- [ ] **Step 2: Backend + OpenAPI drift**

Run: `.venv/bin/python3.14 -m pytest tests/contract/test_project_plan_substrate.py tests/contract/test_project_plan_loader.py tests/contract/test_internal_project_plan_route.py tests/contract/test_openapi_drift_contract.py -q`
Expected: all PASS; OpenAPI drift unchanged (endpoint excluded).

- [ ] **Step 3: Diff scope check**

Run: `git diff --name-only origin/main...HEAD`
Expected: only `resources/project_plan.json`, `docs/agent-execution-plan.md` (banner), `app/services/project_plan_loader.py`, `app/api/routes/internal_project_plan.py`, `app/main.py`, `frontend/src/project/*`, `frontend/src/shell/AppShell.*`, the new tests, spec/plan docs. NO change to `frontend/openapi.json` or `frontend/src/lib/api/*.gen.ts` or existing dynasty endpoints/models.

- [ ] **Step 4: Sprint-closeout tollgate**

Run: `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main`
Expected: ENFORCE PASS (full Python suite + `ruff check src app` + FE gate).

- [ ] **Step 5: Commit (state docs)**

Record the tooling-scope + narrow-HOLD authorizations + the shipped tracker in `AGENT_SYNC.md` and append the ledger entry, then:

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-06-19.md
git commit -m "docs(sync): Project Tracker v1 build complete (tooling scope + HOLD lift recorded)"
```

---

## Self-Review

**1. Spec coverage:**
- §0 authorizations (tooling scope, HOLD lift, Path B) → recorded in spec + Task 6 state docs. ✓
- §3.1 substrate (JSON, schema, enum) → Task 1 (seed) + Task 2 (DTO). ✓
- §3.2 validation matrix (whole-degrade / drop-phase / drop-task) → Task 2 (loader + 15 tests, one per matrix row incl. F1 additions, F2 + F-new-2 regression/empty-id guards). ✓
- §3.2 endpoint (fixed source, include_in_schema=False, fail-closed) → Task 3 (+ openapi-exclusion test). ✓
- §3.3 frontend surface (collapsible phases/tasks, badges, refresh, degraded, empty, parse-error) → Task 4 + Task 5. ✓
- §6 non-goals respected (no writeback, no router, no migration, no AGENT_SYNC parsing). ✓
- §8 AC-1..AC-6 → Tasks 1–6 + closeout. ✓
- Codex residual (schema_version on degrade = null) → Task 2 Interfaces + `test_unsupported_schema_version_degrades`. ✓

**2. Placeholder scan:** No TBD/TODO; every code step is complete. Task 1 seed is the complete v1 macro set (6 phases) written verbatim — no "extend later" instruction — and the T1 `REQUIRED_PHASE_IDS` assertion guards against a partial ledger (F5).

**3. Type consistency:** `ProjectPlanResponse`/`PlanPhase`/`PlanTask` + `load_project_plan`/`PROJECT_PLAN_PATH` defined in Task 2, consumed verbatim in Task 3. Zod `zProjectPlan` (Task 4) mirrors the DTO field-for-field. Status enum identical across substrate/loader/tests. Warning tokens identical between loader impl and tests.

---

## Governance

- Spec (dual-CLEARED v2, `85b81d6`) is the contract. Build via the cockpit cycle: Codex RED → Claude GREEN → dual-CLEAR per task → David-authorized commit → zero-divergence audit.
- Internal tooling: no `decision_supported`, no Engine/model/market change, no dynasty-decision framing. Path B non-destructive (agent-execution-plan.md retained + banner). No new runtime deps. OpenAPI schema unchanged (endpoint excluded).
- This plan is routed through the cockpit for dual-CLEAR before any task execution; David authorizes proceeding.
