# Changelog

## [0.1.0] - 2026-05-12

- Added local FastAPI backend with health, model, preset, conversation, attachment, chat, and auto-agent APIs.
- Added React UI for simulation and orchestration workflows.
- Added JSON persistence under `./data/`.
- Added one-shot launcher scripts.

## [Unreleased]

- Initial scaffolding.
- Changed conversation response fallback calls to inherit generation defaults from the configured OpenAI-compatible server instead of forcing `temperature: 0.7`.
- Added agent-facing manifest and non-streaming run APIs, plus a JSON-first CLI for presets, conversations, and runs.
