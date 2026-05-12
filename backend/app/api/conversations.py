from fastapi import APIRouter, HTTPException

from backend.app.schemas import Conversation, ConversationSummary
from backend.app.storage import conversation_repo

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/")
async def list_conversations() -> list[ConversationSummary]:
    return conversation_repo.list_conversations()


@router.get("/{conv_id}")
async def get_conversation(conv_id: str) -> Conversation:
    conv = conversation_repo.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str) -> dict[str, bool]:
    deleted = conversation_repo.delete_conversation(conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"deleted": True}

