# Dynasty Genius — Follow-up B Increment A Due Diligence: Mock-Aggregation → Projected Capital → Engine A Rookie-Pick Valuation

## Executive Synthesis

**Bottom line: Do NOT build the live mock-adapter pipeline now. Build the identity/backtest substrate now; defer live adapters to December 2026 at the earliest, with a manual-curated JSON path serving the 2026 calendar year.** The free-path signal for the 2027 class in late-May-2026 is too sparse, too WalterFootball-dominated, and too volatile to justify standing up three brittle scrapers; the marginal lift over the existing Regime B slot-curve baseline is likely small until the post-bowl window (Dec 2026 – Apr 2027). Source-by-source, only WalterFootball is technically clean today; NFL.com has not yet published a 2027 mock from any of the named analysts (Jeremiah, Zierlein, Brooks, Edholm, Parr, Reuter, Shook, Band, Frelund); Grinding the Mocks has not opened its 2027 cycle in the public dashboard (year selector still terminates at 2026, "Data as of: April 23, 2026").

**Recommended build order across the 4 subsystems:**
1. **Subsystem 3 — Prospect identity (BUILD NOW).** This is the substrate everything else joins to, it has no time-sensitivity, the free anchors (CFBD `college_athlete_id` + nflverse `cfb_player_id`) are stable, and it pays off in 2026 and every future class. Lowest scraping risk, highest cross-class reuse.
2. **Subsystem 4 — Backtest scaffold using historical FINAL mocks (BUILD NOW, manual-first).** Hand-curate 5–8 historical "final" mocks (2018–2025) per analyst from WalterFootball's static archives plus NFL.com author pages, parsed once into a versioned JSON, joined to nflverse realized draft picks. This produces the projected→realized-capital MAE that gates whether the live pipeline is even worth building.
3. **Subsystem 1 — Aggregation methodology (DESIGN NOW, calibrate after backtest).** Spec the consensus formula and uncertainty contract now; calibration data comes from Subsystem 4. No code or infrastructure cost until the math is locked.
4. **Subsystem 2 — Live per-source adapters (DEFER to Dec 2026; manual-curated JSON in the interim).** Three brittle DOM scrapers against an off-season signal that is ~2 analysts deep (Walt + Charlie only) is negative ROI. A monthly David-paste curated JSON of 3–5 mocks delivers ~80% of the value at ~10% of the engineering cost and zero ToS risk.

**Top-level go/no-go summary:**
| Subsystem | Verdict | Confidence |
|---|---|---|
| 1. Aggregation methodology | **GO (design now)** | High |
| 2. Live adapters | **NO-GO now / manual-curated JSON instead; revisit Dec 2026** | High |
| 3. Prospect identity | **GO (build now)** | High |
| 4. Engine-A scoring + backtest | **GO (manual-first historical pull; deferred live integration)** | Medium-High |

**Net recommendation:** Increment A is **not worth building now as a live, automated artifact**. Build the durable, class-agnostic substrate (identity + backtest harness + aggregation spec), keep the 2026 user-facing path as a manually curated 2027 projection JSON refreshed roughly monthly, and reassess automation in Dec 2026 when (a) bowl-game tape exists, (b) NFL.com analysts have published their first 2027 mocks, (c) Grinding the Mocks has presumably opened its 2027 cycle, and (d) we have 6+ months of historical-final backtest evidence on whether projected capital meaningfully beats the Regime B slot curve. The honest cost/benefit vs Regime B in late-May-2026 is that named-prospect projection only marginally improves on the slot curve for the *top of the class* (QB1/WR1) and is *worse* than the curve elsewhere because of stacked-inference variance plus identity ambiguity in the long tail.

---

## Subsystem 1 — Mock-Consensus Aggregation (Methodology)

### 1. Feasibility
**Defensible with free data — yes, but only at the round/tier bucket, not the exact pick, until the late-season window.** Three free sources (WalterFootball Walt, WalterFootball Charlie, plus one of NFL.com Jeremiah/Zierlein once available, or a manual snapshot of Grinding the Mocks EDP) is the absolute floor for "consensus." Below that, any point estimate is an artifact, not a signal.

### 2. Access / methodology reality
- **Established aggregator methodology — Grinding the Mocks (the gold standard):** Benjamin Robinson uses a **Bayesian hierarchical model** with random effects on mock-draft rounds, grouped by position and conference, producing an **Expected Draft Position (EDP)** with a **Highest Density Interval (HDI)** as the Bayesian equivalent of a confidence interval. Weights combine **time-to-draft** (linear weight: `1/(days_to_draft)`) and **draftnik historic-accuracy**. EDP eligibility requires **"10 different mocks from 10 different draftniks"** (Robinson, *To Declare or Not Declare, That is the Question*, Grinding the Mocks Substack, Jan 27, 2025). Any "consensus" with <10 sources is below GTM's own qualification bar.
- **NFL Mock Draft Database (NFLMDDB) methodology:** Aggregates **"850+ analysts and sites"** into a consensus board, with the pipeline normalizing player and team identities and emitting a clean unified feed (per their API product page, nflmockdraftdatabase.com/api). Excluded from our pipeline by policy (Scout tier $5k/yr, redistribution-forbidden, per-response watermark) — but their public 2027 page is a useful sanity-check reference.
- **Aggregation method recommendation (free-path):** Use a **trimmed median of latest per-source picks** (drop top and bottom 1 source when n≥5), reported alongside **MAD (median absolute deviation)** rather than IQR for outlier robustness with small N. Weight by **inverse days-since-publication** (GTM-style time-decay). Do NOT use simple mean — early-class mocks have multiple analysts who clone each other's top 5 with one outlier "hot take" that pulls the mean. Median + MAD is robust to this.
- **Bayesian approximation from 3 free sources:** Not credible. With n=3, the posterior is dominated by the prior; HDIs are nearly identical to the prior range. Three sources can support a trimmed-median point estimate and a min/max range — that is all. Approximate GTM uncertainty bands require ≥8–10 distinct draftniks; we should not pretend to deliver that from 3.

