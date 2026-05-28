# Research Brief — NFL Mock-Draft Aggregation (Increment A) Build Due-Diligence

**Status:** Research brief (information-gathering scope) — for a web-based research pass, not implementation.
**Date:** 2026-05-28
**Author:** Claude Code
**Purpose:** Do full due diligence on the **four subsystems** of Follow-up B Increment A (near-class NFL mock-draft aggregation → projected NFL draft capital → Engine A near-class rookie pick valuation) **before** we write any design spec. This brief does NOT commit us to building; it defines the questions a research pass must answer so David can make a per-subsystem go/no-go and a build order.

---

## 0. What Increment A is (and why it's decomposed)

Goal: value an **undrafted near-class** dynasty rookie pick (e.g. "a 2027 mid-1st") via *named prospects*, by projecting each prospect's **NFL draft capital** from aggregated mocks, then scoring through **Engine A** into FF slots. The pick-valuation spec (`docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md` §5) classifies this as **"two cascading inferences"** and currently **DEFERRED**, with a hard rule: **consensus mocks are overlay/inference-only; zero mock-adapter imports into the model.**

We are decomposing Increment A into four subsystems; the research must cover all four:

1. **Mock-consensus aggregation** — ≥3 sources → a projected NFL pick/round per prospect (+ range + source count).
2. **Live per-source adapters** — the free sources' access/parse/ToS reality (the brittle, maintenance-heavy part).
3. **Prospect identity** — mapping mock-draft names to our 2027 prospect universe (these are **undrafted college players with no NFL/Sleeper IDs yet** — the hardest new problem).
4. **Engine A near-class scoring + backtest** — projected capital → defensible prospect values + how to validate the projection.

## 1. What we already have (do NOT re-survey)

- **Prior research:** `docs/strategies/Dynasty Genius — Phase 24 Follow-up Scoping- Mock-Draft & Dynasty ADP Sources.md` (with supersession banner). It already surveyed the mock-source landscape and drew **binding license lines** — carry these forward, do not re-litigate:
  - **NFL Mock Draft Database API** ($5k/yr Scout tier; redistribution-forbidden; per-response watermark) — **NOT a redistributable feed.** Usable only as a private internal inference-time overlay if ever subscribed.
  - **PFF Sandbox API** — testing-only license; **not for ingestion.**
  - **Free/usable path:** NFL.com analyst pages (Jeremiah/Zierlein/Brooks/Edholm/Parr/Reuter, stable `/news/{analyst}-{year}-nfl-mock-draft-{version}` URLs); **WalterFootball** (own mocks, 2003→present archive, static PHP); **Grinding the Mocks** (Bayesian Expected Draft Position, 2018–2026, R Shiny dashboard — methodologically strongest, but distributed as a viz, no public feed).
  - **Sports-Reference/PFR** terms restrict automated scraping → use **nflverse / Lee Sharpe's nfldata** for realized draft outcomes (backtest truth).
- **Existing scaffolding in-repo:** `src/dynasty_genius/adapters/manual_export_adapter.py` (curated/manual-input pattern), `resources/mock_prospect_identities_2026_2027.json` (a 2027 identity file already started), `src/dynasty_genius/adapters/prospect_identity_resolver.py` (`normalize_name` + alias bridge), `src/dynasty_genius/scoring/engine_a.py` (`score_prospect` — the consumer).

## 2. Subsystem 1 — Mock-consensus aggregation (methodology)

Questions:
- For a defensible **consensus projected pick/round** from the free sources: what aggregation is sound — simple mean of latest per-source picks, median, or a weighted/Bayesian approach? How do the established aggregators (Grinding-the-Mocks **EDP**, NFLMDDB consensus) actually compute theirs, and can we approximate EDP's uncertainty bands from ≥3 free single-analyst mocks?
- **How many sources** is a credible "consensus" this early (late May 2026, 2027 class)? The prior brief noted way-too-early 2027 mocks already publish — how sparse/divergent are they right now, and does the signal stabilize only closer to the draft (Dec–Apr)?
- Should the output be a **projected pick (point)** + **min/max range** + **n_sources**, and bucket into round tiers (1.early/1.mid/1.late/2/3/4–7/UDFA)? What bucketing do mainstream consensus boards use?

## 3. Subsystem 2 — Live per-source adapters (implementation-level reality)

