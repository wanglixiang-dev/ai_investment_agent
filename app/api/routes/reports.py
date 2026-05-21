from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.repositories import get_research_report_record, list_research_report_records
from app.db.session import get_db
from app.schemas.reports import ResearchReportRecordResponse
from app.services.report_formatter import format_report_as_markdown


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ResearchReportRecordResponse])
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ResearchReportRecordResponse]:
    return [
        ResearchReportRecordResponse.model_validate(record)
        for record in list_research_report_records(db, limit=limit)
    ]


@router.get("/{report_id}", response_model=ResearchReportRecordResponse)
def get_report(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ResearchReportRecordResponse:
    record = get_research_report_record(db, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return ResearchReportRecordResponse.model_validate(record)


@router.get("/{report_id}/markdown", response_class=Response)
def get_report_markdown(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    record = get_research_report_record(db, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return Response(
        content=format_report_as_markdown(record),
        media_type="text/markdown",
    )
