# Dynasty Genius — UI Direction Report

## 1. Executive Summary

**The recommended UI shape for Dynasty Genius is a cockpit-style analytical workspace: a persistent left-rail navigation, a Home / Command Center as the default landing screen, and dedicated drill-down workspaces for Roster Audit, Rookie Board, Player Card, Trade Lab, League Opportunity Map, Trust, and Settings.** It should feel closer to Koyfin or a custom Palantir Foundry Workshop application than to KeepTradeCut or Sleeper — dense but calm, expert-grade, and resolutely advisory rather than action-oriented.

Three governance ideas drive every recommendation:

1. **Two-track value display.** Internal model value (PVO, xVAR, Engine A output) and market value (KTC/DLF/ADP) are always rendered as two separate, visually distinct columns or panels. They are never combined into a single "verdict" number. This is enforced at the component level through a color, typography, and label system (a "model track" and a "market track").
2. **Uncertainty is a first-class visual citizen.** Every numeric value carries an uncertainty hint (band, sparkline, "evidence gap" badge, or stale-data chip). The most important borrow from professional valuation tools is Morningstar's treatment of fair-value uncertainty: from Morningstar's Price to Fair Value Chart page, "The uncertainty rating appears as the thickness of a range of bands." Uncertainty is not a tooltip — it is part of the chart.
3. **No action verbs.** The product surfaces "review areas," "model views," "market snapshots," and "divergence context." It never displays "buy," "sell," "target," "block," "approve," "reject," "pass," or "fail" anywhere David could mistake the surface for a decision. `decision_supported: false` is rendered as a visible chip on every advisory artifact.

The rest of this report provides a complete information architecture, page-by-page wireframes, a visual design system, a banned/preferred language glossary, and an MVP scope.

---

## 2. Recommended Product Information Architecture

Dynasty Genius is a **single-user analytical workspace**, not a feed-driven app. The IA mirrors how David actually thinks about his team across multiple time horizons.

**Top-level zones (left-rail nav, in order):**

1. **Home** — Command Center.
2. **Roster** — David's current roster, age curve, construction, pressure.
3. **Rookies** — Rookie Board, draft state, Engine A output.
4. **Players** — Searchable player universe; the Player Card lives here.
5. **Trade Lab** — Hypothetical trade construction surface.
6. **League** — League Opportunity Map (12-team Redzone Champions context).
7. **Trust** — Governance, freshness, model versions, coverage.
8. **Settings** — Superflex/PPR/taxi/IR rules, posture, artifact timestamps.

**Cross-cutting elements:**

- A persistent **top status strip** (24px) shows: current "as-of" timestamp for the model artifact, the most stale source's age, a `decision_supported: false` chip, and the active league/posture.
- A **command bar (Cmd-K)** at the top center supports keyboard-first player and view jumping (a deliberate Linear/Raycast/Bloomberg ticker-shortcut borrow).
- The right edge is reserved for a **collapsible inspector panel** that displays the currently-selected player or asset context anywhere in the app (a Palantir Foundry Workshop pattern: the persistent right-rail object inspector).

**No bottom tab bar.** Mobile uses a hamburger drawer over the same left-rail IA, plus a sticky top status strip.

---

## 3. Recommended Page Inventory

| # | Surface | Type | Primary Job |
|---|---|---|---|
| 1 | Home / Command Center | Dashboard page | Show today's signal density, stale data, open review areas. |
| 2 | Roster Audit | Workspace page | Inspect David's roster across value, age, position, pressure. |
| 3 | Rookie Board | Workspace page | Engine A rookie rankings, xVAR, draft capital, available-now state. |
| 4 | Player Detail | Page (deep-link), opened from any list | PVO summary, model route, drivers, caveats, market overlay. |
| 5 | Trade Lab | Workspace page | Construct hypothetical trades; Model View + Market Snapshot side-by-side. |
| 6 | League Opportunity Map | Workspace page | League-mate roster profiles, surplus/deficit, divergence context. |
| 7 | Trust / Governance | Page | Data freshness, model versions, coverage, known limitations. |
| 8 | Settings / League Context | Page | League rules, posture, artifact timestamps. |
| – | Player Inspector | Right-rail panel | Lightweight player context that follows the user across surfaces. |
| – | Command Bar | Modal overlay | Cmd-K player/view jump. |

Modals are reserved exclusively for short-lived inputs (e.g., changing posture, confirming a what-if save). Player and trade detail are always pages or panels — never modals — so they are deep-linkable and easy to leave open in browser tabs (a Koyfin-style multi-tab analyst workflow).

---

## 4. Home / Command Center Concept

**Purpose:** When David opens the app, he sees, in one screen, what changed since he last looked, what looks worth inspecting, and what the trust state of the system is. The Home is a **launching surface**, not a verdict surface.

### Layout

- **Header strip (full-width, 56px):** "Woodbury Riders — Redzone Champions League, 12-team Superflex Full PPR, 4–24." Right side: as-of timestamp, freshness pill, `decision_supported: false` chip, posture selector ("Rebuild" by default given record), Cmd-K hint.
- **Body: 12-column grid, four primary panels.**

### Panels

**A. "Today's Review Areas" (top-left, 8 columns, ~360px tall)**
A prioritized list — not an action list — of up to seven *review areas*. Each row:
- Player avatar + name + position + team + age
- Neutral one-line context: "Model higher than market by 18% (uncertainty band: wide)" or "Coverage gap: PFF grade unavailable for last 2 weeks" or "Rank movement: +14 in Engine A since Tuesday"
- Tiny inline divergence bar: a horizontal segment with a tick for model, a tick for market, and a faint shaded band of uncertainty (Tufte-style sparkline density)
- A neutral chevron to expand inline or jump to Player Card

The list is sorted by a *signal density score* the model emits, not by predicted profit. The header label reads "Review Areas — sorted by signal density" with an "i" tooltip explaining the sort.

**B. "Roster Pressure Snapshot" (top-right, 4 columns)**
- Total roster size vs. roster cap as a horizontal capacity bar.
- Position-level capacity: small horizontal bars for QB / RB / WR / TE / Taxi / IR, each showing usage vs. cap. Bars use a neutral steel-gray fill; when capacity is exceeded or marginal, a small caveat icon appears beside the bar (never red as a verdict — red is reserved for stale data / system caveat).
- A single-line "Capacity cost if N rookies are added: M players become forced-cut candidates" — but framed as context, with a "see Roster Audit" link rather than a recommendation.

**C. "Recently Changed Signals" (middle-left, 6 columns)**
A small-multiples grid (Tufte) of ~12 sparklines, each showing the last ~14 days of a key signal: Engine A rookie rank shifts, KTC market value deltas, PFF coverage gaps, depth-chart changes for players David rosters. Each sparkline is annotated with the player or signal name and a delta number. Clicking a sparkline opens the Player Card.

**D. "Trust & Coverage" (middle-right, 6 columns)**
A compact freshness panel mirroring the Trust page in miniature:
- Last successful model run (Engine A, PVO, xVAR — each as a small row with timestamp).
- Source coverage table: KTC market, DLF rankings, Sleeper roster sync, PFF grades, ADP — each with an age in hours/days and a freshness color (green = fresh, amber = warning, gray-with-hatched-fill = stale/unavailable). **No red** unless the source has explicitly failed.
- A small link: "Open full Trust surface →".

**E. "Open Decision Items" (bottom strip, 12 columns, collapsed by default)**
A flat list of any saved what-if scenarios, in-progress trade constructions, or pinned questions David has left open across the app. Functions as session continuity, not as a task manager.

### Interactions

- Hover any row in panel A: right-rail Player Inspector opens with the player's PVO row, model route, and market overlay — no navigation cost.
- Click sparkline: jump to Player Card with that signal pre-selected.
- Posture selector in header (Rebuild / Balanced / Contender) changes nothing in the model — it only changes which *review areas* surface to the top and is labeled "filter posture, not model posture."

