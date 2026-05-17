import json
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from backend.app.schemas import Message
from backend.app.settings import get_settings


def rolling_history(messages: Sequence[Message], limit: int = 40) -> list[dict[str, str]]:
    window = messages[-limit:]
    return [
        {
            "role": "user" if item.role == "user" else "assistant",
            "content": f"{item.name}: {item.content}" if item.role != "user" else item.content,
        }
        for item in window
    ]


async def chat_completion(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    response_format: Mapping[str, Any] | None = None,
) -> str:
    settings = get_settings()
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    payload: dict[str, object] = {
        "model": model or settings.default_model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if response_format:
        payload["response_format"] = response_format

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
        response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
