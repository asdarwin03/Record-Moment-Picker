#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_DIR="$ROOT_DIR/ai"

if [[ -f "$AI_DIR/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="$AI_DIR/.venv/Scripts/python.exe"
elif [[ -f "$AI_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$AI_DIR/.venv/bin/python"
else
  echo "AI virtualenv was not found. Run ./scripts/run-ai.sh once first." >&2
  exit 1
fi

cd "$AI_DIR"

echo "Running AI pipeline/schema tests..."
exec "$PYTHON_BIN" -m pytest app/tests
