# Codex Cross-Read: Frontend Recommendation Synthesis

Date: 2026-05-25
Author: Codex
Scope: Cross-read of `claude-frontend-recommendation.md`, `gemini-frontend-recommendation.md`, and `codex-frontend-recommendation.md`. This is synthesis only, not the merged frontend design.

## Executive Summary

All three recommendations converge on the same product: Dynasty Genius should become an "Honest Terminal" - a dense, calm, expert cockpit over governed PVO/API outputs, with model and market physically separated, uncertainty visible, counterarguments required, and no verdict/action language.

The material disagreement is implementation strategy:

- Claude: server-rendered, Python-first `FastAPI + Jinja2 + HTMX + Alpine + Tailwind + Observable Plot`, with a narrow React island only if Trade Lab state demands it.
- Codex: Vite React TypeScript static bundle served by FastAPI, with Zod/TanStack/Radix-style components and constrained GenUI later.
- Gemini: Next.js App Router + Vercel AI SDK UI mode + shadcn/Radix + structured GenUI as a central architecture, backed by DuckDB/Parquet.

My cross-read conclusion: the merge should carry the shared product doctrine from all three, Claude's invariant/governance discipline, Gemini's closed-schema GenUI and streaming-layout safety concepts, and Codex's repo-grounded FastAPI/PVO-first sequencing. The final stack decision remains the only real unresolved strategic fork.

## Robust Consensus

### Product Philosophy

All three agree the frontend is not a consumer fantasy dashboard. It is a single-user analytical cockpit for David's dynasty decisions.

Shared principles:

- "Honest Terminal" / cockpit framing.
- Dense, repeat-use, expert UI over first-use friendliness.
- No marketing landing page.
- No gamification, celebratory states, trade grades, or verdict badges.
- The UI should show evidence and uncertainty, not tell David what to do.

### Model vs. Market Separation

All three make model/market separation a central design invariant.

Consensus:

- Model outputs and market price discovery must be in separate visual lanes.
- No blended score.
- Market data is context only and never a model input.
- Divergence is a third explanatory element, not a combined value.
- Trade Lab is the highest-risk surface for leakage and false verdicts.

### Trust, Uncertainty, And Counterargument

All three make trust state and uncertainty first-class:

- `decision_supported=false` must be visible, not hidden.
- Experimental or stale surfaces need a persistent degraded treatment.
- Every strong signal should include counterargument/caveats.
- Trust/backtest visibility is a core product surface, not later polish.
- Single-point estimates are dangerous without ranges, bands, or caveats.

Claude emphasizes quantile dotplots and Decision Card fields. Gemini emphasizes Morningstar-style shaded bands and clinical XAI counter-evidence. Codex emphasizes evidence-gap states and typed rendering of caveats/freshness.

### Information Architecture

The three IA models are highly compatible:

- Persistent left rail.
- Global top status/trust strip.
- Command palette.
- Right-side inspector/player detail drawer.
- Core surfaces: Command Center/Home, Roster Audit, Rookie Board, Trade Lab, League Opportunity Map, Trust/Governance, Settings.
- Research Assistant/GenUI is later and gated.

### Data Authority

All three agree the LLM or browser must not invent numbers.

Consensus:

- Player/model values come from governed backend data.
- LLMs, if used, compose layouts and explanations only.
- Numeric values must trace to backend/model/tool outputs.
- Direct market/model blending is prohibited.
- Source freshness and lineage should be visible.

## Material Divergences

### 1. Frontend Stack

This is the central split.

Claude argues for staying closest to Python:

- `FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind + Observable Plot`.
- No Node build by default.
- Component governance via Jinja macros.
- React only as a single Trade Lab island if Alpine becomes unwieldy.
- Rationale: local-first, lowest maintenance, best fit for a solo owner, avoids dependency churn.

Codex argues for a lightweight React layer over FastAPI:

- Vite + React + TypeScript static bundle served by FastAPI.
- Zod mirrors Pydantic; TanStack Query/Table for typed API and dense UI state.
- React chosen for Trade Lab state and future schema-rendered GenUI, without committing to Next.js.
- Rationale: the app already has FastAPI APIs, but the immediate UI needs richer client state than HTMX/Alpine will comfortably support.

Gemini argues for full React/Next GenUI infrastructure:

- Next.js App Router + Vercel AI SDK UI mode + shadcn/Radix.
- Zod component catalog as the center of both static and generative UI.
- DuckDB/Parquet as local analytical substrate; SQLite/Postgres for mutable state.
- Rationale: best alignment with streamable structured GenUI and React component ecosystems.

Critical read:

- Claude is strongest on maintenance and governance cost.
- Gemini is strongest on future GenUI architecture, but starts too far ahead of the current FastAPI/PVO UI need.
- Codex is the pragmatic middle: adds a frontend build step, but avoids Next.js server duplication and keeps FastAPI as authority.

### 2. Generative UI Posture

Claude is most conservative:

- Static cockpit first.
- GenUI much later, additive, David-approved, and only for 4 high-ROI workflows.
- Strongly rejects Databricks, raw JSX, Vercel RSC, and generic chatbot risk.

Codex is moderate:

- Build deterministic component catalog and API-backed surfaces first.
- Later add schema-rendered GenUI over the same catalog.
- GenUI belongs first in a Research Assistant/query workspace, not primary navigation.

Gemini is most aggressive:

- Next.js + AI SDK UI mode is a primary architectural choice.
- GenUI command console and JSON layout mapping are core, though constrained.
- Uses prompt caching, Claude Sonnet, min-height schemas, and fallback nodes as practical runtime details.

