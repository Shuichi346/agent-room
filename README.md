<table>
  <thead>
    <tr>
      <th style="text-align:center"><a href="README_ja.md">日本語</a></th>
      <th style="text-align:center"><a href="README.md">English</a></th>
    </tr>
  </thead>
</table>

# agent-room

agent-room is a local-first multi-agent chat room for experimenting with role-based LLM discussions. It runs a FastAPI backend and a React/Vite frontend on `127.0.0.1`, talks to LM Studio through an OpenAI-compatible API, and persists presets and conversation logs as JSON under `./data/`.

## Preview

<img src="UI-image/UI-main.png" alt="agent-room simulation view" width="480">

Simulation view with the active conversation, agent replies, attachments, and run controls.

<img src="UI-image/UI-setting.png" alt="agent-room orchestration settings view" width="480">

Orchestration view for presets, agent personas, model selection, conversation pattern, max turns, and auto agent generation.

## Features

- Multi-agent conversations with configurable agent names, personas, colors, and model IDs.
- Round Robin and Free Flow conversation patterns.
- Conversation streaming over Server-Sent Events from the FastAPI backend.
- Conversation cancellation from the UI.
- Preset save, import, export, and load workflows backed by JSON files.
- Conversation history persisted under `./data/conversations/`.
- URL attachments fetched as HTML/text only and normalized with `trafilatura`.
- Image attachments validated as PNG, JPEG, or WebP, up to 10 MB and 4096 px per side.
- Auto Agent Creation that asks the configured local model to draft agent personas for a theme.
- Agent-facing JSON API and CLI for capability discovery, preset lookup, and non-streaming runs.
- Single-process production-style serving: the backend mounts `frontend/dist/` when the UI is built.

## Tech Stack

- Backend: Python 3.13, FastAPI, Uvicorn, Pydantic Settings, httpx, Microsoft Agent Framework, Pillow, trafilatura.
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, Zustand, React Router, lucide-react.
- Tooling: `uv` for Python dependency management, npm for frontend dependencies, Ruff for Python linting.

## Requirements

- macOS 26 or later.
- Node.js 24 or later and npm.
- `uv`.
- LM Studio running locally with a chat model loaded.
- LM Studio's OpenAI-compatible server available at the configured `OPENAI_BASE_URL`, defaulting to `http://localhost:1234/v1`.

## Installation

Clone the repository, then run the launcher from the repository root:

```bash
./start.sh
```

On first run, the launcher:

1. Checks for `uv`, Node.js, and npm.
2. Creates `.env` from `.env.example` when `.env` is missing.
3. Installs Python dependencies with `uv sync`.
4. Installs frontend dependencies with `npm install` when the built UI is missing or stale.
5. Builds the frontend with `npm run build`.
6. Starts FastAPI on `127.0.0.1:${APP_PORT:-8000}`.
7. Opens the app in the default browser after `/api/health` responds.

Stop the app with `Ctrl+C` in the launcher terminal, or run:

```bash
./stop.sh
```

## Configuration

Copy `.env.example` to `.env` manually, or let `./start.sh` create it.

| Key | Default | Purpose |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible API base URL, typically LM Studio. |
| `OPENAI_API_KEY` | `lm-studio` | Bearer token sent to the configured API. |
| `DEFAULT_MODEL` | `google/gemma-4-e2b` | Default model ID used by new agents and fallback model lists. |
| `MAX_TURNS` | `10` | Backend default maximum turn count. |
| `LOG_LEVEL` | `info` | Python logging level. |
| `APP_PORT` | `8000` | Local FastAPI port. |
| `APP_HOST` | `127.0.0.1` | Local FastAPI bind host. Keep this loopback-only. |

The frontend can also read `VITE_API_BASE_URL`. When it is unset, API calls use same-origin paths such as `/api/models/`.

## Usage

1. Start LM Studio and load a chat model.
2. Run `./start.sh`.
3. Open the Orchestration view to edit agents, choose Round Robin or Free Flow, and set max turns.
4. Save a preset when you want to reuse the same agent configuration.
5. Open the Simulation view, enter a prompt, optionally attach one or more URLs or images, and send the run.
6. Use the stop button to cancel an active run.

Presets are stored in `./data/presets/`. Conversations are stored in `./data/conversations/`. Generated JSON files in those directories are intentionally ignored by Git.

## Agent API and CLI

Autonomous callers can use JSON-first endpoints instead of the UI streaming endpoint:

```bash
curl http://127.0.0.1:8000/api/agents/manifest
curl -X POST http://127.0.0.1:8000/api/agents/run \
  -H 'Content-Type: application/json' \
  -d '{"preset_id":"YOUR_PRESET_ID","prompt":"Discuss this task.","max_turns":3}'
```

The same functionality is available without starting an HTTP client:

```bash
uv run python -m backend.app.cli manifest
uv run python -m backend.app.cli presets
uv run python -m backend.app.cli run --preset-id YOUR_PRESET_ID --prompt "Discuss this task."
```

The CLI prints JSON by default. Use `--format text` on `run` or `show-conversation` for compact transcript output.

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

Run the Python unit tests:

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
  orchestration/   Agent turn selection, prompting, streaming, and cancellation.
  storage/         JSON persistence for presets and conversations.
  tools/           URL and image attachment helpers.
frontend/src/
  components/      Reusable React UI components.
  lib/             API client, types, and Zustand store.
  routes/          Simulation and Orchestration screens.
data/
  presets/         Runtime preset JSON files.
  conversations/   Runtime conversation JSON files.
```

## Troubleshooting

- If startup says the port is busy, stop the existing listener or run with another port, for example `APP_PORT=8001 ./start.sh`.
- If the UI cannot load models, confirm LM Studio is running, its local server is enabled, and `OPENAI_BASE_URL` points to the correct `/v1` endpoint.
- If a selected model cannot process images, the app still includes a text note that an image was attached.
- If URL attachment fails, confirm the URL is `http` or `https` and returns text or HTML content under the backend size limit.

## License

MIT. See [LICENSE](LICENSE).
