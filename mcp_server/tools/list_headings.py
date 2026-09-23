from __future__ import annotations

from docx import Document


def list_headings(docx_path: str) -> list:
    """List the document's section titles and parse a heading outline for the UI and edit orchestration."""
    doc = Document(docx_path)
    headings = []
    for idx, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if text and paragraph.style.name.startswith("Heading"):
            headings.append({"index": idx, "heading": text, "level": paragraph.style.name.replace("Heading ", "")})
    return headings
