# MCP for SmartComms Document Automation

This project is a real Model Context Protocol (MCP) hackathon demo for SmartComms document automation. It intentionally runs as two separate processes:

- The MCP server in [mcp_server/server.py](mcp_server/server.py) exposes document tools using the official MCP SDK over stdio transport.
- The FastAPI app in [app/main.py](app/main.py) acts as the MCP client and uses a real `ClientSession` to call those tools over the protocol.

The core orchestration loop in [app/orchestrator.py](app/orchestrator.py) sends the tool schema to Claude, waits for a tool call, executes it via the real MCP session, and feeds the tool output back into the next Claude request. This is the key architectural distinction: the app is not importing Python functions directly and calling them; it is routing tool use through MCP.

## Stack

- Python + official `mcp` SDK
- FastAPI + Jinja2
- SQLite + SQLAlchemy
- python-docx
- Anthropic Claude API
- XML variable payloads stored on disk per template/client

## Project layout

- [mcp_server/server.py](mcp_server/server.py): MCP server entry point and tool registration
- [mcp_server/db.py](mcp_server/db.py): SQLite setup, seeding, and mock template metadata
- [mcp_server/tools](mcp_server/tools): tool implementations for template lookup, variable loading, generation, headings, and edits
- [app/mcp_client.py](app/mcp_client.py): real `ClientSession` wiring and Anthropic tool schema conversion
- [app/orchestrator.py](app/orchestrator.py): Claude + MCP orchestration loop and validation/error handling
- [app/main.py](app/main.py): FastAPI routes and web UI service
- [app/templates/index.html](app/templates/index.html): single-page frontend for generate/edit/finalize flow
- [start.sh](start.sh): auto-seeds data and starts both processes
- [templates](templates): mock template docs and XML variable files for multiple clients

## Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`
- Optional but recommended: `ANTHROPIC_API_KEY` in the environment for Claude-driven orchestration

## One-command startup

From the repo root:

```bash
chmod +x start.sh
./start.sh
```

This does:

1. Seed SQLite and mock docs/XML files if they are missing
2. Launch the MCP server in a separate process
3. Launch the FastAPI app on http://localhost:8000

## Manual two-terminal setup

Terminal 1 — MCP server:

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
python mcp_server/server.py
```

Terminal 2 — FastAPI app:

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
export ANTHROPIC_API_KEY="your_key_here"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open http://localhost:8000.

## Real MCP server/client boundary

The actual protocol boundary is between:

- [app/mcp_client.py](app/mcp_client.py): creates the stdio client, initializes the session, and calls `session.list_tools()` / `session.call_tool(...)`
- [mcp_server/server.py](mcp_server/server.py): registers tools with `@mcp.tool(...)` and starts the server with `mcp.run(transport="stdio")`

This means the FastAPI app is not directly importing the tool logic and calling it in-process. Instead, it opens a separate server process and uses a real MCP client session to invoke tools. A judge can verify this by reading the client session calls in [app/mcp_client.py](app/mcp_client.py) and the server startup in [mcp_server/server.py](mcp_server/server.py).

## Orchestration flow

The orchestrator in [app/orchestrator.py](app/orchestrator.py) performs this loop:

1. Opens a real MCP session to the server
2. Lists the server tools
3. Converts the tool schema to Anthropic tool format
4. Calls Claude with the tools attached
5. When Claude returns a tool call, invokes it with `session.call_tool(...)`
6. Feeds the tool output back into Claude until the workflow completes

The app also has explicit validation for missing template/client combinations and missing variable data, so the UI shows a clear error message instead of failing silently.

## Demo behavior

- Select a template and client ID
- Generate a document
- Claude decides the correct tool order, typically: `find_template` -> `fetch_variable_data` -> `generate_document` -> `list_headings`
- The trace panel reflects each tool call and result in real time
- Use the heading outline to submit an edit instruction
- Finalize and download the generated DOCX

## Error handling in the UI

The app includes graceful handling for bad inputs, such as:

- nonexistent template name
- client ID not mapped to that template
- missing XML variable file for the template/client pair
- invalid docx path or document finalization failure

When this happens, the backend returns a structured error and the frontend shows it in the output area and trace panel.

## Verifying MCP routing visually

A judge can confirm the architecture in the browser:

- The trace panel lists each tool call under the real tool name
- Each entry includes the MCP input and the raw tool result
- The backend code in [app/mcp_client.py](app/mcp_client.py) shows the actual `ClientSession` calls
- The server code in [mcp_server/server.py](mcp_server/server.py) shows the tool registration and stdio transport

## Seeded mock data

On first run, the project seeds:

- SQLite `client_template_map` rows for the sample clients
- Template folders under [templates](templates)
- XML variable files under each template's `variables` directory
- DOCX template files under each template's `docs` directory

The sample clients include the demo IDs such as `3227`, `4410`, and `9001`.

## Notes

- This project intentionally uses stdio transport to keep the local demo simple and reliable in a Codespace environment.
- Built-in guardrails ensure the client only calls tools the server exposes.
- The app supports both a real Claude-driven flow and a deterministic demo fallback when `ANTHROPIC_API_KEY` is not configured.
