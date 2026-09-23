from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.db import seed_mock_data
from mcp_server.tools.find_template import find_template
from mcp_server.tools.fetch_variables import fetch_variable_data
from mcp_server.tools.generate_document import generate_document
from mcp_server.tools.list_headings import list_headings
from mcp_server.tools.apply_edit import apply_content_edit

mcp = FastMCP("smartcomms_document_server")


@mcp.tool(name="find_template")
def find_template_tool(template_name: str, client_id: str) -> str:
    """Resolve a client/template document to the exact DOCX file path."""
    return find_template(template_name, client_id)


@mcp.tool(name="fetch_variable_data")
def fetch_variable_data_tool(template_name: str, client_id: str) -> dict:
    """Load the latest XML variable payload for a client/template pair."""
    return fetch_variable_data(template_name, client_id)


@mcp.tool(name="generate_document")
def generate_document_tool(docx_path: str, variables: dict) -> dict:
    """Fill placeholders in a DOCX document and save the working copy to the generated folder."""
    return generate_document(docx_path, variables)


@mcp.tool(name="list_headings")
def list_headings_tool(docx_path: str) -> list:
    """Read the document outline so Claude can target heading-based edits."""
    return list_headings(docx_path)


@mcp.tool(name="apply_content_edit")
def apply_content_edit_tool(docx_path: str, heading: str, instruction: str) -> dict:
    """Apply a heading-scoped content change to a working document using the raw instruction."""
    return apply_content_edit(docx_path, heading, instruction)


if __name__ == "__main__":
    seed_mock_data()
    # This is the MCP server process. The FastAPI app does NOT call Python tools directly;
    # it opens a real stdio-based ClientSession to this process and invokes the tools over MCP.
    mcp.run(transport="stdio")
