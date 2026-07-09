# Composition Package v3.2 — The Value Board (our value, with the Market Margin as its edge)

> **Status:** pre-code composition artifact (shape-before-code gate, DESIGN.md §Enforcement). No production code. Supersedes v2 (`2026-07-08-value-board-composition-v2.md`).
> **Date:** 2026-07-08 · **Author:** Claude (impeccable `shape`) · **Register:** product
> **Regrounded on:** the **fresh 2026-07-08 divergence artifact** (David-authorized one-time rebuild; `universe_market_divergence_latest.json`, captured 2026-07-08T19:43Z). v2's numbers came from a **stale June-23 snapshot** — Codex caught it. Every figure below is verified against the live artifact.
> **v3.1 (cockpit re-review corrections):** Codex + Gemini independently converged on a real source-of-truth defect in v3 — it led with **DVS** as the focal "our value" while the margin is computed from **xVAR** percentiles (`universe_market_divergence.py:191–193`), so the headline rank and the margin direction could contradict each other. Fix: **pin the board to xVAR** (the same basis the margin uses) — which *also* resolves the §10 TE-wall (xVAR is the cross-position transform: FA-by-xVAR is a natural WR7/RB4/TE3/QB1 mix vs 13/15 TEs by DVS). Margin now renders in **percentile space** (native ranks are labels only, no misleading cross-denominator spot-delta), and ranks carry a **confidence/tier** frame (Gemini: pinpoint ranks overclaim precision). §§1,2,3,7,10 updated below.
> **v3.2 tier-calibration correction (David 2026-07-08):** fixed percentile tier labels are NOT an acceptable primary basis. "Elite" must reflect relative model value, production, age/longevity context, and historical field separation — not an arbitrary `top X%` cut. Until a tier-calibration artifact exists, the Value Board may show neutral rank spans / provisional value cohorts, but named labels (Generational / Elite / Cornerstone / Starter / Depth) are suppressed.
> **Uncommitted** pending David's word.

---

## 0. What changed from v2 — and why it matters

v2 was structurally right (ranked Value Board hero, market margin as a column, paired positional rank, three tabs) but its **content was grounded on a stale June-23 artifact**, and that stale data told a false story. The fresh rebuild inverts three things:

1. **The board is 332 players, not 469.** Fresh population: **WR 138 · RB 89 · TE 61 · QB 44**. (183 gates-passed signals + 149 aligned = 332 with both lanes; 11,869 uncomparable; 12,201 total.)
2. **"Engine-A is the unlock" is dead.** v2 said David's marquee rookies (Jeanty, Henderson, Dart, Burden) were **blank** and Engine-A was the single unlock. **They are all valued now.** David is **24 of 27 on-board** (only Braelon Allen, Garrett Wilson, Tank Dell are off-board — availability/identity, not rookie-blindness). Engine-A is **demoted** from "the unlock" to a normal backlog item.
3. **The real divergence story is inverted — and it's the honest one.** The market ranks David's young studs **higher** than our model does (Jeanty market RB3 / our RB18; Dart market QB10 / our QB16; Henderson market RB15 / our RB27 — all **MODEL_LOW_MARKET_HIGH**). Meanwhile our model's biggest "we-see-more" calls are **proven veterans** — Jonnu Smith, Darren Waller, Keenan Allen (aging TEs/WRs, **MODEL_HIGH_MARKET_LOW**). This is a *humbling* pattern (is our model just an age-agnostic production scorer the market has already corrected for?) — exactly the counter-argument-first, `decision_supported=false` posture the constitution demands. **We show it honestly; we do not spin it as an edge.**

