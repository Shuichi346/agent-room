# Work Log

- 2026-05-12 - Project initialized.
- 2026-05-12 - Agent Framework 1.3.0 exposes `agent_framework.Agent` and `agent_framework.openai.OpenAIChatClient`; the older top-level `ChatAgent`, `SequentialBuilder`, and `MagenticBuilder` names from the plan are not top-level exports. Per-agent turns now run through Agent Framework agents, with direct OpenAI-compatible HTTP retained as a fallback path.
