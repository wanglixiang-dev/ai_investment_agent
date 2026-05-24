from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    id: int
    ticker: str
    horizon: str
    risk_level: str
    final_report: str
    steps: list[dict[str, Any]]
    data_sources: list[str]
    errors: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
