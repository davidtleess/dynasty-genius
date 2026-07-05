# H2 Frontend Reset — Design Spec

**Date:** 2026-07-05 · **Author:** Codex (technical reviewer) · **Status:** v1.6 — **RATIFIED by David 2026-07-05** ("we are good to go") after full-package convergence: Claude D1-D3 + deep-research synthesis integrated; semantic data-motion; DG Voice System; Franchise Equity (D1/D2-corrected); DN visual benchmark with all three agents viewing the 14 screenshots directly; Claude + Codex CLEARs on record; Gemini advisory concurrence. Recommended defaults stand on the open decisions unless David rules otherwise; the asset-pipeline decision returns to David concretely when the PlayerIdentity primitive ships.
**Program:** Horizon 2 world-class UI reset after David's I2a preview verdict.
**Related artifacts:** `docs/superpowers/plans/2026-07-05-world-class-frontend-capability-plan.md`; `docs/strategies/2026-07-05-world-class-frontend-research-brief.md`; `docs/strategies/2026-07-05-deep-research-agent-frontend-synthesis.md`; `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`; `docs/strategies/2026-07-05-frontend-css-design-debt-audit.md`; `docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md`; `docs/superpowers/specs/2026-07-05-h2-ui-vision-design.md`; parked `docs/superpowers/specs/2026-07-05-h2-i2a-visual-flip-design.md`.

## 1. Goal

Stop the visual-shipping lane, diagnose the craft failure as a system defect, and restart H2 visual work around evidence-bearing browser inspection, governed UI primitives, and a constrained motion/color/type system.

This spec is not a commit authorization and not a merge plan. It is the reset contract the cockpit should attack before David ratifies the next visual increment.

## 2. Preview Ruling And Current State

David previewed I2a on 2026-07-05 and ruled the current version not good enough. The parked branch work remains useful only as a parts donor; it is not a ship candidate.

The ratified H2 vision v3 remains the aesthetic constitution. The Hard Right Edge, focusable receipts, film-room token direction, Archivo/Plex taste call, and aesthetic cordon still bind H2. This reset replaces the I1/I2 execution path, not the design direction.

The immediate defect class is structural:

- dark tokens were activated over component CSS that still carried light-era hardcoded colors;
- the repo had token tests but no browser-evidence gate that could see whether the rendered result looked coherent;
- the cockpit greened DOM contracts and type checks while missing hierarchy, palette clash, focus visibility, and perceived craft;
- the daily-open idea was directionally right, but the implementation did not yet have a shared visual grammar strong enough to support it.

## 3. Inviolates

These rules hold through the reset:

1. I2a does not merge as the H2 visual flip.
2. No fake sparklines, player/PIT trend lines, or extrapolation placeholders render before the I2b PIT-series API exists. Franchise Equity Trend is separately gated on historical comparable team-matrix snapshots.
3. The No-Verdict line holds: no buy/sell/hold, urgency, action-order, confidence, green/red outcome semantics, or hidden recommendation language.
4. Stack-A remains Vite, React, TypeScript, generated client/Zod boundary, Vitest, Biome, vanilla CSS, and exact dependency-wall governance.
5. Tailwind, shadcn runtime installs, HeroUI, runtime GenUI, Zustand, React Query, TanStack Router, and SSE/thought streaming remain out of H2 unless David opens a separate dependency-wall/spec cycle.
6. Magic/21st is inspiration-only. Generated UI may not land without DG token conversion, accessibility review, screenshot evidence, banned-language scan, and cockpit review.
7. Mitigation tripwires, System Health token isolation, and generated-client boundaries stay locked.
8. Broad visual flips require David preview evidence before commit.

## 4. Root-Cause Diagnosis

The frontend failed because it had correctness contracts without visual perception.

Specific causes to fix:

- **Declared theme, not designed theme:** one static `data-theme="dark"` activation exposed how many surface CSS files still owned their own palette.
- **Tokens without consumption:** semantic aliases existed, but most rendered components still used local CSS decisions.
- **No primitive layer:** receipts, caveats, metric cells, tape facts, chart slots, empty states, and row density were recreated per surface.
- **No focus grammar:** `--dg-focus` existed but did not appear as a visible, consistent keyboard-position system.
- **No elevation/rhythm system:** surfaces used independent radii, spacing, borders, opacity, hover, and row treatments.
- **No agent eyes:** jsdom/Vitest could assert text and roles but not contrast, overlap, visual hierarchy, mobile fit, or whether the page felt coherent.
- **Late human validation:** David saw the visual problem only after local GREEN instead of seeing screenshot evidence during the cockpit cycle.

