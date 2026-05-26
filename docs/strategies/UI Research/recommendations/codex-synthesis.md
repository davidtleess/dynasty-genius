# Codex Synthesis Of The Three Cross-Reads

Date: 2026-05-25
Author: Codex
Scope: Synthesis of `claude-crossread.md`, `codex-crossread.md`, and `gemini-crossread.md`. This is a merge input only. It is not the final merged Frontend Design document.

## Executive View

The three cross-reads have effectively converged on the product and narrowed the unresolved decision to a single implementation fork.

Settled consensus:

- Dynasty Genius should be an Honest Terminal: a dense, calm, expert cockpit.
- Model and market must be physically separated in two lanes.
- Divergence is neutral context, never a verdict.
- Uncertainty, caveats, counterarguments, freshness, model grade, and `decision_supported=false` are first-class UI states.
- The browser and LLM must never invent or compute player values.
- Served FastAPI/PVO/API authority supersedes earlier `file://` research assumptions.
- Databricks is not part of frontend v1.
- Generative UI, if used, must be closed-schema JSON layout composition over registered components.
- The final merge should not carry forward stale age-cliff, DVS-scale, FileReader/localStorage, green/red verdict-color, or browser-source-authority drift.

Remaining fork:

- Claude's Python-first HTMX/Jinja path vs Codex/Gemini's React path.
- Across the cross-reads, the center of gravity shifted toward Codex's Vite + React + TypeScript static bundle served by FastAPI, not full Next.js.

My converged recommendation for the merge: use FastAPI as the backend/API/deployment authority, build a Vite + React + TypeScript frontend bundle for the governed cockpit, adopt Claude's invariant component contracts and palette discipline, adopt Gemini's future GenUI safety mechanics, and sequence shell + component catalog + Trust strip first, then Phase 23 W5b Trade Lab, then the remaining PVO surfaces. Do not merge yet.

## Settled Consensus Across All Three Cross-Reads

### Product Doctrine

All three cross-reads agree the product direction is settled:

- It is not a consumer fantasy tool.
- It is not a generic chatbot.
- It is not a marketing site.
- It is an expert single-user decision-support cockpit.

The final design should use the Honest Terminal framing as the top-level product philosophy.

### Governance-In-UI

The merged design should treat these as non-negotiable:

- `decision_supported=false` is visible everywhere until earned out.
- Experimental/pre-model/stale/unavailable states have visual treatments.
- Strong decision surfaces require counterargument and caveats.
- Banned verdict/action language is enforced mechanically.
- Model/market separation is enforced by component structure, not just copy.
- Trust/backtest state controls surface confidence.

The strongest shared phrasing is Claude's "three structural contracts":

- Decision Evidence Card contract.
- Two-Lane contract.
- Experimental treatment.

The final merge should use those contracts as the spine.

### Data And API Authority

The three cross-reads agree that FastAPI/PVO/artifacts own the data. The frontend renders governed outputs.

Settled rules:

- No browser-side Sleeper/FantasyCalc fetching as primary architecture.
- No browser-owned localStorage source-of-truth cache.
- No client-side valuation, identity matching, forced-cut selection, model grade assignment, or market reconciliation.
- No LLM numerical reasoning.
- Every numeric value must trace to a backend artifact, endpoint, or tool result.

### Generative UI Safety Pattern

All three agree on the safe shape, even where they differ on timing:

- Closed component catalog.
- JSON layout spec.
- Registered component renderer.
- Backend tool calls for all numbers.
- Known player IDs only.
- No raw JSX, HTML, arbitrary code, or untyped component names.
- Standard skeletons/fallbacks for streaming or tool failures.

Gemini's runtime mechanics should be preserved for the later GenUI appendix: `min_height` to prevent layout shift, fallback nodes, structured LeagueContext, and prompt caching economics.

### Research Drift To Correct

All three cross-reads agree the merge must explicitly correct:

