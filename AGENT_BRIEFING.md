# Dynasty Genius - Agent Briefing

For the universal copy/paste session prompt, use `SESSION_STARTER.md`.
This file is the deeper reference for architecture, permissions, examples, and operating practices.

---

## **Context: Four-Agent Development Model**

You are part of a **four-agent development team** building **Dynasty Genius**, a production-grade fantasy football valuation platform following Infrastructure as Code (IaC) standards.

**Your Team:**
1. **Gemini** → Product Manager (strategy, requirements, no development)
2. **Claude Code** → Local Development Agent (Mac Desktop, prototyping, ad-hoc queries)
3. **Codex** → CI/CD Agent (GitHub Actions, automated testing, deployments)
4. **Genie** → Workspace Agent (Databricks native, pipelines, query optimization)

---

## **✅ WHAT'S BEEN BUILT (Phases 1-6)**

### **Phase 1: Service Principal & OAuth Setup**
- **Service Principal**: `dynasty-genius-service-principal`
- **Application ID**: `c058228c-6c4a-44ac-9c83-97441099cb97`
- **OAuth M2M**: Production-grade authentication (not PAT)
- **Secrets**: Stored in `dynasty-genius-secrets` scope
- **Status**: ✅ Validated across all agents

### **Phase 2: DABs Job Scheduling**
- **Job**: `refresh_genius_state` (hourly cron: `0 * * * * ?`)
- **Location**: `/Users/davidleess/dynasty-genius/infrastructure/`
- **Files**: `databricks.yml`, `resources/jobs.yml`, `src/sql/*.sql`
- **Run-as**: Dev target = user, Prod target = service principal
- **Status**: ✅ Deployed, hourly refresh operational

### **Phase 3: Claude Code Local Connector**
- **Script**: `scripts/claude_code_connector.py`
- **Library**: `databricks-sql-connector==3.5.0`
- **Authentication**: Service principal OAuth from local machine
- **Mode**: `read` (Phase 3) | `write` (Phase 6)
- **Status**: ✅ All 4 tests passing

### **Phase 4: GitHub Actions CI/CD**
- **Workflow**: `.github/workflows/codex_audit.yml`
- **Script**: `scripts/codex_audit.py`
- **Tests**: 5 compliance tests (SSoT, governance, DVU anchors, status, 65:35)
- **Triggers**: Push, PR, daily 9 AM Eastern, manual
- **Status**: ✅ 5/5 tests passing

### **Phase 5: Three-Agent Handshake**
- **Validated**: All agents query the same SSoT and should see identical DVU values
- **Current values**: Query `gen_alpha.gold.genius_state` or `gen_alpha.gold.anchors`; do not rely on documented snapshots
- **Status**: ✅ Multi-agent consensus achieved

### **Phase 6: Write Access Upgrade**
- **Permissions**: 22 total (CREATE/MODIFY/INSERT/UPDATE/DELETE)
- **Scope**: `gen_alpha` catalog (gold, silver, bronze schemas)
- **Tables**: Full CRUD on 5 core tables
- **Functions**: CREATE FUNCTION, CREATE MATERIALIZED VIEW, CREATE SCHEMA
- **Status**: ✅ Write operations validated

## **🗄️ DATABASE SCHEMA**

### **Single Source of Truth (SSoT)**
```sql
-- Primary table: gen_alpha.gold.genius_state
-- Hourly refreshed SSoT. Query live state instead of trusting documented counts.
-- Columns: player_name, dvu_anchor, canonical_status, position, 
--          dominator_rating_target, ras_target, class_year, 
--          data_source, source_rank, state_last_refresh
```

### **Core Tables (You Have Full CRUD Access)**
1. `gen_alpha.gold.anchors` - Generational player DVU anchors
2. `gen_alpha.gold.genius_state` - SSoT (hourly refresh)
3. `gen_alpha.gold.governance_rules` - 65:35 compliance rules (2 rules)
4. `gen_alpha.gold.trade_evaluations` - Trade audit log
5. `gen_alpha.silver.efficiency_metrics` - Raw efficiency data

### **Functions**
- `gen_alpha.gold.check_anti_speed_gate_v2(player_name, signal_type, signal_timestamp, source_rank)`
  - Returns: `{gate_status, wait_time_hours, verification_required, user_message, override_applied}`
  - Purpose: Enforce 168-hour wait for unverified trade signals

---

## **🎯 DYNASTY GENIUS FRAMEWORK (CRITICAL)**

