from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SentimentLabel(StrEnum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class NewsArticle(BaseModel):
    title: str
    publisher: str | None = None
    link: str | None = None
    published_at: datetime | None = None
    summary: str | None = None


class NewsAnalysis(BaseModel):
    ticker: str = Field(description="Normalized ticker symbol.")
    sentiment: SentimentLabel
    score: float = Field(ge=-1.0, le=1.0)
    article_count: int = Field(ge=0)
    key_headlines: list[str]
    summary: str
    articles: list[NewsArticle]
    source: str = Field(default="yfinance")