- `file://` and FileReader/localStorage assumptions.
- Browser-side source authority.
- Incorrect cliff examples. Use RB 26, WR 28, TE 30, QB 33 as UI warnings only.
- DVS scale drift. Use the repo-locked 0-100 DVS context.
- Any Engine A/B-as-market mislabeling. Engine A and Engine B are internal model lanes; FantasyCalc/KTC/ADP are market lanes.
- Green/red verdict semantics.
- Banned language appearing in source research examples.

## Divergences: Where Cross-Reads Agree Vs. Disagree

### 1. Tech Stack

All three cross-reads agree this is the core unresolved fork.

What is now effectively rejected:

- Full Next.js + AI SDK as the first committed frontend stack. Gemini's own cross-read moves away from its initial Next-first recommendation and toward Vite React static serving.
- Databricks for frontend v1.
- Pure `file://` zero-build as the primary path.

Remaining candidates:

- Claude option: `FastAPI + Jinja2 + HTMX + Alpine + Tailwind + Observable Plot`, with a React island only if Trade Lab state gets too complex.
- Codex/Gemini convergence option: Vite + React + TypeScript static bundle served by FastAPI, with Zod/TanStack/Radix-style component contracts.

Converged read:

- HTMX/Jinja is strongest on local simplicity, low dependency surface, and long-term maintainability.
- Vite React is strongest on stateful Trade Lab ergonomics, typed browser contracts, component testing, and future schema-rendered GenUI compatibility.
- Next.js is useful as future GenUI reference material, not the v1 shell.

Codex recommendation to feed the merge:

- Adopt Vite + React + TypeScript served by FastAPI for v1.
- Keep FastAPI as data/API/deployment authority.
- Explicitly avoid Next.js until runtime GenUI becomes a validated need.
- If David prioritizes zero Node tooling above Trade Lab ergonomics, Claude's HTMX + one React island remains the viable alternate. The final merge should present that as the only real stack alternative.

### 2. Generative-UI Timing

All three cross-reads now agree on the safe pattern, but not all original recommendations agreed on timing.

Current cross-read convergence:

- Claude: defer hard.
- Codex: defer until deterministic catalog and trust layer exist.
- Gemini cross-read: adopts static-first React bundle with GenUI deferred to later sprints.

Converged recommendation:

- Do not make GenUI the v1 app shell.
- Build deterministic decision surfaces first.
- Include a future GenUI appendix using Gemini's JSON-layout safety mechanics.
- First GenUI candidate should be a gated Research Assistant or narrow scenario view, not a floating chatbot and not the primary Trade Lab asset builder.

### 3. Build Order And Trade Lab Timing

All three agree Trust and Trade Lab are both central. The divergence is ordering.

Claude cross-read changed position after reading the others:

- Earlier Claude recommended Trade Lab later due to governance risk.
- Claude cross-read now leans earlier, after shell/library/Trust, because Phase 23 W5b is the active deferred UI with backend endpoints ready.

Codex:

- Component foundation.
- Trust strip/surface.
- Trade Lab W5b.
- PVO surfaces.
- GenUI later.

Gemini cross-read:

- Supports Trust Surface Phase 1 and Vite React.

Converged recommendation:

1. Shell, design tokens, component catalog, and governance tests.
2. Trust strip plus minimal Trust/Validation surface.
3. Phase 23 W5b Trade Lab, using existing `/api/trade/reconcile` and `/api/trade/reconcile/market`.
4. Player drawer and shared PVO components.
5. Roster Audit and Rookie Board refresh.
6. League Opportunity / Market Divergence.
7. Research Assistant / constrained GenUI.

This balances current repo priority with constitutional caution.

### 4. Palette

All three agree dark-first, dense, no consumer colors. The practical conflict is exact lane colors.

Current convergence:

- Claude/Codex: cool blue/cyan for model, amber/gold for market, no green/red as semantic verdict channels.
- Gemini cross-read accepts Claude's non-colliding blue/amber palette as the merge core, despite Gemini's initial indigo/amethyst/sage proposal.

Converged recommendation:

