# Product substrate investigation — the 115 blanks are not a missing-season feature-store failure

**Date:** 2026-08-18  
**Commission:** David's six-question investigation relayed in `[w#product-investigation]`  
**Scope:** read-only investigation; no product code, feature store, model, migration, or surface changed  
**Layer served:** Layer 3 presenting, with Layer 1/2 dependency verification performed voluntarily under the pending `05` codification  
**Decision status:** `decision_supported=false`

## Executive Summary

The proposed root cause is not supported. The absent 2024 row is the feature store's deliberate inference partition, and 2024 data is visibly used to build the 2025 lag features. The 505 runtime rows for 2025 match all 505 players in a separately fetched 2025 weekly snapshot on `games_t`; Garrett Wilson's seven games and 14.214 PPG match that snapshot exactly. Rebuilding from `ff_opportunity` would therefore attack the wrong problem and would also violate that source's current substrate-only boundary.

The real failure is downstream and broader:

1. The low-game DVS bridge is applied to 114 served players, 85 of whom are veterans with at least three years of experience. It asks for an Engine A rookie prior that the active-PVO builder never supplies. It then returns no DVS while falsely claiming `dvs_engine="A"` and “Engine A prospect score used as prior.”
2. The API labels those null-score rows `modeled` with no degradation because it keys on route, not whether a composite exists.
3. A separate 108 players with only one to three 2025 games are dropped before inference by the four-game feature floor; 99 resolve into the current universe, four are rostered, and none receives even a points projection.
4. Engine B's feature and outcome aggregation includes postseason. Among the 505 current inference players, 162 have postseason rows, 160 have a changed PPG, and six cross the eight-game DVS threshold only because postseason games were counted. Whether this is a defect depends on David's intended PPG definition; the current governing decision record does not settle it.
5. The newly shipped health provenance can mislabel nonempty participation data as `loaded_empty` and describes an ordinary retry as “cache.” The feature values themselves show the participation join was not empty.

QB-1 does **not** need to be rerun because of tonight's alleged runtime-store gap. It used a separately fetched, pinned seven-dataset snapshot that includes 2024 and 2025 and mechanically excludes postseason. Its report remains `decision_supported=false`; QB rushing remains a hypothesis **under test**, not a finding. Engine B-family work does need a conditional rerun if David rules that its PPG target and game counts must be regular-season only.

## Ranked findings

### 1. Critical — the commissioned premise is false; do not rebuild the feature store from `ff_opportunity`

**Evidence**

- `apply_inference_partition` retains only complete T+1/T+2 training rows and the latest inference season, deliberately dropping the in-between season (`src/dynasty_genius/features/feature_assembly.py:46-93`). The ratified BUILD-4 spec states explicitly that “feature-season 2024 is absent by design” (`docs/superpowers/specs/2026-07-03-build4-superflex-qb-design.md:14-16`).
- The builder creates exact T−1/T−2 lags before applying that output partition (`src/dynasty_genius/features/feature_assembly.py:272-325`). Garrett Wilson's 2025 runtime row contains `ppg_t_minus_1=14.817647`, exactly his 17-game 2024 PPG in the independent weekly snapshot; his 2025 `games_t=7` and `ppg_t=14.214286` also match the snapshot exactly.
- Reproduced join: all 505 runtime 2025 rows matched a source player and all 505 had exact `games_t`; the source reaches week 22 and contains `REG` and `POST`. Query: group `app/data/backtest/qb_validation/raw/weekly/weekly_2015_2025.parquet` at 2025 by `player_id`, calculate `nunique(week)`, then inner-join to the 2025 rows of `app/data/features_runtime/engine_b_features_runtime.csv`.
- The apparent three-way count agreement is not player agreement. `games_t<8` contains 115 feature IDs and “DVS null + projection present” contains 115 served rows, but their intersection is 114. Nick Kallerup (`00-0040058`) is the unmatched feature orphan; Bo Melton (`00-0037091`) is the compensating served row and has 13 games in the feature store.
- The proposed replacement source is explicitly third-party expected-points model output, not raw fact, and its landing contract forbids engine consumers without separate validation (`tests/contract/test_ff_opportunity_ingestion_red.py:339-358`). The realized-outcome scorer independently keeps it out (`tests/contract/test_realized_outcome_scorer_wiring_red.py:781-783`).

**Cost to David:** a rebuild would spend the R1 slot changing the model substrate while leaving the actual null-score policy, false provenance, pre-model cohort, and UI ambiguity intact. It could also introduce unvalidated third-party model output into an engine.

