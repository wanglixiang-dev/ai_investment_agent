from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.filings import FilingSearchResponse
from app.schemas.news import NewsAnalysis
from app.schemas.stocks import StockQuote
from app.schemas.workflow import WorkflowRequest, WorkflowResponse, WorkflowStep
from app.tools.filings import FilingRagError, search_filing_context
from app.tools.news import NewsDataError, get_news_analysis
from app.tools.stocks import StockDataError, get_stock_quote


class ResearchWorkflowState(TypedDict, total=False):
    ticker: str
    horizon: str
    risk_level: str
    quote: dict[str, Any]
    news: dict[str, Any]
    filing_context: dict[str, Any]
    final_report: str
    steps: list[dict[str, str]]
    data_sources: list[str]
    errors: list[str]


def run_workflow(request: WorkflowRequest) -> WorkflowResponse:
    ticker = request.ticker.strip().upper()
    initial_state: ResearchWorkflowState = {
        "ticker": ticker,
        "horizon": request.horizon.value,
        "risk_level": request.risk_level.value,
        "steps": [],
        "data_sources": [],
        "errors": [],
    }

    final_state = build_workflow().invoke(initial_state)

    return WorkflowResponse(
        ticker=ticker,
        horizon=request.horizon,
        risk_level=request.risk_level,
        final_report=final_state["final_report"],
        steps=[WorkflowStep(**step) for step in final_state.get("steps", [])],
        data_sources=final_state.get("data_sources", []),
        errors=final_state.get("errors", []),
    )


