import unittest

from backend.app.orchestration import runner
from backend.app.schemas import AgentConfig, Conversation, Message, Preset


def make_agent(agent_id: str, name: str) -> AgentConfig:
    return AgentConfig(
        id=agent_id,
        name=name,
        persona=f"You are {name}.",
        model="test-model",
    )


class TurnPromptTests(unittest.TestCase):
    def test_turn_input_marks_current_agent_messages(self) -> None:
        architect = make_agent("architect", "Architect")
        synthesizer = make_agent("synthesizer", "Synthesizer")
        conv = Conversation(
            preset_snapshot=Preset(
                name="test",
                agents=[architect, synthesizer],
                pattern="free_flow",
            ),
            messages=[
                Message(role="user", name="You", content="Discuss deployment risk."),
                Message(
                    role="assistant",
                    agent_id=architect.id,
                    name=architect.name,
                    content="We should map the rollback path first.",
                ),
                Message(
                    role="assistant",
                    agent_id=synthesizer.id,
                    name=synthesizer.name,
                    content="The key next step is a release checklist.",
                ),
            ],
        )

        turn_input = runner._turn_input(conv, architect)

        self.assertIn("User: Discuss deployment risk.", turn_input)
        self.assertIn("Architect (you): We should map the rollback path first.", turn_input)
        self.assertIn(
            "Synthesizer (other agent): The key next step is a release checklist.",
            turn_input,
        )
        self.assertIn("Do not reply to statements marked (you)", turn_input)


class FreeFlowSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_flow_does_not_reselect_previous_speaker(self) -> None:
        architect = make_agent("architect", "Architect")
        synthesizer = make_agent("synthesizer", "Synthesizer")
        validator = make_agent("validator", "Validator")
        conv = Conversation(
            preset_snapshot=Preset(
                name="test",
                agents=[architect, synthesizer, validator],
                pattern="free_flow",
            ),
            messages=[
                Message(role="user", name="You", content="Discuss deployment risk."),
                Message(
                    role="assistant",
                    agent_id=architect.id,
                    name=architect.name,
                    content="We should map the rollback path first.",
                ),
            ],
        )

        original_chat_completion = runner.chat_completion

        async def choose_previous_speaker(**_: object) -> str:
            return "Architect"

        runner.chat_completion = choose_previous_speaker
        try:
            selected = await runner._choose_free_flow_agent(conv)
        finally:
            runner.chat_completion = original_chat_completion

        self.assertNotEqual(architect.id, selected)
        self.assertIn(selected, {synthesizer.id, validator.id})


if __name__ == "__main__":
    unittest.main()
