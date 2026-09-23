# Start the project manually (without start.sh)

This project is designed to run as two separate processes:

1. The MCP server process
2. The FastAPI app process

The server and app are intentionally separate so the app uses a real MCP client session to talk to the server via stdio transport.

## 1) Seed the mock data (optional but recommended)

Run this once before starting the app:

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
python - <<'PY'
from mcp_server.db import seed_mock_data
seed_mock_data()
print("Seeded mock data.")
PY
```

This creates the SQLite database, template files, variable XML files, and generated output folder if they do not already exist.

## 2) Start the MCP server in Terminal 1

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
python mcp_server/server.py
```

Keep this terminal open while the app is running.

## 3) Start the FastAPI app in Terminal 2

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
export ANTHROPIC_API_KEY="your_key_here"   # optional but needed for Claude-driven orchestration
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

```text
http://localhost:8000
```

## 4) Optional: run without Anthropic API

If you do not set `ANTHROPIC_API_KEY`, the app still works in demo mode using the real MCP tool chain without Claude, but the orchestration is limited to the fallback behavior.

## 5) Stop the app

Press `Ctrl+C` in both terminals.

## Important note

This project is intentionally split into two separate processes:

- MCP server: [mcp_server/server.py](mcp_server/server.py)
- FastAPI client: [app/main.py](app/main.py)

This is the real MCP architecture.
