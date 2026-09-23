from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from mcp_server.db import BASE_DIR


def _get_latest_xml(base_dir: Path, template_name: str, client_id: str) -> Path:
    matches = sorted(base_dir.glob(f"client_{client_id}_{template_name}_v*.xml"))
    if not matches:
        # Also accept legacy naming if the files are ever generated with the older prefix form.
        matches = sorted(base_dir.glob(f"{client_id}_{template_name}_v*.xml"))
    if not matches:
        raise FileNotFoundError(f"No variable XML found for client {client_id} and template {template_name}")
    return matches[-1]


def fetch_variable_data(template_name: str, client_id: str) -> dict:
    """Scan the template variable directory and return the newest XML payload as a dict."""
    var_dir = BASE_DIR / "templates" / template_name / "variables"
    xml_path = _get_latest_xml(var_dir, template_name, client_id)
    root = ET.parse(xml_path).getroot()
    data = {}
    for field in root.findall("field"):
        name = field.get("name")
        if name:
            data[name] = field.text or ""
    return data
