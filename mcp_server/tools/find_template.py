from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from mcp_server.db import BASE_DIR, ClientTemplateMap, engine


def find_template(template_name: str, client_id: str) -> str:
    """Resolve the DOCX file path for a template and client from the SQLite map."""
    with engine.connect() as connection:
        row = connection.execute(
            select(ClientTemplateMap.docx_filename).where(
                ClientTemplateMap.template_name == template_name,
                ClientTemplateMap.client_id == client_id,
            )
        ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"No template mapping for client_id={client_id!r}, template_name={template_name!r}")
    doc_path = (BASE_DIR / "templates" / template_name / "docs" / row).resolve()
    return str(doc_path)
