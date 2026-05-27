# Research Brief — NFL Mock-Draft & Dynasty ADP Sources

**Status:** Research brief (information-gathering scope) — for a research pass, not implementation.
**Date:** 2026-05-26
**Author:** Claude Code
**Purpose:** Scope what we need to learn about (A) NFL mock-draft sources and (B) dynasty rookie/player ADP sources, to unblock two deferred Phase 24 follow-ups. **This brief does not commit us to building either; it defines the questions a research pass must answer so David can decide.**

---

## 1. Why we need this (the two follow-ups)

Both are deferred Phase 24 follow-ups recorded in `docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md`:

- **(A) Near-class projection (§5).** To value a *current/near* rookie class's picks before its NFL draft, Engine A needs **projected NFL draft capital** per prospect. The class-trackers already document the practice — "aggregated mainstream mocks (3+ source minimum)" for projected NFL draft capital range. We need to know *which mock sources*, how to access/aggregate them, and whether historical mocks exist (to backtest the projection).
- **(B) ADP ingestion.** A dynasty **rookie/player ADP feed** would serve as (i) a market overlay alongside FantasyCalc and (ii) a supplement to the thin SF-QB-calibration corpus. We need to know *which ADP feeds* are real-draft-derived, settings-filterable, accessible, and historically deep.

**Both are strictly overlay / inference-time signals — never Engine A/B training inputs** (constitution: market/analyst data is price-discovery/projection, not model truth).

## 2. What we already have (don't re-survey)