For each FREE source (**NFL.com analyst pages, WalterFootball, Grinding the Mocks**), at a build-implementation level:
- **Access & parse:** exact page/endpoint shape, HTML structure stability, whether there's any JSON/embedded data vs brittle DOM scraping; how a per-source parser would extract `(prospect_name, projected_pick, team, version, published_date)`.
- **ToS / robots.txt (current, 2026):** is automated fetch permitted for each? Any rate limits? (Re-verify; the prior brief noted no robots block on NFL.com news / WalterFootball, but confirm current state and capture the exact robots/ToS language.)
- **Cadence & versioning:** how often each updates; how to capture "latest mock per analyst" and avoid double-counting versions.
- **Snapshot-before-parse:** is each source amenable to storing a raw snapshot (HTML) before parsing (our governance requires it)? Any anti-bot/Cloudflare?
- **Grinding the Mocks specifically:** is the EDP data reachable in any ToS-clean machine-readable way (Shiny endpoint, Substack, export), or is it view-only (→ manual/cross-check only)?
- **Historical retrievability:** can past-season *final* mocks be retrieved (NFL.com author archives, WalterFootball 2003+, Grinding 2018+) for the Subsystem-4 backtest, and how?

## 4. Subsystem 3 — Prospect identity for UNDRAFTED 2027 prospects (the hard part)

These prospects have **no NFL draft pick, no Sleeper ID, no MFL ID yet** — only names + colleges. Questions:
- Is there a **free, canonical 2027 draft-prospect list** (name, position, school) to anchor identity — e.g. from a mainstream big board (NFL.com, WalterFootball, PFN, CBS) — and how stable are names this far out (transfers, early declarations, name variants)?
- How do mainstream consensus tools handle prospect identity for not-yet-drafted players? Any public prospect-ID scheme (e.g. a college-player ID from CFBD / nflverse college data) we could anchor to?
- What are the **name-normalization / alias pitfalls** specific to college prospects (Jr./III, nicknames, school-name disambiguation for common names)? Our `normalize_name` + `mock_prospect_identities_2026_2027.json` exist — what would a robust, **reviewable/sandboxed fuzzy-match** approach look like (confidence-scored, human-confirmable, fail-closed on ambiguity)?
- Recommended identity anchor + match strategy for joining mock names → our 2027 universe.

## 5. Subsystem 4 — Engine A near-class scoring + backtest feasibility

- Engine A scores prospects partly from **NFL draft capital**. For undrafted prospects we'd feed **projected** capital. Is that defensible, and how should the **two cascading inferences** (mock→projected-capital, projected-capital→Engine-A) be surfaced as **stacked uncertainty** (wide caveats, `decision_supported=False`)?
- **Backtest:** can we validate the projection by retrieving **historical final mocks** (2018–2025) and comparing **projected → realized** NFL capital (realized via nflverse/nfldata), then projected-capital→Engine-A vs actual outcomes? What's the cleanest backtest design + data sources, and what error metric (mean absolute pick error, round-bucket accuracy)?
- Does projecting capital add value over our existing curve-based Regime B (undrafted future class) valuation, or is the named-prospect projection only marginally better than the historical slot curve? (Honest cost/benefit.)

## 6. Binding governance constraints (carry into any build)

- **Overlay/inference-only, absolute model separation:** consensus mocks/projected-capital are inference-time projections; **zero mock-adapter imports into Engine A/B training**; never a training feature (constitution; pick-valuation spec §5; Gemini).
- **`decision_supported=False`** on all projected output; heavy stacked-inference caveats; **no banned David-facing verdict language.**
- **Free path only.** Never NFLMDDB or PFF as redistributable feeds (private inference-time overlay only, if ever). Respect each source's **ToS/robots**; prefer official/stable access; **snapshot-before-parse**; manual/curated fallback where scraping is disallowed.
- **Local-first**, no Databricks for this. Frontend Phase 12 HOLD; NOISE_BAND lock untouched.

## 6b. Research-pass directives (answers to the agent's scoping questions)

