# Dynasty Genius — UI Architecture Recommendation

## TL;DR
- **Build a single analytical workstation, not seven dashboards.** Adopt a Linear/Bloomberg-Terminal lineage visual language (Inter typeface, 8px spacing scale, dark-first dense layout) with a strict two-lane "Model vs. Market" presentation system, a canonical Decision Card component where uncertainty range and a mandatory counter-argument are first-class fields, and a clearly-marked "Experimental" treatment for surfaces that haven't earned decision-grade trust yet.
- **Tech stack: stay close to Python.** Migrate from raw static HTML to **FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind CSS (shadcn-style CSS-variable tokens) + Observable Plot** — a no-build, single-mental-model stack that fits a solo learning-developer, with a documented escape hatch to a single React island via Vite if Trade Lab's interactive complexity outgrows Alpine. Reject Astro (its own docs route dashboards elsewhere) and reject full React/Next (overkill, build-pipeline tax, harder to maintain alone).
- **Build order: Trade Lab first (full), then Backtest/Trust Surface, then Rookie Board polish.** Trade Lab is the immediate target because the backend just shipped; the Backtest surface goes next not because it's user-facing high-value but because it's the credibility layer — without it, every other surface inherits unearned authority. Rookie Board is most mature analytically but already has a working surface, so it gets the visual-system upgrade after the two new builds.

---

## Key Findings

1. **The product's hardest UI problem isn't density — it's honesty.** The brief bans verdict language and demands first-class uncertainty, but most fantasy tools (KeepTradeCut's "Keep / Trade / Cut," Dynatyze's "A–F" grades, FantasyPros' "fair/win/loss") do exactly what's banned. There is no incumbent to imitate. The closest references are forecasting outlets (FiveThirtyEight 2018+, Silver Bulletin, Bank of England) and dataviz research (Hullman, Kay, Padilla) — all from outside fantasy.

2. **Frequency-framed uncertainty beats density plots and error bars.** Empirically, quantile dotplots and hypothetical outcome plots (HOPs) produce better decisions than error bars or violin plots (Fernandes, Walls, Munson, Hullman & Kay, "Uncertainty Displays Using Quantile Dotplots or CDFs Improve Transit Decision-Making," CHI 2018, doi:10.1145/3173574.3173718; Kale, Nguyen, Kay & Hullman, "Hypothetical Outcome Plots Help Untrained Observers Judge Trends in Ambiguous Data," IEEE TVCG / Proc. InfoVis 2019, doi:10.1109/TVCG.2018.2864909). Quantile dotplots are the right primary uncertainty primitive for Dynasty Genius — better than fan charts for a sophisticated user, because fan charts hide the discreteness the model actually produces (Padilla, Kay & Hullman, "Uncertainty Visualization," ch. 22 in *Computational Statistics in Data Science*, Wiley, 2022).

3. **The cone-of-uncertainty failure mode is the central UX risk.** The NHC's hurricane cone, per Brian McNoldy of the University of Miami Rosenstiel School (Feb 2024): *"Right from the start, the primary criticism of the cone was that it gave people the wrong impression that it indicated threat — if you're inside of the cone you're in trouble, and if you're outside of it, you're fine. But that is not at all what it is designed to indicate and is a dangerous misinterpretation."* Any single-number divergence indicator in Dynasty Genius ("model says +12 vs market") risks the same misread: users binarize a continuous, conditional signal. The system must make the conditioning visible, not just the gap.

4. **FiveThirtyEight's 2018 redesign is the most relevant single precedent.** They removed the "Now-cast" percentage that readers had misread as a forecast and replaced it with a probability bar graph that, as Theatre Journal's December 2018 review notes, *"underscores the scientific nature of data analysis rather than offering the desirable, but more subject-to-interpretation glimpse into the future."* Dynasty Genius should similarly refuse single-number verdicts in favor of probability/range presentations.

5. **The visual language has a clear inheritance.** Linear's design (Inter / Inter Display per Linear's own engineering post; 8px-base spacing per LogRocket's analysis; restrained dark theme over Radix primitives under a private "Orbiter" design system, confirmed by Linear's team on the Radix UI case study page: *"We started using Radix Primitives for some parts of our design system—Orbiter—which is used in Linear's web and desktop applications"*) plus Bloomberg's "conceal complexity" principles (Bloomberg CTO Shawn Edwards: *"We're hiding complexity… across thousands of functions, across domains and asset classes"*) plus Tufte's data-ink discipline give a coherent, citable lineage. The aesthetic to *avoid* is the generic glass-card "AI app" look — saturated gradients, oversized hero numbers, soft pastels.

6. **The right tech stack for this owner is server-rendered, not SPA.** Astro's own docs put dashboards explicitly in the *other-framework* bucket: *"Astro was designed for building content-rich websites… By contrast, most modern web frameworks were designed for building web applications. These frameworks excel at building more complex, application-like experiences in the browser: logged-in admin dashboards, inboxes, social networks, todo lists."* (Astro docs, *Why Astro?*). And TestDriven.io's HTMX course is candid: *"It's lightweight — although you can do a lot with such a small library, if you need a full-scale client-side heavy app, HTMX won't be able to replace React or such."* Dynasty Genius sits in a sweet spot: mostly read-heavy with one interactive surface (Trade Lab). HTMX + Alpine handles 6 of 7 surfaces cleanly; Trade Lab is the one to watch.

