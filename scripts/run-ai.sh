#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_DIR="$ROOT_DIR/ai"

find_python() {
  if [[ -f "$AI_DIR/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "$AI_DIR/.venv/Scripts/python.exe"
    return 0
  fi

  if [[ -f "$AI_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$AI_DIR/.venv/bin/python"
    return 0
  fi

  return 1
}

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  echo "No .env found. Copying .env.example to .env..."
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if ! PYTHON_BIN="$(find_python)"; then
  echo "AI virtualenv was not found. Creating ai/.venv..."
  cd "$AI_DIR"
  python -m venv .venv
  PYTHON_BIN="$(find_python)"
fi

cd "$AI_DIR"

echo "Installing AI dependencies..."
"$PYTHON_BIN" -m pip install -r requirements.txt

HOST="${AI_HOST:-127.0.0.1}"
PORT="${AI_PORT:-8000}"

RELOAD_ARGS=()
if [[ "${AI_RELOAD:-0}" == "1" ]]; then
  RELOAD_ARGS=(--reload)
fi

echo "Starting AI service at http://$HOST:$PORT"
exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" "${RELOAD_ARGS[@]}"