### **Core Metrics**
- **DVU (Dynasty Value Unit)**: Primary valuation currency. 100 DVU = 1.01 rookie pick
- **Dominator Rating**: Team offensive production % (0.32-0.38 = elite)
- **RAS (Relative Athletic Score)**: 0-10 physical tools scale

### **Governance Rules (ALWAYS ENFORCE)**
1. **65:35 Compliance**: 65% quantitative (Rank 1-2 sources) minimum
2. **Anti-Hallucination**: Generational anchors LOCKED in `anchors` table
3. **Source Ranking**:
   - Rank 1-2: PFF, NextGen Stats, Pro Football Reference (quantitative)
   - Rank 3: Market Hype, social media (qualitative, flag if >35%)

### Anchor Discovery

Do not maintain anchor snapshots in this briefing. Always discover current anchors from Unity Catalog:

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

Recent anchor changes live in `gen_alpha.gold.anchors_change_log`.

---

## **🛠️ WHAT YOU CAN DO NOW**

### **All Agents (Shared Capabilities)**
- Query `genius_state` SSoT for DVU values
- Validate 65:35 compliance on trade proposals
- Test anti-speed gate function
- Read governance rules from `governance_rules` table

### **Claude Code (Local Development)**
```bash
# Location: /Users/davidleess/dynasty-genius
# Environment: .env.local (credentials loaded)

# Read operations
python3 scripts/claude_code_connector.py read

# Write operations (CREATE/INSERT/UPDATE/DELETE)
python3 scripts/claude_code_connector.py write

# Custom queries
python3 scripts/claude_code_connector.py  # Modify script for your needs
```

**Use Cases:**
- Prototype DVU recalculation logic locally
- Test trade evaluation queries before production
- Create staging tables for analysis (`gen_alpha.silver.*`)
- INSERT test data for validation

### **Codex (GitHub Actions CI/CD)**
```yaml
# Repository: github.com/davidtleess/dynasty-genius
# Branch: current working branch
# Workflow: .github/workflows/codex_audit.yml

# Triggers:
- Push to main or claude/** branches
- Pull requests to main
- Daily cron at 9 AM Eastern
- Manual dispatch
```

**Use Cases:**
- Run compliance audits on every commit
- Block PRs that violate 65:35 rule
- Deploy schema migrations via DABs
- Validate DVU anchors haven't drifted

### **Genie (Workspace Native)**
```sql
-- Run SQL directly in notebooks or SQL cells
-- Example: Check compliance ratio
SELECT 
    player_name,
    dvu_anchor,
    source_rank,
    CASE 
        WHEN source_rank IN (1, 2) THEN 'Quantitative'
        ELSE 'Qualitative'
    END as data_type
FROM gen_alpha.gold.genius_state;
```

**Use Cases:**
- Build bronze→silver→gold pipelines
- Create materialized views for dashboards
- Write UDFs for custom DVU calculations
- Interactive query optimization

---

## **🚀 BEST PRACTICES**

### **1. Infrastructure as Code (IaC)**
- ❌ **DON'T**: Make changes via Databricks UI
- ✅ **DO**: Update `infrastructure/databricks.yml` → commit to Git → deploy via CLI
- **Why**: Version control, reproducibility, CI/CD ready

### **2. File-Based SQL (Not Inline)**
- ❌ **DON'T**: Write SQL inline in YAML (causes multiline issues)
- ✅ **DO**: Create `.sql` files in `infrastructure/src/sql/`
- **Why**: Cleaner diffs, easier debugging, SQL linting

### **3. Service Principal Authentication**
- ❌ **DON'T**: Use personal access tokens (PATs)
- ✅ **DO**: Use service principal OAuth (already configured)
- **Why**: Production-grade, auditable, no user dependency

### **4. Always Validate Against SSoT**
```sql
-- Before any DVU calculation:
SELECT player_name, dvu_anchor 
FROM gen_alpha.gold.genius_state
WHERE player_name = 'Your Player';

-- Don't trust external sources without 65:35 validation
```

### **5. Lock Generational Anchors**
```sql
-- Read generational anchors from:
SELECT
    class_year,
    player_name,
    status_flag,
    dvu_anchor
FROM gen_alpha.gold.anchors
ORDER BY class_year, dvu_anchor DESC;

-- Never UPDATE these values (anti-hallucination protection)
```

---

## **💡 AI DEV KIT SUGGESTIONS**

