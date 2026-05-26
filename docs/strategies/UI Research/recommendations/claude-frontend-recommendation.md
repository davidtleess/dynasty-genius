# Dynasty Genius — Front-End Recommendation (Claude Code)

**Author:** Claude Code (independent agent recommendation)
**Date:** 2026-05-25
**Status:** Independent recommendation for the multi-agent merge. Opinionated and decisive by design; where I synthesize or diverge from the research corpus I say so explicitly.
**Scope:** The whole Dynasty Genius front end — philosophy, tech stack, design system, information architecture, every decision surface, data flow, generative-UI stance, governance enforcement, and build order.

**Inputs read in full:** all 13 markdown docs in `docs/strategies/UI Research/` plus the `Generative UI Research.pdf` (Google Research, *"Generative UI: LLMs are Effective UI Generators,"* Leviathan et al.). Grounded against `00-product-constitution.md`, `01-north-star-architecture.md`, `02-agent-operating-loop.md`, `03-code-hygiene-policy.md`, and current `AGENT_SYNC.md` repo state.

---

## 0. Executive recommendation (TL;DR)

Build **one analytical cockpit, not seven dashboards** — a dark-first, dense, calm "honest terminal" whose entire reason for existing is to show *model vs. market, with uncertainty and a counter-argument*, never a verdict.

