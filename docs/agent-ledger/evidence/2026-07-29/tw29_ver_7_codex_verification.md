# TW29-VER-7 — Codex adversarial verification

**Date:** 2026-07-29  
**Scope:** findings only; no repair, spec, implementation, commit, schedule change, refresh, or
backup drill.  
**Evidence posture:** the four claims were handed to this lane. Agreement is **corroboration**, not a
second independent measurement. The work below is valuable where it refutes or narrows them.

## Disposition

| Claim | Disposition | What survives |
| :-- | :-- | :-- |
| 1. Transactions never called; activity is a constant | **FALLS as written** | No transaction ingestion/consumer exists in current tracked product code; the activity component is a literal `0.0` and is published as though measured. |
| 2. Draft capital never ingested; root layer 1; Engine B permits training absence | **FALLS as a compound claim** | Engine B's training exclusion is permitted. The blanket “never ingested / root layer 1” diagnosis is false. |
| 3. 113 fabricated Engine-A provenance labels on a path where no engine ran | **STANDS, BUT NARROWED** | The count and fabricated DVS provenance stand. “No engine ran” is false: Engine B produced the projection; Engine A and the DVS formula did not run. |
| 4. Two subsystems failed silently: 07-27 slip and four-day compliance non-run | **PARTLY STANDS, materially narrowed** | The schedule miss and four failed audit dates stand. “Two subsystem failures,” “silent,” and “has not truly run” are broader than the evidence supports. |

---

## Claim 1 — FALLS as written

### Refutation: the endpoint was called

The repository's durable July 6 ledger records a live, read-only call to
`GET /league/{league_id}/transactions/{round}` against David's league. Round 1 returned trades,
waivers, free-agent and commissioner events; rounds 0 and 18 returned empty arrays
(`docs/agent-ledger/2026-07-06.md:138`).

That directly refutes **“has never been called in this product's history.”** The morning search
proved that the endpoint string never entered tracked Python source; it did not prove no call ever
occurred. The documented probe is the counterexample.

### What still stands

- Current product ingestion does not implement the endpoint. `app/data/sleeper.py` enumerates the
  production Sleeper calls and has no transactions method; a current-tree exact endpoint search and
  a reachable-ref/reflog history regex search found no implementation.
- No persisted transaction stream or transaction consumer was found.
- `activity_recency_score` is exactly `0.0` at
  `src/dynasty_genius/league_opportunity_map.py:185`, then participates in the sum and serialized
  component map. This corroborates the handed-off constant finding.

### Could not establish

- No repository inspection can prove that no other ad hoc/manual call occurred outside the durable
  record. The only absolute claim tested here is already refuted by the July 6 probe.
- “Never ingested into the product” is supported for the current code and reachable tracked history,
  but not for every deleted/untracked local experiment that may ever have existed.

---

## Claim 2 — FALLS as a blanket root-layer diagnosis

### Refutation 1: draft capital is already ingested

`app/data/training/prospects_with_outcomes_v3.csv` contains `pick`, `round`, `nfl_pick`, and
`nfl_round`, including provenance companions. `scripts/build_w2_features.py:480,493` names
`nfl_data_py` as the source. Therefore **“draft-capital fields were never ingested” is false for the
product as a whole.**

### Refutation 2: much of the active population already has joinable ingested capital

On the 2026-07-29 served artifact (`captured_at 2026-07-29T13:30:09.001183+00:00`):

- 501 rows have `valuation.engine_path == "ENGINE_B"`.
- Joining their GSIS-shaped player id to `prospects_with_outcomes_v3.csv.gsis_id` finds **373 / 501**
  rows with already-ingested, non-null `pick` and `round`.
- Yet all 501 served Engine B rows still have null `nfl_draft_pick` / `nfl_draft_round`.

Rerun:

```bash
.venv/bin/python3.14 -c 'import json,csv; p=json.load(open("app/data/valuation_runtime/universe_pvo_runtime.json")); b=[r for r in p["players"] if (r.get("valuation") or {}).get("engine_path")=="ENGINE_B"]; a={r["gsis_id"]:r for r in csv.DictReader(open("app/data/training/prospects_with_outcomes_v3.csv"))}; m=[a.get(str(r.get("dg_player_id") or r.get("player_id") or "")) for r in b]; print(len(b),sum(bool(x and x.get("pick") and x.get("round")) for x in m))'
```

For those 373 rows, the absence is not rooted in non-ingestion. The active PVO producer reads only
Engine B feature rows and never joins the already-ingested rookie table
(`scripts/build_universe_pvo_batch.py:_active_pvos_from_engine_b`). The PVO assembler materializes
draft fields only from `features["pick"]` / `features["round"]`
(`src/dynasty_genius/pvo_assembler.py:502-503`). This is a **curation/materialization/join boundary
(layer 2)** for at least that population.

The remaining 128 / 501 served rows did not join to that rookie table in this probe. Their exact root
is not established here; the population is therefore mixed, not uniformly layer 1.

### What still stands

Engine B's 33-column training set contains no draft-capital feature. That is permitted by
`docs/governance/01-north-star-architecture.md:227`, which bars rookie-only pre-NFL features from
active-player training unless explicitly modeled as a prior. This is a **training-feature
permission**, not permission or prohibition for serving/materialization.

A read-only schema check of the live Sleeper `/players/nfl` response on 2026-07-29 found no key name
containing `draft`, so Sleeper is not presently supplying an obvious draft-capital field for the
league snapshot adapter. That does not erase the already-ingested `nfl_data_py` capital above.

### Could not establish

