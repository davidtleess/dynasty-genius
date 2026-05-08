# Dynasty Genius Infrastructure (Databricks Asset Bundles)

Production-grade deployment configuration for Sovereign Unity multi-agent architecture.

## Architecture

- **Framework**: Databricks Asset Bundles (DABs)
- **Catalog**: gen_alpha
- **SSoT Table**: gen_alpha.gold.genius_state (hourly refresh)
- **Service Principal**: dynasty-genius-service-principal
- **Warehouse**: 5e883b4bfbb1e3f4

## Deployment

### Prerequisites
- Databricks CLI v0.299.0+
- Authenticated profile: `dbc-228373f7-57ec`
- Service principal credentials in secret scope: `dynasty-genius-secrets`

### Deploy to Development
```bash
cd infrastructure
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

### Deploy to Production
```bash
databricks bundle deploy --target prod
```

### Manual Job Trigger
```bash
databricks bundle run refresh_genius_state --target dev
```

## Job Configuration

**Name**: `dynasty-genius-sovereign-unity_refresh_genius_state_dev`  
**Schedule**: Hourly (cron: `0 * * * * ?`)  
**Tasks**:
1. `refresh_genius_state_sst` - Rebuild genius_state table
2. `verify_refresh` - Validate row counts and timestamps

**Notifications**: Email on failure to david.t.leess@gmail.com

## File Structure

```
infrastructure/
├── databricks.yml           # Root bundle manifest
├── resources/
│   └── jobs.yml            # Job definitions
├── src/
│   └── sql/
│       └── refresh_genius_state.sql  # SSoT refresh query
├── .gitignore
└── README.md
```

## Governance Integration

Following your Dynasty Genius framework preferences, the refresh query applies rules from `gen_alpha.gold.governance_rules`:
- **rb_age_cliff_28**: 30% DVU reduction for RBs at age 28+
- **medical_qualitative_override**: (Applied via UDF, not in refresh)

DVU (Dynasty Value Unit) is the primary valuation currency where 100 DVU = 1.01 rookie pick.

## Environments

| Target | Purpose | Root Path | Schedule |
|--------|---------|-----------|----------|
| `dev` | Development testing | Default bundle path | Hourly |
| `prod` | Production workload | `/Workspace/.bundles/prod/...` | Hourly |

## Rollback Procedure

```bash
# Revert to previous git commit
git log --oneline  # Find commit hash
git revert <commit-hash>

# Redeploy
databricks bundle deploy --target prod
```

## Phase Integration

This is **Phase 2** of the Sovereign Unity implementation:
- **Phase 1**: Service Principal + OAuth setup ✅
- **Phase 2**: Job scheduling (this infrastructure) 🔄
- **Phase 3**: Claude Code local connector
- **Phase 4**: Codex GitHub Actions CI/CD
- **Phase 5**: Full DABs integration (complete)

## Compliance

All operations maintain the **65:35 quantitative/qualitative ratio** required by governance rules. The genius_state table is the Single Source of Truth (SSoT) for all agent queries.