The local evidence register is `docs/strategies/2026-07-05-frontend-css-design-debt-audit.md`: raw color literals or raw OKLCH values appear across 11 component CSS files; `--dg-focus` is defined but not consumed by component CSS; and font-size/radius choices are surface-local rather than governed.

## 5. Research Principles

The Codex research brief at `docs/strategies/2026-07-05-world-class-frontend-research-brief.md`, the verified deep-research synthesis at `docs/strategies/2026-07-05-deep-research-agent-frontend-synthesis.md`, and Claude's Dynasty Nerds visual benchmark at `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md` are the source layer for the reset.

Current working principles:

- agentic UX still needs machine-readable schemas and human-visible control;
- the shipped app is the design artifact; screenshot-iterate over a minimal token vocabulary instead of pretending a static mockup is the product;
- AI-authored frontend work needs browser screenshots or videos and human visual validation;
- Playwright + axe is the correct first agent-eyes stack, but evidence artifacts precede committed visual goldens;
- Chrome DevTools MCP joins as the interactive iteration and debugging loop; Playwright + axe remain the repeatable evidence gate;
- automated a11y is necessary but not sufficient; keyboard, focus, reduced-motion, contrast, reflow, and name/role/value checks remain explicit;
- motion must guide comprehension, preserve semantic correspondence, and never create urgency or implied action;
- chart motion should be simple and staged: substrate/axis changes first, then marks, then labels/receipts;
- the screen speaks dynasty manager: primary rendered copy uses football/fantasy/dynasty prose, not backend nouns, raw schema terms, snake_case tokens, or route/artifact jargon;
- technical precision lives one layer down in receipts, title attributes, diagnostics, and copied audit values;
- the visual bar is concrete: David's Dynasty Nerds screenshots are the parity floor for dense rankings, league analyzer, rookie board, player profile, and film-room quality, translated through DG's No-Verdict, two-lane, receipt-first law;
- Storybook becomes valuable after DG has a small primitive library, not before;
- Magic/21st is non-negotiable as a tool but cordon-bound as inspiration-only;
- runtime AI-generated components are deferred beyond H2 live surfaces.
- franchise equity belongs in the reset roadmap as a named asset-management view: player value and valued owned future-pick value can share a value yardstick, but current-strength views must stay players-only.

## 6. Reset Architecture

### Task 0 — Stop The Line

Patch the I2a spec and ledger to record the preview outcome:

```text
David previewed I2a on 2026-07-05 and ruled it not good enough. The branch remains parked and must not merge as the H2 visual flip. Restart visual work from the reset spec; treat parked I2a as a parts donor only.
```

Allowed parts to re-enter through later gates:

- endpoint wiring for the daily tape;
- no-fake-series test boundaries;
- font-pipeline activation work;
- H1 copy and disclosure contracts;
- density rows that pass the new browser-evidence gate.

### Task 1 — Browser Evidence Gate

Add a local-first Playwright and axe evidence harness behind a dependency-wall amendment. Add Chrome DevTools MCP as the agent-eyes iteration loop, not as the evidence gate.

Candidate exact pins:

```text
@playwright/test 1.61.1
@axe-core/playwright 4.12.1
```

Initial acceptance is artifact-based, not golden-baseline-based:

- desktop screenshot of Daily What-Changed;
- mobile screenshot of Daily What-Changed;
- keyboard/focus smoke captured as evidence, not a Task-1 pass gate;
- axe smoke over the shell/main region;
- optional Chrome DevTools MCP inspection notes for layout/CSS/network/debugging issues when the visual defect needs live diagnosis;
- route-mocked or fixture-backed data, never gitignored artifact dependency;
- no CI hard gate until repeated local runs prove the harness is stable.

Role split:

- **Chrome DevTools MCP:** interactive screenshot/DOM/CSS/network/performance debugging during iteration. Costs are explicit: Chrome-only, tool-token overhead, and local-preview maturity risk. It is MCP/tooling infrastructure, not a runtime dependency and not a CI gate.
- **Playwright + axe:** repeatable screenshot/a11y evidence bundle for cockpit review. This is the ship gate for visual work.

The current audit shows no governed focus grammar, so the first focus pass is expected to expose failures. Task 1 records those failures into the debt register. Pass gates for keyboard-visible focus begin when Task 2 primitives and Task 3 migration work create the governed focus system.