**Disposition:** stop the proposed `ff_opportunity` rebuild. R1 should remain a serving/availability problem first: put the existing points projection in front of David, then repair the bridge semantics only after choosing what low-volume veterans should mean.

### 2. High — the dead-window bridge is a rookie-prior policy applied mostly to veterans

**Evidence**

- Engine B DVS requires eight games (`src/dynasty_genius/models/engine_b_contract.py:104-107`). Below that, `assemble_pvo` tries to blend with Engine A (`src/dynasty_genius/pvo_assembler.py:394-459`).
- Engine A is explicitly a rookie forecast using pick, round, and age, and its own module says it “does not score veteran careers” (`src/dynasty_genius/scoring/engine_a.py:1-11,50-56,91-118`).
- The active builder copies the runtime feature row, adds only the Engine B prediction, creates `PlayerIdentity`, and calls `assemble_pvo(is_prospect=False)`; it does not add draft pick, draft round, or age-at-entry to `features` (`scripts/build_universe_pvo_batch.py:239-324`).
- Reproduced cohort: 114 served players are both under eight games and missing DVS with a projection. Only 29 have 1–2 years of experience; **85 have 3+ years** and 38 have 7+ years. The cohort includes Kyler Murray (7 years), Carson Wentz (10), Tyreek Hill (10), Russell Wilson (14), and Tyrod Taylor (15).
- The fresh Aug-14 crosswalk resolves all 114 GSIS IDs and contains both draft round and overall pick for 75. That proves draft data exists now; it does not make current age a valid rookie-model input. `assemble_pvo` takes `features["age"]` (`pvo_assembler.py:327-340`), while the runtime feature is current-season age.
- Sixteen of the 114 are rostered and two are on David's roster: Garrett Wilson and Braelon Allen. High existing projections include Jayden Daniels 13.071 PPG, Malik Nabers 12.234, Kyler Murray 11.445, and Garrett Wilson 11.255.

**Cost to David:** real points forecasts disappear for injured or low-volume veterans, and a naive “add draft capital” repair would feed current age into a rookie forecast or use a years-old rookie prior as if it were current veteran value.

**Disposition:** do not blindly populate the existing blend. First decide the product truth for low-volume veterans. The safe immediate presentation is projection + games/data basis. If a prior is retained, persist the historical Engine A result or reconstruct true age-at-entry; never substitute current age.

### 3. High — the system states a prior was used when no Engine A result exists

**Evidence**

- In the no-prior branch, production sets `dynasty_value_score=None`, `dvs_engine="A"`, and adds “Engine A prospect score used as prior” (`src/dynasty_genius/pvo_assembler.py:459-467`).
- Reproduced artifact count: 114 of 115 “DVS null + projection present” rows carry `dvs_engine="A"`; all 114 are the under-eight-game cohort. Their caveats contain the prior-used sentence even though the branch exists specifically because `engine_a_result` is false.
- Route assembly treats `dvs_engine="A"` as an Engine A route (`src/dynasty_genius/universe_pvo_batch.py:26-38`) while the row later remains `MODEL_UNCERTAIN` only because DVS is null (`:50-52`).
- The player API calls any Engine A/B route `modeled` and returns `degradation=None`, even when `dynasty_value_score` is null (`app/api/routes/players.py:239-290`).

**Cost to David:** the product cannot distinguish “projection exists but composite was not formed” from “Engine A prior used,” “score withheld,” or “model unavailable.” The provenance is factually false at the exact seam meant to explain the blank.

**Disposition:** the output needs an explicit score state/reason. A null composite must never claim an engine ran. Surface points regardless of composite state.

### 4. High — the feature floor creates another invisible cohort below the 115

**Evidence**

- The feature builder filters out `games_t < MIN_GAMES_THRESHOLD` before lags, inference partition, and scoring (`src/dynasty_genius/features/feature_assembly.py:138-143`). The ratified BUILD-4 substrate description records this as a four-game floor (`docs/superpowers/specs/2026-07-03-build4-superflex-qb-design.md:14-16`).
- Reproduced from the independent 2025 weekly snapshot: 108 QB/RB/WR/TE players have one to three all-season game rows (34 WR, 28 TE, 27 RB, 19 QB). Ninety-nine map through the fresh crosswalk into the served universe; all 99 are `PRE_MODEL`, and none has `projection_2y` or DVS.
- Four are currently rostered: Anthony Richardson, Austin Ekeler, Jordan James, and Jalen Royals. None is on David's roster.

