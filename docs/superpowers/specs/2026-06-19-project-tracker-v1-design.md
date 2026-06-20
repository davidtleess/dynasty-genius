# Live Project Tracker v1 — Design Spec

**Date:** 2026-06-19
**Status:** v2 (David-authorized initiative; scope/HOLD/source-model/substrate ruled pre-spec; v2 integrates Codex findings 1–4 — explicit validation pipeline/matrix)
**Authored by:** Claude Code (folding Gemini PM v2 structure + Codex technical/validation bounds)
**Phase:** Internal tooling — NOT a Phase-12 dynasty decision surface.

## 0. Authorization & scope (record of David's rulings, 2026-06-19)

This is **internal dev-tooling**, authorized by David as an explicit exception to the product constitution's dynasty-decision mission (precedent: the sprint-closeout verifier). It is **process/tooling scope, NOT a dynasty decision surface** — therefore exempt from decision-surface gates (no `decision_supported`, no model-trust/validation gating, no banned-David-facing-output contract; it shows project state, not player/trade analysis). The product mission itself is **unchanged**.

David's pre-spec rulings:
1. **Scope:** authorize as internal tooling (above).
2. **Frontend HOLD:** narrow lift for **this Project Tracker surface only**; the rest of the Phase-12 frontend HOLD stands; no broader UI work and no new runtime dependencies authorized.
3. **Source model:** structured-source-first.
4. **Substrate (Path B, non-destructive):** `resources/project_plan.json` is the authoritative **structured status ledger**; `docs/agent-execution-plan.md` is **retained** as the historical playbook with a deprecation banner pointing to the JSON for live status; `AGENT_SYNC.md` remains the micro sprint narrative. **No migration, no doc retirement.**

## 1. Goal

A single-pane-of-glass, read-only dashboard — integrated into the existing AppShell — that renders the project's macro roadmap (phases → tasks, with status) from a structured source so it stays synced with the team's recorded state without manual data entry into the UI.

## 2. Core directives & governance

1. **Read-only; never a second source of truth.** The dashboard renders `resources/project_plan.json` and nothing else; it never writes. `project_plan.json` is authoritative for phase/task **status**; prose docs do not duplicate status (the deprecation banner on `agent-execution-plan.md` enforces this).
2. **No semantic inference.** The backend reads a *structured* file and validates it; it does **not** parse prose or infer status/owner/priority. (This is why Path B + a structured substrate was chosen over markdown-prose parsing.)
3. **OpenAPI protection.** The endpoint is excluded from the schema (`include_in_schema=False`) → zero generated-client churn; the frontend consumes it via manual `fetch` + a local Zod schema.
4. **Fail-closed.** Fixed allowlist of exactly one repo-relative source path (`resources/project_plan.json`); no request-supplied paths. Missing/malformed/invalid → a **degraded** response with warnings, never a misleading empty "current plan".
5. **No new runtime dependencies.** AppShell `activeSurface` pattern; no react-router. Backend uses stdlib `json` + Pydantic (already pervasive).
6. **Tooling scope.** No `decision_supported`, no model/market/Engine logic, no dynasty-decision framing.

## 3. Architecture & contracts

### 3.1 Structured substrate — `resources/project_plan.json`