7. **Observable Plot is the right chart library — uniquely.** Plot has native faceting (small multiples), native `quantile` and `threshold` color scales, and is framework-agnostic vanilla JS, so it slots into HTMX-rendered DOM containers without owning the DOM. Recharts and Visx are React-only; ECharts has the marks but heavy config; D3-direct is too low-level for a learning developer. As Eli Holder writes at 3iap: *"It's super quick and relatively mindless to crank out 'good enough' charts and graphs. If you need something fancy, d3 is still a reasonable bet, but for basic bar graphs, line charts, distributions, etc., it [Plot] does the trick with minimal fuss."*

---

## Details

### Part I — Product Soul: Three Hard UX Commitments

Before any component spec, three commitments must be enforced at the design-system level, not as ad-hoc copy decisions on individual screens:

**1. The "Decision Card" contract.** No screen shows a recommendation without four mandatory fields rendered together: *signal*, *uncertainty range*, *strongest counter-argument*, *applicable horizon* (dynasty vs. redraft, contender vs. rebuild). If any field is empty for a given player/decision, the card is automatically rendered in the **Experimental** treatment. This makes it physically impossible to ship a confident-looking surface that lacks a counter-argument.

**2. The "Two Lane" contract.** Model and Market are *never* in the same visual container. They live in side-by-side panes with their own headers, units, and colors (model = teal/blue, market = amber/orange — see palette below). Divergence is shown as a *third* derived element ("model 14% higher than market, inside normal range for rookie WRs"), never by blending values. This mirrors how Bloomberg keeps consensus estimates separate from a firm's own estimate, and how FiveThirtyEight 2020 kept polling averages visually distinct from forecast probabilities.

**3. The "Experimental" treatment.** Any surface flagged "not decision-supported" must be expressed by a consistent visual treatment, not just a footnote. The treatment: (a) a 4px dashed left-border in a desaturated amber, (b) a small `EXPERIMENTAL — calibration unverified` chip above the title, (c) all numbers rendered in a muted weight (`color-mix(in oklab, var(--fg) 70%, transparent)`), (d) a permanent expandable "Why experimental?" disclosure block at the bottom. Roster Audit, Waiver Radar, and League Pulse all begin in this treatment until the Backtest surface earns them out.

These three commitments do more work than any palette or component spec. They make honesty structurally enforced rather than disciplinarily aspired to.

---

### Part II — Visual Design Language (Pillar A)

#### Reference imagery analysis

- **Bloomberg Terminal.** Concealed complexity through dense, color-coded grids with monospaced numerics, persistent global command line, and persistent function navigation (Bloomberg UX team: hiding complexity across thousands of functions for a seamless user journey). Adopt: dense tabular displays, persistent global search ("⌘K"), monospaced tabular numerics, restrained palette where color carries semantic load (not decoration). Avoid: orange-on-black amber clichés — that's costume, not function.

- **Linear.** Inter / Inter Display, 8px spacing scale, restrained dark theme, Radix primitives under a private "Orbiter" design system. Adopt: type stack, spacing scale, the *discipline* of having a small number of tokens with semantic names. Avoid: copying Linear's purple — Dynasty Genius needs its own model/market color pair.

- **Stripe Sigma.** Embedded analytical surface inside a transactional product, leaning on a SQL+template+chart model. The relevant pattern is the "query → table → chart" pipeline as a single workflow: results have to be both auditable (you can see the rows) and visualizable (you can see the shape). Adopt for Research Assistant: tabular result is the primary artifact, charts are derived.

- **FiveThirtyEight 2018+ / Silver Bulletin.** The shift from a single big "Now-cast" percentage to probability bars with explicit uncertainty was driven by 2016 misreads. Adopt: refuse a single hero verdict number; render distributions or ranges as the primary recommendation surface.

- **Bank of England fan charts.** Two-piece normal fan with widening bands for longer horizons. *Adopt selectively* — fan charts are good for time-projected veteran decay / pick appreciation curves but problematic as the primary uncertainty primitive. Ben Bernanke's April 12, 2024 review *"Forecasting for Monetary Policy Making and Communication at the Bank of England"* (Recommendation 11) concluded that fan charts *"have weak conceptual foundations, convey little useful information over and above what could be communicated in other, more direct ways, and receive little attention from the public,"* and Governor Andrew Bailey subsequently signaled the Bank would likely retire them in favor of scenario analysis. Use fan charts for *time* uncertainty (the X axis is years), quantile dotplots for *point* uncertainty (a single estimate).

- **Tufte / Wilke / Knaflic.** Maximize data-ink ratio (Tufte, *The Visual Display of Quantitative Information*); small multiples for cross-position and cross-player comparison; reduce chartjunk; Gestalt enclosure/proximity for grouping without borders (Knaflic, *Storytelling with Data*). Wilke's chapter on uncertainty (*Fundamentals of Data Visualization*, ch. 16) is the operating manual for the Backtest surface.

#### Design tokens

**Typography.**
- Sans: **Inter** (UI), **Inter Display** (titles ≥ 18px). Both via local woff2 — no Google Fonts network dependency, consistent with local-first.
- Mono: **JetBrains Mono** for tabular numerics and IDs. Critical: all numbers in tables use `font-feature-settings: "tnum"` so columns of digits align.
- Scale (px): 11 caption, 13 body-sm, 14 body, 16 body-lg, 18 title-sm, 22 title, 28 title-lg, 36 hero. Line-height 1.4 for body, 1.2 for titles.

