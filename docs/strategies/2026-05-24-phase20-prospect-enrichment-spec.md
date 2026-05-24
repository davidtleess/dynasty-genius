# Phase 20 — Engine A v3 Full Board Activation: QB/RB/WR Enrichment Spec

**Status:** REVISED DRAFT v2 — Codex review addressed; awaiting David approval  
**Author:** Claude Code  
**Date:** 2026-05-24  
**Predecessor phase:** Phase 19 (TE Head A v3 promoted, 2/3 gates, fully live)  
**Revision history:**  
- v1: Initial draft  
- v2: Codex review applied — RB games-field claim corrected, QB contract reconciled to
  existing adapter, EPA/CPOE reclassified, volume gates added, post-rebuild reporting added

---

## 1. Strategic Objective

Extend the Engine A v3 Head A Ridge architecture from TE to WR, RB, and QB wherever the
data supports promotion. Every position is treated as an independent experiment; failure to
pass gates at any position is an acceptable outcome and leaves v2 active for that position.

This spec is grounded in the Phase 19 W3 bakeoff artifact `826e5156` — not hypothesis.
WR and RB both have features in the v3 CSV already; neither passed gates. QB has no CFBD
features. The spec explains each failure mode and defines a targeted, bounded remediation.

---

## 2. Baseline State (from W3 artifact `826e5156`)

| Position | Eligible rows | W3 feature set | W3 result | Root cause |
|----------|---------------|---------------|-----------|------------|
| TE | 62 (aligned) | 5 features, 81–84% | **PASSED 2/3** ✅ | Promoted (Phase 19) |
| WR | 73 (aligned) | 8 features, `yprr_college` dark | **0/3 FAIL** ❌ | Collinear share metrics degraded signal |
| RB | 47 (aligned) | 5 features (`rb_scrimmage_ypg`/`rb_rec_ypg` dropped at 34%) | **0/3 FAIL** ❌ | Feature gap; reduced set also failed |
| QB | 38 (aligned) | baseline only — no CFBD data | **SKIPPED** | No ingestion built |

**WR key finding:** Enrichment hurt. RMSE increased 4.29 → 4.45 with the 8-feature set
(ryptpa at 89.2%). Three of four content features measure the same dimension (share of
team passing game). Multicollinearity, not coverage, is the root cause.

---

## 3. Scope and Non-Scope

### In scope for Phase 20

| Workstream | Scope |
|------------|-------|
| W1 — WR redesign | Trim collinear share metrics; bakeoff rerun (no new CFBD fetch) |
| W2 — RB denominator fix | **BLOCKED** pending denominator path decision (§5) |
| W3 — QB ingestion | Wire `cfbd_qb_adapter.py` into `build_w2b_cfbd.py`; rebuild CSV |
| W4 — Bakeoff | Same harness, same gates; positions evaluated independently |
| W5 — Promotion | Per-position pkl + manifest; only gate-passing positions promoted |
| W6 — Card enrichment | 2026 class cards for promoted positions |
| W7 — Universe refresh | Full league-intelligence artifact chain after W6 |

### Permanently dark — never a model input

| Feature | Reason |
|---------|--------|
| `qb_epa_per_play` | Requires play-by-play EPA calculation. CFBD `/ppa/` is a different,
CFBD-proprietary metric (Predicted Points Added) — not EPA/play. A proper EPA/play
ingestion would require a separate PBP/advanced-stat workstream. Out of scope for Phase 20. |
| `qb_cpoe` (completion % over expected) | Not exposed by CFBD API at player level.
Requires PFF or ESPN Advanced Stats. Dark permanently. |
| `yprr_college` (WR yards per route run) | CFBD has no per-route-run data at player level.
Dark permanently. |
| `te_deep_yard_share` | 100% missing in v3 CSV. Phase 19 accepted limitation. |
| Any KTC / FantasyCalc / ADP / FantasyPros / DynastyNerds value | Product Constitution §3:
market data is overlay-only, never model input. Validated at every rebuild. |

