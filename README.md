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

The virtual environment lives at `.venv/` (not `venv/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

The product needs no terminal: the API runs as a launchd agent
(`ops/launchd/com.davidleess.dynasty-api.plist`, label
`com.davidleess.dynasty-api`) that starts at login and restarts on exit
(RunAtLoad + KeepAlive). Open the bookmark:

**http://127.0.0.1:8000**

The agent serves uvicorn on `127.0.0.1:8000` with the repo root as its
working directory — `app/main.py` mounts the frontend bundle and headshot
cache CWD-relative, and the `/` mount is conditional on a built
`frontend/dist` existing, so a wrong working directory or a missing build
serves the API but 404s on `/`. Deliberately no `--reload`: it would watch
the ~15 GB under `app/data/`.

After a trunk pull, build the frontend BEFORE bootstrapping (or restarting)
the API agent — the agent serves whatever `frontend/dist` holds, and a
stale or absent build renders a stale or absent page:

```bash
cd frontend && npm ci && npm run build
```

One-time install (the plist is committed unloaded; loading it is a manual,
human step):

```bash
ln -s /Users/davidleess/dynasty-genius-product/ops/launchd/com.davidleess.dynasty-api.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.davidleess.dynasty-api.plist
```

Verify: `launchctl list | grep dynasty-api` shows a numeric PID, and
`curl -s http://127.0.0.1:8000/` returns the app shell (a 404 on `/` means
the WorkingDirectory is wrong OR `frontend/dist` was never built).

After retraining models, restart the agent —
`launchctl kickstart -k gui/501/com.davidleess.dynasty-api` — because
`app.main` pins the four rookie model pickles in memory at import; a
running agent keeps serving the old models until restarted.

To run by hand instead (development only):

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Use a non-8000 port for manual runs so they never collide with the agent.
