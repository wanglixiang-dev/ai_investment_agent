from pydantic import BaseModel, Field

from app.schemas.research import ResearchHorizon, RiskLevel


class AgentRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    horizon: ResearchHorizon = ResearchHorizon.medium_term
    risk_level: RiskLevel = RiskLevel.medium


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result: dict


class AgentResponse(BaseModel):
    ticker: str
    model: str
    final_report: str
    tool_calls: list[ToolCall]
    data_sources: list[str]
