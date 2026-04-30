# Codex Review: 2026-04-30

## Prioritized Findings

### Trade output is currently the most misleading surface

`app/services/trade_analyzer.py` values players by feeding current age plus user-provided pick/round into the rookie model, then applying a manual age discount. That makes veteran values look model-backed when they are really a rookie-model proxy plus heuristics. Trade should stay internal or be explicitly labeled as experimental until it reads from a real shared valuation layer.

### Validation is not aligned with the mission yet

`app/data/pipeline/collect_draft_prospects.py` creates an `is_training` flag, but `app/data/pipeline/train_models.py` drops holdout rows and then uses a random train/test split. That misses the forward-looking validation the docs call for and can overstate model quality.

### The current rookie model is too thin for decision confidence

`app/services/rookie_evaluator.py` uses only pick, round, and age. That is a reasonable early baseline, but outputs like `dynasty_tier` and `confidence` can imply more certainty than exists. The confidence field is just draft-pick bucket logic, not model uncertainty.

### The two-engine architecture is mostly documented, not implemented

Docs correctly define Engine A, Engine B, and a unified value layer, but the code only has an early Engine A path. There is no active-player forecast service, no shared `dynasty_value_score`, and no `projection_1y`/`projection_2y`/`projection_3y` output contract yet.

### Hardcoded config can break or silently use the wrong league

`app/services/roster_auditor.py` hardcodes username, league name, and season. If the named league is missing, it falls back to the first league; if no leagues exist, it crashes. `app/services/trade_analyzer.py` also hardcodes `current_year=2025`.

### Model artifacts are not traceable

Training overwrites `app/data/models/*_model.pkl` and only prints metrics. There is no saved validation report, artifact metadata, feature list, training cutoff, data hash, or model version.

### Scraper/data-source layer is still placeholder-level

`app/data/pff.py`, `app/data/playerprofile.py`, and `app/data/ktc.py` are stubs. That is fine for now, but the next data additions should use isolated adapters, cached/raw snapshots, and validation checks as the docs recommend.

## Architecture Alignment

The docs are directionally strong: they correctly prioritize a unified dynasty valuation system over frontend polish. The codebase is still closer to a prototype: FastAPI routes for rookies, roster, and trade; a simple rookie Ridge model; Sleeper roster fetch; and heuristic trade/aging logic.

The biggest mismatch is that product surfaces already exist for roster/trade decisions, but the shared valuation engine they should depend on does not exist yet.

## Next 5 Implementation Tasks

1. Fix training validation first.
   Use a true temporal holdout by draft year or the existing `is_training` split, emit per-position validation reports, and add pass/fail sanity gates. This is the foundation for trusting any downstream output.

2. Add model artifact versioning and metadata.
   Save versioned artifacts with feature names, target definition, training cutoff, row counts, metrics, and timestamp. Stop silently overwriting pickles.

3. Introduce the unified valuation schema.
   Define one internal output shape with `dynasty_value_score`, `confidence_band`, `projection_1y`, `projection_2y`, and `projection_3y`. Wire rookie outputs into it first, even if some fields are provisional.

4. Quarantine or rewrite trade analysis.
   Either clearly mark current player valuation as experimental/heuristic, or make trade analysis consume only the unified valuation schema. Do not keep presenting veteran values as if the rookie model validates them.

5. Stabilize config and roster lookup.
   Move username, league name/id, season, and current year into structured config/env. Make missing league/roster cases fail explicitly instead of falling back silently.

After those, the next modeling work should be RAS ingestion, expanded rookie features from `nfl_data_py`, and then the first Engine B active-player MVP.

## Review Note

Tests were not run. This was a read-only review.