- **FantasyCalc** is integrated as the market overlay (`src/dynasty_genius/adapters/fantasycalc_adapter.py` + the `market_source.py` `MarketSource` abstraction; 3-stage cache; banned-field sanitization). Confirmed params: `isDynasty=true&numQbs=2&numTeams=12&ppr=1`, TE-premium 0. **A new ADP source should extend the `MarketSource` abstraction, not start from scratch.**
- **Prior findings (carry forward, don't repeat)** from `docs/strategies/Rookie Draft Seed Data.md`:
  - Strict 12T/SF/Full-PPR/non-TEP **per-league** rookie-draft corpus is **not publicly indexable** (~3 partial matches only).
  - **DLF MFL Rookie ADP** = aggregated from *real* MFL rookie drafts (the recommended real-draft proxy); **DLF SF Rookie ADP** = analyst *mocks* (not real leagues); **Sleeper rookie ADP** = Sleeper mocks + live; **KTC** = crowd trade-value (related but distinct).
  - **Reddit robots.txt (2024-07-25)** blocks non-Google crawlers → r/DynastyFF "rate my draft" corpus is not reachable at scale via general search.
  - Sleeper has **no league-search-by-settings**; only known `league_id`/`user_id` access.

## 3. Part A — NFL mock-draft sources (for projected NFL draft capital)

**Goal:** a defensible, aggregatable **projected NFL draft pick/round** per incoming-class prospect, pre-NFL-draft, to feed Engine A for near-class pick valuation.

Per-source questions to answer:
- **Coverage & cadence:** Does it publish way-too-early + in-season mocks for the relevant class (e.g., 2027)? How often updated? How deep (round 1 only, or 2–3 rounds)?
- **Access:** Page-scrape, JSON/API, or manual-only? ToS/robots.txt posture? (Flag anything blocked, à la Reddit.)
- **Format & identity:** Player naming (for our normalized-name join to `prospects_with_outcomes.csv` / prospect_cards), position, projected pick/round.
- **Historical availability:** Are *past-season* mocks retrievable? (Needed to **backtest** the projection — does projected capital predict realized value/actual capital?)
- **Aggregation:** Can we combine ≥3 sources into a consensus range (the class-tracker practice)? How divergent are they?
- **Evidence-hierarchy tier:** mocks are **consensus projection / validated-analyst** tier — never primary truth. Which sources are credible vs. content-farm?

**Candidate sources to evaluate (not exhaustive):** PFF mock/big board; ESPN (Kiper/Miller) and The Athletic (Dane Brugler) where accessible; NFL.com; Drafttek (consensus aggregator); PFN/NFL Mock Draft Database (aggregators); Pro Football Network simulator. Identify which are free/scrapable vs paywalled/manual.

## 4. Part B — dynasty rookie/player ADP sources (for ingestion + calibration supplement)

**Goal:** a dynasty **rookie ADP** (and/or player ADP) feed usable as a market overlay and to supplement the SF-QB calibration corpus.

Per-source questions:
- **Real drafts vs mocks:** Is the ADP from *real* leagues (preferred) or organized mocks? (DLF MFL = real; DLF SF Rookie = mocks.)
- **Settings filterability:** Can it be filtered/confirmed to **12-team Superflex Full-PPR non-TEP** (David's league)? If only blended formats, how large is the TEP/PPR/SF skew?
- **Access:** API/JSON vs page-scrape vs manual; ToS; rate limits; auth.
- **Cadence & seasonality:** Year-round vs spring-only (DLF MFL runs only when rookie drafts occur); update frequency.
- **History:** Multi-year ADP history (for backtesting + the thin calibration corpus)?
- **Granularity:** Aggregate ADP only, or per-draft/per-league? (Per-draft would also strengthen the SF-QB calibration corpus.)
- **License/cost:** Free vs paid; redistribution terms.

**Candidate sources:** DLF MFL Rookie ADP (real); DLF SF Rookie ADP (mocks); Sleeper rookie ADP; FantasyCalc (already integrated — note any rookie-specific endpoint we don't yet use); KeepTradeCut; DynastyNerds; FantasyPros consensus; SFBX/other dynasty ADP. For each, the questions above.

## 5. Evaluation matrix (the research pass should fill this per source)

| Source | A=mock / B=ADP | Real-draft vs mock | Settings match (12T/SF/PPR/non-TEP) | Access (API/scrape/manual) | ToS / robots posture | Cadence & seasonality | History depth | Granularity (aggregate/per-draft) | Cost/license | Fit (1–5) |

## 6. Governance constraints (binding on any eventual build)

- **Overlay / inference-only.** Mock-projected capital + ADP **never** enter Engine A/B training dataframes. Mock capital is an *inference-time projection*; ADP is a *market overlay*. (Constitution: "market data is price discovery, not truth"; "no market-derived feature in model training.")
- **Local-first; no Databricks** for this (per the $10/24hr cap + local-first directive). No scrape-at-scale of blocked sources (Reddit robots.txt).
- **Respect ToS/robots.txt** for every source; prefer official APIs; manual/curated fallback where scraping is disallowed (the seed-fixture pattern).
- **Heavy caveats + `decision_supported=False`** on anything surfaced from projected/market data; banned David-facing verdict language stays out.
- **`MarketSource` abstraction** is the integration point for any ADP feed; one adapter per source, snapshot-before-parse, source-rank/freshness caveats (north-star source-adapter rules).

## 7. Deliverable & non-goals

**Deliverable of the research pass:** the §5 matrix filled per candidate source, plus a one-paragraph recommendation for **each** follow-up — (A) which 3+ mock sources to aggregate for projected NFL capital + how to access them + whether a backtest of the projection is feasible; (B) which ADP feed(s) to ingest (real-draft-derived, settings-matched, accessible, historical) + integration sketch via `MarketSource`.

**Non-goals (out of scope for the research pass):** building either adapter; any model-training use; lifting the frontend HOLD; tuning NOISE_BAND (locked to mid-July 2026). The research only informs David's decision on whether/which to build next.

## 8. Specific questions for the research pass to answer

1. Which **≥3 mock-draft sources** give credible, accessible (API/scrapable, ToS-clean) **2027-class projected NFL draft capital**, and do **historical** mocks exist to backtest the projection?
2. Which **dynasty rookie ADP feed** is **real-draft-derived**, closest to **12T/SF/Full-PPR non-TEP**, accessible, and historically deep — and does it offer **per-draft** granularity (which would also feed the SF-QB calibration corpus)?
3. For each chosen source: exact access method, update cadence, identity/naming for our name-join, license, and the cleanest `MarketSource`-style integration.
4. Any source whose ToS/robots posture **forbids** programmatic use (so we plan a curated/manual fallback instead)?
5. Net recommendation: which follow-up (A near-class projection, or B ADP ingestion) is **more feasible to do first** given the data reality?

## 9. Suggested research roles (multi-agent)

- **Lead research / synthesis:** spine agent (Compass/Codex-style) — gather + fill the matrix + recommend.
- **Supporting:** secondary research agent — corroborate access/ToS/format claims; do **not** let supporting-agent enthusiasm expand scope into buy/sell strategy or lifting governance gates.
- **PM (Gemini):** governance read — confirm overlay-only framing and that no proposed source implies a model-training use.