Committed visual goldens require a later cockpit decision after font, viewport, browser, and artifact paths are stable.

### Task 2 — DG Primitive Layer

Create a small `frontend/src/ui/` system before another broad reskin:

- `ReceiptTrigger`: focusable provenance control with `aria-expanded`, Enter/Esc/touch support, and hover as enhancement only.
- `CaveatBlock`: standard high-contrast neutral/amber disclosure block with no nested-card pattern.
- `MetricCell`: mono/tabular value, label, caveat hook, receipt hook, and right-aligned numerals.
- `ValueHero`: large focal valuation number with label, basis receipt, caveat hook, and neutral tier/value-band treatment.
- `PlayerIdentity`: player headshot, name, position chip, NFL team-color chip, optional college logo, and accessible fallback for missing images.
- `SpreadBar`: per-row visual uncertainty/range indicator; may render fold CI, ranker spread, or unavailable state only when the basis is disclosed.
- `ValueBandDivider`: labeled table/group divider with disclosed numeric basis, never subjective "elite/bust" language.
- `GradedBar`: attribute/combine/model component bar with disclosed basis and neutral/brand-safe palette; no verdict colors.
- `DenseTable` / row primitives: 4px-grid padding steps, sticky headers where the viewport needs them, sortable-column affordances only when the sort basis is declared, right-aligned numerals, left-aligned text, and human-readable dates in visible cells.
- `DailyTape`: substrate facts only; capture health and model provenance; degraded states explicit.
- `DisclosureLine`: standard "Descriptive only — not decision-grade." rendering with consistent placement, size, and contrast.
- `SeriesSlot`: empty/pending/gap/series states; no `<path>` unless real series data exists.
- `ChartFrame`: title, disclosure, right-edge contract, accessible summary.

Every primitive must have DOM tests, CSS-token tests, keyboard tests when interactive, and screenshot evidence when it changes visible layout.

Dynasty Nerds parity acceptance for primitives:

- long player/ranking tables must support identity cells, value-as-hero numbers, per-row uncertainty bars, in-grid sparklines only when real series data exists, value-band dividers, updated stamps, search/filter/export chrome where the surface owns that workflow, selectable rows and player-link affordances where the surface offers comparison/profile actions, and group totals with league rank where the data supports it;
- profile/rookie pages must use a persistent player identity header, tabs or section navigation, basis-disclosed graded bars, and embedded football prose only when source/rights policy is satisfied;
- subjective DN tier labels translate to disclosed value bands such as "Band 1 - model value 90-100";
- green/red DN semantics translate to neutral signed deltas and model/market lane hues;
- headshot and logo rendering is gated by the asset-pipeline decision in section 8.

### Task 2b — DG Voice System

Create the voice layer before broad surface rewrites:

- Gemini drafts the initial voice guide as Dynasty-Strategy PM; Claude and Codex review; David ratifies the voice. Current working draft: `docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md`.
- `frontend/src/lib/copy.ts` grows into the single voice module every surface imports for status tokens, metric names, caveats, disclosure lines, capture timestamps, and system-health facts.
- Primary visible strings use prose in football/fantasy/dynasty-manager language.
- System nouns and raw backend terms stay out of visible prose: registry, artifact, schema, vintage, capture store, settlement, structural_context, raw route names, snake_case caveat codes, and literal `decision_supported`.
- Metric names face the same translation rule. Default until David ratifies otherwise: technical symbols such as xVAR/DVS live in receipts or title attributes, while primary copy uses manager phrases such as "value over a replacement starter."
- The H1 raw-ISO title-attribute pattern generalizes: exact values remain inspectable without making the main screen read like a backend report.

Acceptance:

- rendered-copy scan bans snake_case and a ratified system-noun blocklist in visible text;
- receipts, title attributes, developer zone, and copied diagnostics are exempt when they preserve auditability;
- Daily Tape substrate facts render as manager prose, e.g. "Market Sync Active: 32 consecutive days tracked", "prices last captured yesterday", and "Projection Update: July 5, current", not "Registry version: 4" or "Model vintage: ok";
- every new surface imports the shared voice module instead of hand-rolling backend-token copy.

### Task 3 — CSS Token Debt Audit

Add report-first CSS audits before broad migration:

- raw hex/OKLCH census by file;
- raw spacing/radius/font-size census by file;
- focus-token consumption check;
- surface-local duplicate row treatment report;
- new `frontend/src/ui/` files fail on raw colors and non-token font families from day one.

