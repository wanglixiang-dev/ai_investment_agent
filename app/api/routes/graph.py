from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories import create_research_report_record
from app.db.session import get_db
from app.schemas.workflow import GraphResearchRequest, GraphResearchResponse
from app.services.langgraph_research_workflow import run_research_workflow


router = APIRouter(prefix="/graph", tags=["langgraph"])


@router.post("/research", response_model=GraphResearchResponse)
def create_graph_research(
    request: GraphResearchRequest,
    db: Annotated[Session, Depends(get_db)],
) -> GraphResearchResponse:
    response = run_research_workflow(request)
    record = create_research_report_record(db, request, response)
    return response.model_copy(update={"report_id": record.id})
