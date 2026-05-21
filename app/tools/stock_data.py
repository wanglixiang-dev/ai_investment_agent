from datetime import UTC, datetime
from typing import Any

import yfinance as yf

from app.cache.json_cache import get_json_cache
from app.core.config import get_settings
from app.schemas.stocks import StockQuote


class StockDataError(RuntimeError):
    pass


def get_stock_quote(ticker: str) -> StockQuote:
    symbol = ticker.strip().upper()
    if not symbol:
        raise StockDataError("Ticker is required.")

    cache_key = f"stock_quote:{symbol}"
    cached_quote = get_json_cache().get(cache_key)
    if cached_quote is not None:
        return StockQuote.model_validate(cached_quote)

    yf_ticker = yf.Ticker(symbol)

    try:
        fast_info = dict(yf_ticker.fast_info)
    except Exception as exc:
        raise StockDataError(f"Failed to fetch quote for {symbol}.") from exc

    price = _as_float(fast_info.get("last_price"))
    if price is None:
        price = _latest_close_from_history(yf_ticker)

    if price is None:
        raise StockDataError(f"No quote data returned for {symbol}.")

    quote = StockQuote(
        ticker=symbol,
        price=price,
        previous_close=_as_float(fast_info.get("previous_close")),
        open=_as_float(fast_info.get("open")),
        day_high=_as_float(fast_info.get("day_high")),
        day_low=_as_float(fast_info.get("day_low")),
        volume=_as_int(fast_info.get("last_volume")),
        market_cap=_as_int(fast_info.get("market_cap")),
        currency=_as_str(fast_info.get("currency")),
        exchange=_as_str(fast_info.get("exchange")),
        fetched_at=datetime.now(UTC),
    )
    get_json_cache().set(
        cache_key,
        quote.model_dump(mode="json"),
        ttl_seconds=get_settings().stock_quote_cache_ttl_seconds,
    )
    return quote


def _latest_close_from_history(yf_ticker: yf.Ticker) -> float | None:
    history = yf_ticker.history(period="1d", interval="1m")
    if history.empty or "Close" not in history:
        return None

    close = history["Close"].dropna()
    if close.empty:
        return None

    return _as_float(close.iloc[-1])


def _as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None