The first reset increment should reduce or explicitly justify raw-value count. It should not attempt a whole-repo CSS rewrite.

### Task 4 — Motion System

Add `frontend/src/styles/motion.css` only after the browser gate exists.

Use plain CSS tokens derived from the verified Carbon motion model; do not add a motion runtime dependency.

Required token shape:

```css
--dg-duration-fast-01: 70ms;
--dg-duration-fast-02: 110ms;
--dg-duration-moderate-01: 150ms;
--dg-duration-moderate-02: 240ms;
--dg-duration-slow-01: 400ms;
--dg-duration-slow-02: 700ms;
--dg-duration-chart-stage: 1000ms;
--dg-ease-productive-standard: cubic-bezier(0.2, 0, 0.38, 0.9);
--dg-ease-productive-entrance: cubic-bezier(0, 0, 0.38, 0.9);
--dg-ease-productive-exit: cubic-bezier(0.2, 0, 1, 0.9);
```

Micro-interactions should usually live in the 90-120ms range using the nearest token. Distance/size can move a transition up the token scale. Chart transitions are their own Congruence-bounded class, not ordinary UI flourish.

Allowed motion:

- productive hover/focus feedback;
- receipt reveal;
- drawer open/close;
- row sort/filter settle;
- staged chart updates that preserve semantic correspondence once real PIT-series data exists;
- one David-previewed daily-open entrance.
- chart-transition stages around 1000ms only when every intermediate frame remains a valid data graphic.

Forbidden motion:

- pulsing deltas;
- urgency shimmer;
- bounce/stretch;
- morphing unrelated metrics, schema changes, or missing data as if they were continuous observations;
- chart animation when the start and end states share no data dimension;
- drawing past the Hard Right Edge;
- motion that implies confidence, opportunity, or a player action.

Every motion class needs `prefers-reduced-motion: reduce` behavior. Framer Motion, LazyMotion, and other motion libraries remain deferred unless a later spec proves CSS tokens cannot express the required interaction.

### Task 5 — Restart Daily Open

Rebuild the Daily What-Changed visual flip only after Tasks 1-4 have minimum viable coverage.

Acceptance:

- the Task-3 census reports zero dark-on-dark, white-box, or ghost-token findings across the flip blast radius: shell, What-Changed, SystemHealthCard, CommandPalette, and TrustStrip;
- no fake PIT lines;
- tape facts render from route mocks and live-smoke data;
- Dynasty Nerds benchmark parity rows that apply to the daily open are checked at David preview: value numbers have hierarchy, table/list rows carry identity where player rows appear, updated stamps are visible, empty chart slots stay honest, and the screenshot bundle is compared against the relevant benchmark screenshot rather than judged from DOM tests alone;
- screenshot bundle reviewed before GREEN CLEAR;
- David preview happens before commit;
- the parked I2a code is copied selectively, never merged wholesale.

### Task 6 — Franchise Equity View

Add a named H2 product increment for the league-wide asset board David asked for: every team compared by current roster strength and by total dynasty balance sheet.

This is not a claim that the current UI already ships the view. Current repo state gives the substrate: team-value artifacts expose player-value views and future picks; future picks carry valuation fields; `src/dynasty_genius/team_value_matrix.py` explicitly keeps pick value out of `starter_weighted_xvar` team-strength aggregates. The reset must preserve that distinction.

Required manager-facing lanes:

- **Lineup Strength:** players only; current playable lineup and depth.
- **Roster Player Value:** players only; full roster asset base.
- **Future Pick Bank:** owned valued future picks, with outgoing picks disclosed separately and pick-curve receipts plus uncertainty caveats.
- **Franchise Equity:** roster player value plus owned valued future-pick value, presented as dynasty balance sheet, not current weekly strength.

Required layout translation from the directly reviewed DN analyzer:

- left pane: league-wide team comparison with David's team highlighted, league rank visible, and standings/list context below;
- right pane: selected-team inspector grouped by position and Future Pick Bank, each group carrying total value and league rank where available;
- no stacked/team bar, group row, or standings row may imply a recommended trade target or action order.

Acceptance:

