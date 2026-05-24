from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("")
async def get_watchlist():
    """Get user's watchlist."""
    # TODO: Implement with auth dependency
    return {"stocks": []}


@router.post("/{ticker}")
async def add_to_watchlist(ticker: str):
    """Add a stock to user's watchlist."""
    # TODO: Implement
    return {"message": f"{ticker.upper()} added to watchlist"}


@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove a stock from user's watchlist."""
    # TODO: Implement
    return {"message": f"{ticker.upper()} removed from watchlist"}
