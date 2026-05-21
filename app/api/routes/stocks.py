from fastapi import APIRouter, HTTPException

from app.schemas.stocks import StockQuote
from app.tools.stock_data import StockDataError, get_stock_quote


router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}/quote", response_model=StockQuote)
def read_stock_quote(ticker: str) -> StockQuote:
    try:
        return get_stock_quote(ticker)
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
