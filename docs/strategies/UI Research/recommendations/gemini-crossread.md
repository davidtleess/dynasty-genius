# Gemini Cross-Read Synthesis: Frontend Design Specifications

**Document Type:** Strategic Frontend Synthesis  
**Author:** Gemini (Product Manager)  
**Status:** Under Review (Independent Cross-Read Phase)  
**Authority:** PM Oversight (Cross-Agent Alignment Spec)  
**Date:** 2026-05-25  
**Grounded in:**  
- `docs/strategies/UI Research/recommendations/claude-frontend-recommendation.md`
- `docs/strategies/UI Research/recommendations/codex-frontend-recommendation.md`
- `docs/strategies/UI Research/recommendations/gemini-frontend-recommendation.md`

---

## 1. Robust Consensus Across All Three Specifications

A rigorous cross-reading of the Claude, Codex, and Gemini frontend specifications reveals deep structural and philosophical consensus. All three agents are in perfect agreement on the core characteristics of the Dynasty Genius interface, forming an unshakeable foundation for the merge:

1. **Product Stance (The "Honest Terminal"):**
   Reject all standard consumer fantasy conventions (such as KeepTradeCut "Keep/Trade/Cut" letters, "Fair Trade" badges, or simple colored tier lists). The UI must represent an institutional-grade, high-density analytical cockpit (referencing Koyfin, Bloomberg Terminal, Morningstar, and Palantir Foundry) designed for one expert user (David).

2. **The Two-Lane Contract (Visual Model-vs-Market Segregation):**
   Predictive ML evaluations (Engine B `xVAR`, `DVS`, `projections`) and crowdsourced market price discovery (FantasyCalc, KTC, ADP) must **never** be merged, averaged, or combined into composite indexes. They are visually isolated in dedicated lanes. Divergence is a derived third property expressed in neutral, quantitative language, never as a win/loss verdict.

3. **Uncertainty & Counter-Evidence as First-Class Visual Elements:**
   Every recommendation card must visually represent the underlying uncertainty of the projection (deciles, intervals, or Morningstar-style variable-thickness bands). In compliance with advanced clinical-decision-support (XAI) standards, every player card must feature a mandatory, co-located **Counter-Arguments** panel (steel-manning the downside case) and **Evidence Gaps** list.

4. **Linguistic Discipline (The Banned Vocabulary Gate):**
   Strictly ban action verbs or subjective verdicts (`buy`, `sell`, `target`, `block`, `approve`, `reject`, `win`, `loss`, `verdict`, etc.) from components and visible strings. Use neutral, quantified terms (`value surplus`, `positional deficit`, `inside normal range`).

5. **Reject Databricks & Cloud DB Spend Spikes:**
   Unanimously reject remote Databricks cloud VMs for a single-user, 10 GB dataset. Databricks compute easily drains $2,000–$5,000/month. The correct data substrate is local **DuckDB + Parquet on disk**, utilizing Polars in-process for backend ETL, and keeping Postgres/SQLite exclusively for session/history state.

6. **Generative UI Architecture:**
   Unanimously reject streaming raw HTML or JSX as a slow, stochastic, and dangerous anti-pattern. If Generative UI is introduced, it must follow **Pattern A (JSON layout composition)**, where the LLM (Claude Sonnet 4.6) acts as a layout composer, emitting a JSON schema that maps strictly to a closed, type-safe client component catalog, resolving data purely via verified backend tool calls.

7. **Core Repo Reality Alignment:**
   - The *current* served uvicorn/FastAPI architecture moots early file-only (`file://`) sandboxing workarounds (such as `FileReader` drop-zones or client-side Sleeper calls). Data must flow from FastAPI server caches.
   - The DVS scale is locked at **0–100** (Phase 14 Option C), not 0–1000 or 0–10,000.
   - Age cliff warnings use the constitutional values (RB 26, WR 28, TE 30, QB 33) in amber, not red.

---

## 2. Material Divergences & Trade-Offs

The primary disagreements are technical and architectural, representing a classic software engineering tradeoff between build-complexity, stateful interactivity, and local-first longevity.

### 2.1 The Tech Stack Split

This is the most critical fork for David's decision:

```
+---------------------------------------------------------------------------------------------------+
|                                  THE TECH STACK DECISION MATRIX                                   |
+---------------------------------------------------------------------------------------------------+
| Gemini: Next.js (React SPA)          Codex: Vite + React + TS               Claude: HTMX + Jinja  |
| ───────────────────────────          ───────────────────────               ────────────────────  |
| - Rich React ecosystem               - Highly stateful browser TUI          - Zero Node/npm tools |
| - Native AI SDK support              - Seamless FastAPI static serving      - Invariant macro files |
| - High build-tooling overhead        - Zod-to-Pydantic type contracts       - Awkward for builder state |
| - High long-term dependency rot      - Medium Node-tooling overhead         - Maximum local longevity  |
+---------------------------------------------------------------------------------------------------+
```

1. **Option A: Next.js + React 19 SPA (Gemini Proponent):**
   * *Aims:* Capitalizes on the React ecosystem and native Vercel AI SDK primitives for modular UI layout streaming.
   * *Trade-off:* High build-tooling tax, severe long-term dependency rot, and excessive complexity for a single-user FastAPI app.
2. **Option B: Vite + React + TypeScript served statically by FastAPI (Codex Proponent):**
   * *Aims:* Keeps the FastAPI server as the deployment and router authority. Uses React client-side for stateful, interactive widgets (the multi-asset Trade Lab sent/received builder, scenario saving, columns filtering) and is highly prepared for future schema-rendered components. Enforces type contracts via TypeScript/Zod mirroring of Pydantic response models.
   * *Trade-off:* Requires a local Node build and npm package management, introducing mild tooling maintenance.
