# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Engine A v2 enrichment pipeline — Phase 1 complete. PlayerProfiler under corrected gate review (Path B remains operative for model promotion).

## Current Sprint Objective

Engine A v2: validate which enrichment sources deserve model-input status before expanding rookie scoring.

- Task 1 (Source Registry): complete — 12/12 tests passed.
- Task 2 (CFBD enrichment): hygiene patch committed (e14dfd7). CFBD backtest run (Task 4 below).
- Task 3 (PlayerProfiler probe): Path B remains operative — PP is NOT promoted to model input. Original 0% probe is superseded by Gemini's 2-step scraper. Remediation removed the imputed/mislabeled fields and regenerated a clean v2 artifact, but corrected coverage still does not clear the 80% gate. Status: **clean Path B / context_signal**.
- Task 4 (CFBD-only backtest): complete — promotion NOT warranted (CFBD features did not improve Model A on held-out set).
- Tasks 5–8: deferred to Phase 2 (post Phase 1 gate resolution).

## Latest Activity

- Codex (2026-05-11): Completed PP remediation takeover.
  - Removed `yprr`/`imputed_yprr` from the regenerated enriched CSV; no `imputed_median` provenance remains.
  - Fixed hidden `year_stats` typo in `scripts/enrich_training_data.py` and kept PP `Yards Per Team Targets` out of the training artifact.
  - Added narrow deterministic name normalization; no search/network fallback was added.
  - Corrected gate summary: `target_share=608/874 (69.6%)`, `breakout_age WR/TE=375/515 (72.8%)`, `speed_score skill=652/748 (87.2%)`.
  - Relevant tests: 40 passed, 1 skipped.
- David (2026-05-11): Corrected PP status. Gemini's scraper produced real PP artifacts: `target_share` coverage 580/874 = 66.4% — above the old 0% but still below the 80% gate. Current v2 CSV has two governance violations: (1) `yprr` imputed to 1.85 on 258 WR/TE rows (`source_yprr='imputed_median'`); (2) `Yards Per Team Targets` is labeled as `yprr`, which is not verified yards per route run. Path B governance decision preserved.
- Codex (2026-05-11): Verified artifact state. Documented violations in ledger. `pp_id_map.json` and `pp_stats_cache.json` preserved. Gate tests need to be rerun against the 2-step retrieval path; existing `pp_probe_results.json` reflects stale failed probe.
- Claude Code (2026-05-10, Session 3): Phase 1 execution complete. Source registry committed. CFBD backtest run — no promotion.
- Codex (2026-05-10): Ran original PP probe (found=0, parse_error=874). Gate test selected Path B. Engine A contract removed PP-only fields.

## Open Blockers

- PP remains below the 80% promotion gate after clean remediation. Do not run a PP-inclusive backtest or promote PP unless David explicitly requests another identity-matching pass or accepts a revised gate.
- Post-draft PR cleanup (PRs A/B/C) can resume once this remediation patch is reviewed/committed.
- PR #10 (engine-a/historical-enrichment): open, marked non-mergeable. Deferred.

## Next Recommended Work

1. Review and commit PP remediation patch if accepted.
2. Replan Phase 2 around context/risk layers and validation, not automatic source promotion.
3. Post-draft: execute PR A (Data Foundation) and PR B (Rookie Board) after the remediation patch lands.

## Branch / Worktree Notes

Active branch: engine-a/v2-enrichment-pipeline (up to date with origin).
PR #10 (engine-a/historical-enrichment): open, non-mergeable, deferred.
Governance branch codex/governance-seal: superseded by main's sealed governance (6d378d0).
