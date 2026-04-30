# Dynasty Genius

Personal dynasty fantasy football intelligence app built for one user.

## Stack
- **Backend:** FastAPI (Python)
- **Data sources:** Sleeper API, PlayerProfiler, PFF, KTC, RAS, Pro Football Reference

## Structure
- `app/api/` — route handlers
- `app/services/` — business logic (rookie evaluator, roster auditor)
- `app/data/` — external API clients and scrapers
- `app/models/` — Pydantic data models

## Project Docs
- Canonical planning and architecture docs live in `docs/`.
- Start with `docs/README.md`.

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
