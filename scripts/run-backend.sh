#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  echo "No .env found. Copying .env.example to .env..."
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

cd "$BACKEND_DIR"

if [[ ! -d node_modules ]]; then
  echo "Installing backend dependencies..."
  npm install
fi

PORT="${BACKEND_PORT:-3000}"
echo "Starting backend at http://localhost:$PORT"
exec npm start