### Classification of CFBD PPA and WEPA

`cfbd_qb_adapter.py` exposes `ppa` (via `/ppa/players/season`) and `wepa` (via
`/wepa/players/passing`). These are **not** EPA/play and **not** CPOE:

- **PPA** is CFBD's proprietary season-level predicted points metric — structurally different
  from snap-level EPA. Coverage and era-stability are unvalidated in our training window.
- **WEPA** (Win Expected Points Added) is an even more exotic metric from a separate endpoint.
  Coverage is unknown.

Both are **dark in Phase 20**. If a future spec proposes including them, a coverage probe
and era-stability analysis must precede any bakeoff trial.

---

## 4. WR Enrichment Redesign (W1)

### Problem

Three of the four W3 WR content features are correlated share-of-offense metrics:
- `ryptpa` = rec_yds / team_pass_attempts
- `wr_dominator_final` ≈ rec_yds_share (final season)
- `wr_market_share_yds` ≈ rec_yds_share (career)

With n≈73 aligned rows and α=50 Ridge, the model cannot disentangle these signals.
The enriched model cross-regularized toward the 3-feature baseline and degraded.

### Proposed W1 feature set (trimmed)

| Feature | Description | v3 CSV coverage | Action |
|---------|-------------|-----------------|--------|
| `nfl_pick` | Draft position | 100% | Keep (baseline) |
| `nfl_round` | Draft round | 100% | Keep (baseline) |
| `final_college_age` | Age proxy | 100% | Keep (baseline) |
| `wr_breakout_age` | Age at first ≥15% target share | 81.1% | Keep — timing signal, not share |
| `wr_yards_per_reception_career` | Career YPR — efficiency only | 89.9% | Keep — different dimension |
| `ryptpa` | Rec yds / team pass attempts | 89.2% | **Drop** — collinear with dominator |
| `wr_dominator_final` | Final-season share | 89.9% | **Drop** — collinear |
| `wr_market_share_yds` | Career share | 89.9% | **Drop** — collinear with dominator_final |

**Result:** 5-feature set at ≥81% coverage on all included features. Target is ≥2 non-null
features beyond the 3-feature baseline.

**No fallback feature is specified.** `wr_rec_tds_per_game_final` cannot be used —
`build_w2b_cfbd.py` permanently stubs it because CFBD receiving player-season records do not
return a games count (same root cause as the RB denominator problem in §5). No other non-game-
denominator WR feature with validated coverage is available in the v3 CSV beyond those already
in the proposed set. If the 5-feature set fails W4 gates, WR remains on Engine A v2.

### CFBD work required

None. All W1 features exist in `app/data/training/prospects_with_outcomes_v3.csv`. W1 is a
bakeoff harness change only: update the WR feature list in `scripts/run_head_a_bakeoff.py`.

**W1 can start immediately** after D1 approval.

---

## 5. RB Denominator Fix (W2) — BLOCKED

### Problem

`rb_scrimmage_ypg` and `rb_rec_ypg` were dropped in W3 at 34.4% coverage because the
games-proxy approach fails for FCS/G5 programs. The reduced 5-feature set also failed all
gates.

### Codex finding — games field does not exist in CFBD player-stat records

The Phase 20 v1 spec proposed using a `games` field from CFBD `/stats/player/season`
records to compute per-game denominators. **This is wrong.** CFBD rushing/receiving records
have the schema:

```
['season', 'playerId', 'player', 'position', 'team', 'conference', 'category', 'statType', 'stat']
```

No `games` field is present. `build_w2b_cfbd.py` lines 261–263 and 287–289 already document:
*"CFBD /stats/player/season returns CAR, LONG, TD, YDS, YPC for rushing — 'G' (games) is
not returned by this endpoint in practice."*

