"""`revert(to_turn, reason)` — soft rewind the agent to a previous turn.

When the agent calls this tool:
1. Look up the commit sha for Turn N from the agent's `WorkspaceRepo`.
2. Re-execute notebook.py up to that commit via `replay(...)`, producing a
   fresh kernel state.
3. Swap the agent's executor state with the replayed state.
4. Truncate `agent.turns` to N entries.
5. Create a new branch `revert-from-N-<short_sha>` at the target commit and
   check it out — future commits land on the new branch. Failed-attempt
   commits stay on `main` (per the earlier design choice to preserve history).

Returns a short confirmation string the agent prints / uses in its next prompt.
"""
from __future__ import annotations

from typing import Any

from smolagents import tool

from memtree.replay import replay


def _sha_for_turn(agent: Any, turn_number: int) -> str:
    """Resolve a turn number to a commit sha by walking the repo log."""
    log = list(agent.repo.repo.iter_commits("main"))
    log.reverse()  # oldest first; index 0 = Turn 0 (initial scaffolding)
    if turn_number < 0 or turn_number >= len(log):
        raise ValueError(
            f"to_turn={turn_number} is out of range (0..{len(log) - 1})"
        )
    return log[turn_number].hexsha


def make_revert_tool(agent: Any, scope: dict[str, Any]) -> Any:
    """Build a smolagents tool that reverts the given agent.

    `scope` is the original Turn-0 variable bag (docs, conn, etc.) that the
    replay kernel needs to start from. Closed over by the tool.
    """

    @tool
    def revert(to_turn: int, reason: str) -> str:
        """Rewind the agent's kernel to the state at the end of an earlier turn.

        Use this after a recoverable mistake (corrupted variable, dropped column,
        wrong query). The reverted-from commits are preserved on `main`; we
        branch off the target so future work doesn't overwrite the failed path.
        Cannot revert to or past Turn 0 (initial scaffolding is locked).

        Args:
            to_turn: turn number to revert to (>= 1, < current turn).
            reason: one-sentence explanation, shown in the new branch's log.
        """
        if to_turn < 1:
            return f"Refusing to revert: to_turn={to_turn} is locked (Turn 0)."
        if to_turn >= len(agent.turns):
            return (
                f"Refusing to revert: to_turn={to_turn} is not in the past "
                f"(current turn = {len(agent.turns)})."
            )

        target_sha = _sha_for_turn(agent, to_turn)

        # 1. Rebuild kernel state by replay
        new_state = replay(
            repo=agent.repo,
            sha=target_sha,
            scope=scope,
            tools=list(agent.tools.values()),
            additional_authorized_imports=agent.additional_authorized_imports,
        )

        # 2. Swap state into the live executor
        executor = agent.python_executor
        executor.state.clear()
        executor.state.update(new_state)

        # 3. Truncate the in-memory turn list
        del agent.turns[to_turn:]

        # 4. Branch off the target commit so further commits don't clobber the
        #    preserved failed-attempt commits on `main`.
        short = target_sha[:7]
        branch_name = f"revert-from-{to_turn}-{short}"
        new_branch = agent.repo.repo.create_head(branch_name, target_sha)
        new_branch.checkout()

        return (
            f"Reverted to Turn {to_turn} (commit {short}). "
            f"Reason: {reason}. New branch: {branch_name}. "
            f"Kernel state rebuilt from replay; {len(agent.turns)} turns retained."
        )

    return revert
