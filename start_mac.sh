#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Run bash setup_mac.sh first."
  exit 1
fi

if [ ! -f .env ]; then
  echo ".env is missing. Run bash setup_mac.sh first."
  exit 1
fi

brew services start postgresql@17 >/dev/null

uv run fastapi dev Server/main.py &
BACKEND_PID=$!

uv run python -m http.server 5500 --directory Client &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1 && \
     curl -fsS http://127.0.0.1:5500/index.html >/dev/null 2>&1; then
    open http://127.0.0.1:5500/index.html
    break
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "The application did not start successfully."
    exit 1
  fi

  sleep 1
done

echo "Dentistry Scheduler is running. Press Control+C to stop it."
wait
