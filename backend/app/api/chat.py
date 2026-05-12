from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.orchestration.runner import cancel_conversation, run_conversation
from backend.app.schemas import RunRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/run")
async def run_chat(req: RunRequest) -> StreamingResponse:
    return StreamingResponse(
        run_conversation(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cancel/{conv_id}")
async def cancel_chat(conv_id: str) -> dict[str, bool]:
    return {"cancelled": cancel_conversation(conv_id)}