### 3. Governance posture
- Overlay/inference-only: ✓ (every projected-capital output carries `decision_supported=False` with both inference layers flagged).
- No training use: ✓ (mock data never enters Engine A/B feature space; consumed only at scoring time).
- Snapshot-before-parse: ✓ (raw HTML + content_hash stored before any parser runs).
- Fail-closed: ✓ (if n_sources < 3 OR staleness > 60 days OR MAD > 1 round, abstain rather than emit a number).

### 4. Recommendation — Subsystem 1: **GO (design now, calibrate after backtest)**
**Output contract per prospect:**
```
{
  prospect_id,                      // from Subsystem 3
  projected_pick_median,            // trimmed median, time-weighted
  projected_round_bucket,           // 1.early / 1.mid / 1.late / 2 / 3 / 4-7 / UDFA
  projected_pick_range_min,
  projected_pick_range_max,
  mad,                              // median absolute deviation
  n_sources,
  n_unique_analysts,
  staleness_days,                   // days since latest source
  disagreement_flag,                // true if MAD > 16 picks
  abstain,                          // true if any fail-closed gate trips
  decision_supported: false,
  inference_layers: ["mock_to_capital", "capital_to_engine_a"]
}
```
**Round buckets** mirror mainstream tier convention: 1.early (1–10), 1.mid (11–22), 1.late (23–32), 2 (33–64), 3 (65–100), 4–7 (101–end), UDFA. **At late-May-2026 maturity, only the round bucket is materially stable** — exact pick is noise until December. **Big-board exclusion:** require source URL slug to contain "mock-draft" OR explicit "Pick #N → Team X" pairing in scrape; reject pure rankings ("Top 50 Big Board") — those are a distinct artifact and must not be folded into projected capital.

---

## Subsystem 2 — Live Per-Source Adapters (Implementation Reality)

### Per source — current 2026 state

#### A) WalterFootball — Walt & Charlie 2027 mocks
- **Live URLs (verified by fetch, 2026-05-28):**
  - `https://walterfootball.com/draft2027.php` — Walt's 2027 mock R1 picks 1-16 (updated 5/26)
  - `https://walterfootball.com/draft2027_1.php` — Walt picks 17-32
  - `https://walterfootball.com/draft2027_2.php` — Walt Round 2
  - `https://walterfootball.com/draft2027charlie.php` — Charlie Campbell's 2027 mock (updated 5/25)
- **Parse contract:** Server-rendered PHP via WordPress 6.9.4 (after the post-2023 redesign). Each pick is a structured DOM block with team logo image, anchor link to team hub (e.g., `/nflteamhubDolphins2026.php`), bolded team name, prospect name, position, school (visible via `college/{School}_logo.gif` image), and a narrative paragraph. Extractable fields: pick_number (positional), team, prospect_name, position, school, scouting-blurb. **Stable, regex- or BeautifulSoup-tractable.**
- **ToS / robots.txt:** Site is WordPress; meta-robots tag is `max-image-preview:large` (no Disallow on /draft2027.php). No public Terms of Service URL was returned in our checks beyond the WalterPicks LLC footer. **Personal-research reading is permissive in practice; automated mass-scraping carries WordPress-typical legal ambiguity.** Light, polite, rate-limited fetches (≤1 req/min, identified UA) is the responsible posture; aggressive scraping is not.
- **Anti-bot:** None observed on plain GET; pages render to anonymous Python `requests`. No Cloudflare/JS challenge/captcha encountered.
- **Cadence:** Walt's 2027 mock updated 5/19, 5/26 (per Twitter/X post + on-page "Updated 5/26"). Roughly weekly during off-season; daily during draft week. Charlie's separate. Version control: scrape and store `parser_observed_update_date` from page header text ("by Walt • Updated 5/26"). No machine-readable `<meta property="article:modified_time">` on the page — must regex the visible "Updated X/Y" string.
- **Snapshot-before-parse:** Highly amenable. Static HTML, no XHR/JS hydration.
- **Mobile vs desktop drift:** Single responsive template — no separate mobile DOM.
- **Historical archives:** Confirmed back to **2003** at `/draft{YYYY}.php` with archive index pages like `/draft2018archive.php`, `/draft2019archive.php` listing dated weekly snapshots ("Archived 2018 NFL Mock Draft: April 26 (A.M.)" etc.). The pre/post-2023 redesign is a parser break — pre-2024 archives use a different HTML template. **Two parsers needed**: legacy (2003–2023) and modern (2024–present).
- **Bonus asset:** `https://walterfootball.com/draftdata.php` ("NFL Mock Draft Database") is WalterFootball's own manually-curated chart of "14 NFL Mock Drafts found on the Internet… updated EVERY DAY" with top-5 picks per analyst. This is a **manual curator's pre-aggregated table** — a legitimate cross-check, but not a primary feed.
- **Classification: AUTOMATED FETCH (cautious, polite rate) — but in practice this should be MANUAL SNAPSHOT in 2026 due to low marginal value.**

