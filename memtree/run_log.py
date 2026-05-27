"""Capture every agent step (model I/O, tool calls, code, observations) to JSONL.

Wires into smolagents' native `step_callbacks` so each memory step is appended
to a single JSONL file as soon as it finalises. One file per process run.

Usage:
    logger = RunLogger()                    # writes outputs/<timestamp>/run.jsonl
    agent = build_agent(..., run_logger=logger)
    logger.event("final_report", payload)   # for non-step artifacts
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def _to_jsonable(obj: Any) -> Any:
    """Best-effort JSON conversion for smolagents step objects."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    # Pydantic models (e.g. typed final answers, LabBrief)
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        try:
            return _to_jsonable(dump())
        except Exception:
            pass
    # dataclass-ish objects with __dict__ (Timing, TokenUsage, ChatMessage, ToolCall)
    if hasattr(obj, "__dict__"):
        return {k: _to_jsonable(v) for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, BaseException):
        return {"error_type": type(obj).__name__, "message": str(obj)}
    return repr(obj)


class RunLogger:
    """Append-only JSONL logger for one process-level run."""

    def __init__(self, root: str | Path = "outputs", run_id: str | None = None) -> None:
        run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = Path(root) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "run.jsonl"
        self._lock = threading.Lock()  # spawn_agents fans steps from threads
        self._counter = 0
        self.event(
            "run_start",
            {
                "run_id": run_id,
                "pid": os.getpid(),
                "model_id": os.environ.get("MEMTREE_MODEL_ID"),
                "api_base": os.environ.get("MEMTREE_API_BASE"),
            },
        )

    # ------------------------------------------------------------------
    # Low-level write
    # ------------------------------------------------------------------
    def _write(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._counter += 1
            record = {"seq": self._counter, "ts": time.time(), **record}
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def event(self, kind: str, payload: Any) -> None:
        """Log an arbitrary non-step event (run start/end, spawn dispatch, final report)."""
        self._write({"kind": "event", "event": kind, "payload": _to_jsonable(payload)})

    def step_callback(self, agent_label: str):
        """Return a callback compatible with smolagents' `step_callbacks`."""

        def _cb(memory_step: Any, agent: Any = None) -> None:
            self._write(
                {
                    "kind": "step",
                    "agent": agent_label,
                    "step_type": type(memory_step).__name__,
                    "data": _to_jsonable(memory_step),
                }
            )

        return _cb
