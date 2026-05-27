"""Append a labelled finding to the agent's running `findings` list."""
from __future__ import annotations

from smolagents import tool


@tool
def save_finding(findings: list, label: str, content: str) -> int:
    """Append a finding to the in-scope `findings` list and return its index.

    Args:
        findings: The pre-loaded list from scope. Mutated in place.
        label: A short category tag, e.g. "theme", "disagreement", "inconsistency".
        content: The finding text.

    Returns:
        The index of the newly appended finding (== len(findings) - 1 after append).
    """
    findings.append({"label": label, "content": content})
    return len(findings) - 1
