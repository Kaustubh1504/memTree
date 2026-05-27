"""Thin wrapper around smolagents' CodeAgent.

`build_agent` returns a `CodeAgent` wired with our MemEx primitives:
- `TypedFinalAnswerTool` replaces the stock `FinalAnswerTool` when a `final_answer_type` is given.
- Pre-loaded scope is injected via `inject_scope` before the first `run()`.
The persistent Python kernel and ReAct loop are smolagents' own.
"""
from __future__ import annotations

import os
from typing import Any, Type

from pydantic import BaseModel
from smolagents import LiteLLMModel
from smolagents.tools import Tool

from memtree.agent import MemTreeAgent
from memtree.primitives.revert import make_revert_tool
from memtree.primitives.scope import inject_scope
from memtree.primitives.typed_submit import TypedFinalAnswerTool
from memtree.tools.cached import ToolCache, attach_cache

# Model + endpoint are env-driven so the same code runs against Gemini on a
# laptop and a vLLM server on an HPC GPU node without edits.
#   MEMTREE_MODEL_ID — LiteLLM model id (e.g.
#                      "hosted_vllm/Qwen/Qwen2.5-Coder-7B-Instruct",
#                      "gemini/gemini-2.5-flash"). See .env.example.
#   MEMTREE_API_BASE — optional endpoint override (vLLM default: http://localhost:8000/v1).
FALLBACK_MODEL_ID = "gemini/gemini-2.5-flash"
DEFAULT_MODEL_ID = os.environ.get("MEMTREE_MODEL_ID", FALLBACK_MODEL_ID)
DEFAULT_API_BASE = os.environ.get("MEMTREE_API_BASE")


def build_model(
    model_id: str | None = None,
    api_base: str | None = None,
    **kwargs: Any,
) -> LiteLLMModel:
    """Build a LiteLLMModel honouring MEMTREE_MODEL_ID / MEMTREE_API_BASE."""
    model_id = model_id or DEFAULT_MODEL_ID
    api_base = api_base or DEFAULT_API_BASE
    if api_base is not None:
        kwargs.setdefault("api_base", api_base)
    return LiteLLMModel(model_id=model_id, **kwargs)


def build_agent(
    tools: list[Tool] | None = None,
    model: Any | None = None,
    final_answer_type: Type[BaseModel] | None = None,
    scope: dict[str, Any] | None = None,
    additional_authorized_imports: list[str] | None = None,
    run_logger: Any | None = None,
    agent_label: str = "main",
    repo: Any | None = None,
    **agent_kwargs: Any,
) -> MemTreeAgent:
    """Build a CodeAgent with MemEx primitives wired in.

    Args:
        tools: drop-in `@tool` functions.
        model: smolagents model instance; defaults to Gemini Flash via LiteLLM.
        final_answer_type: Pydantic model the agent's `final_answer(...)` must satisfy.
        scope: variables to pre-load into the agent's namespace before turn 1.
        additional_authorized_imports: extra modules the executor may import.
        run_logger: optional `RunLogger` to capture every memory step.
        agent_label: tag attached to log lines so main/sub-agents can be told apart.
    """
    tools = list(tools or [])
    if final_answer_type is not None:
        tools.append(TypedFinalAnswerTool(final_answer_type))

    # When a workspace repo is attached, auto-wrap tools so their outputs are
    # written to repo.tool_outputs_path. This is what replay() consumes later.
    cache: ToolCache | None = None
    if repo is not None:
        cache = ToolCache(path=repo.tool_outputs_path)
        cache.load()
        attach_cache(tools, cache)

    if run_logger is not None:
        existing = agent_kwargs.get("step_callbacks") or []
        if isinstance(existing, dict):
            existing = list(existing.values())
        agent_kwargs["step_callbacks"] = list(existing) + [run_logger.step_callback(agent_label)]

    agent = MemTreeAgent(
        tools=tools,
        model=model or build_model(),
        additional_authorized_imports=additional_authorized_imports or [],
        agent_label=agent_label,
        repo=repo,
        **agent_kwargs,
    )
    agent.tool_cache = cache  # type: ignore[attr-defined]

    if scope:
        inject_scope(agent, **scope)

    # `revert` is only meaningful when there's a repo to walk back through.
    if repo is not None:
        revert_tool = make_revert_tool(agent, scope or {})
        agent.tools[revert_tool.name] = revert_tool

    return agent
