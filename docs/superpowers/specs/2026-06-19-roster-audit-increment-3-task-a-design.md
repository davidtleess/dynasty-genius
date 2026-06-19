# Roster Audit — Increment 3, Task A: Client-Side Sort / Filter / Group — Design Spec

**Date:** 2026-06-19
**Status:** v2 (brainstormed with David; 6 decisions cockpit-CONCURRED pre-spec under the "poll each, then draft" mandate; v2 integrates Codex review findings 1–2)
**Authored by:** Claude Code
**Phase:** Phase 12 (Frontend) decision-surface sequence — Roster Audit Increment 3, Task A (interactive controls over the Inc1-hardened contract + Inc2 read-only surface)
**Predecessors:** Increment 1 (API contract hardening) — MERGED `454b8e7`; Increment 2 (read-only UI) — MERGED `1fe9992`. Consumes `RosterAuditResponse` and the Inc2 components as-is; **no backend / contract / model change.**
**Frontend HOLD:** David's read-only Roster Audit HOLD lift covers Inc3 (confirmed 2026-06-19). The rest of the Phase-12 HOLD stands; this authorizes no other frontend build and no new runtime dependencies.

---

## 1. Goal

Add **client-side sort, filter, and grouping controls** over the existing Inc2 Roster Audit surface so David can re-orient his roster around the dynasty decisions he actually makes (hold / sell / replace / develop) — **without** any verdict, action, recommendation, market overlay, decision-grade total, or `decision_supported` override. All interaction is purely client-side over the typed `GET /api/roster/audit` response. **Zero backend / model / contract / OpenAPI change.**

## 2. Architecture

- **Stack A** (locked ADR): Vite + React + TS served by FastAPI. Work stays in `frontend/src/roster/`.
- **Pure transform module (new):** `frontend/src/roster/rosterTransform.ts` — pure, side-effect-free functions (`applyFilter`, `applySort`, `applyGroup` + null-safe comparators + the producer-token→label map). One clear purpose, fully unit-testable in isolation, no React/DOM dependency. This is where all ordering/segmentation logic lives so components stay "dumb."
- **Controls component (new):** `frontend/src/roster/RosterAuditControls.tsx` — the sticky toolbar (sort/group dropdowns, position multi-select, prospect/active toggle, compact Experimental disclaimer, filtered-out count + reset).
- **Container (modified):** `RosterAudit.tsx` gains **local UI state** (`sortKey`, `positionFilter`, `prospectFilter`, `groupBy`) and applies the transform to `response.players` before rendering. Default state = no sort / all positions / all rows / no grouping → renders the backend order unchanged.
- **Table (modified):** `RosterAuditTable.tsx` renders either a flat list (default) or grouped sections with neutral group headings; `RosterAuditRow.tsx` is unchanged (row trust cells preserved in both modes).
- **No new runtime dependencies. No backend / contract / model / Engine-A / Engine-B / training / market change.**

## 3. Decision D1 — Default order is the backend's (no client re-sort on load)

The backend already orders players by aging urgency (`app/services/roster_auditor.py` sorts on `years_to_cliff`; `assemble_response` preserves that order) and Inc2 renders faithfully (`RosterAuditTable` `players.map`, no sort). **Task A preserves this:** the default `sortKey = "none"` and `groupBy = "none"` render `response.players` in returned order with zero client re-sort. The faithful-order acceptance behavior from Inc2 is intact. Sorting/grouping are explicit opt-in user actions only; the frontend never re-derives the backend's default ordering.

## 4. Decision D2 — Sort controls (single active sort)

A **"Sort by" dropdown**; **single** active sort (not user-composed multi-sort); default **`none` = backend order**. Options and null-safe comparators (all comparators live in `rosterTransform.ts`):

| Option (label) | Field | Direction | Tie-breakers (multi-key, internal) | Nulls |
|---|---|---|---|---|
| None (default) | — | backend order | — | — |
| Age-cliff risk | `roster_audit.age_cliff_risk` | desc | `years_to_cliff` asc → `age` desc → `biological_debt_score` desc | rows with no `roster_audit` / null key sort **last** |
| Age | `age` | desc | (stable) | null **last** |
| Signal completeness | `signal_completeness` | asc | (stable) | field is `float=0.0` (no null); lowest first = trust triage |
| Value above replacement (xVAR) | `xvar` | desc | (stable) | negative xVAR valid (below positive); null **last** |