Authoritative status ledger (minimal; matches the repo's `resources/*.json` convention). Schema:

```json
{
  "schema_version": "project_plan.v1",
  "updated_at": "2026-06-19",
  "doctrine_version": "1.0.0",
  "phases": [
    {
      "id": "phase-12",
      "title": "Phase 12 — Frontend Decision Surfaces",
      "status": "in_progress",
      "summary": "Read-only decision surfaces over the typed contract.",
      "tasks": [
        { "id": "ra-inc3-a", "title": "Roster Audit Inc3 Task A — sort/filter/group", "status": "done", "note": "PR #67" },
        { "id": "ra-inc3-b", "title": "Roster Audit Inc3 Task B — decision-framed grouping", "status": "planned" }
      ]
    }
  ]
}
```

- **Status enum:** `planned | in_progress | done | blocked | deferred` (exact tokens).
- Required: `schema_version`, `updated_at`, `phases[]`; each phase requires `id`, `title`, `status`, `tasks[]`; each task requires `id`, `title`, `status`. `summary`, `note`, `doctrine_version` optional.
- **No `details_markdown`** — rich detail stays in the retained `agent-execution-plan.md` (Path B).
- **Seeding (v1):** hand-curate the current macro phases/tasks (titles + status) from `agent-execution-plan.md` + AGENT_SYNC. This is a data-curation step, not a migration — prose detail is NOT copied in.

### 3.2 Backend API

- **Endpoint:** `GET /api/internal/project-plan`, `include_in_schema=False`.
- **Router/service:** `app/api/routes/internal_project_plan.py` + `app/services/project_plan_loader.py` (load + validate; pure, testable).
- **Response DTO (Pydantic):**

```json
{
  "source": "resources/project_plan.json",
  "schema_version": "project_plan.v1",
  "updated_at": "2026-06-19",
  "phases": [ { "id": "...", "title": "...", "status": "...", "summary": "...|null",
               "tasks": [ { "id": "...", "title": "...", "status": "...", "note": "...|null" } ] } ],
  "warnings": [],
  "parser_version": "v1",
  "status": "ok"
}
```

- **Loader validation pipeline (explicit two-stage contract — resolves the row-salvage vs whole-degrade ambiguity).** All degraded outcomes are HTTP **200** with `status="degraded"` + warnings (never 5xx, never a misleading empty `"ok"`). The pipeline runs in order:
  1. **Read file.** Missing → whole-degrade, `phases=[]`, warning `project_plan_source_missing`.
  2. **Parse JSON.** Malformed → whole-degrade, warning `project_plan_malformed_json`.
  3. **Root validation (whole-degrade on failure, `phases=[]`):** `schema_version` must equal `"project_plan.v1"` (missing or mismatch → `project_plan_schema_version_unsupported`); `updated_at` present (→ `project_plan_missing_root_field:updated_at`); `phases` present and a list (→ `project_plan_missing_root_field:phases`).
  4. **Id-integrity (whole-degrade on failure, `phases=[]`):** duplicate phase `id` (across phases) or duplicate task `id` (within any phase) → `project_plan_duplicate_id:<id>`. (Ids must be unique — they are the UI keys and the status-authority handles; an integrity violation fails closed rather than silently dropping data.)
  5. **Per-phase validation (drop the offending phase + warning; valid phases still render):** a phase missing a required field (`id`/`title`/`status`/`tasks`) or with a status token outside the enum → drop that phase, warning `project_plan_phase_invalid:<id-or-index>`.
  6. **Per-task validation (drop the offending task + warning; valid tasks in the phase still render):** a task missing a required field (`id`/`title`/`status`) or with a status token outside the enum → drop that task, warning `project_plan_task_invalid:<phase-id>/<id-or-index>`.
  7. **Finalize:** `status="degraded"` if any warnings were emitted, else `status="ok"`. `parser_version` + `schema_version` always surfaced for drift visibility.

  **Summary matrix:** malformed JSON · missing/unsupported `schema_version` · missing root field · duplicate id → **whole-degrade** (`phases=[]`). Invalid phase (missing field / bad status) → **drop phase**. Invalid task (missing field / bad status) → **drop task**. Valid remainder always renders.

### 3.3 Frontend surface

- **Integration:** add `"Project Tracker"` to the AppShell `SURFACES` array + a render branch `activeSurface === "Project Tracker" && <ProjectTracker />`. No router.
- **Component:** `frontend/src/project/ProjectTracker.tsx` (+ `.css`, + tests).
- **Data:** manual `fetch("/api/internal/project-plan")` → local Zod schema parse (no generated client; mirrors the Roster Audit pattern).
- **UX:** dense, dark-mode, operational. Collapsible **phases** (each showing status badge + summary), expandable to their **tasks** (status badge + title + note). A manual **Refresh** button (re-fetch). **Degraded state:** when `status="degraded"` or warnings present, render the warnings banner + whatever valid phases exist — never blank, never crash. Empty (`phases=[]`) → honest "No project plan available" state.
- **Status badges:** neutral factual rendering of the enum (planned/in_progress/done/blocked/deferred); no verdict language (and banned-language is N/A here — this is tooling, not a David-facing dynasty surface — but copy stays neutral/professional regardless).

## 4. Data flow

Mount → `fetch` → Zod parse → render phases/tasks (collapsible) or degraded/empty state. Refresh button re-runs the fetch. Read-only; no mutation, no writeback.

## 5. Testing

- **Loader/service unit tests (one per validation-matrix row):** valid file → typed `status="ok"`. **Whole-degrade** cases (`phases=[]` + the named warning): missing file (`project_plan_source_missing`); malformed JSON (`project_plan_malformed_json`); unsupported/missing `schema_version` (`project_plan_schema_version_unsupported`); missing root `updated_at` / `phases` (`project_plan_missing_root_field:*`); duplicate phase id and duplicate task id (`project_plan_duplicate_id:*`). **Drop-phase** cases (valid phases still render): phase with unknown status; phase missing a required field → `project_plan_phase_invalid:*`. **Drop-task** cases (valid tasks still render): task with unknown status; task missing a required field → `project_plan_task_invalid:*`. Assert `status="degraded"` whenever any warning is emitted, `"ok"` otherwise.
- **Route contract tests:** `GET /api/internal/project-plan` 200 happy path (typed shape); degraded paths return 200 + warnings (not 5xx); endpoint absent from `/openapi.json` (assert `include_in_schema=False`); fixed-source (no path param accepted).
- **Frontend tests (vitest):** renders phases + collapsible tasks + status badges from a fixture; Refresh re-fetches; degraded response renders warnings + valid phases; empty renders the honest empty state; Zod-parse failure → honest error (never blank).
- **OpenAPI drift:** `tests/contract/test_openapi_drift_contract.py` stays green (endpoint excluded → no schema change, no client regen).
- **Closeout:** `verify_sprint_closeout.py --base origin/main` ENFORCE PASS (full Python suite + ruff + FE gate); full FE gate green.

## 6. Scope / non-goals (YAGNI)

- **IN:** `resources/project_plan.json` (seeded), the deprecation banner on `agent-execution-plan.md`, the fail-closed internal endpoint, the AppShell ProjectTracker surface (collapsible phases/tasks, status badges, refresh, degraded/empty).
- **OUT (deferred):** any writeback/editing from the UI; URL-addressable `/plan` route + react-router; websocket/live auto-refresh (manual refresh only); migrating/retiring `agent-execution-plan.md` (Path A — a separate David decision); parsing AGENT_SYNC prose; auth; multi-user; semantic status/owner/priority inference.

## 7. Governance

- David-authorized internal tooling (§0); recorded in AGENT_SYNC + ledger. Narrow frontend HOLD lift (this surface only). No dynasty-decision-surface gates apply (tooling). No `decision_supported`, no Engine/model/market/contract change to the dynasty product. Backend touches only the new internal route/service + the new JSON + the banner; no change to existing dynasty endpoints or the OpenAPI schema.
- Build via the cockpit cycle: this spec → dual-CLEAR → implementation plan → Codex-RED / Claude-GREEN TDD per task → dual-CLEAR → David-authorized commit → zero-divergence audit → PR + David merge.

## 8. Acceptance criteria

- **AC-1 (substrate):** `resources/project_plan.json` exists, conforms to `project_plan.v1`, seeded with current macro phases/tasks (status only; no prose detail); `agent-execution-plan.md` retained with a deprecation banner; no doc migrated/retired.
- **AC-2 (endpoint):** `GET /api/internal/project-plan` returns the typed DTO from the fixed source; excluded from OpenAPI (`include_in_schema=False`); accepts no path input.
- **AC-3 (fail-closed, per the §3.2 matrix):** all degraded outcomes are HTTP 200 `status="degraded"` + warnings (never 5xx, never a misleading empty "ok"). **Whole-degrade** (`phases=[]`): missing file, malformed JSON, unsupported/missing `schema_version`, missing root field, duplicate id. **Drop-phase** (valid phases render): phase missing required field or unknown phase status. **Drop-task** (valid tasks render): task missing required field or unknown task status.
- **AC-4 (surface):** AppShell renders ProjectTracker on the new surface (no router); collapsible phases/tasks + status badges + Refresh; degraded → warnings + valid phases; empty → honest empty state; parse failure → honest error.
- **AC-5 (no drift / scope):** OpenAPI drift guard green (endpoint excluded); no change to existing dynasty endpoints/models/Engine/market; no new runtime dependency; rest of frontend HOLD intact.
- **AC-6 (tooling boundary):** no `decision_supported`, no dynasty-decision framing, no model/market logic anywhere in the tracker; copy neutral.
