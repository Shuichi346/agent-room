from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from backend.app.schemas import AgentConfig, Preset
from backend.app.settings import get_settings


def build_chat_client(model: str | None = None) -> OpenAIChatClient:
    settings = get_settings()
    return OpenAIChatClient(
        model=model or settings.default_model,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
    )


def build_agent(config: AgentConfig, extra_instructions: str | None = None) -> Agent:
    instructions = config.persona
    if extra_instructions:
        instructions = f"{instructions}\n\n{extra_instructions}"
    return Agent(
        build_chat_client(config.model),
        instructions=instructions,
        id=config.id,
        name=config.name,
        description=config.persona[:240],
    )


def build_chat_agents(preset: Preset) -> list[Agent]:
    return [build_agent(config) for config in preset.agents]

