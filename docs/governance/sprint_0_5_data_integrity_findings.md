---
title: Sprint 0.5 — Data Integrity Sweep Findings
type: governance
framework_protocol: 1 (Verify Status) + Anti-Speed Protocol
last_updated: 2026-05-03
status: v1 — findings + proposed patches; implementation gated to Codex/Genie
authored_by: Claude Code (Local Dev)
diagnostic_run: 2026-05-04T01:08:50Z (read-only against gen_alpha)
parent_directive: PM Memo 2026-05-03 — Sprint 0.5 Data Integrity Sweep
---

# Sprint 0.5 — Data Integrity Sweep Findings

## Executive Summary

Read-only diagnostic against `gen_alpha` surfaced **four findings**, two of which were unanticipated (Manning IaC gap and connector-script Hunter/Campbell violation):

| # | Finding | Severity | Owner |
|---|---|---|---|
| 1 | Smith duplicates in `genius_state` — Cartesian-product join multiplication (1 anchors × 2 efficiency × 2 NFL = 4 rows) | **Blocking for Trade Engine** | Codex/Genie (refresh SQL patch) |
| 2 | Williams write history — **no race condition; my prior "16:47 UTC mystery write" framing was wrong** (that timestamp belongs to a Manning UPDATE, not Williams) | Resolved (corrected) | Closed |
| 3 | Manning UPDATE on 2026-05-03 16:47 UTC executed from a Databricks notebook with **no IaC migration file** — same governance gap pattern that motivates `anchors_change_log` | Process gap | PM ruling on enforcement |
| 4 | `scripts/claude_code_connector.py` lines 104-107 hard-code "Will Campbell" and "Zachariah Branch" as 2027 prospects in the write demo — **both are already in the NFL** (Campbell = 2025 NFL Draft #4 to NE; Branch = 2026 NFL Draft Rd 3 #79 to ATL). Direct violation of the Hunter/Campbell Amendment. | **Critical — production script** | Codex (immediate scrub) |

---

## Finding 1 — Smith Duplicate Root Cause

### Diagnostic data (verbatim, 2026-05-04T01:08:50Z)

| Source table | Smith row count |
|---|---|
| `gen_alpha.gold.anchors` | **1** ✅ |
| `gen_alpha.silver.efficiency_metrics` | **2** ⚠️ |
| `gen_alpha.bronze.nfl_production_2025` | **2** ⚠️ |
| `gen_alpha.gold.genius_state` (the symptom) | **4** ❌ |

The math: **1 anchor × 2 efficiency × 2 NFL = 4 rows in `genius_state`.** Confirms the LEFT JOIN multiplication theory.

### Proximate cause

`infrastructure/src/sql/refresh_genius_state.sql` lines 53-59:

```sql
FROM gen_alpha.gold.anchors a
LEFT JOIN gen_alpha.silver.efficiency_metrics e
    ON a.player_name = e.player_name
LEFT JOIN gen_alpha.bronze.nfl_production_2025 n
    ON a.player_name = n.player_name
```

Both LEFT JOINs are `ON player_name` only with no deduplication. Any player with N rows in `efficiency_metrics` and M rows in `nfl_production_2025` produces N×M rows in `genius_state`.

### Secondary anomaly: why is Smith in `nfl_production_2025`?

Smith is a **college junior at Ohio State**, draft-eligible 2027. He should not have rows in `bronze.nfl_production_2025`. This suggests either:
- `bronze.nfl_production_2025` is misnamed and contains projection/scouting data, not actual NFL production, OR
- A name collision (a different "Jeremiah Smith" actually in the NFL is being merged with our college Smith), OR
- Manual test data was inserted and never cleaned up

**Action:** Genie should investigate `nfl_production_2025` for Smith specifically and confirm what those 2 rows represent.

### Why are there 2 PFF rows in `silver.efficiency_metrics`?

Diagnostic showed both rows are `data_source = 'PFF'`, `source_rank = 1`. Without visibility into the full schema (no timestamp/season/week column visible), the 2 rows could be:
- 2 seasons (2024 + 2025) — *most likely*
- 2 weekly snapshots
- True duplicates

**Action:** Genie should `SELECT *` on Smith's efficiency_metrics rows and identify the differentiating column (most likely `season` or `last_updated`).

### Proposed Patch (refresh_genius_state.sql)

Defensive deduplication using `QUALIFY ROW_NUMBER()` — preserves source-table identity but enforces one-row-per-player into the join:

```sql
-- ⚠️ ORDER BY column needs Genie confirmation against actual schema.
-- Recommended: latest by season, then by ingestion timestamp.

WITH efficiency_dedup AS (
    SELECT *
    FROM gen_alpha.silver.efficiency_metrics
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY player_name
        ORDER BY season DESC NULLS LAST,
                 last_updated DESC NULLS LAST  -- adjust if column names differ
    ) = 1
),

nfl_dedup AS (
    SELECT *
    FROM gen_alpha.bronze.nfl_production_2025
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY player_name
        ORDER BY snap_count DESC NULLS LAST,    -- prefer player with most snaps
                 last_updated DESC NULLS LAST   -- adjust as appropriate
    ) = 1
)

-- Then in the main CTE:
FROM gen_alpha.gold.anchors a
LEFT JOIN efficiency_dedup e ON a.player_name = e.player_name
LEFT JOIN nfl_dedup n ON a.player_name = n.player_name
```

**Verification query for Genie post-patch:**

```sql
SELECT player_name, COUNT(*) AS row_count
FROM gen_alpha.gold.genius_state
GROUP BY player_name
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

**Backlog note:** the patch addresses the symptom. The underlying schema design (one player → many rows in silver/bronze) is fine for those layers — they should hold all source observations. But `gen_alpha.gold.genius_state` is the SSoT and must enforce one-row-per-player. Consider adding a unique constraint or PK on `(player_name, class_year)` post-patch.

---

## Finding 2 — Williams Write Audit: Corrected

### Original framing (mine, in earlier session output)

> "Williams was already at 88.0/CONDITIONAL_TIER_2 before our UPDATE (timestamp May 3, 16:47 UTC). This means the reconciliation was executed earlier… possibly a parallel-agent race condition."

### What `DESCRIBE HISTORY gen_alpha.gold.anchors` actually shows

Verbatim history (most recent first, last 7 ops):

| Version | Timestamp (UTC) | Operation | Predicate / Notes |
|---|---|---|---|
| 13 | 2026-05-04 00:29:21 | OPTIMIZE | auto |
| 12 | 2026-05-04 00:29:20 | UPDATE | `player_name = Ryan Williams AND class_year = 2027` (this is **our** explicit UPDATE) |
| 11 | 2026-05-04 00:21:56 | OPTIMIZE | auto |
| 10 | 2026-05-04 00:21:53 | **UPDATE** | `player_name = Ryan Williams AND class_year = 2027` (**first** Williams write — 8 minutes before ours) |
| 9 | 2026-05-03 16:47:40 | OPTIMIZE | auto |
| 8 | 2026-05-03 16:47:39 | WRITE | Append, 4 rows |
| 7 | 2026-05-03 16:47:37 | UPDATE | **`player_name = Arch Manning`** ← *the "16:47 UTC mystery"* |

### Correction

**The 16:47 UTC UPDATE was on Arch Manning, not Ryan Williams.** My earlier "race condition" framing was a misattribution born from accepting Genie's report ("Williams was already at 88 at 16:47 UTC") without auditing the actual table history. The Williams writes are versions 10 and 12, both on 2026-05-04 between 00:21 and 00:29 UTC — both by `david.t.leess@gmail.com` from notebooks, both predicates identical. Version 12 was our explicit run; version 10 fired ~8 minutes earlier (probably from Genie executing the same plan ahead of our explicit invocation).

### Findings

- ✅ **No race condition between agents.** The two Williams UPDATEs are 8 minutes apart, sequential, both authored by the same user identity, both idempotent (same predicate, same result row).
- ✅ **No production-stale write.** The 16:47 UTC timestamp was correct in absolute terms but referred to a different player.
- ⚠️ **Idempotent re-execution is still a smell.** The first UPDATE was already correct; firing the same UPDATE 8 minutes later was harmless but wasteful. Worth understanding which agent fired version 10 (probably Genie auto-applying the strategy directive) so we don't have two agents both trying to reconcile every PM ruling.

### Action

- Close the "race condition" concern.
- File a **lower-priority backlog ticket** to coordinate write-firing across agents (so one agent owns each reconciliation rather than two firing the same UPDATE in sequence). Prevent thrash, not bugs.

---

## Finding 3 — Manning UPDATE Without IaC Migration File

### Discovery

`DESCRIBE HISTORY` version 7 (2026-05-03 16:47:37 UTC) shows an UPDATE on the Manning anchor row, executed from notebook `4209166272584975` by `david.t.leess@gmail.com`. **`git log --all --grep="manning\|anchor\|dvu"` shows zero commits with SQL/migration changes** corresponding to this write.

### Implication

`gen_alpha.gold.anchors` is being modified outside any IaC migration tracked in git. This is the same governance gap pattern that motivates the `anchors_change_log` table proposal (Finding 5 below) — but the deeper issue is *workflow*: notebook-direct writes bypass the IaC discipline entirely.

### Recommendation

**Two-layer fix proposed:**

1. **Detection layer (this session's deliverable):** `anchors_change_log` table captures every modification with timestamp, agent, before/after values. See Finding 5.
2. **Prevention layer (PM decision needed):** any UPDATE/INSERT on `anchors` should require either (a) an IaC migration file in `infrastructure/src/sql/migrations/` or (b) a documented exception entry in `anchors_change_log` with PM-ratified rationale. The connector script's write mode and Genie notebook writes should be subject to this discipline equally.

I am not authoring the prevention layer here — that's a PM-level governance decision about workflow, not a Local Dev implementation. Surfacing for ruling.

---

## Finding 4 — Connector Script Hunter/Campbell Violation (CRITICAL)

### Discovery

While reading `scripts/claude_code_connector.py` to understand its query interface, I observed:

```python
# scripts/claude_code_connector.py, lines 103-107
("INSERT test data", """
    INSERT INTO gen_alpha.silver.claude_code_staging VALUES
    ('Will Campbell', 125.0, 'Elite OT prospect - 2027 class', CURRENT_TIMESTAMP(), 'Claude Code'),
    ('Zachariah Branch', 118.0, 'Dynamic WR with elite speed - 2027 class', CURRENT_TIMESTAMP(), 'Claude Code')
"""),
```

### Both players fail the Prospect Verification Checklist

| Player | Claimed in script | Verified status | Source |
|---|---|---|---|
| **Will Campbell** | "Elite OT prospect - 2027 class" | Drafted #4 overall by **New England Patriots in 2025 NFL Draft**; year 2 NFL OT for the Patriots | [Patriots roster](https://www.patriots.com/team/players-roster/will-campbell/) |
| **Zachariah Branch** | "Dynamic WR with elite speed - 2027 class" | Drafted **3rd round / #79 overall by Atlanta Falcons in 2026 NFL Draft**; rookie WR for the Falcons | [NFL Mock Draft Database](https://www.nflmockdraftdatabase.com/players/2026/zachariah-branch) |

### Severity

**Critical — production script.** Anyone running `python3 scripts/claude_code_connector.py write` (an authorized command in the briefing) silently inserts both as 2027 prospects into `gen_alpha.silver.claude_code_staging`. From there, depending on staging-to-gold pipelines, these phantom anchors could propagate into the SSoT.

This is the precise failure mode the Hunter/Campbell Amendment exists to prevent — and the Amendment was authored *because of* the same Will Campbell. The script was authored before the Amendment landed (commit `3558e54`, Phase 3) and was never retroactively scrubbed.

### Proposed Patch

Replace the player-named INSERTs with synthetic test rows that make no eligibility claims:

```python
# scripts/claude_code_connector.py, lines 103-107 (proposed replacement)
("INSERT test data", """
    INSERT INTO gen_alpha.silver.claude_code_staging VALUES
    ('TEST_PROSPECT_ALPHA', 0.0, 'Synthetic test row -- not a real player; do not propagate to gold', CURRENT_TIMESTAMP(), 'Claude Code'),
    ('TEST_PROSPECT_BETA', 0.0, 'Synthetic test row -- not a real player; do not propagate to gold', CURRENT_TIMESTAMP(), 'Claude Code')
"""),
```

**Why synthetic instead of substituting verified 2027 prospects (e.g., Smith, Hardy):** even verified prospects, inserted into staging, risk being picked up by downstream joins or staging-to-gold pipelines and corrupting the actual anchor row. A `TEST_PROSPECT_ALPHA` string is unambiguously test data and will be filtered out by any non-broken consumer.

### Action

**Codex should patch this immediately** — it is on the post-PR-A-merge codebase. Recommend filing as a **P1 blocker on the PR-A merge** rather than a follow-up: don't merge PR-A's connector to main while it contains the violation.

### Audit follow-up

Run a Databricks query before patching to determine if anyone has already executed write mode and inserted these phantom rows:

```sql
SELECT * FROM gen_alpha.silver.claude_code_staging
WHERE player_name IN ('Will Campbell', 'Zachariah Branch');
```

If rows exist, DELETE them after the patch lands.

---

## Finding 5 — Proposed `anchors_change_log` DDL

Per PM directive. New table to capture every modification to `gen_alpha.gold.anchors` with full audit context.

### Proposed DDL

```sql
-- File: infrastructure/src/sql/migrations/20260504_001_create_anchors_change_log.sql
-- Purpose: Audit trail for every modification to gen_alpha.gold.anchors
-- Authority: PM Memo 2026-05-03 (Sprint 0.5 Data Integrity Sweep)

CREATE TABLE IF NOT EXISTS gen_alpha.gold.anchors_change_log (
    -- Identity of the change
    change_id           BIGINT GENERATED ALWAYS AS IDENTITY,
    change_timestamp    TIMESTAMP NOT NULL,
    operation_type      STRING NOT NULL,  -- INSERT | UPDATE | DELETE
    
    -- Identity of the changed row
    player_name         STRING NOT NULL,
    class_year          INT,
    
    -- Before / after state (NULL where not applicable)
    dvu_before          DOUBLE,
    dvu_after           DOUBLE,
    status_flag_before  STRING,
    status_flag_after   STRING,
    dominator_before    DOUBLE,
    dominator_after     DOUBLE,
    ras_before          DOUBLE,
    ras_after           DOUBLE,
    
    -- Provenance
    agent_source        STRING NOT NULL,           -- 'Claude Code' | 'Codex' | 'Genie' | 'Gemini' | 'Direct Notebook'
    user_identity       STRING NOT NULL,           -- email or service principal ID
    notebook_id         STRING,                    -- Databricks notebook ID if applicable
    statement_id        STRING,                    -- Databricks query statement ID
    cluster_id          STRING,                    -- Databricks cluster ID
    
    -- Justification
    iac_migration_file  STRING,                    -- path to migration file if change was IaC-driven
    pm_directive_ref    STRING,                    -- PM memo / commit ref authorizing the change
    qual_rationale      STRING,                    -- free-text rationale, especially for qual-dominant decisions
    
    -- Verification trail
    verification_source STRING,                    -- Primary Data Anchor URL (per Prospect Verification Checklist)
    
    -- Metadata
    log_inserted_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
USING DELTA
PARTITIONED BY (player_name)
COMMENT 'Audit log for all modifications to gen_alpha.gold.anchors. Required by Sprint 0.5 governance.';

-- Index hint: queries by player_name and timestamp dominate the access pattern.
-- Delta auto-optimizes; partitioning by player_name keeps per-player audit reads cheap.
```

### Population strategy

Two paths, not mutually exclusive:

1. **Application-layer trigger:** every script that writes to `anchors` (connector, Genie notebooks, future migrations) MUST also INSERT a row into `anchors_change_log` in the same transaction. Enforced by code review and linting.
2. **Delta CDF (Change Data Feed) sink:** enable Change Data Feed on `gen_alpha.gold.anchors`, then run a Databricks job that reads CDF and writes to `anchors_change_log`. More automatic but loses some provenance (agent_source, pm_directive_ref) that has to come from the writer.

**Recommended:** Path 1 for v1 (ensures full provenance fields), supplemented by Path 2 as a safety net for direct UI/notebook writes that bypass code path.

### Backfill

Once the table exists, backfill the existing `DESCRIBE HISTORY` rows so the log has continuity from the first known anchors write. The Manning UPDATE (version 7) and the two Williams UPDATEs (versions 10, 12) should be inserted with `agent_source = 'Direct Notebook'` and `pm_directive_ref = 'Sprint 0.5 backfill — pre-log writes'`.

---

## Action Items by Owner

### Codex (CI/CD)
- [ ] **P1:** Patch `scripts/claude_code_connector.py` lines 103-107 to remove Will Campbell and Zachariah Branch references (Finding 4 proposed patch). Block PR-A merge until done.
- [ ] **P1:** Add a CI lint check that scans new INSERT/INSERT-VALUES strings in code for any 2025 or 2026 NFL Draft picks (cross-referenced against an allowlist or NFL roster API). Same Hunter/Campbell Amendment, enforced at code-review time.
- [ ] **P2:** Apply Finding 1 patch to `infrastructure/src/sql/refresh_genius_state.sql` after Genie confirms ORDER BY columns.

### Genie (Workspace)
- [ ] **P1:** Confirm the differentiating columns in `silver.efficiency_metrics` and `bronze.nfl_production_2025` for Smith — what's the right ORDER BY for the dedup CTEs in Finding 1?
- [ ] **P1:** Investigate why Smith (college player) has rows in `bronze.nfl_production_2025`. Possible name-collision data corruption.
- [ ] **P2:** Run the Finding 4 audit query against `claude_code_staging` and DELETE any phantom Campbell/Branch rows.
- [ ] **P2:** Implement `anchors_change_log` DDL (Finding 5) once PM approves the schema.
- [ ] **P3:** Backfill `anchors_change_log` from `DESCRIBE HISTORY` for the three pre-log writes (Manning v7, Williams v10, Williams v12).

### Gemini (PM)
- [ ] **Decision:** Approve `anchors_change_log` schema (Finding 5) — schema fields, partitioning choice, CDF strategy.
- [ ] **Decision:** Workflow ruling on Finding 3 — should every `anchors` write require an IaC migration file, with documented exceptions logged via `anchors_change_log`?
- [ ] **Decision:** Should the agent-coordination concern (Finding 2 sub-finding — two agents firing the same UPDATE 8 minutes apart) be formalized into an "owning agent per reconciliation" rule, or accepted as benign?

### Claude Code (Local Dev — me)
- [x] Diagnostic against live warehouse (read-only, complete)
- [x] This findings document
- [ ] Available to draft additional patches once PR-A merges and the strategy branch rebases on the unified codebase

---

## What This Sprint Did Not Catch

Honest scope statement:

- **Other tables** (`silver.*`, `bronze.*`, `governance_rules`, `trade_evaluations`) were not audited for Hunter/Campbell-style player corruption. Recommend a follow-up sweep.
- **Other scripts** (`codex_audit.py`) were not read for hardcoded player names. Recommend a `grep` sweep across all scripts for any string that looks like a player name + class-year claim.
- **Trade engine pre-flight** — even with these fixes, the trade engine should run its own per-player verification checks at runtime, not assume the anchors table is clean. Defense in depth.

## Sources

- Diagnostic queries executed via `scripts/_diag_sprint_0_5.py` (read-only one-off, deleted post-run)
- Will Campbell verification: [Patriots roster](https://www.patriots.com/team/players-roster/will-campbell/), [SI — Patriots select Campbell #4](https://www.si.com/nfl/patriots/onsi/news/new-england-patriots-lsu-will-campbell-2025-nfl-draft)
- Zachariah Branch verification: [NFL Mock Draft Database](https://www.nflmockdraftdatabase.com/players/2026/zachariah-branch), [Dawg Sports draft breakdown](https://www.dawgsports.com/georgia-bulldogs-nfl-draft/37450/draft-breakdownzachariah-branch)
- `DESCRIBE HISTORY gen_alpha.gold.anchors` (read-only) — versions 4-13 visible in diagnostic output