### Two valid paths — requires David's decision (D4)

**Option A — Live schema probe before W2 approval**

Before any W2 implementation begins, probe the live CFBD API to confirm whether `G` ever
appears in rushing/receiving stat records for any year in the training window (2013–2024).
If `G` is found: update the implementation to read it directly from player records and
document which years/endpoints return it.
If `G` is not found: pivot to Option B.

Cost: one bounded script to sample 3–5 cached years and one live API call.

**Option B — Replace YPG with deterministic rate features (no games denominator)**

Remove `rb_scrimmage_ypg` and `rb_rec_ypg` from the spec entirely. Replace with
per-carry and per-reception efficiency metrics that use rushing attempts and receptions
as denominators — both available in the existing CFBD stat records:

| New feature | Formula | Denominator | Coverage expectation |
|-------------|---------|-------------|----------------------|
| `rb_yards_per_carry_final` | `rush_yds / rush_att` (final season) | `CAR` statType (already fetched) | ~90% (any player with ≥ min carries) |
| `rb_yards_per_reception_career` | `career_rec_yds / career_rec` | `REC` statType (already fetched) | ~75–80% |

Both denominators come from data already fetched by the existing
`_pivot_rushing()` / `_pivot_receiving()` calls — **no new API calls required**.

These features are analogous to `te_yards_per_reception_career` (the TE v3 efficiency
feature that contributed to the 2/3 gate pass) and do not require a games count.

**Recommendation:** Option B. Eliminates a fragile external dependency, is fully
deterministic, and reuses existing cache infrastructure.

**W2 remains blocked until David approves D4.**

### RB feature set under Option B

| Feature | Description | Expected coverage | Source |
|---------|-------------|------------------|--------|
| `nfl_pick` | Draft position | 100% | baseline |
| `nfl_round` | Draft round | 100% | baseline |
| `final_college_age` | Age proxy | 100% | W2b |
| `rb_final_dominator` | Final-season dominator rating | 91.7% | W2b existing |
| `rb_school_sp_plus` | School strength (SP+) | 92.7% | W2b existing |
| `rb_yards_per_carry_final` | Rush YPC final season (≥ volume gate) | ~90% | W2b new |
| `rb_yards_per_reception_career` | Rec YPR career (≥ volume gate) | ~75–80% | W2b new |

### Minimum volume gates for RB (§8 applies)

- `rb_yards_per_carry_final`: require `rush_att_final ≥ 50` before setting non-null
- `rb_yards_per_reception_career`: require `career_rec ≥ 10` before setting non-null

---

## 6. QB CFBD Ingestion (W3)

### Baseline situation

- n=38 eligible training rows (smallest position)
- Baseline RMSE 5.68, mean-fold Spearman 0.155 (near-zero)
- `model_grade=PROSPECT_D` already on all v2 QB scores
- W3 bakeoff skipped QB — enriched features equaled baseline (no CFBD ingestion existed)

### Adapter contract (existing)

`src/dynasty_genius/adapters/cfbd_qb_adapter.py` already exists and exposes
`fetch_qb_college_stats()`, which returns:

```python
QB_CFBD_FEATURES = [
    "completion_pct",      # completions / attempts (decimal, 0–1)
    "yards_per_attempt",   # passing yards / attempts
    "td_int_ratio",        # passTDs / max(INTs, 1)  — combined ratio, not separate rates
    "sack_rate",           # sacks / (pass_attempts + sacks)
    "all_purpose_yards",   # passing_yds + rushing_yds
    "passing_yards_share", # player_pass_yds / team_net_pass_yds
    "ppa",                 # CFBD PPA — dark in Phase 20 (§3)
    "wepa",                # CFBD WEPA — dark in Phase 20 (§3)
    "rushing_yards",       # raw rushing yards
    "rushing_tds",         # rushing TDs
]
```

### Feature contract for build_w2b_cfbd.py integration

