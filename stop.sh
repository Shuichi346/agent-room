#!/usr/bin/env bash
set -euo pipefail

PORT="${APP_PORT:-8000}"
lsof -ti tcp:"$PORT" | xargs -r kill -TERM
echo "Stopped."

