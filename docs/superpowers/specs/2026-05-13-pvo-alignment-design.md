# Phase 7 PVO Alignment Design

## Context

Phase 6 closed with Engine B v2 promoted for QB, RB, and WR, with TE retained as an experimental v1 fallback. Roster Auditor now consumes Engine B directly and exposes governance-safe `age_value_context` labels. The codebase also already has an early Player Value Object implementation in `src/dynasty_genius/models/player_value_object.py` and an assembler in `src/dynasty_genius/pvo_assembler.py`.

Phase 7 should align the existing PVO path with the post-Engine-B system. It should not create a second PVO model in `app/models/pvo.py`.

## Goals

1. Make `PlayerValueObject` the canonical model output shape for both Engine A prospects and Engine B active players.
2. Ensure active-player PVOs receive real Engine B projections and model metadata.
3. Keep market data explicitly absent by setting `market_overlay` to `None`.
4. Preserve governance boundaries: no trade-action labels, no market-derived model inputs, no decision-grade claim before gates justify it.
5. Keep RB and TE feature research deferred until the PVO output contract is aligned.

## Non-Goals

- Do not add RB-specific features such as `red_zone_touches` or `targets_per_game`.
- Do not diagnose or retrain the TE model.
- Do not ingest KTC, FantasyCalc, ADP, FantasyPros, or DynastyNerds market data.
- Do not make Roster Auditor decision-grade.
- Do not add frontend polish.

## Existing State

`PlayerValueObject` already contains most required fields:

- `player_id`
- `position`
- `age`
- `engine_used`
- `model_version`
- `model_grade`
- `dynasty_value_score`
- `projection_1y`
- `projection_2y`
- `projection_3y`
- `signal_completeness`
- `inputs_present`
- `inputs_missing`
- `top_drivers`
- `risk_flags`
- `counter_argument`
- `caveats`
- `roster_audit`
- `market_overlay`
- `decision_supported`
- `assembled_at`
- `source_versions`

The gaps are in alignment, provenance, and active-player assembly.

## Required Contract Changes

### PlayerValueObject

Add one top-level provenance field:

```python
source_season: Optional[int] = None
```

`source_season` is the feature season that drove the projection. For Engine B, this maps from `feature_season`. For Engine A prospects, it remains `None` unless a future prospect feature snapshot carries a season.

Keep `decision_supported: bool` as a top-level field. It already exists and should remain consumer-facing so downstream surfaces do not re-derive governance status.

### RosterAuditSignals

Add:

```python
age_value_context: Optional[str] = None
```

This carries the Section 5 display-only overlay through the PVO path. Values must remain context labels, such as `approaching_cliff_high_projection`, never action labels such as sell or hold.

## Engine B Projection Mapping

Engine B predicts `avg_ppg_t1_t2`, a two-year average over T+1 and T+2. Therefore:

```text
Engine B predicted_avg_ppg_t1_t2 -> PVO.projection_2y
PVO.projection_1y -> None
PVO.projection_3y -> None
```

`projection_1y` must not be populated from Engine B v2 unless a separate one-year target model exists. This prevents the PVO from implying temporal precision the model did not estimate.

`dynasty_value_score` remains provisional for active players until a calibrated Engine A/Engine B normalization step exists. For Phase 7 alignment, it should remain `None` for Engine B active-player PVOs unless an explicit normalization design is approved.

## Engine B Metadata Mapping

For active-player PVOs with an Engine B score:

```text
"engine_b"                                -> PVO.engine_used   (constant — identifies the engine family)
engine_b_score.engine                     -> PVO.model_version (e.g. "engine_b_v2_wr", "engine_b_v1")
engine_b_score.feature_season             -> PVO.source_season
engine_b_score.predicted_avg_ppg_t1_t2   -> PVO.projection_2y
engine_b_score.caveats                    -> PVO.caveats
engine_b_score.decision_supported         -> PVO.decision_supported
engine_b_score.experimental               -> model grade/caveat logic
```

Model grade mapping should stay conservative:

```text
QB/RB/WR v2 score, experimental=False -> ACTIVE_B
TE v1 fallback, experimental=True -> EXPERIMENTAL
No Engine B score -> PRE_MODEL
```

If the codebase later standardizes model grade enums, this mapping can be renamed, but the semantics must remain: promoted active-player models are distinct from TE fallback and missing-score rows.

