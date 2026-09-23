from __future__ import annotations

from docx import Document


def apply_content_edit(docx_path: str, heading: str, instruction: str) -> dict:
    """Update a specific heading section in a DOCX based on a natural-language edit instruction."""
    doc = Document(docx_path)
    target_heading = heading.strip()
    before = ""
    after = ""
    found = False

    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == target_heading:
            found = True
            continue
        if found and paragraph.text.strip():
            before = paragraph.text
            replacement = instruction.strip() if instruction.strip() else before
            paragraph.text = replacement
            after = paragraph.text
            break

    if not found:
        raise ValueError(f"Heading '{target_heading}' not found in document.")

    doc.save(docx_path)
    return {
        "status": "updated",
        "heading": target_heading,
        "before": before or "",
        "after": after or replacement if 'replacement' in locals() else "",
        "message": f"Updated content under heading '{target_heading}'.",
    }
