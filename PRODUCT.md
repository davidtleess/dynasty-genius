# Product

> Distilled from the product design corpus and the foundation-redo synthesis
> (`docs/strategies/2026-07-07-design-foundation-redo-synthesis.md`), which itself draws on
> `docs/strategies/2026-07-05-world-class-frontend-research-brief.md`,
> `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`,
> `docs/strategies/2026-07-06-claude-fantasy-ui-research.md`,
> `docs/strategies/2026-07-06-fantasy-app-data-display-research-codex.md`,
> `docs/strategies/2026-07-06-fresh-agent-design-reviews.md`. This file is the current product
> source of truth; dated research and strategy documents provide context.

## Register

product

## Users

One user: David — a dynasty fantasy football manager (Superflex PPR, 12-team league) with 15 years of enterprise-software judgment. Daily-login context: the morning check of what changed overnight in his league's market prices and his model's outputs. He is in a decision workflow (trade, cut, waiver, draft). The product's job is to make him *want* to open it every morning, surface verified facts, ranges, and provenance he can act on — and never to decide for him.

## Product Purpose

Dynasty Genius is a private, single-league **dynasty asset terminal** — a daily point-in-time record of one league's reality wired to a model that refuses to lie about what it knows. It lives in the Sleeper / DynastyNerds / KeepTradeCut category on the surface, and is built to be more honest than any of them underneath. Success = David makes dynasty decisions that look correct 3–7 years out, trusting the surface because every number carries a receipt, *and* enjoys the daily scan because the screen is genuinely a pleasure to read.

## The polarity (read this first)

**Honesty is the substrate. Fantasy-native legibility is the aesthetic.** The product constraints — no verdicts, two isolated lanes, receipts on every number, the Hard Right Edge — are the non-negotiable *frame*, not the design goal. Inside that frame the product must look and feel best-in-class for its category: ranked rows, real player identity, one focal value per row, tiers, trends, hero moments. The failure mode this foundation exists to kill is "an honest developer diagnostics console wearing a fantasy skin." Credibility is the floor; a striking, legible, alive surface is the goal. Both, always — never one as an excuse to skip the other.

## Brand Personality

A private trading terminal for a serious dynasty manager: dense, fast, credible — **and desirable, striking, alive, human.** The screen speaks dynasty-manager prose; technical precision lives one layer down in receipts and title attributes. The jaw-drop is *visible* — the focal value number, real player faces, the σ range, the tier bands, the one orchestrated daily-open entrance — earned by craft, never by chrome. Boldness is spent generously on legibility and hierarchy, never on decoration.

## Anti-references

