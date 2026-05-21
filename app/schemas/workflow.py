from pydantic import BaseModel, Field

from app.schemas.research import ResearchHorizon, RiskLevel


class GraphResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    horizon: ResearchHorizon = ResearchHorizon.medium_term
    risk_level: RiskLevel = RiskLevel.medium


class WorkflowStep(BaseModel):
    name: str
    status: str
    message: str


class GraphResearchResponse(BaseModel):
    report_id: int | None = None
    ticker: str
    horizon: ResearchHorizon
    risk_level: RiskLevel
    final_report: str
    steps: list[WorkflowStep]
    data_sources: list[str]
    errors: list[str]
