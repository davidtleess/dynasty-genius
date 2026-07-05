# World-Class Frontend Reset Research Brief

**Date:** 2026-07-05  
**Author:** Codex (technical reviewer)  
**Status:** DRAFT v1.3 — Codex research layer plus Claude verified deep-research synthesis and directly reviewed Dynasty Nerds visual benchmark integrated; pending final cockpit review.  
**Related artifacts:** `docs/superpowers/plans/2026-07-05-world-class-frontend-capability-plan.md`; `docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md`; `docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md`; `docs/superpowers/specs/2026-07-05-h2-ui-vision-design.md`; `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`.

## 1. Research Question

What skills, plugins, connectors, infrastructure, and visual principles does the Dynasty Genius team need to build a world-class frontend after David rejected the parked I2a visual preview?

This brief focuses on evidence that changes our operating loop. It does not authorize dependencies, commits, or runtime architecture changes.

## 2. Source Set

Primary or operational sources:

- Playwright visual comparison docs — `https://playwright.dev/docs/test-snapshots`
- Playwright accessibility testing docs — `https://playwright.dev/docs/accessibility-testing`
- Claude verified deep-research synthesis — `docs/strategies/2026-07-05-deep-research-agent-frontend-synthesis.md`
- David-supplied Dynasty Nerds screenshot benchmark, directly reviewed by Codex — `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`
- Storybook interaction testing docs — `https://storybook.js.org/docs/writing-tests/interaction-testing`
- WCAG 2.2 — `https://www.w3.org/TR/WCAG22/`
- Carbon motion overview — `https://carbondesignsystem.com/elements/motion/overview/`
- Gemini animated statistical graphics grammar — `https://arxiv.org/abs/2009.01429`
- Gemini2 staged animated transitions — `https://arxiv.org/abs/2108.04385`
- 21st.dev Magic MCP — `https://github.com/21st-dev/magic-mcp`
- 21st.dev Codex plugin — `https://github.com/21st-dev/codex-plugin`
- shadcn MCP — `https://ui.shadcn.com/docs/mcp`
- Vercel AI SDK RSC generative UI state — `https://ai-sdk.dev/docs/ai-sdk-rsc/generative-ui-state`

Interpretive industry sources supplied by David:

- Standard Beagle, agentic UX — `https://standardbeagle.com/agentic-ux-designing-interfaces-for-agents/`
- Jonathan Fulton, AI UX validation problem — `https://medium.com/jonathans-musings/ai-has-a-ux-validation-problem-cf8d93ea4e92`
- Thesys AI frontend infrastructure — `https://www.thesys.dev/blogs/why-ai-frontend-infrastructure-is-the-most-overlooked-layer-in-your-llm-stack`
- Thesys HeroUI / AI-native UI article — `https://www.thesys.dev/blogs/heroui`

## 3. Findings That Matter For DG

### F1 — Agents Need Machine-Legible Interfaces And Human-Visible Control

Standard Beagle's agentic UX framing is directly relevant: UX work shifts toward APIs, schemas, field names, workflows, explainability, and control surfaces when agents participate in the workflow. For DG, this supports the existing generated-client/Zod/resource-hook boundary. It argues against pure visual polish and for a dual contract: the app must be machine-legible for agents and visually inspectable for David.

DG implication:

- Keep Zod/generated client boundaries as frontend UX infrastructure.
- Treat field labels, caveats, provenance metadata, and route states as part of the interface, not backend plumbing.
- Do not let Magic or GenUI produce components that bypass provenance and `decision_supported=false`.

### F2 — The Validation Gap Is Real: Browser Evidence Must Precede Visual CLEAR

The Fulton article states the current AI-frontend frontier plainly: agents can write frontend code, but teams still need screenshots or videos for human validation. The article also names the same failure modes DG just hit: mocks do not capture loading, errors, responsive breakpoints, edge cases, or timing.

DG implication:

- Vitest/jsdom is not enough for any visual increment.
- A cockpit visual CLEAR must include desktop screenshot, mobile screenshot, keyboard/focus evidence, and an a11y smoke or documented exception.
- Screenshot evidence should come before committed goldens. Playwright itself warns that screenshots vary across host OS, browser, settings, hardware, power source, headless mode, and fonts; that makes immediate golden baselines risky.

### F3 — Playwright + axe Is The Correct First "Agent Eyes" Stack

Playwright supports screenshots and visual comparisons, but its own docs warn about rendering variability. Playwright accessibility docs recommend `@axe-core/playwright`, but also warn automated accessibility scans catch only some issues and must be combined with manual assessment.

