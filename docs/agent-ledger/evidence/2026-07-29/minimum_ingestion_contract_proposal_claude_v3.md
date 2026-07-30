# Minimum Ingestion Contract — PROPOSAL v3

**For David to accept, alter, or reject.** Authored by Claude Code. **v1 NOT CLEAR (6 findings). v2 NOT
CLEAR (4 blocking + 3 material). All accepted.**

**Not a platform, tool adoption, dependency, migration, schema change, or implementation.** No running
job changes. **[R]** = the committed research; **[M]** = a defect measured 2026-07-29.

---

## §0 — The structural change in v3, and why it took three attempts

**v1 and v2 both recreated the same denial of service on this repository's own gates.** v1 did it
directly: no check records a proven-failure timestamp, so all **3,972 pytest items across 290 files**
became `unproven`. v2 did it *definitionally*: it defined `C4` as *"underlying class + a declared
`gate_behavior`"*, listed CI, `verify_closeout.py` and the tollgate as C4 examples, then forbade green
from relying on an unproved required C3/**C4** check — while leaving the existing estate unassessed.
Same outcome, new clothes.

**A defect that returns after an honest fix is a scope error, not a wording error.** The proof
requirement was never meant to be universal. David asked about **ingestion**. So:

> **SCOPE OF THIS DOCUMENT.** It binds **three things only**: (1) ingestion **stream declarations**,
> (2) **operational-health claims about ingestion** (freshness, run success, coverage), and
> (3) **publication decisions** — whether an ingested artifact is served or a green claim is made
> about it.
>
> **The existing test, lint, CI, and closeout estate is OUT OF SCOPE.** Not "inventoried", not
> "unassessed" — **out**. v2's inventory kept the estate inside the rule's universe, which is exactly
> how the rule kept reaching it. **No rule in this document applies to a pytest item, a ruff rule,
> `verify_closeout.py`, `verify_sprint_closeout.py`, or a CI job**, unless and until David separately
> extends it.

**Also corrected in v3:** the proof standard was **weaker than the research I cited** (§3), the
`nflreadpy` example **violated my own stream definition** (§5), the unknown count was **wrong for the
third time** (§5), Sleeper was held to a **stricter evidence rule than FantasyCalc** (§5), `status`
conflated two axes (§2), and replay lacked a declared **boundary** (§2).

---

## §1 — Definitions

**Stream = one source object at one grain.** **[M]** A source is not the unit: Sleeper ingests **11
endpoints**; `run_feature_refresh.py:60-65` loads **five distinct nflreadpy objects** at different
grains, one with a different season window. Declaring streams is what lets an **omitted** endpoint
(transactions) be represented rather than disappear into a field list.

**Mechanism classes — three, and `gate_behavior` is NOT one of them.** **[M]** v2's `C4` was a
property masquerading as a class, and that is precisely what let the retroactive rule reach CI.

| Mechanism | Example (ingestion scope only) |
| :-- | :-- |
| **M1 static assertion** | a boundary predicate on a payload shape |
| **M2 batch validator** | a coverage/consistency check over an ingested store |
| **M3 operational monitor** | a freshness, run-success, or missing-run check |

**`gate_behavior` — `blocking` \| `advisory` — is an orthogonal property** any mechanism may carry. It
determines consequence, never proof obligation.

## §2 — What an ingestion stream must declare

| # | Field | Why |
| --: | :-- | :-- |
| 1 | `stream_id` (source + object) · `owner_path` · **`grain`** | **[R]** §6 endpoint/stream + availability grain. **[M]** 5 sources were invisible to a host sweep. |
| 2 | **`lifecycle`** — live \| omitted-stream \| fixture-only \| declared-not-ingested | **[M]** the registry has no status field and fails in both directions. |
| 2b | **`delivery`** — scheduled \| manual | **[M]** v2's enum made `manual` exclusive with `live` while field 3 already had `manual-import`; the real estate has **active manual** streams, so one axis cannot record both truths. |
| 3 | `extraction_mode` — full \| incremental-cursor \| CDC | **[R]** §2.1. |
| 4 | `write_disposition` — replace \| append \| merge \| insert-only \| SCD2 | **[R]** §2.2. Separate failure class from mode. |
| 5 | `primary_key` + `tie_breaker` (per stream) | **[R]** §2.2/§6. |
| 6 | `cursor` + `overlap_window` + late-data policy | **[R]** §2.4. |
| 7 | `delete_behavior` | **[R]** §6. |
| 8 | `declared_cadence` + **`cadence_semantics`** (ingest-interval \| cache-TTL) | **[M]** `freshness_hours` doesn't define its meaning; `sleeper` declares `1` against a 24h job — opposite verdicts. |
| 9 | `schema_policy` — required fields, new-field policy, bad-record vs bad-batch | **[R]** §2.6. |
| 10 | `backfill_range` — **executable** as-of capability, not archive contents | **[R]** §2.7 + **[M]** v1 confused "we have history" with "we can re-run as-of". |
| 11 | **`replay_input` + `replay_boundary`** — raw payload *or equivalent replay input*, **naming the stage replay is promised from**: `extraction` \| `normalization` \| `derivation`, with identity/location/version | **[R]** F2 + **[M]** v2 marked every example `NO` from absence of raw payload, but Sleeper's immutable normalized snapshot may replay *derivation* while being unable to replay *extraction*. **Without the stage named, neither `NO` nor `YES` is auditable.** |
| 12 | `selections_recorded` — known selections/exclusions **+ the schema/doc vintage used** | **[M]** exhaustive enumeration of provider offerings is **not** required — the census could not establish provider-wide offerings for FantasyCalc or nflreadpy. Declined **endpoints** go in field 2. |

## §3 — Proof standard (v2's was weaker than the research it cited)

**[R]** §4.2 requires **three** things. v2 required a generic negative result, which a crash, a wrong
assertion, or an unused unit fixture could satisfy **while proving nothing about the deployed check**
— the same species of defect this clause exists to prevent.

**A check is `proven` only when all three hold:**

1. **A known-good fixture PASSES.**
2. **A known-bad fixture FAILS *for the intended reason*** — the recorded failure reason must match
   the declared predicate. A crash is **not** a pass of this condition.
3. **The real production runner propagates that failure** to the gate or status it claims to control.
   Not a unit harness. The deployed path.

**Proof identity — every element is load-bearing:**

`(check_id, check_version, predicate_id, intended_failure_reason, good_fixture_version,
bad_fixture_version, runner_identity, deployed_config_id, target_set_id, result)`

**[M]** v2's prose said proof lapses when config, target set or runner changes, but its tuple omitted
all three — so the tuple could not detect the lapse its own prose demanded. Fixed.

## §4 — The negative-control clause (ingestion scope only, per §0)

**N1 — Expected-vs-executed reconciliation.** Each run declares its **expected** check/asset IDs and
records the **executed** IDs; a mismatch **fails**; the enumerated-vs-executed evidence is retained.
**[M]** "Empty set fails" catches **zero of four** but **not one of four** — a check silently covering
a quarter of its surface reports green without this.

**N2 — Zero fails only when zero is unexpected.** **[R]** "unless zero is expected for that run."
**[M]** An absolute rule convicts correct behaviour: an optional backup directory legitimately
expanding to zero files, `validate_training_csv.py` accepting an empty file list, conditionally
not-applicable surfaces, and **a violation-finding query correctly returning zero violations.**
**Expected assets, executed assets, and returned violations are three different things.**

**N3 — Proof is version-bound, per §3.** Not a wall-clock timestamp. M1 satisfies it with committed
good/bad fixtures plus a runner-propagation test; M3 additionally re-exercises the deployed path on a
declared trigger.

**N4 — An unproved REQUIRED check must not authorise green.** **[M]** v2's "may not gate" **fails
open** — dropping it from the gate silently reduces coverage. It **blocks the publication/green claim**
until proven or explicitly reclassified by David.

**N5 — Non-green is not one state.** `pass · fail · unproven · stale · timeout · unknown · skipped ·
excluded · unsupported`. **[M]** `codex_audit.py` collapsed every non-`SUCCEEDED` state into
`"Unknown error"`, so one warehouse fault read as five test failures.

**N6 — A predicate, not a response.** **[M]** `codex_audit.py:120-129` returned `PASSED` for any
non-empty result without inspecting values; **3 of 5 named "tests" asserted nothing**, including the
one named for the 65:35 doctrine.

**N7 — Scope, stated once and not re-litigated.** N1–N6 bind **only** the three things in §0: stream
declarations, ingestion operational-health claims, and publication decisions. **They are prospective
for new or changed ingestion checks. They do not reach the existing test/lint/CI/closeout estate at
all** — not as `unassessed`, not as anything.

## §5 — Applied to the live streams *(corrected; nflreadpy is five streams, not one)*

| Stream | grain | mode / disposition | `backfill_range` | `replay_boundary` | `delete_behavior` | `schema_policy` |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **Sleeper `/players/nfl`** | player | full / append immutable per-run dirs + atomic marker swap | none — no as-of arg | **derivation** (normalized snapshot; extraction **not** replayable — 6 fields kept) | **partial** — probe: an ID absent from all inputs disappears next snapshot; one still referenced is retained `unresolved`. Undeclared. | **partial** — rejects falsey whole response (`sleeper.py:78-82`); `.get` selection, extras dropped, missing nulled, malformed non-mapping row aborts |
| **FantasyCalc current-values** | player × date × settings | full (current-only) / append | none — endpoint is current-only, stamps `now` | **normalization** (15-col sidecar + `payload_hash`, **not** the payload) | n/a (append) | **partial** — list/non-empty, stable-key, malformed-row batch abort, source-family enforcement |
| **nflreadpy `player_stats`** | player × week | full / replace, hash-gated | `--season-start` / `--season-end` | **none** — no repo-local raw snapshot | **?** | **?** |
| **nflreadpy `rosters`** | player × roster × season | " | " | " | **?** | **?** |
| **nflreadpy `snap_counts`** | player × week | " | " | " | **?** | **?** |
| **nflreadpy `pbp`** | **play** | " | " | " | **?** | **?** |
| **nflreadpy `participation`** | **play**, **seasons ≥ 2019 only** | " | " | " | **?** | **?** |
| **Sleeper `/league/{id}/transactions/{round}`** | transaction | **`lifecycle = omitted-stream`** — never ingested | — | — | — | — |

**Unknown count, with the rule stated so it is checkable: 10 literal `?` cells** — the five nflreadpy
streams × `delete_behavior` and `schema_policy`. **Sleeper and FantasyCalc carry `partial`, not `?`,
and that is a correction:** v2 marked Sleeper `?` while marking comparable FantasyCalc behaviour
`partial`, **applying two different evidence rules to the same quality of evidence.**

*(Count history, since I got it wrong twice: v1 claimed "nine" with no rule and had six literal cells;
v2 claimed four and had three; v3 states the rule — literal `?` cells in this table — and decomposing
nflreadpy into its five real streams is what moves it to 10. **The number went up because the model got
more honest, not because the foundation got worse.**)*

## §6 — What this does NOT do

No tool adopted, no dependency, nothing implemented, migrated or rescheduled. **It fixes no defect it
cites.** It takes no position on the SQL job, the cliff-age question, or the Databricks retirement.
**It does not touch the existing test estate.**

## §7 — Open questions — David's, not a lane's

1. **Is a daily laptop job expected to run while the laptop is asleep?** The contract records
   lateness; it cannot decide what lateness should mean.
2. **What did `freshness_hours` originally mean** — ingest interval or cache TTL?
3. **Does this apply to the ~10 non-daily sources**, or to the three live ones first?
4. **Where does it live** — extending `SOURCE_REGISTRY`, which fails in both directions today, or a
   new declaration?
5. **Should the proof standard ever extend beyond ingestion?** v3 deliberately says no. That is a
   scope decision, and it is yours — I bounded it because three attempts proved a universal rule
   keeps breaking our own gates, not because the estate is well-proven.

**Recommended next step, explicitly not taken:** fill this form for the **eight live streams** above
and let the residual `?` count measure how well the foundation is understood.
