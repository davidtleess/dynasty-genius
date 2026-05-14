# Phase 9 "Market Overlay" — Architectural Decision Document

**System:** Dynasty Genius (12-team Superflex PPR, Sleeper-backed)
**Phase:** 9 — Market Overlay
**Date:** May 2026
**Status:** Architectural decision document — pre-implementation

---

## 1. Executive Summary

Phase 9 should be built as a **FantasyCalc-only overlay in v1**, with KTC formally deferred and a clean abstraction (`MarketSource`) in place to plug in additional sources later. Five top-level decisions follow directly from the evidence gathered:

1. **FantasyCalc is the right primary source.** It is the only major dynasty market provider that returns a fully structured JSON payload over an unauthenticated HTTP endpoint, *including a direct `sleeperId` field on every player record*. This eliminates the largest engineering risk in market overlays — cross-source identity resolution — and removes any name-fuzzy-matching layer from the critical path.
2. **KTC should remain deferred.** KTC's Terms of Service expressly prohibit automated collection, KTC has no official API (and has stated they have "discussed" but not committed to one), and existing community scrapers are HTML-based BeautifulSoup tools that rely on the site's render and are fragile. A KTC adapter can be added later via the same `MarketSource` interface if and when a sanctioned channel appears, or via a manual periodic CSV import.
3. **`model_minus_market_delta` should be a position-normalized percentile-rank divergence, not a raw arithmetic delta.** Engine B emits PPG (unit: points), FantasyCalc emits a unitless "value" (~0 to 10,500 in the current SF/PPR snapshot). These cannot be subtracted directly. The right primitive is **`pct_rank_model(player) − pct_rank_market(player)` within position**, bucketed into a directional flag with a noise band.
4. **Cache TTL of 24h is correct for the offseason; tighten to 6–12h during the season; never serve stale data without a `stale_market_data` caveat.** FantasyCalc's published cadence ("automatically updated multiple times per day") means a 24h TTL discards real signal during news cycles but is fine in May–July.
5. **Treat market data exclusively as post-scoring overlay.** Engine B v2 must never see `market_value`, `trend_delta`, percentile rank, or any derivative as a feature. This is enforced at the schema level (PVO assembles `market_overlay` after the model has emitted projections) and should be re-asserted in code review checklists for Phase 9 and all subsequent phases.

---

## 2. FantasyCalc API: Confirmed Mechanics

**Status:** Confirmed via live fetch on 2026-05-13.

### 2.1 Endpoint and parameters

```
GET https://api.fantasycalc.com/values/current
    ?isDynasty={true|false}
    &numQbs={1|2}
    &numTeams={8..16}
    &ppr={0|0.5|1}
```

For the Dynasty Genius league (12-team SF PPR), the canonical request is:

```
https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1
```

The endpoint returns 200 OK with `Content-Type: application/json` and a JSON array of player entries. No authentication header is required. The endpoint is **officially documented in a FantasyCalc guest post on fantasydatapros.com** by FantasyCalc's owner Josh Cordell — it is not a reverse-engineered private endpoint. This materially reduces the risk profile compared to a Cloudflare-protected scraper.

### 2.2 Confirmed JSON shape (live response)

