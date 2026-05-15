from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import rookies, roster, trade, engine_b, trust_surface

load_dotenv()

app = FastAPI(title="Dynasty Genius")

app.include_router(rookies.router, prefix="/api")
app.include_router(roster.router, prefix="/api")
app.include_router(trade.router, prefix="/api")
app.include_router(engine_b.router, prefix="/api")
app.include_router(trust_surface.router, prefix="/api")
