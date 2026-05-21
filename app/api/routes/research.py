from fastapi import APIRouter

from app.schemas.research import ResearchRequest, ResearchReport
from app.services.research_service import build_mock_research_report


router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchReport)
def create_research_report(request: ResearchRequest) -> ResearchReport:
    return build_mock_research_report(request)
