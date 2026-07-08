# How Fantasy Football Apps Display Data — Claude Independent Research Brief

**Lane:** Claude (implementation lead) — independent research, David's fundamentals-reset step 2 (2026-07-06).
**Method:** four parallel web-research passes (dynasty market tools · platform apps · premium analytics · cross-cutting craft), synthesized here. The market-tools pass read live production HTML/CSS/JS — hex codes, class names, and column labels below are quoted from shipped code, not memory. Anti-anchoring held: no Codex/Gemini artifacts were read before this brief.
**Status:** uncommitted draft; input to the whole-team rethink. Descriptive research — product decisions remain David's.

---

## 1. Rankings 101 — the universal grammar (David: "the most common barometer")

Every serious tool converges on the same row grammar. A rankings row is:

> **rank · identity (headshot + name + position badge + team) · ONE focal value number · trend-over-named-window · status chips** — everything else behind a tap/hover.

Field-verified variants:

| Tool | Row anatomy (actual) | Focal element |
|---|---|---|
| **KTC** | `RANK \| PLAYER NAME \| POS • AGE \| TIER \| 30 DAY TREND \| VALUE` — rank in a solid blue chip `#4db3e9`, value bold blue `#3c9dd1`, right-aligned; NO headshots | rank chip left, value right; quiet gray between |
| **DynastyNerds** | `# \| Player(headshot) \| team-color badge \| Pos \| Age \| Value \| Trend-3mo sparkline+delta \| PPG` — value TEXT COLOR encodes rank band (top-5 dark red → 76+ slate) | color-graded value number |
| **FantasyCalc** | `# \| Name \| Value \| Age` — green rank block `#52995c`, neutral position chip, trend arrow + "+218 last 30 days" | rank block + raw value |
| **FantasyPros ECR** | `RK \| Player \| POS \| AGE \| BYE \| SOS \| ECR VS. ADP` + a RANKS view: `BEST \| WORST \| AVG \| STD.DEV` | sticky rank+name pair |
| **Sleeper** | headshot + name + position color badge + team + opponent + projection + status chips (Q/O/IR) + trend arrows w/ add-drop counts | projection number |

**The 101 laws every tool obeys:**
1. **One number owns the row.** Nobody lets tier, age, and value compete at equal weight. (Underdog: one projection line as typographic hero. PFF: the colored grade chip. KPI craft: hero value 2–3× label size, delta subordinated.)
2. **Trend is always a signed delta over a NAMED window** ("30 DAY TREND", "Trend 3mo", "+218 last 30 days") with glyph + color (green up / red down). Full history charts live one level down (KTC hover card; player pages everywhere).
3. **Identity is visual, not textual.** Headshots (circular, 32–48px, silhouette fallback), team colors as accents, position hue chips. KTC is the one text-only exception and it compensates with the strongest number-as-price branding.
4. **Rows are dense** (~40px condensed sports norm), numbers right-aligned in tabular numerals, text left-aligned, 4–7 visible columns max, depth behind tap.
5. **Format context is a visible persistent control** (KTC Superflex toggle + TEP stepper; FC numQbs/PPR selects) — KTC keeps *separate value databases per format*. A Superflex product must say it's showing Superflex values.

## 2. Rankings advanced — the differentiating patterns

- **Named tiers beat raw ranks.** DynastyNerds ships named, color-graded bands ("Elite Dynasty Assets" → "Roster Fringe"); PFF reads every 0–100 grade through six named tiers (Elite 90+ → Poor ≤49.9) with a stable color ramp. Cognitive basis: chunking (Miller 7±2); statistical basis: Boris Chen's GMM tiers — a tier encodes uncertainty a raw rank fakes precision over. FantasyPros splits ~540 players into 16 tiers via full-width blue divider rows (payload drifts daily: my fetch read 22 experts/539 players; Codex's same-day refetch read 23/540 — cite counts as of fetch time, never as constants).
- **Uncertainty display is a live differentiator, not a nice-to-have.** FantasyPros exposes BEST/WORST/AVG/STD.DEV per player as a first-class view; DynastyNerds draws a Spread bar (green/amber/red by expert-rank range) and highlights "hot takes" (ranker ≥15 spots off consensus); Yahoo Plus sells min/max projection ranges; RotoViz presents projections as the spread of historical comparables' actual follow-up seasons. **Showing disagreement instead of hiding it is a trust mechanic.**
- **Percentile grammar.** PlayerProfiler renders every metric as `value (Nth percentile)` with the cohort named ("#12 of 50 WR"). Composite scores get cards; components get rows; formulas are public.
- **Evidence rides with the number.** DraftKings: every prop line sits next to its filterable historical hit rate; salary next to FPPG. PFF: rank (plain ordinal) is never confused with grade (colored quality) or projection (plain forecast) — three visually distinct encodings.
- **Market anchor column.** PFF puts ADP beside its rank; FantasyPros has "ECR VS. ADP"; DN has ADP +/-. The "our view vs market view" juxtaposition is an industry-standard column — DG's model-vs-market axis has mainstream precedent.

