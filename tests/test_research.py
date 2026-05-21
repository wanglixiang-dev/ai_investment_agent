from fastapi.testclient import TestClient

from app.main import app
from app.schemas.news import NewsAnalysis, NewsArticle, SentimentLabel
from app.schemas.stocks import StockQuote


client = TestClient(app)


def fake_stock_quote(ticker: str) -> StockQuote:
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
        fetched_at="2026-05-21T00:00:00Z",
    )


def fake_news_analysis(ticker: str) -> NewsAnalysis:
    symbol = ticker.upper()
    return NewsAnalysis(
        ticker=symbol,
        sentiment=SentimentLabel.positive,
        score=0.5,
        article_count=2,
        key_headlines=[
            f"{symbol} revenue growth beats expectations",
            f"Analysts upgrade {symbol} after strong results",
        ],
        summary=f"{symbol} recent news sentiment is positive.",
        articles=[
            NewsArticle(title=f"{symbol} revenue growth beats expectations"),
            NewsArticle(title=f"Analysts upgrade {symbol} after strong results"),
        ],
    )


def test_create_research_report_with_defaults(monkeypatch) -> None:
    monkeypatch.setattr("app.services.research_service.get_stock_quote", fake_stock_quote)
    monkeypatch.setattr("app.services.research_service.get_news_analysis", fake_news_analysis)

    response = client.post("/research", json={"ticker": "aapl"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["horizon"] == "medium_term"
    assert body["risk_level"] == "medium"
    assert body["recommendation"] == "watchlist"
    assert len(body["sections"]) == 3
    assert body["data_sources"] == ["mock", "yfinance"]
    assert body["sections"][1]["title"] == "Market Data"
    assert "AAPL latest available price is $210.12" in body["sections"][1]["summary"]
    assert body["sections"][2]["title"] == "News Sentiment"
    assert "AAPL recent news sentiment is positive." in body["sections"][2]["summary"]


def test_create_research_report_rejects_empty_ticker() -> None:
    response = client.post("/research", json={"ticker": ""})

    assert response.status_code == 422


def test_create_research_report_accepts_custom_profile(monkeypatch) -> None:
    monkeypatch.setattr("app.services.research_service.get_news_analysis", fake_news_analysis)
    monkeypatch.setattr(
        "app.services.research_service.get_stock_quote",
        lambda ticker: StockQuote(
            ticker=ticker.upper(),
            price=430.00,
            previous_close=None,
            open=None,
            day_high=None,
            day_low=None,
            volume=None,
            market_cap=None,
            currency="USD",
            exchange="NMS",
            fetched_at="2026-05-21T00:00:00Z",
        ),
    )

    response = client.post(
        "/research",
        json={
            "ticker": "msft",
            "horizon": "long_term",
            "risk_level": "low",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "MSFT"
    assert body["horizon"] == "long_term"
    assert body["risk_level"] == "low"


def test_create_research_report_keeps_working_when_market_data_fails(
    monkeypatch,
) -> None:
    from app.tools.stock_data import StockDataError

    def fake_get_stock_quote(ticker: str) -> StockQuote:
        raise StockDataError("provider timed out")

    monkeypatch.setattr("app.services.research_service.get_stock_quote", fake_get_stock_quote)
    monkeypatch.setattr("app.services.research_service.get_news_analysis", fake_news_analysis)

    response = client.post("/research", json={"ticker": "nvda"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["sections"][1]["title"] == "Market Data"
    assert "provider timed out" in body["sections"][1]["summary"]


def test_create_research_report_keeps_working_when_news_data_fails(
    monkeypatch,
) -> None:
    from app.tools.news_analysis import NewsDataError

    def fake_get_news_analysis(ticker: str) -> NewsAnalysis:
        raise NewsDataError("news provider timed out")

    monkeypatch.setattr("app.services.research_service.get_stock_quote", fake_stock_quote)
    monkeypatch.setattr("app.services.research_service.get_news_analysis", fake_get_news_analysis)

    response = client.post("/research", json={"ticker": "nvda"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["sections"][2]["title"] == "News Sentiment"
    assert "news provider timed out" in body["sections"][2]["summary"]
