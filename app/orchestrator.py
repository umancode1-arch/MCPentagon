from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from app.mcp_client import anthropic_tool_schema, mcp_client_session, tool_result_to_text

CLAUDE_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def _has_valid_anthropic_key() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY")
    return bool(key and key.strip() and key.strip() != "test")


def _tool_name_list(tools: list[Any]) -> str:
    return ", ".join(tool.name for tool in tools)


def _parse_tool_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        text = payload.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return payload
    return payload


def _extract_tool_error(result: Any) -> str | None:
    text = tool_result_to_text(result)
    if "Error executing tool" in text:
        return text.split("Error executing tool", 1)[1].strip().strip(": ")
    return None


async def generate_document_flow(template_name: str, client_id: str) -> dict[str, Any]:
    """Use Claude + live MCP tools to find data, generate a document, and return the trace + file metadata.

    If no valid Anthropic API key is configured, the app falls back to a deterministic MCP sequence so the
    demo still runs in a sealed/air-gapped environment while keeping the actual MCP tool routing intact.
    """
    trace: list[dict[str, Any]] = []

    try:
        async with mcp_client_session() as session:
            tool_list = (await session.list_tools()).tools
            anthropic_tools = [anthropic_tool_schema(tool) for tool in tool_list]
            allowed_names = {tool.name for tool in tool_list}

            if not _has_valid_anthropic_key():
                # Demo-mode fallback: still uses the real MCP server over ClientSession, just without Claude.
                find_result = await session.call_tool("find_template", {"template_name": template_name, "client_id": client_id})
                find_text = tool_result_to_text(find_result)
                trace.append({"tool_name": "find_template", "input": {"template_name": template_name, "client_id": client_id}, "output": find_text})
                error_text = _extract_tool_error(find_result)
                if error_text:
                    return {"status": "error", "message": error_text, "trace": trace}

                docx_path = _parse_tool_payload(find_text)
                if not isinstance(docx_path, str) or not docx_path:
                    return {"status": "error", "message": "Template could not be resolved for the requested client.", "trace": trace}

                variables_result = await session.call_tool("fetch_variable_data", {"template_name": template_name, "client_id": client_id})
                variables_text = tool_result_to_text(variables_result)
                trace.append({"tool_name": "fetch_variable_data", "input": {"template_name": template_name, "client_id": client_id}, "output": variables_text})
                error_text = _extract_tool_error(variables_result)
                if error_text:
                    return {"status": "error", "message": error_text, "trace": trace}

                variables = _parse_tool_payload(variables_text)
                if not isinstance(variables, dict):
                    return {"status": "error", "message": "No variable data is available for the requested template/client pair.", "trace": trace}

                generation = await session.call_tool("generate_document", {"docx_path": docx_path, "variables": variables})
                generation_text = tool_result_to_text(generation)
                trace.append({"tool_name": "generate_document", "input": {"docx_path": docx_path, "variables": variables}, "output": generation_text})
                if "Error executing tool" in generation_text:
                    return {"status": "error", "message": generation_text.replace("Error executing tool generate_document: ", "").strip(), "trace": trace}

                payload = _parse_tool_payload(generation_text)
                if not isinstance(payload, dict) or "path" not in payload:
                    return {"status": "error", "message": "The document generator returned an invalid response.", "trace": trace}

                headings = await session.call_tool("list_headings", {"docx_path": payload.get("path", docx_path)})
                headings_text = tool_result_to_text(headings)
                trace.append({"tool_name": "list_headings", "input": {"docx_path": payload.get("path", docx_path)}, "output": headings_text})
                if "Error executing tool" in headings_text:
                    return {"status": "error", "message": headings_text.replace("Error executing tool list_headings: ", "").strip(), "trace": trace}

                return {
                    "status": "completed",
                    "final_text": "Document generated using the MCP tool sequence in demo mode.",
                    "trace": trace,
                    "docx_path": payload.get("path") if isinstance(payload, dict) else None,
                }

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            messages = [
                {
                    "role": "user",
                    "content": (
                        f"User wants to generate a {template_name} document for client {client_id}. "
                        f"Use the available MCP tools in the right order. Available tools: {_tool_name_list(tool_list)}. "
                        "First locate the template and variable data, then generate the document. "
                        "After that, call list_headings on the generated file so the UI can show the outline. "
                        "Keep the tool use sequence explicit and do not skip the necessary steps."
                    ),
                }
            ]

            for _ in range(12):
                response = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=4096,
                    system=(
                        "You are an orchestrator using MCP tools to automate document generation. "
                        "Use real tool calls and wait for their results before continuing. "
                        "Do not invent file paths or variable values. "
                        "If the task is complete, respond with a concise summary and the resulting file path."
                    ),
                    tools=anthropic_tools,
                    messages=messages,
                )

                tool_calls = [item for item in response.content if getattr(item, "type", None) == "tool_use"]
                if not tool_calls:
                    final_text = "\n".join(
                        item.text for item in response.content if getattr(item, "type", None) == "text"
                    )
                    generated_path = None
                    for entry in reversed(trace):
                        payload = _parse_tool_payload(entry["output"])
                        if isinstance(payload, dict) and "path" in payload:
                            generated_path = payload["path"]
                            break
                    return {
                        "status": "completed",
                        "final_text": final_text,
                        "trace": trace,
                        "docx_path": generated_path,
                    }

                for tool_call in tool_calls:
                    if tool_call.name not in allowed_names:
                        raise ValueError(f"Claude attempted to call disallowed tool: {tool_call.name}")
                    result = await session.call_tool(tool_call.name, tool_call.input)
                    result_text = tool_result_to_text(result)
                    trace.append({
                        "tool_name": tool_call.name,
                        "input": tool_call.input,
                        "output": result_text,
                    })

                    if "Error executing tool" in result_text:
                        error_message = result_text.replace("Error executing tool", "").strip().strip(": ")
                        return {"status": "error", "message": error_message, "trace": trace}

                    messages.append({
                        "role": "assistant",
                        "content": [{
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.input,
                        }],
                    })
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": result_text,
                            "is_error": False,
                        }],
                    })

            raise RuntimeError("Claude did not complete the workflow in the expected number of steps.")
    except Exception as exc:
        message = str(exc)
        if not message.strip():
            message = "Could not generate the document because the requested template or client was not found."
        return {"status": "error", "message": message, "trace": trace}


