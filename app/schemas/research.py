from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchHorizon(StrEnum):
    short_term = "short_term"
    medium_term = "medium_term"
    long_term = "long_term"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class ResearchRequest(BaseModel):
    ticker: str = Field(
        min_length=1,
        max_length=10,
        description="Public company ticker symbol, such as AAPL or MSFT.",
    )
    horizon: ResearchHorizon = Field(
        default=ResearchHorizon.medium_term,
        description="Investment time horizon for the research report.",
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.medium,
        description="Investor risk tolerance used to frame the analysis.",
    )


class ReportSection(BaseModel):
    title: str
    summary: str


class ResearchReport(BaseModel):
    ticker: str
    horizon: ResearchHorizon
    risk_level: RiskLevel
    thesis: str
    recommendation: str
    sections: list[ReportSection]
    data_sources: list[str]