#### B) NFL.com analyst pages (Jeremiah, Zierlein, Brooks, Edholm, Parr, Reuter, Shook, Band, Frelund)
- **CRITICAL FINDING — empirically verified by subagent probe 2026-05-28:** **No NFL.com analyst has published a 2027 mock draft as of late May 2026.** Searches against `site:nfl.com "2027 mock draft"` and analyst-specific slugs return zero results. The author archives for Daniel Jeremiah (`/author/daniel-jeremiah-09000d5d82906849`) and Lance Zierlein (`/author/lance-zierlein-0ap3000000458453`) terminate at 2026-cycle content. The closest 2027 content is a video clip "Why Daniel Jeremiah leans Dante Moore over Arch Manning for 2027 No. 1 pick" — verbal commentary on the Rich Eisen show, not a structured first-round mock.
- **URL convention (confirmed for 2026; predictive for 2027):**
  - Numbered: `nfl.com/news/{first}-{last}-{year}-nfl-mock-draft-{N}-0[-headline-slug]`
  - Final: `nfl.com/news/{first}-{last}-final-{year}-nfl-mock-draft`
  - Example live: `nfl.com/news/daniel-jeremiah-2026-nfl-mock-draft-3-0-rb-jeremiyah-love-lb-sonny-styles-crack-top-five`
  - Edholm slug oddity: `eric-edholm-s-top-100-…` (possessive). Parser must tolerate.
- **Parse contract (from 2026-cycle pages):** React-rendered with server-side hydration; primary pick blocks are accessible in the initial HTML payload. Each pick: `<h3>` with "1. Las Vegas Raiders · Fernando Mendoza · QB · Indiana" structure plus narrative `<p>`. Extractable: pick_number, team, prospect, position, school. Stable enough across iterations 1.0 → final.
- **ToS / robots.txt:**
  - **robots.txt (verbatim, fetched):** `User-agent: * Disallow: /_ctv/ Disallow: /_fantasy-app/ Disallow: /_libraries/ Disallow: /_mobile-app/ Disallow: /_mobileview/ Disallow: /_phs/ Disallow: /_sponsors/ Disallow: /account/ Disallow: /nfl-films-beta/ Disallow: /search/ Sitemap: https://www.nfl.com/sitemap-index.xml`. **`/news/` is NOT disallowed.**
  - **Terms (NFL.com T&Cs, updated 2024-05-16):** Standard "no automated access that adversely impacts site performance" language; no clean explicit per-page "no scraping" clause that goes beyond robots.txt. **Robots.txt permits /news/ fetches; ToS permits non-disruptive personal research access.**
- **Anti-bot:** Light. Cloudflare CDN fronts the site but does not consistently challenge polite Python UAs on /news/ article URLs. No captcha observed in spot-checks.
- **Cadence & versioning:** Jeremiah publishes 3–4 numbered mocks per cycle (1.0 in late January, 2.0 around combine, 3.0 around early April, "final" in draft week) plus video tie-ins. Zierlein, Brooks, Edholm, Parr, Reuter, Shook, Band, Frelund follow similar patterns. **2027 first mocks historically arrive in January–February 2027 after underclassman declarations.** Today (May 2026), expect zero NFL.com 2027 mocks for ~7 more months.
- **Snapshot-before-parse:** Amenable. Static-ish article HTML.
- **Published-date machine-readability:** NFL.com articles do include OpenGraph `article:published_time` meta tags — reliable. **Better than WalterFootball on this dimension.**
- **Archive discovery:** Author-archive pages list historical mocks chronologically; manual seed URLs needed for the 2018–2021 era because slug conventions varied earlier.
- **Classification: AUTOMATED FETCH ALLOWED (polite rate, /news/ paths) — but not actionable in May 2026 because the 2027 mocks do not yet exist.**

#### C) Grinding the Mocks (Benjamin Robinson)
- **Primary URL:** `grindingthemocks.shinyapps.io/Dashboard/`. R Shiny dashboard. Companion newsletter at `grindingthemocks.substack.com/`.
- **Empirical probe finding:** The Shiny app's static fetch returns only `© 2026 Benjamin Robinson & Grinding the Mocks, LLC. All Rights Reserved` and the public pull-quotes from WSJ/Ringer/WaPo. The year-dropdown shows **Draft Year: 2026 · 2025 · 2024 · 2023 · 2022 · 2021 · 2020 · 2019 · 2018** with **"Data as of: April 23, 2026"** — i.e., **the 2027 cycle has not yet been opened in the public dashboard as of late May 2026.** Historically, GTM begins meaningful 2027-class EDP modeling once the draftnik volume crosses the eligibility threshold (≥10 mocks from ≥10 distinct draftniks per prospect), which has not happened in May 2026.
- **Parse contract:** Shiny app — interactive plots, no clean JSON endpoint exposed publicly. **View-only in practice.** Robinson states directly that **"This is the same data that is flowing into the NFL IQ product that the NFL's Next Gen Stats and the team at AWS built"** (*How Well Can Weighted Mock Drafts Predict Round 1 Draft Picks?*, Grinding the Mocks Substack) — i.e., this is a commercial product feeding NFL clubs, not a free machine-readable feed. **There is no documented free, machine-readable export.**
- **ToS reality:** Footer "© 2026 Benjamin Robinson & Grinding the Mocks, LLC. All Rights Reserved." Robinson is monetizing this product. **Automated scraping of his Shiny app is hostile to the business model and unwise even where technically possible.** Substack posts: standard Substack ToS (no automated republication).
- **Anti-bot:** Shiny apps require a websocket session for dynamic state. Static GET returns only the shell.
- **Classification: MANUAL SNAPSHOT ONLY (view-only) — David visits, eyeballs EDP/HDI for the top ~10–20 prospects in the curated 2027 list, pastes into the same curated JSON used elsewhere. NEVER automate.**