### Mobile/Tablet

On tablet, the four panels reflow into a 2×2 grid; the Open Decision Items strip becomes a separate tab. On phone, the layout becomes a single column with A → B → D → C → E vertical order; sparklines simplify to a value + delta. The status strip remains sticky.

---

## 5. Roster Audit UI Recommendations

**Purpose:** Let David inspect his 4–24 rebuild roster as a portfolio: who holds what value, where age curves are cliff-risk, which positions are over- or under-capacitized, where forced-cut pressure is forming.

### Layout

- **Header:** "Roster Audit — Woodbury Riders. Last roster sync: X minutes ago." Filter chips: position, age band, model value band, market value band, contract/IR/Taxi status.
- **Body, three stacked sections (each independently scrollable on desktop):**

### Section 1 — Roster table (primary)

A dense Bloomberg/Koyfin-style table with these columns (left to right):

1. Player (name, team, position, age — small composite cell)
2. **Model column group (cool blue track):** PVO, xVAR, model rank, model rank ∆ vs. 14d.
3. **Market column group (warm amber track):** KTC value, KTC ∆ 14d, DLF rank, ADP.
4. **Divergence column:** a tiny inline horizontal sparkbar showing model vs. market position on a 0–100 normalized scale. Label reads "model higher" / "market higher" / "inside band" — never "undervalued/overvalued."
5. **Roster context:** depth-chart slot, taxi/IR flag, biological debt indicator (a small age-curve glyph showing position on the curve).
6. **Caveats:** an icon column. Hovering surfaces "Coverage gap: ___" or "Stale: ___ days."
7. **Capacity cost:** a 1–5 dot scale indicating how much roster space this player consumes relative to model contribution.

Rows are sortable on every column. Default sort is by **position then PVO descending** (so David sees his QB room first — appropriate for Superflex). The table never highlights "good" or "bad" rows; it only highlights *caveat rows* (faint gray hatched left border).

