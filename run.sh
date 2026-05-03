#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"
PID_FILE="$ROOT_DIR/.naviable.pids"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FLUTTER_DEVICE="${FLUTTER_DEVICE:-}"
FLUTTER_WEB_HOST="${FLUTTER_WEB_HOST:-127.0.0.1}"
FLUTTER_WEB_PORT="${FLUTTER_WEB_PORT:-5173}"
NAVIABLE_DEMO_MODE="${NAVIABLE_DEMO_MODE:-false}"
ENABLE_HYBRID_CLIP="${ENABLE_HYBRID_CLIP:-false}"
# Default API URL varies by device: android uses 10.0.2.2, others use localhost
API_BASE_URL="${API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
SKIP_PIP_INSTALL="${SKIP_PIP_INSTALL:-false}"
YOLO_V10_MODEL="${YOLO_V10_MODEL:-./YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt}"
SKIP_DOCKER="${SKIP_DOCKER:-false}"
SKIP_FRONTEND="${SKIP_FRONTEND:-false}"

BACKEND_PID=""
DOCKER_STARTED=false

usage() {
  cat <<'EOF'
Usage: ./run.sh [OPTIONS]

Starts NaviAble project: database (Docker) + backend + frontend.

Optional environment variables:
  BACKEND_HOST       (default: 127.0.0.1)
  BACKEND_PORT       (default: 8000)
  FLUTTER_DEVICE     (default: chrome)
  FLUTTER_WEB_HOST   (default: 127.0.0.1)
  FLUTTER_WEB_PORT   (default: 5173)
  NAVIABLE_DEMO_MODE (default: false)
  ENABLE_HYBRID_CLIP (default: false)
  API_BASE_URL       (default: http://BACKEND_HOST:BACKEND_PORT)
  SKIP_PIP_INSTALL   (default: false)
  YOLO_V10_MODEL     (default: ./YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt)
  SKIP_DOCKER        (default: false) - skip starting database
  SKIP_FRONTEND      (default: false) - skip starting frontend

Flags:
  -h, --help    Show this help message
  -b, --backend-only Run only the backend (skip frontend)
  -d, --docker-only  Start only Docker containers

EOF
}

BACKEND_ONLY=false
DOCKER_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -b|--backend-only)
      BACKEND_ONLY=true
      SKIP_FRONTEND=true
      shift
      ;;
    -d|--docker-only)
      DOCKER_ONLY=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Error: '$cmd' is required but not found in PATH."
    exit 1
  fi
}

cleanup() {
  local exit_code=$?

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ "$DOCKER_STARTED" == "true" ]]; then
    echo "Stopping Docker containers..."
    docker-compose -f "$ROOT_DIR/docker-compose.yml" down >/dev/null 2>&1 || true
  fi

  rm -f "$PID_FILE"
  exit $exit_code
}

trap cleanup EXIT INT TERM

echo "🚀 Starting NaviAble project..."

if [[ "$SKIP_DOCKER" != "true" ]]; then
  echo ""
  echo "📦 Starting Docker services (PostgreSQL + PostGIS)..."
  require_cmd docker
  require_cmd docker-compose

  if ! docker-compose -f "$ROOT_DIR/docker-compose.yml" up -d >/dev/null 2>&1; then
    echo "❌ Failed to start Docker services"
    exit 1
  fi
  DOCKER_STARTED=true

  echo "⏳ Waiting for database to be ready..."
  for i in {1..30}; do
    if docker-compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgis pg_isready -U naviable -d naviable >/dev/null 2>&1; then
      echo "✅ Database is ready"
      break
    fi
    if [[ $i -eq 30 ]]; then
      echo "❌ Database did not become ready within 30 seconds"
      exit 1
    fi
    sleep 1
  done
fi

if [[ "$DOCKER_ONLY" == "true" ]]; then
  echo "✅ Docker containers started. Containers are running."
  echo "Press Ctrl+C to stop."
  sleep infinity
fi

