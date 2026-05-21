import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.agent import AgentResearchRequest
from app.services.deepseek_agent_service import execute_agent_tool, run_deepseek_research_agent


client = TestClient(app)


class FakeChatCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            quote_tool_call = SimpleNamespace(
                id="call_quote",
                function=SimpleNamespace(
                    name="get_stock_quote",
                    arguments=json.dumps({"ticker": "AAPL"}),
                ),
            )
            news_tool_call = SimpleNamespace(
                id="call_news",
                function=SimpleNamespace(
                    name="get_news_analysis",
                    arguments=json.dumps({"ticker": "AAPL"}),
                ),
            )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[quote_tool_call, news_tool_call],
                        )
                    )
                ]
            )

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Final report using quote and news tools.",
                        tool_calls=None,
                    )
                )
            ]
        )


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeChatCompletions()


class FakeClient:
    def __init__(self) -> None:
        self.chat = FakeChat()


def test_run_deepseek_research_agent_executes_tool_loop(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.deepseek_agent_service.get_stock_quote",
        lambda ticker: SimpleNamespace(model_dump=lambda mode: {"ticker": ticker, "price": 210.12}),
    )
    monkeypatch.setattr(
        "app.services.deepseek_agent_service.get_news_analysis",
        lambda ticker: SimpleNamespace(
            model_dump=lambda mode: {
                "ticker": ticker,
                "sentiment": "positive",
                "article_count": 2,
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.deepseek_agent_service.get_settings",
        lambda: SimpleNamespace(
            deepseek_api_key="test-key",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-flash",
        ),
    )

    result = run_deepseek_research_agent(
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
    monkeypatch.setattr(
        "app.services.deepseek_agent_service.get_settings",
        lambda: SimpleNamespace(deepseek_api_key=None),
    )

    response = client.post("/agent/research", json={"ticker": "AAPL"})

    assert response.status_code == 503
    assert response.json()["detail"] == "DEEPSEEK_API_KEY is required to run the DeepSeek agent."
