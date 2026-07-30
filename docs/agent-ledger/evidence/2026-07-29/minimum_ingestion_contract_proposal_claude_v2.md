# Minimum Ingestion Contract — PROPOSAL v2

**For David to accept, alter, or reject.** Authored by Claude Code; reviewed by Codex (v1 returned
**NOT CLEAR**, six blocking findings, all accepted).

**Not a platform, tool adoption, dependency, migration, schema change, or implementation.** No running
job changes.

**Justification rule:** every obligation cites **[R]** the committed research or **[M]** a defect
measured on 2026-07-29. Nothing here rests on taste. v1's unjustified items were cut, not softened.

---

## §0 — What v1 got wrong (retracted, not summarised away)

| v1 claim | Status |
| :-- | :-- |
| FantasyCalc `raw_retention = YES` | **FALSE.** `fc_forward_capture_raw` is a **15-column normalized sidecar** holding a `payload_hash` — a hash, **not** the payload. Verified myself. |
| nflreadpy `backfill_range = ?` | **FALSE.** `run_feature_refresh.py:174-176` exposes `--season-start` (default 2018) and `--season-end`. **I marked it unknown without opening the file's own argparse** — the same error shape as this morning's draft-capital conclusion. |
| FantasyCalc `schema_policy = ?` | **Overstated.** Executable boundary behaviour already exists: list/non-empty validation, stable-key requirement, malformed-row whole-batch abort, source-family enforcement, silent discard of unselected fields. Dispersed and incomplete — not unknown. |
| Sleeper `write_disposition = replace` | **Wrong.** It is **append of immutable per-run directories + atomic replacement of the accepted-run marker.** |
| **"Nine unknowns"** | **NOT REPRODUCIBLE and withdrawn.** The table has **six** literal `?` cells and I defined no counting rule. Several were answerable from disk. **This is exactly the "an unknown a ten-minute check would resolve is homework, not an unknown" failure.** |
| Transactions as a `fields_declined` value | **Wrong category.** Transactions are an **omitted endpoint**, not a declined field within an ingested stream. v1 could not express the difference — see §1. |

---

## §1 — Definitions (v1 was unenforceable without these)

**Stream.** One endpoint/object at one grain. **A source is not the unit** — `Sleeper` ingests **11
endpoints at different grains**, so a source-wide `primary_key` is meaningless. **[M]** **The contract
declares streams, not sources.** This is what lets an *un-ingested stream* (transactions) be
distinguished from *fields declined within an ingested stream*.

**Check classes.** v1 said "check" without defining it, so its rules could not be applied or bounded.
Four classes, with different proof obligations:

| Class | Example here | Proof obligation |
| :-- | :-- | :-- |
| **C1 static assertion** | a pytest item, a ruff rule | **version-controlled negative case** — no wall-clock timestamp |
| **C2 batch validator** | `codex_audit_sql.py`, backup anti-rot | negative fixture **+** expected-vs-executed reconciliation |
| **C3 operational/scheduled** | the retired compliance job, freshness monitors | as C2 **+** an expected trigger and a missing-run signal |
| **C4 gate** | CI, `verify_closeout.py`, the tollgate | as its underlying class **+** a declared `gate_behavior` |

**Proof identity.** A proof is `(check_id, check_version, fixture_version, result)`. **[R]+[M]** A
timestamp alone is stale the moment the predicate, fixture, config, target set, or runner changes.
**Proof is bound to the deployed version, never to the clock alone.**

---

## §2 — What a stream must declare

