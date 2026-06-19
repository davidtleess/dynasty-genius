# Roster Audit — Increment 2: Read-Only UI Surface — Design Spec

**Date:** 2026-06-19
**Status:** v1 (brainstormed with David; 4 decisions cockpit-CONCURRED pre-spec)
**Authored by:** Claude Code
**Phase:** Phase 12 (Frontend) decision-surface sequence — Roster Audit Increment 2 (read-only UI over the Inc1-hardened contract)
**Predecessor:** Increment 1 (API contract hardening) — MERGED `454b8e7`. Consumes `RosterAuditResponse` as-is; no backend/contract change.
**Frontend HOLD:** David lifted the binding Phase-12 HOLD **scoped to this read-only Roster Audit surface only** (2026-06-19). The rest of the HOLD stands; this lift authorizes no other frontend build, no new runtime dependencies.

---

## 1. Goal

Wire the existing empty **"Roster Audit"** nav slot in `AppShell` into a **read-only, faithful, honesty-first** UI surface over `GET /api/roster/audit`. It renders the typed `RosterAuditResponse` (the Inc1-T6 generated client type) so David can see his rostered skill players, each player's model status / scores / age-cliff signal / caveats, the QB context cards, and the envelope's honest trust/degraded/failure state — **without** any verdict, recommendation, or decision-grade framing.

## 2. Architecture

- **Stack A** (locked ADR): Vite + React + TS served by FastAPI. New surface folder `frontend/src/roster/`, mirroring `trade/`, `trust/`, `player/`.
- **Shell wiring:** `AppShell.tsx` renders `<RosterAudit />` when `activeSurface === "Roster Audit"` (the nav button + command already exist; only the render branch is added).
- **Data source:** a manual `fetch("/api/roster/audit")` whose body is validated through the generated **Zod** schema `zRosterAuditResponse` (alias `zAuditRosterApiRosterAuditGetResponse`) and typed via the generated `RosterAuditResponse`. This matches the existing surfaces' pattern — `TrustConsole.tsx` uses `await fetch(...)` + `zTrustSurfaceResponse.parse(...)`. NOTE: the `@hey-api` codegen emits **types + Zod schemas only**; there is **no callable generated client function** for this (or any) endpoint.
- **Single model-only lane:** Inc1's contract is market-free (no `market_overlay`), so this surface is one model lane — explicitly NOT the two-lane (model/market) pattern of Trade Lab / Player Detail.
- **No new runtime dependencies; no backend/contract/model change.**

## 3. Components

Each component has one purpose, a typed prop interface, and a colocated `.test.jsx`.

- **`RosterAudit.tsx`** — container. Fetches the audit on mount; owns the state machine (§6); renders `RosterAuditHeader` + `RosterAuditTable` + `QbContextSection` on success, or a full-surface state from `RosterAuditStates` on loading / 422 / 503 / parse-error. Never renders a blank/empty table on failure.
- **`RosterAuditHeader.tsx`** — honesty header. Props: `status`, `model_status_by_position`, `caveats`, `dropped_player_count`. Renders overall `status`, one `model_status` chip per position present, the envelope caveats, the dropped-row count, and a prominent **"Experimental — not decision-grade"** disclaimer (the surface-level expression of `decision_supported=False`).
- **`RosterAuditTable.tsx`** + **`RosterAuditRow.tsx`** — the faithful table. Rows in the contract's returned order (aging urgency; no client re-sort). Primary columns: **Player · Pos · Team · Age · model_grade · model_status · DVS (+dvs_pct) or "—" · age-cliff signal (+years_to_cliff) · signal_completeness · caveats indicator.** Per-row: a `model_status_applies` chip; rows whose position is EXPERIMENTAL (or `model_status_applies=false`) are visually **de-emphasized**. Inline **row-expand** reveals detail: `counter_argument`, `top_drivers`, `risk_flags`, `projection_1y/2y/3y`, `xvar`, `liquidity_risk`, `biological_debt_score`, full `caveats`. Reuse `player/EvidenceSection` + `lib/trustCopy` where they fit; do not fork their logic.
- **`QbContextSection.tsx`** — renders `qb_context_cards` (epa_per_dropback, cpoe, dakota, dropback_count, pass_attempts, annotations, caveats), each labeled **"context signal — not decision-grade"** (`context_role="context_signal"`).
- **`RosterAuditStates.tsx`** — the non-success states: loading skeleton; **422** → "Roster not configured"; **503** → "Roster data unavailable"; Zod/parse or network error → generic honest error; honest **empty roster** ("No rostered skill players").
- **`RosterAudit.css`** + existing `styles/tokens.css` (no new design tokens unless justified).

## 4. Primary columns & row-expand detail

(See §3 `RosterAuditTable`.) Scores render only when present; absent scores show "—" with the player's own caveat explaining why (e.g. PRE_MODEL / EXPERIMENTAL). The caveats indicator summarizes count and reveals the full list on expand.

## 5. Honesty / no-false-certainty posture (governance core)

- **Disclaimer + markers:** the header disclaimer, per-position `model_status` chips, per-row `model_status_applies` chip, and EXPERIMENTAL de-emphasis together carry `decision_supported=False` to the surface. This is the "Mandate Honest Uncertainty over False Certainty" expression.
- **No verdicts:** the surface presents raw signals/scores/caveats as DATA, never as hold/sell/replace/develop advice. No verdict vocabulary, no derived recommendation, no ranking-as-instruction.
- **Neutral copy + visual emphasis (hard requirement, cockpit-raised):** copy and visual weight must NOT make DVS + age-cliff signal *read* as a recommendation. Column labels, chips, and emphasis stay neutral/descriptive. The spec's acceptance tests assert neutral labels; design review checks emphasis.
- **Banned-language is server-solved (Inc1):** the contract already suppresses banned David-facing vocabulary (free-text via `_evidence_list_field`, tokens via SAFE_TOKENS). The UI **renders contract text verbatim** and adds only neutral labels. The FE banned-vocabulary gate (`shell/banned_vocabulary.json` + the existing lint/test) is a **test/lint guard, NOT a runtime suppressor** — the UI does not filter or rewrite contract text at runtime.