### **For Claude Code (Databricks Assistant SDK)**
```python
# Use Databricks Assistant SDK for workspace integration
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Query SQL Warehouse programmatically
results = w.statement_execution.execute_statement(
    warehouse_id="5e883b4bfbb1e3f4",
    statement="SELECT * FROM gen_alpha.gold.genius_state"
)

# Advantage: No separate sql-connector, unified SDK
```

### **For Codex (DABs CLI in CI/CD)**
```yaml
# .github/workflows/deploy.yml
- name: Deploy Infrastructure
  run: |
    databricks bundle deploy --target prod
    databricks pipelines start --pipeline-id $PIPELINE_ID
    
# Validate deployment
- name: Validate SSoT Refresh
  run: python scripts/validate_genius_state.py
```

### **For Genie (Lakeflow Pipelines)**
```sql
-- Use Spark Declarative Pipelines (formerly DLT)
-- infrastructure/pipelines/dvu_calculation.sql

CREATE OR REFRESH STREAMING TABLE efficiency_metrics_bronze;

CREATE OR REFRESH LIVE TABLE efficiency_metrics_silver AS
SELECT 
    player_name,
    dominator_rating,
    ras_score,
    -- Calculate DVU
    (dominator_rating * 100) + (ras_score * 20) as dvu_calculated
FROM LIVE.efficiency_metrics_bronze;

CREATE OR REFRESH LIVE TABLE anchors_gold AS
SELECT * FROM LIVE.efficiency_metrics_silver
WHERE dvu_calculated >= 95.0;  -- Elite threshold
```

---

## **📋 NEXT WORK**

Do not maintain sprint-specific next steps in this briefing. Agents should use:

- `SESSION_STARTER.md` Section 4 for current user intent
- `docs/backlog.md` for queued work
- GitHub issues and pull requests for active implementation state
- Unity Catalog queries in `SESSION_STARTER.md` Section 2 for live data state

---

## **🔑 KEY RESOURCES**

### **Local Development (Claude Code)**
- Repo: `/Users/davidleess/dynasty-genius`
- Connector: `scripts/claude_code_connector.py`
- Environment: `.env.local` (credentials loaded)

### **CI/CD (Codex)**
- GitHub: `github.com/davidtleess/dynasty-genius`
- Branch: current working branch
- Workflow: `.github/workflows/codex_audit.yml`

### **Workspace (Genie)**
- Host: `https://dbc-228373f7-57ec.cloud.databricks.com`
- SQL Warehouse: `5e883b4bfbb1e3f4`
- Infrastructure: `/Workspace/Users/david.t.leess@gmail.com/dynasty-genius-infrastructure/`

### **Documentation**
- Phase 6 README: `PHASE6_README.md` (write operation examples)
- Custom Instructions: `.assistant_instructions.md` (Dynasty Genius rules)
- This Briefing: `AGENT_BRIEFING.md` (comprehensive reference)

---

## **📞 RESPONSE REQUESTED**

After reading this briefing:

1. **Confirm you understand your role** (PM, Local Dev, or CI/CD)
2. **Ask any clarifying questions** about the architecture
3. **Suggest which next step** you'd recommend (Options 1-4)
4. **Identify any gaps** or additional tools you need

**Your development environment is production-ready. You have full CRUD access. Let's build Dynasty Genius features following IaC standards.**

---

## **📊 ARCHITECTURE DIAGRAM**

```
┌─────────────────────────────────────────────────────────────┐
│          SOVEREIGN UNITY FOUR-AGENT ARCHITECTURE            │
│               (Multi-Agent Development Model)               │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ CLAUDE CODE  │   │    CODEX     │   │    GENIE     │
    │(Mac Desktop) │   │(GitHub CI/CD)│   │ (Workspace)  │
    │              │   │              │   │              │
    │Full CRUD ✅   │   │Full CRUD ✅   │   │Full CRUD ✅   │
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
           │                  │                  │
           │   OAuth M2M      │   OAuth M2M      │   Workspace
           │   Service Principal                 │   Native Auth
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                 ┌────────────▼────────────┐
                 │   SERVICE PRINCIPAL     │
                 │ c058228c-6c4a-44ac...   │
                 │   22 Permissions ✅      │
                 └────────────┬────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         ┌────▼─────┐                  ┌─────▼────┐
         │   SSoT   │                  │Governance│
         │ Tables   │                  │  Rules   │
         │(live UC) │                  │ (65:35)  │
         └──────────┘                  └──────────┘

              ┌─────────────────────────┐
              │       GEMINI (PM)       │
              │   Strategy Oversight    │
              │   Read-Only Access      │
              └─────────────────────────┘
```

---

**End of Briefing**
