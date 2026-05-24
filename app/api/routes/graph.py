from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repo import create_report
from app.db.session import get_db
from app.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.services.workflow import run_workflow


router = APIRouter(prefix="/graph", tags=["langgraph"])


@router.post("/research", response_model=WorkflowResponse)
def create_graph_research(
    request: WorkflowRequest,
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowResponse:
    response = run_workflow(request)
    record = create_report(db, request, response)
    return response.model_copy(update={"report_id": record.id})
