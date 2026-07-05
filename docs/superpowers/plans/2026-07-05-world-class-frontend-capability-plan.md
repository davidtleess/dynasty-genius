# World-Class Frontend Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the skills, plugins, validation infrastructure, and design-system workflow needed for Dynasty Genius to reach a world-class frontend without weakening the product constitution, Stack-A wall, or No-Verdict line.

**Architecture:** Keep the shipped Vite/React/vanilla-CSS stack as the runtime foundation. Add external inspiration and inspection tools around the repo, then add repo-native visual validation, accessibility, and governed UI primitives before any broad surface redesign.

**Tech Stack:** Vite, React, TypeScript, Zod, Vitest, Biome, vanilla CSS tokens, @fontsource Archivo/IBM Plex, browser-use/Playwright candidate, axe-core candidate, Chrome DevTools MCP candidate, optional MCP tools gated by source and dependency-wall review.

---

## Context

This plan supersedes the I2a ship question. David previewed I2a and ruled it **not good enough**. I2a stays parked on `feature/horizon2-i2-daily-open`; do not merge the visual flip. The failure mode is now part of the evidence: correctness-first cockpit work produced reliable contracts, but the frontend loop still cannot see visual quality.

Current branch when drafted: `feature/horizon2-i2-daily-open`.

Current dirty files include parked Claude/Codex I2a work plus `.mcp.json`. Treat them as protected in-flight artifacts.

This plan is versioned as a working cockpit artifact. Claude's verified deep-research synthesis and the directly reviewed Dynasty Nerds screenshot benchmark are integrated through the reset spec and this plan; the package still needs final cockpit CLEAR before David ratifies execution.

## Source Synthesis

1. Standard Beagle, "When agents are the users" (2026): agentic UX shifts part of the interface into schemas, APIs, workflows, field names, and explainability. DG implication: visual polish is insufficient unless every number keeps machine-readable provenance and human-visible control.
2. Jonathan Fulton, "AI Has a UX Validation Problem" (2026): agents can write frontend code but still need screenshots, videos, and human validation for visual correctness. DG implication: David preview gates and browser evidence are not ceremony; they are the quality system.
3. Playwright official visual comparison docs: screenshot comparisons are built into Playwright, but rendering varies by OS/browser/fonts, so baselines need a controlled environment and review discipline.
4. Playwright accessibility docs: automated accessibility checks catch common issues but do not replace manual accessibility assessment. DG implication: add axe-style gates plus keyboard/focus evidence.
5. Storybook docs: stories can become component tests with browser rendering and Vitest integration. DG implication: useful after DG has a small internal primitive library, not before.
6. Vercel AI SDK generative UI docs: GenUI connects tool-call results to React components. DG implication: defer runtime GenUI; DG cannot let an LLM dynamically choose decision-shaped components inside live league surfaces.
7. 21st.dev Magic MCP docs: Magic can generate and improve modern UI components through natural-language prompts. DG implication: install and use it as an inspiration/prototyping tool, then port only reviewed vanilla-CSS/React patterns behind DG tests.
8. shadcn MCP docs: shadcn MCP can browse/search/install registry components. DG implication: do not add it now; it conflicts with the current dependency wall unless David explicitly opens a dependency-wall amendment.
9. Thesys AI frontend infrastructure and HeroUI pages: the visible takeaway is that AI-native UI tooling is moving quickly toward generative/interactive component systems. DG implication: watch the space, but keep runtime UI deterministic and locally governed.
10. W3C WCAG 2.2: accessibility requirements are organized as principles, guidelines, and testable success criteria, but WCAG itself says accessibility still needs a combination of automated testing and human evaluation. DG implication: focus visibility, keyboard reachability, contrast, reflow, name/role/value, and reduced-motion behavior become frontend acceptance criteria.
11. IBM Carbon motion guidance: motion should guide complex experiences, be productive by default, reserve expressive motion for occasional important moments, avoid decorative bounce/stretch, and provide reduced-motion alternatives. DG implication: the product needs motion tokens and choreography rules, not isolated CSS animations.
12. Gemini/Gemini2 animated statistical-graphics research: statistical chart motion works when it preserves semantic correspondence and decomposes complex changes into staged operations. DG implication: chart motion cannot morph unrelated metrics or draw beyond the Hard Right Edge; once PIT series exist, updates should stage substrate/axis changes before marks and labels.
13. Claude deep-research synthesis: Linear's craft model validates screenshot iteration over the shipped app as the design artifact; Chrome DevTools MCP is the current agent-eyes iteration tool; Carbon motion tokens can be implemented as plain CSS; Lost Pixel is archived and must not be adopted; dense tables need 4px-grid padding, right-aligned numerals, sticky/sortable affordances, and human-readable dates.
14. Dynasty Nerds visual benchmark: David supplied 14 screenshots and named Dynasty Nerds as the gold standard. Direct review confirms the parity floor: identity-heavy rows, value-as-hero numbers, compact per-row uncertainty bars with sigma labels, in-grid sparklines, tier/value band dividers, selectable rows and player-link affordances, group totals with league rank, a two-pane league analyzer, first-class valued picks, tabbed player profiles, graded bars, and embedded football prose. DG translates DN through neutral deltas, disclosed value bands, two-lane model/market truth, receipts, and the Hard Right Edge.

Research URLs:

- `https://standardbeagle.com/agentic-ux-designing-interfaces-for-agents/`
- `https://medium.com/jonathans-musings/ai-has-a-ux-validation-problem-cf8d93ea4e92`
- `https://playwright.dev/docs/test-snapshots`
- `https://playwright.dev/docs/accessibility-testing`
- `https://storybook.js.org/docs/writing-tests/component-testing`
- `https://www.w3.org/TR/WCAG22/`
- `https://carbondesignsystem.com/elements/motion/overview/`
- `https://arxiv.org/abs/2009.01429`
- `https://arxiv.org/abs/2108.04385`
- `docs/strategies/2026-07-05-deep-research-agent-frontend-synthesis.md`
- `https://github.com/21st-dev/magic-mcp`
- `https://github.com/21st-dev/codex-plugin`
- `https://ui.shadcn.com/docs/mcp`
- `https://sdk.vercel.ai/docs/ai-sdk-rsc/generative-ui-state`
- `https://www.thesys.dev/blogs/why-ai-frontend-infrastructure-is-the-most-overlooked-layer-in-your-llm-stack`
- `https://www.thesys.dev/blogs/heroui`

