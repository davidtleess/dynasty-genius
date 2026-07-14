# Static Comp v4 Punch List (post-Codex-verdict iteration; from round-3 audits + lanes)

Frozen comp (ef826f2c) untouched until the Codex verdict; these land in v4.

1. **The central verb: "gap widened/narrowed N pts" replaces "moved N pts toward X"** (audit F: "toward" reads as convergence even when the gap diverged — Mac Jones: market was higher AND rose → WIDENED). Full grammar: price arrow first (▲ his market price rose), then "gap widened 4 pts · market side" / "narrowed 4 pts". One-pass, direction-proof.
2. **Player-first H1 on the Daily Open**: names + direction in the headline ("Mac Jones: the biggest market move on your roster since Thu"), the model-held clause to the subhead; retire the "22 of 23 compared players" stat-speak from the lead. (Hero-nomination check: the H1 names the TOP of the declared sort — same content as the list; keep it factual, no styling emphasis beyond the headline itself.)
3. **FA closest calls quantified as distance-below-the-line** ("Keenan Allen · 2.0 below the line") — the number that makes tomorrow's check-in worth it; the disagreement chip stays secondary. Data: xVAR directly.
4. **Market-value trajectory in the inspector** — OUR capture holds 19 days/player (verified: Legette 472→…→555→450→555 since 06-24). Market-lane sparkline, amber, endpoint dot + printed current value, Hard Right Edge, "our capture began Jun 24" receipt. This is KTC's hook from our own PIT store. (The 14-day depth gate binds OUR margin trends; this is the market's own value series, disclosed basis, 19 days deep.)
5. Inspector: collapse the off-season "Why it moved" slot to one line; add a market-neighbors toggle (market-value ordered) beside model-neighbors; owner context for non-rostered players.
6. Degraded frame: single bold timestamp (it repeats 3×); replace "would manufacture motion" with manager prose ("comparing today to Saturday would invent moves that didn't happen").
7. "pts" anchor visible above the fold once per view (column header carries "percentile points" — mobile needs its one-line anchor).
8. **P0 (audit E) — the rank/verdict collision, on-row:** when native-rank ordering contradicts the percentile verdict (Mac Jones DG QB32 · Mkt QB37 · "Market higher"), the row reads as a bug. Options for David (touches his ratified paired-rank element): (a) on contradiction rows only, swap the Mkt native label for "ranks differ ⓘ"; (b) an inline ≠ marker + receipt; (c) demote native ranks entirely (against the ratified thesis element). RECOMMEND (a): familiarity stays where it helps, disappears exactly where it lies.
9. Mover sentence gets an explicit subject (audit E), merged with #1: "Mac Jones · ▲ market price up · gap widened 4 pts (market side)".
10. Receipt scale explanation: "our model 4.9 (points above a replacement starter) · the market 450 (FantasyCalc value)" — the 4.9-vs-450 juxtaposition invites "typo?" doubt.
11. De-cron the footers ("last attempted" prose), collapse repeated hedging footers to once per view + receipt; densify universe rows toward ~KTC row counts per screen (audit E: ~5/screenful vs 20+).
12. Mobile: fix dangling "· now" wraps, "#146"-vs-"146" rank format drift, dumbbell min-size or chip-only fallback.
13. Fold Codex's frozen-comp verdict findings (pending) before executing v4.
GATE STATUS after round 3: NOT met (E rubric mean 6.7; F trust 9 / desirability 7 / scan 6). Unanimous ceiling across all three rounds: identity (photos/team color — David-gated) + trend history (now data-proven available, item 4) + the item-8 P0.

## Codex frozen-comp verdict (read from pane mid-write 07-13; final doc pending its harness approval)
- CONVERGENT with audit E's P0: identical native QB ranks beside a 20-pt gap "initially looks contradictory" (its first-time-manager persona). Two independent lanes, same finding → item 8 is confirmed the top v4 priority.
- P1: "Closest calls: Allen and Hunt" headline is FALSE as written (Waller/Ertz lead disagreement; Allen/Hunt lead the xVAR/near-replacement sort) and reads as a waiver recommendation → keep aggregate truth, declare the sort, identities live in rows only.
- P1: degraded frames never show the dashed market lane; inspector workflow not composed row-to-panel (the separate inspector file partially answers this — v4 composes them together).
- P1 evidence-bundle: 01-top.png vs 02-midscroll byte-identity check (verified locally — see session ledger); the healthy MID-SCROLL capture is mandatory per the design law.
- Minor: nonadjacent sample ranks need ellipsis rows; ~45px desktop rows vs 32px canonical density (44px targets are mobile-specific); frozen HTML title still says "v2"; receipt must name "our model 4.9" (xVAR, points above replacement) + raw DVS + rounding rule.
- Codex questions routed to David: direction-word chips vs signed deltas = CONTRACT change; can the inspector finish the thought without nominating an action (v1 inspector says yes — neutral tray); is initials-only identity acceptable for directional preview or must headshots precede visual GREEN?

