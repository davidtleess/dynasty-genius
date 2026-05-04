# DYNASTY GENIUS - UNIVERSAL SESSION STARTER

**Copy/paste this at the start of ANY agent session. Only update Section 4 (Context) as needed.**

---

## 1. PROJECT OVERVIEW (Evergreen)

**Dynasty Genius** - Four-agent fantasy football platform with production-grade Infrastructure as Code.

**Your Team:**
- **Gemini** -> PM (strategy, requirements, read-only)
- **Claude Code** -> Local Dev (Mac, prototyping, Git operations)
- **Codex** -> CI/CD (GitHub Actions, automated deployments)
- **Genie** -> Workspace (Databricks native, SQL optimization)

**Authentication:** Service Principal `c058228c-6c4a-44ac-9c83-97441099cb97` (OAuth M2M)
**SQL Warehouse:** `5e883b4bfbb1e3f4`
**Catalog:** `gen_alpha`

---

## 2. DISCOVER CURRENT STATE (Run These - Always Accurate)

### A. Anchor Discovery (SSoT)

```sql
SELECT
    class_year,
    player_name,
    status_flag,
    dvu_anchor,
    dominator_rating_target,
    ras_target
FROM gen_alpha.gold.anchors
ORDER BY class_year, dvu_anchor DESC;
```

### B. Recent Changes (Audit Trail)

```sql
SELECT
    `timestamp`,
    player_name,
    change_type,
    old_dvu,
    new_dvu,
    executing_agent
FROM gen_alpha.gold.anchors_change_log
ORDER BY `timestamp` DESC
LIMIT 10;
```

### C. Governance State (Compliance Check)

```sql
SELECT
    COUNT(*) AS total_players,
    ROUND(AVG(dvu_anchor), 2) AS avg_dvu,
    MAX(state_last_refresh) AS last_refresh
FROM gen_alpha.gold.genius_state;
```

---

## 3. CORE FRAMEWORK (Evergreen Principles)

**Governance Rules (ALWAYS ENFORCE):**
1. **65:35 Compliance** - 65% quantitative (Rank 1-2 sources) minimum
2. **IaC Enforcement** - All gold table writes via migration scripts (database property: `manual_gold_writes_allowed=false`)
3. **Hunter/Campbell Amendment** - Verify prospect eligibility (college enrolled, not NFL/transfer portal)
4. **Anti-Speed Protocol** - Verify unfamiliar work before asserting facts
5. **DATA-DRIVEN OVERRIDE** - Allow justified modifications with documented rationale (requires PM approval + audit trail)

**Core Metrics (Definitions):**
- **DVU (Dynasty Value Unit)** - Primary valuation currency (100 DVU = 1.01 rookie pick)
- **Dominator Rating** - Team offensive production % (0.32-0.38 = elite)
- **RAS (Relative Athletic Score)** - 0-10 physical tools scale

**Database Schema (Locations):**
- `gen_alpha.gold.anchors` - Generational player DVU anchors
- `gen_alpha.gold.anchors_change_log` - Audit trail (10-column schema, CDF enabled)
- `gen_alpha.gold.genius_state` - SSoT (hourly refresh via DABs)
- `gen_alpha.gold.governance_rules` - 65:35 compliance rules
- `gen_alpha.gold.trade_evaluations` - Trade audit log
- `gen_alpha.silver.efficiency_metrics` - Raw efficiency data

**Key Functions:**
- `gen_alpha.gold.check_anti_speed_gate_v2(player_name, signal_type, signal_timestamp, source_rank)`
  - Returns: `gate_status`, `wait_time_hours`, `verification_required`, `user_message`, `override_applied`
  - Purpose: Enforce 168-hour wait for unverified qualitative signals

---

## 4. CURRENT CONTEXT (Update This Section Only)

**Your Role:** [Gemini | Claude Code | Codex | Genie]

**Current Focus:**
[Example: "Building automated trade evaluation pipeline with aging curve penalties"]

**Recent Milestone:**
[Example: "Latest governance work merged; confirm current state from Section 2 queries"]

**Git Branch:**
[Example: "main" or "claude/feature-aging-curve"]

**What You Need Help With:**
[Example: "Implement position-specific depreciation thresholds (RB=26, WR=28, TE=30, QB=33)"]

---

## 5. BEST PRACTICES (Evergreen)

**Infrastructure as Code:**
- DON'T: Make changes via Databricks UI
- DON'T: Write SQL inline in YAML (causes multiline issues)
- DO: Update `databricks.yml` -> commit to Git -> deploy via DABs CLI
- DO: Create `.sql` files for queries (better version control)

**Always Validate Against SSoT:**

```sql
-- Before any DVU calculation
SELECT player_name, dvu_anchor
FROM gen_alpha.gold.genius_state
WHERE player_name = 'Player Name';
```

**Lock Generational Anchors:**
- Query `gen_alpha.gold.anchors` for baseline values
- Never UPDATE anchors without PM approval + DATA-DRIVEN OVERRIDE
- All modifications logged in `anchors_change_log` (audit trail required)

---

## 6. NEXT ACTIONS

After reading this prompt:

1. Run Section 2 queries to discover current state
2. Read detailed docs for architecture and examples:
   - `AGENT_BRIEFING.md` (repo root) - detailed architecture, examples, best practices
   - `.assistant_instructions.md` (repo root) - concise anchor reference
3. Confirm your role and current task understanding
4. Ask clarifying questions before starting work

---

**Status:** Evergreen - Only update Section 4 (Context) as needed
**Template Version:** 1.0
