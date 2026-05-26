# Operational Playbook: Agent-Driven Dynasty Fantasy Football App (FastAPI + React/TypeScript, 2026)

## TL;DR

- **Codegen the contract, don't hand-write it.** Use Hey API (`@hey-api/openapi-ts`) as your single source of truth from FastAPI's OpenAPI → TypeScript types + Zod v4 schemas + TanStack Query hooks; it is the one tool actively shipping new features (releases on 2026-04-20, 2026-04-28, 2026-05-04 visible in their newreleases.io feed) and the project repo describes itself as *"OpenAPI to TypeScript codegen. Production-grade SDKs, Zod schemas, TanStack Query hooks, and 20+ plugins. Used by Vercel, OpenCode, and PayPal."*
- **Treat the multi-agent peer-review on one branch as a protocol, not a vibe.** Run `AGENTS.md` (released by OpenAI in August 2025, moved to Linux Foundation stewardship via the Agentic AI Foundation on December 9, 2025) as the single source of truth, symlink or `@import` it from `CLAUDE.md`, and use OpenAI's official `codex-plugin-cc` (`/codex:review`, `/codex:adversarial-review`, `/codex:rescue`) from inside Claude Code so Codex's review pass runs as a Stop-hook gate, not a parallel guess.
- **Pin the boring stack and don't fight it.** Vite + React 19 + TS strict + Tailwind v4 + shadcn/ui (new-york, OKLCH tokens) + TanStack Router + TanStack Query + TanStack Table + TanStack Virtual + Zod v4 + Biome + Vitest + Playwright + pnpm 10 + mise (Node 22 LTS). Use Observable Plot via a tiny `useEffect` wrapper for the analytical charts that justify Plot's grammar; use Recharts (or Tremor — Vercel-acquired January 23, 2025, all blocks now free/MIT) anywhere a stock dashboard chart will do; reach for Visx only for the one or two genuinely bespoke visualizations (quantile dotplot, calibration plot).

---

## Key Findings

### What's settled (use these without debate)

| Area | Pick | Why |
|---|---|---|
| Pydantic → TS/Zod | **Hey API (`@hey-api/openapi-ts`)** with `zod` + `tanstack-query` plugins | Active maintenance through May 2026, Vercel/PayPal/OpenCode in production, plugin architecture, Zod v4 first-class |
| Component library | **shadcn/ui new-york style + Radix** | Copy-paste source, no abstraction tax, official Tailwind v4 + React 19 path |
| CSS / tokens | **Tailwind v4 with `@theme inline` + OKLCH** | CSS-first, no `tailwind.config.js`, opacity modifiers work, dark-first via `.dark` class + `@custom-variant` |
| Server state | **TanStack Query v5** | Universal in TanStack codegen output |
| Tables | **TanStack Table v8 + TanStack Virtual** (row + column virtualization, CSS grid layout for dynamic row heights) | The canonical dense-grid stack; pattern documented at tanstack.com/table/v8/docs/framework/react/examples/virtualized-rows |
| Router | **TanStack Router** | Type-safe search params/loaders matter for Trade Lab + URL-hash-addressable Player Detail drawer |
| Command palette | **`cmdk` (via shadcn `Command` component)** + TanStack Virtual for the 600-player list | Same library Linear/Raycast use; battle-tested |
| Validation | **Zod v4** | Native `.meta()` for OpenAPI, faster, broader ecosystem |
| Lint+format | **Biome v2** | One tool; Biome's own benchmarks (biomejs.dev) state *"scores 97% compatibility with Prettier"* and *"can be 25x faster than the ESLint + Prettier combo"*; eliminates the config matrix |
| Tests | **Vitest** (unit) + **Playwright** (E2E) + **MSW** (network mocks) + **Testing Library** | Vitest is the Vite-native default; Playwright MCP integrates with Claude Code |
| Pkg mgr | **pnpm 10** | ~50.2M weekly npm downloads (per npmtrends.com, v10.32.1), strict node_modules, lifecycle scripts opt-in since 10.0; safest for long-lived solo projects |
| Toolchain pin | **mise** | Rust-based, asdf-compatible, single `.tool-versions` for Node/Python/pnpm; fastest activation |
| Multi-agent project file | **`AGENTS.md`** as source of truth, **`CLAUDE.md`** as thin layer that `@AGENTS.md`-imports | LF/AAIF standard; Claude Code doesn't natively read AGENTS.md as of May 2026, but `@import` is the documented workaround |
| Peer-review protocol | **`openai/codex-plugin-cc`** inside Claude Code, optionally with `--enable-review-gate` Stop hook | The only first-party Claude↔Codex bridge; written by OpenAI |

### What's contested (and how to decide)

**TanStack Router vs React Router v7** — TanStack wins for a single-user analytical SPA. End-to-end type-safe search params is exactly what a Trade Lab builder, a URL-hash-addressable Player Detail drawer, and a Research Assistant workbench need; you'll be passing 10+ scoped filters in URLs and you do not want stringly-typed `useParams<{id: string}>` casts. React Router v7's edge is RSC/Remix-style SSR, which you do not have and do not need. *Recommendation: TanStack Router.*

