# Codex challenge — PFF NCAA passing second-lane framing v2

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Artifact reviewed:** `framing_pff_ncaa_passing_candidate_claude_v2.md`  
**Verdict:** **CHALLENGE — 6 blocking framing defects. No RED opens.**

## Checks performed

- Read v2 in full and profiled the current `pff_master_inventory.json` and
  `pff_schema_catalog.json` at the intended player-season grain.
- Read all nine preferred NCAA REGPO Passing Summary and Passing Depth files (2017–2025), filtering
  `position == QB`, joining on `(season, player_id)`, and checking attempts, dropbacks, game counts,
  and derived rate formulas.
- Read the live Engine-A scorer/manifest contract, the CFBD QB normalizer, and the current
  126-row QB training cohort.

## Findings

### 1. “Served today by CFBD alone” incorrectly promotes a candidate lane into active-model state

**What failed.** Lines 17–18 say the constitution's third QB input is served today by CFBD alone.
It is not served by the active QB scorer. `EngineAScorer.score_prospect()` accepts only position,
pick, round, and age (`engine_a.py:131-138`); the v3 manifest/contract contains TE only
(`engine_a.py:143-153`, `head_a/v3_manifest.json`); and the Phase-20 QB arm never fit or promoted a
model. The four CFBD fields exist as a candidate ingestion/training-table lane, not an active QB
scoring input.

**Required correction.** Say CFBD is the only currently implemented **candidate source lane** for
these four QB college-production fields. Do not say it serves the active model or David-facing
score.

### 2. The historical 25.4% figure is again attached to the wrong bakeoff denominator

Line 25 says the historical block was measured at 25.4% against the runner threshold. The runner
gated on 38 eligible rows: the artifact records 39.5% for three fields and 0.0% for sack rate.
`32/126 = 25.4%` is the full-table population figure from the ledger, and it remains defect evidence.
Both can be reported, but they must not be described as one measurement.

### 3. The 2,954 reconciliation count is stale through 2024 and hides a real population asymmetry

**Independent current result:** NCAA REGPO 2017–2025 contains **3,362** Passing Summary QB rows and
**3,401** Passing Depth QB rows. All **3,362 overlap rows** reconcile Summary
`attempts`/`dropbacks`/`player_game_count` to Depth
`base_attempts`/`base_dropbacks`/`player_game_count`. The remaining **39 Depth-only rows** all have
`base_attempts = 0` and `base_dropbacks` from 1 to 4.

`2,954` is exactly the 2017–2024 Summary count; 2025 contributes another 408. The corrected framing
must report the current 3,362/3,362 result and the 39-row zero-attempt population asymmetry. “Stable
schema” does not mean identical row population.

### 4. The allowlist rule is not yet safe because the two sack rates have different grain and formula

**Evidence.** The current CFBD `qb_sack_rate_final` is a **team-season** rate:
`sacksAllowed / (team passAttempts + sacksAllowed)`
(`cfbd_qb_adapter.py:330-342`). PFF Passing Summary is player-season grain, and the current archive
reproduces PFF `sack_percent` as `sacks / dropbacks` within 0.05 percentage-point rounding for all
3,362 Summary QB rows. A row-wise comparison would label a team-vs-player definition mismatch as a
vendor disagreement.

**Required correction.** Add a metric registry with `grain`, raw numerator, raw denominator, unit,
scope, and formula. Until equivalent grain is established, sack rate emits
`not_comparable: metric_grain_mismatch`; it does not enter an agreement delta. Fixing CFBD semantics
or aggregating PFF to team-season is a separate scope decision, not an incidental implementation
choice here.

### 5. Reviewer-owned allowlist — enumerate by role, not as one undifferentiated set

I will own this enumeration as RED author, using the current schema hash
`3a3eba34…` (Passing Summary, 44 columns) and `c1ede0cb…` (Passing Depth, 554 columns):

- **identity/context only:** `player_id`, `player`, `position`, `team_name`, `player_game_count`;
- **comparison raw counts:** `attempts`, `completions`, `yards`, `touchdowns`, `interceptions`;
- **PFF-only diagnostic pending grain equivalence:** `sacks`, `dropbacks`;
- **cross-family QA only:** Depth `base_attempts`, `base_dropbacks`, `player_game_count`.

Completion fraction, YPA, and TD:INT are recomputed locally from the raw counts with registered
zero-denominator behavior; provider rates do not become comparison inputs. Every other Summary and
Depth field is excluded by default, including accuracy, aimed-pass, BTT/TWP, pressure attribution,
EPA, grades, depth/direction splits, thrown-away, hit-as-threw, and provider-derived rates. The RED
must test these four roles separately so identity and QA fields cannot leak into comparison output.

### 6. The era boundary is already measurable, and all-overlap acceptance needs a non-vacuity guard

The active CSV's `season` is draft year and the builder registers final college season as
`draft_year - 1` (`build_w2b_cfbd.py:876,890,903`). The QB cohort is **126 rows, draft years
2015–2025**; **32/126** are draft years 2015–2017, before PFF's earliest 2017 college season can
cover them. Among the 38 non-censored bakeoff-eligible rows, **16/38** are pre-2018 draft years.
The v3 framing should carry these measured denominators instead of “may reach earlier.”

Seed 9 also needs an explicit **zero eligible / zero resolved overlap refusal**. “Every eligible
row” is vacuously true for an empty set. This is not a magic power floor: one resolved row remains
semantically testable, while zero rows cannot establish reconciliation at all. The artifact should
still write the source/cohort counts and refusal reason.

## Constitutional and architectural alignment

- Parallel source-qualified lanes, no fallback/coalescing, remains correct.
- The 840-ID all-position substrate stays out of scope.
- No model run, feature promotion, paid refresh, active CSV mutation, or identity-substrate build is
  authorized by this challenge.