## Current Visual-Audit Evidence

Claude's post-preview audit gives the failure register this plan must answer:

- The dark theme was declared, not designed. Component CSS still hardcodes light-era colors, producing unreadable surfaces and white patches on a dark canvas.
- Exactly one component rule meaningfully consumed the new semantic aliases. The token layer exists, but it did not govern rendered components.
- The command palette has a transparent overlay defect that predates dark mode. The DOM-test loop never saw it.
- Fifteen surfaces were styled independently as they shipped. There is no shared visual grammar for density, elevation, interaction, focus, or motion.
- The system defines three font sizes but rendered CSS uses many more; spacing, opacity, and radii are similarly ad hoc.
- The focus token is effectively unused. A visual system that cannot show keyboard position cannot claim premium craft or accessibility.
- There are no designed hover states, transitions, elevation model, or responsive visual acceptance gates. The only crafted motion moment was the parked I2a 150ms settle.

Codex's local CSS audit (`docs/strategies/2026-07-05-frontend-css-design-debt-audit.md`) confirms the same class of failure from repo evidence: raw color literals or raw OKLCH values appear across 11 component CSS files, semantic token consumption is thin and uneven, `--dg-focus` is defined but not consumed by component CSS, and font-size/radius choices remain surface-local.

This is not a polish backlog. It is a stop-the-line process defect: no H2 visual increment should ship until the cockpit can inspect pixels and the repo has a small governed primitive system.

## Why The Current Frontend Feels Weak

The current app has strong honesty but weak craft density. It is structurally correct, yet many surfaces still read like independent proof-of-concept panels rather than one premium terminal.

Weaknesses to correct:

- Visual validation is mostly DOM/unit-test driven. There is no standard screenshot bundle, mobile viewport evidence, overlap scan, or accessibility report attached to visual changes.
- The preview failure proved the token system is not yet a design system. Dark theme activation landed over component CSS still carrying hardcoded light-era colors, so locally correct token work produced globally incoherent pixels.
- CSS is surface-local and uneven. Tokens exist, but many files still carry raw spacing, raw grayscale values, one-off row treatments, and local typography choices.
- There is no small internal primitive system. Components such as receipt triggers, caveat blocks, metric rows, tape facts, chart frames, empty states, and two-lane cells are still recreated by surface.
- The quality loop relies on humans catching visual regressions late. Agents can pass tests while missing hierarchy, rhythm, mobile fit, and perceived polish.
- External tooling is not yet integrated into the cockpit workflow. Magic is installed locally but unauthenticated; Figma/Storybook are not part of the repo workflow; `.mcp.json` ownership is unresolved.
- Generative UI advice from the market conflicts with DG's constraints unless sharply bounded. Streaming arbitrary components, Tailwind registries, and runtime LLM UI selection would weaken provenance and No-Verdict guarantees.

## Principles

1. **Credibility is the aesthetic.** The jaw-drop should come from density, receipts, history boundaries, and visible refusal to extrapolate.
2. **Every pixel has a contract.** A visual primitive must have a data contract, caveat behavior, accessibility behavior, and test evidence.
3. **External tools suggest; DG governs.** Magic, Figma, Storybook, shadcn, HeroUI, and GenUI can inform patterns, but committed code must satisfy DG's stack wall and cockpit tests.
4. **Browser evidence is mandatory for visual work.** Vitest and TypeScript are necessary, not sufficient.
5. **No runtime AI-generated UI in H2.** Agents can help build static React components; live surfaces render from generated clients, Zod validation, and deterministic DG components.
6. **Motion is evidence-aware.** Motion can reveal hierarchy or receipt state; it must never imply urgency, confidence, or player action.
7. **Data motion preserves identity.** Chart motion may guide attention only when the same semantic object persists. Schema changes, missing data, and unrelated metrics use staged remove/add or static replacement, not morphing.
8. **The screen speaks dynasty manager.** Backend precision remains mandatory, but primary UI copy is football/fantasy/dynasty prose. Raw route names, schema terms, caveat codes, system nouns, and metric symbols live in receipts/diagnostics, not the main reading surface.
9. **Strength and equity are different products.** Lineup strength answers "who can beat me now?" Franchise equity answers "who owns the best dynasty balance sheet?" Valued owned draft picks may share the same value yardstick as players, but they must not be silently folded into current-strength rankings.
10. **The shipped app is the design artifact.** Static mockups can inform direction, but craft is earned by screenshotting, inspecting, and iterating on the actual running app over a small governed token vocabulary.
11. **The benchmark is concrete.** David's Dynasty Nerds screenshots are the visual parity floor. DG must match the density, hierarchy, identity, group totals, first-class pick treatment, profile grammar, and hero moments while exceeding DN with two-lane model/market truth, receipts, real uncertainty, and the Hard Right Edge.

## Principles First, Practical Next, Spectacular Last

**Principles first:** Dynasty Genius should feel like an audited league terminal, not a generic dashboard. The core visual promise is: every number has provenance, every caveat is visible, every time-series stops at the Hard Right Edge, and every interaction is calm enough to read under pressure.

**Practical next:** before another redesign attempt, build the harness that can see. The minimum practical stack is Chrome DevTools MCP for live inspection, Playwright screenshots, mobile/desktop viewport checks, axe scans, keyboard/focus assertions, CSS raw-value audits, and a primitive library that forces surfaces to share the same receipt/caveat/metric/tape/chart contracts.

**Practical copy:** before another David-facing rewrite, build the voice layer that translates strict backend facts into manager language. Same integrity, different surface: "Day 11 of daily league tracking" instead of "Registry version: 4"; "model verified current" instead of "Model vintage: ok."

**Spectacular last:** only after the primitive layer, visual evidence gate, and voice layer exist should DG spend boldness on motion, chart choreography, deep-dark palette tuning, daily-open sequencing, and signature chart primitives. Spectacular here means unmistakably credible, not louder.

