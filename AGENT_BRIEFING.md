# 🚀 UNIVERSAL SESSION STARTER

**Copy/paste this at the start of ANY new agent session - no edits needed:**

---

I'm working on **Dynasty Genius** - a four-agent fantasy football platform with production-grade Infrastructure as Code.

**Read these three sources to get current state:**

1. **Agent Briefing** (architecture, permissions, capabilities):
   ```
   Read: /Workspace/Users/david.t.leess@gmail.com/dynasty-genius-infrastructure/AGENT_BRIEFING.md
   ```

2. **Current Data State** (SSoT - always up-to-date):
   ```sql
   SELECT 
       'Players: ' || COUNT(*) || ', Avg DVU: ' || ROUND(AVG(dvu_anchor), 2) as current_state,
       MAX(state_last_refresh) as last_refresh
   FROM gen_alpha.gold.genius_state;
   ```

3. **Custom Instructions** (governance rules, framework):
   ```
   Read: /Users/david.t.leess@gmail.com/.assistant_instructions.md
   ```

4. **Git Repository** (latest code):
   - Repo: `github.com/davidtleess/dynasty-genius`
   - Branch: `claude/pr-a-storage-governance-pivot`
   - Check commit history for recent changes

**Your role:** [Gemini = PM | Claude Code = Local Dev | Codex = CI/CD | Genie = Workspace]

**Current task:** [Describe what you need help with]

---

**Why this works:**
- ✅ Never needs manual updates (sources are self-updating)
- ✅ Works in any session, any time
- ✅ Agents read current state themselves
- ✅ Points to single sources of truth


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
- **Validated**: All agents query same SSoT, see identical DVU values
- **Jeremiah Smith**: 120.0 DVU (all agents)
- **Ryan Williams**: 116.0 DVU (all agents)
- **Ahmad Hardy**: 108.0 DVU (all agents)
- **Status**: ✅ Multi-agent consensus achieved

### **Phase 6: Write Access Upgrade**
- **Permissions**: 22 total (CREATE/MODIFY/INSERT/UPDATE/DELETE)
- **Scope**: `gen_alpha` catalog (gold, silver, bronze schemas)
- **Tables**: Full CRUD on 5 core tables
- **Functions**: CREATE FUNCTION, CREATE MATERIALIZED VIEW, CREATE SCHEMA
- **Status**: ✅ Write operations validated

---

## **🗄️ DATABASE SCHEMA**

### **Single Source of Truth (SSoT)**
```sql
-- Primary table: gen_alpha.gold.genius_state
-- 11 players, 108.09 avg DVU, hourly refresh
-- Columns: player_name, dvu_anchor, canonical_status, position, 
--          dominator_rating_target, ras_target, class_year, 
--          data_source, source_rank, state_last_refresh
```

### **Core Tables (You Have Full CRUD Access)**
1. `gen_alpha.gold.anchors` - Generational player DVU anchors (8 players)
2. `gen_alpha.gold.genius_state` - SSoT (11 players, hourly refresh)
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

### **Generational Anchors (DO NOT MODIFY)**
```sql
-- 2026 Class
Jeremiyah Love (RB): 100.0 DVU, 0.32 Dominator, 9.8 RAS
Ashton Jeanty (RB): 95.0 DVU, 0.34 Dominator, 8.5 RAS

-- 2027 Class  
Jeremiah Smith (WR): 120.0 DVU, 0.38 Dominator, 9.9 RAS
Ryan Williams (WR): 116.0 DVU, 0.35 Dominator, 9.5 RAS
Ahmad Hardy (RB): 108.0 DVU, 0.38 Dominator, 8.9 RAS
Arch Manning (QB): 120.0 DVU, 0.30 Dominator, 9.2 RAS
```

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
# Branch: claude/pr-a-storage-governance-pivot
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
SELECT * FROM gen_alpha.gold.anchors WHERE is_generational = TRUE;

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

## **📋 SUGGESTED NEXT STEPS**

### **Option 1: Automated Trade Evaluation Pipeline** (30 min)
**Goal**: Validate trades against 65:35 compliance automatically

**Steps:**
1. **Gemini**: Define trade evaluation requirements
2. **Claude Code**: Prototype compliance query locally
3. **Genie**: Create `gen_alpha.gold.trade_evaluations_v2` table
4. **Codex**: Deploy DABs job to run nightly compliance checks

**Deliverable**: Automated trade alerts when 65:35 rule violated

---

### **Option 2: DVU Recalculation Engine** (25 min)
**Goal**: Update DVU anchors when new efficiency metrics arrive

**Steps:**
1. **Gemini**: Prioritize which players need recalculation
2. **Claude Code**: Test recalc logic: `DVU = (Dominator * 100) + (RAS * 20)`
3. **Genie**: Write MERGE statement to update `anchors` table
4. **Codex**: Validate no generational anchors drifted

**Deliverable**: Automated DVU refresh pipeline

---

### **Option 3: Governance Dashboard** (20 min)
**Goal**: Real-time compliance monitoring

**Steps:**
1. **Gemini**: Define dashboard KPIs (65:35 ratio, source rank distribution)
2. **Claude Code**: Prototype queries for each metric
3. **Genie**: Create Lakeview dashboard with live queries
4. **Codex**: Embed dashboard link in daily compliance report

**Deliverable**: Executive dashboard for compliance oversight

---

### **Option 4: Agent Collaboration Demo** (15 min) ⭐ **RECOMMENDED FIRST**
**Goal**: Quick win to validate end-to-end workflow

**Steps:**
1. **Gemini**: Request "Add Travis Hunter (WR, 2027) to anchors: DVU 130"
2. **Claude Code**: Validate calculation locally, commit to Git
3. **Genie**: Execute INSERT INTO `gen_alpha.gold.anchors`
4. **Codex**: Run compliance audit, confirm no violations

**Deliverable**: Proof that all four agents can collaborate successfully

---

## **🔑 KEY RESOURCES**

### **Local Development (Claude Code)**
- Repo: `/Users/davidleess/dynasty-genius`
- Connector: `scripts/claude_code_connector.py`
- Environment: `.env.local` (credentials loaded)

### **CI/CD (Codex)**
- GitHub: `github.com/davidtleess/dynasty-genius`
- Branch: `claude/pr-a-storage-governance-pivot`
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
         │(11 rows) │                  │ (65:35)  │
         └──────────┘                  └──────────┘

              ┌─────────────────────────┐
              │       GEMINI (PM)       │
              │   Strategy Oversight    │
              │   Read-Only Access      │
              └─────────────────────────┘
```

---

**End of Briefing** 🏗️

**Status**: ✅ Production Ready - All four agents operational with full CRUD  
**Last Updated**: 2026-05-03  
**Next Step**: Option 4 (Agent Collaboration Demo) recommended