- no primary label renders raw field names such as `starter_weighted_xvar`, `total_xvar_capped`, or `future_picks`;
- future picks render as a first-class valued group with group total, league rank where available, method receipt, unvalued-pick exclusion count, and outgoing-pick disclosure; they are not hidden inside a generic total;
- pick values carry receipts describing historical expected value, round-tier/generic-pick limits, and thin-sample caveats where present;
- picks with null value, including round-4+ or unresolved-slot picks outside the current pick curve, are counted as unvalued and excluded from the equity total;
- outgoing picks are disclosure-only because they are not included in the owned bucket;
- the surface states plainly that picks are separate from current lineup strength;
- ranks disclose basis and never become a hidden action order;
- the view uses the DG voice module and shared primitives, not one-off League Pulse copy.

Trend extension:

- Franchise Equity Trend compares every team over time using historical comparable team-matrix snapshots, not `_latest` alone;
- existing dated `team_value_matrix_phase17-3-*` files are seed substrate, but committed tests use temp fixtures and a dependency-injected reader seam;
- no trend path renders with fewer than two comparable captures for that team;
- missing captures render as gaps, not interpolation;
- every plotted point carries capture date, source artifact id, roster player value, owned valued pick total, unvalued-pick excluded count, and outgoing-picks disclosure count;
- the Hard Right Edge stops at the latest verified team-matrix capture;
- trend copy says "compared with league" or equivalent manager prose, never action-order language.

## 7. Falsification Seeds

1. A test suite passes but desktop screenshot shows hardcoded light panels on dark background. Expected: visual GREEN blocked.
2. Mobile screenshot has clipped or overlapping text. Expected: visual GREEN blocked until layout is fixed or text is moved.
3. Axe passes but receipt cannot be opened by keyboard. Expected: RED fails; axe alone is not enough.
4. Magic emits Tailwind or shadcn code. Expected: blocked unless manually ported into DG vanilla CSS and dependency wall remains unchanged.
5. A chart slot renders an SVG path without a real PIT-series response. Expected: RED fails.
6. A visual test reads gitignored `app/data/**`. Expected: RED rejected; use route mocks/temp fixtures.
7. A new UI primitive uses raw hex or local font-family. Expected: primitive CSS test fails.
8. A motion class lacks reduced-motion handling. Expected: motion test fails.
9. `.mcp.json` contains a literal API key. Expected: fail; only env-var references are permitted.
10. Browser evidence is missing from a visual CLEAR. Expected: cockpit does not accept the CLEAR unless the change is proven non-visual.
11. Visual goldens are introduced before screenshot artifacts prove local stability. Expected: reject goldens; keep evidence bundle only.
12. A "quiet day" empty state implies nothing important happened when capture/provenance is degraded. Expected: empty state must distinguish healthy quiet from unavailable substrate.
13. A chart animation morphs one metric/schema into another without a shared semantic identity. Expected: RED fails; use staged remove/add or no animation.
14. Primary visible text renders snake_case, route names, system nouns, or raw backend tokens such as `decision_supported`, `structural_context`, `registry`, `artifact`, `schema`, `vintage`, `capture_store`, or `settlement`. Expected: rendered-copy tripwire fails unless the term appears only in an exempt receipt/title/diagnostic context.
15. Franchise Equity silently folds pick value into Lineup Strength. Expected: RED fails; players-only strength and players-plus-owned-valued-picks equity are separate lanes.
16. Future pick bank renders as certain player-equivalent value without caveats. Expected: RED fails; pick receipts disclose exact-slot vs round-tier/generic basis, historical expected-value limits, and the count of null/unvalued picks excluded from the total.
17. Outgoing picks are subtracted from the current pick bank. Expected: RED fails; outgoing picks are disclosure-only because they are not included in owned picks.
18. Franchise Equity trend renders from `_latest` only or with fewer than two comparable captures. Expected: RED fails; trend requires historical comparable snapshots and otherwise renders insufficient-history copy.
19. Franchise Equity trend interpolates missing captures or draws past the latest verified team-matrix capture. Expected: RED fails; gaps stay visible and the Hard Right Edge holds.
20. A primitive table renders comparable numeric values left-aligned, visible ISO timestamps, or non-sticky headers in a dense comparison view. Expected: RED fails; numerals are right-aligned, visible dates are manager-readable, and sticky/sortable behavior follows the declared table contract.
21. Motion tokens use ad hoc durations/easings or chart transitions animate through invalid intermediate graphics. Expected: RED fails; Carbon-derived CSS tokens and the Congruence rule are enforced.
22. A visual CLEAR cites Chrome DevTools MCP inspection but lacks the Playwright/axe evidence bundle. Expected: cockpit does not accept the CLEAR; DevTools MCP is the iteration loop, not the repeatable evidence gate.
23. A rebuilt rankings/player table lacks player identity cells, value-hero hierarchy, disclosed uncertainty bars, updated stamp, or value-band dividers where the corresponding Dynasty Nerds screenshot has them. Expected: David-preview parity gate fails unless the omission is explicitly justified by unavailable governed data.
24. A value band uses subjective labels such as "elite", "bust", or "core piece" without disclosed numeric basis. Expected: RED fails; DG uses disclosed value bands and manager prose without smuggled verdicts.
25. A franchise-equity panel hides picks in a total instead of rendering Future Pick Bank as its own valued group with league rank and receipts. Expected: RED fails; picks are first-class assets but separate from lineup strength.
26. Headshots, team chips, or college logos hotlink external assets without the ratified asset-pipeline policy. Expected: RED fails; image identity requires the David-gated cache/hotlink decision and accessible fallbacks.
27. A profile page lacks persistent player identity header, tabs/section navigation, or basis-disclosed graded bars when implementing the DN-profile parity class. Expected: RED fails.
28. A visual CLEAR lacks `benchmark-delta.md` or equivalent notes explaining how the DG screenshot compares to the relevant Dynasty Nerds screenshot. Expected: cockpit does not accept the CLEAR for Daily Open or I4 visual surfaces.

