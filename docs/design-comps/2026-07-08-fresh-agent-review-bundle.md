You are a fresh, independent reviewer. Give an adversarial critique — find what's weak, not reasons to approve. Frictionless praise is a failed review.

# What I need
I'm building "Dynasty Genius," a private dynasty-fantasy-football asset terminal for one user (David, Superflex PPR). Below is a PRE-CODE COMPOSITION (design thinking, no code yet) for two core surfaces, followed by the design foundation (PRODUCT.md + DESIGN.md excerpts) and the constitutional No-Verdict rule it must honor. Critique the COMPOSITION against that foundation.

Core thesis: our edge is the MARGIN between OUR model's value for a player and the MARKET's value for that same player, across the whole universe — shown heat-mapped on every comparable player. Honesty rule we CANNOT break: we SHOW the disagreement descriptively; we do NOT claim it proves we're right (unvalidated hypothesis) — no buy/sell/underpriced/edge/target language, no verdict colors (no green/red), model and market shown as equal-weight lanes (blue=model, amber=market).

Reality the design must survive honestly: our value = a 0–100 model score (DVS); market = 0–~9000 (FantasyCalc); the margin is therefore in PERCENTILE space (where we rank a player vs where the market does). Coverage is thin: ~168 of ~12,000 players have a real signal; ~11,900 are "no model read yet"; HALF of David's own roster — including his best (young/rookie) players — has no margin signal.

# Critique these, specifically (cite the part you react to)
1. Thesis fit: is the MARGIN genuinely the hero of each surface's 5-second answer + focal hierarchy?
2. Honesty: where could the heat-map / bars / copy STILL read as a buy/sell verdict? Any place "we're right" leaks in?
3. Fantasy-native quality: does this read as a best-in-class asset terminal (Sleeper / DynastyNerds / KeepTradeCut bar) or slide toward a developer diagnostics console? Name the exact elements doing each.
4. Coverage: is the design honest AND still worth opening daily when David's marquee players show "no model read"? Would he be disappointed? What makes that state land vs feel broken?
5. Comprehension: does percentile-vs-percentile ("model 63rd / market 28th, +35") land as intuitively as "we say 100, market says 50"? Too abstract? Propose a clearer encoding.
6. The two-surface split (universe Margin Board vs roster Daily Open): right call, right altitude, missing states?
7. The single biggest risk this becomes another disappointing surface, and the one change you'd make first.

Output: numbered findings, most-severe first, each with a concrete fix. Then score 1–10 (name any below 7): first-viewport story, fantasy-native identity, information hierarchy, density, color discipline / lane isolation, mobile integrity, honesty (No-Verdict integrity). Push hard.

═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT UNDER REVIEW — the composition
═══════════════════════════════════════════════════════════════════════════════
# Composition Package — The Value Margin Surfaces

> **Status:** pre-code composition artifact (shape-before-code gate, DESIGN.md §Enforcement). No production code. Feeds a disposable real-content static comp and the cockpit review, then David's directional preview.
> **Date:** 2026-07-08 · **Author:** Claude (impeccable `shape`) · **Register:** product
> **Governs:** PRODUCT.md + DESIGN.md + 00-product-constitution.md (No-Verdict Line) + the CORE THESIS (below).
> **Uncommitted** pending David's word.

---

## 0. The core thesis this serves (David, 2026-07-08)

The product exists to hold a **better, more accurate, more predictive value for each player than the market.** The competitive edge is the **MARGIN** between *our* per-player value and the *market's* per-player value, across the player universe. The margin must be **visible on every player, heat-mapped.** "What changed" / trends are **secondary and gradual** (our values rest on large samples; week-over-week they barely move) — surfaced, but never the hero.

**Two core surfaces (David: "both are core surfaces"):**
1. **The Margin Board** — the universe view. Every comparable player, ranked, our-value vs market-value margin heat-mapped on every row. (This is the "rankings first" surface.)
2. **The Daily Open** — the roster-scoped daily entry. My roster's margins + what the market did to them overnight + a whisper that data is fresh.

Both compose from the same central object: **the margin.**

---

## 1. What the REAL data forced (honesty substrate — read before the designs)

I grounded this in the live artifacts, not fixtures. Four facts reshape the design:

**A. The margin already exists, computed honestly.** `app/data/valuation/universe_market_divergence_latest.json` (`universe_market_divergence.v1`, Phase 17.4) computes per player: `model_percentile`, `market_percentile`, `model_minus_market_delta`, a typed `signal` (`MODEL_HIGH_MARKET_LOW` / `MODEL_LOW_MARKET_HIGH` / `INSIDE_BAND` / `UNAVAILABLE`), `decision_supported: false`, no imperative language. We are not inventing the margin; we are giving an existing honest artifact a world-class surface.

**B. The scale problem is already solved — the margin lives in PERCENTILE space.** Our value is **DVS 0–100** (median 48). Market value is **FantasyCalc 0–~9,000**. You cannot subtract them. The honest common ground is **percentile-within-universe**: where WE rank a player vs where the MARKET ranks him. So David's "we say 100, market says 50" renders honestly as **"model 63rd percentile / market 28th percentile, +35"** — the disagreement, scale-free. Raw DVS and raw market value ride along as receipts, never as the cross-player-comparable number.

