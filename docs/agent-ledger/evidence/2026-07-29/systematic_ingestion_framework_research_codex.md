# Systematic ingestion frameworks and patterns — research findings

**Date:** 2026-07-29

**Lane:** Codex research / corroboration lane

**Status:** Findings only; uncommitted

**Layers served:** 1–2 (source acquisition through curated stores)

**Decision question:** Is there an established way to make ingestion systematic, and what would adopting it cost a one-user, one-league, laptop-first product?

## Executive summary

Yes. The established construct is a **stateful, replayable ingestion pipeline with explicit write semantics, boundary contracts, and executable quality gates**. It is not one product and it is not synonymous with orchestration.

The research supports six findings:

1. **The patterns are established and separable.** Extraction state, write disposition, replay/backfill, event-time handling, schema enforcement, orchestration, and data-quality assertions solve different failure classes. No surveyed framework owns all of them well.
2. **A connector platform is not compelled at this scale.** Airbyte and Meltano/Singer make the strongest case when connector reuse is the dominant problem. Airbyte's local deployment still creates Kubernetes in Docker and installs Helm charts. That is substantial machinery for three live APIs and a daily laptop cadence.
3. **A Python-native ingestion library is the closest framework-shaped fit, but is not proved necessary.** dlt directly implements cursor state, append/replace/merge, schema evolution/contracts, replay after interrupted loads, and local destinations. It still requires source-specific extraction logic and disciplined handling of state, keys, deletes, and load outcomes.
4. **The orchestrator is not the ingestion contract.** Airflow, Dagster, and Prefect can schedule, retry, backfill, record runs, and expose failures. They do not determine whether an API should be full-refreshed, appended, merged, or queried with overlap. Airflow is operationally disproportionate here; Dagster and Prefect are more plausible only if durable run history and scheduling observability justify another always-on subsystem.
5. **Data-quality tools do not make checks truthful automatically.** dbt, Great Expectations, Soda, pandera, and Dagster can execute real predicates, but each can be wired weakly. Dagster asset checks are non-blocking by default; a dbt data test passes when its query returns zero failure rows; any tool can be pointed at zero assets or given a vacuous predicate. A green result is evidence only when the check itself has been shown to fail.
6. **For this product, the pattern matters more than the framework.** The evidence does not establish that a platform migration would repay its dependency and operating cost. It does establish that any future ingestion approach—hand-written or framework-backed—needs the same minimum protocol: declared source/cadence/mode/key/cursor, persisted run and source state, idempotent replay, explicit backfill, boundary validation, measured quality assertions, a zero-work guard, and a dead-check signal.

**Decision implication, not an authorised design:** research supports adopting the systematic contract before adopting a broad platform. Among surveyed tools, dlt and pandera demonstrate that much of the contract can live in-process and local-first. Airbyte and Airflow are over-adopted for the stated scale unless future connector count or multi-user operations changes materially. A specific stack choice is **not established** by this research.

## 1. Coverage and evidence standard

### Surveyed

- Ingestion modes: batch, incremental/cursor-based, and log-based CDC.
- Destination semantics: replace/full refresh, append, merge/upsert, insert-only, and SCD Type 2.
- Reliability semantics: idempotency, replay, durable state, overlap windows, late-arriving data, and backfills.
- Historical correctness: event time, versioned facts, and point-in-time joins.
- Boundary controls: schema evolution, frozen contracts, domain predicates, and quarantine/failure choices.
- Ingestion/connector frameworks: dlt, Airbyte, Meltano, and Singer.
- Transformation contracts: dbt.
- Orchestration: Dagster, Apache Airflow, and Prefect.
- Data quality: Great Expectations, Soda, and pandera.
- Negative-control practices: valid/invalid fixtures, unit tests for rules, mutation testing terminology, synthetic/black-box checks, missing-signal alerts, zero-work guards, and gate propagation.
- Current upstream release tags for the ten named frameworks, captured 2026-07-29.

### Not surveyed

- Managed-service prices or enterprise contract terms.
- Connector-by-connector coverage for the product's specific external sources.
- Security review, supply-chain review, or license-law analysis.
- Performance benchmarks.
- Adoption/popularity rankings.
- Production trials, package installation, or failure injection against this repository.
- Credentialed Databricks behavior or spend.
- The census's specific SQL findings, cliff-age contradiction, or a proposed product architecture.

### Evidence labels

- **[UPSTREAM DOC]** means documentation maintained by the project or vendor. It establishes documented behavior, not independent proof of reliability.
- **[UPSTREAM RELEASE]** means the project's GitHub release record.
- **[UPSTREAM ISSUE]** means first-hand user/maintainer evidence of a specific failure, not an incidence rate.
- **[INFERENCE]** is this review's bounded conclusion from the documented architecture and the product constraints supplied in the request.

No adoption or benchmark claim is made. No vendor claim is presented as independent evidence. I did not install or run these frameworks, so operational-cost judgments are architectural inferences, not measurements.

