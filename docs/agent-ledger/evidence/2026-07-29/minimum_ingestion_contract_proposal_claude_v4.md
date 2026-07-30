# Minimum Ingestion Contract — PROPOSAL v4

**For David to accept, alter, or reject.** Authored by Claude Code.
**v1 NOT CLEAR · v2 NOT CLEAR · v3 NOT CLEAR. All findings accepted.**

**v4 is an AMENDMENT, not a rewrite.** Rounds 1–3 oscillated: each version fixed the last blocker and
silently dropped a prior win. The cause was mechanical — I was re-authoring the whole document each
round. **§A below is the regression ledger, carried in the document so a loss is visible on its face
rather than found by a reviewer three rounds later.**

**Not a platform, tool adoption, dependency, migration, schema change, or implementation.** No running
job changes. **[R]** = committed research; **[M]** = defect measured 2026-07-29.

---

## §A — Regression ledger (v2 → v3 → v4)

| Element | v2 | v3 | **v4** |
| :-- | :-- | :-- | :-- |
| Scope wall (estate out of reach) | ✗ recreated the DoS definitionally via `C4` | ✅ **added — reviewer-tested, no side-door reach** | ✅ **KEPT** |
| Run record contract | ✅ added | ⛔ **DELETED — the v3 regression** | ✅ **RESTORED** (§4) |
| State / replay obligations | ✅ added | ⛔ **DELETED** | ✅ **RESTORED** (§5) |
| Proof standard = research §4.2 | ✗ weaker (generic negative) | ✅ fixed | ✅ **KEPT** |
| `gate_behavior` orthogonal to mechanism | ✗ `C4` was a class | ✅ fixed | ✅ **KEPT** |
| Stream (not source) as declared unit | ✗ | ✅ added | ✅ **KEPT + pipeline unit added** (§2) |
| **Per-check declaration** | ✗ | ✗ | ✅ **NEW — N1–N4 were unenforceable without it** (§7) |
| Mechanism names | — | ✗ `M1 static` misclassified | ✅ **fixed — boundary vs post-ingest** (§2) |
| Worked-example unknown count | 4 claimed / 3 actual | 10 markers, **but not 10 evidence unknowns** | ✅ **homework done** (§8) |
| Live-stream population | — | ✗ said 8; actually 7 rows, and ≥17 exist | ✅ **corrected** (§8) |

---

## §1 — SCOPE (v3's wall, kept verbatim in effect; reviewer-tested and it held)

> This document binds **three things only**: (1) ingestion **stream declarations**, (2) **operational-
> health claims about ingestion** (freshness, run success, coverage), and (3) **publication decisions**
> — whether an ingested artifact is served or a green claim is made about it.
>
> **The existing test, lint, CI, and closeout estate is OUT OF SCOPE.** Not "inventoried", not
> "unassessed" — **out**. **No rule here applies to a pytest item, a ruff rule,
> `verify_closeout.py`, `verify_sprint_closeout.py`, or a CI job**, unless David separately extends it.

**Why this wording and not a reworded proof rule:** v1 broke the estate directly (all **3,972 pytest
items across 290 files** would read `unproven`); v2 broke it definitionally. **A defect that returns
after an honest fix is a scope error.** The reviewer tested v3's wall for indirect reach and found
none — that blocker is resolved and v4 does not reopen it.

## §2 — Definitions

**Stream = one source object at one grain.** **[M]** Sleeper ingests **11 endpoints**;
`run_feature_refresh.py:60-65` loads **five distinct nflreadpy objects**, one with a different season
window. Streams are what let an **omitted** endpoint (transactions) be declared rather than vanish
into a field list.

**Pipeline = one composite load → build → publish unit. NEW in v4, and required.** **[M]** Verified
myself: `compute_source_hash(loader_outputs: dict[str, pd.DataFrame], …)` hashes **all five frames
collectively**; `build_engine_b_features` produces **one** candidate; `publish_runtime` atomically
replaces **one** composite runtime. **So "full / replace, hash-gated" is the PIPELINE's disposition,
not five per-stream dispositions.** v3 wrongly assigned the composite write to each input stream.
**The honest model needs both units: N input-stream declarations + one pipeline run/output
relationship.**

**Mechanism — three, renamed after review.** `gate_behavior` is an **orthogonal property**, never a
mechanism. **[M]** v3's `M1 static assertion` was misclassified: a payload-shape predicate executed
during ingestion is a **runtime boundary validator**, not a static assertion — and M1/M2 are not
separated by target-set size.