**C. Coverage is the dominant truth, and it must be designed, not hidden.** Of 12,201 players: **168 have a real divergence signal** (109 we-value-higher, 59 we-value-lower), **104 agree** (inside band), **11,929 are UNAVAILABLE** (no model-backed value). A literal "heat-map on every player" is ~98% empty cells. The honest hero is *the ~272 players we can actually compare* — the board's job is to make those sing and to render "unavailable" as a designed, explained state.

**D. Half of David's own roster is UNAVAILABLE — including his best players.** Of his 27 rostered assets: 14 have a signal (3 we-high, 4 aligned, 7 we-low); **13 are unavailable — Ashton Jeanty, TreVeyon Henderson, Jaxson Dart, Luther Burden** and other young/rookie players the *active* model can't value yet (no NFL usage; rookie-engine values aren't joined into this artifact). **The margin hero is blank for his marquee names.** The design must treat this as a first-class, well-designed, explained state — or the surface reads as broken exactly where David looks first.

**Real magnitudes** (David's roster, today): we're higher than market on Xavier Legette (model 63rd / market 28th, **+0.35**), Kaelon Black (+0.26), Theo Johnson (+0.15); lower on Parker Washington (−0.29), Fernando Mendoza (−0.23), AJ Barner (−0.20), Rome Odunze (−0.14). Universe extremes: Jonnu Smith **+0.85** (model 96th / market 11th), Drake Maye **−0.43** (model 55th / market 98th).

**The honesty boundary (rides on everything below):** we SHOW the margin; we do NOT claim it proves we're right. `decision_supported=false`. The margin is a **hypothesis** — many "we're high" cases are the model under-discounting age (old vets); many "market's high" cases are Superflex-QB scarcity or rookie draft capital the model is cautious on, where the market may be right. The **compounding realized-outcome track record** is what earns "more accurate than market" over time. No buy/sell/underpriced/edge/target/act. No tool-nominated single player. Lanes symmetric; no verdict hues.

---

## 2. The shared central object — the Margin Row

Both surfaces compose from one row grammar (extends DESIGN.md's canonical AssetRow; the margin is the focal value):

```
rank · pos-chip · IDENTITY (headshot+name+team) · [ MODEL ▸——gap——◂ MARKET ]dual-percentile bar · +Δ focal · signal chip · trend(small) · receipt
```

- **The focal value is the signed margin** (`+35` / `−29`), Archivo, 2–3× weight, right-aligned tabular — the one number that owns the row.
- **The dual-percentile SpreadBar** (existing primitive, `lane` prop) is the visible proof: a **model-blue** mark and a **market-amber** mark on one shared 0–100 axis; the gap between them IS the margin, direction-carrying without any verdict hue. This is the heat-map, per-row.
- **Signal chip** (neutral, glyph + word): "Model higher" / "Market higher" / "Aligned" / "No model read." Direction is data, not judgment.
- **Receipts** (focusable, beside the number): raw DVS, raw market value + rank, market source + as-of, the failed-gate reason when unavailable, `decision_supported=false` in manager prose.
- **Coverage state is part of the grammar:** a row is *covered* (margin + bar), *aligned* (bar with marks nearly overlapping, quiet), or *unavailable* (identity intact, margin slot shows a designed "No model read yet — [reason]", never a fake 0 or blank).

**Heat-map encoding (David's ask, No-Verdict-safe):** magnitude → bar gap length + a low-chroma intensity ramp *within each lane's own hue* (deeper blue = we're more above market; deeper amber = market more above us). **Never green/red.** Direction is carried by which lane leads, redundantly with the signal-chip glyph (no color-only meaning).

---

## 3. SURFACE 1 — The Margin Board (universe view, "rankings first")

### 5-second answer
> "Across the players I can actually compare, here's where my model most disagrees with the market — and which way it leans."

The eye lands on a ranked list sorted by **|margin|**, each row showing the dual-percentile bar and the signed delta. In five seconds David sees the biggest disagreements, top of list, both directions legible.

### Focal hierarchy
1. **The margin column** (dual-percentile bar + signed Δ) — owns the eye, every row.
2. **Player identity** (headshot + name + team-color ring) — recognition infrastructure.
3. **Signal direction** (chip glyph) — which way the disagreement leans.
4. Position-rank chip, raw receipts — support, quiet.
5. Coverage/health, source provenance — whisper / drawer, never the story.

### Lane-order statement
Model (blue) is the product's voice and reads **left** on the shared axis; Market (amber) is the overlay and reads **right**; the delta is neutral. Lanes are visually equal weight — neither is "correct." Identity/position hues are orthogonal, desaturated, and never collide with blue/amber (accent-subordination law).

### Layout strategy
A dense, Bloomberg-grade board. **Default view = the ~272 comparable players** (168 signal + 104 aligned), sorted by |margin| desc. Controls (quiet, top): sort (|margin| / model% / market% / position), filter (Model-higher / Market-higher / Aligned / by position), and a coverage toggle. **Value-band dividers** group the list ("MODEL HIGHER THAN MARKET (109)" / "ALIGNED (104)" / "MARKET HIGHER (59)") with counts — the honest census, first. The 11,929 unavailable players are **not** rendered as a rainbow of empty cells; they live behind an explicit "Uncovered universe (11,929) — no model read yet" section/filter with the reason, so coverage is honest and legible, never faked.

### Desktop viewport sketch (~1440px)
```
┌───────────────────────────────────────────────────────────────────────────┐
│ THE MARGIN BOARD          model vs market · percentile disagreement   ⌂ ⚙  │
│ 272 players compared · 11,929 no model read yet          [freshness whisper]│
│ sort: |margin| ▾   filter: All ▾ · position ▾        [ Model↑ · Market↑ · = ]│
├───────────────────────────────────────────────────────────────────────────┤
│ ▸ MODEL HIGHER THAN MARKET (109) — we rate these above the crowd            │
│  1  TE  ◍ Jonnu Smith      MIA   [M ●96 ────────────── 11○ K]  +85  ⓘ       │
│  2  TE  ◍ Noah Fant        SEA   [M ●78 ──────────── 12○ K]    +66  ⓘ       │
│  3  RB  ◍ Kareem Hunt      KC    [M ●63 ───────────  2○ K]     +61  ⓘ       │
│  …                                                                          │
│ ▸ ALIGNED — model and market agree (104)                                    │
│     WR  ◍ Garrett Wilson   NYJ   [M ●91◉91 K]                   ±0  ⓘ        │
│ ▸ MARKET HIGHER THAN MODEL (59) — crowd pays a premium we don't            │
│     QB  ◍ Drake Maye       NE    [K ○98 ────────────── ●55 M]  −43  ⓘ       │
│     RB  ◍ Blake Corum      LAR   [K ○69 ──────── ●18 M]        −50  ⓘ       │
│ ─────────────────────────────────────────────────────────────────────────  │
│ ▸ Uncovered universe (11,929) — no model read yet · why ⓘ      [ expand ]   │
└───────────────────────────────────────────────────────────────────────────┘
   M ●  = our model percentile (blue)   K ○ = market percentile (amber)
   bar gap = the margin; deeper hue = larger gap. No green/red.
```

### Mobile viewport sketch (~390px)
```
┌───────────────────────────┐
│ MARGIN BOARD        ⌂ ⚙   │
│ 272 compared · fresh 6:12 │
│ [Model↑][Market↑][=][pos] │
├───────────────────────────┤
│ MODEL HIGHER (109)        │
│ ◍ Jonnu Smith  TE·MIA     │
│   M●96 ─────── 11○K  +85  │
│ ◍ Noah Fant    TE·SEA     │
│   M●78 ────── 12○K   +66  │
│ …                         │
│ MARKET HIGHER (59)        │
│ ◍ Drake Maye   QB·NE      │
│   K○98 ─────── 55●M  −43  │
├───────────────────────────┤
│ Uncovered (11,929)  ⓘ  ▸  │
└───────────────────────────┘
 tap row → bottom-sheet receipts
```

---

## 4. SURFACE 2 — The Daily Open (roster-scoped daily entry)

### 5-second answer
> "On my roster: where my model and the market disagree, and what the market did to those gaps overnight — with a quiet sign the data is fresh."

### Focal hierarchy
1. **My roster's margins** — the same Margin Row, scoped to my players, sorted by |margin|; the covered players lead.
2. **Coverage honesty line** — "14 of 27 players have a model read; 13 pending (young players, not enough NFL usage yet)." Stated plainly, once, high — because his stars are in the pending set.
3. **The overnight margin-shift tape** (secondary, small) — "the market moved on these players since yesterday, widening/narrowing the gap": market-driven, because our anchor holds. This is the honest, *minor* "what changed."
4. **Freshness whisper** (ambient) — "captured 6:12 AM," glanceable, zero-attention when healthy.
5. **Degraded banner** (exception only) — loud, unmissable, dashes the affected lane, only on real failure.

### Lane-order statement
Identical to the board: model-blue left, market-amber right, neutral delta, equal weight, orthogonal identity hues. The roster summary line leads in manager prose before any rows (DESIGN.md canonical-row law): *"Your roster vs the market: model higher on 3, market higher on 7, aligned on 4, 13 awaiting a model read."*

### Key states
- **Default (today's real data):** roster summary line → covered margin rows (14) → "awaiting model read" group (13, identity intact, reason given) → small overnight-shift tape → freshness whisper.
- **Quiet day** (market barely moved): the tape collapses to "Market held — gaps unchanged overnight." Designed, not empty-error. The margins (the hero) are still fully present — they don't need a "change" to be worth seeing.
- **Stale/failed market capture:** loud degraded banner; market lane dashes (`—`); never last-known-as-fresh (falsification seed).
- **Unavailable player:** identity + "No model read yet — [young player / insufficient usage]"; never a fake 0 margin.
- **Zero-crossing / tie:** delta exactly 0 → aligned; `−0.0` preserves sign; ties sort deterministically by canonical id.

### Desktop viewport sketch
```
┌───────────────────────────────────────────────────────────────────────────┐
│ DAILY OPEN — Woodbury Riders                              captured 6:12 AM  │  ← whisper
│ Your roster vs the market: model higher on 3 · market higher on 7 ·         │
│ aligned on 4 · 13 awaiting a model read.                                    │
├───────────────────────────────────────────────────────────────────────────┤
│  WR  ◍ Xavier Legette   CAR   [M ●63 ───────── 28○ K]   +35  Model higher ⓘ │
│  RB  ◍ Kaelon Black     SF    [M ●69 ─────── 44○ K]     +26  Model higher ⓘ │
│  WR  ◍ Rome Odunze      CHI   [K ○84 ──── ●69 M]        −14  Market higher ⓘ│
│  QB  ◍ Fernando Mendoza LV    [K ○80 ─────── ●57 M]     −23  Market higher ⓘ│
│  WR  ◍ Parker Washington JAX  [K ○76 ──────── ●47 M]    −29  Market higher ⓘ│
│  …aligned (4)…                                                              │
│ ─ Awaiting a model read (13) — young players, not enough NFL usage yet ──── │
│  RB ◍ Ashton Jeanty LV · RB ◍ TreVeyon Henderson NE · QB ◍ Jaxson Dart NYG …│
├───────────────────────────────────────────────────────────────────────────┤
│ Overnight: market moved on 6 of your players — gaps widened on Odunze,      │  ← small tape
│ narrowed on Legette. (Model held.)                                    ▸    │
└───────────────────────────────────────────────────────────────────────────┘
```

### Mobile viewport sketch
```
┌───────────────────────────┐
│ DAILY OPEN      fresh 6:12 │
│ Riders vs market:         │
│ 3 model↑ · 7 market↑ · 4= │
│ 13 awaiting a read        │
├───────────────────────────┤
│ ◍ X. Legette WR·CAR       │
│  M●63 ───── 28○K   +35    │
│ ◍ R. Odunze  WR·CHI       │
│  K○84 ── 69●M      −14    │
│ …                         │
│ Awaiting a read (13) ▸    │
├───────────────────────────┤
│ Overnight: market moved   │
│ on 6 · model held      ▸  │
└───────────────────────────┘
```

---

## 5. Interaction & motion
- **Row → receipts:** tap/click opens the inspector (desktop drawer / mobile bottom-sheet) with raw DVS, raw market value+rank, source+as-of, failed-gate reason, `decision_supported=false` in prose, and the model/market percentile derivation. Keyboard-first, focusable, Esc closes.
- **Motion:** productive only (150–240ms). The dual-percentile bar marks settle on load (object-constancy, reduced-motion-safe); no urgency, no count-up except a single first hero reveal; no drawing past the Hard Right Edge on any trend spark. The margin is never animated to imply confidence.
- **Trend sparkline** (where shown) is the *market* series terminating at the Hard Right Edge — small, in the receipt/inspector, not the row hero (trends are secondary).

## 6. Content / copy (manager prose, no schema nouns)
- Signal chips: "Model higher" · "Market higher" · "Aligned" · "No model read yet."
- Coverage: "14 of 27 players have a model read." / "Awaiting a model read — young players, not enough NFL usage yet."
- Honesty cordon (focusable, one designed block, not stacked warnings): "These are disagreements between our model and the market's prices — a descriptive hypothesis, not a validated recommendation. We haven't yet proven our value is the more accurate one; the track record earns that over time."
- Freshness whisper: "captured 6:12 AM." Degraded: "Market data hasn't refreshed since [time] — gaps may be stale."
- **Banned everywhere:** buy/sell/hold/start/sit, underpriced/overpriced, edge/target/gap-to-exploit/value window/arbitrage, recommended/priority/act, any tool-nominated "player of the day."

## 7. Recommended impeccable references for build
`layout.md` (dense board rhythm), `typeset.md` (Archivo focal value vs mono receipts), `animate.md` (bar-settle, reduced-motion), `harden.md` (unavailable / stale / tie / zero-cross states), `clarify.md` (signal + coverage copy).

## 8. Open questions for David / fresh agents (I've defaulted where I can)
1. **Percentile margin as the primary number** (recommended) with raw DVS + market value as receipts — confirm, vs leading with a raw-value "we say / market says" number (needs a rescale assumption; less honest cross-player). *Default: percentile primary.*
2. **David's marquee players are uncovered.** Is the near-term Daily Open honest-and-useful with the covered 14 + a clear "awaiting a read (13)" section (my design), or does the **coverage gap need closing first** — joining rookie-engine (Engine A) values so Jeanty/Henderson/Dart get margins? That's a real producer build (its own RED/GREEN), and arguably the highest-leverage next step after this composition. *Flagging, not deciding — it's a roadmap call.*
3. **Board default scope:** covered-players-first with uncovered behind a filter (my design) vs showing the full universe with unavailable inline. *Default: covered-first; uncovered explicit but not faked.*
4. **The live producer join.** Both surfaces read a margin the live Daily Open producer doesn't yet expose (it came through `0`/`null`). Wiring `universe_market_divergence` into the serving path is the follow-up build that makes these surfaces real end-to-end. The disposable comp will hand-join the real artifact values so the preview is truthful now.

---

*Composition artifact only. Next: cockpit adversarial review → disposable real-content static comp (hand-joined real margin values) → David's directional preview. No production code until the composition is cleared and David authorizes implementation.*


═══════════════════════════════════════════════════════════════════════════════
# DESIGN FOUNDATION — PRODUCT.md (the WHAT / the honesty+aesthetic frame)
═══════════════════════════════════════════════════════════════════════════════

# Product

> Distilled from the David-ratified design corpus and the foundation-redo synthesis
> (`docs/strategies/2026-07-07-design-foundation-redo-synthesis.md`), which itself draws on
> `docs/strategies/2026-07-05-world-class-frontend-research-brief.md`,
> `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`,
> `docs/strategies/2026-07-06-claude-fantasy-ui-research.md`,
> `docs/strategies/2026-07-06-fantasy-app-data-display-research-codex.md`,
> `docs/strategies/2026-07-06-fresh-agent-design-reviews.md`, and
> `docs/governance/00-product-constitution.md`. Those documents govern on any conflict; this
> file is the working design foundation the impeccable skill injects each session. Working
> draft, tracked in-repo; changes committed only with David's word.

## Register

product

## Users

One user: David — a dynasty fantasy football manager (Superflex PPR, 12-team league) with 15 years of enterprise-software judgment. Daily-login context: the morning check of what changed overnight in his league's market prices and his model's outputs. He is in a decision workflow (trade, cut, waiver, draft). The product's job is to make him *want* to open it every morning, surface verified facts, ranges, and provenance he can act on — and never to decide for him.

## Product Purpose

Dynasty Genius is a private, single-league **dynasty asset terminal** — a daily point-in-time record of one league's reality wired to a model that refuses to lie about what it knows. It lives in the Sleeper / DynastyNerds / KeepTradeCut category on the surface, and is built to be more honest than any of them underneath. Success = David makes dynasty decisions that look correct 3–7 years out, trusting the surface because every number carries a receipt, *and* enjoys the daily scan because the screen is genuinely a pleasure to read.

## The polarity (read this first)

**Honesty is the substrate. Fantasy-native legibility is the aesthetic.** The constitutional constraints — no verdicts, two isolated lanes, receipts on every number, the Hard Right Edge — are the non-negotiable *frame*, not the design goal. Inside that frame the product must look and feel best-in-class for its category: ranked rows, real player identity, one focal value per row, tiers, trends, hero moments. The failure mode this foundation exists to kill is "an honest developer diagnostics console wearing a fantasy skin." Credibility is the floor; a striking, legible, alive surface is the goal. Both, always — never one as an excuse to skip the other.

## Brand Personality

A private trading terminal for a serious dynasty manager: dense, fast, credible — **and desirable, striking, alive, human.** The screen speaks dynasty-manager prose; technical precision lives one layer down in receipts and title attributes. The jaw-drop is *visible* — the focal value number, real player faces, the σ range, the tier bands, the one orchestrated daily-open entrance — earned by craft, never by chrome. Boldness is spent generously on legibility and hierarchy, never on decoration.

## Anti-references

- **Developer/diagnostics UI** — raw schema nouns, snake_case constants, ISO timestamps, database IDs, `Status: ok` plumbing, or a System-Diagnostics panel anywhere in a user viewport. An engineer's admin view is the single thing this product must never resemble.
- Consumer fantasy-app **cheerleading** — green/red verdict colors, "BUY NOW" energy, urgency motion, pulsing deltas. (Reject the verdict *semantics*, not the category's visual richness.)
- Generic dashboard gloss: glassmorphism, backdrop blurs, gradient chrome; SaaS hero-metric cards; identical card grids.
- Dark-terminal-with-acid-accent template aesthetics.

## Design Principles

1. **Fantasy-native first, governed underneath.** The visible grammar is a Sleeper/DN/KTC-class asset terminal — ranked rows, player identity, focal values, tiers, trends, hero cards. Honesty is the substrate beneath, never the surface aesthetic.
2. **The canonical row is a fixed contract.** `rank · position-rank chip · identity (headshot + name + team) · ONE focal value · named-window trend · status/receipt chips`. One number owns the row (2–3× label weight/size, right-aligned tabular); current value and its delta always travel together; no per-row label repetition; a rank with no disclosed basis is a defect. Every surface (player card, Trade Lab, league, waiver, rookie board) composes from this row. **The macro answer comes first:** the Daily Open opens with a roster-level summary line in manager prose ("Your roster overnight: model value +1.2%, market −0.4%" / "Quiet morning — no model changes, market held") before any rows, so the morning scan never starts as mental math.
3. **Player identity is required recognition infrastructure.** Headshots with the mandatory fallback chain (headshot → initials-on-position-color disc → silhouette; never a broken image, never a raw id). Team = abbreviation + color mark as a ring/chip, never a row-fill, never a logo. Identity is factual, orthogonal to the model/market lanes.
4. **No verdicts, ever.** Descriptive surfaces issue no buy/sell/hold, no recommended action, no verdict hues. Direction is data (signed, neutral), not judgment. Aspiration language never smuggles a verdict ("edge/target/priority/Elite/Bust" are watched words). **No system-nominated single-player hero** — a tool-selected "biggest mover" or "story of the day" is an implicit verdict; single-player emphasis is legitimate only when user-selected, David-supplied, aggregate, or explicitly lane-symmetric and non-actionable (the banned MoverHero pattern). The first viewport preserves the surface's declared order and lane symmetry — never a market-only recency lead. `decision_supported=false` until validation earns otherwise.
5. **Two-lane truth, visibly a system.** Model (blue) and market (amber) are structurally isolated *and* the hues actually frame their own objects on the primary surface — not spent on nav links while the model card shows no blue. Position and delta color are orthogonal token families that never collide with the lane hues. A market swing must never read as a model signal.
6. **The scaffolding-hide law.** No implementation artifact reaches the surface: no raw IDs, snake_case, ISO timestamps, diagnostics panels in the hero, or roadmap/DEVELOPER chrome in nav. Every quiet, pending, and failure state is a *designed* state. **Proportionality (the ban is not only lexical):** system, trust, freshness, and caveat plumbing may never be the *primary first-viewport story* even in polished manager prose — the first screen is a fantasy/asset narrative, not a status board.
7. **Honesty is designed, not dumped — "visible, not wallpaper."** Receipts, caveats, disclosed bases, and the Hard Right Edge stay — rendered as designed elements, with evidence riding *next to* the number, not only behind hover. Uncertainty display (σ ranges, percentile-of-cohort, disagreement) is DG's signature honesty asset, not italic monospace wallpaper. **Layered caveats:** only high-priority blocking warnings (e.g., the ≥26h stale badge) render as active blocks in the primary viewport; minor disclaimers, model-basis notes, and diagnostics tuck into a collapsible caveats/provenance drawer or the inspector — never 4–5 warnings stacked on the active screen.
8. **Tiers reveal cliffs; trends show direction, never urgency.** Value-band dividers with a disclosed basis answer "where is the cliff to the next cluster?" (neutral labels legal now; calibrated-lexicon names gated behind the 00 amendment; no verdict hue). Trends are a signed delta over a named window, glyph-first and CVD-safe, weighted so magnitude is legible.
9. **Mobile is a first-class layout**, not a squeezed desktop: daily tape + top changed rows, collapsed nav, status pill over pinned panels, bottom-sheet inspector, no horizontal overflow.
10. **The shipped app is the design artifact, and contract-green is never a visual GREEN.** Whole-viewport (not the diff) is the review unit; a scored benchmark-delta against the Sleeper/DN/KTC bar is the instrument; an independent, unanchored fresh-agent visual audit is the standing pre-David gate; mid-scroll captures are mandatory in every evidence bundle (full-page screenshots hide sticky/overlay collisions). **Shape before code:** every surface build starts from a required pre-code composition artifact (the 5-second answer, the focal hierarchy, a desktop+mobile viewport sketch, and the lane-order statement) — the audit gate must never be the first time composition is judged. The bar is "truly exceptional," per David's standing directive.

## Accessibility & Inclusion

Keyboard-first: every receipt/disclosure focusable and operable (Enter/Esc/touch; hover is enhancement only). Visible focus via the governed `--dg-focus` grammar in both themes. `prefers-reduced-motion` honored by every motion class. axe violations = 0 on shipped surfaces; contrast at WCAG AA minimums. No information carried by color alone (constitutionally reinforced — hue never carries verdict meaning anyway).


═══════════════════════════════════════════════════════════════════════════════
# DESIGN FOUNDATION — DESIGN.md (the HOW / tokens, row, primitives, motion)
═══════════════════════════════════════════════════════════════════════════════

# Design

> The HOW layer beneath `PRODUCT.md`. Captured from the shipped visual system
> (`frontend/src/styles/tokens.css`, `frontend/src/styles/motion.css`,
> `frontend/src/ui/ui.css`) and the foundation-redo synthesis
> (`docs/strategies/2026-07-07-design-foundation-redo-synthesis.md`). Governing law: H2 vision
> spec v3 §3 (tokens) + §8 (aesthetic cordon), reset spec v1.6, `00-product-constitution.md`.
> Working draft, tracked in-repo; changes committed only with David's word.

## Theme

Film-room charcoal, dark-first (`[data-theme="dark"]` on `index.html`); a light scope carries the same hues. Hue *meaning* is constitutional and identical across themes — themes shift lightness/chroma only. Dark elevation = lighter surface (a 4%→16% white overlay ramp), desaturated accents, AA 4.5:1 against the *elevated* surface, charts on their own dark palette.

## Color (OKLCH only; tokens only — raw color literals are test-banned in governed files)

- Canvas `--dg-bg` `oklch(0.16 0.010 250)` · surfaces `--dg-surface` / `--dg-surface-raised` step up in lightness.
- Ink `--dg-text` `oklch(0.92 0.005 250)` · `--dg-text-muted` `oklch(0.68 0.008 250)`.
- Borders `--dg-border` / `--dg-border-strong`. Whitespace + single-direction 1px rules over zebra (zebra collides with hover/selected).
- **Model lane (the product's voice): blue** `--dg-model` family, hue 255 — must actually frame model objects on the primary surface.
- **Market lane (overlay only): amber** `--dg-market` family, hue 75 — frames market objects only; never blended into a model reading.
- Structural warnings only: `--dg-caveat` / `--dg-cliff`. **No green/red anywhere. No verdict hues.**
- Position categoricals (`--dg-pos-*`) and the DVS neutral ramp (`--dg-dvs-floor/ceiling`) are orthogonal to both lanes and to delta color — three token families that must never collide.
- Focus: `--dg-focus` high-contrast ring, both themes.
- **Content-is-style:** the visual system is built from the data itself — team colors as micro-accents (rings/chips, never row-fills), lane hues on lane objects, and **type weight/size as the primary contrast lever.** This is what lets a striking surface keep the blue/amber isolation clean.
- **Accent-subordination law:** the lane hues (blue/amber) own the primary chroma on any row. Position categoricals and team marks render desaturated/muted — a small low-chroma dot or ring on neutral, never a saturated fill — and at most one non-lane accent carries real chroma per row. A dense row must never become a rainbow (5–6 saturated points) that drowns the model/market lanes.
- **Palette caveat:** the Sleeper position-hue *family* (QB pink/red, RB teal, WR blue, TE orange) is David's muscle memory and a high-confidence direction, but exact hexes must NOT enter the token spec without direct screenshot sampling (Codex cross-review gate). Position hues render as chips/badges/rings only.

## Typography (self-hosted @fontsource, latin subsets; no network fonts)

- Display: **Archivo** (`--dg-font-display`) — surface titles, the focal value number, band-divider labels.
- Body: **IBM Plex Sans** (`--dg-font-sans`).
- Data: **IBM Plex Mono** (`--dg-font-mono`), `font-variant-numeric: tabular-nums`, numerals right-aligned so columns compare digit-by-digit; consistent decimal precision per column. **Mono is for numeric values only** — non-numeric metadata (player names, position labels, team abbreviations, column headers) is Plex Sans. Monospacing text labels drags the surface back toward a terminal/diagnostics look (Gemini product-edge note).
- Fixed rem scale: `--dg-text-sm` 0.8125rem · `--dg-text-base` 0.9375rem · `--dg-text-lg` 1.125rem. The drama is weight-and-scale hierarchy — a big focal Archivo value against muted mono support columns — not color or chrome. `ValueHero` may take a larger display size than today; it is currently undersized versus the destination.

## Layout & the canonical row

- Cockpit grid: rail · trust strip · main · inspector drawer; 12-col / 8px baseline; spacing tokens `--dg-space-1..4` (0.25–1rem), paddings on a 4px grid (4/8/12). Wide content scrolls in its own container; the page never scrolls sideways. Two-pane "compare-then-inspect" is the desk signature.
- **Density: 32px data rows** (fantasy-native, not "too much"), 4–7 visible columns, depth behind tap/hover. The identity column freezes under horizontal scroll; the sparkline sits in the rightmost slot.
- **The row is a fixed grammar** (PRODUCT principle 2): `rank · position-rank chip · identity · ONE focal value · named-window trend · status/receipt chips`. Current value + delta travel together (`4,812 / +109 · +2.3%` — "+109 of what?" is never left unanswerable). No repeated per-row labels; the column header carries the label once and states the sort basis.
- **The Daily Open opens with a roster-level summary line** — the macro answer in manager prose before any rows ("Your roster overnight: model value +1.2%, market −0.4%" / "Quiet morning — no model changes, market held"). It answers "how did my roster do?" first; the individual rows are the drill-down beneath it.
- **First-viewport order is declared, not recency-driven.** On desktop and mobile the first viewport preserves the surface's declared order and lane symmetry; "top changed rows" is never a market-only recency lead, and system/trust/caveat plumbing is never the primary story (scaffolding-hide proportionality).
- **Layered caveats:** only high-priority blocking warnings (e.g., the ≥26h stale badge) render as active layout blocks in the primary viewport; minor disclaimers, model-basis notes, and diagnostics live in a collapsible caveats/provenance drawer or the inspector — the main viewport stays a clean fantasy narrative, never a status board.
- **Mobile is a first-class layout:** first screen = daily tape + roster summary + top changed rows (declared order); collapsed nav; a status pill replaces pinned panels; the inspector is a bottom sheet; two-line row cards; no horizontal overflow, no multi-thousand-px scroll.

## Components

Compose from `frontend/src/ui/` primitives — never rebuild locally: ReceiptTrigger, CaveatBlock, MetricCell, ValueHero, PlayerIdentity, SpreadBar, ValueBandDivider, GradedBar, DailyTape, DisclosureLine, SeriesSlot, ChartFrame. Radius vocabulary: 4px controls/blocks, 6px region containers, 3px chips. One focus grammar: 2px `--dg-focus` outline, offset 2. Every quiet/pending/failure state is a *designed* primitive state, never raw text.

## Motion (plain CSS, Carbon-derived tokens; no motion runtime)

- Tokens: `--dg-duration-fast-01/02` (70/110ms) · `moderate-01/02` (150/240ms) · `slow-01/02` (400/700ms) · `chart-stage` (1000ms); `--dg-ease-productive-standard/entrance/exit`.
- Two-tier policy: productive motion everywhere data-facing; expressive rationed to rare significant moments. Allowed: hover/focus feedback, receipt reveal, drawer, row settle, skeleton shimmer mirroring real layout, FLIP row-reorder for object constancy, a single non-looping settle that marks a row changed since the last capture (object-constancy cue only — reduced-motion-safe, no color shift, no size change, no confidence or urgency semantics; it says "new since your last visit," never "act on this"), staged (axes→marks→labels) chart updates over real data, and ONE orchestrated daily-open entrance (David-previewed) — narrowed: a data-state reveal tied to the changed rows, never decorative choreography; content is fully present and readable without the animation (never gated on it), productive timing, reduced-motion equivalent. This is the deliberate project-law exception to the impeccable product register's default "no orchestrated page-load sequence."
- Forbidden: pulsing/looping ambient motion in data regions, urgency shimmer, bounce/stretch, count-up on sort/filter (only on first hero reveal), drawing past the Hard Right Edge, motion implying confidence or action.
- Every motion class carries a `prefers-reduced-motion: reduce` override.

## Signature elements (spend boldness on these — visible, not reserved for honesty mechanisms)

Boldness goes to the elements that make the surface striking *and* legible: the **focal value number** as a real hero; **player identity** (faces, team-color marks); the **per-row uncertainty σ bar** with its printed number (a place DG *exceeds* the benchmark — fold CIs, not ranker disagreement); **inline sparklines** with an endpoint dot and printed current value, terminating at the **Hard Right Edge** (empty grid beyond); **tier/value-band dividers** with group total + league rank in the header (`QUARTERBACKS (5) — 10,140 (5/12)`); **hero moments** (player-highlight card, graded bars, Franchise Equity = roster value + owned valued picks + equity trend); and the **one daily-open entrance**. **A hero is never a system-nominated single player on a descriptive surface** — it is user-selected, David-supplied, aggregate, or lane-symmetric and non-actionable; a tool picking "the biggest mover" is the banned MoverHero pattern. Receipts, the daily tape, and the Hard Right Edge remain signatures too — but as designed elements, not the *only* place craft is allowed.

## Enforcement (best-in-class made testable, not vibes)

Three gates stand between an idea and a visual GREEN:

- **Shape before code (pre-build).** Before implementing any surface, produce a composition artifact: the 5-second answer (what the manager learns in five seconds), the focal hierarchy (what owns the eye), a desktop + mobile viewport sketch, and the lane-order statement. Composition is judged here — the scored audit must never be the first time it is judged.
- **Objective blockers (automated checks).** The scaffolding-hide law as a DOM/screenshot audit on user routes: fail on any visible raw schema token, snake_case key, database ID, ISO timestamp, or diagnostics/`Status:` plumbing outside approved receipt/drawer/dev surfaces. A viewport-first product test: the first screen is a fantasy/asset story, not system status. Receipt containment (provenance/health/raw IDs live behind approved primitives). Benchmark component grammar: AssetRow primitives present on rankings/daily-open surfaces. No naked diagnostics (SystemHealthCard, raw health labels) in primary content regions.
- **The unanchored scored audit (human/agent taste).** "Jaw-dropping" is gated by a mandatory independent fresh-agent visual audit: each of the seven rubric dimensions (first-viewport story, fantasy-native identity, information hierarchy, density, color discipline, mobile integrity, benchmark parity vs the Sleeper/DN/KTC bar) is scored 1–10. **Pass = two independent unanchored passes, each mean ≥ 8/10, no single dimension < 7, and zero P0/P1 findings.** The evidence bundle — desktop + mobile + mandatory mid-scroll captures + the scored rubric — is written to `docs/design-audits/YYYY-MM-DD-<surface>.md`. Fresh agents score; David ratifies the visual GREEN; any dimension below the floor blocks the ship. Not brittle aesthetic snapshots.

**Integrity guardrails (do not let aspiration break the frame):** aspiration words must not become verdicts; rich color must not weaken lane isolation or reintroduce verdict green/red; fantasy-native polish must not make unvalidated market data look decision-grade; hiding scaffolding must never hide caveats (translate to manager prose, never delete); the scored audit must stay unanchored and failure-seeking so it never rubber-stamps.


═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTION — The No-Verdict Line (the hard honesty rule)
═══════════════════════════════════════════════════════════════════════════════

### Descriptive Tools Issue No Verdicts (The No-Verdict Line)

A descriptive tool surfaces facts, ranges, ranks, and risks so David can decide. It must not decide for him.

This line governs running-software outputs — JSON payloads, API responses, stdout, written artifacts, and their caveats. It does not restrict design specs, roadmap plans, or strategy/PM briefs, which may discuss product-vision destinations (sell-timing, contrarian targets, transaction horizons) as where the product is headed — provided they never claim the current shipped model has already arrived.

Rulings:

- While a tool is classified as descriptive, every output carries `decision_supported=False` recursively — root and every nested model. A tool earns decision-grade status only through a pre-registered validation David ratifies; until then the no-verdict line holds.

- Descriptive is not directive. A descriptive tool may report quantities, explicit sort orders, counts, ranks, value-at-risk ranges, deficits, gaps, caveats, and structural states. It may not emit a normative verdict, recommendation, or imperative — no "buy/sell/hold", "keep/cut", "must"/"do not", "safe to", "recommended", or equivalent. Banned-language scans over running-software output and artifacts are a legitimate enforcement mechanism. Enforcement tests may scan source code, templates, fixtures, or generated-client surfaces when those are direct proxies for running-software output; that is enforcement of runtime safety, not a ban on strategy, spec, or roadmap language.

- Surface the arithmetic honestly, unclamped. Show gaps that cross zero (a cut that is a net upgrade reads negative), deficits as raw counts, and wide volatile ranges as wide ranges. Tightening, clamping, banding, or editorializing a number into a recommendation is the failure mode this line prevents. When inputs cannot be trusted — stale, missing, malformed, or low-coverage — report unavailable, block, or widen uncertainty; never fabricate a confident tidy number that reads as a verdict.

- Ranks and tiers must disclose their basis, never nudge. A default sort or rank must be tied to a declared transparent metric or rule, and any composite ordering must disclose its components and not function as a hidden recommended action order. Present raw percentile position; avoid subjective static tier labels ("Elite", "Bust", "Starter Depth") that smuggle a value judgment into a descriptive category.

- No nominated target by the back door. A tool may echo a David-supplied hypothesis (a proposed cut or trade) and display candidate rows — including player identifiers — under an explicit sort key. It may not select a player or action as the tool's own chosen target: a "next/marginal" cost is an index of the next increment in an existing order, not a recommendation, and carries no hidden "do this" payload.

Precedent: Roster Capacity Scenario Simulator v1 (PR #91), built end-to-end against this line. This consolidates and broadens the Frontend ("no decision-grade confidence before validation"), In-Season ("descriptive overlay, `decision_supported=False`"), and KTC ("overlay-only") rulings into a single decision-surface rule. [David-ratified 2026-06-28.]
