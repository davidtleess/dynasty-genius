# Dynasty Genius — UI/UX Research & Design System Specification

**Version:** 1.0 · **Status:** Foundational · **Audience:** Implementing developer agents
**Date:** May 25, 2026

---

## TL;DR

- Build a **dark-first, Linear-structure + Stripe-depth cockpit** in pure vanilla HTML/CSS/JS that boots from `file://`, drives off a Radix-derived dark-slate canvas with calibrated position hues, and renders every signal as a *range, band, or magnitude* — never a red/green verdict.
- The **Trade Lab is the keystone surface**: two visually distinct lanes (Model = cool tint, Market = warm tint) read PVO objects produced upstream, present xVAR deltas as horizontal magnitude bars, and show arbitrage state as `model_higher_than_market` / `model_lower_than_market` / `inside_band` — no buy/sell glyphs anywhere in the system.
- The deliverable below is a **prescriptive, copy-paste-ready spec**: complete `:root` token block, HTML skeletons, BEM class names, ring-meter SVG math, container-query layout strategy, accessibility patterns, and stale-data degradation rules — production-grade engineering, single-user simplicity.

---

## Key Findings

1. **The "no binary verdicts" doctrine has a clean visual translation.** A blue↔amber chromatic axis (the Wong palette, published by Bang Wong in *Nature Methods* 8, 441 (2011; doi:10.1038/nmeth.1618), which Nature journals explicitly recommend for all scientific figures) is non-cultural, colorblind-safe across protanopia/deuteranopia/tritanopia, and carries no "right/wrong" connotation. We use it as the system-wide signal axis; green and red appear nowhere.

2. **Radix `slateDark` and `amberDark` are the right foundation.** They ship paired light/dark scales tested for perceptual uniformity and APCA contrast targeting, with Radix's documentation stating that "Text colors are guaranteed to pass target contrast ratios against the corresponding background colors." Using their scales verbatim removes most contrast-tuning labor and accelerates Stage 1.

3. **Container queries replace media queries for component-level responsiveness.** Per web.dev's August 2025 Baseline monthly digest, container queries became Baseline Widely Available in August 2025 (30 months after their February 2023 cross-browser debut), and "the majority of sites should now be confident in adopting" them. They ship without polyfill, work under `file://`, and let the Player Card atom render correctly in a 240px lane *and* a 1100px Trade Lab with one set of rules.

4. **Lane separation in the Trade Lab needs four reinforcing signals, not one.** Background tint, eyebrow label, vertical seam, and accent-border together produce a pre-attentive "Model lane vs Market lane" read in <500ms. No single signal is sufficient — a designer-only color swap will fail the glance test for protanopes.

5. **Density requires Carbon's `body-compact-01` rhythm, not standard prose.** 14px / 18px line-height (ratio 1.29) is the documented dense-data setpoint; 13px also works at slightly tighter leading. JetBrains Mono with tabular-nums is required for every numeric cell.

6. **Reduced-motion is not "no motion" — it is "opacity-only motion."** Scale, large translation, and pulse rings are vestibular triggers; opacity is safe. We provide explicit fallbacks for every animated component.

---

## Details

### Section 1 — Design Philosophy & Visual Psychology

#### 1.1 The Cockpit Metaphor

Dynasty Genius is an **asset-management cockpit**, not a fantasy app. The user (David) is operating a 25-man portfolio across a 3+ year horizon while pricing optionality against an illiquid market. The closest real-world analog is a portfolio manager's desk: positions, exposures, capacity, mark-to-model vs mark-to-market, and forward draft capital that behaves like options on future inventory.

The cockpit metaphor implies:

1. **Surface for monitoring, drawer for action.** Top-level surfaces (League Pulse, Roster Audit) are read-heavy, dense, and ambient. Action surfaces (Trade Lab) are isolated, focused, and intentional. This mirrors Bloomberg's panel-vs-launcher pattern: per Bloomberg LP's article "How Bloomberg Terminal UX designers conceal complexity," Bloomberg CTO Shawn Edwards said, *"'We're hiding complexity,' he says. 'And we do it across thousands of functions, across domains and asset classes, so the user has a seamless experience through their whole journey within the Terminal.'"* Dynasty Genius copies the *discipline* (dense, hierarchical, fast) while rejecting the *form* (CRT-era phosphor glyphs, function-code keyboard syntax).

2. **Information density is a capability, not a liability.** David has 15 years of enterprise software fluency. Whitespace exists to group, not to decorate.

3. **Calm chrome, loud signal.** Linear's blog post "A calmer interface for a product in motion" (linear.app/now/behind-the-latest-design-refresh) states verbatim: *"Linear is designed to surface exactly what you need, when you need it. The challenge was preserving that rich density of information without letting the interface feel overwhelming."* The chrome — sidebars, headers, dividers — must recede; only data and warnings should carry chromatic weight.

#### 1.2 Linear + Stripe Hybrid Rationale

| Dimension | Take from Linear | Take from Stripe |
|---|---|---|
| Information hierarchy | Restrained chrome, minimal separators, content-first | — |
| Color system | LCH-derived scales, neutral cool-grey base | — |
| Surface depth | Flat panels with subtle borders | Layered glass surfaces, gradient depth, popover elevation |
| Brand temperature | Cool, almost monochrome | Subtle gradient warmth on actionable elements |
| Typography | Inter (clarity) | Sophisticated number rendering, tabular nums |

Linear's UI works because it treats *the page* as the canvas. Per Sequoia Capital's profile "Linear: Designing for the Developers," Linear co-founder Karri Saarinen explained: *"Linear is designed to read as 'professional' to engineers...It's based on the black coding environments many engineers prefer, minimizing battery drain and eye strain."* Stripe Dashboard's dark mode added something Linear deliberately omitted: **layered translucency for elevation** — modals, popovers, and inspector panels sit *above* the canvas via `backdrop-filter` glass. We borrow Stripe's depth vocabulary for transient surfaces (popovers, the Trade Lab inspector) and keep Linear's flat discipline for the persistent shell.

We reject Vercel/Geist pure-monochrome severity for one specific reason: this is a *positional* sport. QB/RB/WR/TE/Pick must be visually pre-attentive. Pure grayscale fails that test.

#### 1.3 The Three-Tier Information Hierarchy

```
TIER 1 — AMBIENT CONTEXT      League posture, season clock, last-refresh chip
                              (slate-11 text on slate-1/2 canvas)
                              No interaction. Always-visible header strip.

TIER 2 — PRIMARY SIGNAL       Roster cards, xVAR deltas, position pills,
                              arbitrage band state, ring meters.
                              (slate-12 text + position hue + amber warnings)
                              Glanceable. Density is high; truncation is OK.

TIER 3 — DRILL-DOWN DETAIL    Right inspector panel, player detail variant,
                              trade lane totals, mini-charts.
                              (full chroma, mono-numerics, expanded ranges)
                              Triggered. Hidden until requested.
```

Three tiers, not four, because David is a single user with a single mental model. Bloomberg has four-plus tiers because thousands of users each need a different slice. We collapse configuration/settings into a one-time docked drawer.

#### 1.4 "No Binary Verdicts" — Visual Translation

| Forbidden pattern | Replacement |
|---|---|
| Red-down / green-up arrows | **Cool-blue (`--signal-positive-delta`) vs amber-warm (`--signal-negative-delta`) horizontal bars** with numeric magnitude. The hue pair is non-cultural — blue and amber don't read as "right/wrong," they read as "more model / more market." |
| Thumbs up / thumbs down | **Ring meters** showing magnitude on a 0–100 capacity axis. Empty ≠ bad; it just means "low utilization." |
| "Fair trade" badge | **Arbitrage band state pill**: `model_higher_than_market`, `model_lower_than_market`, `inside_band`. |
| Pass/fail color on age | **Amber cliff-warning tag** (RB≥26, WR≥28, TE≥30, QB≥33) — *amber, not red*, because the cliff is a *consideration*, not a disqualifier. |
| Big "DROP" button | **"Mark as cut candidate"** subtle text affordance with no execution side-effect. |
| "Win probability 73%" | **xVAR delta margin with uncertainty range** rendered as a horizontal band, not a single number. |