The implementation path is to add `compute_qb_cfbd_features()` to `build_w2b_cfbd.py`
that calls `fetch_qb_college_stats()` and maps its output to v3 CSV column names.

**v3 CSV column names and mapping from adapter:**

| v3 CSV column | Adapter key | Notes |
|---------------|-------------|-------|
| `qb_completion_pct_final` | `completion_pct` | Decimal (0–1). Volume gate: ≥100 pass_attempts. |
| `qb_yards_per_attempt_final` | `yards_per_attempt` | Volume gate: ≥100 pass_attempts. |
| `qb_td_int_ratio_final` | `td_int_ratio` | passTDs / max(INTs,1). **Not** separate td_rate / int_rate. Volume gate: ≥100 pass_attempts. |
| `qb_sack_rate_final` | `sack_rate` | Volume gate: ≥100 pass_attempts. |

**Why not `qb_td_rate_final` / `qb_int_rate_final` separately:** The Phase 20 v1 spec
proposed these two features. The adapter does not expose them individually — it returns
`td_int_ratio` as a combined ratio. Splitting them would require raw `passTDs` and
`interceptions` counts, which would mean modifying the adapter contract. Keeping `td_int_ratio`
intact is the correct implementation path without adapter surgery.

**Features explicitly excluded from Phase 20 QB contract:**

| Adapter key | Why excluded |
|-------------|-------------|
| `ppa` | CFBD-proprietary metric; not EPA/play; coverage unvalidated (§3) |
| `wepa` | Exotic metric; coverage unvalidated (§3) |
| `all_purpose_yards` | Raw volume; not normalized; multicollinear with pass_yds / pick |
| `passing_yards_share` | Requires team net passing yards from a second endpoint call; fragile |
| `rushing_yards` / `rushing_tds` | Scrambler signal is real but n=38 makes 8-feature QB model high-risk |

**Recommended Phase 20 QB feature set:** 4 features — `qb_completion_pct_final`,
`qb_yards_per_attempt_final`, `qb_td_int_ratio_final`, `qb_sack_rate_final`.

### Implementation path for build_w2b_cfbd.py

1. **Extend `cfbd_qb_adapter.py` to expose `pass_attempts`** (Option A — recommended):
   The adapter already fetches `/stats/player/season?category=passing` at line 135, which
   returns `ATT` statType records. Parse the `ATT` row for the player's final season and
   add `"pass_attempts": <int>` to the return dict of `fetch_qb_college_stats()`. This
   keeps all QB CFBD parsing inside the adapter boundary; `build_w2b_cfbd.py` never
   re-parses raw CFBD records directly.

   **Required TDD (must be written before extending the adapter):**
   Add a test in `tests/test_cfbd_qb_adapter.py` (or the equivalent adapter test file)
   that asserts `fetch_qb_college_stats()` returns `"pass_attempts"` as an integer key
   in its result dict when passing records contain an `ATT` statType row.
   Watch it fail (adapter currently returns no such key). Then add the parse.

2. Add `compute_qb_cfbd_features(name, final_year, api_key)` in `build_w2b_cfbd.py`
   that calls `fetch_qb_college_stats()` and maps the four contracted features
3. Apply volume gate: if `result["pass_attempts"] < 100`, set all four features
   `_missing=1` and `_source="below_volume_gate"` — `pass_attempts` is the `ATT`
   statType value returned by the extended adapter (step 1 above)
4. Emit `_missing` and `_source` flags per the existing pattern
5. Wire into `main()` — same fetch-and-cache pattern as WR/RB/TE
6. TDD: write failing tests first per the existing `tests/test_w2b_cfbd.py` structure

### Name matching

The training CSV has `pfr_player_name`. The adapter takes `player_name` directly.
Use the existing `_norm_name()` normalizer from `build_w2b_cfbd.py` to match against
CFBD player records — same approach used for WR/RB/TE name matching.