3. **Option C: FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind (Claude Proponent):**
   * *Aims:* Rejects Node, npm, and build pipelines entirely, ensuring 10-year local longevity with zero dependency rot. Uses serverside HTML templates with Alpine for minor local toggles, and Observable Plot for vanilla JS charting.
   * *Trade-off:* Rendering highly stateful client interactions (like the dual-pane, reactive Trade Lab builder) in Alpine stores and partial-swapping string containers becomes extremely complex and difficult to scale.

### 2.2 Generative UI Rollout Posture
* **Gemini (Generative-First Shell):** Proposes a generative-first dashboard shell using AI SDK layouts as the primary viewport.
* **Claude / Codex (Deterministic Cockpit First, GenUI Later):** Agree that generative UI is a much-later, additive layer. We must build and verify the static, deterministic dashboard cockpit surfaces (Roster Audit, Trade Lab, Rookie Board) first. GenUI is only integrated when those surfaces have earned backtest-grade trust.

### 2.3 Visual Palette Separation
* **Claude / Codex (Colorblind-Safe Non-Cultural):** Strictly Cool Blue/Azure for Model, and Warm Amber for Market. Green and red are completely banned to prevent win/loss verdict biases. TE/position pills take non-amber hues to avoid colliding with the market signal.
* **Gemini:** Proposed Indigo for Model, Sage/Amethyst for Market, and Gold for Divergence.

---

## 3. Strongest Ideas Worth Carrying into the Merge

Each agent has contributed outstanding architectural breakthroughs that should be preserved in the final merged Frontend Design Document.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
|                                   THE MERGE CORE                                 |
├─────────────────────────┬───────────────────────────────┬────────────────────────┤
|      Claude's Core      |         Codex's Core          |     Gemini's Core      |
├─────────────────────────┼───────────────────────────────┼────────────────────────┤
| - Banned-Language Lint  | - Vite + React + TS static    | - Claude Sonnet 4.6    |
| - Three Invariant Specs | - Zod-to-Pydantic contracts   |   Structured JSON      |
| - Non-colliding Palette | - Trust Surface built Phase 1 | - Ephemeral Caching    |
└─────────────────────────┴───────────────────────────────┴────────────────────────┘
```

### 3.1 Claude's Strongest Ideas
* **Automated CI Banned-Language Linter:** Enforce linguistic rules mechanically rather than relying on human discipline. Scan visible source strings and UI components in CI/pre-commit for banned verdict tokens (`buy`, `sell`, `win`, `loss`, `verdict`, etc.) and block commits that fail.
* **Three Invariant Structural Contracts:**
  - *The Decision Card contract:* Component properties require `signal`, `uncertainty`, `counter_argument`, and `horizon`—or the card auto-renders in a de-saturated "Experimental" frame.
  - *The Two-Lane contract:* Hardcoded separate visual containers for model and market.
  - *The Experimental treatment:* Visibly de-rates surfaces that have not yet earned backtest validation.
* **The Non-Colliding Color Palette:** Lock the cool-blue (Model) and warm-amber (Market/Cliffs) signal axes, and strictly prevent position accents (specifically TE) from utilizing amber, avoiding semantic color overloading.

### 3.2 Codex's Strongest Ideas
* **Vite + React + TypeScript Static Bundle Served by FastAPI:** This is the most practical middle-ground. It allows David to build highly stateful interactive features (dynamic Trade Lab, filtering) using standard React without Next.js complexity, serving everything directly from the existing FastAPI server.
* **Zod-to-Pydantic Mirroring:** Generates TypeScript Zod schemas directly from FastAPI Pydantic models. This guarantees the browser UI strictly conforms to model/PVO output schemas, preventing fuzzy-matching or data misalignment failures in the UI.
* **Trust Surface Built as Phase 1:** Build the global trust strip and trust/backtest dashboard *first*, as it defines the decision-support promotion states and controls the de-saturation treatment for the other surfaces.

### 3.3 Gemini's Strongest Ideas
* **Claude Sonnet 4.6 Structured JSON Layout Composition:** Designing the orchestrator to compose layouts strictly as type-safe JSON specs, mapping to a closed client component catalog.
* **Ephemeral 5-Minute Prompt Caching:** Storing the `LeagueContext` block in the cached prompt prefix, reducing marginal LLM costs by 90% and making real-time generative layouts highly economical (~$30–$55/month).

---

## 4. Proposed Synthesis Solution (PM Stance)

Through the PM lens, the optimal path is a **static-first, type-safe React bundle serving the "Honest Terminal," with a phased, constrained Generative UI exploration deferred to later sprints.**

1. **Stack Decision:** We adopt **Codex's Vite + React + TypeScript static serving** stack. It provides a robust browser runtime for the complex, stateful Trade Lab builder and future layout compositions, while keeping FastAPI as the master data/API authority, completely bypassing Next.js Node-routing overhead.
2. **Visual & Structural Design:** We adopt **Claude's colorblind-safe Blue/Amber palette, the three invariant component contracts, and the automated CI banned-language linter**. This guarantees constitutional compliance in code, not in copy.
3. **Information Flow:** We adopt **Gemini's 5-minute ephemeral prompt caching and structured JSON catalog composition** for future Generative UI widgets, ensuring high-fidelity layouts remain highly cost-efficient and hallucination-free.
