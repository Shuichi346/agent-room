import unittest
from unittest.mock import patch

import httpx

from backend.app.orchestration.llm import chat_completion


class FakeAsyncClient:
    payloads: list[dict] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, *args: object, **kwargs: object) -> httpx.Response:
        self.payloads.append(kwargs["json"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=httpx.Request("POST", "http://test.local/chat/completions"),
        )


class ChatCompletionPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        FakeAsyncClient.payloads = []

    async def test_omits_temperature_by_default(self) -> None:
        with patch("backend.app.orchestration.llm.httpx.AsyncClient", FakeAsyncClient):
            await chat_completion(
                model="test-model",
                system_prompt="system",
                messages=[{"role": "user", "content": "hello"}],
            )

        self.assertNotIn("temperature", FakeAsyncClient.payloads[0])

    async def test_sends_explicit_temperature(self) -> None:
        with patch("backend.app.orchestration.llm.httpx.AsyncClient", FakeAsyncClient):
            await chat_completion(
                model="test-model",
                system_prompt="system",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0.2,
            )

        self.assertEqual(0.2, FakeAsyncClient.payloads[0]["temperature"])


if __name__ == "__main__":
    unittest.main()
