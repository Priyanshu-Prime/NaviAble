#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FLUTTER_DEVICE="${FLUTTER_DEVICE:-chrome}"
FLUTTER_WEB_HOST="${FLUTTER_WEB_HOST:-127.0.0.1}"
FLUTTER_WEB_PORT="${FLUTTER_WEB_PORT:-5173}"
NAVIABLE_DEMO_MODE="${NAVIABLE_DEMO_MODE:-false}"
ENABLE_HYBRID_CLIP="${ENABLE_HYBRID_CLIP:-false}"
API_BASE_URL="${API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
SKIP_PIP_INSTALL="${SKIP_PIP_INSTALL:-false}"
YOLO_V10_MODEL="${YOLO_V10_MODEL:-./YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt}"

BACKEND_PID=""

usage() {
  cat <<'EOF'
Usage: ./run.sh

Starts NaviAble backend + Flutter frontend in one go.

Optional environment variables:
  BACKEND_HOST      (default: 127.0.0.1)
  BACKEND_PORT      (default: 8000)
  FLUTTER_DEVICE    (default: chrome)
  FLUTTER_WEB_HOST  (default: 127.0.0.1)
  FLUTTER_WEB_PORT  (default: 5173)
  NAVIABLE_DEMO_MODE(default: true)
  ENABLE_HYBRID_CLIP(default: false)
  API_BASE_URL      (default: http://BACKEND_HOST:BACKEND_PORT)
  SKIP_PIP_INSTALL  (default: false)
  YOLO_V10_MODEL    (default: ./YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' is required but not found in PATH."
    exit 1
  fi
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

require_cmd python3
require_cmd flutter

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Error: backend directory not found at $BACKEND_DIR"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "Error: frontend directory not found at $FRONTEND_DIR"
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/requirements.txt" ]]; then
  echo "Error: backend requirements file missing at $BACKEND_DIR/requirements.txt"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python3 -m pip install --upgrade pip
if [[ "$SKIP_PIP_INSTALL" != "true" ]]; then
  python3 -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

echo "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT} (DEMO_MODE=${NAVIABLE_DEMO_MODE})"
echo "Using YOLOv10 model from: ${YOLO_V10_MODEL}"
pushd "$BACKEND_DIR" >/dev/null
NAVIABLE_DEMO_MODE="$NAVIABLE_DEMO_MODE" ENABLE_HYBRID_CLIP="$ENABLE_HYBRID_CLIP" YOLO_V10_MODEL="$YOLO_V10_MODEL" python3 -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!
popd >/dev/null

if command -v curl >/dev/null 2>&1; then
  echo "Waiting for backend health endpoint..."
  BACKEND_READY=false
  for _ in {1..60}; do
    if curl -fsS "$API_BASE_URL/health" >/dev/null 2>&1; then
      BACKEND_READY=true
      break
    fi
    if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      echo "Error: backend exited before becoming ready."
      exit 1
    fi
    sleep 1
  done
  if [[ "$BACKEND_READY" != "true" ]]; then
    echo "Error: backend did not become healthy within 60 seconds."
    exit 1
  fi
else
  echo "Warning: curl not found; skipping backend health wait."
fi

echo "Running frontend on device '$FLUTTER_DEVICE' with API_BASE_URL=$API_BASE_URL"
pushd "$FRONTEND_DIR" >/dev/null
flutter pub get
set +e
flutter run -d "$FLUTTER_DEVICE" --web-hostname "$FLUTTER_WEB_HOST" --web-port "$FLUTTER_WEB_PORT" --dart-define=API_BASE_URL="$API_BASE_URL"
FRONTEND_EXIT=$?
set -e
popd >/dev/null

exit "$FRONTEND_EXIT"

