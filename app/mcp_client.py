from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT_DIR = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT_DIR / "mcp_server" / "server.py"


@asynccontextmanager
async def mcp_client_session():
    """Open a real MCP stdio session to the separate Python server process."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        cwd=str(ROOT_DIR),
        env={**os.environ, "PYTHONPATH": str(ROOT_DIR)},
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def anthropic_tool_schema(tool: Any) -> dict[str, Any]:
    """Convert an MCP tool object to the Anthropic tool-use schema expected by the API."""
    input_schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "name": tool.name,
        "description": getattr(tool, "description", "") or "",
        "input_schema": input_schema,
    }


def tool_result_to_text(result: Any) -> str:
    """Flatten a tool result into a human-readable string for the trace and Claude feedback loop."""
    try:
        content = getattr(result, "content", []) or []
    except Exception:
        return str(result)

    chunks: list[str] = []
    for item in content:
        if hasattr(item, "text"):
            chunks.append(str(item.text))
        elif isinstance(item, dict):
            if item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
            else:
                chunks.append(str(item))
        else:
            chunks.append(str(item))
    return "\n".join(chunks) if chunks else str(result)
