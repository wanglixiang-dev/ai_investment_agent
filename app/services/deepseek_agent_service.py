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
        "function": {
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
    },
    {
        "type": "function",
        "function": {
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
    },
]


def run_deepseek_research_agent(
    request: AgentResearchRequest,
    client: OpenAI | None = None,
) -> AgentResearchResponse:
    settings = get_settings()
    if client is None:
        if not settings.deepseek_api_key:
            raise AgentServiceError("DEEPSEEK_API_KEY is required to run the DeepSeek agent.")
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    ticker = request.ticker.strip().upper()
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _agent_instructions(),
        },
        {
            "role": "user",
            "content": (
                f"Create a concise investment research note for {ticker}. "
                f"Investment horizon: {request.horizon.value}. "
                f"Risk tolerance: {request.risk_level.value}. "
                "Use the available tools for market data and news before writing."
            ),
        },
    ]

    tool_executions: list[ToolExecution] = []

    try:
        for _ in range(3):
            completion = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )
            message = completion.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []

            if not tool_calls:
                return AgentResearchResponse(
                    ticker=ticker,
                    model=settings.deepseek_model,
                    final_report=_message_content(message),
                    tool_calls=tool_executions,
                    data_sources=_data_sources(tool_executions),
                )

            messages.append(_assistant_message_with_tool_calls(message))

            for tool_call in tool_calls:
                function = tool_call.function
                name = function.name
                arguments = json.loads(function.arguments or "{}")
                result = execute_agent_tool(name, arguments)
                tool_executions.append(
                    ToolExecution(
                        name=name,
                        arguments=arguments,
                        result=result,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )
    except Exception as exc:
        if isinstance(exc, AgentServiceError):
            raise
        raise AgentServiceError(f"DeepSeek agent failed: {exc}") from exc

    raise AgentServiceError("DeepSeek agent exceeded the maximum tool-calling rounds.")


def execute_agent_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    ticker = str(arguments.get("ticker", "")).strip().upper()
    if not ticker:
        raise AgentServiceError(f"{name} requires a ticker argument.")

    if name == "get_stock_quote":
        return get_stock_quote(ticker).model_dump(mode="json")

    if name == "get_news_analysis":
        return get_news_analysis(ticker).model_dump(mode="json")

    raise AgentServiceError(f"Unknown tool requested by model: {name}")


def _assistant_message_with_tool_calls(message: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": _message_content(message) or None,
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ],
    }


def _message_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content:
        return str(content)
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
