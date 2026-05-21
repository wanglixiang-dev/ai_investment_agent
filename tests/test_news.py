from fastapi.testclient import TestClient

from app.main import app
from app.schemas.news import NewsAnalysis, NewsArticle, SentimentLabel


client = TestClient(app)


def test_read_news_analysis(monkeypatch) -> None:
    def fake_get_news_analysis(ticker: str) -> NewsAnalysis:
        return NewsAnalysis(
            ticker=ticker.upper(),
            sentiment=SentimentLabel.positive,
            score=0.5,
            article_count=2,
            key_headlines=[
                "AAPL revenue growth beats expectations",
                "Analysts upgrade Apple after strong results",
            ],
            summary="AAPL recent news sentiment is positive.",
            articles=[
                NewsArticle(title="AAPL revenue growth beats expectations"),
                NewsArticle(title="Analysts upgrade Apple after strong results"),
            ],
        )

    monkeypatch.setattr("app.api.routes.news.get_news_analysis", fake_get_news_analysis)

    response = client.get("/news/aapl/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["sentiment"] == "positive"
    assert body["article_count"] == 2
    assert body["source"] == "yfinance"


def test_read_news_analysis_returns_502_on_provider_error(monkeypatch) -> None:
    from app.tools.news_analysis import NewsDataError

    def fake_get_news_analysis(ticker: str) -> NewsAnalysis:
        raise NewsDataError(f"No news data returned for {ticker.upper()}.")

    monkeypatch.setattr("app.api.routes.news.get_news_analysis", fake_get_news_analysis)

    response = client.get("/news/unknown/analysis")

    assert response.status_code == 502
    assert response.json()["detail"] == "No news data returned for UNKNOWN."