| Mechanism | Meaning |
| :-- | :-- |
| **B — boundary validator** | runs *at ingestion*, on the payload/frame as it arrives |
| **P — post-ingest validator** | runs *after* persistence, over a stored set |
| **O — operational monitor** | freshness, run-success, missing-run, coverage over time |

## §3 — Proof standard (v3's, kept — it matches [R] §4.2)

A check is `proven` only when **all three** hold:

1. **A known-good fixture PASSES.**
2. **A known-bad fixture FAILS *for the intended reason*** — recorded failure reason must match the
   declared predicate. **A crash is not a pass of this condition.**
3. **The real production runner propagates that failure** to the gate or status it claims to control.

`(check_id, check_version, predicate_id, intended_failure_reason, good_fixture_version,
bad_fixture_version, runner_identity, deployed_config_id, target_set_id, result)`

## §4 — RESTORED: what a run must record

*Deleted in v3. **[R]** §6 + `:470-474`, scale-independent.*

`logical_interval` · `run_id` · code/config version · `cursor_before` → `cursor_after` ·
`rows_in` / `rows_written` / `rows_rejected` · **validation counts** · `replay_input_id` ·
**destination commit** · **publication decision** · `terminal_status`

**[M] plus `scheduled_for` alongside `started_at`.** On **2026-07-17 (~2h) and 2026-07-27 (~10h)** the
morning jobs ran late together while every health surface read green. Lateness must be a fact in the
record.

## §5 — RESTORED: state and replay obligations

*Deleted in v3. **[R]** `:418-431`. A replay-boundary declaration does **not** substitute for an
idempotent run/state-transition contract — that substitution was the v3 error.*

1. **Durable, inspectable source state** — cursor/watermark readable without running the job.
2. **State commits only after a validated destination write.** Committing first loses data on a failed
   write.
3. **Idempotent replay invariant** — re-running a logical interval yields the same destination state.
4. **Point-in-time semantics** — event vs observation vs version time wherever historical training or
   as-of reconstruction is involved.
5. **Explicit backfill × cursor interaction.**

## §6 — What a stream must declare

`stream_id` (source + object) · `owner_path` · **`grain`** · **`lifecycle`** (live | omitted-stream |
fixture-only | declared-not-ingested) · **`delivery`** (scheduled | manual) · `extraction_mode` ·
`primary_key` + `tie_breaker` · `cursor` + `overlap_window` + late-data policy · `delete_behavior` ·
`declared_cadence` + **`cadence_semantics`** (ingest-interval | cache-TTL) · `schema_policy` ·
`backfill_range` (**executable** as-of capability, not archive contents) · **`replay_input` +
`replay_boundary`** (extraction | normalization | derivation) · `selections_recorded` + schema vintage

**`write_disposition` moves to the PIPELINE** (§2), not the stream — v3's error.

*Justifications unchanged from v3: `lifecycle`/`delivery` split because the estate has active manual
streams and one enum cannot hold both truths; `cadence_semantics` because `freshness_hours` does not
define its own meaning (`sleeper` declares `1` against a 24h job); `replay_boundary` because a blanket
`NO` is not auditable; `selections_recorded` narrowed because the census could not establish
provider-wide offerings.*

## §7 — NEW: what each check must declare

**[R]** per-check minimum. **[M] N1–N4 were unenforceable without this** — N4 could not identify an
"unproved REQUIRED check", N1 had no authoritative expected set, and O had no declared trigger.

`check_id` · **`required` | optional** · `mechanism` (B | P | O) · `predicate` ·
**`expected_target_set`** · `gate_behavior` (blocking | advisory) · `cadence_or_trigger` ·
**`controlled_publication`** — which publication decision or status claim this check governs

## §8 — Negative-control clause (unchanged from v3; scope per §1)