**Biome vs ESLint+Prettier** — Biome wins for a solo, greenfield, single-user app on a stack with zero custom plugins. The one residual gap is type-aware rules (no-floating-promises, react-hooks deps) that still require `@typescript-eslint` and `eslint-plugin-react-hooks`. *Recommendation: Biome v2 as primary; layer ESLint *only* for `eslint-plugin-react-hooks` and `@typescript-eslint/no-floating-promises` if and when you actually catch a bug those would prevent.*

**Charting: Visx vs Recharts vs Observable Plot vs Tremor** — You have three different chart needs:
1. **Stock dashboard charts** (sparklines, KPI tiles, bar/line, age-curves): **Tremor's open-source components** (Vercel-owned since January 23, 2025, Recharts under the hood, MIT, free) or plain **Recharts**. Tremor's strength is that the analytical-cockpit aesthetic is already styled — small KPI deltas, tabular nums, dark mode.
2. **Small-multiples, quantile dotplots, calibration plots** (your weird ones): **Observable Plot** via a tiny `useEffect` wrapper. Plot's grammar (`marks`, `facets`) is purpose-built for what you described.
3. **One-off bespoke viz** (League Opportunity Map, Trust/Backtest fan chart): **Visx** is the right choice when Plot's grammar runs out — you get D3 primitives with React lifecycle.

Skip Plotly (license + bundle size), Nivo (slower release cadence), and ECharts (overkill for SVG-density data).

**pnpm vs Bun** — pnpm 10. Bun is 3-5× faster on cold installs but binary lockfile, smaller ecosystem, and you don't need the 4 seconds. pnpm's "lifecycle scripts opt-in by default since 10.0" is exactly the Saturday-morning catastrophe insurance you want.

### What changed since 2025 (be alert)

- **shadcn/ui v4** deprecated `forwardRef`, replaced `tailwindcss-animate` with `tw-animate-css`, deprecated `toast` in favor of `sonner`, moved HSL → OKLCH, and added `data-slot` attributes to every primitive.
- **Tremor was acquired by Vercel on January 23, 2025.** Per Vercel's own announcement (vercel.com/blog/vercel-acquires-tremor): *"Today, Tremor and its cofounders Severin Landolt and Christopher Kindl are joining Vercel's Design Engineering team."* All previously-paid Tremor Blocks went MIT/free post-acquisition; Tremor v3 components are now drop-in.
- **Cal.com closed-sourced** — the open-source artifact is `cal.diy`. The Cal.com Storybook (`ui.cal.com`) is still browsable as a reference for shadcn-style design system patterns.
- **AGENTS.md became a Linux Foundation project.** Per the LF press release (Dec 9, 2025): *"Released by OpenAI in August 2025, AGENTS.md is a simple, universal standard that gives AI coding agents a consistent source of project-specific guidance needed to operate reliably across different repositories and toolchains."* Per OpenAI's own announcement (openai.com/index/agentic-ai-foundation/): *"Since its release in August 2025, AGENTS.md has been adopted by more than 60,000 open-source projects and agent frameworks including Amp, Codex, Cursor, Devin, Factory, Gemini CLI, Github Copilot, Jules and VS Code among others."*
- **Anthropic blocked Claude Pro/Max subscriptions** from being used by most third-party multi-agent orchestrators on April 4, 2026 — Claude Squad, OpenClaw, Ruflo, etc. now require API billing for orchestration. Anthropic's first-party `Agent Teams` (experimental, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=true`) is the only fully-supported path on a Pro/Max plan.
- **Codex `gpt-5.4-mini`** and Claude **Opus 4.7 / Sonnet 4.6 / Haiku 4.5** are the current production models (Sonnet 4 + original Opus 4 retire 2026-06-15).
- **Tremor v4**, **Recharts 3**, **Zod v4**, **Pydantic v2.13** (with v2.14 in alpha), **TanStack Table v8.x**, **TanStack Virtual 3.x**, **Tailwind v4.x**, **Vite 7.x**, **Vitest 3.x** are all on stable cadence.

### What to avoid

- **`pydantic2ts`** — last meaningful release was 2022/2023; the maintained replacement path is Pydantic → OpenAPI (FastAPI) → TS via Hey API.
- **`datamodel-code-generator` in reverse** — possible but operationally fragile; you'd be running Python on the frontend side. Skip.
- **Orval** — still maintained, but Hey API has overtaken it in both maintenance velocity and TanStack Query/Zod integration. If you already had Orval running on a project, fine; for greenfield, pick Hey API.
- **Kubb** — promising plugin architecture, but smaller adoption and an operation-scoped type model that fights with app-level Zod schemas. Skip for a solo project.
- **Stainless** — commercial SDK generator, designed for selling SDKs to external consumers. Overkill for a single-user app talking to its own FastAPI backend.
- **`openapi-typescript-codegen`, openapi-generator's TS client** — older, less ergonomic, weaker Zod story.
- **Claude Squad / OpenClaw / Ruflo on Pro/Max** — blocked by Anthropic policy April 4, 2026. Requires API billing.
- **`forwardRef` in new components, `tailwind.config.js`, HSL color tokens** — all replaced by React 19 / Tailwind v4 / OKLCH conventions in shadcn new-york.

