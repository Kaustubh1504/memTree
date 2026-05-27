"""Return the full body of a doc, or a single named markdown section."""
from __future__ import annotations

from smolagents import tool


@tool
def read_section(docs: dict, doc_id: str, section: str | None = None) -> str:
    """Read a document body, optionally restricted to one section.

    Args:
        docs: The pre-loaded `{doc_id: body}` dict from scope.
        doc_id: The document key (filename without .md, e.g. "alpha_methodology").
        section: Case-insensitive section heading to extract (without `##`). If
            None, return the full body.

    Returns:
        The requested text, or an explanatory string if the doc or section is
        not found.
    """
    if doc_id not in docs:
        return f"[doc_id {doc_id!r} not in corpus; known ids: {sorted(docs.keys())}]"
    body = docs[doc_id]
    if section is None:
        return body

    target = section.strip().lower()
    lines = body.splitlines()
    start: int | None = None
    end: int | None = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("## "):
            heading = line.lstrip("# ").strip().lower()
            if start is None and heading == target:
                start = i + 1
            elif start is not None:
                end = i
                break
    if start is None:
        return f"[section {section!r} not found in {doc_id}]"
    return "\n".join(lines[start : end if end is not None else len(lines)]).strip()
