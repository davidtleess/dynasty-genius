# Databricks compliance check — RETIREMENT RECORD

**Authority:** David, 2026-07-29 — *"retire the databricks check."*
**Status: BUILT, UNCOMMITTED, UNPUSHED.** No commit or push word exists. He said retire, not commit.

---

## 0. ⚠ CORRECTION — v1 of this record was materially false, and is retracted here

**v1 of this document — and the workflow comment, the script docstring, and the 11:59 ledger entry —
asserted that five governance commitments "were verified by this check." That is FALSE for three of
them.** Adversarial review caught it (`docs/agent-ledger/2026-07-29.md`, 12:08 ET entry, NOT CLEAR).

`execute_query()` returns **`PASSED` for ANY successful, non-empty SQL response, without inspecting
its values** (`scripts/codex_audit.py:120-129`). The reviewer reproduced `PASSED` against
deliberately absurd fake responses: governance-rule counts of `[0,0,0]`, a status distribution
containing only `NOT_A_VALID_STATUS`, and a source-rank distribution of 100% rank 9.

**I read those exact lines this morning while tracing why the job went red, and drew no conclusion
from them.** I asked why the check was failing and never asked whether it had meant anything while it
was passing. **The corrected statement below is materially worse than what I originally wrote, and it
is the more useful one.**

---

## 1. WHAT THE RETIRED JOB ACTUALLY VERIFIED — corrected

| # | Named "test" | What it actually did | Real coverage lost by retiring |
| :-- | :-- | :-- | :-- |
| 1 | `genius_state` SSoT accessibility | **Genuine connectivity/accessibility probe** — a non-empty response does demonstrate reachability | **YES** |
| 2 | Governance Rules Validation | **NOT AN ASSERTION.** Aggregate query (`:425-435`) returns one row even for an empty table — passes regardless of content | **NO — never verified this** |
| 3 | DVU Anchor Integrity | **The one real domain assertion** (`:241-326` build explicit failure lists) | **YES** |
| 4 | Status Classification Distribution | **NOT AN ASSERTION** (`:441-452`). Asserts no classification rule | **NO — never verified this** |
| 5 | **Source Rank Distribution (65:35)** | **NOT AN ASSERTION** (`:455-467`). A bare `SELECT … GROUP BY source_rank`. **Nothing is ever compared to 65:35** — `65` and `0.35` appear only in the docstring, a comment, and the test's own NAME | **NO — there was never an enforcement mechanism to lose** |

### What this changes

- **Only items 1 and 3 lose real coverage.** For 2, 4 and 5 the retirement does not create a
  verification gap — **it removes a green signal that never covered them.**
- **My v1 sentence that item 5's "enforcement mechanism is now absent" was the worst line in the
  document.** There was no enforcement mechanism. A `GROUP BY` named after a constitutional doctrine
  is not enforcement of it, and calling it that made the constitution look better guarded than it was.
- **All five remain unverified obligations today.** The corrected history is that **three of them
  were unverified while CI was green** — worse than "we just lost five checks", and more useful.

**Where any of the five must now live is UNDECIDED — David's call.** Three options, none authorised
or opened (`05` §3):

- **(a) Re-home against local stores.** Items 4 and 5 are distribution checks that may be computable
  locally without a warehouse — and **unlike the retired versions would have to be written with real
  acceptance criteria.** Not assessed.
- **(b) Repair the runner and keep Databricks.** Requires statement polling **and** writing the
  missing assertions for 2/4/5. Needs a live warehouse and credentialed spend.
- **(c) Retire the obligations deliberately** — legitimate only as an explicit David ruling, never by
  default, and never by a check quietly disappearing.

---

## 2. What was changed

### 2.1 `.github/workflows/codex_audit.yml`

- **Removed the `catalog-compliance` job** ("Sovereign Unity compliance audit") in full — the
  checkout, Python setup, `databricks-sdk==0.30.0` install, the audit step with its `DATABRICKS_HOST`
  / `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` / `DATABRICKS_WAREHOUSE_ID` env block, and
  the artifact upload.
- **Replaced it with a retirement comment block** recording the authority, the failure dates, the
  verified mechanism, and the five now-unverified obligations, so the removal is discoverable from
  the file rather than only from git history.
- **Removed `scripts/codex_audit.py` from the `push` and `pull_request` path triggers**, with an
  inline reason — no job runs that script any more, so a change to it would otherwise fire a workflow
  that does nothing.

**Verified after editing:** the file still parses as YAML; remaining jobs are exactly
`['sql-governance']`; triggers unchanged (`push`, `pull_request`, `schedule`, `workflow_dispatch`).
The only surviving references to the warehouse id are inside the explanatory comment, which is
deliberate.

### 2.2 `scripts/codex_audit.py`

**Docstring only. No executable line touched.** Added a retirement banner stating that the script is
no longer run by any job, the verified failure mechanism, that the five tests are now unverified, and
that the file is retained deliberately.

**Why the script was NOT deleted — corrected.** v1 argued it is *"the only surviving definition of
what those five checks mean."* **That argument fails on its own terms and is withdrawn:** a file with
no acceptance criteria cannot specify items 2, 4 or 5. It is retained as an **unwired query
reference** — useful for option (a) or (b) as a starting point for the SQL shape — and the banner now
says exactly that.

