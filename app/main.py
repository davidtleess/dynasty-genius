import mimetypes
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    engine_b,
    internal_project_plan,
    league_pulse,
    league_what_changed,
    morning_tape,
    players,
    realized_outcome_scorecard,
    rookies,
    roster,
    roster_capacity,
    system_capture_health,
    system_health,
    system_model_provenance,
    system_tier_readiness,
    trade,
    trade_market,
    trust_surface,
)

load_dotenv()

# Serve JS modules with the WHATWG/RFC-9239 MIME (text/javascript), overriding any OS
# mimetypes entry that would otherwise return the legacy application/javascript.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")

app = FastAPI(title="Dynasty Genius")

app.include_router(rookies.router, prefix="/api")
app.include_router(roster.router, prefix="/api")
app.include_router(roster_capacity.router, prefix="/api")
app.include_router(realized_outcome_scorecard.router, prefix="/api")
app.include_router(trade.router, prefix="/api")
app.include_router(trade_market.router, prefix="/api")
app.include_router(engine_b.router, prefix="/api")
app.include_router(trust_surface.router, prefix="/api")
app.include_router(players.router, prefix="/api")
app.include_router(internal_project_plan.router, prefix="/api")
app.include_router(league_pulse.router, prefix="/api")
app.include_router(league_what_changed.router, prefix="/api")
app.include_router(morning_tape.router, prefix="/api")
app.include_router(system_model_provenance.router, prefix="/api")
app.include_router(system_capture_health.router, prefix="/api")
app.include_router(system_tier_readiness.router, prefix="/api")
app.include_router(system_health.router, prefix="/api")


# --- Increment-1 headshot cache mount (spec v3 §2; rebuildable, gitignored) ---
# Registered BEFORE the /assets bundle mount so the longer prefix wins. CONDITIONAL
# on the local cache existing: a fresh checkout/CI has no cache and simply 404s —
# the frontend's onError fallback chain renders initials, never a broken image.
_HEADSHOT_CACHE = Path("app/data/assets/headshots")
if _HEADSHOT_CACHE.is_dir():
    app.mount(
        "/assets/headshots",
        StaticFiles(directory=_HEADSHOT_CACHE),
        name="headshot-assets",
    )

# --- Frontend SPA static mount (Phase-12 surface 1; spec 2026-06-03-frontend-design-spec) ---
# Serve the built Stack-A bundle (`frontend/dist/`) as a SCOPED fallback, registered LAST so it
# never shadows the API/docs namespace. The mount is CONDITIONAL on a built dist existing, so
# environments without a frontend build (the backend test suite, a fresh checkout) are unchanged.
# `rookie_board.html` is served by its own standalone `scripts/serve_rookie_board.py`, never here.
_FRONTEND_DIST = Path("frontend/dist")
_FRONTEND_INDEX = _FRONTEND_DIST / "index.html"

if _FRONTEND_DIST.is_dir() and _FRONTEND_INDEX.is_file():
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        # Real built assets only; a missing asset 404s here (never falls back to index.html).
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend-assets")

    # include_in_schema=False: the SPA fallback serves index.html for client routes and is
    # NOT an API endpoint. Excluding it keeps app.openapi() deterministic regardless of
    # whether a built dist is present (CI's backend job has none), so the committed
    # frontend/openapi.json snapshot matches across environments (Hey API codegen seam).
    @app.get("/{spa_path:path}", include_in_schema=False)
    def _serve_spa(spa_path: str) -> FileResponse:
        """SPA fallback for client-side routes. Excludes the API/docs namespace and any
        asset-extension path so generated docs, the API, and missing files never resolve to
        the SPA shell."""
        # Never claim the API namespace or FastAPI's own doc routes.
        if spa_path.startswith("api/") or spa_path in {"openapi.json", "docs", "redoc"}:
            raise HTTPException(status_code=404)
        # A path whose last segment carries a file extension (e.g. rookie_board.html, app.css)
        # is a file request, not an SPA route — 404 rather than silently serving the shell.
        if "." in spa_path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404)
        return FileResponse(_FRONTEND_INDEX)
