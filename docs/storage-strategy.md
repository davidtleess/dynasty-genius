# Storage Strategy

This doc defines where Dynasty Genius data lives — current state, target state, and the migration path between them. The system evolves from a local-file substrate to a Databricks Lakehouse on AWS S3. Both modes coexist during migration; the contracts agents implement against are the target.

- Strategy and architecture: [system-design.md](system-design.md)
- Adapter and identity contracts: [data-source-contracts.md](data-source-contracts.md)
- Implementation playbook: [agent-execution-plan.md](agent-execution-plan.md)
- Phase advancement gates: [validation-gates.md](validation-gates.md)

## Why a Lakehouse

The current substrate (local snapshots under `app/data/cache/raw/`, training CSVs under `app/data/training/`, model artifacts under `app/data/models/runs/`, validation reports as committed JSON) was right for the bootstrap phase: simple, reviewable, no cloud bill. As the project plans to ingest film-derived signals (pose / route classification from video) and run high-fan-out career simulations, the local-file substrate stops being right for three concrete reasons:

1. **Time-travel and provenance.** Composite-gate analysis and backtests need to ask "what did the model see when this decision was made?" Delta Lake's transaction log answers that natively; flat files don't.
2. **Schema enforcement at write time.** Today, schema drift surfaces as parser failures downstream of the snapshot. Delta + Unity Catalog refuses the write that violates the schema.
3. **Multi-engine compute over the same canonical tables.** Engine A retraining, Engine B feature pipelines, and the backtest harness should read the same gold tables, not maintain three slightly divergent copies.

This doc is the blueprint. Code follows.

## Target Architecture

### Substrate: Delta Lake on S3

All durable data lives as Delta tables on AWS S3 under the `gen_alpha` Unity Catalog. Snapshots, normalized rows, model artifacts, and decision cards are versioned by Delta's transaction log (time-travel via `VERSION AS OF`), governed by Unity Catalog, and schema-validated at write.

Local file caches under `app/data/cache/` continue to exist as a dev-time scratch area and as a fallback when offline; they are never the source of truth and never feed production decisions.

### Medallion Layering

The `gen_alpha` catalog uses three schemas, each with a single, sharp responsibility:

| Layer | Schema | Owns | Examples |
| --- | --- | --- | --- |
| **Bronze** | `gen_alpha.bronze` | Raw, source-shaped snapshots — pre-parse, pre-normalization. Append-only. The audit trail. | `bronze.sleeper_rosters_raw`, `bronze.pff_grades_raw`, `bronze.ras_yearly_raw`, `bronze.ktc_values_raw` |
| **Silver** | `gen_alpha.silver` | Normalized rows conforming to the per-source schemas defined in [data-source-contracts.md](data-source-contracts.md). Identity-resolved to canonical `player_id`. | `silver.player_seasons`, `silver.draft_capital`, `silver.usage_metrics`, `silver.identity_canonical_mapping`, `silver.market_signals` (quarantined) |
| **Gold** | `gen_alpha.gold` | DVU-anchored decision-ready outputs — the unified Player Value Object, the DVU Decision Cards each surface emits, the validation reports, the market overlay. Read-only from the API layer. | `gold.player_value_object`, `gold.decision_cards`, `gold.validation_reports`, `gold.market_overlay`, `gold.snapshot_manifests` |

Cross-cutting rules:

- **Bronze never lies.** Raw bytes are preserved; nothing is enriched or coerced before landing.
- **Silver is reproducible from bronze.** A silver-layer rebuild is a pure function of the bronze partitions it reads. Identity resolution is the only non-pure step; its output (the canonical mapping) is itself a silver table with audit columns.
- **Gold never feeds Engine A or Engine B training.** Gold is the *output* layer. Models train on silver. Letting gold leak back into training is the exact circularity that the trade-verdict ban and the KTC-not-in-features test exist to prevent.
- **No layer skipping.** Every Engine B ingestion path is `bronze → silver → gold`. A direct `bronze → gold` pipeline is a defect.
- **Time-travel is contractual.** Every PVO row in `gold.player_value_object` carries the silver table version (`silver_snapshot_version`) it was computed from, and every silver row carries the bronze partition (`bronze_partition_id`) it was derived from. A decision card is reproducible end-to-end without asking a human.