1. **Output format — structured per-subsystem + leading synthesis.** Deliver **4 subsystems × {feasibility, access/ToS reality, governance posture, recommendation}**, preceded by a short **executive synthesis** (recommended build order + overall go/no-go + the "build now vs wait for Dec–Apr maturity" verdict). Not a single undifferentiated essay.
2. **Signal probing — YES, light empirical probe.** Actually retrieve a **small sample of current 2027 mocks** from the free sources (NFL.com authors / WalterFootball / Grinding-the-Mocks) to empirically assess signal sparsity/divergence **and** verify access/parse feasibility. Constraints: **read-only, ToS/robots-respecting, small-N** (a handful of fetches, never scrape-at-scale); if a source disallows automated fetch, note it and fall back to manual/visual inspection. This is information-gathering on public pages — not building an ingester.
3. **NFLMDDB / PFF Sandbox — light re-verify only; the exclusion stands regardless.** A one-line current-2026-terms confirmation is welcome insurance, but **free-path-only is a policy decision, not contingent on their pricing/terms** — these are excluded as redistributable feeds either way. Do not spend research budget re-litigating; just flag if anything changed materially.

## 7. Deliverable of the research pass

For **each of the 4 subsystems**: a feasibility verdict + concrete recommendation, plus:
1. The **recommended ≥3 free mock sources** + exact access/parse method + ToS/robots posture + snapshot approach.
2. A **consensus aggregation method** (point + range + n_sources + round bucketing).
3. A **prospect-identity anchor + sandboxed fuzzy-match** strategy for undrafted 2027 prospects.
4. A **backtest design** (historical mocks → realized capital → Engine A) with data sources + error metric.
5. A **recommended build order** across the 4 subsystems, and a **per-subsystem go/no-go** given the data reality and the late-May-2026 signal sparsity.
6. **Net recommendation:** is Increment A worth building now, or should it wait until the 2027 signal matures (Dec 2026–Apr 2027)? Honest cost/benefit vs the existing Regime B curve.

## 8. Non-goals (out of scope for the research pass)

Building any adapter/scraper; any model-training use; lifting the frontend HOLD; tuning NOISE_BAND. The research only informs David's per-subsystem go/no-go and build order.

## 9. Suggested research roles (multi-agent)

- **Lead research / synthesis:** spine agent (Compass/Codex-style) — gather, verify access/ToS per source, fill per-subsystem recommendations.
- **Supporting:** secondary research agent — corroborate ToS/robots/format claims; **do not** let supporting-agent enthusiasm expand scope into buy/sell strategy or lifting governance gates.
- **PM (Gemini):** governance read — confirm overlay-only / no-training-use framing and that nothing proposed implies a model-training feed or a redistributable use of a forbidden source.

---

## 10. Codex research requests (technical/engineering lens)

Added by Codex. Framing: *the main engineering risk is not the aggregation math — it is brittle acquisition + weak undrafted identity + insufficient historical backtest coverage.*

**10.1 Parser stability / source access** — per free source: a concrete current URL example + exact parse contract (fields, selector/DOM or embedded-data path, pagination/versioning, resilience to minor layout changes). Whether published dates are machine-readable; if not, the reliable timestamp fallback (HTTP `Last-Modified` / fetch time / manual metadata). Light-probe anti-bot/CDN behavior (Cloudflare, JS-render requirement, blocked Python UA, rate limits, robots, mobile/desktop markup drift). NFL.com: stable author/version URL conventions across years vs. archive discovery needing manual seed URLs. WalterFootball: one static template vs. pre/post-redesign parsers. Grinding-the-Mocks: is any machine-readable EDP ToS-clean & durable, or classify as **manual cross-check only, not an adapter target**.

**10.2 Snapshot / data contract** — recommended raw-snapshot shape (raw HTML path, source URL, analyst, version, published_date, fetched_at, parser_version, content_hash, parse_status). Normalized pre-aggregation row contract (source_id, source_name, analyst, mock_version, published_date, prospect_name_raw, position_raw, school_raw, projected_pick, projected_round, nfl_team, source_rank, raw_row_hash). Fail-closed behavior for: missing pick numbers, team-only mocks, trade mocks with duplicated teams, two-round-only mocks, **big boards misrepresented as mocks** (must be a distinct source type, not folded into projected capital).

**10.3 Consensus methodology / uncertainty** — compare median / trimmed mean / simple mean / source-count-weighted on historical final mocks; recommend the outlier-robust one. Require uncertainty outputs (min/max, IQR or MAD, n_sources, n_unique_analysts, staleness age, disagreement flag), not just a point. Minimum coverage thresholds by time of year (late-May / preseason / bowls / combine / final month) — when is n_sources too thin for anything beyond a caveated artifact? Whether exact pick or round/tier is materially more stable this early.

