# H2 Frontend Rethink — Whole-Team Design Brief (Fundamentals Reset, Step 3)

**Status:** v3 — **DAVID-RATIFIED as the design of record (2026-07-06)**, with rulings: **OQ1 = hybrid proving slice** (AssetRow/Inspector primitives once → proven on the Daily Open → composed into the Asset Board); **OQ2 = DG orthogonal hues now + a measured Sleeper-adjacent candidate sheet** produced in Increment 0 (David chooses the final family from evidence); **brief ratified — proceed to Increment 0** via the normal cockpit TDD cycle. Content ratified; the document remains uncommitted until David's commit word. v2 had integrated the cockpit adversarial round (Codex 5 findings + sequencing amendment; Gemini product-edge review incl. its own amber-deficit retraction).
**Method:** impeccable `shape` flow (product register), grounded in PRODUCT.md/DESIGN.md and the David-ratified corpus (vision spec v3 · reset spec v1.6 · DN benchmark · voice guide · manager-voice doctrine v3/roadmap). Visual-direction image probes skipped: harness lacks native image generation.
**Inputs (quoted positions, not manufactured consensus):**
- Claude research: `docs/strategies/2026-07-06-claude-fantasy-ui-research.md` (post cross-review corrections)
- Codex research + rethink: `docs/strategies/2026-07-06-fantasy-app-data-display-research-codex.md`, `docs/strategies/2026-07-06-impeccable-led-frontend-rethink-codex.md`
- Gemini product-edge brief (advisory): `~/.gemini/.../fantasy_apps_display_research.md` + cross-review reply (lexicon coexistence, utilization badges, deficit visibility)
- Cross-review evidence rulings: FP payload drifts daily (cite as-of-fetch); KTC caps 9999; Sleeper palette = CANDIDATE hue family only (unverified hexes); Gemini's DynastyGM-toggle claim UNVERIFIED (no named source) — nothing below depends on it.

---

## 1. Feature Summary

Rebuild Dynasty Genius's visible grammar from fantasy-category fundamentals: a universal ranked-row system (the "AssetRow") carrying player identity, one focal value, tier structure, and model/market trend — reused by every surface (Daily Open, Rankings/Asset Board, League Equity, Trade Lab, Waivers/Capacity, Rookie Board, Player Inspector). The failed Task-5 preview was typographically honest but informationally flat; the category's 101 laws (one focal number per row; visual identity; trend-over-named-window; tier chunking; density behind disclosure) were all violated. This rethink adopts those laws and translates them through DG law: no verdicts, two-lane truth, receipts, Hard Right Edge.

**Whole-team diagnosis, unanimous across independent lanes:** DG has been presenting as a governed backend report. The category standard is an asset terminal. The constitutional honesty stack is a differentiator only when mounted on the category's row grammar — Codex: "DG should not skip the 101 layer."

## 2. Primary User Action

David opens the app in the morning and, within five seconds, can answer: *what changed, which assets moved, and what number should I look at first* — then drill any number to its receipt. (Codex critique test: "identify the top player, the drop-off, and the basis of the sort in five seconds.")

## 3. Design Direction