- **Developer/diagnostics UI** — raw schema nouns, snake_case constants, ISO timestamps, database IDs, `Status: ok` plumbing, or a System-Diagnostics panel anywhere in a user viewport. An engineer's admin view is the single thing this product must never resemble.
- Consumer fantasy-app **cheerleading** — green/red verdict colors, "BUY NOW" energy, urgency motion, pulsing deltas. (Reject the verdict *semantics*, not the category's visual richness.)
- Generic dashboard gloss: glassmorphism, backdrop blurs, gradient chrome; SaaS hero-metric cards; identical card grids.
- Dark-terminal-with-acid-accent template aesthetics.

## Design Principles

1. **Fantasy-native first, truthful underneath.** The visible grammar is a Sleeper/DN/KTC-class asset terminal — ranked rows, player identity, focal values, tiers, trends, hero cards. Honesty is the substrate beneath, never the surface aesthetic.
2. **The canonical row is a fixed contract.** `rank · position-rank chip · identity (headshot + name + team) · ONE focal value · named-window trend · status/receipt chips`. One number owns the row (2–3× label weight/size, right-aligned tabular); current value and its delta always travel together; no per-row label repetition; a rank with no disclosed basis is a defect. Every surface (player card, Trade Lab, league, waiver, rookie board) composes from this row. **The macro answer comes first:** the Daily Open opens with a roster-level summary line in manager prose ("Your roster overnight: model value +1.2%, market −0.4%" / "Quiet morning — no model changes, market held") before any rows, so the morning scan never starts as mental math.
3. **Player identity is required recognition infrastructure.** Headshots with the mandatory fallback chain (headshot → initials-on-position-color disc → silhouette; never a broken image, never a raw id). Team = abbreviation + color mark as a ring/chip, never a row-fill, never a logo. Identity is factual, orthogonal to the model/market lanes.
4. **No verdicts, ever.** — **AMENDED 2026-08-29 by David; the PRESENTATION half of this principle is superseded.** His ruling (verbatim in `~/dg-build/DG091-DESIGN-BRIEF.md`): *"I don't care to persist the governance of language and caveats and lack of overall recommendation from the back end into the front end. I'd rather use layman's terms and call a spade a spade, and I've given it the green light to do so."* So the frontend MAY say buy/sell/hold and state overall recommendations in plain fantasy prose, and the lexical watched-word policing below no longer binds frontend copy (DG-104 re-scoped the enforcing linter accordingly). What STILL STANDS, untouched by a presentation ruling: the backend never fabricates; `decision_supported=false` until validation earns otherwise; and no typed decision field (`verdict`/`dynasty_tier`/`confidence`/`recommended_action`/`roster_action`) may be published to the screen — as a rendered property *or* as its display label ("Confidence score: 82%") — because the contract does not produce one. The clauses below are the pre-amendment text, kept for the half that survives; anything narrower than the ruling is David's to re-ratify, not a lane's to infer. Descriptive surfaces issue no buy/sell/hold, no recommended action, no verdict hues. Direction is data, not judgment — **AMENDED 2026-08-30 by David, verbatim design-panel option label: "Green up / red down".** The presentation half of this clause ("signed, neutral") is superseded for direction only: a delta may be colored by *which way it moved*, never by whether that is good or bad for you, and the signed value is still printed on every delta so color is never the only channel. "No verdict hues" itself is untouched and still binds — see DESIGN.md's Color section for the enforced rule. Aspiration language never smuggles a verdict ("edge/target/priority/Elite/Bust" are watched words). **No system-nominated single-player hero** — a tool-selected "biggest mover" or "story of the day" is an implicit verdict; single-player emphasis is legitimate only when user-selected, David-supplied, aggregate, or explicitly lane-symmetric and non-actionable (the banned MoverHero pattern). The first viewport preserves the surface's declared order and lane symmetry — never a market-only recency lead. `decision_supported=false` until validation earns otherwise.
5. **Two-lane truth, visibly a system.** Model (blue) and market (amber) are structurally isolated *and* the hues actually frame their own objects on the primary surface — not spent on nav links while the model card shows no blue. Direction color (`--dg-up`/`--dg-down`), the neutral chrome family and the DVS ramp are orthogonal token families that never collide with the lane hues — DG-115 holds the direction pair ≥35° off both lanes and holds chrome near-achromatic, and it deleted the never-rendered position hues rather than leave dead tokens claiming to be a family. A market swing must never read as a model signal.
6. **The scaffolding-hide law.** No implementation artifact reaches the surface: no raw IDs, snake_case, ISO timestamps, diagnostics panels in the hero, or roadmap/DEVELOPER chrome in nav. Every quiet, pending, and failure state is a *designed* state. **Proportionality (the ban is not only lexical):** system, trust, freshness, and caveat plumbing may never be the *primary first-viewport story* even in polished manager prose — the first screen is a fantasy/asset narrative, not a status board.
7. **Honesty is designed, not dumped — "visible, not wallpaper."** Receipts, caveats, disclosed bases, and the Hard Right Edge stay — rendered as designed elements, with evidence riding *next to* the number, not only behind hover. Uncertainty display (σ ranges, percentile-of-cohort, disagreement) is DG's signature honesty asset, not italic monospace wallpaper. **Layered caveats:** only high-priority blocking warnings (e.g., the ≥26h stale badge) render as active blocks in the primary viewport; minor disclaimers, model-basis notes, and diagnostics tuck into a collapsible caveats/provenance drawer or the inspector — never 4–5 warnings stacked on the active screen.
8. **Tiers reveal cliffs; trends show direction, never urgency.** Value-band dividers with a disclosed basis answer "where is the cliff to the next cluster?" Neutral labels are allowed; named tiers must be evidence-backed and never use verdict hues. Trends are a signed delta over a named window, glyph-first and CVD-safe, weighted so magnitude is legible.
9. **Mobile is a first-class layout**, not a squeezed desktop: daily tape + top changed rows, collapsed nav, status pill over pinned panels, bottom-sheet inspector, no horizontal overflow.
10. **The shipped app is the design artifact, and passing component tests does not prove visual quality.** Review the whole viewport against the Sleeper/DN/KTC bar on desktop and mobile, including mid-scroll states where sticky and overlay collisions appear. **Shape before code:** define the 5-second answer, focal hierarchy, desktop/mobile composition, and lane order before implementing a surface. The bar is truly exceptional.

## Accessibility & Inclusion

Keyboard-first: every receipt/disclosure focusable and operable (Enter/Esc/touch; hover is enhancement only). Visible focus via the `--dg-focus` grammar in both themes. `prefers-reduced-motion` honored by every motion class. axe violations = 0 on shipped surfaces; contrast at WCAG AA minimums. No information is carried by color alone; hue never carries verdict meaning.