DG implication:

- Adopt local Playwright screenshot artifacts first.
- Add `@axe-core/playwright` for automated smoke, scoped to stable app regions.
- Keep manual screenshot review and keyboard assertions mandatory.
- Delay CI hard-gating until repeated local runs prove stable.

### F4 — Storybook Is Valuable After DG Has Primitives, Not Before

Storybook interaction tests attach user-event play functions to component stories and can be automated through its Vitest integration. That is useful only when there is a component library worth exercising. DG currently has surface-local CSS and repeated local treatments, so installing Storybook immediately would catalog inconsistency.

DG implication:

- Defer Storybook and Storybook MCP until `frontend/src/ui/` has stable DG primitives: ReceiptTrigger, CaveatBlock, MetricCell, DailyTape, SeriesSlot/ChartFrame.
- Use Storybook later to enumerate degraded, loading, empty, focus, and responsive primitive states.

### F5 — Motion Must Be A System, Not Decoration

Carbon's motion guidance supports the H2 reset direction: use motion to guide users quickly to value, avoid distracting or decorative easing, and avoid bounce/stretch/sudden-stop curves. The named productive standard easing `cubic-bezier(0.2, 0, 0.38, 0.9)` matches the motion-token plan.

DG implication:

- Add `motion.css` only after browser evidence exists.
- Permit productive motion for focus/hover, receipt reveal, drawers, row sort/filter settle.
- Reserve expressive motion for one David-previewed daily-open entrance.
- Ban pulsing deltas, urgency shimmer, recommendation-like animation, bounce, and stretch.
- Require `prefers-reduced-motion` coverage.

### F6 — Magic/21st Is Non-Negotiable, But It Must Be Cordon-Bound

The 21st Magic MCP repo describes component generation from natural-language prompts and direct IDE integration. The Codex plugin wires a remote `21st` MCP server with the `API_KEY_21ST` bearer-token environment variable and exposes component search/generation tooling.

DG implication:

- Keep the install; it satisfies David's non-negotiable tooling requirement.
- Treat generated output as inspiration or parts donor.
- No generated component lands unless ported into vanilla CSS, semantic DG tokens, a11y behavior, and cockpit tests.
- `.mcp.json` may be committed only if it contains env-var references and no secrets.

### F7 — shadcn/HeroUI/Tailwind Are Useful Market Signals, Not DG Runtime Choices

shadcn's MCP server can browse, search, and install registry components by natural language. That is powerful and risky for DG because it invites direct registry imports and style-system drift. HeroUI/NextUI and AI-native component libraries prove the market is moving toward ready-made UI systems, but adopting them would fight DG's vanilla-CSS and dependency-wall discipline.

DG implication:

- Keep shadcn MCP deferred.
- Reject HeroUI/NextUI and Tailwind for H2 runtime unless David explicitly opens a dependency-wall amendment.
- Use these ecosystems only as visual references for density, component states, and interaction patterns.

### F8 — Runtime Generative UI Is A Future Experiment, Not H2 Infrastructure

Vercel AI SDK RSC supports generative UI state and React component streaming, but the page itself flags AI SDK RSC as experimental and recommends AI SDK UI for production. More importantly, DG's live league surfaces cannot let an LLM choose decision-shaped UI at runtime.

DG implication:

- No runtime GenUI in H2.
- Future GenUI can only emit JSON selecting from a closed DG component catalog with Zod validation, provenance receipts, `decision_supported=false`, and no verdict language.

### F9 — WCAG Must Become Visual Acceptance, Not A Compliance Appendix

WCAG's testable criteria reinforce the reset's focus on text alternatives, labels, contrast, keyboard/focus, reduced motion, and reflow. Playwright's accessibility docs also make clear that automation is incomplete.

DG implication:

- Add keyboard/focus assertions beside axe scans.
- Add mobile viewport evidence for reflow and text fit.
- Treat focus visibility as a first-class design token consumer.
- Do not let hover-only receipts or hover-only provenance pass.

### F10 — Data Motion Must Preserve Semantics

The visualization research behind Gemini and Gemini2 is directly relevant to DG's "spectacular" layer. Animated transitions can help viewers follow related statistical graphics, but only when transition steps preserve semantic correspondence, use simple/staged changes, and avoid implying relationships that are not in the data. Gemini2's staged-keyframe work reinforces that complex chart changes should be decomposed into semantic edit operations before animation is allowed.

DG implication:

