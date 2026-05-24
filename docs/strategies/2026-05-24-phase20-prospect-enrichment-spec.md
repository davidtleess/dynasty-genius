# Phase 20 — Engine A v3 Full Board Activation: QB/RB/WR Enrichment Spec

**Status:** DRAFT — Awaiting David Review  
**Author:** Claude Code  
**Date:** 2026-05-24  
**Predecessor phase:** Phase 19 (TE Head A v3 promoted, 2/3 gates, fully live)

---

## 1. Strategic Objective

Extend the Engine A v3 Head A Ridge architecture from TE to the remaining three positions
(WR, RB, QB) so the full 2026 Rookie Board scores via CFBD-enriched models wherever the
data supports it.

**This spec is grounded in W3 bakeoff failures.** WR and RB both have features in the v3
CSV already; neither passed W3 gates. The spec explains why and defines targeted remediation
for each position. QB has zero CFBD features and the weakest baseline signal; its prospects
are guarded.

---

## 2. Baseline State (from W3 artifact `826e5156`)

| Position | Eligible rows | W3 feature set | W3 result | Root cause |
|----------|---------------|---------------|-----------|------------|
| TE | 62 (after CFBD align) | 5 features, 81–84% coverage | **PASSED 2/3** ✅ | Promoted |
| WR | 73 (aligned) | 8 features, `yprr_college` dark | **0/3 FAIL** ❌ | Signal degraded with current feature set |
| RB | 47 (aligned) | 5 features (`rb_scrimmage_ypg`/`rb_rec_ypg` dropped at 34%) | **0/3 FAIL** ❌ | Feature gap + weak signal on reduced set |
| QB | 38 (aligned) | 3 features = baseline, no enrichment | **SKIPPED** | No CFBD data ingested |

**Key fact:** WR failure was NOT a data coverage issue. ryptpa was included at 89.2% and the
8-feature enriched model was strictly worse than the 3-feature baseline on RMSE (4.45 vs 4.29)
and NDCG (0.783 vs 0.810). Enrichment hurt. Feature multicollinearity is the prime suspect.

---

## 3. Scope and Non-Scope

### In scope for Phase 20

- W1 WR feature redesign: prune collinear metrics, test a trimmed 3–4 feature set
- W2 RB scrimmage data fix: replace games-proxy approach with a direct player-stat games count
- W3 QB CFBD ingestion: college completion %, yards/attempt, TD rate, INT rate (CFBD passing stats)
- W4 bakeoff rerun: same W3 harness, same gates (2/3: RMSE + one rank metric)
- W5 promotion: only positions that pass W4 gates receive new pkl + manifest entry; others remain on v2

### Permanently out of scope

| Feature | Reason |
|---------|--------|
| `yprr_college` (WR yards per route run) | CFBD does not provide per-route-run data at player level. Dark permanently. |
| `qb_epa_per_play` / `qb_cpoe` | Requires PFF or ESPN Advanced Stats. Not in CFBD. Dark permanently. |
| Any market-derived signal (KTC, FC, ADP) | Product Constitution §3: market data is overlay-only, never model input. |
| `te_deep_yard_share` | Already 100% missing in v3 CSV. Phase 19 accepted limitation. |

---

## 4. WR Enrichment Redesign (W1)

### Problem

The W3 WR feature set was too dense and internally collinear:
- `ryptpa` = rec_yds / team_pass_attempts
- `wr_dominator_final` ≈ rec_yds_share (final season)
- `wr_market_share_yds` ≈ rec_yds_share (career)
- `wr_yards_per_reception_career` = efficiency metric

Three of the four content-bearing features are correlated share-of-offense metrics.
With α=50 Ridge and n≈73 aligned training rows, the model cannot disentangle these
signals and likely cross-regularizes toward the 3-feature baseline anyway.

### Proposed W1 feature set (trimmed)

| Feature | Description | Coverage (v3 CSV) | CFBD source |
|---------|-------------|-------------------|-------------|
| `nfl_pick` | Draft position | 100% | v2 baseline |
| `nfl_round` | Draft round | 100% | v2 baseline |
| `final_college_age` | Age proxy | 100% | W2b |
| `wr_breakout_age` | Age at first ≥15% target share | 81.1% | W1 existing |
| `wr_yards_per_reception_career` | Career YPR (efficiency, not volume) | 89.9% | W2b |

**Hypothesis:** Replacing the three correlated share metrics with a single efficiency metric
(`wr_yards_per_reception_career`) and retaining the temporal signal (`wr_breakout_age`) may
reduce collinearity without losing meaningful information. Target: ≥5 features at ≥80% coverage.

**Alternative if trimmed set fails:** Try `wr_rec_tds_per_game_final` as a sixth feature.
This is already in the v3 CSV (coverage TBD at bakeoff time) and captures scoring production
per game — a distinct dimension from efficiency.

