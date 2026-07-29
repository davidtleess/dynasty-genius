# Layers 1–2 Inventory — Claude lane, working artifact v1

**Thread:** TW29-INV-1, opened by David 2026-07-29 (*"okay on 1/2"*), against his 2026-07-28 21:13
framing: **what we ingest · what is missing · what is stale · what is silently a constant.**

**Status:** IN PROGRESS. Thread 3 complete; threads 4, 1, 2 not yet started.

**Standing boundary:** findings only. `05` §3 — *a conclusion is not a licence to fix.* Nothing in
this document is authorisation to repair, scope, or spec anything. Uncommitted; no push word exists.

**Grading vocabulary used throughout:** **PROVED** = established by a rerunnable check recorded here.
**NOT PROVED** = observed but the cause or consequence is not established. The distinction is not
decorative — `05` §4 records this lane asserting a root layer from an absence, and this artifact is
written to avoid repeating it.

---

## ⚠ Contamination disclosure — read before trusting thread 4

The method for this inventory was **measure first, read prior work second**, so that earlier lanes'
figures land as corroboration rather than as seed.

**I broke that for thread 4, accidentally, and I am recording it rather than quietly proceeding.**
While grepping `docs/agent-ledger/2026-07-28.md` for thread-3 corroboration, the search returned
adjacent lines containing Gemini's full prior **diagnosis of the red compliance check** (line 1411).
I read it before taking any measurement of my own on that thread.

**Consequence, stated honestly:** my thread-4 result cannot be reported as an independent blind
measurement. It will be labelled **"verification of a prior diagnosis"**, which is a weaker claim,
and I will say which parts I confirmed from source versus which I merely failed to contradict.
Threads 1, 2 and 3 are unaffected — no prior figure for them was read before measuring.

---

## ⚖ RECONCILIATION with the independent review — read before any finding below

Codex's adversarial pass is at `docs/agent-ledger/evidence/2026-07-29/tw29_ver_7_codex_verification.md`.
**I verified its two load-bearing counter-facts myself rather than accepting them**, and both hold.
Dispositions below are mine; the section headings further down are corrected in place.

*(Citation status, stated so this record does not overclaim its own evidence: that review artifact is
**on disk and UNCOMMITTED** at the time this file is committed. It belongs to the review lane and is
not mine to commit — David's word named the inventory and the drill evidence, and it has been listed
to Tower rather than swept in. **The verdicts and their reasoning are quoted inline below and in each
corrected section, so this record stands on its own if that file never lands.**)*

| Its verdict | My disposition | Basis |
| :-- | :-- | :-- |
| Claim 1 **falls as written** | **CONCEDED IN FULL** | Verified `docs/agent-ledger/2026-07-06.md` — Codex probed `GET /league/{league_id}/transactions/{round}` against David's league live; round 1 returned trades and waivers. |
| Claim 2 **falls as a root-layer diagnosis** | **CONCEDED IN FULL — this is the serious one** | Reproduced independently: **373 of 501** Engine B rows join `prospects_with_outcomes_v3.csv` on `gsis_id`, and **all 373 carry non-null `pick` AND `round`.** |
| Claim 3 **stands, narrowed** | **CONCEDED, and its addition adopted** | Verified `pvo_assembler.py:415` — the branch sits inside `if engine_b_resolved and _below_games_gate`. Engine B **did** run. |
| Claim 4 **partly stands** | **CONCEDED on "silence"; artifact wording was already narrower than my verbal report** | The GHA workflow was visibly red and the 07-28 ledger recorded it. |

### Why claim 2 falling matters more than the others

I concluded **"root layer is LAYER 1, and this is newly established."** It is **wrong**, and the way it
is wrong is the specific failure this document was written to avoid.

I checked two places draft capital could have been — the live Sleeper snapshot and the Engine B
training set — found it in neither, and concluded non-ingestion. **I never checked whether it already
existed elsewhere on disk and was simply not joined.** It does. `prospects_with_outcomes_v3.csv`
carries `pick`, `round`, `nfl_pick`, `nfl_round` with provenance companions, sourced from
`nfl_data_py` (`scripts/build_w2_features.py:480,493`), and 373 of the 501 served Engine B players
join straight to it.

**Corrected root layer: a layer-2 join/materialization gap for at least 373/501, not a layer-1
ingestion gap.** Mechanism verified at `src/dynasty_genius/pvo_assembler.py:501-503` — the draft
fields materialize **only** from `features["draft_class"] / ["pick"] / ["round"]`, and the active
producer never joins the rookie table into that feature dict. The remaining **128** did not join in
this probe and **their root is not established** — the population is **mixed**, not uniform.

