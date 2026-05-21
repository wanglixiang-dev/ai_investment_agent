from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentResearchRequest, AgentResearchResponse
from app.services.openai_agent_service import AgentServiceError, run_openai_research_agent


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/research", response_model=AgentResearchResponse)
def create_agent_research(request: AgentResearchRequest) -> AgentResearchResponse:
    try:
        return run_openai_research_agent(request)
    except AgentServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
