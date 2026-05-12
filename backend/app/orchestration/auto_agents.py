import logging

import httpx

from backend.app.orchestration.llm import chat_completion, parse_json_object
from backend.app.schemas import AgentConfig
from backend.app.settings import get_settings

COLORS = ["#08D9C7", "#0FA89A", "#00C2FF", "#B48CFF", "#FF5A7A"]
logger = logging.getLogger(__name__)

AUTO_AGENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "auto_agent_response",
        "schema": {
            "type": "object",
            "properties": {
                "agents": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "persona": {"type": "string"},
                            "model": {"type": "string"},
                            "color": {"type": "string"},
                        },
                        "required": ["name", "persona", "model", "color"],
                    },
                }
            },
            "required": ["agents"],
        },
    },
}


def _fallback_agents(theme: str, count: int | None, model: str) -> list[AgentConfig]:
    target_count = count or 3
    templates = [
        (
            "Strategist",
            "You are the Strategist. Frame the discussion, identify constraints, "
            f"and keep the agents focused on {theme}.",
        ),
        (
            "Researcher",
            "You are the Researcher. Surface evidence, examples, unknowns, and "
            f"context that matter for {theme}.",
        ),
        (
            "Validator",
            "You are the Validator. Challenge assumptions, point out risks, and "
            f"test whether conclusions about {theme} are defensible.",
        ),
        (
            "Synthesizer",
            "You are the Synthesizer. Convert the discussion into concise options, "
            "trade-offs, and next steps.",
        ),
        (
            "Operator",
            "You are the Operator. Focus on practical execution, sequencing, and "
            "what should happen next.",
        ),
    ]
    return [
        AgentConfig(name=name, persona=persona, model=model, color=COLORS[index % len(COLORS)])
        for index, (name, persona) in enumerate(templates[:target_count])
    ]


def _normalize_persona(persona: str, name: str, theme: str) -> str:
    value = " ".join(persona.split())[:800]
    if not value:
        value = f"You are {name}. Add one useful perspective to the discussion about {theme}."
    if not value.lower().startswith("you are"):
        value = f"You are {name}. {value}"
    return value


def _normalize_agents(data: dict, theme: str, count: int | None, model: str) -> list[AgentConfig]:
    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list):
        raw_agents = []
    expected = count or min(max(len(raw_agents), 2), 5)
    agents: list[AgentConfig] = []
    used_names: set[str] = set()
    for index, item in enumerate(raw_agents[:5]):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or f"Agent {index + 1}").strip()[:40]
        if not name or name.lower() in used_names:
            name = f"Agent {len(agents) + 1}"
        used_names.add(name.lower())
        agents.append(
            AgentConfig(
                name=name,
                persona=_normalize_persona(str(item.get("persona") or ""), name, theme),
                model=model,
                color=COLORS[len(agents) % len(COLORS)],
            )
        )
    if len(agents) < expected:
        for fallback in _fallback_agents(theme, expected, model):
            if len(agents) >= expected:
                break
            if fallback.name.lower() not in used_names:
                agents.append(fallback)
                used_names.add(fallback.name.lower())
    return agents[:expected]


async def generate_agents(theme: str, count: int | None, model: str) -> list[AgentConfig]:
    settings = get_settings()
    target_model = model or settings.default_model
    count_rule = "choose 2 to 5 agents" if count is None else f"produce exactly {count} agents"
    system = (
        "You generate agent presets for a local multi-agent discussion app. "
        "Return strict JSON only with this shape: "
        '{"agents":[{"name":"...","persona":"You are...","model":"...", "color":"#RRGGBB"}]}. '
        f"Names must be distinct and 1-40 chars. Personas must be second-person. {count_rule}."
    )
    user = {
        "role": "user",
        "content": f"Theme: {theme}\nDefault model: {target_model}\nProduce JSON now.",
    }
    last_error: Exception | None = None
    response_formats = [AUTO_AGENT_RESPONSE_FORMAT, None]
    for response_format in response_formats:
        try:
            text = await chat_completion(
                model=target_model,
                system_prompt=system,
                messages=[user],
                temperature=0.4,
                response_format=response_format,
            )
            data = parse_json_object(text)
            return _normalize_agents(data, theme, count, target_model)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in {400, 422}:
                break
            logger.info("Auto-agent structured output rejected; retrying without it: %s", exc)
        except Exception as exc:
            last_error = exc
            user["content"] += "\nYour previous response was invalid. Output only JSON."
    logger.warning("Auto-agent generation fell back to local templates: %s", last_error)
    return _fallback_agents(theme, count, target_model)
