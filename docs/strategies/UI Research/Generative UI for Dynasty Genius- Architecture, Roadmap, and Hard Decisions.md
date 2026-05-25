# Generative UI for Dynasty Genius: Architecture, Roadmap, and Hard Decisions

**TL;DR**
- **Build it on AI SDK 5/6 `useChat` + tool-invocation generative UI in Next.js (App Router) on top of your existing FastAPI service, with Claude Sonnet 4.6 as the primary structured-output engine and Claude Haiku 4.5 as the cheap default — total marginal LLM spend ~$30–55/month at 30 prompts/day with session-clustered prompt caching.** Do **not** stream raw JSX. Do **not** spin up Databricks for a single user — DuckDB + Parquet on local disk, with Postgres only if you genuinely need transactional writes, is the right substrate for the framework-driven ML you described.
- **Static dashboards are still better for ~60% of dynasty workflows.** Generative UI earns its keep in exactly four high-ROI surfaces: complex multi-asset trade evaluation, 3–5-year roster simulation, contextual rookie tiering, and injury-impact "what-if" branching. Everything else (rosters, lineups, league standings, KTC tables) should stay declarative and stable.
- **Phase rollout: hybrid shell first (Phase 8 alongside your existing engine work), then generative widgets, then a fully generative "ask anything" surface in Phase 16–17.** The framework-as-feature-selector / data-as-algorithm principle survives this cleanly because the LLM never invents numbers — it only composes registered components against schema-validated, cached data the Python backend computes.

---

## Key Findings

1. **The architectural fork is JSON-schema → registered components vs. raw JSX streaming, and JSON is the correct answer for this app.** Per Vercel's official `vercel/ai` GitHub Discussion #3251, maintainer @lgrammel announced: "Development of AI SDK RSC is paused. We recommend using AI SDK UI," noting "there are several long-standing limitations with AI SDK RSC that have been causing pain for our users, and there are no good solutions in the near term" (github.com/vercel/ai/discussions/3251). The replacement pattern is `streamText` + tool invocations returning structured data + a client-side component map keyed on `toolName`. Thesys C1, json-render, LangChain's Generative UI guide, and Anthropic's structured outputs all converge on the same pattern: define a typed catalog, the LLM emits JSON that conforms to it, the client renders.

2. **Subscription seats handle 90% of LLM cost; APIs handle runtime.** Claude Max ($100–200/mo) covers all development, schema design, prompt iteration, and one-off data exploration via Claude Code and Claude Desktop. Gemini Pro subscription handles long-context research over your historical Parquet (1M-token window, free via web/CLI). Codex CLI / ChatGPT Plus handles ad-hoc script generation. The **only** workload that genuinely needs a paid runtime API key is the live generative UI rendering loop — and for a single user at realistic volumes that's $30–55/month on Sonnet 4.6 with session-aware caching.

3. **Databricks is the wrong default here.** A 14-day trial exists, but minimum production usage requires a Premium-tier workspace plus underlying cloud VM costs. Per costbench.com's 2026 Databricks pricing analysis (corroborated by cloudforecast.io): "A typical mid-size team can expect to spend $2,000–$5,000 per month on Databricks alone, with total infrastructure costs reaching $4,000–$15,000 monthly." For ~10 GB of structured Parquet across nflverse, Sleeper snapshots, market values, and PFR multi-year stats, DuckDB on local disk is "decisively faster than PostgreSQL for analytical queries, with 16–26x overall speedup" per Saurabh Sharma's April 2026 benchmark of 128.2M rows of NYC taxi data, with MotherDuck reporting a single TPC-DS query at 1500x speedup — and costs zero. Databricks becomes the right answer only above ~100 GB *and* multi-user *and* requiring Delta Lake's ACID guarantees on shared tables — none of which apply.

4. **Sleeper API is no-auth and read-only.** You already use it. The community maintains multiple working Sleeper MCP servers (e.g., `einreke/sleeper-scraper-mcp`, `GregBaugues/tokenbowl-mcp`) that wrap the same endpoints you're calling from FastAPI — so when the agent layer needs Sleeper data, it can go through MCP or your FastAPI cache layer; either way, no API key, just rate-limit discipline (<1000 calls/min per Sleeper's docs).

5. **The data layer is mostly free or scrapable, but KTC explicitly has no public API.** Per KTC's own FAQ, they "don't currently have an API or any sort of .csv available." FantasyCalc, by contrast, has an actively documented public JSON endpoint (`https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1`) returning Sleeper-mapped IDs and trade values. nflverse provides nightly-updated PBP, rosters, snap counts, and PFR advanced stats via `nfl_data_py` (Python, free). PlayerProfiler and PFF require paid scraping under personal subscription. RAS.football is HTML-only; maintainer Kent Lee Platte does not publish an API, and the site currently warns of plugin-related table issues.

6. **Hallucination is solved by constrained decoding + RAG-from-cache, not by prompting.** Anthropic's structured outputs (beta header `anthropic-beta: structured-outputs-2025-11-13`, GA on Sonnet 4.5/4.6 and Opus 4.5/4.6/4.7) compile your JSON schema into a grammar that constrains token generation. The LLM literally **cannot** emit a player name not in your catalog if you typed the prop as `z.enum(playerIdList)`. Combined with the policy that the LLM never sees raw numbers it should "compute" — only references retrieved values via tool calls — the surface area for hallucinated stats collapses to nearly zero.