### Unity Catalog as Governance

Unity Catalog enforces the Tier-1/2/3 source hierarchy from the Domain Framework at the platform level, not just at code-review time:

- **Tier-1 (ground truth)** sources — PFR, NGS, PFF, PlayerProfiler, Sleeper — get write permission to bronze and read permission across silver and gold.
- **Tier-2 (validated analyst)** sources are not ingested as data. They are referenced in `docs/` only.
- **Tier-3 (market signal)** sources — KTC, FantasyCalc, Dynasty Nerds, ADP — get write permission to a single quarantined silver table (`silver.market_signals`) that has *no read permission* from any Engine A or Engine B feature pipeline. Only the `gold.market_overlay` job and the DVU peg job read it. This is the platform-level analog of the existing `tests/contract/test_ktc_not_in_features.py` rule — defense in depth.

Unity Catalog audit logs answer "who wrote what to which table when." That answer is the spine of `validation-gates.md`'s caveat-hygiene composite criterion.

### MLflow as the Lifecycle Tracker

Every evaluator run — Engine A retrain, Engine B retrain, backtest harness execution, calibration job — logs to MLflow under the experiment `/Shared/dynasty_genius`.

Per-run logging contract:

- **Params** — `model_family`, `model_version`, feature set version, training data SHA, holdout split definition, cross-cutting threshold versions consumed.
- **Metrics** — every numeric field from `validation_report.json` (R², Spearman, top-K hit rate, RMSE, bust avoidance, plus the composite-gate components from `validation-gates.md` once Step 0.5 ships them).
- **Tags** — `model_grade`, `position`, `caveats` (joined as a comma-separated tag), `engine: A | B`.
- **Artifacts** — pointer to the gold-table version that produced this run (Delta `VERSION AS OF`), pointer to the silver feature snapshot consumed, and the model binary itself.

The MLflow run ID is recorded in `gold.validation_reports`, so a decision card is traceable end-to-end: card → PVO row → silver feature snapshot → bronze source rows.

MLflow is observability, not enforcement. It does not gate writes; Unity Catalog does.

## The Currency: Dynasty Value Unit (DVU)

DVU is the system's common currency for cross-asset comparison.

**Peg:** `100 DVU = current market value of the 1.01 rookie pick`.

Properties of the peg:

- The peg is **market-anchored**, sourced from `gold.market_overlay` (which reads `silver.market_signals` from KTC). The peg refreshes daily; historical pegs are preserved so any past DVU Decision Card is reproducible against the market state it was generated under.
- The peg is the **only** point at which market data touches a value the user sees on a card. Engine A and Engine B continue to score in production-units (projected fantasy PPG, conformed to whatever the engine's natural output is). The DVU conversion happens at PVO assembly, *after* the score is final.
- **DVU is a display unit, not a feature.** No Engine A or Engine B feature pipeline reads DVU. No model artifact's feature list contains DVU. The contract test that enforces "no KTC in features" extends to DVU implicitly: KTC cannot enter; DVU is downstream of KTC.

Why the 1.01 peg specifically: the market value of the 1.01 rookie pick is the most-traded, most-priced asset in dynasty. Anchoring to it gives every cross-asset trade ("does this veteran equal a 1.01 + a future second?") a stable referent. The peg drifts over time as rookie classes change perceived strength, which is fine: the *unit* drifts with the market it claims to denominate, and the time-stamped peg is preserved in `gold.market_overlay` history.

**Counter-argument, honestly:** anchoring the display unit to KTC means the user's read of value moves with the market. A pure model-only display would move only with model retrains. The DVU choice trades off "stability vs. relevance." The system already accepts market data in the user-facing layer (the `market_overlay` block on every PVO); DVU just makes that choice explicit and consistent across surfaces. The alternative — a pure model-unit display — was considered and rejected because cross-asset comparison ("vet vs. pick + pick") is impossible without anchoring picks somewhere, and the model has no natural pick valuation absent market data.

## Terminology Ratchet: DVU Decision Cards

Every structured evaluator output — Rookie Board entry, Roster Audit row, Trade Lab per-asset breakdown, Waiver Radar candidate, League Pulse team line — is now formally a **DVU Decision Card**. The schema (the universal decision card schema referenced in `system-design.md` "No Mystery Rankings" and Phase 8) gains two required fields:

- `dvu_value: float` — the asset's value in DVU at the time the card was generated.
- `dvu_peg_version: string` — the timestamp/version of the peg used (so a card is reproducible against the same market state).

The trade `verdict` field stays banned per the Field Ratchet in `system-design.md`. **"DVU Decision Card" is the *name* of the card; it is not a re-introduction of `verdict` under a new label.** The decision-support fields on a DVU Decision Card are unchanged: `delta_status` for trades, `signal` for roster, `top_drivers`, `risk_flags`, `counter_argument`, `caveats`, `model_grade`.

This is a terminology ratchet only. The underlying schema gains two fields (`dvu_value`, `dvu_peg_version`) and gains a name. `system-design.md`, `agent-execution-plan.md`, and `validation-gates.md` will be updated in a follow-up doc-only PR to reflect "DVU Decision Card" wording where they currently say "decision card."

## Credentials & Secrets

No credential of any kind ever lives in code, in tracked files, in commit messages, or in PR descriptions.

| Credential | Where it lives | How code reads it |
| --- | --- | --- |
| Databricks PAT | Databricks-managed user token; or `DATABRICKS_TOKEN` env var for local CLI | `databricks-sdk` reads from env / config file |
| Databricks Workspace URL | `DATABRICKS_HOST` env var | `databricks-sdk` |
| AWS S3 bucket / region | Databricks-managed via Unity Catalog external location | not directly read by code |
| PFF subscriber session | Databricks Secret in scope `dynasty-genius/pff` | adapter reads via Databricks SDK secrets API |
| PlayerProfiler subscriber session | Databricks Secret in scope `dynasty-genius/playerprofiler` | same |
| KTC scrape session (when applicable) | Databricks Secret in scope `dynasty-genius/ktc` | same |
| GitHub PAT (for `gh` automation) | OS keychain (existing) | `gh` CLI |

For local-file dev mode, secrets fall back to `~/.config/dynasty-genius/<source>.env` (gitignored) read via `python-dotenv`. The same env-var names are used in both modes so adapter code is unaware which substrate it is running on.

`.gitignore` already enforces `.env`, `.env.*`, `*.env`, `*.pem`, `*.key`, `*credential*`, `*secret*`. A future contract test (Step 0.2 or later) will scan tracked diffs for credential-shaped strings (`databricks_token`, `aws_secret_access_key`, `pff_session`, etc.) and fail the PR if any literal pattern appears.

## Migration Path

The Lakehouse pivot does not happen in one PR. Phase ordering:

| Phase | Substrate state | Notes |
| --- | --- | --- |
| **Today** (post Step 0.1) | Local files only. `app/data/cache/raw/` for snapshots, `app/data/models/runs/` for artifacts, `validation_report.json` as committed JSON. | What ships now. |
| **Step 0.2** | Unchanged substrate; CI / test scaffolding lands. | No infrastructure cost yet. |
| **Migration Phase M.1** | Unity Catalog `gen_alpha` provisioned. Bronze tables created for Sleeper and `nfl_data_py`. Adapters dual-write (local + bronze). | Validates the substrate without committing to it. |
| **Migration Phase M.2** | Silver normalized tables for Sleeper and `nfl_data_py`. Identity mapping migrates to `silver.identity_canonical_mapping`. | Production cuts over to read silver. Local files still written for fallback. |
| **Migration Phase M.3** | PFF, PlayerProfiler, RAS, KTC adapters land directly into bronze (no local-only path). MLflow tracks all retrains. | Paid sources skip the local stage. |
| **Migration Phase M.4** | Engine A and Engine B retrain pipelines read from silver, write artifacts + validation reports to gold. DVU peg job goes live. | Local model pickles deprecated. |
| **Migration Phase M.5** | Frontend reads `gold.decision_cards` via API. Local file fallback retired. | Lakehouse-only. |

Each migration phase gets its own PR with its own validation gate. Until M.5 lands, the local-file path remains a working fallback — every adapter implements both modes behind the same `SourceAdapter` interface defined in `data-source-contracts.md`.

The Step 0–11 phases in `agent-execution-plan.md` are unchanged in *order* by this pivot — they describe domain progress (League Context, Identity, Engine A/B, etc.). The Migration Phases M.1–M.5 are a parallel substrate track that lands as each domain phase is ready to consume it. Concretely: M.1 lands as Phase 3 (Source Adapter Contract) starts; M.2 lands as Phase 2 (Identity) closes; M.3 lands as Phase 4 (Engine A Feature Expansion) needs paid sources; M.4 lands as Phase 6 (Engine B MVP) needs the gold output layer; M.5 lands as Phase 11 (Frontend) starts.

## Counter-Argument

This pivot adds non-trivial infrastructure cost to a one-user app. Honest tradeoffs:

- **Cost.** Databricks workspace + S3 storage + small periodic compute. For one user, this is real money relative to "zero" (local files). Justified only if the film-as-data and career-simulation workloads land — neither has been built yet. If those workloads don't materialize, the Lakehouse pivot is over-engineering.
- **Local dev velocity.** Iterating on a parser locally and seeing the result is faster on local files than round-tripping bronze writes. The migration path mitigates this by keeping local fallback through M.4, but eventually that fallback retires.
- **Single point of failure.** Today, an outage of `nfl_data_py` or PFF degrades one source. After migration, an outage of Databricks degrades everything. Mitigation: bronze tables are also S3-readable directly; in a Databricks outage we can fall back to reading parquet from S3 with a local Python process.
- **Reversibility.** Delta tables are parquet underneath. Walking back the pivot is "stop writing to bronze, resume writing to local files" — the bronze data remains as a frozen archive on S3. The pivot is not a one-way door.

## Track in Git (carries over from local-file era)

These rules survive the migration. They become more important, not less, as credentials move into Databricks secrets.

Track:

- Application code in `app/` and `scripts/`
- Planning, architecture, and decision docs in `docs/`
- Project context: `AGENTS.md`, `CLAUDE.md`, `README.md`
- Dependency manifests: `requirements.txt`
- Pointer files (e.g., `app/data/models/latest.json`) that name the canonical artifact in Delta / MLflow but never the bytes
- Composite-gate measurement scripts
- Small bootstrap fixtures under `tests/fixtures/` (≤ 1 MB per file)

Do **not** track:

- Raw scrape dumps, HTML/API caches, browser automation artifacts (already enforced by `.gitignore`)
- Model binaries above ~500 KB once Lakehouse is the source of truth (currently transitional — small Ridge pickles remain in git through Phase 0)
- Any credential or session file
- Parquet / Delta files (under `app/data/cache/` or anywhere else)

CI verifies on every PR:

```bash
git ls-files app/cache app/data/cache app/data/raw app/data/processed app/data/artifacts
# expected: only .gitkeep placeholders
```

A future contract test (Step 0.2 or later) extends this to detect credential-shaped strings in any tracked file, including PR descriptions and commit messages where possible.