1. **Three structural contracts enforce the constitution in code, not in copy:** the **Decision Card** (signal + uncertainty range + mandatory counter-argument + time horizon), the **Two-Lane** model/market separation (never blended), and the **Experimental treatment** (any surface that hasn't earned backtest-grade trust is visibly de-rated). These are the product's soul; everything else is detail.

2. **Tech stack: stay in Python. `FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind (CSS-variable tokens) + Observable Plot`.** No Node build pipeline. One documented escape hatch: a single React-via-Vite *island* for the Trade Lab builder if Alpine state outgrows itself. This is the only stack in the corpus that respects local-first, solo-learning-developer, longevity (no dependency rot), and "frontend comes last." **Reject** the Next.js/React SPA, the Svelte 5 SPA, and — emphatically — the Vercel AI SDK + React Server Components + **Databricks** generative-UI stack (it violates the $10/24-hr Databricks cap, the local-first directive, the "frontend last" gate, and the "no generic AI chatbot" non-goal all at once).

3. **Design system: dark cool-slate canvas, Inter + JetBrains Mono (tabular nums), 8px scale, and a strict two-axis color system** — a *signal axis* (cool blue = model, warm amber = market; **no green/red anywhere**) kept orthogonal to optional *position hues*. Uncertainty is a first-class visual citizen (quantile dotplots primary; fan charts only for time; Morningstar-style bands; opacity decay for low confidence).

4. **Build order:** App shell + component library → Player Card + Roster Audit → **Trust/Backtest surface (the credibility layer)** → Rookie Board → Trade Lab → League Opportunity Map → Settings. Generative UI is a *much-later, additive, David-approved* layer, never the foundation.

5. **The corpus contains real drift I am correcting** (Section 10): an Engine A/B-as-"market" mislabel, DVS-scale confusion (0–100 is correct), invented cliff ages, banned-language self-violations inside the design docs, a `file://` premise that no longer matches the served-FastAPI reality, and placeholder league data. My recommendation is built on the *actual* repo state, not the docs' assumptions.

---

## 1. Product soul: what this front end is (and is not)

The constitution is unambiguous: Dynasty Genius is a **single-user decision-support system** that optimizes to be *right in 3–7 years*, where **frontend polish comes last** and **no surface may imply decision-grade confidence before the model, source freshness, and validation gates justify it.** The corpus is near-unanimous (and correct) that the reference class is *institutional analytical tooling* (Bloomberg's "conceal complexity," Linear's calm chrome, Morningstar/Koyfin/Palantir Foundry, FiveThirtyEight's post-2016 refusal of single-number verdicts), **not** consumer fantasy apps (KeepTradeCut's "Keep/Trade/Cut," tier letters, "Fair Trade" badges).

I adopt three commitments — the framing in *UI Architecture Recommendation* is the strongest in the corpus, and I make it the spine — because each converts a constitutional rule from an aspiration into a **structural invariant**:

- **The Decision Card contract.** No surface renders a recommendation without four co-located, mandatory fields: **signal**, **uncertainty range**, **strongest counter-argument** (steel-manned, per the constitution's Counter-Argument mandate), and **applicable horizon** (dynasty vs. redraft; contender vs. rebuild). If any field is empty, the card auto-renders in the Experimental treatment. This makes it *physically impossible* to ship a confident-looking card without its counter-argument.
- **The Two-Lane contract.** Model (Engine A / Engine B / PVO / xVAR) and Market (FantasyCalc/KTC overlay) are **never in the same visual container**. Divergence is a *derived third element* with neutral, cohort-aware phrasing ("model 14% higher than market — inside normal range for 23-y.o. WRs"), never a blended score. This is the constitution's "market is price discovery, not truth / overlay only" rule made visual.
- **The Experimental treatment.** Any surface not yet earned out by the Trust/Backtest layer carries a consistent visual de-rating (dashed accent border, `EXPERIMENTAL — calibration unverified` chip, muted numerics, a permanent "why experimental?" disclosure). The constitution's `decision_supported = false` (currently true for *everything* per AGENT_SYNC) is rendered as a visible chip, never a hidden flag.

These three do more work than any palette. They are the answer to the single biggest UI risk the corpus correctly identifies: **the slow drift of language and visual treatment back toward consumer-tool conventions.**

---

## 2. Tech stack — the central decision

This is where the corpus genuinely splits, into **four mutually exclusive stacks**. I list them honestly, then choose.

| Stack | Champion doc(s) | Verdict |
|---|---|---|
| Zero-dependency vanilla HTML/CSS/JS over `file://` | the 3 *Design System* docs, *Cockpit Specification* | **Reject as the target** (it's the *current* state; see below). Right instincts (no build, synchronous data arrays) but no component reuse, no shared token/contract enforcement across 7 surfaces, and built on a `file://` premise that no longer holds. |
| Next.js 15 + React 19 SPA (shadcn/Radix/TanStack/Recharts) | *Direction-Cockpit Style* | **Reject.** Wrong shape: one user, mostly-read, FastAPI already serves the data. Build-pipeline tax + framework churn + hydration model = maintenance burden for a solo learning developer, and a long-term dependency-rot liability the constitution's longevity posture argues against. |
| Svelte 5 SPA + LayerCake + shadcn-svelte (Vite build, served by FastAPI) | *UI Architecture Research-GenUI* | **Reject (close-ish).** Lighter than React, but still a Node/Vite build pipeline and a smaller charting/community ecosystem, for benefits a single-user read-mostly app doesn't need. |
| Vercel AI SDK RSC + Databricks Lakehouse online feature stores | *Architectural Blueprint for Generative UI*, the PDF | **Reject hard.** Collides simultaneously with the **$10/24-hr Databricks cap** (the spend memory: ~$1,000 already spent, local-first mandatory), the **local-first** directive, **"frontend comes last,"** and the non-goal **"no generic AI chatbot that bypasses structured decision cards."** Even the corpus's own *Generative UI: Hard Decisions* doc explicitly says **do not use Databricks for a single user** (DuckDB + Parquet local instead) and **do not stream raw JSX**. |

### My choice: `FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind + Observable Plot`

This is the *UI Architecture Recommendation* stack, and after reading everything I am convinced it is correct for this owner and this constitution:

- **It matches reality.** The app is **already** FastAPI (`uvicorn app.main:app`) serving HTML + `resources/*.js`. Jinja2 templating is the smallest possible step up from that, not a rewrite. HTMX (16KB) gives partial-page updates server-side; Alpine (15KB) gives local UI state (toggles, drawers, the Trade Lab builder) — both via `<script>` tags, **no Node, no bundler, no npm**.
- **It enforces governance cheaply.** A single `components.html` Jinja macros file lets the Decision Card, Two-Lane panel, banned-language, and `decision_supported` chip be defined **once** and reused everywhere. The vanilla-`file://` approach can't do this; that's why the *Design System* docs accidentally ship `Buy WR` badges (Section 10).
- **Charts: Observable Plot** (framework-agnostic vanilla JS; native faceting/small-multiples; native `quantile`/`threshold` scales — ideal for the uncertainty primitives) as primary, **ECharts** as the documented fallback if Plot lacks a mark. Avoid Chart.js (too basic for distributions) and Recharts/Visx (React-only).
- **One escape hatch, not a pivot.** If the Trade Lab's interactive multi-asset builder outgrows Alpine `$store` (~300 lines of cross-pane state), build **only the Trade Lab center column** as a single React-via-Vite island mounted into a `<div>` — everything else stays HTMX. Documented, single-surface, reversible.

### Critical correction: the `file://` premise is stale

Four docs (the 3 Design System docs + Cockpit Specification) architect elaborate workarounds for `file://` CORS sandboxing — `FileReader` drop-zones, `localStorage` capability probes, synchronous `<script src>` data arrays. **The current app is served by uvicorn/FastAPI**, so the same-origin sandbox simply does not apply: server-rendered Jinja and HTMX (which require a server) are perfectly viable, and the browser-side `localStorage` Sleeper cache is unnecessary — **the FastAPI backend already owns the Sleeper rate-limit cache.** Keep the *spirit* the docs got right (load critical DOM first, lazy-load market overlays, degrade visibly when stale) and drop the `file://` gymnastics.

---

## 3. Design system

### 3.1 Foundation
- **Dark-first, cool slate canvas** (Radix `slateDark` is a sound, APCA-tuned starting point — the *UI:UX Research & Design System Specification* nails this). Light mode is secondary, not default. Calm chrome / loud signal (Linear's doctrine): the rail and headers recede; only data and warnings carry chromatic weight.
- **Typography:** Inter (UI) + **JetBrains Mono with `font-variant-numeric: tabular-nums`** for every numeric cell — non-negotiable for scanning dense columns. 8px spacing scale, 4px half-step. Carbon `body-compact-01` rhythm (14/18) for dense tables.
- **Density:** ~32px default row height (Bloomberg-dense), comfortable toggle to 40px. Data-ink discipline (Tufte): grouping by proximity and weight, not borders/zebra-stripes.

### 3.2 Color — resolving the corpus's biggest inconsistency

The docs propose at least six different model/market palettes (slate/cobalt, indigo/sage, teal/amethyst, emerald/purple, cool-blue/amber, cyan/amethyst). I resolve it with **two orthogonal color systems**, which is the genuinely sophisticated idea buried in the flagship spec:

1. **Signal axis (model vs. market) — reserved and sacred.** Cool **blue/azure = model**; warm **amber = market**. This pairing is the consensus of the two strongest IA docs (*UI Architecture Recommendation*, *Direction-Cockpit Style*) and the flagship spec, and the Wong palette makes it **colorblind-safe and non-cultural**. **No green and no red appear anywhere as a primary signal** — green reads "go/approve," red reads "bad/sell," both are banned verdict semantics. Divergence direction is shown on a third muted axis (muted green/rose) *as a hint only*, with text carrying the meaning — the explicit defense against the "cone of uncertainty" binarization failure.
2. **Position hues — a separate, optional, secondary encoding.** QB/RB/WR/TE pre-attentive identification on small position pills, where the **letter is the primary signal and color is reinforcement**.

**The one trap to avoid:** do not let a position hue collide with the reserved signal axis. The *UI Design System* and flagship spec both put **amber on a position** (WR or TE) while *also* using amber for the market lane and for cliff warnings — amber gets overloaded three ways. **My rule: amber belongs to Market + aging-cliff only.** Position hues should be chosen off the blue/amber axis (e.g., violet QB, teal RB, magenta WR, indigo PICK), and TE — which the docs keep wanting to make amber — should take a distinct hue, with cliff state shown by a differently-*shaped* chip, not by recoloring the pill.

### 3.3 Uncertainty visualization (the differentiator)
The constitution demands uncertainty be first-class; the corpus (especially *UI Architecture Recommendation*, with strong CHI/IEEE citations) is right about *how*:
- **Quantile dotplots (20 dots) are the primary primitive** — frequency-framed ("3 of 20 plausible futures see this player as a top-12 WR"), empirically better for decisions than error bars or violin plots.
- **Fan charts only for *time* projections** (aging-decay, pick-appreciation), with the Bernanke/BoE caveat noted — never as the primary point-estimate display.
- **Morningstar-style uncertainty bands** (band *thickness* = uncertainty) on the divergence strip.
- **Opacity/saturation decay** for low-confidence/experimental assets — a high median with a wide error renders *visually unstable*.
- **Banned:** the "collapsed probability" single integer with false precision (show `7,800 ±400`, not `7,842.3`).

### 3.4 Cliff warnings — lock to the constitution
Several docs invented cliff ages (Cockpit Spec: RB 27 / WR 29; Direction-Cockpit: RB 27–28 / WR 30–31 from aging research). **The UI's human-readable cliff *warnings* must use the constitution's locked ages: RB 26, WR 28, TE 30, QB 33** (archetype split for QB), rendered in **amber, not red**, as a *consideration* not a disqualifier. Fitted continuous aging curves may use research-derived shapes for the *curve*, but the warning threshold is constitutional. (The *UI Design System* and flagship spec got this right; others did not — reconcile to the constitution.)

---

## 4. Information architecture

A persistent **cockpit shell** (strong convergence across the corpus):
- **Left rail** (≤8 surfaces, Hick's/Miller's law), collapsible to icons.
- **Top status / Trust strip (24px, always visible):** "as-of" timestamp, most-stale source age, `decision_supported: false` chip, active league + posture, ⌘K hint. This keeps the trust state un-hideable at every viewport.
- **⌘K command palette** for player/pick/surface/rival jump (Bloomberg/Linear) — removes deep menus.
- **Right-side Player Inspector drawer** that follows the user across surfaces (Palantir Foundry object-inspector pattern). **Player and trade detail are addressable routes/drawers, never modals** — deep-linkable, openable in tabs.

**Surfaces:** Home / Command Center · Roster Audit · Rookie Board · Trade Lab · League Opportunity Map · Player Detail (drawer + route) · Trust / Governance · Settings / League Context.

**Posture (rebuild/balanced/contender) filters the UI only — it never changes model output.** (Constitutional: posture propagates to recommendations, not to training data.)

---

## 5. Surface-by-surface

For each surface: its job, the model/market separation, uncertainty treatment, neutral language, and what it reads from the backend. (The *Direction-Cockpit Style* wireframes are the most complete in the corpus; I adopt their structure, corrected for governance.)

- **Home / Command Center** — a *launching* surface, not a verdict surface. Panels: **Today's Review Areas** (sorted by signal density, neutral one-liners + inline divergence sparkbar — "review area," never "action"); **Roster Pressure Snapshot** (capacity bars, forced-cut *candidate count* framed as context); **Recently Changed Signals** (Tufte small-multiples sparklines); **Trust & Coverage mini** (source freshness, green/amber/hatched-gray — red only for hard failure). No feed, no gamification, no "for you."

- **Roster Audit** — David's roster as a portfolio. Dense table with strict two-lane column groups (model group / market group, never sharing a cell), age-curve small-multiples per position (cliff band at constitutional ages), capacity bars (active/taxi/IR), and a **forced-cut candidate list explicitly labeled "sorted by model-value-per-slot — not a recommendation, `decision_supported: false`."** Starts in the Experimental frame until the Trust surface earns it out.

- **Rookie Board** — Engine A surface. Ranked table, two-lane (Engine A model vs. market), **xVAR shown as a range/quantile dotplot, never a static integer**, draft-capital chip, roster-fit dot (descriptive: "WR room already has 3 sub-23 players" — not "fits your team"), live draft-state band (taken rookies dimmed + struck-through, not removed), and an **Evidence Gap flag** wherever validation is incomplete. Right-rail inspector: drivers, counter-argument, comparables-as-evidence, Engine version + run timestamp.

- **Player Detail Card** — the most-visited atom; satisfies the Two-Lane rule completely. Top scoreboard: **Model View panel (cool/blue)** and **Market Snapshot panel (warm/amber)**, never merged, with a **divergence strip** between them (blue tick = model, amber tick = market, uncertainty band thickness) and neutral phrasing ("model lower than market by 18%, uncertainty medium"). Below: **Model Route** (lineage: which engine/feature-set/fallback fired — answers "why did the model say this?"), **signed driver-contribution bars**, a dedicated **Caveats + Counter-Argument panel** (never a tooltip), and an extended market-overlay time series with explicitly-labeled Model / Market lines. Footer: `decision_supported: false` chip + model version + as-of.

- **Trade Lab** — highest governance risk; build *after* the design system hardens. Three columns (your side / analysis / their side). Analysis pane = four stacked panels mirroring governance: **Model View** (xVAR/DVS deltas as magnitude bars + uncertainty), **Market Snapshot** (raw FantasyCalc, separate), **Divergence Context** (per-asset, neutral), **Roster Penalty & Pressure** (forced-cut penalty from the live RosterCutEngine; package-dilution *caveat*, not adjustment; pick caveats). A **horizon control (1/3/5-yr)** re-renders model values so "picks appreciate, veterans depreciate" becomes visceral. **No "Simulate/Approve/Reject/Fair" — ever.** No win-probability. Counter-argument mandatory. This surface is the natural home of the optional React island.

- **League Opportunity Map** — 12-team matrix (xVAR by position, posture *inferred* not asserted, future-pick context, surplus/deficit, divergence). Neutral throughout: "review area," "potential overlap," "model higher than market" — **never** "trade target." Heatmap toggle uses the blue↔amber divergent axis (no green/red).

- **Trust / Governance** — the credibility layer and the canonical home of `decision_supported`. Model artifact registry (version, last run, coverage, decision_supported chip), source-freshness table (Stripe Sigma "last data load" pattern; green/amber/hatched-gray; red only for hard failure), David-curated **Known Limitations**, and a **decision-support promotion log** (the audit trail that would record any future `false → true` promotion with the justifying backtest). This surface is what *earns* every other surface out of the Experimental frame.

- **Settings / League Context** — league rules read from Sleeper (Superflex, PPR, TE-premium, roster/taxi/IR limits — **bind to the real league, `1314363401744416768` / "Woodbury Riders" / Redzone Champions / 12-team SF PPR**, not placeholder numbers), posture selector (UI-only), artifact version pins, display density/theme, precision rules. No push notifications (request-pull tool).

---

## 6. Data flow & API contract

- **The UI is strictly read-only over pre-computed Player Value Objects.** It never recomputes, re-weights, or imputes a value; if a number isn't in the PVO, the UI says "unavailable" — never guesses. (Constitutional and unanimous in the corpus.)
- **Two physically separate data paths.** Model lane reads PVO/Engine outputs; market lane fetches FantasyCalc separately and is merged **only in the presentation layer**. Market-derived values must never reach a model feature — that's leakage, a defect.
- **`decision_supported = false` everywhere right now** (per AGENT_SYNC, Phase 15+). The chip is universal until the Trust surface promotes.
- **Backend change to flag:** uncertainty viz needs **distributions, not point estimates**. The PVO serializers should expose decile/quantile arrays (e.g., p5/p50/p95 or 20-quantile dots) per projection — transmit deciles and interpolate client-side to keep payloads small. This is the one substantive backend ask the front end creates, and it should be specced and David-approved before build (it touches the PVO contract).
- **DVS/xVAR scale: 0–100** (Phase 14 locked Option C). Ignore the docs that say 0–1000 or show 0–10,000 "currency" values (Section 10). Display to the *meaningful* significant figure with the uncertainty band, not false precision.
- **Sleeper rate limit** (<1000/min) is handled by the **FastAPI backend cache**, not the browser. Stale data degrades visibly (saturation + dashed border + "last refreshed Xh ago"); the system shows *no* data rather than confidently-wrong stale data.
- **Identity:** render only deterministically-resolved (canonical `player_id` / Sleeper ID) rows. Per the architecture, fuzzy matching lives only in reviewable staging and unresolved rows go to triage — so the UI **flags any fuzzy/unresolved match as review-only and never presents it as verified**. (The corpus splits between "forbid fuzzy" and "allow with a flag"; the constitution's actual rule is the reconciliation: deterministic in production, flagged-and-quarantined otherwise.)

---

## 7. Generative UI — defer, then constrain

Generative UI is real and promising — the Google Research PDF demonstrates LLM-generated UIs are overwhelmingly preferred over markdown, and *Generative UI: Hard Decisions* is the most clear-eyed doc in the corpus about how to do it safely (closed component catalog, schema-driven, LLM as presentation router that never reasons numerically, DuckDB+Parquet local, ~$30–55/mo, **explicitly no Databricks, no raw JSX**). But for Dynasty Genius, **now is emphatically not the time**, for four reasons:

1. **The constitution gates it last.** Frontend comes last; a generative *layer on top of* the frontend comes later still. The static decision surfaces must exist and be trusted first.
2. **It brushes a hard non-goal.** "Generic AI chatbot that bypasses structured decision cards" is a standing non-goal. A generative "ask anything" surface is acceptable *only* if it routes strictly through the structured Decision Card catalog (the Hard Decisions doc's `VerdictCard`/closed-schema approach honors this; a free-form chat does not).
3. **The two heavyweight gen-UI proposals violate hard constraints** (Databricks spend cap, local-first, React/Next dependency weight). Only the DuckDB-local + closed-catalog variant is even compatible.
4. **Latency.** The PDF's own primary limitation is ~1–2 minutes per generated view — at odds with the sub-100ms interactivity the cockpit needs for filtering/sorting.

**Recommendation:** build the static cockpit. *Later*, if David wants it, add generative UI as an **additive, opt-in layer for ~4 high-ROI conversational surfaces** (multi-asset trade what-ifs, 3–5-yr roster simulation, contextual rookie re-tiering, injury branching) — schema-driven over a **closed component catalog reusing the same Jinja/Decision-Card components**, local DuckDB, never raw HTML/JSX, with explicit David sign-off against the chatbot non-goal. Keep ~60% of the app declarative regardless.

---

## 8. Governance enforcement (make honesty mechanical)

The corpus proves the danger: multiple *Design System* docs, while *claiming* to ban verdict language, ship `Buy WR` badges and "optimal target acquisition window" copy in their own examples. **Aspirational discipline fails.** Therefore:

- **A banned-language linter in CI/pre-commit** scanning rendered templates/components for: `buy, sell, target, block, approve, reject, pass, fail, win, loss, winner, loser, fair, unfair, verdict, bust, elite, steal, must-have, must-cut, drop (as button), recommended, you should`. Wire it into the existing ruff-style hygiene ratchet (`03-code-hygiene-policy.md`). The acceptance criterion several docs ask for ("zero banned tokens in the DOM") becomes a gate, not a hope.
- **`decision_supported: false` chip is component-level**, attached to the Decision Card macro — impossible to render a recommendation without it until promotion.
- **The banned David-facing output patterns** from `01-north-star-architecture.md` (rookie confidence-from-pick-bucket, dynasty_tier letters, trade verdicts, trade side totals before validated uncertainty bands, roster "Sell now" actions) are enforced in the same lint pass.
- **No write-back to Sleeper. No automated trade execution.** Read-only, advisory, always.

---

## 9. Build order (reconciling the corpus's two orderings)

The two strongest docs disagree: *UI Architecture Recommendation* says **Trade Lab first** (backend just shipped); *Direction-Cockpit Style* says **Player Card / Roster Audit / Trust first, defer Trade Lab** (highest governance risk). I side mostly with the latter, because the constitution says *trust before polish* and the Trade Lab is the single highest banned-language/false-certainty risk surface — it should be built on a *hardened* design system, not used to harden it.

1. **App shell + design tokens + component library** — `tokens.css`, `components.html` macros (Decision Card, Two-Lane, Player Card, quantile dotplot, divergence strip, caveat/cliff chips, Trust strip, Experimental frame). Locks every contract before any surface ships.
2. **Player Card + Roster Audit (read-only)** — exercises Two-Lane + uncertainty on mature data; lower governance risk; both start in the Experimental frame.
3. **Trust / Backtest surface** — the credibility layer. Without it every other surface inherits unearned authority. This is what unblocks the `decision_supported` chip having meaning and earns surfaces out of Experimental.
4. **Rookie Board** — analytically the most mature; visual-system upgrade is cheap.
5. **Trade Lab** — after the system is hardened; the just-shipped backend is ready; this is where the React-island escape hatch may trigger.
6. **League Opportunity Map** — depends on full Sleeper league sync + stable posture inference.
7. **Settings**, then (much later, optional, David-approved) **generative-UI layer**.

Honest tradeoff: this ships the most *common* high-stakes surface (Trade Lab) later than #1. I accept that because the cost of getting Trade Lab's governance wrong (a "Fair Trade"-style verdict creeping in) is higher than the cost of waiting, and the design system needs lower-risk surfaces to harden against first.

---

## 10. Critical findings — drift and errors in the corpus I am correcting

A disciplined, critical read surfaced several places where the research docs diverge from the constitution, the architecture, or the actual repo. My recommendation is built on the corrections:

1. **Engine A/B mislabeled as "market."** The flagship *UI:UX Research & Design System Specification* labels the Trade Lab lanes "ENGINE A · MODEL" vs. "ENGINE B · MARKET" and its data contract comments `// Engine B — Market` on `market_value`. **This is wrong and would corrupt the whole premise.** Engine A *and* Engine B are both internal **model** engines (rookie vs. active player); the **market** lane is FantasyCalc/KTC. The Two-Lane split is **Model (Engine A or B) vs. Market (FantasyCalc)** — Engine B belongs in the model lane.
2. **DVS scale confusion.** Docs variously assert 0–1000 ("E27 currency," *Research Brief2*/*Direction Spec*) or show 0–10,000 values (*Design System2*). **Phase 14 locked DVS at 0–100** (Option C). Lock the UI to 0–100.
3. **Invented cliff ages.** Use the constitution's RB 26 / WR 28 / TE 30 / QB 33 (amber, display-warning only), not the docs' 27/29 or 27–28/30–31.
4. **Banned-language self-violations** inside the *Design System* docs (`Buy WR`, "optimal target acquisition window"). Proof the rule must be machine-enforced (Section 8).
5. **Stale `file://` premise.** The served-FastAPI reality moots the CORS/`FileReader`/`localStorage` workarounds in 4 docs. Server-render with Jinja/HTMX; cache Sleeper in the backend.
6. **Databricks generative-UI stack** violates the spend cap + local-first + frontend-last + chatbot non-goal. Use the local DuckDB + closed-catalog path only, and only much later.
7. **Placeholder league data.** Docs show 25-slot caps, "Contender" posture, Sleeper ID `82914`. The real context is **league `1314363401744416768`, "Woodbury Riders," Redzone Champions, 12-team Superflex Full PPR, rebuild posture, 26-slot capacity** (corroborated across the two strongest docs + AGENT_SYNC). Bind to real context.
8. **Palette inconsistency** (six model/market pairings). Resolved to **blue=model, amber=market, no green/red**, with position hues as a separate axis (Section 3.2).
9. **Fuzzy-matching split** (forbid vs. allow-with-flag). Reconciled to the architecture: deterministic IDs in production; anything fuzzy/unresolved is flagged review-only and quarantined, never silently rendered.

---

## 11. Open questions for David (decisions that change the build)

1. **PVO distribution output.** Approve exposing decile/quantile arrays from the PVO serializers (needed for quantile dotplots)? This touches the model output contract.
2. **Build order.** Endorse Trust-before-Trade-Lab (my rec, §9), or Trade-Lab-first (the just-shipped backend)?
3. **Position-hue vs. signal-axis collision.** Accept reserving amber for Market + cliff only (so TE takes a non-amber hue)?
4. **Market display normalization.** Show FantasyCalc *as fetched* (SF/0.5-PPR default) with a format-mismatch chip, or normalize to the league's Full PPR? (Recommend: show as-fetched + chip; never silently transform market data.)
5. **Generative UI.** Off the table for now (my rec), or do you want a scoped, David-approved, closed-catalog exploration queued behind the static cockpit?
6. **`decision_supported` promotion criteria.** What concretely must a backtest show to promote a surface `false → true`? The Trust surface needs the log; the criteria must come from you.

---

## 12. Caveats on this recommendation

- It is **opinionated**, as the brief requested — dark, dense, Bloomberg/Linear lineage. A user who wanted a brighter consumer aesthetic would find it austere; the constitution explicitly wants the analytical-workstation feel, so I took that at face value.
- The **HTMX + Observable Plot integration is mildly novel** (no large named precedent combines exactly this for 7 small-multiples dashboards). Plot's vanilla API is small and the risk is low, but ECharts is the named fallback.
- **Quantile dotplots are a learned read** — mitigated by the per-chart disclosure ("each dot = 1 of 20 plausible futures") and the fact that David is a sophisticated single user.
- I have deliberately **not** designed pixel-exact components; tokens and structure are specified, final pixel values belong in the design-system file once built.
- This is **one agent's independent view** for the merge. Where Codex and Gemini converge with me (I expect: cockpit IA, Two-Lane, no-verdict language, uncertainty-first, dark/dense, local-first) those points are robust; where we diverge (most likely: tech stack weight and the generative-UI posture) the disagreement is the most valuable input to the merge.
