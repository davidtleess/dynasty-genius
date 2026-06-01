# Task C (Trade-Market Baseline) — Emotional-Market Data Sourcing Verification

**Result: NOT FOUND — Task C-as-conceived is data-blocked. No fabrication; the forward FantasyCalc collection is the only integrity-clean path.**

- **Date:** 2026-06-01
- **Initiative:** Harness Trust Completion → Task C (the *real* mispricing test: does Engine B beat the **emotional** trade market over time, distinct from the *rational* expert consensus that G3 + Task B already measured?).
- **Lineage:** follows the 2026-05-30 data-sourcing research brief (`docs/strategies/2026-05-30-historical-market-archive-sourcing-research-brief.md`) and three research outputs (`docs/strategies/{Point-in-Time Dynasty Superflex Value Archives…, Dynasty Market Value Data Sourcing, deep-research-report-Dynasty data backfill}.md`). See [[project_w1_needs_historical_fc_archive]].

## What Task C needs

A **point-in-time** dynasty-**Superflex** (`numQbs=2`, 12-team, `ppr=1`) **emotional trade-market** value archive (FantasyCalc or KeepTradeCut — crowd/transaction-derived, *not* expert consensus) for four dates (2021/2022/2023/2024-09-08, ±7d), passing the strict integrity bar: as-published (not recomputed), survivorship-safe, intrinsically dated, no live-endpoint reconstruction.

## Why the existing archive does not satisfy it

`app/data/fc_snapshots.db` contains only `source='dp_archive'` (DynastyProcess `value_2qb`) across the four dates. DynastyProcess values are **FantasyPros-ECR-derived** (`Value = 10500·e^(ECR·−0.0235)`) — **rational expert consensus**, the exact instrument G3 (`dynastyprocess_ecr_2qb`) and the Task B subpopulation study already evaluated ("model ≈ rational consensus"). Re-using it answers a question already answered; it is **not** the emotional market Task C targets.

## Leads checked (against the integrity bar)

| Lead | Obtainable? | Integrity / fit | Conclusion |
|---|---|---|---|
| DynastyProcess `value_2qb` (git history) | Yes | Clean PIT, but **ECR = rational consensus** | Redundant — not the emotional market |
| **Dynasty Daddy** (KTC → Postgres, Sleeper-keyed) | **No** | README: data scraped to a **private** Postgres; **no public dump / CSV / API**. KTC baseline is **.5-PPR** (format mismatch) | **Not obtainable** |
| **FantasyCalc** (preferred source) | **No** (for the 4 dates) | Public API (`/values/current`) is **current-only**; only a rolling ~1-year UI window; a FantasyCalc commenter says data exists back to 2021 but it is **not** a documented public export | **No verified, documented, integrity-passing public historical export for the four required dates** |
| FantasyCalc via Wayback (JSON captures) | Unverified | Research rates captures **sparse / fragile**; `web.archive.org` was **not fetchable** from this environment, so not verifiable inline | Low-confidence; deferred |
| Community KTC+FC sheet (Reddit, u/325xi5mt, "daily since 2020") | Located/documented (cited in the sourcing research), not directly retrieved here | Community-maintained = lowest integrity (survivorship / as-published / intrinsic dating unverifiable); KTC .5-PPR mismatch | **Rejected/deferred pending integrity verification** (located but unvetted; not "missing") |

## Conclusion

No **obtainable, integrity-passing** historical **emotional-market** dataset exists for the four dates. This is the **"not found is a valid answer"** outcome the research brief explicitly sanctioned. Substituting any unverified or rational-consensus source for the emotional market would be the precise false-confidence failure (a survivorship-scrubbed or relabeled "history" making a model look prophetic) that the trust harness exists to prevent — so **none is substituted**.

**Caveat on this verification:** it was *focused*, not exhaustive. A deep Wayback CDX probe of FantasyCalc `/values/current?numQbs=2&isDynasty=true` JSON captures near the four dates (which research rated low-confidence) could in principle recover a date or two, but requires `archive.org` access this environment lacks; it is deferred to a web-enabled research pass or a manual check, not relied upon.

## Recommended path (forward, not backward)

The only integrity-clean route to a real **model-vs-emotional-market** verdict is the system's **own forward FantasyCalc collection** — `scripts/snapshot_fantasycalc.py` (W2a: immutable daily `fc_native`, verify-or-raise), already built. Starting its scheduler begins the **Gate-4 clock**; a forward backtest becomes possible once enough point-in-time history accrues (~6+ months). Recommended actions:

1. **Start the forward clock:** David `launchctl load`s the W2a daily-snapshot scheduler so genuine point-in-time `fc_native` emotional-market values begin accruing now. (David-gated machine action.)
2. **Shelve historical Task C** as data-blocked; revisit when the forward `fc_native` series is long enough to backtest, or if a verified Wayback/community emotional-market archive is later sourced.
3. **No model/training change; no fabricated history.** Frontend HOLD intact; `decision_supported` unaffected.

## Provenance

- Verification method: README/API inspection (Dynasty Daddy, FantasyCalc) + targeted web search (community sheet); `web.archive.org` CDX unfetchable from this environment (Wayback path deferred).
- No data was loaded, fabricated, or substituted. `fc_snapshots.db` unchanged (still `dp_archive` only).
