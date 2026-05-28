# Increment A (NFL Mock Aggregation) — Research Reconciliation & Go-Forward Decision

**Date:** 2026-05-28
**Author:** Claude Code (reconciliation); reviewed by Codex (technical) + Gemini (governance)
**Inputs (preserved as-received, NOT edited):**
- Brief: `docs/strategies/2026-05-28-increment-a-nfl-mock-aggregation-research-brief.md`
- Report #1: `docs/strategies/Mock aggregation research.md`
- Report #2: `docs/strategies/Mock Agg deep-research-report.md`
- Reviews logged in `docs/agent-ledger/2026-05-27.md`

This doc reconciles two independent web-research reports answering the Increment A brief, plus the Codex + Gemini cockpit reviews of both. **Four-way triangulated** (both reports + both agents converge). The reports themselves are preserved unedited; corrections are recorded here.

## Converged decision (unanimous)

**Increment A is an identity-substrate + backtest-machinery project NOW — NOT a 2027 projected-value product.** Build the machinery to later *test* whether projected NFL capital beats the existing Regime B slot curve; do not ship 2027 projected pick values now. All output stays **overlay/inference-only, `decision_supported=False`**, with a **fail-closed match-rate gate** so a thin/ambiguous signal never emits false precision into Trade Lab. **No mock/market data ever enters Engine A/B training.**

### Build order (per-subsystem go/no-go)
| Subsystem | Verdict | Notes |
|---|---|---|
| **3 — Prospect identity substrate** | **GO — build first** | Hardest new problem; highest cross-class reuse; no time-sensitivity; de-risks everything. |
| **4 — Backtest harness (manual-first)** | **GO — build next** | Two-stage, never conflated. Gated on S3 having shape. |
| **1 — Consensus aggregation** | **DESIGN now, calibrate after Backtest A** | Median/round-tier + abstention gates; no infra cost to design. |
| **2 — Live per-source adapters** | **NO-GO now (defer until permission + maturity gates pass)** | Gated on explicit written permission **and** signal maturity (≈ Dec 2026–Apr 2027); manual-curated versioned JSON is the standing posture. |

## Reconciliation: where the reports differ (Report #2 governs)

1. **ToS / legality (Report #2's harder findings govern).** Report #1 treated the free sources as broadly usable; Report #2 surfaced binding terms that make **automation legally gated for all three**:
   - **NFL.com** — terms expressly prohibit *systematic retrieval to compile a collection/database* (even though `robots.txt` allows `/news/`) → **manual-snapshot only**.
   - **Grinding-the-Mocks (shinyapps.io / Posit)** — terms prohibit scraping/spidering/crawling without written consent → **manual cross-check / methodology benchmark only**.
   - **WalterFootball** — legally **ambiguous** (no current terms/robots affirmatively permitting automation) → **manual-first**.
   - **Net:** there are **not yet three legally + operationally clean automated inputs.** Deferring live adapters is driven by **legal posture + signal immaturity together** — automation requires **explicit written permission AND signal maturity (≈ Dec 2026–Apr 2027)**, not merely a calendar date.
2. **Identity bridge (Codex correction; Report #2 safer).** Report #1 overstates CFBD `athlete_id` ↔ nflverse `cfb_player_id` as a clean pre-draft bridge. **There is no out-of-box pre-draft bridge.** Treat CFBD `athlete_id` as a strong *college-side* anchor only; the nflverse/PFR IDs (`cfb_player_id`, `gsis_id`, `pfr_id`) are *realized-outcome* IDs. S3 must keep **separate nullable source-ID fields** and create an **explicit reviewed bridge at draft time** — not assume the IDs line up.

**Superseded as too-strong (do not carry into the spec):** Report #1's "NFL.com automated fetch permitted" and "CFBD `athlete_id` == nflverse `cfb_player_id`" claims.

## Binding design decisions (from the reconciled reports + reviews)

- **Subsystem 3 scope (substrate-only, per Codex):** (a) source-ID **registry schema** for undrafted prospects with separate nullable IDs (`cfbd_athlete_id`, `cfb_player_id`, later `pfr_id`/`gsis_id`/`sleeper_id`) + aliases/schools/positions/class-year; (b) CFBD roster/player ingestion **or a manual fixture path**; (c) name normalization (nflverse `merge_name` spirit) + reviewable alias table; (d) **fail-closed** candidate matching + human review queue (never auto-match common-name collisions; transfers are a soft disambiguator, not a hard blocker); (e) **bridge-ready** fields for future NFL-side IDs; (f) tests proving **no mock/ADP/market data enters model training**. Abstain rather than project if precision/coverage is weak.
- **Subsystem 4 (two-stage backtest, binding):** **Backtest A** = mock/manual-snapshot → realized NFL draft capital (nflreadr draft truth) — strict `published_date < draft_date`, exclude redraft/post-draft revisions; metrics = overall-pick MAE, round-bucket accuracy, top-36 skill recall, UDFA false-positive rate, coverage-after-abstention, early-pick-weighted error. **Backtest B** = projected-capital → Engine A vs Regime B — only after S3 has an auditable historical bridge **and** Backtest A is good enough by round/position bucket; **abstain** if Backtest A is poor outside top-15/36 rather than manufacture precision.
- **Subsystem 1 (aggregation):** outlier-robust **median** (not mean) of latest eligible pick per analyst; output `projected_pick_median/min/max`, `IQR|MAD`, `n_sources`, `n_unique_analysts`, `staleness_days`, `disagreement_flag`; **round-tier primary** (R1 early/mid/late, R2, R3, Day 3, UDFA). **Abstention gates:** <3 analysts → abstain; 3–4 → round-tier only; exact pick only at ≥5 current analysts + tight dispersion — and even then **exact pick is an internal diagnostic, never David-facing**, until historical MAE supports it.
- **Manual snapshots are still versioned** (raw HTML/text + sidecar metadata: source URL, analyst, mock version, `published_date`, `fetched_at`, `content_hash`, `parser_version`, `parse_status`) — manual-first ≠ unversioned paste-only.
- **Big board ≠ mock draft:** a ranked big board is a discovery/identity surface, never projected NFL capital unless labeled as a distinct source type.
- **Parser caution (WalterFootball):** Charlie Campbell's 2027 page title still reads "2026 NFL Mock Draft" while the body is the 2027 mock — any parser must take year/class from URL/body/update metadata, never the HTML title alone.

## Governance posture (unchanged, reaffirmed)
Overlay/inference-only; `decision_supported=False`; no model-training feed; free-path only (NFLMDDB / PFF never as redistributable feeds); respect ToS/robots; snapshot-before-parse; local-first; frontend HOLD + NOISE_BAND lock untouched.

## Next step
Brainstorm **Subsystem 3 (prospect identity substrate)** — scoped to the (a)–(f) substrate-only shape above — via the cockpit workflow (brainstorm → spec → cockpit review → writing-plans → TDD cockpit build). Subsystems 4 and 1 follow as separate specs; Subsystem 2 stays deferred.
