# Codex Frontend Recommendation for Dynasty Genius

Date: 2026-05-25
Author: Codex
Scope: Independent frontend recommendation after governance bootstrap, full UI Research corpus review, PDF text extraction, and current repo inspection. This file intentionally does not read or incorporate Claude or Gemini recommendation artifacts.

## Executive Recommendation

Build Dynasty Genius as a deterministic analytical workstation first, not as a chatbot, not as a consumer fantasy app, and not as a raw generative-UI sandbox.

The right frontend target is a FastAPI-served, API-backed cockpit with a typed component catalog, strict model-vs-market lane separation, explicit trust state, and every decision surface reading from existing Player Value Object and reconciliation endpoints. Generative UI should arrive later as a constrained layout-composition layer over that same catalog. It must never emit raw HTML, JSX, uncontrolled numbers, player identities, verdict language, or model calculations.

My recommended stack is:

- Backend/API authority: existing FastAPI app in `app/main.py`.
- Initial frontend: Vite + React + TypeScript as a static bundle served by FastAPI.
- UI primitives: Radix/shadcn-style source-owned components, Tailwind or CSS variables for tokens, lucide icons where icons are appropriate.
- Data fetching/state: TanStack Query for API reads, Zod schemas mirroring Pydantic responses, no direct browser calls to Sleeper/FantasyCalc.
- Tables: TanStack Table with virtualization for roster, rookie, market, and league matrices.
- Charts: Observable Plot or visx for uncertainty, aging curves, small multiples, and calibration views. Use one chart vocabulary, not per-page library churn.
- Generative UI later: schema-rendered component specs only, using a closed catalog and backend tool results. No raw JSX streaming.

This is a middle path between the research camps. The file-only/zero-build docs are now behind the repo. The full Next.js/AI-SDK docs are directionally right for runtime GenUI, but too early and too broad for the current product state. The current repo already has the hard backend contracts: FastAPI routes, PVOs, trust artifacts, roster audit, model-native trade reconciliation, market reconciliation, market leakage guards, and Phase 23 W5b UI explicitly deferred. The frontend should exploit that shape instead of introducing a second application architecture before deterministic surfaces exist.

## Governance Constraints That Control The Frontend

The frontend is subordinate to the Product Constitution and North Star architecture:

- Dynasty Genius is decision support, not an automated manager.
- Market data is price-discovery context only. It must never be blended into model-native value or visually imply authority over model output.
- No decision surface may use action/verdict language such as buy, sell, target, approve, reject, pass, fail, win, lose, drop, or grade.
- Hard age cliffs are UI warnings only: RB 26, WR 28, TE 30, QB 33. Models consume fitted continuous aging curves.
- `decision_supported=false` is not a footnote. It is a visual state that must affect the surface itself.
- Backtest and validation state must be visible before polished decision interfaces imply earned confidence.
- Source freshness, identity coverage, missing inputs, market caveats, and model grade are product data, not debug metadata.
- The frontend must not create its own valuation logic. It renders API/PVO results and may only compute presentation transforms.

## Current Repo State

The repo is not a blank frontend slate:

- `app/main.py` is a FastAPI entrypoint with routers for rookies, roster audit, trade, market trade reconciliation, Engine B scores, and trust surface.
- `POST /api/trade/reconcile` returns model-native trade reconciliation and forced-cut penalty from `universe_pvo_latest.json` and the Sleeper universe snapshot.
- `POST /api/trade/reconcile/market` returns the parallel FantasyCalc market lane with forced-cut market penalty, divergence context, realism warnings, caveats, and recursive `decision_supported=false`.
- `GET /api/roster/audit` returns roster audit PVO output.
- `POST /api/rookies/score` and `/score-class` assemble rookie PVOs with market overlay enrichment.
- `GET /api/trust-surface/{position}` and `/model-card` expose backtest and model-card artifacts.
- The canonical PVO schema already includes identity, engine used, model grade, DVS, xVAR, projections, completeness, drivers, counterargument, caveats, market overlay, roster audit signals, and `decision_supported`.
- There is no existing frontend framework, no `package.json`, no `app/static`, and no template system. The only checked-in HTML surface found is `src/dynasty_genius/dashboard/rookie_board.html`.
- `AGENT_SYNC.md` says Phase 23 W5b is the next UI work: a standalone two-panel Trade Lab page with model view and market snapshot, browser-tested, with banned-language checks.