- **Color strategy: Restrained, upgraded to Committed on data surfaces** — the film-room charcoal canvas stays restrained; the data rows now actually SPEND the legal color system (position hues as chips/marks, model-blue/market-amber lanes, DVS neutral ramp) instead of near-zero usage (David's diagnosis of the failed preview).
- **Scene sentence (unchanged from ratified vision):** David, alone at a desk in the early morning or late evening, lamplight or dark room, checking his league's overnight tape like a trader before the open — the dark film-room theme is forced.
- **Anchor references:** Dynasty Nerds rankings widget (the David-designated parity benchmark: headshots, team-color badges, named tier bands, spread bars, sparklines); KTC's rankings row + value-history hover (focal-number discipline, named-window trend); Bloomberg/private-terminal density (already constitutional at 32px rows). Anti-references hold (no betting-app energy, no verdict green/red, no SaaS hero-metric cards).

## 4. Scope

- **Fidelity:** production-ready increments, David-previewed per increment (the reset's evidence-gate machinery — Playwright captures + benchmark-delta — stays binding).
- **Breadth:** whole visible layer over time, executed in increments; first increment per §11's David choice.
- **Interactivity:** shipped-quality; every row opens the Inspector; receipts keyboard-operable.
- **Time intent:** polish until "truly exceptional" (David's standing bar); preview gates, not calendar gates.

## 5. Layout Strategy — the universal AssetRow grammar

Codex's `AssetRow` proposal, amended by cross-review, is adopted as the core primitive — composing and EXTENDING existing `frontend/src/ui/` primitives, never rebuilding them. Codex R1–R3 primitive-contract corrections (v2):
- **PlayerIdentity must be EXTENDED in Increment 0**, not merely composed: its current contract (name/team/position/imageStatus) renders fallback initials only and no image even when `imageStatus="available"`; headshot rendering, team mark, and pos-rank are NEW props under the asset-pipeline decision.
- **ValueHero stays out of 32px rows** (it is a stacked inspector/header hero); rows use `MetricCell` + hierarchy styling or a new compact row-value variant.
- **SpreadBar is model-colored today** (`--dg-model` dot); it gains a lane prop/variant with token-law tests before any market-lane use — a market swing must never inherit model blue.

```
[rank] [identity: headshot→fallback · name · pos chip · team mark · pos-rank] [FOCAL VALUE] [model lane: value·trend] [market lane: value·trend] [context col(s)] [status tokens] [receipt]
```

- **One focal number per row**, chosen by the active sort, visually dominant (one step larger, heavier weight, tabular numerals) — never sentiment-colored; deltas carry direction via glyph+sign first, lane color second.
- **32px desktop rows** (48–56px only where headshots + two-line identity require); mobile = two-line cells with a fixed right-side value stack, inspector as bottom sheet.
- **Tier structure**: full-width `ValueBandDivider` rows at band boundaries — NEUTRAL labels now (Tier 1..N + disclosed basis, FantasyPros-style); named lexicon bands (Generational/Elite/Cornerstone/Starter/Depth) light up ONLY after roadmap Steps 1–3 COMPLETE (00 amendment → canonical field + threshold derivation → lexicon module + enforcement REDs; Codex R4 — amendment-only is NOT sufficient), then per Gemini's coexistence design: word+number badge (`Elite (96%)`), dividers at lexicon boundaries, Model Grade Receipt in the Inspector disclosing threshold/hysteresis/staleness.
- **Two-lane columns stay symmetric** in weight; a market swing must never read as a model signal; sparklines terminate at the Hard Right Edge.
- **Sort basis is always disclosed in the header** ("sorted by model value percentile") — a rank without basis is a defect (both lanes independently).

## 6. Key States

- **Loading:** skeleton rows mirroring the AssetRow layout, left-to-right shimmer (research: layout-mirroring skeletons read fastest), Carbon motion tokens, reduced-motion = instant.
- **Empty/off-season quiet:** manager-prose quiet states (voice guide), never bare "no data"; each names when the next data arrives (refresh-cadence-as-habit, research-confirmed).
- **Stale/degraded:** stale-desaturation + explicit token; staleness degrades labels (doctrine); absent artifact = honest 200-degraded pattern (existing law).
- **Changed-since-last-capture:** one-shot decay pulse on just-changed values (never looping); the Daily Tape is a filtered AssetRow list, "changed rows only."
- **Headshot fallback chain:** headshot → initials-on-position-hue disc → silhouette; a broken image never renders (research: nflverse/Sleeper pattern).
- **Error/fail-closed:** existing 503/sanitized patterns untouched.

## 7. Interaction Model

Scan → inspect → compare → decide (by David). Row click/Enter opens the right-side **Player Inspector** (drawer desktop / bottom sheet mobile): first viewport = identity, model percentile, xVAR, market value, model-market delta, age/curve state, freshness; second layer = drivers, counter-argument, ranges, receipts, trend history (Hard Right Edge), comparable cohorts. Hover = enhancement only; keyboard-first per a11y law. Position tabs/chips + format context ("Superflex · PPR" always visible — category law). No action-order buttons anywhere.

## 8. Content Requirements

- **Copy register:** dynasty-manager prose (voice guide binding); banned-language scans + cordon tests keep enforcing; category action-words translate per Codex's table (Buy/Sell → market divergence; Target → candidate row under selected sort; Winner → side delta).
- **Assets (David-granted unlock, formalized here):** self-hosted asset pipeline — Sleeper CDN headshot mirror keyed by canonical player_id + a 32-team color map (primary+secondary per team, per-theme contrast-picked, accents only). Private single-user use = low trademark risk (research); colors+abbreviations preferred over logo files.
- **Position hues — NAMED DECISION for David (§11):** existing DG tokens are orthogonal-by-design (QB 300 purple / RB 170 green / WR 340 pink / TE 205 cyan); Sleeper's familiar family (QB pink-red / RB teal / WR BLUE / TE orange) collides at WR with the constitutional model-blue lane. Options: (a) keep DG orthogonal hues (lane law pristine, familiarity cost), (b) adopt a Sleeper-adjacent family with WR shifted off-blue — v2 (Codex R5): under-specified until EVERY candidate hue passes the token-law tests (≥35° from model 255 and market 75, banned red/green arcs — Sleeper-ish QB pink-red and RB teal need proof too); only orderable as a measured candidate sheet (OKLCH distances, contrast, screenshot samples, token-test updates), (c) full Sleeper family + move model lane off blue (rejected by Claude: model-blue is ratified brand). Lane positions: Codex = (a) now, (b) only as measured sheet; Gemini (advisory) = (b); Claude = (a) now, produce the (b) candidate sheet in Increment 0 so David can choose with evidence.
- **Data already available to light up:** real PIT capture series (sparklines are honest — we own the history), dvs_pct/percentile fields (PlayerProfiler grammar: `value (Nth of cohort)`), spread/divergence data, utilization fields (Gemini's driver-badge input: subordinated `▲ routes` badge next to changed values — team to verify field coverage per surface).

## 9. Recommended References (implementation phase)

impeccable `craft` per increment; `critique` with heuristic scoring on each preview candidate BEFORE David sees it (the missing flow last time); `polish` pre-preview; `animate` (Carbon tokens exist; motion = state only); `adapt` for the mobile pass. Evidence gates (axe=0, captures, benchmark-delta) stay binding per reset spec v1.6.

## 10. Open Questions (real ones, not defaults)

1. **Increment 1 shape — the A/B choice (David):** Codex prefers **A** (Asset Board + Inspector first: system coherence, every surface inherits) and honestly steelmans **B** (Daily-Open rescue as a thin proving slice using the same AssetRow primitives: repairs the exact surface David saw fail, fastest daily-login value). Claude's position: **B-scoped-as-A's-proving-slice** — build the AssetRow/Inspector primitives ONCE, prove them on the daily open (smallest honest preview), then compose the full Asset Board; pure-A risks another long dark stretch with no David preview, which is what the preview gate exists to prevent. Gemini (advisory, manager-lens) endorses the hybrid: primitives first, proven on the tight daily screen, then expanded. C (surface-by-surface reskin) is unanimously rejected. **This is David's call — lane positions stand as stated; no consensus is declared on A-vs-hybrid.**
2. **Position-hue decision** (§8, three options).
3. ~~Deficit-marker styling~~ **RESOLVED in the adversarial round (three-way convergence):** neutral treatment — plain descriptive copy ("WR shortfall: 2 vs league median 4") with a quiet gray token; NO amber (Gemini retracted its own amber proposal: amber is the market lane, a deficit border would misread as a market signal); no bracketed all-caps `[DEFICIT]` copy (Codex); gray-outline vs plain-text variants compared at critique.
4. ~~Mobile priority~~ **RESOLVED (three-way convergence):** desktop-terminal-first increments, with the two-line mobile AssetRow + bottom-sheet Inspector co-designed and shipped in the SAME acceptance gate as desktop (Codex: not a later responsive cleanup).

## 11. Execution Sequence (post-ratification)

Increment 0: asset pipeline (headshots + team map) — with its OWN spec/RED treatment per Codex: offline-safe cache, no hotlinking at render time, missing-image fallback classes, team-color contrast validation — plus the position-hue decision (incl. the option-b measured candidate sheet) and the AssetRow/Inspector primitive extensions with critique flow. Any visible primitive/layout change carries the reset-spec evidence bundle (screenshots + axe + benchmark-delta) — Increment 0 is not exempt. Increment 1: David's A/B choice surface, full impeccable critique→craft→polish cycle, evidence bundle + benchmark-delta, David preview. Then compose outward (Asset Board ⇄ Daily Tape, League Equity, Trade Lab, Waiver/Capacity, Rookie Board) — each increment David-previewed. Lexicon adoption stays gated behind roadmap Steps 1–3 (00 amendment → canonical field/thresholds → lexicon module + REDs); nothing here jumps that queue.

**Success criteria for the next David preview (Codex's list, team-adopted):** real player rows with headshots/fallbacks in the first viewport; the focal value and sort basis obvious; tier structure visible without reading a paragraph; model and market lanes distinct; at least one sparkline ending at the Hard Right Edge; mobile view designed; receipts accessible but quiet; the screen reads as a dynasty asset terminal, not a compliance report.
