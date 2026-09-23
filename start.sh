#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

python - <<'PY'
from mcp_server.db import seed_mock_data
seed_mock_data()
PY

SERVER_PID=""
APP_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ -n "$APP_PID" ]]; then
    kill "$APP_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

python mcp_server/server.py &
SERVER_PID=$!

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

echo ""
echo "MCP server is running in a separate stdio process."
echo "FastAPI demo UI: http://localhost:8000"
echo "Press Ctrl+C to stop both processes."
wait "$APP_PID"
