from datetime import UTC, datetime
from types import SimpleNamespace

from app.schemas.news import NewsAnalysis, NewsArticle, SentimentLabel
from app.schemas.stocks import StockQuote
from app.tools.news import get_news_analysis
from app.tools.stocks import get_stock_quote


class FakeCache:
    def __init__(self, cached_value=None) -> None:
        self.cached_value = cached_value
        self.writes = []

    def get(self, key: str):
        return self.cached_value

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self.writes.append((key, value, ttl_seconds))


def test_stock_quote_uses_cache(monkeypatch) -> None:
    cached_quote = StockQuote(
        ticker="AAPL",
        price=210.12,
        fetched_at=datetime(2026, 5, 21, tzinfo=UTC),
    ).model_dump(mode="json")
    cache = FakeCache(cached_quote)
    monkeypatch.setattr("app.tools.stocks.get_json_cache", lambda: cache)

    quote = get_stock_quote("aapl")

    assert quote.ticker == "AAPL"
    assert quote.price == 210.12
    assert cache.writes == []


def test_stock_quote_writes_cache_on_miss(monkeypatch) -> None:
    cache = FakeCache()
    monkeypatch.setattr("app.tools.stocks.get_json_cache", lambda: cache)
    monkeypatch.setattr(
        "app.tools.stocks.get_settings",
        lambda: SimpleNamespace(stock_quote_cache_ttl_seconds=60),
    )
    monkeypatch.setattr(
        "app.tools.stocks.yf.Ticker",
        lambda ticker: SimpleNamespace(
            fast_info={
                "last_price": 210.12,
                "previous_close": 208.50,
                "currency": "USD",
            }
        ),
    )

    quote = get_stock_quote("aapl")

    assert quote.price == 210.12
    assert cache.writes[0][0] == "stock_quote:AAPL"
    assert cache.writes[0][2] == 60


def test_news_analysis_uses_cache(monkeypatch) -> None:
    cached_analysis = NewsAnalysis(
        ticker="AAPL",
        sentiment=SentimentLabel.positive,
        score=0.5,
        article_count=1,
        key_headlines=["Apple revenue growth beats expectations"],
        summary="AAPL recent news sentiment is positive.",
        articles=[NewsArticle(title="Apple revenue growth beats expectations")],
    ).model_dump(mode="json")
    cache = FakeCache(cached_analysis)
    monkeypatch.setattr("app.tools.news.get_json_cache", lambda: cache)

    analysis = get_news_analysis("aapl")

    assert analysis.ticker == "AAPL"
    assert analysis.sentiment == SentimentLabel.positive
    assert cache.writes == []
