# Dynasty Genius

Personal dynasty fantasy football intelligence system for David's primary Superflex PPR league.

## Mandatory Agent Start

Before working in this repository, agents must read:

1. `docs/governance/02-agent-operating-loop.md`
2. `docs/governance/00-product-constitution.md`
3. `docs/governance/01-north-star-architecture.md`
4. `docs/governance/03-code-hygiene-policy.md`
5. `PRODUCT.md` and `DESIGN.md` when the task touches frontend, UI, CSS, components, or any visual surface
6. `AGENT_SYNC.md`

The governance docs are the canonical operating system for this project.

## Stack

- Backend: FastAPI / Python
- Data and modeling: `nfl_data_py`, scikit-learn, versioned artifacts
- Data sources: Sleeper, PlayerProfiler, PFF, KTC overlay, RAS, Pro Football Reference

## Structure

- `app/api/` route handlers
- `app/services/` business logic
- `app/data/` external API clients, scrapers, pipelines, and model artifacts
- `app/models/` Pydantic models
- `docs/governance/` binding product and agent doctrine
- `docs/agent-ledger/` cross-agent session logs

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```
