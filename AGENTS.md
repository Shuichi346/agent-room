# agent-room Agent Notes

## Coding Conventions

- Use UTF-8.
- Comments must be English and explain current behavior.
- Do not add log-style comments about edits.
- Python files use `snake_case.py`; React components use `PascalCase.tsx`.
- Never bind the backend to `0.0.0.0`; use `127.0.0.1`.

## Boundaries

- Read port, base URL, model, and max turns from `.env` or settings.
- Use `./data/` for presets and conversations.
- Do not commit `.env`, API keys, generated presets, or generated conversations.
- Do not execute arbitrary user-supplied code.
- Only fetch HTML/text for URL attachments.

## Re-entry Notes

Check `NOTES.md` before changing orchestration, storage, or launcher behavior.