## 6. Data flow & state machine

Mount → `fetch("/api/roster/audit")`, then `zRosterAuditResponse.parse(await res.json())` (manual fetch + Zod parse, per the existing surfaces).

- **HTTP 200 + parse OK, `status="active"`** → header (active) + table + QB section.
- **HTTP 200 + parse OK, `status="degraded"`** → SAME table view, with the header in its degraded presentation (degraded banner, dropped-count, caveats). Degraded is renderable-but-flagged — explicitly distinct from 503.
- **HTTP 422** → "Roster not configured" full-surface state. Mapped on the **HTTP status only** — the UI shows a generic message and does **not** parse or render the backend `detail` body, so it cannot break on an unexpected detail shape (maximally defensive).
- **HTTP 503** → "Roster data unavailable" full-surface state (same HTTP-status-only mapping, no detail-shape dependency).
- **Zod parse failure / network error** → generic honest error state (never silently render partial/garbage).
- **200 + `players` empty (status active)** → honest "No rostered skill players" state, not a crash.

All states are read-only. No mutation, no retry-with-side-effects beyond a manual refresh.

## 7. Testing

Colocated vitest `.test.jsx` per the existing surface pattern:

- Table renders from a `RosterAuditResponse` fixture; primary columns + per-row `model_status_applies` chip + EXPERIMENTAL de-emphasis.
- Honesty header: `status`, per-position `model_status` chips, caveats, dropped-count, and the "not decision-grade" disclaimer all present.
- Row-expand reveals the detail fields; collapses correctly.
- State machine: `status="degraded"` (200) renders the table+degraded banner; 422 / 503 / parse-error / empty each render their honest full-surface state.
- Neutral-copy assertion: column labels / chips contain no verdict vocabulary; FE banned-vocabulary gate clean.
- **Real-PVO coverage (closes the logged Inc1 follow-up — two halves, stated precisely):**
  - *UI half (FE):* at least one vitest fixture is shaped like a real `assemble_pvo()`/Inc1 `RosterAuditResponse` (flat PVO fields, free-text caveats, market fields already excluded), proving the surface renders the true producer shape.
  - *Backend half (Python):* a small permanent integration test asserting a real `assemble_pvo()`-shaped row maps through `assemble_response()` without drop/leak (flat fields, free-text caveats survive, `market_overlay` excluded). This is the actual Inc1 follow-up — a FE fixture alone does NOT prove the backend mapping. Both halves together close it.
- The full FE gate (typecheck / lint / vitest / banned-language / build) AND the full Python suite stay green; the OpenAPI drift guard remains untouched (no contract change).

## 8. Scope / non-goals (YAGNI)

- **IN:** read-only faithful table; honesty header; inline row-expand; QB context section; loading/422/503/degraded/parse-error/empty states; contract aging-urgency order; real-PVO-shaped fixture.
- **OUT (deferred):** column sort, position filter, any mutation/action, market lane (none in contract), decision/verdict framing, cross-surface navigation changes beyond rendering the existing nav slot, changes to the shared `PlayerInspector`/`TrustStrip`.

## 9. Governance

- Scoped frontend-HOLD lift (David-authorized 2026-06-19, this read-only surface only) recorded here + in `AGENT_SYNC.md`. No other frontend work is authorized by this lift.
- No backend / contract / model / Engine-A / Engine-B / training / market change. `decision_supported` remains `Literal[False]` (consumed, never overridden). Frontend HOLD otherwise intact.
- Build via the cockpit cycle: this spec → dual-CLEAR → implementation plan → Codex-RED / Claude-GREEN TDD → dual-CLEAR per task → David-authorized commit → zero-divergence audit, identical to Inc1.

## 10. Acceptance criteria

- **AC-1 (faithful render):** all `players` render as rows in contract order with the primary columns; scores absent → "—" + caveat.
- **AC-2 (honest trust/degraded):** header shows `status`, per-position `model_status`, caveats, `dropped_player_count`, disclaimer; `status="degraded"` renders table+banner; 422/503/parse-error/empty render distinct honest full-surface states (never blank).
- **AC-3 (no false certainty):** per-row `model_status_applies` chip + EXPERIMENTAL de-emphasis present; neutral copy/emphasis (no verdict vocabulary); FE banned-vocabulary gate clean; disclaimer surfaces `decision_supported=False`.
- **AC-4 (row-expand detail):** expand reveals counter_argument / top_drivers / risk_flags / projections / xvar / liquidity_risk / biological_debt_score / full caveats; rendered verbatim (no runtime suppression).
- **AC-5 (QB context):** `qb_context_cards` render in their own section, labeled context-signal / not-decision-grade.
- **AC-6 (boundary robustness):** Zod-parse at the boundary; 422/503 mapped on HTTP status only (generic messages, no `detail`-shape dependency); parse failure / network error → honest error state, never a partial/garbage render.
- **AC-7 (real-PVO coverage, both halves):** a real-`assemble_pvo()`-shaped FE fixture renders correctly (UI half) AND a permanent Python integration test asserts a real `assemble_pvo()`-shaped row maps through `assemble_response()` with no drop/leak and free-text caveats surviving (backend half) — together closing the Inc1 follow-up.
- **AC-8 (no regression / scope):** full FE gate green; OpenAPI drift guard untouched; no backend/contract change; `PlayerInspector`/`TrustStrip` unchanged.