**Benchmark floor:** spectacular is not abstract. David's Dynasty Nerds screenshots define the minimum professional density and hierarchy: player identity everywhere, value numbers as focal objects, row-level uncertainty, team/group rank context, first-class valued picks, tabbed profile pages, graded bars with basis, and prose beside the numbers. DG's job is to translate that grammar into its stricter constitution, not to ignore it.

## Tooling Decisions

### Adopt Now

- **Playwright agent-eyes harness**
  - Use: browser screenshots, viewport matrix, keyboard interaction checks, trace/video capture when a flow matters, and screenshot bundles for David/cockpit review.
  - Rule: start with evidence artifacts and deterministic browser checks before committing golden visual regression baselines.
  - CI implication: exact-pinned Playwright is still a dependency-wall amendment, but CI browser automation comes after local evidence proves stable. Do not make merges depend on a new browser-infra gate on day one.

- **Chrome DevTools MCP**
  - Use: interactive agent-eyes iteration over the live app: screenshot/DOM/CSS inspection, console and network diagnosis, device emulation, and performance trace investigation.
  - Rule: DevTools MCP is the iteration/debugging loop; it does not replace the Playwright + axe evidence bundle required for visual CLEAR.
  - Cost: Chrome-only, nontrivial tool-token overhead, and local-preview maturity risk. It is local MCP/tooling infrastructure, not runtime code and not a dependency-wall change by itself.

- **axe accessibility checks over Playwright**
  - Use: automated a11y smoke for shell, Daily What-Changed, receipt popovers, command palette, and future player inspector.
  - Rule: axe is necessary but not sufficient; keyboard/focus assertions and human visual preview remain required.

- **21st.dev Magic MCP / Codex plugin**
  - Status: installed as `21st@21st-local`; `.mcp.json` present; `API_KEY_21ST` still required; Codex restart required for tools.
  - Use: inspiration and first-pass component sketches only.
  - Rule: no direct generated component lands without DG token conversion, Stack-A audit, banned-language scan, accessibility review, and screenshot evidence.

- **Codex browser-use / local browser verification**
  - Status: available as a Codex skill.
  - Use: every visual increment gets desktop and mobile screenshots, interaction smoke, and overlap inspection before CLEAR.

- **Dynasty Nerds screenshot benchmark**
  - Status: David-supplied visual quality bar, documented in `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md` and independently reviewed by Codex from the 14 source screenshots.
  - Use: every restarted Daily Open and I4 surface preview includes screenshot-vs-screenshot comparison against the corresponding DN pattern.
  - Rule: parity is structural, not constitutional mimicry. DN green/red, subjective tiers, and single consensus values translate to DG neutral deltas, disclosed value bands, two-lane model/market views, receipts, and no-verdict language.

### Adopt Later

- **Storybook + Storybook MCP**
  - Adopt after `frontend/src/ui/` has 8-12 stable DG primitives, or immediately after cockpit decides the primitive extraction is the first rebuild step.
  - Use for isolated primitive states, receipt/caveat variants, empty/degraded/loading variants, and keyboard stories.
  - Do not start by installing Storybook into the current surface-first codebase; that would catalog inconsistency instead of fixing it.

- **Figma MCP**
  - Install only if David wants a Figma design source of truth or imported design snapshots.
  - Use official Figma MCP or a vetted connector only. Avoid third-party MCP packages with shell-exec risk unless security reviewed.
  - Figma is not required for I2a/I2b; it becomes valuable when a visual design file exists.

- **Internal DG frontend skill/plugin**
  - Build after the first two H2 visual increments settle. It should encode DG-specific rules: Hard Right Edge, receipts, no verdict hues, 32px rows, caveat placement, no nested cards, mobile fit, browser evidence.

### Defer Or Reject For Now

- **Tailwind CSS and Tailwind IntelliSense:** reject for H2 unless David explicitly amends the Stack-A wall. DG already has token guards and vanilla CSS discipline.
- **shadcn/ui MCP:** defer. Useful registry, but direct installs would add dependency and style-system drift.
- **HeroUI / NextUI:** reject as runtime dependency for H2. It is too general-purpose and would fight DG's terminal identity.
- **Vercel AI SDK / LCEL runtime GenUI:** defer beyond H2. Runtime generated components are incompatible with live No-Verdict/provenance controls unless redesigned around a closed DG component catalog.
- **Lost Pixel:** reject. The verified synthesis says the repo is archived read-only as of 2026-04-22; do not adopt it for visual regression.
- **Framer Motion / Motion runtime:** defer. Plain CSS tokens cover H2 motion scope; the vendor-acknowledged bundle floor is not justified. LazyMotion is only a future fallback if a later spec proves imperative orchestration is necessary.
- **Zustand / React Query / TanStack Router:** reject for H2 unless a concrete state problem exceeds existing `useEndpointResource` and `useUrlSurfaceState`.
- **SSE/thought streaming:** reject for current live surfaces. Consider later only for background jobs or a redesigned Research Assistant, and never stream chain-of-thought.
- **Bidirectional canvas manipulation:** reject for DG core surfaces. It optimizes for editing documents, not reading audited league intelligence.

## Proposed Program

### Task 0: Stop-The-Line Visual Reset

**Files:**
- Modify: `docs/superpowers/specs/2026-07-05-h2-i2a-visual-flip-design.md`
- Create: `docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md`
- Modify: `docs/agent-ledger/2026-07-05.md`

- [ ] **Step 1: Mark I2a parked**

Record the preview outcome:

```markdown
## Preview Outcome

David previewed I2a on 2026-07-05 and ruled it not good enough. The branch remains parked and must not merge as the H2 visual flip. The defect class is structural: dark tokens activated without component CSS migration and without browser-evidence gates.
```

- [ ] **Step 2: Freeze visual ship criteria**

No visual increment can route for GREEN CLEAR without:

```text
1. desktop screenshot
2. mobile screenshot
3. keyboard/focus smoke
4. axe or documented manual a11y check
5. CSS/token audit delta
6. David preview evidence for broad visual flips
```

- [ ] **Step 3: Restart the visual flip and treat I2a as a parts donor**

Decision:

