from fastapi import APIRouter, HTTPException

from backend.app.paths import get_conversations_dir, get_presets_dir
from backend.app.schemas import (
    AgentCapability,
    AgentManifest,
    AgentRunRequest,
    AgentRunResponse,
    RunRequest,
)
from backend.app.storage import preset_repo

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _resolve_run_request(req: AgentRunRequest) -> RunRequest:
    preset = req.preset
    if req.preset_id:
        preset = preset_repo.get_preset(req.preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="preset not found")
    if preset is None:
        raise HTTPException(status_code=400, detail="preset is required")
    if req.max_turns is not None:
        preset = preset.model_copy(update={"max_turns": req.max_turns})
    return RunRequest(
        preset=preset,
        prompt=req.prompt,
        attachments=req.attachments,
        conversation_id=req.conversation_id,
    )


@router.get("/manifest")
async def agent_manifest() -> AgentManifest:
    return AgentManifest(
        name="agent-room",
        version="0.1.0",
        description=(
            "Local-first multi-agent discussion runtime with JSON preset, conversation, "
            "and non-streaming run APIs for autonomous callers."
        ),
        endpoints=[
            AgentCapability(
                method="GET",
                path="/api/agents/manifest",
                description="Return machine-readable API capabilities for AI agents.",
            ),
            AgentCapability(
                method="POST",
                path="/api/agents/run",
                description="Run a preset to completion and return JSON instead of SSE.",
            ),
            AgentCapability(
                method="GET",
                path="/api/presets/",
                description="List saved presets that can be referenced by preset_id.",
            ),
            AgentCapability(
                method="GET",
                path="/api/conversations/{conversation_id}",
                description="Read a persisted conversation transcript.",
            ),
        ],
        storage={
            "presets": str(get_presets_dir()),
            "conversations": str(get_conversations_dir()),
        },
    )


@router.post("/run")
async def run_agent_conversation(req: AgentRunRequest) -> AgentRunResponse:
    from backend.app.orchestration.runner import run_conversation_to_completion

    return await run_conversation_to_completion(_resolve_run_request(req))