## 3. The other surfaces (post-rankings)

- **Player cards:** ESPN 2025 = sticky header with action buttons, Overview + tabs (logs/splits/depth chart). DN = team-color header panel, accent stripe, ghosted jersey number, headshot at the color intersection. PlayerProfiler leads with a Best Comparable Player card. KTC player page = three big stat blocks (Value / Overall Rank / Positional Rank), value-history chart with range toggles, recent trades, "value-adjacent players." Sleeper's card is thin — reviewers name it a gap.
- **League/matchup views:** Sleeper = points/projected focal, tap-for-scoring-breakdown, GameDay live layer; ESPN = swipe between matchups, sticky score header, live re-projection, "Matchup Moments" feed; win-probability bars are NOT native in Sleeper (third-party extensions fill it).
- **Trade UIs:** Yahoo Trade Hub is the most structured (Most Traded / Team Analysis / League Rosters / Top-3 partner matching by complementary needs). Sleeper's trade tool is the chat itself + multi-team support. FantasyCalc homepage = calculator with "players to equalize" suggestions.
- **Waivers:** Sleeper's trending adds/drops = raw counts over 24h lookback via public API — quantified crowd behavior as a first-class number; ESPN 2025 = "Trending" + roster-aware "Recommended" filters with row-level quick-add; waiver processing as a countdown *event* with results posted to chat.
- **Draft rooms:** Sleeper is board-first (color tiles make position runs visible as color bands); ESPN/Yahoo/NFL are list-first with queue + timer. The board-as-color-field is the strongest ambient use of the position palette anywhere.
- **Mobile:** condensed rows (Yahoo), sticky headers/columns (FP two sticky columns; ESPN sticky everything), card lists replacing tables (DN mobile), bottom sheets over modals (preserve the ranked context behind the detail), 2–4 decision columns max with the rest behind disclosure.

## 4. Cross-cutting craft (the fundamentals under all of it)

- **The position color convention.** Modern standard = Sleeper's palette: **QB `#FF2A6D` · RB `#00CEB8` · WR `#58A7FF` · TE `#FFAE58` · K `#BD66FF` · DEF `#7988A1`** — a CANDIDATE palette only: consistent across multiple community replicas but unverified against any official Sleeper source; per Codex cross-review, these hexes must NOT enter a token spec without direct screenshot sampling or source confirmation. The hue *family* (QB pink/red, RB teal, WR blue, TE orange) is the high-confidence claim. These hues were designed FOR dark surfaces. Applied as chips/badges/left-borders — never full-row fills. Position-hue and delta-color are two token families that must never collide. David's league lives on Sleeper: this color language is his muscle memory.
- **Table craft:** tabular lining numerals (`font-variant-numeric: tabular-nums`) or right-aligned columns don't align; consistent decimal precision per column; whitespace + single-direction 1px rules over zebra (zebra collides with hover/selected states); identity column frozen under horizontal scroll; sparkline in the rightmost slot.
- **Sparklines (Tufte):** word-sized, ~45° banked slope, endpoint dot + printed current value (a sparkline without its number is decoration), light context band not axes, shared y-scale only if cross-row comparison is the point.
- **Delta semantics:** glyph-first (▲/▼ + sign), color second — CVD-safe. If red/green, shift toward teal-green `#009E73` / vermillion `#D55E00`.
- **Identity assets:** headshot fallback chain (headshot → initials-on-position-color disc → silhouette; never a broken image). Sleeper CDN serves headshots at predictable URLs with silhouette fallback; nflverse ships `headshot_url` + placeholder pattern. Team colors from teamcolorcodes/teampalettes; store primary+secondary per team, pick per theme; many official primaries fail contrast on dark — use as accents (avatar ring, 3px bar), never text color. Trademark reality: private non-commercial single-user use is the low-risk class; colors+abbreviations are cleaner than logo files.
- **Dark theme:** base `#121212`-class (Sleeper: `#0d0d14/#15151e/#1c1c28` + teal accent), elevation = lighter surface (4%→16% white overlay), desaturated accents, AA 4.5:1 tested against elevated surfaces, charts get their own dark palette.
- **Motion:** skeletons with left-to-right shimmer mirroring real layout; count-up once on first hero-value reveal (~500–800ms), never on sort/filter; FLIP row-reorder animation preserves object constancy; one-shot decay pulse for a just-changed value; `prefers-reduced-motion` always; no looping ambient motion in data regions.
- **Habit mechanics observed:** KTC's vote-toll ("submit a KTC periodically to see the rankings") + every-vote freshness; Sleeper's chat/trending/waiver-countdown; DK's stated 5-minute refresh cadence; PFF's known "grades drop Monday" rhythm. **Pattern: state the refresh cadence explicitly — a known cadence is itself a habit hook** (maps to our compounding-product lens).

