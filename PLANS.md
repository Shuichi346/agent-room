# Implementation Plan: agent-room

**Overview:**
Build a local-first multi-agent chat web application named `agent-room` where multiple LLM-powered agents converse with each other about a user-provided topic, image, or URL. The user runs a single shell script (`./start.sh`) which boots a Python FastAPI backend (Microsoft Agent Framework + LM Studio via OpenAI-compatible API) and automatically opens the React UI in the default browser. After this change, a user with no terminal experience can double-click `start.sh`, see a messenger-style stream of agents (Architect, Synthesizer, etc.) discussing their prompt, configure / save / load agent presets as JSON, and switch between "Free Flow" (LLM picks next speaker) and "Round Robin" (sequential) conversation modes.

**Stated Assumptions:**
1. The user runs macOS 26.x (Tahoe) on Apple Silicon (Mac mini M4) and has internet access for the first run (to download Python deps, npm deps, and uv).
2. LM Studio is installed separately by the user, started by them, and exposes its OpenAI-compatible endpoint at `http://localhost:1234/v1` (the LM Studio default). The plan does not automate LM Studio launch.
3. The user already has Node.js v26.1.0 installed (confirmed by the user) and Homebrew available (used as a fallback to install `uv`).
4. There is no authentication; the app binds only to `127.0.0.1` and is single-user.
5. "Storage in the same directory as the app" means a `./data/` folder relative to the project root (the user explicitly chose this over `~/Library/Application Support/`). This folder is git-ignored.
6. Vision support is best-effort: if the active model is not multimodal, the backend falls back to passing a text description note (`[image attached: filename.png — model is non-vision, content not analyzed]`) so the conversation does not crash.
7. The "Auto Agent Creation" feature uses the same `DEFAULT_MODEL` unless the user picks a separate model for it in settings.
8. License is MIT, single root `LICENSE` file, no third-party license aggregation required at this stage.
9. The plan is executed by a single general-purpose AI coding agent; role labels are intent markers.
10. Maximum conversation history kept in memory per session is bounded by `MAX_TURNS × number_of_agents`; older messages are persisted to disk but not resent to the LLM beyond a rolling window (last 40 messages) to stay within typical local-model context windows.

**Requirements:**
1. Running `./start.sh` from a fresh clone on macOS 26 results in: (a) the Python venv is created if missing, (b) deps installed, (c) the frontend built if not built, (d) FastAPI binds to `http://127.0.0.1:8000`, (e) the default browser opens to `http://127.0.0.1:8000` showing the agent-room UI, and (f) `Ctrl+C` in the terminal cleanly stops the server.
2. The UI provides two main routes: `/simulation` (the chat stream with input box, attach-image, attach-URL, Round-Robin/Free-Flow indicator, stop button) and `/orchestration` (agent CRUD, conversation pattern picker, Export/Import JSON, Save Configuration to JSON).
3. From the orchestration view, the user can add/remove agents, set each agent's name, persona (system prompt), and model engine (a dropdown populated from `GET /v1/models` on the configured `OPENAI_BASE_URL`). Pressing **Save Configuration to JSON** writes `./data/presets/<name>.json` and pressing **Import JSON** loads one back.
4. From the simulation view, the user can type a prompt, optionally attach one image (PNG/JPEG/WebP, ≤ 10 MB) and/or one URL, then press send. Agent messages stream into the chat in order; each message shows the agent's name, a timestamp, and the text.
5. Two conversation patterns work end-to-end:
   - **Round Robin**: Agents speak in the exact order shown in the orchestration list; after the last agent speaks, the cycle restarts. Stops at `MAX_TURNS` (counted as one full visit to one agent) or when the user presses stop.
   - **Free Flow**: A Magentic-style orchestrator decides which agent speaks next based on the conversation context. Stops at `MAX_TURNS` or stop button.
6. Pressing the **Stop** button in the UI cancels the active streaming run within ≤ 2 seconds and leaves the partial conversation visible and saved.
7. **Auto Agent Creation**: From the orchestration view, the user enters a desired discussion theme, picks either a fixed number (1–5) or "Auto (LLM decides, ≤ 5)", and clicks Generate. The backend returns a draft list of agents (name + persona + suggested model). The user can edit any field and then click "Adopt" to replace the Active Agents list, or "Cancel" to discard.
8. All settings, presets, and conversation logs are persisted as JSON under `./data/` and survive restart. The sidebar shows past conversations and clicking one re-opens its full transcript.
9. Calling `curl http://127.0.0.1:8000/api/health` returns `{"status":"ok","version":"0.1.0"}` with HTTP 200.
10. The frontend's API base URL is read from `import.meta.env.VITE_API_BASE_URL` (defaulting to `""` for same-origin) so a future Electron migration only needs to change the env var. The Python data directory is resolved via a single function `get_data_dir() -> Path` in `backend/app/paths.py` for the same reason. Backend port is read from `APP_PORT` env var (default `8000`).
11. The project contains `.gitignore`, `.gitkeep` in empty dirs, `NOTES.md`, `AGENTS.md`, `CHANGELOG.md`, `README.md`, and `LICENSE` (MIT).

**Tech Stack and Conventions:**

