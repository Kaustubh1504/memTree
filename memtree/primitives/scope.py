"""Live scope at rollout start.

smolagents already keeps a persistent Python namespace in `agent.python_executor.state`.
We surface a tiny helper so callers can pre-load that namespace before turn 1, MemEx-style.
"""
from __future__ import annotations

from typing import Any

from smolagents import CodeAgent


def inject_scope(agent: CodeAgent, **variables: Any) -> None:
    """Inject variables into the agent's namespace so they exist on turn 1.

    Updates both `agent.state` (so subsequent `run()` calls re-send them) and the
    executor's live `state` dict (so they're visible immediately if `run()` has
    already initialised the executor).
    """
    agent.state.update(variables)
    if getattr(agent, "python_executor", None) is not None:
        agent.python_executor.send_variables(variables)
