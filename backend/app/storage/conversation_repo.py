import json
import logging
import os
from pathlib import Path

from backend.app.paths import get_conversations_dir
from backend.app.schemas import Conversation, ConversationSummary, Message, utc_now

logger = logging.getLogger(__name__)


def _path(conv_id: str) -> Path:
    return get_conversations_dir() / f"{conv_id}.json"


def _load(path: Path) -> Conversation | None:
    try:
        return Conversation.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Skipping unreadable conversation %s: %s", path, exc)
        return None


def list_conversations() -> list[ConversationSummary]:
    summaries: list[ConversationSummary] = []
    for path in sorted(get_conversations_dir().glob("*.json")):
        conv = _load(path)
        if not conv:
            continue
        summaries.append(
            ConversationSummary(
                id=conv.id,
                title=conv.title or "Untitled conversation",
                updated_at=conv.updated_at,
                message_count=len(conv.messages),
            )
        )
    return sorted(summaries, key=lambda item: item.updated_at, reverse=True)


def get_conversation(conv_id: str) -> Conversation | None:
    path = _path(conv_id)
    if not path.exists():
        return None
    return _load(path)


def save_conversation(conv: Conversation) -> Conversation:
    if not conv.title:
        first_user = next((msg for msg in conv.messages if msg.role == "user"), None)
        conv.title = (first_user.content[:60] if first_user else "Untitled conversation").strip()
    conv.updated_at = utc_now()
    path = _path(conv.id)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(conv.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)
    return conv


def append_message(conv_id: str, msg: Message) -> Conversation:
    conv = get_conversation(conv_id)
    if conv is None:
        raise KeyError(conv_id)
    conv.messages.append(msg)
    return save_conversation(conv)


def delete_conversation(conv_id: str) -> bool:
    path = _path(conv_id)
    if path.exists():
        path.unlink()
        return True
    return False