Backend:
- Python **3.13** (target). Fallback to **3.12** only if `agent-framework` wheels are unavailable for 3.13 at install time (the agent must check `uv python list` and pick 3.13 first, then 3.12).
- Package/runtime manager: **uv** (Astral). Project layout uses `pyproject.toml` (PEP 621) + `uv.lock`.
- Web framework: **FastAPI** (latest stable, ≥ 0.115). ASGI server: **uvicorn[standard]** (latest).
- LLM orchestration: **Microsoft Agent Framework Python** (`agent-framework`, latest stable 1.0.x). Use `agent_framework.openai.OpenAIChatClient` to talk to LM Studio (it accepts a `base_url` override). Use `agent_framework.SequentialBuilder` for Round Robin, and `agent_framework.MagenticBuilder` for Free Flow (Magentic is MAF's built-in manager-led group-chat orchestration; the manager picks the next speaker).
- HTML extraction: **trafilatura** (latest 2.x).
- Image handling: **Pillow** (latest) just for validation + metadata; the image bytes are passed to the model as a base64 data URL via the OpenAI vision content-part schema.
- Env loading: **python-dotenv** (latest) and Pydantic Settings (`pydantic-settings`).
- Streaming to UI: FastAPI `StreamingResponse` over SSE (`text/event-stream`). Each event line: `data: {"type": "...", ...}\n\n`.

Frontend:
- **React 18** + **Vite 5/6 latest** + **TypeScript 5.x latest** + **Tailwind CSS v4** (Tailwind v4 uses `@tailwindcss/vite` plugin, not PostCSS).
- State: built-in React hooks + a tiny store via **Zustand** (latest).
- Routing: **react-router-dom** v6 (latest).
- Icons: **lucide-react** (latest).
- HTTP: native `fetch`. SSE: native `EventSource` for GET streams; for the POST-then-stream chat run, use `fetch` with a `ReadableStream` body parser (a small helper `parseSSE(response)`).
- Color palette: light theme with mint/teal accents (`#5EE0C6` primary, `#0FA89A` accent, off-white `#F7F9FA` backgrounds, dark text `#1B2A33`). This matches the user-supplied reference screenshots (named "AetherControl" in the mocks — we will rename all UI strings to "agent-room").

Conventions:
- File encoding: UTF-8.
- All code comments in English.
- No "I added this here" / "changed below" LLM-style comments.
- Python: `ruff` formatter+linter config in `pyproject.toml` (line length 100, target-version py313).
- TS: `eslint` + `prettier` defaults from `npm create vite@latest -- --template react-ts`.
- File naming: Python `snake_case.py`, TypeScript components `PascalCase.tsx`, hooks `useCamelCase.ts`.

**Boundaries:**

```
✅ Always:
  - Read every config value (port, base URL, model name, max turns) from .env or a settings file, never hardcode.
  - Use trafilatura.extract() for URL → text; reject URLs that return non-text/html or > 2 MB.
  - Validate uploaded images: PNG/JPEG/WebP only, ≤ 10 MB, dimension ≤ 4096 px.
  - Bind FastAPI to 127.0.0.1 only (never 0.0.0.0).
  - Persist every saved conversation as ./data/conversations/<uuid>.json on every assistant turn (write-through).

⚠️ Ask First:
  - Adding any Python package not listed in the Tech Stack section.
  - Changing the data directory layout (./data/ subfolders) after Phase 2 is complete.
  - Switching the orchestration library away from agent-framework.

🚫 Never:
  - Commit secrets, API keys, or .env files (only .env.example is committed).
  - Bind the server to a non-loopback interface.
  - Execute arbitrary user-supplied code or shell commands (the "URL" feature only fetches HTML; no code execution).
  - Send conversation history beyond the rolling window (last 40 messages) to the LLM.
```

**Architecture Changes:**

Target directory tree (after Phase 0):

```
agent-room/
├── .gitignore
├── .env.example
├── LICENSE                       # MIT
├── README.md
├── AGENTS.md
├── NOTES.md
├── CHANGELOG.md
├── start.sh                      # One-shot launcher (chmod +x)
├── stop.sh                       # Optional convenience: kill listener on $APP_PORT
├── pyproject.toml                # uv-managed
├── uv.lock
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app factory + static mount
│   │   ├── settings.py           # pydantic-settings, reads .env
│   │   ├── paths.py              # get_data_dir(), get_project_root()
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── models.py         # GET /api/models (proxies to LM Studio /v1/models)
│   │   │   ├── presets.py        # CRUD /api/presets
│   │   │   ├── conversations.py  # list/get past conversations
│   │   │   ├── chat.py           # POST /api/chat/run  (SSE stream)
│   │   │   ├── auto_agents.py    # POST /api/auto-agents
│   │   │   └── attachments.py    # POST /api/attachments/image, /api/attachments/url
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   ├── factory.py        # build ChatAgent list from preset
│   │   │   ├── round_robin.py    # SequentialBuilder wrapper
│   │   │   ├── free_flow.py      # MagenticBuilder wrapper
│   │   │   └── runner.py         # cancellable async runner -> yields SSE events
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── url_fetch.py      # httpx + trafilatura
│   │   │   └── image.py          # Pillow validation, base64 data URL
│   │   └── schemas.py            # Pydantic models for Agent, Preset, Conversation, Message
│   └── tests/                    # (left empty per user request, but folder kept w/ .gitkeep)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts        # only if v4 needs it; otherwise inline @theme in CSS
│   ├── postcss.config.cjs        # absent under Tailwind v4 + Vite plugin
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # router
│       ├── index.css             # @import "tailwindcss";
│       ├── lib/
│       │   ├── api.ts            # fetch helpers, parseSSE()
│       │   ├── store.ts          # Zustand store: agents, pattern, conversation, runStatus
│       │   └── types.ts          # mirrors backend schemas
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   ├── ChatStream.tsx
│       │   ├── MessageBubble.tsx
│       │   ├── PromptInput.tsx
│       │   ├── AgentCard.tsx
│       │   ├── PatternToggle.tsx
│       │   ├── PresetActions.tsx
│       │   └── AutoAgentDialog.tsx
│       └── routes/
│           ├── Simulation.tsx
│           └── Orchestration.tsx
└── data/                         # git-ignored; created at runtime
    ├── .gitkeep
    ├── presets/
    │   └── .gitkeep
    └── conversations/
        └── .gitkeep
```

After build, `frontend/dist/` is produced; `backend/app/main.py` mounts it at `/` so a single uvicorn process serves both API (under `/api`) and the static UI.

**Agent Summary:**

| Agent              | Step Count | Phases Involved        |
|--------------------|------------|------------------------|
| coding-agent       | 17         | 1, 2, 3, 4, 5, 6, 7   |
| devops-agent       | 4          | 0, 1, 7               |
| documentation-agent| 2          | 0, 7                  |
| review-agent       | 7          | 0G, 1G, 2G, 3G, 4G, 5G, 6G, 7G (phase gates) |
| refactoring-agent  | 1          | 7                     |

**Implementation Steps:**

---

### Phase 0: Repository Bootstrap

**Purpose:** Establish the project skeleton, license, docs, and `.gitignore` so subsequent work happens in a clean, MIT-licensed repo with the directory structure already in place.

**Step 0.1: Initialize Git Repo and Top-Level Files**
- Agent: `devops-agent`
- Location: repository root
- Action: Create the directory tree shown in "Architecture Changes" with empty files plus `.gitkeep` files in `data/`, `data/presets/`, `data/conversations/`, `backend/tests/`. Create `.gitignore` containing at minimum: `.DS_Store`, `Thumbs.db`, `__pycache__/`, `*.pyc`, `.venv/`, `.python-version`, `node_modules/`, `frontend/dist/`, `data/presets/*.json`, `data/conversations/*.json`, `.env`, `*.log`, `.vscode/`, `.idea/`, `.uv-cache/`. Run `git init` and stage initial commit.
- Details: `.gitignore` must keep `data/.gitkeep`, `data/presets/.gitkeep`, `data/conversations/.gitkeep` (i.e., negative-pattern `!data/**/.gitkeep`).
- Dependencies: None
- Verification: Run `ls -la` — confirm `.gitignore`, `LICENSE`, `README.md`, `AGENTS.md`, `NOTES.md`, `CHANGELOG.md` exist at root. Run `git status` — confirm `data/.gitkeep` is tracked but no other files under `data/` are.
- Complexity: Low
- Risk: Low

**Step 0.2: Add MIT LICENSE**
- Agent: `documentation-agent`
- Location: `./LICENSE`
- Action: Create the standard MIT license text with copyright year `2026` and copyright holder placeholder `agent-room contributors`.
- Dependencies: 0.1
- Verification: First non-blank line of `LICENSE` reads `MIT License`. `grep -c "MIT License" LICENSE` returns ≥ 1.
- Complexity: Low
- Risk: Low

**Step 0.3: Seed Markdown Docs**
- Agent: `documentation-agent`
- Location: `README.md`, `AGENTS.md`, `NOTES.md`, `CHANGELOG.md`
- Action: Create minimal initial content:
  - `README.md`: Title "agent-room", one-paragraph description, "Quick start" section showing `./start.sh`, "Requirements" (macOS 26+, Node 24+, LM Studio running on :1234), and "License: MIT".
  - `AGENTS.md`: Coding conventions (UTF-8, English comments, no log-style comments, file-naming rules, "never bind to 0.0.0.0"). Mirror the **Boundaries** block above.
  - `NOTES.md`: A header "Work Log" with one initial entry `2026-05-12 — Project initialized.`
  - `CHANGELOG.md`: `## [Unreleased]` with a sub-bullet `- Initial scaffolding.`
- Dependencies: 0.1
- Verification: `head -1 README.md` outputs `# agent-room`. All four files are non-empty.
- Complexity: Low
- Risk: Low

**Step 0.G: Phase Gate — Scaffolding Verification**
- Agent: `review-agent`
- Action: Confirm directory structure and required files exist.
- Verification: Running `find . -maxdepth 2 -type f | sort` lists at minimum `./LICENSE`, `./README.md`, `./AGENTS.md`, `./NOTES.md`, `./CHANGELOG.md`, `./.gitignore`, `./backend/app/__init__.py` placeholder presence is not required yet (created in Phase 1), but the directories `./backend`, `./frontend`, `./data/presets`, `./data/conversations` must all exist (verified by `test -d` for each, exit code 0). Observable check: `git log --oneline` shows the initial commit.
- Dependencies: 0.1, 0.2, 0.3

---

### Phase 1: Python Backend Foundation

**Purpose:** Stand up a runnable FastAPI service that loads `.env`, exposes `/api/health`, and can be started by uvicorn under uv. After this phase, hitting `/api/health` returns 200 with version info.

**Step 1.1: Initialize uv Project and pyproject.toml**
- Agent: `devops-agent`
- Location: repository root + `pyproject.toml`
- Action: Run `uv init --python 3.13 --package` (if 3.13 wheels for `agent-framework` are unavailable, fall back to `--python 3.12` and record the reason in `NOTES.md`). Edit `pyproject.toml` to declare the project name `agent-room`, version `0.1.0`, license `MIT`, dependencies listed below. Pin to latest stable as of execution date.
- Details: Add these runtime dependencies (use `uv add` for each so `uv.lock` is updated):
  - `agent-framework` (latest stable 1.x)
  - `fastapi` (≥ 0.115)
  - `uvicorn[standard]` (latest)
  - `pydantic` (≥ 2.7)
  - `pydantic-settings` (latest)
  - `python-dotenv` (latest)
  - `httpx` (latest)
  - `trafilatura` (≥ 2.0)
  - `pillow` (latest)
  - `python-multipart` (for file uploads)
  - `anyio` (latest)
  
  Dev dependencies (`uv add --dev`): `ruff`.
  
  Add a `[tool.ruff]` section with `line-length = 100` and `[tool.ruff.lint] select = ["E","F","I","B","UP"]`.
  
  Add `[project.scripts] agent-room = "backend.app.main:cli"` if you decide to expose a CLI entrypoint (optional; safe to omit).
- Dependencies: 0.G
- Verification: `uv sync` exits 0; `uv run python -c "import agent_framework, fastapi, trafilatura; print('ok')"` prints `ok`.
- Complexity: Medium
- Risk: Medium — `agent-framework` may not yet ship wheels for Python 3.13. Per research (https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes), `agent-framework-core` is at 1.0.0rc1+ as of Feb 2026. If install fails on 3.13, retry with 3.12 immediately.
- Idempotence & Recovery: Safe to rerun `uv sync`. If a failed dep install leaves a partial lock, delete `uv.lock` and `.venv/`, then rerun `uv sync`.

**Step 1.2: Create `.env.example` and settings module**
- Agent: `coding-agent`
- Location: `./.env.example`, `backend/app/settings.py`
- Action: Create `.env.example` with:
  ```
  OPENAI_BASE_URL=http://localhost:1234/v1
  OPENAI_API_KEY=lm-studio
  DEFAULT_MODEL=lmstudio-community/qwen2.5-7b-instruct
  MAX_TURNS=10
  LOG_LEVEL=info
  APP_PORT=8000
  APP_HOST=127.0.0.1
  ```
  Create `backend/app/settings.py` defining a `Settings(BaseSettings)` class (from `pydantic_settings`) with fields matching the env keys above plus types: `openai_base_url: str`, `openai_api_key: str`, `default_model: str`, `max_turns: int = 10`, `log_level: str = "info"`, `app_port: int = 8000`, `app_host: str = "127.0.0.1"`. Configure `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)`. Expose a module-level cached accessor `def get_settings() -> Settings` using `functools.lru_cache`.
- Dependencies: 1.1
- Verification: Copy `.env.example` to `.env`. Run `uv run python -c "from backend.app.settings import get_settings; s=get_settings(); print(s.openai_base_url, s.max_turns)"` — output: `http://localhost:1234/v1 10`.
- Complexity: Low
- Risk: Low

**Step 1.3: Implement `paths.py`**
- Agent: `coding-agent`
- Location: `backend/app/paths.py`
- Action: Define `get_project_root() -> Path` returning the absolute path two parents up from `__file__` (i.e., the repo root). Define `get_data_dir() -> Path` returning `get_project_root() / "data"`, calling `.mkdir(parents=True, exist_ok=True)` and the same for `presets/` and `conversations/` subdirs on first call. Cache result with `functools.lru_cache`. (This is the single seam used to switch storage location when migrating to Electron.)
- Details: Function signatures:
  ```
  def get_project_root() -> Path
  def get_data_dir() -> Path        # ensures data/, data/presets/, data/conversations/ exist
  def get_presets_dir() -> Path
  def get_conversations_dir() -> Path
  ```
- Dependencies: 1.1
- Verification: `uv run python -c "from backend.app.paths import get_data_dir; p=get_data_dir(); print(p.exists(), p.name)"` prints `True data`.
- Complexity: Low
- Risk: Low

**Step 1.4: Define Pydantic Schemas**
- Agent: `coding-agent`
- Location: `backend/app/schemas.py`
- Action: Define the following Pydantic v2 models:
  - `AgentConfig`: `id: str` (uuid4 hex), `name: str` (1–40 chars), `persona: str` (1–4000 chars), `model: str` (1–200 chars), `color: str | None = None` (hex like `#5EE0C6` or `None`).
  - `ConversationPattern`: `Literal["round_robin", "free_flow"]`.
  - `Preset`: `id: str`, `name: str` (filename-safe, 1–60 chars), `agents: list[AgentConfig]` (1–8 items), `pattern: ConversationPattern`, `max_turns: int = 10` (1–50), `auto_agent_model: str | None = None`, `created_at: datetime`, `updated_at: datetime`.
  - `Message`: `id: str`, `agent_id: str | None` (None if user), `role: Literal["user","assistant","system"]`, `name: str`, `content: str`, `attachments: list[Attachment] = []`, `created_at: datetime`.
  - `Attachment`: `kind: Literal["image","url"]`, `payload: str` (data URL for image, extracted text for URL), `source: str | None = None` (original URL or filename).
  - `Conversation`: `id: str`, `title: str`, `preset_snapshot: Preset`, `messages: list[Message]`, `created_at: datetime`, `updated_at: datetime`.
  - `RunRequest`: `preset: Preset`, `prompt: str` (≥1 char), `attachments: list[Attachment] = []`, `conversation_id: str | None` (resume an existing conv if provided).
  - `AutoAgentRequest`: `theme: str` (≥1 char), `count: int | None = None` (None → auto, 1–5 → fixed), `model: str` (the LLM that does the generation).
  - `AutoAgentResponse`: `agents: list[AgentConfig]`.
- Details: Use `model_config = ConfigDict(extra="forbid")` on every model. All datetimes are timezone-aware UTC.
- Dependencies: 1.1
- Verification: `uv run python -c "from backend.app.schemas import Preset; print(Preset.model_json_schema()['properties'].keys())"` lists all defined fields.
- Complexity: Medium
- Risk: Low

**Step 1.5: Implement Health and App Factory**
- Agent: `coding-agent`
- Location: `backend/app/main.py`, `backend/app/api/health.py`
- Action: In `health.py`, create `router = APIRouter(prefix="/api", tags=["health"])` with one route `GET /health` returning `{"status":"ok","version":"0.1.0"}`. In `main.py`, create `create_app() -> FastAPI` that: sets `title="agent-room"`, `version="0.1.0"`, configures CORS allowing `http://localhost:5173` (Vite dev) and same-origin, includes `health.router`, and (later) mounts `frontend/dist` at `/` if it exists. Add a `main()` function that reads `Settings`, configures Python logging at the `log_level`, and runs `uvicorn.run("backend.app.main:create_app", host=settings.app_host, port=settings.app_port, factory=True, reload=False)`.
- Details: The static-mount block must check `if (get_project_root() / "frontend" / "dist").exists()` and only then `app.mount("/", StaticFiles(directory=..., html=True), name="ui")`. This lets the backend run alone during development.
- Dependencies: 1.2, 1.3, 1.4
- Verification: Run `uv run python -m backend.app.main` (after adding `if __name__ == "__main__": main()` block). In a second terminal: `curl -s http://127.0.0.1:8000/api/health` returns exactly `{"status":"ok","version":"0.1.0"}` and HTTP 200 (`curl -o /dev/null -w "%{http_code}"` prints `200`).
- Complexity: Medium
- Risk: Low

**Step 1.G: Phase Gate — Backend Smoke Test**
- Agent: `review-agent`
- Action: Verify the backend boots and serves `/api/health`.
- Verification:
  1. `uv run ruff check backend/` — exits 0.
  2. Start server: `uv run python -m backend.app.main &` then sleep 2 seconds.
  3. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/health` — prints `200`.
  4. `curl -s http://127.0.0.1:8000/api/health | grep -c '"status":"ok"'` — prints `1`.
  5. Kill the background process.
- Dependencies: 1.1–1.5

---

### Phase 2: Storage Layer (Presets & Conversations)

**Purpose:** Persist user-defined agent presets and conversation transcripts to `./data/` as JSON, exposed through CRUD endpoints. After this phase, presets and conversations survive server restarts and are visible via API.

**Step 2.1: Preset Repository Module**
- Agent: `coding-agent`
- Location: `backend/app/storage/preset_repo.py` (create `backend/app/storage/__init__.py`)
- Action: Implement functions:
  - `list_presets() -> list[Preset]`: enumerate `*.json` under `get_presets_dir()`, parse each into `Preset`, return sorted by `updated_at` desc. Files that fail to parse are skipped and logged at WARNING level.
  - `get_preset(preset_id: str) -> Preset | None`.
  - `save_preset(preset: Preset) -> Preset`: writes to `<presets_dir>/<sanitized_name>.json` using **atomic write**: write to `<name>.json.tmp` then `os.replace`. Update `updated_at` to now (UTC).
  - `delete_preset(preset_id: str) -> bool`.
- Details: Sanitize names with `re.sub(r"[^A-Za-z0-9._-]", "_", name)`. Refuse names like `""`, `"."`, `".."`. On collision (same sanitized name, different id), append `_<short_id>` to filename.
- Dependencies: 1.3, 1.4
- Verification: `uv run python -c "from backend.app.storage.preset_repo import save_preset, list_presets; ..."` script (the agent should add a one-off check) that saves a dummy preset and then lists it — output contains the preset's name. Then `ls data/presets/` shows the JSON file; opening it shows valid JSON.
- Complexity: Medium
- Risk: Medium — filesystem races and partial writes.
- Idempotence & Recovery: Atomic via `os.replace`. Re-running `save_preset` overwrites cleanly. If a `.tmp` file is left behind, it is ignored by `list_presets` (only `*.json` are read) and can be safely deleted.

**Step 2.2: Conversation Repository Module**
- Agent: `coding-agent`
- Location: `backend/app/storage/conversation_repo.py`
- Action: Implement:
  - `list_conversations() -> list[ConversationSummary]` where `ConversationSummary = (id, title, updated_at, message_count)`.
  - `get_conversation(conv_id: str) -> Conversation | None`.
  - `save_conversation(conv: Conversation) -> Conversation`: atomic write to `<conversations_dir>/<conv_id>.json`. Auto-generate `title` from the first user message (first 60 chars) if blank.
  - `append_message(conv_id: str, msg: Message) -> Conversation`: load → append → save (whole-file rewrite; acceptable for local single-user usage).
  - `delete_conversation(conv_id: str) -> bool`.
- Dependencies: 1.3, 1.4
- Verification: Add a temporary test snippet (then delete) that creates a conversation with one message, calls `append_message`, reloads via `get_conversation`, and asserts `len(messages) == 2`. Run via `uv run python -c "..."` and confirm exit 0.
- Complexity: Medium
- Risk: Medium — same as 2.1.
- Idempotence & Recovery: Atomic via `os.replace`. Whole-file rewrite means partial-state risk is bounded to "the most recent message may be lost on power-cut", which is acceptable for a local dev tool.

**Step 2.3: Presets REST API**
- Agent: `coding-agent`
- Location: `backend/app/api/presets.py`
- Action: Implement an `APIRouter(prefix="/api/presets", tags=["presets"])` with:
  - `GET /` → `list[Preset]`.
  - `GET /{preset_id}` → `Preset` or 404.
  - `POST /` body `Preset` (id may be empty string, server assigns) → `Preset` (created).
  - `PUT /{preset_id}` body `Preset` → `Preset`.
  - `DELETE /{preset_id}` → `{"deleted": true}` or 404.
  - `POST /import` accepts multipart file `file: UploadFile`. Validate JSON, parse into `Preset`, save, return `Preset`.
  - `GET /{preset_id}/export` → `FileResponse` with `Content-Disposition: attachment; filename="<name>.json"`.
  
  Register this router in `main.py`.
- Dependencies: 2.1
- Verification: With server running, `curl -X POST http://127.0.0.1:8000/api/presets -H "Content-Type: application/json" -d '{"id":"","name":"test","agents":[{"id":"a1","name":"A","persona":"p","model":"m"}],"pattern":"round_robin","max_turns":10,"created_at":"2026-05-12T00:00:00Z","updated_at":"2026-05-12T00:00:00Z"}'` returns HTTP 200 with a JSON body whose `name` field is `"test"`. `curl http://127.0.0.1:8000/api/presets` returns a list containing that preset.
- Complexity: Medium
- Risk: Low

**Step 2.4: Conversations REST API**
- Agent: `coding-agent`
- Location: `backend/app/api/conversations.py`
- Action: Implement `APIRouter(prefix="/api/conversations", tags=["conversations"])` with:
  - `GET /` → `list[ConversationSummary]`.
  - `GET /{conv_id}` → `Conversation` or 404.
  - `DELETE /{conv_id}` → `{"deleted": true}`.
  
  Register in `main.py`. (Creation is implicit — happens in the chat-run endpoint, Phase 4.)
- Dependencies: 2.2
- Verification: `curl http://127.0.0.1:8000/api/conversations` returns `[]` on a fresh data dir, HTTP 200.
- Complexity: Low
- Risk: Low

**Step 2.G: Phase Gate — Storage Verification**
- Agent: `review-agent`
- Action: Verify persistence and CRUD round-trips.
- Verification:
  1. `uv run ruff check backend/` exits 0.
  2. Start server. POST a preset via `curl` (as in 2.3). Stop the server. Restart it. `curl http://127.0.0.1:8000/api/presets` still lists that preset (proves on-disk persistence).
  3. `ls data/presets/*.json | wc -l` matches the number of presets created.
- Dependencies: 2.1–2.4

---

### Phase 3: Attachments & Model Discovery

**Purpose:** Enable the chat run to consume images and URLs, and let the UI dropdown populate model names live from the configured `OPENAI_BASE_URL`. After this phase, the UI can show available LM Studio models and the backend can normalize attachments for the model.

**Step 3.1: URL Fetcher**
- Agent: `coding-agent`
- Location: `backend/app/tools/url_fetch.py`
- Action: Implement `async def fetch_url_as_text(url: str, timeout_s: float = 15.0, max_bytes: int = 2_000_000) -> str`. Behavior:
  - Validate URL scheme is `http` or `https` (raise `ValueError("invalid scheme")` otherwise).
  - Use `httpx.AsyncClient(follow_redirects=True, timeout=timeout_s, headers={"User-Agent": "agent-room/0.1"})`.
  - Stream the response; abort with `ValueError("too large")` if cumulative bytes exceed `max_bytes`.
  - Verify `Content-Type` begins with `text/` or `application/xhtml`; else raise `ValueError("unsupported content-type")`.
  - Pass HTML to `trafilatura.extract(html, include_comments=False, include_tables=False, no_fallback=False)`. If `None`, return the raw text limited to 20 000 chars.
  - Return a string with format: `f"# {url}\n\n{extracted_text[:20000]}"`.
- Details: Concrete I/O example — given `https://example.com`, returns approximately `# https://example.com\n\nExample Domain\nThis domain is for use in illustrative examples...`.
- Dependencies: 1.1
- Verification: `uv run python -c "import asyncio; from backend.app.tools.url_fetch import fetch_url_as_text; print(asyncio.run(fetch_url_as_text('https://example.com'))[:80])"` prints a non-empty string starting with `# https://example.com`.
- Complexity: Medium
- Risk: Medium — network dependency for verification.
- Idempotence & Recovery: Pure read, no side effects.

**Step 3.2: Image Validator and Encoder**
- Agent: `coding-agent`
- Location: `backend/app/tools/image.py`
- Action: Implement:
  - `validate_image(data: bytes, filename: str) -> tuple[str, tuple[int, int]]`: opens with Pillow, asserts format is one of `PNG|JPEG|WEBP`, asserts `max(width, height) <= 4096`, asserts `len(data) <= 10*1024*1024`. Returns `(mime_type, (width, height))`. Raises `ValueError` with a descriptive message on failure.
  - `to_data_url(data: bytes, mime: str) -> str`: returns `f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"`.
- Dependencies: 1.1
- Verification: Write a small ad-hoc script that loads a tiny test PNG (the agent should `python -c` to generate a 32×32 PNG via Pillow into memory), passes its bytes to `validate_image`, asserts the returned mime is `image/png`. Exit code 0.
- Complexity: Low
- Risk: Low

**Step 3.3: Attachments REST API**
- Agent: `coding-agent`
- Location: `backend/app/api/attachments.py`
- Action: Implement `APIRouter(prefix="/api/attachments", tags=["attachments"])` with:
  - `POST /image` accepting `file: UploadFile`. Reads bytes, calls `validate_image`, returns `Attachment(kind="image", payload=<data_url>, source=file.filename)` on success, HTTP 400 with `{"detail": "<error>"}` on failure.
  - `POST /url` accepting JSON `{"url": "..."}`. Calls `fetch_url_as_text`, returns `Attachment(kind="url", payload=<extracted_text>, source=<url>)` on success.
  
  Register in `main.py`.
- Dependencies: 3.1, 3.2
- Verification: With server running, `echo '{"url":"https://example.com"}' | curl -s -X POST http://127.0.0.1:8000/api/attachments/url -H "Content-Type: application/json" -d @-` returns HTTP 200 with a JSON body whose `kind` is `"url"` and whose `payload` starts with `# https://example.com`.
- Complexity: Medium
- Risk: Low

**Step 3.4: Models Discovery Endpoint**
- Agent: `coding-agent`
- Location: `backend/app/api/models.py`
- Action: Implement `APIRouter(prefix="/api/models", tags=["models"])` with `GET /` that:
  - Reads `settings.openai_base_url` and `settings.openai_api_key`.
  - Calls `GET {base_url}/models` via `httpx.AsyncClient` with `Authorization: Bearer <api_key>` header, 10 s timeout.
  - On success, returns `{"models": [item["id"] for item in resp.json()["data"]], "default": settings.default_model}`.
  - On any failure, returns `{"models": [], "default": settings.default_model, "error": "<message>"}` with HTTP 200 (so the UI does not crash).
  
  Register in `main.py`.
- Dependencies: 1.5
- Verification: With LM Studio running and at least one model loaded, `curl http://127.0.0.1:8000/api/models` returns HTTP 200 with a `models` array containing at least one entry. Without LM Studio running, still returns HTTP 200 with `models: []` and an `error` field — confirm by stopping LM Studio temporarily.
- Complexity: Medium
- Risk: Medium — external service dependency.

**Step 3.G: Phase Gate — Attachments & Discovery**
- Agent: `review-agent`
- Action: Verify attachments and model listing work end-to-end.
- Verification:
  1. `uv run ruff check backend/` exits 0.
  2. With server running, `curl -s http://127.0.0.1:8000/api/attachments/url -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com"}' | python -c "import sys, json; d=json.load(sys.stdin); assert d['kind']=='url' and d['payload'].startswith('# https://example.com'); print('ok')"` prints `ok`.
  3. `curl -s http://127.0.0.1:8000/api/models | python -c "import sys, json; d=json.load(sys.stdin); assert 'models' in d and 'default' in d; print('ok')"` prints `ok`.
- Dependencies: 3.1–3.4

---

### Phase 4: Orchestration Core (Round Robin + Free Flow) with SSE Streaming

**Purpose:** Plug Microsoft Agent Framework into FastAPI. After this phase, posting to `/api/chat/run` streams agent messages as Server-Sent Events, persists the conversation on the fly, and can be cancelled.

**Step 4.1: Agent Factory**
- Agent: `coding-agent`
- Location: `backend/app/orchestration/factory.py`
- Action: Implement `def build_chat_agents(preset: Preset) -> list[ChatAgent]`. For each `AgentConfig` in `preset.agents`, construct a `ChatAgent` from `agent_framework` with:
  - `name=cfg.name`
  - `instructions=cfg.persona`
  - `chat_client=OpenAIChatClient(base_url=settings.openai_base_url, api_key=settings.openai_api_key, model_id=cfg.model)` (the exact import path: `from agent_framework.openai import OpenAIChatClient`; constructor accepts `base_url`, `api_key`, `model_id` — confirmed via Microsoft Learn docs at https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.openai.openaichatclient).
  - If `cfg.model` is empty, fall back to `settings.default_model`.
  
  Also implement `def build_orchestrator_chat_client(model_override: str | None = None) -> OpenAIChatClient` for use by Free Flow.
- Details: `ChatAgent` is the top-level agent class in `agent_framework` (the framework exposes both `ChatAgent` and lower-level `AgentExecutor` — use `ChatAgent` because `SequentialBuilder.participants(...)` accepts `AgentProtocol` which `ChatAgent` implements).
- Dependencies: 1.4, 1.5
- Verification: `uv run python -c "from backend.app.orchestration.factory import build_chat_agents; from backend.app.schemas import Preset, AgentConfig; from datetime import datetime, timezone; p=Preset(id='x',name='x',agents=[AgentConfig(id='a',name='A',persona='p',model='m')],pattern='round_robin',max_turns=10,created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc)); a=build_chat_agents(p); print(type(a[0]).__name__)"` prints `ChatAgent`.
- Complexity: Medium
- Risk: Medium — framework API names may shift between RC and 1.0; the agent should `pip show agent-framework` and `python -c "import agent_framework; print(dir(agent_framework))"` to confirm symbols `ChatAgent`, `SequentialBuilder`, `MagenticBuilder`, `OpenAIChatClient` exist before writing this file. If any name differs, consult `https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework` and update accordingly, recording the divergence in `NOTES.md`.

**Step 4.2: Round Robin Workflow**
- Agent: `coding-agent`
- Location: `backend/app/orchestration/round_robin.py`
- Action: Implement `async def run_round_robin(preset: Preset, prompt: str, attachments: list[Attachment], on_event, cancel_event: asyncio.Event) -> None`:
  - Build agents via `build_chat_agents(preset)`.
  - Construct workflow: `workflow = SequentialBuilder().participants(agents).build()`.
  - Wrap the user prompt + attachments into the initial input message (text + image content parts; URL attachments are appended to the prompt as `\n\n[Reference content from {source}]:\n{payload}`).
  - Loop: iterate `preset.max_turns` total agent-speaks, where each pass through the list counts as `len(agents)` turns. Inside the iteration, run the workflow once and consume its event stream; on each `AgentRunResponseUpdate` (or equivalent streaming event) call `on_event({"type":"message_delta", ...})`; on agent completion call `on_event({"type":"message_complete", "agent_id":..., "name":..., "content":...})`.
  - Check `cancel_event.is_set()` between turns and at every streamed chunk; if set, call `on_event({"type":"cancelled"})` and return.
  - On completion call `on_event({"type":"done", "reason":"max_turns"})`.
- Details: The exact event-emission API of `agent-framework` 1.0 is `workflow.run_stream(input)` returning an async iterator of events. Each event has a `type` discriminator; the agent should print `event.__class__.__name__` once during development to discover the precise classes (`AgentRunResponseUpdate`, `WorkflowOutputEvent`, etc.) and branch accordingly. Document the discovered event shape in `NOTES.md` under "Agent Framework Event Catalog".
- Dependencies: 4.1
- Verification: Deferred to integration step 4.5 (end-to-end via `/api/chat/run`).
- Complexity: High
- Risk: High — depends on framework streaming-event shape which may differ across point releases. Mitigation: log raw events to `NOTES.md` during first run.
- Idempotence & Recovery: Each call creates a fresh workflow instance; safe to re-invoke. Cancellation is cooperative via the `cancel_event` — partial state is forwarded via `on_event` and the caller persists messages as they arrive.

**Step 4.3: Free Flow (Magentic) Workflow**
- Agent: `coding-agent`
- Location: `backend/app/orchestration/free_flow.py`
- Action: Implement `async def run_free_flow(preset: Preset, prompt: str, attachments: list[Attachment], on_event, cancel_event: asyncio.Event) -> None`:
  - Build agents (4.1). Build orchestrator client (4.1).
  - Construct workflow: `workflow = MagenticBuilder().participants(*agents).with_standard_manager(chat_client=orchestrator_client, max_round_count=preset.max_turns).build()`.
  - Stream events identically to 4.2.
- Details: Per https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.magenticbuilder, `MagenticBuilder` exposes a `participants(*args)` method and a manager configuration step. The exact manager-config method name in 1.0 is `with_standard_manager(...)`; the agent must verify symbol existence (as in 4.1) and adjust to the actual method name printed by `dir()`. Record the verified call signature in `NOTES.md`.
- Dependencies: 4.1
- Verification: Deferred to 4.5.
- Complexity: High
- Risk: High — same reason as 4.2.

**Step 4.4: Cancellable Runner & SSE Encoder**
- Agent: `coding-agent`
- Location: `backend/app/orchestration/runner.py`
- Action: Implement:
  - `class SSEEvent(BaseModel)` with `event: str`, `data: dict`.
  - `def encode_sse(ev: dict) -> bytes`: returns `f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode("utf-8")`.
  - `async def run_conversation(req: RunRequest) -> AsyncIterator[bytes]`:
    - Resolve or create `Conversation` (via `conversation_repo`); append the user message with attachments immediately.
    - Create `asyncio.Event` named `cancel_event`. Register it in a module-level `dict[str, asyncio.Event]` keyed by `conversation.id` (so a `POST /api/chat/cancel/{conv_id}` can set it).
    - Pick `run_round_robin` or `run_free_flow` based on `req.preset.pattern`.
    - Define `on_event(payload)` as a closure that: (a) if `type == "message_complete"`, persists the message via `conversation_repo.append_message`; (b) yields `encode_sse(payload)` to the caller via an `asyncio.Queue`.
    - Launch the workflow in an `asyncio.Task` and stream from the queue until a sentinel is enqueued.
    - On `cancel_event.set()`, the workflow function emits `{"type":"cancelled"}` and finishes; the runner then enqueues the sentinel.
  - `def cancel_conversation(conv_id: str) -> bool`: looks up the event in the registry and sets it.
- Details: Use `asyncio.Queue` because `on_event` is a sync callback called from inside async generators; the queue bridges them. The runner registers `cancel_event` at start and pops it at end (use `try/finally`).
- Dependencies: 4.2, 4.3, 2.2
- Verification: Deferred to 4.5.
- Complexity: High
- Risk: High — concurrency. Mitigation: keep the queue bounded to 256 to surface bugs early; log a warning if a slow consumer causes backpressure.

**Step 4.5: Chat Run Endpoint**
- Agent: `coding-agent`
- Location: `backend/app/api/chat.py`
- Action: Implement `APIRouter(prefix="/api/chat", tags=["chat"])` with:
  - `POST /run` body `RunRequest` → `StreamingResponse(run_conversation(req), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`.
  - `POST /cancel/{conv_id}` → calls `cancel_conversation(conv_id)`; returns `{"cancelled": <bool>}`.
  
  Register in `main.py`.
- Dependencies: 4.4
- Verification (END-TO-END, this is the phase's observable behavior gate):
  1. With LM Studio running and one chat model loaded, create a preset via `POST /api/presets` with 2 agents (Architect, Synthesizer) both using the loaded model, pattern `round_robin`, max_turns 4.
  2. Run: `curl -N -X POST http://127.0.0.1:8000/api/chat/run -H "Content-Type: application/json" -d '{"preset": <preset>, "prompt": "Discuss the trade-offs of microservices vs monolith.", "attachments": []}'`. Confirm streamed `data: {...}` lines arrive within 10 seconds, including at least 2 `message_complete` events with different `name` values, ending with a `done` event.
  3. Confirm `ls data/conversations/*.json | wc -l` increased by 1.
  4. Open the JSON file; the `messages` array has ≥ 3 entries (user + 2 assistants).
- Complexity: High
- Risk: High — first end-to-end integration of the orchestration stack.

**Step 4.G: Phase Gate — Orchestration**
- Agent: `review-agent`
- Action: Confirm Step 4.5's verification has passed (the observable end-to-end test). Also confirm `uv run ruff check backend/` exits 0.
- Verification: Re-run the 4.5 curl command. Cancel test: start a long run (max_turns=20); after the second message arrives, `curl -X POST http://127.0.0.1:8000/api/chat/cancel/<conv_id>`. Confirm a `cancelled` event arrives within 2 seconds and the connection closes cleanly.
- Dependencies: 4.1–4.5

---

### Phase 5: Auto Agent Creation

**Purpose:** Add the LLM-driven feature that, from a theme description, drafts a set of agents the user can review and adopt.

**Step 5.1: Auto Agent Generator**
- Agent: `coding-agent`
- Location: `backend/app/orchestration/auto_agents.py`
- Action: Implement `async def generate_agents(theme: str, count: int | None, model: str) -> list[AgentConfig]`. Behavior:
  - Build a single `OpenAIChatClient(model_id=model)`.
  - Construct a system prompt that instructs the model to output strict JSON of the form `{"agents":[{"name":"...","persona":"...","model":"<same as caller's default>","color":"#RRGGBB"}, ...]}` with these rules embedded verbatim in the prompt: names are 1–40 chars and distinct; personas are 1–800 chars in second person ("You are..."); colors are mint-family hex codes; if `count` is null choose 2–5 based on the theme; otherwise produce exactly `count` agents.
  - User message: `Theme: {theme}\n\nProduce the JSON now. Do not include any prose outside the JSON object.`
  - Call the chat client with `response_format={"type":"json_object"}` if supported; otherwise rely on the prompt and post-parse.
  - Parse JSON, validate via `AutoAgentResponse`, assign fresh uuids to each agent, set `model` to `settings.default_model` if missing.
  - On JSON parse failure, retry once with an appended "Your previous response was not valid JSON. Output only JSON." message. After two failures, raise `RuntimeError("auto-agent generation failed")`.
- Details: I/O example — input theme `"Should we adopt Rust for our backend?"`, count `null` → output 3–4 agents like `{name: "Pragmatist", persona: "You are a pragmatic backend engineer..."}`, etc.
- Dependencies: 4.1
- Verification: Deferred to 5.2.
- Complexity: Medium
- Risk: Medium — depends on local model's JSON-following ability; mitigated by retry.

**Step 5.2: Auto Agents Endpoint**
- Agent: `coding-agent`
- Location: `backend/app/api/auto_agents.py`
- Action: `APIRouter(prefix="/api/auto-agents", tags=["auto-agents"])` with `POST /` body `AutoAgentRequest` → `AutoAgentResponse`. Register in `main.py`.
- Dependencies: 5.1
- Verification: With LM Studio running, `curl -X POST http://127.0.0.1:8000/api/auto-agents -H "Content-Type: application/json" -d '{"theme":"Pros and cons of remote work","count":3,"model":"<loaded_model>"}'` returns HTTP 200 with a JSON body whose `agents` array length is exactly 3.
- Complexity: Low
- Risk: Medium — depends on 5.1.

**Step 5.G: Phase Gate — Auto Agents**
- Agent: `review-agent`
- Verification: Re-run 5.2 verification. Confirm response shape conforms to `AutoAgentResponse` schema (validate via `python -c "import sys,json; from backend.app.schemas import AutoAgentResponse; AutoAgentResponse.model_validate_json(sys.stdin.read()); print('ok')"`).
- Dependencies: 5.1, 5.2

---

### Phase 6: Frontend (React + Vite + Tailwind v4)

**Purpose:** Build the messenger-style UI matching the user-supplied mockups (renamed from "AetherControl" to "agent-room"), wired to the backend. After this phase, opening the browser shows a fully functional UI.

**Step 6.1: Scaffold Vite + React + TS**
- Agent: `devops-agent`
- Location: `frontend/`
- Action: From repo root: `npm create vite@latest frontend -- --template react-ts`. Inside `frontend/`: `npm install`. Then install deps: `npm install zustand react-router-dom lucide-react` and `npm install -D tailwindcss @tailwindcss/vite`. Update `vite.config.ts` to include the `@tailwindcss/vite` plugin and add a `server.proxy` for `/api` pointing to `http://127.0.0.1:8000` (so dev mode at :5173 transparently calls the backend).
- Details: `vite.config.ts` essentials:
  ```ts
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'
  import tailwindcss from '@tailwindcss/vite'
  export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
    build: { outDir: 'dist', emptyOutDir: true },
  })
  ```
  Replace `src/index.css` with a single line `@import "tailwindcss";` followed by a `@theme { ... }` block defining the palette tokens (`--color-mint-primary: #5EE0C6;` etc.) per Tailwind v4 conventions.
- Dependencies: 0.G
- Verification: `cd frontend && npm run build` exits 0; `frontend/dist/index.html` exists.
- Complexity: Medium
- Risk: Low

**Step 6.2: Type Mirrors and API Client**
- Agent: `coding-agent`
- Location: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- Action: In `types.ts`, define TypeScript interfaces mirroring Phase 1.4 schemas (`AgentConfig`, `Preset`, `Conversation`, `Message`, `Attachment`, `RunRequest`, `AutoAgentRequest`, `AutoAgentResponse`, `ConversationSummary`). In `api.ts`, define:
  - `const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ""` (empty string → same-origin, so dev proxy + prod static mount both work).
  - `async function getJson<T>(path: string): Promise<T>`, `postJson<T>`, `del`.
  - `async function* parseSSE(response: Response): AsyncGenerator<{type: string; [k: string]: unknown}>` that reads `response.body!.getReader()`, decodes UTF-8, splits on `\n\n`, parses each `data: ...` line as JSON, yields each parsed event. Stops cleanly on stream end or AbortError.
  - `async function runChat(req: RunRequest, signal: AbortSignal)`: POSTs to `/api/chat/run` and returns the async generator from `parseSSE`.
- Details: SSE parsing example: input chunk `"data: {\"type\":\"message_complete\",\"name\":\"Architect\"}\n\n"` yields `{type:"message_complete", name:"Architect"}`.
- Dependencies: 6.1
- Verification: `cd frontend && npx tsc --noEmit` exits 0.
- Complexity: Medium
- Risk: Low

**Step 6.3: Zustand Store**
- Agent: `coding-agent`
- Location: `frontend/src/lib/store.ts`
- Action: Define a Zustand store with state:
  - `agents: AgentConfig[]`, `pattern: "round_robin"|"free_flow"`, `maxTurns: number`, `defaultModel: string`, `availableModels: string[]`.
  - `currentConversationId: string | null`, `messages: Message[]`, `runStatus: "idle"|"running"|"cancelling"`, `abortController: AbortController | null`.
  - Actions: `addAgent`, `removeAgent(id)`, `updateAgent(id, patch)`, `setPattern`, `setMaxTurns`, `appendMessage`, `replaceMessages`, `startRun(req)`, `cancelRun()`, `loadPreset(preset)`, `loadModels()`, `loadConversation(id)`.
- Details: `startRun` consumes the SSE generator and calls `appendMessage` on each `message_complete` event, updates `runStatus`. `cancelRun` calls `abortController.abort()` AND posts to `/api/chat/cancel/<id>` to stop the server side.
- Dependencies: 6.2
- Verification: `npx tsc --noEmit` exits 0.
- Complexity: Medium
- Risk: Low

**Step 6.4: App Shell, Routing, Sidebar**
- Agent: `coding-agent`
- Location: `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/components/Sidebar.tsx`
- Action:
  - `main.tsx`: wrap `<App/>` in `<BrowserRouter>`.
  - `App.tsx`: defines routes `/` (redirects to `/simulation`), `/simulation` → `<Simulation/>`, `/orchestration` → `<Orchestration/>`. Layout: left `<Sidebar/>` (fixed 220 px), right content area.
  - `Sidebar.tsx`: header with app title "agent-room" and a status dot; primary button "New Session" (clears current conversation, navigates to `/simulation`); nav links "Simulation" and "Orchestration"; bottom links "Logs" (opens a modal showing the last 200 lines of server console, optional — can be a stub `<a href="/api/health">`) and "Docs" (opens README on GitHub in new tab; placeholder URL).
  - Below "New Session", show a scrollable list of past conversations (titles, timestamps) loaded from `GET /api/conversations`.
- Details: Color tokens from `@theme`. Light theme: white sidebar with subtle mint accents, active nav item background `bg-mint-primary/15`, text `text-mint-accent`. Match the user-supplied screenshot layout (sidebar on left, main content centered).
- Dependencies: 6.3
- Verification: `npm run dev`, open `http://localhost:5173`, observe sidebar with the two nav links, app title `agent-room`. Click both links — URL changes.
- Complexity: Medium
- Risk: Low

**Step 6.5: Orchestration View**
- Agent: `coding-agent`
- Location: `frontend/src/routes/Orchestration.tsx`, `frontend/src/components/AgentCard.tsx`, `frontend/src/components/PatternToggle.tsx`, `frontend/src/components/PresetActions.tsx`, `frontend/src/components/AutoAgentDialog.tsx`
- Action: Implement the view shown in the first reference screenshot, renamed to "agent-room":
  - Header: title "Orchestration Settings", subtitle "Configure AI agent parameters, system prompts, and collaborative patterns.", right-side buttons "Export JSON" and "Import JSON".
  - "Global Pattern" card: `<PatternToggle/>` with two pills "Free Flow" and "Sequential" (mapped to backend `free_flow`/`round_robin`); a short description text on the right that updates with the choice; a `<NumberInput/>` for `Max Turns` (1–50).
  - "Auto Agent Creation" card (above Active Agents per the user spec): textarea for theme description; radio "Number of agents" with options `Auto`, `1`, `2`, `3`, `4`, `5`; model dropdown defaulting to `defaultModel`; "Generate" button → opens `<AutoAgentDialog/>` showing the preview list, each row editable, with "Adopt" (replaces store agents) and "Cancel".
  - "Active Agents" section header with "Add Agent" button on the right. Each agent rendered as an `<AgentCard/>`: a left-side avatar circle (initial + color), then form fields "Agent Name", "Model Engine" (dropdown from `availableModels`), and "System Persona (Prompt)" (multiline). "Remove" link in the top-left of each card.
  - Bottom-right: "Save Configuration to JSON" button that prompts for a preset name (use `window.prompt`) and POSTs to `/api/presets`.
- Details: Export → `window.location = "/api/presets/<id>/export"`. Import → file input → `POST /api/presets/import` as `multipart/form-data`.
- Dependencies: 6.4
- Verification: `npm run dev`. Navigate to `/orchestration`. Add 2 agents, fill names+personas, pick model from dropdown (which should populate from `/api/models`). Click "Save Configuration to JSON", enter name "demo". Confirm `data/presets/demo.json` exists on disk and its content matches what was entered.
- Complexity: High
- Risk: Medium — most complex UI screen.

**Step 6.6: Simulation View**
- Agent: `coding-agent`
- Location: `frontend/src/routes/Simulation.tsx`, `frontend/src/components/ChatStream.tsx`, `frontend/src/components/MessageBubble.tsx`, `frontend/src/components/PromptInput.tsx`
- Action: Implement the view shown in the second reference screenshot, renamed to "agent-room":
  - Top right of header: a status pill indicating current pattern ("ROUND ROBIN" / "FREE FLOW"); the existing app-title remains centered.
  - Main area: `<ChatStream/>` — a scrollable list of `<MessageBubble/>` components. Each bubble has a colored vertical accent bar, agent avatar circle, agent name + timestamp header, and message body. The first system note "ENCRYPTED SIMULATION STARTED" from the mock is replaced by "Conversation started at HH:MM:SS".
  - Auto-scroll to bottom on new message, but pause auto-scroll if the user has scrolled up (resume on "Jump to latest" button).
  - Bottom: `<PromptInput/>` — textarea with placeholder "Type a topic or steer the discussion…", left toolbar icons: paperclip (image upload) and link (URL attach, opens a small popover with a URL input), and a "Parameters" gear that opens a panel showing current preset + max_turns; right side: a teal "Send" button. When `runStatus === "running"`, the Send button becomes a red "Stop" button.
  - On Send: builds a `RunRequest` from the store, calls `store.startRun(req)`. Each `message_complete` event appends a bubble.
- Details: Image attach flow: file picker → `POST /api/attachments/image` → store the returned `Attachment` in a "pending attachments" array shown as small chips above the input → cleared after Send. URL flow: same but `POST /api/attachments/url`.
- Dependencies: 6.5
- Verification: With backend running and a preset configured, type "Discuss pros and cons of TypeScript vs JavaScript" and press Send. Within 15 seconds, multiple distinct agent bubbles appear in sequence. Press Stop mid-conversation — within 2 seconds the stream halts and the Send button reappears.
- Complexity: High
- Risk: High — SSE streaming + UI state + cancellation interplay.

**Step 6.G: Phase Gate — Frontend**
- Agent: `review-agent`
- Action: Verify the UI works end-to-end.
- Verification:
  1. `cd frontend && npx tsc --noEmit` exits 0.
  2. `npm run build` exits 0 and `frontend/dist/index.html` exists.
  3. Manual flow (LM Studio + backend running): open `http://localhost:5173`, add 2 agents at `/orchestration`, save preset; switch to `/simulation`, send a prompt, watch ≥2 distinct agent bubbles stream in, press Stop and confirm halt within 2 s.
- Dependencies: 6.1–6.6

---

### Phase 7: One-Shot Launcher and Polish

**Purpose:** Provide the `./start.sh` experience the user explicitly asked for, mount the built frontend on the backend, and finalize docs. After this phase, `git clone` → `./start.sh` → browser opens automatically, fully wired.

**Step 7.1: Mount Built Frontend**
- Agent: `coding-agent`
- Location: `backend/app/main.py`
- Action: Confirm the existing static mount block (1.5) serves `frontend/dist/`. Add a fallback route: any GET to a non-API path returns `index.html` (so client-side routing on `/orchestration` works on a hard refresh). Implement as a catch-all `@app.get("/{full_path:path}")` that returns `FileResponse(dist/index.html)` if the path does not start with `api/` and `dist/` exists; otherwise 404.
- Dependencies: 1.5, 6.G
- Verification: `cd frontend && npm run build`. Restart backend. `curl -s http://127.0.0.1:8000/orchestration | head -1` outputs `<!doctype html>` (proves SPA fallback works).
- Complexity: Low
- Risk: Low

**Step 7.2: start.sh Launcher**
- Agent: `devops-agent`
- Location: `./start.sh`
- Action: Bash script (with `#!/usr/bin/env bash` and `set -euo pipefail`) that:
  1. `cd` to the script's directory.
  2. If `command -v uv` fails, print an instruction to install via `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv` and exit 1.
  3. Run `uv sync` (idempotent; fast if already synced).
  4. If `frontend/dist/index.html` does not exist OR `frontend/package.json` is newer than `frontend/dist/index.html`: `cd frontend && npm install && npm run build && cd ..`.
  5. If `.env` does not exist, copy `.env.example` to `.env` and echo a note "Created .env from template — edit if needed.".
  6. Determine the port: `PORT="${APP_PORT:-8000}"`.
  7. Start the server in the background: `uv run python -m backend.app.main &` capture the PID into a variable `SERVER_PID`.
  8. Wait until `curl -sf http://127.0.0.1:$PORT/api/health` succeeds (poll every 0.5 s up to 20 s).
  9. Open the browser: `open "http://127.0.0.1:$PORT"`.
  10. Trap SIGINT/SIGTERM/EXIT to `kill $SERVER_PID 2>/dev/null || true`.
  11. `wait $SERVER_PID` (block until server exits).
- Details: Make executable: `chmod +x start.sh`. The script must be safe to re-run (idempotent). If `npm install` fails because Node is missing, print a clear message pointing at `https://nodejs.org/`. If port is busy, print `Port $PORT busy — set APP_PORT=8001 ./start.sh` and exit 1 (check with `lsof -i :$PORT` or `nc -z 127.0.0.1 $PORT`).
- Dependencies: 7.1
- Verification: From a fresh shell, `./start.sh` — within 30 s the default browser opens to `http://127.0.0.1:8000` showing the agent-room UI sidebar. Ctrl+C in the terminal terminates the server cleanly (no orphan `uvicorn` process: `pgrep -f "backend.app.main"` returns nothing after Ctrl+C).
- Complexity: Medium
- Risk: Medium — shell portability and signal handling.
- Idempotence & Recovery: All steps are individually idempotent. If the script fails mid-way, it can be re-run safely.

**Step 7.3: Optional stop.sh**
- Agent: `devops-agent`
- Location: `./stop.sh`
- Action: A 5-line bash script that runs `lsof -ti tcp:${APP_PORT:-8000} | xargs -r kill -TERM`, prints `Stopped.`. `chmod +x`.
- Dependencies: 7.2
- Verification: With server running, `./stop.sh` exits 0 and the server stops (`curl http://127.0.0.1:8000/api/health` then fails with "connection refused").
- Complexity: Low
- Risk: Low

**Step 7.4: Polish Pass (Refactor)**
- Agent: `refactoring-agent`
- Location: `backend/app/`, `frontend/src/`
- Action: Without changing external behavior, address:
  - Extract any duplicated SSE-event-construction code into a single helper.
  - Replace any `print(...)` calls with `logger.info/debug`.
  - Ensure every Python module has UTF-8 source and English comments only.
  - Verify no `// added here` / `# fixed below` style log-comments remain — strip if any.
  - Run `uv run ruff check --fix backend/` and `cd frontend && npx tsc --noEmit && npx eslint . --fix` (eslint is shipped by the Vite template).
- Dependencies: 7.2
- Verification: `uv run ruff check backend/` and `cd frontend && npx tsc --noEmit` both exit 0. Existing 4.5 end-to-end test still passes (re-run it).
- Complexity: Medium
- Risk: Low

**Step 7.5: Final Documentation Pass**
- Agent: `documentation-agent`
- Location: `README.md`, `AGENTS.md`, `NOTES.md`, `CHANGELOG.md`
- Action: Expand `README.md` to include: a screenshot description, "Quick Start" with `./start.sh`, "Prerequisites" (macOS 26+, Node ≥ 24, uv, LM Studio running on :1234 with at least one chat model loaded), "Configuration" (the `.env` keys table), "Architecture" (1-paragraph diagram in ASCII: Browser → FastAPI → Agent Framework → OpenAI-compatible API → LM Studio), "Future: Electron Migration" subsection (one paragraph noting the three abstraction seams: `VITE_API_BASE_URL`, `APP_PORT`, `get_data_dir()`), "License: MIT". Update `CHANGELOG.md` to add `## [0.1.0] - 2026-05-12` with a bullet list of features. Add to `AGENTS.md` a "Re-entry Notes" section pointing future agents to `NOTES.md`.
- Dependencies: 7.4
- Verification: `wc -l README.md` ≥ 50. Open README in a markdown previewer — sections render. `grep -c "MIT" LICENSE README.md` returns ≥ 2.
- Complexity: Low
- Risk: Low

**Step 7.G: Phase Gate — Final System Verification**
- Agent: `review-agent`
- Action: Full system smoke test.
- Verification:
  1. From a clean clone (or after `rm -rf .venv frontend/node_modules frontend/dist data/presets/* data/conversations/*`), run `./start.sh`. Within 60 s the browser opens to the UI.
  2. In the UI: go to Orchestration, add 2 agents (one named "Architect", one "Synthesizer"), pick a real model loaded in LM Studio for each, save preset "demo".
  3. Confirm `data/presets/demo.json` exists.
  4. Go to Simulation, type "Discuss whether to use Rust or Go for a new CLI tool.", press Send.
  5. Observe ≥ 2 distinct agent bubbles streaming in within 30 s.
  6. Press Stop — within 2 s streaming halts.
  7. Refresh the page — past conversation appears in the sidebar; click it — full transcript reloads.
  8. Switch pattern to "Free Flow", run again — observe that the order of speakers is not strictly round-robin.
  9. Open Auto Agent Creation, type "Should we move to a microservices architecture?", count = Auto, Generate → preview shows 2–5 agents → Adopt → Active Agents list is replaced.
  10. Ctrl+C in the terminal — server stops, no orphan processes (`pgrep -f backend.app.main` empty).
- Dependencies: 7.1–7.5

---

**Risks and Mitigations:**

| Risk | Mitigation | Step |
|---|---|---|
| `agent-framework` symbol names (e.g., `MagenticBuilder.with_standard_manager`) may differ from the docs at execution time. | Before writing 4.1/4.2/4.3, the agent runs `python -c "import agent_framework; print(dir(agent_framework))"` and inspects the actual API; records findings in `NOTES.md`. | 4.1 |
| Local model produces invalid JSON for Auto Agents. | Retry-once strategy + strict `response_format` request; on failure return HTTP 502 with clear UI error. | 5.1 |
| Long-running SSE stream consumes too much context. | Rolling-window 40-message cap before sending to the LLM, even though full history is persisted. | 4.4 |
| Port 8000 busy. | `start.sh` checks the port and exits with a clear "set APP_PORT=8001" message. | 7.2 |
| LM Studio not running when user launches the app. | `/api/models` returns empty list gracefully; the UI shows a banner "No models available — is LM Studio running on $OPENAI_BASE_URL?". The chat-run endpoint surfaces a clear error event `{"type":"error","message":"..."}` if the OpenAI client raises. | 3.4, 4.5 |
| Cancellation leaves zombie workflow tasks. | `runner.py` always pops the registry entry in `finally`; the `asyncio.Task` is awaited with a timeout after `cancel_event.set()`. | 4.4 |
| Future Electron migration would require deep refactors. | Three abstraction seams (`VITE_API_BASE_URL`, `APP_PORT`, `get_data_dir()`) are introduced from day one so migration is mostly a wrapper. | 1.3, 6.2, 7.5 |

**Success Criteria:**
1. `./start.sh` on a fresh clone, with LM Studio running on `http://localhost:1234/v1` and one chat model loaded, opens the browser to a working UI within 60 seconds.
2. `curl http://127.0.0.1:8000/api/health` returns `{"status":"ok","version":"0.1.0"}` HTTP 200.
3. A user can create a preset of 2+ agents, save it to JSON in `./data/presets/`, restart the server, and reload that preset.
4. Sending a prompt in Round Robin mode produces messages from each agent in the configured order, ending at `max_turns`.
5. Sending a prompt in Free Flow mode produces messages whose speaker order is determined by the Magentic orchestrator (not strictly round-robin).
6. Pressing Stop halts the stream within 2 seconds; the partial conversation is persisted under `./data/conversations/`.
7. Auto Agent Creation with `count=Auto` returns 2–5 agents; with `count=N` returns exactly N agents (1 ≤ N ≤ 5).
8. URL attachment: pasting `https://example.com` results in an assistant message that references the page's content.
9. Image attachment: with a multimodal model loaded, attaching a small PNG results in agent messages that mention the image content.
10. `uv run ruff check backend/` and `cd frontend && npx tsc --noEmit` both exit 0.
11. Ctrl+C in the launcher terminal stops the server with no orphan processes (`pgrep -f backend.app.main` empty afterwards).
12. The repo contains `.gitignore`, `LICENSE` (MIT), `README.md`, `AGENTS.md`, `NOTES.md`, `CHANGELOG.md`, and `data/.gitkeep` (with conversation/preset files git-ignored).

---

**Progress:**
- [ ] Phase 0: Repository Bootstrap (0.1, 0.2, 0.3, 0.G)
- [ ] Phase 1: Backend Foundation (1.1–1.5, 1.G)
- [ ] Phase 2: Storage Layer (2.1–2.4, 2.G)
- [ ] Phase 3: Attachments & Discovery (3.1–3.4, 3.G)
- [ ] Phase 4: Orchestration Core (4.1–4.5, 4.G)
- [ ] Phase 5: Auto Agent Creation (5.1, 5.2, 5.G)
- [ ] Phase 6: Frontend (6.1–6.6, 6.G)
- [ ] Phase 7: Launcher & Polish (7.1–7.5, 7.G)

**Decision Log:**
- Decision: Use the local Web-server architecture (Python FastAPI + browser UI) instead of Electron. Three abstraction seams (`VITE_API_BASE_URL`, `APP_PORT`, `get_data_dir()`) are introduced from day one to keep a future Electron migration cheap.
  Rationale: User explicitly preferred Web-server style for simplicity; future Electron path is preserved.
  Date: 2026-05-12
- Decision: Map UI label "Sequential" to backend `round_robin` and "Free Flow" to backend `free_flow` (Magentic-style).
  Rationale: Matches reference screenshots while using MAF's idiomatic builders.
  Date: 2026-05-12
- Decision: Store data under `./data/` (repo-relative) rather than `~/Library/Application Support/agent-room/`.
  Rationale: User explicitly requested this in answer #4.
  Date: 2026-05-12
- Decision: Target Python 3.13 first, fall back to 3.12 only if `agent-framework` wheels are missing.
  Rationale: User stated mild preference for 3.13; library compatibility takes precedence.
  Date: 2026-05-12

**Surprises & Discoveries:**
*(To be filled in by the executing agent as work proceeds. Reserve entries for: actual class names emitted by `agent_framework` workflow streams; LM Studio quirks; Tailwind v4 theme-token resolution issues.)*

**Outcomes & Retrospective:**
*(To be filled in after Step 7.G passes.)*