- Use cool blue/cyan for Model.
- Use amber/gold for Market.
- Use amber for age warning states, but distinguish by shape/label from market panels.
- Do not use green/red as positive/negative value semantics.
- Keep position hues orthogonal and non-colliding with the model/market signal axis.

### 5. File-Mode vs Served FastAPI

All three cross-reads agree this is settled.

Converged recommendation:

- Use served FastAPI and JSON-over-HTTP.
- Drop `file://`, FileReader, browser source caches, and client-side source authority from the primary architecture.
- If FileReader exists at all, it should be an explicitly-scoped debug/import utility, not a product data path.

## Strongest Inputs To Carry Into The Merge

### Claude

Carry forward:

- Three structural contracts: Decision Card, Two-Lane, Experimental treatment.
- Banned-language linter as a code/CI gate.
- Non-colliding color system.
- Corpus drift corrections: Engine A/B model lane, DVS scale, constitutional cliff ages, stale `file://`, banned-language examples.

Why it matters:

- Claude turns governance from prose into product mechanics.

### Codex

Carry forward:

- Repo-grounded endpoint and PVO map.
- FastAPI remains API/deployment authority.
- Vite + React + TypeScript as pragmatic middle path.
- Zod/Pydantic contract mirroring.
- Trust Surface before polished decision surfaces.
- Component APIs that make invalid model/market mixing difficult or impossible.

Why it matters:

- Codex keeps the final design buildable against the current codebase instead of research abstractions.

### Gemini

Carry forward:

- Closed-schema GenUI runtime safety pattern.
- `min_height` and fallback nodes for streaming layout stability.
- LeagueContext/prompt-caching economics for later GenUI.
- DuckDB/Parquet over Databricks for single-user economics.
- Signal-density review area concept for Command Center.

Why it matters:

- Gemini provides the best future GenUI operating model once deterministic surfaces are stable.

## Converged Recommendation For The Merge

When David directs the merge, Codex recommends the final Frontend Design document take this stance:

1. Product: Honest Terminal / analytical cockpit.
2. Stack v1: FastAPI backend plus Vite React TypeScript static frontend served by FastAPI.
3. Alternate stack note: HTMX/Jinja plus React island remains a viable low-tooling option if David rejects Node build tooling.
4. Reject for v1: full Next.js/AI SDK shell, pure `file://`, direct browser source fetching, Databricks.
5. Component invariants: Decision Evidence Card, Two-Lane Panel, Experimental/Evidence Gap Frame, Trust Strip.
6. Data flow: source adapters/artifacts -> FastAPI -> typed frontend schemas -> components.
7. Build order: component catalog + governance tests + Trust strip/surface -> Phase 23 W5b Trade Lab -> shared PVO components -> Roster/Rookie -> League/Market Divergence -> constrained GenUI.
8. GenUI: defer; preserve Gemini's closed JSON layout pattern as future appendix.
9. Palette: blue/cyan model, amber/gold market, no green/red verdict channels, orthogonal position hues.
10. Governance: banned-language tests, schema tests, model/market separation tests, `decision_supported=false` rendering tests, and browser screenshot checks for Trade Lab.

## Decision Points For David

The merge should put these to David explicitly:

- Adopt Vite React TypeScript v1, or prefer Claude's lower-tooling HTMX/Jinja + React island path?
- Build Phase 23 W5b immediately after Trust foundation, or force a broader Roster/Player component pass first?
- Approve blue/cyan model and amber/gold market as reserved lane colors?
- Approve GenUI as deferred appendix only, with no runtime implementation in v1?
- Decide where saved Trade Lab scenarios live: browser-local, SQLite via FastAPI, or deferred?

## Final Note

The three cross-reads no longer meaningfully disagree on product doctrine. The merge should spend little energy rearguing Honest Terminal, Two-Lane separation, uncertainty, counterarguments, or trust visibility. Those are settled.

The only high-leverage merge work is choosing the v1 frontend stack and expressing the build order tightly enough that Phase 23 W5b can proceed without violating the constitution.
