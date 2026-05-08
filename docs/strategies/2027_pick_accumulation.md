---
title: 2027 Pick Accumulation Strategy — The Great Liquidation
type: project-knowledge
framework_protocol: 4D — Maintain Project Knowledge Documents
last_updated: 2026-05-03
status: v1 — initial strategy directive
authored_in_response_to: PM Memo "Strategy Directive — 2027 Value Arbitrage & Strategic Liquidation" (2026-05-03)
companion_docs:
  - docs/class-trackers/2027.md (consensus + verified production)
  - docs/class-trackers/analyst_notes_2027.md (subjective framing; not gating)
review_cadence: quarterly until Sep 2027; then monthly through April 2027 NFL Draft
---

# 2027 Pick Accumulation Strategy — The Great Liquidation

## 1. Mission

Convert depreciating veteran assets approaching or past their position-specific Age Cliff into 2027 1st-round capital, with concentrated targeting of the 2027 WR/QB top tier. Move the roster from "production held past peak" to "optionality on appreciating draft capital."

This document is the **deterministic** version of that mission — explicit triggers, thresholds, and exit conditions. It is not analyst commentary.

Per Framework Rule 6 (never conflate dynasty/redraft): every threshold below is dynasty-only. The 2026 redraft value of these veterans is irrelevant to this strategy.

---

## 2. The Liquidation Side

### 2.1 Verified Liquidation Targets (May 2026)

| Player | Pos | Age (May 2026) | Cliff Status | 2025 Production | 2026 Status | Strategic Class |
|---|---|---|---|---|---|---|
| Davante Adams | WR | 33 | Past Age 28 WR Cliff | **14 rec TD (NFL leader), 60/789** | LA Rams | **Sell — terminal depreciation** |
| Tyreek Hill | WR | 32 | Past Age 28 WR Cliff | Knee dislocation + ACL tear Week 4 | **Free Agent** (released by Miami Feb 16, 2026); recovering from ACL surgery, agent waiting on medical clearance | **Sell-Now — distressed asset** |
| Jonathan Taylor | RB | 27 | At Age 26 RB Cliff (final 2025 game: Jan 4, 2026) | _Pending verification_ | _Pending verification_ | **Sell-High — peak market window** |

> *Ages and Adams/Hill cliff status reflect the PM Memo (2026-05-03). Per Rule 1, the dynasty-relevant fact is "past the position cliff," not the precise birthdate; cliff position is what drives the trigger.*

### 2.2 Sell-Order Priority

**Priority 1 — Jonathan Taylor.** He is the only one of the three whose **market value has not yet collapsed**. Adams and Hill are already discounted in dynasty markets (the cliff has been priced in for 2+ years). Taylor's elite 2025 production and the calendar (offseason = peak RB market window before training-camp injury risk) create the highest-leverage sell window of the three. **This is the trade that funds the strategy.**

**Priority 2 — Davante Adams.** Sell into any contender willing to convert him to a 2027 2nd or a 2028 1st. Do not hold for "if he produces in 2026 his value goes up" — at age 33 there is no upward path; every week of holding is decay.

**Priority 3 — Tyreek Hill.** Same logic as Adams. Marginal speed retention has been the public bull case for 2+ years and has not arrested the value decline. Sell into any acceptable return.

### 2.3 Liquidation Pricing Floors (Engine A baseline reference)

| Asset | Acceptable Floor (do not sell below) | Stretch Target (start asks here) |
|---|---|---|
| Jonathan Taylor | 2027 1st (mid-round, **estimated 1.05–1.08**) + a startable WR3/RB3 | 2027 1st (top-4 protected) + a 2028 2nd |
| Davante Adams | 2027 2nd OR 2028 1st (mid) | 2027 2nd + 2028 3rd |
| Tyreek Hill | **2027 2nd (any slot)** — distressed asset; FA + ACL recovery materially compresses ceiling | 2027 2nd + small kicker (only if a contender bites pre-medical-clearance) |

> *Floors must be revisited if KTC live integration ships (currently deferred per `next-sprint.md`). Until then, floors are heuristic anchors, not Engine B outputs.*

### 2.4 Hard Exit Triggers (auto-sell conditions)

