# Unified Product Manager Synthesis: Frontend Design Convergence

**Document Type:** Strategic Frontend Synthesis and Convergence Spec  
**Author:** Gemini (Product Manager)  
**Status:** Converged Recommendation (Cross-Read Synthesis Phase)  
**Authority:** PM Oversight (Authoritative Spec Input)  
**Date:** 2026-05-25  
**Grounded in:**  
- `claude-frontend-recommendation.md` / `claude-crossread.md`
- `codex-frontend-recommendation.md` / `codex-crossread.md`
- `gemini-frontend-recommendation.md` / `gemini-crossread.md`

---

## 1. Executive Summary: The "Unified Honest Terminal"

A comprehensive cross-analysis of all three independent frontend recommendations and cross-read syntheses reveals an exceptionally strong, multi-agent convergence. Working independently, Claude Code, Codex, and Gemini have outlined a singular product vision: **Dynasty Genius must be built as an institutional-grade, dense, calm, expert "Honest Terminal."**

The frontend will function as a **decision-support laboratory**, not a verdict engine. It will never tell David what to do, output binary win/loss grades, or disguise uncertainty. Instead, it will map model evidence, overlay market context, steel-man counter-arguments, and display caveats explicitly.

```
+--------------------------------------------------------------------------------------+
|                                  THE CONVERGENCE MAP                                 |
+--------------------------------------------------------------------------------------+
|  Product Soul:          Bloomberg-dense analytical cockpit                           |
|  Visual Invariants:     Model Lane (Blue) | Market Lane (Amber) Segmented Tracks     |
|  Uncertainty Engine:    Morningstar uncertainty bands + Quantile dotplots + Cliffs   |
|  Governance Gates:      Banned-language CI linter + universal decision_supported=F   |
|  Data Substrate:        DuckDB + local Parquet on disk (Skip Databricks)             |
|  Tech Stack Fork:       FastAPI static serving -> Vite + React + TS (Pragmatic Middle)|
+--------------------------------------------------------------------------------------+
```

This document converges the three perspectives into a single, concrete PM recommendation to feed the final Frontend Design merge.

---

## 2. Settled Consensus: The 13-Point Backbone

The following thirteen principles are unanimously agreed upon by all three agents across their recommendations and cross-reads. **The merge must treat these points as settled, carry them forward as system invariants, and protect them from future design drift:**

1. **Analytical Cockpit Framing:** The app is a dense, high-signal, single-user dashboard designed for repeat, expert use by David. It strictly avoids marketing-style landing pages, news feeds, gamified layouts, or "today's recommended actions."
2. **Strict Two-Lane Visual Contract:** Proprietary ML model values and consensus market prices exist in separate physical tracks (never blended or averaged).
3. **Divergence as Factual Context:** Divergence is a third, derived element displaying raw mathematical variance between tracks in neutral language (e.g. "Model +14% over Market"), never as a buy/sell rating.
4. **Uncertainty as a First-Class Citizen:** point estimates must be accompanied by range bars, Morningstar-style shaded bands (thickness = uncertainty), or frequency-framed quantile dotplots.
5. **Universal `decision_supported: false` Visibility:** The chip is universal, highly visible, and non-dismissible on all advisory surfaces, acting as a visual state rather than a footnote.
6. **Mandatory Counter-Arguments & Caveats:** Every decision or player card requires a dedicated, visible panel containing steel-manned counter-arguments and explicit evidence gaps. If missing, the card auto-degrades to an Experimental frame.
7. **Constitutional Age Cliffs:** Roster warnings use the constitution's locked thresholds in amber: RB 26, WR 28, TE 30, QB 33.
8. **App Shell IA:** Persistent left-rail nav (~7–8 pages), sticky top trust strip, global keyboard command bar (⌘K), and right-side collapsible player inspector panel.
9. **Core Surfaces Inventory:** Command Center, Roster Audit, Rookie Board, Player Detail, Trade Lab, League Opportunity Map, Trust & Freshness, Settings.
10. **Reject Databricks in the Frontend:** Fully reject remote Databricks Premium workspaces. The data substrate is local **DuckDB + Parquet on disk** for analytical queries, and SQLite/Postgres for mutable UI state.
11. **Constrained JSON-Schema Generative UI:** Generative UI must only compose layouts, never invent numbers. The LLM (Claude Sonnet 4.6) acts as a layout composer, emitting a JSON schema validated by the client and mapped to a closed, type-safe component catalog.
12. **Read-Only over PVO:** The frontend never computes models, DVS, xVAR, or identity matching. It renders FastAPI endpoint values.
13. **Trust & Backtest Surface Built Early:** The backtest validation and model-card dashboard governs the trust strip used everywhere else, and must be established early.

---

## 3. Synthesis of Key Divergences: Agree vs. Disagree

The cross-reads reveal highly mature alignments on how the remaining tech stack, timing, and palette divergences should be reconciled.

### 3.1 The Tech Stack: Settle on the Pragmatic Middle

The central stack split is resolved by analyzing client-side state requirements for the Trade Lab:

* **Claude's HTMX + Jinja2 + Alpine** stack optimizes for local longevity and zero dependency rot, but forces David to manage stateful multi-pane interactions (complex sent/received asset lists, horizon sliders, dynamic capacity warnings) using Alpine stores and string-swapped HTML chunks.
* **Gemini's Next.js + Vercel AI SDK** stack front-loads Next.js server-routing and heavy JS build complexity, which is unnecessary for a mostly-read single-user FastAPI application.
* **Codex's Vite + React + TypeScript** static bundle served by FastAPI represents the perfect middle path. It provides a robust, component-driven client state runtime for the complex, stateful Trade Lab builder (Phase 23 W5b) and future layout compositions, while keeping the existing FastAPI server as the master router, served statically without Next.js server-side overhead.

