# Composition Package v2 — The Value Board (with the Market Margin as its edge)

> **Status:** pre-code composition artifact (shape-before-code gate, DESIGN.md §Enforcement). No production code. Supersedes v1 (`2026-07-08-margin-surfaces-composition.md`).
> **Date:** 2026-07-08 · **Author:** Claude (impeccable `shape`) · **Register:** product
> **Reviewed into existence by:** Codex + Gemini + two independent fresh agents (v1 scored 6/7 dimensions below floor; honesty + hierarchy below floor in both fresh reads). David ruled the reframe.
> **Uncommitted** pending David's word.

---

## 0. What changed from v1 (the reframe)

v1 made **the margin** the hero. Four independent reviewers converged: the margin is too **thin** (168 of 12,201 players have a signal; half of David's roster blank) and, as a standalone ranked-by-magnitude hero, kept **leaking verdicts** (intensity heat = "act here", `|margin|` sort = action order, editorial band copy). David's ruling:

- **The hero is a ranked VALUE BOARD** — *our* value for every player, in the fantasy-native unit (position rank). **The market margin is the killer *column*** on that board, present where coverage exists. The board stands on its own where the margin is blank.
- **The margin unit is paired positional rank** ("Model WR8 · Market WR24"), never raw percentile.
- **Three tabs** on one board engine: **My Roster · Other Teams · Full Universe** — Full Universe filterable by **Free Agents / Rostered** (the waiver/stash surface) and by position. Daily Open = the My-Roster daily entry.
- **Default sort:** roster/team scopes → **position-grouped (Sleeper-style)**; universe → **overall rank + position filters**.
- **No magnitude heat ramp, no editorial copy, no schema nouns on the surface, no scarcity caveat** (David's call, sole domain-expert user). No green/red ever.
- **Engine-A rookie join is prioritized** (parallel producer build) — the single unlock for the blank marquee players.

---

## 1. The real data this is grounded in (fresh-shape discipline)

Verified against live artifacts, not fixtures:

- **Our value = DVS 0–100.** Resolved for ~**469** players (per position: WR 167, TE 99, RB 90, QB 43). That ~469 *is* the fantasy-relevant universe — a real rankings board.
- **Market value = FantasyCalc** (0–~9000), with a native position rank per player.
- **The margin already exists**, computed honestly in percentile space (`universe_market_divergence.v1`): 168 real signals, 104 aligned, 11,929 uncomparable. `decision_supported=false` throughout.
- **The blank-hero truth:** 13 of David's 27 assets — **Ashton Jeanty, TreVeyon Henderson, Jaxson Dart, Luther Burden** — have **no DG value at all** (DVS null; young/rookie, active model can't read them, rookie engine not joined). This is why **Engine-A is the unlock**: it gives them a value → they appear on the board → and a margin wherever the market also has them.
- **STALENESS (must fix before preview):** the divergence artifact was captured **2026-06-23**. All margin numbers below are from that snapshot and are labeled honestly as such; the disposable comp and any preview must **recompute on fresh market + PVO**.

**Real paired positional ranks (David's roster, June-23 snapshot) — the encoding, on real data:**

| Player | Pos | Our rank | Market rank | Read |
|---|---|---|---|---|
| Kaelon Black | RB | **RB25** | RB61 | we rank +36 higher |
| Xavier Legette | WR | **WR70** | WR108 | we rank +38 higher |
| Garrett Wilson | WR | WR16 | WR14 | aligned |
| Tucker Kraft | TE | TE9 | TE5 | aligned |
| Rome Odunze | WR | WR58 | **WR25** | market +33 higher |
| Parker Washington | WR | WR93 | **WR36** | market +57 higher |
| AJ Barner | TE | TE51 | **TE20** | market +31 higher |
| Ashton Jeanty | RB | **—** | RB3 | market top-3; our read forming |
| Jaxson Dart | QB | **—** | QB10 | market QB10; our read forming |

Sign convention: **+ = our model ranks the player higher than the market does; − = the market ranks him higher; aligned = within a band.** Neutral. Never "buy/sell."

---

## 2. The shared Value Row grammar (both surfaces compose from this)

Extends DESIGN.md's canonical AssetRow. **The focal value is OUR value/rank; the margin is a distinct column, not the hero.**

```
rank · pos-chip · IDENTITY (headshot + name + team-ring) · OUR VALUE (focal) · MARGIN col · trend(small) · receipt
```

- **Focal value = our value, rendered as position rank** (Archivo, 2–3× weight, right-aligned tabular): "WR16". Raw DVS + a 0–100 index live in the receipt. On the universe/overall scope the focal is overall rank; within a position group it's position rank.
- **Margin column (the edge)** = paired positional rank + a signed spot-delta: `Model WR70 · Market WR108 · +38`. A **slim two-mark bar** visualizes it — one **model-blue** mark, one **market-amber** mark on a shared position-rank axis; **the gap length carries magnitude** (no intensity/saturation ramp, no hue-heat). Direction is read from which mark leads + the signed number. Where a lane is missing, the margin cell shows a designed **"forming a read"** state, never a fake 0.
- **Direction is stated once, not thrice** (v1 bug): the bar + signed number carry it; no redundant "Model higher" chip (a small glyph at most).
- **Receipts** (focusable, beside the row): raw DVS, 0–100 index, raw market value + rank, source + as-of date, and — in **manager prose, never schema nouns** — "a descriptive disagreement, not a recommendation."

**Row coverage states** (all first-class, all designed):
1. **Both lanes** → value rank + margin bar.
2. **Aligned** → margin marks nearly overlap; quiet "aligned" glyph, no magnitude drama.
3. **Our value, no market** → value rank + "market hasn't priced him" (appears once Engine-A joins deep rookies).
4. **Market only, our read forming** → identity + market rank + draft capital + age + "our read is still forming (rookie value not joined yet)". A *fantasy* state, not a blank.

---

## 3. SURFACE 1 — The Value Board (the hero)

### 5-second answer
> "Here's where **we** rank every player — and, next to it, where the market ranks him and by how much we disagree."

### Focal hierarchy
1. **Player identity** (headshot + name + team ring) — recognition is the strongest pull; it leads.
2. **Our value** as position rank — the focal number.
3. **The margin column** (paired rank + signed spots + slim bar) — the edge, second read.
4. Trend (small), receipts — quiet / drawer.
5. Coverage/health — a quiet persistent scope label, never the headline.

### Lane-order statement
Our model (blue) is the product's voice and owns the **value** (the focal). Market (amber) appears **only** in the margin column, as an overlay — equal visual weight *within that column*, never blended into the value read. Position/identity hues are orthogonal, desaturated. No verdict hue anywhere.

### Layout & scope
One board engine, three durable **tabs** (top-left):
- **My Roster** — your team, **position-grouped** (Sleeper-style): `QUARTERBACKS (n) · RUNNING BACKS (n) · …`, each group ranked by our value; band dividers carry the group's count + our-value total.
- **Other Teams** — browse each league-mate's roster (team picker), same position-grouped grammar + margin column. This is the trade-target lens: where our model and the market disagree on the players *another manager* holds.
- **Full Universe** — **overall rank** (1..~469 by our value) with **position filters** (All · QB · RB · WR · TE), sorts (our value / |margin| / market rank), and a **Free Agents / Rostered** filter. Free Agents is the waiver/stash surface — real today: 196 free agents carry a DG value, 46 where our model ranks above the market (descriptive only — never "pick up"; and note these skew to aging vets, the model's known age blind spot).
- **Coverage is honest but demoted:** a quiet persistent chip ("469 ranked · margin on 272"), never a diagnostic headline. Uncomparable players are reachable by filter, not a rainbow of empty cells.
- **A persistent one-line honesty header** sits on the board (not a tucked drawer): "Descriptive — our model's ranking vs the market's. Not validated as more accurate yet."

### Desktop sketch — universe scope, overall rank (~1440px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ THE VALUE BOARD        [ My Roster · Other Teams · Full Universe ]      ⌂ ⚙   │
│ Descriptive — our ranking vs the market's. Not yet validated as more accurate. │
│ 469 ranked · margin on 272   [Free Agents · Rostered]  pos: All ▾   fresh 6:12 │
├────┬──────────────────────────┬────────────┬───────────────────────────┬──────┤
│ #  │ PLAYER                   │ OUR VALUE  │ MARKET MARGIN             │ trend│
├────┼──────────────────────────┼────────────┼───────────────────────────┼──────┤
│  1 │ ◍ Player A       WR·xxx  │  WR1       │ Model WR1 ●◉ WR1 · aligned│  ▸   │
│  9 │ ◍ Garrett Wilson NYJ·WR  │  WR16      │ M●WR16 ─ WR14○K · +2 mkt  │  ▸   │
│ 24 │ ◍ Rome Odunze    CHI·WR  │  WR58      │ M●WR58 ──── WR25○K · −33  │  ▸   │
│ 31 │ ◍ Xavier Legette CAR·WR  │  WR70      │ M●WR70 ──── WR108○K · +38 │  ▸   │
│ …  │ ◍ Ashton Jeanty  LV·RB   │  forming   │ market RB3 · our read      │  —   │
│    │                          │            │ forming (rookie value      │      │
│    │                          │            │ not joined yet)            │      │
├────┴──────────────────────────┴────────────┴───────────────────────────┴──────┤
│  M ● = our rank (blue)   K ○ = market rank (amber)   gap = disagreement size   │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Desktop sketch — roster scope, position-grouped (real data)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MY ROSTER — Woodbury Riders   [ position-grouped ]              fresh 6:12 AM  │
│ QUARTERBACKS (5)                                                               │
│  ◍ Fernando Mendoza LV   QB10   M●QB10 ─ QB14○K · +4      ▸                     │
│  ◍ Mac Jones        SF   QB35   M●QB35 ─ QB42○K · +7      ▸                     │
│  ◍ Jaxson Dart      NYG  forming   market QB10 · our read forming             │
│  ◍ J.J. McCarthy    MIN  forming   market QB31 · our read forming             │
│ RUNNING BACKS (5)                                                             │
│  ◍ Kaelon Black     SF   RB25   M●RB25 ──── RB61○K · +36  ▸                     │
│  ◍ Braelon Allen    NYJ  RB42   M●RB42 ── RB57○K · +15    ▸                     │
│  ◍ Ashton Jeanty    LV   forming   market RB3 · our read forming             │
│  ◍ TreVeyon Henderson NE forming   market RB15 · our read forming            │
│ WIDE RECEIVERS (…)  TIGHT ENDS (…)                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mobile sketch (~390px, two-line row)
```
┌───────────────────────────┐
│ VALUE BOARD  [Roster ▾]   │
│ 469 ranked · fresh 6:12   │
│ RUNNING BACKS (5)         │
│ ◍ Kaelon Black  SF·RB     │
│   our RB25        +36 ▸   │
│   M●RB25 ──── RB61○K       │
│ ◍ Ashton Jeanty LV·RB     │
│   forming    market RB3 ▸ │
│   read forming (rookie)   │
└───────────────────────────┘
 line1: identity + our rank + signed margin
 line2: the paired-rank bar (or the pending reason)
```

---

## 4. SURFACE 2 — The Daily Open (roster scope + a quiet league preview)

### 5-second answer
> "My roster, ranked by our value and grouped by position — where we and the market disagree, plus a quiet note of anything that moved in my league overnight."

### Focal hierarchy
1. **My roster, position-grouped** — the Value Board at roster scope (identical grammar).
2. **The margin column** on each covered player.
3. **A quiet league-relevant margin-movement preview** — "the market moved on N players you could target/trade; model held." Secondary, small, market-driven (our anchor is stable, so this is the only honest "daily" element).
4. **Freshness whisper** (ambient) — "captured 6:12 AM," zero-attention when healthy.
5. **Degraded banner** (exception only) — loud, dashes the affected lane, only on real failure.

### Lane-order statement
Identical to the board: our value leads (blue focal), market appears only in the margin column (amber overlay), equal weight within that column, orthogonal identity hues.

### Key states
- **Default:** roster summary line ("Your roster: we rank higher on 3, market higher on 7, aligned on 4, 13 reads forming") → position groups with margin column → league-movement preview → freshness whisper.
- **Quiet day:** league preview collapses to "Nothing moved in your league overnight; model held." Designed, not empty — the rankings are still the point.
- **Stale/failed market capture:** loud banner; market column dashes (`—`); never last-known-as-fresh.
- **Read forming:** first-class market-context row (never a text bin).

### Mobile: two-line rows, position groups collapsible, league preview as a bottom card, inspector = bottom sheet.

---

## 5. Interaction & motion
- **Row → receipts:** tap/click → inspector (desktop drawer / mobile bottom-sheet): raw DVS, 0–100 index, raw market value + rank, source + as-of, and the "descriptive disagreement, not a recommendation" line. Keyboard-first, focusable, Esc closes.
- **Scope/filter/sort:** instant, FLIP row-reorder for object constancy; no count-up on re-sort.
- **Motion:** productive only (150–240ms); the paired-rank marks settle on load (reduced-motion-safe); no urgency, no magnitude "pulse", nothing drawn past the Hard Right Edge on any spark. Motion never implies confidence or action.

## 6. Copy — manager prose, translation table (no schema nouns on the surface)
| Never show | Show instead |
|---|---|
| `decision_supported=false` | "A descriptive disagreement, not a recommendation." |
| "failed-gate reason" / UNAVAILABLE | "Our read is still forming" / "Why no read yet" |
| "active model" / "model_status" | "NFL-usage model" |
| "MODEL HIGHER THAN MARKET (109)" + "we rate above the crowd" | "Model rank above market (109)" — count only, no gloss |
| "market pays a premium we don't" | "Market rank above model (59)" |
| `universe_market_divergence` / "producer join" / "Phase 17.4" | (never surfaced — internal only) |
Banned on the surface everywhere: buy/sell/hold/start/sit, under/over-priced, edge/target/value-window/arbitrage, recommended/priority/act, "crowd", tool-nominated "player of the day".

## 7. States & edge-case matrix (RED seeds — the fuller set Codex flagged)
our-value-only · market-only (read forming) · both · aligned/±0 (render "aligned", never visible −0.0) · unresolved identity · stale divergence artifact · stale PVO · empty roster · all-reads-forming roster · malformed/out-of-range rank or percentile · signal/percentile mismatch · duplicate identity or rank · position with <N ranked (thin position) · market rank present but no position (fallback) · league-scope player on multiple rosters · deterministic tie ordering (canonical id).

## 8. New / extended primitive work (Codex correction — not "existing support")
- **PairedRankBar** — NEW: two marks (blue model, amber market) on one shared position-rank axis, gap = magnitude, no intensity fill. (SpreadBar today renders a *single* dot on one lane — this is an extension or a new primitive.)
- **ValueRow** — extend the local Daily-What-Changed AssetRow into a shared primitive with a focal value-rank + margin column + the four coverage states.
- **ScopeSwitcher** (My Roster / League Rosters / Universe), **PositionGroup** divider with counts/totals, **FormingReadCell** (market-context pending). DailyTape stays capture/provenance only.

## 9. Parallel track (the unlock) — Engine-A rookie join
Its own framing → RED → GREEN producer build: join rookie-engine (Engine A) values into the valuation/divergence surface so young players (Jeanty, Henderson, Dart, Burden) get a DG value → a board rank → and a margin wherever the market has them. Design note: Engine A is capital+age prior (settled fork); its values ship with their own experimental grade and the same `decision_supported=false`. This does not gate the v2 composition, but it is the highest-leverage next build for the surface to stop being blank where David cares most.

## 10. Open decisions (defaulted where possible)
1. **RESOLVED (David 2026-07-08):** three tabs — My Roster · Other Teams (browse each league-mate's roster) · Full Universe (with a Free Agents / Rostered filter + position filters). Data-supported: `league_context.rostered` + `roster_id`/`owner`.
2. **Overall-rank population for the universe scope** — rank the ~469 resolved players by our value; the paired-rank margin's denominators differ slightly (our ~469-pop rank vs market's full-FC rank) — disclosed in receipts. *Default: per-source native position rank, basis disclosed.* Acceptable, or normalize to a shared population?
3. **Fresh-data recompute** — the comp + any preview recompute divergence on current market+PVO (the June-23 artifact is stale). Assumed.

---
*Composition v2. Next: cockpit adversarial re-review → recompute fresh margin data → disposable real-content static comp (hand-joined) → David's directional preview. Engine-A join spec runs in parallel. No production code until cleared and David authorizes.*
