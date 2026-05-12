# agent-room

agent-room is a local-first multi-agent chat application. It serves a React UI from a FastAPI backend and talks to LM Studio through its OpenAI-compatible API.

## Quick Start

```bash
./start.sh
```

The launcher installs Python dependencies with `uv`, installs frontend dependencies with `npm`, builds the UI, starts the backend on `127.0.0.1:8000`, and opens the app.

## Prerequisites

- macOS 26+
- Node.js 24+
- `uv`
- LM Studio running at `http://localhost:1234/v1` with a chat model loaded

## Configuration

Copy `.env.example` to `.env` or let `./start.sh` create it.

| Key | Default |
| --- | --- |
| `OPENAI_BASE_URL` | `http://localhost:1234/v1` |
| `OPENAI_API_KEY` | `lm-studio` |
| `DEFAULT_MODEL` | `google/gemma-4-e2b` |
| `MAX_TURNS` | `10` |
| `APP_HOST` | `127.0.0.1` |
| `APP_PORT` | `8000` |

## Architecture

```text
Browser -> React/Vite UI -> FastAPI -> OpenAI-compatible API -> LM Studio
```

Presets and conversations are stored as JSON under `./data/`.

## Features

- Simulation view with multi-agent conversation streaming
- Orchestration view for agent CRUD and conversation pattern selection
- Round Robin and Free Flow conversation modes
- URL and image attachment normalization
- Preset import/export and conversation persistence
- Auto Agent Creation using the configured local model

## Future Electron Migration

The app keeps three migration points explicit: `VITE_API_BASE_URL` for frontend API routing, `APP_PORT` for the backend listener, and `get_data_dir()` for storage location. An Electron shell can replace these without rewriting app logic.

## License

MIT

