from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchReportRecord
from app.schemas.workflow import GraphResearchRequest, GraphResearchResponse


def create_research_report_record(
    db: Session,
    request: GraphResearchRequest,
    response: GraphResearchResponse,
) -> ResearchReportRecord:
    record = ResearchReportRecord(
        ticker=response.ticker,
        horizon=request.horizon.value,
        risk_level=request.risk_level.value,
        final_report=response.final_report,
        steps=[step.model_dump() for step in response.steps],
        data_sources=response.data_sources,
        errors=response.errors,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_research_report_records(
    db: Session,
    limit: int = 20,
) -> list[ResearchReportRecord]:
    statement = (
        select(ResearchReportRecord)
        .order_by(ResearchReportRecord.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def get_research_report_record(
    db: Session,
    report_id: int,
) -> ResearchReportRecord | None:
    return db.get(ResearchReportRecord, report_id)