**Cost to David:** “1–7 games” is not one degraded band. Four-to-seven-game players have a hidden points forecast; one-to-three-game players have no Engine B prediction at all. A star injured after three games silently looks the same as a player outside the model population.

**Disposition:** treat this as a distinct state, not an extension of the 115. A points-first fallback would need a separately validated basis; the current model cannot honestly fabricate one for this cohort.

### 5. High, conditional on David's definition — Engine B includes postseason in both game counts and PPG

**Evidence**

- `fetch_and_agg_stats` filters positions but never filters `season_type`; it aggregates PPR points and `nunique(week)` over all rows (`scripts/assemble_engine_b_dataset.py:158-207`).
- The ratified BUILD-4 spec already notes that max games reaches 21 because postseason is included (`docs/superpowers/specs/2026-07-03-build4-superflex-qb-design.md:22-25`). The governing Engine B record says only “2-year average PPG” and does not resolve regular-season versus all-game scope (`docs/governance/03-engine-b-decision-record.md:13-19`).
- Among the 505 current inference players, 162 have postseason rows; all 162 gain games, 160 change PPG, and the mean absolute PPG change is 0.412. Six cross from fewer than eight regular-season games to at least eight all-season games solely because postseason was included: Jake Bobo, Lil'Jordan Humphrey, Ronnie Rivers, D'Ernest Johnson, Cade Stover, and Durham Smythe.
- Large 2025 changes include Christian Kirk 2.144 PPG, Kenneth Walker III 2.042, Brock Purdy 1.567, and TreVeyon Henderson 1.553.

**Cost to David:** if the intended construct is regular-season fantasy PPG, training labels, features, the current eight-game bridge, P90 normalization, and replacement baselines all use the wrong population. Postseason teams also receive extra opportunity relative to non-playoff teams.

**Disposition:** this needs a definition ruling, not a silent code edit. If David rules regular-season only, rerun the Engine B family and every dependent calibration listed in the rerun matrix below. If all-game PPG is intentional, disclose it explicitly on every points surface.

### 6. High — health provenance confuses shape, retry, and cache semantics

**Evidence**

- `_load_stream_isolated` calls any nonempty frame without a `season` column `loaded_empty`, because `status="loaded"` depends on deriving `effective_season` (`scripts/run_feature_refresh.py:102-116`). Participation is consumed through game/play identifiers and `offense_players`, not a required `season` column (`src/dynasty_genius/features/feature_assembly.py:210-232`).
- The current report says participation is `loaded_empty` after a ValueError fallback, but current 2025 inference features have TPRR/YPRR populated for 205/207 WR rows and 108/109 TE rows. The report's candidate and prior runtime both contain 2,746 rows, and every recorded numeric mean delta is zero (`app/data/features_runtime/feature_refresh_latest_report.json`, JSON paths `stream_provenance`, `validation.drift`). This is incompatible with participation actually disappearing during this run.
- `fallback_used` records that a shorter season window was retried (`scripts/run_feature_refresh.py:86-120`). System health converts any fallback into a cached-source diagnosis and says the stream is “on {season} cache” (`app/api/routes/system_health.py:380-420`). In the 2026 offseason, retrying an unavailable 2026 player-stats file with 2018–2025 is normal source behavior, not proof that a cache was used.

**Cost to David:** the health surface can flag the exact data used successfully as empty/degraded and direct investigation toward a false cache failure. Commit `62768d0` may have improved visibility while still encoding the wrong cause.

**Disposition:** report row count separately from season coverage, and describe retries as retries. Do not infer cache use without evidence of a cache path.

### 7. Medium — publish readiness is structurally fail-closed but semantically weak

**Evidence**

- Scheduled publish floors are only four total rows and one per position (`scripts/run_feature_refresh.py:43-49`).
- Validation covers schema, duplicates, one inference season, tiny coverage floors, selected ranges, and configured null rates (`src/dynasty_genius/features/feature_validation.py:86-250`). It does not require source row counts or position-specific completeness for every consumed feature.
- Publication writes a ready marker from that validation (`src/dynasty_genius/features/feature_publish.py:117-156`). The marker carries no `source_as_of`; the reader returns that absent field as `None` (`src/dynasty_genius/features/feature_source.py:83-106`).

**Cost to David:** a genuinely degraded future frame can pass because it is nonempty and structurally valid, and a consumer cannot explain the source vintage from the ready marker.

**Disposition:** add only the smallest evidence-bearing checks: source row counts, inference-position coverage, and completeness for features actually consumed. This is a data acceptance repair, not a new governance layer.

### 8. Medium/low scope — stale position precedence erases Bo Melton's otherwise valid score