**Spacing.** 8px base, with 4px half-step for icon padding and table cell vertical padding only. Tokens: `--space-1` = 4px, `--space-2` = 8px, `--space-3` = 12px, `--space-4` = 16px, `--space-6` = 24px, `--space-8` = 32px, `--space-12` = 48px. Nathan Curtis's *"8pt linear scale for elements with a 4pt half step for spacing icons or small text blocks"* (EightShapes) is the explicit precedent.

**Color (dark-first; light is a secondary mode, not the default).** Tokens use semantic names à la shadcn/ui (a portable token convention — shadcn's component layer is React-only, but its CSS-variable approach ports cleanly to Jinja). All colors specified in OKLCH for perceptual uniformity.

- `--bg-base` #0B0D10, `--bg-raised` #14171C, `--bg-overlay` #1B1F26.
- `--fg-primary` #E6E8EC, `--fg-secondary` #A0A5AE, `--fg-muted` #6B7280.
- `--border-default` #232830, `--border-strong` #3A4150.

**Semantic two-lane palette.** The single most consequential color decision:
- **Model lane:** `--model-fg` teal-blue #4FB8C7, `--model-bg` rgba(79,184,199,0.10).
- **Market lane:** `--market-fg` amber #D9A23A, `--market-bg` rgba(217,162,58,0.10).
- These two colors are reserved. They appear *only* when model or market data is on screen, never for decoration. A user trained on this palette can recognize the two lanes in their peripheral vision.

**Divergence colors.** Diverging scale on a third axis so it doesn't compete with model/market:
- `--div-positive` (model higher than market) muted green #6FAE7E
- `--div-negative` (model lower than market) muted rose #C97B6F
- `--div-neutral` (inside normal range) `--fg-muted`. The user must read text to interpret; color is a hint, not a verdict — this is the explicit defense against the cone-of-uncertainty failure mode.

**Risk / experimental.**
- `--exp-accent` desaturated amber #B8902F for the experimental dashed border and chip.
- `--risk-low` `--fg-muted`, `--risk-mid` #D9A23A, `--risk-high` #C97B6F. Used only on labeled risk flags, never as a background fill.

**Density.** Default row height 32px (Bloomberg-dense), comfortable mode 40px (toggle in settings). Tables max 12 columns visible; overflow goes to a horizontal scroll lane with the player-name column sticky-left (a Linear/Notion table pattern).

---

### Part III — Component Inventory

Components specified at API + states level. All components live in a single Jinja macros file (`components.html`) with matching Tailwind utility classes — no JS framework component model required.

**1. Decision Card** (canonical). Slots: `signal` (top), `uncertainty-range` (right), `key-drivers` (3-bullet max), `counter-argument` (mandatory, dedicated block with `--div-negative` left border), `caveats` (chip row), `horizon` (dynasty / redraft toggle, defaults dynasty), `as-of` timestamp. States: *default*, *experimental* (dashed border, muted weights), *insufficient-data* (signal + uncertainty replaced by "model declines to call this," counter-argument still renders), *stale* (timestamp red if > 7 days old).

**2. Two-Lane Comparison Panel.** Two equal-width panels, left = model, right = market. Each has its own header, value, percentile, and sparkline. A 1px center divider in `--border-strong`. Below the two panels, a single neutral-language divergence string: *"Model 14% higher than market — inside normal range for rookie WRs with this draft position."* No buy/sell verbs. States: *both available*, *model only* (right pane shows "market comparison unavailable"), *market only* (left pane reads "model declines to value — see why"), *both stale*.

**3. Player Row** (table primitive). Columns: name (sticky), position chip, age, model value, market value, divergence chip, 3-yr trajectory sparkline, risk chip(s). Hover reveals a small popover with 2-line counter-argument. Click opens the shared Player Detail drawer (right-side slide-in, not a full route).

**4. Quantile Dotplot** (uncertainty primitive). 20 dots in a 4×5 grid representing the model's predictive distribution as discrete frequency-framed outcomes. Reading: "of 20 equally plausible futures, 3 see this player as a top-12 WR." Empirically the best-performing frequency-framed display for decision-making, per Fernandes, Walls, Munson, Hullman & Kay (CHI 2018), which reported that "quantile dotplots yielded better decisions" than no-uncertainty controls. Implemented as a single Observable Plot `dot` mark.

**5. Hypothetical Outcome Plot (HOP)** — *optional secondary*. Animated 1Hz cycling through 8–12 sampled outcomes. Hullman, Resnick & Adar, "Hypothetical Outcome Plots Outperform Error Bars and Violin Plots for Inferences about Reliability of Variable Ordering," *PLoS ONE* 10(11): e0142444 (Nov 16, 2015) established the original finding; Kale, Nguyen, Kay & Hullman (IEEE TVCG 2019) extended it to trend-judgment tasks. Use sparingly — Trade Lab's "what could this trade look like in 3 years" view is the natural fit, but the static quantile dotplot remains primary; HOPs are for narrative animations on hover.

**6. Aging Curve Mini-Chart** (sparkline variant). 60×24px inline chart showing the player's modeled value trajectory ±2 years from current age, with a vertical "today" marker. WRs/QBs render relatively flat; RBs render with a visible cliff. References the empirical finding that RB peak age averages 25.46 vs. WR 26.95 with RBs *"1.5 years shorter at every stage of the career arc"* (Apex Fantasy Leagues age-curve study, March 2026).

**7. Divergence Chip.** Inline label: `M>K +12%` (model higher than market by 12%) with `--div-positive` background tint. On hover, expands to full neutral sentence. States: *positive*, *negative*, *neutral* (`Inside normal range`), *unavailable* (`Market data N/A`). Critically: chip never says "BUY" or "SELL" or "TARGET."

**8. Counter-Argument Block.** A dedicated typographic block, not a footnote. Renders as a left-bordered (`--div-negative`, 3px) paragraph with a small `▽ COUNTER` label, followed by 1–3 sentences of structured opposing case (e.g., *"Counter: the model's confidence depends heavily on 2024 target share, which is volatile under coach turnover. If Detroit moves to a committee approach, the 3-yr forecast drops by ~22%."*). Required on Decision Card; recommended elsewhere.

**9. Caveat Chips.** Small pill-shaped chips below a recommendation: `Small sample`, `Coach change`, `Injury recent`, `New scheme`, `<2 years data`. Color: `--fg-muted` border with no fill — they don't compete visually but are always present when applicable.

**10. Experimental Frame.** Wrapper component (not a card). Adds the 4px dashed border, EXPERIMENTAL chip, muted treatment, and disclosure block to any container. Implemented as a Jinja macro `{% call experimental("Roster Audit") %}…{% endcall %}`.

**11. Trust Strip** (global). A 24px horizontal strip at top of the app showing: data freshness ("Stats: 2h ago · Market: 8m ago · Model: 14h ago"), model version ("v0.4.2 — backtest: rookie cohort 2018–2024 only"), and a single-letter status (G/A/R) for the current surface based on the backtest pane. Always visible.

**12. Empty / Loading / Unavailable.** Three distinct states, never collapsed into one:
- *Empty* (no data exists yet): structured prompt explaining what's missing.
- *Loading*: skeleton matching final layout (no spinners — they imply progress that may not exist).
- *Unavailable* (data should exist but doesn't this run): explicit "Why" link to a diagnostics page. Never silently shows "—".

**13. Global Command (⌘K) palette.** Single shortcut opens a fuzzy-search palette over players, picks, surfaces, and league rivals. Bloomberg-Terminal-style direct navigation; eliminates need for deep menus.

---

### Part IV — Information Architecture & Navigation (Pillar B)

#### Sitemap

```
/                          → Home (League Pulse summary + Trust Strip + recent decisions)
/rookies                   → Rookie Board (compare-many)
/rookies/:player_id        → Player Detail (shared drawer, also addressable)
/trade                     → Trade Lab (builder)
/trade/saved/:trade_id     → Saved trade scenario
/roster                    → Roster Audit (EXPERIMENTAL frame)
/waivers                   → Waiver Radar (EXPERIMENTAL frame)
/league                    → League Pulse (rival rosters, surplus/deficit map)
/league/:owner             → Owner detail (their roster, your trade-fit lens)
/backtest                  → Backtest / Trust Surface
/research                  → Research Assistant (saved questions, ad-hoc query)
/research/q/:question_id   → Saved research thread
/admin/data                → Data freshness + diagnostics (one click from Trust Strip)
```

#### App shell

Three persistent regions:
1. **Top bar (48px):** League name, current week, ⌘K global search, settings.
2. **Trust Strip (24px):** Data freshness + model version + current-surface trust indicator.
3. **Left nav (200px collapsible):** Vertical nav over the 7 surfaces, with a 32px-tall "League Context" block at bottom showing: my record, contender/rebuild posture toggle, pick inventory count.

This is Linear's inverted-L plus a Bloomberg-style status strip. The shell never goes away; surfaces render into the main content region.

#### Cross-cutting decisions

- **Player Detail is a slide-in drawer**, not a route. Opens from any player row, anywhere. Has its own URL hash so it's bookmarkable. Closes back to context. This is the key "many vs. one" pattern: you stay in your comparison list while inspecting one player.
- **League context (roster, picks, posture) is always visible** in the left nav block. Trade Lab and Roster Audit additionally show it as a contextual right rail.
- **Global search (⌘K)** unifies player, pick, rival owner, and saved-research lookup. No nested menus.
- **No tabs inside tabs.** If a surface has more than two views, they go in a top segmented control with at most 4 segments.

#### Primary user flows

*Rookie Pick (mid-draft, time-pressured):*
1. From Home or via ⌘K → `/rookies`
2. Default view: ranked rookie list with model value, market value, divergence chip, position chip, college risk chip
3. Filter by position; sort by model value
4. Hover top 3 candidates → counter-argument popovers
5. Click chosen player → drawer with quantile dotplot, aging curve, comparables
6. Decision: close drawer, mark drafted (logs to local "decisions" table for later backtest)

*Trade Evaluation (received offer):*
1. ⌘K → "Trade Lab"
2. Build offer: add my-assets and their-assets via player search
3. Live: model value totals (two boxes), market value totals (two boxes), forced-cut warnings if my roster spots would overflow
4. Center column: per-asset comparison rows, asset-by-asset divergence chips
5. Right column: neutral-language insights ("4-for-1 deals historically deliver 60% of nominal value to the receiving side — flag")
6. Decision: save scenario, no auto-verdict. Counter-argument block mandatory.

*Roster Review (off-season):*
1. ⌘K → "Roster Audit"
2. EXPERIMENTAL frame visible
3. Default view: positional surplus/deficit map (small multiples by position) with team's contender-now vs. future-value tilt
4. Per-player rows show holds vs. develop vs. depth-stash *as descriptive labels, not imperatives* ("Aging 30+, on declining curve" — not "SELL NOW")
5. Click into player → drawer with 3-yr fan chart and quantile dotplot for next-year production

*Waiver Scan (Tuesday morning):*
1. ⌘K → "Waiver Radar"
2. EXPERIMENTAL frame visible
3. Ranked by model-projected value-over-replacement next 12 weeks
4. Each row has usage signal chips (target share, snap %, route participation)
5. Counter-argument popover on hover for top candidates

---

### Part V — Decision-UX & Trust/Uncertainty Visualization (Pillar C — the differentiator)

#### The Canonical Decision Card (annotated spec)

```
┌─────────────────────────────────────────────────────────────────┐
│  Player Name  ·  WR ·  DET ·  age 23.4                          │
│  Dynasty   [• Dynasty / Redraft]                                │
│─────────────────────────────────────────────────────────────────│
│  MODEL                            MARKET                         │
│  Value: 8,420 (P78 cross-pos)     Value: 7,950 (KTC)             │
│  3-yr forecast: 24.3 PPG ±3.1     Mkt 14-day: ↑ 4.2%             │
│  [quantile dotplot, 20 dots]      [sparkline 90d]                │
│                                                                  │
│  Divergence: Model 6% higher than market — inside normal         │
│  range for 23 y.o. WRs with 800+ target-share-adj snaps.         │
│─────────────────────────────────────────────────────────────────│
│  KEY DRIVERS                                                     │
│  • Top-decile target share in age-22 season                      │
│  • Receiver-friendly scheme retention y/y                        │
│  • Quarterback environment stable through 2027                   │
│                                                                  │
│  ▽ COUNTER                                                       │
│  Model leans heavily on 2024 target share, which historically    │
│  regresses ~20% when an OC changes. If DET coordinator moves     │
│  this offseason, 3-yr forecast drops to ~21.0 PPG.               │
│                                                                  │
│  CAVEATS                                                          │
│  [Small sample] [<3 yrs data] [Position scheme volatility]       │
│─────────────────────────────────────────────────────────────────│
│  Data as of 2026-05-25 14:02 · Model v0.4.2 · Trust: B           │
└─────────────────────────────────────────────────────────────────┘
```

What this card does *not* contain, by hard constraint: no verdict word, no buy/sell, no tier letter, no "fair/win/loss," no confidence percent that derives from draft slot, no recommendation imperative.

#### Uncertainty visualizations: which when

Drawing on Wilke (*Fundamentals of Data Visualization*, ch. 16) and Padilla, Kay & Hullman ("Uncertainty Visualization," ch. 22 in *Computational Statistics in Data Science*, Wiley, 2022):

- **Quantile dotplot (20 dots): primary.** For any single-point estimate with uncertainty (player value, projected PPG, trade balance). Always 20 dots — preserves the "frame of 20 plausible futures" mental model across the app.
- **Fan chart: time projections only.** For multi-year forecasts (pick appreciation curves, veteran decay curves). 50/80/95% bands, two-piece normal. *Never* the primary uncertainty primitive — Bernanke's 2024 review of the Bank of England recommended retiring fan charts as central uncertainty displays, citing their "weak conceptual foundations."
- **Hypothetical Outcome Plot (HOP): narrative on hover.** Animated sampling, 1Hz, 8–12 frames. For Trade Lab "what could this trade look like in 3 years" hover-card only. Stop animation on hover-out — HOPs cost attention; reserve for moments where the user is *choosing* to look.
- **Sparklines (Tufte, *Beautiful Evidence*): contextual.** Inline 60×24px line in tables, 90-day market sparkline next to market value, 60-month aging-curve next to age. No axes; show shape, not magnitude.
- **Cone/range *avoid as primary*.** The NHC cone-of-uncertainty's misread failure (per McNoldy: users believed "if you're inside of the cone you're in trouble, and if you're outside of it, you're fine") is exactly the failure mode any binary divergence indicator must avoid.

#### Model-vs-Market two-lane spec

Three rules, enforced at the component level:
1. **Spatially separated.** Two side-by-side panels with a 1px center divider. Never overlay them on the same axis — that's what KeepTradeCut's chart-blender-style sites do, and it makes divergence invisible.
2. **Color-coded.** `--model-fg` and `--market-fg` reserved for the lanes — never used for decoration. A user develops peripheral recognition.
3. **Divergence is a derived third element** with neutral phrasing: *"model X% higher/lower than market — inside / outside normal range for [cohort]."* The cohort comparison is critical: a 14% divergence on a 23-year-old WR is normal; the same 14% on a 29-year-old RB is large. Always include the cohort or say "no comparable cohort."

#### Time-horizon visibility

Every value in the app carries an implicit horizon. Make it explicit:
- A persistent **Dynasty / Redraft toggle** in the player detail drawer.
- The aging-curve sparkline always shows ±2 years from current age, so veteran decay vs. pick appreciation is visible inline.
- The pick-inventory block in the left nav shows pick year next to value so the user feels rookie-pick appreciation over time.
- Trade Lab has a **horizon control** (1, 3, 5 years) that re-renders the per-asset model value; the same trade can look balanced at 1 year and lopsided at 5.

---

### Part VI — Tech Stack Recommendation (with full trade-offs)

#### Stack chosen: **FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind CSS + Observable Plot**

No Node build pipeline for the default path. Tailwind via the standalone CLI binary (single Go-native executable that produces a single CSS file from your HTML). Observable Plot loaded as a single `<script type="module">` import map.

**Why this stack over the alternatives:**

| Option | Verdict | Reasoning |
|---|---|---|
| **Stay zero-dep static HTML** | Reject | Already shows strain — no component reuse, no consistent tokens, no way to enforce the Decision Card contract across surfaces. The brief explicitly worries about maintainability across 7 surfaces. |
| **React / Next.js** | Reject | Wrong shape for the problem: one user, mostly read, FastAPI already serves JSON. Build-pipeline tax, framework churn, more concepts (hooks, hydration, server vs. client components) for a solo learning-developer. Bundle size unjustified. |
| **Svelte / SvelteKit** | Reject | Same shape mismatch as React but smaller community + smaller charting ecosystem. Worth less than React's larger ecosystem if you're going SPA anyway. |
| **Vue / Nuxt** | Reject | Same. No specific advantage over React for this case. |
| **Astro + islands** | Reject (close call) | Astro's own docs put "logged-in admin dashboards" in the *other-framework* bucket. TutorialsPoint's Astro guide is explicit: *"the island architecture is not ideal for highly interactive applications like online tools, dashboards, etc."* Trade Lab would be unhappy. Reasonable for a content-rich personal site; not for an analytical workstation. |
| **FastAPI + HTMX + Alpine + Plot (CHOSEN)** | Accept | Single mental model (server returns HTML). FastAPI already there. Plot is framework-agnostic and slots into HTMX-rendered containers. Tailwind tokens portable from shadcn convention. One language for backend + templates + light JS. The TestDriven.io caveat *"if you need a full-scale client-side heavy app, HTMX won't be able to replace React"* is the right warning to take seriously — hence the escape hatch below. |

**Escape hatch — single React island via Vite, if needed.** If Trade Lab's interactive multi-asset builder proves too painful in Alpine (specifically: live drag-and-drop reordering with cross-asset state, undo/redo, optimistic updates on a complex object graph), build *only Trade Lab's center column* as a standalone React component mounted into a `<div id="trade-builder">` placeholder. Vite-build into a single `trade-builder.js` bundle. Keep the rest of the app HTMX. This is a documented, single-surface concession — not a stack pivot.

**Trade-offs honestly stated:**
- **Risk:** No named precedent combines HTMX + Alpine + Observable Plot for 7 dashboards of small multiples. You'll be on novel ground integrating Plot into Jinja partials. Mitigation: Plot's vanilla-JS API is small; the integration is `Plot.plot({...}).appendTo(el)` — there's no framework owning the DOM.
- **Risk:** Cross-component state in Alpine (e.g., a Trade Lab where adding a player on the left updates totals on the right and warnings at the top) gets ugly with `$store`. Mitigation: use Alpine's `$store` for global state; if it gets > ~300 lines, that's the signal to extract to a React island.
- **Risk:** TypeScript is harder to retrofit. Mitigation: use JSDoc type annotations in plain `.js` files; TypeScript can check without compiling. Skip TS unless an island grows large.

**Tailwind v4 + shadcn-style tokens** for the design system. Tailwind v4 has CSS-variable-first theming, which means the entire palette above can live in `:root { --color-bg-base: ... }` and Tailwind utility classes resolve at runtime — no preprocessing needed. shadcn's component layer is React-only and won't apply, but the *token convention* (`--background`, `--foreground`, `--muted`, `--border` etc.) is portable and clean. As the shadcn handbook puts it: *"shadcn/ui uses CSS variables as design tokens instead of hard-coded values. Components rely on semantic variables like --background, --foreground, --primary, --muted, and --border. These tokens represent meaning, not specific colors."*

#### Migration path from current static dashboards

**Stage 0 — Foundation (≈1 week).** Create `/templates/components.html` with Jinja macros for every component above as empty shells. Define `/static/tokens.css` with all color/typography/spacing tokens. Add Tailwind standalone binary + `tailwind.config.js`. Add HTMX (16KB) and Alpine.js (15KB) via `<script>` tags. No new endpoints yet.

**Stage 1 — Trade Lab full build (≈3 weeks).** Build Trade Lab end-to-end against the just-shipped backend, using all canonical components. This is where the visual language gets battle-tested.

**Stage 2 — Backtest / Trust Surface (≈2 weeks).** Without this, every other surface ships unearned authority. Includes calibration-by-cohort plots, model-vs-market backtest tables, "where the model has earned out" cohort matrix.

**Stage 3 — Rookie Board upgrade (≈1 week).** Migrate the existing surface to the new component system. Cheap because the analytical work is already mature.

**Stages 4–6 — Roster Audit, Waiver Radar, League Pulse (≈2 weeks each, all in EXPERIMENTAL frame).** Build to architectural completeness; defer fine-grained UX polish until backtest justifies decision-grade treatment.

**Stage 7 — Research Assistant (≈1 week).** Last because it's the most freeform; benefits most from having the rest of the system stable.

---

### Part VII — Phased Build Roadmap (deepest on Trade Lab + Rookie Board)

#### Trade Lab — full architectural spec (immediate first target)

**Layout: three columns + top bar.**
- **Top bar (sticky):** Two big number panes — `MY TOTAL` and `THEIR TOTAL`, each split into a Model value and a Market value (two-lane). Below each: a `Forced-cut cost` indicator if accepting the trade would overflow roster slots.
- **Left column (~30%):** "Their side" — list of assets they're sending, each as a Player Row with model value, market value, divergence chip, and an X to remove. A "+ Add asset" affordance opens an inline player search.
- **Center column (~40%):** Per-asset comparison rendered as a small-multiples table: one mini-comparison per row, with model contribution, market contribution, age, position, and a 60×24 aging-curve sparkline. The asset rows pair across sides where possible (e.g., "your RB23 vs. their RB17 + 2027 2nd"). Below the table, a single neutral-language **Realism warning** block: *"You are sending 4 assets to receive 1. Historically, the receiving side of 4-for-1 deals captures ~60% of nominal value. This is advisory, not a verdict."* — exactly the brief's "many-for-one realism warning."
- **Right column (~30%):** "Your side," mirror of the left.

**Below the columns: Decision Card** with:
- *Signal:* model says deal is X% in your favor (neutral phrasing), market says Y%
- *Uncertainty:* quantile dotplot showing the distribution of 3-year model outcomes for net team value gain/loss
- *Key drivers:* top 3 most-influential assets
- *Counter-argument:* mandatory — populated either by the system (positional surplus you're losing) or by you (free-text override the user can write and save)
- *Caveats:* chips for any asset with `<2 yrs data`, recent injury, scheme volatility, etc.

**Horizon control:** 1 / 3 / 5-year toggle re-renders model values across all panes. This is where the "picks appreciate, veterans depreciate" insight becomes visceral — a contender-favoring trade at 1 year often inverts at 5.

**Saved scenarios:** Trade Lab maintains a local `/trade/saved/:id` list. Each saved scenario is replayable; users can revisit a trade they declined in 6 months and see how it would have played out (this is also data for the Backtest surface).

**Why this is build #1:** The backend just shipped, so the work is purely UI; Trade Lab is the most common high-stakes decision a dynasty owner makes; and it forces the entire component library (decision card, two-lane comparison, quantile dotplot, counter-argument, caveat chips, divergence chip, aging-curve sparkline, forced-cut indicator) into existence on a single surface.

#### Rookie Board — full architectural spec (build #3, visual upgrade)

**Layout: two-pane (compare-many + inspect-one).**
- **Left pane (~60%):** Ranked rookie list as a dense table — name (sticky), position, college, model value, model rank, market value, market rank, divergence chip, college-production sparkline, athleticism chip, scheme-fit chip. Sortable on any column. Filterable by position. Default sort: cross-positional model value. Row height 32px (Bloomberg-dense); user can toggle 40px comfortable.
- **Right pane (~40%):** Player Detail for the selected rookie (also openable as a route for sharing). Contains:
  - Two-Lane comparison panel
  - Quantile dotplot for projected year-3 PPG
  - Aging curve mini-chart (most rookies render with appreciating-then-flat curves, but RBs show the early cliff)
  - Three nearest comparables from the historical training set (e.g., "closest comparables in 2018–2024 cohort: [Player A] hit, [Player B] mid, [Player C] miss")
  - Counter-argument block (e.g., "Counter: 70% of rookies with this draft slot/college profile bust by year 3 — comparables include [Player C, Player D]")
  - Caveat chips

**Header strip:** Filter by position; toggle 1QB/Superflex; toggle PPR/half/standard; toggle "TE premium." All controls produce instant filter without a page reload (HTMX `hx-get` swapping just the table body).

**Banned patterns enforced:** No tier letters ("Elite/Strong/Bust"). No confidence percentages derived from draft slot. No "BPA" verdict label — instead, a neutral "cross-positional rank" column.

**Why this is build #3, not build #1:** Rookie Board's analytical model is the most mature, but the existing surface is already functional. Trade Lab and Backtest both need to ship first to establish the component system and earn the trust the Rookie Board's polish would otherwise be wasted on.

#### The other five surfaces (architectural sketches)

**Roster Audit (EXPERIMENTAL):**
- Default view: positional surplus/deficit map — small multiples by position (QB/RB/WR/TE), each panel showing your roster's value-by-age distribution vs. league median.
- Player table with descriptive labels (`Aging 30+, declining curve` — not "SELL"), grouped by age cohort and trajectory.
- Drawer reuses Player Detail.
- Stays EXPERIMENTAL until Backtest validates the audit logic.

**Waiver Radar (EXPERIMENTAL):**
- Ranked list of available players by 12-week model VORP.
- Usage signal chips per row (snap %, target share, route participation, red-zone touches).
- Counter-argument popovers on hover for the top 10.
- EXPERIMENTAL until usage signals are backtested.

**League Pulse:**
- Top section: surplus/deficit map across all 12 rosters, small-multiples grid (12 mini panels).
- Per-rival roster view (click into) showing their roster valued by your model and market, with a "trade-target fit" lens — players where your need overlaps their surplus.
- No EXPERIMENTAL framing; this is read-mostly aggregation.

**Backtest / Trust Surface (BUILD #2 — credibility layer):**
- Calibration-by-cohort plots (model's predicted vs. actual rank by position, age band, draft round).
- Model-vs-market backtest: where has model beaten the market historically? Cohort matrix.
- Per-surface "trust earned" indicators that the Trust Strip reads from.
- No EXPERIMENTAL framing — this surface *defines* what earns out.

**Research Assistant:**
- Saved-question thread interface (Stripe Sigma–style query → table → chart pipeline).
- Each saved thread has a question, a structured query payload (positions, age, draft round, etc.), a table result, and optional chart.
- Ad-hoc player lookup as the entry point.

---

## Recommendations

**Immediate next steps (in this order):**

1. **Week 1: Lock the tokens.** Build `tokens.css` with the full palette, typography, and spacing scale. Build `components.html` with empty Jinja macros for the 13 components above. Pin Tailwind v4 standalone binary + HTMX 2.x + Alpine 3.x + Observable Plot via import map. Commit a screenshot of the Decision Card empty shell to lock the contract.

2. **Weeks 2–4: Trade Lab full build.** Top bar → Left/Right asset columns → Center comparison table → bottom Decision Card → horizon control → saved scenarios. Force every component above into existence on this surface.

3. **Weeks 5–6: Backtest surface.** Without this, Trade Lab's authority is unearned. Build calibration-by-cohort visualizations + per-surface trust indicator wiring into the global Trust Strip.

4. **Week 7: Rookie Board visual migration.** Cheap because the analytical work is mature.

5. **Weeks 8–13: Roster Audit, Waiver Radar, League Pulse, Research Assistant** at architectural depth, all starting in EXPERIMENTAL framing.

**Benchmarks that would change the recommendation:**

- *Tailwind/HTMX/Alpine hits a wall:* If Trade Lab's interactive complexity in Alpine exceeds ~300 lines of `$store`-based state, extract Trade Lab's center column into a single React-via-Vite island. **Do not** pivot the whole stack.
- *Plot can't draw a needed chart:* If a specific surface needs a chart type Plot lacks (unlikely — Plot has the marks for everything specified), drop to vanilla D3 for that one chart. Plot and D3 share idioms.
- *Backtest reveals the model isn't earning out a surface:* Keep that surface permanently in EXPERIMENTAL framing — the visual treatment is *designed* to support this outcome. This is the most important benchmark: the Trust Surface is allowed to keep surfaces experimental forever.
- *A second user is ever added:* This invalidates the local-first / no-auth premise. At that point, the stack still works but you'll want to add session middleware. Don't pre-build for this.

**Things to refuse, even if they feel valuable:**

- A "trade grade" letter or percent, however well-calibrated.
- A "sell now / hold / buy" verb on any player anywhere.
- A blended "Dynasty Genius value" that combines model and market.
- A confidence number derived from draft pick slot (a specifically-called-out banned pattern, and a real failure mode in incumbent tools).
- An "AI assistant" floating chatbot — the brief is explicit about avoiding generic AI-app aesthetics.

---

## Caveats

1. **The brief contains one internal tension worth surfacing.** The brief calls Trade Lab "the immediate first full build target" *and* calls Rookie Board "the most mature surface." Both are true, but they point to different first builds. I've resolved this by recommending Trade Lab first (per the brief's explicit "immediate first full build target") with Rookie Board polished third — but a reasonable reading of the brief would build Rookie Board first to lock the visual system on the most mature data, then Trade Lab. If you weight "validate visual system on mature data" higher than "ship the just-shipped backend," reverse the first and third stages of the roadmap.

2. **The Observable Plot + HTMX integration is novel.** I could not find a named production example combining FastAPI + HTMX + Alpine + Observable Plot for an analytical app — the closest precedents (e.g., Blake Crosley's blakecrosley.com production site, which uses FastAPI + HTMX + Alpine + Jinja2 with no build step) use Chart.js for visualizations rather than Plot. Plot's vanilla-JS API is small and the integration is straightforward in principle, but this is the single highest-risk technical decision in the recommendation. Fallback: ECharts has a similar framework-agnostic API with more docs, at the cost of a heavier, less idiomatic chart vocabulary.

3. **Quantile dotplot interpretation is a learned skill.** The empirical research on quantile dotplots (Fernandes, Walls, Munson, Hullman & Kay, CHI 2018) is on novice users in transit decisions. A sophisticated single user will likely interpret them well, but they're less self-evident than a single point estimate. The Trust Strip's "Trust: G/A/R" letter and the disclosure block under each dotplot ("each dot is one of 20 equally plausible futures") are explicit mitigations.

4. **The "model-vs-market never blend" rule is harder to enforce than it sounds.** The user will probably *want* a blended number eventually ("just tell me what to do"). The architectural answer is the Decision Card's mandatory counter-argument field: the system can produce a directional signal, but it can never produce a signal without simultaneously producing the strongest opposing case. That structure is the design's primary defense against false certainty.

5. **The aesthetic recommendation is opinionated.** Bloomberg/Linear/Stripe Sigma lineage means dark-default, dense, restrained color, monospaced numerics. A user who actually prefers a brighter, more consumer-aesthetic look (à la KeepTradeCut or Sleeper) would find this oppressive. The brief explicitly calls for an analytical workstation feel and warns against consumer-app aesthetics — I've taken that at face value.

6. **Open questions to resolve before Week 1:**
   - What's the exact contract for "model declines to value"? When does the model abstain vs. produce a low-confidence value? This determines how often the "model only / market only / both unavailable" states fire.
   - How is "applicable horizon" defaulted on the Decision Card — always Dynasty, or contextually (e.g., redraft on Waiver Radar)?
   - Does the backtest produce per-surface trust grades or only per-cohort? The Trust Strip's surface-level letter depends on this.
   - Is the historical training set large enough to support cohort-specific divergence-normal bands ("inside normal range for 23 y.o. WRs with 800+ targets") on the Two-Lane panel? If not, simplify to position + age-band cohorts.