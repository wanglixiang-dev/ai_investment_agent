import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.agent import AgentResearchRequest
from app.services.openai_agent_service import execute_agent_tool, run_openai_research_agent


client = TestClient(app)


class FakeResponses:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                id="resp_1",
                output_text="",
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_quote",
                        name="get_stock_quote",
                        arguments=json.dumps({"ticker": "AAPL"}),
                    ),
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_news",
                        name="get_news_analysis",
                        arguments=json.dumps({"ticker": "AAPL"}),
                    ),
                ],
            )

        return SimpleNamespace(
            id="resp_2",
            output_text="Final report using quote and news tools.",
            output=[],
        )


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_run_openai_research_agent_executes_tool_loop(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.openai_agent_service.get_stock_quote",
        lambda ticker: SimpleNamespace(model_dump=lambda mode: {"ticker": ticker, "price": 210.12}),
    )
    monkeypatch.setattr(
        "app.services.openai_agent_service.get_news_analysis",
        lambda ticker: SimpleNamespace(
            model_dump=lambda mode: {
                "ticker": ticker,
                "sentiment": "positive",
                "article_count": 2,
            }
        ),
    )

    result = run_openai_research_agent(
        AgentResearchRequest(ticker="aapl"),
        client=FakeClient(),
    )

    assert result.ticker == "AAPL"
    assert result.final_report == "Final report using quote and news tools."
    assert [call.name for call in result.tool_calls] == [
        "get_stock_quote",
        "get_news_analysis",
    ]
    assert result.data_sources == ["yfinance:quote", "yfinance:news"]


def test_execute_agent_tool_rejects_unknown_tool() -> None:
    try:
        execute_agent_tool("unknown_tool", {"ticker": "AAPL"})
    except Exception as exc:
        assert "Unknown tool" in str(exc)
    else:
        raise AssertionError("Expected unknown tool to fail")


def test_agent_route_returns_503_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr("app.services.openai_agent_service.get_settings", lambda: SimpleNamespace(openai_api_key=None))

    response = client.post("/agent/research", json={"ticker": "AAPL"})

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is required to run the OpenAI agent."