**This is the same error recorded in `05` §4, committed by the same lane, in the document written to
prevent it.** `05` §4's closing line reads: *"The check is cheap: the measurement that broke the
premise ran in under a minute once someone thought to run it."* The join that refuted me runs in
under a second. I did not think to run it, and an independent reviewer did. **The doctrine's own
argument for independent review is this entry.**

### What the review added that I did not find

`tests/contract/test_phase14_dvs.py:95-106` **asserts `pvo.dvs_engine == "A"` in the no-Engine-A
case.** Verified. The fabricated provenance label is not drift — it is **pinned by a committed
contract test**, so any correction breaks that test deliberately rather than incidentally. I found the
defect; the review found that it is specified. That is the stronger finding.

### Where my own grading held up

The review's *"could not establish"* items for thread 3 — the cause of the 07-27 slip and whether
dependency ordering survived — are items **this artifact had already marked NOT PROVED before the
review ran** (§3.2). Those are corroborations of my stated limits, not refutations. The
proved/not-proved vocabulary did its job in thread 3; it failed in thread 1 precisely where I stopped
grading and asserted.

---

## Thread 3 — the 2026-07-27 scheduled data jobs and their run times

**Layer: 1–2, directly.** No layers 1–2 dependency check is owed; this thread *is* that check.

### 3.1 What is scheduled (the ingest map)

Read from `~/Library/LaunchAgents/*.plist` via `PlistBuddy -c "Print :StartCalendarInterval"`, and
cross-checked against `launchctl list`. **Ten jobs loaded; all report last exit `0`.**

| Local time | Job | Script |
| :-- | :-- | :-- |
| 09:00 daily | `dynasty-fc-snapshot` | `scripts/run_fc_forward_capture.py` |
| 09:15 daily | `dynasty-feature-refresh` | `scripts/run_feature_refresh.py` |
| 09:20 daily | `dynasty-league-capture` | `scripts/run_league_snapshot_capture.py` |
| 09:30 daily | `dynasty-model-pvo-refresh` | `scripts/run_pvo_refresh.py` |
| 09:40 daily | `dynasty-market-divergence-refresh` | `scripts/run_market_divergence_refresh.py` |
| 09:45 daily | `dynasty-what-changed-report` | `scripts/run_what_changed_report.py` |
| 10:00 Tuesdays | `dynasty-realized-outcome-scoring` | `scripts/run_realized_outcome_scoring.py` |
| 10:15 daily | `dynasty-backup-irreplaceable` | `scripts/backup_irreplaceable_data.py` |
| 22:00 daily | `dg-cockpit-backup` | a cockpit shell script (outside the product pipeline) |
| every 30s | `dg-mail-carrier` | inert — paused by design, enable-flag absent |

Three `*-sync` plists are present on disk with a `.disabled` suffix and are **not** loaded.

### 3.2 FINDING 3-A — on 2026-07-27 the pipeline did not run on schedule. **PROVED.**

The morning jobs fired roughly **ten hours late**, together, in the evening.

| Evidence | Value | Source |
| :-- | :-- | :-- |
| League capture run id | `league-20260727T233130Z` | `app/data/logs/league_capture.out.log` |
| Backup `started_at` | `2026-07-27T23:31:30.903041+00:00` | `app/data/logs/backup_irreplaceable.out.log` |
| PVO `source_snapshot_captured_at` | `2026-07-27T23:31:42.976508+00:00` | `app/data/logs/pvo_refresh.out.log` |

`23:31:30Z` is **19:31 EDT**. The league capture (scheduled 09:20) and the backup (scheduled 10:15)
carry the **same timestamp to the second**, and the PVO refresh follows 12 seconds later. Every other
day in the window is regular: league capture is `T132000Z` (09:20 EDT) on 07-25, 07-26 and 07-28;
the backup is `T141500Z` (10:15 EDT) on 07-26 and 07-28.

**Rerun:**
```
grep -h 'league capture ok' app/data/logs/league_capture.out.log
grep -hE '"(started|finished)_at": "2026-07-2[678]' app/data/logs/backup_irreplaceable.out.log
```

**NOT PROVED:** the cause. The signature — several jobs collapsing onto one wake instant — is
consistent with launchd deferring missed calendar intervals while the machine slept, but no sleep/wake
log was consulted and no other hypothesis was excluded.

**NOT PROVED, and material:** whether pipeline **ordering** survived. The schedule encodes a
dependency chain (capture → refresh → PVO → divergence → what-changed). On a collapsed wake-fire the
09:20 and 10:15 jobs share a start second. Whether the downstream artifacts consumed the intended
upstream inputs that day is unestablished and is a real question, not a rhetorical one.

