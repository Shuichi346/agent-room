#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it with: brew install uv"
  exit 1
fi

if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.nvm/nvm.sh"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 24+ is required. Install it from https://nodejs.org/"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required. If you use nvm, run: source ~/.nvm/nvm.sh"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from template. Edit it if your LM Studio endpoint differs."
fi

set -a
source .env
set +a

PORT="${APP_PORT:-8000}"
if lsof -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT busy. Run with APP_PORT=8001 ./start.sh or stop the listener."
  exit 1
fi

uv sync

if [[ ! -f frontend/dist/index.html || frontend/package.json -nt frontend/dist/index.html ]]; then
  (cd frontend && npm install && npm run build)
fi

uv run python -m backend.app.main &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

for _ in {1..40}; do
  if curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null; then
    open "http://127.0.0.1:$PORT"
    wait "$SERVER_PID"
    exit $?
  fi
  sleep 0.5
done

echo "Server did not become healthy on http://127.0.0.1:$PORT within 20 seconds."
exit 1
