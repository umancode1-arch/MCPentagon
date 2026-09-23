# MCP for SmartComms Document Automation

This project is a hackathon demo that uses a real Model Context Protocol (MCP) architecture for document automation. It has two separate processes:

- The MCP server in [mcp_server/server.py](mcp_server/server.py) exposes document tools over the official MCP stdio transport.
- The FastAPI app in [app/main.py](app/main.py) acts as the MCP client and uses a real `ClientSession` to talk to that server.

The orchestration loop in [app/orchestrator.py](app/orchestrator.py) sends the tool schema to Anthropic Claude, lets Claude choose which MCP tool to call, and then feeds the tool result back into the next Claude request. This is the critical architecture distinction: the app is not calling Python functions directly; it is using the MCP client protocol to route requests to the server.

## Stack

- Python + official `mcp` SDK
- FastAPI + Jinja2 + SQLite + SQLAlchemy
- python-docx for DOCX generation and edits
- Anthropic Claude API for tool selection and orchestration
- XML variable payloads on disk for template data

## Project layout

- [mcp_server/server.py](mcp_server/server.py): MCP server entry point
- [mcp_server/db.py](mcp_server/db.py): SQLite schema and mock data seeding
- [mcp_server/tools](mcp_server/tools): tool implementations for template lookup, variable loading, document generation, heading lists, and content edits
- [app/mcp_client.py](app/mcp_client.py): actual `ClientSession` setup and tool schema conversion
- [app/orchestrator.py](app/orchestrator.py): Claude + MCP tool loop
- [app/main.py](app/main.py): FastAPI routes and UI service
- [app/templates/index.html](app/templates/index.html): single-page UI
- [start.sh](start.sh): startup helper for creating mock data and launching both processes

## Prerequisites

- Python 3.11+
- Anthropic API key in the environment as `ANTHROPIC_API_KEY`
- `pip install -r requirements.txt`

## One-command startup

From the repo root:

```bash
chmod +x start.sh
./start.sh
```

This will:

1. Seed SQLite and templates on first run
2. Start the dedicated MCP server process in the background
3. Start the FastAPI app on http://localhost:8000

## Manual two-terminal setup

Terminal 1 (MCP server):

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
python mcp_server/server.py
```

Terminal 2 (FastAPI app):

```bash
cd /workspaces/MCPentagon
export PYTHONPATH="$PWD"
export ANTHROPIC_API_KEY="your_key_here"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open http://localhost:8000.

## Where the MCP boundary lives

The real boundary is between:

- [app/mcp_client.py](app/mcp_client.py): this creates the stdio-enabled `ClientSession` and calls `await session.initialize()` and `await session.call_tool(...)`.
- [mcp_server/server.py](mcp_server/server.py): this exposes the tools with `@mcp.tool(...)` and runs on stdio via `mcp.run(transport="stdio")`.

That means the FastAPI app is not importing the tool functions directly. Instead, it opens a separate process for the server and invokes tools over the MCP protocol. A judge can confirm this by reading the `ClientSession` calls in [app/mcp_client.py](app/mcp_client.py) and the `mcp.run(transport="stdio")` call in [mcp_server/server.py](mcp_server/server.py).

## How the tool loop works

The orchestrator in [app/orchestrator.py](app/orchestrator.py) does this:

1. Opens a real MCP client session to the server
2. Lists tools via `session.list_tools()`
3. Converts the MCP tool schema to Anthropic tool format
4. Calls Claude with those tools attached
5. When Claude emits a `tool_use` block, executes it with `session.call_tool(...)`
6. Feeds the result back to Claude and repeats until the task is complete

This is the actual MCP-aware architecture that matches the requested demo design.

## Demo flow

- Generate from a template + client ID
- Claude chooses the tool sequence: `find_template` -> `fetch_variable_data` -> `generate_document` -> `list_headings`
- The UI displays the trace in the “Live MCP Trace” panel
- The user can submit heading-level edit instructions, which Claude routes to `apply_content_edit`
- Finalize to download the `.docx` output

## Verifying the MCP routing in the UI

A judge can verify this visually in the browser:

- The trace panel shows each tool call as it happens, labeled with the actual MCP tool name
- Each entry includes the tool input and returned text result
- The orchestrator calls the tool via `ClientSession.call_tool(...)`, not by direct Python imports

## Seeded mock data

On first run, the project seeds:

- SQLite entries in `client_template_map`
- Template folders under [templates](templates)
- XML variable payloads under each template's `variables` directory
- DOCX files under each template's `docs` directory

## Notes

- The project intentionally keeps the MCP server and app as separate processes for a real demo architecture.
- Because this is a Codespace hackathon setup, stdio transport is used for simplicity and reliability.
- Built-in guardrails ensure the client only calls the tools the server exposes.
