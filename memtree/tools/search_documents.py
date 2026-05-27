"""Keyword search across a pre-loaded markdown corpus."""
from __future__ import annotations

from smolagents import tool


@tool
def search_documents(docs: dict, query: str, max_hits: int = 5) -> list[dict]:
    """Search the document corpus by case-insensitive substring match.

    Args:
        docs: The pre-loaded `{doc_id: body}` dict from scope.
        query: Substring to match against document bodies. Case-insensitive.
        max_hits: Cap on the number of returned hits.

    Returns:
        A list of `{doc_id, snippet}` dicts. `snippet` is ~200 chars of context
        around the first match in that document. Doc IDs are the filenames
        without the .md extension (e.g. "alpha_methodology").
    """
    q = query.lower()
    hits: list[dict] = []
    for doc_id, body in docs.items():
        idx = body.lower().find(q)
        if idx < 0:
            continue
        start = max(0, idx - 80)
        end = min(len(body), idx + len(query) + 120)
        snippet = body[start:end].replace("\n", " ").strip()
        hits.append({"doc_id": doc_id, "snippet": snippet})
        if len(hits) >= max_hits:
            break
    return hits