**One job did NOT slip:** the 09:00 FC snapshot carries `retrieved_at 2026-07-27T13:00:01Z` — 09:00
EDT, on time. So the outage window opens **after 09:00 and before 09:20** local.

### 3.3 FINDING 3-B — no surface carries a ten-hour slip *across days*. **PROVED, narrowed after review.**

*(Narrowing: the raw timestamps were in the logs all along, so "silent" in an absolute sense is wrong.
The established defect is **health aggregation that does not carry cross-day lateness** — not absent
evidence. The jobs also **completed late; they did not fail**, which §3.2 already stated correctly.)*

Every one of the ten jobs reports last exit `0`. `launchctl list` cannot distinguish "ran on time"
from "ran ten hours late." The status marker records `status: completed` and `sha256_verified: true`
for 07-27 without reference to when it was due.

**Corroborating and illustrating the gap simultaneously:** Gemini's 07-28 telemetry read
(`docs/agent-ledger/2026-07-28.md:1416`) states *"Scheduled Jobs: Healthy. All morning data jobs …
completed successfully with zero failures."* That statement is **accurate for 07-28** — I reproduced
the 07-28 on-time stamps independently. It is a **same-day** read, and the 07-27 slip is invisible to
it. **This is not an error by that lane; it is the absence of a cross-day miss-detection surface.**
The `02` backup law already names 26-hour staleness as degraded — that law binds the backup only, and
the automation for even that is a named pending follow-up.

### 3.4 FINDING 3-C — the feature refresh does nothing on 30 of 31 runs. **PROVED as behaviour; explicitly NOT a defect.**

`app/data/logs/feature_refresh.out.log` contains 31 lines: **30 × `noop`, 1 × `ok`.**

I nearly filed this as a broken job. It is not. `scripts/run_feature_refresh.py:6` states the runner is
*"gated on the source content hash (honest `noop` when the upstream source is unchanged)"* — the noop
is the design working correctly, and `:108` explicitly guards against a *false* noop. The upstream
(an `nflreadpy` season pull) genuinely does not change in the off-season.

**The finding is therefore not "the job is broken" but a cadence question:** a daily job against a
source that only changes in-season. `02` §Compounding-product lens requires cadence *"matched to the
data's real rate of meaningful change (and is season-aware — in-season ≠ off-season)."* **Whether that
is a mismatch worth changing is NOT PROVED and is not mine to decide** — and any scheduling change is
outside the boundary of this thread regardless.

**Rerun:** `sort app/data/logs/feature_refresh.out.log | uniq -c`

### 3.5 FINDING 3-D — the daily What-Changed model lane has reported a real model change once in 34 runs. **PROVED as counts; cause NOT PROVED.**

`app/data/logs/what_changed_report.out.log`, 34 logged runs:

| `model_status` | Runs |
| :-- | --: |
| `baseline_holding` | 16 |
| `vintage_changed_no_score_delta` | 15 |
| `model_multi_vintage_ambiguous` | 2 |
| **`ok`** | **1** |

`market_status` is `ok` on 34/34; `structural_status` is `ok` on 34/34.

**Presenting layer 6** (a David-facing daily surface). **Layers 1–2 dependency check, performed:**
I read `run_feature_refresh.py` and the feature log (§3.4) and established that the upstream feature
source is genuinely unchanged off-season and the noop is honest. **Result:** an unchanged model input
is sufficient to produce `vintage_changed_no_score_delta` without any defect existing anywhere.
**Conclusion: this is NOT established as a layers 1–2 hole, and the mechanism above is a plausible
benign explanation I did not disprove.** I am explicitly *not* concluding it is fine either — the
`model_multi_vintage_ambiguous` pair and the single `ok` are unexplained. **Recorded as an open
question, not a defect.**

### 3.6 FINDING 3-E — realized-outcome scoring has never produced a score. **PROVED.**

All three logged runs of the Tuesday job emit
`{"status": "noop", "noop_reason": "no_predictions_for_target", "decision_supported": false}`.

Consistent with the known accrual gate (forward PIT accrual ~Dec 2026) rather than a fault. **Cause
NOT independently PROVED here** — I read the noop reason, not the predicate that produces it.

### 3.7 Freshness at time of writing

`app/data/valuation_runtime/universe_pvo_runtime.json` → `captured_at 2026-07-28T13:30:04Z`;
`app/data/valuation/universe_market_divergence_latest.json` → `captured_at 2026-07-28T13:40:00Z`.
Both are yesterday's on-time run. **Not stale** — today's 09:00–09:45 window had not yet fired when
these were read (~08:55 EDT).

