"""MemTreeAgent — CodeAgent that captures every executed step as a `Turn`.

Hooks into smolagents' `_finalize_step` (the per-step lifecycle hook on
smolagents 1.25; `step()` is unused by the run loop, which calls
`_step_stream` directly). On each ActionStep we:

1. Project it into a `Turn` on `self.turns` and pretty-print it.
2. If `repo` is attached, commit the turn (notebook.py + tool_outputs.json).
3. Refresh `state_summary.json` so the dashboard sees current kernel state.
4. Honour any pending file-based revert request from the dashboard.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.panel import Panel
from smolagents import CodeAgent
from smolagents.memory import ActionStep

from memtree.state_summary import write_state_summary


@dataclass
class Turn:
    """One captured ReAct turn — what the agent thought, ran, and observed."""

    turn_number: int
    step_number: int  # smolagents' per-run step counter
    code: str
    observations: str
    tool_calls: list[dict]
    action_output: Any
    error: str | None
    token_usage: dict | None
    is_final_answer: bool


def _turn_from_step(turn_number: int, step: ActionStep) -> Turn:
    """Project a populated ActionStep into a Turn record."""
    tool_calls: list[dict] = []
    for tc in step.tool_calls or []:
        tool_calls.append(
            {
                "name": getattr(tc, "name", None),
                "arguments": getattr(tc, "arguments", None),
                "id": getattr(tc, "id", None),
            }
        )

    err = step.error
    if err is not None and not isinstance(err, str):
        err = f"{type(err).__name__}: {err}"

    tu = step.token_usage
    token_usage = (
        {"input": tu.input_tokens, "output": tu.output_tokens, "total": tu.total_tokens}
        if tu is not None
        else None
    )

    return Turn(
        turn_number=turn_number,
        step_number=step.step_number,
        code=step.code_action or "",
        observations=step.observations or "",
        tool_calls=tool_calls,
        action_output=step.action_output,
        error=err,
        token_usage=token_usage,
        is_final_answer=bool(step.is_final_answer),
    )


class MemTreeAgent(CodeAgent):
    """CodeAgent that records every executed step as a Turn on `self.turns`.

    When `repo` is supplied, each captured turn also appends to the repo's
    notebook.py and creates a git commit. Sub-agents are built without a repo,
    so their turns stay in memory only — see CLAUDE.md "Main agent only" choice.
    """

    def __init__(
        self,
        *args: Any,
        agent_label: str = "main",
        repo: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.agent_label: str = agent_label
        self.repo = repo
        self.turns: list[Turn] = []
        self._turn_console = Console()

    def _finalize_step(self, memory_step: Any) -> Any:
        result = super()._finalize_step(memory_step)
        if isinstance(memory_step, ActionStep):
            turn = _turn_from_step(turn_number=len(self.turns) + 1, step=memory_step)
            self.turns.append(turn)
            self._log_turn(turn)
            if self.repo is not None:
                # Refresh state_summary.json BEFORE the commit so it lands in
                # the same commit as the code that produced this state.
                write_state_summary(
                    self.python_executor.state,
                    self.repo.state_summary_path,
                    turn=turn.turn_number,
                )
                sha = self.repo.append_turn(turn)
                self._turn_console.print(
                    f"[dim]workspace commit:[/dim] [green]{sha[:7]}[/green]"
                )
                self._handle_revert_request()
        return result

    def _handle_revert_request(self) -> None:
        """If the dashboard wrote `.revert_request`, honour it and delete the file."""
        req_path = self.repo.path / ".revert_request"
        if not req_path.exists():
            return
        try:
            payload = json.loads(req_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            req_path.unlink(missing_ok=True)
            return
        req_path.unlink(missing_ok=True)  # consume request before acting

        to_turn = payload.get("to_turn")
        reason = payload.get("reason", "dashboard checkout")
        if not isinstance(to_turn, int) or "revert" not in self.tools:
            return
        msg = self.tools["revert"].forward(to_turn=to_turn, reason=reason)
        self._turn_console.print(f"[yellow]revert request honoured:[/yellow] {msg}")

    def _log_turn(self, turn: Turn) -> None:
        status = "FINAL" if turn.is_final_answer else ("ERROR" if turn.error else "ok")
        header = (
            f"[bold]{self.agent_label}[/bold] · Turn {turn.turn_number} "
            f"(step {turn.step_number}) · {status}"
        )
        body_lines = []
        if turn.code:
            body_lines.append(f"[dim]code:[/dim]\n{turn.code[:400]}")
        if turn.tool_calls:
            names = ", ".join(tc.get("name") or "?" for tc in turn.tool_calls)
            body_lines.append(f"[dim]tool_calls:[/dim] {names}")
        if turn.observations:
            body_lines.append(f"[dim]obs:[/dim] {turn.observations[:200]}")
        if turn.error:
            body_lines.append(f"[red]error:[/red] {turn.error[:200]}")
        if turn.token_usage:
            body_lines.append(
                f"[dim]tokens:[/dim] in={turn.token_usage['input']} out={turn.token_usage['output']}"
            )
        self._turn_console.print(Panel("\n".join(body_lines), title=header, border_style="blue"))
