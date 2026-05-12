# Work Log

- 2026-05-12 - Project initialized.
- 2026-05-12 - Agent Framework 1.3.0 exposes `agent_framework.Agent` and `agent_framework.openai.OpenAIChatClient`; the older top-level `ChatAgent`, `SequentialBuilder`, and `MagenticBuilder` names from the plan are not top-level exports. Per-agent turns now run through Agent Framework agents, with direct OpenAI-compatible HTTP retained as a fallback path.
- 2026-05-12 - Free-flow orchestration now excludes the previous assistant speaker when another agent is available and renders per-turn transcripts from the current agent's point of view, marking prior self messages as `(you)` to prevent agents from replying to their own comments as if they were from another participant.
