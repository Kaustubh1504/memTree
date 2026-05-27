"""`spawn_agent()` — fan out sub-agents that share scope and return typed results.

The MemEx paper shows `await asyncio.gather(spawn_agent(...))` inside the agent's
code. smolagents' executor doesn't support top-level `await` cleanly, so Phase 1
exposes a *synchronous* `spawn_agent`. Parallelism is recovered by `spawn_agents`,
which fans a list of tasks through a `ThreadPoolExecutor`. From the caller's code:

    reports = spawn_agents(
        [{"task": f"Analyse {r}", "scope": {"region": r}} for r in regions],
        return_type=RegionReport,
        tools=[search_web],
    )

Known divergence from MemEx: callers express parallelism as a list call rather
than `asyncio.gather`. Documented in CLAUDE.md.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Sequence, Type

from pydantic import BaseModel
from smolagents.tools import Tool

from memtree.kernel import build_agent


def spawn_agent(
    task: str,
    scope: dict[str, Any] | None = None,
    return_type: Type[BaseModel] | None = None,
    tools: Sequence[Tool] | None = None,
    model: Any | None = None,
    max_steps: int | None = None,
    additional_authorized_imports: list[str] | None = None,
) -> Any:
    """Spin up a sub-CodeAgent, inject scope, run synchronously, return its typed result."""
    sub = build_agent(
        tools=list(tools or []),
        model=model,
        final_answer_type=return_type,
        scope=scope,
        additional_authorized_imports=additional_authorized_imports,
    )
    run_kwargs: dict[str, Any] = {}
    if max_steps is not None:
        run_kwargs["max_steps"] = max_steps
    return sub.run(task, **run_kwargs)


def spawn_agents(
    jobs: Sequence[dict[str, Any]],
    return_type: Type[BaseModel] | None = None,
    tools: Sequence[Tool] | None = None,
    model: Any | None = None,
    max_workers: int | None = None,
    max_steps: int | None = None,
    additional_authorized_imports: list[str] | None = None,
) -> list[Any]:
    """Run a batch of sub-agents in parallel via a thread pool.

    Each `job` is a dict with at minimum a `task` key and an optional `scope` dict.
    Per-job `return_type`/`tools` override the batch defaults.
    """
    if not jobs:
        return []

    def _run_one(job: dict[str, Any]) -> Any:
        return spawn_agent(
            task=job["task"],
            scope=job.get("scope"),
            return_type=job.get("return_type", return_type),
            tools=job.get("tools", tools),
            model=job.get("model", model),
            max_steps=job.get("max_steps", max_steps),
            additional_authorized_imports=job.get(
                "additional_authorized_imports", additional_authorized_imports
            ),
        )

    with ThreadPoolExecutor(max_workers=max_workers or len(jobs)) as pool:
        return list(pool.map(_run_one, jobs))
