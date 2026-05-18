<table>
  <thead>
    <tr>
      <th style="text-align:center"><a href="README_ja.md">日本語</a></th>
      <th style="text-align:center"><a href="README.md">English</a></th>
    </tr>
  </thead>
</table>

# agent-room

agent-room is a local-first multi-agent discussion workspace for LM Studio and other
OpenAI-compatible local chat servers. It provides a React UI for configuring role-based agents,
running multi-turn conversations, attaching reference material, and saving reusable presets. It
also exposes JSON-first API and CLI workflows so other AI agents can discover capabilities, launch
runs, and read persisted transcripts without driving the browser UI.

## Table of Contents

- [Preview](#preview)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Using the App](#using-the-app)
- [Agent API and CLI](#agent-api-and-cli)
- [Development](#development)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Preview

<img src="UI-image/UI-main.png" alt="agent-room simulation view" width="480">

Simulation view with the active transcript, agent replies, attachments, and run controls.

<img src="UI-image/UI-setting.png" alt="agent-room orchestration settings view" width="480">

Orchestration view for presets, agent personas, model IDs, conversation pattern, maximum turns, and
automatic agent drafting.

## Features

- Configure up to eight agents with names, personas, colors, and model IDs.
- Run conversations with Round Robin or Free Flow speaker selection.
- Stream UI runs over Server-Sent Events and cancel active conversations.
- Persist presets under `./data/presets/` and conversations under `./data/conversations/`.
- Save, import, export, and reload preset JSON files.
- Attach URL references fetched as HTML/text only and normalized with `trafilatura`.
- Attach PNG, JPEG, or WebP images up to 10 MB and 4096 px per side.
- Ask a configured local model to draft agent personas from a theme.
- Use agent-oriented JSON APIs and a CLI for manifest discovery, preset lookup, non-streaming runs,
  and transcript reads.
- Serve the built React app from FastAPI in a single local process.

## Requirements

- macOS 26 or later.
- Python 3.13 or later.
- Node.js 24 or later and npm.
- `uv`.
- LM Studio, or another OpenAI-compatible chat server, with a model loaded.
- Local chat API reachable at `OPENAI_BASE_URL`, defaulting to `http://localhost:1234/v1`.

## Quick Start

From the repository root:

```bash
./start.sh
```

The launcher creates `.env` from `.env.example` when needed, installs Python dependencies with
`uv sync`, installs frontend dependencies when the built UI is missing or stale, builds the React
frontend, starts FastAPI on `127.0.0.1:${APP_PORT:-8000}`, and opens the app after `/api/health`
responds.

Stop the app with `Ctrl+C` in the launcher terminal, or run:

```bash
./stop.sh
```

## Configuration

Copy `.env.example` to `.env` manually, or let `./start.sh` create it.

| Key | Default | Purpose |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible API base URL, usually LM Studio. |
| `OPENAI_API_KEY` | `lm-studio` | Bearer token sent to the configured API. |
| `DEFAULT_MODEL` | `google/gemma-4-e2b` | Default model ID used by new agents and fallback model lists. |
| `MAX_TURNS` | `10` | Backend default maximum turn count. |
| `LOG_LEVEL` | `info` | Python logging level. |
| `APP_PORT` | `8000` | Local FastAPI port. |
| `APP_HOST` | `127.0.0.1` | Local FastAPI bind host. Keep this loopback-only. |

The frontend can also read `VITE_API_BASE_URL`. When unset, API calls use same-origin paths such as
`/api/models/`.

## Using the App

1. Start LM Studio and load a chat model.
2. Run `./start.sh`.
3. Open the Orchestration view.
4. Edit agents, select Round Robin or Free Flow, and set the maximum turn count.
5. Save a preset if you want to reuse the configuration.
6. Open the Simulation view.
7. Enter a prompt, optionally attach URLs or images, and start the run.
8. Stop an active run from the UI when needed.

Generated preset and conversation JSON files are intentionally ignored by Git.

## Agent API and CLI

agent-room includes a non-streaming interface for autonomous callers that need complete JSON results
instead of browser-oriented SSE streams.

### HTTP

Inspect machine-readable capabilities:

```bash
curl http://127.0.0.1:8000/api/agents/manifest
```

Run a saved preset to completion:

```bash
curl -X POST http://127.0.0.1:8000/api/agents/run \
  -H 'Content-Type: application/json' \
  -d '{"preset_id":"YOUR_PRESET_ID","prompt":"Discuss this task.","max_turns":3}'
```

The run endpoint also accepts an inline `preset` object instead of `preset_id`, optional
`attachments`, and an optional `conversation_id` to continue an existing transcript.

Useful API routes:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agents/manifest` | Return agent-facing capabilities and storage locations. |
| `POST` | `/api/agents/run` | Run a preset to completion and return JSON. |
| `GET` | `/api/presets/` | List saved presets. |
| `GET` | `/api/conversations/` | List saved conversations. |
| `GET` | `/api/conversations/{conversation_id}` | Read a full transcript. |
| `POST` | `/api/chat/run` | Stream a UI-oriented conversation over Server-Sent Events. |

### CLI

The CLI uses the same local storage and orchestration code as the API:

```bash
uv run python -m backend.app.cli manifest
uv run python -m backend.app.cli presets
uv run python -m backend.app.cli conversations
uv run python -m backend.app.cli show-conversation CONVERSATION_ID --format text
uv run python -m backend.app.cli run --preset-id YOUR_PRESET_ID --prompt "Discuss this task."
```

You can also run from a preset file or pipe prompt text on stdin:

```bash
printf 'Compare these implementation options.' | \
  uv run python -m backend.app.cli run --preset-file ./data/presets/example.json
```

CLI output is JSON by default. `run` and `show-conversation` support `--format text` for compact
transcript output.

## Development

Install dependencies:

```bash
uv sync
cd frontend
npm install
```

Build the frontend:

```bash
cd frontend
npm run build
```

Run the backend from the repository root:

```bash
uv run python -m backend.app.main
```

For frontend-only development, Vite proxies `/api` to the backend on `127.0.0.1:8000`:

```bash
cd frontend
npm run dev
```

## Testing

Run backend unit tests:

```bash
uv run python -m unittest discover -s backend/tests
```

Run Ruff:

```bash
uv run ruff check .
```

Verify the frontend build:

```bash
cd frontend
npm run build
```

## Project Structure

```text
backend/app/
  api/             FastAPI route modules.
  orchestration/   Agent prompting, turn selection, streaming, and JSON run completion.
  storage/         JSON persistence for presets and conversations.
  tools/           URL and image attachment helpers.
frontend/src/
  components/      Reusable React UI components.
  lib/             API client, types, export helpers, and Zustand store.
  routes/          Simulation and Orchestration screens.
data/
  presets/         Runtime preset JSON files.
  conversations/   Runtime conversation JSON files.
```

## Troubleshooting

- If startup says the port is busy, stop the existing listener or run with another port, for example
  `APP_PORT=8001 ./start.sh`.
- If the UI cannot load models, confirm the local chat server is running, a model is loaded, and
  `OPENAI_BASE_URL` points to the correct `/v1` endpoint.
- If a selected model cannot process images, agent-room still includes a text note that an image was
  attached.
- If URL attachment fails, confirm the URL is `http` or `https` and returns text or HTML content
  within the backend size limit.

## License

MIT. See [LICENSE](LICENSE).
