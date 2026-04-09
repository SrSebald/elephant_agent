#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
DATA_DIR="$BACKEND_DIR/data"
TEST_DB_RELATIVE="data/elephant_agent_test.db"
TEST_DB_PATH="$BACKEND_DIR/$TEST_DB_RELATIVE"
PORT="${BACKEND_PORT:-8000}"
RESET_DB="${BACKEND_RESET_DB:-true}"

mkdir -p "$DATA_DIR"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is not installed. Run 'pip install -e ./backend' first."
  exit 1
fi

if command -v netstat >/dev/null 2>&1; then
  if netstat -an 2>/dev/null | grep -E "[\.:]$PORT[[:space:]]" | grep LISTEN >/dev/null 2>&1; then
    echo "Port $PORT is already in use. Stop the current process or set BACKEND_PORT to another value."
    exit 1
  fi
fi

if [ "$RESET_DB" = "true" ] && [ -f "$TEST_DB_PATH" ]; then
  rm -f "$TEST_DB_PATH"
fi

export DATABASE_PATH="$TEST_DB_RELATIVE"
export ALLOW_DRY_RUN="${ALLOW_DRY_RUN:-true}"

echo "Starting Elephant Agent backend with test database:"
echo "  $TEST_DB_PATH"
echo "Reset DB on start: $RESET_DB"
echo "Backend URL: http://127.0.0.1:$PORT"

(cd "$BACKEND_DIR" && exec uvicorn app.main:app --reload --host 127.0.0.1 --port "$PORT")