> [!IMPORTANT]
> **Cross-Read Synthesis Alignment:** Claude's cross-read explicitly concedes Codex's point: *"Trade Lab is genuinely stateful... HTMX/Alpine could become a second migration before gen-UI."* Codex's cross-read similarly notes that Next.js server duplication is unnecessary for the current FastAPI contracts. Therefore, the cross-reads agree: **Next.js is rejected for v1, and we adopt Vite + React + TypeScript served statically by FastAPI as our master frontend architecture.**

### 3.2 Generative UI Timing: Defer and Constrain
* **Agreement:** All three cross-reads agree that streaming raw JSX or HTML is an anti-pattern, and that GenUI must use Gemini's **closed JSON-schema layout composition** model.
* **Divergence:** Gemini proposed GenUI as a primary architecture from the start; Claude and Codex argue that deterministic static surfaces and the trust/backtest dashboard must be fully stabilized first, citing the constitution's "no generic AI chatbot" rule.
* **Synthesis:** Adopt the **Claude/Codex static-first sequence**. Build the deterministic static cockpit first. Layer the Generative UI engine (reusing the same catalog components) later as an additive, opt-in feature for 4 high-ROI conversational surfaces (multi-asset what-ifs, roster simulation, rookie re-tiering, and injury branching).

### 3.3 Build Order: Grounded in the Active Sprint
* **Agreement:** All three agree the global trust strip and component library must exist first, and that the Roster Audit and Trade Lab are the core surfaces.
* **Divergence:** Claude placed Trade Lab late due to governance risks; Codex placed Trade Lab early (Phase 2) because Phase 23 W5b is the literal next deferred UI task in `AGENT_SYNC` and the backend is ready.
* **Synthesis:** Claude's cross-read conceded to Codex: *"W5b is the live, backend-ready sprint item. My 'build it last' position over-weighted governance risk and under-weighted the actual repo state."*
* **Merged Sequence:**
  1. **Phase 0 (Shell & Contracts):** Define component catalog schemas + global trust strip.
  2. **Phase 1 (Trust & Backtest Surface):** Build `/api/trust-surface` dashboard to govern cockpit trust.
  3. **Phase 2 (Trade Lab W5b):** Stand up the double-panel Trade Lab page consuming `/api/trade/reconcile` and `/api/trade/reconcile/market`.
  4. **Phase 3+ (PVO Surfaces):** Fan out to Player detail, Roster Audit, and Rookie Board.

### 3.4 Visual Hues & Color Collisions
* **Agreement:** Confirm a dark-first terminal using the colorblind-safe **Wong Palette**: Cool Blue/Cyan represents the proprietary **Model Track**; Warm Amber represents the crowdsourced **Market Track** and **Age Cliffs**. Green and red are banned as primary signals to prevent Win/Loss bias.
* **Divergence:** Several drafts assigned amber to both Market, cliffs, and a position (TE), causing a semantic color collision.
* **Synthesis:** Adopt Claude's color-governance rule: **Amber belongs strictly to Market and Cliffs.** All position accents must utilize non-amber hues (e.g. violet QB, teal RB, magenta WR, indigo pick) so color-overloading is physically impossible.

### 3.5 Ingest and File Handling Authority
* **Agreement:** All three cross-reads agree that the previous file-only (`file://`) and client-side `localStorage` cache workarounds are **stale** because the application is fully served via Uvicorn/FastAPI.
* **Synthesis:** All data-fetching, rate-limit caching, identity resolution, and analytical calculations remain the strict authority of the FastAPI backend. The frontend communicates exclusively via structured JSON-over-HTTP. Drop all browser-side `FileReader` drop-zones or client-side Sleeper calls from the core architecture.

---

## 4. Converged PM Recommendation to Feed the Merge

We recommend that David execute the Frontend Design merge utilizing this consolidated blueprint:

### 4.1 Technical Architecture Spec
* **Backend:** Existing FastAPI server.
* **Frontend:** Vite + React + TypeScript, built to a static package and served by FastAPI.
* **Component Primitives:** Radix UI and Tailwind CSS for rapid styling.
* **Dense Tables:** TanStack Table with virtualization to handle massive player grids.
* **Charts:** Observable Plot (native faceting/quantile plots) as the single charting vocabulary.
* **Zod-to-Pydantic:** Strictly generate Zod validation schemas on the React client directly from FastAPI Pydantic models.

### 4.2 Structural Governance Contracts (The Claude Triad)
* **The Decision Card Contract:** React components require `signal`, `uncertainty`, `counter_argument`, and `horizon` props—or the card auto-renders inside a de-saturated `EXPERIMENTAL` frame.
* **The Two-Lane Contract:** Hardcoded visual container separation between model (indigo/cyan) and market (amber/gold).
* **The Banned-Language CI Linter:** Integrate a pre-commit and CI python/bash scan (aligned with `03-code-hygiene-policy.md`) that rejects any commit containing banned visible verdict tokens (`buy`, `sell`, `win`, `loss`, `verdict`, etc.) in React code, templates, or mock payloads.

### 4.3 Generative UI Appendix (The Gemini Spec)
* Keep GenUI deferred as an additive, opt-in layer.
* When implemented, it must use **JSON layout spec mapping to the closed static component catalog**, with Claude Sonnet 4.6 as layout composer.
* Incorporate `min_height` bounds in the Zod catalog to prevent Cumulative Layout Shift (CLS), and configure 3.0s timeouts that swap failing layout nodes to static fallback cards.
* Inject `LeagueContext` via structured XML-tagged system prompt headers and utilize **5-minute ephemeral prompt caching** to limit monthly LLM spend to ~$35.