Backup marker `app/data/ops/backup_status_latest.json` → run `20260728T141500Z`, `status: completed`,
`sha256_verified: true`. Within the 26-hour law, which does not bite until ~12:15 today.

---

## Thread 4 — the red compliance check standing since 2026-07-25

**Layer: `governance` with a layer-2 target** (it audits the Databricks *gold* layer,
`gen_alpha.gold.genius_state`). The failure itself is a CI/monitoring defect, not a curation defect.

**⚠ Contaminated thread.** I read Gemini's diagnosis (`docs/agent-ledger/2026-07-28.md:1411`) before
measuring. Each item below is graded **INDEPENDENT** (I derived it from a source Gemini did not hand
me) or **VERIFICATION** (I confirmed a claim I had already read).

### 4.1 FINDING 4-A — the failure is real, dated, and isolated to one job. **INDEPENDENT. PROVED.**

From `gh run list --workflow codex_audit.yml --limit 30` — a source, not a summary:

- **24 consecutive scheduled successes, 2026-07-01 → 2026-07-24.**
- **4 consecutive failures: 07-25, 07-26, 07-27, 07-28.** Last success `30104934179` (07-24T15:21).
- **No 07-29 run yet** at time of writing; cron is `0 14 * * *` (10:00 EDT) per
  `.github/workflows/codex_audit.yml:19`.

The workflow has two jobs. **`SQL governance audit` (static, `codex_audit_sql.py`) is `success` on
every run including all four failures.** Only **`Sovereign Unity compliance audit`
(`codex_audit.py`, Databricks-backed) fails.** Verified on both the first failure (`30162646061`)
and the latest (`30376171931`), and against the last success.

### 4.2 FINDING 4-B — the mechanism, confirmed at the line. **VERIFICATION. PROVED.**

`scripts/codex_audit.py:90-96` calls `execute_statement(..., wait_timeout="50s")` and then tests
**only** `if response.status.state == StatementState.SUCCEEDED:`. There is no polling loop, no
`on_wait_timeout` argument, and no handling of the non-terminal `PENDING`/`RUNNING` states.

`:113-114` — the `else` branch reads
`response.status.error.message if response.status.error else "Unknown error"`. **A non-terminal
state carries no `.error`, so it prints exactly `"Unknown error"`.**

### 4.3 FINDING 4-C — the timing arithmetic. **INDEPENDENT. PROVED, and it resolves an apparent contradiction.**

The failed run's log shows all five tests failing within **one millisecond** of each other
(`16:05:12.943`–`16:05:12.944`), including the authentication line — which reads like an instant
failure and would falsify a timeout hypothesis.

**It does not, and the step timings prove why.** From `gh run view --json jobs`:

| Run | Step `Run Codex Compliance Audit` | Duration |
| :-- | :-- | --: |
| **Failure** `30376171931` | 16:00:59 → 16:05:13 | **254 s** |
| **Last success** `30104934179` (whole job) | 15:21:38 → 15:22:13 | **35 s** |

**254 s ≈ 5 queries × 50 s `wait_timeout` + overhead.** The identical log timestamps are a Python
stdout-buffering artifact — the process genuinely ran 254 seconds and flushed its output in 1 ms at
exit. When the warehouse responds (07-24), all five queries complete inside **35 seconds total**.

This is the quantitative confirmation the prior diagnosis asserted; I derived the 254 s independently
from the step timings rather than accepting the "~250 s" figure.

### 4.4 FINDING 4-D — the prior conclusion is HALF confirmed, and the other half is unobservable. **This is a correction, not a concurrence.**

The prior diagnosis concluded: **a broken check, not a product defect.**

- **First half — CONFIRMED.** The check *is* broken. It cannot represent a non-terminal statement
  state, and it reports one as `"Unknown error"`. That is a defect in `codex_audit.py` regardless of
  what Databricks is doing.
- **Second half — NOT PROVED, and NOT PROVABLE THROUGH THIS CHECK.** *"…not a product defect"*
  requires knowing the queries would have succeeded given time. **The code discards the evidence
  needed to know that.** A cold warehouse, a suspended warehouse, a quota block, a permissions
  change, a renamed table, or genuinely absent `gen_alpha.gold.genius_state` rows would **all**
  present identically through `:113-114` — as `"Unknown error"` after a 50 s wait.

**Conclusion recorded, per `05` §3:** the check's own defect is what makes the underlying question
unanswerable. Whether a product defect also exists is **UNKNOWN**. Calling it "not a product defect"
overstates what the evidence can carry. *(The warehouse's actual state is deliberately unverified:
that needs a credentialed Databricks call, which is both David-gated spend and outside a findings-only
inventory.)*