**Strict visual separation:** The model column group has a thin cool-blue (#3B82F6 family) left border and uses a slab-serif/monospace number style. The market column group has a thin warm-amber (#D97706 family) left border and uses a tabular sans-serif number style. They never share a cell.

### Section 2 — Age curve & biological debt

A small-multiples grid of position groups (QB, RB, WR, TE). Each tile shows:
- A 2D scatter: x = age, y = PVO (or model value), each player a labeled dot.
- A faint dashed overlay line: the generic positional age curve. This curve is drawn from football-specific aging research, not borrowed wholesale from baseball: per Mike Braude's March 2026 PPR-scoring study at Apex Fantasy Leagues using NFL data since 2000, **RB average peak age is 25.46 and WR average peak age is 26.95**. The Dynasty Edge's EPA study (2014–2024) corroborates that **RBs peak between ages 25–27 then fade quickly after 28**, while **WRs show a broad production peak from 26 to 30**. The dashed overlay curves should reflect those values, and the cliff bands should be drawn just past them (RB cliff at ~27–28, WR cliff at ~30–31).
- A vertical band marking the **position cliff zone**.
- A title with the position and a single-number summary: "Avg roster age: 23.4 — youngest tile in your roster."

The visual job: David sees in one glance which position rooms are stacked young (asset-rich for a rebuild) and which have biological-debt drift toward the cliff zone.

### Section 3 — Roster construction & pressure

Two stacked components:

- **Position capacity bars** (a more detailed version of the Home panel). Each position is a stacked bar: starters in solid fill, depth in lighter fill, taxi/IR in hatched fill. Bar end shows cap, with a "capacity cost" annotation if the room is over-filled.
- **Forced-cut pressure list:** if David's roster is over cap or near cap, a neutral list of *candidates by lowest model-value-per-roster-slot*, with explicit caveat language ("This list is sorted by model value per slot. It is not a recommendation. `decision_supported: false`."). Each row shows model value, market value, biological-debt score, and a one-line counter-argument.

### Interactions

- Click any row → Player Card opens in main pane (table collapses to a side rail).
- Hover any age-curve dot → tooltip with player + uncertainty band on the model estimate.
- Filter to "model higher than market by ≥15%" → table re-renders with only divergence-context rows.

### Mobile/Tablet

On tablet, the table simplifies to: Player | Model | Market | Caveats. Age curves stack vertically. On phone, the table becomes card rows, and the age-curve section is replaced by a single position-selector with one curve tile at a time.

---

## 6. Rookie Board UI Recommendations

**Purpose:** Show David the current state of Engine A's rookie rankings, with xVAR, draft capital, his roster need, recent rank movement, caveats, and (when applicable) live draft state — all in a way that distinguishes active-roster decisions from rookie draft decisions.

### Layout

- **Header:** "Rookie Board — 2026 Class. Engine A v_X (run: timestamp). Coverage: 60 prospects." Toggles: "All rookies" | "Top 60" | "Top 36" (the 12×3 board). Posture filter: "Superflex" (default on, can't be turned off in this league).
- **Body:** A primary ranked table on the left (8 cols), a contextual right rail (4 cols).

### Primary Rookie Table

Each row:
1. Rank (large), with a small Engine A rank ∆ indicator (e.g., "+3 since model run prior").
2. Player (name, position, college team, age).
3. **Engine A model track (cool blue):** xVAR, projected role tier, model rank, uncertainty band glyph (a small horizontal band of variable thickness — width = uncertainty, borrowed directly from Morningstar's fair-value uncertainty band concept where "the uncertainty rating appears as the thickness of a range of bands").
4. **NFL draft capital (neutral gray):** Projected round/pick (when available), or "Pre-draft estimate" chip.
5. **Market track (warm amber):** KTC rookie value, DLF rookie rank, KTC ∆ 14d.
6. **Divergence context:** a tiny inline glyph — "model higher than market" / "model lower than market" / "inside band." Hovering shows the % gap and the model's confidence in the gap.
7. **Roster fit:** a small dot-glyph showing how well this player slots into David's current position need (purely descriptive — e.g., "WR room has 3 sub-23 players already" — not "fits your team").
8. **Caveats:** icons for coverage gaps, missing landing spot, stale ADP, etc.

The header row labels read "Engine A model" and "Market snapshot" — never "rank" or "value" alone — so the cognitive separation is constant.

### Right Rail — Contextual Inspector

When a rookie is selected:
- Engine A drivers (top 4–6 features that move the score), each with a small horizontal bar.
- Counter-arguments: "Model is lower than consensus market by 22% — likely drivers: small school, age 23.4, weak workouts." Stated as evidence, not as a hedge.
- Caveats and missing-input list.
- Comparable-prospect strip: 3–5 historical comps with their actual NFL outcomes (small horizontal bars on a normalized scale). This is the closest thing to PECOTA's "comparable players" pattern — but rendered as evidence, not as a projection.
- Engine A version + model run timestamp (always visible).
- An explicit `decision_supported: false` chip with help-text on hover.

### Available-Now Draft State (during active rookie draft)

When David is mid-draft, a slim sticky band appears at the top:
- "On the clock: pick 2.04 in 8 minutes" (if Sleeper draft state is synced) — or "Draft state: idle" if not.
- The table gets a "Available now" filter chip auto-applied; taken rookies are visually de-emphasized (rendered in a 50%-opacity row with a strikethrough) rather than removed, so David can still see where they were ranked.

### Interactions

- Hover any rookie row → right-rail inspector updates.
- Click rank ∆ → opens a small chart of that prospect's Engine A rank history.
- Filter for "model higher than market by ≥15%" → review-area discovery mode.

### Mobile/Tablet

On tablet, the right rail becomes a bottom drawer. On phone, the table becomes ranked cards with two visible tracks (Engine A | Market) stacked vertically.

---

## 7. Player Card UI Recommendations

**Purpose:** A single source of truth for any player — David's, league-mate's, or rookie. The Player Card is the most-visited surface and must satisfy the two-track separation rule completely.

### Layout

- **Header:** Player name, position, team, age, height/weight, contract/IR/Taxi status, "as-of" timestamp for the artifact.
- **Body:** A vertical stack of sections, all collapsible. Default-open: PVO Summary, Model Route, Market Overlay, Caveats. Closed-by-default: News, Comparable Players, History, Notes.

### Section 1 — PVO Summary

Top-of-card "scoreboard" containing **two adjacent panels, never merged**:

- **Left panel — Model View (cool blue track):** PVO (large number), xVAR, model rank, model tier, uncertainty band (a horizontal bar with variable-thickness shading directly inspired by Morningstar's Price-to-Fair-Value chart treatment — "the uncertainty rating appears as the thickness of a range of bands").
- **Right panel — Market Snapshot (warm amber track):** KTC value, KTC rank, DLF rank, ADP, KTC ∆ 14d sparkline.

Between the two panels is a **divergence strip** — a horizontal band 0–100 normalized, with a labeled blue tick (model position) and a labeled amber tick (market position), and a shaded uncertainty band around the model tick. The label below the strip reads neutrally: "Model higher than market by 18%" or "Inside band (<5%)" or "Model lower than market by 9%." This is the single most important component in the product. It directly borrows two patterns from professional valuation tools:

- Morningstar's Price/Fair Value ratio, anchored at 1.00, where "a ratio above 1.00 indicates that the stock's price is higher than Morningstar's estimate of its fair value; a ratio below 1.00 indicates the stock's price is lower than our estimate of fair value."
- Simply Wall St's plain-language phrasing on its valuation pages — for example "Below Future Cash Flow Value: SNOW ($143.55) is trading below our estimate of future cash flow value ($237.27)" — which is neutral, quantified, and never imperative.

### Section 2 — Model Route

A small flow visualization (3–5 stops) showing how the PVO was computed: which model variant ran, which inputs were used, which fallbacks fired. Each stop is a tiny pill: "Engine A v_X → PVO feature set v_Y → fallback ADP v_Z." Hovering a stop shows the values that flowed through it.

This is borrowed from MLflow/W&B-style model lineage UIs, simplified to a single horizontal track. The user can always answer: "Why did the model say this?"

### Section 3 — Valuation Drivers

A vertical list of the top 5–8 drivers, each with:
- Driver name (e.g., "Career target share %, last 16 games")
- Driver value
- A horizontal contribution bar (signed, centered on zero) — positive contributions extend right in cool blue, negative extend left in muted gray
- A small uncertainty hint per driver

### Section 4 — Caveats, Counter-arguments, and Evidence Gaps

A dedicated panel — never folded into a tooltip. Each item is a row:
- Caveat type icon (stale source, coverage gap, role uncertainty, injury)
- One-line evidence statement
- Optional drill: "Missing data: PFF grade for weeks 12–14"

A separate sub-section "Counter-arguments" lists 1–3 reasons the model could be wrong, in plain language. The principle behind this section is taken directly from clinical-decision-support XAI research — Schoonderwoerd, Jorritsma, Neerincx, and van den Bosch's "Human-centered XAI: Developing design patterns for explanations of clinical decision support systems" (*International Journal of Human-Computer Studies*, 2021, DOI 10.1016/j.ijhcs.2021.102684), which formalizes Design Pattern 3 (Certainty) and elements 5–6 (supporting- and counter-evidence) as required explanation components. This is the most important departure from KeepTradeCut-style products, which collapse all uncertainty into a single value.

### Section 5 — Roster Context (only if David rosters the player)

A small block: depth-chart slot, current capacity cost, age-curve position, biological debt score.

### Section 6 — Market Overlay (extended)

Time-series chart of KTC value and (when available) DLF rank, with the Engine A model rank overlaid as a separate cool-blue line. The two lines are visually distinct in weight and color, and the legend explicitly labels "Market" and "Model" — never combined.

### Section 7 — Comparable Players (rookies and early-career only)

A horizontal strip of 3–5 historical comps with their early-career outcomes plotted on the same axes as the focal player. Inspired by PECOTA's similarity-score approach but rendered as evidence panels rather than a projection.

### Persistent footer

`decision_supported: false` chip + model version + artifact timestamp + "Open in Trade Lab" / "Open in Roster Audit" navigation chips.

### Mobile/Tablet

The two-panel scoreboard becomes a stacked pair (model on top, market below) with the divergence strip sandwiched between them. All other sections collapse to accordions. The divergence strip and caveats section never collapse.

---

## 8. Trade Lab UI Recommendations

**Purpose:** Let David construct hypothetical trades and see Model View, Market Snapshot, forced-cut roster penalty, package dilution warnings, model-vs-market divergence, pick caveats — all as advisory-only output, never as a verdict.

### Layout

- **Header:** "Trade Lab — Hypothetical. Not synced to Sleeper. Last save: …" Always-on chip: `decision_supported: false`.
- **Body, three columns:**
  - **Left (4 cols): "Side A — Woodbury Riders gives"** — drag/drop or search-add players and picks.
  - **Center (4 cols): Analysis pane.**
  - **Right (4 cols): "Side B — [league-mate] gives"** — same construction.

### Analysis Pane (center)

The most carefully designed surface in the product. It contains **four stacked panels** that mirror the governance model:

**Panel 1 — Model View (cool blue, top)**
- Side A total model value vs. Side B total model value, as two horizontal bars on a shared axis.
- Per-asset model contribution stack below each bar (each asset a labeled segment).
- A single neutral statement: "Model view: Side A total higher by X% (uncertainty band: ±Y%)." Never "Side A wins."
- Engine A version + run timestamp.

**Panel 2 — Market Snapshot (warm amber, middle)**
- The exact same shape as Panel 1, but using KTC + DLF market values.
- Single neutral statement: "Market snapshot: Side A total higher by X% per KTC."
- KTC freshness chip ("KTC market: updated 18 min ago").

**Panel 3 — Divergence Context**
- A single horizontal divergence strip showing model-vs-market delta for the trade as a whole.
- Per-asset divergence rows below, each with the inline model/market tick + uncertainty band visualization used elsewhere in the product.
- Plain-language summary: "Two assets in this package show model higher than market by >15%. Three assets show inside band." Never "two players you should target." (This is the Alpha Spread "Undervalued by X%" tile pattern with the language stripped down: descriptive delta, no verb.)

**Panel 4 — Roster Penalty & Pressure**
- Forced-cut roster penalty: if accepting this trade would push David over roster cap, a list of forced-cut candidates with their model values (sorted ascending) — explicitly labeled "Capacity cost: M players would need to be released. This list is descriptive, not a recommendation."
- Package dilution warning: if either side is sending 3+ assets for 1 elite asset, a neutral caveat — "Package dilution context: the side receiving fewer, higher-value assets typically captures more per-slot value." Borrowed from KTC's roster-clogger logic but rendered as caveat, not adjustment.
- Pick caveats: if any draft picks are in the trade, "2027 1st: pick value uncertainty is high; landing-spot and class strength unknown" chip.

### Side A / Side B columns

Each shows:
- Player or pick row with model value + market value side-by-side (the two-track rule).
- A small "remove" affordance.
- At the bottom: a "Roster after trade" capacity bar showing position-level pressure.

### Save / Pin

- "Save scenario" stores the trade in Home's Open Decision Items.
- "Open in League Opportunity Map" jumps to the league view with this league-mate pre-selected.

### Interactions

- Add/remove an asset → all four panels re-render under 100ms.
- Hover a model bar segment → that player's Player Card opens in the right-rail inspector.
- The pane never displays a "fair" / "unfair" verdict, a percentage win probability, or any action verb. Specifically removed from the design: KTC's "Fair Trade" verdict chip — Dynasty Genius shows only divergence, never a fairness label.

### Mobile/Tablet

Trade Lab is the surface that gracefully degrades least well to mobile. Recommendation: on tablet, Sides A/B collapse to top tabs and the Analysis pane fills the screen. On phone, Trade Lab is a read-only viewer for saved scenarios; full construction is desktop-only (clearly stated on entry).

---

## 9. League Opportunity Map UI Recommendations

**Purpose:** Give David a portfolio-style view of the other 11 teams in Redzone Champions League — their roster profiles, surplus/deficit by position, where their market view diverges from his model, and what opportunities exist *for him to inspect* — without telling him to do anything.

### Layout

- **Header:** "League Opportunity Map — Redzone Champions League, 12 teams. Last roster sync: …"
- **Body, two columns:**
  - **Left (5 cols): League grid.**
  - **Right (7 cols): Selected-team inspector or overlap heatmap.**

### League Grid

A 3×4 grid of team tiles. Each tile (~180×120px) shows:
- Team name + manager handle
- Record + posture inference ("appears in rebuild / appears competitive / posture unclear" — inferred from age + record + recent transactions; never asserted)
- Position-level surplus/deficit strip: small horizontal bars for QB / RB / WR / TE, with surplus extending right, deficit extending left, relative to a 12-team Superflex roster baseline
- Total roster age (average) — a single number
- Total market value (KTC) and total model value (PVO sum) — side-by-side
- A subtle "divergence with you" indicator showing where this team's surplus matches your deficit, and vice versa

Tile borders use the same cool-blue / warm-amber tracks — the surplus/deficit bars are neutral gray; "matches David's deficits" is shown as a faint dotted overlay on relevant position bars, never as a flashy highlight.

### Right Pane — Selected-Team Inspector

When David clicks a tile:
- Full roster of that team, in the same dense table style as Roster Audit.
- A "potential overlap" view: small-multiples of position rooms where David has surplus and they have deficit (and vice versa).
- A "market-divergence opportunities" panel: assets on their roster where David's model is higher than the market by >15%, and assets on David's roster where his model is lower than the market by >15%. Each row is neutral — "Their RB2: model higher than market by 19%. Coverage: full. Uncertainty: medium."
- A button "Open in Trade Lab" that pre-populates Side B with this team's roster.

**Critical language rule:** This surface never says "trade target," "target acquisition," "block," or "approach." It says "review area," "potential overlap," "divergence context," "model higher than market."

### Heatmap view (toggle)

A 12 × 4 position heatmap (teams × QB/RB/WR/TE), each cell colored by net surplus/deficit. David can see at a glance which teams are deepest at which position. The heatmap uses a single-hue diverging palette (cool blue ↔ warm amber, neutral gray at zero) and is purely descriptive.

### Interactions

- Hover a tile → quick preview of overlap with David's roster.
- Click a tile → full inspector.
- Filter by "posture: competitive" or "model-vs-market divergence ≥15%."

### Mobile/Tablet

On tablet, the grid becomes 2×6 with smaller tiles; the inspector becomes a bottom drawer. On phone, the grid stacks to a single column; the heatmap is horizontally scrollable.

---

## 10. Trust / Governance UI Recommendations

**Purpose:** Make the model's epistemic state legible. This surface is the canonical reference for `decision_supported`, data freshness, model versions, source coverage, and known limitations.

### Layout

- **Header:** "Trust Surface — System state as of [timestamp]."
- **Body, four sections.**

### Section 1 — Model artifact registry

A table of every model in the system. Columns:
- Model name (Engine A, PVO, xVAR, etc.)
- Current version
- Last run timestamp
- Coverage (e.g., "All 36 active rookies; 412/450 NFL skill players")
- `decision_supported` status (currently `false` for all advisory models — rendered as a visible chip, never a hidden flag)
- "Open changelog" link

### Section 2 — Source freshness

A table of every external source, each with:
- Source name (KTC, DLF, PFF, ADP, Sleeper roster sync, NFL roster sync)
- Last successful fetch
- Age (with a green/amber/gray-hatched chip — gray-hatched explicitly means "unavailable," not "bad")
- Coverage notes
- Backoff / retry state if relevant

This explicitly borrows Stripe Sigma's documented data-freshness pattern. Stripe's docs state: "The interface in the Dashboard displays the date and time of the last payments data. You can use data_load_time as a value in your queries to represent when data is most recently processed on your account." Dynasty Genius applies that same first-class freshness treatment to every external data source it depends on.

### Section 3 — Known limitations

A plain-language list, written by David (editable). Examples:
- "Engine A's pre-draft rookie projections assume current ADP-implied landing spots. Post-NFL Draft refresh expected on April 27."
- "KTC values reflect Superflex / 0.5 PPR by default; this league is Superflex / Full PPR. Internal model already adjusts for this; market snapshot does not."
- "No injury severity model. Injury status is sourced from Sleeper only."

This section is curated by David, not generated. It is the canonical place where he records the things the system explicitly does not do.

### Section 4 — Decision-support promotion log

If Dynasty Genius ever promotes an artifact from `decision_supported: false` to `true`, that change is logged here with the date, model version, and the test results that justified the promotion. This is the audit trail that distinguishes Dynasty Genius from consumer tools.

### Interactions

- Click any model row → opens a small detail panel with run history.
- Click any source row → opens fetch-history sparkline + last error.

### Mobile/Tablet

Trust is a reference surface, not a workflow surface. Tables degrade gracefully to mobile by collapsing less-important columns; the freshness chips and `decision_supported` chips remain visible at all sizes.

---

## 11. Visual Design Principles

### Color system (semantic, not decorative)

| Role | Color (suggested) | Use |
|---|---|---|
| **Model track** | Cool blue, `#3B82F6` family with `#1E40AF` for strong emphasis | All model-derived numbers, bars, ticks, borders |
| **Market track** | Warm amber, `#D97706` family with `#92400E` for strong emphasis | All market-derived numbers, bars, ticks, borders |
| **Neutral data** | Slate gray (`#475569`, `#64748B`) | Roster context, age, structural metadata |
| **Caveat / uncertainty** | Muted yellow `#A16207` for caveat chips; hatched gray `#94A3B8` for unavailable | Caveat icons, uncertainty bands, stale source indicators |
| **Urgent / system caveat** | Desaturated red `#B91C1C` — RESERVED for stale/failed sources and `decision_supported` warnings, never for player value | Trust surface only, plus stale-source chips |
| **Background** | Near-white `#FAFAFA` and a paper-warm dark mode `#0F172A` | Light = analyst default; dark = optional |
| **Strong text** | Near-black `#0F172A` | Headers, key numbers |
| **Secondary text** | `#475569` | Labels, metadata |

Color is **always paired with a non-color cue** (border weight, icon, label) so the model/market separation survives color-blindness, dark mode, and printing.

### Typography hierarchy

- **Numbers:** A tabular monospace or tabular-figures sans-serif (e.g., Inter with `font-variant-numeric: tabular-nums`, JetBrains Mono for the most data-dense tables). Numbers line up vertically — non-negotiable for tables.
- **Body:** Inter or IBM Plex Sans, 14px base on desktop.
- **Headers:** Same family at 16/18/20/24 with weight (not color) carrying hierarchy.
- **Captions:** 12px, gray.
- **Dynasty Genius does not use display fonts, italic emphasis, or decorative type.**

### Information density

Target ~1.5× the density of Sleeper or KTC and ~80% of Bloomberg. Concretely:
- Table row height: 32px desktop, 36px tablet, 44px mobile.
- Page padding: 24px desktop, 16px tablet, 12px mobile.
- Sparkline height: 16px for inline, 32px for small-multiples.
- The Linear design principle is the explicit reference. From Linear's March 12, 2026 blog post "A calmer interface for a product in motion" (authored by Charlie Aufmann and Maxime Heckel): "The navigation sidebar used to appear bright enough that it remained visually prominent even after a user had reached their destination. In the updated interface, it's a few notches dimmer, allowing the main content area—where users work—to take precedence." Dynasty Genius's chrome and nav recede; data takes precedence.

### Spacing & grid

12-column grid at 1440px and above; 8-column at 1024–1439; 4-column at <1024. 8px spacing scale (8 / 16 / 24 / 32 / 48 / 64) — borrowed directly from the Linear / shadcn convention.

### Component patterns

- **Two-track panel:** the canonical Dynasty Genius primitive — two adjacent panels with a thin colored left border each (cool blue / warm amber) and a divergence strip between or below.
- **Sparkline cell:** 60×16 inline sparkline embedded in table cells; uses one line (the focal series) plus a faint band (uncertainty).
- **Divergence strip:** the model-vs-market normalized bar described above; appears in Player Card, Trade Lab, Rookie Board, Roster Audit, and League Opportunity Map.
- **Caveat chip:** rounded rectangle, 20px tall, muted yellow background, small icon, single-line label. Hover expands to a 2-line tooltip with source/age.
- **Freshness chip:** small pill — green / amber / hatched gray — with text "X min ago" / "X hr ago" / "unavailable since…"
- **`decision_supported: false` chip:** a distinct pill in slate-gray with a small lock icon, never green and never red. Hovers reveal a short explanation linking to the Trust surface.
- **Tables:** zebra striping disabled by default (too noisy); section dividers via 1px slate-100 lines. Sticky header row and sticky first column (player name) on horizontal scroll.
- **Tooltips:** delay 300ms, max 280px wide, always include source and timestamp where relevant.
- **Modals:** only for short-lived input. Player and trade detail are pages or panels.

### Iconography

Lucide or Phosphor (Outline weight). Icons used only where they add scan-speed (caveat, stale, lock, drill-into, jump-to). Never decorative.

### Dynasty-specific data visualization patterns

- **Age curve tile** — scatter + dashed positional curve + cliff-zone band. Curve calibration is football-specific (RB peak ~25.46, WR peak ~26.95 per the Apex Fantasy Leagues 2026 study, with cliffs drawn just past those peaks). Used in Roster Audit and in Player Card.
- **Divergence strip** — the model/market two-tick bar with uncertainty band rendered as variable thickness (Morningstar pattern).
- **Capacity bar** — segmented horizontal bar with starter/depth/taxi fills.
- **Driver contribution bar** — signed, centered-zero horizontal bar per model driver.
- **Position heatmap** — 12-team × position grid for League Opportunity Map.
- **Sparkline small-multiples** — Tufte-style grid used on Home for recently-changed signals.

---

## 12. Language and Terminology Guidelines

### Banned in David-facing recommendation contexts

`buy`, `sell`, `target`, `block`, `approve`, `reject`, `pass`, `fail`, `winner`, `loser`, `fair trade`, `unfair`, `trade winner`, `must-have`, `must-cut`, `sleeper` (in evaluative sense), `bust`, `steal`, `rip-off`, `red flag` (use "caveat"), `green light`, `actionable`, `recommended`, `we recommend`, `you should`, `verdict`.

### Preferred neutral vocabulary

- **Model view** — Engine A / PVO / xVAR output panel.
- **Market snapshot** — KTC / DLF / ADP panel.
- **Inside band** — divergence is below the meaningful threshold (e.g., <5%).
- **Model higher than market** / **Model lower than market** — the two divergence directions. Borrowed directly from Morningstar's framing: "A ratio above 1.00 indicates that the stock's price is higher than Morningstar's estimate of its fair value; a ratio below 1.00 indicates the stock's price is lower than our estimate of fair value."
- **Divergence context** — generic label for any model-vs-market comparison.
- **Review area** — a thing worth inspecting, not a thing to do.
- **Roster pressure** — capacity strain; never "roster crunch" or "must cut."
- **Capacity cost** — what a roster slot costs in model-value terms.
- **Forced-cut candidate** — descriptive list, not a recommendation.
- **Biological debt** — age-curve-driven expected decline. Use only with a defined glossary entry.
- **Position cliff** — the age band where positional value historically drops sharply.
- **Coverage gap** — a missing input.
- **Evidence gap** — a known-unknown that the model cannot resolve.
- **Stale source** — data is older than its freshness SLA.
- **Unavailable** — source returned nothing on last fetch.
- **Unresolved** — the model declined to score this asset.
- **Caveat** — anything that should temper interpretation.
- **Advisory warning** — the system itself is flagging an interpretive risk.
- **Posture** — David's filter on the UI (rebuild / balanced / contender). Does not change model output.
- **Artifact** — any persisted model run, ranking, or scenario.
- **`decision_supported: false`** — verbatim flag, displayed as a chip.

### Tone

Plain, declarative, third-person where possible, never imperative. Example pairs:

| Avoid | Use |
|---|---|
| "Buy Jordan Addison" | "Engine A model higher than market by 19% on Jordan Addison." |
| "Trade this guy" | "Inspection candidate: model lower than market by 22%." |
| "Cut to make room" | "Capacity cost: adding 1 rookie would put roster at 1 over cap. Lowest model-value-per-slot players: …" |
| "Fair trade" | "Side A total higher than Side B per model by 6% (inside band). Per market: Side A higher by 11%." |

---

## 13. Comparable Product Analysis

| Product | What to borrow | What to explicitly NOT borrow |
|---|---|---|
| **Bloomberg Terminal** | Two-track separation of inputs and outputs; persistent status strip; keyboard-first command bar; "always-on" data freshness; the principle of *concealing complexity behind consistent panels*; the Launchpad workspace concept of persistent analytical tools. | Cryptic shortcut codes; proprietary color conventions; the implicit hierarchy of "trader expertise as gatekeeper." |
| **Koyfin** | Customizable dashboard with widget panels; "snapshot" pages that put performance, valuation, capital structure and analyst estimates in one composed view ("a comprehensive range of key company metrics" per Koyfin's own help docs); My Dashboards Grouping where widgets share a color group; reskinning between themes; charting/template reuse. | Asset-class breadth; pitch-deck heroification; chart-first centrality. |
| **Palantir Foundry Workshop / Carbon** | The Ontology-Object pattern translated to fantasy: every player is an object with attached views, drivers, and history; persistent right-rail object inspector; workspace separation between operational app and analytical app; the principle that decisions are represented in the data model. | Anything resembling AIP automation prompting David to "approve or reject" agent suggestions; the platform's enterprise admin scaffolding. |
| **Linear** | The "calmer interface" doctrine (sidebar a few notches dimmer than content area, per Linear's March 2026 design refresh post); 8px spacing scale; modular components without a forced grid; Cmd-K command bar; "Last updated" as a first-class sort attribute exposed in display options; precision typography. | Issue-tracking conventions (status labels, assignees, due dates) that imply automated workflow. |
| **PFF Premium / FantasyPros / DLF / KTC** | Tiering language; depth-chart visualizations; the rookie-board ranked-list table layout; the small composite player cell (avatar + name + position + team + age). PFF's grading philosophy itself — "The PFF grading system evaluates every player on every play during a football game" — is used as a feeder signal, not as a verdict. | The verdict-driven "Buy / Sell / Hold" article framing; the "Fair Trade" / "Unfair Trade" calculator verdict; KTC's daily "Keep/Trade/Cut" gamified prompt; ad-supported chrome; tipster tone. |
| **Morningstar Stock Pages** | The Price-to-Fair-Value ratio anchored at 1.00; the Price-to-Fair-Value time-series chart with uncertainty rendered as the thickness of a range of bands ("The uncertainty rating appears as the thickness of a range of bands"); the neutral "trading at a discount or premium to" framing; the explicit decoupling of analyst-derived ("A") and quantitative-derived ("Q") values through a superscript marker. | The 1–5 star bucket as the dominant visual — it summarizes too aggressively and reads as a verdict; the "consider buying" / "consider selling" price labels that creep into action language. |
| **Simply Wall St** | The plain-language valuation-check phrasing (e.g., "Below Future Cash Flow Value: SNOW ($143.55) is trading below our estimate of future cash flow value ($237.27)"); the per-check labelled card layout on valuation pages; the separation of "Fair Ratio" (model construct) from "current ratio" (market observation); the docs' explicit statement that the Snowflake glyph "simply summarises visually relevant characteristics of a stock" — descriptive, not a recommendation. | The Snowflake itself — radar charts collapse too many dimensions into one shape, and the size/color shorthand reads as a quality verdict. |
| **Alpha Spread** | The intrinsic-value-vs-market-price comparison *table* (flat, descriptive side-by-side); the per-ticker "X% over/undervalued" tile as a neutral percentage label; the framing that "If the DCF value is higher than the market price, it suggests that the stock is undervalued. This discrepancy indicates that the stock's market price does not fully reflect its future cash flow potential, as estimated by our DCF analysis." | The "Undervalued" / "Overvalued" verb labels themselves when used as headers — Dynasty Genius prefers "Model higher than market" / "Model lower than market." |
| **PECOTA / FanGraphs aging research** | The shape and philosophy of aging curves and the use of comparable-players panels as *evidence*, not as projection. Football-specific calibration is taken from PPR-scoring studies: per Mike Braude's March 2026 Apex Fantasy Leagues study using NFL data since 2000, RB average peak age is 25.46 and WR average peak age is 26.95; per The Dynasty Edge's EPA study, RBs peak ages 25–27 and fade quickly after 28, while WRs show a broad production peak from 26 to 30. The explicit acknowledgment that aging curves are population-level averages with high individual variance. | The full PECOTA percentile spreadsheet — too dense, too specialized, and projection-output rather than evidence-input. |
| **Stripe Dashboard / Sigma** | The data-freshness pattern as a first-class field surfaced in the interface. Per Stripe Sigma's docs: "The interface in the Dashboard displays the date and time of the last payments data. You can use data_load_time as a value in your queries to represent when data is most recently processed on your account." | Anything related to payments / commerce UI; growth metrics. |
| **Vercel `stale-while-revalidate`** | The semantic model from Vercel's caching docs: "This cache-control directive allows you to serve content from the Vercel CDN cache while simultaneously updating the cache in the background with the response from your function." Serve the last-known-good model artifact while a fresh one is computing, visually marked as stale; stale is acceptable if labeled. | The technical implementation as an architectural mandate — Dynasty Genius is single-user, not edge-cached. |
| **Datadog / Grafana** | The three-layer information model for operational dashboards (top-line status / what's running now / what's escalating); SLO-style freshness thresholds applied to model artifact freshness. | Time-series-heavy chart density; multi-team RBAC; alert routing. |
| **Clinical Decision Support XAI research** | Schoonderwoerd, Jorritsma, Neerincx, and van den Bosch's "Human-centered XAI: Developing design patterns for explanations of clinical decision support systems" (*International Journal of Human-Computer Studies*, 2021, DOI 10.1016/j.ijhcs.2021.102684) — formalizes Design Pattern 3 (Certainty) and elements 5–6 (supporting- and counter-evidence) as required explanation components. Directly informs Player Card's caveats-and-counter-arguments section. Also: line-graph trended risk presentation over single-point risk values. | The MD-facing alert fatigue model; auto-prescribing workflows. |
| **Tufte (Visual Display, Envisioning Information)** | Small multiples; sparklines; high data density; the "data-ink ratio" doctrine; macro-micro reading; range-frames over closed boxes. | Chartjunk; pseudo-3D anything; ornamental flourishes. |
| **Sleeper** | League sync API as the source of truth for roster and league state. | Sleeper's UI itself — it is a transactional surface, not an analytical one. |

---

## 14. Anti-Patterns To Avoid

Each anti-pattern below is in production at one or more public fantasy products. Dynasty Genius must not adopt any of these.

1. **The verdict chip.** A green "BUY" / red "SELL" / yellow "HOLD" pill on a player or trade.
2. **The fairness verdict.** A "Fair / Unfair / Slight Edge" label on a trade — borrowed directly from KTC; banned.
3. **Single combined value.** Reporting a player as "value: 7842" with model and market collapsed into one number.
4. **Uncertainty as tooltip-only.** Burying confidence intervals behind hover. Uncertainty must be visible in the primary visualization.
5. **Color-as-verdict.** Coloring a row green or red to imply value judgment. Color is reserved for *track* (model/market) and *system caveats* (stale, unavailable). It never says "good" or "bad."
6. **Radar / spider charts as primary visualization.** Simply Wall St's Snowflake collapses five axes into a glyph that reads as overall quality.
7. **Gamification.** No streaks, badges, leaderboards, daily-prompt nags, animated confetti, or "you might also like."
8. **Auto-promoted recommendations.** Every advisory surface carries `decision_supported: false` until explicitly promoted.
9. **Stale data without a chip.** Silent staleness is the worst failure mode in an analytical product.
10. **Modals for player or trade detail.** Players and trades must be addressable URLs, openable in multiple browser tabs.
11. **Dashboard-only ML lineage.** The model route, version, drivers, and missing inputs must be on the Player Card itself, not behind a developer-only debug page.
12. **Bottom tab bar on mobile that hides the Trust state.** The status strip stays sticky at every viewport.
13. **"Smart" recommendations from market data.** Market data is price discovery only. It never originates a recommendation, even an advisory one.
14. **Premature precision.** Showing PVO as "7842.3" when the model uncertainty is ±400. Display to the meaningful significant figure.
15. **Decorative iconography or illustrations.** No mascots, no team-spirit visuals, no hero imagery.
16. **The "for you" feed.** Home is structured by signal density and freshness, not by algorithmic personalization that David can't introspect.

---

## 15. Concrete Wireframe Descriptions

Each wireframe below is described as a sequence of regions, panels, and components. Together with sections 4–10, this gives an engineer enough to build a Figma file.

### 15.1 Home / Command Center
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Woodbury Riders · Redzone Champions L. · 12T SF FullPPR · 4-24      │
│         [as-of: 2:14 PM] [freshness: 12m] [decision_supported: false] [⌘K] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─Today's Review Areas (8 col, 360px)───┐ ┌─Roster Pressure (4 col)─────┐  │
│ │ • J. Addison · WR · 23.4              │ │ Cap: 32/35 ████████░       │  │
│ │   Model higher than market by 18%     │ │ QB ███▌  RB ██▌  WR █████  │  │
│ │   [divergence strip]                  │ │ TE █▌  Tx ██  IR █          │  │
│ │ • Z. Charbonnet · RB · 24.1           │ │ Capacity cost +1 rookie:    │  │
│ │   Coverage gap: PFF wks 12-14         │ │ 1 forced-cut candidate      │  │
│ │ • [6 more rows]                       │ │ → Open Roster Audit         │  │
│ └───────────────────────────────────────┘ └─────────────────────────────┘  │
│ ┌─Recently Changed Signals (6 col)──────┐ ┌─Trust & Coverage (6 col)────┐  │
│ │ [12 sparklines in 4×3 small multiples]│ │ Engine A: ran 38m ago ✓     │  │
│ │ Each: title + line + delta number     │ │ PVO: ran 38m ago ✓          │  │
│ │                                       │ │ xVAR: ran 6h ago ⚠          │  │
│ │                                       │ │ KTC market: 12m ago ✓       │  │
│ │                                       │ │ PFF grades: 18d ago ░       │  │
│ │                                       │ │ → Open full Trust surface   │  │
│ └───────────────────────────────────────┘ └─────────────────────────────┘  │
│ ┌─Open Decision Items (12 col, collapsed)─────────────────────────────────┐│
│ │ ▶ 3 saved scenarios · 1 pinned question                                 ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 15.2 Roster Audit
```
HEADER: Roster Audit · Last sync 4m · [Filter: pos | age | model | market | caveat]
┌─Roster Table (full width)──────────────────────────────────────────────────┐
│ Player          │ MODEL ▎ PVO  xVAR  rk  Δ14d │ MARKET ▎ KTC  Δ14d  DLF ADP│
│                 │  [cool blue group]          │  [warm amber group]        │
│                 │ Divergence │ Roster ctx │ Caveats │ Cap cost              │
│ ─────────────── │ ───────── │ ────────── │ ─────── │ ────────              │
│ B. Robinson RB23│  ▎ 0.78 6.2 RB14 ↑3      │ ▎ 7842 ↑220 RB12 RB18          │
│                 │ [tick model][band][tick market]  │ depth1 [↓curve]│ –   │ ●●●○○│
│ [more rows...]                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
┌─Age Curve Small-Multiples (4 tiles, QB/RB/WR/TE)──────────────────────────┐
│ Each tile: scatter (age × PVO), dashed positional curve (RB peak ~25.5,    │
│ WR peak ~27), cliff band drawn just past peak, label                       │
└─────────────────────────────────────────────────────────────────────────────┘
┌─Capacity & Forced-Cut Candidates──────────────────────────────────────────┐
│ Position bars (stacked) · Forced-cut candidate list (descriptive)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 15.3 Rookie Board
```
HEADER: Rookie Board · 2026 · Engine A v_X (ran 38m ago) · [All|Top60|Top36]
┌─Rookie Table (8 col)─────────────────────────────┐┌─Inspector (4 col)─────┐
│ # │ Player        │MODEL▎xVAR rk band│DRAFT cap   ││ Drivers (bars)        │
│   │               │MARKET▎KTC DLF Δ  │Divergence  ││ Counter-arguments     │
│   │               │RosterFit│Caveats │            ││ Caveats               │
│ 1 │ J. Mendoza QB │ ▎0.91 12 [band] │ Proj R1.5  ││ Comparable players    │
│   │ Indiana 23.0  │ ▎8410 QB1  ↑180 │            ││ Engine A v_X (38m)    │
│   │               │ [model higher by 4% · inside]││ [decision_supported]  │
│ 2 │ [more rows]                                  ││                       │
└──────────────────────────────────────────────────┘└───────────────────────┘
[Sticky band during draft: "On the clock: pick 2.04 · 8 min"]
```

### 15.4 Player Card
```
HEADER: Jordan Addison · WR · MIN · 23.4 · Active · [as-of 2:14 PM]
┌─PVO Summary (full width)──────────────────────────────────────────────────┐
│ ┌─MODEL VIEW──────────────────┐  ┌─MARKET SNAPSHOT──────────────────────┐ │
│ │ PVO  0.72                   │  │ KTC value  7212                       │ │
│ │ xVAR 5.4                    │  │ KTC rank   WR22                       │ │
│ │ Model rank WR16             │  │ DLF rank   WR19                       │ │
│ │ Tier 2                      │  │ ADP        38                          │ │
│ │ [uncertainty band: medium]  │  │ KTC Δ14d   ↑180 [sparkline]           │ │
│ └─────────────────────────────┘  └──────────────────────────────────────┘ │
│ ┌─DIVERGENCE STRIP──────────────────────────────────────────────────────┐ │
│ │ 0─────────────●(model+band)───────────────●(market)──────────100      │ │
│ │ Model lower than market by 18% (uncertainty: medium)                  │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─Model Route──────────┐┌─Valuation Drivers────────────┐┌─Caveats────────┐
│ EngineA v_X →        ││ Career target share % +0.31 ─│││ • PFF wks 12-14 │
│ Feature set v_Y →    ││ Air yards trend        -0.12 ─││   missing       │
│ Fallback ADP v_Z     ││ Team OL pass-block grade+0.18 ─││ • Role uncertain│
└──────────────────────┘└──────────────────────────────┘└─────────────────┘
┌─Market Overlay (time series, two lines explicitly labeled Model / Market)─┐
└─────────────────────────────────────────────────────────────────────────────┘
[footer: decision_supported: false · Open in Trade Lab · Open in Roster Audit]
```

### 15.5 Trade Lab
```
HEADER: Trade Lab · Hypothetical · decision_supported: false · [Save scenario]
┌─Side A: WOODBURY (4col)─┐┌─Analysis (4col)─────────────┐┌─Side B (4col)──────┐
│ + Add player or pick    ││ MODEL VIEW (cool blue)      ││ + Add player/pick  │
│ • B. Robinson  M:6.2 K:7││ A ████████░  B ██████▓     ││ • J. Addison M:5.4│
│ • 2026 1st     M:4.1 K:5││ A higher by 8% (band ±5%) ││ • 2027 2nd  M:2.8 │
│ Roster after: 33/35     ││ MARKET SNAPSHOT (amber)    ││ Roster after: 34/35│
│                         ││ A ███████▓  B ███████      ││                    │
│                         ││ A higher by 3% (KTC 12m)   ││                    │
│                         ││ DIVERGENCE CONTEXT          ││                    │
│                         ││ Per-asset divergence rows  ││                    │
│                         ││ ROSTER PENALTY & PRESSURE  ││                    │
│                         ││ Forced-cut candidates: 1   ││                    │
│                         ││ Package dilution: none     ││                    │
│                         ││ Pick caveats: 2027 1st un. ││                    │
└─────────────────────────┘└─────────────────────────────┘└────────────────────┘
```

### 15.6 League Opportunity Map
```
HEADER: League Opportunity Map · Redzone Champions L. · 12 teams · sync 4m
┌─League Grid (5 col)────────────────┐┌─Selected-Team Inspector (7 col)────┐
│ ┌─T1─┐ ┌─T2─┐ ┌─T3─┐                ││ Roster table (Roster Audit-style)  │
│ │ ME │ │ … │ │ … │                  ││ Potential overlap:                 │
│ └────┘ └────┘ └────┘                ││   Their RB surplus · your RB defct │
│ ┌─T4─┐ ┌─T5─┐ ┌─T6─┐                ││ Market-divergence opportunities:   │
│ │ … │ │ … │ │ … │                  ││  Their RB2: model higher by 19%    │
│ └────┘ └────┘ └────┘                ││  Your WR4: model lower by 22%      │
│ … 12 tiles total in 3×4 grid …      ││ → Open in Trade Lab                │
│ [Toggle: heatmap view]              ││                                    │
└─────────────────────────────────────┘└────────────────────────────────────┘
```

### 15.7 Trust / Governance
```
HEADER: Trust Surface · System state as of 2:14 PM
┌─Model artifact registry────────────────────────────────────────────────┐
│ Model     │ Version │ Last run    │ Coverage      │ decision_supported │
│ Engine A  │ v0.7.2  │ 38m ago     │ 36/36 rookies │ false              │
│ PVO       │ v0.5.0  │ 38m ago     │ 412/450 sklp  │ false              │
│ xVAR      │ v0.3.1  │ 6h ago ⚠   │ 36/36 rookies │ false              │
└────────────────────────────────────────────────────────────────────────┘
┌─Source freshness─────────────────────────────────────────────────────┐
│ Source        │ Last fetch │ Age     │ Coverage notes                 │
│ KTC market    │ 2:02 PM    │ 12m  ✓ │ SF/0.5PPR (league is FullPPR)  │
│ DLF rankings  │ 8:00 AM    │ 6h   ⚠ │ All positions                   │
│ PFF grades    │ Apr 28     │ 18d  ░ │ Unavailable (auth)              │
│ Sleeper sync  │ 2:10 PM    │ 4m   ✓ │ Roster + transactions           │
└──────────────────────────────────────────────────────────────────────┘
┌─Known limitations (curated by David)──────────────────────────────────┐
│ • Engine A pre-draft assumes ADP-implied landing spots.               │
│ • KTC defaults to SF/0.5PPR; model adjusts internally for FullPPR.    │
│ • No injury severity model; injury flags from Sleeper only.           │
└──────────────────────────────────────────────────────────────────────┘
┌─Decision-support promotion log────────────────────────────────────────┐
│ (empty — no artifact has been promoted)                               │
└──────────────────────────────────────────────────────────────────────┘
```

### 15.8 Settings / League Context
```
HEADER: Settings · Redzone Champions L. · Sleeper sync 4m ago
Sections:
  League rules (read from Sleeper API)
    12 teams · Superflex · Full PPR · TE premium tier · Roster slots …
    Taxi: enabled (3 slots, 1st-2nd year) · IR: 3 slots
  Posture
    [ Rebuild ▾ ]  (filters UI only — does not change model)
  Artifacts
    Engine A pinned version: v0.7.2 (auto-update: weekly)
    Display precision: 1 decimal (PVO), integer (KTC), 1 decimal (xVAR)
  Display
    Light / Dark / System
    Density: Compact / Standard
  Notifications
    None (Dynasty Genius is request-pull, not push)
```

---

## 16. Open Questions For David

1. **Posture and the model.** Should "Rebuild / Balanced / Contender" *only* filter UI surfacing, or should it ever weight Engine A's output? Recommendation: filter only.
2. **TE Premium.** This league's exact TE premium setting needs to be confirmed and made visible in Settings. Both the model and the market need to know it.
3. **xVAR currency.** Is xVAR expressed in the same units as PVO, or in different units (in which case it needs an axis label)?
4. **Forced-cut candidates: ordering.** Sort by model value per roster slot, or by model value alone? Current recommendation: per slot, because Superflex roster math is what matters.
5. **Comp panel coverage.** Engine A presumably has comparable-prospect data for rookies. Does it have anything similar for active veterans? If yes, the Player Card should render it.
6. **Market sources.** KTC default values are Superflex / 0.5 PPR; the league is Full PPR. Should the UI display the KTC-as-fetched values, or normalized to Full PPR? Recommendation: display KTC-as-fetched, with a chip noting the format mismatch — never silently transform market data.
7. **Trust surface scope.** Should it list each model's *exact* training data window and last refit date, or only versions and run times? Recommendation: include both, behind a single expand affordance.
8. **Mobile expectation.** Is mobile meant to be read-only review, or full construction? Trade Lab is recommended to be desktop-only for now.
9. **Notes.** Should the Player Card support private notes that persist across sessions? Strongly recommended yes — it converts the Card into a research notebook.
10. **Draft pick uncertainty model.** Engine A's uncertainty band on future picks is critical to Trade Lab. Is there a calibrated model for "2027 1st" pick value uncertainty, or is it currently a fixed prior?
11. **Promotion criteria.** What concretely must happen for an artifact to move from `decision_supported: false` to `true`? The Trust surface needs a defined log, but the criteria themselves must come from David.

---

## 17. Suggested MVP UI Scope

Build, in this order:

1. **App shell.** Left rail, top status strip with freshness + `decision_supported` chip, Cmd-K command bar, right-rail Player Inspector (read-only), persistent posture selector. Component library: shadcn/ui on top of Radix + Tailwind, Inter + tabular-nums.
2. **Player Card.** The two-track scoreboard, divergence strip, model route, drivers, caveats, market overlay, comparable players. Every other surface needs the Card to be solid first.
3. **Roster Audit.** Roster table with full two-track separation, age-curve small-multiples for the four positions (calibrated to RB peak ~25.5, WR peak ~27), capacity bars, forced-cut candidate list.
4. **Trust surface.** Model artifact registry, source freshness table, known-limitations editor, promotion log (empty). The Trust surface unblocks the `decision_supported` chip being meaningful everywhere else.
5. **Home / Command Center.** Today's Review Areas, Roster Pressure Snapshot, Trust & Coverage mini, Recently Changed Signals small-multiples.
6. **Rookie Board.** Ranked table with two-track separation, right-rail inspector, available-now draft state filter.
7. **Settings.** League rules read from Sleeper, posture selector, artifact version pins, density and theme.

The MVP intentionally **does not include** Trade Lab or League Opportunity Map. Both depend on Player Card and Roster Audit being mature, and both are the surfaces where the language and governance rules are easiest to violate. Build them only once the design system has been pressure-tested on simpler surfaces.

Estimated MVP scope: ~6–8 weeks for a single senior full-stack engineer with Figma support, given the existing FastAPI backend. Target stack: Next.js 15 App Router, React 19, TypeScript, Tailwind v4, shadcn/ui on Radix, TanStack Table for the dense grids, Recharts or Visx for sparklines/age curves, SWR for data fetching with explicit `stale-while-revalidate` semantics that match what the Trust surface displays.

---

## 18. Suggested Later UI Scope

In order of value:

1. **Trade Lab** — the highest-risk surface for governance violations, so it lands after the design system is hardened.
2. **League Opportunity Map** — depends on a full league roster sync from Sleeper and on stable posture inference; build after Trade Lab.
3. **Player notes and research notebook** — per-player markdown notes, attached files (CSVs from David's own work), pinnable to Open Decision Items.
4. **Custom dashboards in the Koyfin / Foundry mold** — David configures his own Home variant, saves multiple layouts (e.g., "Pre-rookie-draft," "Trade season"). Use the Koyfin My Dashboards Grouping concept: dashboard widgets share a color group that synchronizes their selected player.
5. **Scenario history and diffing** — saved Trade Lab scenarios with side-by-side diffs of model output across model versions, so David can see how Engine A's view of a trade has shifted over time.
6. **Decision-support promotion workflow** — UI for promoting an artifact from `false` to `true` with required justification fields. This is the surface that converts Dynasty Genius from an advisory tool into a partial decision system, so it ships last.
7. **Mobile parity for Trade Lab** — only after the desktop surface is stable.
8. **Calibration dashboards** — backtest dashboards comparing past Engine A predictions to subsequent outcomes (a small Weights & Biases / MLflow-style model-quality view). Lives inside the Trust surface.
9. **Comparable-prospect drill-down** — clickable historical comps that open their own historical Player Cards.
10. **Light "what changed since I last logged in" diff** — a session-aware diff on Home highlighting deltas since David's last visit. Not personalization, just temporal context.

---

## Caveats on this report itself

- The UI direction here is opinionated and prescriptive. Where Dynasty Genius's actual product needs diverge from these recommendations — particularly around xVAR semantics, posture coupling to the model, and TE premium math — the report's prescriptions yield to David's domain knowledge.
- Aging-curve calibration values in this report (RB peak 25.46, WR peak 26.95, RB cliff 27–28, WR cliff 30–31) are drawn from publicly available football-specific studies (Apex Fantasy Leagues March 2026 PPR study; The Dynasty Edge EPA study, 2014–2024). These are population-level averages with high individual variance; Engine A should always render its own player-specific uncertainty band rather than rely on the population curve as a prediction.
- Comparable-product analysis draws on publicly documented patterns from Bloomberg, Koyfin, Palantir Foundry, Linear, Morningstar, Simply Wall St, Alpha Spread, Stripe, Vercel, KTC, DLF, PFF, FanGraphs/PECOTA aging research, and academic XAI literature (Schoonderwoerd et al., 2021). Several of these tools have private design systems; descriptions here reflect their public-facing docs and product surfaces, with direct quotes used where available.
- This report does not include an accessibility audit. WCAG 2.2 AA compliance (color-blind safe palettes, focus rings, keyboard reachability of every advisory surface) should be a constraint on the design system from day one, not a later pass.
- This report does not propose specific pixel measurements at every component level. Sizes given (e.g., 32px row height, 8px spacing scale, 24px status strip) are starting points; the design system should canonicalize them in tokens.
- The single most important UI risk in Dynasty Genius is the slow drift of language and visual treatment back toward consumer-tool conventions over time. The banned-words list in Section 12 and the anti-pattern list in Section 14 should be enforced in code review as living constraints, not one-time launch criteria.