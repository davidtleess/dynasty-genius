from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import rookies, roster, trade

load_dotenv()

app = FastAPI(title="Dynasty Genius")

app.include_router(rookies.router, prefix="/api")
app.include_router(roster.router, prefix="/api")
app.include_router(trade.router, prefix="/api")