### 4.5 FINDING 4-E — four days with no observed terminal compliance result. **INDEPENDENT. PROVED, narrowed after review.**

The five checks are, by their own names in `codex_audit.py`: `genius_state` SSoT accessibility ·
Governance Rules Validation · DVU Anchor Integrity · Status Classification Distribution ·
**Source Rank Distribution (65:35 Compliance)**.

⚠ **Two corrections to my original wording, both conceded:**

1. **"Have not run" is too strong.** The script *ran* and authenticated on all four dates; it
   submitted its statements and stopped observing each after the 50-second wait. Because it persists
   no statement ids and never polls, **the repository cannot tell whether any statement later
   completed server-side.** The warranted claim is: **no *observed, terminal* compliance result since
   2026-07-24.**
2. **"Nothing surfaced this to David" is false.** The GitHub workflow was **visibly red**, and the
   07-28 ledger recorded the failure (`docs/agent-ledger/2026-07-28.md:1394-1403`).

**What survives, and it is sharper than what I first wrote:** on the very same day the failure was
diagnosed in the ledger, the telemetry closeout still declared *"Health verdict: Healthy. All
pipelines are green"* (`:1414-1417`). **The defect is health aggregation that carries neither
cross-day schedule lateness nor a separate red workflow — not invisibility.** Same family as
FINDING 3-B, and that pairing survives the narrowing intact.

---

## Thread 1 — draft-capital fields on modeled rows

**Presenting layer: 3** (model features / served valuation). **Layers 1–2 dependency check owed and
performed — see §1.4.** Measured blind; prior figures read only afterward.

Artifact measured: `app/data/valuation_runtime/universe_pvo_runtime.json`,
`captured_at 2026-07-28T13:30:04.081845+00:00`, **12,203 rows**.

### 1.1 FINDING 1-A — the population, by the artifact's own engine field. **PROVED. Corroborates prior lanes exactly.**

Grouping on `valuation.engine_path`:

| `engine_path` | rows | `nfl_draft_round` | `nfl_draft_pick` | `draft_class` |
| :-- | --: | --: | --: | --: |
| PRE_MODEL | 9,480 | 0 | 0 | 0 |
| INACTIVE | 2,141 | 0 | 0 | 0 |
| **ENGINE_B** | **501** | **0** | **0** | **0** |
| **ENGINE_A** | **80** | **80** | **80** | **80** |
| UNRESOLVED_IDENTITY | 1 | 0 | 0 | 0 |

**Universe-wide: 80 of 12,203.** Reached independently; it matches the prior lanes' 0/501 and
80/12,203 exactly. **Recorded as corroboration.**

### 1.2 FINDING 1-B — two engine fields on the same row disagree, and one of them is fabricated. **PROVED. NEW — not in the prior record.**

My first measurement grouped on the **top-level `dvs_engine`** field and produced **388 B / 193 A** —
which contradicted the prior lanes. The contradiction is not an error in either measurement. **The row
carries two engine markers that disagree:**

| | `dvs_engine` | `valuation.engine_path` |
| :-- | --: | --: |
| Engine B | 388 | **501** |
| Engine A | **193** | 80 |

Cross-tabulated, the entire discrepancy is one set: **113 rows with `engine_path = ENGINE_B` and
`dvs_engine = "A"`.** All 113 are `valuation_status = MODEL_UNCERTAIN`; **all 113 have
`dynasty_value_score` null AND `xvar` null.** Sample: Josh Whyle, Jayden Reed, Brayden Willis,
Jonathan Mingo, Roschon Johnson.

**Verified at source** — `src/dynasty_genius/pvo_assembler.py:448-456`. ⚠ **Corrected after review:**
I originally described this as *"the branch taken when there is neither an Engine A nor an Engine B
result,"* repeating the code's own inline comment. **That comment is false about the execution state,
and I should not have restated it as fact.** The branch sits inside
`if engine_b_resolved and _below_games_gate:` (`:415`) — **Engine B did run and produced a forecast**;
the below-games gate stopped DVS normalization, Engine A never ran, and no DVS was produced. The
accurate statement is *"the branch where Engine B ran but no DVS was computed."*

```python
else:
    # Spec 3.4: no A or B — DVS = None; dvs_engine = 'A' as provenance marker.
    dynasty_value_score = None
    dvs_engine = "A"
    _dw_caveat = ("Insufficient professional season data — Engine A prospect score used as prior")
```