Critical read:

- All three agree on closed JSON layouts and no raw JSX/HTML.
- The disagreement is timing and centrality.
- Gemini's GenUI mechanics are useful, but its roadmap activates GenUI before the deterministic Trust Board and static surfaces are fully grounded.
- Claude/Codex better match the constitution's "frontend polish comes last" and current Phase 23 W5b repo state.

### 3. Build Order

Claude:

- App shell/component library.
- Player Card + Roster Audit.
- Trust/Backtest.
- Rookie Board.
- Trade Lab.
- League Map.
- Settings.
- GenUI later.

Codex:

- Frontend contract foundation.
- Trust Strip and Trust Surface.
- Trade Lab W5b.
- Player/PVO components.
- Roster Audit.
- Rookie Board.
- League/Market Divergence.
- Research Assistant/GenUI.

Gemini:

- Zod component catalog.
- FileReader/local storage parser layer.
- Static Trade Lab and League Pulse.
- FastAPI agent endpoint.
- GenUI activation.
- Trust Board later in Phase 4.

Critical read:

- Claude and Codex agree Trust should be early, though Codex puts Trade Lab immediately after trust because W5b is the active deferred UI.
- Gemini's Trust Board is too late given the constitution and North Star. Its FileReader/localStorage phase is also stale relative to the current served FastAPI repo state.

### 4. Data Flow And File Handling

Claude and Codex reject browser-side source authority:

- Browser should not fetch Sleeper/FantasyCalc directly.
- Browser should not own source-of-truth localStorage caches.
- FastAPI/source adapters/artifacts remain authority.

Gemini partially diverges:

- It recommends FileReader drag-and-drop zones and local storage driver in Phase 1 to bypass origin controls.
- That is internally inconsistent with its later FastAPI/Next integration and with the actual repo state.

Critical read:

- The merge should drop FileReader/localStorage as primary architecture.
- It may remain a debug/import utility only if explicitly scoped, never as the source-of-truth path.

### 5. Color System And Age Warnings

Consensus:

- Dark-first terminal.
- Reserved model and market lane colors.
- Avoid red/green verdict semantics.

Divergence:

- Claude: cool blue = model, amber = market, no green/red, avoid amber collision with position hues.
- Codex: cool cyan/blue = model, amber/gold = market, red only for hard failures.
- Gemini: indigo = model, amethyst/sage = market, gold = divergence.

Critical read:

- Claude's color-governance argument is strongest because it prevents semantic collision.
- Gemini's age-curve examples include RB cliff 28 / WR cliff 31 in Roster Audit, which conflicts with the constitution's UI warning thresholds: RB 26, WR 28, TE 30, QB 33. The merged doc should explicitly correct this.

## Single Strongest Idea From Each Recommendation

### Claude: Three Structural Contracts

Claude's strongest contribution is the explicit triad:

- Decision Card contract.
- Two-Lane contract.
- Experimental treatment.

This converts governance into component invariants instead of relying on discipline in copywriting. It should be the backbone of the merged design.

### Codex: Repo-Grounded FastAPI/PVO-First Sequencing

Codex's strongest contribution is grounding the frontend plan in actual current endpoints and artifacts:

- `/api/trade/reconcile`
- `/api/trade/reconcile/market`
- `/api/roster/audit`
- `/api/rookies/score`
- `/api/trust-surface/{position}`
- PVO fields and `decision_supported`

The merge should preserve this discipline: build deterministic API-backed surfaces first, then introduce GenUI only after the catalog and trust layer exist.

### Gemini: Closed-Schema GenUI With Runtime Safety

Gemini's strongest contribution is the operational detail for safe GenUI:

- Zod component catalog.
- JSON layout spec.
- `min_height` per component to prevent CLS.
- Fallback components on tool failure/timeouts.
- Prompt context/caching discipline.
- LLM as layout composer only.

Even if GenUI is deferred, these mechanics are valuable and should define the future GenUI appendix.

## Recommended Merge Direction

Do not merge yet, but when David directs the merge, I would recommend this synthesis:

- Product doctrine: use the shared Honest Terminal / cockpit framing.
- Invariants: adopt Claude's three structural contracts.
- Data flow: adopt Codex's FastAPI/PVO-only authority and reject browser source-fetching as primary.
- Stack: resolve explicitly between Claude's Python-first HTMX path and Codex's Vite React middle path. Gemini's full Next.js path should be reserved for a later GenUI shell only if David prioritizes runtime GenUI over local simplicity.
- GenUI: adopt Gemini's closed-schema safety model, but Codex/Claude timing: defer until deterministic surfaces, trust strip, and component catalog are stable.
- Build order: component catalog + trust surface first, then Phase 23 W5b Trade Lab, then PVO surface expansion, then constrained GenUI.
- Governance enforcement: carry Claude's banned-language linter and Codex's component/schema tests as hard gates.

## Risks To Preserve For David's Decision

- Stack choice is not cosmetic. HTMX/Jinja minimizes build complexity; Vite React improves client-state ergonomics; Next.js optimizes future GenUI at the cost of more architecture now.
- Trade Lab is both urgent and dangerous. It is the active deferred UI, but it is the easiest place to accidentally create a verdict engine.
- GenUI should not become a shortcut around trust. All three docs can support a safe GenUI path, but only if the merged spec keeps it behind the deterministic component catalog and backend tool outputs.
- The merged doc must correct stale research drift: file-only assumptions, browser-source authority, incorrect age cliffs, and any language that implies action rather than evidence.
