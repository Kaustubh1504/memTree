"""Tool-output cache + decorator for deterministic replay.

Sequential / tape design (per 2026-05-26 design decision):
- `ToolCache.entries` is an ordered list of `{tool, output}` records.
- In `record` mode, every wrapped tool call appends to that list.
- In `replay` mode, a cursor advances through the list. The Nth call returns
  the Nth recorded output, with a tool-name sanity check.

We persist the cache to `tool_outputs.json` (a file inside `WorkspaceRepo`).
JSON serialization uses `default=str` so non-trivial outputs (DB rows as tuples,
Pydantic objects, etc.) survive a round trip as best-effort strings — outputs
are only consumed by the kernel during replay, not by the model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from smolagents.tools import Tool


class ToolCache:
    """Append-only call log persisted to tool_outputs.json."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path: Path | None = Path(path) if path is not None else None
        self.entries: list[dict[str, Any]] = []
        self.mode: str = "record"  # "record" | "replay"
        self._cursor: int = 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load entries from `self.path` (or reset if it doesn't exist)."""
        if self.path is not None and self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        else:
            self.entries = []
        self._cursor = 0

    def save(self) -> None:
        if self.path is not None:
            self.path.write_text(
                json.dumps(self.entries, indent=2, default=str), encoding="utf-8"
            )

    def load_text(self, text: str) -> None:
        """Load entries from a raw JSON string (used by replay() reading git blobs)."""
        self.entries = json.loads(text or "[]")
        self._cursor = 0

    # ------------------------------------------------------------------
    # Record / replay
    # ------------------------------------------------------------------
    def record(self, tool_name: str, output: Any) -> None:
        self.entries.append({"tool": tool_name, "output": output})
        self.save()

    def next(self, tool_name: str) -> Any:
        if self._cursor >= len(self.entries):
            raise RuntimeError(
                f"Replay cache exhausted at call to {tool_name!r} "
                f"(have {len(self.entries)} entries)"
            )
        entry = self.entries[self._cursor]
        self._cursor += 1
        if entry["tool"] != tool_name:
            raise RuntimeError(
                f"Replay mismatch at index {self._cursor - 1}: "
                f"expected {tool_name!r}, cache has {entry['tool']!r}"
            )
        return entry["output"]


def attach_cache(tools: Sequence[Tool], cache: ToolCache) -> None:
    """In-place wrap each tool's `forward()` so calls flow through `cache`.

    Mutates the Tool objects. If a tool has already been wrapped, we don't
    re-wrap — we just swap the cache reference in its slot. That way replay
    can temporarily route calls through a different cache without producing
    nested wrappers (which would call the real function once *per* layer).
    """
    for t in tools:
        slot: dict[str, Any] | None = getattr(t, "_memtree_cache_slot", None)
        if slot is not None:
            slot["cache"] = cache
            continue

        original = t.forward
        tool_name = t.name
        slot = {"cache": cache}

        def make_wrapper(orig: Any, name: str, ref: dict[str, Any]) -> Any:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                c: ToolCache = ref["cache"]
                if c.mode == "replay":
                    return c.next(name)
                out = orig(*args, **kwargs)
                c.record(name, out)
                return out

            return wrapper

        t.forward = make_wrapper(original, tool_name, slot)
        t._memtree_cache_slot = slot  # type: ignore[attr-defined]


def current_cache(tool: Tool) -> ToolCache | None:
    """Return the cache currently attached to a tool, or None."""
    slot = getattr(tool, "_memtree_cache_slot", None)
    return slot["cache"] if slot is not None else None