Sell **immediately, into any acceptable floor**, if:
- **Taylor:** any reported soft-tissue injury OR usage drops below 18 touches/game in first 4 weeks of 2026
- **Adams or Hill:** any reported soft-tissue injury OR target share drops below 22% in first 4 weeks of 2026
- **Any of the three:** team trade rumor publicly reported (NFL trades collapse dynasty value within 48 hours)

---

## 3. The Acquisition Side — 2027 Generational Tier

Per Rule 1, this section separates **verified** profile data from **consensus projection** from **analyst framing**. Acquisition thresholds key off verified data + consensus projection only. Analyst framing is logged to `analyst_notes_2027.md`, never used as a strategy gate.

### 3.1 Jeremiah Smith — WR, Ohio State

- **Status:** Verified 2027-eligible (junior in 2026 season).
- **Verified production:** 163 rec / 2,558 yds / 27 TD across 2024–2025; Unanimous All-American 2025; FBS receiving leader since 2024.
- **Consensus projection:** Top-3 to Top-5 overall (Reid/ESPN, McShay/BR, multiple boards).
- **Acquisition class:** **Anchor.** Strategy succeeds or fails on whether we land Smith.

### 3.2 Arch Manning — QB, Texas

- **Status:** Verified 2027-eligible (returned to Texas in Dec 2025, did not enter 2026 draft).
- **Verified production (2025):** 3,163 pass yds / 26 TD / 7 INT; **399 rush yds / 10 rush TD** (one source reports 8; season-review and Citrus Bowl 2-rush-TD performance support 10). Led Texas to Cheez-It Citrus Bowl win over Michigan.
- **Superflex insurance (Rushing Floor):** the 10 rush TDs are the load-bearing data point for the SF case. A QB with documented dual-threat scoring carries a fantasy floor that hedges the published intermediate-accuracy concern. Per Rule 4 (65/35), this is *quant* support for the co-anchor pricing — not narrative.
- **Consensus projection:** Betting market favorite for #1 overall (BetMGM +175 to +225 as of May 2026). **Important caveat:** PFF's way-too-early 2027 mock has Julian Sayin #1 and Manning lower. The "Manning #1" thesis is the *betting market consensus*, not the *analyst consensus*. Treat as Top-5 lock; treat as "Top-3 likely, #1 plausible."
- **Acquisition class:** **Co-anchor in Superflex.** Manning is the QB-tier hedge that makes the whole strategy SF-resilient.

### 3.3 Ryan Williams — WR, Alabama