That state argues for a frontend that consumes existing APIs and artifacts first. It does not argue for direct browser fetching, local file APIs, or a full generative shell as the first committed UI.

## Critical Read Of The Research Corpus

The research corpus has strong convergence on product philosophy:

- The app should feel like an analytical cockpit or asset-management terminal.
- Model and market must be physically separated.
- Dense tables, small multiples, confidence bands, caveats, and counterarguments are better than consumer fantasy cards and verdict badges.
- Trust/freshness/model-grade state should be always visible.
- Generative UI is valuable when the answer shape changes by query, but dangerous if it invents UI, numbers, or authority.

The corpus also contains drift that should not be carried forward:

- Several docs still assume `file://` and zero dependencies. That was useful for early static artifacts, but it is not the primary architecture now that FastAPI routes and artifact-backed APIs exist.
- Several docs propose direct browser calls to Sleeper, FantasyCalc, localStorage caches, or user-side raw JSON ingestion. That bypasses the source adapter, raw snapshot, provenance, and rate-limit boundaries already established in the codebase.
- Some docs use or imply action language such as "Buy WR", "optimal target", "drop list", "accept", or "divestment required". Those must be rewritten as neutral analytical labels.
- Some docs use age cliffs that conflict with doctrine. The frontend must use RB 26, WR 28, TE 30, QB 33 and treat those as warnings only.
- Some docs overstate Databricks or real-time lakehouse requirements. The current product is single-user and artifact-backed. FastAPI plus local artifacts is the immediate substrate.
- Some docs recommend full Next.js/AI SDK as the first frontend. That is viable later for runtime GenUI, but it front-loads orchestration complexity before deterministic decision surfaces are proven.
- Some docs describe "VerdictCard". The component idea is useful, but the name is not. Use "Decision Evidence Card" or "Scenario Evidence Card".

## Product Philosophy

Dynasty Genius should be an honest terminal.

It should not try to feel friendly in the consumer fantasy sense. It should feel calm, dense, inspectable, and resistant to false certainty. The user should always know:

- What the internal model says.
- What the market says.
- Whether the model is decision-grade, experimental, pre-model, stale, incomplete, or abstaining.
- What data was missing.
- What counterargument weakens the signal.
- What roster or league context changes the interpretation.
- What is model-native vs. external price discovery.

The product posture is not "tell David what to do." It is "show David the evidence, uncertainty, and tradeoffs so he can decide."

## Tech Stack Decision

### Recommended Primary Stack

Use Vite + React + TypeScript as a frontend package, built to static assets and mounted by FastAPI.

Why:

- The repo already has FastAPI APIs and Python model/data ownership.
- The frontend needs real client state for Trade Lab: editable asset sets, horizon toggles, saved scenarios, paired model/market requests, forced-cut display, and browser verification.
- React gives the best ecosystem for future schema-rendered GenUI without committing to Next.js now.
- Vite keeps the build lightweight and avoids introducing server-side React or route duplication.
- TypeScript plus Zod gives an enforceable browser-side contract against Pydantic response shapes.
- FastAPI remains the deployment and API authority.

### Why Not HTMX/Jinja As The Main Path

HTMX/Jinja is attractive for read-heavy dashboards, but Trade Lab is the immediate deferred UI and it is stateful. The frontend will need side-by-side asset builders, derived totals, synchronized model and market responses, warnings, filters, drawers, and eventual component-level generative layouts. Those are awkward in Alpine stores and string-swapped partials. HTMX could work for an MVP, but it would likely become a second migration before GenUI.

### Why Not Next.js First

Next.js should remain an escape hatch for a later GenUI shell, not the first committed frontend layer. The current product does not need Next routing, server components, Vercel deployment assumptions, or an AI SDK dependency to build W5b and the trust surfaces. Introducing Next now would duplicate backend concerns and shift attention away from the existing FastAPI contracts.