- Whether all 128 unmatched active rows lack draft capital at every available source.
- Whether active-serving draft fields are intended requirements now; `01` says the PVO required
  fields apply “as the system matures,” and this task does not make a product ruling.

---

## Claim 3 — STANDS, BUT “no engine ran” is false

### Corroborated count and provenance defect

The refreshed 2026-07-29 artifact corroborates the handed-off shape:

- **113** rows have `valuation.engine_path == "ENGINE_B"` and top-level `dvs_engine == "A"`.
- All 113 have null `dynasty_value_score` and null `xvar`.
- Their nested valuation is `MODEL_UNCERTAIN`.

The source contract defines `dvs_engine` as **which engine produced DVS** and says it is populated
when DVS is non-null (`src/dynasty_genius/models/player_value_object.py:82-83`). The fallback branch
sets DVS null and nevertheless writes `"A"` (`src/dynasty_genius/pvo_assembler.py:449-451`).
Therefore the Engine-A DVS provenance label is fabricated. This is distinct from the false prose
caveat written immediately below it.

The behavior is not accidental drift only: `tests/contract/test_phase14_dvs.py:95-106` explicitly
expects `dvs_engine == "A"` even when Engine A inputs are absent, while the governing model-field
comment says the label names the engine that produced DVS. The test pins the contradiction.

### Refutation/narrowing: Engine B did run

The branch is reachable only inside:

```python
if engine_b_resolved and _below_games_gate:
```

at `src/dynasty_genius/pvo_assembler.py:415`. The current affected rows carry non-null
`projection_2y`, an Engine B `model_version`, `model_grade == "ACTIVE_B"`, and
`valuation.engine_path == "ENGINE_B"`.

Accurate statement: **Engine B produced a forecast, but the below-games gate prevented Engine B DVS
normalization; Engine A did not run; no DVS was produced; the code still labeled DVS provenance
`"A"`**. The source comment “no A or B” is itself false about the surrounding execution state.

---

## Claim 4 — factual cores stand; compound “silent failures” claim does not

### 07-27 schedule miss — corroborated, but not a proved subsystem failure

The local logs carry:

- league capture run `league-20260727T233130Z`
  (`app/data/logs/league_capture.out.log:12`);
- backup start `2026-07-27T23:31:30.903041+00:00`
  (`app/data/logs/backup_irreplaceable.out.log:350`);
- PVO source snapshot `2026-07-27T23:31:42.976508+00:00`
  (`app/data/logs/pvo_refresh.out.log:156831`).

`23:31Z` is 19:31 EDT, about ten hours after the registered morning schedule. The slip stands.

What does **not** follow:

- the jobs did not fail; they completed late;
- the cause (sleep/wake deferral, manual run, or something else) is not established;
- intended dependency ordering on the collapsed run is not established;
- “silent” is false if it means no evidence existed—the timestamps are in the logs. What was absent
  was a cross-day lateness alert/summary.

### Compliance — four failed scheduled dates stand; “not truly run” is unproved

Read-only GitHub Actions inspection at 09:47 EDT showed:

- last successful scheduled run: **2026-07-24**, run `30104934179`;
- four consecutive scheduled workflow failures: **07-25, 07-26, 07-27, 07-28**;
- on 07-28, the static `SQL governance audit` job passed while `Sovereign Unity compliance audit`
  failed;
- its audit step ran **254 seconds** and authenticated successfully, then reported five
  `"Unknown error"` results.

The mechanism is corroborated: `scripts/codex_audit.py:93-114` waits 50 seconds, recognizes only
`SUCCEEDED`, and converts a non-terminal state with no error to `"Unknown error"`. Five waits explain
the ~254-second step.

But **“has not truly run for four days” is not established**:

- the script ran and authenticated on all four dates;
- it submitted statements and stopped observing each after the 50-second wait;
- it does not persist statement ids or poll, so the repository cannot tell whether any statement
  later completed server-side;
- it cannot tell whether the underlying Databricks data is compliant or defective.

The strongest warranted claim is: **the five Databricks-backed checks have produced no observed,
terminal compliance result since July 24.**

### “Silent behind healthy surfaces” — narrowed

The GitHub workflow itself was visibly red, and the failure was recorded in the durable ledger on
July 28 (`docs/agent-ledger/2026-07-28.md:1394-1403`). It was therefore not silent in an absolute
sense. However, the same day's telemetry closeout still declared all pipelines healthy
(`docs/agent-ledger/2026-07-28.md:1414-1417`). The established defect is **health aggregation that
did not carry cross-day schedule lateness or the separate red compliance workflow**, not two
literally invisible subsystem failures.

### Could not establish

- 07-27 slip cause or dependency-order correctness.
- Current Databricks warehouse/catalog truth.
- Whether timed-out statements later reached terminal states.
- Whether David saw a notification before the July 28 durable ledger diagnosis.

---

## Final verification answer

- **Falls:** Claim 1's “never called”; Claim 2's blanket “never ingested / root layer 1.”
- **Stands:** Claim 1's hardcoded activity component; Claim 2's Engine B training permission;
  Claim 3's 113-row fabricated DVS provenance label.
- **Stands only after narrowing:** Claim 3 must say Engine B forecast ran but no DVS/Engine-A
  computation did; Claim 4 must say late completion plus four dates without an observed terminal
  compliance result, with a health-aggregation gap.
- **Not established:** the absolute runtime-history negative beyond durable records; a uniform root
  for all 501 active rows; 07-27 cause/order; underlying Databricks product truth; later server-side
  completion of the timed-out statements; absolute silence to David.
