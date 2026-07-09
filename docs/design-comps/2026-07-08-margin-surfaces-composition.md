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
