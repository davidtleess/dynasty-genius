# Phase 24 — Draft Pick Valuation: Closeout

**Date:** 2026-05-26
**Status:** Ready-now tier COMPLETE and merged on `main`. Two follow-ups remain DEFERRED pending external data research.
**Specs:** [`docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md`](../superpowers/specs/2026-05-26-draft-pick-valuation-design.md), [`…regime-a-drafted-class-pick-valuation-design.md`](../superpowers/specs/2026-05-26-regime-a-drafted-class-pick-valuation-design.md), [`…sf-qb-knob-calibration-design.md`](../superpowers/specs/2026-05-26-sf-qb-knob-calibration-design.md)
**Reopening decision:** [`2026-05-26-future-pick-valuation-reopening-decision.md`](2026-05-26-future-pick-valuation-reopening-decision.md)

## What shipped

Dynasty rookie draft picks now carry an **xVAR** value, grounded in a historical slot curve rather than an invented currency.

- **Curve** — `app/data/valuation/draft_pick_value_curve_v1.json`, built by `scripts/build_draft_pick_value_curve.py`. Bridge: the first-36 skill players in NFL draft order ≈ a 36-slot FF rookie board; realized `y24_ppg` → DVS → xVAR per slot over mature classes 2015–2022.
- **Regime A (drafted-class board valuation)** — when a prospect board + exact slot (or round) is known, value the pick from the board directly (`_value_pick_from_prospect_board`); otherwise fall back to the historical curve. `PickValue.valuation_regime` records which path was taken.
- **Pick integration** — future picks are reconstructed and valued (`sleeper_universe.reconstruct_future_picks`, `PICK_VALUE_STATUS = "active_v1_historical"`) but **excluded** from `starter_weighted_xvar` (coverage flag `future_picks_present_valued_excluded_from_strength`): a pick is latent value, not current roster strength.
- **`source.method` cleanup** — provenance string on the curve artifact now names the bridge, the Option-A floor, and the tiering, so the artifact is self-documenting.

## Two decisions worth remembering

1. **Option A — option-value floor (the key "be right, not fast" moment).** A first build produced *negative* round-2/3 xVAR from real data. We paused rather than ship. Consensus (Codex + Gemini, David-approved): a draft pick is a **call option** — its downside is "the player busts," which floors realized value at 0, not below. So per player `priced_xvar = max(0, raw_xvar)`, and a slot's expected value is the **mean of priced** samples (both `raw_samples` and `priced_samples` retained for audit). This stops busts from dragging late picks negative while keeping the upside intact.
2. **SF-QB knob calibration → K = 0 (an honest null result).** The curve assumes "FF rookie-draft order ≈ NFL skill-position order," weakest for QBs in Superflex. `scripts/calibrate_sf_qb_knob.py` measured `promotion = nfl_skill_rank − ff_slot` across 6 real SF rookie drafts (David's Sleeper league chain + 3 seed drafts), 27 matched QBs / 3 unmatched. **Median promotion = 0.0** → `K = clamp(round_half_up(median), 0, 3) = 0`. So `sf_qb_promote_slots` stays `0` and the curve is unchanged: in this (thin) corpus the assumption holds for QBs. The knob is re-runnable as the league accrues drafts; artifact carries `sf_qb_calibration_thin_sample`.

## Governance posture (unchanged)

- Pick values are an NFL-derived historical **expectation**, never a market-measured price and never an Engine A/B training input. All pick output stays `decision_supported=False`; banned David-facing verdict language stays out.
- Read-only Sleeper (public API, no auth, no Databricks) for the calibration; no writes to the league.
- Frontend remains on the Phase 12 HOLD.

## Deferred follow-ups (gated on external-data research)

The research brief [`docs/strategies/2026-05-26-mocks-and-adp-sources-research-brief.md`](../strategies/2026-05-26-mocks-and-adp-sources-research-brief.md) scopes the data needed for:

- **(A) Near-class projection** — value a *current* rookie class's picks before its NFL draft, via aggregated mock NFL draft capital → Engine A.
- **(B) ADP ingestion** — a dynasty rookie/player ADP overlay via the `MarketSource` abstraction, which would also supplement the thin SF-QB calibration corpus.

A decision-rule / accept-floor layer (turning pick xVAR into trade-comparison signal) remains explicitly gated on the valuation being trusted, and is **not** started. Pick appreciation over time is deprioritized.