### Honest prognosis

n=38 eligible rows, 4 folds, ~9–10 test rows per fold. RMSE estimates at this scale
are unstable. Even the current draft-capital baseline barely correlates with NFL QB output
(Spearman 0.155). **Most likely outcome: FAIL or SKIP.** This is acceptable — QB v2 remains
active and `score_prospect_v3()` gracefully falls through to v2 for any position without a
v3 contract.

Do not delay W1 (WR) or W2 (RB) work waiting for W3 (QB). QB is the lowest-priority workstream.

---

## 7. Model Architecture (unchanged from Phase 19)

```
Pipeline([StandardScaler(), Ridge()])
```

- **α sweep:** [0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0] — best per fold via RidgeCV
- **Target variable:** `best3of4_ppg`
- **Training filter:** `censored_incomplete_arc == 0` AND all candidate features non-null
- **Walk-forward:** same 4-fold temporal split (train max year → test year)
- **Gates (2/3 required):** RMSE improvement ≥7% vs. row-aligned baseline; mean-fold
  Spearman candidate > baseline; mean-fold NDCG@10 candidate > baseline
- **Feature retention:** drop if <50% populated in aligned training rows
- **LOOO guard:** features with >25% coefficient drift quarantine any gate-passing candidate

`scripts/run_head_a_bakeoff.py` and `tests/test_head_a_bakeoff.py` are reused unchanged.

---

## 8. Minimum Volume Protection Gates

Rate and ratio features must not be computed from trivially small samples. The following
thresholds apply at ingestion time in `build_w2b_cfbd.py`. Rows failing a threshold have
the feature set to null with `_missing=1` and `_source="below_volume_gate"`.

| Feature | Denominator | Denominator source | Minimum threshold | Rationale |
|---------|-------------|-------------------|-------------------|-----------|
| `qb_completion_pct_final` | pass attempts (final season) | `ATT` statType from `/stats/player/season?category=passing` — returned by extended `fetch_qb_college_stats()` as `pass_attempts` | ≥ 100 | Starter-level sample; avoids wildcard/backup seasons |
| `qb_yards_per_attempt_final` | pass attempts (final season) | Same as above | ≥ 100 | Same |
| `qb_td_int_ratio_final` | pass attempts (final season) | Same as above | ≥ 100 | Same |
| `qb_sack_rate_final` | pass attempts + sacks (final season) | Same `pass_attempts`; sacks already parsed by adapter | ≥ 100 combined | Same |
| `rb_yards_per_carry_final` | rush attempts (final season) | `CAR` statType from `/stats/player/season?category=rushing` — already parsed by `_pivot_rushing()` in `build_w2b_cfbd.py` | ≥ 50 | Feature back workload |
| `rb_yards_per_reception_career` | career receptions | `REC` statType from `/stats/player/season?category=receiving` — already parsed by `_pivot_receiving()` in `build_w2b_cfbd.py` | ≥ 10 | Minimal receiving involvement |

Non-null alone does not qualify a row for rate-feature training. A player must meet
the volume threshold for the feature to be included in that row's training eligibility
(i.e., if `rb_yards_per_carry_final` is null after gate, that row is excluded from
aligned fold training for the RB enriched candidate).

---

## 9. Post-Rebuild Reporting Requirements

After any v3 CSV rebuild (W2 RB fix or W3 QB ingestion), the implementing agent must
produce and log the following before any W4 bakeoff run is approved:

### 9a. Coverage table

For each position with new features, report for each feature:
```
position | feature | n_rows | n_non_null | pct_populated | volume_gate_applied
```

### 9b. Missingness blockers

List any feature with <50% non-null in the aligned training rows, since the bakeoff
harness will drop it. These must be documented as accepted limitations or trigger a
re-spec before proceeding.

### 9c. Market field contamination scan