## 5. What this means for Dynasty Genius (my lane read — for the rethink, not a prescription)

**Why Task-5 read as disappointing, in research terms:** the daily open violated the 101 laws — no visual identity layer (headshots/team/position color), no focal number hierarchy, no trend-over-named-window microviz, prose lines where the industry uses one hero value + subordinated context. It was typographically honest but informationally flat: every fact at equal weight is the opposite of every successful surface studied here.

**The gap DG occupies is real and confirmed:** Sleeper (our league host) has thin player analysis and no native analytics layer; market tools show market price but no model view; nobody but FP/DN/RotoViz shows disagreement/uncertainty well, and nobody joins **model vs market with receipts**. The model-vs-market side-by-side is already an industry column pattern (ADP-vs-rank) — DG's version is differentiated by the model being ours and the divergence being tracked over time.

**Constitutional mapping (where patterns are legal, gated, or banned):**
- LEGAL NOW: position color system (descriptive identity, not verdict); headshots/team identity; tabular-numeral dense tables; sparklines + named-window deltas on captured history (we own real PIT series); focal-number hierarchy; percentile grammar `value (Nth of cohort)` — matches our existing `dvs_pct`/percentile fields; FP-style spread/disagreement display; explicit refresh-cadence stamps; skeleton/shimmer + one-shot change pulses (Carbon motion tokens already shipped).
- GATED (roadmap Step 1, 00 amendment): named tier bands — DN's "Elite Dynasty Assets" and PFF's named tiers are exactly the David-ratified calibrated-lexicon shape (Generational/Elite/Cornerstone/Starter/Depth), word+number, hysteresis. Until the amendment lands, tier bands can exist with NEUTRAL labels (Tier 1..N, FantasyPros-style) — legal today.
- BANNED (cordon holds): KTC's Keep/Trade/Cut action lexicon; ESPN's "Recommended for your roster" framing; matchup-quality green/red as *advice* coloring; verdict colors on values; DN-style "hot take" editorializing without basis disclosure.
- HONESTY EDGE (ours to own): RotoViz-style comp-anchored ranges and DK-style evidence-adjacent-to-number are *stronger* honesty patterns than anything in our current UI — the receipts architecture (H2 vision) is the right chassis; research says surface the evidence NEXT TO the number, not only behind a focus interaction.

**Levers David already named, now research-confirmed:** self-hosted headshots + team-color map (Sleeper CDN pattern + fallback chain) and bold in-cordon position hues (Sleeper palette as the reference family) are indeed the two biggest DN-parity levers; add the third the research surfaces: **one focal value number per row with everything else subordinated** — the cheapest, largest single upgrade.

---
*Sources: cited inline in the four underlying research passes (retained in session transcript); key primary sources — keeptradecut.com live HTML/CSS, dynastynerds rankings widget v1.21.2 JS, fantasycalc Angular bundles + public API, fantasypros ecrData payload (22 experts/539 players at my fetch; 23/540 at Codex's refetch — daily drift; 16 tiers stable), Sleeper support docs + public API docs, ESPN 2025 redesign press materials, PFF grades/premium-stats docs, playerprofiler live player pages, Tufte sparkline notebook, A List Apart table typography, NN/g mobile tables + bottom sheets + skeletons, Material dark theme.*