| # | Field | Why |
| --: | :-- | :-- |
| 1 | `stream_id` (source + endpoint) · `owner_path` · **`grain`** | **[M]** 5 sources were invisible to a host sweep; Sleeper's 11 endpoints differ in grain. **[R]** §6 requires endpoint/stream and availability grain. |
| 2 | `status` — live \| manual \| fixture-only \| declared-not-ingested \| **omitted-stream** | **[M]** the registry has no status field and fails in both directions; `omitted-stream` is how transactions get represented. |
| 3 | **`extraction_mode`** — full \| incremental-cursor \| CDC \| manual-import | **[R]** §2.1. *Split from disposition — v1 conflated them.* |
| 4 | **`write_disposition`** — replace \| append \| merge \| insert-only \| SCD2 | **[R]** §2.2. Separate failure class from mode. |
| 5 | `primary_key` + `tie_breaker` (**per stream**) | **[R]** §2.2/§6. |
| 6 | `cursor` + `overlap_window` + late-data policy | **[R]** §2.4. |
| 7 | `delete_behavior` | **[R]** §6. |
| 8 | `declared_cadence` **+ `cadence_semantics`** (ingest-interval \| cache-TTL) | **[M]** `freshness_hours` doesn't define its meaning; `sleeper` declares `1` against a 24h job, and the two readings imply opposite verdicts. |
| 9 | `schema_policy` — required fields, new-field policy, bad-record vs bad-batch | **[R]** §2.6. |
| 10 | `backfill_range` — **executable** as-of capability, not archive contents | **[R]** §2.7 + **[M]** v1 confused "we have history" with "we can re-run as-of". |
| 11 | **`replay_input`** — raw payload **or equivalent replay input**, with identity, location, version | **[R]** F2 + **[M]**. *Narrowed from v1: "without raw, replay is impossible" was not established.* |
| 12 | **`selections_recorded`** — known selections/exclusions **+ the schema/doc vintage used** | **[M]**. *Narrowed from v1: exhaustive enumeration of everything a provider offers is NOT required — the census could not establish provider-wide offerings for FantasyCalc or nflreadpy.* Declined **endpoints** are recorded as `omitted-stream` (field 2), not here. |

## §3 — What a run must record

**[R]** §6: `logical_interval` · `run_id` · code/config version · `cursor_before` → `cursor_after` ·
`rows_in` / `rows_written` / `rows_rejected` · `replay_input_id` · `terminal_status`
**plus, added after review:** **validation counts · destination commit · publication decision.**

**[M] plus `scheduled_for` alongside `started_at`.** On **2026-07-17 (~2h) and 2026-07-27 (~10h)** the
morning jobs ran late together while every health surface read green. Lateness must be a fact in the
record, not something only a human comparing logs can see.

## §4 — State and replay obligations (omitted from v1)

**[R]** all four:

1. **Durable, inspectable source state** — cursor/watermark readable without running the job.
2. **Cursor commits only after a validated destination write.** Committing first loses data on a
   failed write.
3. **Idempotent replay invariant** — re-running a logical interval produces the same destination
   state.
4. **Point-in-time semantics** — event time vs observation time vs version, wherever historical
   training or as-of reconstruction is involved; and **explicit backfill × cursor interaction**.

## §5 — Negative-control clause v2

*v1's version was **both overbroad and incomplete**. It condemned the entire existing estate while
missing the failure class that actually bit us.*

**N1 — Expected-vs-executed reconciliation.** Every check run declares its **expected check/asset IDs**
and records the **executed IDs**; a mismatch is a **failure**, and the enumerated-vs-executed evidence
is retained.
**[M] This is the deeper defect, and v1's rule would not have caught it.** "Empty target set fails"
catches **zero of four**. It does **not** catch **one of four** — a check silently covering a quarter of
its intended surface reports green under v1's rule. Reconciliation catches both.

**N2 — Zero is a failure only when zero is unexpected.** **[R]** requires "unless zero is expected for
that run." **v1's absolute rule was wrong** and would convict correct behaviour: an optional backup
directory legitimately expanding to zero files, `validate_training_csv.py` accepting an empty file
list, conditionally-not-applicable tollgate surfaces, and **a violation-finding query correctly
returning zero violations.** **Expected assets, executed assets, and returned violations must never be
conflated.**

**N3 — Proof is version-bound.** A check is `proven` only against `(check_version, fixture_version)`.
**When the predicate, fixture, config, target set, or runner changes, the proof lapses.** C1 satisfies
this with a committed negative case; C3 additionally exercises the whole path periodically.

**N4 — An unproved REQUIRED check must not authorise green.** **[M]** *"May not gate" in v1 was unsafe
wording:* dropping an unproved check from the gate **fails open** and quietly reduces coverage. The
correct behaviour is that it **blocks the green/publication claim** until proven or explicitly
reclassified as non-required by David.

**N5 — Non-green is not one state.** Checks report `pass` · `fail` · `unproven` · `stale` · `timeout` ·
`unknown` · `skipped` · `excluded` · `unsupported`. **[M]** `codex_audit.py` collapsed every
non-`SUCCEEDED` state into `"Unknown error"`, which is why one warehouse fault read as five test
failures and nobody could tell what had actually happened.