The parked record names the **caveat** as false on these rows. **It does not name `dvs_engine`.** The
same branch writes a **structured field** asserting Engine A provenance for a computation that did not
occur — worse than the prose caveat, because a consumer grouping by `dvs_engine` silently counts 113
non-existent Engine A valuations.

**This is not hypothetical: it happened to this measurement, this morning.** My first pass reported
193 Engine A rows and would have gone out as fact had the totals not forced a cross-check.

**Recorded, not opened** — the modeled-blank thread is parked by David and this does not resume it.

### 1.3 FINDING 1-C — where draft capital does and does not exist upstream. **PROVED.**

| Source | Draft capital present? | Evidence |
| :-- | :-- | :-- |
| Engine A training (`prospects_with_outcomes_v3.csv`) | **YES** — `round`, `pick`, `nfl_round`, `nfl_pick`, each with `_missing` and `_source` provenance companions | CSV header |
| Engine B training (`engine_b_features_v2.csv`, 33 cols) | **NO** — no draft-ish column of any kind | CSV header |
| **The live Sleeper snapshot the PVO pipeline consumes** | **NO** | see below |

The live snapshot is `app/data/league_runtime/runs/league-20260728T132000Z/snapshot.json`
(`captured_at 2026-07-28T13:20:04Z`, 12,203 players) — reached via
`scripts/build_universe_pvo_batch.py:29`, `load_league_set_for_root(ROOT).paths["snapshot.json"]`.
**Each player record carries exactly six attributes: `age`, `full_name`, `position`,
`sleeper_status`, `team`, `years_exp`.** No draft field exists anywhere in it.

### 1.4 The layers 1–2 dependency check — asked, answered, and the answer was WRONG