---

## Details

### 1. Pydantic ↔ TypeScript/Zod Codegen

**Adopted: Hey API (`@hey-api/openapi-ts`) with plugins.** It is on an active release cadence and ships a first-party Vite plugin (`@hey-api/vite-plugin`) plus a Zod plugin tuned for Zod v4 metadata.

**Concrete pipeline for this project:**

1. FastAPI generates OpenAPI 3.x at `/openapi.json` (already free with `@fastapi.openapi`).
2. Add to backend a small CLI script (`scripts/dump_openapi.py`) that writes `openapi.json` to disk on every backend startup or via a `make openapi` target.
3. Frontend has `openapi-ts.config.ts`:
   ```ts
   import { defineConfig } from '@hey-api/openapi-ts';
   export default defineConfig({
     input: '../backend/openapi.json',
     output: { path: 'src/api', format: 'biome', lint: 'biome' },
     plugins: [
       '@hey-api/client-fetch',
       '@hey-api/schemas',
       '@hey-api/typescript',
       { name: '@hey-api/sdk', validator: true, transformer: true },
       'zod',
       '@tanstack/react-query',
     ],
   });
   ```
4. `pnpm openapi` regenerates `src/api/` — treat it as a build artifact (do not edit), commit it so agents have something to read.
5. A pre-commit hook (`lefthook` or `husky`) runs `openapi-ts` if `backend/**/*.py` changed and fails if `src/api/` is dirty after generation.

**Runtime validation strategy**: For an analytical single-user app reading mutable JSON, validate at the **edge** (every API response goes through the generated Zod schema). Enable Hey API's `validator: true` on the SDK plugin and you'll get response validation for free. Mark anything weird-looking (an unexpected `null`, an out-of-bound percentile) as a Zod parse error that surfaces in the UI as a "data quality issue" rather than a silent NaN.

**Why not also generate Zod on the Python side?** You could (`pydantic` → JSON Schema → `json-schema-to-zod`), but it adds a second source of truth. The OpenAPI document FastAPI already emits is the right single source.

### 2. shadcn/ui + Radix + Tailwind v4 + TanStack patterns

**Design tokens (the dark cockpit).** Tailwind v4's `@theme inline` is the single point of truth. The shadcn pattern is:

```css
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));

:root {
  /* light surface defaults — present but you'll force-dark in production */
}
.dark {
  --background: oklch(0.14 0.005 285);
  --foreground: oklch(0.96 0.003 286);
  --muted: oklch(0.18 0.006 286);
  --muted-foreground: oklch(0.65 0.012 286);
  --border: oklch(0.22 0.006 286);
  /* two-track separation for model vs market lanes: */
  --model: oklch(0.74 0.13 215);    /* cool blue, your model lane */
  --market: oklch(0.78 0.14 65);    /* warm amber, market lane */
  --radius: 0.375rem;               /* tight cockpit corners */
}
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-muted: var(--muted);
  --color-model: var(--model);
  --color-market: var(--market);
  /* etc. */
}
```

OKLCH is mandatory because (a) it's perceptually uniform, so your model/market lane colors look balanced in dark mode without manually re-luminance-matching, and (b) shadcn new-york now ships OKLCH by default.

**Component-override structure.** Don't subclass shadcn — own the source. The shadcn philosophy (from the docs) is: *"one of the major advantages of using shadcn/ui is that the code you end up with is exactly what you'd write yourself."* For your design system:

```
src/components/
  ui/                  # shadcn-generated primitives, edited freely
    button.tsx
    dialog.tsx
    command.tsx        # cmdk wrapper for ⌘K
  cockpit/             # YOUR design system on top of ui/
    Cell.tsx           # tabular-nums monospace data cell
    KPITile.tsx
    LaneBadge.tsx      # model/market variant
    DensityProvider.tsx# context for compact/comfortable
```

Use `class-variance-authority` (already a shadcn dep) for variant matrices on cockpit components.

**Typography.** Inter Variable for UI, JetBrains Mono for numerics and codes, with `font-variant-numeric: tabular-nums slashed-zero` set globally on data cells. This is the standard Bloomberg/Linear/Koyfin convention.

**TanStack Table for dense grids.** Use the "spacer-based virtualization" pattern documented at tanstack.com/table/v8/docs/framework/react/examples/virtualized-rows: render `<table style={{ display: 'grid' }}>`, use `useVirtualizer` from `@tanstack/react-virtual` for rows, keep the row virtualizer in the lowest possible component (TableBody) to avoid re-renders, and use `position: sticky` headers + CSS grid for dynamic row heights. For your Roster Audit / Rookie Board / League Opportunity Map cross-column scoring, define a `meta: { lane: 'model' | 'market', formatter: 'pct' | 'rank' | 'tier' }` on each column so cells can pull cockpit styling without per-cell conditionals.

**TanStack Virtual for ⌘K.** The 600-player palette doesn't need a full table — use a flat virtualized `useVirtualizer({ count: matches.length, estimateSize: () => 32, overscan: 8 })` inside the `cmdk` `CommandList`. Pre-filter with `cmdk`'s built-in fuzzy scorer (it uses `command-score`) and only re-virtualize the filtered set.

