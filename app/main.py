from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routes import engine_b, rookies, roster, trade, trade_market, trust_surface

load_dotenv()

app = FastAPI(title="Dynasty Genius")

app.include_router(rookies.router, prefix="/api")
app.include_router(roster.router, prefix="/api")
app.include_router(trade.router, prefix="/api")
app.include_router(trade_market.router, prefix="/api")
app.include_router(engine_b.router, prefix="/api")
app.include_router(trust_surface.router, prefix="/api")
