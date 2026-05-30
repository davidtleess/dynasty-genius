# Step-5a — Historical Market Source Verification (DynastyProcess) — Findings

**Date:** 2026-05-30 · **Type:** read-only source verification (NO DB writes, NO loader, NO imputation) · **Tool:** `scripts/verify_dynastyprocess_source.py` (`verify_source`) · **Tests:** `tests/contract/test_harness_trust_step5a_source_verification.py` (6, GREEN).

**Source:** `github.com/dynastyprocess/data` (`files/values.csv`, `files/db_playerids.csv`) — GPL-3.0. **`source_family = dynastyprocess_ecr_2qb`** / methodology `fantasypros_ecr_consensus`. **This is expert-consensus (FantasyPros ECR), NOT the FantasyCalc trade-market** — a G3 verdict on this source reads as *"beats expert consensus,"* not *"beats the trade market"* (the forward Gate-4 instrument). David approved this substitution (fresh §8.4-extension sign-off, 2026-05-30).

## Result: VIABLE — all four fold dates verify clean

| Target | Commit | Δdays (on-or-before) | value_2qb | crosswalk coverage | matched pools (PICK excluded) | evaluability vs primary-k |
|---|---|---|---|---|---|---|
| 2021-09-08 | `79fee04a` | −5 | ✅ | 99.61% | QB 78, RB 152, WR 202, TE 85 | all **evaluable** |
| 2022-09-08 | `beb24c54` | −6 | ✅ | 99.64% | QB 68, RB 165, WR 229, TE 89 | all **evaluable** |
| 2023-09-08 | `889aa430` | 0 (exact) | ✅ | 99.51% | QB 86, RB 174, WR 229, TE 115 | all **evaluable** |
| 2024-09-08 | `1f17c551` | −2 | ✅ | 100.0% | QB 82, RB 144, WR 196, TE 91 | all **evaluable** |

Primary-k thresholds (Gate B §8.2): QB/TE @12, RB/WR @24 — every position at every date is **far above** its threshold, so no fold defers from the market side (the binding constraint will be our model's own scored universe, not DynastyProcess).

## Integrity checks (all pass)
- **Point-in-time, no look-ahead:** each selected commit is the nearest *on-or-before* the target within ±7 days (git-commit date is intrinsic provenance). 2023 is an exact match.
- **Survivorship (genuine snapshots):** since-retired players present at their then-value — **Roethlisberger 2021 (`value_2qb=222`)**, **Brady 2022 (1129)**, **Rodgers 2023 (1064) / 2024 (376)**. A scrubbed dataset would have dropped the fading vets.
- **Revision guard:** in-file `scrape_date ≤ commit_date` (a later scrape_date = post-hoc revision → fail closed).
- **Crosswalk:** `values.fp_id → db_playerids.fantasypros_id → sleeper_id` at the **era** commit; PICK pseudo-position excluded from player pools (surfaced as `mapped_pick_rows_excluded`).

## Schema discovered (loader spec input)
- `values.csv`: `player,pos,team,age,draft_year,ecr_1qb,ecr_2qb,ecr_pos,value_1qb,value_2qb,scrape_date,fp_id` (quoted; **position col = `pos`**; SF value = `value_2qb`).
- `db_playerids.csv`: crosswalk key = **`fantasypros_id`** → `sleeper_id` (not `fp_id↔fp_id`).
- Retrieval: `git show <SHA>:files/{values,db_playerids}.csv` at the four commits above.

## Recommendation → loader increment (David-gated)
DynastyProcess is a verified, point-in-time-clean, ~100%-crosswalk source for all four dates with ample pools. The **loader** maps each commit's player rows → the W1.4 adapter rows (`sleeper_id`, `value=value_2qb`, `position=pos`, `archive_publish_date=commit_date`, `source=dp_archive`, `updated_at=scrape_date`), feeding `backfill_market_archive` (which re-applies the PIT gates). Then G3 runs and publishes the honest **model-vs-expert-consensus** verdict, labeled as such. **No** smoothing / centered-window / forward-fill / imputation / composite. Any date that ever fails a gate just defers (no false verdict).
