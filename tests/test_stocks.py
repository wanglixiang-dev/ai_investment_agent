from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.stocks import StockQuote


client = TestClient(app)


def test_read_stock_quote(monkeypatch) -> None:
    def fake_get_stock_quote(ticker: str) -> StockQuote:
        return StockQuote(
            ticker=ticker.upper(),
            price=210.12,
            previous_close=208.50,
            open=209.00,
            day_high=212.00,
            day_low=207.80,
            volume=12345678,
            market_cap=3200000000000,
            currency="USD",
            exchange="NMS",
            fetched_at=datetime(2026, 5, 21, tzinfo=UTC),
        )

    monkeypatch.setattr("app.api.routes.stocks.get_stock_quote", fake_get_stock_quote)

    response = client.get("/stocks/aapl/quote")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["price"] == 210.12
    assert body["source"] == "yfinance"


def test_read_stock_quote_returns_502_on_provider_error(monkeypatch) -> None:
    from app.tools.stock_data import StockDataError

    def fake_get_stock_quote(ticker: str) -> StockQuote:
        raise StockDataError(f"No quote data returned for {ticker.upper()}.")

    monkeypatch.setattr("app.api.routes.stocks.get_stock_quote", fake_get_stock_quote)

    response = client.get("/stocks/unknown/quote")

    assert response.status_code == 502
    assert response.json()["detail"] == "No quote data returned for UNKNOWN."
