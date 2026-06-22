#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_DIR="$ROOT_DIR/ai"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
ENV_FILE="$ROOT_DIR/.env"
VENV_DIR="$AI_DIR/.venv"
REQUIREMENTS="$AI_DIR/requirements.txt"
STAMP="$VENV_DIR/.requirements.sha256"
CHECK_ONLY=0
SKIP_INSTALL=0

for argument in "$@"; do
  case "$argument" in
    --check) CHECK_ONLY=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    *) echo "Unknown argument: $argument" >&2; exit 2 ;;
  esac
done

step() { printf '[RMP] %s\n' "$1"; }

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.example" "$ENV_FILE"
  step "Created .env from .env.example."
fi

set -a
# shellcheck disable=SC1090
source <(sed 's/\r$//' "$ENV_FILE")
set +a

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "$1 was not found. $2" >&2
    exit 1
  }
}

find_base_python() {
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

venv_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    printf '%s\n' "$VENV_DIR/bin/python"
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    printf '%s\n' "$VENV_DIR/Scripts/python.exe"
  else
    return 1
  fi
}

if PYTHON_BIN="$(venv_python 2>/dev/null)" &&
   "$PYTHON_BIN" -c 'import sys; assert sys.prefix != sys.base_prefix' >/dev/null 2>&1; then
  :
else
  [[ -d "$VENV_DIR" ]] && { step "Removing invalid or moved ai/.venv."; rm -rf "$VENV_DIR"; }
  BASE_PYTHON="$(find_base_python)" || {
    echo "Python 3.11 or newer was not found." >&2
    exit 1
  }
  step "Creating ai/.venv with $BASE_PYTHON."
  "$BASE_PYTHON" -m venv "$VENV_DIR"
  PYTHON_BIN="$(venv_python)"
fi

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

CURRENT_HASH="$(hash_file "$REQUIREMENTS")"
SAVED_HASH="$(cat "$STAMP" 2>/dev/null || true)"
if [[ "$SKIP_INSTALL" -eq 0 && "$CURRENT_HASH" != "$SAVED_HASH" ]]; then
  step "Installing AI dependencies."
  "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS"
  printf '%s' "$CURRENT_HASH" > "$STAMP"
fi

IFS=',' read -ra PROVIDERS <<< "${STT_PROVIDER_OPTIONS:-whisper}"
for provider in "${PROVIDERS[@]}"; do
  provider="$(printf '%s' "$provider" | xargs)"
  case "$provider" in
    whisper) module=whisper; package=openai-whisper ;;
    faster_whisper) module=faster_whisper; package=faster-whisper ;;
    whisperx) module=whisperx; package=whisperx ;;
    *) echo "Unsupported STT provider: $provider" >&2; exit 1 ;;
  esac
  if ! "$PYTHON_BIN" -c "import $module" >/dev/null 2>&1; then
    [[ "$SKIP_INSTALL" -eq 1 ]] && { echo "Python module $module is missing." >&2; exit 1; }
    step "Installing STT provider package $package."
    "$PYTHON_BIN" -m pip install "$package"
  fi
done

if [[ "$("$PYTHON_BIN" -c "import torch; print('1' if torch.cuda.is_available() else '0')")" == "1" ]]; then
  export STT_DEVICE_OPTIONS="cpu,cuda"
else
  export STT_DEVICE_OPTIONS="cpu"
  if [[ "${WHISPER_DEVICE:-cpu}" == "cuda" ]]; then
    echo "[RMP] CUDA is unavailable. Falling back to WHISPER_DEVICE=cpu and int8." >&2
    export WHISPER_DEVICE="cpu"
    export WHISPER_COMPUTE_TYPE="int8"
  fi
fi

require_command node "Install the current Node.js LTS release."
require_command npm "Install npm with Node.js."
require_command "${FFMPEG_BINARY:-ffmpeg}" "Install ffmpeg and add it to PATH."
require_command "${FFPROBE_BINARY:-ffprobe}" "Install ffprobe and add it to PATH."

for directory in "$BACKEND_DIR" "$FRONTEND_DIR"; do
  if [[ ! -d "$directory/node_modules" ]]; then
    [[ "$SKIP_INSTALL" -eq 1 ]] && { echo "$directory/node_modules is missing." >&2; exit 1; }
    step "Installing dependencies in $(basename "$directory")."
    (cd "$directory" && npm install)
  fi
done

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v ss >/dev/null 2>&1; then
    ss -ltn | grep -q ":$port "
  else
    netstat -an 2>/dev/null | grep -q "[.:]$port .*LISTEN"
  fi
}

AI_PORT="${AI_PORT:-8000}"
BACKEND_PORT="${BACKEND_PORT:-3000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
for pair in "AI:$AI_PORT" "Backend:$BACKEND_PORT" "Frontend:$FRONTEND_PORT"; do
  name="${pair%%:*}"
  port="${pair##*:}"
  port_in_use "$port" && { echo "$name port $port is already in use." >&2; exit 1; }
done

(cd "$AI_DIR" && "$PYTHON_BIN" -c 'import fastapi, uvicorn; import app.main')
step "Environment check completed."
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  printf 'AI:       http://127.0.0.1:%s\n' "$AI_PORT"
  printf 'Backend:  http://127.0.0.1:%s\n' "$BACKEND_PORT"
  printf 'Frontend: http://127.0.0.1:%s\n' "$FRONTEND_PORT"
  exit 0
fi

pids=()
cleanup() {
  step "Stopping all services."
  for pid in "${pids[@]:-}"; do
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$AI_DIR" && exec "$PYTHON_BIN" -m uvicorn app.main:app \
  --host "${AI_HOST:-127.0.0.1}" --port "$AI_PORT") &
pids+=("$!")
(cd "$BACKEND_DIR" && exec npm start) &
pids+=("$!")
(cd "$FRONTEND_DIR" && exec npm run dev -- \
  --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort) &
pids+=("$!")

printf '\nFrontend: http://127.0.0.1:%s\n' "$FRONTEND_PORT"
echo "Press Ctrl+C to stop all services."
while true; do
  for pid in "${pids[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "A service exited. Stopping the remaining services." >&2
      exit 1
    fi
  done
  sleep 1
done