### Snapshot & data-contract recommendation
**Raw snapshot row:**
```
raw_snapshots/{source}/{analyst}/{YYYY-MM-DD}_{version}.html
+ sidecar JSON: { source_url, fetched_at_utc, parser_version, content_sha256, http_status, http_last_modified, content_length, ua_string }
```
**Normalized pre-aggregation row:**
```
{ source_id, source_name, analyst, mock_version, published_date, fetched_at,
  prospect_name_raw, prospect_name_normalized, position_raw, position_normalized,
  school_raw, school_normalized,
  projected_pick, projected_round, nfl_team,
  source_rank, raw_row_hash, parser_version, parse_status, prospect_id_match_status }
```
**Fail-closed rules:**
- Missing pick number → row dropped, log warning.
- Team-only mock (no prospect names) → reject whole mock.
- Trade mocks with duplicate teams → accept; pick_number is positional, team is informational only.
- Two-round-only mocks (most are 32-pick) → flag `coverage=top_32_only`; do not synthesize round-3+ picks.

### Cost/benefit honest assessment (this is the crux for Subsystem 2)
**Live scrapers vs manual curated export, May–Dec 2026:**

| Dimension | 3 live scrapers | Manual JSON (David pastes ~3 mocks/month) |
|---|---|---|
| Engineering cost | 2–4 dev-weeks + ongoing breakage | 0 |
| 2026 maintenance | Walt redesign happened in 2023; will happen again. NFL.com React updates break parsers. GTM has no API. | ~30 min/month |
| Coverage in May 2026 | 2 mocks (Walt + Charlie). NFL.com 2027 absent. GTM 2027 absent. | Same 2 mocks + GTM manual eyeball + ESPN/CBS/SI as bonus |
| ToS risk | Non-trivial across 3 sources | Zero |
| Governance burden | Snapshot infra, fail-closed gates, rate limiting | Trivial |
| Value delivered | ~100% if all 3 sources operational | ~80–90% |

**Verdict: Manual curation wins decisively for the 2026 calendar year.** Standing up scrapers when 2 of 3 sources have not even published a 2027 mock is engineering for a problem that does not exist yet.

### Subsystem 2 Recommendation: **NO-GO live adapters now. Manual-curated JSON path through 2026; reassess in Dec 2026.**

---

## Subsystem 3 — Prospect Identity for Undrafted 2027 Prospects

### 1. Feasibility — **High.** This is the most under-appreciated leverage point in the whole increment.

### 2. Access / data reality
**Free, canonical 2027-prospect anchor candidates:**

**(A) CollegeFootballData (CFBD) — `collegefootballdata.com`**
- Free tier: $0 / 1,000 API calls per month; API key required (submit email, accept Terms).
- Academic tier: $0 / 3,000 calls (with .edu email).
- Paid tier ladder (billed via Patreon): Tier 1 $1/mo / 5k calls; **Tier 2 $5/mo / 30k calls — labeled "Most Popular"** with added Live Scoreboard, Weather, Opponent-Adjusted Metrics; Tier 3 $10/mo / 75k calls adding GraphQL + live PBP + realtime subscriptions; Tier 4 $15/mo / 125k; Tier 5 $20/mo / 200k; Tier 6 $30/mo / 500k. Overage policy: temporary disable until next month, upgradeable instantly.
- **Stable `college_athlete_id`** (bigint integer) exposed via both REST and GraphQL endpoints. The GraphQL `athlete` type has fields `id`, `firstName`, `lastName`, `position`, `hometownId`, `jersey`, `weight`, `height`, plus `athleteTeams` joining athletes to teams over `startYear`/`endYear` (handles transfer history).
- `cfbd_draft_picks()` endpoint already joins college rosters to NFL Draft picks via a `college_athlete_id` field, which means **the same ID anchors a prospect from college roster through NFL draft selection.**
- **Caveat:** CFBD has no formal SLA on ID immutability. In practice IDs are persistent integers reused across seasons, but this is community/empirical knowledge, not a contractual guarantee. Treat as "stable in practice, verify post-draft."