```text
Restart the visual flip from the reset spec. Treat parked I2a as a parts donor, not as a ship candidate and not as trash. Cleared non-visual work can re-enter piece by piece through the new evidence gates: tape data plumbing, no-fake-series boundaries, font-pipeline work, and copy contracts.
```

### Task 1: Tooling Registry And Local MCP Hygiene

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-h2-frontend-capability-design.md`
- Modify: `docs/agent-ledger/2026-07-05.md`
- Potentially decide later: `.mcp.json`

- [ ] **Step 1: Write the capability spec**

Document the exact tool statuses:

```markdown
## Tool Status

- 21st.dev Magic: installed locally; requires API_KEY_21ST and Codex restart; inspiration-only.
- Chrome DevTools MCP: conditional local agent-eyes iteration tool; no runtime code; Playwright+axe remains evidence gate.
- Figma MCP: conditional; no install until design-file ownership exists.
- Storybook MCP: conditional; no install until DG primitives exist.
- shadcn MCP: deferred; dependency-wall conflict.
- Tailwind IntelliSense: rejected for repo work; vanilla CSS remains binding.
```

- [ ] **Step 2: Route the spec through cockpit**

Send to Claude and Gemini:

```text
PLEASE REPLY with: (a) concrete defects/gaps in the tool adoption matrix, OR (b) no finding after checking Stack-A, No-Verdict, and H2 vision constraints.
```

- [ ] **Step 3: Resolve `.mcp.json` ownership**

Decision options to put in front of David:

```text
Option A: keep `.mcp.json` local-only and gitignore it.
Option B: commit a project `.mcp.json` that references only env-var based credentials and contains no secrets.
Recommendation: B only if the team wants shared MCP bootstrap; otherwise A.
```

Expected verification:

```bash
git status --short --branch
test -n "$API_KEY_21ST"
codex plugin list
```

Expected evidence: `21st@21st-local` installed/enabled; API key presence reported without printing the key.

### Task 2: Browser Evidence Gate

**Files:**
- Create: `frontend/e2e/visual-smoke.spec.ts`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/package.json`
- Modify: `tests/contract/test_frontend_scaffold_contract.py`
- Later, after flake observation: `.github/workflows/ci.yml`

- [ ] **Step 1: RED for dependency-wall amendment**

Add exact-pinned dev dependencies only after cockpit clears them:

```python
EXPECTED_DEV_DEPENDENCIES = {
    # existing entries retained
    "@playwright/test": "1.61.1",
    "@axe-core/playwright": "4.12.1",
}
```

Expected failure before package edit: scaffold contract rejects missing exact pins.

- [ ] **Step 1b: Record Chrome DevTools MCP role split**

Add the local iteration tool without confusing it with the ship gate:

```text
Chrome DevTools MCP = live inspection and debugging loop.
Playwright + axe = repeatable evidence gate.
```

Expected checks:

```text
DevTools MCP use never replaces desktop/mobile screenshot artifacts.
DevTools MCP findings are cited as inspection notes, not visual CLEAR evidence.
No runtime dependency, generated client, or package-wall change is implied by MCP installation.
```

- [ ] **Step 2: RED for screenshot evidence artifacts**

Create a Playwright test that loads the built app, stubs API responses, and writes review artifacts. Do **not** start with golden baselines.

```ts
await page.setViewportSize({ width: 1440, height: 960 });
await page.screenshot({ path: "artifacts/visual/daily-open-desktop.png", fullPage: true });
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: "artifacts/visual/daily-open-mobile.png", fullPage: true });
```

Expected failure before GREEN: Playwright config/scripts absent. Expected GREEN: screenshot files exist and are attached to cockpit review.

- [ ] **Step 3: RED for accessibility smoke**

Use axe on the shell and Daily What-Changed:

```ts
const results = await new AxeBuilder({ page }).include("main").analyze();
expect(results.violations).toEqual([]);
```

Expected failure before dependency install/config: missing module or no runner.

- [ ] **Step 4: GREEN with deterministic fixture server**

Use Playwright `webServer` to serve the Vite preview or FastAPI frontend path with route mocks. Tests must not require gitignored artifacts.

Expected commands:

```bash
cd frontend && npm run build
cd frontend && npm run visual:smoke
```

Expected result: screenshots produced as artifacts, no axe violations for tested regions. No visual GREEN may be routed without these artifacts unless the change is proven non-visual.

- [ ] **Step 5: Observe flake before CI hard gate**

Run the local visual smoke at least three times across two sessions before adding a CI browser gate:

```bash
cd frontend && npm run visual:smoke
cd frontend && npm run visual:smoke
cd frontend && npm run visual:smoke
```

Expected result: stable artifact generation and no false failures. Only then write a separate CI amendment for browser automation.

- [ ] **Step 6: Golden-baseline decision gate**

Committed visual regression baselines require a separate cockpit decision:

```text
Evidence bundles are mandatory now. Golden snapshots become mandatory only after the browser environment, fonts, viewport, and artifact paths are stable enough to avoid review noise.
```

### Task 3: DG Primitive Library

**Files:**
- Create: `frontend/src/ui/ReceiptTrigger.tsx`
- Create: `frontend/src/ui/ReceiptTrigger.test.tsx`
- Create: `frontend/src/ui/CaveatBlock.tsx`
- Create: `frontend/src/ui/CaveatBlock.test.tsx`
- Create: `frontend/src/ui/MetricCell.tsx`
- Create: `frontend/src/ui/MetricCell.test.tsx`
- Create: `frontend/src/ui/ValueHero.tsx`
- Create: `frontend/src/ui/ValueHero.test.tsx`
- Create: `frontend/src/ui/PlayerIdentity.tsx`
- Create: `frontend/src/ui/PlayerIdentity.test.tsx`
- Create: `frontend/src/ui/SpreadBar.tsx`
- Create: `frontend/src/ui/SpreadBar.test.tsx`
- Create: `frontend/src/ui/ValueBandDivider.tsx`
- Create: `frontend/src/ui/ValueBandDivider.test.tsx`
- Create: `frontend/src/ui/DenseTable.tsx`
- Create: `frontend/src/ui/DenseTable.test.tsx`
- Create: `frontend/src/ui/DailyTape.tsx`
- Create: `frontend/src/ui/DailyTape.test.tsx`
- Create: `frontend/src/ui/SeriesSlot.tsx`
- Create: `frontend/src/ui/SeriesSlot.test.tsx`
- Create: `frontend/src/ui/ui.css`