### What is NOT proposed

Do not add new CFBD WR features. The existing v3 CSV already has the full set of what
CFBD `receiving` endpoint provides at player level. Adding more receiving features will
increase multicollinearity, not resolve it. The W1 fix is subtraction, not addition.

### CFBD work required for W1

None. All proposed W1 features already exist in `app/data/training/prospects_with_outcomes_v3.csv`.
W1 is a bakeoff harness change — update the WR feature list in `run_head_a_bakeoff.py`.

---

## 5. RB Scrimmage Data Fix (W2)

### Problem

`rb_scrimmage_ypg` and `rb_rec_ypg` are only 34.4% populated (83/233 rows) because the
games-proxy approach in `build_w2b_cfbd.py` fetches team game counts from CFBD `/games`,
which returns no results for FCS and many G5 programs. The bakeoff harness dropped both
features at the 50% coverage threshold.

### Root cause

`load_team_games_count()` queries `/games?year=X&team=Y&seasonType=regular`. CFBD's `/games`
endpoint only covers FBS teams in its default scope. FCS and G5 programs with low CFBD
coverage return empty lists.

### Fix: player-stat games field

CFBD `/stats/player/season` returns a `games` field on each player-stat record (number
of games in which the player accumulated that stat category). For `category=rushing`,
`games` gives the denominator for `rb_scrimmage_ypg`. This removes the need for a separate
team-level game count lookup and works for any program that has player-level data.

**New computation:**

```
rb_scrimmage_ypg = (rushing_yds + receiving_yds) / rushing_games
rb_rec_ypg       = receiving_yds / receiving_games
```

Where `rushing_games` and `receiving_games` come from the `games` field on the rushing
and receiving player-stat records respectively.

**Expected coverage improvement:** From 34.4% → ~85%+ (any player with a rushing stat
record will have a games count). Requires verification after rebuild.

### CFBD work required for W2

- Modify `compute_rb_cfbd_features()` in `scripts/build_w2b_cfbd.py` to:
  1. Accept the per-player `games` field from the already-fetched player-stat records
     (no new API call — `games` is already returned in the player stat JSON)
  2. Remove the separate `load_team_games_count()` call for RBs
  3. Set `rb_scrimmage_ypg = (rush_yds + rec_yds) / rush_games` where `rush_games` > 0
- Update `tests/test_w2b_cfbd.py` with TDD coverage for the new game-count path
- Rebuild `app/data/training/prospects_with_outcomes_v3.csv`

### RB feature set for W4 bakeoff

| Feature | Description | Expected coverage after fix |
|---------|-------------|----------------------------|
| `nfl_pick` | Draft position | 100% |
| `nfl_round` | Draft round | 100% |
| `final_college_age` | Age proxy | 100% |
| `rb_final_dominator` | Final season dominator rating | 91.7% (unchanged) |
| `rb_school_sp_plus` | School strength (SP+) | 92.7% (unchanged) |
| `rb_scrimmage_ypg` | Scrimmage yards per game | ~85% (up from 34%) |
| `rb_rec_ypg` | Receiving yards per game | ~85% (up from 34%) |

---

## 6. QB CFBD Ingestion (W3)

### Baseline situation

QB is the hardest position:
- n=38 eligible training rows (smallest position)
- Baseline RMSE 5.68 (highest), Spearman 0.155 (near zero)
- `model_grade=PROSPECT_D` — current Engine A v2 QB scores carry negative R² caveat
- W3 produced no candidate because enriched features equaled baseline (no CFBD data existed)

### What CFBD can provide

CFBD `/stats/player/season?category=passing` returns per-player:
`passAttempts`, `passCompletions`, `passYards`, `passTDs`, `interceptions`

Computable features:
| Feature | Formula | Interpretation |
|---------|---------|----------------|
| `qb_completion_pct_final` | completions / attempts (final season) | Accuracy |
| `qb_yards_per_attempt_final` | pass_yds / attempts (final season) | Efficiency |
| `qb_td_rate_final` | TDs / attempts (final season) | Scoring production |
| `qb_int_rate_final` | INTs / attempts (final season) | Turnover risk |

### Honest prognosis

n=38 with 4 new features → 7 total features. This is a HIGH-RISK enrichment with a real
probability of failure:

1. **Sample size**: 38 eligible rows across 4 folds means ~9–10 test rows per fold.
   RMSE estimates are unstable at this scale.
2. **College QB stat variance**: College offenses differ enormously by scheme
   (Air Raid completion % ≠ run-heavy completion %). Raw passing stats may not
   transfer meaningfully to NFL `best3of4_ppg`.
3. **Baseline signal**: Spearman 0.155 means even the draft-capital baseline barely
   correlates with NFL production. There may be no learnable signal here.

**Recommendation:** Attempt W3 QB ingestion as a bounded experiment with acceptance
that the most likely outcome is SKIP or FAIL. Do not delay WR/RB work waiting for QB.

