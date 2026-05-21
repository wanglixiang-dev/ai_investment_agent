from pydantic import BaseModel, Field

from app.schemas.research import ResearchHorizon, RiskLevel


class AgentResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    horizon: ResearchHorizon = ResearchHorizon.medium_term
    risk_level: RiskLevel = RiskLevel.medium


class ToolExecution(BaseModel):
    name: str
    arguments: dict
    result: dict


class AgentResearchResponse(BaseModel):
    ticker: str
    model: str
    final_report: str
    tool_calls: list[ToolExecution]
    data_sources: list[str]