- **xVAR sort governance:** opt-in only, numeric-only, neutral label "Value above replacement (xVAR)", Experimental disclaimer in view, nulls last. `xvar` is the cross-position-comparable field (`pvo_assembler.py`: `xvar = (dynasty_value_score − position_replacement) × position_lambda`); `dynasty_value_score` and `dvs_pct` are **within-position** and are NOT used as the roster-wide value sort key (they remain context columns only).
- **Stability:** JS `Array.prototype.sort` is stable; equal-key rows preserve backend relative order. Null/missing rows are **always visible**, sorted last, **never dropped**.

## 5. Decision D3 — Filter controls

Two filters; client-side subset only (never hides via trust):

- **Position** — multi-select over `position` (mandatory, non-null). Default all selected. **Empty selection resolves to All**, never a blank roster.
- **Prospect / Active** — segmented toggle over `is_prospect` (bool, default false). Options: All (default) / Active / Prospects.
- **No trust-hide filter** (governance ruling): hiding EXPERIMENTAL / low-completeness rows creates a falsely-pristine roster and conceals uncertainty — the roster is the roster. The locked `signal_completeness` asc sort serves trust triage **without hiding** any row.
- **Partial-view guard:** when any filter is active, show a **filtered-out count** and a **reset** control; a filter that yields zero rows shows an explicit **"filters produced no rows"** state (distinct from data-absence; does **not** reuse the generic Inc2 empty-state copy) and preserves the header/disclaimer.
- `is_prospect` is a **filter only**; it is explicitly excluded from D4 grouping (no redundant segmentation).

## 6. Decision D4 — Grouping controls (opt-in)

A **"Group by" dropdown**, opt-in, default **None (flat)** — which preserves D1. Options:

- **None** (default, flat).
- **Position** — group rows by `position`.
- **Depreciation-band** — group by the **backend's producer-owned `roster_audit.signal` token** (faithful per-token, "Option P"); the frontend does a **token→label lookup only**, never threshold math:
  - `past_cliff` → "Past cliff age"
  - `at_cliff` → "At cliff age"
  - `approaching_cliff` → "Approaching cliff"
  - `no_age_signal` → "3+ years (No immediate cliff)"
  - missing `roster_audit` / `signal` → "Missing age signal" bucket, **rendered last, rows visible**
- **Excluded:** `is_prospect` grouping (it is the D3 filter), value-band grouping (tiering risk), trust/status grouping (covered by sort + header chips).
- **Group order (deterministic, independent of the active sort):** **Position** groups render in **first-seen backend order** (the order each position first appears in the backend-ordered list — no frontend-imposed position ranking). **Depreciation-band** groups render in the fixed producer-token severity order — `past_cliff` → `at_cliff` → `approaching_cliff` → `no_age_signal` → "Missing age signal" (always last). Group order **never** changes with the active sort.
- **Within-group order:** preserve backend relative order by default; if an explicit alternate sort (D2) is active, apply that sort **within each group only**. **Grouping never globally re-sorts** and never re-derives backend logic.
- Group headings are neutral/factual; the Experimental disclaimer and per-row trust cells are retained in grouped views.

## 7. Decision D5 — Trust preservation (all Inc2 surfacing persists)

Inc2 already surfaces trust; Task A **preserves it identically across every sort/filter/group state**:

- **Per-row:** `model_grade`, `model_status_applies` (applies / n-a), `signal_completeness` %, caveats indicator, and expanded-row context — visible in both flat and grouped renders.
- **Header:** overall `status`, per-position `model_status` chips, caveats, `dropped_player_count`, and the "Experimental — not decision-grade" disclaimer — stays mounted above the interactive table/grouped view.
- **EXPERIMENTAL / non-applicable de-emphasis is CSS styling ONLY** — it never participates in sorting, filtering, grouping, or row removal.
- **No new degraded auto-banner** (existing header status + chips suffice; a second banner would duplicate state).
- **Contextual persistence (sticky disclaimer):** because interactive sorts (especially xVAR value) let the user re-orient on model value, the **compact Experimental / not-decision-grade disclaimer must remain in-viewport with the controls** — embedded in the sticky controls toolbar (§8) — so the user never loses EXPERIMENTAL context while making sort decisions. The full header remains mounted above.

