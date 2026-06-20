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
    # 3. root validation (whole-degrade)
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