- [ ] **Step 1: RED for receipt accessibility**

Pin the H2 receipt contract:

```tsx
render(<ReceiptTrigger label="Projection Update" capturedAt="2026-07-05T10:15:00-04:00" source="model_registry" />);
const trigger = screen.getByRole("button", { name: /provenance for projection update/i });
expect(trigger).toHaveAttribute("aria-expanded", "false");
await user.click(trigger);
expect(trigger).toHaveAttribute("aria-expanded", "true");
expect(screen.getByTestId("receipt-raw-source")).toHaveTextContent("model_registry");
await user.keyboard("{Escape}");
expect(trigger).toHaveAttribute("aria-expanded", "false");
```

- [ ] **Step 2: RED for caveat and metric primitives**

Pin standard caveat placement and mono/tabular values:

```tsx
render(<MetricCell label="xVAR" value="+12.4" receipt={{ source: "engine_b", capturedAt: "2026-07-05T10:15:00-04:00" }} />);
expect(screen.getByText("+12.4")).toHaveClass("dg-ui-metric__value");
expect(screen.getByRole("button", { name: /provenance for xvar/i })).toBeInTheDocument();
```

- [ ] **Step 3: GREEN primitive CSS**

Use semantic tokens only:

```css
.dg-ui-metric__value {
  font-family: var(--dg-font-mono);
  font-variant-numeric: tabular-nums;
}
```

Expected verification:

```bash
cd frontend && npm test -- --run src/ui
cd frontend && npm run typecheck
cd frontend && npm run lint
```

- [ ] **Step 4: RED for dense-table conventions**

Pin the comparison-table craft rules:

```tsx
render(<DenseTable rows={rows} />);
expect(screen.getByText("12 Jun 2025")).toBeInTheDocument();
expect(screen.queryByText(/2025-06-12T/)).not.toBeInTheDocument();
expect(screen.getByText("+12.4")).toHaveClass("dg-ui-table__numeric");
expect(screen.getByRole("columnheader", { name: /franchise equity/i })).toHaveAttribute("aria-sort");
```

CSS contract:

```text
Visible dates are human-readable, never raw ISO.
Comparable numerals are right-aligned and tabular.
Text labels are left-aligned.
Dense rows use 4px-grid padding steps such as 4/8/12px.
Sticky headers and sortable affordances are allowed only when the table has enough scroll/compare density and the sort basis is declared.
```

- [ ] **Step 5: RED for Dynasty Nerds parity primitives**

Add the benchmark-driven primitives to the same library, behind DG's constitutional translations:

```tsx
render(<PlayerIdentity name="Bijan Robinson" team="ATL" position="RB" imageStatus="available" />);
expect(screen.getByText("Bijan Robinson")).toBeInTheDocument();
expect(screen.getByText("ATL")).toHaveAttribute("data-team-color-basis", "ATL");

render(<ValueHero label="Player value" value="10,256" basis="model value 90-100" />);
expect(screen.getByText("10,256")).toHaveClass("dg-ui-value-hero__number");

render(<SpreadBar label="Value range" value={8.4} basis="fold CI" />);
expect(screen.getByRole("img", { name: /value range.*fold ci/i })).toBeInTheDocument();
```

Expected contract:

```text
PlayerIdentity supports missing-image fallback and no external image fetch until the asset-pipeline decision is ratified.
ValueHero makes the number the visual focal point without green/red verdict semantics.
SpreadBar displays uncertainty/range only with basis copy, numeric label, and accessible summary.
ValueBandDivider labels a disclosed numeric band, not subjective fantasy tiers.
Dense ranking rows support selectable-row affordances and player-link affordances when the surface offers row-level actions or profile navigation.
Tabbed profile pages use a persistent player header and section navigation before long-form score/prose/film content.
GradedBar renders only with a disclosed basis and neutral/brand-safe palette; it cannot encode verdict colors.
```

### Task 4: CSS Token Debt Audit

**Files:**
- Create: `frontend/src/styles/rawCssAudit.test.js`
- Create: `frontend/src/styles/visualCraftAudit.test.js`
- Modify: surface CSS files only after RED identifies sanctioned migrations.

- [ ] **Step 1: RED for raw color and spacing census**

Write a report-style test that inventories raw hex values, raw rem spacing, and duplicate row patterns. The first version should report, not fail, except for new files under `frontend/src/ui/`.

```js
expect(newUiCss).not.toMatch(/#[0-9a-f]{3,8}\b/i);
expect(newUiCss).not.toMatch(/font-family:\s*(?!var\()/i);
```

- [ ] **Step 2: Migrate only touched visual surfaces**

For each H2 visual increment, migrate the touched surface toward:

```css
color: var(--dg-text);
border-color: var(--dg-border);
font-family: var(--dg-font-sans);
```

Expected verification: raw-value count decreases or stays justified; no hue-guard regression.

- [ ] **Step 3: RED for visual craft primitives**

Assert that key interactive surfaces consume focus, hover, and elevation tokens:

```js
expect(cssBundle).toMatch(/:focus-visible/);
expect(cssBundle).toMatch(/var\(--dg-focus\)/);
expect(cssBundle).toMatch(/--dg-shadow|box-shadow/);
```

Expected initial result: fail or report-only fail until tokens and primitives exist. This is a known debt register, not an excuse to ship more visual work.

### Task 4b: Motion System

**Files:**
- Create: `frontend/src/styles/motion.css`
- Create: `frontend/src/styles/motion.test.js`
- Modify: `frontend/src/styles/tokens.css`

- [ ] **Step 1: RED for motion tokens**

Pin Carbon-derived plain-CSS durations/easing without importing a motion library:

```js
expect(motionCss).toContain("--dg-duration-fast-01: 70ms");
expect(motionCss).toContain("--dg-duration-fast-02: 110ms");
expect(motionCss).toContain("--dg-duration-moderate-01: 150ms");
expect(motionCss).toContain("--dg-duration-moderate-02: 240ms");
expect(motionCss).toContain("--dg-duration-slow-01: 400ms");
expect(motionCss).toContain("--dg-duration-slow-02: 700ms");
expect(motionCss).toContain("--dg-duration-chart-stage: 1000ms");
expect(motionCss).toContain("--dg-ease-productive-standard: cubic-bezier(0.2, 0, 0.38, 0.9)");
expect(motionCss).toContain("--dg-ease-productive-entrance: cubic-bezier(0, 0, 0.38, 0.9)");
expect(motionCss).toContain("--dg-ease-productive-exit: cubic-bezier(0.2, 0, 1, 0.9)");
```

- [ ] **Step 2: RED for reduced motion**

Every animation class must have a reduced-motion override:

```js
expect(motionCss).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
expect(motionCss).toMatch(/animation:\s*none|transition:\s*none/);
```

- [ ] **Step 3: GREEN without decorative motion**

Allowed motion categories:

```text
productive: hover/focus feedback, receipt reveal, drawer open/close, row sort/filter settle
chart: staged chart transitions around 1000ms only when intermediate frames remain valid data graphics
expressive: daily-open entrance only, David-previewed
forbidden: pulsing deltas, urgency shimmer, bounce/stretch, motion implying recommendation
```

The chart rule is the Heer/Robertson Congruence rule: if start and end states share no data dimension, use static replacement or staged remove/add instead of morphing.

Expected verification:

```bash
cd frontend && npm test -- --run src/styles/motion.test.js
cd frontend && npm run banned-language
```

### Task 4c: DG Voice System

**Files:**
- Created: `docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md`
- Modify: `frontend/src/lib/copy.ts`
- Create: `frontend/src/lib/copyVisibleText.test.ts`
- Create: `frontend/src/test/renderedCopyScan.ts`

- [ ] **Step 1: Review and ratify the voice guide**

Working artifact:

```text
docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md
```

Expected cockpit state: Gemini authored the product vocabulary draft; Codex integrated it as v0.2 with No-Verdict-safe wording; Claude/Codex review; David ratifies before implementation.

- [ ] **Step 2: RED for visible backend-language leaks**

Add a rendered-copy scanner that inspects visible text only:

```ts
const forbiddenVisiblePatterns = [
  /\b[a-z]+_[a-z0-9_]+\b/,
  /\bdecision_supported\b/i,
  /\bregistry\b/i,
  /\bartifact\b/i,
  /\bschema\b/i,
  /\bvintage\b/i,
  /\bcapture store\b/i,
  /\bstructural_context\b/i,
  /\bsettlement\b/i,
];

expect(
  scanVisibleText(container, {
    exemptSelectors: ["[title]", "[data-receipt]", "[data-diagnostic]"],
  }),
).toEqual([]);
```

Expected failure before GREEN: existing surfaces or fixtures expose at least one backend term in primary visible text, or the scanner helper does not exist.

- [ ] **Step 3: RED for Daily Tape manager prose**

Pin the concrete translation shape:

```ts
expect(screen.getByText(/market sync active/i)).toBeInTheDocument();
expect(screen.getByText(/projection update/i)).toBeInTheDocument();
expect(screen.getByText(/status: synced/i)).toBeInTheDocument();
expect(screen.queryByText(/registry version|model vintage|artifact|schema/i)).not.toBeInTheDocument();
```

Expected failure before GREEN: I2a-derived tape copy still reads like substrate diagnostics.

- [ ] **Step 4: Grow `frontend/src/lib/copy.ts` into the voice module**

Add functions after David ratifies the guide:

```ts
export function describeSystemFact(token: string): string {
  // Locked map from the ratified voice guide.
}

export function describeMetricName(metric: string): string {
  // xVAR/DVS etc. translated for primary prose unless David ratifies taught product vocabulary.
  // Exact symbols remain exposed by receipt/title.
}
```

Expected GREEN: every David-facing surface imports from this module for caveats/status/metric labels instead of hand-rolling backend terms.

Verification:

```bash
cd frontend && npm test -- --run src/lib/copyVisibleText.test.ts
```

Expected: visible-copy tripwire passes; receipt/title/diagnostic exemptions preserve auditability.