**Evidence**

- The active builder gives the May-16 crosswalk position precedence over prediction and feature positions (`scripts/build_universe_pvo_batch.py:299-305`).
- Bo Melton is WR in the 2025 feature row with 13 games, but CB in the served PVO. CB has no Engine B P90, so the DVS normalization does not run (`src/dynasty_genius/pvo_assembler.py:397-410`).
- A full audit of the 503 joined Engine B PVO rows found exactly one feature/PVO position mismatch: Bo Melton.

**Cost to David:** low by player importance, high as evidence: this one row made the two 115 counts appear identical and helped validate the wrong causal story.

**Disposition:** resolve position from the model feature/prediction for Engine B eligibility and separately disclose crosswalk disagreement; do not silently let an older identity snapshot override the model's position.

## What tonight changes

### What must be rethought

1. **R1 is a presentation and state-semantics problem before it is a data rebuild.** The model already emits points for the four-to-seven-game cohort. The first safe improvement is to show that number with units, horizon, and data basis.
2. **“Dead window” is not a rookie-only bridge.** Seventy-five percent of the served cohort (85/114) has at least three years of experience. A rookie prior is not automatically a valid anchor for an injured veteran.
3. **One blank cannot represent four states.** The product currently conflates composite unavailable, composite deliberately withheld, pre-model/no projection, and unresolved identity.
4. **Game-count semantics matter as much as data freshness.** A fully populated all-game store can still be the wrong construct if David means regular-season PPG.
5. **Health must report what happened, not infer a diagnosis.** Row count, requested window, returned coverage, retry, and cache provenance are separate facts.

### New product ideas/features that follow directly

These are product findings, not implementation authorization:

1. A first-line **points projection** with `PPG`, horizon, feature season, and games basis, visible even when DVS/xVAR is absent or withheld.
2. Explicit score states such as `projection_available_composite_unavailable`, `composite_withheld`, `pre_model`, `identity_unresolved`, and `source_degraded`, with a named reason.
3. A low-volume evidence label that distinguishes 1–3 games from 4–7 games and shows whether game counts are regular-season or all-game.
4. A historical-prior field that stores the actual rookie-time Engine A score and its input vintage if David chooses to keep a bridge. Do not reconstruct it from current age.
5. Source-health facts that expose returned rows and coverage separately; retry is not cache.

## Rerun matrix

| Asset or finding | Rerun now because of tonight? | Evidence-based disposition |
|---|---:|---|
| QB-1 study | **No** | It uses a separate pinned raw root (`scripts/run_qb1_study.py:48-60`), admits seven nonempty provenance-bearing datasets fail-closed (`src/dynasty_genius/eval/qb_validation/sources.py:23-103`), and filters to `REG` before labels (`scripts/run_qb1_study.py:245-251`; `qb_ppg_labels.py:16-24,783-788`). The Aug-14 manifest includes 2024 and 2025 PBP plus a 199,868-row weekly snapshot; the report pins the snapshot IDs and registration hash and remains `decision_supported=false` (`app/data/backtest/qb_validation/raw/fetch_manifest.json`; `app/data/backtest/qb_validation/qb_validation_report.json:1941-2042`). |
| Engine A training/validation | **No** | The false runtime-store premise does not touch its prospect training source. A bridge repair may require preserving historical Engine A outputs, not retraining Engine A. |
| R2 identity, R3 unused usage store, R4 dead depth-chart feed | **No** | Those are independently established substrate/identity facts. This investigation neither invalidates nor repairs them. |
| Current PVO universe | **Yes, rescore after an authorized bridge/provenance decision** | This is artifact assembly, not necessarily model retraining. Preserve the old capture as historical evidence. |
| Engine B QB/RB/WR v2 and TE v3 | **Conditional** | Rerun only if David rules the target and feature season must be regular-season only. The current assembler includes postseason. |
| Engine B P90, replacement DVS, xVAR/percentiles, calibration and Engine-B-derived comparative findings | **Conditional, same ruling** | These constants depend on the Engine B training/inference distribution (`src/dynasty_genius/models/engine_b_contract.py:19-29,71-89`). Recompute after any regular-season-only rebuild; do not mix old constants with a new population. |
| Any `ff_opportunity`-based model or finding | **Not authorized / not yet valid** | Current contract is substrate-only and says the source is third-party expected-points model output. It needs separate validation before any consumer exists. |

### QB-1 conclusion, stated narrowly