- Do not animate unrelated metrics or schema changes as if one continuously morphs into the other.
- Prefer staged transitions for chart updates: axes/substrate first, then marks, then labels/receipts.
- Keep the Hard Right Edge static as the factual boundary; no animation may draw beyond the last verified capture.
- Motion tests should assert reduced-motion behavior and no SVG path appears without real PIT-series data.

### F11 — Integrity Is Backend Discipline; UI Copy Is Dynasty Language

David's directive resolves the copy hierarchy: the models, data contracts, caveats, and provenance must stay strict, but the primary frontend cannot speak like a backend log. Raw field names, API route names, schema terms, caveat tokens, and validation jargon are implementation evidence. They belong in receipts, developer diagnostics, and tests. David-facing prose should read like a sharp dynasty manager, not a JSON payload.

DG implication:

- Keep raw technical identifiers available in receipts, titles, dev tools, or copied diagnostics where they preserve auditability.
- Translate primary UI copy into football, fantasy, and dynasty-manager language.
- `describeStatusToken`, `DisclosureLine`, `CaveatBlock`, `DailyTape`, and future copy helpers become part of the design system, not one-off wording.
- REDs should fail if primary UI regions render raw backend terms such as route names, snake_case caveat codes, or `decision_supported` copy.

### F12 — Dynasty Balance Sheet Views Need Explicit Separation From Weekly Strength

David's player-ranking and team-value question exposes a product requirement for the reset: the frontend needs an asset-management view that compares every roster as a dynasty balance sheet, not only as a current lineup. The data substrate can value players and owned future picks on the same yardstick, but the interface must not collapse those into one ambiguous "team value" number.

DG implication:

- Add a named Franchise Equity view to H2 planning.
- Keep Lineup Strength players-only.
- Render Future Pick Bank separately as owned valued picks, with outgoing picks shown as disclosure rather than subtracted.
- Count null/unvalued picks as excluded from the equity total, with the excluded count visible.
- Render Franchise Equity as roster player value plus owned valued future-pick value, with basis disclosed and no action-order language.
- Add Franchise Equity Trend as a follow-on league comparison over historical team-matrix snapshots. The trend must show gaps, insufficient-history states, and the Hard Right Edge rather than implying a smooth uninterrupted curve.

### F13 — The Shipped App Is The Design Artifact

Claude's verified synthesis adds the Linear craft model: static mockups are references, not the product. The running app is what gets screenshot, marked up, and iterated. For DG, this confirms that a small governed token vocabulary plus screenshot iteration is more valuable now than a large component-library install or design-file pipeline.

DG implication:

- Treat browser screenshots as design artifacts, not merely QA attachments.
- Keep the token vocabulary intentionally small until the app has coherent rendered evidence.
- Do not let a static mockup override evidence from the actual FastAPI/Vite path.

### F14 — Chrome DevTools MCP Is Iteration, Playwright + axe Is Evidence

The verified synthesis identifies Chrome DevTools MCP as the strongest current agent-eyes iteration loop: live screenshot/DOM/CSS inspection, console and network diagnosis, device emulation, and performance traces. It is not the same thing as the repeatable evidence gate. Playwright + axe remains the packageable evidence bundle for cockpit review.

DG implication:

- Add Chrome DevTools MCP to local tooling if David ratifies it.
- Cite DevTools MCP findings as inspection notes during design iteration.
- Still require desktop/mobile Playwright screenshots and axe/keyboard evidence for visual CLEAR.

### F15 — Motion Should Be Plain CSS Tokens, Not A Runtime Library

The verified synthesis grounds H2 motion in the Carbon token model: six durations from 70ms to 700ms, productive standard/entrance/exit cubic-beziers, bounce/stretch banned, and chart transitions treated separately around one second per Congruence-bounded stage. It also verifies that Framer Motion has a bundle floor DG does not need for H2, while Lost Pixel is archived and should not be adopted.

DG implication:

- Implement `motion.css` with the Carbon-derived token set.
- Keep chart animation under the semantic Congruence rule: intermediate frames must remain valid data graphics.
- Reject Lost Pixel; defer Framer Motion/LazyMotion unless a later spec proves CSS tokens cannot express the interaction.

### F16 — Dense Tables Need Their Own Craft Contract

The verified synthesis adds dense-data mechanics that should become primitive contracts, not one-off CSS: 4px-grid padding steps, sticky headers where density requires them, sortable affordances only with declared sort basis, right-aligned tabular numerals, left-aligned text, and human-readable dates.

DG implication:

- Add `DenseTable` or equivalent row primitives after the browser evidence gate.
- Fail visible ISO timestamps in table cells unless they are receipts/title attributes.
- Right-align comparable numeric values and keep text labels left-aligned.