- **The check performed — and its defect, named.** I enumerated the draft-capital columns of both
  training feature sets from their CSV headers; enumerated every player attribute in the live
  snapshot the PVO builder actually reads (traced from the builder's own path constant, not assumed);
  and read `01` §Engine B and `00` §Rookie Evaluation Rules. **What I did not do — and it is the
  whole ballgame — is search for the field anywhere else on disk, or attempt a join.** A check that
  only inspects the locations you already suspect cannot distinguish "absent everywhere" from "present
  somewhere you did not look."
- **The result, corrected.** The field is absent from the Sleeper snapshot and from the Engine B
  training set — **but it is present and already ingested** in
  `app/data/training/prospects_with_outcomes_v3.csv` (`pick`, `round`, `nfl_pick`, `nfl_round`, with
  provenance companions, from `nfl_data_py`). **373 of 501 served Engine B rows join to it on
  `gsis_id` with non-null pick AND round.** My original result line — *"it is never ingested"* — was
  false, and is retracted.
- **The conclusion — ⛔ RETRACTED. My check was incomplete and its conclusion was wrong.**

  **What I wrote:** *"ROOT LAYER IS LAYER 1, and this is newly established… the absence originates at
  ingestion."* **That is false.** I checked two candidate locations and concluded from their emptiness
  that the data was never ingested. I never asked whether it existed somewhere else on disk.

  **Corrected conclusion, verified independently (see §RECONCILIATION):** draft capital **is already
  ingested** — `prospects_with_outcomes_v3.csv` carries `pick`/`round`/`nfl_pick`/`nfl_round` from
  `nfl_data_py`. **373 of the 501 served Engine B rows join to it on `gsis_id` with non-null pick AND
  round, and are still served blank.** For that population the root is a **layer-2
  join/materialization gap**: `pvo_assembler.py:501-503` materializes the draft fields only from
  `features["pick"] / ["round"] / ["draft_class"]`, and the active producer never joins the rookie
  table into that feature dict.

  **The remaining 128 of 501 did not join in this probe and their root layer is NOT established.**
  The population is **mixed**. No single root layer covers it.

  **What survives from my measurement:** the served-artifact counts (§1.1), the six-field live
  snapshot (§1.3), and the Engine B training-set absence — which remains **governance-consistent**
  under `01` §Engine B, a training-feature permission that says nothing about serving.

**And, separately, NOT PROVED: that this is a defect.** The two are different questions and this
document does not conflate them:

- `01` §Engine B disallows *"rookie-only pre-NFL features leaking into **active-player training**
  unless explicitly modeled as a prior."* The absence from the 33-column Engine B **training** set is
  therefore **governance-consistent**, not a hole.
- The `nfl_draft_round` / `nfl_draft_pick` / `draft_class` keys on the PVO are **serving** fields.
  `01` constrains training, not materialization, and does not resolve whether they should be
  populated for display or analysis.
- `00` §Rookie Evaluation Rules frames draft capital as the strongest **rookie** predictor — a rookie
  rule, and Engine B is the active-player forecast.

**Also NOT verified, and it bounds the finding:** whether the Sleeper API even offers draft round/pick
for active players. If it does not, "not ingested from Sleeper" is not an adapter failure and the
field would need a different source entirely. Checking that requires an external API call and is
outside a findings-only inventory.

---

## Thread 2 — Sleeper transactions, and the trade-partner activity component

**Presenting layer: 5** (David's league-context advantage). **Layers 1–2 dependency check owed and
performed — see §2.3.** Measured blind.

### 2.1 FINDING 2-A — transactions are **never ingested by the product**. ⚠ CORRECTED: my original absolute — *"never been called, not once, in the entire history of this repository"* — **FALLS.**

**The refutation, which I verified rather than accepted:** `docs/agent-ledger/2026-07-06.md` records
Codex probing `GET /league/{league_id}/transactions/{round}` **live against David's league
`1314363401744416768`** — round 1 returned trades, waivers, free-agent and commissioner events.
**The endpoint has been called.** My three methods proved the string never entered tracked Python
source; I overreached from that to "never called," which they cannot support. A durable ledger record
is exactly the counterexample a source search cannot see.

**What survives, and it is what actually matters for layer 1:**

1. **Working tree:** `grep -rn "transactions" --include=*.py src app scripts` → **0 files.**
2. **Full history:** `git log --oneline -S'transactions' --all -- '*.py'` → **0 commits.** The string
   has never entered a Python file in any commit ever made.
3. **Complete endpoint enumeration** of `app/data/sleeper.py` — every Sleeper path the product calls:

   `/user/{username}` · `/user/{user_id}/leagues/nfl/{season}` · `/league/{league_id}` ·
   `/league/{league_id}/rosters` · `/league/{league_id}/users` · `/league/{league_id}/traded_picks` ·
   `/league/{league_id}/drafts` · `/draft/{draft_id}` · `/draft/{draft_id}/picks` · `/players/nfl` ·
   `/state/nfl`

   **`/league/{league_id}/transactions/{round}` is absent.** Note `traded_picks` **is** called — the
   product ingests the *outcome* of trades on picks, but never the transaction stream itself: no
   trade, waiver claim, or free-agent add is ever ingested.

### 2.2 FINDING 2-B — `activity_recency_score` is a hardcoded literal, published as a measurement. **PROVED.**

`src/dynasty_genius/league_opportunity_map.py:185`:

```python
activity_recency_score = 0.0
```

No input, no data source, no branch. It is then:

- **summed into the headline score** at `:189-195`, alongside `complementarity_score`,
  `divergence_density_score`, and `posture_alignment_score`; and
- **serialized into the payload** at `:206` under `score_components`, beside the three genuinely
  computed components.

The other three are real: complementarity from positional z-scores (`:170-177`), divergence density
from counted divergence rows (`:178-184`), posture alignment from posture labels (`:186-188`).
**A consumer reading `score_components` cannot distinguish the constant from a measured zero.**

This is David's fourth axis — *what is silently a constant* — in its strongest form: not a stale
value, not a default that rarely updates, but a literal that has never been anything else.

### 2.3 The layers 1–2 dependency check — the clearest result in this inventory

- **The check performed.** The three-method endpoint search of §2.1, plus reading the score's
  construction at source (§2.2).
- **The result.** `activity_recency_score` requires transaction history to compute. Transaction
  history has never been ingested.
- **The conclusion — the layer-5 symptom is a symptom of a layer-1 gap. This survives the review**
  (the review refuted the "never called" absolute, **not** the non-ingestion finding). The component
  is not mis-weighted, mis-scaled, or poorly designed; it is **uncomputable from anything in the
  system**, because no transaction stream is ingested or persisted anywhere. **Fixing this at layer 5
  is impossible by construction.** This is the case David's doctrine describes: *"if we're struggling
  in layer 4 but we haven't fortified and tested layers 1 and 2, we're not thinking correctly."*

  **Bounded honestly:** "not ingested" is established for current code and reachable tracked history.
  It cannot be established for every untracked local experiment that may ever have existed — and the
  07-06 probe proves such things happen without leaving code behind.

**Scope note, stated so the finding is not read wider than it is:** this establishes the root layer
for **this component**. It does not establish that ingesting transactions is authorised, scoped, or
even the right response — `05` §3, a conclusion is not a licence to fix.

---

## DGX-02 RESTORE DRILL — executed 2026-07-29 on David's word (*"run the restore drill"*)

**Authority:** David's fresh word, which is what `02` §Standing Infrastructure ruling 4 requires for a
restore drill. **Boundaries held:** no commit, no push, no schedule change, no new work opened.

### D.1 Traffic constraint — resolved by not needing a backup run at all

**No manual backup was started, and none was needed.** The proof standard is *restore*, and a restore
reads from the **already-completed** run `20260728T141500Z`. Every operation below is a read
(`storage cat`, `storage ls`, `storage cp` **from** the bucket). Nothing was written to the bucket,
no run prefix was created, and the `latest.json` pointer was not touched.

**The drill therefore could not race the 10:15 scheduled job.** It began ~09:50 and completed
**09:55 ET**, twenty minutes clear, and would have been safe regardless because two readers do not
contend. `pgrep -fl backup_irreplaceable` → no process; this lane started none.

### D.2 What was restored

Pointer `gs://dynasty-genius-backup-dtl/dynasty-genius/latest.json` →
`run_id 20260728T141500Z`, `verified: true`, `generated_at 2026-07-28T15:14:45Z`.
Run prefix holds **301 objects**. All five DGX-02 named stores were downloaded in full —
**267 objects, 120 MB** — into a session scratch directory (deliberately described, not reproduced,
per `02` §Durable evidence).

### D.3 The bytes — SHA-256 of every restored file against its local counterpart

| Store | MATCH | DIFFER | MISSING |
| :-- | --: | --: | --: |
| `app/data/pff_exports` | **3** | 0 | 0 |
| `app/data/league_snapshots` | **12** | 0 | 0 |
| `app/data/research/league_behavior/raw` | **173** | 0 | 0 |
| `app/data/league_runtime/runs` | **78** | 0 | 0 |
| `app/data/prospect_identity_review.jsonl` | 0 | **1** | 0 |
| **TOTAL** | **266** | **1** | **0** |

### D.4 Both apparent discrepancies resolve as point-in-time drift, not restore failure

**(a) Six local files absent from the backup.** All six are
`app/data/league_runtime/runs/league-20260729T132511Z/*` — **today's 09:25 league capture**, which
post-dates a 07-28 backup. A point-in-time backup is *supposed* not to contain them.

**(b) The one differing file — `prospect_identity_review.jsonl`. Resolved by object metadata, not by
inference:**

| | bytes | lines | sha256 (first 16) | time |
| :-- | --: | --: | :-- | :-- |
| Restored from backup | 1,241,543 | 5,718 | `b4f5710e74580f0d` | object created **2026-07-28T14:44:12Z** |
| Local now | 1,259,165 | 5,799 | `24ecd628821441 36` | mtime **2026-07-28T23:15:49Z** |

The backup **object's own `Content-Length` is 1,241,543 — byte-exact with the restored file.** That
proves the download was complete and faithful *independently of the local comparison*. The local file
was appended to **8 hours 31 minutes after** the backup captured it (+81 lines). **The backup holds a
correct point-in-time copy; the local file moved on.**

### D.5 Verdict

**THE RESTORE DRILL PASSES, on the standard that was set:** the named assets were **pulled out of the
backup** and their bytes confirmed — 266 of 267 objects byte-identical to local, and the 267th proved
faithful to its stored object by its own `Content-Length`, with the local divergence explained by a
timestamped post-backup append.

**What this now closes, and precisely that:** DGX-02's coverage is no longer only *asserted* by a
manifest entry or *implied* by `sha256_verified: true`. **The four named files, the league-snapshot
and coverage globs, and the raw PFF exports are provably retrievable.** That claim is now earned.

**What it does NOT establish:** anything about stores outside these five; anything about future runs;
and nothing about the 34 objects in the run prefix not covered here. A passing drill on 07-29 is not a
standing guarantee.

**Independent verification owed:** Codex verifies this restore evidence. The durable form of the
evidence is the hashes and object metadata recorded above, which are reproducible from the bucket
without this lane's scratch directory.

---

## Observation recorded during measurement

Today's pipeline ran while this inventory was being written: `league-20260729T132511Z` appeared under
`app/data/league_runtime/runs/` — **09:25:11 EDT against a 09:20 schedule.** Within noise, and
materially different from the 07-27 slip. All figures above were read from the **07-28** artifacts and
are stamped as such.

**A second staleness question, measured but not chased:** `app/data/league_snapshots/sleeper_universe_snapshot_latest.json`
carries `captured_at 2026-06-23T13:17:20Z` — **36 days old** — while the live pipeline consumes
`league_runtime/runs/`. Seven modules reference the `league_snapshots` path. Whether any of them reads
that stale `_latest` at runtime is **NOT established** and would need a call-path trace. Recorded as
an open question, not a finding.