### CFBD work required for W3

- New `compute_qb_cfbd_features()` in `scripts/build_w2b_cfbd.py` using
  `/stats/player/season?category=passing` (same pattern as receiving/rushing fetch)
- Features: `qb_completion_pct_final`, `qb_yards_per_attempt_final`, `qb_td_rate_final`,
  `qb_int_rate_final` + corresponding `_missing` and `_source` flags
- Prefetch passing TPA (already cached as `passAttempts` from team stats — reuse)
- Update tests + rebuild v3 CSV

---

## 7. Model Architecture (unchanged from Phase 19)

All three positions use the identical harness proven in Phase 19:

```
Pipeline([StandardScaler(), Ridge()])
```

- **α sweep**: [0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0] — best per fold via RidgeCV
- **Target variable**: `best3of4_ppg` (PPR PPG, best 3 of first 4 NFL seasons)
- **Training filter**: `censored_incomplete_arc == 0` AND all features non-null
- **Walk-forward harness**: same 4-fold temporal split from W3 (train max year → test year)
- **Gate thresholds** (2/3 required to pass):
  - RMSE improvement vs. row-aligned baseline ≥ 7% (`rmse_improvement_pct >= 0.07`)
  - Mean-fold Spearman: candidate > aligned baseline
  - Mean-fold NDCG@10: candidate > aligned baseline
- **Feature retention**: features dropped if < 50% populated in the aligned training fold
- **LOOO guard**: features with > 25% coefficient drift are flagged; candidates with flagged
  features cannot pass even if gate metrics clear

**No new architecture work required for Phase 20.** `scripts/run_head_a_bakeoff.py` and
`tests/test_head_a_bakeoff.py` are reused unchanged.

---

## 8. Workstream Structure

| Workstream | Work | Dependency |
|------------|------|------------|
| W1 | WR feature redesign: update bakeoff feature list, run W4 harness, review results | None — no new CFBD ingestion |
| W2 | RB games-count fix: modify `build_w2b_cfbd.py`, rebuild v3 CSV, run W4 harness | None (parallel with W1) |
| W3 | QB CFBD ingestion: new passing features, rebuild v3 CSV, run W4 harness | W2 (shares rebuild) |
| W4 | Codex review of W1/W2/W3 bakeoff results | W1, W2, W3 |
| W5 | Promotion: pkl serialization + manifest update for each passing position | W4 Codex clearance |
| W6 | Prospect card enrichment (2026 class) for promoted positions | W5 |
| W7 | Universe batch refresh | W6 |

**W1 can start immediately** — no new data, just a bakeoff rerun with a trimmed WR feature list.

---

## 9. Promotion Decision Criteria

Each position is evaluated independently. A position is eligible for promotion only if:

1. At least one candidate (Ridge or GBT) passes 2/3 gates in W4
2. Codex review finds no implementation defects (aligned rows, OOF metrics, LOOO guard)
3. David explicit approval

Positions that fail W4 remain on Engine A v2 (draft capital only) indefinitely. There is
no automatic fallback promotion — if a position fails, its v3 entry is omitted from
`v3_manifest.json` and `score_prospect_v3()` returns `None` for that position (graceful
degradation to v2 already in place from Phase 19 W5).

---

## 10. Governance Invariants

All Phase 19 invariants carry forward unchanged:

| Invariant | Status |
|-----------|--------|
| `decision_supported = False` on all surfaces | Required, always |
| Market data overlay-only (never model input) | Required, always |
| `latest.json` and `engine_b/v2_manifest.json` unchanged by Head A promotions | Required, always |
| Head B dark (W4 null result; not revisited in Phase 20) | Maintained |
| CFBD_API_KEY in `.env`, never committed | Required, always |
| Model pkl + manifests gitignored (local-only) | Required, always |
| Local-first; Databricks requires David's manual override | Required, always |

---

## 11. Open Decisions for David

The following require David's explicit direction before implementation begins:

**D1 — WR feature set**
> Proposed: trim to `[nfl_pick, nfl_round, final_college_age, wr_breakout_age, wr_yards_per_reception_career]`.
> Alternative: keep the full 8-feature set and accept that WR v3 may not promote.
> Recommendation: try trimmed set first (W1 is low-cost — no data fetch needed).

**D2 — QB attempt vs. defer**
> QB has n=38, Spearman≈0.155 baseline, and no existing CFBD features.
> A Phase 20 QB enrichment attempt is a bounded experiment likely to fail.
> Recommendation: include QB in Phase 20 as a low-priority W3 item but do not block
> WR/RB progress waiting for it. Communicate that QB v3 promotion probability is low.

**D3 — W1 start timing**
> W1 WR bakeoff rerun requires no new data and can start the moment this spec is approved.
> Proceed immediately after approval?
