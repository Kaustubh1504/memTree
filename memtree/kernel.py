"""Thin wrapper around smolagents' CodeAgent.

`build_agent` returns a `CodeAgent` wired with our MemEx primitives:
- `TypedFinalAnswerTool` replaces the stock `FinalAnswerTool` when a `final_answer_type` is given.
- Pre-loaded scope is injected via `inject_scope` before the first `run()`.
The persistent Python kernel and ReAct loop are smolagents' own.
"""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel
from smolagents.tools import Tool

from memtree.primitives.scope import inject_scope
from memtree.primitives.typed_submit import TypedFinalAnswerTool

DEFAULT_MODEL_ID = "gemini/gemini-2.5-flash"


def build_model(model_id: str = DEFAULT_MODEL_ID, **kwargs: Any) -> LiteLLMModel:
    return LiteLLMModel(model_id=model_id, **kwargs)


def build_agent(
    tools: list[Tool] | None = None,
    model: Any | None = None,
    final_answer_type: Type[BaseModel] | None = None,
    scope: dict[str, Any] | None = None,
    additional_authorized_imports: list[str] | None = None,
    **agent_kwargs: Any,
) -> CodeAgent:
    """Build a CodeAgent with MemEx primitives wired in.

    Args:
        tools: drop-in `@tool` functions.
        model: smolagents model instance; defaults to Gemini Flash via LiteLLM.
        final_answer_type: Pydantic model the agent's `final_answer(...)` must satisfy.
        scope: variables to pre-load into the agent's namespace before turn 1.
        additional_authorized_imports: extra modules the executor may import.
    """
    tools = list(tools or [])
    if final_answer_type is not None:
        tools.append(TypedFinalAnswerTool(final_answer_type))

    agent = CodeAgent(
        tools=tools,
        model=model or build_model(),
        additional_authorized_imports=additional_authorized_imports or [],
        **agent_kwargs,
    )

    if scope:
        inject_scope(agent, **scope)

    return agent
