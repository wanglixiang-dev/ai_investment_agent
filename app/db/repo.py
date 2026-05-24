from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReportRecord
from app.schemas.workflow import WorkflowRequest, WorkflowResponse


def create_report(
    db: Session,
    request: WorkflowRequest,
    response: WorkflowResponse,
) -> ReportRecord:
    record = ReportRecord(
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


def list_reports(
    db: Session,
    limit: int = 20,
) -> list[ReportRecord]:
    statement = (
        select(ReportRecord)
        .order_by(ReportRecord.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def get_report(
    db: Session,
    report_id: int,
) -> ReportRecord | None:
    return db.get(ReportRecord, report_id)