@lru_cache
def build_workflow():
    graph = StateGraph(ResearchWorkflowState)

    graph.add_node("fetch_market_data", fetch_market_data)
    graph.add_node("analyze_news", analyze_news)
    graph.add_node("retrieve_filing_context", retrieve_filing_context)
    graph.add_node("generate_report", generate_report)

    graph.add_edge(START, "fetch_market_data")
    graph.add_edge("fetch_market_data", "analyze_news")
    graph.add_edge("analyze_news", "retrieve_filing_context")
    graph.add_edge("retrieve_filing_context", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


def fetch_market_data(state: ResearchWorkflowState) -> ResearchWorkflowState:
    ticker = state["ticker"]
    try:
        quote = get_stock_quote(ticker)
        return {
            "quote": quote.model_dump(mode="json"),
            "steps": _append_step(
                state,
                "fetch_market_data",
                "success",
                f"Fetched latest available quote for {ticker}.",
            ),
            "data_sources": _append_unique(state, "yfinance:quote"),
        }
    except StockDataError as exc:
        return {
            "steps": _append_step(
                state,
                "fetch_market_data",
                "failed",
                f"Market data unavailable for {ticker}.",
            ),
            "errors": [*state.get("errors", []), str(exc)],
        }


def analyze_news(state: ResearchWorkflowState) -> ResearchWorkflowState:
    ticker = state["ticker"]
    try:
        news = get_news_analysis(ticker)
        return {
            "news": news.model_dump(mode="json"),
            "steps": _append_step(
                state,
                "analyze_news",
                "success",
                f"Analyzed recent Yahoo Finance headlines for {ticker}.",
            ),
            "data_sources": _append_unique(state, "yfinance:news"),
        }
    except NewsDataError as exc:
        return {
            "steps": _append_step(
                state,
                "analyze_news",
                "failed",
                f"News data unavailable for {ticker}.",
            ),
            "errors": [*state.get("errors", []), str(exc)],
        }


def retrieve_filing_context(state: ResearchWorkflowState) -> ResearchWorkflowState:
    ticker = state["ticker"]
    query = (
        f"{ticker} business risks revenue growth margins liquidity competition "
        "management discussion financial condition"
    )
    try:
        filing_context = search_filing_context(ticker=ticker, query=query, top_k=3)
        return {
            "filing_context": filing_context.model_dump(mode="json"),
            "steps": _append_step(
                state,
                "retrieve_filing_context",
                "success",
                f"Retrieved local filing context for {ticker}.",
            ),
            "data_sources": _append_unique(state, "local_filings"),
        }
    except FilingRagError as exc:
        return {
            "steps": _append_step(
                state,
                "retrieve_filing_context",
                "failed",
                f"Filing context unavailable for {ticker}.",
            ),
            "errors": [*state.get("errors", []), str(exc)],
        }


def generate_report(state: ResearchWorkflowState) -> ResearchWorkflowState:
    report = "\n\n".join(
        [
            _thesis_section(state),
            _market_data_section(state),
            _news_section(state),
            _filing_section(state),
            _risk_section(state),
            _decision_section(state),
        ]
    )

    return {
        "final_report": report,
        "steps": _append_step(
            state,
            "generate_report",
            "success",
            "Generated deterministic research report from workflow state.",
        ),
    }


def _thesis_section(state: ResearchWorkflowState) -> str:
    return (
        f"Thesis\n"
        f"{state['ticker']} is currently a watchlist candidate for a "
        f"{state['horizon']} investor with {state['risk_level']} risk tolerance. "
        "The workflow combines market data and recent news before a final decision."
    )


def _market_data_section(state: ResearchWorkflowState) -> str:
    quote_data = state.get("quote")
    if not quote_data:
        return "Market Data\nMarket data was unavailable, so price-based conclusions are limited."

    quote = StockQuote.model_validate(quote_data)
    previous_close = (
        f" Previous close was {_format_money(quote.previous_close, quote.currency)}."
        if quote.previous_close is not None
        else ""
    )
    volume = f" Latest reported volume was {quote.volume:,}." if quote.volume else ""
    return (
        "Market Data\n"
        f"Latest available price is {_format_money(quote.price, quote.currency)}."
        f"{previous_close}{volume}"
    )


def _news_section(state: ResearchWorkflowState) -> str:
    news_data = state.get("news")
    if not news_data:
        return "News Sentiment\nNews data was unavailable, so sentiment conclusions are limited."

    news = NewsAnalysis.model_validate(news_data)
    headlines = "; ".join(news.key_headlines[:3])
    return f"News Sentiment\n{news.summary} Key headlines: {headlines}"


def _filing_section(state: ResearchWorkflowState) -> str:
    filing_data = state.get("filing_context")
    if not filing_data:
        return "SEC Filing Insights\nNo local filing context was available for this ticker."

    filing_context = FilingSearchResponse.model_validate(filing_data)
    bullets = [
        f"- {chunk.text[:240]}{'...' if len(chunk.text) > 240 else ''}"
        for chunk in filing_context.chunks
    ]
    return "SEC Filing Insights\n" + "\n".join(bullets)


def _risk_section(state: ResearchWorkflowState) -> str:
    risks = [
        "provider data may be delayed or incomplete",
        "keyword sentiment can miss nuance",
    ]
    if state.get("errors"):
        risks.append("one or more workflow tools failed")

    return f"Key Risks\nPrimary risks: {', '.join(risks)}."


def _decision_section(state: ResearchWorkflowState) -> str:
    if state.get("quote") and state.get("news") and state.get("filing_context"):
        decision = "watchlist with further SEC filing review"
    elif state.get("quote") and state.get("news"):
        decision = "watchlist pending SEC filing review"
    else:
        decision = "insufficient data for a confident decision"

    return f"Watchlist Decision\nDecision: {decision}."


def _append_step(
    state: ResearchWorkflowState,
    name: str,
    status: str,
    message: str,
) -> list[dict[str, str]]:
    return [
        *state.get("steps", []),
        {
            "name": name,
            "status": status,
            "message": message,
        },
    ]


def _append_unique(state: ResearchWorkflowState, source: str) -> list[str]:
    sources = state.get("data_sources", [])
    if source in sources:
        return sources
    return [*sources, source]


def _format_money(value: float, currency: str | None) -> str:
    prefix = "$" if currency == "USD" else ""
    suffix = "" if currency == "USD" or currency is None else f" {currency}"
    return f"{prefix}{value:,.2f}{suffix}"
