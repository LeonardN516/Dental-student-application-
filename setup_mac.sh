#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh and run this script again."
  exit 1
fi

brew list uv >/dev/null 2>&1 || brew install uv
brew list postgresql@17 >/dev/null 2>&1 || brew install postgresql@17
brew list --cask pgadmin4 >/dev/null 2>&1 || brew install --cask pgadmin4

brew services start postgresql@17

POSTGRES_BIN="$(brew --prefix postgresql@17)/bin"
DATABASE_NAME="Dentistry_scheduler"

sleep 2

if ! "$POSTGRES_BIN/pg_isready" -q; then
  echo "PostgreSQL did not become ready."
  exit 1
fi

if ! "$POSTGRES_BIN/psql" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '$DATABASE_NAME'" | grep -q 1; then
  "$POSTGRES_BIN/createdb" "$DATABASE_NAME"
fi

"$POSTGRES_BIN/psql" \
  -v ON_ERROR_STOP=1 \
  -d "$DATABASE_NAME" \
  -f "$PROJECT_DIR/database_setup.sql"

if [ ! -f .env ]; then
  printf 'DATABASE_URL=postgresql+psycopg://%s@localhost:5432/%s\n' \
    "$USER" "$DATABASE_NAME" > .env
fi

uv sync

echo
echo "Setup complete. Start the application with:"
echo "bash start_mac.sh"