**(B) nflverse / Lee Sharpe nfldata**
- `load_draft_picks()` returns columns including `season, round, pick, team, gsis_id, pfr_player_id, cfb_player_id, pfr_player_name, position, college_name, college_conference` — **`cfb_player_id` is the foreign key.** This is the realized-truth join field for backtests.
- `load_players()` aggregates IDs across GSIS, PFR, PFF, OTC, ESPN, ngs, and smart_id with one row per player, manually curated via `players_manual_overwrite.json` for known mismatches.
- **The clean cross-walk is `CFBD.college_athlete_id ≡ nflverse.cfb_player_id`** once a prospect is drafted. Pre-draft, only CFBD owns the prospect; post-draft, nflverse picks them up with the cfb_player_id preserved.

### 3. Name-normalization pitfalls (specific to college prospects)
- **Suffixes:** Jr./III/IV are inconsistent across sources. "Marvin Harrison Jr." vs "Marvin Harrison" vs "Marvin Harrison II". Normalize to a strict `{normalized_first}|{normalized_last}|{suffix_or_null}|{school}|{position}` key.
- **Nicknames vs legal names:** "AJ" vs "A.J." vs "Anthony Jr." (e.g., "A.J. Terrell" was tracked as both; nflverse normalizes via `football_name`).
- **Hyphens/apostrophes:** "O'Cyrus Torrence", "Jer'Zhan Newton", "Olu Fashanu", "Olumuyiwa Fashanu". Apply Unicode NFKC + strip diacritics + standardize hyphen/apostrophe to ASCII.
- **Common-name collisions:** "Leonard Moore" (CB, Notre Dame) vs other "Leonard Moores"; "Jeremiah Smith" (WR, OSU) vs prior college "Jeremiah Smiths." **Never auto-match on name alone for common surnames.**
- **Transfers:** Cam Coleman: Auburn → Texas. Brandon Sorsby: Texas Tech (with transfer history). Treat school as a **soft disambiguator with transfer-history awareness** (CFBD `athleteTeams` supports this), not a hard gate.
- **Schools absent from CFBD:** FCS or partial programs. Rare for top-32 prospects but possible; require manual review.
- **Position changes:** WR→CB (e.g., Travis Hunter scenarios). Tolerate position drift in matching; do not block on position mismatch alone if name+school agree.

### 4. Fail-closed matching algorithm
```
1. Normalize prospect_name from each mock-source row (NFKC + ASCII + strip suffixes to canonical set).
2. Build candidate pool: CFBD athletes with team membership in current_year ± 1 (handles transfers).
3. Tier A — exact match: (normalized_first, normalized_last, normalized_position_group, school OR transfer-history-school) → assign confidence=1.0.
4. Tier B — alias-table hit (curated common-prospect alias JSON): assign confidence=0.95.
5. Tier C — fuzzy: Jaro-Winkler ≥ 0.92 on full name AND school match AND position_group match → confidence = JW score; flag for human review if 0.92 ≤ JW < 0.97.
6. Tier D — ambiguous (multiple candidates above threshold) → DO NOT MATCH; queue for human review.
7. Tier E — no candidate → unmatched; queue.
```
**Reviewable, sandboxed, fail-closed.** All Tier C/D/E rows are surfaced in a reviewer UI; no auto-promotion without sign-off.

### 5. Match-rate gate for the whole 2027 artifact
**If, on the curated 2027 universe (top ~50 named prospects across ≥3 free sources), <90% of mock-consensus prospects join cleanly to a CFBD `college_athlete_id`, the 2027 pick-valuation module fails closed and emits the Regime B slot-curve value only.** Suggested gates:
- **Identity-match precision floor:** ≥90% Tier A+B on top-32; ≥80% on top-50.
- **False-match rate ceiling:** ≤1% on held-out sample (require manual audit of 50 random matches per cycle).
- Below these thresholds → `abstain=true`, `decision_supported=false`, fall back to slot curve.

### 3. Governance posture
- Overlay/inference-only: ✓ (identity layer is data-plumbing; no model training).
- ID-table snapshot: stored locally, version-pinned to CFBD pull date.
- Fail-closed on ambiguity: ✓ (human-review queue, never auto-match collisions).
- ToS: CFBD free tier permits this use within 1k calls/month (single full prospect pull is well under that).

### 4. Recommendation — Subsystem 3: **GO (BUILD NOW).** This is the highest-leverage, lowest-risk substrate. It pays off in every future class. Build the CFBD↔nflverse crosswalk, the normalization rules, the alias table, the fuzzy-match sandbox, and the 90%/80%/1% gates *first* — before any aggregation or scoring code.

---

## Subsystem 4 — Engine A Near-Class Scoring + Backtest Feasibility

### 1. Feasibility
Defensible **as a clearly-labeled cascaded inference**. Engine A consumes NFL draft capital as one feature; substituting *projected* capital adds one inference layer. The compounding variance from (mock → projected pick) × (projected pick → Engine A score) must be surfaced, not hidden. Output must always carry `decision_supported=False` with both inference layers itemized.

