# Storage Strategy

Dynasty Genius is moving from local file/SQLite storage to a Databricks Lakehouse foundation.

The target split is:

- **Databricks Lakebase** for real-time transactional state, especially current DVU state and user-facing decision sessions.
- **Delta Lake governed by Unity Catalog** for analytical data, feature history, validation artifacts, Film-as-Data, and simulation inputs.

Local files remain acceptable only for code, docs, tiny bootstrap fixtures, and reviewable test artifacts. Production data must flow through the Lakehouse.

## Lakebase: Transactional State

Lakebase is the system of record for mutable app state:

- Current player DVU state
- David's active roster and pick inventory snapshots
- Trade decision sessions
- Source verification receipts
- Lakebase transaction verification flags used by the Anti-Speed Protocol

Runtime connection settings live in `app/config/lakebase_config.py` and are read from environment variables only. Secrets are never committed.

## Delta Lake: Analytical State

Delta Lake is the system of record for data used by Engine A, Engine B, compliance checks, simulations, and backtests.

Unity Catalog naming convention:

| Layer | Schema | Purpose |
| --- | --- | --- |
| Bronze | `gen_alpha.bronze` | Raw snapshots from Sleeper, PFF, Next Gen, PlayerProfiler, RAS, PFR, KTC, and manual exports |
| Silver | `gen_alpha.silver` | Cleaned identity-resolved metrics, source-ranked records, and DVU-normalized market overlays |
| Gold | `gen_alpha.gold` | Decision-ready PVOs, anchor locks, validation reports, and simulation-ready feature tables |

No process may write directly to Gold from raw or app input. Gold writes must come from Silver, and Silver writes must come from Bronze.

## Medallion Architecture for Dynasty Metrics

### Bronze

Bronze tables preserve source truth with minimal transformation:

- `gen_alpha.bronze.pff_player_metrics`
- `gen_alpha.bronze.nextgen_player_metrics`
- `gen_alpha.bronze.sleeper_rosters`
- `gen_alpha.bronze.playerprofiler_prospects`
- `gen_alpha.bronze.ktc_market_snapshots`
- `gen_alpha.bronze.film_events`

Bronze records must include `source_name`, `source_rank`, `ingested_at`, and raw source identifiers.

### Silver

Silver tables normalize identity, units, and DVU representation:

- `gen_alpha.silver.player_metrics_normalized`
- `gen_alpha.silver.adjusted_yac_rank1`
- `gen_alpha.silver.market_values_dvu`
- `gen_alpha.silver.prospect_features`
- `gen_alpha.silver.active_player_features`

Market data is allowed in Silver only as a price overlay or DVU-normalized comparison signal. It must not appear in Engine A or Engine B feature lists.

### Gold

Gold tables are decision-ready and governed:

- `gen_alpha.gold.player_value_objects`
- `gen_alpha.gold.trade_decision_cards`
- `gen_alpha.gold.anchors`
- `gen_alpha.gold.validation_reports`
- `gen_alpha.gold.simulation_inputs`

Gold tables must carry Unity Catalog partition metadata: `source_rank` and `compliance_tag`.

## Strategic Constants

The 2027 generational anchors are strategic constants in `gen_alpha.gold.anchors`:

| Player | Position | Floor |
| --- | --- | ---: |
| Jeremiah Smith | WR | 120 DVU |
| Arch Manning | QB | 120 DVU |

These floors are locked by SHA-256 hashes in `app/utils/lakehouse_governance.py`. Market fluctuations may change `market_overlay`, but they cannot depreciate the Gold anchor floor.

## Enforcement Rules

- Adjusted YAC used for RB elite exceptions must come from Rank 1 ground truth: PFF or Next Gen Stats.
- Rank 3 market data must never enter Engine A or Engine B feature tables.
- Gold writes without Silver provenance are rejected.
- Trade ACCEPT/REJECT signals require source-hierarchy verification and Lakebase transaction verification.
- Every valuation output carries `source_rank`, `compliance_tag`, and `compliance_header`.

## GitHub Rule

The repo tracks code, docs, schemas, tests, and small reviewable fixtures. It must not track Databricks exports, raw scrape dumps, secrets, cache files, or large Delta artifacts.