## 8. Decision D6 — Controls UX & state persistence

- **Placement:** a **sticky controls toolbar** above the table, carrying the compact Experimental disclaimer (satisfies §7 contextual persistence). The full Inc2 header (status / chips / caveats / dropped-count) stays mounted above the toolbar.
- **Sort/Group UI:** distinct **dropdown** controls (not clickable column headers) — the locked sort keys are semantic lenses, not 1:1 table columns (age-cliff risk is nested; xVAR is in expanded detail; completeness sort is intentionally ascending).
- **Filter UI:** Position multi-select + Prospect/Active segmented toggle.
- **State persistence:** **local component state ONLY** — resets to default (backend order, all rows, no grouping) on reload. **No URL params / no shareable state** — a deliberate governance choice so the surface cannot produce a screenshottable/shareable "value-ranked" link that reads more durable than this EXPERIMENTAL surface. URL/shareable persistence is deferred to a later increment.
- **Responsive / a11y:** desktop-first with basic non-overlap responsiveness. Sticky toolbar stays in normal DOM/focus order; `role="status"` reserved for real state changes (e.g., filtered-zero notice), NOT for the static disclaimer; controls have explicit labels; group headings are semantic without hiding row trust cells.

## 9. Data flow

Inc2 fetch/Zod/state-machine is unchanged (mount → `fetch` → `zRosterAuditResponse.parse`). Task A adds, after a successful parse, a transform whose shape **differs for flat vs grouped views** so that grouping is never a global re-sort (Codex review finding 1):

- **Flat view (`groupBy = none`):** `applyFilter(players, {positionFilter, prospectFilter})` → `applySort(filtered, sortKey)` → render.
- **Grouped view (`groupBy = position | depreciation-band`):** `applyFilter(...)` → **`applyGroup(filtered, groupBy)`** (assigns rows to groups; emits groups in the deterministic group order of §6, independent of the active sort) → **`applySort` applied within each group only** → render grouped sections.

With default state (`sortKey = none`, `groupBy = none`) the flat chain is identity-preserving (backend order). The 200-active / 200-degraded / 422 / 503 / parse-error / empty states from Inc2 are unchanged; controls render only in the success (200 active/degraded) path.

## 10. Testing (cockpit TDD: Codex RED → Claude GREEN → dual-CLEAR)

- **Pure transform unit tests** (`rosterTransform.ts`): each sort comparator incl. null-last placement and tie-break order; stability (equal-key preserves input order); each filter incl. empty-position→All and zero-result; grouping incl. producer-token→label map and the "Missing age signal" bucket rendered last; default state = identity (backend order preserved).
- **Faithful-default test:** with default UI state, rendered row order equals `response.players` order (D1 guard).
- **Sort tests:** each sort reorders correctly; null/missing rows visible and last; xVAR negative below positive, null last.
- **Filter tests:** position multi-select; empty selection = All (not blank); prospect/active; filtered-out count + reset; filtered-zero shows the explicit "filters produced no rows" state (not the generic empty-state) with header/disclaimer preserved.
- **Group tests:** Position and Depreciation-band grouping; per-token labels; missing bucket last; within-group order preserved (and follows active sort when set); row trust cells present in grouped render.
- **Group-order determinism (Codex finding 1):** "Group by Position + Sort xVAR desc" preserves the deterministic group order (first-seen backend order for Position; producer-token severity order for Depreciation-band, Missing last) while sorting rows **inside** each group — i.e., the active sort never reorders the groups themselves.
- **Trust-preservation tests:** header status/chips/caveats/dropped-count/disclaimer present across flat/sorted/filtered/grouped states; de-emphasis is styling-only (does not change order); compact Experimental disclaimer present **with the controls** while the full header stays mounted.
- **Governance/neutral-copy:** control labels and group headings contain no verdict/action vocabulary; FE banned-vocabulary gate clean.
- **No-regression:** full FE gate (typecheck / lint / vitest / banned-language / build) green; full Python suite green; **OpenAPI drift guard untouched** (no contract change); `PlayerInspector` / `TrustStrip` / Inc1 backend unchanged.