The following is an actual element of the live SF/PPR/dynasty array (Bijan Robinson, overall #1 on the day of capture):

```json
{
  "player": {
    "id": 9833,
    "name": "Bijan Robinson",
    "mflId": "16161",
    "sleeperId": "9509",
    "espnId": "4430807",
    "fleaflickerId": "17603",
    "ffpcId": "28755",
    "position": "RB",
    "maybeBirthday": "2002-01-30",
    "maybeHeight": "71",
    "maybeWeight": 215,
    "maybeCollege": "Texas",
    "maybeTeam": "ATL",
    "maybeAge": 24.2,
    "maybeYoe": 3
  },
  "value": 10503,
  "overallRank": 1,
  "positionRank": 1,
  "trend30Day": -39,
  "redraftValue": 10503,
  "combinedValue": 21006,
  "redraftDynastyValueDifference": 0,
  "redraftDynastyValuePercDifference": 0,
  "maybeMovingStandardDeviation": 0,
  "maybeMovingStandardDeviationPerc": 0,
  "maybeMovingStandardDeviationAdjusted": 2,
  "displayTrend": false,
  "maybeOwner": null,
  "starter": false,
  "maybeTier": 1,
  "maybeAdp": null,
  "maybeTradeFrequency": null
}
```

### 2.3 Field-by-field mapping to `MarketOverlay`

| `MarketOverlay` field | FantasyCalc source | Notes |
|---|---|---|
| `source` | literal `"fantasycalc"` | |
| `market_value` | `value` | dynasty value on the SF Dynasty scale |
| `trend_delta` | `trend30Day` | signed integer in the same units as `value` |
| `model_minus_market_delta` | computed (see §5) | not from API |
| `market_percentile` | computed within position from `value` | API exposes `positionRank` and `overallRank`, but rank ≠ percentile; compute from the full position cohort |
| `source_timestamp` | HTTP fetch time (UTC) | **There is no `lastUpdated` field in the response.** Use the time of the fetch as best-available proxy and record it on the PVO. |
| `caveats` | derived | see §6, §9 |

### 2.4 Scale (confirmed)

- The SF dynasty scale tops at **~10,500** in the current snapshot (Bijan = 10503; Jahmyr Gibbs = 10363).
- The scale is **position-agnostic** in its top values: a top RB (10503) and a top WR (Ja'Marr Chase = 10118) sit close in value, while QBs are scaled into the same space (Josh Allen = 6232 at overall rank #19 in SF) — consistent with SF QB inflation.
- The "scale" is *not* fixed at a hard 10,000 ceiling; it floats with the cohort. This is a relative-value scale, not a calibrated absolute one. Phase 9 must therefore not assume any fixed maximum.
- `combinedValue` = `value` + `redraftValue` and exists purely for ranking-blend purposes. **Do not store `combinedValue`** in `MarketOverlay`; it conflates dynasty horizon with redraft, which contradicts Dynasty Genius's t1/t2 PPG focus.

### 2.5 Cross-source IDs in the response

FantasyCalc embeds **five external IDs per player** in the `player` block: `mflId`, `sleeperId`, `espnId`, `fleaflickerId`, `ffpcId`. This is a near-best-case scenario for crosswalk: join key is `player.sleeperId` directly. See §4.

For rookies recently added (e.g., Jeremiyah Love, Carnell Tate, Makai Lemon, Jordyn Tyson in the snapshot), the `mflId` is `"UNK"`, `espnId` and `fleaflickerId` are `null` / `"empty_ff_id"`, **but `sleeperId` is still populated**. This is critical: rookie matching does not regress to name-fuzzy in this API.

### 2.6 Trend, freshness, IR/retired handling

- `trend30Day` is a rolling 30-day delta in `value` units. The current snapshot shows a healthy range of values (−1048 to +914), confirming it is live and not a vestigial field.
- There is **no `lastUpdated` timestamp in the body**. FantasyCalc's site states values are "automatically updated multiple times per day." Treat any fetch as a fresh snapshot.
- Retired players are pruned from the response over time; injured players (e.g., players on IR) generally remain. The API has no explicit availability flag — the system must NOT infer IR/retired from absence; that's the Sleeper-side responsibility. Phase 9 should simply leave `market_overlay=None` for any roster player not present in the FC response.
- `maybeMovingStandardDeviation` is a market-volatility signal computed from FC's trade database (per their Dynasty Research page, MSTD over last 100 trades). This is **valuable as a "market confidence" caveat** but should not be conflated with `trend_delta`.

### 2.7 Reliability and rate limits

- **No published rate limits.** No documented limits, but FantasyCalc is a small operation and the endpoint serves a multi-MB JSON. Be polite: cache aggressively; never burst.
- **No Cloudflare challenge / JS challenge** observed on this endpoint as of the fetch. Plain `requests.get` with default User-Agent succeeds.
- **Reliability risk profile (community-known, soft consensus):** the endpoint is documented by FC themselves and is consumed by multiple third-party tools (e.g., dynasty-tradecraft.lovable.app advertises FC as one of three sources). Risk of unannounced breaking change is real but low; risk of intermittent 5xx exists.

---

## 3. KTC: Current State & Whether to Pursue

**Recommendation: defer indefinitely.** Implement no KTC adapter in Phase 9. Keep a stub `KTCMarketSource` class that raises `NotImplementedError` so the abstraction is real but the surface is zero.

### 3.1 Confirmed facts

- **KTC has no official API.** From their FAQ: *"We don't currently have an API or any sort of .csv available for our rankings and values data. This is something we've discussed adding at some point down the line."*
- **Scraping is explicitly forbidden** in two independent places: (a) the FAQ states *"scraping player values and other data from the site, using full KTC values in tools/resources, or reproducing our rankings and player values in their entirety is expressly forbidden by our Terms and Conditions"*; (b) the Terms and Conditions enumerate *"Any form of automated data collection"* as prohibited.
- **KTC employs active anti-bot measures.** The site runs "test KTC" questions with one obvious answer to detect bots, and a "failed a test KTC" warning is surfaced to suspect sessions. The site also requires periodic engagement (a KTC every few hours when cookies are accepted) to keep the rankings panel visible.
- **Community Python scrapers exist but are fragile.** `ees4/KeepTradeCut-Scraper` on GitHub is a single-file BeautifulSoup tool that uploads to Google Sheets. It depends on HTML structure and is not actively maintained as a library. No equivalent of `ffscrapr` exists for KTC.
- **KTC's underlying valuation algorithm is documented at a high level** in their FAQ: an *"adapted ELO algorithm"* that processes pairwise KTC submissions (Keep/Trade/Cut among three players) and produces values designed to "follow a reasonable distribution on the value spectrum." Superflex and 1QB are entirely separate databases.

### 3.2 Mathematical properties of the 0–10,000 KTC scale

This is the most-asked, least-documented question in dynasty analytics. The honest finding:

- **KTC does not publish a closed-form mapping** of their internal ELO outputs to the 0–10,000 display range. The FAQ describes the goal ("represent the scarcity of studs and also the gradient of player values from top to bottom") but not the function.
- **There is no widely-published normalization formula** (Z-score, log, percentile) from /r/DynastyFF or DynastyProcess that converts KTC values to a calibrated distribution. DynastyProcess's *own* trade values (`dp_values()`) are built from FantasyPros ECR, not from KTC.
- **The community-asserted claim that KTC is "non-linear / logarithmic"** is plausible by inspection (the gap from 9000→9500 represents a different competitive tier than 3000→3500) but is not formally verified anywhere I could find. The behavior is consistent with an ELO-derived scale, where ELO points themselves are derived from a logistic, not logarithmic, function: the *expected score* in ELO is `1 / (1 + 10^((Rb - Ra)/400))`. Translating that back through KTC's rescaling to 0–10,000 produces a curve that is *approximately* linear in the middle and compressed at both tails — closer to a logistic / sigmoid shape than a strict log.
- **Practical implication:** any divergence calculation against KTC values should not assume linearity. Percentile-rank or rank-based comparisons are more robust than raw subtraction. This reinforces the §5 recommendation.

### 3.3 FantasyCalc scale comparison (mathematical)

FantasyCalc's scale is derived from a different mechanism: an optimization over a "trade database" of real fantasy trades (~1M+, per FC's own statement). It is *not* ELO. The scale appears more linear in the middle ranges and inflates at the very top similarly to KTC. The two scales are highly correlated empirically but not identical. **Crucially, since Dynasty Genius will only ingest one of them in v1, the choice of internal scale is moot** — what matters is consistent application of within-source normalization.

### 3.4 If/when to reconsider KTC

Trigger conditions:
- KTC publishes an official API or partner program.
- Dynasty Genius adds a one-time manual CSV import pathway (acceptable under ToS for personal use of displayed rankings — though "reproducing in entirety" remains forbidden).
- A community-curated, ToS-clean KTC snapshot becomes available (none exists today).

---

## 4. Player ID Resolution Strategy

### 4.1 Recommendation

**Primary path:** Use `player.sleeperId` from the FantasyCalc response as a direct join key against the PVO's Sleeper player ID. This requires no fuzzy matching, no crosswalk file, and no name normalization.

**Fallback path (for the small number of FC records with missing or stale `sleeperId`):**
1. Try `mflId` → Sleeper via the DynastyProcess `db_playerids.csv` crosswalk.
2. If still unresolved, log the FC entry to a "unresolved_market_players" structured log and skip — do **not** name-match.

### 4.2 DynastyProcess `db_playerids` — confirmed

The `dynastyprocess/data` GitHub repository publishes `db_playerids.csv` (≈11,668 rows, 35 columns) including these ID columns:

- `mfl_id`, `sportradar_id`, `fantasypros_id`, `gsis_id`, `pff_id`, `sleeper_id`, `nfl_id`, `espn_id`, `yahoo_id`, `fleaflicker_id`, `cbs_id`, `pfr_id`, `cfbref_id`, `rotowire_id`, `rotoworld_id`, **`ktc_id`**, `stats_id`, `stats_global_id`, `fantasy_data_id`, `swish_id`

**Critically, this file already includes a `ktc_id` column** — so if KTC is ever added later (via a sanctioned channel), the join is already solved on the Dynasty Genius side. It is also auto-refreshed by a DynastyProcess script and exposed via the `ffscrapr::dp_playerids()` R function; the underlying file is a plain CSV in a public GitHub repo and can be pulled directly:

```
https://github.com/DynastyProcess/data/raw/master/files/db_playerids.csv
```

### 4.3 Failure-rate expectations

- For active veterans, FC's `sleeperId` is reliably populated. The unresolved cohort in the snapshot was limited to a handful of recent rookies (e.g., several `mflId: "UNK"` cases) **where `sleeperId` was still present**. The expected name-fuzzy fallback rate is therefore effectively zero in the current API state.
- Known historic edge cases (Jr./Sr. suffixes, hyphens, "DJ" vs "D.J.", "Marvin Harrison Jr" vs "Marvin Harrison Jr.") are entirely avoided by using IDs.
- **Recommendation:** treat any `sleeperId == null` from FC as a hard match failure, not a fuzzy-match opportunity. Log it; don't guess. This is consistent with the "the data decides, we never invent" principle.

---

## 5. Mathematical Framework for `model_minus_market_delta`

### 5.1 Core decision: percentile-rank divergence within position

After comparing the four options in the prompt against actual dynasty-analytics practice:

| Option | Verdict | Reason |
|---|---|---|
| **A. Percentile rank within position, then divergence** | ✅ **Adopt** | Unit-free, robust to non-linear market scales, naturally bounded in [−1, +1], directly interpretable as "the model thinks this player belongs N percentile points higher than the market does" |
| B. Fit market_value ~ f(model_PPG), use residual | ❌ Reject for v1 | Requires a fit step, hides nonlinearity in the residual, and is brittle for positions where Engine B is weak (TE) |
| C. Z-score within position | ❌ Reject | Sensitive to outlier players at scale tops; FC's compressed tails make z-scores misleading at the elite tier |
| D. Min-max to [0,1] | ❌ Reject | Same outlier sensitivity as z-score, plus loses ordinal robustness |

Option A is also the implicit approach in the practitioner reference I found that most closely mirrors Dynasty Genius's stated philosophy: DynastyProcess publishes both their own `value` (algorithm-derived) and ECR (rank-based), and dynasty research routinely reasons in *rank tiers* rather than raw value differences. The percentile-rank framework matches that idiom.

### 5.2 Formula (pseudocode)

```
# Inputs (post Phase 8):
#   pvo.projected_avg_ppg_t1_t2       float, points per game
#   pvo.position                       one of {"QB","RB","WR","TE"}
#   pvo.market_overlay.market_value    int, FantasyCalc 'value' (None if unmatched)
#
# Step 1: build cohorts per position from the league universe
#   universe = all rostered + reasonable free-agent pool (e.g., top-300)
#   for each position p in {QB, RB, WR, TE}:
#       cohort[p] = [pvo for pvo in universe if pvo.position == p]
#
# Step 2: percentile rank within position
def pct_rank(values, x):
    # fraction of values strictly less than x, with mid-rank for ties
    n = len(values)
    if n < 2: return 0.5
    less = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return (less + 0.5 * equal) / n

for p in positions:
    model_vals  = [v.projected_avg_ppg_t1_t2 for v in cohort[p]]
    market_vals = [v.market_overlay.market_value for v in cohort[p]
                   if v.market_overlay is not None]

    for pvo in cohort[p]:
        if pvo.market_overlay is None:
            continue  # skip — leave delta None, caveat already set
        m_pct = pct_rank(model_vals,  pvo.projected_avg_ppg_t1_t2)
        k_pct = pct_rank(market_vals, pvo.market_overlay.market_value)

        pvo.market_overlay.market_percentile         = round(k_pct, 3)
        pvo.market_overlay.model_minus_market_delta  = round(m_pct - k_pct, 3)

# Step 3: directional flag with noise band
def divergence_flag(delta, position, model_grade):
    NOISE_BAND = 0.10  # 10 percentile points — see §5.3 for justification
    if model_grade in {"experimental", "fails_validation"}:
        return "model_unreliable"           # TE case
    if abs(delta) < NOISE_BAND:
        return "aligned"
    if delta > 0:
        return "model_higher_than_market"   # BUY candidate
    return "model_lower_than_market"        # SELL candidate
```

### 5.3 The noise threshold (10 percentile points): justification

This is the most important uncertain choice in the entire phase. The reasoning:

- The model and market are expected to be highly positively correlated by construction — both are descriptions of expected future fantasy production. Empirically in dynasty analytics this correlation is typically 0.80–0.92 within position (e.g., DynastyProcess's value vs. consensus ECR rank correlation in published research is in this band).
- At that correlation level, **small percentile gaps are statistical noise**, not signal. A 5-pp gap between model and market for a WR ranked #20 by both within a 60-deep cohort is meaningless.
- **10 percentile points** corresponds roughly to one "tier" in a typical dynasty rankings tier structure (KTC publishes 30+ tiers across the dynasty pool; FantasyCalc's `maybeTier` field in the snapshot ranges 1–35+). Cross-tier disagreement is genuine signal.
- This threshold should be **revisited after observing 1–2 months of data** in production. If 80%+ of flags are "aligned," tighten to 0.08; if too many noisy flags, loosen to 0.12.

### 5.4 Why NOT to expose raw deltas to the owner

The owner-facing display should show **the flag and the percentile gap**, not the raw arithmetic difference of unit-incompatible scales. A line like:

> *"De'Von Achane — Model: 78th pct (RB), Market: 92nd pct (RB) → Δ −14pp → SELL candidate (model lower than market)"*

is interpretable. A line like *"model_minus_market_delta = −1247"* is not, because the units of the subtraction don't exist.

### 5.5 Historical model-vs-market reliability (community consensus)

The published, repeatable findings worth honoring as priors:

- **RBs age 26+ where market is lower than model:** market is usually right. The Apex Fantasy Leagues study (15+ PPR/G, 2010-present) confirms 76.5% of qualifying RB1 seasons occur ages 22–26 and 94.8% occur before age 29. If Engine B prices a 27-year-old RB above the market, *the market is signaling discount-for-cliff and Engine B's age decay function is probably under-weighted*. This is a SELL-candidate trap, not a BUY opportunity.
- **WRs age 26–28 where model is above market:** model is more often right. WRs sustain elite production into late 20s much more reliably than RBs; markets sometimes prematurely discount.
- **Rookie WRs / RBs in Year 1 where market is far above model:** the "KTC Rookie Bump" is real. The market routinely overpays for unproven rookies relative to their probabilistic hit rates. DynastyProcess explicitly distinguishes this in their calculator with two algorithms: *"Perfect Knowledge"* (ceiling: assume rookie hits) vs *"Hit Rate"* (realistic: probability-weighted). The bump peaks **April–May post-NFL-Draft and pre-rookie-draft**. Phase 9 should flag any rookie where market > model by >20pp during May–August as a high-conviction SELL window.

---

## 6. Caching, Freshness, and Degraded Behavior

### 6.1 Cache TTL recommendation

| Period | TTL | Rationale |
|---|---|---|
| **Offseason (Feb 15 – Aug 15)** | 24h | FC values move slowly; combine/draft are punctual events the user can manually invalidate around |
| **Preseason / regular season (Aug 16 – Jan 15)** | 6h | Weekly news cycle, injury reports, snap counts move FC overnight |
| **High-volatility windows** | 1h, manual | NFL draft week, trade deadline week, post-combine week |
| **Playoffs / dead period (Jan 16 – Feb 14)** | 24h | Same as offseason |

FantasyCalc's own description is *"automatically updated multiple times per day"* — so polling more often than every ~3h yields no fresh content. 6h is the safe Nyquist-ish floor.

### 6.2 Degraded behavior (recommendation)

**Two-stage fallback:**

1. **Stage 1 — Fresh fetch:** if cache miss or expired, attempt HTTP fetch. On 200 OK, refresh cache, emit normal `MarketOverlay`.
2. **Stage 2 — Stale-serve with caveat:** if fetch fails (network, 5xx, timeout), serve the most recent cached payload **with `caveats=["stale_market_data", "fetched_at=<ts>", "stale_for=<hours>"]`** appended. Do NOT silently return None.
3. **Stage 3 — Hard fail:** if no cache exists at all (cold start in a failure), return `market_overlay=None` with `caveats=["market_data_unavailable"]`.

This matches the standard "graceful degradation with explicit provenance" pattern. Total silent failure (returning None with no caveat) is the worst option and should be impossible by construction.

### 6.3 Static-snapshot fallback

`dynastyprocess/data` publishes a `values.csv` (and `values-players.csv` / `values-picks.csv`) on GitHub, refreshed automatically. While these values are built from FantasyPros ECR (not FC), they serve as a **legitimate offline fixture for local development and unit tests**. For Phase 9 specifically:

- **Test fixtures:** commit one captured FC response (e.g., the 2026-05-13 snapshot) as `tests/fixtures/fantasycalc_sf_ppr_dynasty.json`. Use it for all unit tests of the adapter and the divergence math.
- **Cold-start emergency seed:** consider committing a once-monthly snapshot of FC's response so that even a fresh checkout has a usable baseline. License/ToS is permissive for FC's free API for personal use.

There is no comparable community-maintained CSV mirror specifically of FantasyCalc's live values that I could find.

---

## 7. Positional Nuance & Caveats

### 7.1 QB (Superflex)

- **Use the SF-specific FC values (`numQbs=2`)**, not 1QB values. The snapshot confirms this: Josh Allen at overall #19, value 6232 in SF — in 1QB he would sit dramatically lower in the cross-positional ranking. Mismatching league format would systematically misprice every QB in the divergence calculation.
- Engine B QB RMSE = 4.51 is the best of the three production positions. QB model-vs-market divergence is **the highest-confidence signal in the system**. Flag aggressively.

### 7.2 RB

- **Auto-attach an `rb_cliff_watch` caveat** for any RB with `age >= 26` AND `pvo.projected_avg_ppg_t1_t2` percentile > market percentile + 10pp. This is the canonical "Veteran Age Cliff Panic" trap where the model is naive and the market has correctly priced in cliff risk.
- For RBs aged 22–25 in the opposite direction (market > model by >10pp), flag as `rb_youth_premium` — the market may be paying for upside the model can't see yet (often legitimate, but worth surfacing).

### 7.3 WR

- Engine B WR RMSE = 2.89, lowest of the three. Highest signal-to-noise. Treat WR divergence flags as high-conviction.
- No special caveat needed beyond the standard flag.

### 7.4 TE

- Engine B TE is experimental and **fails the validation gate**. The divergence flag must be **forced to `model_unreliable`** for every TE regardless of the computed delta. The `model_minus_market_delta` field should still be populated for transparency, but with a hard caveat `"te_model_experimental_do_not_trade_on"`.
- FantasyCalc/KTC TE values are also notoriously volatile (per community consensus and as visible in the snapshot — Trey McBride trend30Day = +491 — that's a 7%+ move in 30 days). So even market-side TE data deserves a `"te_market_high_variance"` caveat.

### 7.5 Rookies and rookie picks

- FantasyCalc tracks rookies as players, not as picks. The current SF snapshot shows several pre-NFL-rookie WRs and RBs already with values (Jeremiyah Love at 7768, Carnell Tate at 2439, Makai Lemon at 2254, Jordyn Tyson at 1585). These are pre-draft prospects with `birthday`, `team`, `college` all null — confirming FC ingests them as soon as the dynasty community starts trading them, well before any production data exists.
- **Engine B cannot project rookies before their first NFL season** by construction (no production history). For rookies, `model_minus_market_delta` should be marked `model_uninformative_rookie`, and only the market-side data (`market_value`, `trend_delta`, `market_percentile`) carries meaning. Do not pretend to compute divergence for a player the model has no opinion on.
- **The "KTC Rookie Bump" / FantasyCalc equivalent peaks in May**, immediately post-NFL-Draft. Players like Jeremiyah Love and Omarion Hampton in the snapshot show large positive `trend30Day` values (+289, +300) consistent with this. A `rookie_peak_value_window` caveat should fire on rookies during April 1 – July 1.

---

## 8. Alternative Sources Worth Considering Later

Ranked by signal-quality-per-engineering-cost:

1. **DynastyProcess `values.csv`** — free, GitHub-hosted, refreshed automatically, joined by `mfl_id`/`sleeper_id`, built from FantasyPros ECR (an *expert-consensus* signal, not crowd-sourced). Would provide a complementary "what the analysts think" signal vs. FantasyCalc's "what the trades say." **High value, near-zero cost. Strongly recommend as Phase 9.5.**

2. **KTC** — see §3. Defer until ToS-clean access exists.

3. **DynastyDataLab** — exists at dynastydatalab.com with a subscription model (the publicly visible offering is a $-tier subscription page; the prompt's reference to "$4 per 1000 requests" matches the typical hobbyist-API price range but I could not independently verify a programmatic API from the public site, which positions itself as a tools/ADP site rather than an API vendor). The methodology mix is "ADP and trade analytics." **Defer; insufficient signal beyond what FC + DP provides.**

4. **DynastyNerds** — has a polished trade calculator powered by "Dynasty Nerds Premium Rankings" (expert-consensus, not crowdsourced), but no public/structured API surface I could find. Their data sits behind authentication. **Defer.**

5. **Underdog ADP** — best-ball ADP, useful as a redraft/season-long ceiling proxy, NOT a dynasty signal. **Defer for dynasty use case.**

6. **Scott Fish Bowl (SFBX) ADP** — a once-per-year tournament ADP. Niche format. **Defer.**

7. **FantasyPros ECR** — the underlying signal for DynastyProcess values. Direct ingestion would duplicate effort. **Subsume via DynastyProcess.**

8. **Consensus aggregation across multiple sources** — appealing in theory ("blend FC + DP + KTC"), but research on consensus methods in dynasty (and in fantasy projections generally) suggests single-source overlays are cleaner for divergence signal: blending market sources produces a smoother signal that masks the very divergences the system is designed to surface. **Recommend against** a consensus blend unless and until at least two sources are confirmed operational, and even then prefer parallel overlays (multiple `MarketOverlay` objects per PVO, source-tagged) over averaged values.

---

## 9. Governance, Leakage, and Bias Heuristics

### 9.1 Leakage discipline (binding architectural constraint)

- `market_value`, `trend_delta`, `market_percentile`, `model_minus_market_delta`, and any derivative thereof must **never** appear in:
  - Engine B's feature set, train or inference
  - Engine B's validation set construction
  - Any age-cliff signal computation that feeds back into Engine B
  - Any rookie projection scaffold
- This is enforced by:
  1. **Schema-level temporal ordering:** PVO assembles `market_overlay` strictly after `engine_b_v2_projection` is final.
  2. **Code-review checklist item:** "Does this PR cause any field in `MarketOverlay` (or any computed-from-market field) to be read inside Engine B's training pipeline or inference path?"
  3. **Test-time fixture isolation:** Engine B training fixtures should not contain a populated `market_overlay` field at all.

### 9.2 The model-market correlation risk

The model and FantasyCalc are descriptions of the same underlying quantity (expected future fantasy production), so their correlation will be high (likely 0.80–0.92 within position based on dynasty analytics norms). This has three implications:

1. **Most players will have `|delta| < 0.10` and be flagged `aligned`.** This is correct behavior — most of the time, the market and a well-calibrated model agree. The system's value is in the *minority* of mispriced players.
2. **Small deltas are not signal.** Hence the 10pp noise band in §5.3.
3. **A correlation-confidence check is worth adding (deferred to Phase 9.5):** periodically compute `corr(model_pct_rank, market_pct_rank)` within position. If correlation drops below 0.70, something has broken (either the model has drifted or the market has). Surface this as a system-health metric, not an end-user feature.

### 9.3 Known systematic biases in market sentiment (community consensus to exploit)

These are *features* of the divergence signal — places where Engine B should reliably outperform the market if Engine B is sound:

| Bias | Direction | Phase 9 action |
|---|---|---|
| **KTC Rookie Bump (April–July)** | Market overprices unproven rookies | Caveat `rookie_peak_value_window`; if model has any read (post-Y1), flag as SELL candidate |
| **Veteran Age Cliff Panic (RB 26+)** | Market correctly discounts; *model* often wrong | Caveat `rb_cliff_watch`; *defer to market*, do not flag as BUY |
| **Recency bias (last 4 games)** | Market overreacts to short-sample stretches | Compare `trend30Day` magnitude vs. cohort norms; surface as `market_recency_swing` |
| **Youth fever / "shiny new thing"** | Market overprices breakout sophomores after one good year | Sophomore (Yoe=2) players with model < market by 15pp+ → SELL |
| **Late-season name-recognition (vets)** | Market under-discounts declining stars (Kelce, Adams, Henry) | RB/TE age 30+ with market > model by 10pp+ → SELL candidate (the "name premium" trap) |
| **Post-trade-rumor spike** | Single news event moves market 1–2 tiers | `trend30Day` outliers (>2σ within position) trigger `news_driven_swing` caveat |
| **Crowdsource vs. trade-data drift** | KTC (crowd opinion) and FC (real trades) routinely diverge — Phase 9 sees only FC, which is the *truer* of the two | No action; FC choice is already correct |

### 9.4 Known precedents of leakage in dynasty tooling

I found no published, well-documented case of a dynasty analytics tool publicly admitting circular use of market data as a model training feature. This is plausibly because (a) most tools don't have a "model" distinct from their market data — they *are* the market data with cosmetics, and (b) tools that do have proprietary models (Draft Sharks' "3D values+", DynastyProcess) are explicit that their values are *outputs*, not inputs. Dynasty Genius's discipline here is meaningfully stricter than the field norm and worth preserving as a differentiator.

---

## 10. Open Questions and Uncertainties

These are gaps the research did not resolve. Per the "data decides" principle, they should be flagged as such rather than papered over:

1. **FantasyCalc rate limits.** No published limit; behavior under aggressive polling untested. **Mitigation:** poll at most every 6h; back off exponentially on any 429/5xx.
2. **Exact mathematical form of the KTC 0–10,000 scale.** ELO-derived but no published closed form, and no published normalization formula from any dynasty practitioner. The "non-linear" community claim is plausible but unverified. **Mitigation:** KTC is deferred, so this does not block Phase 9.
3. **DynastyDataLab API pricing and methodology.** Public pages describe a subscription product oriented toward consumers, not an API at $X/1000 requests. The prompt's specific pricing reference could not be independently confirmed from public sources.
4. **The right noise band for the divergence flag (10pp).** Chosen by reasoning from known model-market correlations and dynasty tier structures, not from empirical Dynasty Genius data. **Mitigation:** make it a config parameter; review after 1–2 months of production data.
5. **Whether FC's `maybeMovingStandardDeviation` should feed into divergence flagging.** FC's MSTD measures market disagreement on a player. Plausibly: high-MSTD players should have a wider noise band before the system flags divergence (because the market itself isn't sure). Not implemented in v1; **candidate for Phase 9.5.**
6. **Handling of FC's `displayTrend` flag.** FC sets `displayTrend: true` on some players to indicate the 30-day trend is meaningful enough to display. Whether Dynasty Genius should mirror this filter on `trend_delta` is unresolved. **Default: surface `trend_delta` always; gate UI display on `|trend_delta| > position-specific threshold` rather than on FC's flag.**
7. **Pick valuations.** FC and KTC both value rookie picks as separately-tradeable assets, but Phase 9's PVO is per-player; pick assets are a different object model entirely. Whether Phase 9 should accommodate picks (and how) is deliberately scoped out here. Recommend a separate `PickValueOverlay` design in a future phase.
8. **Source-timestamp granularity from FC.** The API response itself has no `lastUpdated`. Using HTTP fetch time as the timestamp is a reasonable approximation, but it overstates freshness by up to ~12h (FC's internal refresh cadence). Document this caveat in the overlay's `caveats` field as `"source_timestamp_is_fetch_time_not_publish_time"` whenever it is consumed downstream.