The Wong palette (Bang Wong, *Nature Methods* 8, 441 (2011); doi:10.1038/nmeth.1618 — Nature journals explicitly recommend it for all scientific figures) anchors this: blue (#0072B2) and orange (#E69F00) remain visually distinct under protanopia, deuteranopia, and tritanopia. It is the maximally distinguishable non-cultural pair.

---

### Section 2 — Unified CSS Custom Properties System (Design Tokens)

Implementing agents copy this into `static/css/tokens.css` verbatim. The slate scale is the official Radix Colors `slateDark` package; the amber scale is Radix `amberDark`. Radix's own documentation states: *"Text colors are guaranteed to pass target contrast ratios against the corresponding background colors. Contrast targets are based on the modern APCA contrast algorithm, which accurately predicts how human vision perceives text."*

```css
/* ============================================================
   tokens.css — Dynasty Genius Design System
   Foundation: Radix slateDark + amberDark, calibrated for cockpit density.
   DO NOT add tokens here without architectural review.
   ============================================================ */

:root {
  /* ---------- SURFACE ELEVATIONS (cool dark slate) ---------- */
  --surface-0:        hsl(200 8% 6%);          /* deep canvas, below Radix slate-1 */
  --surface-1:        hsl(200 7% 8.8%);        /* slate-1: page background */
  --surface-2:        hsl(195 7% 11%);         /* slate-2: panel background */
  --surface-3:        hsl(197 6.8% 13.6%);     /* slate-3: raised card */
  --surface-4:        hsl(198 6.6% 15.8%);     /* slate-4: hover/active card */
  --surface-popover:  hsl(199 6.4% 17.9%);     /* slate-5: popover, dropdown */
  --surface-modal:    hsl(201 6.2% 20.5%);     /* slate-6: modal background */

  /* Translucent glass overlays (Stripe-depth). Use sparingly, only above content. */
  --surface-glass:           hsla(200 8% 8% / 0.62);
  --surface-glass-strong:    hsla(200 8% 6% / 0.78);
  --backdrop-blur:           blur(14px) saturate(140%);
  --backdrop-blur-strong:    blur(22px) saturate(160%);

  /* ---------- TEXT (Radix slate 11/12) ---------- */
  --text-hi:          hsl(210 6% 93%);         /* slate-12: headlines, key numbers */
  --text-mid:         hsl(206 6% 63%);         /* slate-11: body, labels */
  --text-low:         hsl(206 5.2% 49.5%);     /* slate-10: captions, axis labels */
  --text-disabled:    hsl(207 5.6% 31.6%);     /* slate-8 */
  --text-on-warm:     hsl(36 100% 6.1%);       /* amber-1, for text on solid amber */

  /* ---------- BORDERS ---------- */
  --border-subtle:           hsl(201 6.2% 20.5%);   /* slate-6 */
  --border-default:          hsl(203 6% 24.3%);     /* slate-7 */
  --border-strong:           hsl(207 5.6% 31.6%);   /* slate-8 */
  --border-position-accent:  currentColor;          /* set per-component to position hue */
  --border-glass:            hsla(210 30% 95% / 0.06);

  /* ---------- POSITION COLORS ----------
     Hue spacing > 60° between adjacent positions to ensure pre-attentive
     differentiation. All steps tuned for AA contrast on --surface-2.
     QB = violet (cerebral / leader), RB = teal-cyan (motion / volume),
     WR = magenta-pink (explosive / outlier), TE = amber-gold (utility /
     cliff-prone), PICK = indigo (option / future).
     These hue pairings deliberately avoid red and green to stay outside
     the cultural verdict palette and remain colorblind-safe.            */

  --pos-qb:           hsl(265 70% 66%);    /* violet 9 */
  --pos-qb-bg:        hsl(265 40% 16%);
  --pos-qb-border:    hsl(265 55% 38%);

  --pos-rb:           hsl(178 65% 52%);    /* teal-cyan 9 */
  --pos-rb-bg:        hsl(178 40% 13%);
  --pos-rb-border:    hsl(178 50% 30%);

  --pos-wr:           hsl(322 72% 64%);    /* magenta-pink 9 */
  --pos-wr-bg:        hsl(322 38% 16%);
  --pos-wr-border:    hsl(322 55% 36%);

  --pos-te:           hsl(38 92% 60%);     /* amber-gold 9 */
  --pos-te-bg:        hsl(38 50% 14%);
  --pos-te-border:    hsl(38 70% 34%);

  --pos-pick:         hsl(220 75% 66%);    /* indigo 9 */
  --pos-pick-bg:      hsl(220 42% 16%);
  --pos-pick-border:  hsl(220 55% 38%);

  /* ---------- SEMANTIC STATE COLORS (NON-VERDICT) ---------- */
  /* Aging cliff: amber, not red. Radix amberDark anchors. */
  --warn-age:          hsl(39 100% 57%);          /* amber-9 */
  --warn-age-bg:       hsl(33 100% 14.6%);        /* amber-5 */
  --warn-age-text:     hsl(39 97% 93%);           /* amber-12 */
  --warn-age-border:   hsl(35 91% 21.6%);         /* amber-7 */

  /* Stale data: desaturated, not red. */
  --warn-stale:        hsl(210 4% 45%);
  --warn-stale-bg:     hsl(210 6% 14%);

  /* Delta direction tokens — DELIBERATELY NOT GREEN/RED.
     "positive" = model finds excess value (cool, calm, analytical signal).
     "negative" = market shows excess price (warm, attentional, but not alarm). */
  --signal-positive-delta:        hsl(205 80% 62%);   /* cool azure */
  --signal-positive-delta-bg:     hsl(205 40% 14%);
  --signal-positive-delta-border: hsl(205 55% 32%);

  --signal-negative-delta:        hsl(28 88% 60%);    /* warm amber-orange */
  --signal-negative-delta-bg:     hsl(28 45% 14%);
  --signal-negative-delta-border: hsl(28 60% 34%);

  /* Arbitrage band states */
  --band-inside:        hsl(206 6% 43.9%);
  --band-inside-bg:     hsl(198 6.6% 15.8%);
  --band-model-high:    var(--signal-positive-delta);
  --band-market-high:   var(--signal-negative-delta);

  /* ---------- TYPOGRAPHY ---------- */
  --ff-display:  'Outfit', system-ui, -apple-system, sans-serif;
  --ff-body:     'Inter', system-ui, -apple-system, sans-serif;
  --ff-mono:     'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;

  /* Fluid type scale (clamp[min, fluid, max]).
     Body anchor is 13–14px following Carbon Design System's body-compact-01
     pattern (per carbondesignsystem.com/guidelines/typography/type-sets/):
     "body-compact-01 — Type: IBM Plex Sans, Size: 14px / .875rem,
     Line height: 18px / 1.125rem, Weight: 400 / Regular, Letter spacing: .16px…
     This is for short paragraphs with no more than four lines and is commonly
     used in components." */
  --fs-micro:    clamp(0.625rem, 0.6rem + 0.1vw, 0.6875rem);   /* 10–11px */
  --fs-xs:       clamp(0.6875rem, 0.66rem + 0.13vw, 0.75rem);  /* 11–12px */
  --fs-sm:       clamp(0.75rem, 0.72rem + 0.16vw, 0.8125rem);  /* 12–13px */
  --fs-body:     clamp(0.8125rem, 0.78rem + 0.18vw, 0.875rem); /* 13–14px */
  --fs-lg:       clamp(0.9375rem, 0.9rem + 0.2vw, 1rem);       /* 15–16px */
  --fs-xl:       clamp(1.0625rem, 1rem + 0.3vw, 1.25rem);      /* 17–20px */
  --fs-h:        clamp(1.25rem, 1.15rem + 0.5vw, 1.5rem);      /* 20–24px */
  --fs-display:  clamp(1.625rem, 1.4rem + 1.1vw, 2.25rem);     /* 26–36px */

  --lh-tight:    1.15;
  --lh-data:     1.29;   /* Carbon body-compact-01 ratio: 14/18 */
  --lh-body:     1.5;
  --lh-loose:    1.7;

  --ls-tight:    -0.01em;
  --ls-normal:   0;
  --ls-caps:     0.06em;

  --fw-reg:      400;
  --fw-med:      500;
  --fw-sm:       600;
  --fw-bold:     700;

  /* ---------- SPACING (4px base) ---------- */
  --space-0:   0;
  --space-1:   0.25rem;   /*  4px */
  --space-2:   0.5rem;    /*  8px */
  --space-3:   0.75rem;   /* 12px */
  --space-4:   1rem;      /* 16px */
  --space-5:   1.25rem;   /* 20px */
  --space-6:   1.5rem;    /* 24px */
  --space-7:   2rem;      /* 32px */
  --space-8:   2.5rem;    /* 40px */
  --space-9:   3rem;      /* 48px */
  --space-10:  4rem;      /* 64px */
  --space-11:  5rem;      /* 80px */
  --space-12:  6rem;      /* 96px */

  /* ---------- RADII ---------- */
  --r-xs:    2px;
  --r-sm:    4px;
  --r-md:    6px;
  --r-lg:    10px;
  --r-xl:    14px;
  --r-2xl:   20px;
  --r-full:  9999px;

  /* ---------- SHADOWS & GLOWS ----------
     On dark canvas, traditional drop shadows largely disappear. We layer
     a darker outer shadow with an inner top-edge highlight to fake depth. */
  --shadow-card:     0 1px 0 hsla(210 30% 95% / 0.04) inset,
                     0 1px 2px hsla(0 0% 0% / 0.4),
                     0 4px 12px hsla(0 0% 0% / 0.25);

  --shadow-popover:  0 1px 0 hsla(210 30% 95% / 0.05) inset,
                     0 6px 16px hsla(0 0% 0% / 0.45),
                     0 14px 40px hsla(0 0% 0% / 0.35);

  --shadow-modal:    0 1px 0 hsla(210 30% 95% / 0.06) inset,
                     0 12px 32px hsla(0 0% 0% / 0.55),
                     0 32px 80px hsla(0 0% 0% / 0.45);

  --glow-active:     0 0 0 1px hsla(205 80% 62% / 0.4),
                     0 0 16px 2px hsla(205 80% 62% / 0.18);

  --glow-warn:       0 0 0 1px hsla(39 100% 57% / 0.4),
                     0 0 14px 2px hsla(39 100% 57% / 0.16);

  --focus-ring:      0 0 0 2px var(--surface-1),
                     0 0 0 4px hsla(205 80% 62% / 0.7);

  /* ---------- MOTION ----------
     ease-out-soft is gentle/analytical, never bouncy.
     ease-spring used only for player-card expand and modal entrance. */
  --ease-out-soft:  cubic-bezier(0.22, 1, 0.36, 1);
  --ease-spring:    cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-linear:    linear;

  --dur-instant:    80ms;
  --dur-fast:       140ms;
  --dur-base:       220ms;
  --dur-slow:       360ms;
  --dur-glacial:    600ms;

  /* ---------- Z-INDEX SCALE ---------- */
  --z-base:      0;
  --z-raised:    10;
  --z-sticky:    100;
  --z-drawer:    400;
  --z-overlay:   500;
  --z-popover:   600;
  --z-modal:     700;
  --z-toast:     900;
  --z-debug:     9999;

  /* ---------- LAYOUT ---------- */
  --rail-width-desktop:   220px;
  --rail-width-collapsed: 56px;
  --inspector-width:      360px;
  --bp-mobile:            560px;
  --bp-tablet:            900px;
  --bp-desktop:           1280px;
  --bp-wide:              1680px;
}
```

#### 2.1 Visual psychology notes (for implementers)

- **Why slate-cool, not zinc-neutral or warm-gray?** A cool slate (hue ~200°) reads "analytical" the way warm grays read "editorial." Linear has moved warmer for calm; we deliberately stay slightly cool because the analytical posture is exactly what we want for a quant desk.
- **Why Radix's HSL values specifically?** They are pre-tuned with APCA targeting and ship paired light/dark scales — Radix docs: *"Text colors are guaranteed to pass target contrast ratios against the corresponding background colors."* Using their scales verbatim removes most contrast-tuning labor.
- **Why no green token, anywhere?** Green is reserved across the design language as a no-go because of its cultural binding to "go / good / approve." Even a desaturated emerald reads "valid." We don't want any cell, badge, or arc to suggest "this trade passed."
- **Why amber for both TE position and aging-cliff?** Because TE is the position with the steepest cliff (30) and the warm hue reinforces "watch this." The aging tag uses a different chip *shape* (rounded square with icon) vs the position pill (oval) to prevent confusion.
- **JetBrains Mono for numerics**, per JetBrains' design notes: *"Standard-width letters help keep lines to the expected length. The shape of ovals approaches that of rectangular symbols. This makes the whole pattern of the text more clear-cut. The outer sides of ovals ensure there are no additional obstacles for your eyes as they scan the text vertically."*

---

### Section 3 — Layout System & Responsive Strategy

#### 3.1 Approach: CSS Grid + Container Queries

The whole shell is a **CSS Grid template-areas** layout. Inner panels (player cards, matrix cells, trade lanes) use **container queries** so they restructure based on their *own* width — critical because the same player card lives in a 240px sidebar AND a 1100px Trade Lab lane and must read clearly in both.

Per web.dev's August 2025 Baseline monthly digest, container queries became Baseline Widely Available in August 2025 (30 months after their February 2023 cross-browser debut), and "the majority of sites should now be confident in adopting" them. They require no polyfill and ship cleanly via `file://`.

#### 3.2 Breakpoints

```css
:root {
  --bp-mobile:   560px;   /* below: stacked, read-only flows */
  --bp-tablet:   900px;   /* above: split panes, collapsible rail */
  --bp-desktop: 1280px;   /* above: full rail + main + optional inspector */
  --bp-wide:    1680px;   /* above: rail + main + inspector + Pulse expanded */
}
```

Use media queries **only** for the global shell (rail show/hide). Use container queries for every component.

#### 3.3 Global App Shell

```html
<body class="dg-app">
  <aside class="dg-rail" aria-label="Primary navigation">
    <!-- collapsed icon nav on tablet; expanded on desktop -->
  </aside>

  <header class="dg-topbar">
    <!-- league posture chip, season clock, last-refresh chip, search -->
  </header>

  <main class="dg-main" id="content">
    <!-- view content; container-queried inside -->
  </main>

  <aside class="dg-inspector" data-state="closed" aria-label="Detail inspector">
    <!-- right drawer, slides in from right; backdrop-filter glass -->
  </aside>
</body>
```

```css
.dg-app {
  display: grid;
  min-height: 100vh;
  grid-template-columns: var(--rail-width-desktop) 1fr auto;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    "rail topbar inspector"
    "rail main   inspector";
  background: var(--surface-0);
  color: var(--text-mid);
  font-family: var(--ff-body);
  font-size: var(--fs-body);
  line-height: var(--lh-data);
  font-feature-settings: 'tnum' 1, 'ss01' 1;  /* tabular nums globally */
}
.dg-rail      { grid-area: rail; }
.dg-topbar    { grid-area: topbar; }
.dg-main      { grid-area: main; }
.dg-inspector { grid-area: inspector; width: 0; transition: width var(--dur-base) var(--ease-out-soft); }
.dg-inspector[data-state="open"] { width: var(--inspector-width); }

@media (max-width: 1279px) {
  .dg-app {
    grid-template-columns: var(--rail-width-collapsed) 1fr auto;
  }
}

@media (max-width: 899px) {
  .dg-app {
    grid-template-columns: 1fr;
    grid-template-areas:
      "topbar"
      "main";
  }
  .dg-rail { display: none; }       /* hamburger drawer instead */
  .dg-inspector { display: none; }  /* mobile is read-only; no inspector */
}
```

#### 3.4 Graceful Collapse Rules

| Surface | Desktop (≥1280) | Tablet (900–1279) | Mobile (≤899) |
|---|---|---|---|
| Rail | 220px expanded | 56px icons-only | Hidden, behind hamburger |
| Trade Lab | Side-by-side lanes | Side-by-side, narrower gutters | **Stacked**, sticky lane toggle pill |
| League Pulse Matrix | 12 rows × N columns | Horizontal scroll, sticky team column | Each team = expandable card |
| Roster Audit ring meters | Inline cluster | Inline | Wrap to 2 per row |
| Inspector | Always available (drawer) | Tap-summons | **Not available** (read-only mobile) |
| Player Card Detailed variant | Used in inspector | Used in inspector | Fallback to Standard |

---

### Section 4 — Standalone Trade Lab (Double-Panel Split)

This is the single most important surface. Every decision below exists to enforce **lane separation** so model evaluations and market price discovery can never be conflated.

#### 4.1 HTML Skeleton

```html
<section class="trade-lab" aria-label="Trade Lab">
  <header class="trade-lab__header">
    <h1 class="trade-lab__title">Trade Lab</h1>
    <div class="trade-lab__band" data-state="inside_band" aria-live="polite">
      <span class="band-pill band-pill--inside">Inside band · Δ ±4.1</span>
    </div>
  </header>

  <div class="trade-lab__split">
    <!-- LEFT: MODEL LANE (Engine A) -->
    <section class="lane lane--model" aria-label="Model lane">
      <header class="lane__header">
        <span class="lane__eyebrow">ENGINE A · MODEL</span>
        <h2 class="lane__title">Roster-aware xVAR</h2>
      </header>

      <div class="lane__assets" data-side="give">
        <h3 class="lane__side-label">Sending</h3>
        <ul class="lane__list">
          <li class="player-card player-card--compact" data-pos="rb">...</li>
        </ul>
        <button class="lane__add" type="button">+ add asset</button>
      </div>

      <div class="lane__assets" data-side="get">
        <h3 class="lane__side-label">Receiving</h3>
        <ul class="lane__list">...</ul>
        <button class="lane__add" type="button">+ add asset</button>
      </div>

      <footer class="lane__totals">
        <div class="gauge gauge--xvar">
          <span class="gauge__label">xVAR Δ</span>
          <span class="gauge__value">+12.3</span>
          <span class="gauge__bar" data-direction="positive"></span>
        </div>
        <div class="gauge gauge--consolidation">
          <span class="gauge__label">Consolidation premium</span>
          <span class="gauge__value">+3.8</span>
        </div>
        <div class="capacity-cost">
          <span class="capacity-cost__icon" aria-hidden="true">⌗</span>
          <span class="capacity-cost__text">Forces cut: <strong>AJ Barner</strong> (model val 4.2)</span>
        </div>
      </footer>
    </section>

    <div class="trade-lab__seam" aria-hidden="true"></div>

    <!-- RIGHT: MARKET LANE (Engine B) -->
    <section class="lane lane--market" aria-label="Market lane">
      <header class="lane__header">
        <span class="lane__eyebrow">ENGINE B · MARKET</span>
        <h2 class="lane__title">FantasyCalc overlay</h2>
      </header>

      <div class="lane__assets" data-side="give">
        <h3 class="lane__side-label">Sending</h3>
        <ul class="lane__list">
          <li class="player-card player-card--compact" data-pos="rb">
            <span class="value-pill value-pill--market">7,420</span>
          </li>
          <li class="pick-card" data-pos="pick">
            <span class="pick-card__label">2026 1st (mid)</span>
            <span class="range-band">
              <span class="range-band__track"></span>
              <span class="range-band__fill" style="--lo:30%; --hi:70%"></span>
              <span class="range-band__label">5,200 – 9,600 · ±40%</span>
            </span>
          </li>
        </ul>
        <button class="lane__add" type="button">+ add asset</button>
      </div>

      <div class="lane__assets" data-side="get">...</div>

      <footer class="lane__totals">
        <div class="gauge gauge--market">
          <span class="gauge__label">Market Δ</span>
          <span class="gauge__value">−820</span>
        </div>
      </footer>
    </section>
  </div>
</section>
```

#### 4.2 Lane Visual Separation Strategy

The two lanes are distinct via **four reinforcing signals**, none of which alone is sufficient:

| Signal | Model lane (left) | Market lane (right) |
|---|---|---|
| Background tint | `linear-gradient(180deg, hsla(205 40% 14% / 0.3), transparent 50%)` over `--surface-2` (cool cast) | `linear-gradient(180deg, hsla(28 40% 14% / 0.25), transparent 50%)` over `--surface-2` (warm cast) |
| Top eyebrow label | `ENGINE A · MODEL` in `--signal-positive-delta` mono micro-caps | `ENGINE B · MARKET` in `--signal-negative-delta` mono micro-caps |
| Vertical seam | 1px `--border-strong` divider with `box-shadow: 1px 0 0 var(--border-glass)` | (same seam, shared) |
| Lane accent border (top) | 2px `--signal-positive-delta` at 18% alpha | 2px `--signal-negative-delta` at 18% alpha |
| Number prefix | numerics shown as plain magnitudes | numerics prefixed with `M:` to reinforce "market price" |

Both tints are subtle — saturation under 15% on the canvas, blended via `rgba()` so they never compete with player position colors. The tinting is *just enough* to make a 200ms glance categorize the lane correctly.

#### 4.3 Left Panel — Model Lane Components

**xVAR Delta Gauge.** Horizontal bar with origin in the center, extending right for positive (cool tint) or left for negative (warm tint).

```css
.gauge--xvar .gauge__bar {
  position: relative;
  height: 8px;
  border-radius: var(--r-full);
  background: var(--surface-4);
  overflow: hidden;
}
.gauge--xvar .gauge__bar::before {
  content: '';
  position: absolute;
  inset: 0;
  left: 50%;
  width: var(--magnitude, 30%);
  background: linear-gradient(90deg,
    var(--signal-positive-delta-bg),
    var(--signal-positive-delta));
  border-radius: var(--r-full);
  transition: width var(--dur-base) var(--ease-out-soft);
}
.gauge--xvar .gauge__bar[data-direction="negative"]::before {
  left: auto; right: 50%;
  background: linear-gradient(270deg,
    var(--signal-negative-delta-bg),
    var(--signal-negative-delta));
}
```

**Consolidation Premium Gauge.** Same primitive, capped, single-direction (always positive — consolidation either rewards or doesn't). Sub-label: "Consolidation premium (multi-for-one)."

**Forced-Cut Display.** Pinned at the bottom of the Model lane footer. Surfaces in plain language: *"Forces cut: AJ Barner (model val 4.2). Capacity cost included."* The cut value is added back to the giving side total so the lane shows the net model exchange. The `[⌗ capacity cost]` badge uses `--border-subtle` and `--text-low`.

#### 4.4 Right Panel — Market Lane Components

**Raw FantasyCalc Value Pill.** Monospace number in a `.value-pill--market` chip. Zero hue except a subtle warm-cast border (`hsla(28 60% 34% / 0.4)`). No comparator — it is the raw FC market number.

**Pick Range Band.** Generic picks render as a **horizontal range band** with ±40% volatility:

```css
.range-band {
  display: inline-grid;
  grid-template-rows: 6px auto;
  gap: var(--space-1);
  width: 100%;
}
.range-band__track {
  position: relative;
  background: var(--surface-4);
  border-radius: var(--r-full);
}
.range-band__fill {
  position: absolute;
  inset: 0;
  left: var(--lo);
  right: calc(100% - var(--hi));
  background: linear-gradient(90deg,
    var(--signal-negative-delta-bg),
    var(--signal-negative-delta-bg) 50%,
    var(--signal-negative-delta-bg));
  border-radius: var(--r-full);
  opacity: 0.6;
}
.range-band__label {
  font-family: var(--ff-mono);
  font-size: var(--fs-micro);
  color: var(--text-low);
}
```

**Arbitrage Band State Pill.** Single source of truth at the top of Trade Lab — never duplicated per lane. Three states only:

```html
<span class="band-pill band-pill--model-high">Model higher · Δ +12.3</span>
<span class="band-pill band-pill--market-high">Market higher · Δ −8.7</span>
<span class="band-pill band-pill--inside">Inside band · Δ ±4.1</span>
```

```css
.band-pill {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--r-full);
  font-family: var(--ff-mono);
  font-size: var(--fs-xs);
  letter-spacing: var(--ls-caps);
  text-transform: uppercase;
  border: 1px solid var(--border-subtle);
  background: var(--surface-3);
}
.band-pill--model-high {
  border-color: var(--signal-positive-delta-border);
  background: var(--signal-positive-delta-bg);
  color: var(--signal-positive-delta);
  box-shadow: 0 0 18px hsla(205 80% 62% / 0.18);
}
.band-pill--market-high {
  border-color: var(--signal-negative-delta-border);
  background: var(--signal-negative-delta-bg);
  color: var(--signal-negative-delta);
  box-shadow: 0 0 18px hsla(28 88% 60% / 0.18);
}
.band-pill--inside {
  color: var(--text-mid);
  background: var(--band-inside-bg);
}
```

The band-state determines **which lane glows**. `model_higher_than_market` → Model lane gets a soft cool outer glow. `market_higher_than_model` → Market lane gets a warm glow. `inside_band` → neither lane glows.

#### 4.5 Trade Input UX

**Adding assets.** A search input at each lane's `+ add asset` button. Vanilla JS reads `window.PVO_SNAPSHOT` and renders a filtered dropdown. Items are added by `Enter` or click. No drag-and-drop on v1 — drag is hard to get right in vanilla and breaks on touch.

**Totals.** Each lane footer auto-recomputes on mutation. Each lane shows its own subtotal in its own value vocabulary (xVAR for Model, raw FC value for Market). The arbitrage band pill at the top is the *only* place the two subtotals are compared.

**Asymmetry visualization.** When sides differ in count, a horizontal **ledger line** beneath each side shows: `Sending 3 · Receiving 1`. Never use the word "consolidation" pejoratively; surface only the count and let the Consolidation Premium gauge speak.

#### 4.6 Mobile Collapse (≤899px)

```html
<div class="trade-lab__lane-toggle" role="tablist" aria-label="Lane">
  <button role="tab" aria-selected="true"  data-target="model">Model</button>
  <button role="tab" aria-selected="false" data-target="market">Market</button>
</div>
```

Sticky-positioned (`position: sticky; top: 0`). Lanes stack below; active lane is full width; inactive lane collapses to a 1-line summary strip showing band state + lane subtotal so the user retains awareness.

---

### Section 5 — Roster Audit & Capacity Gauges

#### 5.1 Circular Ring Meters

Three meters: Active roster (e.g., 23/26), Taxi squad (5/5 triggers warning), IR (e.g., 2/4). Construction follows the standard SVG `stroke-dasharray` / `stroke-dashoffset` pattern (per CSS-Tricks "Building a Progress Ring, Quickly"). Circumference computed once at render; `stroke-dashoffset = circumference * (1 - progress)`.

```html
<figure class="ring-meter" data-state="ok" aria-labelledby="rm-active-label">
  <svg viewBox="0 0 120 120" width="96" height="96" aria-hidden="true">
    <circle class="ring-meter__track" cx="60" cy="60" r="54"
            fill="none" stroke-width="10"></circle>
    <circle class="ring-meter__indicator" cx="60" cy="60" r="54"
            fill="none" stroke-width="10" stroke-linecap="round"
            style="--circumference: 339.292; --progress: 0.885;
                   stroke-dasharray: 339.292;
                   stroke-dashoffset: calc(339.292 * (1 - 0.885));"></circle>
  </svg>
  <figcaption class="ring-meter__caption">
    <span class="ring-meter__value">23/26</span>
    <span id="rm-active-label" class="ring-meter__label">Active roster</span>
  </figcaption>
</figure>
```

```css
.ring-meter__track {
  stroke: var(--surface-4);
}
.ring-meter__indicator {
  stroke: var(--signal-positive-delta);
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
  transition: stroke-dashoffset var(--dur-slow) var(--ease-out-soft);
}
.ring-meter[data-state="warn"] .ring-meter__indicator {
  stroke: var(--warn-age);
}
.ring-meter[data-state="warn"] {
  filter: drop-shadow(0 0 8px hsla(39 100% 57% / 0.25));
  animation: pulse-glow 2s var(--ease-out-soft) infinite;
}
```

| State | Trigger | Indicator color |
|---|---|---|
| `ok` | utilization < 95% | `--signal-positive-delta` |
| `near` | 95–100% but not full | `--text-mid` |
| `warn` | utilization = 100% (taxi 5/5, IR 4/4) | `--warn-age` + pulse glow |

The full-taxi case explicitly triggers warn state — fulfilling the "5/5 — full triggers visual warning" requirement.

#### 5.2 Cut-Candidate Cards

Each candidate is a Standard variant Player Card (§7) with:

1. **Cliff warning tag** (if age ≥ position cliff threshold):
   ```html
   <span class="age">26.4 y.o.</span>
   <span class="cliff-tag" data-pos="rb">
     <svg aria-hidden="true" width="10" height="10"><path d="M5 1 L9 8 L1 8 Z" fill="currentColor"/></svg>
     Cliff
   </span>
   ```
2. **Inline model-vs-market magnitude bar** beneath the values.
3. **Subtle "Mark as cut candidate" affordance** — text-button styled with 1px `--border-subtle` outline. No icon. No color.

The cliff tag uses `--warn-age` (amber, not red) — a *consideration*, not a verdict.

#### 5.3 Advisory Drop List

Container carries `aria-label="Advisory considerations"` and a visible micro-label above the list reads `CONSIDERATIONS · NOT ACTIONS`. There is no "drop" button. The only affordance per row is a checkbox toggle labeled `Mark as cut candidate`, which writes a `localStorage` flag and visually adds the candidate to a "marked" subset but **does not invoke any backend action**.

---

### Section 6 — League Pulse Matrix (12-Team Heatmap)

#### 6.1 Structure

```html
<section class="league-pulse" aria-labelledby="lp-title">
  <h2 id="lp-title">League Pulse</h2>
  <div class="league-pulse__scroll">
    <table class="pulse-matrix" role="table" aria-describedby="pulse-caption">
      <caption id="pulse-caption" class="visually-hidden">
        Twelve teams scored across positional xVAR, future draft capital, posture, and tradeable opportunities. Cells encode value via background tint on a blue-amber divergent scale.
      </caption>
      <thead>
        <tr>
          <th scope="col" class="pulse-matrix__sticky">Team</th>
          <th scope="col">QB xVAR</th>
          <th scope="col">RB xVAR</th>
          <th scope="col">WR xVAR</th>
          <th scope="col">TE xVAR</th>
          <th scope="col">2026 picks</th>
          <th scope="col">2027 picks</th>
          <th scope="col">2028 picks</th>
          <th scope="col">Posture</th>
          <th scope="col">Opportunities</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row" class="pulse-matrix__sticky">Woodbury Riders</th>
          <td class="cell" style="--tint: 0.6;" data-direction="positive"
              aria-label="QB xVAR 8.4, top quartile">8.4</td>
          <td class="cell" style="--tint: 0.2;" data-direction="negative"
              aria-label="RB xVAR -2.1, bottom quartile">-2.1</td>
          <!-- ... -->
          <td class="posture-cell">
            <span class="posture-pill posture-pill--rebuilder">Rebuilder</span>
          </td>
          <td class="opportunities-cell">
            <span class="opp-tag opp-tag--surplus" data-pos="wr">WR surplus</span>
            <span class="opp-tag opp-tag--gap" data-pos="rb">RB gap</span>
            <span class="opp-tag opp-tag--rich" data-pos="pick">2027 pick rich</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
```

#### 6.2 Divergent Heatmap Cells

Each xVAR cell carries `--tint` (0.0–1.0, set by JS based on z-score). Background interpolates from neutral toward `--signal-positive-delta-bg` (positive) or `--signal-negative-delta-bg` (negative) — the same blue/amber divergent axis used system-wide. Colorblind-safe, non-verdict, perceptually uniform via `color-mix(in oklab, …)`.

```css
.cell {
  font-family: var(--ff-mono);
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
  text-align: right;
  padding: var(--space-2) var(--space-3);
  background-color: var(--surface-3);
  border-right: 1px solid var(--border-subtle);
}
.cell[data-direction="positive"] {
  background-color: color-mix(
    in oklab,
    var(--surface-3),
    var(--signal-positive-delta-bg) calc(var(--tint, 0) * 100%)
  );
  color: color-mix(in oklab, var(--text-hi), var(--signal-positive-delta) calc(var(--tint,0) * 60%));
}
.cell[data-direction="negative"] {
  background-color: color-mix(
    in oklab,
    var(--surface-3),
    var(--signal-negative-delta-bg) calc(var(--tint, 0) * 100%)
  );
}
```

#### 6.3 Posture Tag Pills

| Tag | Class | Visual |
|---|---|---|
| Championship Contender | `.posture-pill--contender` | Warm amber border, amber-12 text, faint amber-bg fill |
| Rebuilder | `.posture-pill--rebuilder` | Cool azure border, signal-positive text, faint cool fill |
| Reloading | `.posture-pill--reloading` | Neutral slate-7 border, slate-12 text, slate-3 fill |
| Drift | `.posture-pill--drift` | Desaturated slate-6 *dashed* border, slate-11 text, no fill |

The dashed border on "Drift" communicates *unsettled posture* visually without a color verdict.

#### 6.4 Opportunities Column

Inline tag clusters per team. Each `.opp-tag` is a micro-pill (`--fs-micro`, height 18px) with:

- Position color border (cool for picks, position hue for positions)
- Icon glyph (`+`, `−`, `※`)
- Brief text: "RB surplus", "QB gap", "2027 pick rich"

#### 6.5 Sticky Team Column & Mobile Collapse

The team-name `<th scope="row">` is `position: sticky; left: 0`. On tablet, the matrix scrolls horizontally inside `.league-pulse__scroll`. On mobile, the matrix transforms into a stack of expandable cards via a container query — one card per team, summary collapsed (posture pill + top opportunity) until tapped.

```css
@container (max-width: 700px) {
  .pulse-matrix { display: block; }
  .pulse-matrix thead { display: none; }
  .pulse-matrix tbody tr { display: grid; /* card layout */ }
}
```

---

### Section 7 — Player Card Component (Reusable Atom)

#### 7.1 Variants

| Variant | Class modifier | Height | Used in |
|---|---|---|---|
| Compact | `.player-card--compact` | ~64px | Lane lists, drop lists, search results |
| Standard | `.player-card--standard` | ~120px | Matrix cell expansion, cut-candidate cards |
| Detailed | `.player-card--detailed` | ~280px | Right inspector panel only |

#### 7.2 HTML Skeleton

```html
<article class="player-card player-card--standard"
         data-pos="rb" data-stale="false"
         aria-label="Bijan Robinson, RB, ATL">
  <span class="player-card__pos-pill" aria-hidden="true">RB</span>
  <header class="player-card__head">
    <h3 class="player-card__name">Bijan Robinson</h3>
    <div class="player-card__meta">
      <span class="player-card__team">ATL</span>
      <span class="player-card__age">24.1 y.o.</span>
    </div>
  </header>

  <dl class="player-card__values">
    <div class="player-card__value">
      <dt>Model</dt><dd class="num">12.4</dd>
    </div>
    <div class="player-card__value">
      <dt>Market</dt><dd class="num">7,820</dd>
    </div>
    <div class="player-card__value">
      <dt>Arb</dt><dd><span class="band-pill band-pill--model-high">Model +1.6σ</span></dd>
    </div>
  </dl>

  <footer class="player-card__stale">
    <span class="stale-dot" aria-hidden="true"></span>
    Last refreshed 14h ago
  </footer>
</article>
```

#### 7.3 Position Pill

24×24 rounded square. Position abbreviation in `--ff-mono`, `--fw-bold`, `--fs-xs`. Background uses `var(--pos-{pos}-bg)`, text uses `var(--pos-{pos})`, 1px border `var(--pos-{pos}-border)`. The cliff tag (when present) sits adjacent and uses `--warn-age` styling — *rounded-square* shape vs the *oval* position pill, never the same shape.

#### 7.4 Cliff Warning Tag

```css
.cliff-tag {
  display: inline-flex; align-items: center; gap: 4px;
  height: 18px; padding: 0 6px;
  border-radius: var(--r-sm);
  background: var(--warn-age-bg);
  color: var(--warn-age);
  border: 1px solid var(--warn-age-border);
  font-family: var(--ff-mono);
  font-size: var(--fs-micro);
  letter-spacing: var(--ls-caps);
  text-transform: uppercase;
}
```

#### 7.5 Container Query Sizing

```css
.player-card {
  container-type: inline-size;
  background: var(--surface-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r-md);
  border-left: 3px solid var(--pos-rb);
  padding: var(--space-3) var(--space-4);
  transition: transform var(--dur-fast) var(--ease-out-soft),
              box-shadow var(--dur-fast) var(--ease-out-soft);
}
.player-card[data-pos="qb"]   { border-left-color: var(--pos-qb); }
.player-card[data-pos="rb"]   { border-left-color: var(--pos-rb); }
.player-card[data-pos="wr"]   { border-left-color: var(--pos-wr); }
.player-card[data-pos="te"]   { border-left-color: var(--pos-te); }
.player-card[data-pos="pick"] { border-left-color: var(--pos-pick); }

@container (max-width: 320px) {
  /* compact mode */
  .player-card__values { display: none; }
}
```

---

### Section 8 — Micro-Animations & Dynamic States

All animations honor `prefers-reduced-motion`. The reduced-motion fallback is **not** "no animation" — it is "opacity-only fade." Scaling, translating, and pulsing are vestibular triggers; opacity is safe.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

#### 8.1 Card Expand

```css
.player-card--detailed {
  max-height: 0;
  overflow: hidden;
  transition: max-height var(--dur-slow) var(--ease-spring),
              padding var(--dur-slow) var(--ease-spring);
}
.player-card--detailed[data-state="open"] {
  max-height: 320px;
  padding: var(--space-4);
}
.player-card--detailed > * {
  opacity: 0;
  transform: translateY(4px);
  transition: opacity var(--dur-base) var(--ease-out-soft) calc(var(--i, 0) * 40ms),
              transform var(--dur-base) var(--ease-out-soft) calc(var(--i, 0) * 40ms);
}
.player-card--detailed[data-state="open"] > * {
  opacity: 1;
  transform: translateY(0);
}
```

#### 8.2 Tab Switch (Sliding Underline)

```html
<div role="tablist" class="tabs">
  <button role="tab" aria-selected="true">Model</button>
  <button role="tab" aria-selected="false">Market</button>
  <span class="tabs__indicator" aria-hidden="true"
        style="--tab-x: 0px; --tab-w: 70px;"></span>
</div>
```

```css
.tabs { position: relative; }
.tabs__indicator {
  position: absolute; bottom: 0; left: 0; height: 2px;
  width: var(--tab-w, 60px);
  transform: translateX(var(--tab-x, 0));
  background: var(--signal-positive-delta);
  transition: transform var(--dur-base) var(--ease-out-soft),
              width var(--dur-base) var(--ease-out-soft);
}
.tabs [role="tabpanel"] {
  transition: opacity var(--dur-base) var(--ease-out-soft);
}
.tabs [role="tabpanel"][hidden] { opacity: 0; }
```

#### 8.3 Hover Lift

```css
.player-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card),
              0 6px 14px hsla(0 0% 0% / 0.3);
}
```

#### 8.4 Live Pulse Rings (Active Picks / Live Waivers)

Breathing glow only — **never scale or translate** (vestibular safety).

```css
@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 0 1px hsla(205 80% 62% / 0.35),
                0 0 12px 2px hsla(205 80% 62% / 0.12);
  }
  50% {
    box-shadow: 0 0 0 1px hsla(205 80% 62% / 0.6),
                0 0 22px 6px hsla(205 80% 62% / 0.28);
  }
}
.is-live { animation: pulse-glow 2s var(--ease-out-soft) infinite; }

@media (prefers-reduced-motion: reduce) {
  .is-live {
    animation: none;
    box-shadow: 0 0 0 1px hsla(205 80% 62% / 0.5);
  }
}
```

#### 8.5 Stale Data Degradation

```css
.is-stale {
  filter: saturate(0.6) brightness(0.92);
  border-style: dashed;
  border-color: var(--warn-stale);
}
.is-stale .player-card__stale {
  display: flex;
}
.is-stale .stale-dot {
  width: 6px; height: 6px;
  border-radius: var(--r-full);
  background: var(--warn-stale);
  display: inline-block;
}
```

JS sets `data-stale="true"` and toggles `.is-stale` when `Date.now() - pvo.snapshot_ts_ms > THRESHOLD` (default 6h, configurable per surface).

#### 8.6 Skeleton Loaders

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--surface-3) 0%,
    var(--surface-4) 50%,
    var(--surface-3) 100%);
  background-size: 200% 100%;
  animation: skeleton-sweep 1.4s linear infinite;
  border-radius: var(--r-sm);
}
@keyframes skeleton-sweep {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; opacity: 0.6; }
}
```

#### 8.7 Number Ticker (Subtle, No Celebration)

```css
.num--changed {
  animation: num-flash var(--dur-base) var(--ease-out-soft);
}
@keyframes num-flash {
  0%   { background-color: transparent; }
  30%  { background-color: hsla(205 80% 62% / 0.18); }
  100% { background-color: transparent; }
}
.num--changed[data-direction="negative"] {
  animation-name: num-flash-warm;
}
```

JS animates the integer with `requestAnimationFrame` over 220ms using `easeOutQuart`. No celebratory leap; the value glides.

---

### Section 9 — Accessibility & Density Considerations

#### 9.1 Contrast Verification Approach

Every color combination must pass **WCAG 2.2 AA**: 4.5:1 for normal text, 3:1 for large text (≥18pt or 14pt bold). Because Radix Colors scales are pre-tuned against APCA — Radix docs explicitly state *"Text colors are guaranteed to pass target contrast ratios against the corresponding background colors. Contrast targets are based on the modern APCA contrast algorithm, which accurately predicts how human vision perceives text"* — combinations of `--text-hi`/`--text-mid` on `--surface-{1,2,3}` already pass.

**Verification gates** (implementing agent runs these once at build and on every token change):

1. `--text-mid` on `--surface-2`: ≥ 4.5:1.
2. `--text-hi` on every surface: ≥ 7:1 (AAA target for key numbers).
3. Every position color used as *text* on `--surface-3`: ≥ 4.5:1. As borders/pills: ≥ 3:1 against adjacent surface.
4. `--signal-positive-delta` and `--signal-negative-delta` as text on their own `-bg` token: ≥ 4.5:1.

Build a `scripts/contrast-check.js` that computes APCA values for each token pair and outputs a report. No npm dependency — APCA is ~80 lines of vanilla JS.

#### 9.2 Keyboard Navigation

Tab order in Trade Lab:

1. Lane Add buttons (left, then right)
2. Each player card in lane lists (top to bottom, within lane)
3. Lane subtotal gauges (read-only, not focusable)
4. Arbitrage band pill (focusable for `aria-live` re-read)
5. Inspector toggles, then modal controls

```css
:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--r-sm);
}
```

`--focus-ring` is a double-ring (surface-1 inset, then 2px cool-azure outer) so it stays visible on every surface tier.

#### 9.3 Screen Reader Patterns for the Matrix

The Pulse Matrix is a true `<table>` with `<caption>`. Every data cell carries an explicit `aria-label`:

```html
<td class="cell" aria-label="Woodbury Riders, QB xVAR 8.4, top quartile in league"
    style="--tint: 0.7;" data-direction="positive">8.4</td>