Tonight's proposed feature-store gap does **not** invalidate QB-1 because QB-1 did not use the runtime Engine B CSV. Its separate snapshot contains 2024 and 2025, its target is registered as regular-season Sleeper points per qualifying game, and postseason rows are rejected. The existing registration caveat still applies: source admission proves file presence and recorded provenance, not content binding between every snapshot and parsed frame, source-timestamp authenticity, or parser-version authenticity (`docs/validation/2026-07-21-qb-1-study-registration.md:278-283,332,348`). That is an existing limitation, not a consequence of tonight.

The report is still `decision_supported=false`. QB rushing remains a hypothesis **under test**; no result, marginal contribution, or dynasty-value claim is licensed until David rules.

## Direct answers to David's six questions

1. **Other major gaps:** yes — false DVS provenance, a mostly-veteran rookie-prior bridge, a hidden one-to-three-game cohort, postseason contamination or undisclosed all-game semantics, health misclassification, weak source-vintage/readiness evidence, and one position-precedence identity defect.
2. **What must be rethought:** the repair target. This is not “missing 2024 destroyed 2025.” It is state semantics, model-population policy, and presentation. Low sample is not the same as missing data.
3. **New ideas/features:** points-first presentation; named score-unavailable states; unit/horizon/game-basis disclosure; and, only if retained, a versioned historical prior rather than current-age reconstruction.
4. **Rerun everything:** no. Do not rerun QB-1 or Engine A because of this premise. Conditionally rerun the full Engine B-dependent family if David rules regular-season-only PPG. Rescore PVO after an authorized bridge correction.
5. **What else was uncovered:** the exact 115 agreement was a one-in/one-out coincidence; 108 additional one-to-three-game players sit below the feature floor; 85/114 low-game served rows are veterans; six players cross the DVS threshold only through postseason; current participation provenance is internally inconsistent with populated route features.
6. **Obvious improvements:** show the points already held; stop claiming an Engine A prior when none ran; separate blank states; fix health facts; and resolve the PPG season-type definition before another model cycle.

## What could not be verified

- The upstream provider's independent truth was not verified beyond the pinned local Aug-14 nflreadpy snapshots and their manifest hashes. The 505/505 runtime match proves consistency with that separate capture, not the NFL's official record.
- No live browser or Studio filesystem was inspected. The visual behavior described in the commission was treated as established; this investigation verified backend artifacts and API semantics only.
- The exact training impact of removing postseason was not simulated. The measured cohort and PPG changes establish exposure, not the direction or size of model-metric changes.
- Whether David intended all-game or regular-season PPG for Engine B is not stated in the current decision record; therefore the postseason finding is conditional, not declared a defect by fiat.
- No alternative low-volume-veteran model was evaluated. Showing the existing points projection is supported; inventing a replacement composite is not.

## Reproduced measurement notes

All probes were read-only and executed in the repository virtual environment on 2026-08-18.

- **Runtime/source match:** filter runtime CSV to `feature_season==2025`; group the Aug-14 weekly parquet at 2025 by `player_id`; compare `games_t` to `nunique(week)`. Result: 505 runtime, 505 source matches, 505 exact games.
- **115 reconciliation:** set A = runtime 2025 `games_t<8` GSIS IDs; set B = served PVO rows where DVS is null and `projection_2y` nonnull, keyed by `dg_player_id`. Result: |A|=115, |B|=115, |A∩B|=114, one ID each side.
- **Veteran/draft/roster cohort:** join the 114 intersection to served `player.years_exp`, league context, and the Aug-14 `ff_playerids_full.parquet`. Result: 85 with 3+ years, 38 with 7+; 16 rostered, two David; 75 with draft round and overall pick.
- **One-to-three-game cohort:** group the Aug-14 2025 skill-position weekly rows by player, keep `nunique(week)` in [1,3], map via fresh Sleeper IDs into the universe PVO. Result: 108 raw, 99 served matches, four rostered, zero projection and zero DVS.
- **Postseason exposure:** restrict weekly source to the 505 runtime IDs; compare all-season versus `season_type==REG` player aggregates. Result: 162 postseason participants, 160 changed PPG, mean absolute change 0.412, six cross the eight-game threshold.
- **Participation evidence:** inference WR TPRR/YPRR nonnull 205/207; TE 108/109. Current refresh report candidate/prior rows 2,746/2,746 and all numeric mean drift values are zero despite `participation.status=loaded_empty`.

One compact count chart accompanies the portable report because the adjacent 114-player and 108-player cohorts are easy to conflate but are produced by different gates. No causal trend chart is included; ranked evidence and the rerun matrix communicate the heterogeneous defects more honestly.