- **Status flag:** **Eligibility not fully settled in public sources.** Majority of mainstream outlets project 2027; Draft Scout lists him as 2028. *Action: Verify eligibility year via Alabama athletics roster page and 247Sports recruiting profile before committing trade capital. Logged as open gap §6.*
- **Verified production (2025 sophomore, full season, 14 games):** 49 rec / 689 yds / 4 TD on 77 targets — **a step down from his freshman-year breakout**. Per published evaluation, "consistency of explosive plays that made him appointment viewing as a freshman has changed."
- **Consensus projection (assuming 2027 eligibility):** Late 1st (Dane Brugler way-too-early mock at #32). **Not a top-tier consensus lock.**
- **Analyst comparisons (logged to `analyst_notes_2027.md`, NOT a gate):** DeVonta Smith / Jameson Williams hybrid framing.
- **Acquisition class:** **Conditional Tier-2.** Buy-low thesis on talent rebound, not a generational anchor purchase. **Strategy must not pay anchor-tier prices for Williams** — his 2025 production decline + eligibility ambiguity creates real downside.

### 3.4 Acquisition Pricing Ceilings (do not pay above)

| Target | Max Acceptable Cost (from current roster) | Notes |
|---|---|---|
| **Pre-draft pick** that lands Smith (top-3) | 2027 1st + a starting RB2/WR2 | Anchor — pay up |
| **Pre-draft pick** that lands Manning (top-5 SF) | 2027 1st + a starting QB2 + a future 2nd | Co-anchor — pay nearly equal to Smith in SF |
| **Pre-draft pick** projected to land Williams (late 1st, **conditional on eligibility**) | 2027 mid-2nd + small kicker | Tier-2 pricing, not Tier-1 |
| **Post-draft Smith** at his rookie-draft slot | 1.01 in 2027 rookie draft + a 2028 1st (conditional) | Only if we hold the 2027 1.02-1.04 and need to move up |
| **Post-draft Manning** at his rookie-draft slot | 1.01-1.02 in 2027 rookie draft | SF premium |

---

## 4. Value Arbitrage Triggers — 2026 Class Liquidation

### 4.1 The Core Rule

**Any 2026 1st we hold that cannot land Mendoza, Love, or Tate at its slot must be converted to 2027 capital before the 2026 rookie draft.**

The dynasty market overweights "near rookie draft" picks because of recency bias. Selling a 2026 mid-1st in the 30 days before the rookie draft typically returns 2027 1st-round equivalence. Holding it through the draft and using it on a non-anchor 2026 rookie is a value destruction event.

### 4.2 Explicit Exit Conditions (2026 mid-1sts)

Convert to 2027 capital if all three conditions hold:

1. **Slot:** Pick range 1.05 or later in 2026 rookie draft.
2. **Board:** Mendoza (gone, expected), Love (gone, expected — Cardinals selected #3 NFL), Tate (gone if available — Titans selected #4 NFL → likely gone in 1.02–1.04 dynasty range) are all off the board at the slot.
3. **Return:** Trade returns at minimum a 2027 1st (any slot) OR a 2027 1st-equivalent package (pick + meaningful kicker).

If any condition fails, hold and use the pick. Do not sell below 2027 1st equivalence — that is a value-destroying transaction even by this strategy's own logic.

### 4.3 What This Strategy Will Not Do

- Will not trade 2026 1.01 / 1.02 holdings (asymmetric retention — top-end capital is the only 2026 capital that competes with 2027 anchor capital on EV).
- Will not sell 2026 picks for 2028 capital. The 2028 class has zero tracked names as of May 2026 (per `docs/class-trackers/2028.md`); converting present capital to maximum-uncertainty future capital fails Rule 4 (65/35 discipline).
- Will not chase Williams at anchor-tier prices on the strength of 2024 freshman tape alone. Pay Tier-2 or pass.

---

## 5. The 65/35 Quant-Qual Discipline (Rule 4 Compliance)

### 5.1 What Counts as 65% Quantitative Anchor in This Strategy

| Quant Input | Source | Used For |
|---|---|---|
| Verified college production (rec, yds, TD by season) | School/ESPN box scores | Acquisition tier classification |
| Projected NFL draft capital range | Aggregated mainstream mocks (3+ source minimum) | Acquisition pricing ceilings |
| Position-specific Age Cliff thresholds | Internal model + published research | Liquidation triggers |
| Snap counts, target share, touch share (when 2026 season starts) | PFF / NFL Next Gen Stats | Hard exit triggers (§2.4) |
| College Dominator Rating (when ingested) | PlayerProfiler | Tier rebalancing post-2026 college season |
| RAS / verified athletic profile (when measured) | RAS.football, NFL Combine | Final tier confirmation pre-draft |

### 5.2 What Counts as 35% Qualitative — and Stays in Its Lane

| Qual Input | Permitted Use | Forbidden Use |
|---|---|---|
| Manning family lineage / "Arch Manning narrative" | Tiebreaker between Manning and a structurally-identical QB | Sole basis for paying co-anchor pricing |
| Calvin Johnson / Julio Jones comparisons for Smith | Marketing copy in trade pitches to receiving managers | Internal acquisition justification |
| "Looks the part" tape commentary on Williams | One input among many for the eligibility/upside hedge | Override on the verified 2025 production decline |

### 5.3 Anti-Drift Guardrail (per Step 0.1 commits)

If any acquisition decision is made primarily on qualitative inputs (the 35%), it must be flagged in the trade record as a `qual_dominant=true` decision. This creates an audit trail to retrospectively check whether qual-dominant decisions outperform or underperform quant-dominant ones across the strategy's life. Without this, the 65/35 rule is rhetoric; with it, it is a measurable discipline.

---

## 6. Open Verification Gaps (Rule 1 Compliance)

Strategy execution is **conditional** on resolving these gaps before any committed trade is executed against the named 2027 targets:

| Gap | Owner | Resolution Cadence |
|---|---|---|
| Ryan Williams 2027 vs. 2028 eligibility — sources conflict | David (manual check via Alabama athletics + 247Sports) | Before any trade prices Williams as 2027 |
| Smith and Manning combine athletic profiles (RAS) — not yet measured | Track post-Combine (Feb 2027) | Updates `class-trackers/2027.md` |
| Whether KTC live integration ships before 2026 rookie draft | Codex (deferred in `next-sprint.md`) | If yes, replace heuristic floors in §2.3 with Engine B values |
| Whether the QB tier separates by Nov 2026 (Sayin/Manning/Moore/Mestemaker) | Track via class-tracker reviews | Sets late-1st 2027 pick valuation per `class-trackers/2027.md` § Pick Value Implications |
| Adams/Hill/Taylor verified target/touch share for 2026 — pending season start | Sleeper API ingestion | Powers §2.4 hard exit triggers |

---

## 7. Counter-Argument (Rule 5 — Mandatory)

Three reasons this strategy could be wrong, stated honestly:

1. **The "Sell veterans for picks" thesis assumes pick hit rates that mid-1sts historically do not deliver.** Roughly 35–45% of dynasty mid-1sts fail to return WR2/RB2 value within three years. If we liquidate Adams/Hill/Taylor for three 2027 picks and one is Smith (anchor hit) but two are mid-1sts that bust, the portfolio outcome could be worse than holding the veterans through their final productive years. **Mitigation:** the strategy's tier-pricing discipline is designed for this — anchor-tier acquisitions get anchor capital, Tier-2 acquisitions get Tier-2 capital. We are not converting equally across all three picks.

2. **Manning is the betting market favorite, not the analyst consensus #1.** If PFF's Sayin-#1 mock proves prescient and Manning slides into the #6–#10 NFL range, the SF dynasty premium on Manning compresses materially. The strategy's co-anchor pricing on Manning (§3.4) carries this risk. **Mitigation:** acquisition timing — pay co-anchor pricing only after the 2026 college season's first 6 weeks resolve the Sayin/Manning order.

3. **The veterans may have one more elite year.** Adams produced into his 30s; Hill's speed-based game has aged better than typical. Selling at the start of 2026 sacrifices a known production year for uncertain future picks. **Mitigation:** this is the conscious trade. The strategy explicitly favors optionality over terminal production. If David's roster window is "Contend Now" rather than "Build," this strategy is wrong for this roster — re-evaluate against §2 of the Trade Calculator's Roster Window framework before executing.

---

## 8. Execution Checklist (Pre-Trade Verification)

Before any trade executed under this strategy, confirm:

- [ ] Roster Window confirmed as "Build" or "Mid" (not "Contend Now" — this strategy is wrong for contenders)
- [ ] Counterparty's 2027 1st has been verified to actually exist and be unencumbered (no prior trade obligations)
- [ ] If pricing Williams as 2027: eligibility verified per §6
- [ ] Engine A baseline reviewed for the trade; deltas flagged if >15% from this strategy's pricing tables
- [ ] Counter-Argument (§7) re-read in full — Rule 5 is non-negotiable
- [ ] Trade logged with `qual_dominant` flag if applicable

---

## 9. Sources (Verification Snapshot, May 2026)

- [Cardinals select Jeremiyah Love No. 3 — NFL.com](https://www.nfl.com/news/jeremiyah-love-cardinals-no-3-overall-pick-2026-nfl-draft)
- [Titans select Carnell Tate No. 4 — NFL.com](https://www.nfl.com/news/2026-nfl-draft-titans-select-ohio-state-wr-carnell-tate-with-no-4-overall-pick)
- [Raiders select Mendoza No. 1 — Raiders.com](https://www.raiders.com/news/fernando-mendoza-no-1-overall-pick-raiders-quarterback-2026-nfl-draft-indiana-football)
- [Arch Manning betting favorite for 2027 #1 — NBC Sports](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/arch-manning-is-the-betting-favorite-to-be-the-first-overall-pick-in-the-2027-nfl-draft)
- [PFF way-too-early 2027 mock (Sayin #1)](https://www.pff.com/news/draft-way-too-early-2027-nfl-mock-draft)
- [ESPN: 2027 mock with Manning at top](https://www.espn.com/nfl/draft2027/story/_/id/48611355/2027-nfl-mock-draft-early-first-round-predictions-32-picks-manning-smith)
- [Ryan Williams late-1st in Brugler way-too-early mock](https://clutchpoints.com/ncaa-football/alabama-football-news-ryan-coleman-williams-1st-round-expert-mock)
- [Draft Scout: Ryan Williams listed in 2028](https://draftscout.com/dsprofile.php?PlayerId=1100171&DraftYear=2028)
- See `docs/class-trackers/2027.md` § Sources for full Smith verification chain
