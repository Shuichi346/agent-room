import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx

from backend.app.orchestration.factory import build_agent
from backend.app.orchestration.llm import chat_completion, rolling_history
from backend.app.schemas import Attachment, Conversation, Message, RunRequest, utc_now
from backend.app.storage import conversation_repo

logger = logging.getLogger(__name__)
_cancel_events: dict[str, asyncio.Event] = {}


def encode_sse(ev: dict) -> bytes:
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode()


def cancel_conversation(conv_id: str) -> bool:
    event = _cancel_events.get(conv_id)
    if not event:
        return False
    event.set()
    return True


def _attachment_text(attachments: list[Attachment]) -> str:
    parts: list[str] = []
    for attachment in attachments:
        if attachment.kind == "url":
            parts.append(f"\n\n[Reference content from {attachment.source}]\n{attachment.payload}")
        elif attachment.kind == "image":
            source = attachment.source or "attached image"
            parts.append(
                f"\n\n[Image attached: {source}. If your model supports vision, consider it.]"
            )
    return "".join(parts)


def _agent_prompt(agent_name: str, pattern: str) -> str:
    return (
        "You are participating in a multi-agent discussion inside agent-room. "
        f"You are speaking as {agent_name}. Keep your reply focused, concise, and useful. "
        f"The current conversation pattern is {pattern}. Build on prior messages and do not "
        "pretend to use tools you do not have."
    )


def _turn_input(conv: Conversation) -> str:
    transcript = []
    for message in conv.messages[-40:]:
        transcript.append(f"{message.name}: {message.content}")
    return (
        "Conversation so far:\n"
        + "\n\n".join(transcript)
        + "\n\nNow provide your next contribution."
    )


async def _choose_free_flow_agent(conv: Conversation) -> str:
    agents = conv.preset_snapshot.agents
    names = [agent.name for agent in agents]
    if len(agents) == 1:
        return agents[0].id
    selector_model = conv.preset_snapshot.auto_agent_model or agents[0].model
    history = rolling_history(conv.messages, limit=12)
    system = (
        "Select the next speaker for a multi-agent discussion. "
        "Return only the exact name of one available agent."
    )
    user = {
        "role": "user",
        "content": f"Available agents: {', '.join(names)}\n\nWho should speak next?",
    }
    try:
        selected = await chat_completion(
            model=selector_model,
            system_prompt=system,
            messages=[*history, user],
            temperature=0.2,
        )
        for agent in agents:
            if agent.name.lower() in selected.lower():
                return agent.id
    except Exception as exc:
        logger.info("Free-flow selector fell back to local order: %s", exc)

    assistant_count = len([msg for msg in conv.messages if msg.role == "assistant"])
    return agents[(assistant_count * 2 + 1) % len(agents)].id


async def _run_agent_turn(conv: Conversation, agent_id: str, queue: asyncio.Queue[dict]) -> None:
    agent = next(agent for agent in conv.preset_snapshot.agents if agent.id == agent_id)
    await queue.put(
        {
            "type": "message_start",
            "conversation_id": conv.id,
            "agent_id": agent.id,
            "name": agent.name,
        }
    )
    system_prompt = f"{agent.persona}\n\n{_agent_prompt(agent.name, conv.preset_snapshot.pattern)}"
    try:
        runtime_agent = build_agent(agent, _agent_prompt(agent.name, conv.preset_snapshot.pattern))
        response = await runtime_agent.run(_turn_input(conv))
        content = str(getattr(response, "text", "") or response).strip()
        if not content:
            content = f"{agent.name} completed the turn, but the model returned an empty response."
    except Exception as exc:
        if isinstance(exc, httpx.HTTPError):
            content = (
                f"Unable to reach LM Studio for {agent.name}: {exc}. "
                "Confirm LM Studio is running and the selected model is loaded."
            )
        else:
            logger.info("Agent Framework run failed; falling back to direct chat call: %s", exc)
            try:
                content = await chat_completion(
                    model=agent.model,
                    system_prompt=system_prompt,
                    messages=rolling_history(conv.messages),
                )
            except Exception as fallback_exc:
                content = f"{agent.name} could not complete the turn: {fallback_exc}"

    msg = Message(
        agent_id=agent.id,
        role="assistant",
        name=agent.name,
        content=content,
        created_at=utc_now(),
    )
    conv.messages.append(msg)
    conversation_repo.save_conversation(conv)
    await queue.put(
        {
            "type": "message_complete",
            "conversation_id": conv.id,
            "message": msg.model_dump(mode="json"),
            "agent_id": agent.id,
            "name": agent.name,
            "content": content,
        }
    )


async def _conversation_task(
    req: RunRequest,
    conv: Conversation,
    queue: asyncio.Queue[dict],
) -> None:
    cancel_event = _cancel_events[conv.id]
    try:
        for turn_index in range(req.preset.max_turns):
            if cancel_event.is_set():
                await queue.put({"type": "cancelled", "conversation_id": conv.id})
                return
            if req.preset.pattern == "round_robin":
                agent = req.preset.agents[turn_index % len(req.preset.agents)]
                agent_id = agent.id
            else:
                agent_id = await _choose_free_flow_agent(conv)
            await _run_agent_turn(conv, agent_id, queue)
        await queue.put({"type": "done", "conversation_id": conv.id, "reason": "max_turns"})
    except Exception as exc:
        logger.exception("Conversation failed")
        await queue.put({"type": "error", "conversation_id": conv.id, "message": str(exc)})
    finally:
        await queue.put({"type": "sentinel"})


async def run_conversation(req: RunRequest) -> AsyncIterator[bytes]:
    existing = (
        conversation_repo.get_conversation(req.conversation_id) if req.conversation_id else None
    )
    conv = existing or Conversation(
        id=req.conversation_id or uuid4().hex,
        preset_snapshot=req.preset,
    )
    prompt = req.prompt + _attachment_text(req.attachments)
    user_message = Message(
        role="user",
        name="You",
        content=prompt,
        attachments=req.attachments,
        created_at=utc_now(),
    )
    conv.messages.append(user_message)
    conv.preset_snapshot = req.preset
    conversation_repo.save_conversation(conv)

    cancel_event = asyncio.Event()
    _cancel_events[conv.id] = cancel_event
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)
    await queue.put(
        {
            "type": "conversation_started",
            "conversation_id": conv.id,
            "message": user_message.model_dump(mode="json"),
        }
    )
    task = asyncio.create_task(_conversation_task(req, conv, queue))

    try:
        while True:
            event = await queue.get()
            if event.get("type") == "sentinel":
                break
            yield encode_sse(event)
    finally:
        cancel_event.set()
        _cancel_events.pop(conv.id, None)
        try:
            await asyncio.wait_for(task, timeout=2)
        except TimeoutError:
            task.cancel()
