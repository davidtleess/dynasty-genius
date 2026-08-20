# Dynasty Genius

Personal dynasty fantasy football intelligence system for David's primary Superflex PPR league.

## Product direction

- `PRODUCT.md` describes the product experience and decision surfaces.
- `DESIGN.md` describes the visual system.
- `AGENTS.md` is the concise builder charter for engineering agents.

## Stack

- Backend: FastAPI / Python
- Data and modeling: `nfl_data_py`, scikit-learn, versioned artifacts
- Data sources: Sleeper, PlayerProfiler, PFF, KTC overlay, RAS, Pro Football Reference

## Structure

- `app/api/` route handlers
- `app/services/` business logic
- `app/data/` external API clients, scrapers, pipelines, and model artifacts
- `app/models/` Pydantic models
- `docs/` product, architecture, validation, and historical design material
- `tests/` executable product and data contracts

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