## Gemini round-2 protocol (2026-07-13) — PASS with adoptions; v4.1 QUEUE (apply in ONE pass after Codex round-2; v4 bytes frozen while under its review)
Verdict: grammar reads ONE-pass ("trigger then consequence — no coordinate math mid-coffee"); sparkline edge = "a massive trust-builder" but copy reads defensive; prior visual gaps confirmed resolved on pixels.
SCREEN NOTE: its "market WR pool ~350 / twice our cohort" was a wrong guess — verified 07-11 market WR pool = 152 (ours = 199; the market's is SMALLER). Recommendation adopted with real numbers; the error flagged back to the lane.
v4.1 queue:
1. Sparkline footnote → "450 as of Sat Jul 11 · 18-day daily trend, accruing since Jun 24 · market lane (amber)"; the ⓘ keeps the full honesty ("our capture began Jun 24; no earlier history exists; FantasyCalc value, captured daily by DG").
2. Receipt + inspector familiar-ranks lines gain REAL denominators: "DG WR87 of the 199 we value · market WR109 of its 152-listed WRs (different pools; not subtractable)".
3. Mobile "pts" anchor once per phone: legend footer gains "· pts = percentile points".
4. Universe receipt anchors to a SELECTED row (Legette row aria-selected + raised; receipt titled "for the selected row") — Codex's detached-receipt P1 residue.
5. Fold Codex round-2 findings (in flight).
BUILD-PHASE parity seeds (for the surface REDs, not the comp): search filters 468 players <50ms w/ single-char + alias matching ("J.J."/"McCarthy"); sticky group headers or quick-jump anchor bar on mobile roster; team badges + headshots via Sleeper static assets (DAVID-GATED pipeline).
VERIFIED FIXED (320px): all four phone frames flex to 288px, zero element clipping (programmatic check + own-eyes on 08-320px-mobile-board.png); the page-level h-scroll is the desktop frames' intentional min-width.

## Codex round-2 (v4 bytes) — DUAL NOT-CLEAR; ALL CONCEDED on the facts; v4.1 spec final
Visual mean 6.0. Clears protected: all core counts/ranks/movement/FA facts + the 18-read sparkline reconcile; extractor ruff-pass.
1. LEDE: "Mac Jones moved most" was FALSE (Mac/Legette/Bell tied |4pp|; canonical-id tiebreak ≠ magnitude) + hero-ban violation → aggregate macro returns (pp units); price-arrow grammar stays per-row.
2. UNITS: pp everywhere (ratified), FIXED producer-side (extractor d0b7638d: pp, pluralization, side-cross carries "a 3pp move").
3. SIGNED DELTAS RESTORED = contract-true (+28pp/−14pp, lane-tinted, sign legend anchored); direction-word chips → DAVID PROPOSAL w/ both audits' reasoning.
4. COLLISION rows: BOTH labels kept + "pools differ ⓘ" ("ranks differ" was itself false for McCarthy — labels match).
5. RECEIPT: xVAR = "WR-equivalent points above the position baseline" (pvo_assembler:471-487); rounding = gap rounds ONCE from stored delta (0.276→+28), endpoints separately.
6. "Thursday is the previous comparison day" (FC holds a Jul-10 read — Legette 477, verified in our own series).
7. Jeanty ×2 at mobile sites; Braelon row = "DG read unavailable" (model-routed xVAR null, NOT pre-model); mobile ARIA carries stored gaps (Jeanty 13.9 / Black 31.3 / K.Allen 49.4 / Kyle 7.2).
8. DEGRADED cause copy = the true event (our refresh read the store before the day's prices landed); stale styling extended to the market-side chips; model vintage line.
End-user: FA rows print 2.0/3.5-under-the-line; inspector close ✕ + Esc/focus-return; mobile movers ≤2 lines (compact signed chip); sticky thumb rail; tabs/search/radios focusable; 200% reflow; capture 06 re-shot under iPhone emulation.
HOLD-SCOPE COUNTER sent: signed-delta restoration makes every fix factual-or-contract-true; David items = chips ratification, headshots, preview, commits. Awaiting Codex (a)/(b).

## Round-6 gate inputs — audit B (morning-simulation, v4.4 pixels) → v4.5 QUEUE
Scores: trust 7.5 · desirability 6 · scan 5 (desktop alone 7). "The roster-diff brief and inspector neighbors are real hooks KTC doesn't have."
1. P0 NON-GATED: mobile mover grammar STILL ambiguous — "grew 4pp → −14pp" misreads as "grew to −14"; ▲(price) vs "lead grew"(gap) = two subjects one glyph. FIX: "▲ market lead grew 4pp · now −14pp" (the "now" kills the misread; measured to fit one line at 390/320 — desktop sentence already passes its read-aloud test).
2. NON-GATED: model credibility anchor — honest line "track record accruing since Jun 24 · first verdict ~Dec" (TRUE per Gate-4 forward capture) on Daily Open + inspector; today the core number "has no reason to be believed."
3. NON-GATED: jargon load at first touch — pp undefined in mobile first viewport (H3 suffix "pp = percentile points"), DG unexpanded once, "T-RB18 ×2" needs its receipt, "raw values" internal-speak.
4. NON-GATED: age reads as rank ("QB · 27" → "QB27" double-take) → "age 27" or "27y".
5. NON-GATED: degraded morning = dead end → quiet-day fallback ("your biggest standing gaps" — data is current even when prices pause).
6. NON-GATED: 555/450 scale named at point of use ("FantasyCalc points"); double timestamp → one visible + ⓘ; disclaimer once per surface; mobile dumbbell needs its percentile anchor in the legend; mobile board density + dead panel.
7. GATED (David): the WHY (news/usage), photos.
CONTRADICTION-STACK note (comp-only): two demo mornings visible in one phone scroll — builder-note it; the product never renders two days at once.

## Round-6 gate inputs — audit A (rubric twin, v4.4 pixels)
Mean 5.6 (identity 4, parity 4 — the David-gated ceiling weighs 2 dims; hierarchy 6, mobile 7, first-viewport 7). Convergent w/ B: mover triangle/sign/verb collision. NEW P0s:
1. Hunt "+46pp" emphasis-blue on a below-replacement FA = gap magnitude conflated with player VALUE → v4.5: FA below-line rows de-emphasize the gap chip; the under-the-line figure leads.
2. Rank-pair-vs-sign collision (McCarthy/Jones) "not rescued by the tooltip" — structural options (re-base to one pool, or demote raw ranks to inspector) FOLDED into the standing David shape question.
MOVER GRAMMAR SYNTHESIS (both audits, contract-true): "▲ price up · market lead grew 4pp · now −14pp" — subject verb restored, "now" kills the grew→negative misread; measured to fit one line 390/320.
P1s queued: amber mobile timestamps→gray (amber must mean market-lane only); legend dedup (board phone keeps it; daily H3 carries "pp = percentile points"); tie "×2" title attr; scroll-edge padding; FA-row chip de-emphasis CSS.
DISPUTED (contract wins over audit): "no FantasyCalc read" is the ratified source-bounded lexicon, not a vendor leak — "market" would overclaim a single-source read. ⓘ-per-row is the receipt LAW; density tension noted for David.
GATED echo (both audits): headshots/identity + the WHY + credibility anchor — the anchor is buildable TODAY as the honest line "track record accruing since Jun 24 · first verdict ~Dec".

## Codex round-7 formal record (against v4.5) — rulings of note
- LEXICON DISPUTE RULED FOR THE CONTRACT: "'No FantasyCalc read' is CONTRACT-CORRECT source-bounded wording: KEEP it" (audit A's vendor-leak claim rejected).
- Its pin verification: DG_AS_OF reproduces every frozen number incl. an INVALID Jul-12 pin failing closed; live derives 336/195/94. The reproducibility engineering is CLEAR.
- All its round-7 items (value-first names, modal truth, nav sync, pin provenance, antecedent, pp placement, receipt width, sparkline range, disc saturation) are already landed in the delivered v4.6 (f56088de).