require_cmd python3
require_cmd flutter

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "❌ Error: backend directory not found at $BACKEND_DIR"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" && "$SKIP_FRONTEND" != "true" ]]; then
  echo "❌ Error: frontend directory not found at $FRONTEND_DIR"
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/requirements.txt" ]]; then
  echo "❌ Error: backend requirements file missing at $BACKEND_DIR/requirements.txt"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "📝 Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ""
echo "📥 Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null 2>&1
if [[ "$SKIP_PIP_INSTALL" != "true" ]]; then
  python3 -m pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null 2>&1
fi

echo ""
echo "🔧 Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
echo "   DEMO_MODE=${NAVIABLE_DEMO_MODE}"
echo "   YOLO_MODEL=${YOLO_V10_MODEL}"

# Kill any existing process on the backend port
if command -v lsof >/dev/null 2>&1; then
  lsof -ti:$BACKEND_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  sleep 1
fi

pushd "$BACKEND_DIR" >/dev/null
NAVIABLE_DEMO_MODE="$NAVIABLE_DEMO_MODE" ENABLE_HYBRID_CLIP="$ENABLE_HYBRID_CLIP" YOLO_V10_MODEL="$YOLO_V10_MODEL" python3 -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_FILE"
popd >/dev/null

if command -v curl >/dev/null 2>&1; then
  echo "⏳ Waiting for backend to be ready..."
  BACKEND_READY=false
  for i in {1..60}; do
    if curl -fsS "$API_BASE_URL/health" >/dev/null 2>&1; then
      BACKEND_READY=true
      echo "✅ Backend is ready"
      break
    fi
    if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      echo "❌ Backend exited unexpectedly. Check logs."
      exit 1
    fi
    sleep 1
  done
  if [[ "$BACKEND_READY" != "true" ]]; then
    echo "❌ Backend did not become healthy within 60 seconds"
    exit 1
  fi
else
  echo "⚠️  curl not found; skipping backend health check"
  sleep 3
fi

if [[ "$SKIP_FRONTEND" == "true" ]] || [[ "$BACKEND_ONLY" == "true" ]]; then
  echo ""
  echo "✅ Backend is running on $API_BASE_URL"
  echo "🛑 To stop all services, run: ./stop.sh"
  echo ""
  # Keep running
  wait
else
  echo ""
  echo "🎨 Starting frontend..."

  # If no device specified, show options
  if [[ -z "$FLUTTER_DEVICE" ]]; then
    echo ""
    echo "Available devices:"
    flutter devices 2>/dev/null | grep -v "^$" | tail -n +2 || echo "  • chrome (Web browser)"
    echo ""
    echo "Choose a device (or press Ctrl+C to exit):"
    echo "  1) chrome (Web browser - recommended)"
    echo "  2) android-emulator (Android Emulator)"
    echo "  3) ios-simulator (iOS Simulator)"
    echo ""
    read -p "Enter choice (default: 1): " device_choice
    case "$device_choice" in
      1|"") FLUTTER_DEVICE="chrome" ;;
      2) FLUTTER_DEVICE="android-emulator" ;;
      3) FLUTTER_DEVICE="ios-simulator" ;;
      *)
        read -p "Enter device ID: " FLUTTER_DEVICE
        if [[ -z "$FLUTTER_DEVICE" ]]; then
          FLUTTER_DEVICE="chrome"
        fi
        ;;
    esac
  fi

  echo "Using device: $FLUTTER_DEVICE"
  pushd "$FRONTEND_DIR" >/dev/null
  flutter pub get >/dev/null 2>&1 || true
  set +e
  if [[ "$FLUTTER_DEVICE" == "chrome" ]]; then
    flutter run -d "$FLUTTER_DEVICE" --web-hostname "$FLUTTER_WEB_HOST" --web-port "$FLUTTER_WEB_PORT" --dart-define=API_BASE_URL="$API_BASE_URL"
  else
    flutter run -d "$FLUTTER_DEVICE" --dart-define=API_BASE_URL="$API_BASE_URL"
  fi
  FRONTEND_EXIT=$?
  set -e
  popd >/dev/null
  exit "$FRONTEND_EXIT"
fi
