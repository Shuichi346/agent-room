from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentConfig(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1, max_length=40)
    persona: str = Field(min_length=1, max_length=4000)
    model: str = Field(min_length=1, max_length=200)
    color: str | None = None


ConversationPattern = Literal["round_robin", "free_flow"]


class Preset(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1, max_length=60)
    agents: list[AgentConfig] = Field(min_length=1, max_length=8)
    pattern: ConversationPattern = "round_robin"
    max_turns: int = Field(default=10, ge=1, le=50)
    auto_agent_model: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Attachment(StrictModel):
    kind: Literal["image", "url"]
    payload: str
    source: str | None = None


class Message(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    agent_id: str | None = None
    role: Literal["user", "assistant", "system"]
    name: str
    content: str
    attachments: list[Attachment] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Conversation(StrictModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str = ""
    preset_snapshot: Preset
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConversationSummary(StrictModel):
    id: str
    title: str
    updated_at: datetime
    message_count: int


class RunRequest(StrictModel):
    preset: Preset
    prompt: str = Field(min_length=1)
    attachments: list[Attachment] = Field(default_factory=list)
    conversation_id: str | None = None


class AgentRunRequest(StrictModel):
    preset: Preset | None = None
    preset_id: str | None = None
    prompt: str = Field(min_length=1)
    attachments: list[Attachment] = Field(default_factory=list)
    conversation_id: str | None = None
    max_turns: int | None = Field(default=None, ge=1, le=50)

    @model_validator(mode="after")
    def require_one_preset_source(self) -> "AgentRunRequest":
        if bool(self.preset) == bool(self.preset_id):
            raise ValueError("provide exactly one of preset or preset_id")
        return self


class AgentRunResponse(StrictModel):
    conversation_id: str
    conversation: Conversation
    new_messages: list[Message]
    status: Literal["completed", "cancelled", "error"]
    reason: str | None = None
    error: str | None = None
    event_count: int


class AgentCapability(StrictModel):
    method: str
    path: str
    description: str


class AgentManifest(StrictModel):
    name: str
    version: str
    description: str
    endpoints: list[AgentCapability]
    storage: dict[str, str]


class AutoAgentRequest(StrictModel):
    theme: str = Field(min_length=1)
    count: int | None = Field(default=None, ge=1, le=5)
    model: str


class AutoAgentResponse(StrictModel):
    agents: list[AgentConfig] = Field(min_length=1, max_length=5)