Also folded from cockpit re-review: header renamed **"DG Model Rank" / "vs Market Rank"** (kills the "our value is authoritative" overclaim); **FA sorts by our value** (David's ruling); Full Universe **defaults to the ranked board + a "Show uncomparable" toggle**; **all "target/trade" copy removed** (my own v2 leak Codex flagged); denominator basis disclosed in receipts, not as a surface footnote.

**A finding that surfaced and was then resolved in re-review (see §10):** sorting free agents by *raw DVS* surfaced a **wall of tight ends** (13 of the top 15). In v3 I flagged this for David's decision as the deferred PVO-normalization project. The cockpit re-review closed it: **xVAR is already the cross-position transform**, so pinning the board to xVAR (v3.1) yields a natural WR7/RB4/TE3/QB1 mix and needs no normalization project. Only a cosmetic market-comparable 0–2000 rescale remains deferred — no David decision required to ship an honest sort.

---

## 1. The real data this is grounded in (fresh, 2026-07-08)

Verified against the live artifact, not fixtures:

- **Our value = xVAR** (expected value above replacement, Engine B) — the **same quantity the margin is computed from** (the divergence ranks players by within-position xVAR percentile, `universe_market_divergence.py:191`). Rendered as a within-position percentile rank. **DVS 0–100** (Dynasty Value Score) is a related composite that lives in the **receipt**, not the focal rank — leading with it while the margin uses xVAR is the contradiction v3.1 fixes. Resolved for **332** players — the fantasy-relevant board.
- **Market value = FantasyCalc** (Superflex 2QB / 12-team / PPR / dynasty), captured same-day, with a native position rank per player.
- **The margin is computed honestly in percentile space** (`universe_market_divergence.v1`): 183 gates-passed signals (**137 MODEL_HIGH_MARKET_LOW · 46 MODEL_LOW_MARKET_HIGH**), 149 aligned, 11,869 uncomparable. `decision_supported=false` throughout. Zero banned-language present; zero `decision_supported=true`.
- **David (Woodbury Riders, roster 1) — 24 of 27 on-board**, the most-covered roster in the league. Summary: **we rank higher on 9 · market higher on 7 · aligned on 8 · 3 reads forming** (Braelon Allen, Garrett Wilson, Tank Dell — availability/identity).

**Real paired positional ranks — David's roster, fresh 2026-07-08 (the encoding, on real data):**

| Player | Pos | DG Model Rank | vs Market Rank | Read |
|---|---|---|---|---|
| Kaelon Black | RB | **RB30** | RB65 | we rank ~35 higher |
| Theo Johnson | TE | **TE23** | TE37 | we rank ~14 higher |
| Xavier Legette | WR | **WR87** | WR105 | we rank ~18 higher |
| Tucker Kraft | TE | TE11 | TE5 | aligned |
| Rome Odunze | WR | WR38 | **WR26** | market ~12 higher |
| TreVeyon Henderson | RB | RB27 | **RB15** | market ~12 higher |
| Jaxson Dart | QB | QB16 | **QB10** | market ~6 higher |
| Ashton Jeanty | RB | RB18 | **RB3** | market ~15 higher |

Sign convention: **+ = our model ranks the player higher than the market; − = the market ranks him higher; aligned = within the noise band.** Neutral. Never "buy/sell." (Rank magnitude is directional; sort/magnitude is driven by the underlying percentile delta — the ranks' denominators differ by source, §2.)

**The universe extremes (Full Universe content, fresh):**
- **Biggest "we see more" (MODEL_HIGH_MARKET_LOW):** Jonnu Smith (TE), Darren Waller (TE, FA), Keenan Allen (WR, FA), Cole Kmet (TE, FA). *Pattern: proven veterans / TEs.* Counter-argument surfaced in the receipt: our model reads production, not dynasty longevity — this is the known age blind spot, stated, not hidden.
- **Biggest "market pays more" (MODEL_LOW_MARKET_HIGH):** Joe Burrow (QB), rookie QBs (Carson Beck, Michael Penix Jr., Shedeur Sanders), rookie RBs (Tank Bigsby, Nicholas Singleton). *Pattern: the Superflex youth/upside premium.*

---

## 2. The shared Value Row grammar (both surfaces compose from this)

Extends DESIGN.md's canonical AssetRow. **The focal value is OUR value/rank; the margin is a distinct column, not the hero.**

```
rank · pos-chip · IDENTITY (headshot + name + team-ring) · DG MODEL RANK (focal) · vs MARKET RANK col · trend(small) · receipt
```

- **Focal value = our value (xVAR), rendered as position rank** (Archivo, 2–3× weight, right-aligned tabular): "WR38" — the within-position xVAR percentile rank, the *same basis the margin uses*. DVS + the raw xVAR + the 0–100 index live in the receipt. Universe/overall scope → focal is overall rank (by xVAR, the cross-position transform); within a position group → position rank. **Ranks are point estimates, not pinpoint truth** — the row treats a rank as the center of a value cohort, and the receipt discloses the confidence band. **Important v3.2 correction:** the named lexicon (Generational / Elite / Cornerstone / Starter / Depth) may not bind to fixed percentile cuts. It is gated on a `tier_calibration` artifact (§11) that derives cohort boundaries from unclamped model value plus historical outcome separation. Until that exists, render neutral math-first spans such as "Top cohort · WR1–7" or "Value band · RB18–31"; do not render "Elite" or "Cornerstone" in production.
- **Margin column ("vs Market Rank")** — the honest comparable quantity is the **percentile gap**, not a raw spot-delta. A **slim two-mark bar** plots the two *percentiles* on a shared 0–100 axis — one **model-blue** mark (our xVAR percentile), one **market-amber** mark (market percentile); **the gap length carries magnitude** (no intensity/saturation ramp, no hue-heat, no green/red). The paired native ranks (`DG WR87 · Market WR105`) are shown as **familiar labels** beside the bar, but the direction/magnitude/sort come from the percentile delta — never a cross-denominator spot subtraction presented as a headline "+18". Missing lane → a designed **"forming a read"** state, never a fake 0.
- **Cohort rail background (David line-graph correction):** the paired-rank rail should also show where the player sits inside the position's calibrated model-value field. The background may be divided into neutral shaded cohort spans, but those spans come from the tier-calibration artifact, not arbitrary percentiles. Example shape: if the calibrated RB top cohort is RB1–RB6 this run, the rightmost rail segment spans exactly RB1–RB6; if the next run's historical/current distribution supports RB1–RB11, the segment changes. The rail still carries no verdict hue; model/market marks remain blue/amber.
- **Denominator honesty (Codex #3 + Gemini risk 2):** our rank is within the 332-player board; the market rank is FantasyCalc's native rank over its full universe — the two denominators differ, so a raw spot-delta between them is *distorted* (e.g. DG WR87-of-138 is bottom-tier while Market WR105-of-~500 is mid-tier — the market actually values him higher, though a naive "+18" reads the opposite). The receipt shows the derivation explicitly — **"Model 63rd pct · Market 79th pct"** — so the sign is never misread. The percentile delta is the single source of magnitude + sort.
- **Direction stated once, not thrice** (v1 bug): the bar + signed number carry it; no redundant "Model higher" chip.
- **Receipts** (focusable, beside the row): raw DVS, 0–100 index, raw market value + rank, source + as-of date, the denominator basis, and — in **manager prose, never schema nouns** — "a descriptive disagreement, not a recommendation."

**Row coverage states** (all first-class, all designed):
1. **Both lanes** → value rank + margin bar.
2. **Aligned** → margin marks nearly overlap; quiet "aligned" glyph, no magnitude drama.
3. **Our value, no market** → value rank + "market hasn't priced him."
4. **Market only, our read forming** → identity + market rank + draft capital + age + "our read is still forming." A *fantasy* state, not a blank.

---

## 3. SURFACE 1 — The Value Board (the hero)

### 5-second answer
> "Here's where **we** rank every player — and, next to it, where the market ranks him and by how much we disagree."

### Focal hierarchy
1. **Player identity** (headshot + name + team ring) — recognition is the strongest pull; it leads.
2. **Our value (xVAR)** as position rank (the "DG Model Rank") — the focal number, same basis as the margin.
3. **The margin column** ("vs Market Rank": percentile-gap bar with native ranks as labels) — the edge, second read.
4. Trend (small), receipts — quiet / drawer.
5. Coverage/health — a quiet persistent scope label, never the headline.

### Lane-order statement
Our model (blue) is the product's voice and owns the **value** (the focal). Market (amber) appears **only** in the margin column, as an overlay — equal visual weight *within that column*, never blended into the value read. Position/identity hues are orthogonal, desaturated. No verdict hue anywhere.

### Layout & scope
One board engine, three durable **tabs** (top-left):
- **My Roster** — your team, **position-grouped** (Sleeper-style): `QUARTERBACKS (n) · RUNNING BACKS (n) · …`, each group ranked by our value; band dividers carry the group's count.
- **Other Teams** — browse each league-mate's roster (team picker), same position-grouped grammar + margin column. Descriptive lens on where our model and the market disagree about the players *another manager* holds. (No "trade target" language — the disagreement is the content; the manager decides.)
- **Full Universe** — **overall rank by our value (xVAR)** (1..332) with **position filters** (All · QB · RB · WR · TE), a **Free Agents / Rostered** filter, and a **"Show uncomparable"** toggle (default off — the 11,869 no-signal players are reachable, never a rainbow of empty cells). Free Agents sorts by **our value (xVAR)**, highest first. Real today: **89 free agents carry a value** on the board; the xVAR sort yields a natural WR/RB/TE/QB mix (Keenan Allen, Kareem Hunt, Marvin Mims on top), not the TE-wall a raw-DVS sort produced. *(See §10 — xVAR is the honest cross-position basis; the 0–2000 rescale is a separate deferred producer project.)*
- **Coverage is honest but demoted:** a quiet persistent chip ("332 ranked · margin on 183"), never a diagnostic headline.
- **A persistent one-line honesty header:** "Descriptive — our model's ranking vs the market's. Not validated as more accurate yet."

### Desktop sketch — universe scope, overall rank (~1440px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ THE VALUE BOARD        [ My Roster · Other Teams · Full Universe ]      ⌂ ⚙   │
│ Descriptive — our ranking vs the market's. Not yet validated as more accurate. │
│ 332 ranked · margin on 183   [Free Agents · Rostered]  pos: All ▾   fresh 2:43 │
├────┬──────────────────────────┬────────────┬───────────────────────────┬──────┤
│ #  │ PLAYER                   │ DG MODEL   │ vs MARKET RANK            │ trend│
├────┼──────────────────────────┼────────────┼───────────────────────────┼──────┤
│  1 │ ◍ Player A       WR·xxx  │  WR1       │ DG WR1 ●◉ WR1 · aligned   │  ▸   │
│ 12 │ ◍ Tucker Kraft   GB·TE   │  TE11      │ DG●TE11 ─ TE5○K · −6 mkt  │  ▸   │
│ 40 │ ◍ Rome Odunze    CHI·WR  │  WR38      │ DG●WR38 ── WR26○K · −12   │  ▸   │
│ 58 │ ◍ Xavier Legette CAR·WR  │  WR87      │ DG●WR87 ──── WR105○K · +18│  ▸   │
│ …  │ ◍ Braelon Allen  NYJ·RB  │  forming   │ market read forming        │  —   │
├────┴──────────────────────────┴────────────┴───────────────────────────┴──────┤
│  DG ● = our rank (blue)   K ○ = market rank (amber)   gap = disagreement size  │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Desktop sketch — roster scope, position-grouped (real 2026-07-08 data)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MY ROSTER — Woodbury Riders   [ position-grouped ]              fresh 2:43 PM  │
│ we rank higher on 9 · market higher on 7 · aligned on 8 · 3 reads forming      │
│ QUARTERBACKS (4)                                                              │
│  ◍ Jaxson Dart      NYG  QB16   DG●QB16 ── QB10○K · −6 mkt   ▸                  │
│  ◍ Fernando Mendoza  ?   QB20   DG●QB20 ── QB15○K · −5 mkt   ▸                  │
│  ◍ J.J. McCarthy    MIN  QB30   DG●QB30 ●◉ QB30○K · aligned  ▸                  │
│  ◍ Mac Jones        SF   QB32   DG●QB32 ─ QB38○K · +6        ▸                  │
│ RUNNING BACKS (5)                                                             │
│  ◍ Ashton Jeanty    LV   RB18   DG●RB18 ──── RB3○K · −15 mkt ▸                  │
│  ◍ TreVeyon Henderson NE RB27   DG●RB27 ── RB15○K · −12 mkt  ▸                  │
│  ◍ Kaelon Black     SF   RB30   DG●RB30 ────── RB65○K · +35  ▸                  │
│  ◍ Rasheen Ali      BAL  RB82   DG●RB82 ──── RB112○K · +30   ▸                  │
│  ◍ Braelon Allen    NYJ  forming   read forming (off-board)                    │
│ WIDE RECEIVERS (…)  TIGHT ENDS (…)                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mobile sketch (~390px, two-line row)
```
┌───────────────────────────┐
│ VALUE BOARD  [Roster ▾]   │
│ 332 ranked · fresh 2:43   │
│ RUNNING BACKS (5)         │
│ ◍ Ashton Jeanty LV·RB     │
│   our RB18     −15 mkt ▸  │
│   DG●RB18 ──── RB3○K       │
│ ◍ Kaelon Black  SF·RB     │
│   our RB30      +35 ▸     │
│   DG●RB30 ────── RB65○K    │
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
3. **A quiet league-relevant margin-movement preview** — "the market moved on N players in your league overnight; our model held." Secondary, small, market-driven (our anchor is stable, so this is the only honest "daily" element). **No "target/trade" verb** — it reports movement, it does not prescribe action.
4. **Freshness whisper** (ambient) — "captured 2:43 PM," zero-attention when healthy.
5. **Degraded banner** (exception only) — loud, dashes the affected lane, only on real failure. (David's ruling: trust the system to produce real data; warn *only* on failure.)

### Lane-order statement
Identical to the board: our value leads (blue focal), market appears only in the margin column (amber overlay), equal weight within that column, orthogonal identity hues.

### Key states
- **Default:** roster summary line ("we rank higher on 9 · market higher on 7 · aligned on 8 · 3 reads forming") → position groups with margin column → league-movement preview → freshness whisper.
- **Quiet day:** league preview collapses to "Nothing moved in your league overnight; our model held." Designed, not empty — the rankings are still the point.
- **Stale/failed market capture:** loud banner; market column dashes (`—`); never last-known-as-fresh.
- **Read forming:** first-class market-context row (never a text bin).

### Mobile: two-line rows, position groups collapsible, league preview as a bottom card, inspector = bottom sheet.

---

## 5. Interaction & motion
- **Row → receipts:** tap/click → inspector (desktop drawer / mobile bottom-sheet): raw DVS, 0–100 index, raw market value + rank, source + as-of, denominator basis, and the "descriptive disagreement, not a recommendation" line. Keyboard-first, focusable, Esc closes.
- **Scope/filter/sort:** instant, FLIP row-reorder for object constancy; no count-up on re-sort.
- **Motion:** productive only (150–240ms); the paired-rank marks settle on load (reduced-motion-safe); no urgency, no magnitude "pulse," nothing drawn past the Hard Right Edge on any spark. Motion never implies confidence or action.

## 6. Copy — manager prose, translation table (no schema nouns on the surface)
| Never show | Show instead |
|---|---|
| `decision_supported=false` | "A descriptive disagreement, not a recommendation." |
| "failed-gate reason" / UNAVAILABLE | "Our read is still forming" / "Why no read yet" |
| "active model" / "model_status" | "NFL-usage model" |
| "MODEL HIGHER THAN MARKET (137)" + "we rate above the crowd" | "Model rank above market (137)" — count only, no gloss |
| "market pays a premium we don't" | "Market rank above model (46)" |
| `universe_market_divergence` / "producer join" / "Phase 17.4" | (never surfaced — internal only) |
| any "target / trade / add / drop" verb (incl. my own v2 leak) | state the disagreement; the manager acts |

Banned on the surface everywhere: buy/sell/hold/start/sit, under/over-priced, edge/target/value-window/arbitrage, recommended/priority/act, "crowd," tool-nominated "player of the day."

## 7. States & edge-case matrix (RED seeds)
our-value-only · market-only (read forming) · both · aligned/±0 (render "aligned," never visible −0.0) · unresolved identity · stale divergence artifact · stale market cache · stale PVO · empty roster · all-reads-forming roster · malformed/out-of-range rank or percentile · signal/percentile mismatch · duplicate identity or rank · position with <N ranked (thin position) · market rank present but no position (fallback) · league-scope player on multiple rosters · deterministic tie ordering (canonical id).

**Read-path seeds Codex added in v3.1 re-review (these are the ones that keep the surface honest):**
- **Rank-basis consistency** — the API must pin ONE model basis: the focal "our value" rank and the margin percentile are both **xVAR**; DVS is never a sort/rank basis (else contradictory signs — a QB reads market-higher by percentile while DVS text implies model-higher).
- **Raw spot-delta forbidden** unless a shared-population rank exists — the bar renders **percentile positions**, and any displayed spot-count is a label, never subtracted across mismatched denominators.
- **Phase-0 marker missing/stale degrades the READ path** — when the daily-recompute status marker is absent or stale, the board shows a degraded/freshness state, never last-known-as-fresh.
- **Show-uncomparable at scale** — virtualization/pagination for the 11,869 no-signal rows (never render all at once).
- **Missing `league_context.rostered`/`roster_id`/`owner`** — scope tabs degrade gracefully.
- **No visible schema nouns / action words in receipts**; keyboard/focus receipt tests (the inspector is keyboard-first).

**Tier-calibration RED seeds added after David's v3.2 correction:**
- **No fixed-percentile primary rule** — a test fails if "Elite", "Generational", "Starter", "Depth", or any shaded cohort span is assigned from a static percentile ladder (`>=99`, `95-99`, etc.) without the tier-calibration artifact.
- **No market-as-input** — market rank/value may appear on the margin lane, but never influences DG cohort boundaries.
- **No clamped top-end basis** — a test fails if named labels or top-cohort breaks are derived from public clamped DVS/xVAR when an unclamped latent value exists; current data shows RB/WR/TE top-end plateaus under the public fields.
- **Historical support required for named labels** — named labels render only when the artifact carries sufficient historical outcome support for that cohort; otherwise the UI renders neutral rank/value spans.
- **Boundary honesty** — players near a cohort break render a boundary/uncertainty marker instead of snapping confidently into a named tier.
- **Stale/low-coverage degradation** — stale calibration, low historical sample, or missing latent-value support suppresses named labels before it suppresses numeric rank/value.

## 8. New / extended primitive work
- **PairedRankBar** — NEW: two marks (blue model, amber market) on one shared position-rank axis, gap = magnitude, no intensity fill. (SpreadBar today renders a *single* dot on one lane — this is an extension or a new primitive.)
- **ValueRow** — extend the local Daily-What-Changed AssetRow into a shared primitive with a focal value-rank + margin column + the four coverage states.
- **ScopeSwitcher** (My Roster / Other Teams / Full Universe), **PositionGroup** divider with counts, **FormingReadCell** (market-context pending). DailyTape stays capture/provenance only.

## 9. Model character — the honest finding (replaces v2's "Engine-A unlock")
The fresh data retires v2's premise. The interesting, honest pattern is now the **shape of the disagreement**:
- Our model's biggest "we-see-more" calls cluster on **proven veterans and TEs** (Jonnu Smith, Waller, Keenan Allen). The market's biggest premiums cluster on **young QBs/RBs** (Burrow, rookie QBs, rookie RBs) — the Superflex youth premium.
- **Counter-argument (mandatory, per the constitution):** this could mean our model is a **production scorer that under-weights dynasty longevity/age** — i.e., the market may already be *correct* to pay the youth premium. We surface this as a descriptive disagreement with the age/experience context in the receipt; we do **not** claim the gap is an edge. Gate-4 validation (deferred, ~Dec 2026 accrual) is the only thing that could earn the word "edge."
- Engine-A (rookie capital+age prior) is **demoted** to a normal backlog item — no longer "the unlock," since the rookies are already valued. If it lands, its values ship with their own experimental grade and the same `decision_supported=false`.

## 10. Cross-position value basis — resolved by xVAR (was: "the TE-wall decision")
**The finding (v3):** sorting the Full Universe / Free Agents by **raw DVS** surfaces a wall of tight ends — 13 of the top 15 free agents by DVS are TEs (Colby Parkinson 81.6, Cade Otton 81.6 … vs the top FA WR at 58.6). DVS is a within-position production composite; comparing it across positions is not meaningful.

**The resolution (v3.1, Codex #6, verified):** we do **not** need to defer or build the 0–2000 rescale to fix this — **xVAR already is the cross-position transform** (`pvo_assembler.py:471`), and it is the basis the margin already uses. Sorting free agents by xVAR yields a natural **WR7 / RB4 / TE3 / QB1** mix (Keenan Allen, Kareem Hunt, Marvin Mims on top) instead of 13/15 TEs. So pinning the board's "our value" to xVAR (v3.1) resolves the rank-basis contradiction **and** the TE-wall in one move — no David decision required to ship an honest overall sort.

**What remains genuinely deferred (unchanged from David's ruling):** the **market-comparable 0–2000 rescale** — i.e. expressing our value on a scale directly comparable to FantasyCalc's magnitude. Per Codex, that should be a **producer field with explicit provenance, not a UI-side normalization**. It is a nicety for magnitude-comparison, not a blocker: the percentile-space margin (§2) is already the correct apples-to-apples comparison. Still David-gated, still low priority.

*(Net: the one "open decision" from v3 is closed by xVAR. Nothing here blocks the Phase-0 build or the static comp.)*

---

## 11. Tier calibration contract (v3.2)

David's correction changes the tier contract materially: **"Elite" is not a percentile bucket.** It is a named rendering of a calibrated value cohort only after the model proves that cohort is meaningfully different from the field.

**Producer artifact required before named labels ship:** `tier_calibration_latest.json` (name illustrative; exact path is a future RED/GREEN decision), built from the valuation layer, not the frontend. The artifact owns cohort boundaries, label eligibility, receipts, and stale/degraded states. UI code reads it; UI code does not invent tiers.

**Calibration basis:**
- Primary input = an **unclamped latent DG value** by position. The current public DVS is explicitly clamped to 0–100 (`pvo_assembler.py:389–407`), and current public xVAR is derived from that clamped DVS (`pvo_assembler.py:471–487`), so current RB/WR/TE top-end values flatten exactly where tier precision matters. The calibration producer may expose a raw/unclamped xVAR-like field or a calibrated latent value, but it must name its formula and provenance.
- Current proof point from the 2026-07-08 artifact: public xVAR ties Puka Nacua, Jaxon Smith-Njigba, Ja'Marr Chase, Amon-Ra St. Brown, Rashee Rice, and George Pickens at WR1 because their public DVS is 100, but their unclamped projection-derived raw value separates materially. TE is more extreme: Trey McBride and ten other TEs share public xVAR 2.85 despite projection-derived raw value separating McBride from the field. A tier calibrator that cannot see through that ceiling cannot accurately define "Elite."
- Context inputs = production projection, age / fitted aging-curve state, role/sample reliability, engine path/version, model grade, and completeness flags. These are model/value-context inputs, not UI heuristics.
- Explicitly excluded = FantasyCalc/KTC/market values, ADP, expert consensus, or any market-derived field. Market remains overlay-only.

**Break-finding method:**
- Derive candidate cohorts within position from the current model-valued field using a robust one-dimensional segmentation method such as optimal natural breaks / dynamic-programming changepoints / model-selected mixtures. The chosen method must penalize tiny unstable cohorts, bottom-tail noise, and day-over-day boundary churn.
- Do not predeclare cohort counts. Some positions may have a small top shelf; others may not have a true top break in a given run.
- Persist rank spans, value ranges, cohort size, uncertainty, method version, and data-health status.

**Historical validation:**
- Walk the same rule through historical Engine B feature seasons and realized outcomes (`engine_b_features_v2.csv` outcome `avg_ppg_t1_t2`) with no lookahead. A named label earns display only if its cohort shows material and reasonably stable separation from adjacent cohorts on future production/value outcomes, with a sample-size floor.
- If historical support is weak or incomplete, render the cohort neutrally: "Top cohort · WR1–7" / "Value band · RB18–31", not "Elite" or "Cornerstone."
- Cornerstone additionally requires an empirically derived age/longevity rule from fitted aging curves or a David-ratified taste rule disclosed as such.

**Display contract:**
- The row/rail can show neutral shaded cohort spans immediately once the artifact exists; named labels are an additional gated layer.
- Every cohort display includes a nearby receipt basis: population, position, value basis, calibration version, captured date, historical-support state, and `decision_supported=false`.
- Cohort shading is neutral and low-saturation. It must not use verdict hues, intensity ramps, or action copy.

**Current-state implication:** v3.1's static comp tier chips are directional placeholders only. Production implementation must suppress named labels until the tier-calibration artifact is specified, RED-tested, and built.

## 12. Open items (defaulted where possible)
1. **RESOLVED (David 2026-07-08):** three tabs — My Roster · Other Teams · Full Universe (Free Agents / Rostered + position filters). Data-supported: `league_context.rostered` + `roster_id`/`owner`.
2. **Denominator basis** — our board-relative rank vs market's full-FC rank; the signed percentile delta is the apples-to-apples magnitude. *Default: paired native ranks as readout, delta for sort/magnitude, basis in receipt.* Confirmed acceptable in cockpit.
3. **Fresh-data recompute** — DONE for this comp (2026-07-08 artifact). The daily recompute that keeps it fresh is **Phase 0** (Codex authoring the RED now, PIT included).
4. **Cross-position basis** — RESOLVED by xVAR (§10, v3.1); only the market-comparable 0–2000 rescale remains deferred (producer-side field with provenance, low priority — the percentile margin is already the apples-to-apples comparison).
5. **Tier-calibration producer** — REQUIRED before named tier labels ship (§11). Neutral cohort spans are acceptable only from the artifact; static percentiles are not.

---
*Composition v3.2, regrounded on fresh 2026-07-08 data and corrected for the Codex+Gemini rank-basis re-review (pin to xVAR · percentile-space margin · §7 read-path seeds), plus David's tier-calibration correction (no fixed-percentile named tiers; calibrated cohort artifact required). Next: brief cockpit confirm on v3.2 → disposable real-content static comp may show neutral placeholders only → David's directional preview. Phase-0 daily recompute keeps the data fresh once David authorizes the commit + LaunchAgent install. No production code on the board surface until cleared and David authorizes.*
