# Frontend Design Spec — Dynasty Genius "Honest Terminal" Cockpit

**Status: DRAFT (for cockpit dual-CLEAR)**
**Date:** 2026-06-03 · **Author:** Claude Code · **Type:** Design spec — the build contract for the Phase-12 frontend

---

## 0. Scope & Standing Constraints

This is the **merged Frontend Design spec** deferred by the 2026-05-25 frontend-stack ADR and unblocked by its 2026-06-03 hold-lift addendum (`docs/validation/2026-05-25-frontend-stack-consensus-decision.md`). It ratifies the converged multi-agent round in `docs/strategies/UI Research/recommendations/` and encodes it as a build contract.

**Binding inputs (do not relitigate):**
- ADR + addendum: Stack A (Vite + React + TypeScript, FastAPI serves the built static bundle as a mount/fallback — never a route rewrite); **minimal RUNTIME deps = React + Vite + TS + Zod only; Tailwind BARRED → plain CSS variables**; **cockpit primitives + ⌘K is the first surface**; Hey API codegen comes *after* the shell; Biome frontend-only; `rookie_board.html` retained standalone (`scripts/serve_rookie_board.py`) until a React equivalent earns displacement via its own ADR.
- **Runtime vs dev/build tooling (Codex finding 1):** the "minimal deps = four" budget is **runtime**. Dev/build tooling — **Biome + Vitest** — is separate, **dev-only, exact-pinned, zero runtime impact**. Future component-test libs (`@testing-library/react`, `jsdom`, browser-mode) must be named in the scaffold plan or ADR'd as **dev-only**; they never enter the runtime budget.
- Constitution: *"No David-facing surface implies decision-grade confidence before the model, source freshness, and validation gates justify it."* This spec **encodes** that guardrail; it does not relax it.
- Each new runtime dependency beyond the four requires its own ADR.

**This spec is planning only.** It does not authorize a dependency install; scaffolding follows a separate plan + cockpit TDD, and this spec must be committed first.

---

## 1. Product Doctrine — the Honest Terminal

Dynasty Genius is a **dense, calm, single-user analytical cockpit** for repeat expert use — a decision-support *laboratory*, not a verdict engine. It maps model evidence, overlays market context, steel-mans counter-arguments, and shows caveats explicitly. It is **not** a consumer fantasy tool, a chatbot, a marketing site, a news feed, or a "today's recommended actions" surface.

It never tells David what to do, never emits win/loss grades, and never disguises uncertainty.

## 2. The Three Structural Contracts (the spine)

Encoded in component **type signatures**, not just copy — a surface that can't satisfy the contract fails typecheck or auto-degrades to Experimental.

1. **Decision Evidence Card** — any advisory surface must render: the model evidence, its uncertainty, the market overlay, ≥1 steel-manned counter-argument + explicit evidence gaps, and a universal non-dismissible `decision_supported` state. Missing counter-argument/caveats ⇒ auto-degrade to Experimental framing.
2. **Two-Lane contract** — model values (Engine A/B, *both* are "model") and market values (FantasyCalc/consensus) live in **separate physical tracks**, never blended/averaged. **Divergence** is a third *derived* element in neutral language ("Model +14% vs Market"), never a buy/sell rating.
3. **Experimental treatment** — pre-model / stale / unavailable / low-sample states have explicit visual treatments; nothing renders as decision-grade until earned.

## 3. Settled Invariants (the 13-point backbone — protect from drift)

Analytical-cockpit framing · strict two-lane · divergence-as-factual-context · uncertainty-first (range bars / shaded bands / quantile dotplots) · universal `decision_supported=false` · mandatory counter-arguments + caveats · constitutional age cliffs (RB 26 / WR 28 / TE 30 / QB 33, amber) · app-shell IA (left rail, sticky top trust strip, ⌘K, right inspector) · core surfaces inventory (§6) · reject Databricks (the frontend is read-only over FastAPI JSON and commits to **no analytics data-substrate of its own** — DuckDB/Parquet is a *backend* concern, not a frontend-spec commitment; **no server-side mutable-UI-state store in v1** — ephemeral client state / `localStorage` only, a persistent store deferred to a surface that earns it via ADR) · constrained JSON-schema generative-UI (deferred, never invents numbers) · read-only over PVO · Trust/backtest surface built early.

## 4. Visual System (Tailwind-free)