**N1** expected-vs-executed reconciliation — a mismatch fails; evidence retained. **[M]** "empty set
fails" catches zero-of-four but **not one-of-four**.
**N2** zero fails **only when zero is unexpected** — **[R]** "unless zero is expected for that run".
**[M]** counterexamples: an optional backup dir correctly expanding to zero, `validate_training_csv.py`
accepting an empty list, not-applicable surfaces, and **a violation query correctly returning zero
violations**. Expected assets, executed assets, and returned violations are three different things.
**N3** proof is version-bound per §3, not a wall-clock timestamp.
**N4** an unproved **required** check **must not authorise green** — **[M]** "may not gate" **fails
open**.
**N5** non-green is not one state: `pass · fail · unproven · stale · timeout · unknown · skipped ·
excluded · unsupported`. **[M]** `codex_audit.py` collapsed all of these into `"Unknown error"`.
**N6** a predicate, not a response. **[M]** `codex_audit.py:120-129` returned `PASSED` for any
non-empty result; **3 of 5 named "tests" asserted nothing.**
**N7** prospective for new/changed ingestion checks; **does not reach the estate at all** (§1).

## §9 — Applied: the homework, done

**The `?` count was overstated for the third time, and the test that caught it has now fired three
times on me.** v3 marked ten nflreadpy cells `?`. **I resolved them from the installed package and the
active path**, and they are **not** evidence unknowns:

- **`nflreadpy==0.1.5`** installed, all five loaders present.
- **`schema_policy` = partial, established.** The assembly **directly indexes required columns** —
  `rosters_agg.groupby(["gsis_id","season"])`, `snaps_agg.groupby(["pfr_player_id","season"])["offense_pct"]`,
  `pbp_qbs.groupby(["passer_player_id","season"])` — so a **missing required column aborts the batch**;
  selected columns drive the result; extras are ignored.
- **`delete_behavior` = partial, established.** `player_stats` is the base population; missing
  roster/snap/PBP/participation rows propagate through explicit left/inner joins; the next accepted
  runtime **replaces the prior whole output**. Existing tests prove a missing snap row **retains the
  player with a null snap share**.

**Applying the same `partial` standard used for Sleeper and FantasyCalc: 0 literal `?` cells remain in
the worked example.** The honest statement is **"undeclared and incomplete, but executable and
established"** — which is a materially different problem from "unknown", and points at *declaration*
work rather than *investigation* work.

**Population, corrected.** v3 said "eight live streams"; §5 held **seven** live rows. On v4's own
premise the live population is **at least 17 streams** — **11 Sleeper endpoints** + FantasyCalc + **5
nflreadpy objects** — plus **one declared omitted stream** (`/league/{id}/transactions/{round}`) and
**one pipeline** (feature-refresh). v3 applied the form to `/players/nfl` only and silently dropped
the other ten Sleeper endpoints. **v4 states the real denominator rather than the convenient one.**

| Unit | grain | disposition | replay_boundary | delete / schema |
| :-- | :-- | :-- | :-- | :-- |
| Sleeper `/players/nfl` | player | *(stream)* | **derivation** — extraction not replayable, 6 fields kept | partial / partial |
| Sleeper × 10 further endpoints | various | *(streams)* | **not yet declared** | **not yet declared** |
| FantasyCalc current-values | player × date × settings | *(stream)* | **normalization** — 15-col sidecar + `payload_hash` | n/a / partial |
| nflreadpy `player_stats` · `rosters` · `snap_counts` · `pbp` · `participation` | player×week · player×roster×season · player×week · **play** · **play (≥2019)** | *(streams — no independent persistence)* | none — no repo-local raw | partial / partial |
| **feature-refresh PIPELINE** | composite | **full / replace, hash-gated** (collective hash over all five frames) | — | — |
| Sleeper `transactions` | transaction | **`lifecycle = omitted-stream`** | — | — |

## §10 — What this does NOT do

No tool adopted, no dependency, nothing implemented, migrated or rescheduled. **It fixes no defect it
cites.** No position on the SQL job, the cliff-age question, or the Databricks retirement. **It does not
touch the existing test estate.**

## §11 — Open questions — David's, not a lane's

1. **Is a daily laptop job expected to run while the laptop is asleep?** The contract records
   lateness; it cannot decide what lateness should mean.
2. **What did `freshness_hours` originally mean** — ingest interval or cache TTL?
3. **Does the contract apply to all 17 live streams, or to the three sources first?** The denominator
   is now honest; the sequencing is yours.
4. **Where does it live** — extending `SOURCE_REGISTRY`, which fails in both directions today, or a
   new declaration?
5. **Should the proof standard ever extend beyond ingestion?** v4 says no. That is a scope decision and
   it is yours — bounded because three attempts proved a universal rule keeps breaking our own gates,
   **not** because the estate is well-proven.

**Recommended next step, explicitly not taken:** declare the **three live sources' streams** first —
the work is *declaration*, not investigation, now that the homework is done.
