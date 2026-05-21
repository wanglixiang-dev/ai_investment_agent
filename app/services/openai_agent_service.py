import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.schemas.agent import AgentResearchRequest, AgentResearchResponse, ToolExecution
from app.tools.news_analysis import get_news_analysis
from app.tools.stock_data import get_stock_quote


class AgentServiceError(RuntimeError):
    pass


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_stock_quote",
        "description": "Get the latest available quote for a public company ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol such as AAPL, MSFT, or NVDA.",
                }
            },
            "required": ["ticker"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_news_analysis",
        "description": "Get recent company news headlines and baseline sentiment analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol such as AAPL, MSFT, or NVDA.",
                }
            },
            "required": ["ticker"],
            "additionalProperties": False,
        },
    },
]


def run_openai_research_agent(
    request: AgentResearchRequest,
    client: OpenAI | None = None,
) -> AgentResearchResponse:
    settings = get_settings()
    if client is None:
        if not settings.openai_api_key:
            raise AgentServiceError("OPENAI_API_KEY is required to run the OpenAI agent.")
        client = OpenAI(api_key=settings.openai_api_key)

    ticker = request.ticker.strip().upper()
    input_items: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Create a concise investment research note for {ticker}. "
                f"Investment horizon: {request.horizon.value}. "
                f"Risk tolerance: {request.risk_level.value}. "
                "Use the available tools for market data and news before writing."
            ),
        }
    ]

    tool_executions: list[ToolExecution] = []

    try:
        response = client.responses.create(
            model=settings.openai_model,
            instructions=_agent_instructions(),
            input=input_items,
            tools=TOOL_DEFINITIONS,
        )

        for _ in range(3):
            function_calls = _extract_function_calls(response)
            if not function_calls:
                return AgentResearchResponse(
                    ticker=ticker,
                    model=settings.openai_model,
                    final_report=_output_text(response),
                    tool_calls=tool_executions,
                    data_sources=_data_sources(tool_executions),
                )

            tool_outputs = []
            for call in function_calls:
                result = execute_agent_tool(call["name"], call["arguments"])
                tool_executions.append(
                    ToolExecution(
                        name=call["name"],
                        arguments=call["arguments"],
                        result=result,
                    )
                )
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result),
                    }
                )

            response = client.responses.create(
                model=settings.openai_model,
                instructions=_agent_instructions(),
                input=tool_outputs,
                tools=TOOL_DEFINITIONS,
                previous_response_id=_response_id(response),
            )
    except Exception as exc:
        if isinstance(exc, AgentServiceError):
            raise
        raise AgentServiceError(f"OpenAI agent failed: {exc}") from exc

    raise AgentServiceError("OpenAI agent exceeded the maximum tool-calling rounds.")


def execute_agent_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    ticker = str(arguments.get("ticker", "")).strip().upper()
    if not ticker:
        raise AgentServiceError(f"{name} requires a ticker argument.")

    if name == "get_stock_quote":
        return get_stock_quote(ticker).model_dump(mode="json")

    if name == "get_news_analysis":
        return get_news_analysis(ticker).model_dump(mode="json")

    raise AgentServiceError(f"Unknown tool requested by model: {name}")


def _extract_function_calls(response: Any) -> list[dict[str, Any]]:
    calls = []
    for item in getattr(response, "output", []):
        item_type = _get_attr(item, "type")
        if item_type != "function_call":
            continue

        calls.append(
            {
                "call_id": _get_attr(item, "call_id"),
                "name": _get_attr(item, "name"),
                "arguments": json.loads(_get_attr(item, "arguments") or "{}"),
            }
        )

    return calls


def _get_attr(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _response_id(response: Any) -> str | None:
    return _get_attr(response, "id")


def _output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text)
    return "The model returned no final text."


def _data_sources(tool_executions: list[ToolExecution]) -> list[str]:
    sources = []
    if any(call.name == "get_stock_quote" for call in tool_executions):
        sources.append("yfinance:quote")
    if any(call.name == "get_news_analysis" for call in tool_executions):
        sources.append("yfinance:news")
    return sources


def _agent_instructions() -> str:
    return (
        "You are an investment research assistant. Use tools before making claims "
        "about current price or news. Write a concise report with sections for "
        "Thesis, Market Data, News Sentiment, Key Risks, and Watchlist Decision. "
        "Do not invent missing data."
    )
