from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db import repo
from app.db.session import get_db
from app.schemas.reports import ReportResponse
from app.services.formatter import to_markdown


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportResponse])
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ReportResponse]:
    return [
        ReportResponse.model_validate(record)
        for record in repo.list_reports(db, limit=limit)
    ]


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ReportResponse:
    record = repo.get_report(db, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return ReportResponse.model_validate(record)


@router.get("/{report_id}/markdown", response_class=Response)
def get_report_markdown(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    record = repo.get_report(db, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return Response(
        content=to_markdown(record),
        media_type="text/markdown",
    )