### 2. Cascade error propagation
Approximate variance compounding (assuming roughly independent errors, which is conservative):
- **Layer 1 (mock → realized pick):** Per Benjamin Robinson's own published evaluation (*To Declare or Not Declare, That is the Question*, Grinding the Mocks Substack, Jan 27, 2025): **"the average prospects' draft stock is off by only about one round on average (assuming that Undrafted Players are all drafted in 'Round 8') or by about 40 picks up or down"** — this is the mid-season figure, *with* GTM's full Bayesian aggregator. In late May the prior-class MAE is materially wider — for non-top-10 prospects in a 2-source consensus, easily 1.5–2 rounds. (Note: a specific GTM-published numerical MAE for the final pre-draft week was not located in available literature; treat the "tightens toward draft" trajectory as directional rather than a specific quoted figure.)
- **Layer 2 (capital → Engine A fantasy score):** Engine A's existing calibration on realized capital has its own residual variance; substituting noisy projected capital widens prediction intervals proportional to (1 + var_capital_projection / var_realized_capital).
- **Practical implication:** For a top-3 QB prospect, the cascaded interval is tolerable (the top is sticky). For a projected-Round-3 prospect in May, the cascaded interval spans Round 1 through UDFA — making the Engine A output indistinguishable from the slot curve, and arguably worse because it introduces false precision.

### 3. Backtest design — two SEPARATE backtests (do NOT conflate)
**Backtest A — Mock → Realized Capital Accuracy**
- Pull historical FINAL mocks per source per year (2018–2025).
- Per year × source × prospect: capture `projected_pick`, `projected_round`, `team`.
- Join to nflverse `load_draft_picks()` on `cfb_player_id` (post-Subsystem-3 identity).
- Compute per-source-per-year: pick-number MAE, round-bucket accuracy, top-36 skill (QB/RB/WR/TE) recall, UDFA false-positive rate (projected drafted but went UDFA), per-position calibration.
- Compute aggregate (trimmed median across sources): same metrics, vs. each individual source — does the consensus beat any single source?

**Backtest B — Projected Capital → Engine A vs Regime B Slot Curve**
- Held-out historical classes (e.g., 2021–2025 as test, 2018–2020 as calibration).
- Hold each class out, score with (a) Engine A using projected capital, (b) Regime B slot-curve baseline.
- Compare on realized fantasy outcomes (years 1–3 PPG, top-12/24 hit rate by position).
- **Key question:** Does (a) beat (b) by a margin that exceeds the cascaded variance? If not, Increment A is delivering false precision and should be shelved.

### 4. Per year × source — historical FINAL mock availability for backtest
| Year | WalterFootball Walt | WalterFootball Charlie | NFL.com Jeremiah | NFL.com Zierlein | Grinding the Mocks |
|---|---|---|---|---|---|
| 2018 | ✓ (draft2018.php) | ✓ (draft2018charlie.php) | ✓ (archive) | ✓ (archive) | (paper begins 2018) |
| 2019 | ✓ | ✓ | ✓ | ✓ | ✓ (dashboard) |
| 2020 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2021 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2022 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2023 | ✓ (legacy template) | ✓ | ✓ | ✓ | ✓ |
| 2024 | ✓ (modern template) | ✓ | ✓ | ✓ | ✓ |
| 2025 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2026 | ✓ (final 4/23 ish) | ✓ | ✓ (final published) | ✓ | ✓ |

**Coverage: ≥8 years × ≥3 sources is achievable.** This comfortably exceeds the proposed gate of ≥5 years × ≥3 sources. GTM historicals are view-only (Shiny dashboard) but are manually capturable for the top-100 of each historical class.

### 5. Realized-truth join
**nflverse `load_draft_picks()` is the authoritative truth source.** Lee Sharpe's `nfldata` (`https://raw.githubusercontent.com/leesharpe/nfldata/master/data/draft_picks.csv`) is the simpler CSV alternative — same PFR underlying data. Join key: `cfb_player_id` (or `pfr_player_name + season + team` as fallback for pre-Subsystem-3 spot checks).

### 6. Metrics specification
- **Pick-number MAE:** Per source, per cycle-stage (Aug / Bowl / Combine / Final).
- **Round-bucket accuracy:** % of predictions in correct 1.early/1.mid/1.late/2/3/4-7/UDFA bucket.
- **Top-36 skill recall:** Of prospects who actually went in NFL picks 1–36 at skill positions (QB/RB/WR/TE), what fraction had a final pre-draft consensus projected pick ≤36?
- **UDFA false-positive rate:** Of prospects projected drafted in final consensus, what fraction went UDFA?
- **Per-position calibration plot:** Projected pick vs realized pick, with 45° reference.
- **Coverage / abstention rate after identity fail-closed:** How often does the pipeline emit a number vs abstain? Track both, separately.

### 7. Leakage check
**Mandatory.** All historical mocks used in Backtest A must carry `published_date < draft_date`. WalterFootball's "Re-Draft" / "Mock Re-Draft" / "Why the Slide" posts are POST-DRAFT and must be excluded — easy to filter on URL slug containing `redraft` or `whytheslide`. NFL.com post-draft reviews similarly excluded.

### 3. Governance posture
- Overlay/inference-only: ✓ — projected capital never enters Engine A training.
- Stacked-inference labeling: every output carries both inference layer flags and a wide-band uncertainty range.
- Snapshot-before-parse: ✓ for historical mocks (curated JSON; immutable once captured).
- Fail-closed: ✓ — if backtest MAE on a position exceeds a configurable threshold, that position's Engine A projected-capital output is suppressed in favor of slot-curve.