```

Posture pills: `role="status"`. Opportunity clusters: wrapped in `<ul>` with `aria-label="Tradeable opportunities"`. The arbitrage band pill at the top of Trade Lab uses `aria-live="polite"` so screen readers announce state changes.

#### 9.4 Reduced-Motion Coverage

| Animation | Default | Reduced-motion fallback |
|---|---|---|
| Card hover lift | translateY(-2px) + shadow | shadow only, no transform |
| Pulse glow rings | box-shadow keyframe loop | static box-shadow at peak |
| Skeleton sweep | gradient translation | static dim opacity 0.6 |
| Tab indicator slide | transform translateX | opacity crossfade |
| Card expand | max-height + spring | display block + opacity fade |
| Number ticker | rAF count-up + bg flash | snap to value, no flash |

#### 9.5 Density Without Wall-of-Text

Per Carbon Design System's `body-compact-01` token (carbondesignsystem.com/guidelines/typography/type-sets/): *"body-compact-01 — Type: IBM Plex Sans, Size: 14px / .875rem, Line height: 18px / 1.125rem, Weight: 400 / Regular, Letter spacing: .16px. This is for short paragraphs with no more than four lines and is commonly used in components."*

Specific guidance:

- **Tables and matrix cells**: `font-size: var(--fs-sm)` (~13px), `line-height: var(--lh-data)` (1.29).
- **Numerics anywhere**: `font-family: var(--ff-mono)` + `font-variant-numeric: tabular-nums`.
- **Micro-labels** (column heads, eyebrows): `--fs-micro`, `--ls-caps` (0.06em), uppercase.
- **Grouping rhythm**: 8–12px gaps within a group (`--space-2`/`--space-3`); 24–32px between groups (`--space-6`/`--space-7`). Never use horizontal rules inside a panel — use spacing.
- **Borders as grouping**: 1px `--border-subtle` is enough on the dark canvas. Heavier borders reserved for lane separation.

---

### Section 10 — Implementation Notes for Developer Agents

#### 10.1 File Structure

```
/static/
  index.html
  /css/
    tokens.css                  # :root design tokens — copy from §2 verbatim
    base.css                    # CSS reset, body, typography, focus rings, .visually-hidden, .is-stale
    layout.css                  # app shell grid, rail, topbar, main, inspector
    /components/
      trade-lab.css
      roster-audit.css
      league-pulse.css
      player-card.css
      ring-meter.css
      gauge.css
      band-pill.css
      posture-pill.css
      skeleton.css
  /js/
    app.js                      # boot: load resources, mount views, hash-route
    trade-lab.js                # add/remove/totals/band-state
    roster-audit.js             # ring meters, cut-candidate list
    league-pulse.js             # matrix render, sort, sticky
    inspector.js                # right-panel open/close, content swap
    contrast-check.js           # dev-only token contrast validator
  /resources/
    prospect_cards.js           # window.PROSPECT_CARDS = [...]
    pvo_snapshot.js             # window.PVO_SNAPSHOT = {...}
    league_context.js           # window.LEAGUE_CONTEXT = {...}