- **Tokens as plain CSS custom properties** (OKLCH values), no Tailwind. A single `tokens.css` is the design-system source.
- **Palette:** cool **blue = model**, **amber = market** (+ amber reserved for cliff warnings); **no green/red** (no verdict colors); position hues orthogonal to the model/market axis.
- **DVS 0–100** (constitutional scale). Cliffs amber at the constitutional ages.
- **Uncertainty visuals first-class:** point estimates always carry a range bar / Morningstar-style shaded band (thickness = uncertainty) or frequency-framed quantile dotplot.

## 5. App Shell & Data Contract

- **Shell:** persistent left-rail nav (~7–8 pages), sticky top **Trust strip** (model grade + freshness, governs confidence everywhere), global **⌘K** command bar, right-side collapsible **player inspector**.
- **Data authority:** the browser and any future LLM **never compute or invent** player values, DVS, xVAR, or identity matches. The frontend **renders FastAPI/PVO endpoint values only**.
- **Contract codegen:** **FastAPI OpenAPI is the single source of truth.** Hey API (`@hey-api/openapi-ts`, pinned) generates TS types + Zod validators under the frontend tree; generated code is a build artifact, never hand-edited. Validate responses at the SDK boundary. (Real route families today: reconcile / reconcile-market, roster audit, trade evaluate, rookie score, per-position model-card / trust-surface — the generated client reflects the live OpenAPI, not a hand-list.)
- **Serving (Codex finding 2 — pinned exclusions):** `vite build` → static bundle; FastAPI mounts it as a **fallback** for non-API, non-legacy paths only. The SPA catch-all must **not shadow `/api/*`, `/openapi.json`, `/docs`, `/redoc`, or built asset paths**, and must **not touch the standalone `rookie_board.html`** (served by its own `scripts/serve_rookie_board.py` process, outside the main app). Mount ordering puts the SPA fallback last, and **contract tests must assert these exclusions** when scaffolding.

## 6. Core Surfaces & Build Sequence

Inventory: Command Center · Roster Audit · Rookie Board · Player Detail · Trade Lab · League Opportunity Map · Trust & Freshness · Settings.

**Build order (locked):**
1. **Shell + component catalog + ⌘K + Trust strip** — the proving ground for the three contracts, the palette, and the codegen seam. *(First surface; no stateful Trade Lab yet.)*
2. **Trade Lab** (the Phase-23 W5b deferred backend task; genuinely stateful — the reason for React).
3. Player Detail / Roster Audit / Rookie Board (React) / League Opportunity Map.
4. **(Deferred, David-approved later)** constrained generative-UI.

`rookie_board.html` remains the **live draft tool** throughout until a React Rookie Board earns displacement via ADR.

## 7. Governance-in-UI (mechanical, not advisory)

- **Banned-language CI linter (Codex finding 4 — scoped)** — the constitution's banned David-facing patterns (rookie `confidence`/`dynasty_tier`, trade `verdict`/side-totals-before-validated-bands, roster `action` instructions) are enforced **in CI** against **authored frontend source + UI-rendered string literals**. **Generated clients (Hey API output) are EXCLUDED** — backend schema field names (e.g. a `difference`/`action`/`verdict`-shaped API field) must not false-positive. The rule fails any *component that renders* a banned field/label, not the generated type that carries it.
- `decision_supported=false` is a visual state, universal + non-dismissible, until earned out.
- Model/market separation enforced by **component structure**, not copy.
- Trust/backtest state controls surface confidence everywhere.

## 8. Deferred — Generative UI (future ADR, not v1)

LLM as a **layout composer only**: emits a **closed JSON schema** validated client-side → mapped to a registered, type-safe component catalog. Numbers come only from tool calls / PVO, never the model. `min_height`/CLS guards, fallback nodes, `LeagueContext` system-prompt block. Cost envelope to be re-estimated at proposal time. **Not built in v1.**

## 9. Resolved (cockpit, 2026-06-03 — Codex + Gemini concur)

1. **Charting:** **hand-rolled SVG / CSS** for the v1 shell. No Tremor/Recharts/Observable Plot/Visx — each would need its own ADR. Uncertainty visuals (range bars, shaded bands, dotplots) render in SVG/CSS over the OKLCH tokens.
2. **State/query:** start with **React + platform `fetch` + the generated Hey API client**. TanStack Query/Router only when Trade Lab's state genuinely demands it, via its own ADR — not in the v1 scaffold.
3. **Test/lint harness:** **Biome + Vitest in the initial scaffold**, classified as **dev/build tooling (dev-only, exact-pinned, zero runtime impact)** — not part of the four-dep runtime budget (see §0).

---

**Next after dual-CLEAR:** a build plan (`docs/superpowers/plans/`) for surface 1 (shell + ⌘K + Trust strip), then cockpit TDD scaffolding. No dependency install until this spec is committed.
