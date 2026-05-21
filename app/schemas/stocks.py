from datetime import datetime

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    ticker: str = Field(description="Normalized ticker symbol.")
    price: float = Field(description="Latest available market price.")
    previous_close: float | None = Field(default=None)
    open: float | None = Field(default=None)
    day_high: float | None = Field(default=None)
    day_low: float | None = Field(default=None)
    volume: int | None = Field(default=None)
    market_cap: int | None = Field(default=None)
    currency: str | None = Field(default=None)
    exchange: str | None = Field(default=None)
    fetched_at: datetime = Field(description="Server-side timestamp when data was fetched.")
    source: str = Field(default="yfinance")