7. **MCP is now an industry standard, not Anthropic-only.** Per maintainer David Soria Parra's blog post "The 2026 MCP Roadmap" (March 9, 2026, blog.modelcontextprotocol.io), MCP's current released spec is `2025-11-25` with a release candidate `2026-07-28` in flight delivering "a stateless protocol core, the Extensions framework, Tasks, MCP Apps, authorization hardening, and a formal deprecation policy." Anthropic donated MCP to the Agentic AI Foundation under the Linux Foundation in December 2025 (co-founded with Block and OpenAI), so betting on MCP is no longer single-vendor.

---

## 1. Football-Specific Generative UI Use Cases, Ranked

Generative UI is overkill for stable, well-understood surfaces. It earns its keep when the **shape** of the answer depends on the question. Here is the honest ranking:

| # | Use case | Why GenUI beats a static dashboard | ROI |
|---|---|---|---|
| 1 | **Multi-asset trade evaluation involving future picks** ("trade my 2027 1st + Cook for CMC + a 2026 2nd") | Required components vary: pick-value sliders, age-curve overlays, positional-need-fit, contender-vs-rebuild lens, cap-on-roster-spots. No static layout fits every shape. | **Very high** |
| 2 | **3–5-year roster simulation under a specific trade** ("show me my RB room over 2026–2029 if I trade my 2027 1st for CMC") | The view must morph based on whose curves you're projecting, how many rookies enter, what the user wants compared (points-per-game? VORP? championship odds?). | **Very high** |
| 3 | **Injury-impact branching** ("if Bijan tears his ACL Week 6, what's my flex Weeks 7–14?") | A static UI would force a model decision before the user types. GenUI lets the agent pick: depth-chart card, weekly projection diff, waiver-wire suggestions, or a trade target list — whatever fits the specific bench. | **High** |
| 4 | **Contextual rookie draft tiering** ("re-tier the rookie class for Superflex Full PPR with my current roster") | Tier breaks shift by league settings; the right cluster boundaries differ each year. GenUI can render boundary explanations as ad-hoc callouts vs. forcing a fixed tier component. | **High** |
| 5 | **Conversational waiver/FAAB strategy** ("who should I bid on this week and what's max FAAB?") | The relevant metrics vary by player type — snap% trend for an RB, route participation for a WR. | **Medium-high** |
| 6 | **Roster-construction critique** ("I'm 4-24, rebuild. What does my window look like in 2027?") | Multi-axis: age, positional balance, pick capital, market value. | **Medium-high** |
| 7 | **Trade-finder agent** ("find two leaguemates I should call this week and why") | Needs to surface different evidence per partner — overrosters, holes, recent transactions. | **Medium** |
| 8 | **Aging-cliff post-mortems** ("show me how every WR I've owned aged past 28") | Personal-history shape is unique per user; static report can't anticipate it. | **Medium** |
| 9 | Weekly start/sit | A stable table beats GenUI. | **Low** — keep static |
| 10 | League standings, transactions log, calendar | Stable, declarative; GenUI is friction. | **Low** — keep static |

### Worked example: "3-year value outlook of my RB room if I trade my 2027 1st for Christian McCaffrey"

What the system should do, step by step:

1. **Intent parsing.** Claude Sonnet 4.6 with strict tool use receives the prompt + a structured `LeagueContext` object (roster_id=1, league_id=1314363401744416768, scoring=Superflex Full PPR, aging cliffs RB/26 WR/28 TE/30 QB/33). The tool catalog includes `simulate_trade`, `project_position_group`, `render_layout`.
2. **Tool invocation 1: `simulate_trade`.** Backend resolves "my 2027 1st" → the actual traded-pick asset on roster 1, "CMC" → player_id from Sleeper master. Returns post-trade roster JSON for both sides.
3. **Tool invocation 2: `project_position_group(position='RB', roster_id=1, years=[2026,2027,2028])`.** Runs the data-driven model (XGBoost/elastic net trained on PFR + nflverse + PlayerProfiler features your framework doc selects) and returns per-player projected fantasy points by year, with confidence intervals.
4. **Tool invocation 3: `render_layout`.** Claude emits a JSON layout spec validated against the component catalog. For this query it would compose:
   - `TradeHeader` (assets out / in, market-value delta, KTC + FantasyCalc divergence)
   - `PositionGroupTimeline` (line chart, pre-trade vs post-trade RB room PPG by year, with aging-cliff shading at RB-26)
   - `AgingCurveOverlay` (small multiples: each RB on the roster, curve from age-26 cliff overlay)
   - `OpportunityCostPanel` (what else that 2027 1st historically returns, p25/p50/p75)
   - `RoleSnapshot` (CMC's current snap%/touch share/red-zone share vs. injury-history flag)
   - `VerdictCard` (model-driven recommendation with the **three drivers** that moved the needle most — feature importance from the projection model)
5. **Stream to client.** AI SDK 5 `useChat` decodes tool-result parts, the client maps `toolName: 'render_layout'` → `<GenLayout spec={…} />`, which walks the JSON and renders each registered component. Skeletons appear immediately for each card; data fills in as `project_position_group` resolves.

The LLM never makes up a number. Every projection, market value, and confidence interval is pre-computed by the Python backend and either cached in DuckDB or fetched live from FantasyCalc/Sleeper.

---

## 2. Component Library & UX Patterns

### The atomic component catalog

Treat this as a single Zod schema your FastAPI middleware exposes to Claude as a strict tool. The LLM cannot emit a component name or prop name not in the catalog.

| Component | Required props | Data dependency | When the AI should pick it | Composes with |
|---|---|---|---|---|
| `TradeHeader` | `assets_out[], assets_in[], market_delta_pct` | KTC scrape + FantasyCalc API | Any trade evaluation | Anything |
| `PositionGroupTimeline` | `position, roster_id, years[], metric` | Internal projection model | Multi-year roster questions | `AgingCurveOverlay` |
| `AgingCurveOverlay` | `player_ids[], cliff_age` | nflverse historical + your aging model | When a question crosses an aging cliff | `PositionGroupTimeline`, `PlayerCard` |
| `PickValueSlider` | `season, round, league_settings` | KTC/FantasyCalc pick chart | Trades involving picks | `TradeHeader` |
| `RookieTierBoard` | `class_year, format_modifiers{}, count` | KTC rookie + your model | Rookie draft prep | `TierBreakNote` |
| `DepthChartCard` | `nfl_team, position, fantasy_roster_id?` | Sleeper + scraped depth | Injury or role questions | `SnapCountTimeline` |
| `SnapCountTimeline` | `player_id, weeks[]` | nflverse weekly | Role-trend questions | `TargetShareEvolution` |
| `TargetShareEvolution` | `player_id, weeks[]` | nflverse weekly | WR/TE outlook | `RoleSnapshot` |
| `MarketVsModelDivergence` | `player_ids[], market_source` | KTC/FantasyCalc + internal | Buy-low/sell-high lists | `VerdictCard` |
| `AgePositionScatter` | `roster_id, position?, league_avg_overlay` | Sleeper + birthdays | Roster-construction critique | `RoleSnapshot` |
| `RosterConstructionMap` | `roster_id, years[]` | Composite | Big-picture rebuild view | Anything |
| `OpportunityCostPanel` | `pick_asset, n=100` | PFR historical draft outcomes | Whenever a pick is in play | `VerdictCard` |
| `VerdictCard` | `recommendation, drivers[3], confidence` | Model output | Closing any analytical chain | Always last |
| `ExpectedRecoveryTimeline` | `player_id, injury_type` | Injury scrape | Injury-impact branches | `WeeklyFlexProjection` |
| `WeeklyFlexProjection` | `roster_id, weeks[], without_player_ids[]` | Projection model | "Who plays for the next 8 weeks?" | `ExpectedRecoveryTimeline` |
| `ReasoningTrace` | `feature_importance[], top_factors[]` | Model interpretability output | When user asks "why?" | Anything |

### UX safety guardrails

- **CLS prevention during stream.** Every component declares `min_height` per breakpoint in its schema. The renderer reserves space before data arrives. The Renderer pattern from json-render and LangChain's Generative UI guide handles this via `loading={true}` passed to children awaiting their tool results.
- **WCAG 2.1 AA.** Catalog components inherit from shadcn/ui + Radix primitives, which v0/Vercel and Crayon (the design system underneath Thesys C1) both build on — they ship correct ARIA roles, focus rings, keyboard trapping, and color contrast by default. Charts use Recharts with explicit `aria-label` props enforced at the schema level.
- **Slow/failed component renders.** Each `render_layout` JSON node has a `fallback` prop. If the resolving tool call times out (set hard 3s deadline per node), the renderer swaps to the fallback (usually `PlayerCard` or a plain markdown summary). The shell never freezes.
- **No raw HTML.** The renderer never compiles strings. There is no `dangerouslySetInnerHTML` anywhere. The catalog is closed.

### User correction mechanisms

The single most undervalued feature of generative UI is the correction loop. Four patterns, in order of complexity:

1. **Component-level edit (subtree regen).** Every rendered component has an invisible `data-node-id`. User clicks "swap this chart" → client sends just `{node_id, instruction: "replace with weekly projections line graph"}` to a `/regenerate-node` endpoint. The middleware re-runs only that subtree of the layout spec with the same parent context. The rest of the view stays mounted.
2. **View-level edit.** User says "redo this whole answer for 1QB instead of Superflex." Middleware re-runs the **entire** original prompt with a single override in `LeagueContext.format`. Cache hits 90% of the prefix.
3. **Conversation-anchored revision.** AI SDK 5's `messages` array stores tool-invocation results. A "revise" action references a prior message ID and emits a new `render_layout` whose JSON spec diffs against the prior one — only changed nodes get fresh component mounts (React keys).
4. **Undo.** Trivial because every layout spec is just JSON. Persist the spec array in localStorage; `Cmd+Z` pops the stack. No server roundtrip.

### What v0, Thesys C1, and Anthropic Artifacts are actually doing in production

- **Vercel v0** (March 2026 update) is now a full-stack app builder with Git, database connectivity, and agentic workflows. Internally it's a fine-tuned model + a hard-coded preference for shadcn/ui + Tailwind. **It is not the runtime pattern you want.** It's a development-time tool for generating component code, not for generating UI at user-prompt-time.
- **Thesys C1** is the most mature runtime offering: an OpenAI-compatible endpoint that returns Crayon-component JSON instead of text, with a React SDK that streams progressive renders. Their docs explicitly handle malformed-LLM-response repair and provider failover. A concrete production reference: Entelligence's "Ask Ellie" agent — founder Aiswarya Sankar posted on Thesys's Product Hunt page: "Thesys helped us power all the charts and reports in Ask Ellie, pulling data from multiple dashboards and turning it into clear visual insights that show up directly inside the chat experience." Entelligence reports one customer running "about 340 PRs a day" through the system (entelligence.ai/blogs/scoble-interview). **If you want to skip a year of plumbing work, Thesys is the buy-vs-build candidate.** The trade-off is lock-in to Crayon's component vocabulary; building your own football-specific catalog is more work.
- **Anthropic Artifacts** (Claude.ai's built-in code/document panel) is closest to a sibling pattern — Claude generates a runnable React component that lives in a side panel. It works because the rendered surface is isolated and the user can iterate. **It is not a model for production multi-component layouts.**
- **LangChain's Generative UI** (`@json-render/core`) and the broader **OpenUI standard launched March 11, 2026** are the open-source convergence point. **Your build target should be schema-compatible with OpenUI** so you can swap renderers later.

---

## 3. Technical & Architectural Blueprint

### End-to-end flow with latency budgets

```
┌──────────────┐   user prompt   ┌──────────────────┐   structured    ┌────────────────┐
│ Next.js      │────────────────▶│  FastAPI         │   tool calls    │  Claude        │
│ /chat        │  + LeagueCtx    │  /agent endpoint │◀───────────────▶│  Sonnet 4.6    │
│ useChat hook │                 │  (orchestrator)  │   layout JSON   │  (structured   │
└──────┬───────┘                 └──────┬───────────┘                 │   outputs)     │
       │                                │                             └────────────────┘
       │ stream parts                   │ tool dispatch
       │                                ▼
       │                         ┌──────────────────┐
       │                         │ DuckDB / Parquet │  ◀── nightly ETL ── nflverse, Sleeper,
       │                         │ (read-only)      │      FantasyCalc, scraped KTC/PFF/PP/RAS
       │                         └──────────────────┘
       │                                ▲
       │                                │ projections, simulations
       │                                ▼
       │                         ┌──────────────────┐
       │                         │ Projection model │ (Polars + scikit-learn / XGBoost)
       │                         │ Trade simulator  │  framework.yaml defines features
       │                         └──────────────────┘
       ▼
┌──────────────┐
│ Renderer     │  catalog of typed components, Suspense boundaries per node
│ (shadcn+Radix│
└──────────────┘
```

**Latency budget for a typical generative render:**

| Hop | Budget | Notes |
|---|---|---|
| Browser → Next.js → FastAPI | 30 ms | Same-region or same-host |
| FastAPI: build LeagueContext from cache | 20 ms | Redis or in-memory |
| FastAPI → Claude Sonnet 4.6 first token | 600–900 ms | With prompt caching, ~400 ms after warm |
| Claude: tool calls (1–3 round trips) | 200–500 ms each | Tools resolve against DuckDB/Polars locally (<50 ms typical) |
| Claude: final layout JSON | 800–1500 ms | Streaming starts at ~400 ms |
| Client renders first skeleton | <100 ms after first byte | Component map keyed on `toolName` |
| All data resolved + components hydrated | 2.5–4.0 s | Acceptable for a "thinking" answer |

### Middleware layer: which model for which job

| Job | Model | Why |
|---|---|---|
| Live generative UI prompt → layout JSON | **Claude Sonnet 4.6** with structured outputs | Best price/quality for strict tool use; 5x output ratio is predictable; structured outputs guarantee schema compliance |
| Cheap classification ("is this a trade question or a roster question?") | **Claude Haiku 4.5** | $1/$5 per MTok; 5x cheaper than Sonnet; latency <300ms |
| Long-context league history synthesis (every transaction since startup, all trade rumors, all chat logs) | **Gemini 2.5 Pro** via subscription | 1M context, the right tool when you need to read your entire league |
| One-off code generation, ETL script writing, schema migrations | **Codex CLI / ChatGPT Plus subscription** OR **Claude Code with Max** | Either subscription seat — no API spend |
| Schema design, prompt iteration, debugging | **Claude Code via Max** | Counts against your subscription, not API |
| Final "verdict" reasoning where quality matters most (championship-window decisions) | **Claude Opus 4.7** | Reserve for ≤5% of calls; same input price as Opus 4.6 but ~35% more tokens per text due to new tokenizer — budget accordingly |

### Frontend framework decision: be opinionated

For a single-user app with Python/FastAPI backend and generative streaming requirements, the choice is **Next.js (App Router) + AI SDK 5/6 + shadcn/ui**. Reasoning:

- **AI SDK has the most mature generative-UI primitives** of any framework in 2026 (`useChat`, tool invocations, streamable values). It is React-only in practice.
- **Vercel paused `streamUI`/RSC generative UI** (per GitHub Discussion #3251), but the replacement pattern (`streamText` + tool invocations + client component map) is more flexible *and* doesn't require RSC's bleeding edge. So you don't actually need RSC.
- **SolidJS is faster** — per PkgPulse's "React vs Solid.js in 2026" analysis, "Solid.js's fine-grained reactivity system is roughly 70% faster than React's Virtual DOM in standardized benchmarks" based on the krausest/js-framework-benchmark — but the AI SDK / Vercel / Thesys / shadcn ecosystem is React-centric. For a single-user app, the perf gains are imperceptible.
- **Qwik's resumability** matters when first-page load is the metric. This app has authenticated repeat visits; TTI doesn't matter.
- **HTMX + Alpine** would let you stay in Python end-to-end. Tempting. But streaming structured tool invocations from an LLM into typed components is fundamentally awkward in HTMX — you'd be reimplementing AI SDK in Python.

**Pick Next.js, not because it's perfect, but because it's where the generative UI ecosystem actually lives in 2026.** You keep FastAPI as the data/agent backend (Python is where nflverse, Polars, DuckDB, your projection models live). Next.js is the thin presentation layer plus the LLM orchestration shell. They talk via JSON over HTTP.

### Architecture pattern decision: JSON schema, not raw JSX

| | Pattern A: LLM emits JSON layout spec, client renders against catalog | Pattern B: LLM emits raw JSX/HTML, client compiles |
|---|---|---|
| Safety | High — closed catalog, no XSS surface, no fabricated components | Low — sandboxing JSX from an LLM is non-trivial |
| Determinism | High — schema validation rejects malformed output | Low — invalid JSX crashes the render |
| Speed | Faster — structured outputs use grammar-constrained decoding; smaller token count | Slower — JSX is verbose and token-expensive |
| Flexibility | Lower — bounded by catalog; new components need code | Higher — LLM can invent layouts |
| Model lock-in | Low — works with any JSON-capable LLM | High — depends on model's HTML/JSX competence |
| Debugging | Easy — log the spec, replay deterministically | Hard — every render is a stochastic JSX dump |

**Pick Pattern A.** The "more flexible" argument for raw JSX evaporates as soon as you realize the catalog is **your** product — extending it costs hours, not days, and every new component is permanent and reusable. Pattern B's flexibility is essentially "I can ship buggy, insecure, slow UI faster," which is not a good trade.

### Databricks vs. simpler alternatives — be honest

| Option | Capacity ceiling | Monthly cost (this workload) | Setup time | When it wins |
|---|---|---|---|---|
| **DuckDB + Parquet on disk** | ~hundreds of GB on a modern laptop | $0 | hours | Single-user analytical workload — your case |
| **Postgres + dbt** | TB-scale OLTP with extensions | $0 local / $10–25/mo managed | days | If you need multi-user writes or row-level constraints |
| **Polars in-process** | RAM-bound (~30 GB practical) | $0 | minutes | Hot-path projections, scoring runs |
| **SQLite** | small | $0 | minutes | Tiny config/state tables only |
| **Databricks (Premium)** | infinite | **$2,000–5,000/mo typical mid-size team baseline per costbench.com 2026 analysis (cloudforecast.io confirms)**, plus underlying cloud VM costs | days to weeks | TB-scale data, multi-team workspaces, Unity Catalog governance |

**Databricks is the wrong call for this app.** The single-user analytical workload — Parquet of nflverse PBP (~5–10 GB compressed), historical Sleeper snapshots (~MB), KTC/FantasyCalc time series (~MB), scraped PFF/PlayerProfiler (~hundreds of MB) — fits comfortably on a laptop SSD. DuckDB queries this in seconds (per Saurabh Sharma's April 2026 benchmark: "DuckDB is decisively faster than PostgreSQL for analytical queries, with 16–26x overall speedup" on 128.2M rows). The only argument for Databricks is "I have access," which is a sunk-cost argument. Use Databricks only if you later (a) add multiple users, (b) cross ~100 GB of hot data, or (c) need Delta Lake's ACID semantics for a write workload — none of which apply.

**Storage recommendation for Dynasty Genius:**

```
~/dynasty-genius/data/
├── raw/                    # immutable scraped/API pulls, partitioned by source/date
│   ├── sleeper/league=1314363401744416768/date=2026-05-25/...
│   ├── ktc/date=2026-05-25/...
│   ├── fantasycalc/date=2026-05-25/...
│   └── pff/...
├── silver/                 # cleaned, joined, Parquet
│   ├── players.parquet     # master player dimension
│   ├── pbp_2014_2025.parquet
│   ├── snap_counts.parquet
│   └── market_history.parquet
└── gold/                   # feature-engineered per the framework doc
    ├── features_qb.parquet
    ├── features_rb.parquet
    ├── features_wr.parquet
    ├── features_te.parquet
    └── aging_curves.parquet
```

Postgres holds **only** mutable state: `chat_sessions`, `saved_layouts`, `user_preferences`, `corrections_log`. Everything analytical is Parquet + DuckDB. This is the lakehouse pattern without the lakehouse vendor.

### LLM call layer — subscription vs. API discipline

| Activity | Channel | Why |
|---|---|---|
| Designing the component catalog, iterating prompts, generating ETL code | **Claude Code (Max plan)** | Already paid; doubled 5-hour limits as of recent update; weekly cap is the absolute ceiling but you'll only hit it during intense build sprints |
| Researching the framework doc against nflverse PBP, exploring data | **Gemini Pro web app** | 1M context, free under subscription, perfect for "what features should the framework include for WR breakouts?" sessions |
| Writing one-off Python scripts (scrapers, migrations) | **Codex CLI / ChatGPT Plus** | Subscription seat; no token meter |
| **Live user-facing generative UI render** | **Claude API (Sonnet 4.6 with structured outputs)** | Only path that bills per request; budget below |
| Heavy classification at scale (e.g., labeling 50K historical trades) | **Claude API (Haiku 4.5) + Batch API** | 50% discount for non-time-sensitive |
| Anything Anthropic-specific you'd want to A/B against | **Gemini API (2.5 Flash-Lite)** as fallback router | $0.10/$0.40 per MTok; cheapest reasonable model |

The hard rule: **subscription seats handle anything where you're the human in the loop. APIs only fire when a user prompt hits the live system.**

---

## 4. Data Integration & Context Engine

### Data streams, refresh cadence, and authority

| Source | What you pull | Cadence | How |
|---|---|---|---|
| **Sleeper API** | rosters, matchups, transactions, drafts, traded picks, NFL state | every 5 min in-season, daily off-season | direct REST, no key (<1000 req/min limit per Sleeper docs) |
| **nflverse / `nfl_data_py`** | PBP, weekly stats, snap counts, PFR advanced, FTN charting, draft picks | nightly during season | `nfl_data_py` Python lib; nightly Parquet snapshot |
| **FantasyCalc API** | dynasty + redraft trade values, 30-day trends | daily | JSON endpoint `api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` |
| **KTC** | crowdsourced market values, recent trades DB | weekly scrape (no API per KTC FAQ) | respectful HTML scrape; cache aggressively |
| **PFF** | snap%, route participation, YPRR, pass-block grades | weekly | scrape under personal subscription, store local Parquet |
| **PlayerProfiler** | Dominator Rating, breakout age, college dominator | weekly | scrape under subscription |
| **RAS.football** | athleticism scores for incoming rookies | once/year post-Combine | HTML scrape (no API; site has documented plugin issues currently) |
| **Injury reports** | official NFL injury reports + expected return | daily in-season | scrape NFL.com / ESPN; can use nflverse `load_injuries()` |
| **Depth charts** | who's actually starting/rotating | weekly | nflverse `load_depth_charts()` |
| **Coaching/scheme changes** | hires, fires, OC changes | as-needed (manual flag) | scrape ESPN/NFL.com headlines; tag in DB |

**Single-user economics let you cheat in your favor.** No enterprise feed is justified. The combination of nflverse (free, comprehensive, nightly), Sleeper (free, real-time), FantasyCalc (free JSON API), plus your own PFF and PlayerProfiler subscriptions for scraping covers ~95% of decision-quality data. Skip Pro Football Focus's enterprise API; their consumer subscription is enough.

### Context engine — how the agent maintains session state

This is the most important architectural decision after the JSON-vs-JSX one. Four options:

| Approach | Latency | Cost | Stability | Fit here |
|---|---|---|---|---|
| Server-side session store (Redis or Postgres `chat_sessions` table) | Low (<10ms lookup) | Trivial | High — you control invalidation | **Pick this** |
| Client-side state passed every request | Zero server lookup | Higher (more input tokens) | Brittle (browser refresh loses it) | No |
| Vector-indexed memory of prior interactions | High (embedding + retrieval) | Embedding storage + tokens | Overkill for one user with ~hundreds of turns | No |
| Structured "league context" object at top of every prompt | Low | Low with caching | High | **Combine with above** |

**Recommended approach: server-side session store + a structured `LeagueContext` block at the top of every prompt, with Anthropic prompt caching on the prefix.**

This aligns with Anthropic's own context-engineering guidance. Per "Effective context engineering for AI agents" (anthropic.com/engineering/effective-context-engineering-for-ai-agents): "Context engineering refers to the set of strategies for curating and maintaining the optimal set of tokens (information) during LLM inference… Given that LLMs are constrained by a finite attention budget, *good* context engineering means finding the *smallest* *possible* set of high-signal tokens that maximize the likelihood of some desired outcome." They specifically recommend "organizing prompts into distinct sections (like `<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`, etc) and using techniques like XML tagging or Markdown headers to delineate these sections."

```python
# FastAPI side, pseudocode
LEAGUE_CONTEXT = {
    "league": {"id": "1314363401744416768", "format": "Superflex", "ppr": 1.0, "teams": 12},
    "user": {"roster_id": 1, "team_name": "Woodbury Riders", "record": "4-24", "stance": "rebuild"},
    "framework": {
        "aging_cliffs": {"RB": 26, "WR": 28, "TE": 30, "QB": 33},
        "feature_groups": ["age", "opportunity", "efficiency", "athleticism", "market"],
        # this is the FEATURE SELECTION GUIDE, not weights
    },
    "rosters_summary": [...],   # all 12 teams, compact form
    "recent_transactions": [...],  # last 14 days
    "framework_doc": framework_yaml_compact,
}
# This block is ~6-8K tokens and stable across a session.

system_prompt = build_system_prompt(LEAGUE_CONTEXT)
messages = [
    {"role": "system", "content": system_prompt, "cache_control": {"type": "ephemeral"}},
    *session.history,  # last N turns
    {"role": "user", "content": user_prompt},
]
```

Anthropic's pricing docs confirm the caching mechanics: "5-minute cache write tokens are 1.25 times the base input tokens price," "1-hour cache write tokens are 2 times the base input tokens price," and "Cache read tokens are 0.1 times the base input tokens price." A worked monthly cost projection on Sonnet 4.6 ($3 input / $15 output per MTok) for this app, assuming 30 prompts/day, 8K stable prefix, 200-token queries, 2K outputs:

| Scenario | Math | Monthly cost |
|---|---|---|
| **No caching** | 900 × 8K input + 900 × 2K output = $21.60 + $0.54 + $27.00 | **~$49.14** |
| **5-min cache, prompts unclustered (worst case)** | Every request is a cache miss at 1.25x write premium | **~$54.54** (caching hurts) |
| **5-min cache, ~6 sessions/day × 5 prompts** (realistic) | 180 writes + 720 reads | **~$34.67** |
| **1-hour cache + keep-alive** | 480 writes/mo + 900 reads | **~$52.74** (write premium dominates at low volume) |

**Operational takeaway:** Use 5-min ephemeral caching, and design the UI so that follow-up prompts naturally cluster (e.g., once a user opens a "trade analysis" session, push them toward refining within 5 minutes rather than walking away and coming back). At 30 prompts/day this lands ~$35/month all-in for Sonnet — well under the $50–100 ceiling.

If usage doubles to 60/day, expect ~$70/month. If it 5xs, switch the default classifier to Haiku and reserve Sonnet for layout generation only — that pushes the blended rate back to ~$50.

### Token budget management

- **Stable vs. volatile.** Cache: framework doc, league settings, master player dimension, aging curves. Don't cache: this week's matchups, today's market values, latest injuries — pass these as fresh tool results.
- **When to summarize vs. send full.** Rule: if the data is more than 1.5K tokens and the user query likely needs only an aggregate, summarize via DuckDB in the tool call. If the user is asking a specific lookup, send the precise row.
- **Tool definitions are tokens too.** Per Anthropic's "Introducing advanced tool use on the Claude Developer Platform" post: "That's 58 tools consuming approximately 55K tokens before the conversation even starts. Add more servers like Jira (which alone uses ~17K tokens) and you're quickly approaching 100K+ token overhead. At Anthropic, we've seen tool definitions consume 134K tokens before optimization." Use Tool Search Tool (`defer_loading: true` on rare tools) so Claude only sees the 6–10 components and 4–5 data tools relevant to the current question.

### Storage layer recommendation, restated bluntly

- **Hot, mutable state (sessions, saved layouts, corrections):** Postgres if you go cloud (Railway/Fly), otherwise SQLite. Either works.
- **Everything analytical:** Parquet files on disk, queried with DuckDB. Use Polars for in-memory transforms during ETL.
- **Skip:** Databricks Delta tables (overkill), Snowflake (cost), MongoDB (wrong shape), Redis (you only need it for session cache, and Postgres handles that fine at this scale).

---

## 5. Implementation Roadmap & Risks

### Phased rollout, mapped to existing Phases 8/9/13/15/16/17

| Existing phase | New generative UI scope | Build target | Success metric |
|---|---|---|---|
| **Phase 8 (current engine)** | None — keep building the engine; lay only the *foundations* | Next.js shell with shadcn, FastAPI `/agent` endpoint scaffolded but no LLM calls yet; component catalog defined as Zod schema | Catalog renders deterministically from hand-written JSON specs |
| **Phase 9** | Hybrid: static shell + first 2 generative widgets | Trade Evaluator + Rookie Tier Board are generative; everything else static | First end-to-end "ask anything about a trade" works; ≤4s P95 to first useful component |
| **Phase 13** | Inject ML projections into the catalog | `project_position_group` tool returns model output; `VerdictCard` includes top-3 feature drivers | Projections render with confidence intervals; user can click "why?" and see feature importance |
| **Phase 15** | Injury simulation + 3-year roster outlook | `WeeklyFlexProjection` + `PositionGroupTimeline` + `ExpectedRecoveryTimeline` shipped | "If my RB1 tears ACL, what's my flex Weeks 7-14?" returns useful answer |
| **Phase 16** | Conversation-anchored revision + component-level edits | "Swap this chart" works; undo works | Average prompts-to-satisfaction (subjective): ≤2 |
| **Phase 17** | Fully generative "ask anything" surface | One page, one input box, every other view derived | Replace ≥3 previously-static views with generative equivalents that test better |

### Risk register

| Risk | Mitigation |
|---|---|
| **LLM hallucinates a player stat** | Constrained decoding via Anthropic structured outputs (beta header `structured-outputs-2025-11-13`); `player_id` typed as `z.enum(known_ids)`; LLM never writes numbers — only references tool-returned values; assertion layer rejects any rendered numeric not traceable to a tool call |
| **API costs spike** | Hard monthly cap via Anthropic console; Haiku fallback when Sonnet quota approaches limit; cache hit ratio tracked daily; alert at 70%/85%/95% of budget |
| **User cognitive overload — too much GenUI** | Keep ~60% of app declarative (rosters, lineups, standings, KTC tables). GenUI only fires from the "Ask" surface, not from primary navigation. A/B test each generative surface against its static equivalent |
| **Streaming jank / CLS** | Schema-declared `min_height` on every component; Suspense boundaries per tool result; skeleton states standardized in catalog |
| **Accessibility regression** | All components built on Radix + shadcn primitives that ship correct ARIA; axe-core CI check on the rendered DOM of a fixed set of "golden" specs |
| **Lock-in to Claude** | Layout JSON schema is provider-agnostic; abstraction layer `LLMAdapter` with `claude.py` / `gemini.py` / `openai.py` adapters; structured outputs are now offered by all three (Anthropic structured outputs, Gemini response schema, OpenAI strict mode); swap is ~1 week of work, not a rewrite |
| **Sleeper or KTC blocks scraping** | Sleeper is explicit no-auth public API; not at risk. KTC: cache aggressively, scrape weekly, fall back to FantasyCalc which has a real API |
| **PFF/PlayerProfiler ToS** | Personal-use scraping for a single-user app stays well within fair use; never redistribute scraped data; rate-limit politely |

### Concrete monthly cost projection

| Line item | Cost | Notes |
|---|---|---|
| Claude API runtime (Sonnet 4.6, 30 prompts/day, session-clustered cache) | **~$35** | See arithmetic above |
| Headroom for Opus 4.7 on ~5% of high-stakes calls | **~$8** | Reserve for championship-window decisions |
| Gemini Flash-Lite fallback / classification | **~$2** | $0.10/$0.40 per MTok |
| FastAPI hosting (Fly.io or Railway Hobby) | **$5–10** | Or $0 if local-only |
| Next.js frontend on Vercel Hobby | **$0** | Single-user fits free tier |
| Postgres (if cloud) | **$5** | Or SQLite for $0 |
| **Total marginal monthly** | **~$50–60** | Existing Claude Max / Gemini Pro / ChatGPT Plus subs absorb all development costs |

### Local-only vs. cloud hosting

| | Local-only (FastAPI + Next dev server on your machine) | Cloud (Fly.io / Railway / Vercel) |
|---|---|---|
| Cost | $0 | $10–20/mo |
| Always-on | No — needs your laptop running | Yes |
| Latency to Claude API | Excellent if you're on good home internet | Excellent |
| Mobile access while traveling | No (unless you use Tailscale or a tunnel) | Yes |
| Data privacy | Maximum | Still good — all data is public-source anyway |
| **Recommendation** | **Start here for Phases 8–13** | **Move here at Phase 15 when injury alerts and live in-season use matter** |

---

## Final Recommendation: What to Build First

**Three things, in this exact order, before adding any new model or chart:**

1. **Lock in the component catalog as a Zod schema** in your Next.js repo. 12–15 components defined with types and `min_height`. No LLM yet. Render them by hand from sample JSON specs. This forces you to think in catalog primitives before the LLM tempts you into improvising.

2. **Stand up the `/agent` endpoint in FastAPI** that takes `{prompt, league_context, session_id}`, calls Claude Sonnet 4.6 with structured outputs against your catalog tool, and streams the layout JSON back. Wire up exactly one query: "Show me my RB room over the next 3 years." No trades yet, no rookies — just the simplest possible generative render that exercises the full plumbing: prompt caching, tool call, projection model stub, layout JSON, streamed render.

3. **Then** layer trade simulation onto that. Reuse `PositionGroupTimeline` and add `TradeHeader`, `PickValueSlider`, `VerdictCard`. The CMC-for-2027-1st example from Section 1 becomes the integration test.

Everything else — injury sim, rookie tiering, market divergence, the rest of the catalog — follows the same template once the first three steps are solid.

**What not to do first:**
- Don't pick a hosting platform yet. Local is fine until Phase 15.
- Don't touch Databricks. Don't even create the workspace; it'll burn DBUs in the background.
- Don't try to make this work on Pages Router or with RSC streaming. Both are dead ends for new builds in 2026.
- Don't build a "chat that can do anything" surface as Phase 1. The cognitive load on you (designing prompts, watching for hallucinations, debugging spec output) is too high without the component catalog locked first.
- Don't pay for any new LLM seats. Claude Max + Gemini Pro + ChatGPT Plus already cover development.

The framework-as-feature-selector, data-as-algorithm principle survives this architecture cleanly: the LLM is a presentation-layer router, not a numerical reasoner. It picks components and composes layouts. Every number on the screen comes from a tool call that ran your model on cached, validated data. That separation is what makes the whole thing safe, debuggable, and cheap to operate.

---

## Caveats

- **2026 LLM landscape moves monthly.** Sonnet pricing has held at $3/$15 across four releases, but the next Anthropic generation could change ratios. The 5-min vs 1-hour cache TTL economics are sensitive — re-run the arithmetic if Anthropic changes the multipliers. Community reports (DEV.to "Claude Prompt Caching in 2026") have claimed Anthropic shortened a previous 60-min default to 5-min in early 2026, raising effective costs 30–60%; this is not Anthropic-confirmed but worth monitoring.
- **Vercel AI SDK RSC is paused, not killed.** Per maintainer @lgrammel in GitHub Discussion #3251: "Development of AI SDK RSC is paused. We recommend using AI SDK UI." Vercel could revive it; if they do, the migration cost from `useChat` + tool invocations back to `streamUI` is small (the components remain, only the orchestration changes). Don't bet the architecture on it returning, but don't burn bridges either.
- **Scraping is a maintenance tax.** KTC, PFF, PlayerProfiler, and RAS.football all change their site structure occasionally. Budget ~2–4 hours/month for scraper maintenance. RAS.football is currently warning of plugin issues on its homepage — confirm it stabilizes before depending on it.
- **Anthropic structured outputs are beta as of late 2025/early 2026.** Beta status means the API contract can change; pin the beta header version and watch the changelog. The feature is stable enough for production single-user use; just don't be surprised by a header rename.
- **MCP is now governed by the Agentic AI Foundation (Linux Foundation)** after Anthropic donated it in December 2025, with the current released spec dated 2025-11-25 and a 2026-07-28 release candidate in flight per blog.modelcontextprotocol.io. If you adopt MCP servers (e.g., a Sleeper MCP), pin to the released spec version and revisit when the next final ships.
- **The "data is the algorithm" principle requires discipline.** It's tempting to put rules into the prompt ("weight age higher for RBs"). Resist. The framework doc selects features; the model trains on history; the prompt only describes what to render. Every time you find yourself writing weights in a prompt, that's a sign a feature belongs in the framework doc and the data layer.
- **Production case studies for generative UI in single-user verticals remain thin.** Entelligence's "Ask Ellie" (Thesys C1) is the closest analog, with one customer running ~340 PRs/day, but no published cost/build-time deltas. Chicago Global is named on Thesys's homepage as a generative-UI financial-data customer but has no public case-study page with quantitative outcomes. Treat your architecture as ahead of the published-case-study curve — that's appropriate for a personal app where the goal is your own decision quality, not a marketing reference.