## 2. The established ingestion pattern

### 2.1 Batch, incremental, and CDC answer different source questions

| Mode | Use when | What it captures | Principal failure mode |
|---|---|---|---|
| Full batch snapshot | Source is small, no reliable cursor exists, or deletions/current state matter | Current source state on each run | Cost and inability to reconstruct prior states unless snapshots are retained |
| Cursor/key incremental | Source exposes monotonic ID or reliable updated timestamp | New and updated rows after a saved cursor | Missed deletes; missed or duplicated rows around equal timestamps, clock skew, or state loss |
| Log-based CDC | Database exposes an ordered change log and low-latency/deletes matter | Inserts, updates, and deletes in log order | Log retention, connector offsets, source-specific privileges, snapshot handoff, and operational weight |

Meltano documents the distinction directly: log-based replication reads database logs and can identify inserts, updates, and deletes, while key-based incremental replication sees inserts and updates but not deletes. Full-table replication extracts all rows each run. **[UPSTREAM DOC]** [Meltano replication methods](https://docs.meltano.com/guide/integration/)

Debezium documents the database-specific CDC shape: an initial consistent snapshot followed by change events read from database logs, including delete and transaction metadata where the source supports it. **[UPSTREAM DOC]** [Debezium features](https://debezium.io/documentation/reference/features.html)

**Finding:** CDC is not a synonym for “incremental API polling.” For a small HTTP API without a change log, a cursor plus overlap window or a full snapshot is normally the relevant pattern. Installing a CDC framework cannot manufacture source semantics the source does not expose.

### 2.2 Write disposition must follow record semantics

dlt's documented decision model is representative:

- **Replace/full refresh:** destination becomes exactly what the source produced in this run.
- **Append:** new immutable events are added.
- **Merge/upsert:** mutable entities are reconciled by a primary or merge key.
- **SCD2:** changes are versioned so historical states remain queryable.

**[UPSTREAM DOC]** [dlt incremental loading and write dispositions](https://dlthub.com/docs/general-usage/incremental-loading), [dlt merge strategies](https://dlthub.com/docs/general-usage/merge-loading)

The important rule is semantic, not tool-specific:

- An immutable event such as a transaction naturally supports append, provided it has a stable event ID and duplicates are rejected.
- Mutable current state such as a roster or player profile requires replace or keyed merge.
- A changing dimension needed for historical reconstruction requires versioning, not an overwrite that erases what was known.
- A full snapshot may be the safest operation when the source is small and deletions cannot otherwise be observed.

**Finding:** “incremental” alone is under-specified. It must name the cursor, tie behavior, overlap policy, destination key, deletion behavior, and replay semantics.

### 2.3 Idempotency is a property of the write and state transition

An idempotent run can be repeated for the same logical interval without changing the correct result. Common mechanisms are:

- Upsert or delete-insert on a stable natural/source key.
- Append with a uniqueness constraint or deterministic event key.
- Partition replacement for a named interval.
- Commit ingestion state only after the destination write and validation succeed.
- Preserve raw response/load identity so a failed normalization or publish step can be replayed.

Airflow's best-practices documentation treats tasks like transactions, recommends UPSERT rather than INSERT during retries, and recommends reading/writing a specific partition instead of “latest” or wall-clock `now()`. **[UPSTREAM DOC]** [Airflow best practices 3.3.0](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

dlt documents safe rerun after a destination connection failure by continuing the outstanding load jobs from the current load package. **[UPSTREAM DOC]** [How dlt works 1.29.1](https://dlthub.com/docs/reference/explainers/how-dlt-works)

**Finding:** a scheduler retry is unsafe until the underlying operation is idempotent. Retries are amplification, not correctness.

### 2.4 Watermarks need an overlap and late-data policy

Two times must remain distinct:

- **Event time:** when the source says the event happened or record changed.
- **Processing time:** when this pipeline observed it.

A cursor is a source-progress watermark. It is not proof that no earlier event will arrive later. Apache Beam's model explicitly treats a watermark as an estimate of input completeness and requires an allowed-lateness/trigger decision; with the default zero allowed lateness, late data is discarded. **[UPSTREAM DOC]** [Beam programming guide](https://beam.apache.org/documentation/programming-guide/)

For periodic APIs, the analogous established pattern is:

1. retain a durable high-water mark;
2. query with a deliberate overlap/lag window;
3. deduplicate or merge by stable key;
4. measure late records and cursor regressions;
5. advance state only after a successful, validated write.

**Finding:** “last successful timestamp” is insufficient when timestamps can collide, records can be edited late, or clocks differ. A compound cursor such as `(updated_at, stable_id)` or a bounded re-read window is needed to define the edge.

### 2.5 Point-in-time correctness requires historical source state

Point-in-time correctness means a row computed for time `t` may use only information available at or before `t`. Feast describes its historical retrieval as scanning backward for the latest eligible feature value and preventing future values from leaking into training. **[UPSTREAM DOC]** [Feast point-in-time join behavior](https://docs.feast.dev/v0.11-branch/feast-on-kubernetes/user-guide/getting-training-features)

This requires more than a current-state table:

- source/event time;
- ingestion/observation time where relevant;
- stable entity key;
- version or validity interval;
- reproducible as-of join semantics;
- retained raw or versioned facts.

**Finding:** a “latest” overwrite can be correct for today's UI and simultaneously incapable of supporting historically honest training. That is a storage-semantic decision at ingestion time.

### 2.6 Schema evolution and contracts are different policies

Schema evolution answers what the pipeline does when the source shape changes. A contract states what is allowed.

dlt exposes explicit modes such as evolve, discard, and freeze; in freeze mode a new column raises a `DataValidationError`, surfaced through pipeline failure. **[UPSTREAM DOC]** [dlt schema contracts 1.29.1](https://dlthub.com/docs/general-usage/schema-contracts)

dbt model contracts constrain the shape of a transformed model, but dbt explicitly does not support contracts for sources, snapshots, or seeds. Its documentation also distinguishes contracts from data tests: contracts enforce shape; tests assert content. **[UPSTREAM DOC]** [dbt model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts)

The boundary needs separate decisions for:

- Missing required field.
- New optional field.
- Type change.
- Nullability change.
- Enum/domain expansion.
- Renamed or semantically redefined field.
- Malformed individual record versus malformed entire response.

**Finding:** automatic schema evolution is availability-friendly but correctness-hostile when semantic changes are accepted silently. A frozen schema is correctness-friendly but operationally brittle. The established answer is a declared per-boundary policy plus captured rejected evidence, not one global setting.

### 2.7 Backfill is a normal execution mode

A first-class backfill has:

- explicit source and logical interval;
- the same extraction/normalization/validation code as recurring runs;
- a declared interaction with the normal cursor;
- an idempotent destination disposition;
- reprocessing policy;
- concurrency/rate-limit bounds;
- run manifest and outcome;
- dry-run or enumeration where feasible.

Airflow 3.3.0 exposes date-range backfills with explicit reprocessing behaviors (`none`, `failed`, `completed`), concurrency limits, and dry-run enumeration. **[UPSTREAM DOC]** [Airflow backfill](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html)

Dagster models backfills over explicit asset partitions. **[UPSTREAM DOC]** [Dagster backfilling data 1.13.15](https://docs.dagster.io/guides/build/partitions-and-backfills/backfilling-data)

**Finding:** a one-off script that bypasses recurring validation and state semantics is not a backfill; it is an untracked alternate ingestion path.

## 3. Framework comparison

Current releases were captured from upstream GitHub on 2026-07-29. A release tag does not establish compatibility with this repository.

| Family / tool | Pinned release | Actually solves | Does not solve | Operational and ceremony cost | Fit signal for stated product |
|---|---:|---|---|---|---|
| dlt | [1.29.1](https://github.com/dlt-hub/dlt/releases/tag/1.29.1) | Python extraction resources, cursor state, append/replace/merge/SCD2, normalization, schema evolution/contracts, local and remote destinations, load packages | Source meaning, correct keys/cursors, useful domain checks, scheduling | Python dependency plus per-source resource code; local pipeline state and destination metadata must be protected; merge and nested-table semantics require care | **Plausible / not compelled.** Closest match to local Python and few sources |
| Airbyte | [2.0.0](https://github.com/airbytehq/airbyte/releases/tag/v2.0.0) | Connector catalog, source/destination configuration, sync modes, run UI/history, connector isolation | Correct source-specific semantics when connector lacks them; product domain validation; lightweight embedding | Local `abctl` requires Docker, creates a kind Kubernetes cluster, installs Helm and ingress; connector/version operations become another platform | **Low at current scale.** Connector breadth is unlikely to repay runtime weight |
| Meltano + Singer | [Meltano 4.2.2](https://github.com/meltano/meltano/releases/tag/v4.2.2) | Tap/target plugin composition, Singer protocol, full/key/log replication modes, catalogs, state IDs, schedules and logs | Tap quality uniformity, domain contracts, correctness of plugin-specific state/deletes | Project/plugin configuration, virtual environments, tap/target selection and upgrades, state backend; custom tap work if no suitable plugin | **Conditional.** Better when reusable taps/targets exceed custom API simplicity |
| dbt Core | [1.12.0](https://github.com/dbt-labs/dbt-core/releases/tag/v1.12.0) | SQL transformation graph, incremental models, snapshots, model contracts, data/unit tests | Extraction, HTTP cursors, source-boundary enforcement, job scheduler by itself | SQL project plus adapter and SQL engine; contracts add per-model metadata; warehouse execution may incur spend | **Complement only.** Not an ingestion replacement |
| Dagster | [1.13.15](https://github.com/dagster-io/dagster/releases/tag/1.13.15) | Asset graph, partitions/backfills, schedules/sensors, run history, asset checks | Extraction semantics and truthful predicates | Definitions/resources/assets/checks plus webserver/daemon for full scheduling; local filesystem/SQLite can persist history | **Conditional.** Strong semantics, meaningful ceremony for a few daily jobs |
| Apache Airflow | [3.3.0](https://github.com/apache/airflow/releases/tag/3.3.0) | Mature DAG scheduling, retry, backfill, concurrency, run history, broad integrations | Ingestion correctness, schema/domain semantics | Scheduler, DAG processor, API server, metadata database and DAG bundle are minimal architecture components; production operation adds database and health monitoring | **Low.** Disproportionate for one laptop and one daily owner |
| Prefect | [3.8.0](https://github.com/PrefectHQ/prefect/releases/tag/3.8.0) | Python flow/task orchestration, retries, schedules, deployments, UI/run state | Source and destination semantics; domain checks | Self-hosted server plus long-running `serve` process or worker; SQLite is documented for lightweight single-server use | **Conditional / lighter orchestration candidate.** Still another persistent control plane |
| Great Expectations | [1.19.1](https://github.com/fivetran/great_expectations/releases/tag/1.19.1) | Expectation definitions, validation results, checkpoints, actions/notifications, data docs | Scheduling and ingestion; proof that expectations are non-vacuous | Data Context, assets/batches, suites/definitions, checkpoints, stores/actions; significant object model per small pipeline | **Conditional.** Richer evidence than required unless reporting/history is valuable |
| Soda Core | [4.19.0](https://github.com/sodadata/soda-core/releases/tag/v4.19.0) | YAML/contract-style scans; freshness, schema, row-count, missing, duplicate and custom checks; process exit codes | Ingestion/orchestration; automatic proof that a threshold is meaningful | CLI/library plus data-source packages and YAML; Cloud/Library/OSS capability and licensing boundaries add evaluation burden | **Conditional.** Concise assertions, but edition/version surface needs care |
| pandera | [0.32.1](https://github.com/unionai-oss/pandera/releases/tag/v0.32.1) | In-process DataFrame schema/type/null/domain/custom checks, lazy error reports, pipeline decorators, generated valid data strategies | Scheduler, cursor, run history, freshness over time, source-to-target reconciliation by itself | Smallest conceptual layer here; schema code and explicit tests remain; no operational UI | **High pattern fit, not a platform.** Local boundary validation without another service |

### 3.1 Connector frameworks

#### dlt

Strengths:

- Implements the core write dispositions directly.
- Cursor state, lag windows, schema evolution/contracts, and refresh are first-class.
- Runs as Python and supports local destinations, matching local-first constraints.
- Load packages support resuming destination failures.

Costs and failure modes:

- Correct keys, cursor choice, and delete behavior remain the implementer's responsibility.
- Merge without keys can fall back to append; that is a dangerous configuration if misunderstood.
- State and local pipeline working data become protected operational assets.
- A full refresh can erase stored schema history depending on mode.
- The pipeline API documents that individual load-job terminal failures may require inspecting returned load information rather than assuming every problematic job raises. A wrapper must propagate the intended failure contract.

**[UPSTREAM DOC]** [dlt pipeline API](https://dlthub.com/docs/api_reference/dlt/pipeline), [dlt pipeline state and refresh](https://dlthub.com/docs/general-usage/pipeline)

#### Airbyte

Strengths:

- Best surveyed option when a maintained connector already expresses the needed source and destination behavior.
- Centralizes configuration, sync state, run history, and connector lifecycle.
- Supports full and incremental replication modes, with CDC on supported sources.

Costs and failure modes:

- The local installation is a platform: `abctl` creates Kubernetes via kind in Docker and installs Airbyte and NGINX with Helm.
- Connector capability is not uniform; cursor, primary-key, delete, and schema behavior remain connector/source specific.
- A custom or patched connector introduces its own SDK, image, release, and upgrade lifecycle.
- Upstream issues document installation and custom-image debugging failures. These demonstrate possible operational modes, not prevalence.

**[UPSTREAM DOC]** [Airbyte `abctl` local architecture](https://github.com/airbytehq/abctl)

**[UPSTREAM ISSUE]** [Helm installation failure example](https://github.com/airbytehq/airbyte/issues/45105), [custom local connector image debugging example](https://github.com/airbytehq/airbyte/issues/43893)

#### Meltano / Singer

Strengths:

- Clear protocol boundary between taps and targets.
- Explicit full-table, key-incremental, and log-based replication modes.
- State can be inspected, copied, merged, exported, and imported.
- Schedules and cross-plugin workflows are available without adopting Airbyte's Kubernetes runtime.

Costs and failure modes:

- Quality and maintenance vary by tap/target; the protocol does not guarantee source correctness.
- Without a stable state ID, `meltano el` starts from scratch. Without an active environment, `meltano run` does not generate or track state.
- Key-based incremental replication does not capture deletions.
- Per-source plugin configuration can exceed the ceremony of a small custom client when the source lacks a mature tap.

**[UPSTREAM DOC]** [Meltano replication](https://docs.meltano.com/guide/integration/), [Meltano CLI/state behavior](https://docs.meltano.com/reference/command-line-interface)

### 3.2 Transformation contracts: dbt

dbt is downstream of extraction. It contributes:

- model contracts for output column names/types;
- data tests whose SQL returns failing rows;
- unit tests with explicit mock inputs and expected outputs;
- incremental model and snapshot patterns.

It does not enforce the raw HTTP response boundary, own API state, or schedule itself. Contracts do not apply to sources.

dbt unit tests are a strong negative-control mechanism because fixtures can contain deliberately bad input and the expected transformation result is compared explicitly; failures produce exit code 1. **[UPSTREAM DOC]** [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests), [dbt data tests](https://docs.getdbt.com/docs/build/data-tests)

**Finding:** dbt is useful if SQL transformations already justify dbt. Adding it only to name an ingestion registry or validate Python-produced local files would introduce an adapter/engine boundary without solving extraction.

### 3.3 Orchestrators

#### Dagster

- Asset/partition semantics make lineage and bounded backfills explicit.
- Local persistent storage can use filesystem and SQLite.
- Asset checks return an explicit boolean and can attach metadata.
- **Important default:** a failed asset check does not block downstream materialization unless `blocking=True`.

**[UPSTREAM DOC]** [Dagster instance configuration](https://docs.dagster.io/deployment/oss/oss-instance-configuration), [Dagster asset checks](https://docs.dagster.io/guides/test/asset-checks)

#### Airflow

- Strong scheduled batch and backfill control.
- Best-practice guidance explicitly supports idempotent transactional tasks.
- Minimal architecture already includes scheduler, DAG processor, API server, metadata database, and DAG bundle.
- SQLite/standalone mode is for local development; production operation adds database upgrades, health checks, and component monitoring.

**[UPSTREAM DOC]** [Airflow architecture 3.3.0](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html), [Airflow installation](https://airflow.apache.org/docs/apache-airflow/stable/installation/index.html), [Airflow production deployment](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html)

#### Prefect

- Python-native flow/task syntax and retry/deployment semantics.
- Self-hosted SQLite is explicitly recommended for lightweight single-server deployment.
- A static `serve` process is documented as a simple option for small, regularly scheduled flows; work pools/workers add indirection for dynamic infrastructure.
- Client/server compatibility and database migrations remain operational responsibilities.

**[UPSTREAM DOC]** [Prefect server](https://docs.prefect.io/v3/concepts/server), [Prefect deployments](https://docs.prefect.io/v3/concepts/deployments)

**Finding:** the orchestrator decision should be driven by a demonstrated need for durable scheduling state, backfill control, dependency coordination, and run observability. It should not be used to compensate for undefined source semantics or vacuous checks.

### 3.4 Data-quality and expectation layers

#### Great Expectations

- Expectations return structured validation results.
- Checkpoints run validation definitions and actions can notify on failures.
- Offers richer evidence/history/reporting structure than an in-process assertion library.
- The object model—context, data source/asset/batch, expectation suite, validation definition, checkpoint, stores/actions—is material ceremony for a handful of files.
- Notification is configurable action behavior, not proof that a failed validation terminates the parent ingestion process.

**[UPSTREAM DOC]** [GX Checkpoints and actions 1.19.1](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/)

#### Soda

- Human-readable threshold assertions for row count, missing values, duplicates, schema, freshness, distributions, and custom SQL.
- The Python API documents explicit exit codes: 0 pass, 1 warn, 2 fail, 3 runtime issue.
- The CLI supports local scans; Cloud adds history/alerts and commercial capability.
- A non-matching check path can execute no checks. Therefore the caller still needs an executed-check-count guard.
- Current documentation mixes Soda Core, Soda Library/Cloud, contract beta, and licensing-specific capabilities. This research did not establish a single clean OSS capability matrix for release 4.19.0.

**[UPSTREAM DOC]** [Soda checks](https://docs.soda.io/sodacl-reference/metrics-and-checks), [Soda Python API exit codes](https://docs.soda.io/soda-library/python_api.html/), [Soda CLI check-path behavior](https://docs.soda.io/reference/cli-reference)

#### pandera

- Directly validates DataFrame columns, types, nullability, uniqueness, and arbitrary predicates.
- Can aggregate failures lazily and integrate at function boundaries.
- Can derive Hypothesis strategies that generate data satisfying a schema, useful for positive/property-based tests.
- Does not track scheduled freshness, run history, or source-vs-target completeness without surrounding code.

**[UPSTREAM DOC]** [pandera DataFrame schemas](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html), [pandera data synthesis](https://pandera.readthedocs.io/en/stable/data_synthesis_strategies.html)

**Finding:** for local DataFrame/CSV/SQLite boundaries, pandera covers the narrow validation problem with the least platform surface. GX and Soda add reporting and scan semantics when those capabilities are actually required. None replaces an end-to-end completion and absence signal.

## 4. The negative-control discipline

### 4.1 What the discipline is called

There is no single data-engineering trademark for this. The established practices come from several testing and reliability disciplines:

- **Positive and negative test cases:** known-valid input must pass; known-invalid input must fail.
- **Test the test / meta-testing:** the validation rule itself is executable behavior and receives unit tests.
- **Mutation testing:** deliberately alter production/rule logic and require the test suite to detect the mutation.
- **Synthetic or black-box monitoring:** exercise externally visible behavior rather than trusting internal “ran” signals.
- **Dead-man's switch / missing-signal alerting:** absence of the expected completion heartbeat is itself a failure.
- **Fail-closed gating:** invalid, errored, skipped, or zero-work validation cannot be translated into green.

Great Expectations' custom-expectation contribution guidance historically required at least one positive and one negative example case. **[UPSTREAM DOC, historical 0.18 guidance]** [GX positive and negative cases](https://docs.greatexpectations.io/docs/0.18/oss/guides/expectations/features_custom_expectations/how_to_add_example_cases_for_an_expectation/)

Python's mutmut project demonstrates the mutation-testing mechanism: it makes small code mutations, runs the relevant tests, and exposes surviving mutants for which a detecting test must be written. **[UPSTREAM DOC]** [mutmut workflow](https://github.com/boxed/mutmut)

Prometheus supports unit tests for alerting rules using synthetic input series and expected alerts. Its `absent_over_time()` function exists specifically to alert when an expected series has not existed for a time window. **[UPSTREAM DOC]** [Prometheus rule unit tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/), [Prometheus missing-signal functions](https://prometheus.io/docs/prometheus/latest/querying/functions/#absent_over_time)

Google's SRE guidance distinguishes black-box monitoring—testing externally visible behavior as a user would—from white-box internal telemetry, and notes that only end-to-end tests detect successful protocol responses carrying wrong content. **[UPSTREAM DOC]** [Google SRE monitoring systems](https://sre.google/sre-book/monitoring-distributed-systems/)

### 4.2 Minimum proof that a check can fail

A quality check is established only when all of the following are true:

1. **A predicate exists.** The observed value is compared with an explicit acceptance rule. Returning rows or a successful query is not an assertion.
2. **A known-good fixture passes.**
3. **A known-bad fixture fails for the intended reason.**
4. **The real runner propagates failure.** The same CLI/function/job invoked in production returns a failing status or blocks publication.
5. **Zero work cannot be green.** The runner asserts the expected checks/assets were discovered and executed; `0 checked` is failure unless zero is explicitly expected for that run.
6. **Errors and skips are distinct from pass.** Timeout, unknown, not-run, excluded, and unsupported are non-green terminal states.
7. **The schedule itself is observed.** An expected completion heartbeat carries logical interval, source, run ID, counts, and terminal status; its absence after the cadence deadline alerts.
8. **A periodic canary exercises the whole path.** A synthetic bad record, isolated fixture destination, or rule-unit test proves the deployed check still transitions to failure.
9. **Evidence is retained.** The run records what was enumerated, what executed, measured values, thresholds, rejected rows, cursor before/after, and publication decision.

**Finding:** freshness, volume, uniqueness, distribution, and schema monitors are useful checks, but they are not negative controls. The negative control proves those monitors can detect a known violation and that the surrounding workflow does not swallow the result.

### 4.3 What each failure class requires

| Failure class | Direct assertion | Negative control |
|---|---|---|
| Empty source or wrong path | `rows_seen > 0` or explicit source-specific expected-empty state | Point the test runner at an empty fixture and require failure |
| Check discovery silently finds nothing | Expected check IDs equal executed check IDs; count > 0 | Use a fixture config with missing target and require non-green |
| Schema drift | Required names/types/nullability/domain | Add/remove/change a fixture field and require failure/quarantine |
| Duplicate replay | Stable-key uniqueness and repeat-run equality | Run same logical interval twice and compare destination |
| Cursor gap | Source interval coverage and cursor monotonicity | Inject equal/late timestamps across the boundary |
| Missed deletion | Source-vs-destination reconciliation or tombstone handling | Delete a fixture source row and require target removal/version close |
| Stale source | Source event-time age against declared cadence | Freeze source timestamp while scheduler continues |
| Job never ran | Completion heartbeat by deadline | Suppress heartbeat and require missing-signal alert |
| Check returns measurement but no verdict | Explicit comparison and nonzero exit/block | Feed a violating measurement and assert terminal failure |
| Downstream publish despite failed check | Gate on validated terminal result | Force validation failure and assert no curated publication |

### 4.4 Framework defaults that matter

- dbt data tests select failure rows; zero rows is pass. The query must actually target the intended relation, and discovery/execution counts remain external concerns.
- dbt unit tests compare fixture input to expected output and return a failing exit code on mismatch.
- Dagster asset checks require `blocking=True` to prevent downstream materialization after a failed upstream check.
- GX Checkpoint actions can notify based on validation failure; the parent process still must treat the result as a gate if publication must stop.
- Soda exposes fail/error exit codes, but non-matching check selection can execute zero checks.
- pandera raises on schema violations, but a caller can catch and suppress the exception.

**Finding:** no surveyed framework provides “provably non-vacuous checks” merely by being installed. Proof comes from rule tests, negative fixtures, execution-count assertions, fail-closed status propagation, and absence monitoring.

## 5. Fit to the stated product

Constraints supplied for this research:

- one user;
- one league;
- laptop execution;
- daily cadence;
- local-first preference;
- hard Databricks spend cap;
- currently few live external sources.

### 5.1 What is scale-independent

These obligations do not become optional because the product is small:

- Stable source identity and declared cadence.
- Explicit mode, key, cursor, and delete semantics.
- Idempotent repeat of a logical interval.
- Durable, inspectable state.
- Raw evidence or equivalent replay input.
- Boundary schema/domain validation.
- Point-in-time semantics where historical training is involved.
- Explicit backfill and reprocessing behavior.
- Run manifests and terminal state.
- Negative-control tests, zero-work guard, and missing-run detection.

### 5.2 What is likely scale-dependent

These capabilities may be waste at current scale:

- Kubernetes-based connector control plane.
- Multi-executor distributed scheduler.
- Dedicated metadata database solely for orchestration.
- Web UI requiring a daemon/server for a handful of daily jobs.
- Large connector marketplace when each needed source still requires custom semantics.
- Separate hosted data-quality control plane for one operator.
- Warehouse-first transformation framework when the authoritative path remains local files/SQLite.

### 5.3 Bounded fit conclusion

**Established:** the product needs the systematic pattern.

**Not established:** the product needs Airbyte, Meltano, dbt, Dagster, Airflow, Prefect, GX, Soda, or pandera specifically.

**Strongest fit signals from the survey:**

- dlt covers the largest share of ingestion-state/write/replay concerns without requiring a service platform.
- pandera covers local boundary assertions with the least operational surface.
- Prefect and Dagster are the more proportionate surveyed orchestrators if durable run history/backfills justify adopting one; they remain additional persistent systems.
- dbt is justified by a SQL transformation program, not by ingestion alone.

**Strongest anti-fit signals:**

- Airbyte's local Kubernetes/Helm runtime is disproportionate to the stated connector count.
- Airflow's minimum component architecture is disproportionate to a one-user laptop pipeline.
- GX's object model and hosted-quality features are likely ceremony unless durable validation documentation and action routing are explicit requirements.

**[INFERENCE]** The honest answer at this scale is “the pattern matters; the framework may not.” A small shared ingestion protocol implemented through ordinary Python and tests could be more reliable than a broad platform if it covers the scale-independent obligations and remains easier to inspect. Conversely, another set of source-specific scripts with no durable state contract would merely repeat the current failure class.

## 6. What adopting the established approach costs

The unavoidable cost is not primarily software installation. It is making source semantics explicit and testing them:

- Per source: source identifier, owner, declared cadence, availability grain, auth class, extraction mode, endpoint/stream, primary key, cursor, tie-breaker, overlap, delete behavior, destination disposition, schema policy, and backfill range.
- Per run: logical interval, attempt/run ID, code/config version, cursor before and after, requests/pages/rows/bytes, raw artifact identity, validation counts, rejected rows, destination commit, and terminal status.
- Per boundary: required fields/types/domains, missing/new-field policy, and bad-record versus bad-batch policy.
- Per check: predicate, positive fixture, negative fixture, expected target set, gate behavior, and last proven-failure timestamp.
- Operationally: state backup/restore, dependency updates, source API changes, alert delivery, and run-history retention.

Frameworks can standardize these mechanics, but they cannot eliminate the source-specific decisions.

Additional framework cost by family:

- **Connector platform:** runtime services, connector/plugin upgrades, source-compatibility debugging.
- **Orchestrator:** control-plane availability, metadata storage, daemon/worker health, migrations.
- **Transformation framework:** adapter/engine lifecycle, model metadata, SQL execution.
- **Quality platform:** expectation/check authoring, result store, action/gate integration, its own dead-check monitoring.

**Finding:** adopting all four families would create more control-plane surfaces than data sources. Layering should be justified one failure class at a time.

## 7. Implied work — explicitly not authorised

The research implies that the following must exist before a systematic ingestion approach can be evaluated or claimed. These are **not** a design, implementation plan, schema, repair, or licence to act:

1. A source-by-source semantics record covering mode, key, cursor, ties, overlap, deletes, write disposition, cadence, and backfill.
2. A framework-neutral acceptance contract for run state, replay, publication gating, and retained evidence.
3. A negative-control contract requiring positive/negative fixtures, expected check enumeration, fail-closed statuses, and a missing-run signal.
4. A bounded proof-of-fit, if David later authorises one, comparing the lightest credible implementation with one framework candidate on a representative mutable source and append-only source.
5. Explicit cost ceilings for added services, local state, dependency count, maintenance, and any warehouse execution.

No specific framework adoption, proof of concept, migration, or product change is authorised by this artifact.

## 8. Further questions this research could not establish

- Do maintained connectors exist for every product source with the exact endpoints, cursor semantics, and fields required?
- Which sources expose stable IDs, updated timestamps, deletion markers, or historical endpoints?
- What maximum tolerated data loss and recovery time apply to local ingestion state?
- Is a daily laptop job expected to run while the laptop is asleep or offline?
- Is a durable UI/run history valuable enough to operate an orchestrator service?
- Must validation failures quarantine individual rows, reject the batch, or preserve both raw and rejected records?
- Which datasets require point-in-time historical reconstruction versus current-state replacement?
- What is the allowed late-arrival window for each source?
- Which checks should block curated publication versus warn?
- What exact evidence must a backup/restore exercise prove? The separate restore drill remains unauthorised and was not started.

## 9. Caveats

- All capability descriptions are from upstream/vendor-maintained documentation unless marked as an issue or inference.
- Upstream documentation establishes intended behavior, not reliability in this repository.
- Release tags were current when queried on 2026-07-29 and may move.
- Airbyte's latest GitHub platform release was 2.0.0 despite later connector and deployment-tool activity; this survey did not resolve Airbyte's platform-versus-connector version taxonomy.
- Great Expectations' positive/negative custom-expectation citation is explicitly historical 0.18 guidance; the current 1.19.1 checkpoint behavior was sourced separately.
- Soda's current public documentation mixes product generations and commercial/OSS surfaces. A precise 4.19.0 OSS capability and licensing audit remains not established.
- No framework was installed or executed. Dependency weight and ceremony are qualitative architectural judgments.
- No credentialed Databricks operation occurred.

## 10. Primary source index

### Ingestion and CDC

- [dlt incremental loading 1.29.1](https://dlthub.com/docs/general-usage/incremental-loading)
- [dlt merge loading 1.29.1](https://dlthub.com/docs/general-usage/merge-loading)
- [dlt schema contracts 1.29.1](https://dlthub.com/docs/general-usage/schema-contracts)
- [dlt pipeline API 1.29.1](https://dlthub.com/docs/api_reference/dlt/pipeline)
- [dlt internal load/replay behavior](https://dlthub.com/docs/reference/explainers/how-dlt-works)
- [Airbyte local deployment CLI](https://github.com/airbytehq/abctl)
- [Airbyte replication modes](https://airbyte.com/blog/understanding-data-replication-modes)
- [Meltano replication methods](https://docs.meltano.com/guide/integration/)
- [Meltano CLI and state](https://docs.meltano.com/reference/command-line-interface)
- [Singer specification summary](https://hub.meltano.com/singer/spec/)
- [Debezium CDC features](https://debezium.io/documentation/reference/features.html)

### Time and historical correctness

- [Apache Beam watermarks and late data](https://beam.apache.org/documentation/programming-guide/)
- [Feast point-in-time historical joins](https://docs.feast.dev/v0.11-branch/feast-on-kubernetes/user-guide/getting-training-features)

### Transformation and orchestration

- [dbt model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
- [dbt data tests](https://docs.getdbt.com/docs/build/data-tests)
- [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests)
- [Dagster asset checks](https://docs.dagster.io/guides/test/asset-checks)
- [Dagster local/persistent instance configuration](https://docs.dagster.io/deployment/oss/oss-instance-configuration)
- [Airflow best practices 3.3.0](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Airflow architecture 3.3.0](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html)
- [Airflow backfill 3.3.0](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html)
- [Prefect server v3](https://docs.prefect.io/v3/concepts/server)
- [Prefect deployments v3](https://docs.prefect.io/v3/concepts/deployments)

### Quality, negative controls, and dead-check detection

- [Great Expectations Checkpoints and actions 1.19.1](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/)
- [Great Expectations historical positive/negative example guidance](https://docs.greatexpectations.io/docs/0.18/oss/guides/expectations/features_custom_expectations/how_to_add_example_cases_for_an_expectation/)
- [Soda checks](https://docs.soda.io/sodacl-reference/metrics-and-checks)
- [Soda programmatic scan exit codes](https://docs.soda.io/soda-library/python_api.html/)
- [pandera DataFrame schemas](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html)
- [pandera data synthesis](https://pandera.readthedocs.io/en/stable/data_synthesis_strategies.html)
- [mutmut mutation-testing workflow](https://github.com/boxed/mutmut)
- [Prometheus unit testing for alert rules](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/)
- [Prometheus `absent_over_time`](https://prometheus.io/docs/prometheus/latest/querying/functions/#absent_over_time)
- [Google SRE: black-box versus white-box monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