## Engine B Invocation In PVO Assembly

`assemble_pvo()` currently scores prospects through Engine A but leaves active players as `PRE_MODEL`. Phase 7 should add an active-player path:

1. If `is_prospect=True`, preserve the existing Engine A path.
2. If `is_prospect=False`, attempt Engine B scoring.
3. Prefer an explicit `engine_b_score` supplied in `features` when the caller already scored an inference partition.
4. Otherwise call `predict_player_season(features)` when the feature dict has the required Engine B columns for that player position.
5. If no score is available, keep the PVO `PRE_MODEL` with `no_usage_signal` and `age_curve_only` caveats.

This keeps batch callers efficient while allowing direct single-player assembly in tests and services.

## Active Feature Completeness

`pvo_assembler.py` currently defines stale `_ENGINE_B_REQUIRED` values such as `target_share`, `breakaway_run_pct`, and `run_blocking_grade`. Those are not Engine B v2 contract features.

Phase 7 must replace the stale dict with `ENGINE_B_FEATURES_BY_POSITION` from `src/dynasty_genius/models/engine_b_contract.py`.

Rules:

- `inputs_present` and `inputs_missing` for active players are computed from the actual per-position Engine B contract.
- Metadata columns such as `player_id`, `position`, `team`, and `feature_season` remain identity/provenance fields, not model-input fields.
- RB required features are the Engine B base features only.
- WR and TE required features share the same feature list but remain separate model/artifact paths.
- QB required features include QB efficiency and archetype fields only for QBs.

## Roster Audit Integration

`_build_roster_audit_signals()` currently calls `audit_player(player)` without an Engine B score, so `age_value_context` always degrades to `no_engine_b_projection`.

Phase 7 should pass the Engine B score into `audit_player(player, engine_b_score=engine_b_score)` when one is available. The resulting `RosterAuditSignals` should include:

- `cliff_age`
- `years_to_cliff`
- `age_cliff_risk`
- `biological_debt_score`
- `liquidity_risk`
- `signal`
- `signal_drivers`
- `age_value_context`
- `caveats`
- `decision_supported=False`

TE fallback caveats must continue to propagate as `engine_b_experimental_v1_fallback`.

## Market Isolation

Market data remains absent in Phase 7:

```python
market_overlay = None
```

No KTC, FantasyCalc, ADP, FantasyPros, DynastyNerds, or market-derived values may enter Engine B features, PVO score fields, or active-player projection logic. The PVO simply reserves the `market_overlay` slot for Phase 9.

## Testing Requirements

Add or update tests that prove:

1. Active-player PVOs can carry Engine B metadata and `projection_2y`.
2. Engine B `predicted_avg_ppg_t1_t2` does not populate `projection_1y`.
3. `source_season` maps from Engine B `feature_season`.
4. `_ENGINE_B_REQUIRED` drift is eliminated by using `ENGINE_B_FEATURES_BY_POSITION`.
5. `RosterAuditSignals.age_value_context` receives the Engine B-backed context label.
6. TE active-player PVOs retain the experimental fallback caveat.
7. `market_overlay` remains `None`.
8. `decision_supported` remains `False` for active-player PVOs.
9. No market-derived field appears in `inputs_present`, `inputs_missing`, or Engine B score payloads.

Use `.venv/bin/python3.14` for verification because Engine B artifacts require the Python 3.14 environment.

## Acceptance Criteria

- `tests/contract/test_pvo_schema.py` exists or is updated to lock the Phase 7 schema.
- Active-player PVO assembly uses Engine B for QB/RB/WR when feature inputs are available.
- TE rows use the v1 fallback path with explicit experimental caveats.
- Engine B two-year average maps only to `projection_2y`.
- Active-player `inputs_present` and `inputs_missing` are based on `ENGINE_B_FEATURES_BY_POSITION`.
- Roster Audit can consume PVO roster signals without losing `age_value_context`.
- Full suite passes with `.venv/bin/python3.14 -m pytest -q`.

## Open Follow-On Work

- RB feature expansion remains a separate research spec.
- TE diagnosis remains a separate exploratory research track.
- Market overlay remains Phase 9.
- Decision surfaces reading exclusively from PVO remains Phase 8 after this contract alignment lands.