```

`index.html` loads CSS in dependency order: `tokens.css` → `base.css` → `layout.css` → `components/*.css`. JS loads `resources/*.js` first (so globals are populated), then `js/app.js`.

#### 10.2 BEM Naming Convention

Standard BEM (`block__element--modifier`). No utility framework. Block names are component-scoped. Examples:

- `.player-card`, `.player-card__pos-pill`, `.player-card--compact`, `.player-card--detailed`
- `.lane`, `.lane__header`, `.lane__totals`, `.lane--model`, `.lane--market`
- `.gauge`, `.gauge__label`, `.gauge__value`, `.gauge--xvar`, `.gauge--consolidation`
- `.ring-meter`, `.ring-meter__track`, `.ring-meter__indicator`, `.ring-meter__caption`
- `.band-pill`, `.band-pill--model-high`, `.band-pill--market-high`, `.band-pill--inside`
- `.posture-pill`, `.posture-pill--contender`, `.posture-pill--rebuilder`, `.posture-pill--reloading`, `.posture-pill--drift`
- `.pulse-matrix`, `.pulse-matrix__sticky`
- `.cell` (used inside `.pulse-matrix` only)
- `.opp-tag`, `.opp-tag--surplus`, `.opp-tag--gap`, `.opp-tag--rich`
- `.cliff-tag` (standalone atom)
- `.skeleton` (modifier-less; consumers apply sizing via inline style)

**State as `data-*` attributes**, not classes, when JS-controlled and `aria-*`-paired: `data-state="open"`, `data-direction="positive"`, `data-stale="true"`. CSS uses attribute selectors. This keeps JS thin and markup self-describing.

#### 10.3 Data Contracts (illustrative)

Files are vanilla JS assigning to `window.*`. Shapes documented as JSDoc inside files:

```js
// resources/pvo_snapshot.js
// PVO = Player Value Object. Produced upstream by Engine A + Engine B.
// The UI MUST treat this as read-only and MUST NOT recompute values.
window.PVO_SNAPSHOT = {
  snapshot_ts_ms: 1748044800000,
  players: [
    {
      player_id: "4881",                  // Sleeper ID
      full_name: "Bijan Robinson",
      pos: "RB",                          // "QB" | "RB" | "WR" | "TE"
      team: "ATL",
      age: 24.1,
      // Engine A — Model
      model_value: 12.4,
      model_value_lo: 10.8,
      model_value_hi: 14.0,
      // Engine B — Market
      market_value: 7820,
      // Cross-engine
      arb_state: "model_higher_than_market",
      arb_z: 1.6,
      // Capacity
      forces_cut: null,                   // null | { player_id, full_name, model_value }
      consolidation_premium: 0,
      // Metadata
      stale: false,
      last_refreshed_ms: 1748044800000
    }
  ],
  picks: [
    {
      pick_id: "2026-1-mid",
      label: "2026 1st (mid)",
      market_value_lo: 5200,
      market_value_hi: 9600,
      market_value_mid: 7400,
      volatility_pct: 0.40
    }
  ]
};
```

```js
// resources/league_context.js
window.LEAGUE_CONTEXT = {
  league_id: "1314363401744416768",
  league_name: "Redzone Champions League",
  user_roster_id: 1,
  user_team_name: "Woodbury Riders",
  format: { teams: 12, superflex: true, ppr: 1.0 },
  posture_by_roster: { "1": "rebuilder", "2": "contender" },
  team_xvar: {
    "1": { QB: 2.1, RB: -2.1, WR: 4.3, TE: -1.0 }
  },
  team_picks: { "1": { "2026": 4, "2027": 5, "2028": 3 } },
  opportunities_by_roster: {
    "1": [
      { kind: "surplus", pos: "WR" },
      { kind: "gap", pos: "RB" },
      { kind: "rich", pos: "pick", season: "2027" }
    ]
  }
};
```

```js
// resources/prospect_cards.js
window.PROSPECT_CARDS = [
  {
    prospect_id: "p_2026_001",
    full_name: "Travis Hunter",
    pos: "WR",
    college: "COL",
    rookie_class: 2025,
    model_value: 14.8,
    model_lo: 11.2,
    model_hi: 18.4,
    stale: false
  }
];
```

#### 10.4 Browser Support Targets

- **Modern evergreen Chrome, Safari, Firefox, Edge** (last 2 major versions).
- **CSS Container Queries**: required, no polyfill. Per web.dev's August 2025 Baseline monthly digest, container queries became Baseline Widely Available in August 2025 (30 months after their February 2023 cross-browser debut), and "the majority of sites should now be confident in adopting" them.
- **`backdrop-filter`**: required for `--surface-glass`. Falls back gracefully via `@supports (backdrop-filter: blur(1px))` to solid `--surface-3`.
- **`color-mix(in oklab, …)`**: required for heatmap interpolation. Stable in evergreen Chrome 111+, Safari 16.4+, Firefox 113+. Fallback: pre-compute discrete tint stops in JS and write inline `background-color`.
- **CSS nesting**: acceptable in component CSS. Avoid in `tokens.css` to keep tokens flat and grep-able.
- **No build step. No bundler. No npm. No CDN runtime dependency.** Google Fonts `<link>` is acceptable when network is present but the site **must function fully without it** — `--ff-body`/`--ff-display` fall back through `system-ui` to `-apple-system`. JetBrains Mono falls back to `ui-monospace` then `Menlo`. **Recommended for `file://` reliability**: download the fonts once and bundle into `/static/fonts/`.

#### 10.5 Graceful Degradation: Missing / Stale Data

| Condition | UI behavior |
|---|---|
| PVO missing for a roster slot | Slot renders as `.player-card.skeleton`; no error toast; `aria-label="Player data unavailable"`. |
| `model_value` present, `market_value` absent | Card shows model value, market column reads `—`, arbitrage pill is `band-pill--inside` styled and reads "Market data unavailable". |
| `stale === true` OR `Date.now() - snapshot_ts_ms > 6 * 3600 * 1000` | Card receives `.is-stale`; saturation 0.6; dashed border; footer "Last refreshed Xh ago". League Pulse cells also dim. |
| Entire `PVO_SNAPSHOT` absent | App boots to empty-state with one instructional card: "No PVO snapshot loaded. Generate `resources/pvo_snapshot.js` from the upstream engines and refresh." No spinner. |
| Resource file fails to parse | Browser console error; app continues rendering whatever DID load. **Never** render a half-blank panel without a visible empty-state explanation. |

#### 10.6 What Implementing Agents Must Not Do

Binding. Any deviation requires architectural review.

1. **No build step, bundler, or npm dependency.** Every line in `/static/` must be plain HTML/CSS/JS readable on disk.
2. **Do not recompute, re-weight, or invent a value.** The UI reads PVO objects and renders. If a number isn't in the PVO, the UI says "unavailable" — never imputes.
3. **No green or red as a primary signal hue.** Blue/amber is the entire signal system. Position colors live in a separate semantic space and never overlap with state colors.
4. **No "buy / sell / win / loss / approve / reject / good / bad / yes / no" in any user-facing copy.** Use "model higher", "market higher", "inside band", "consideration", "tradeoff", "capacity cost", "aging cliff".
5. **No "submit trade" button.** Dynasty Genius surfaces considerations. It does not execute.
6. **No scale or large-translation animation.** Only opacity, color, box-shadow, and small (≤4px) translations are permitted, all gated by `prefers-reduced-motion`.
7. **Never skip the `.is-stale` styling when data is stale.** The user must always know what they are looking at.

---

## Recommendations (Staged Implementation)

1. **Stage 1 — Foundations (Day 1).** Land `tokens.css`, `base.css`, `layout.css`, and the app shell (§3). Validate contrast via `scripts/contrast-check.js`. **Threshold to advance:** all four breakpoints render the shell with no overflow; all tokens used by `base.css` pass AA on `--surface-2`.

2. **Stage 2 — The Atom (Day 2).** Land the Player Card (§7) in all three variants with container-query layout. Static demo page with one of each variant per position. **Threshold to advance:** all five position hues render with their tag chips, cliff tag triggers at correct age thresholds, hover lift and focus ring are visible.

3. **Stage 3 — Trade Lab (Days 3–4).** Land the double-panel Trade Lab (§4) with vanilla JS for add/remove/totals/band state. **Glance test**: at <500ms, can you tell which lane is which? If not, increase tint saturation by 5%. **Threshold to advance:** band-pill state transitions correctly across all three arbitrage states; mobile lane toggle works; no buy/sell language anywhere in the DOM.

4. **Stage 4 — Roster Audit (Day 5).** Land ring meters (§5), cut-candidate list, advisory drop list. The 5/5 taxi-full case must trigger the warn glow. **Threshold to advance:** ring math correct (rendered arc matches numeric value within 1°); cliff warnings trigger at the correct positional thresholds.

5. **Stage 5 — League Pulse (Day 6).** Land the 12-row matrix (§6) with sticky team column, divergent heatmap, posture pills, opportunity tags. **Threshold to advance:** matrix scrolls correctly on tablet, collapses to cards on mobile, screen-reader walkthrough reads each cell's full context.

6. **Stage 6 — Polish (Day 7).** Skeleton loaders, stale-data degradation, micro-animations, reduced-motion. **Threshold to advance:** the entire app boots from `file://` with `Network: Offline` in DevTools and renders correctly using only the on-disk resources.

**Benchmarks that should change recommendations:**

- If contrast script reports any token pair below AA on the canvas, **block release** and adjust the token; do not adjust component CSS.
- If the user reports lanes "feel similar" after Stage 3, **increase lane-tint saturation by 5% increments** and rerun the glance test until they read distinctly.
- If `prefers-reduced-motion` users report residual motion sickness, **strip the animation entirely** from that surface; opacity-only is the floor.

---

## Caveats

- **The `--rb` teal vs `--te` amber proximity.** Teal-cyan and amber-gold are well-separated on the color wheel (≈140°), but on a small position pill at 14px they may briefly resemble each other for some viewers. The position pill always carries the *letter* abbreviation as text — the color is reinforcement, not the primary signal.
- **Browser `color-mix(in oklab, …)` support.** Stable in evergreen Chrome 111+, Safari 16.4+, Firefox 113+. For older environments, fall back to JS-computed discrete tint stops written to inline `background-color`.
- **`backdrop-filter` performance on dense surfaces.** Per LambdaTest's CSS Backdrop Filter reference guide: *"Large blur radii on full-screen backdrops drop frame rates on low-end Android phones. Cap the radius at 12 to 16 pixels and avoid stacking multiple blurred surfaces in the same scroll area."* Glass is reserved for the inspector and modals only — never for the main canvas or matrix cells.
- **The "Drift" posture pill's dashed border** is a non-color signal that may not render distinctly on very low-DPI displays. The pill text ("Drift") carries the semantic load; the dashed border is reinforcement.
- **Container queries on the league-pulse matrix.** A `<table>` cannot directly be a container; `container-type` is set on the wrapping `.league-pulse__scroll` div. The card-collapse below 700px is container-queried on the *wrapper*, not the table. Follow the wrapper-as-container pattern throughout — designate the parent of the responsive component, never the responsive component itself.
- **Source mix.** Authoritative anchors include Radix Colors (radix-ui.com/colors), Carbon Design System (carbondesignsystem.com), MDN, Linear's own blog (linear.app/now), Bloomberg LP's UX article, and Bang Wong's *Nature Methods* paper (doi:10.1038/nmeth.1618). Tertiary corroborating sources (Medium, dev.to, LogRocket) inform stylistic choices but are not load-bearing for tokens, contrast, or accessibility rules.
- **Future engine expansion.** The Trade Lab currently assumes exactly two engines. If a future Engine C arrives (e.g., a sentiment overlay), the double-panel split becomes a triple-panel split, at which point the lane-tint strategy needs a third hue. Recommend: cool azure (Engine A) → neutral slate (Engine C) → warm amber (Engine B). The neutral middle reads as "context" rather than "third opinion."
- **Sleeper integration scope.** This spec covers presentation only. The pipeline from Sleeper's API → Engine A (xVAR) → Engine B (FantasyCalc overlay) → PVO snapshot files is out of scope for this document and lives in the Python/FastAPI backend.