### Data Storage

Do not add Databricks for frontend work. The UI should read FastAPI endpoints backed by current local artifacts. If mutable UI state is needed, start with local JSON/SQLite through FastAPI. If saved scenarios or sessions grow, add SQLite or Postgres behind FastAPI. Analytical data stays in versioned artifacts/Parquet/DuckDB-style workflows when needed.

## Design System

### Visual Language

Use a dark-first, dense, financial/scientific cockpit. The UI should be compact and high signal, but not visually aggressive.

Base rules:

- Neutral slate background, restrained borders, no decorative gradients, no glow-heavy AI aesthetic.
- Tabular numerals for all values.
- Position color is secondary metadata, not primary meaning.
- Red is reserved for system failure or severe stale/corrupt state, not "bad player" or "negative trade".
- Model and market colors are reserved and never used decoratively.
- Cards are for repeated entities and tools only; do not wrap page sections in nested cards.
- Every component has explicit loading, unavailable, stale, experimental, and unsupported states.

### Semantic Colors

Recommended token semantics:

- Model lane: cool cyan/blue.
- Market lane: amber/gold.
- Divergence: neutral direction tokens with labels, not green/red verdicts.
- Stale or evidence gap: amber/dashed treatment.
- System failure: muted red/rust, used sparingly.
- Age cliff warning: amber, never red.
- Position accents: QB, RB, WR, TE, Pick as small chips/borders only.

### Required Components

- App Shell: left rail, top context bar, always-visible trust strip.
- Trust Strip: source freshness, model version, artifact run, surface trust/grade.
- Model Lane Panel.
- Market Lane Panel.
- Divergence Context Row.
- Decision Evidence Card: signal, uncertainty, drivers, counterargument, caveats, horizon, timestamps.
- Player Row and Player Detail Drawer.
- Caveat Chips.
- Evidence Gap Frame for `decision_supported=false`, `EXPERIMENTAL`, `PRE_MODEL`, stale artifacts, or missing coverage.
- Forced-Cut Penalty Panel.
- Market Realism Warning Panel.
- Quantile/Interval Chart primitive.
- Aging Curve primitive.
- Calibration/Backtest Matrix primitive.
- Empty/Unavailable/Error states with exact cause and source path/endpoint.

### Language System

Component labels must encode governance:

- Use: Model View, Market Snapshot, Divergence Context, Capacity Cost, Forced-Cut Penalty, Evidence Gap, Validation State, Counterargument, Caveats, Inside Band, Model Higher Than Market, Model Lower Than Market.
- Avoid: Buy, Sell, Target, Drop, Stash, Accept, Reject, Approve, Block, Pass, Fail, Win, Lose, Fair, Grade.

Add a frontend banned-language test early. It should scan visible strings and fixture payload mappings, with explicit allowlists for internal code-only enum names when required.

## Information Architecture

The app should be one workstation with stable navigation:

1. Command Center
2. Trade Lab
3. Roster Audit
4. Rookie Board
5. League Opportunity Map
6. Market Divergence
7. Trust and Validation
8. Research Assistant, later and gated
9. Settings, file-backed and minimal

The app shell:

- Left rail: primary surfaces.
- Top context bar: league, season/week/draft state, active roster context.
- Trust strip: data freshness and current surface decision-support status.
- Main workspace: dense surface content.
- Right drawer: Player Detail, artifact detail, source/caveat inspector.
- Command palette: player, pick, team, saved scenario, and artifact lookup.

Do not lead with a marketing-style landing page. The first viewport should be the Command Center or Trade Lab depending on current sprint state.

## Decision Surfaces

### Command Center

Purpose: show system state, not recommendations.

Content:

- Roster capacity and forced-cut pressure.
- Data freshness and artifact status.
- Top evidence gaps by surface.
- Latest model/market divergence changes.
- Draft state and open league-state items.
- Links into Trade Lab, Roster Audit, Rookie Board, Trust.

Avoid:

- News feed.
- Generic fantasy content.
- "Today's recommended actions."