**It is also stale and unsafe to copy from.** It queries `rule_id = 'rb_age_cliff_28'`
(`scripts/codex_audit.py:431`) while `00-product-constitution.md:106` locks the RB warning at **age
26**, and the surviving static auditor **requires 26** (`scripts/codex_audit_sql.py:218,300`).
**A stale, still-executable harness that contradicts the constitution must not be labelled the
definition of anything.** Anyone re-homing these checks should treat its SQL as a sketch to be
re-derived from `00`, not copied.

---

## 3. The verified mechanism — why this was a broken check, not a product signal

| Evidence | Value |
| :-- | :-- |
| Scheduled successes | **24 consecutive**, 2026-07-01 → 2026-07-24 |
| Scheduled failures | **5 consecutive**, 2026-07-25 → 2026-07-29 |
| Last success | run `30104934179`, whole job **35 s** |
| Latest failure | run `30467494608` (2026-07-29) |
| 2026-07-28 failure step duration | **254 s** ≈ 5 queries × 50 s `wait_timeout` |
| Same-workflow SQL job | **`success` on every run, including all five failures** |

`scripts/codex_audit.py:114-117` calls `execute_statement(..., wait_timeout="50s")` and tests
**only** `state == StatementState.SUCCEEDED` (`:120`). There is no polling loop and no
`on_wait_timeout`. At `:138` the else-branch reads `response.status.error.message if
response.status.error else "Unknown error"` — and a non-terminal state has no `.error`.

*(Line citations corrected: v1 cited `:90-96` and `:113-114`, which were the pre-docstring locations
and became stale the moment I added the banner. Fixed to the current lines.)*

**⛔ CLAIM WITHDRAWN.** v1 said *"one connection that never answered was rendered as five distinct
test failures."* **That is not established.** The evidence supports exactly this and no more:
**five non-`SUCCEEDED` responses, each rendered as `"Unknown error"` after ~50 s.** Whether that was
one unanswered connection, five, or something else **cannot be known from here** — the runner
discards the statement state and persists no statement ids. *(The stronger phrasing originated in
relay and I repeated it without bounding it; it is corrected in the record and with David.)*

**Retained limitation, unchanged by this retirement:** because the runner discards the statement
state and persists no statement ids, **it was never possible to tell from CI whether the underlying
Databricks data was compliant or defective.** A cold warehouse, a suspended warehouse, a quota block,
a permissions change, or genuinely missing rows all rendered identically. **Retiring the check does
not resolve that question — it removes the only thing that was asking it.**

---

## 4. What I deliberately left alone

| Left alone | Why |
| :-- | :-- |
| **`docs/governance/01-north-star-architecture.md`** | Still names Databricks the preferred governed data platform. **Explicitly outside this word.** The contradiction is real and is being put to David as its own decision. |
| **`docs/storage-strategy.md`** | Still describes migrating **to** Databricks as the target. Same reason. |
| **The `sql-governance` job** | Authorised scope was the warehouse-dependent job. **But see §5 — I found the evidence Tower asked me to look for, and did not act on it.** |
| **`scripts/codex_audit.py` logic** | Docstring only. Repairing the polling defect is option (b) and is not authorised. |
| **The Databricks workspace itself** | No credentialed call, no spend, no warehouse inspection. |
| **The `schedule:` trigger** | Retained — the surviving job still uses it. |

---

## 5. ⚠ FINDING WHILE IMPLEMENTING — the surviving green job verifies nothing

The retirement was scoped to the warehouse job *"unless you find evidence the rest is equally
orphaned."* **That evidence exists, and I am reporting it rather than widening my own authority.**

`sql-governance` runs `python scripts/codex_audit_sql.py resources`. **There are zero `.sql` files
anywhere under `resources/`.** Run exactly as CI runs it, the script reports, in its own words:

```
Codex SQL audit passed for 0 SQL file(s).
exit=0
```

**It has been passing green on every run — including all five failure days — because it has nothing
to check.** That is the same disease as the retired job, in the opposite direction: the red check
verified nothing and said so loudly; the green check verifies nothing and says so reassuringly.

**Not acted on. This is a David decision**, and it changes what the retirement leaves behind.

**Stated as a safety consequence rather than an observation, per review:** after this retirement the
workflow named **"Codex Compliance Audit" is a KNOWN GREEN NO-OP.** Its one surviving job checks zero
files and reports success. **It must never be described — in a status report, a dashboard, a ledger,
or to David — as a healthy compliance surface.** A green badge on a workflow that audits nothing is
the same failure this whole retirement was meant to end, wearing the opposite colour.

---

## 6. Verification performed

- `.github/workflows/codex_audit.yml` re-parsed as YAML after editing; jobs enumerated.
- `scripts/codex_audit_sql.py resources` executed locally exactly as CI invokes it.
- Run history read from `gh run list --workflow codex_audit.yml`; per-job conclusions read for the
  first failure, the latest failure, and the last success.
- The failure mechanism read at source line-by-line, not inferred from logs.
- **No test suite run:** no executable Python line changed. The only Python edit is a docstring.

**Independent review: OWED.** Codex holds the reviewer seat and has not reviewed this. **No commit or
push word exists for any of it.**
