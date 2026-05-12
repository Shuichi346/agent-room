import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx

from backend.app.orchestration.factory import build_agent
from backend.app.orchestration.llm import chat_completion, rolling_history
from backend.app.schemas import AgentConfig, Attachment, Conversation, Message, RunRequest, utc_now
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


def _agent_prompt(agent: AgentConfig, agents: list[AgentConfig], pattern: str) -> str:
    roster = "\n".join(
        f"- {item.name}{' (you)' if item.id == agent.id else ''}" for item in agents
    )
    return (
        "You are participating in a multi-agent discussion inside agent-room. "
        f"The authoritative display name for this turn is {agent.name}. "
        f"The current conversation pattern is {pattern}.\n\n"
        "Agent roster:\n"
        f"{roster}\n\n"
        "Transcript labels are authoritative. Messages marked (you) are your own earlier "
        "messages; do not address, agree with, or critique them as if another participant wrote "
        "them. Messages marked (other agent) are from another configured agent. Keep your reply "
        "focused, concise, and useful. Write only your next message content without a speaker "
        "label, and do not pretend to use tools you do not have."
    )


def _format_message_for_agent(message: Message, current_agent: AgentConfig) -> str:
    if message.role == "user":
        speaker = "User"
    elif message.agent_id == current_agent.id:
        speaker = f"{message.name} (you)"
    elif message.role == "assistant":
        speaker = f"{message.name} (other agent)"
    else:
        speaker = message.name
    return f"{speaker}: {message.content}"


def _turn_input(conv: Conversation, current_agent: AgentConfig) -> str:
    transcript: list[str] = []
    for message in conv.messages[-40:]:
        transcript.append(_format_message_for_agent(message, current_agent))
    return (
        "Conversation so far, from your point of view:\n"
        + "\n\n".join(transcript)
        + f"\n\nYou are {current_agent.name}. Provide {current_agent.name}'s next contribution. "
        "Do not include a speaker label. Do not reply to statements marked (you) as if they were "
        "from another participant."
    )


def _last_assistant_message(conv: Conversation) -> Message | None:
    return next(
        (message for message in reversed(conv.messages) if message.role == "assistant"),
        None,
    )


def _eligible_free_flow_agents(conv: Conversation) -> list[AgentConfig]:
    agents = conv.preset_snapshot.agents
    if len(agents) <= 1:
        return agents
    last_message = _last_assistant_message(conv)
    if not last_message or not last_message.agent_id:
        return agents
    eligible = [agent for agent in agents if agent.id != last_message.agent_id]
    return eligible or agents


def _fallback_free_flow_agent_id(conv: Conversation, candidates: list[AgentConfig]) -> str:
    agents = conv.preset_snapshot.agents
    if not candidates:
        return agents[0].id
    last_message = _last_assistant_message(conv)
    if last_message and last_message.agent_id:
        last_index = next(
            (index for index, agent in enumerate(agents) if agent.id == last_message.agent_id),
            -1,
        )
        if last_index >= 0:
            candidate_ids = {agent.id for agent in candidates}
            for offset in range(1, len(agents) + 1):
                candidate = agents[(last_index + offset) % len(agents)]
                if candidate.id in candidate_ids:
                    return candidate.id
    assistant_count = len([msg for msg in conv.messages if msg.role == "assistant"])
    return candidates[assistant_count % len(candidates)].id


def _match_agent_name(selected: str, agents: list[AgentConfig]) -> str | None:
    cleaned = selected.strip().strip("`\"'")
    for agent in agents:
        if cleaned.casefold() == agent.name.casefold():
            return agent.id
    selected_normalized = cleaned.casefold()
    for agent in agents:
        if agent.name.casefold() in selected_normalized:
            return agent.id
    return None


async def _choose_free_flow_agent(conv: Conversation) -> str:
    agents = conv.preset_snapshot.agents
    names = [agent.name for agent in agents]
    if len(agents) == 1:
        return agents[0].id
    candidates = _eligible_free_flow_agents(conv)
    candidate_names = [agent.name for agent in candidates]
    last_message = _last_assistant_message(conv)
    last_speaker = last_message.name if last_message else "none"
    selector_model = conv.preset_snapshot.auto_agent_model or agents[0].model
    history = rolling_history(conv.messages, limit=12)
    system = (
        "Select the next speaker for a multi-agent discussion. "
        "Return only the exact name of one eligible agent. "
        "Do not select the previous assistant speaker when another eligible agent exists."
    )
    user = {
        "role": "user",
        "content": (
            f"All agents: {', '.join(names)}\n"
            f"Previous assistant speaker: {last_speaker}\n"
            f"Eligible next speakers: {', '.join(candidate_names)}\n\n"
            "Who should speak next?"
        ),
    }
    try:
        selected = await chat_completion(
            model=selector_model,
            system_prompt=system,
            messages=[*history, user],
            temperature=0.2,
        )
        selected_id = _match_agent_name(selected, candidates)
        if selected_id:
            return selected_id
    except Exception as exc:
        logger.info("Free-flow selector fell back to local order: %s", exc)

    return _fallback_free_flow_agent_id(conv, candidates)


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
    prompt_rules = _agent_prompt(agent, conv.preset_snapshot.agents, conv.preset_snapshot.pattern)
    system_prompt = f"{agent.persona}\n\n{prompt_rules}"
    turn_input = _turn_input(conv, agent)
    try:
        runtime_agent = build_agent(agent, prompt_rules)
        response = await runtime_agent.run(turn_input)
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
                    messages=[{"role": "user", "content": turn_input}],
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
