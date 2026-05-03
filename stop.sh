#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.naviable.pids"

usage() {
  cat <<'EOF'
Usage: ./stop.sh [OPTIONS]

Stops NaviAble project gracefully: frontend + backend + Docker services.

Flags:
  -h, --help         Show this help message
  -d, --docker-only  Stop only Docker containers
  -a, --all          Kill all processes forcefully (emergency mode)

EOF
}

DOCKER_ONLY=false
FORCE_KILL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -d|--docker-only)
      DOCKER_ONLY=true
      shift
      ;;
    -a|--all)
      FORCE_KILL=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

echo "🛑 Stopping NaviAble project..."

# Kill backend if PID file exists
if [[ -f "$PID_FILE" ]] && [[ ! "$DOCKER_ONLY" == "true" ]]; then
  BACKEND_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$BACKEND_PID" ]]; then
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Stopping backend (PID $BACKEND_PID)..."
      kill "$BACKEND_PID" 2>/dev/null || true
      # Wait for graceful shutdown
      for i in {1..10}; do
        if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
          echo "✅ Backend stopped gracefully"
          break
        fi
        if [[ $i -eq 10 ]]; then
          echo "⚠️  Backend did not stop gracefully, force killing..."
          kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
        sleep 0.5
      done
    fi
  fi
  rm -f "$PID_FILE"
fi

# Kill Flutter/frontend processes
if ! pgrep -f "flutter run" >/dev/null 2>&1; then
  # No flutter processes running
  :
else
  echo "Stopping frontend..."
  if [[ "$FORCE_KILL" == "true" ]]; then
    pkill -9 -f "flutter run" 2>/dev/null || true
    pkill -9 -f "flutter" 2>/dev/null || true
  else
    pkill -f "flutter run" 2>/dev/null || true
    # Give it a moment to shutdown
    sleep 1
    pkill -9 -f "flutter run" 2>/dev/null || true
  fi
  echo "✅ Frontend stopped"
fi

# Stop Docker services
echo "Stopping Docker containers..."
if docker-compose -f "$ROOT_DIR/docker-compose.yml" ps 2>/dev/null | grep -q "naviable"; then
  if docker-compose -f "$ROOT_DIR/docker-compose.yml" down >/dev/null 2>&1; then
    echo "✅ Docker containers stopped"
  else
    echo "⚠️  Failed to stop Docker containers gracefully"
    if [[ "$FORCE_KILL" == "true" ]]; then
      docker-compose -f "$ROOT_DIR/docker-compose.yml" kill >/dev/null 2>&1 || true
      echo "   Force killed Docker containers"
    fi
  fi
else
  echo "   No running Docker containers"
fi

# Additional cleanup: stop any remaining uvicorn processes from this project
if [[ "$FORCE_KILL" == "true" ]]; then
  echo "Force killing remaining processes..."
  pkill -9 -f "uvicorn app.main" 2>/dev/null || true
  pkill -9 -f "python3 -m uvicorn" 2>/dev/null || true
fi

echo ""
echo "✅ NaviAble project stopped"
echo ""
echo "To start again, run: ./run.sh"