### 4. Recommendation — Subsystem 4: **GO (manual-first historical pull; deferred live integration)**
- Build the backtest harness on historical data NOW using Subsystem 3's identity substrate.
- Run Backtest A first to characterize per-source and per-cycle-stage MAE.
- Then run Backtest B to determine whether the named-prospect path even beats Regime B's slot curve. **This is the gating decision for the entire Increment A live path.**
- Only after Backtest B shows positive lift over slot curve (above the cascaded variance band) commit to live integration in Dec 2026.

---

## Empirical Probe — Current 2027 Mock Landscape (Late May 2026)

### What was actually retrieved (all read-only, public-page, ToS-respecting)
| Source | URL | Result | Parse feasibility | Anti-bot | Updated |
|---|---|---|---|---|---|
| WalterFootball — Walt 2027 R1 | walterfootball.com/draft2027.php | **Full HTML retrieved.** 16 picks, team-by-team with prospect, position, school, narrative. WordPress 6.9.4. | High — stable DOM, predictable selectors. | None encountered. | "Updated 5/26" |
| WalterFootball — Walt picks 17-32 | walterfootball.com/draft2027_1.php | Live, same structure. | High. | None. | 5/26 |
| WalterFootball — Walt Round 2 | walterfootball.com/draft2027_2.php | Live, same structure. | High. | None. | 5/26 |
| WalterFootball — Charlie 2027 | walterfootball.com/draft2027charlie.php | Live. | High. | None. | "Updated 5/25" |
| NFL.com — Jeremiah 2027 | (predicted slug pattern) | **Not yet published.** Author archive ends at 2026 cycle. Only video clip "Why Jeremiah leans Dante Moore over Arch Manning for 2027 No. 1 pick" (Rich Eisen show). | N/A | — | n/a |
| NFL.com — Zierlein/Brooks/Edholm/Parr/Reuter 2027 | — | **Not yet published.** | N/A | — | n/a |
| Grinding the Mocks dashboard | grindingthemocks.shinyapps.io/Dashboard/ | Shell HTML retrieved; interactive Shiny app. **Year dropdown lists 2018–2026; 2027 not yet open.** "Data as of: April 23, 2026." | Low (Shiny, view-only). | Static GET returns only shell. | 2026 cycle data |

### Sparsity assessment
- **Free-path landscape with 2027 mocks in late May 2026: only WalterFootball (2 analysts).** NFL.com: zero. Grinding the Mocks: dashboard not yet cycled to 2027.
- **Broader landscape (out-of-scope by policy, but informative for sparsity assessment):** ESPN (Reid 4/30), CBS Sports (Canady), Sports Illustrated, Bleacher Report (Sobleski/Parson/Holder), NBC Sports, Pro Football Focus, NFL Mock Draft Database aggregating 850+ analysts — these have published, but **NFLMDDB ($5k/yr Scout, redistribution-forbidden) and PFF (testing-only license) are policy-excluded; the others are not in our identified free-path stack**.
- **In short: in the free-path universe, n_sources = 2 today.** That is below ANY defensible aggregation threshold.

