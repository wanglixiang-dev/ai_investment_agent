from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent import AgentServiceError, run_agent


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/research", response_model=AgentResponse)
def create_agent_research(request: AgentRequest) -> AgentResponse:
    try:
        return run_agent(request)
    except AgentServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