**10.4 Undrafted identity** — best free anchor (name, position, school, class, ideally college player id): compare CFBD, nflverse/nfldata, ESPN/CBS/NFL big boards, curated manual file. A concrete fail-closed algorithm: normalize → exact name+position+school → alias table → fuzzy candidate generation with score thresholds → human-review queue for low-confidence → never auto-match common-name collisions. Transfer/school-change handling (hard gate vs soft disambiguator). Edge cases: suffixes, initials, nicknames, hyphen/apostrophe names, position changes, duplicate names, schools absent from CFBD/nflverse.

**10.5 Backtest feasibility** — per year 2018–2026 × source: are final pre-draft mocks available (rounds, exact URLs, parse feasibility)? Realized truth via nflverse/nfldata + exact join fields. **Two separate backtests** (do not conflate): mock→realized-capital accuracy; and projected-capital→Engine-A usefulness vs the existing slot-curve/Regime-B baseline. Metrics: pick-number MAE, round-bucket accuracy, top-36 skill recall, UDFA false-positive rate, calibration by position, coverage/abstention after identity fail-closed. **Leakage check:** backtest mocks must be timestamped *before* the actual draft; exclude post-draft revisions.

**10.6 Build/no-build gates** — explicit go/no-go thresholds (min legal/source-safe free sources, min historical coverage, max parser brittleness, min identity-match precision, late-May-2026 maturity). Honest "build now artifact-only/manual-first vs wait for Dec–Apr maturity" recommendation. Codex default bias: **build only the identity/backtest substrate now if source access is brittle; defer live adapters until source stability + signal maturity justify maintenance**; ask whether a manual curated snapshot path delivers ~80% of value with far less scraper risk for 2026.

**10.7 Governance-specific** — per source: quote/summarize ToS/robots and classify use (automated fetch / manual snapshot / private inference-only / no-use); confirm no terms prohibit storing raw snapshots locally for personal research (if unclear → manual-only or skip); output stays projection/uncertainty-only (no trade advice, no buy/sell/target, no `decision_supported=True`).

## 11. Gemini research requests (PM/governance lens)

Added by Gemini. Framing: protect the analytical core + Product Constitution alignment under "free path only" + model separation.

**11.1 ToS & ingestion rigor for free sources** — for NFL.com news pages, WalterFootball, Grinding-the-Mocks: does the **current 2026 ToS explicitly prohibit automated collection/scraping/machine-parsing even where `robots.txt` does not block** the UA? Specific copyright/redistribution restrictions on Grinding-the-Mocks' Bayesian EDP — if Shiny/Substack, can a read-only script retrieve it ToS-clean for personal use?

**11.2 Anti-bot gating & access feasibility** — do any free sites deploy aggressive anti-bot middleware (Cloudflare JS challenge, Turnstile, captcha)? If automated GETs with a custom UA trigger blocks, the source is designated **disallowed for automated ingestion → manual-curation fallback** (don't fight anti-bot; respects local-first/lightweight principles).

**11.3 Cascade-inference error propagation & fail-closed gates** — for the two cascading inferences (mock → projected capital → Engine A DVS/xVAR), how does error compound, and what is the resulting variance on the final pick value? What **fail-closed match-rate threshold** should gate the whole 2027 pick-valuation artifact — i.e., if name-ambiguity prevents joining more than X% of mock-consensus prospects to our 2027 universe, the module **fails closed** rather than emit false precision into Trade Lab.

**11.4 Automated parsing vs. manual curated JSON — cost/benefit** — given the volatility/unstructured HTML of "way-too-early" mocks (May–Dec), does maintaining brittle DOM scrapers outweigh a version-controlled manual curator export (David pastes ~3 core mocks into a curated JSON ~monthly)? Honest engineering cost/benefit of automating the 3 scrapers vs manual curation during the off-season.

**11.5 Canonical college-ID alignment (nflverse)** — strongest **public collegiate player-ID scheme compatible with our ground-truth `nflverse`/`nfldata`** outcomes, so early identities reconcile cleanly. Do `nflverse` college datasets (`cfb_data` / Lee Sharpe's draft data) provide stable college IDs (e.g. CFBD player ids) that early big boards can map to, **preventing identity-reconciliation debt** once these prospects are officially drafted?
