"""Auto-derive a JSON summary of the agent's kernel state.

After each turn, MemTreeAgent calls `write_state_summary(executor.state, path)`
to refresh `workspace/state_summary.json`. The dashboard reads this file to
populate the kernel-state panel — no inter-process channel needed.

We filter out:
- Dunders (`__name__`, etc.)
- Anything that looks like a Tool object (has both `.name` and `.forward`)
- Callables (the agent's tools end up in state as bound forwards)
- The replay no-op `final_answer`

The remainder is what the human cares about: docs, conn, findings, briefs,
plus anything the agent created.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_MAX_REPR = 240


def _length(value: Any) -> int | None:
    """Return len(value) if it has a sane __len__, else None."""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return None


def _short_repr(value: Any) -> str:
    """Best-effort short repr without exploding on huge objects."""
    try:
        r = repr(value)
    except Exception as e:
        return f"<unrepr-able: {type(e).__name__}>"
    return r if len(r) <= _MAX_REPR else r[: _MAX_REPR - 1] + "…"


def _should_skip(name: str, value: Any) -> bool:
    if name.startswith("_") or name == "final_answer":
        return True
    if callable(value):
        return True
    # smolagents Tool objects expose .name and .forward — skip them too.
    if hasattr(value, "name") and hasattr(value, "forward"):
        return True
    return False


def summarise_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Project executor.state into a list of variable summaries."""
    out: list[dict[str, Any]] = []
    for name, value in sorted(state.items()):
        if _should_skip(name, value):
            continue
        out.append(
            {
                "name": name,
                "type": type(value).__name__,
                "length": _length(value),
                "repr": _short_repr(value),
            }
        )
    return out


def write_state_summary(state: dict[str, Any], path: str | Path, turn: int) -> None:
    """Write a JSON summary of the kernel state to `path` (atomic-ish)."""
    payload = {"turn": turn, "variables": summarise_state(state)}
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