async def apply_edit_flow(docx_path: str, instruction: str) -> dict[str, Any]:
    """Ask Claude to choose the edit target and call the MCP edit tool on the generated document."""
    trace: list[dict[str, Any]] = []

    try:
        async with mcp_client_session() as session:
            tool_list = (await session.list_tools()).tools
            anthropic_tools = [anthropic_tool_schema(tool) for tool in tool_list]
            allowed_names = {tool.name for tool in tool_list}

            document_outline = await session.call_tool("list_headings", {"docx_path": docx_path})
            outline_text = tool_result_to_text(document_outline)

            if not _has_valid_anthropic_key():
                heading = "How Fees Work"
                result = await session.call_tool("apply_content_edit", {"docx_path": docx_path, "heading": heading, "instruction": instruction})
                trace.append({"tool_name": "apply_content_edit", "input": {"docx_path": docx_path, "heading": heading, "instruction": instruction}, "output": tool_result_to_text(result)})
                return {"status": "completed", "trace": trace, "result": trace[-1]["output"] if trace else ""}

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            messages = [{
                "role": "user",
                "content": (
                    f"The user wants this document edited: '{instruction}'. "
                    f"Use the tool(s) available to interpret the request in the context of the document outline and update the right heading. "
                    f"Document outline: {outline_text}. "
                    f"Available MCP tools: {_tool_name_list(tool_list)}."
                ),
            }]

            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                tools=anthropic_tools,
                messages=messages,
            )

            tool_calls = [item for item in response.content if getattr(item, "type", None) == "tool_use"]
            if not tool_calls:
                return {"status": "completed", "final_text": "No tool call required.", "trace": trace}

            for tool_call in tool_calls:
                if tool_call.name not in allowed_names:
                    raise ValueError(f"Claude attempted to call disallowed tool: {tool_call.name}")
                result = await session.call_tool(tool_call.name, tool_call.input)
                trace.append({
                    "tool_name": tool_call.name,
                    "input": tool_call.input,
                    "output": tool_result_to_text(result),
                })
                messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": tool_call.id, "name": tool_call.name, "input": tool_call.input}]})
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": tool_result_to_text(result), "is_error": False}]})

            return {"status": "completed", "trace": trace, "result": trace[-1]["output"] if trace else ""}
    except Exception as exc:
        message = str(exc)
        if not message.strip():
            message = "Could not apply the requested edit because the document could not be opened or the heading was not found."
        return {"status": "error", "message": message, "trace": trace}


async def finalize_document(docx_path: str) -> dict[str, Any]:
    """Validate the generated file and return a downloadable output payload."""
    try:
        async with mcp_client_session() as session:
            heading_result = await session.call_tool("list_headings", {"docx_path": docx_path})
            heading_text = tool_result_to_text(heading_result)
            headings = _parse_tool_payload(heading_text)
            return {
                "status": "finalized",
                "docx_path": docx_path,
                "headings": headings,
                "download_url": f"/download?path={docx_path}",
            }
    except Exception as exc:
        return {"status": "error", "message": f"Document could not be finalized: {exc}", "docx_path": docx_path}