Confirm that none of the following strings appear as keys or values in the Engine A/B
feature columns of the generated CSV:
`ktc`, `keeptradecut`, `fantasycalc`, `fantasy_calc`, `adp`, `fantasypros`,
`dynastynerds`, `dynasty_nerds`, `fc_value`, `ktc_value`

This scan runs as part of the existing `scripts/validate_governance.py` gate.

---

## 10. Workstream Structure

| Workstream | Status | Dependency | Blocker |
|------------|--------|------------|---------|
| W1 — WR trimmed bakeoff | Ready after D1 approval | None | D1 |
| W2 — RB denominator fix | **BLOCKED** | D4 decision | D4 — denominator path |
| W3 — QB ingestion | Ready after D2 approval | W2 CSV rebuild (shares pipeline) | D2 |
| W4 — Bakeoff | After W1/W2/W3 | W1, W2, W3 | — |
| W5 — Promotion | After W4 + Codex review | W4 | — |
| W6 — Card enrichment | After W5 | W5 | — |
| W7 — Universe refresh | After W6 | W6 | — |

W3 (QB) can share the same v3 CSV rebuild as W2 (RB) if both proceed — one rebuild run.
If D4 leads to Option B (no live schema probe), W2 and W3 can be rebuilt in a single pass.

---

## 11. Promotion Decision Criteria

Each position is evaluated independently. A position receives a v3 pkl + manifest entry
only if:
1. At least one candidate (Ridge or GBT) passes 2/3 gates in W4
2. Codex review finds no implementation defects
3. David explicit approval

Positions that fail W4 remain on v2 (draft capital only). The graceful degradation path
(`score_prospect_v3()` returns `None` for any position without a v3 contract) is already
in place from Phase 19 W5.

---

## 12. Governance Invariants

| Invariant | Status |
|-----------|--------|
| `decision_supported = False` on all surfaces | Required, always |
| Market data overlay-only — no KTC/FC/ADP/DynastyNerds field enters Engine A/B inputs | Required, always; validated per §9c |
| `latest.json` and `engine_b/v2_manifest.json` unchanged by any Head A v3 promotion | Required, always |
| Head B remains dark (W4 null result; not revisited in Phase 20) | Maintained |
| CFBD_API_KEY in `.env`, never committed | Required, always |
| Model pkl and manifests gitignored (local-only) | Required, always |
| Local-first; Databricks requires David's manual override per session | Required, always |

---

## 13. Open Decisions for David

**D1 — WR feature set (unblocks W1)**
> Approve trimmed 5-feature set: `[nfl_pick, nfl_round, final_college_age, wr_breakout_age, wr_yards_per_reception_career]`?
> W1 can start immediately after approval — no new data fetch required.

**D2 — QB attempt vs. defer (unblocks W3)**
> Include QB as a low-priority bounded experiment (likely FAIL, v2 stays active)?
> Or defer QB entirely to a later phase?

**D3 — W1 start timing**
> Proceed with W1 WR bakeoff immediately once D1 is approved?

**D4 — RB denominator path (unblocks W2)** ← New, required
> **Option A:** Run a live CFBD schema probe first to confirm whether `G` ever appears in
> rushing/receiving player-stat records. Implement whichever path the probe reveals.
>
> **Option B (recommended):** Skip `rb_scrimmage_ypg`/`rb_rec_ypg` entirely. Replace with
> deterministic efficiency features `rb_yards_per_carry_final` and
> `rb_yards_per_reception_career` computed from `CAR`/`REC` denominators already in the
> existing cache. No new API calls required.

**D5 — QB feature set scope** ← New
> Phase 20 QB contract: `[qb_completion_pct_final, qb_yards_per_attempt_final, qb_td_int_ratio_final, qb_sack_rate_final]`
> (4 features from existing adapter). Approve this scope?
> Note: `ppa`, `wepa`, `rushing_yards`, `rushing_tds` are excluded from Phase 20 (dark or deferred).
