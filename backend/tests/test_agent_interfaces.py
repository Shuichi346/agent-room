import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.orchestration import runner
from backend.app.schemas import AgentConfig, Message, Preset, RunRequest, utc_now
from backend.app.storage import conversation_repo


def make_agent(agent_id: str, name: str) -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name=name,
        persona=f"You are {name}.",
        model="test-model",
    )


class AgentApiTests(unittest.TestCase):
    def test_manifest_lists_agent_run_endpoint(self) -> None:
        client = TestClient(create_app())

        response = client.get("/api/agents/manifest")

        self.assertEqual(200, response.status_code)
        paths = {item["path"] for item in response.json()["endpoints"]}
        self.assertIn("/api/agents/run", paths)


class AgentRunCompletionTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_to_completion_returns_new_messages(self) -> None:
        critic = make_agent("critic", "Critic")
        preset = Preset(name="agent-test", agents=[critic], max_turns=2)

        async def fake_agent_turn(conv, agent_id: str, queue) -> None:
            agent = next(agent for agent in conv.preset_snapshot.agents if agent.id == agent_id)
            assistant_turn = len([item for item in conv.messages if item.role == "assistant"]) + 1
            msg = Message(
                agent_id=agent.id,
                role="assistant",
                name=agent.name,
                content=f"turn {assistant_turn}",
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
                    "content": msg.content,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            conversations_dir = Path(temp_dir)
            with (
                patch.object(conversation_repo, "get_conversations_dir", lambda: conversations_dir),
                patch.object(runner, "_run_agent_turn", fake_agent_turn),
            ):
                response = await runner.run_conversation_to_completion(
                    RunRequest(preset=preset, prompt="Review this plan.")
                )

        self.assertEqual("completed", response.status)
        self.assertEqual("max_turns", response.reason)
        self.assertEqual(["You", "Critic", "Critic"], [msg.name for msg in response.new_messages])
        self.assertEqual(3, len(response.conversation.messages))


if __name__ == "__main__":
    unittest.main()
