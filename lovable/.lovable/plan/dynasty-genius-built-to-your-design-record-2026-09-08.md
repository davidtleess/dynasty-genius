# Dynasty Genius — built to your design record

## What I read

All three repos are public, so I read them: **dynasty-genius** (the local Python/FastAPI system,
~15 GB of data and trained models, plus the React frontend; `PRODUCT.md` and `DESIGN.md`),
**dg-build** (the board, the DG-091 design brief and Studio spec, and the 1440/390 comps), and
**dg-cockpit** (Mac cockpit and agent tooling — reference only, nothing from it ships).

Your design record above is now the controlling document. Where it conflicts with the older
specs in the repos, the record wins.

Confirmed from Sleeper: **Redzone Champions League**, 2026, 12 teams, dynasty, Superflex, full
PPR, no TE premium — your team is **Woodbury Riders**.

Honest limit: the trained model files and multi-gigabyte history can't run inside this app. The
market lane and the production inputs come from live free feeds; our own valuation is computed
here and versioned. Nothing is estimated silently — missing is said, never rendered as zero.

## What the product is for (your rulings, applied)

- **Full Sleeper universe, all year.** Not a my-roster tool. Every player, every rival roster.
- **Rank against rank is the main number** on the roster page and the player card — not a
  0–100 score, because a five-year rank beside another model's number is apples vs oranges.
- **The margin — our value vs the market's — is the killer secondary column**, present on every
  player, heat-mapped, but not a standalone hero surface (your 8 July revision stands).
- **The edge is separating look-alikes and surfacing the non-obvious**: two round-one WRs of the
  same age must resolve to which one produces. A board that just re-sorts on draft capital and
  age fails.
- Trends are secondary and earn little surface. Level comparison outranks overnight movement.

## Screens

Roster first, per your 8 September call. Rail nav; parked items (Rookie Board, Waiver Radar,
Research Assistant, Project Tracker) are out of the rail and reachable by URL only.

1. **Roster** — your players grouped by position, Sleeper-style, alternatives arriving without
   the roster leaving the screen. Columns: our rank, market rank, margin, tier, age. Cut
   pressure shown as a sort of the same table, not a second screen.
2. **Value board** — one board engine, three scope presets: My Roster · League Rosters · Full
   Comparable Universe. Roster-scoped is the daily entry point. Team and roster scopes are
   position-grouped; the universe scope is overall rank with position filters. Watchlist
   included (your 8 September reversal).
3. **League** — 12 team cards: our valuation of each roster next to what that manager appears
   to value it at, which is where the actionable difference lives.
4. **Trades** — builder stating the arithmetic on both pricings and naming the disagreement,
   with no take-or-pass imperative. Who-to-call partner cards.
5. **Player card** — a drawer over any surface, opened from any player name anywhere, state in
   the URL. Rank vs rank, margin, tier with its disclosed basis, production and age context, and
   a chart that carries position-cohort bands inside it rather than a bare line.
6. **Track record** — how the model has actually done, in plain prose.

The inspector stays a compact neutral preview with a plain count — no grade, no edge, no delta,
no warning glyph. The full evidence card lives on its own page.

No screen nominates its own hero. Single-player emphasis is legal only when you select it, you
supply it, it's aggregate, or it's lane-symmetric and non-actionable.

## How it speaks

- Football, fantasy, dynasty-manager prose. No system nouns or pipeline keys on screen; a copy
  dictionary maps every backend token to human words and an unmapped key never reaches body copy.
- Qualitative labels and named cohorts are allowed: **Generational** (top 1%, your word) ·
  **Elite** · **Cornerstone** · **Starter** · **Depth**. A tier renders only when a calibration
  earns it, against the field and the historicals, with the basis disclosed on press. Hand-
  bucketed percentile labels stay banned.
- The product may call a player elite. It may not tell you to do something.
- `verdict` is banned as a word and a field. The disagreement is a **margin**, never a spread.
- Absence is explained in words — "unmodeled category", "no active model score" — never a vague
  "evidence incomplete", never a zero.
- Wording is fixed at the producer; the render-time guard stays only as defence in depth.
- Glyphs vs prose, read narrowly per your 4 September ruling: a status indicator on the morning
  path is a symbol; an explanation a manager reads is prose.

## How it looks

- **Colour never encodes direction or verdict.** The divergence strip stays uniform neutral;
  direction is carried by label text.
- **One exception, granted twice:** green-up / red-down on rank-movement arrows only, glyph and
  signed number coloured as a single chip. Never on worth, margin or tier. (Your repo currently
  has two tests asserting no such arrow renders — here they will render, as you approved.)
- Margin heat-mapping is a magnitude ramp, not a good/bad hue — a single neutral-to-intense
  scale, with the signed number always printed.
- Typography, spacing, palette and light-vs-dark are **unruled by you**. Rather than inherit the
  team's invention silently, I'll show you two or three real rendered directions of the Roster
  screen and you pick. Until you pick, I'll build on the shipped dark charcoal so nothing stalls.
- Bar: Dynasty Nerds is the floor, not the target. I'll audit the rendered screen, at 1440 and
  390, and raise it until it clears — a passing test suite is never a visual pass.
- The 390px phone shell is in scope now, not deferred.

## Data

All free, no keys, fetched server-side and snapshotted daily so deltas and trend windows are real:

- **Sleeper** — league, all 12 rosters, users, transactions, traded picks, full player universe,
  headshots, injury status.
- **FantasyCalc** — dynasty Superflex market values and market ranks. This is the market side of
  the margin.
- **nflverse public CSVs** — weekly and seasonal production, snaps, targets, age, draft data.
  These feed our own valuation and the tier calibration.

## Build order

1. **Data spine first** (your 31 July sequencing: front end is gated behind the foundation) —
   tables for the player universe, daily value and rank snapshots, league state, rosters and
   transactions; a scheduled refresh writing one dated snapshot per player per day.
2. **Our valuation and rank + the margin**, versioned, with the tier calibration derived from
   the field and historicals so a tier label is earned rather than bucketed.
3. **Foundation shell** — CSS-variable design tokens, rail, ⌘K player search, canonical row,
   player drawer, receipts sheet, copy dictionary, sign-in so it's private to you.
4. **Roster** (main composition), then **Value board** with the three scopes.
5. **League**, then **Trades**.
6. **Player card** in full, cohort-banded chart.
7. **Track record**, phone pass at 390px, and a visual audit round against the bar.

## Two things I need you to rule on

1. **The stack conflict.** Your 3 June ruling locks React + Vite + TypeScript + Zod with CSS
   variables and bars Tailwind. This platform's stack is React + Vite + TypeScript with Tailwind
   compiled in; I can't remove it. My proposal: every colour, space and type value lives in CSS
   variables as you ruled, Tailwind is used only as the plumbing that applies them, and no
   Tailwind colour literal ever appears in a component. Say the word if that's not acceptable.
2. **Look and feel.** Since you've never ruled on type, spacing or palette, I'd rather you
   choose than inherit. I'll put rendered Roster-screen directions in front of you before the
   visual layer sets.

## Assumptions unless you say otherwise

- Redzone Champions League only for now; your 18-team league can be added later.
- Values default to dynasty Superflex, full PPR, no TE premium — your league's settings.
- Sign-in is email + password, your account only.