## 11. Scope / non-goals (YAGNI)

- **IN:** client-side single-active sort (4 keys incl. opt-in xVAR), Position + Prospect/Active filters, opt-in None/Position/Depreciation-band grouping, sticky controls toolbar with persistent Experimental disclaimer, local-state-only, full trust preservation, partial-view guards.
- **OUT (deferred):** Contender-vs-Rebuilding grouping (out-of-contract; needs a backend posture join + its own contract decision), value-band filter/grouping (tiering risk), trust-hide filter, user-composed multi-sort, URL/shareable state, mobile polish, any mutation/action, market lane (none in contract), decision/verdict framing, changes to `PlayerInspector`/`TrustStrip`/backend.

## 12. Governance

- David mandated "poll each, then draft" (2026-06-19); all 6 pre-spec decisions were independently cockpit-CONCURRED by Codex (technical) + Gemini (governance) + Claude (repo/exec). David approved the consolidated design **synthesis** and authorized routing this spec through the cockpit; this v1/v2 spec is **under cockpit review and awaits David's review + authorization before any commit or implementation** (no implied approval of the written spec doc as final).
- Read-only Roster Audit HOLD lift covers Inc3 (David-confirmed). No other frontend work authorized.
- No backend / contract / model / Engine-A / Engine-B / training / market change. `decision_supported` remains `Literal[False]` (consumed, never overridden). Frontend HOLD otherwise intact.
- Build via the cockpit cycle: this spec → dual-CLEAR → implementation plan → Codex-RED / Claude-GREEN TDD → dual-CLEAR per task → David-authorized commit → zero-divergence audit, identical to Inc1/Inc2.

## 13. Acceptance criteria

- **AC-1 (faithful default):** default UI state renders `response.players` in backend order with no client re-sort (D1).
- **AC-2 (sort):** each of the 4 sorts orders correctly with internal null-safe multi-key tie-breaking; null/missing rows visible and last; xVAR negatives below positives, nulls last; single active sort only.
- **AC-3 (filter):** Position multi-select + Prospect/Active toggle subset correctly; empty position = All (never blank); active filters show filtered-out count + reset; filtered-zero shows the explicit "filters produced no rows" state (distinct from data-absence) with header/disclaimer preserved; no trust-hide filter exists.
- **AC-4 (group):** opt-in None/Position/Depreciation-band; depreciation-band uses the producer `signal` token → neutral label (Option P) with no frontend threshold math; "Missing age signal" bucket last; **group order is deterministic and independent of the active sort** (first-seen backend order for Position; producer-token severity order for Depreciation-band); within-group order preserved / follows active sort within each group only; row trust cells preserved in grouped render.
- **AC-5 (trust preservation):** all Inc2 trust surfacing persists across every interactive state; de-emphasis is styling-only and never reorders; compact Experimental disclaimer present in the sticky controls region while the full header stays mounted; no new degraded banner.
- **AC-6 (controls UX / state):** sticky toolbar; dropdown sort/group controls; local component state only (resets on reload; no URL/shareable state); a11y — normal focus order, `role="status"` only for real state changes, static disclaimer not repeatedly announced.
- **AC-7 (no false certainty / neutral copy):** no verdict/action vocabulary in labels/headings; FE banned-vocabulary gate clean; `decision_supported` never overridden; xVAR sort numeric-only/neutral-label/Experimental.
- **AC-8 (no regression / scope):** full FE gate + full Python suite green; OpenAPI drift guard untouched; no backend/contract/model change; `PlayerInspector`/`TrustStrip` unchanged; Contender-vs-Rebuilding grouping and value-band controls absent (deferred).