### F17 — Dynasty Nerds Establishes The Concrete Parity Floor

David's 14 screenshots make the benchmark specific rather than aspirational. Direct viewing confirms the decisive mechanics: identity cells with headshots/team chips, selectable rows and player-link affordances, value numbers as focal objects, compact per-row uncertainty bars with numeric sigma labels, in-grid sparklines, tier/value band dividers, updated stamps, filter/search/export chrome, two-pane league analyzer layout, position/pick group totals with league rank, first-class valued draft picks, tabbed player profiles, graded bars, and embedded scouting prose/film surfaces.

DG implication:

- Add `PlayerIdentity`, `ValueHero`, `SpreadBar`, `ValueBandDivider`, and `GradedBar` primitives.
- Require screenshot-vs-screenshot comparison and a benchmark-delta note for Daily Open and I4 surface previews.
- Translate DN's green/red and subjective tier language into neutral signed deltas, disclosed value bands, receipts, and model/market lanes.
- Treat Future Pick Bank as a first-class valued group in Franchise Equity, not a hidden subcomponent.
- Gate headshots, team chips, and college logos behind a ratified asset-pipeline policy with accessible fallbacks.

## 4. What The Current UI Is Missing

The current UI is bad because it lacks a governed visual operating system:

- no browser evidence loop;
- no shared primitive library;
- no enforced token consumption;
- no consistent focus/elevation/hover model;
- no motion system;
- no semantic transition grammar for data motion;
- no strict manager-language layer between backend truth and David-facing copy;
- no explicit franchise-equity view or trend that separates current lineup strength from players-plus-owned-valued-picks dynasty balance sheet;
- no Chrome DevTools MCP / Playwright role split;
- no dense-table primitive contract for numerals, dates, sticky headers, or sortable affordances;
- no concrete benchmark-parity gate against David's Dynasty Nerds screenshots;
- no disciplined bridge between external component generators and DG's constraints;
- no visual acceptance record for mobile and dense data states.

The surprising part is not that I2a looked bad. The surprising part is that our process let it get to David before producing screenshot evidence that would have made the incoherence obvious.

## 5. Skills, Plugins, Connectors, Infrastructure

Adopt now:

- Chrome DevTools MCP for local interactive inspection and debugging.
- Playwright local screenshot evidence harness.
- `@axe-core/playwright` accessibility smoke.
- Codex browser-use skill for local visual inspection.
- 21st.dev Magic MCP / Codex plugin, env-var authenticated, inspiration-only.

Adopt after primitives:

- Storybook and Storybook MCP.
- Internal DG frontend skill/plugin encoding Hard Right Edge, receipts, no verdict hues, 32px rows, caveat placement, no nested cards, responsive fit, and evidence requirements.

Conditional:

- Figma MCP only if David designates a Figma file as source of truth.

Reject or defer for H2:

- Lost Pixel visual regression.
- Framer Motion / Motion runtime.
- Tailwind/Tailwind IntelliSense as repo style system.
- shadcn direct installs.
- HeroUI/NextUI runtime dependency.
- Vercel AI SDK / LCEL runtime GenUI.
- Zustand/React Query/TanStack Router absent a proven state problem.
- SSE/thought streaming for live surfaces.
- Bidirectional canvas manipulation for core DG reading surfaces.

## 6. Reset Program Consequences

The next visual work should not be "make the parked I2a prettier." It should be:

1. stop-the-line reset spec;
2. browser evidence harness;
3. primitive library;
4. CSS token debt audit;
5. motion token system;
6. dense-table primitives and chart Congruence rules;
7. Dynasty Nerds benchmark parity primitives and screenshot-delta evidence;
8. manager-language copy layer;
9. franchise-equity asset board;
10. franchise-equity trend versus league, gated by historical comparable captures;
11. restarted daily open using I2a only as a parts donor;
12. David preview before commit.

## 7. Open Questions For Cockpit

1. Should `.mcp.json` be committed env-var-only or kept local/gitignored?
2. Should the first executable task be browser evidence or primitive library? Codex position: browser evidence first.
3. Should Storybook enter immediately after three primitives or wait for eight to twelve? Codex position: wait for enough surface area to avoid cataloging inconsistency.
4. Does Claude's deep-research synthesis add a design principle or tool that changes the task order?

## 8. Self-Review

- Placeholder scan: no incomplete placeholder rows.
- Source hierarchy: primary docs used for infrastructure claims; industry articles used only for interpretive framing.
- Governance: No-Verdict and Stack-A constraints remain explicit.
- Scope: research brief only; no dependency install or runtime code change.
