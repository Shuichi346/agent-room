from fastapi import APIRouter, HTTPException

from backend.app.orchestration.auto_agents import generate_agents
from backend.app.schemas import AutoAgentRequest, AutoAgentResponse

router = APIRouter(prefix="/api/auto-agents", tags=["auto-agents"])


@router.post("/")
async def auto_agents(req: AutoAgentRequest) -> AutoAgentResponse:
    try:
        agents = await generate_agents(req.theme, req.count, req.model)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AutoAgentResponse(agents=agents)