### Trade Lab

This is the immediate build target because Phase 23 W5b is deferred and the backend is ready.

Layout:

- Two primary panels: Model View and Market Snapshot.
- Shared asset builder for sent/received assets.
- Model View calls `/api/trade/reconcile`.
- Market Snapshot calls `/api/trade/reconcile/market`.
- Results are never blended. A third Divergence Context region summarizes differences in neutral language.
- Forced-cut penalty is visible in both lanes, but model-native selection remains the authoritative roster-capacity computation.
- Market realism warnings appear only as advisory context.
- `market_package_requires_manual_review` may appear only in the combined UI layer where both model xVAR and market lane are visible.

Controls:

- Asset search by canonical IDs/PVO rows.
- Future pick selector with exact/generic/bucket states and caveats.
- Horizon control only if backed by API output; otherwise defer.
- Save scenario as local/API state, not as a decision.

Hard requirements:

- No fair/unfair/trade won language.
- No combined score.
- No market-to-model conversion.
- No hidden forced-cut overflow.
- API unavailable/stale states must be visible and non-blocking where appropriate.

### Roster Audit

Purpose: portfolio balance sheet.

Content:

- Active/taxi/IR capacity.
- Player table grouped by position and model route.
- xVAR, DVS, model grade, age, years-to-cliff warning, signal completeness, risk flags, caveats, market overlay as separate columns.
- Roster Audit Signals from PVO, not new UI scoring.
- Forced-cut candidate context from the roster cut report where available, always `decision_supported=false`.

Treatment:

- Evidence Gap Frame until the corresponding validation state supports stronger interpretation.
- Use small multiples by position for age/value distribution and replacement exposure.

### Rookie Board

Purpose: Engine A draft board and prospect uncertainty surface.

Content:

- Ranked prospects from PVO.
- Engine A version/model grade.
- xVAR/DVS and signal completeness.
- Draft status from `resources/draft_state.js` or future API equivalent.
- Uncertainty/range display where model output supports it.
- Identity resolution status and age blockers.
- Counterargument and caveats per prospect.

Avoid:

- Tier verdict names.
- Bust/lock/franchise labels.
- Confidence percentages that are actually draft-slot proxies.

### Player Detail Drawer

Purpose: inspect one asset without leaving compare-many context.

Required sections:

- Identity and source IDs.
- Model route: Engine A, Engine B, blend, PRE_MODEL, INACTIVE, UNRESOLVED.
- Model View: DVS/xVAR/projections only if present.
- Market Snapshot: FantasyCalc overlay only if present.
- Divergence Context: percentile delta and flag with caveats.
- Drivers.
- Counterargument.
- Risk flags/caveats.
- Source freshness and model/artifact provenance.
- Roster context.
- Aging curve warning using doctrine thresholds.

### League Opportunity Map

Purpose: map league structure, not produce trade targets.

Content:

- 12-team matrix from team value matrix and league opportunity artifacts.
- Positional surplus/deficit as model context.
- Pick inventory context when artifact coverage allows.
- Market divergence cards from existing Phase 17.5 artifacts.

Language:

- Use "fit context", "surplus alignment", "roster gap", "market divergence".
- Do not use "target this owner" or "send offer".

### Market Divergence Surface

Purpose: inspect model-vs-market deltas across the universe.

Content:

- Filterable table by position, roster status, model grade, caveats, source timestamp, divergence flag.
- Model and market columns physically separated.
- Cohort/band labels where available.
- Unavailable rows are still visible as coverage information.

### Trust And Validation

Purpose: make confidence earned and auditable.

Content:

- Position-level backtest artifact from `/api/trust-surface/{position}`.
- Model cards from `/model-card`.
- Promotion grade and experimental status.
- Latest artifact run IDs and timestamps.
- Market snapshot health.
- Identity coverage matrix status.
- Known limitations and current evidence gaps.
- Surface readiness matrix: each UI surface maps to its governing artifact and decision-support level.

This surface should be built early, not after polish. It controls the trust strip used everywhere else.

### Research Assistant

Purpose: late-stage schema-rendered analysis surface.