## 8. Open Decisions For David

1. Commit `.mcp.json` with env-var-only config, or keep it local/gitignored.
2. Authorize the Playwright/axe dependency-wall amendment with the exact pins above.
3. Choose the design source of truth for H2: repo screenshots/specs first, or Figma first.
4. Confirm the next executable order: browser evidence gate before primitives, or primitives before browser evidence. Codex recommends browser evidence first because the preview failure was a perception failure.
5. Confirm the document hierarchy: H2 vision v3 remains the aesthetic constitution; this reset spec governs the restarted I1/I2 execution path; the parked I2a spec remains historical with an outcome patch.
6. Ratify the DG voice guide after Gemini drafts it and Claude/Codex review it, including whether metric symbols such as xVAR/DVS are taught as product vocabulary or remain receipt/title symbols behind primary prose.
7. Ratify Franchise Equity as an H2 named increment: players-only lineup strength stays distinct from players-plus-owned-valued-picks dynasty balance sheet, with unvalued-pick exclusions disclosed.
8. Ratify Franchise Equity Trend as a follow-on view over historical team-matrix snapshots, gated by insufficient-history and Hard Right Edge rules.
9. Ratify Chrome DevTools MCP as local agent-eyes iteration infrastructure while keeping Playwright + axe as the evidence gate.
10. Ratify the player-identity asset pipeline: cache Sleeper headshots/team-color chips/college logos locally, hotlink with policy controls, or defer images until a self-hosted cache exists.

## 9. Cockpit Review Request

Route this draft only after Claude's research package either lands or remains materially delayed:

```text
From Codex (technical reviewer) - H2 frontend reset spec working draft

Artifact: docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md (NEW, uncommitted, DRAFT v1.6 on feature/horizon2-i2-daily-open). This is the Codex working draft after integrating Claude's verified deep-research synthesis and Dynasty Nerds visual benchmark; it still needs final dual cockpit CLEAR before David ratifies the package.

Scope: stop-the-line reset after David's negative I2a preview; no runtime implementation, no dependency install, no edits to parked I2a code. It encodes I2a-as-parts-donor, browser evidence before visual GREEN, DG primitive library before broad reskin, CSS token debt audit, motion constraints, Magic/21st cordon, and David decision points.

PLEASE REPLY with: (a) concrete defects/gaps in the reset diagnosis, task order, falsification seeds, David decision list, or Dynasty Nerds benchmark translation, OR (b) no finding after checking it against the capability plan, H2 vision v3, Stack-A wall, No-Verdict line, Claude's verified deep-research synthesis, and the Dynasty Nerds visual benchmark.
```

## 10. Self-Review

- Placeholder scan: no unfinished placeholder markers or unspecified implementation slots remain; the Codex research brief, Claude deep-research synthesis, and Dynasty Nerds benchmark are linked.
- Scope check: this is a reset design, not implementation. It does not install dependencies or change runtime code.
- Consistency check: I2a remains parked; allowed work re-enters only through evidence gates.
- Governance check: No-Verdict, Stack-A, generated-client boundary, and no-fake-series constraints are explicit.