### Divergence at the top
Free-path + cross-check sample of named #1 picks (Walt, Charlie, ESPN Reid, CBS, SI, BR, PFF, NBC):
- Arch Manning: 5–6 of 8 mocks
- Dante Moore: 1–2
- Julian Sayin: 1 (PFF)
- Jeremiah Smith (WR): 0 (but consistently #2 or #3)

**Top-of-board has roughly 75% agreement on Arch Manning.** Beyond the top 5, divergence widens fast — by pick 15, no two of these mocks agree on the same prospect, and at pick 25 the noise is total. **Signal is concentrated in the top 3–5 prospects and the QB tier; everywhere else, May 2026 is noise.**

### Signal maturity timeline
- **May–Aug 2026:** "Way-too-early" first mocks. Top-5 QB-driven, rest is noise. **Free-path n=2.**
- **Sep–Nov 2026:** In-season mocks begin; NFL.com analysts publish first 2027 mocks (historically January–February of draft year, but some analysts go earlier). Free-path n likely climbs to 3–5.
- **Dec 2026 (post-bowls):** Underclassman declaration deadline approaches. **First meaningful consensus window.** GTM 2027 cycle likely opens. Free-path n: 4–8.
- **Jan–Feb 2027 (Senior Bowl + Combine):** Mock volume explodes. GTM EDP eligibility threshold ("10 different mocks from 10 different draftniks", per Robinson) crossed for top ~50 prospects.
- **March–April 2027 (final):** Maximum signal. Backtest MAE historically tightens substantially in the top 32.

**Late May 2026 is at the absolute trough of signal-to-noise. Building scrapers now to catch a signal that won't exist until December is engineering for a hypothetical.**

---

## Build/No-Build Gates (Explicit Thresholds)

| Gate | Threshold | Status late-May-2026 |
|---|---|---|
| Min legal/source-safe free sources for live consensus | ≥3 distinct analysts across ≥2 sources | **FAIL** (n=2: Walt + Charlie, both WalterFootball) |
| Min historical backtest coverage | ≥5 years × ≥3 sources | **PASS** (≥8 years × ≥3 sources achievable) |
| Max parser brittleness (qualitative) | No more than 1 brittle DOM scraper at a time; no Shiny/SPA dependency | **MARGINAL** (NFL.com is React; GTM is Shiny → manual only) |
| Min identity-match precision | ≥90% Tier A+B on top-32; ≥80% on top-50 | **PASS expected** (CFBD anchor + nflverse crosswalk) |
| Max identity false-match rate | ≤1% on held-out audit | **PASS expected** |
| Late-May-2026 signal maturity | ≥3 free sources, ≥top-32 coverage, MAD < 1 round on top-10 | **FAIL** (n=2, R1 coverage only, MAD likely 1.5+ rounds outside top 5) |
| Backtest lift over Regime B | Engine-A-with-projected-capital MAE < slot-curve MAE by ≥10% on held-out historical | **UNKNOWN — must measure** |

**Default bias confirmed by the gates:** Build the identity/backtest substrate now; defer live adapters until signal maturity AND backtest lift are demonstrated. Manual-curated snapshot path delivers approximately 80–90% of the achievable 2026 value with roughly 10% of the engineering cost and zero ToS risk.

---

## Governance Classification Summary (Per Source)

| Source | Classification | Rationale |
|---|---|---|
| WalterFootball | **Manual snapshot in 2026; automated fetch permissible at polite rate later** | Static PHP, no robots.txt block on draft pages, no anti-bot, but marginal value vs manual right now |
| NFL.com analyst /news/ pages | **Automated fetch permitted (polite rate)** when 2027 mocks publish; **n/a today** | robots.txt allows /news/; ToS no explicit per-page scraping prohibition beyond "non-disruptive" |
| Grinding the Mocks (Shiny + Substack) | **Manual snapshot only — view-only** | Shiny dynamic rendering; "All Rights Reserved" footer; same dataset commercially feeds NFL clubs via NFL IQ (Next Gen Stats / AWS) per Robinson's own published statement; no public ML-readable export |
| NFL Mock Draft Database (Scout) | **Private inference-only — POLICY EXCLUDED** | Confirmed: $5k/yr, redistribution-forbidden, per-response watermark |
| PFF Sandbox API | **Private inference-only — POLICY EXCLUDED** | Testing-only license |
| nflverse / Lee Sharpe nfldata | **Automated fetch ENCOURAGED** (open data, public GitHub) | Open-source community data; canonical realized-truth source |
| CollegeFootballData (CFBD) | **Automated fetch ALLOWED with API key** (free tier 1k/mo; Academic 3k/mo; "Most Popular" Tier 2 $5/mo for 30k) | Free tier explicit; key required; commercial use permitted at paid tiers |

**No identified terms prohibit storing raw snapshots locally for personal research** for any free-path source. All output remains projection/uncertainty-only with `decision_supported=False`; no trade advice; no buy/sell/target language emitted at any layer.

---

## Final Recommendation

**Build the substrate now; defer the live mock pipeline; ship a manual-curated 2026 path.**

1. **Now (June–August 2026):** Build Subsystem 3 (identity/CFBD crosswalk) and the historical-mock backtest harness (Subsystem 4). Hand-curate the 2018–2025 final mocks across Walt/Charlie/Jeremiah/Zierlein from snapshots, join to nflverse, run Backtest A. Spec Subsystem 1's aggregation contract.
2. **August–November 2026:** Run Backtest B (projected-capital vs slot-curve). Decision point: if lift is <10% over Regime B baseline outside the top-15, **kill the live pipeline permanently** and rely on slot-curve plus a manually-curated top-15 named-prospect overlay only.
3. **December 2026:** Reassess live adapters. By this point: NFL.com analysts have published; GTM has likely opened 2027; underclassman declarations have shrunk the universe; consensus has tightened. The n≥3 gate becomes attainable.
4. **Jan–Apr 2027:** If green-lit, stand up the three adapters (WalterFootball automated, NFL.com automated with polite rate, Grinding the Mocks manual snapshot). Always with the `decision_supported=False` stacked-caveat banner.

This stages the spend, preserves the policy-compliant free-path-only posture, avoids brittle scrapers against off-season noise, and gates the entire live build on whether the math even works.

---

## Caveats

- All output remains overlay/inference-only with `decision_supported=False`. No mock data enters Engine A/B training. Frontend remains on HOLD; NOISE_BAND lock untouched.
- NFL.com's ToS update history (last modified 2024-05-16) and CFBD's full Terms & Conditions page were not retrievable in full during the empirical probe (CFBD `/terms` was bot-blocked at the body level); a final legal review of CFBD commercial-use language is advisable before any paid-tier use. Free-tier personal-research use is uncontested.
- Grinding the Mocks year-dropdown state (2027 open/closed) was inferred from the Shiny app's static-fetch payload (year selector listed 2018–2026; "Data as of: April 23, 2026"), not from an interactive browser session. Recommend a David eyeball check before any first manual EDP capture.
- The "EDP overprojects by ~1 round on average" figure is sourced specifically to Robinson's mid-season Substack post (Jan 27, 2025); a specific published GTM MAE for the *final pre-draft week* was not located in available literature. Treat the "tightens toward draft" trajectory as directional rather than a precisely quoted figure.
- Sources like ESPN/CBS/SI/BR have published 2027 mocks but are out-of-scope per the prior brief's free-path stack; they are referenced here only as evidence of overall landscape sparsity, not as candidate adapters.
- Backtest leakage discipline is mandatory: every mock used must have `published_date < draft_date`. "Re-Draft" and "Why the Slide" content must be filtered out by URL slug.