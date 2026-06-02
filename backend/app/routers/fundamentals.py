from fastapi import APIRouter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.services.fundamentals_service import FundamentalsService

router = APIRouter()
_service = FundamentalsService()

_sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
_engine = create_engine(_sync_url, pool_size=2, max_overflow=2)


@router.get("/{ticker}")
async def get_fundamentals(ticker: str):
    ticker = ticker.upper()
    with Session(_engine) as session:
        return _service.get(ticker, session)
