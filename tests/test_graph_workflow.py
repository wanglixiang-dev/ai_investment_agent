from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.news import NewsAnalysis, NewsArticle, SentimentLabel
from app.schemas.stocks import StockQuote
from app.schemas.filings import FilingChunk, FilingSearchResponse


client = TestClient(app)


def override_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        yield db


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


def fake_filing_context(ticker: str, query: str, top_k: int = 3) -> FilingSearchResponse:
    return FilingSearchResponse(
        ticker=ticker.upper(),
        query=query,
        chunks=[
            FilingChunk(
                ticker=ticker.upper(),
                chunk_id=0,
                score=0.75,
                text="Revenue growth depends on services margin and product demand.",
            )
        ],
    )


def test_graph_research_workflow_success(monkeypatch) -> None:
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.get_stock_quote",
        fake_stock_quote,
    )
    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.get_news_analysis",
        fake_news_analysis,
    )
    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.search_filing_context",
        fake_filing_context,
    )

    response = client.post("/graph/research", json={"ticker": "aapl"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["data_sources"] == ["yfinance:quote", "yfinance:news", "local_filings"]
    assert [step["name"] for step in body["steps"]] == [
        "fetch_market_data",
        "analyze_news",
        "retrieve_filing_context",
        "generate_report",
    ]
    assert "Market Data" in body["final_report"]
    assert "News Sentiment" in body["final_report"]
    assert "SEC Filing Insights" in body["final_report"]
    assert body["report_id"] == 1
    app.dependency_overrides.clear()


def test_graph_research_workflow_continues_when_tools_fail(monkeypatch) -> None:
    app.dependency_overrides[get_db] = override_db
    from app.tools.news_analysis import NewsDataError
    from app.tools.stock_data import StockDataError
    from app.tools.filing_rag import FilingRagError

    def fail_quote(ticker: str) -> StockQuote:
        raise StockDataError("quote timeout")

    def fail_news(ticker: str) -> NewsAnalysis:
        raise NewsDataError("news timeout")

    def fail_filing(ticker: str, query: str, top_k: int = 3) -> FilingSearchResponse:
        raise FilingRagError("filing missing")

    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.get_stock_quote",
        fail_quote,
    )
    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.get_news_analysis",
        fail_news,
    )
    monkeypatch.setattr(
        "app.services.langgraph_research_workflow.search_filing_context",
        fail_filing,
    )

    response = client.post("/graph/research", json={"ticker": "nvda"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["data_sources"] == []
    assert body["errors"] == ["quote timeout", "news timeout", "filing missing"]
    assert body["steps"][0]["status"] == "failed"
    assert body["steps"][1]["status"] == "failed"
    assert body["steps"][2]["status"] == "failed"
    assert body["steps"][3]["status"] == "success"
    assert "insufficient data" in body["final_report"]
    assert body["report_id"] == 1
    app.dependency_overrides.clear()