**N6 — A predicate, not a response.** **[M]** `codex_audit.py:120-129` returned `PASSED` for any
non-empty result without inspecting values; **3 of its 5 named "tests" asserted nothing**, including
the one named for the 65:35 doctrine.

**N7 — Scope, so this is not a denial of service on our own gates.** **[M]** The estate is **3,972
pytest items across 290 files**, plus ruff, CI, the backup tests and both closeout verifiers, and
**no check anywhere records a proven-failure timestamp.** v1 would have marked **100% unproven on day
one.** Therefore:

- **Prospective.** N1–N6 bind **new or changed ingestion checks** only.
- **Existing estate is inventoried, not condemned** — each existing check marked `assessed` or
  `unassessed`. `unassessed` is a known gap, **not** a failure.
- **One retroactive rule only, and it is the load-bearing one:** **no green or publication claim may
  rely on an unproved REQUIRED operational (C3/C4) check.** That is the rule that would have caught
  both defects found today.
- **Per-check `gate_behavior`** (blocking / advisory) and **per-check cadence or trigger** are declared
  — **[M]** v1's rule 5 referenced a declared cadence that no field declared, so it was inert.

## §6 — Applied to the three live streams *(corrected)*

*Grain-bearing streams only; Sleeper's remaining endpoints follow the same form.*

| Field | **Sleeper `/players/nfl`** | **FantasyCalc current-values** | **nflreadpy season load** |
| :-- | :-- | :-- | :-- |
| `grain` | player | player × date × settings | player × season |
| `extraction_mode` | full | full (current-only endpoint) | full, source-hash-gated |
| `write_disposition` | **append of immutable per-run dirs + atomic marker swap** | append | replace + noop-if-unchanged |
| `primary_key` | `sleeper_player_id` | player + date + settings | player + season |
| `cursor` / `overlap` | none | `snapshot_date` (stamped `now`) | content hash |
| `declared_cadence` | **`1h` registry vs 24h observed — semantics undefined** | `24h`, matches | `168h` registry vs daily job |
| `schema_policy` | **?** no declared required-field set | **partial** — list/non-empty, stable-key, malformed-row batch abort, source-family enforcement | 33 cols, no declared contract |
| `backfill_range` | **none** — runner has no as-of argument | **none** — endpoint is current-only | **`--season-start` / `--season-end`** |
| `replay_input` | **NO** — 6 fields retained | **NO** — 15-col sidecar + `payload_hash`, not the payload | **NO** repo-local raw snapshot |
| `delete_behavior` | **?** | n/a (append) | **?** |
| Omitted streams | **`/league/{id}/transactions/{round}` — never ingested** | — | — |

**Four literal unknowns remain** — two `delete_behavior`, two `schema_policy`. **A defined count, not
an impression**: cells marked `?` in this table. *(v1 claimed nine with no counting rule; six were
literal and several were answerable from disk.)*

**What the exercise demonstrates:** declaring streams rather than sources is what makes
`transactions` representable as an **omitted stream** rather than disappearing into a field list —
and that single distinction is the difference between a contract that could have surfaced today's
layer-5 gap and one that could not.

---

## §7 — What this does NOT do

No tool adopted, no dependency added, nothing implemented, migrated or rescheduled. **It fixes no
defect it cites** — every `?` stays a `?`. It takes **no position** on the SQL job, the cliff-age
question, or the Databricks retirement.

## §8 — Open questions — David's, not a lane's

1. **Is a daily laptop job expected to run while the laptop is asleep?** The contract can *record*
   lateness; it cannot decide what lateness should mean.
2. **What did `freshness_hours` originally mean** — ingest interval or cache TTL?
3. **Does the contract apply retroactively** to the ~10 non-daily sources, or prospectively only?
4. **Where does it live** — extending `SOURCE_REGISTRY`, which today fails in both directions, or a
   new declaration?
5. **New in v2:** for the existing 3,972-item estate, is `unassessed` an acceptable standing state, or
   does it need a retirement date?

**Recommended next step, explicitly not taken:** fill this form for the **three live streams only**
and let the residual `?` count measure how well the foundation is understood.
