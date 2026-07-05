# Dynasty Nerds Visual Benchmark — the ratified quality bar

**Date:** 2026-07-05 · **Source:** 14 David-captured screenshots (Desktop, `Screen Shot 2026-07-05 at 2.53–2.59 PM`), read and analyzed by Claude. David's directive: "this is the gold standard. DG should be at this level... at least."
**Feeds:** the reset package (capability plan + reset spec) as the concrete visual bar every rebuilt surface is measured against — screenshot-to-screenshot.

## 1. What the gold standard actually does (observed)

**Rankings table (dynasty-rankings, PPR + SF):**
- Tier-banded rows with labeled group dividers and a colored left tick ("ELITE DYNASTY ASSETS", "TIER 1 — CORE DYNASTY PIECES"…)
- Player identity everywhere: circular headshots, team chip in REAL TEAM COLORS (ATL red, DET blue…) paired with a position chip
- Columns: rank · player · pos-rank (RB1) · **value as the big colored focal number** (10,256 scale; color shifts by tier band) · **Spread — a per-player uncertainty dot-bar with σ value** · ADP · signed rank delta (▲+9/▼−4) · **trend sparkline with net movement number**
- Chrome that respects the user: format chips (PPR/SF/STD/SF-TEP), position chips, consensus-ranker dropdown ("across 4 expert rankers · Updated weekly"), rookies-only toggle, search, CSV export, "Rankings updated Jun 25, 2026," "Showing 300 of 336"
- ~52px rows, generous-but-dense, white canvas, weight-based hierarchy

**Dynasty GM / Analyzer (David's real league):**
- **League-wide stacked bar chart** — 12 teams ranked, position-colored segments, YOUR bar highlighted; "League Rank: 4/12"
- Roster panel grouped by position with colored group headers, each carrying **group total + league rank** ("QUARTERBACKS (5) — 10,140 (5/12)")
- **DRAFT PICKS as a first-class group: every pick valued, group total 7,848, league rank (1/12)** — the franchise-equity view, live, with a disclosed method note ("Pick proj using Contender rank and in-season performance")
- Standings list with total team values; Standings/Schedule/Transactions actions

**Rookies + player detail:**
- Player-highlight hero card (photo, measurables, three stat chips: OVR rank / ADP / pos rank)
- Rookie table with **Best/Worst/Avg across rankers** (ranker spread as columns) + ADP
- Tabbed player profile (Overview / Analysis / NerdScore / College Stats / Film Room): NerdScore hero numbers, **graded attribute bars** (Quickness 65, Catch Radius 92.5…), combine metrics with grade bars, **ceiling/floor player comps**, embedded video, and a named scout's prose analysis with strengths/weaknesses chips
- Prospect Film Room: hero-title page, college logos, per-prospect film libraries, in-page video modal, user scouting notes (synced)

## 2. The parity requirements (structure DG must match)

1. **Identity everywhere** — headshots, team-color chips, college logos. Data feels human. (Sleeper CDN serves headshots by sleeper_id; team colors are a static map — both self-hostable.)
2. **The value number is the hero** — big, weighted, focal; everything else supports it.
3. **Uncertainty is a VISUAL, per row** — DN ships a σ dot-bar per player. DG has real fold CIs and ranges and shows almost none of it visually.
4. **Sparklines in the row grid** — trend-at-a-glance per asset (ours: PIT series, Hard Right Edge, neutral semantics).
5. **Tier banding with labeled dividers** — scannable structure in long tables.
6. **Group totals + league rank on every panel** — "(5/12)" contextualizes every number instantly.
7. **Picks as a first-class asset group** — valued, totaled, ranked (Franchise Equity, already a named increment — DN proves the pattern in David's own league).
8. **Filter/search/export/updated-stamp chrome** as standard table equipment.
9. **Hero moments** — a highlight card at the top of a surface; tabbed player profiles with graded bars and comps.
10. **Prose analysis embedded** — a named voice speaking football, beside the numbers (maps to our counter-argument + qualitative-doc surfaces).

## 3. Constitutional translations (where DN's grammar breaks our law — and ours is better)

| DN pattern | DG translation |
|---|---|
| Green/red trend + delta semantics | Neutral signed deltas; sparklines in lane hue or neutral ink — direction is data, not verdict |
| "ELITE DYNASTY ASSETS" subjective tier labels | Value-band dividers with a DISCLOSED basis ("Band 1 · model value 90–100") — same scannability, no smuggled judgment |
| Consensus value as a single truth | **Two lanes — model AND market, side by side with divergence** (DN cannot do this; nobody can without our capture) |
| Ceiling/floor comps as flat assertions | Deferred to the qualitative-manual lane per the locked reconciliation; if ever surfaced, comps carry a disclosed basis |
| Implied freshness | **Receipts + the tape**: every number carries provenance DN doesn't have |

## 4. Where DG exceeds the gold standard (the "at least" clause)

- **Two-lane truth**: model vs market with visible divergence — DN is single-source.
- **Receipts/provenance on every number** — verifiable, not asserted.
- **The Hard Right Edge** — honest sparkline endings vs DN's implicit continuation.
- **Real uncertainty** — our σ comes from validation folds, not ranker disagreement.
- **The daily PIT archive** — trend depth on OUR league that no vendor owns.

## 5. Package insertions

- The reset spec's Task 5 (restarted daily open) and every I4 surface adopt §2 parity items as acceptance rows; screenshots of DG are compared against the corresponding DN screenshot at David preview.
- New primitives implied: `PlayerIdentity` (headshot+chips), `SpreadBar` (uncertainty dot-bar), `ValueHero`, band dividers with disclosed basis — join the primitive library task.
- Rankings board + Franchise Equity increments inherit DN's observed structures (§1) with §3 translations.
- Asset pipeline note: headshots via sleeper CDN require a self-hosting decision (cache locally vs hotlink) — David-gated, network-fetch policy applies.

## 6. Codex Direct-Viewing Addendum

Codex independently viewed all 14 source screenshots on 2026-07-05. Claude's reading holds. Technical deltas added to the reset package:

- Rankings rows include selectable checkboxes and per-player profile/link affordances; DG dense rows should support those affordance slots when a surface offers comparison or profile navigation.
- The uncertainty visual is a compact horizontal dot/bar with a numeric sigma label; DG's `SpreadBar` must carry an accessible basis and visible numeric/range label, not just a decorative glyph.
- The analyzer is a two-pane workflow: league-wide stacked/team comparison with standings context on the left, selected-team group inspector on the right. DG Franchise Equity should preserve that compare-then-inspect structure.
- The player profile pattern is a persistent identity header plus tabs/section navigation, graded bars, stats, film, and prose. DG needs profile-shell primitives, not isolated cards only.
- Graded bars appear in score and combine contexts; DG can use them only with disclosed basis and neutral/brand-safe color semantics.
- Visual CLEAR needs a benchmark-delta artifact explaining where DG matches DN and where DG intentionally diverges for No-Verdict, receipts, two-lane truth, or unavailable governed data.