### Task 4d: Franchise Equity View

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-h2-franchise-equity-design.md`
- Later implementation files depend on the ratified spec; likely `frontend/src/league-pulse/*`, a shared `MetricCell`/`ReceiptTrigger`, and a backend/API slice if the current League Pulse contract does not expose the needed net-pick totals cleanly.

- [ ] **Step 1: Write the product contract**

Define this as a named candidate surface, not an existing shipped feature:

```text
Franchise Equity = roster player value + owned valued future-pick value, displayed beside but never merged with current lineup strength.
```

The spec must preserve the repo-state distinction in `src/dynasty_genius/team_value_matrix.py`: future picks carry valuation fields, but remain intentionally excluded from `starter_weighted_xvar` and other team-strength aggregates. The `owned` bucket is the current pick bank; the `outgoing` bucket is disclosure for picks originally owned by the roster but now held elsewhere, not a subtrahend.

- [ ] **Step 2: RED for the separation of views**

Pin three manager-facing lanes:

```text
Lineup Strength: players only, current playable roster.
Roster Player Value: players only, full roster asset base.
Future Pick Bank: owned valued picks, with outgoing picks disclosed separately and pick-curve caveats shown.
Franchise Equity: roster player value + owned valued future-pick value.
```

Expected failure before GREEN: current UI exposes raw team-value fields and pick status, but does not render the franchise-equity lens as a clean manager-facing view.

- [ ] **Step 3: RED for pick-value caveats and receipts**

Pick values must disclose whether they are exact-slot, round-tier, historical expected, thin-sample, or otherwise caveated. Generic future picks must not read like certain player-equivalent value. Picks with null value, such as round-4+ or unresolved-slot picks outside the current pick curve, must be counted as unvalued and excluded from the equity total.

```ts
expect(screen.getByText(/future pick bank/i)).toBeInTheDocument();
expect(screen.getByText(/franchise equity/i)).toBeInTheDocument();
expect(screen.getByText(/lineup strength/i)).toBeInTheDocument();
expect(screen.getByText(/picks are separate from current lineup strength/i)).toBeInTheDocument();
expect(screen.getByText(/unvalued picks excluded/i)).toBeInTheDocument();
```

Expected GREEN: David can compare every team by lineup strength and by franchise equity without mistaking picks for current starters or treating unvalued picks as zero-value proof.

- [ ] **Step 4: Keep manager prose primary**

Primary labels should read:

```text
Lineup Strength
Roster Player Value
Future Pick Bank
Outgoing Picks
Franchise Equity
```

Technical symbols such as `xVAR`, raw field names such as `starter_weighted_xvar`, and pick-curve caveats remain in receipts/title/diagnostic layers unless David ratifies taught product vocabulary.

- [ ] **Step 5: Add the Franchise Equity trend contract**

David's requested trend view compares Franchise Equity over time versus other teams. This requires historical comparable team-matrix snapshots, not `_latest` alone. Existing dated `team_value_matrix_phase17-3-*` artifacts are a seed substrate; committed tests must use temp fixtures and a dependency-injected reader.

Trend rules:

```text
Franchise Equity Trend = per-team roster player value + owned valued future-pick value at each comparable capture date.
```

Acceptance:

- no trend line renders with fewer than two comparable captures for a team;
- gaps render as gaps, not interpolation;
- every point carries capture date, source artifact id, owned valued pick total, unvalued-pick excluded count, and outgoing-picks disclosure count;
- the Hard Right Edge stops at the latest verified team-matrix capture;
- trend labels compare teams by equity basis, never as action-order or trade-target ranking.

Expected RED:

```ts
expect(screen.getByText(/franchise equity trend/i)).toBeInTheDocument();
expect(screen.getByText(/compared with league/i)).toBeInTheDocument();
expect(screen.getByText(/unvalued picks excluded/i)).toBeInTheDocument();
expect(screen.queryByTestId("franchise-equity-trend-path")).toBeNull(); // until >=2 comparable captures
```

- [ ] **Step 6: Pin the DN analyzer layout translation**

The directly reviewed analyzer screenshot is not just a total. It is a two-pane manager workflow:

```text
Left pane: league-wide stacked/team comparison, David's team highlighted, league rank visible, standings list below.
Right pane: selected-team inspector grouped by position and picks, each group carrying total value and league rank.
```

Expected RED:

```ts
expect(screen.getByText(/league rank/i)).toBeInTheDocument();
expect(screen.getByText(/future pick bank/i)).toBeInTheDocument();
expect(screen.getByText(/1\/12|rank 1 of 12/i)).toBeInTheDocument();
expect(screen.getByText(/picks are separate from lineup strength/i)).toBeInTheDocument();
```

DG translation: the stacked comparison uses neutral position colors and receipts; it cannot imply a recommended target team or trade action.

### Task 4e: Dynasty Nerds Benchmark Parity Gate

**Files:**
- Source benchmark: `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`
- Modify later: the relevant surface specs and screenshot evidence bundle paths.

- [ ] **Step 1: Add parity acceptance rows to Daily Open and I4 surface specs**

Every surface rebuilt under H2 must name the corresponding benchmark pattern:

```text
Rankings board: identity rows, value hero, uncertainty bar with numeric basis, band dividers, selectable rows, player-link affordance, updated stamp, search/filter/export chrome.
League analyzer / Franchise Equity: stacked/grouped team comparison, selected-team inspector, group totals, league rank, Future Pick Bank as first-class valued group.
Player profile: persistent player header, tabs, value/score chips, graded bars only with disclosed basis, embedded prose analysis.
Rookie board: rookie-specific identity rows, rank spread, ADP/market lane, capital/age receipts.
Film/qualitative lane: film library and notes only after source and rights policy are ratified.
```

- [ ] **Step 2: RED for screenshot-vs-screenshot preview evidence**

Visual CLEAR must cite a DG screenshot bundle and the benchmark screenshot class it was compared against:

```text
daily-open-desktop.png compared with DN rankings/analyzer benchmark as applicable
daily-open-mobile.png checked for the same hierarchy and no overlap
benchmark-delta.md records intentional differences caused by No-Verdict, receipts, or unavailable governed data
```

Expected failure: a visual CLEAR with only DOM tests, or with screenshots but no benchmark comparison, is not accepted for Daily Open or I4 visual surfaces.

- [ ] **Step 3: Pin the asset-pipeline decision**

David must ratify one of:

```text
Cache Sleeper headshots/team chips/college logos locally.
Hotlink with explicit policy controls and fallbacks.
Defer image identity until a self-hosted cache exists.
```

No implementation may fetch external player images in committed tests. Tests use local fixtures or missing-image fallbacks.

### Task 5: Storybook Decision Gate

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-h2-storybook-gate-design.md`

- [ ] **Step 1: Count stable primitives**

Run:

```bash
find frontend/src/ui -maxdepth 1 -name '*.tsx' | wc -l
```

Expected gate: Storybook remains deferred until at least 8 stable DG primitives exist.

- [ ] **Step 2: If gate opens, write a separate dependency-wall spec**

The spec must include exact pins, CI runtime impact, and whether Storybook snapshots live in repo.

Expected cockpit question:

```text
Does Storybook now reduce risk more than it adds dependency/runtime surface?
```

### Task 6: Figma And Design Source Gate

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-h2-figma-source-gate-design.md`

- [ ] **Step 1: Establish whether a Figma file is authoritative**

David answers one practical question before install:

```text
Is Figma the source of truth for DG's H2 visual system, or are repo screenshots/specs the source of truth?
```

- [ ] **Step 2: If yes, install only an official/vetted Figma MCP path**

Acceptance:

```text
The connector can read design tokens/layout metadata but cannot write repo files without cockpit review.
```

- [ ] **Step 3: If no, keep Figma out of the critical path**

Acceptance: H2 continues with repo-native specs, screenshots, and David preview gates.

### Task 7: Agentic UI Boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-05-h2-agentic-ui-boundary-design.md`

- [ ] **Step 1: Write the closed-catalog rule**

The rule:

```text
An LLM may never emit arbitrary JSX into a live DG surface. Future GenUI experiments may emit only JSON selecting from a closed DG component catalog, with Zod validation, decision_supported=false, provenance receipts, and no player/trade verdict language.
```

- [ ] **Step 2: Pin rejected patterns**

Reject:

```text
thought streaming, buy/sell recommendation cards, arbitrary shadcn installs, Tailwind generated layouts, unreviewed component registry code, and localStorage bypasses for UI proof.
```

- [ ] **Step 3: Add browser-evidence clause**

Acceptance:

```text
Every visual cockpit CLEAR must include screenshot evidence or a clear reason the change is non-visual.
```

## Falsification Matrix

1. Magic generates a nice component that violates DG tokens. Expected: rejected unless ported into semantic tokens and tests.
2. A screenshot test passes while mobile text overlaps. Expected: add mobile viewport and text-overflow assertions.
3. Axe passes but keyboard receipt control fails. Expected: keyboard-specific tests still required.
4. Storybook is installed before primitives exist. Expected: reject as cataloging inconsistency.
5. Figma connector can write files or infer unreviewed CSS. Expected: read-only/inspection-only use until cockpit authorizes generated diffs.
6. A GenUI tool proposes a player verdict card. Expected: blocked by closed-catalog/no-verdict rule.
7. Tailwind/shadcn dependency sneaks into `package.json`. Expected: scaffold contract fails.
8. Playwright goldens flake across hosts. Expected: local screenshot bundle first; committed goldens only under pinned browser/OS discipline.
9. `.mcp.json` contains secrets. Expected: fail; only env-var references permitted.
10. Visual REDs depend on gitignored data. Expected: fail; route mocks/temp fixtures only.
11. Franchise equity is presented as current team strength. Expected: fail; player lineup strength and players-plus-owned-valued-picks equity must render as separate lanes.
12. Future pick values are added without caveats. Expected: fail; pick-bank receipts disclose pick-curve basis, generic future-pick uncertainty, and count null/unvalued picks excluded from the equity total.
13. Outgoing picks are subtracted from the current pick bank. Expected: fail; outgoing picks are disclosure-only because they are not included in the owned bucket.
14. Franchise Equity trend interpolates missing captures or renders a one-point line. Expected: fail; show gaps or an insufficient-history state.
15. Franchise Equity trend uses `_latest` only. Expected: fail; trend reads historical comparable team-matrix snapshots through a tested reader seam.
16. Visual CLEAR cites Chrome DevTools MCP inspection but lacks desktop/mobile Playwright evidence. Expected: fail; DevTools MCP is iteration, not the evidence gate.
17. Motion CSS uses ad hoc durations/easings or imports Framer Motion. Expected: fail; H2 motion uses the verified Carbon-derived plain-CSS token set.
18. Chart animation morphs through invalid intermediate graphics. Expected: fail; use the Congruence rule, static replacement, or staged remove/add.
19. Dense tables render comparable numerals left-aligned or visible ISO timestamps. Expected: fail; right-align tabular numerals and show human-readable dates.
20. A rebuilt player/rankings table omits player identity cells, value-hero hierarchy, uncertainty bars with numeric basis, updated stamp, selectable/link affordances, or value-band dividers where the benchmark pattern requires them. Expected: fail unless the omission is justified by unavailable governed data and logged in benchmark-delta evidence.
21. A surface copies DN green/red or subjective tier language. Expected: fail; DG translates to neutral deltas, disclosed value bands, and no-verdict manager prose.
22. Franchise Equity hides draft picks inside an aggregate instead of rendering a first-class Future Pick Bank group with total, league rank where available, unvalued-pick exclusion, and receipts. Expected: fail.
23. A profile page lacks persistent player identity header, tabs/section navigation, or basis-disclosed graded bars when implementing the DN-profile parity class. Expected: fail.
24. Headshots/team chips/college logos hotlink live assets in committed tests or runtime code before David ratifies the asset-pipeline policy. Expected: fail; use fixtures/fallbacks until policy exists.
25. A visual CLEAR lacks `benchmark-delta.md` or equivalent notes explaining how the DG screenshot compares to the relevant Dynasty Nerds screenshot. Expected: fail for Daily Open and I4 visual surfaces.

## Cockpit Routing Request

After saving this plan, route it to Claude and Gemini:

```text
From Codex (technical reviewer) - H2 frontend capability plan for cockpit review

Artifact: docs/superpowers/plans/2026-07-05-world-class-frontend-capability-plan.md (NEW, uncommitted, on feature/horizon2-i2-daily-open). Scope: capability/tooling plan only; no runtime implementation and no dependency install. It incorporates David's Magic MCP directive, the user-provided Figma/Storybook/Tailwind/shadcn/GenUI suggestions, current Stack-A dependency wall, H2 vision constraints, and external research on agentic UX/frontend validation.

Key positions: Magic installed but API-key/restart still required; Chrome DevTools MCP proposed as the local iteration loop; Playwright+axe proposed as the repeatable evidence gate and next gated dependency-wall amendment; Dynasty Nerds benchmark becomes the screenshot parity floor; Storybook deferred until DG primitives exist; Figma conditional on an authoritative design file; Tailwind/shadcn/HeroUI/Zustand/GenUI rejected or deferred for H2 live surfaces; Lost Pixel rejected as archived; Framer Motion deferred; runtime UI remains deterministic React+vanilla CSS with browser evidence and receipts.

PLEASE REPLY with: (a) concrete defects/gaps in the tool matrix, validation gate, task order, or Dynasty Nerds benchmark translation, OR (b) no finding after checking Stack-A, No-Verdict, H2 vision, the benchmark doc, and current I2a preview boundary.
```

## Self-Review

- Spec coverage: covers tooling, principles, validation, current frontend weaknesses, Magic/MCP status, Dynasty Nerds benchmark parity, cockpit routing, and practical next increments.
- Placeholder scan: no unfinished placeholder markers or unspecified implementation rows remain.
- Scope check: this is a capability plan, not an I2a implementation plan; it avoids touching in-flight visual flip files.
- Dependency discipline: all new dependencies are proposed behind explicit David/cockpit dependency-wall amendments.