It should not be a floating chatbot. It should be a query workspace that returns tables, charts, and evidence cards from registered components. Every numeric value must come from a backend tool result or artifact. It is the first natural home for generative UI after deterministic surfaces stabilize.

## API And Data Flow

Frontend data flow should be one-way:

1. Sources are ingested by scripts/adapters.
2. Artifacts/PVOs are produced under `app/data/` and `resources/`.
3. FastAPI routes expose governed JSON.
4. Frontend fetches FastAPI only.
5. Components render typed responses.
6. UI state stores filters, view settings, and saved scenarios only.

The browser must not:

- Fetch Sleeper directly.
- Fetch FantasyCalc directly.
- Scrape KTC, PFF, PlayerProfiler, or any source.
- Compute valuation, model grade, market divergence, forced-cut selection, or identity matching.
- Store source-of-truth player dictionaries in localStorage as an authority layer.

Frontend contracts should be generated or mirrored from Pydantic:

- PVO response schemas.
- Trade reconciliation response.
- Market reconciliation response.
- Trust surface/model card response.
- Roster audit response.
- Rookie scoring/class response.

If a response has `decision_supported=false`, `model_grade=EXPERIMENTAL`, missing values, or caveats, the component must render those states. Silent dashes are not acceptable.

## Trust And Uncertainty UX

Uncertainty is not a decoration. It is the point of the product.

Rules:

- Every major value shows source, timestamp, and model grade either inline or through a nearby inspector.
- Do not render a single large number without caveats and counterargument.
- Prefer intervals, bands, quantile dotplots, or calibrated buckets over false precision.
- Use fan charts only for time trajectories, such as aging or pick-value horizon.
- Use quantile/dot/range displays for single-player and trade outcome uncertainty where distributions exist.
- Use explicit "unavailable" states when distributions do not exist yet. Do not fake them.
- Every warning needs an escape hatch: source detail, artifact detail, model-card link, or input coverage explanation.

Surface readiness should be explicit:

- Decision Grade: validation artifact supports the surface.
- Experimental: backtest incomplete or promotion gate not passed.
- Pre-Model: PVO has no validated score.
- Context Only: market or external data only.
- Evidence Gap: missing identity/source coverage.
- Stale: source timestamp violates freshness rule.

## Generative UI Stance

Generative UI is valuable, but only after the deterministic component catalog exists.

Use it for:

- Ad hoc trade scenario explanations.
- Multi-year roster simulation layouts.
- Injury/role what-if branching.
- Rookie class re-tiering by league context.
- Research questions that naturally produce different table/chart layouts.

Do not use it for:

- The primary roster table.
- The core Trade Lab asset builder.
- Source ingestion.
- Model scoring.
- Identity resolution.
- Market reconciliation.
- Any UI that can be a stable deterministic surface.

Architecture:

- Closed component catalog.
- Backend tool calls compute all numbers.
- LLM emits a JSON layout spec validated by schema.
- Client renders registered components only.
- Numeric props must be traceable to tool results.
- Player IDs must come from known IDs, not free-text names.
- Every generated surface inherits the same banned-language, caveat, trust, and `decision_supported` rules.

The Google Generative UI paper supports the idea that users prefer generated interfaces over plain markdown when the model has tools, examples, and strong instructions. Its limits matter here: generation can be slow, code can fail, and prompt philosophy materially affects output. Dynasty Genius should take the lesson as "custom UI beats text when constrained", not "let an LLM write arbitrary app UI."

## Governance Enforcement In The Frontend

Add governance checks as part of the first frontend commit, not after design polish.

Required checks:

- Banned visible-language scan over frontend source and fixture labels.
- Component tests for `decision_supported=false` rendering.
- Component tests for model/market physical separation.
- API fixture tests proving market values never render in Model View containers.
- Accessibility checks for critical surfaces.
- Screenshot/browser checks for Trade Lab at desktop and mobile/tablet breakpoints.
- Schema validation tests for all consumed API payloads.
- A freshness/caveat rendering test for each major surface.

Governance should also be encoded in the component API:

- `ModelLane` cannot accept market fields.
- `MarketLane` cannot accept model xVAR/DVS as market values.
- `DecisionEvidenceCard` requires `counterArgument`, `caveats`, `horizon`, and `asOf`.
- `PlayerValueCell` requires model grade and source metadata.
- `ExperimentalFrame` wraps surfaces or rows that are not decision-grade.

## Build Order

### Phase 0: Frontend Contract Foundation

- Create frontend package with Vite React TypeScript.
- Add design tokens and app shell.
- Add API client with Zod schemas for current endpoints.
- Add banned-language and `decision_supported` rendering tests.
- Add a static component harness or Storybook equivalent for the core components.

Exit criteria: component catalog renders from mocked API fixtures and governance scans pass.

### Phase 1: Trust Strip And Trust Surface

- Build the global trust strip.
- Build Trust and Validation page over `/api/trust-surface/{position}` and `/model-card`.
- Render model grade, experimental state, promotion gate, artifact timestamps, and known limitations.

Exit criteria: every later surface can display trust state from a shared component.

### Phase 2: Trade Lab W5b

- Build the standalone two-panel Trade Lab page.
- Wire `/api/trade/reconcile` and `/api/trade/reconcile/market`.
- Show forced-cut penalties, market realism warnings, divergence context, caveats, stale/cold market state, and missing artifact errors.
- Add browser tests and screenshot checks.

Exit criteria: Phase 23 W5b is complete without model/market leakage or banned UI language.

### Phase 3: Player Detail Drawer And Shared PVO Components

- Build the canonical player row, detail drawer, caveat chips, evidence gap states, and model/market display primitives.
- Use PVO fixtures from rookie and roster endpoints.

Exit criteria: every PVO-consuming surface uses the same player and evidence components.

### Phase 4: Roster Audit

- Wire `/api/roster/audit`.
- Add capacity gauges, player table, age warnings, roster audit signal rendering, forced-cut/capacity context, and market overlay columns.

Exit criteria: no UI-local roster scoring; all warnings trace to PVO/API fields.

### Phase 5: Rookie Board Refresh

- Replace or supersede the current static rookie board with typed components.
- Keep live draft state, available-now panel, Engine A caveats, identity status, and counterarguments.

Exit criteria: draft-day surface is browser-tested and governance-safe.

### Phase 6: League Opportunity And Market Divergence

- Render Phase 17.5 league opportunity artifact through API or a new read-only route.
- Render universe market divergence with model/market separation.

Exit criteria: league structure is inspectable without action language.

### Phase 7: Research Assistant And Constrained GenUI

- Define the JSON layout schema from the already-built component catalog.
- Add a backend agent endpoint only after deterministic component rendering is proven.
- Start with one query class, such as "show my RB room over three years", and keep all numbers backend-generated.

Exit criteria: generated layouts replay deterministically from saved JSON specs.

## Open Decisions

These should be resolved before frontend implementation begins:

- Should Phase 0 use Tailwind utilities or plain CSS modules over CSS variables? I prefer Tailwind plus semantic CSS variables if David is comfortable adding Node tooling; otherwise CSS modules are acceptable.
- Should saved Trade Lab scenarios be persisted to local file/SQLite through FastAPI, or remain browser-local for W5b?
- What exact freshness thresholds should the Trust Strip use for Sleeper, FantasyCalc, PVO batch, market divergence, and backtest artifacts?
- Which endpoint should expose Phase 17.5 league opportunity artifacts to the frontend?
- Should mobile be read-only rather than fully supported? I recommend desktop-first with tablet-readable layouts and mobile read-only fallback, not no mobile at all.

## Final Position

Dynasty Genius should build the frontend as a governed evidence cockpit over the existing FastAPI/PVO architecture. Start with the component contracts and trust layer, then finish Phase 23 W5b Trade Lab, then expand across PVO surfaces. Keep generative UI as a later, constrained renderer over the same components.

The product will fail if it becomes either a pretty fantasy dashboard or an unconstrained AI interface. It will succeed if every screen makes the same promise: model evidence, market context, uncertainty, counterargument, provenance, and no false verdict.
