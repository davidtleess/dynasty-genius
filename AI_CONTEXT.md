# Dynasty Genius AI Context

This file is a bootstrap pointer, not the governing doctrine.

Before using this context, every agent must read:

1. `docs/governance/02-agent-operating-loop.md`
2. `docs/governance/00-product-constitution.md`
3. `docs/governance/01-north-star-architecture.md`
4. `AGENT_SYNC.md`

## Project Identity

Dynasty Genius is a personal dynasty fantasy football intelligence system for David's primary Superflex PPR league. It is not a public SaaS product.

The mission is to help David win now while remaining a sustained dynasty contender through better rookie draft, trade, roster, waiver, and league-opponent decisions.

## Current Technical Direction

- Engine A: rookie forecast from pre-NFL and draft-time features.
- Engine B: active-player forecast from NFL usage, efficiency, production trends, and fitted aging curves.
- Unified Player Value Object: one comparable valuation row used by decision surfaces.
- Market values: overlay only, never model input.
- Backtesting: required trust layer before polished frontend expansion.

## Current Stack

- Backend: FastAPI / Python
- Modeling: `nfl_data_py`, scikit-learn, versioned artifacts
- Data collection: `httpx`, `requests`, BeautifulSoup, Playwright where needed
- Configuration: `python-dotenv`
- App entrypoint: `app/main.py`

## Important Paths

- `docs/governance/` binding product and agent doctrine
- `AGENT_SYNC.md` current shared state
- `docs/agent-ledger/` daily cross-agent logs
- `app/api/` route handlers
- `app/services/` business logic
- `app/data/` data clients, scrapers, pipelines, and model artifacts
- `app/models/` Pydantic models

## Current Cautions

- Do not optimize for frontend polish before model credibility.
- Do not add authentication, billing, roles, public SaaS, or generic multi-user abstractions.
- Do not use KTC, ADP, FantasyPros, or other market-derived values as model features.
- Do not hardcode aging cliffs into predictive models.
- Do not use high RAS as a positive score boost unless backtesting proves lift.

For detailed rules, use the governance docs, not this summary.