**Routing.** TanStack Router. Define each surface as a route with typed `validateSearch` Zod schemas. The Player Detail drawer is *not* a route — it's a sibling state addressable by URL hash (`#player=12345`), captured by a `useHash` hook and a `<PlayerDetailDrawer />` mounted at the root. This keeps the drawer cross-cutting per spec.

**Charts.** Three-tier strategy:
- **Tremor** for KPI tiles, sparklines, simple bars/lines on the Command Center home. (Now Vercel-owned, MIT, free.)
- **Observable Plot** for small-multiples, age-curves, faceted distributions. The standard React integration is the `useEffect`-and-append pattern, no wrapper library needed:
  ```tsx
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const chart = Plot.plot({
      marks: [Plot.dot(data, { x: 'age', y: 'value', stroke: 'lane' })],
      color: { domain: ['model', 'market'], range: ['var(--model)', 'var(--market)'] },
    });
    ref.current?.append(chart);
    return () => chart.remove();
  }, [data]);
  ```
- **Visx** for the bespoke ones (quantile dotplot, calibration plot, fan chart). Wrap each in a `<VisxFigure>` that handles ResizeObserver + theme.

### 3. AI agent pair-programming on the same branch — the central operational pattern

This is the part you'll re-read every week, so it gets the most detail.

#### 3a. The file layout that makes the three-agent pattern work

```
repo/
  AGENTS.md                # source of truth (LF/AAIF spec, 60k+ repos per OpenAI's own announcement)
  CLAUDE.md                # one line: "@AGENTS.md plus Claude-specific addenda below"
  GEMINI.md                # one line: "@AGENTS.md, read-only PM context below"
  .codex/
    config.toml            # codex model + effort
  .claude/
    skills/                # CLAUDE-Code skills (project-scoped)
    rules/                 # path-scoped rules
  docs/
    decisions/             # ADR-style: 0001-pick-tanstack-router.md
    specs/                 # spec-driven dev: 0001-trade-lab.md
    runbooks/              # how to regen openapi, run tests, etc.
  scripts/
    dump_openapi.py
    regen_api.sh
```

**`AGENTS.md` content (the operational policy, not the README).** The AGENTS.md spec deliberately leaves structure open ("use whatever headings make sense"), but the Linux Foundation describes it as *"a simple, universal standard that gives AI coding agents a consistent source of project-specific guidance needed to operate reliably across different repositories and toolchains."* For this project, the file should contain only what an agent needs *before its first character*:

1. Exact commands (`pnpm dev`, `pnpm test`, `pnpm openapi`, `pnpm check` for biome+tsc)
2. Numbered priorities (`Priority 1: tsc --noEmit passes. Priority 2: biome check passes. Priority 3: Vitest green.`)
3. Hard rules (`Never edit src/api/ — regenerate via pnpm openapi.`)
4. Tool stack (so the agent knows *not* to suggest npm i tailwind-config when you're on v4)
5. Definition of done (PR description checklist)

Keep it under 200 lines. Long files burn tokens and the agent ignores deep instructions.

**Critical**: As of May 2026, Claude Code still does not natively read AGENTS.md (per Anthropic's own docs; tracked as an open GitHub issue with thousands of upvotes). The documented workaround is to put `@AGENTS.md` at the top of `CLAUDE.md`, or `ln -s AGENTS.md CLAUDE.md` on macOS/Linux.

#### 3b. Same-branch coordination protocol

You explicitly want Claude Code and Codex on the *same git branch*, alternating implementer/reviewer. The proven pattern in 2026 is:

1. **One agent writes at a time, never both.** Tmux pane focus is the lock. The "implementer" pane is whichever agent is currently editing files; the other pane is reviewing the last commit. You enforce this by hand (you're the one swapping focus).
2. **Commit at every handoff.** Implementer agent finishes a unit of work → runs `pnpm check && pnpm test` → commits with a structured message:
   ```
   feat(trade-lab): scaffold builder state machine
   
   [implementer: claude-code, session-id: ...]
   [next: codex review for: state-machine correctness, edge cases]
   ```
3. **Reviewer agent reads the diff, not the whole repo.** Use `/codex:review` (or `/codex:adversarial-review` for sensitive paths). OpenAI's plugin README documents the command as: *"Runs a normal Codex review on your current work. It gives you the same quality of code review as running /review inside Codex directly."* The review is read-only — it writes findings to a PR comment (if there is a PR) or to `.codex/reviews/<id>.md`.
4. **Implementer applies the review.** Implementer agent reads the review artifact and addresses findings as a new commit `fix(trade-lab): address codex review #2`.
5. **Repeat until clean.** Either you call it done, or you enable the Stop hook (next section).

**Optional Stop-hook gate.** OpenAI's codex-plugin-cc has a documented review-gate mode: *"When the review gate is enabled, the plugin uses a Stop hook to run a targeted Codex review based on Claude's response. If that review finds issues, the stop is blocked so Claude can address them first."* OpenAI's own docs add: *"The review gate can create a long-running Claude/Codex loop and may drain usage limits quickly. Only enable it when you plan to actively monitor the session."*

For solo development, **leave the Stop-hook gate OFF by default** and trigger reviews manually with `/codex:review`. Enable it only for high-risk surfaces (Trade Lab state mutation, Backtest math).

#### 3c. The PM (Gemini) layer

Gemini CLI reads AGENTS.md natively. Give Gemini read-only access to:
- `docs/specs/` — for understanding what surfaces are pending
- `docs/decisions/` — for understanding why current code looks the way it does
- The actual code (read-only)
- Git log

And give Gemini one job: *"Write a 10-line standup summary every morning. List: what shipped yesterday, what's in-progress, what's blocked, what spec needs a decision."* Gemini writes to `docs/standups/YYYY-MM-DD.md`. This keeps the human PM context fresh without burning Claude/Codex context.

#### 3d. Memory and context across sessions

Three layers:
1. **Durable, versioned (always relevant)** → `AGENTS.md` + `CLAUDE.md` + `docs/decisions/`
2. **Spec-scoped (current feature)** → `docs/specs/0007-trade-lab.md` — the agent reads it at the start of a session and writes back to it as understanding evolves. This is the pattern documented in `alexop.dev`'s spec-driven Claude Code post (*"The SQLite to IndexedDB migration would have taken me 2-3 days manually. With this workflow, it took one afternoon."*): a `tasks.md` file as persistent memory across subagent sessions with atomic commits.
3. **Session-scratch (this conversation)** → in-memory only, summarized into spec file on context compaction.

For Claude Code specifically, use `/compress-session` (v1.9.0+) before any context-pressure event, and the `PreCompact` hook to auto-snapshot.

#### 3e. tmux orchestration

You already have the three-pane setup. The 2026 best-practice variant:

- **Pane 1 (top-left)**: Claude Code, working dir = repo root, `--dangerously-skip-permissions` ONLY if you trust your AGENTS.md (otherwise use `bypassPermissions` per-tool).
- **Pane 2 (top-right)**: Codex CLI, working dir = repo root, same branch.
- **Pane 3 (bottom)**: Gemini CLI, read-only by convention (Gemini doesn't enforce; you do via AGENTS.md priorities).
- **Pane 4 (split)**: `pnpm dev` + dev server logs + watch tsc.

If you want zero-config orchestration on top of this, `claude-squad` (vibecodinghub.org review confirms it works with Claude Code, Codex, Gemini CLI, Aider, OpenCode, Amp) is the most-cited 2026 option — but be aware Anthropic blocked it from Pro/Max usage on April 4, 2026. If you're on a Claude Pro/Max plan, **use Anthropic's first-party `Agent Teams`** (set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=true`, requires Opus 4.6+ as documented in the Claude Code agent-teams docs).

#### 3f. Skills, slash commands, MCP servers (the concrete install list)

**Must-install MCP servers:**

| MCP | Source | Install (Claude Code) | What it does |
|---|---|---|---|
| **Context7** | `upstash/context7` | `claude mcp add context7 -- npx -y @upstash/context7-mcp --api-key $C7_KEY` | Pulls *version-pinned* docs into prompts. Project description: *"Context7 pulls up-to-date, version-specific documentation and code examples straight from the source — and places them directly into your prompt."* Critical for "what's the TanStack Router v1.x API for `useSearch`?" |
| **Playwright MCP** | `microsoft/playwright-mcp` | `claude mcp add playwright -s user -- npx @playwright/mcp@latest` | Browser automation via accessibility tree, no vision model needed |
| **Chrome DevTools MCP** | `ChromeDevTools/chrome-devtools-mcp` | `claude mcp add chrome-devtools npx chrome-devtools-mcp@latest` | Performance traces, network waterfall, console — what Playwright MCP *can't* do |
| **Shadcn MCP** | docs at `ui.shadcn.com/docs/mcp` (built into shadcn CLI itself); community alternative `Jpisnice/shadcn-ui-mcp-server` | Per shadcn CLI docs | Lets the agent browse and install registry components in natural language. Per shadcn docs: *"The shadcn MCP Server allows AI assistants to interact with items from registries. You can browse available components, search for specific ones, and install them directly into your project using natural language."* |
| **FastAPI MCP / fastapi-mcp-openapi** | `alamkanak/fastapi-mcp-openapi` (`FastAPIMCPOpenAPI(app)` → `/mcp`) or the more featureful `jlowin/fastmcp` 2.0 (`FastMCP.from_fastapi(fastapi_app)`) | `pip install fastapi-mcp-openapi` then mount | Exposes endpoint introspection / OpenAPI docs to agents |
| **OpenAPI Schema MCP** | `hannesj/mcp-openapi-schema` | `claude mcp add openapi-schema npx -y mcp-openapi-schema` | If you want the agent to query schemas without re-reading the giant openapi.json |

**Should-install Claude Code skills:**

From Anthropic's official `anthropics/skills` repo, the relevant ones are `frontend-design` (create distinctive, production-grade frontend interfaces with high design quality), `webapp-testing` (Playwright-based local web app testing), and `theme-factory`. The official Anthropic-published `web-artifacts-builder` skill is documented as a *"suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui)"* — its prompts and patterns are worth reading even if you don't run it.

For your stack specifically:

| Skill | Source | What it does |
|---|---|---|
| `tailwind-v4-shadcn` | `jezweb/claude-skills` | Tailwind v4 + shadcn setup pattern: *"Production-tested setup for Tailwind CSS v4 with shadcn/ui, Vite, and React… Covers: @theme inline pattern, CSS variable architecture, dark mode with ThemeProvider, component composition, vite.config setup, common v4 gotchas."* |
| `tanstack-table` | `jezweb/claude-skills` (browsable at `claude-plugins.dev/skills/@jezweb/claude-skills/tanstack-table`) | TanStack Table v8.21.3 column generation, virtualization with react-virtual 3.13.12, pagination patterns |
| `zod-skill` (Zod v4 — 27 rules) | `anivar/zod-skill` | Catches the most common v3→v4 mistakes (e.g. `z.string().email()` vs `z.email()`); the README states *"AI agent skill for Zod v4 — 27 rules: schema design, parsing, error handling, type inference. Works with Claude Code, Cursor, Codex, Windsurf."* |
| `shadcn-claude-skill` | `capraidev/shadcn-claude-skill` | Components / theming (oklch + next-themes) / forms with React Hook Form + Zod / data tables / accessibility |
| `accessibility-review` / `a11y-meta-skills` | `claudskills.com/skills/accessibility-review/`; `zivtech.github.io/a11y-meta-skills` | WCAG 2.1/2.2 AA audit, axe-core + jsx-a11y + Playwright. Triggers: *"audit accessibility", "check a11y", "is this accessible?"* |

**Must-install plugins / slash commands:**

| Plugin | Source | Commands |
|---|---|---|
| **codex-plugin-cc** (Codex from Claude Code) | `openai/codex-plugin-cc` | `/codex:setup`, `/codex:review`, `/codex:adversarial-review`, `/codex:rescue`, `/codex:status`, `/codex:result`, `/codex:cancel` |
| **cc-plugin-codex** (Claude Code from Codex) | `sendbird/cc-plugin-codex` | `$cc:review`, `$cc:adversarial-review`, `$cc:rescue`, etc. — mirror of above for symmetric coverage |
| **adamsreview** (multi-lens review pipeline) | `adamjgmiller/adamsreview` | `/adamsreview:review`, `/adamsreview:codex-review`, `/adamsreview:fix`, `/adamsreview:walkthrough` — optional but powerful for the trickier surfaces |

#### 3g. Code review prompts that actually catch bugs

Reserve `/codex:adversarial-review` for the **5 high-risk surfaces**: Trade Lab state machine, Backtest math, Roster Audit cross-column scoring, ⌘K palette ranking, the openapi.json regen pipeline. For everything else, plain `/codex:review` is fine.

Author your own slash commands in `.claude/commands/`:
- `/review-a11y` → runs `axe-core` via Playwright MCP on the current dev-server URL and reports WCAG violations.
- `/review-perf` → uses Chrome DevTools MCP to record a trace, identify LCP element, run `performance_analyze_insight` on `LCPBreakdown`.
- `/regen-api` → runs `pnpm openapi && pnpm check && pnpm test` and reports any new type errors.
- `/spec <feature>` → reads `docs/specs/<feature>.md` and produces a numbered task list with acceptance criteria.

#### 3h. Lint/format/type gates

Strict mode TypeScript config:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "useDefineForClassFields": true,
    "moduleResolution": "bundler",
    "verbatimModuleSyntax": true
  }
}
```

Add `@total-typescript/ts-reset` as the first import in your entry point (overrides `JSON.parse` → `unknown`, `.json()` → `unknown`, `localStorage.getItem` → `string | null`). This single import catches a class of agent-written bugs (parsing JSON and immediately reading a field).

Biome config (`biome.json`) — let it run defaults and only override what you actually disagree with. Run `pnpm check` = `biome check --write . && tsc --noEmit` as your one command. Make this the *first* thing the AGENTS.md `Priority 1` definition-of-done points at.

#### 3i. Test strategy

- **Unit (Vitest)**: pure logic — Zod schemas, trade-value math, ranking, fuzzy-search ranking. Agents are GOOD at writing these from a clear spec. Use TDD pattern: write the test file first, ask Claude Code to implement.
- **Component (Vitest + Testing Library + MSW)**: shadcn-derived components and the cockpit primitives. MSW lets you replay realistic API responses from the Hey-API-generated schemas.
- **E2E (Playwright + Playwright MCP)**: 8–12 happy paths, one per final-state surface. Run on every PR. Agents can extend these from a spec file.
- **Visual regression**: Playwright snapshot mode for the cockpit primitives (KPI tile, dense grid row, command palette open state). Run weekly, not per-commit.

Agents are *better* at writing tests *after* a feature lands than TDD-style, *unless* you write the spec file first. With a spec file (`docs/specs/0007-trade-lab.md` containing acceptance criteria), TDD works fine.

#### 3j. Documentation conventions (ADR + spec-driven)

Two parallel folders:
- `docs/decisions/NNNN-title.md` — short ADR (Context, Decision, Consequences). Keep them under 200 words. One per non-obvious choice (e.g., `0001-tanstack-router-not-react-router.md`, `0002-hey-api-not-orval.md`, `0003-observable-plot-via-effect-not-wrapper.md`).
- `docs/specs/NNNN-feature.md` — followed by implementation tasks. Pattern adopted from the `alexop.dev` spec-driven Claude Code workflow (used to migrate a SQLite/WASM sync engine to IndexedDB in one afternoon vs. 2-3 days manual) and similar to `Pimzino/claude-code-spec-workflow` (Requirements → Design → Tasks → Implementation phases under `.claude/specs/`) — though pin a copy locally rather than depending on the upstream skill since that repo has shifted to an MCP version with limited Claude-Code-only updates. `github/spec-kit` is the alternative when specs need to live in PRs reviewed by humans.

### 4. UI/UX excellence references for the cockpit

**Open-source repos worth pattern-matching:**
- **Tremor's `tremorlabs/tremor` and `tremorlabs/tremor-blocks`** — now MIT post-Vercel acquisition. The "Tremor Raw" dashboard template (`dashboard.tremor.so`) is the closest open-source equivalent to what you're describing. Built on Tremor Raw + Recharts + Radix.
- **`shadcn-ui/ui` example dashboards** — the new-york style examples are intentionally minimal; less reference value than Tremor.
- **`cal.diy`** (formerly `cal.com`) — `ui.cal.com` Storybook is browsable. Useful for shadcn-style design system patterns and dialog/sheet conventions.
- **`vercel/next.js`'s admin dashboard starter** — minimal but architecturally clean.
- **Tabler**, **TailAdmin**, **Devias Kit** — denser dashboards but mostly MUI/HTML, less reference value for Tailwind/shadcn.
- **`linear.app`** — closed source, but study via the live product and SaaSUI's screenshot library (`saasui.design`).
- **Bloomberg Terminal aesthetic** — there are no open-source clones worth referencing. Build from first principles.

**v0.dev / Bolt.new for generation?** v0.dev now bakes in Tremor (per Vercel's acquisition announcement, Vercel said Tremor's library would *"enhance v0—our generative UI system—enabling the creation of more complex and data-rich interfaces from simple text prompts"*). It produces shadcn-compliant React + TS + Tailwind output that a Claude Code agent can iterate on without ceremony. Use v0 for first drafts of new surfaces (Command Center home, Settings); have Claude Code refactor into your cockpit/ design-system primitives. **Avoid Bolt.new** for this project — it's optimized for full-app scaffolding, not component-level iteration on an existing repo.

### 5. Solo-dev longevity hardening

1. **Pin Node via `mise`** — `.mise.toml`:
   ```toml
   [tools]
   node = "22.11.0"
   pnpm = "10.5"
   python = "3.12"
   ```
   And in `package.json`:
   ```json
   "engines": { "node": ">=22.11.0", "pnpm": ">=10" },
   "packageManager": "pnpm@10.5.0"
   ```
2. **Renovate (preferred) or Dependabot** — Renovate's `:dependencyDashboard` + `:rebaseStalePrs` is the gold standard for solo developers. Group all `@tanstack/*` updates into one PR. Schedule for Sundays.
3. **Lockfile hygiene** — Always `pnpm install --frozen-lockfile` in CI. Never commit a manual lockfile edit. Review lockfile diffs as carefully as code diffs (binary `bun.lock` is one reason to prefer pnpm's YAML lockfile).
4. **Pnpm "lifecycle scripts opt-in by default since v10"** — leave this default. When a new dependency wants postinstall, pnpm will surface the prompt; don't blindly allow.
5. **Strip-shadcn escape hatch** — Because shadcn is copy-paste source, you can always bypass Tailwind by inlining the CSS from each primitive. Document this in `docs/decisions/0010-tailwind-escape-hatch.md`: "If Tailwind v5 ships breaking changes and we can't migrate within a week, run `pnpm run tailwind:freeze` which compiles current `tailwindcss` to a single static `tokens.css`, then nuke `tailwindcss` from devDependencies." You can write this script in 50 lines.
6. **Vendor small dependencies that have been hot-takes** — `cmdk` (small, single-author, critical to UX), `class-variance-authority`, `clsx`, `tailwind-merge`. Either vendor the source under `vendor/` or pin exact versions and never bump without a manual diff.
7. **Six-month-gap survivability** — Every spec, every ADR, and every slash command needs to make sense to your future self with zero working memory. Re-read `AGENTS.md` and the top 5 specs every quarter; delete what's stale.
8. **Backups for the AI-collab artifacts** — `.claude/`, `.codex/`, `docs/specs/`, `docs/decisions/` are *all* committed to git. Personal scratch like `CLAUDE.local.md` is gitignored. Never put API keys in any of these.

---

## Recommendations (staged)

### Day 1 — Foundations
1. `pnpm create vite@latest cockpit -- --template react-ts`. Set strict TS.
2. `mise use node@22 pnpm@10`. Commit `.mise.toml` and `package.json` engines/packageManager.
3. `pnpm dlx shadcn@latest init` (new-york style, OKLCH, neutral base).
4. `pnpm add @tanstack/react-query @tanstack/react-router @tanstack/react-table @tanstack/react-virtual zod`
5. `pnpm add -D @hey-api/openapi-ts @hey-api/vite-plugin @biomejs/biome vitest @vitest/ui playwright @playwright/test @total-typescript/ts-reset`
6. Wire `pnpm openapi` to FastAPI's `openapi.json`. Generate first cut. Commit `src/api/`.
7. Create `AGENTS.md` (~150 lines) + `CLAUDE.md` (one line: `@AGENTS.md` + 30 lines of Claude-specific addenda) + `GEMINI.md`.
8. Install `codex-plugin-cc` and verify `/codex:setup` succeeds.

### Day 2 — Multi-agent rig
1. Install MCP servers: Context7, Playwright MCP, Chrome DevTools MCP, fastapi-mcp-openapi (mounted on backend).
2. Author 4 slash commands: `/regen-api`, `/review-a11y`, `/review-perf`, `/spec`.
3. Install community skills: `tailwind-v4-shadcn`, `tanstack-table`, `zod-skill` from `jezweb/claude-skills` and `anivar/zod-skill`. Pin to specific versions.
4. Write `docs/decisions/0001-0005` ADRs for the contested choices documented above.
5. First spec file: `docs/specs/0001-command-palette.md`. Acceptance criteria. Hand to Claude Code to implement.

### Week 1 — Cockpit primitives
1. Build `cockpit/Cell.tsx`, `cockpit/KPITile.tsx`, `cockpit/LaneBadge.tsx`, `cockpit/DensityProvider.tsx`.
2. Wire dark-cockpit OKLCH tokens, two-track model/market colors, tabular-nums typography.
3. Ship ⌘K palette (cmdk + TanStack Virtual + fuzzy filter on 600 players).
4. Set up Vitest + Testing Library + MSW. One unit test per Zod schema.

### Week 2-3 — First surface
1. Trade Lab as proof of the workflow: spec file → Claude implements → Codex reviews → revisions → Playwright E2E → merge.
2. After Trade Lab ships, audit your `AGENTS.md` against what actually slowed the agents down. Tighten.

### Benchmarks that should change the plan
- If a Codex `/codex:review` round catches >2 substantive bugs/week → enable `--enable-review-gate` Stop hook for the implicated surface.
- If `pnpm openapi` regen takes >5 seconds → Hey API has known a perf path (the 2026-04-28 release credits @SukkaW for fixes that produced *"a 10x-30x performance gain on larger specs, with meaningful improvements on smaller specs as well"*); ensure you're on latest.
- If Tailwind v5 ships before 2027 → execute the strip-shadcn escape hatch instead of rushing migration.
- If Anthropic changes Pro/Max policy on third-party orchestrators (the April 4, 2026 block) → re-evaluate `claude-squad` for orchestration.
- If you find yourself writing the same review prompt 3+ times → promote it to a slash command in `.claude/commands/`.

---

## Caveats

- **AGENTS.md governance is new.** Per OpenAI: *"Since its release in August 2025, AGENTS.md has been adopted by more than 60,000 open-source projects and agent frameworks…"* (openai.com/index/agentic-ai-foundation/). It was moved to the Linux Foundation / Agentic AI Foundation in December 2025. Spec stability is high (the spec deliberately specifies almost nothing structurally), but tool support is still in flux — Claude Code in particular doesn't natively read AGENTS.md as of May 2026.
- **The April 4, 2026 Anthropic policy change** (blocking Pro/Max subscriptions from third-party orchestrators) is recent and could be reversed or expanded. Treat orchestrator choice as a 6-month decision, not a forever decision.
- **Hey API is in "initial development"** per its own README — *"This package is in initial development. Please pin an exact version so you can safely upgrade when you're ready."* Pin to an exact version and re-evaluate on each upgrade. The maintenance velocity and Vercel/PayPal usage make this a safe bet despite the disclaimer, but it's worth knowing.
- **Pydantic v2.14 is in alpha** (May 2026) — stick to v2.13.x stable for now. v3 is at least 6 months out per Pydantic's version policy.
- **The "Codex peer review on the same branch" pattern is a community pattern, not an officially blessed workflow.** OpenAI's codex-plugin-cc README explicitly warns: *"The review gate can create a long-running Claude/Codex loop and may drain usage limits quickly. Only enable it when you plan to actively monitor the session."* Treat the workflow as a productivity tool, not a quality gate substitute for human review of risky code.
- **Tremor's open-source path post-Vercel acquisition is healthy as of May 2026**, but Vercel's strategic direction for it could shift. The escape hatch is simple: Tremor components are Recharts under the hood, and you can always swap to plain Recharts.
- **Observable Plot in React requires a `useEffect` wrapper** — there is no maintained React wrapper library that the Plot team endorses. This is the documented pattern but ages a tiny bit awkwardly with React 19's compiler. Test the wrapper in your codebase before committing to Plot for >2 charts.
- **Some 2026-dated articles cited in research above are content marketing sites of varying authority** (PkgPulse, Codersera, Better Stack, Techsy, blink.new). Primary sources — Anthropic docs, OpenAI repos, Linux Foundation press release, library GitHub repos — should be the ones you re-check before any meaningful decision. Where this report cites a benchmark or quote, it's from those primary sources or the LF/OpenAI announcements wherever possible.